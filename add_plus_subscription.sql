-- Migration: RECIPE Plus subscription support
-- Run this in Supabase SQL Editor (Dashboard → SQL Editor)
-- Safe to run multiple times (uses IF NOT EXISTS / ADD COLUMN IF NOT EXISTS)

-- 1. Add subscription columns to profiles table
ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS is_plus boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS plus_expires_at timestamptz DEFAULT NULL;

-- 2. Create subscriptions audit table
CREATE TABLE IF NOT EXISTS public.subscriptions (
  id                    uuid        NOT NULL DEFAULT gen_random_uuid(),
  user_id               uuid        NOT NULL,
  status                text        NOT NULL DEFAULT 'active'
                          CHECK (status IN ('active', 'expired', 'cancelled')),
  plan                  text        NOT NULL DEFAULT 'plus',
  amount_soles          numeric(10, 2) DEFAULT 5.99,
  izipay_order_id       text        UNIQUE,
  izipay_transaction_uuid text,
  starts_at             timestamptz NOT NULL DEFAULT now(),
  expires_at            timestamptz NOT NULL,
  created_at            timestamptz NOT NULL DEFAULT now(),
  updated_at            timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT subscriptions_pkey PRIMARY KEY (id),
  CONSTRAINT subscriptions_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE
);

-- Unique constraint: one active subscription row per user (upsert key)
CREATE UNIQUE INDEX IF NOT EXISTS subscriptions_user_id_idx ON public.subscriptions (user_id);

-- 3. Row-Level Security — backend uses service role key (bypasses RLS), but define policies anyway
ALTER TABLE public.subscriptions ENABLE ROW LEVEL SECURITY;

-- Service role bypasses RLS, so these policies are for direct Supabase client access only
CREATE POLICY IF NOT EXISTS "Users can read own subscription"
  ON public.subscriptions FOR SELECT
  USING (auth.uid() = user_id);
