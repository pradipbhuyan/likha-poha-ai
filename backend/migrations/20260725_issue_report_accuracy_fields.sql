-- ─────────────────────────────────────────────────────────────────────────────
-- 20260725_issue_report_accuracy_fields.sql
-- Improve product-bug data capture so issues can be triaged/closed without
-- going back and forth with the reporter. Idempotent — safe to run multiple
-- times.
--
-- Adds:
--   - steps_to_reproduce, expected_behavior, actual_behavior (structured
--     repro data instead of everything crammed into one free-text field)
--   - reproducibility (always/sometimes/rarely/once)
--   - app_version, device_info (explicit environment capture — web build
--     tag / mobile app version + a human-readable device/browser string)
--   - reporter_email (denormalized at submit time so admins can follow up
--     without joining to auth.users/profiles)
-- Expands issue_type with more specific categories (audio/video, payments,
-- performance, sync, notifications, downloads, accessibility, feature
-- requests) so reporters aren't forced into "other" for common cases.
-- ─────────────────────────────────────────────────────────────────────────────

ALTER TABLE product_issue_reports
  ADD COLUMN IF NOT EXISTS steps_to_reproduce TEXT,
  ADD COLUMN IF NOT EXISTS expected_behavior  TEXT,
  ADD COLUMN IF NOT EXISTS actual_behavior    TEXT,
  ADD COLUMN IF NOT EXISTS reproducibility    TEXT,
  ADD COLUMN IF NOT EXISTS app_version        TEXT,
  ADD COLUMN IF NOT EXISTS device_info        TEXT,
  ADD COLUMN IF NOT EXISTS reporter_email     TEXT;

-- reproducibility CHECK constraint (idempotent add)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'chk_issue_reproducibility'
  ) THEN
    ALTER TABLE product_issue_reports
      ADD CONSTRAINT chk_issue_reproducibility
      CHECK (reproducibility IS NULL OR reproducibility IN ('always','sometimes','rarely','once'));
  END IF;
END $$;

-- Expand issue_type CHECK constraint with more granular categories.
-- Drop the old constraint (name assigned by Postgres from the inline CHECK
-- in the original CREATE TABLE follows the pattern product_issue_reports_issue_type_check)
-- and recreate with the wider list. Wrapped so it's safe if already applied.
DO $$
BEGIN
  ALTER TABLE product_issue_reports DROP CONSTRAINT IF EXISTS product_issue_reports_issue_type_check;
  ALTER TABLE product_issue_reports
    ADD CONSTRAINT product_issue_reports_issue_type_check
    CHECK (issue_type IN (
      -- Content & learning
      'content_issue','wrong_explanation','missing_section','wrong_formula',
      'wrong_answer','translation_language','audio_video_issue',
      -- Technical
      'broken_page','app_crash','slow_performance','sync_progress',
      'notification_issue','download_issue',
      -- Account & billing
      'login_issue','payment_billing',
      -- Other
      'accessibility_issue','feature_request','other'
    ));
END $$;

CREATE INDEX IF NOT EXISTS idx_issues_reproducibility ON product_issue_reports (reproducibility);
CREATE INDEX IF NOT EXISTS idx_issues_app_version      ON product_issue_reports (app_version);
