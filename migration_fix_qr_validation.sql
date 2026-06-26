-- Ejecutar en Supabase SQL Editor
-- Elimina la validación de qr_tokens ya que el backend de Python (con JWT) ahora se encarga de esto de forma más segura.

CREATE OR REPLACE FUNCTION confirm_delivery(p_session_id UUID, p_qr_token TEXT, p_validator_id UUID)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
declare
  v_session delivery_sessions%rowtype;
  v_profile profiles%rowtype;
  v_item delivery_items%rowtype;
  v_user_id UUID;
begin
  -- p_qr_token ahora recibe el USER_ID directamente desde el backend en Python
  v_user_id := p_qr_token::UUID;

  select * into v_session
  from delivery_sessions
  where id = p_session_id and status = 'draft';

  if not found then
    raise exception 'Sesión no disponible o ya confirmada';
  end if;

  if not exists (
    select 1 from delivery_items where session_id = p_session_id
  ) then
    raise exception 'La sesión no tiene materiales registrados';
  end if;

  select * into v_profile
  from profiles where id = v_user_id;
  
  if not found then
    return jsonb_build_object(
      'success', false,
      'error', 'Estudiante no encontrado en la base de datos'
    );
  end if;

  -- Insertar recyclings por cada item
  for v_item in
    select * from delivery_items where session_id = p_session_id
  loop
    insert into recyclings
      (user_id, center_id, material, kg, points_earned, co2_saved_kg)
    values (
      v_user_id,
      v_session.center_id,
      v_item.material,
      v_item.kg,
      v_item.points_to_award,
      v_item.co2_saved_kg
    );
  end loop;

  update delivery_sessions set
    status       = 'confirmed',
    student_id   = v_user_id,
    confirmed_at = now()
  where id = p_session_id;

  insert into validator_actions (validator_id, center_id, action, payload)
  values (
    p_validator_id,
    v_session.center_id,
    'DELIVERY_CONFIRMED',
    jsonb_build_object(
      'session_id',   p_session_id,
      'student_id',   v_user_id,
      'total_points', v_session.total_points,
      'total_kg',     v_session.total_kg
    )
  );

  -- Leer el saldo actualizado DESPUÉS de que el trigger corrió
  select points into v_profile.points
  from profiles where id = v_user_id;

  return jsonb_build_object(
    'success',      true,
    'student_name', v_profile.full_name,
    'total_points', v_session.total_points,
    'total_kg',     v_session.total_kg,
    'total_co2_kg', v_session.total_co2_kg,
    'total_trees',  v_session.total_trees,
    'new_balance',  v_profile.points,
    'confirmed_at', now()
  );

exception when others then
  return jsonb_build_object(
    'success', false,
    'error',   sqlerrm
  );
end;
$$;
