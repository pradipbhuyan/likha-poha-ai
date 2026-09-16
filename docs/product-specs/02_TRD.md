# Technical Requirements Document (TRD) — Likha Poha AI

_Reverse-engineered from the current codebase (`backend/`, `frontend/`, `mobile/`) on 2026-07-18, last reviewed for accuracy 2026-07-21. Where the older `PLATFORM_ARCHITECTURE.md` (2026-07-15) disagreed with actual `package.json`/`requirements.txt` values, the live code wins and is called out below._

---

## 1. System Overview

```
React/Vite Web App  ─┐
                      ├─► FastAPI Backend (Render) ─► Supabase (Postgres+Auth+Storage+pgvector) ─► AI Providers
React Native Mobile ─┘                              ─► Razorpay (payments)
                                                      ─► Resend/SMTP (email)
```

Single FastAPI backend serves both web and mobile clients over HTTPS/JSON REST. No GraphQL, no direct client-to-Supabase table writes (except Supabase Auth itself).

## 2. Tech Stack (verified against source, 2026-07-18)

| Layer | Technology | Version (from source) |
|---|---|---|
| Web framework | React | 19.2.6 |
| Web build tool | Vite | 8.0.12 |
| Web test runner | Vitest | 4.1.7 (+ Playwright 1.60 for E2E) |
| Web UI libs | framer-motion 12, lucide-react 1.16, recharts 3.8, react-markdown 10, mermaid 11 | |
| Math rendering | KaTeX via rehype-katex 7 / remark-math 6 | |
| Auth client | @supabase/supabase-js | 2.106.2 (web), 2.45.0 (mobile) |
| Mobile framework | React Native | 0.81.5 |
| Mobile SDK | Expo | ~54.0.0 (SDK 54 — **not** SDK 53 as an older doc states) |
| Mobile router | expo-router | ~6.0.24 (**v6**, not v4) |
| Mobile language | TypeScript | ~5.9.2 |
| Mobile session storage | expo-secure-store | ~15.0.8 |
| Mobile OAuth webview | react-native-webview | ^14.0.1 |
| Backend framework | FastAPI | 0.136.1 |
| Backend language | Python | 3.13 |
| ASGI/WSGI | Plain Uvicorn, single process — no Gunicorn | |
| LLM orchestration | langchain 1.2.11, langgraph 1.1.0, openai 2.26.0 | |
| TTS | edge-tts 7.2.8 | |
| Database | PostgreSQL 15 (Supabase) + pgvector | |
| Payments | Razorpay | |
| Email | Resend (primary), SMTP (fallback) | |
| Web hosting | Vercel (auto-deploy from `main`) | |
| Backend hosting | Render (`api.likhapoha.in`; `nixpacks.toml`/`Procfile` both run plain `uvicorn app.main:app`). Migrated off Railway; a Railway deploy hook is still kept as an optional parallel target in CD, skipped automatically if unconfigured. | |
| Mobile distribution | Manual EAS/Gradle APK build → side-load (not yet Play Store) | |

**`newArchEnabled: true`** is required for the mobile app — React Native 0.81.5 needs New Architecture; disabling it causes silent crashes on some devices (confirmed on OxygenOS 16).

## 3. Backend Architecture

### 3.1 Route Domains (`backend/app/routes/`, actual files)

