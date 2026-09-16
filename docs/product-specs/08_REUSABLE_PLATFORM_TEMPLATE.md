# Reusable Platform Template — "Multi-Role, Subscription-Gated, AI-Augmented Platform"

_A generalized architecture blueprint distilled from Likha Poha AI's strongest patterns (§2 of `07_ARCHITECTURE_ASSESSMENT.md`), with its known weaknesses (§3) designed out from day one. Applicable to any product with the same shape: several distinct user roles, tiered subscriptions gating features, AI/LLM calls in the critical path, and web + mobile clients sharing one backend. Examples beyond edtech: fitness/health coaching platforms, legal-assist tools, corporate L&D, therapy/coaching marketplaces, financial-advice apps._

---

## 1. When This Template Fits

Use this if your product has **most** of these characteristics:
- 2+ distinct user roles with different permissions (e.g., end-user / manager-of-end-users / staff / admin).
- A subscription or credit-based paywall gating specific features, not just "logged in vs not."
- AI/LLM calls that are expensive enough to need caching, provider fallback, or cost control.
- Web and mobile clients that must stay behaviorally consistent.
- A need for audit trails (payments, admin actions, or regulated data).

If you don't have tiered access control or AI cost pressure, this template is heavier than you need — a simpler CRUD-plus-auth starter will serve you better.

## 2. High-Level Architecture

```
┌────────────────────────────── CLIENT LAYER ──────────────────────────────┐
│  Web App (React/Vite)              Mobile App (React Native/Expo)        │
│       │                                    │                             │
│       └──────────────┬─────────────────────┘                            │
│         shared/ package (imported by both clients — see §3.2)            │
│         auth-state logic · plan/feature interpretation · formatting      │
└──────────────────────┼───────────────────────────────────────────────────┘
                        │ HTTPS/JSON, Authorization: Bearer <jwt>
┌───────────────────────▼───────────────────────────────────────────────────┐
│                          BACKEND API (single service)                     │
│  Middleware: CORS → Redis-backed rate limit → JWT auth → audit logging   │
│                                                                            │
│  Route layer (thin, one canonical module per domain, no _v2/_p2 forks)   │
│       │                                                                   │
│  Domain services  ──►  Canonical Access Layer  ──►  Data Access Layer    │
│  (business logic)      (Subscription Resolver +      (typed, generated   │
│                          Feature Authorization)        from live schema) │
│       │                                                                   │
│  AI Orchestration Layer (provider-agnostic, multi-provider fallback,     │
│  per-feature model routing, prompt template store, cache-first)          │
│       │                                                                   │
│  Background Job Queue (Redis-backed) — RECOMMENDED, not yet built in     │
│  LPAI: today's cache-miss generation runs in-request and pre-warming/    │
│  sweeps are manually-triggered scripts, not a queue (see §4)             │
└──────────┬───────────────────────────────┬───────────────────┬──────────┘
           │                               │                   │
   ┌───────▼────────┐            ┌─────────▼────────┐  ┌───────▼────────┐
   │  Primary DB     │            │  Redis            │  │  AI Providers   │
   │  Postgres +RLS  │            │  rate limits ·     │  │  (N providers,  │
   │  ONE schema,    │            │  metrics · job     │  │  1 fallback     │
   │  partitioned    │            │  queue · cache     │  │  chain)         │
   │  not split      │            └────────────────────┘  └────────────────┘
   │  across projects│
   └────────┬────────┘
            │
   ┌────────▼────────────────────────────┐
   │  Third-party: Payments · Email ·     │
   │  Object storage · Error tracking     │
   │  (Sentry) from day 1                 │
   └───────────────────────────────────────┘
```

