# Product Requirements Document (PRD) — Likha Poha AI

_Reverse-engineered from the current codebase and `LikhapohaContext-docs/` on 2026-07-18. This is a living document — update it when business rules change._

---

## 1. Product Vision

Likha Poha AI is an AI-powered CBSE learning platform for students in Grades 5–12. It delivers structured AI-generated lessons, AI doubt-solving, mock tests, formula sheets, exemplar practice, and (for Grade 11/12) competitive exam prep (JEE Main, NEET UG, CUET UG) — wrapped in dashboards for four roles: **Student, Parent, Teacher, Admin**.

The product must be reliable, safe, mobile-friendly, and understandable to non-technical users (parents in particular).

## 2. Problem Statement

Indian CBSE students need affordable, on-demand, syllabus-aligned tutoring that adapts pacing to the individual, gives instant doubt resolution, and gives parents visibility into progress — without requiring a human tutor for every subject. Existing options are either expensive (private tutors) or generic (non-CBSE-aligned content).

## 3. Target Users & Personas

| Role | Who they are | Primary goal |
|---|---|---|
| **Student** | Grades 5–12, CBSE board, using web or Android app | Learn chapter content, clear doubts, practice, track progress, feel motivated |
| **Parent** | Pays for the subscription, manages 1–2 child profiles | Understand child's progress without interpreting raw data; manage subscription |
| **Teacher** | Manages a roster of assigned students (school or independent tutor) | Classroom productivity: know who needs attention, assign tasks, track intervention |
| **Admin** | Platform operators | Manage accounts, subscriptions, content quality, AI configuration, support |

## 4. Core Features by Role

### Student
- AI-generated step-by-step lessons per grade/subject/chapter (with audio narration/TTS)
- Ask Doubts — AI tutor Q&A with follow-up and history
- Mock tests — CBSE-style MCQs with instant scoring and analytics
- Formula Sheets — freemium reference content, Grade 5–12
- Exemplar lessons/research (NCERT Exemplar, RAG-grounded) — premium
- Exam Prep Center (Grade 11/12 only) — JEE Main, NEET UG, CUET UG: question bank, simulated tests, stream-eligibility gating
- Progress dashboard: streaks, achievements, weak-topic alerts, recommendations, exam countdown
- Platform Chat with teacher/parent (where enabled)

### Parent
- Add/manage child profile(s) — credential handoff on creation
- Dashboard: per-child status, progress story, strengths/weaknesses, mock test trend, recommendations
- Academic insights, printable progress report
- Notifications (feature-locked, inactive child, low score, expiry)
- Subscription management (view plan, upgrade, payment)

### Teacher
- Roster management within plan limits (10 free / 30 paid students)
- Student invitations (create, resend, cancel, expiry tracking)
- Classrooms (create, rename, archive, assign students, per-classroom analytics)
- Intervention queue (Needs Immediate Attention / Needs Review / Doing Well)
- Tasks (manual + suggested-from-intervention), private notes (never exposed to students/parents)
- Student Workspace: Overview, Progress, Assessments, Notes, Activity, Parent, Settings
- Teacher Assistant — rule-based summary of what needs attention today
- Parent communication (where linked)
- Credential email / password reset (credential email is paid-only)

### Admin
- Admin Console: Overview, Accounts, Families & Access, Associations, Offers, AI & Settings, Operations, Analytics, Support, Bulk Tools, Lesson Lab
- Operations Dashboard: system health, payments, webhooks, subscription monitoring, expiry job control
- Cache & Question Bank Management: lesson/audio/question prewarming, cost estimates
- Exam Prep Question Bank: AI generation + paste-import from ChatGPT/Custom GPT with 6-tier validation
- AI Studio: provider/model routing per feature, prompt template versioning, fallback provider config
- Subscription Settings: DB-driven plan pricing, duration, feature toggles — no code deploy needed
- Platform Chat admin controls (kill-switch, per-user grants, moderation)
- Product Bugs/Issues triage
- "View as User" read-only simulation
- Feature Authorization Audit / Lesson Quality Audit tooling

## 5. Monetization Model

| Plan | DB Key | Price | Duration | Access | Child Limit |
|---|---|---:|---:|---|---:|
| Free Tier | `free_tier` | ₹0 | forever | Limited | 1 |
| Premium Nano | `free` (legacy key) | ₹99 | 8 days | Full | 1 |
| Premium | `starter` | ₹299 | 30 days | Full | 1 |
| Family Premium | `family_premium` | ₹499 | 30 days | Full | 2 |
| Premium — 6 Months | `standard_6month` | ₹1,495 | 184 days | Full | 1 (hidden/admin) |
| Premium — Annual | `standard_annual` | ₹2,999 | 366 days | Full | 1 (hidden/admin) |
| Family Premium — Annual | `family_annual` | ₹4,999 | 366 days | Full | 2 (hidden/admin) |

**Note on `profiles.subscription_plan = "free"`:** this legacy DB value actually means **Premium Nano** (time-limited paid), not the free tier. True free tier is distinguished by the absence of `access_cbse=True` + `subscription_expires_at`. Never branch UI/business logic on this raw field — always use the canonical subscription resolver.

As of 2026-07-08, price, discount %, duration, and feature toggles (`access_exam_prep`, `access_exemplar`) are **DB-driven** via `subscription_plan_settings` — admins can change these without a code deployment.

## 6. Business Rules (Canonical)