Auth & profile: `auth.py`, `profile.py`, `onboarding_guide.py`
Learning content: `lesson.py`, `lesson_experience.py`, `lesson_lab.py`, `lesson_repair.py`, `syllabus.py`, `doubt.py`, `mock_test.py`, `quiz.py`, `formula_sheets.py`, `formula_import.py`, `resources.py`, `images.py`, `progress.py`, `recommendations.py`, `study_planner.py`
Exam prep: `exam_prep.py`, `exam_prep_packs.py`, `exam_schedule.py`
Analytics/history: `analytics.py`, `weak_area_alerts.py`, `usage.py`, `unanswered_review.py`
Subscriptions/payments: `subscription.py`, `payments.py`, `offer.py`, `product_catalogue.py`
Parent: `parent_dashboard.py`, `student_dashboard.py`
Teacher: `teacher.py`, `teacher_dashboard.py`, `teacher_classroom.py`
Admin: `admin_analytics.py`, `admin_bulk.py`, `admin_control.py` (slimmed core), plus its feature-area split-outs — `admin_subscription_settings.py`, `admin_onboarding.py`, `admin_offer_codes.py`, `admin_associations.py`, `admin_ai_settings.py`, `admin_payment_logs.py`, `admin_blog_collaborators.py`, `admin_platform_settings.py` — `admin_operations.py`, `admin_qa.py`, `admin_support.py`, `admin_views.py`, `ai_studio.py`, `cache_management.py`, `evaluation.py`, `performance_tests.py`, `learning_simulation.py`
Other: `chatbot.py`, `platform_chat.py`, `issues.py`, `rag.py` + `rag_bulk_book_upload.py`, `sales.py`, `tts.py`

`parent_dashboard.py`/`teacher_classroom.py` no longer have `_p2`/`_v2` siblings (consolidated); `admin_control.py`/`rag.py` were proactively split by feature area for the same reason before they grew unmanageable — see `07_ARCHITECTURE_ASSESSMENT.md` §3.5.

### 3.2 Service Layer (`backend/app/services/`, ~60 modules)

Key services and responsibilities:

| Service | Responsibility |
|---|---|
| `auth_service.py` | Supabase admin client, JWT decode, profile creation |
| `subscription_resolver_service.py` | Canonical plan/access-state resolution |
| `feature_authorization_service.py` | Canonical feature-gate checks, including `_DB_DRIVEN_FEATURES` (exam prep, exemplar) |
| `subscription_timeline_service.py` | Append-only subscription lifecycle events, idempotency keys |
| `expiry_job_service.py` | Idempotent expiry sweep; never revokes admin grants |
| `audit_log_service.py` | Sanitized, non-blocking writes to `platform_audit_logs` |
| `metrics_service.py` | Redis-backed shared counters when `REDIS_URL` is set (survives restarts, shared across instances); falls back to process-local counters if Redis is unset/unreachable |
| `tutor_service.py` | LLM orchestration for lessons/doubts/tests |
| `openai_service.py` / `model_routing_service.py` | Provider abstraction across 9 LLM providers, per-feature routing, fallback |
| `rag_service.py` / `rag_visual_service.py` / `rag_job_service.py` | pgvector similarity search over NCERT Exemplar content |
| `lesson_cache_service.py` / `lesson_kb_service.py` / `prewarm_service.py` | Lesson Knowledge Base cache read/write, background pre-warming |
| `lesson_repair_service.py` | Detects and regenerates broken/low-quality lessons |
| `audio_cache_service.py` / `tts_service.py` | TTS generation, text-cleaning pipeline, dual-Supabase audio storage routing |
| `test_history_service.py` / `mock_test_service.py` | Mock test generation, scoring, persistence. CBSE MCQ format is bank-only at serving time (never calls an LLM live); `written`/`mixed` formats still call `ask_llm()` live per request (`_generate_written_questions()`) |
| `exam_prep_service.py` | JEE/NEET/CUET access-check, stream eligibility, question bank |
| `parent_dashboard_service.py` / `progress_service.py` / `recommendation_service.py` | Dashboard aggregation, weak-area detection, rule-based recommendations |
| `grade_db_router.py` / `supabase_grade_1112_client.py` | Routes queries between the two Supabase projects by grade |
| `email_service.py` | Resend primary, SMTP fallback, always non-fatal |
| `rate_limit_service.py` | Redis-backed sliding-window limiter, per-IP and per-user, shared across worker processes/instances when `REDIS_URL` is set; falls back to in-memory sliding-window on any Redis failure |
| `redis_client.py` | Shared Redis connection backing `rate_limit_service.py`/`metrics_service.py`; `None` (graceful no-op) when `REDIS_URL` is unset or unreachable |
| `chatbot_service.py` | Platform Chat business logic |
| `ai_studio_service.py` | Prompt template storage/versioning, provider/model config |
| `subscription_settings_service.py` | Canonical subscription plan/contact settings (`subscription_plan_settings`), shared by `auth.py`, `parent_dashboard.py`, `payments.py`, `exam_prep_packs.py`, `feature_authorization_service.py` |