**The one structural change from Likha Poha AI's actual architecture:** a single primary database instead of two separate database projects. To be precise about what's actually wrong with LPAI's version: routing discipline is *not* the problem — every content query already goes through one function (`get_content_db()`), so route/service files don't decide ad hoc. The two-project split exists purely to stay under Supabase's free-tier row/storage limits pre-revenue; it's a cost-deferral workaround, not a sharding decision (see `08`'s sibling doc, `07_ARCHITECTURE_ASSESSMENT.md` §3.3). The template's fix is simpler than "pick a sharding key" — it's "don't split at all until you actually need to shard for scale, and if you do, keep the same one-function-owns-routing discipline LPAI already has."

## 3. Core Patterns to Replicate (the parts that worked)

### 3.1 Canonical Access Layer — the most important pattern in this template

Every product in this shape needs exactly **two** services that everything else depends on, and nothing else should duplicate their logic:

```
SubscriptionResolver.resolve(user_id) -> {
  canonical_plan_key: str,      # stable enum, never a raw DB string
  access_level: str,
  has_full_access: bool,
  expires_at: datetime | None,
  entity_limit: int | None,     # e.g. "seats", "child profiles", "projects"
  restrictions: list[str],
}

FeatureAuthorization.check(user_id, feature: Feature) -> {
  allowed: bool,
  feature: str,
  canonical_plan_key: str,
  reason: str,                  # machine-readable, e.g. "upgrade_required"
  upgrade_message: str | None,  # human-readable, safe to show verbatim
}
```

**Rules that make this pattern actually hold over time:**
1. No route handler, no frontend component, ever reads a raw plan/subscription DB column directly. Grep for raw field access in CI (a simple regex lint rule) to enforce this mechanically, not just by convention.
2. `FeatureAuthorization` sits **on top of** `SubscriptionResolver`, never the other way around, and never independently re-derives access.
3. Feature-gate configuration (which plan unlocks which feature) lives in a DB table editable by non-engineers, with **immediate effect** (no deploy) — this is the single highest-leverage thing Likha Poha AI got right (`subscription_plan_settings`).
4. Ship a standing regression suite that walks every (plan × feature) combination and asserts the expected `allowed` value — build this in week one, not as an afterthought. It's cheap early and is the thing that catches "free tier got premium access" bugs before a user does.

### 3.2 Shared Client Logic — actually wire it in

Create the shared package early, and **prove it's used** with an automated check, not just good intentions:
```
shared/
  plan-interpretation.ts     # maps canonical_plan_key -> display label, badge, upgrade CTA
  feature-access.ts          # thin client wrapper around the FeatureAuthorization response shape
  entity-eligibility.ts      # any "which subset of content is this user allowed to see" logic
  score-normalization.ts     # or whatever your domain's "never trust raw numbers" helper is
```
Enforce with a CI lint rule: if `frontend/` or `mobile/` reimplements plan-label mapping or feature-check logic inline (detectable via a simple pattern match on the canonical plan key names), fail the build. This is the fix for the exact failure mode originally found in `07_ARCHITECTURE_ASSESSMENT.md` §3.4 — a good shared package that nobody imported because nothing forced anyone to. LPAI has since wired `shared/` into both clients (web re-exports through it, mobile imports it via a bundler resolver alias — not an actual npm/yarn workspace, just plain relative/aliased imports), but still has no CI check enforcing it stays that way; the lint rule above remains a real gap, not just a template nicety.

### 3.3 Idempotency by Default on Anything Money- or State-Adjacent

- Every payment webhook keyed on the provider's unique payment ID.
- Every "sweep" job (expiry, cleanup, batch recompute) is safe to re-run with no side effects on a second run — check-then-act, not act-then-check.
- Every append-only history table (subscription timeline, audit log) uses an idempotency key so retried writes don't double-record.
- Test-mode payment paths activate by an internal plan ID, never by the amount actually charged — a specific, cheap guard against test-payment-grants-wrong-plan bugs.

### 3.4 AI Orchestration Layer — provider-agnostic from day one

Even if you start with one LLM provider, build the seam now — it's much cheaper than retrofitting:
```
AIProvider interface: generate(prompt, params) -> response
ProviderRegistry: [primary, fallback_1, fallback_2, ...]
ModelRouting: per-feature provider/model assignment, admin-editable, DB-backed
PromptTemplateStore: versioned, admin-editable, DB-backed, hardcoded fallback if DB unavailable
```
Pair this with a **cache-first** generation path for anything content-shaped and reusable across users (lessons, summaries, generated exercises): check cache → generate on miss → write back to cache → return. Pre-warm the cache in a background job ahead of expected demand rather than always generating live. This is the single biggest lever on LLM cost at scale, and it's a pattern, not a specific vendor integration — it transfers directly to any AI-per-request product.

### 3.5 Never Fabricate Data

Every dashboard/summary field has three states: real value, explicit "not available yet," explicit "unable to load" — never a silently-defaulted zero or blank that looks like real data. Bake a `safe_query()` helper into the data access layer from the start so this is the path of least resistance, not an extra step engineers have to remember.

### 3.6 Audit Everything Sensitive, Expose Nothing Sensitive

- One `audit_log` table, append-only, sanitized at write time (strip anything that looks like a secret or full PII before it lands in the row).
- One rule, enforced by a lint/review checklist: role-scoped private fields (staff notes, admin metadata) are filtered at the service layer, not trusted to be filtered by the frontend.

## 4. What to Do Differently From Day One (fixes baked in, not retrofitted)

LPAI's rate limiting, metrics, and Sentry rows below are now fixed in production — kept here because the *reason to build it in from day one* still holds for a new product (these were expensive to retrofit under load, cheap to build in up front).

| Gap (fixed in LPAI on the date noted, or still open) | Template's day-1 answer |
|---|---|
| In-memory rate limiting, broke under multi-process — **fixed 2026-07-20**, now Redis-backed with in-memory fallback | Redis-backed rate limiter from the first deploy, even at low traffic — the cost is negligible and it removes an entire bug class later |
| Process-local metrics, unreliable dashboards — **fixed 2026-07-20**, same Redis backing | Metrics shipped to a shared store (Redis counters, or a real APM) from day one; never build an Ops Dashboard against in-process state |
| Two Supabase projects for cost reasons (not ad hoc routing — LPAI already routes through one function, `get_content_db()`) — **still open** | One database, one schema, with a single documented sharding/partitioning key if scale requires it later — decide before day one whether you need this at all, since retrofitting the merge is harder than never splitting |
| `shared/` package — **wired into both clients**, but still no CI enforcement that it stays that way — **partially open** | CI check that fails the build if plan/feature logic appears inline outside `shared/` |
| Route file sprawl via `_p2`/`_v2` version suffixes — **fixed**: `parent_dashboard.py`/`teacher_classroom.py` consolidated, `admin_control.py`/`rag.py` proactively split by feature area before hitting the same problem | Convention from day one: split by feature area within a domain as it grows (e.g. `admin_billing.py`, `admin_onboarding.py`), never by numeric/version suffix — a `_p2`/`_v2` file is the anti-pattern, not a second file per se |
| No typed schema, tribal-knowledge "these columns don't exist" doc — **still open** | Generate typed bindings from the live DB schema (e.g. `supabase gen types`, or an ORM with migrations as the single source of truth) and wire a CI check against them |
| Manual laptop-based mobile builds — **still open** | CI-based mobile build pipeline (EAS Build cloud, or equivalent) from the first internal release, not after the first missed release |
| Sentry/observability — **already wired** (`init_sentry()` at startup) | Wire error tracking before the first external user, not after the first incident |

## 5. Recommended Tech Stack (generalized, not vendor-locked to Likha Poha AI's exact choices)

| Layer | Recommendation | Why |
|---|---|---|
| Web frontend | React + Vite + TypeScript | Fast dev loop, large ecosystem, matches mobile's React Native mental model for shared engineers |
| Mobile | React Native + Expo (managed) | Fastest path to iOS+Android parity; use `expo-router` for file-based routing consistency with web's route structure |
| Shared logic | A shared package actually imported by both clients (plain relative imports, a bundler resolver alias, or a real npm/yarn workspace — LPAI uses the first two, not a formal workspace), enforced by CI (see §4) | The import mechanism doesn't matter much; whether anything forces it to stay used does |
| Backend | FastAPI (Python) or NestJS (TypeScript) — pick based on team's AI/ML tooling needs | FastAPI wins if you're doing in-process ML/embedding work; NestJS wins if the team is TS-first end to end |
| Database | Postgres (managed — Supabase, RDS, or Neon), one project/instance, RLS as defense-in-depth | Single source of truth; add read replicas before you add a second project |
| Cache / rate-limit / queue store | Redis from day one | Backs rate limiting, metrics, job queue, and generation cache with one piece of infrastructure |
| Background jobs | A queue worker (Arq/RQ/Celery for Python, BullMQ for Node) against the same Redis | Decouples slow AI-generation paths from fast CRUD request latency |
| AI providers | Design for 2+ providers from day one (primary + fallback), even if you only wire one initially | The seam is cheap now, expensive to retrofit once every call site assumes one provider's response shape |
| Payments | Stripe (global) or Razorpay (India-specific) — either way, webhook-idempotent from the first integration | |
| Observability | Sentry (errors) + a metrics store that survives restarts (not process-local) | Wire before first external user |
| Auth | Managed auth provider (Supabase Auth, Clerk, Auth0) over hand-rolled JWT issuance | Buys you OAuth flows, session management, and password-reset flows you don't want to own |
| Hosting | Render/Fly for backend, Vercel/Netlify for web, EAS Build (cloud) for mobile | Matches Likha Poha AI's proven choice (Render, having migrated off Railway), swaps the manual mobile build for the cloud equivalent |

## 6. Folder Structure Template

```
platform/
├── backend/
│   ├── app/
│   │   ├── routes/          # one file per feature area, no _v2/_p2 version suffixes
│   │   ├── services/
│   │   │   ├── access/      # subscription_resolver.py, feature_authorization.py — canonical, everything else depends on these
│   │   │   ├── ai/          # provider abstraction, model routing, prompt template store
│   │   │   ├── jobs/        # background job definitions (queue workers)
│   │   │   └── domain/      # one subfolder per business domain
│   │   ├── models/          # generated/typed schema bindings, not hand-maintained
│   │   └── data/
│   ├── migrations/          # versioned, CI-applied — never "apply manually via the DB console"
│   └── tests/
│       └── access_matrix/   # the (plan × feature) regression suite — build this in week one
├── frontend/
│   └── src/
├── mobile/
│   └── app/
├── shared/                  # imported by both frontend/ and mobile/, enforced by CI lint
│   ├── access/              # plan-interpretation.ts, feature-access.ts
│   ├── domain/              # normalization helpers, formatting, eligibility logic
│   └── config/
└── docs/                    # living architecture/product docs, same six-doc structure as this repo
```

## 7. Day-1 Checklist

Before writing the first feature-specific endpoint:
- [ ] `SubscriptionResolver` + `FeatureAuthorization` exist and are the only access-check path, even if there's only one plan today.
- [ ] `shared/` package exists, is imported by both clients for the first piece of cross-client logic, and CI fails if that logic gets duplicated inline.
- [ ] Redis is provisioned and used for rate limiting from the first deploy, not added later.
- [ ] Migrations are versioned and applied via CI, never via a manual console step.
- [ ] Sentry (or equivalent) is wired before the first external user.
- [ ] The (plan × feature) access regression suite exists, even with just 2 plans and 3 features — it grows with the product instead of being retrofitted under pressure.
- [ ] AI provider calls go through an abstraction with a fallback slot, even if only one provider is configured initially.
- [ ] Every dashboard/summary endpoint has an explicit "not available" state path — no field is ever silently defaulted to zero/blank.

## 8. What Doesn't Transfer

Not everything in Likha Poha AI's architecture is domain-general — these are specific to its constraints and shouldn't be copied blindly:
- The Zscaler-aware mobile WebView OAuth flow — only relevant if your users are on corporate networks with TLS-inspecting proxies.
- The exact 9-provider AI roster — the *pattern* (multi-provider, fallback, per-feature routing) transfers; the specific vendor list doesn't.
- Grade/stream-specific subject filtering — this is Likha Poha AI's domain model (CBSE curriculum structure); your equivalent "eligibility filtering" logic will look completely different but should live in the same architectural layer (`shared/domain/eligibility`).
- The temporary two-Supabase-project split (§2) — this exists solely to stay under Supabase free-tier limits pre-revenue. It is not a sharding pattern to replicate; the only reusable part is the single-function routing discipline (`get_content_db()`) that keeps it from spreading further while it lasts.
