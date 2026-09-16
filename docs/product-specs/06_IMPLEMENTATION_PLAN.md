# Implementation Plan — Likha Poha AI

_Reverse-engineered from `LikhapohaContext-docs/docs/14_ROADMAP.md`, commit history, and current source state on 2026-07-18. Section 1 is what's already shipped (for context); Section 2 is the actionable forward plan, phased and prioritized._

---

## 1. What's Already Built (baseline)

### Foundation
- Free signup without an offer-code requirement; canonical subscription resolver + feature authorization service; DB-driven plan catalog (`subscription_plan_settings`); payment idempotency; audit logs; subscription timeline; expiry job; Admin Console.

### Parent Experience (Phases 1–3) — complete
- 9-tab child workspace, notifications, analytics, progress report, academic insights, Add Child flow with credentials panel, score normalization.

### Student Experience — complete
- Card-based dashboard redesign, canonical `GET /api/student/dashboard/summary`, exam schedule (student self-service CRUD + mobile countdown), Formula Sheet (96 formulas, Grade 5–12 freemium), signup redesign, session/OAuth reliability fixes, Lesson Page Workbook layout + TTS (including LaTeX-to-speech and unicode math-symbol conversion) + LKB chips, stricter practice-question scoring.

### Teacher Experience — complete (Phase 2/3)
- Command-center dashboard, Student Workspace (7 sections), interventions, tasks, private notes, classroom analytics, Teacher Assistant.

### Admin / Platform QA — complete
- Lesson Quality Audit, Feature Authorization Audit (42/42 checks passing), Cache & Question Bank Management, AI Studio (9 providers, model routing, prompt versioning), Subscription Settings (DB-driven), Platform Chat (with admin kill-switch), Exam Prep Center core (access-check, stream eligibility, paste-import with 6-tier validation), TTS pre-warming.

### Mobile
- Working Android app via Expo Go (SDK 54); standalone APK build pipeline functional; feature parity with web for lessons/mock tests/doubt/formula/analytics/exam prep/exemplar; admin, teacher, and parent dashboards intentionally **not** on mobile.

## 2. Forward Plan

### Phase 1 — Data Integrity & Content Quality (near-term, low risk, unblocks other work)

