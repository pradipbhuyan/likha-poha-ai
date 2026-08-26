# Feature Matrix

This matrix is the product-level source of truth. Backend feature authorization and frontend rendering must match it.

## Subscription Feature Matrix

_"Nano" is retired (no new subscriptions, `isPublic:false`, purchase 404s) — column kept only to describe existing legacy holders' access until expiry. Premium 6-Month / Premium Annual behave like Premium; Family Annual behaves like Family Premium — omitted as separate columns for readability. See `03_SUBSCRIPTIONS.md` for the full current plan list, including the standalone Exam Prep Center add-on (not shown here — it does not grant any CBSE feature below; see the Exam Prep Center Feature Matrix)._

| Feature | Free Tier | Nano (legacy holders only) | Premium | Family Premium | Admin/Admin Grant |
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

> **Role override (added 2026-08-25):** regardless of plan, the **teacher role** cannot access Exemplar lessons, Exemplar section, or Exemplar research in any form — blocked unconditionally at the route layer (`backend/app/routes/teacher.py`, `backend/app/routes/doubt.py`). This is a student-only paid feature; the columns above describe student/parent access only. See `06_TEACHER_PLATFORM.md`.

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

**2026-08-26 update — access model changed:** the legacy per-exam pack purchase system (`exam_prep_packs`, JEE/NEET/CUET-only) was removed entirely (see `03_SUBSCRIPTIONS.md`'s 2026-08-26 section, TECH_DEBT.md TD-04). Content access is now a single flag: `subscription_plan_settings.access_exam_prep`, satisfied by the standalone **Exam Prep Center** plan (₹1,999/year — covers all 6 exams, no more per-exam partial access) or an admin/test-user override. Whether the main CBSE Premium/Family Premium plans *also* carry `access_exam_prep=true` is an admin-configurable DB setting (Admin → Subscription Settings), not fixed in code — verify the live value rather than assuming from this table.

| Access Type | JEE Main | NEET UG | CUET UG |
|---|---|---|---|
| Grade 5–10 student | ❌ Grade locked | ❌ Grade locked | ❌ Grade locked |
| Grade 11/12, `access_exam_prep=false` on current plan | 🔒 Preview only | 🔒 Preview only | 🔒 Preview only |
| Grade 11/12, `access_exam_prep=true` on current plan | Stream-dependent | Stream-dependent | ✅ Active |
| PCM stream | ✅ Eligible | ❌ | ✅ Eligible |
| PCB stream | ❌ | ✅ Eligible | ✅ Eligible |
| PCMB stream | ✅ Eligible | ✅ Eligible | ✅ Eligible |
| Admin role | ✅ Full | ✅ Full | ✅ Full |
| Test users (akshita.teststudent) | ✅ Full | ✅ Full | ✅ Full |

**Access check endpoint:** `GET /api/exam-prep/access-check` — always call this; never infer from plan string.

**Known gap:** the admin-editable `coaching_programs` visibility toggle (`backend/app/data/product_catalogue.py`, `PATCH /api/admin/product-catalogue/program`) is not read anywhere by `exam_prep.py`/`exam_prep_service.py` — flipping it has no effect. See TECH_DEBT.md.

**Question states:** `draft` (admin only) → `published` (students) → `archived` (hidden)

**Content source:** Admin generates via AI prewarm OR pastes JSON from ChatGPT/Custom GPT.

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