### 3.3 Middleware Stack

Only two global ASGI middlewares are registered in `main.py`:
1. CORS — explicit allowlist (`likhapoha.in`, localhost, mobile `likhapoha://`); no wildcard origin in production.
2. `TracingMiddleware` (`app/middleware/tracing.py`) — injects a trace ID and logs structured request/response events for every call.

Rate limiting, auth, and audit logging are **not** global middleware — they're applied per-route: rate limiting via a `Depends(rate_limit_dependency(...))` on specific endpoints (stricter on `/auth/login`, `/auth/signup-free`), auth via the `get_current_user` dependency, and audit logging via explicit calls to `audit_log_service.py` inside individual route handlers.

### 3.4 Architectural Principles
1. Backend owns all business rules and authorization; frontend only renders decisions.
2. Subscription state is resolved by one canonical resolver — never re-derived ad hoc.
3. Feature access is gated by one canonical feature-authorization service/matrix.
4. Sensitive actions are audited.
5. Payments and webhooks are idempotent (`razorpay_payment_id` uniqueness).
6. Every dashboard (admin/teacher/parent/student) has one canonical summary endpoint — avoid N duplicate KPI queries.
7. UI components remain modular and mobile-friendly.

## 4. Frontend (Web) Architecture

- React 19 + Vite 8. No router library (`react-router` is not a dependency) — `App.jsx` switches between ~40+ directly-imported page components via local `useState`, not URL-based routing. Only a handful of real browser routes exist, for auth/marketing pages: `/`, `/signup`, `/blog`, `/blog/:slug`, `/reset-password`, `/refund-policy`, `/privacy-policy`, `/terms-of-service`.
- API access centralized through `authFetch` (`frontend/src/api/`) — attaches `Authorization: Bearer <supabase_jwt>`, handles 401/403 uniformly, retries briefly post-OAuth.
- State: React context (`frontend/src/context/ToastContext.jsx`) + local component state; no global store framework observed.
- Structure: `src/pages/` (~58 page components — note one, `QuizPage.jsx`, is unreachable dead code, not imported/routed anywhere), `src/components/` (feature-grouped, e.g. `components/teacher/`), `src/api/`, `src/config/` (e.g. `subscriptionPlans.js`, re-exported from `shared/`), `src/tests/` (Vitest) + `frontend/e2e/` (Playwright).
- Theming: CSS custom properties (`--surface`, `--text`, `--border`, `--panel`) with explicit light-mode fallbacks so components work correctly in both light and dark mode.

## 5. Mobile Architecture

- Expo SDK 54 managed workflow, `expo-router` v6 file-based routing under `mobile/app/`.
- Entry point **must** be `import "expo-router/entry"` in `index.ts` — never `registerRootComponent(App)` (bypasses the router, causes silent crashes).
- Storage adapter: `RobustStorageAdapter` in `mobile/lib/supabase.ts` — writes to an in-memory `Map` first, then best-effort `SecureStore`, because `expo-secure-store` fails silently on emulators without a lock screen.
- `authFetch.ts` mirrors the web 401/403 handling.
- Root layout (`_layout.tsx`) implements a Slot-based session guard (logged-in + in `auth/` → redirect to tabs; logged-out + not in `auth/` → redirect to login) with a `wasAuthenticated` ref guard against spurious `SIGNED_OUT` events during OAuth session replacement.
- APK build pipeline: `mobile/build_apk.sh` (git pull → feature checklist → bump versionCode → install → inject Zscaler network-security-config → gradlew assembleRelease → rename → commit/push).
- EAS archives from the repo root, so `.easignore` exists both at repo root and inside `mobile/`.

