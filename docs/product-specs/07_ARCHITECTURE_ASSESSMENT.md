# Architectural Assessment — Likha Poha AI

_Assessment date: 2026-07-18. Last reviewed for accuracy: 2026-07-21 (see §3 for what's since been resolved). Grounded in direct inspection of `backend/app/`, `frontend/src/`, `mobile/app/`, and `shared/` — not just the context docs. Every finding below cites the file(s) it's based on._

---

## 1. Summary

Likha Poha AI has an unusually disciplined **authorization architecture** for a product at its stage — canonical resolvers, DB-driven feature flags, and audit trails are the kind of thing most teams retrofit painfully after an incident. That part is genuinely strong and worth preserving as a pattern (see `08_REUSABLE_PLATFORM_TEMPLATE.md`).

Most of the original P0/P1 risk list has since been fixed (Redis-backed rate limiting/metrics, `shared/` wired into both clients, secrets policy documented — see §3). What's left: the **two-Supabase-project split** still has no enforcement behind its documented rationale, and **`parent_dashboard.py`/`teacher_classroom.py`** are now the largest route files in the repo (the files that previously held this title, `admin_control.py`/`rag.py`, were split into feature-area modules and are no longer a concern).

## 2. Strengths (patterns worth keeping and reusing)

### 2.1 Single, canonical authorization path
`subscription_resolver_service.py` → `feature_authorization_service.py` is the only path any endpoint should use to decide access. The codebase backs this with an actual regression suite (`scripts/audit_feature_authorization.py`, 42+ scenarios) rather than just a convention in a doc. This is the single best thing about the architecture — it's rare to see "don't check raw `access_cbse` in the UI" enforced by a test rather than just a comment.

### 2.2 Idempotency discipline on money-adjacent flows
Payment verification, the expiry job, and subscription-timeline writes are all explicitly idempotency-keyed. Admin ₹1 test payments activate by intended plan ID, never by charged amount — a specific, non-obvious bug class (test payment accidentally granting a ₹1 plan) that was clearly anticipated and closed off deliberately.

### 2.3 DB-driven configuration for business-tunable values
`subscription_plan_settings` lets non-engineers change price, duration, discount, and feature toggles without a deploy. This is the right boundary — it's business logic that changes on a marketing cadence, not an engineering one, and it's been correctly pulled out of code.

### 2.4 Cost-aware AI layer
Multi-provider abstraction (9 providers) with per-feature model routing and automatic fallback isn't just resilience — it's active cost arbitrage (e.g. routing to free-tier Ollama Cloud models where quality allows). Combined with lesson/audio/question-bank pre-warming, this is a deliberate strategy to keep LLM spend proportional to content breadth rather than to live traffic. For an AI-per-request product, this is the difference between a viable and non-viable unit economics model.

### 2.5 Honest degradation over fabrication
The "tables that do not exist" documentation and the `_safe_query()` pattern reflect a real product principle (never show fabricated analytics) enforced structurally, not just by policy. This is unusually mature restraint for a product under growth pressure, where the easy shortcut is usually to fake a number.

## 3. Weaknesses & Risks (prioritized)

### P0 — Fix before the next scaling event

**3.1 / 3.2 — RESOLVED (2026-07-20).** Rate limiting and metrics are now Redis-backed (`redis_client.py`, `rate_limit_service.py`, `metrics_service.py`) with graceful in-memory fallback if Redis is unreachable, verified live in production. Originally: in-memory-only state meant each worker process got its own counters, so limits/metrics silently diverged the moment the backend ran more than one process.

**3.3 Two-Supabase-project split is a workaround wearing an architecture's clothes.**
Grade 5–10 data lives on one Supabase project, Grade 11/12 lesson cache and Exam Prep data on another, routed via `grade_db_router.py`. This means:
- Every new feature that might ever touch both grade bands has to remember to route correctly — a class of bug that's invisible until a Grade 11/12 user hits a Grade 5–10-only code path (or vice versa).
- No cross-project joins are possible, ever — any future feature wanting a single query across all grades (e.g. platform-wide leaderboard, cross-grade admin analytics) has to fan out manually.
- **Update (2026-07-21): the original driver is now documented** in `grade_db_router.py`'s module docstring. It is a temporary cost-deferral measure, not a deliberate sharding decision — both Supabase projects are on the free tier, and splitting Grade 11/12 content onto a second project keeps each project under the free-tier row/storage limits until Likha Poha AI has paying subscribers. The documented intended fix is to upgrade to a paid Supabase plan and merge both projects back into one once subscriber revenue justifies it — **not** to formalize this as permanent sharding architecture. This resolves the ambiguity that used to block deciding which fix path to take.
- What's still unresolved: this remains a *convention*, not an enforced one — `get_content_db()` is documented as the required single entry point for all content queries, but there is no lint rule or regression test (unlike the feature-authorization audit in §2.1) that catches a bare Supabase client call bypassing it for Grade 11/12 content. The trigger condition for the merge (paying-subscriber revenue covering the higher plan tier) is also not tied to any tracked metric or reminder — it currently only exists as a comment, so it's easy to let this ride indefinitely even after the condition is met.

### P1 — Fix within the next few quarters

**3.4 — RESOLVED.** `shared/` is now actually wired in: `frontend/src` re-exports through it (`utils/resolveSubscription.js`, `utils/subjectAccess.js`, `utils/markdownCleanup.js`, `config/subscriptionPlans.js`), and mobile imports it directly via `@likhapoha/shared/...`. No more duplicated client-side logic. Originally: the package existed but had zero imports from either client.

**3.5 Route file sprawl — pattern fixed, but two large files remain.**
The specific complaint here — `_p2`/`_v2` numeric-suffix files making it unclear which file owns an endpoint — is resolved: `parent_dashboard.py` and `teacher_classroom.py` are each back to a single file, and `admin_control.py`/`rag.py` (2,619 and 2,031 lines, the two largest files at assessment time) were proactively split into feature-area modules (`admin_subscription_settings.py`, `admin_onboarding.py`, `admin_offer_codes.py`, etc.; `rag_bulk_book_upload.py` + a new `rag_book_title_inference.py` service) before they caused the same problem.

What's not resolved: consolidation merged files, it didn't shrink them. `parent_dashboard.py` is now 1,658 lines and `teacher_classroom.py` is 1,933 lines — both larger than `rag.py` was before its split, and `teacher_classroom.py` isn't far off `admin_control.py`'s pre-split size. These are now the two largest route files in the repo and the natural next candidates for the same feature-area split treatment.

**3.6 No typed/generated schema layer.**
The existence of a documented "tables and columns that do NOT exist" section (`test_history.score`, `chapter_progress`, `ai_conversation_logs`) is a symptom: these are bugs a typed schema (e.g., Supabase-generated TypeScript types, or a Pydantic model per table validated in CI against the live schema) would catch at review time instead of requiring a standing document to prevent. The current mitigation is documentation discipline, which works only as long as every contributor (human or AI) reads it first — that's a process control substituting for a technical one.

**3.7 No CI-based mobile release pipeline.**
`build_apk.sh` runs manually on a developer's laptop, ending in a manual `git push` of the version bump. This is a single point of failure for releases (specific hardware, specific developer availability) and has no build-artifact provenance or reproducibility guarantee beyond "it worked on this machine." Not urgent while release cadence is low and the team is small, but it's the kind of thing that's much cheaper to move to CI now than after a release goes out with an environment-specific bug that can't be reproduced elsewhere.

### P2 — Worth planning for, not urgent

**3.8 Synchronous LLM calls share a process pool with fast CRUD requests.**
Cache-miss lesson generation, live doubt-answering, and mock-test generation all appear to run in-request against the same FastAPI/Gunicorn worker pool that serves dashboard reads. Pre-warming absorbs most of the load in practice, but any burst of cache misses (e.g., a new chapter added, or a content-quality sweep invalidating a batch of cached lessons) can starve unrelated dashboard traffic on the same instance. A background job queue for the generation path (even a lightweight one — Arq/RQ against Redis, or Supabase Edge Functions) would decouple these without a large rewrite.

**3.9 — RESOLVED.** See `09_SECRETS_ACCESS_POLICY.md` — secret inventory by blast radius, rotation cadence, and access-roster recommendation, written as the lightweight audit this item called for.

## 4. Recommended Sequencing

Items below are what's still open. §3.1, 3.2, 3.4, and 3.9 are done (see their entries above) and dropped from this table.

| Priority | Action | Why this order |
|---|---|---|
| P0 | Two-Supabase-project split (§3.3): add a lint/test that flags bare Supabase client calls bypassing `get_content_db()` for Grade 11/12 content, and tie the plan-upgrade-and-merge trigger to a tracked revenue metric instead of a comment | The decision (upgrade + merge once paying subscribers justify it) is already made and documented — what's missing is enforcement and a concrete trigger |
| P1 | Split `parent_dashboard.py` (1,658 lines) and `teacher_classroom.py` (1,933 lines) into feature-area modules (§3.5), same treatment already applied to `admin_control.py`/`rag.py` | They're now the two largest route files in the repo; do it before a new feature phase adds another `_p2`-style file out of habit |
| P1 | Generate typed schema bindings from the live DB and add a CI check that flags references to non-existent columns/tables (§3.6) | Converts the "tables that don't exist" doc from a read-it-or-suffer convention into a build-time guarantee |
| P2 | Move mobile builds to CI — EAS Build cloud + GitHub Actions (§3.7) | Removes single-laptop dependency before it causes a missed release |
| P2 | Introduce a background job queue for cache-miss LLM generation paths (§3.8) | Only urgent once traffic/content-churn grows enough for cache misses to cluster |

## 5. What Not to Change

Explicitly worth protecting during any refactor:
- The canonical subscription resolver / feature authorization split (§2.1) — this is the architectural backbone; any fix to §3.3–3.6 should route through it, not around it.
- The audit-log/subscription-timeline append-only pattern.
- The "never fabricate data, show explicit unavailable states" product principle and its `_safe_query()` implementation.
- The multi-provider AI abstraction with per-feature routing — this is a genuine cost-control moat, not incidental complexity.
