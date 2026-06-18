-- Añade la columna expiration_days a la tabla merchant_products
-- Esta columna indica el número de días de vigencia de un cupón al ser canjeado.
-- Por defecto se asignan 30 días si no se especifica.

ALTER TABLE public.merchant_products
ADD COLUMN expiration_days integer DEFAULT 30;