1. Offer codes are not required for signup — every user can sign up free.
2. New users (and newly added children) always start on Free Tier.
3. Free Tier has restricted access; it must never accidentally receive full premium capability.
4. Nano/Premium/Family Premium grant full platform access only while active.
5. Nano expires after exactly 8 days; Premium/Family Premium after exactly 30 days (or DB-configured `duration_days`).
6. Expired paid plans fall back to Free Tier or valid offer-code access.
7. An active paid plan always overrides free/offer access.
8. Pending/failed payments never unlock premium access.
9. Admin ₹1 test payments are admin-only, must activate by intended plan ID (not charged amount), and must be audited.
10. Teacher: Free plan = 10 students, Paid plan = 30 students; credential email is paid-only.
11. Parent–child association is admin-controlled.
12. Admin-granted access is never revoked by the automated expiry job.
13. `parentId` alone never implies paid access for a child — only `access_cbse=true` does.
14. Feature access must always be resolved via the canonical Subscription Resolver + Feature Authorization service — never by inspecting raw fields (`subscription_plan`, `access_cbse`) in the UI or an endpoint directly.

## 7. Feature Access Matrix (summary)

| Feature | Free Tier | Nano | Premium | Family Premium | Admin |
|---|---|---|---|---|---|
| Core lessons | Limited | Full | Full | Full | Full |
| Exemplar lessons / research | No | Yes | Yes | Yes | Yes |
| Mock tests | Limited (5/day) | Full | Full | Full | Full |
| Ask Doubts / AI assistant | Limited | Full | Full | Full | Full |
| Formula Sheet expansion | Preview (3/chapter) | Full | Full | Full | Full |
| Exam Prep Center (Gr 11/12) | Preview only | Preview only | Stream-dependent full | Stream-dependent full | Full |
| Platform Chat | Admin-grant only | Auto-enabled | Auto-enabled | Auto-enabled | Always |
| Child profiles | 1 | 1 | 1 | 2 | Admin-controlled |

Full detail: `LikhapohaContext-docs/docs/FEATURE_MATRIX.md`.

## 8. Product Guardrails

- Never expose internal field names, raw Supabase/PostgREST errors, or teacher-private notes/admin audit metadata to end users.
- Never invent analytics — show "Not available yet" / "No activity during selected period" / "Unable to load" rather than fabricated data.
- Use "Platform Access" (not "CBSE Access") in all user-facing UI.
- Prefer clear business language over implementation language.
- No emoji in the Exam Prep Center UI (web or mobile) — use Lucide icons instead.

## 9. Definition of Done (per feature)

A feature ships only when:
- Backend enforces authorization (never frontend-only gating).
- Frontend renders the correct allowed/restricted state, including direct-URL navigation.
- Mobile UX is usable (mobile-first is mandatory).
- Sensitive actions are audited (`platform_audit_logs`).
- Tests cover success, failure, and access-denial paths, including Free/paid/expired/offer/admin-grant scenarios.
- Documentation is updated if business rules changed.

## 10. Non-Goals / Explicitly Out of Scope (current state)

- `homework` (standalone) is not built — the parent academic-insights endpoint returns `available:false` gracefully rather than fabricating data. (`exam_schedule` shipped since the original assessment — see `backend/app/routes/exam_schedule.py`: students self-manage exams via `/api/student/exams`, parents via `/api/parent/children/{id}/exams`, with a next-exam countdown on mobile. The parent *academic-insights* view specifically hasn't been wired to it yet and still stubs `exams: {available: false}`.)
- Admin Panel, Teacher Platform, and Sales/Influencer tools are **web-only by design** — not planned for mobile.
- Push notifications on mobile are not yet implemented.
- **SOF Olympiad (NSO/IMO/IEO) is discontinued** (removed 2026-07-18). The platform is CBSE-only. Do not re-add an "SOF" mode, `access_sof_*` fields, Olympiad subjects/RAG upload, or SOF mock-test/doubt/lesson branches — this was a deliberate product decision, not an oversight. A DB migration (`backend/migrations/20260718_remove_sof.sql`) drops the `access_sof_*` profile columns and purges SOF-tagged `question_bank`/`rag_documents` rows; confirm it has been run in Supabase before assuming those columns are gone.
- **Grades 1–4 are not supported** and never have been fully built out — no chaptered content, no question bank, no lesson prewarm. `getVisibleGrades()` in `frontend/src/utils/syllabusDefaults.js` hides them from every student/admin selector, and `SYLLABUS` in `backend/app/data/syllabus.py` only generates Grade 5–12. Do not build features assuming Grade 1–4 support without an explicit product decision to add it — it would require building the chaptering pipeline from scratch first (the same process Grades 5–10 already went through).

## 11. Success Signals (implicit from current tracking)

- Feature Authorization Audit: 42/42 automated checks passing (Free/Paid/Expired × all features, no leakage).
- Score integrity: all displayed scores normalized 0–100 via `_normalize_score_pct()`.
- Parent dashboard: "understand child's progress in under 10 seconds."
- Student dashboard: "know what to do next in under 5 seconds."
- Teacher dashboard: "know who needs attention within seconds" (single-page command center, no tab-clicking required for critical insight).

## 12. Roadmap Snapshot

See `06_IMPLEMENTATION_PLAN.md` for the full phased breakdown. Headline items:
- **Done:** Parent/Student/Teacher dashboards, Formula Sheets (96 formulas), signup redesign, Exam Prep Center core, Platform QA Center, TTS audio pre-warming, Platform Chat.
- **Pending:** Formula Sheet v3 migration (LaTeX/MCQ fields), Homework & Exam Center, LaTeX-to-speech for TTS, production hardening (E2E tests, load testing, Sentry, backups).
