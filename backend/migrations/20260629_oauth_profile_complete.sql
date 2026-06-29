-- Migration: Add oauth_profile_complete flag + update OAuth trigger
-- Run once in Supabase SQL Editor.
--
-- oauth_profile_complete = FALSE means a Google OAuth user's profile was
-- auto-created by the trigger but the user has NOT yet explicitly chosen
-- their platform role via /api/auth/oauth/complete-profile.
--
-- oauth_profile_complete = TRUE (default) means the profile was set up
-- explicitly — either via email signup or via the OAuth complete-profile flow.
--
-- This column is the authoritative signal for whether to show role selection.
-- It replaces the unreliable "identity age < 3 min" heuristic in the frontend.

-- 1. Add the column (TRUE default so all EXISTING profiles are marked complete).
ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS oauth_profile_complete BOOLEAN NOT NULL DEFAULT TRUE;

-- 2. Replace the OAuth trigger so newly Google-created profiles get FALSE.
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
  -- Only act on OAuth sign-ins (provider != 'email').
  -- email/password signups always have their profile created by the backend.
  IF NEW.raw_app_meta_data->>'provider' = 'email' THEN
    RETURN NEW;
  END IF;

  -- Derive display name from Google metadata
  v_username := COALESCE(
    NEW.raw_user_meta_data->>'full_name',
    NEW.raw_user_meta_data->>'name',
    split_part(NEW.email, '@', 1)
  );

  -- Create a placeholder family so parent-child features work after upgrade
  v_family_id := gen_random_uuid();
  INSERT INTO public.families (id, family_name)
  VALUES (v_family_id, v_username || '''s Family')
  ON CONFLICT DO NOTHING;

  -- Insert placeholder profile.
  -- oauth_profile_complete = FALSE signals that the user still needs to
  -- explicitly choose their role via /api/auth/oauth/complete-profile.
  -- role = 'student' is a placeholder only; the backend endpoint overwrites it.
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
    account_status,
    oauth_profile_complete
  ) VALUES (
    NEW.id,
    NEW.email,
    v_username,
    'student',        -- placeholder; overwritten by /oauth/complete-profile
    'Grade 9',        -- placeholder
    'CBSE',
    NULL,
    v_family_id,
    false,            -- Free Tier: no CBSE access until explicitly granted
    false,
    false,
    false,
    '{}',
    0,                -- no token quota until profile is complete
    0,
    'free',
    'active',
    false             -- ← key flag: role not yet confirmed
  )
  ON CONFLICT (id) DO NOTHING;

  RETURN NEW;
END;
$$;

-- Re-create the trigger (idempotent)
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_new_oauth_user();
