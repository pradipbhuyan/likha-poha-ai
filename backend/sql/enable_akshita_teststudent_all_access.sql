-- One-time helper for the QA student account.
--
-- The application also contains a narrow username-based bypass for
-- akshita.teststudent so the account can test every grade, board, and subject.
-- This update keeps the profile flags aligned in Admin Control.

update public.profiles
set
  account_status = 'active',
  access_cbse = true,
  access_sof_science = true,
  access_sof_maths = true,
  access_sof_english = true,
  cbse_subjects = '[]'::jsonb,
  daily_token_limit = 0,
  monthly_token_limit = 0
where lower(username) = 'akshita.teststudent';
