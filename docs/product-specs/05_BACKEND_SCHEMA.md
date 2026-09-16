# Backend Schema Document — Likha Poha AI

_Reverse-engineered from `LikhapohaContext-docs/docs/11_DATABASE.md`, `Architecture/PLATFORM_ARCHITECTURE.md`, and `backend/migrations/` on 2026-07-18, last reviewed for accuracy 2026-07-21. Two Supabase (Postgres 15 + pgvector) projects are in play — call them **Supabase 1 (primary, Grades 5–10)** and **Supabase 2 (Grade 11/12 client)**. Always confirm which project a table lives on before writing a migration or query — several tables below are explicitly project-scoped._

---

## 1. Authentication & Profiles

| Table | Project | Purpose |
|---|---|---|
| `auth.users` | Both (Supabase-managed) | Supabase Auth users |
| `profiles` | Supabase 1 | User profiles — student, parent, teacher, admin |
| `families` | Supabase 1 | Family groupings (links parent ↔ children) |

### `profiles` — key columns
```sql
profiles (
  id uuid PRIMARY KEY,              -- = auth.users.id
  email text,
  username text,
  role text,                        -- 'student' | 'parent' | 'teacher' | 'admin'
  grade text,                       -- 'Grade 5' .. 'Grade 12' is the supported/content-backed range;
                                     -- FLAG: backend VALID_GRADES (auth.py, from product_catalogue.py's
                                     -- ALL_GRADES_INCLUDING_HIDDEN) currently accepts 'Grade 1'..'Grade 4'
                                     -- too, because product_catalogue.py marks them visible:True. No UI
                                     -- surfaces them (frontend hides 1-4) and no content exists for them,
                                     -- but server-side validation would not reject a directly-crafted
                                     -- signup/profile-update request for Grade 1-4. Worth a deliberate
                                     -- fix (mark 1-4 visible:False, or make VALID_GRADES exclude them) to
                                     -- match the documented "Grade 1-4 unsupported" decision (01_PRD.md §10)
                                     -- at the backend layer, not just the UI layer.
  stream text,                      -- 'PCM' | 'PCB' | 'PCMB' | 'Commerce' | 'Humanities'
  board text,                       -- 'CBSE'
  cbse_subjects text[],
  subscription_plan text,           -- DO NOT branch UI on this directly — canonical resolver only
  subscription_expires_at timestamptz,  -- nullable
  access_cbse boolean,              -- canonical paid-access flag
  -- access_sof_science/maths/english boolean columns EXISTED here until the
  -- SOF removal (2026-07-18) — see backend/migrations/20260718_remove_sof.sql.
  -- Do not re-add; SOF/Olympiad is discontinued (see 01_PRD.md §10).
  oauth_profile_complete boolean,   -- default TRUE; FALSE = new Google OAuth user pending role selection
  parent_id uuid,                   -- nullable, set when a parent creates a child
  family_id uuid,                   -- nullable
  account_status text,
  daily_token_limit int,
  monthly_token_limit int,
  study_streak_days int,
  lessons_completed int
)
```
**Gotcha:** `subscription_plan = "free"` is a legacy value meaning **Premium Nano** (time-limited paid), not the free tier. True Free Tier is distinguished by the absence of `access_cbse=true` + `subscription_expires_at`. Never infer plan from this column directly — use `subscription_resolver_service.py`.

## 2. Learning & Progress

| Table | Key columns | Notes |
|---|---|---|
| `student_progress` | `username, subject, chapter, completed, current_step_index` | **The only** progress table — `chapter_progress` / `lesson_progress` do **not** exist |
| `test_history` | `username, percentage (0-100), raw_score, max_score, subject, chapter` | Use `percentage` only. `score` and `total_questions` columns **do not exist** |
| `mock_test_wrong_answers` | per-question | Per-wrong-answer tracking for review |
| `weak_area_alerts` | `username, subject, chapter, best_score` | Drives "Weak Topics" dashboard cards |
| `ai_usage_logs` | `username, feature, created_at, total_tokens` | Canonical activity source — **not** `ai_conversation_logs` or `student_activity` (neither exists) |
| `lesson_cache` | `grade, subject, chapter, step_title, lesson_content, practice_questions` | Pre-generated lessons (Grades 5–10) |
| `lesson_kb` | Supabase 1 | Lesson Knowledge Base cache |
| `lesson_kb` (same table name) | Supabase 2 | Grade 11/12 copy — same table name on the second project, distinguished by which project's client `grade_db_router.get_content_db()` returns, not by a different table name |
| `doubt_history` | `user_id, question, answer, created_at` | Ask Doubt history |

