-- Ejecutar en Supabase SQL Editor
-- Reescribe register_recycling_delivery para recibir user_id directamente
-- (el backend Python ya valida el JWT y pasa el user_id en p_token)

CREATE OR REPLACE FUNCTION register_recycling_delivery(
  p_token      TEXT,
  p_validator_id UUID,
  p_center_id  UUID,
  p_material   TEXT,
  p_kg         NUMERIC
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_user_id    UUID;
  v_profile    profiles%rowtype;
  v_pts        INT;
  v_co2        NUMERIC;
  v_trees      NUMERIC;
BEGIN
  -- p_token ahora recibe el user_id directamente desde Python (JWT ya validado)
  v_user_id := p_token::UUID;

  SELECT * INTO v_profile FROM profiles WHERE id = v_user_id;
  IF NOT FOUND THEN
    RETURN jsonb_build_object('success', false, 'error', 'Estudiante no encontrado');
  END IF;

  -- Calcular puntos y métricas según material
  v_pts := CASE p_material
    WHEN 'plastico'  THEN ROUND(p_kg * 50)
    WHEN 'papel'     THEN ROUND(p_kg * 30)
    WHEN 'vidrio'    THEN ROUND(p_kg * 40)
    WHEN 'aluminio'  THEN ROUND(p_kg * 80)
    ELSE                  ROUND(p_kg * 30)
  END;

  v_co2 := CASE p_material
    WHEN 'plastico'  THEN p_kg * 1.50
    WHEN 'papel'     THEN p_kg * 1.10
    WHEN 'vidrio'    THEN p_kg * 0.30
    WHEN 'aluminio'  THEN p_kg * 9.00
    ELSE                  p_kg * 1.00
  END;

  v_trees := v_co2 / 21.7;

  INSERT INTO recyclings (user_id, center_id, material, kg, points_earned, co2_saved_kg)
  VALUES (v_user_id, p_center_id, p_material, p_kg, v_pts, v_co2);

  INSERT INTO validator_actions (validator_id, center_id, action, payload)
  VALUES (
    p_validator_id,
    p_center_id,
    'RECYCLING_REGISTERED',
    jsonb_build_object(
      'student_id', v_user_id,
      'material',   p_material,
      'kg',         p_kg,
      'points',     v_pts
    )
  );

  -- Leer saldo actualizado (el trigger ya sumó los puntos)
  SELECT points INTO v_profile.points FROM profiles WHERE id = v_user_id;

  RETURN jsonb_build_object(
    'success',      true,
    'student_name', v_profile.full_name,
    'points_earned', v_pts,
    'new_balance',  v_profile.points,
    'co2_saved_kg', v_co2,
    'trees',        v_trees
  );

EXCEPTION WHEN others THEN
  RETURN jsonb_build_object('success', false, 'error', SQLERRM);
END;
$$;
