-- Execute this in the Supabase SQL Editor

CREATE TABLE IF NOT EXISTS public.merchant_banners (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  merchant_partner_id uuid NOT NULL,
  title text,
  banner_url text NOT NULL,
  link_url text,
  is_active boolean DEFAULT true,
  display_order integer DEFAULT 0,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT merchant_banners_pkey PRIMARY KEY (id),
  CONSTRAINT merchant_banners_merchant_partner_id_fkey FOREIGN KEY (merchant_partner_id) REFERENCES public.merchant_partners(id) ON DELETE CASCADE
);

-- Habilitar RLS si es necesario (asumiendo que el backend usa service_role y by-passes RLS, pero por si acaso)
ALTER TABLE public.merchant_banners ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Enable read access for all users" ON public.merchant_banners FOR SELECT USING (true);
CREATE POLICY "Enable all access for service role" ON public.merchant_banners USING (true) WITH CHECK (true);