## 6. Database Layer

- **Platform:** Supabase (Postgres 15 + pgvector), split across **two projects**: a primary project (Grades 5–10 content, most tables) and a second project used for Grade 11/12 lesson cache and Exam Prep tables. `grade_db_router.py` selects the correct client per request.
- **Auth:** Supabase Auth (JWT, RS256), Row-Level Security policies enforced at the DB layer as defense-in-depth (backend authorization is still the primary trust boundary).
- **Storage:** Supabase Storage buckets for generated lesson audio (`lesson-audio`), routed by grade (Grade 9 → primary project's bucket; all other grades → the second project's bucket; the `lesson_audio_cache` **table** always lives on the primary project regardless of where the file is stored).
- Full schema detail: `05_BACKEND_SCHEMA.md`.

## 7. Authentication & Authorization

### JWT flow
1. Client authenticates (email/password or Google OAuth) against Supabase.
2. Supabase issues `access_token` + `refresh_token`.
3. Web stores the session via the Supabase JS client (localStorage); mobile stores it via `RobustStorageAdapter` (SecureStore + in-memory fallback).
4. Every API call sends `Authorization: Bearer <access_token>`.
5. Backend's `get_current_user()` decodes/validates the JWT via the Supabase admin client.

### OAuth — web vs mobile differ intentionally
| Platform | Flow | Why |
|---|---|---|
| Web | PKCE (`?code=` in redirect URL, `exchangeCodeForSession`) | Default Supabase v2 browser client behavior |
| Mobile | Implicit (`#access_token=` in redirect hash) via a **WebView** | Tokens arrive in a hash, not a code; `exchangeCodeForSession` fails on this path. WebView is used (not Chrome Custom Tab) because corporate Zscaler TLS inspection is only trusted via the app's own `network_security_config.xml`, which a WebView respects and Chrome's cert store does not. |

Known mobile OAuth fragility points and their fixes are documented in `LikhapohaContext-docs/docs/10_SECURITY.md` — consult that file first if OAuth breaks (secure-storage silent failure, spurious `SIGNED_OUT`, double token exchange, routing timing, repeat-login account caching).

### Authorization layers
| Layer | Mechanism |
|---|---|
| Route-level | `get_current_user` dependency → 401 if no valid JWT |
| Role-based | Handlers check `user.role` (`admin`/`teacher`/`parent`/`student`) |
| Subscription | Canonical resolver + `GET /api/subscription/features` |
| Ownership | `_verify_child_ownership()` for parent→child; teacher limited to assigned students |
| Grade/stream lock | Frontend reads `grade`/`stream`/`cbse_subjects` from `/api/auth/me` |
| Database | Supabase RLS as defense-in-depth |

New Google OAuth users have `oauth_profile_complete=false` until they complete a one-time role/grade picker via `POST /api/auth/oauth/complete-profile` (returns 409 on role conflict).

## 8. AI / LLM Layer

- **9 providers wired into live generation/fallback**: OpenAI, Venice AI, Groq, Cerebras, Gemini, SambaNova, NVIDIA, Ollama Cloud, Local Ollama. Anthropic is configurable and testable in AI Studio ("Test Connection") but has no branch in `get_chat_client()`/`ask_llm()`/the fallback dispatch — not actually callable for generation yet.
- **Per-feature model routing** — each feature (e.g. `lesson_repair`, `mcq_generation`) can be assigned a different provider/model via Admin → AI Studio → Model Routing.
- **Fallback provider** — configured via `admin_settings.ai_settings.fallback_provider`; `ask_llm()` automatically retries on the fallback when the primary provider times out or returns 429.
- **Prompt templates** — 10 default CBSE templates seeded and versioned in DB (`ai_studio_service.py`); each save creates a new version, any prior version can be reactivated.
- **RAG** — pgvector similarity search over NCERT Exemplar content; embeddings generated via an OpenAI embedding model; top-K chunks injected into the LLM prompt for grounded answers.
- **Lesson generation flow:** check cache (`lesson_kb`/`lesson_cache`) → build prompt from active template → call provider with retry → fallback provider on failure → validate/parse → write to cache → return structured markdown.

