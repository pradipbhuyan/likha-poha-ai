# Feature Matrix

This matrix is the product-level source of truth. Backend feature authorization and frontend rendering must match it.

## Subscription Feature Matrix

| Feature | Free Tier | Nano | Premium | Family Premium | Admin/Admin Grant |
|---|---|---|---|---|---|
| Core lessons | Limited | Full | Full | Full | Full |
| Exemplar lessons | No | Yes | Yes | Yes | Yes |
| Exemplar section | No | Yes | Yes | Yes | Yes |
| Exemplar research | No | Yes | Yes | Yes | Yes |
| Mock tests | Limited | Full | Full | Full | Full |
| Unlimited mock tests | No | Yes | Yes | Yes | Yes |
| Ask Doubts | Limited | Full | Full | Full | Full |
| AI assistant | Limited | Full | Full | Full | Full |
| AI solutions | Limited/Restricted | Full | Full | Full | Full |
| Progress view | Basic | Full | Full | Full | Full |
| Parent dashboard | Basic | Full | Full | Full | Full |
| Child profiles | 1 | 1 | 1 | 2 | Admin-controlled |

## Teacher Feature Matrix

| Feature | Free Teacher | Paid Teacher | Admin |
|---|---|---|---|
| Add students | Up to 10 | Up to 30 | Admin-controlled |
| Create classrooms | Yes | Yes | Yes |
| Student invitations | Yes | Yes | Yes |
| Email login details | No | Yes | Yes |
| Reset temporary password | Yes | Yes | Yes |
| Parent communication | If allowed by data model | If allowed by data model | Yes |
| Teacher notes | Yes | Yes | Yes |
| Interventions/tasks | Yes | Yes | Yes |

## Parent Feature Matrix

| Feature | Free | Paid | Family Premium |
|---|---|---|---|
| Add child | 1 child | 1 child | 2 children |
| View child dashboard | Basic | Full | Full |
| Progress analytics | Limited | Full | Full |
| Homework/exam insights | Limited | Full | Full |
| Notifications | Basic | Full | Full |

## Admin Feature Matrix

Admins can access admin console, operations, analytics, support tools, audit views, access management, parent-child linking, teacher-student linking, offers, AI settings, and payment test tools. Admin endpoints must still be server-side protected.

## Exam Prep Center Feature Matrix

Two independent access paths exist for exam prep content, both grade-11/12-gated:

1. **Bundled-in-plan** (`GET /api/exam-prep/access-check`) — Premium/Family Premium subscribers get `EXAM_PREP_CONTENT` automatically via `subscription_plan_settings.access_exam_prep` on their CBSE plan.
2. **Per-exam packs** (`POST /api/exam-prep/pack-order` + `/pack-verify`) — any Grade 11/12 student (including Free tier) can buy a single exam's pack independently of their CBSE plan, via `exam_prep_subscriptions`. Six packs exist: `exam_prep_jee`, `exam_prep_neet`, `exam_prep_cuet`, `exam_prep_sat`, `exam_prep_ielts`, `exam_prep_toefl` (`backend/app/data/subscription_plans.py`).

| Access Type | JEE Main | NEET UG | CUET UG | SAT | IELTS | TOEFL iBT |
|---|---|---|---|---|---|---|
| Grade 5–10 student | ❌ Grade locked | ❌ Grade locked | ❌ Grade locked | ❌ Grade locked | ❌ Grade locked | ❌ Grade locked |
| Grade 11/12 Free/Nano | 🔒 Preview only (bundled path) — pack purchase available | 🔒 Preview only (bundled path) — pack purchase available | 🔒 Preview only (bundled path) — pack purchase available | 🔒 Preview only (bundled path) — pack purchase available | 🔒 Preview only (bundled path) — pack purchase available | 🔒 Preview only (bundled path) — pack purchase available |
| Grade 11/12 Premium+ | Stream-dependent | Stream-dependent | ✅ Active | ✅ Active | ✅ Active | ✅ Active |
| PCM stream | ✅ Eligible | ❌ | ✅ Eligible | ✅ Eligible | ✅ Eligible | ✅ Eligible |
| PCB stream | ❌ | ✅ Eligible | ✅ Eligible | ✅ Eligible | ✅ Eligible | ✅ Eligible |
| PCMB stream | ✅ Eligible | ✅ Eligible | ✅ Eligible | ✅ Eligible | ✅ Eligible | ✅ Eligible |
| Admin role | ✅ Full | ✅ Full | ✅ Full | ✅ Full | ✅ Full | ✅ Full |
| Test users (akshita.teststudent) | ✅ Full | ✅ Full | ✅ Full | ✅ Full | ✅ Full | ✅ Full |