### Score normalization rule
Always compute via `_normalize_score_pct(percentage, raw_score, max_score)`:
- `percentage` in `[0,100]` → use directly.
- `percentage > 100` → invalid, fall back to `raw_score / max_score * 100`.
- `max_score = 0` or no data → return `None` → UI shows "Score not available".
- Never multiply an already-percent value by 100 again.

## 3. Student Features

| Table | Purpose |
|---|---|
| `student_exam_schedule` | Exam dates added by the student or their parent; countdown display |
| `formula_sheets` | Formula reference content, Grade 5–12, freemium |

### `formula_sheets` — column generations
- **v1 (base):** `id, grade, subject, chapter, section_title, formula_name, expression, explanation, example, display_order, active, created_at`
- **v2 (applied):** adds `topic, variables, solution_steps, memory_tip, tags (TEXT[]), difficulty, chapter_order`
- **v3 (PENDING Supabase Studio application):** adds `expression_latex, variables_json (JSONB), use_when, mcqs_json (JSONB), source_type, status, quality_score, updated_at`
- **Fallback behavior:** if v3 hasn't been applied yet, the endpoint catches the resulting `42703` error and falls back to base columns automatically — no crash.

## 4. Parent Platform

| Table | Purpose |
|---|---|
| `parent_notifications` | Persistent notifications (feature_locked, child_inactive, low_score, expiry types), with a rule-based fallback when the table is empty |

## 5. Teacher Platform

| Table | Purpose |
|---|---|
| `teacher_student_assignments` | Teacher ↔ student relationships |
| `teacher_classrooms` | Classroom groupings |
| `teacher_tasks` | `title, priority, status, due_date, source, student_id` |
| `teacher_student_notes` | `note, visibility (teacher_private), soft-delete` — never exposed to students/parents |
| `teacher_parent_messages` | `subject, message, status (sent/failed/no_email)` |

## 6. Payments & Subscriptions

| Table | Purpose |
|---|---|
| `subscription_payments` | Payment records (Razorpay) — there is no separate `payments` table, despite the name suggesting one |
| `subscription_timeline` | Append-only lifecycle history, idempotency-keyed |
| `offer_redemptions` | Offer code usage tracking |
| `offer_codes` | Promotional codes for signup |
| `subscription_plan_settings` | **DB-driven plan config** (see below) |
| `subscription_contact_settings` | Support email/phone/WhatsApp shown on the parent subscription page |

### `subscription_plan_settings` — admin-configurable fields (2026-07-08+)
```
price                 → Razorpay charge amount (minus discount_percent)
discount_percent      → applied before charge
duration_days         → exact subscription validity, overrides legacy billing-label lookup
access_exam_prep      → gates Exam Prep Center (JEE/NEET/CUET) for this plan
access_exemplar       → gates Exemplar Research & Lessons for this plan
access_cbse           → core platform access after payment
daily_token_limit / monthly_token_limit → AI quota per plan
included / not_included → feature list text shown on the subscription page
```
Expiry resolution order (`plan_expires_at()` in `backend/app/routes/payments.py`):
1. `plan.duration_days` (DB-explicit, admin-configurable) — most precise
2. `_BILLING_LABEL_TO_DAYS` lookup — legacy fallback
3. `None` — perpetual / admin-grant

## 7. Admin / QA

| Table | Purpose |
|---|---|
| `lesson_quality_audit_runs` | Lesson quality audit job history |
| `platform_audit_logs` | Admin audit trail — **never** expose to parents/students |
| `product_issue_reports` | Student/user-reported bugs |
| `ai_prompt_templates` / `ai_prompt_template_versions` | Configurable, versioned AI prompt templates |

## 8. Exam Prep Center (Supabase 2 — grade_1112_client)

| Table | Purpose |
|---|---|
| `exam_prep_questions` | Question bank; states `draft → published → archived` |
| `exam_prep_attempts` | Student attempt records |
| `exam_prep_simulated_tests` | Simulated full-length test sessions |
| `exam_prep_simulated_test_answers` | Per-question answers within a simulated test |
| `exam_prep_prewarm_jobs` | Background AI-generation job tracking |
| `exam_prep_subscriptions` | Per-plan JEE/NEET/CUET pack subscription/purchase records |

## 9. TTS / Audio

| Table | Project | Purpose |
|---|---|---|
| `lesson_audio_cache` | **Always Supabase 1** regardless of where the audio file itself is stored | Pre-warmed TTS audio URLs |

