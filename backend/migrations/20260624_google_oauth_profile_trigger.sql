-- Migration: auto-create profiles row for Google (OAuth) sign-ins
-- Run once in Supabase SQL Editor.
--
-- When a new user is created via Google OAuth, Supabase inserts a row into
-- auth.users but does NOT insert a profiles row — this trigger does that.
-- Existing email+password users are unaffected (ON CONFLICT … DO NOTHING).

CREATE OR REPLACE FUNCTION public.handle_new_oauth_user()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_family_id uuid;
  v_username  text;
BEGIN
  -- Only act on OAuth sign-ins (provider != 'email')
  -- For email/password signups the backend creates the profile explicitly.
  IF NEW.raw_app_meta_data->>'provider' = 'email' THEN
    RETURN NEW;
  END IF;

  -- Derive a display name from Google's user_metadata
  v_username := COALESCE(
    NEW.raw_user_meta_data->>'full_name',
    NEW.raw_user_meta_data->>'name',
    split_part(NEW.email, '@', 1)
  );

  -- Create a family for this user so parent-child features work if they upgrade
  v_family_id := gen_random_uuid();
  INSERT INTO public.families (id, family_name)
  VALUES (v_family_id, v_username || '''s Family')
  ON CONFLICT DO NOTHING;

  -- Insert the profiles row; ignore if it already exists
  INSERT INTO public.profiles (
    id,
    email,
    username,
    role,
    grade,
    board,
    parent_id,
    family_id,
    access_cbse,
    access_sof_science,
    access_sof_maths,
    access_sof_english,
    cbse_subjects,
    daily_token_limit,
    monthly_token_limit,
    subscription_plan,
    account_status
  ) VALUES (
    NEW.id,
    NEW.email,
    v_username,
    'student',          -- default role; user can change on first login
    'Grade 9',          -- default grade
    'CBSE',
    NULL,               -- no parent
    v_family_id,
    false,              -- no CBSE access by default; activate via offer code / payment
    false,
    false,
    false,
    '{}',
    50000,
    1000000,
    'free',
    'active'
  )
  ON CONFLICT (id) DO NOTHING;

  RETURN NEW;
END;
$$;

-- Drop old trigger if it exists (idempotent re-run safety)
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_new_oauth_user();