SAT/IELTS/TOEFL are open to all streams (global standardised tests have no stream prerequisite, unlike JEE/NEET's subject requirements). JEE/NEET/CUET stream eligibility is computed by `build_exam_eligibility()` in `backend/app/services/exam_prep_service.py`.

**Access check endpoint:** `GET /api/exam-prep/access-check` — always call this; never infer from plan string.

**Pack ownership endpoint:** `GET /api/exam-prep/my-packs` — which of the six packs the signed-in user currently owns (independent of CBSE plan).

**Question states:** `draft` (admin only) → `published` (students) → `archived` (hidden)

**Content source:** Admin generates via AI prewarm OR pastes JSON from ChatGPT/Custom GPT. As of 2026-07-31, JEE/NEET/CUET have populated question banks; **SAT/IELTS/TOEFL have no question bank content yet** — the schema, syllabus taxonomy, purchase flow and eligibility logic all support them, but admin content authoring for these three exams hasn't happened. IELTS/TOEFL packs cover Reading & Listening only — Writing/Speaking are not MCQ-based and are out of scope for this question-bank system.

**CUET UG subjects supported (2026-07-07):**
English, General Test, Physics (Domain), Chemistry (Domain), Mathematics (Domain), Biology (Domain), History, Geography, Political Science, Economics, Accountancy, Business Studies, Sociology, Psychology, Legal Studies, Hindi (Domain)

**CUET UG simulation:** Student picks subject combination (preset: PCM/PCB/PCMB/Commerce/Humanities or Custom), duration varies by section count, marking scheme +5/-1.

## DB-Driven Feature Toggles (2026-07-08)

Admin can enable/disable per-plan without code deployment:

| Feature | DB flag | Admin control |
|---|---|---|
| Exam Prep Center (JEE/NEET/CUET) | `subscription_plan_settings.access_exam_prep` | ✅ Admin → Subscription Settings |
| Exemplar Research & Lessons | `subscription_plan_settings.access_exemplar` | ✅ Admin → Subscription Settings |
| Subscription expiry | `subscription_plan_settings.duration_days` | ✅ Admin → Subscription Settings |
| Razorpay charge amount | `subscription_plan_settings.price` + `discount_percent` | ✅ Admin → Subscription Settings |

These changes take effect immediately for new subscriptions/feature checks without backend restart.

## Platform Chat Feature Matrix (Added 2026-07-12)

| Feature | Free Tier | Paid Plan | Teacher | Admin |
|---|---|---|---|---|
| Access platform chat | ❌ (admin-grant only) | ✅ Auto | ✅ Always | ✅ Always |
| Send text messages | Admin-granted only | ✅ | ✅ | ✅ |
| Send file attachments | Admin-granted only | ✅ (if global ON) | ✅ (if global ON) | ✅ (if global ON) |
| Send voice messages | Admin-granted only | ✅ (if global ON) | ✅ (if global ON) | ✅ (if global ON) |
| Contact routing | Student↔Teacher+Parent | Student↔Teacher+Parent | All students | All users |
| Admin kill-switch | `global_enabled=false` disables for everyone | — | — | Can toggle |

**Access enforcement:**
1. `GET /api/chat/settings` — always call before showing chat widget; never infer from plan string
2. `global_enabled=false` in `admin_settings.platform_chat_settings` overrides all other rules
3. Teachers always enabled (no subscription check)
4. Admins always enabled
5. Non-free plan → auto-enabled
6. Free users → only if their user_id is in `admin_settings.chat_access_users`

**Attachment rules:**
- Max file size: configurable by admin, default 10 MB
- Images >2 MB auto-compressed client-side before upload
- All files served via Supabase signed URL (1-hour expiry) — never public
- Voice: WebM format via MediaRecorder API (browser-native)
- Screenshot paste: Ctrl+V supported in conversation input

## Access Enforcement Requirements

For every feature above:

- Frontend must display allowed/restricted state.
- Backend endpoint must enforce authorization.
- Direct URL navigation must not bypass restrictions.
- Direct API calls must return 403 where restricted.
- Tests must cover Free, paid, expired, offer, admin grant, and admin scenarios where relevant.
