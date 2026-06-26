-- migration_atomic_redeem.sql
-- Ejecutar este archivo en Supabase SQL Editor para habilitar canjes atómicos (ALTO-1)

CREATE OR REPLACE FUNCTION redeem_product_atomic(p_user_id UUID, p_product_id UUID)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_product RECORD;
    v_user_points INT;
    v_current_time TIMESTAMPTZ := now();
    v_redemption_code TEXT;
    v_expires_at TIMESTAMPTZ;
    v_redemption_id UUID;
    v_merchant_data JSONB;
BEGIN
    -- 1. Bloquear producto para actualización (evita race conditions)
    SELECT * INTO v_product
    FROM merchant_products
    WHERE id = p_product_id
    FOR UPDATE;

    IF NOT FOUND OR v_product.is_active = FALSE THEN
        RETURN jsonb_build_object('error', 'Producto no encontrado o inactivo', 'code', 404);
    END IF;

    -- Validar disponibilidad
    IF v_product.status IS NOT NULL AND v_product.status != 'active' THEN
        RETURN jsonb_build_object('error', 'Producto no disponible', 'code', 400);
    END IF;

    IF v_product.available_from IS NOT NULL AND v_product.available_from > v_current_time THEN
        RETURN jsonb_build_object('error', 'Producto aún no disponible', 'code', 400);
    END IF;

    IF v_product.available_until IS NOT NULL AND v_product.available_until < v_current_time THEN
        RETURN jsonb_build_object('error', 'Producto expirado', 'code', 400);
    END IF;

    IF v_product.stock IS NOT NULL AND v_product.stock <= 0 THEN
        RETURN jsonb_build_object('error', 'Producto sin stock', 'code', 400);
    END IF;

    -- 2. Bloquear usuario para actualizar puntos
    SELECT points INTO v_user_points
    FROM profiles
    WHERE id = p_user_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RETURN jsonb_build_object('error', 'Perfil no encontrado', 'code', 404);
    END IF;

    IF v_user_points < v_product.points THEN
        RETURN jsonb_build_object('error', 'Puntos insuficientes', 'code', 400);
    END IF;

    -- 3. Descontar puntos
    UPDATE profiles
    SET points = points - v_product.points
    WHERE id = p_user_id;

    -- 4. Descontar stock (si aplica)
    IF v_product.stock IS NOT NULL THEN
        UPDATE merchant_products
        SET stock = stock - 1
        WHERE id = p_product_id;
    END IF;

    -- 5. Generar canje
    v_redemption_code := upper(substring(md5(random()::text) from 1 for 8));
    
    IF v_product.expiration_days IS NOT NULL THEN
        v_expires_at := v_current_time + (v_product.expiration_days || ' days')::INTERVAL;
    END IF;

    INSERT INTO merchant_redemptions (
        user_id, merchant_product_id, points_spent, redemption_code, status, expires_at
    ) VALUES (
        p_user_id, p_product_id, v_product.points, v_redemption_code, 'pending', v_expires_at
    ) RETURNING id INTO v_redemption_id;

    -- 6. Historial Wallet
    INSERT INTO wallet_entries (
        user_id, points, type, title, detail, emoji
    ) VALUES (
        p_user_id, v_product.points, 'spent', 'Canje: ' || COALESCE(v_product.name, 'Recompensa'), 'Marketplace', '🎁'
    );

    -- 7. Preparar respuesta
    SELECT jsonb_build_object(
        'id', id,
        'business_name', business_name,
        'logo_url', logo_url
    ) INTO v_merchant_data
    FROM merchant_partners
    WHERE id = v_product.merchant_partner_id;

    RETURN jsonb_build_object(
        'success', true,
        'redemption', jsonb_build_object(
            'id', v_redemption_id,
            'user_id', p_user_id,
            'merchant_product_id', p_product_id,
            'points_spent', v_product.points,
            'redemption_code', v_redemption_code,
            'status', 'pending',
            'expires_at', v_expires_at
        ),
        'product', jsonb_build_object(
            'id', v_product.id,
            'name', v_product.name,
            'points', v_product.points,
            'merchant', v_merchant_data
        )
    );
END;
$$;