| Item | Why it's next | Effort |
|---|---|---|
| Apply `formula_sheets` v3 migration via Supabase Studio (`expression_latex`, `variables_json`, `mcqs_json`, `use_when`, `source_type`, `status`, `quality_score`) | Unblocks the Admin LLM Formula Prewarm workflow and richer formula MCQ practice; currently silently falling back to base columns | Small — migration + verify fallback removal |
| Admin LLM Formula Prewarm (`POST /api/admin/content/formula-sheets/prewarm`) | Depends on v3 migration; generates draft formula content per grade/chapter for admin review | Medium |
| Scan Grade 10 Science and Grade 8 Science for broken LaTeX (same process already used for Maths) | Known content-quality gap; process already exists, just needs to be re-run on these grades/subjects | Small, repeatable script run |
| Regenerate Grade 5 Santoor poem chapters with `POEM_SYSTEM` prompt (Papa's Spectacles, Rainbow, Frog, Vocation) | Currently mis-detected/thin content; archive stale cache + re-prewarm | Small |
| Re-run prewarm question generation for all Grade 5 chapters | Stricter scoring prompts shipped but Grade 5 bank wasn't regenerated against them | Small, batch script |

### Phase 2 — Audio/TTS Completion

LaTeX-to-speech and unicode math-symbol conversion (`clean_text_for_tts()` in `tts_service.py`) shipped since the original plan — moved to baseline (§1).

| Item | Why | Effort |
|---|---|---|
| Re-prewarm Grade 9 English audio to Supabase 1 (cleared July 2026) | Cache was cleared and not yet rebuilt | Small, script run |
| Audio prewarm for Grades 5–8 and Grade 10 via Supabase 2 | Extends TTS coverage beyond Grade 9 | Medium — cost/time scales with lesson count |

### Phase 3 — Lesson Page UX Polish

| Item | Why | Effort |
|---|---|---|
| Workbook layout responsive behavior under 768px (hide floating TOC, show inline section links) | Current floating TOC button is desktop-oriented | Small |
| "Next step" preview card at bottom of lesson for smoother navigation | Reduces friction returning to the top bar for every step | Small |
| Section-read progress tracking as student scrolls | Nice-to-have engagement signal, no backend table yet — would need a lightweight progress event, not a new table (`student_progress` may extend) | Medium |
| Grade 5 font-size review (`1rem` may be too large for early grades; consider `0.95rem` floor) | Cosmetic, low risk | Trivial |

### Phase 4 — New Feature Surface: Homework & Exam Center

`exam_schedule` shipped since the original plan (`student_exam_schedule` table, `/api/student/exams` + `/api/parent/children/{id}/exams` routes, student dashboard UI + mobile countdown — see §1). Remaining scope is narrower than originally stated:

| Item | Why | Effort |
|---|---|---|
| Design + migrate `homework` table | No homework table/routes exist yet — this remains a real capability gap | Medium — schema design, teacher-assignment flow, parent visibility rules |
| Teacher: assign homework to a classroom/student | Natural extension of existing Tasks/Classroom infrastructure | Medium |
| Wire Parent "Homework & Exams" tab / `academic-insights` endpoint to the **already-existing** `student_exam_schedule` data | `parent_dashboard.py`'s academic-insights endpoint still hardcodes `exams: {available: false}` even though the data now exists and `ParentChildWorkspace`'s homework/exams tab never calls the already-shipped `getChildExams` API | Small — integration, not schema work |
| Parent/Student: homework visibility once the `homework` table exists | Wire into `ParentChildWorkspace` "Homework & Exams" tab and Student "Today's Plan" | Medium |

Recommend sequencing this **after** Phase 1–3, since homework is still the largest net-new schema/authorization surface and should build on a stable content pipeline. The exam-schedule wiring task above is small and can happen anytime.

### Phase 5 — Production Hardening (parallelizable with Phases 1–4)

| Item | Why | Effort |
|---|---|---|
| E2E browser test coverage expansion (Playwright, `frontend/e2e/`) | Currently present but roadmap flags it as still needing broader coverage | Medium, ongoing |
| Performance / load testing | No current load-test evidence; `performance_tests.py` / `performance_test_service.py` exist as scaffolding — extend scenario coverage | Medium |
| Backup/restore procedures | Currently manual JSON export (`scripts/backup_db.py`) — formalize a tested restore runbook, not just a backup script | Small-Medium, mostly process |
| Confirm `SENTRY_DSN` is set in Render production env | Code integration is done (`observability_service.py::init_sentry()`, wired into `main.py` startup) — it's a documented no-op if the env var isn't set, so this is a config check, not an integration task | Small |
| Google Play Store submission | Mobile is currently side-loaded APK only; Play Store requires signing, store listing, and policy compliance review (data safety form, permissions justification) | Medium-Large, mostly process/compliance |

### Phase 6 — Mobile Parity Gaps

| Feature | Status | Recommended action |
|---|---|---|
| Push notifications | Not implemented (web or mobile) | Scope after Homework & Exam Center ships (notifications are more valuable once there's assignable homework/deadlines to notify about) |
| Doubt solving on mobile | **Confirmed shipped** — `mobile/app/(tabs)/doubt.tsx` exists. `MOBILE_APP.md` (dated 2026-07-12) marking this 🔲 is stale | No action needed — correct the stale doc |
| Analytics on mobile | **Confirmed shipped** — `mobile/app/(tabs)/analytics.tsx` exists. Same stale doc issue | No action needed — correct the stale doc |
| Google OAuth on mobile | Implemented via WebView (see App Flow §1.3) — the same stale doc marks this "planned" | No action needed — correct the stale doc |

**Verified 2026-07-18:** `ls mobile/app/(tabs)/` confirms `doubt.tsx` and `analytics.tsx` both exist alongside `lessons.tsx`, `mocktest.tsx`, `formula.tsx`, `examprep.tsx`, `exemplar.tsx`, `learn.tsx`. `MOBILE_APP.md` (2026-07-12) is out of date on this point; `Architecture/PLATFORM_ARCHITECTURE.md` (2026-07-15) was correct. Recommend updating `LikhapohaContext-docs/docs/MOBILE_APP.md`'s "Mobile vs Web Feature Status" table to remove this stale gap.

## 3. Known Technical Debt (carry-forward, track until resolved)

1. `chapter_progress` table was never created — every code path must use `student_progress` instead. Any new contributor (human or AI agent) touching progress code should be pointed at `05_BACKEND_SCHEMA.md` §11 first.
2. `test_history.score` / `total_questions` columns do not exist — `percentage` is canonical. Same guidance as above.
3. `formula_sheets` v3 migration not yet applied (see Phase 1).
4. Google OAuth has multiple documented edge-case fixes across web and mobile (secure-storage silent failure, spurious `SIGNED_OUT`, double token exchange, routing timing, account-picker caching) — these are fragile-but-fixed points, not open bugs, but any OAuth regression should check `LikhapohaContext-docs/docs/10_SECURITY.md` §"Known fragile points" **before** re-diagnosing from scratch.
5. `metrics_service.py` counters are process-local and reset on restart — do not present them as durable/global metrics in any stakeholder-facing report without that caveat.

## 4. Suggested Immediate Next Steps (if starting work today)

1. Apply the `formula_sheets` v3 migration (Phase 1) — smallest effort, unblocks the most downstream work (formula MCQ practice, admin LLM prewarm).
2. Run the existing broken-LaTeX scan script against Grade 8 and Grade 10 Science (reuses an already-built tool, pure content-quality win).
3. Scope the `homework` schema (Phase 4) as a design task even if implementation waits — `exam_schedule` is already built, so this is homework-only now. Separately, wire the Parent "Homework & Exams" tab to the already-existing exam-schedule data (small, independent of the homework schema work).
4. Update the stale mobile feature-status table in `LikhapohaContext-docs/docs/MOBILE_APP.md` (small doc-hygiene fix, see §2 Phase 6 note above).