## 9. Payments

- **Provider:** Razorpay.
- **Signup-time payment:** `POST /api/auth/signup-order` (server creates order) → client opens Razorpay checkout → `POST /api/auth/complete-signup` verifies HMAC-SHA256 signature before creating the auth user + profile.
- **Upgrade payment:** `POST /api/payments/create-order` → checkout → `POST /api/payments/verify` verifies signature → updates `access_cbse`/`subscription_expires_at`.
- **Idempotency:** webhooks keyed on `razorpay_payment_id`.
- **Admin test payments:** ₹1 charge, admin-only, activates by intended plan ID (never by charged amount), always audited.

## 10. Non-Functional Requirements

### Security
- Backend is the sole trust boundary; no client-side-only access control.
- Pydantic models validate all request bodies.
- Parameterized queries via the Supabase client (no raw SQL string interpolation).
- React/RN auto-escaping; `dangerouslySetInnerHTML` avoided on auth paths.
- No secrets, API keys, or plaintext passwords ever returned to a client.
- `platform_audit_logs` never exposed to parents/students; teacher-private notes never exposed to parents/students.
- All `/api/admin/qa/*` and other admin endpoints require `require_admin`.

### Reliability
- Email failures are always non-fatal (never block signup/test submission).
- Missing/optional tables are queried via `_safe_query()` helpers that degrade gracefully instead of crashing.
- Expiry job and payment webhooks are idempotent and safely re-runnable.

### Observability
- Sentry (`observability_service.py::init_sentry()`) — wired at startup, error tracking; no-op if `SENTRY_DSN` isn't set.
- `metrics_service.py` — Redis-backed shared counters when `REDIS_URL` is set; falls back to process-local (reset on restart, not global) if Redis is unavailable.
- `platform_audit_logs` — durable audit trail for sensitive actions.
- `subscription_timeline` — durable, append-only subscription history for support/analytics.

### Performance
- Lesson/audio/question-bank pre-warming ("prewarm") pipelines pre-compute expensive AI generations ahead of user demand.
- TTS: pre-warmed audio served instantly from CDN when cached; falls back to live Edge TTS generation (~15–20s) on cache miss.

## 11. Testing Strategy

- **Backend:** pytest suite in `backend/tests/`.
- **Frontend:** Vitest unit tests (`frontend/src/tests/`) + Playwright E2E (`frontend/e2e/`).
- **Regression-critical suites:**
  - `scripts/audit_feature_authorization.py` — 42+ scenario matrix (Free/Paid/Expired/Offer/Admin-grant × every gated feature).
  - Lesson Quality Audit — deterministic + optional LLM checks, JSON/MD/CSV reports.
- Every behavior-changing PR must add regression tests per the Definition of Done in the PRD.

## 12. Deployment

| Component | Host | Trigger |
|---|---|---|
| Backend | Render (`nixpacks.toml`/`Procfile`, plain Uvicorn) — Railway kept only as an optional parallel deploy hook | Push to `main` |
| Web frontend | Vercel | Push to `main` (Vite build) |
| Mobile | Manual EAS/Gradle build (`build_apk.sh`) | Manual, side-loaded APK (not yet on Play Store) |
| Database | Supabase (2 projects) | Manual SQL migrations via Supabase SQL editor / Studio |

Migrations live in `backend/migrations/` as timestamped, idempotent SQL files (see the directory for current count — it changes often) and must be applied manually per-project (some apply to the primary Supabase project only, some to the Grade 11/12 project only — see `05_BACKEND_SCHEMA.md`).
