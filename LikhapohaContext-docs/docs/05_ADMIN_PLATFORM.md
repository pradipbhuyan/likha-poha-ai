# Admin Platform

_Last updated: 2026-07-07_

## Admin Console Structure

The Admin Console is mobile-friendly and organized into sections/tabs:

- Overview
- Accounts
- Families & Access
- Associations
- Offers
- AI & Settings
- Operations
- Bulk Tools / Support / Analytics as available

## Operations Dashboard

Admin-only dashboard showing:

- System health
- Payment monitoring
- Webhook monitoring
- Subscription monitoring
- Usage metrics
- Alerts/incidents
- Expiry job status and manual run

Operations endpoints must not expose secrets and must label process-local metrics clearly.

## Admin Productivity Features

- Quick Actions
- Global Search
- Favorites/Pinned Actions
- Recent Activity
- Notification Center
- Saved Views
- Analytics
- Support Tools
- Bulk Tools
- View as User read-only simulation

## Platform Access Terminology

Use “Platform Access” and “Platform Access (Admin Override)” in admin UI. Avoid “CBSE Access”.

## Support Tools

Support tools should provide:

- user search
- resolved subscription state
- subscription history
- sanitized audit history
- payment summary
- parent/teacher/student associations
- resend welcome/credential actions where supported
- reset temporary password with secure one-time handling

## View as User

Use frontend/read-only simulation. Do not issue user JWTs. Always show a banner and block destructive/payment/admin actions.

## Cache & Question Bank Management

### Cache Management Page (`/admin` → "Cache & Question Bank")

Admin-only page for generating and managing pre-warmed content.

**Sections:**
1. **Grade-by-grade prewarm** — lesson cache, question bank, Doubt KB, Audio cache, LKB chips
2. **Chapter-by-chapter prewarm** — test one chapter at time (~$0.002/chapter)
3. **Cost estimates** — dynamic based on model selection
4. **Exam Prep Question Bank (JEE/NEET/CUET)**
5. **Paste & Import Questions** — import from ChatGPT/Custom GPT
6. **Review & Publish Questions** — admin review panel

### Exam Prep Question Bank

**AI Generation:**
- Admin selects: Exam (JEE Main/NEET UG/CUET UG), Grade, Subject, Topic (optional), Question Count (1-50), Publish Mode (draft/auto_publish), Difficulty mix (Easy%/Medium%/Hard%)
- Backend: `POST /api/admin/exam-prep/question-bank/prewarm`
- All questions saved as `draft` by default unless publish_mode=auto_publish AND validation passes

**Paste & Import (from ChatGPT/Custom GPT):**
- Admin pastes JSON array from ChatGPT → validates → imports
- Endpoint: `POST /api/admin/exam-prep/questions/import-bulk`
- 6-tier validation:
  1. Required fields check
  2. Field value validation (exam_type, difficulty, correct_option, options A/B/C/D)
  3. GPT self-invalidation detection ("invalid and should be replaced" in explanation)
  4. Answer mismatch detection ("Therefore answer is X" ≠ correct_option) → `imported_with_warning`
  5. Exact deduplication via MD5 of question_text
  6. All valid → saved as `draft`
- Returns per-question report: imported / warnings / skipped_duplicate / skipped_invalid
- After successful import, Review panel auto-refreshes

**Question states:** `draft` → `published` → `archived`
- Draft: visible only to admin
- Published: visible to eligible students
- Archived: hidden from everyone

**Review & Publish Panel:**
- Filter by exam type, status (draft/published/archived), subject
- Expand any card to see full question, options, explanation, validation issues
- Per-question Publish / Archive buttons
- Bulk "Publish All" / "Archive All" buttons
- "Copy for AI Review" — copies all visible questions as a structured ChatGPT review prompt

### Light/Dark Mode
All form controls in admin pages use CSS variables with light-mode-compatible fallbacks:
- `background: "var(--surface,#f8fafc)"` — light gray in light mode, dark in dark mode
- `color: "var(--text,#1e293b)"` — dark text in light mode, light in dark mode
- `border: "1px solid var(--border,#e2e8f0)"` — subtle in light mode

## Admin Safety

- Audit sensitive admin actions.
- Require confirmation for destructive/bulk actions.
- Never expose secrets or plaintext passwords.
- Keep mobile layouts usable.