```sql
lesson_audio_cache (
  id uuid PRIMARY KEY,
  cache_key text UNIQUE,     -- SHA256(grade|subject|chapter|step_title|voice|rate)
  grade text, subject text, chapter text, step_title text,
  voice text, rate text,
  audio_url text,            -- public CDN URL
  file_path text,            -- e.g. grade-9/english/chapter-1/concept-introduction.mp3
  file_size_bytes integer,
  status text,                -- active | archived
  created_at timestamptz,
  last_accessed_at timestamptz
)
```
**Storage routing** (`audio_cache_service.py`): Grade 9 → Supabase 1 `lesson-audio` bucket; all other grades → Supabase 2 `lesson-audio` bucket. **RLS:** admin full access; authenticated users read-only where `status=active`. **Index:** `lesson_audio_cache_lookup_idx` on `(grade, subject, chapter, step_title, voice, rate)`.

## 10. Platform Chat

| Table | Purpose |
|---|---|
| `chat_rooms` / `chat_messages` | Admin-to-student / student-to-teacher-and-parent messages, attachments via signed URL |

Settings (not a table, stored in `admin_settings.platform_chat_settings`): `global_enabled`, file/voice toggles, max file size (default 10MB), retention days (default 90, 0 = forever).

## 11. Tables That Do NOT Exist (do not query these)

| Table | Use instead |
|---|---|
| `chapter_progress` | `student_progress` |
| `lesson_progress` | `student_progress` |
| `homework` | not built — return `available: false` |
| `exam_schedule` (standalone) | `student_exam_schedule` |
| `ai_conversation_logs` | `ai_usage_logs` |
| `student_activity` | `ai_usage_logs` |

## 12. Safety Rules

1. Never expose `platform_audit_logs` to parents or students.
2. Never expose teacher-private fields (`teacher_student_notes`) to parents.
3. Missing/optional tables must be read via `_safe_query()` helpers — never crash the endpoint.
4. Student-owned data requires the `require_student` dependency.
5. Parent-owned data requires `require_parent` **and** `_verify_child_ownership()`.
6. Admin QA data (`/api/admin/qa/*`) requires `require_admin` on every endpoint.

## 13. Migrations (`backend/migrations/`, idempotent SQL)

Representative/most-relevant entries:

| File | Purpose |
|---|---|
| `20260627_parent_notifications.sql` | `parent_notifications` table |
| `20260628_formula_sheets.sql` | `formula_sheets` base table |
| `20260628_formula_sheets_v2.sql` | topic/variables/solution_steps/memory_tip/difficulty/chapter_order |
| `20260628_formula_sheets_v3.sql` | expression_latex/mcqs_json/source_type/status (**pending Studio application**) |
| `20260628_student_exam_schedule.sql` | `student_exam_schedule` table |
| `20260628_lesson_quality_audit_runs.sql` | QA audit job history |
| `20260703_lesson_audio_cache.sql` | `lesson_audio_cache` + RLS |
| `20260703_lesson_kb_grade_1112.sql` | `lesson_kb` table on the Grade 11/12 project |
| `20260707_exam_prep_center.sql` | `exam_prep_questions`, `_attempts`, `_simulated_tests`, `_simulated_test_answers`, `_prewarm_jobs` (Supabase 2) |
| `20260707_grade1112_stream.sql` | Adds `stream` column for Grade 11/12 exam eligibility |
| `20260708_subscription_plan_feature_flags.sql` | Adds `duration_days`, `access_exam_prep`, `access_exemplar` to `subscription_plan_settings` (Supabase 1) |
| `20260709_exam_prep_subscriptions.sql` | `exam_prep_subscriptions` table |
| `20260711_exam_prep_add_sat_ielts_toefl.sql` | Adds SAT/IELTS/TOEFL iBT to the exam-eligibility model |
| `20260712_platform_chat.sql` | `chat_rooms` + `chat_messages` tables |
| `20260718_remove_sof.sql` | Drops `access_sof_*` profile columns, purges SOF-tagged content rows (see §1) |

New migrations continue to land as timestamped files — check `backend/migrations/` directly for the current count and confirm target project before applying via the Supabase SQL editor (migrations are **not** auto-applied by CI).

## 14. Row-Level Security (RLS)

- Supabase RLS policies are treated as **defense-in-depth**, not the primary trust boundary — the backend (`get_current_user`, role checks, ownership checks) is the authoritative gate.
- Confirmed explicit RLS example: `lesson_audio_cache` — admin full access, authenticated read-only on `status='active'`.
- General pattern elsewhere: service-role key used server-side for privileged writes; anon key + RLS used for any client-facing direct Supabase reads (auth session only — the app does not otherwise let clients write tables directly).
