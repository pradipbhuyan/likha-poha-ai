# Tech Debt Register

_Last updated: 2026-08-26_

This file tracks known architecture, security, and operational debt across the platform (web, backend, mobile). It exists so debt is planned against deliberately instead of rediscovered by whoever hits it next.

Origin: a full-platform assessment (architecture / design / security / usability) conducted 2026-07-16, cross-checked against `10_SECURITY.md`, `14_ROADMAP.md`'s existing "Key Technical Debt" section, and direct code inspection (file sizes, middleware, auth guard coverage, dependency tree).

**2026-08-26 re-verification:** 422 commits landed between the original assessment and this pass. Every open item below was re-checked against current code (not against git history or old doc text). Two items closed (TD-04, TD-07 — mostly), one item's root cause got worse despite partial fixes (TD-03), one got worse in shape though not severity (TD-06), and five new items were found (TD-12–TD-16).

## How to use this doc

- **Status:** `Open` → `In Progress` → `Done` (move done items to the Resolved section with the date and what changed).
- **Priority:** `P0` (do next) · `P1` · `P2` — set at intake, re-rank anytime; this doc doesn't dictate order, planning conversations do.
- Add new items as they're found. Don't delete — move to Resolved so the history of what's been paid down is visible.

---

## Priority queue (P0)

Refreshed 2026-08-26. Order below is a recommendation, not a commitment — pick the starting point in planning.

| ID | Item | Category | Status |
|---|---|---|---|
| ~~TD-01~~ | ~~OAuth docs contradict actual behavior~~ | Security / Docs | ✅ Done — see [Resolved](#resolved) |
| [TD-02](#td-02-no-production-observability) | No production observability (errors, uptime) | Operational | In Progress — backend Sentry wired, DSN setup pending on you |
| [TD-03](#td-03-monolithic-files-at-the-eslint-ceiling) | Monolithic files driving CI lint ceiling | Architecture | Open — 2 of 8 original files fixed, but net worse: 5 new files crossed the same threshold |
| ~~TD-04~~ | ~~Exam Prep subscription model is ambiguous~~ | Architecture / Billing | ✅ Resolved, committed 2026-08-26 — see [Resolved](#resolved) |
| [TD-05](#td-05-mobile-release-process-is-a-single-fragile-local-script) | Mobile release process is a single fragile local script | Operational | Open — unverified this pass, versionCode has reached 50 |
| ~~TD-07~~ | ~~No rate limiting on any endpoint~~ | Security | ✅ Mostly resolved — see [Resolved](#resolved); residual gap tracked as [TD-13](#td-13-complete-signup-endpoint-has-no-rate-limit-and-leaks-username-availability-pre-payment) |
| [TD-12](#td-12-username-uniqueness-db-index-prod-applied-status-unverifiable) | Username-uniqueness DB index — prod-applied status unverifiable | Security | Open |
| [TD-13](#td-13-complete-signup-endpoint-has-no-rate-limit-and-leaks-username-availability-pre-payment) | `complete-signup` has no rate limit; pre-payment username enumeration | Security | Open |

---

## Architecture

### TD-03: Monolithic files at the ESLint ceiling
**Status:** Open · **Priority:** P0 · **Re-verified 2026-08-26 — table below refreshed, half the original files fixed, half worse**

| File | 2026-07-16 | 2026-08-26 | Verdict |
|---|---:|---:|---|
| `frontend/src/pages/AdminControlPage.jsx` | 3,932 | 3,920 | Unchanged — still open |
| `frontend/src/pages/RagUploadPage.jsx` | 3,428 | 3,058 | Shrank some — still open |
| `frontend/src/pages/LessonsPage.jsx` | 2,969 | 407 | **Fixed** — dissolved into `frontend/src/components/LessonSections.jsx` (1,126) + `frontend/src/components/journey/{StudyRenderer.jsx (634), JourneyRenderer.jsx (609), ChapterJourneyView.jsx (412)}` via the Chapter Journey refactor (`6d3eef21`) |
| `frontend/src/pages/ExamPrepPage.jsx` | 2,918 | 3,174 | **Grew** — still open |
| `backend/app/routes/admin_control.py` | 2,610 | 384 | **Fixed** — split into 8 focused route files: `admin_offer_codes.py` (604), `admin_associations.py` (367), `admin_onboarding.py` (286), `admin_platform_settings.py` (283), `admin_ai_settings.py` (246), `admin_subscription_settings.py` (181), `admin_blog_collaborators.py` (127), `admin_payment_logs.py` (121) — commit `62be9e29` |
| `backend/app/routes/rag.py` | 2,423 | 523 | **Fixed** — split into `rag_bulk_book_upload.py` (944) + `backend/app/services/rag_book_title_inference.py` (629), also `62be9e29` |
| `backend/app/services/exam_prep_service.py` | 2,393 | **2,631** | **Grew**, despite TD-04's cleanup removing ~104 lines of pack logic — other feature growth outpaced it. Still mixes access control with hardcoded syllabus data for all 6 exams (`JEE_SUBJECTS`, `NEET_BIOLOGY`/`PHYSICS`/`CHEMISTRY`, `CUET_SUBJECTS`, `SAT_SUBJECTS`, `IELTS_SUBJECTS`, `TOEFL_SUBJECTS`, `EXAM_SUBJECTS_MAP`, `EXAM_DATES`) — the suggested split below never happened |
| `frontend/src/App.jsx` | 1,869 | 2,152 | **Grew** — still open |

**New files that crossed ~1,500 lines since 2026-07-16 — not on the original list:**

| File | Lines |
|---|---:|
| `frontend/src/App.css` | **15,056** (was 15,099 when first measured; net -43 after TD-11's consolidation pass) — found 2026-08-26 while fixing TD-11. Not an ESLint-ceiling file (different linter applies to CSS, if any is configured at all), but bigger than every file in the original table combined. Holds the real `:root`/`body.dark-mode` token system plus 389 `body.dark-mode`-scoped rule blocks (738 declarations) — see TD-11 for the full breakdown of how much of that is genuinely load-bearing vs. consolidatable. |
| `frontend/src/pages/AdminCacheManagementPage.jsx` | 2,755 |
| `backend/app/routes/teacher_classroom.py` | 2,331 |
| `backend/app/routes/parent_dashboard.py` | 1,830 |
| `backend/app/routes/auth.py` | 1,829 |
| `backend/app/services/tutor_service.py` | 1,792 |

**Impact, updated:** the split pattern worked exactly as intended where it was applied — `admin_control.py` and `rag.py` both dissolved into focused files under ~1,000 lines each, proving the approach. It just wasn't applied platform-wide: `AdminControlPage.jsx`, `RagUploadPage.jsx`, `ExamPrepPage.jsx`, `App.jsx`, and `exam_prep_service.py` are unchanged or worse, and 5 new files independently grew past the threshold from ordinary feature work in the meantime. The count of files over ~1,500 lines is about the same as 2026-07-16 — just a different set.

**Suggested next cut:** `exam_prep_service.py`'s static syllabus dictionaries are still the easiest win — same suggestion as last time, still not done. `teacher_classroom.py` (2,331, new) and `parent_dashboard.py` (1,830, new) are the next-best candidates given the `admin_control.py`/`rag.py` split already proved the pattern works here.

---

## Security

### TD-08: No HTML sanitizer despite `dangerouslySetInnerHTML` usage
**Status:** Open · **Priority:** P2

`dompurify` (or equivalent) isn't in `frontend/package.json`. Two call sites inject raw HTML: `BlogPostPage.jsx` (`post.html`) and `ExamPrepPage.jsx`'s `MathText` component. Both are currently fed admin/build-authored content, so today's risk is low — but the content pipeline is trending toward more LLM-generated content with less per-item human review (bulk question import, formula prewarm). "Trust the source" doesn't scale with that trend. *(Not re-verified in the 2026-08-26 pass — carried forward as-is.)*

---

### TD-12: Username-uniqueness DB index — prod-applied status unverifiable
**Status:** Open · **Priority:** P1 · **Found 2026-08-26**

The real incident behind `dea9df74` (see `10_SECURITY.md`'s "Go-Live Security Hardening" section): two profiles both named "likha" leaked one child's mock-test scores to an unrelated parent. The fix has two layers — an app-level `_reject_taken_username()` guard (confirmed live) and `backend/sql/add_username_uniqueness_to_profiles.sql`, a DB-level unique index meant as the actual backstop. That SQL file is a **manual "run in Supabase SQL Editor" step** — nothing in the repo (migration runner, CI, deploy script) applies it automatically, so its applied-in-production status cannot be confirmed by reading code.

**Impact:** the app-level guard has the usual race-condition gap any app-level uniqueness check has (two concurrent signups both passing the check before either commits); the DB index is the only thing that closes that gap completely, and it might not be live.

**Resolution needed:** confirm in Supabase Studio (production project) whether the index exists; if not, apply it; either way, note the outcome here.

---

### TD-13: `complete-signup` endpoint has no rate limit, and leaks username availability pre-payment
**Status:** Open · **Priority:** P1 · **Found 2026-08-26, residual gap from TD-07**

`POST /api/auth/complete-signup` (`backend/app/routes/auth.py`) — the endpoint that finalizes a *paid* signup after checkout — has no `rate_limit_dependency`, unlike every other auth endpoint (see TD-07's Resolved writeup below). Worse: its `_reject_taken_username(data.name)` check runs *before* Razorpay signature verification, so an attacker can probe arbitrary usernames for existence at unlimited request rate without any proof of payment. Same enumeration shape the original TD-07 described for `/lookup-email/{username}`, on an endpoint that wasn't in scope at the time.

**Resolution needed:** add the standard `rate_limit_dependency` used elsewhere in `auth.py`; consider moving the username-availability check to after signature verification, or rate-limiting it independently of the endpoint as a whole.

---

## Operational

### TD-02: No production observability
**Status:** In Progress · **Priority:** P0

No error tracking (Sentry or equivalent), no uptime monitoring, no load testing — all listed as still-pending under `14_ROADMAP.md`'s "Production Readiness" section. The platform is a live paid product; right now, outages and errors are discovered via support tickets, not alerts.

**Progress (2026-07-16):** Backend Sentry wiring is code-complete but dormant — `app/services/observability_service.py`'s `init_sentry()` is called at startup, reads `SENTRY_DSN`/`ENVIRONMENT` from `app/config.py`, and no-ops safely when `SENTRY_DSN` is unset (verified: app imports and boots cleanly either way, `tests/test_health.py` passes). It does nothing until a real DSN is supplied. While in there, also fixed a duplicate `/api/health` route registration in `main.py` that was silently shadowing a dead handler.

**Re-checked 2026-08-26 — unchanged:** local `backend/.env` still has both `SENTRY_DSN` and `REDIS_URL` empty (fallback/no-op mode); `observability_service.py` and the newer `redis_client.py` both still no-op safely when unset. Neither `frontend/package.json` nor `mobile/package.json` has a Sentry package yet — the "still open after that" list below is still accurate as written, nothing new landed in this area since 2026-07-16. The duplicate-`/api/health` fix is confirmed still holding (exactly one handler).

**⚠️ Reminder — action needed from you (not automatable):**
1. Create a Sentry project at sentry.io (Python/FastAPI platform).
2. Copy its DSN into `SENTRY_DSN` in the real backend `.env` (local) **and** in Railway's env vars (production) — see `backend/.env.example` for the exact var names.
3. Set `ENVIRONMENT=production` in Railway specifically (defaults to `development` otherwise, which would mistag production events).

**Still open after that:**
- Frontend (`@sentry/react`) and mobile (`sentry-expo`) Sentry wiring — backend-only so far.
- Uptime monitor (e.g. UptimeRobot) hitting `GET /api/health`.
- Load testing — `backend/simulations/*.py` exist as manual journey scripts but aren't scheduled/automated.

---

### TD-05: Mobile release process is a single fragile local script
**Status:** Open · **Priority:** P0

`mobile/build_apk.sh` depends on: git credentials cached on one specific machine, a Zscaler corporate cert only present on that machine, and (until 2026-07-16) a `versionCode` bump that lived only in an uncommitted local file. That last gap caused two real incidents — build 17 and build 34 both had their version counter silently reset when local `app.json` changes were discarded before a `git pull`. The auto-commit-and-push fix landed 2026-07-16, but the underlying single-machine dependency (git auth, Zscaler cert, Android Studio/Java toolchain) remains.

*(Not independently re-verified in the 2026-08-26 pass — `versionCode` has reached 50 with no new incident reported, consistent with the 2026-07-16 auto-commit fix holding, but the single-machine dependency itself wasn't re-checked.)*

**Resolution needed:** move the build onto EAS Build or a CI runner so release capability isn't tied to one laptop.

---

### TD-16: `backend/scripts/` accumulates one-off scripts faster than it archives them
**Status:** Open · **Priority:** P2 · **Found 2026-08-26**

`backend/scripts/` currently holds 169 Python files (~48,400 lines). A sample of 27 plus pattern-matching across naming families found the dominant growth pattern is "one-off script per content batch, run once, never deleted": `ingest_exam_prep_month{1-13}_output.py` + `prepare_exam_prep_month{1-13}_prompts.py` (26 files, one new pair roughly monthly — month 13 landed 2026-08-07, month 14 is likely next), `backfill_grade*_visuals.py` (14 files), and assorted `fix_legacy_*`/`patch_*`/`migrate_*` one-offs. Rough estimate: **100+ of the 169 files are one-off/per-batch and safe-to-archive after they've run**, versus a smaller, genuinely load-bearing core (~25-35 files: `audit_*`, `seed_*`, `prewarm_*`, `backup_db.py`, the CI-referenced smoke/isolation scripts) that's still actively referenced in docs, CI workflows, or each other.

The 15 loose `fix*.py`/`add_*.py`/`fetch_*.py` scripts at the **repo root** (not `backend/scripts/`) are simpler: all 15 were added in a single commit (`49d11cb0`, 2026-07-29), have zero commits and zero references anywhere since, and are unambiguously one-off — safe to archive or delete outright.

**Impact:** low (doesn't break anything), but it makes `backend/scripts/` progressively harder to search for the tooling that *is* still live, and a fresh contributor can't tell which is which without git-blaming each file.

**Resolution needed:** no urgency, but consider a `backend/scripts/archive/` (or deletion, since git history preserves them) for scripts confirmed one-off, and a naming or README convention going forward so the distinction is visible without investigation. Start with the 15 root scripts — zero risk, zero ambiguity.

---

### TD-09: Deferred migrations have become permanent application logic
**Status:** Open · **Priority:** P2

`formula_sheets` v3 migration was never applied (per `14_ROADMAP.md`), so the code permanently carries a "catch Postgres error 42703, fall back to base columns" branch rather than a clean schema. This is a pattern worth watching — deferred migrations that the code has to permanently accommodate add up to real complexity over time.

---

## Design / Usability

### TD-10: Admin surfaces have outgrown "internal tool" usability
**Status:** Open · **Priority:** P2

`AdminControlPage.jsx` (3,932 lines) and `RagUploadPage.jsx` (3,428 lines) are hard for anyone but their original author to safely operate or extend. Same root cause as TD-03, but called out separately because the impact here is on the team's own operating experience, not just code maintainability.

---

### TD-11: Dark mode rolled out inconsistently rather than as a platform-wide system
**Status:** In Progress · **Priority:** P2

`14_ROADMAP.md` lists "Light/Dark Mode Compatibility (ExamPrepPage + AdminCacheManagementPage)" as a discrete recent fix, implying other surfaces got dark-mode support later and separately rather than via one token system applied platform-wide from the start.

**Progress (2026-08-26):** `frontend/src/App.css` does have one real token system (`:root` / `body.dark-mode`, both keying off the same `--bg`/`--panel`/`--text`/`--border`/etc. names) — the problem traced to concretely, not just "inconsistent style." A repo-wide diff of every `var(--x)` reference against every actually-defined `--x` found **5 token names used across 54 files that were never defined anywhere**: `--surface` (45 files, 158 call sites), `--card-bg` (6 files), `--text-secondary`, `--border-color`, and `--accent-soft` (1 file each). Every one of those call sites was silently frozen on its inline fallback color and never responded to the dark-mode toggle, despite being written to look token-based — this is very likely the direct cause of the "some pages just don't dark-mode" pattern this item describes. Separately, `--danger`/`--success`/`--warning` had no `body.dark-mode` override at all, which is why `App.jsx` had a hand-rolled `darkMode ? "#fbbf24" : "#b45309"` ternary instead of trusting `var(--warning)`.

**Fixed:** all 8 tokens now have explicit light and dark values in `App.css`. Verified via Playwright against the running dev server — `getComputedStyle` on all 8 now correctly flips value when `.dark-mode` is toggled (it didn't, for 4 of the 8, on the first attempt: an initial fix aliased `--surface: var(--panel)` on `:root`, which looked right but doesn't work — `:root` is the `<html>` element, one level above where `body.dark-mode` applies, so the cross-reference resolves against `:root`'s own light-mode cascade and never sees the override. Explicit values in both blocks, matching every other token in the file, is what actually works). Zero console errors; change is purely additive (new variable definitions only, no existing selector touched), so it can only affect the previously-broken call sites.

**Guardrail added (2026-08-26):** `frontend/scripts/check-css-tokens.mjs` — fails if any `var(--x)` reference anywhere in `src/` doesn't resolve to a token actually defined in `App.css`. Wired into `npm run lint:css-tokens` and into CI's `frontend-lint` job (`.github/workflows/ci.yml`), which gates merges to `main`. Verified against both a real positive (passes on the current, fixed tree) and a real negative (an injected fake `var(--totally-undefined-token)` was caught with exit 1 and a clear file:line message before being reverted). This is the part of the item that was fully achievable: **a 6th `--surface`-style token can no longer land undetected.**

**Correction to this item's original framing (2026-08-26):** the "50+ redundant blocks" estimate below was wrong — it generalized from the first ~15 `body.dark-mode` blocks in the file without checking the rest. A full parse (postcss AST, not regex) found **389 separate `body.dark-mode` rule blocks totaling 738 declarations** scattered across the entire 15,099-line file, not a contained "50-ish" section. Cross-referencing every one of those 738 against its corresponding light-mode/base rule found:

- **2 declarations** were purely dead weight — the base rule already used the matching token, so the dark-mode override did nothing at all.
- **65 more** were a hardcoded-twice pattern: the base rule had one literal color, the dark-mode override had a different hardcoded literal, and the two together exactly matched one existing token's light/dark pair (e.g. base `background: #ffffff` + dark override `background: #0f172a !important` — literally `--panel`, written out by hand in two places instead of referenced once). These were mechanically safe to consolidate: rewrite the base declaration to `var(--panel)`, delete the now-redundant override. **Done** — 28 base declarations tokenized, 23 dark-mode declarations removed, 14 rules left empty by that removal deleted outright. Verified via `getComputedStyle` before/after (identical resolved values in both light and dark) and a visual Playwright screenshot pass; zero console errors.
- **The remaining ~671 declarations are not redundant** — they're the *only* dark-mode styling for selectors whose base/light rule is itself a hardcoded literal, not a token reference. Deleting them would break dark mode for those components, not clean it up. This is the real shape of the debt: most of `App.css`, in both light and dark mode, was simply never written against the token system in the first place. It's not duplication of an existing system so much as ~600+ components each getting their own hand-picked light color and, separately and later, their own hand-picked dark color.

**Still open, and now accurately scoped:** converting those ~671 declarations' base rules to token references (which would then make each corresponding dark override deletable, the same way the 65 above were) is a real fix, but it's a fix of a different order of size — on the order of hundreds of individual selector+property pairs across a 15,099-line file, each needing the same base/dark cross-check done here, most of which won't cleanly match an existing token at all (bespoke per-component art, gradients, one-off accent colors) and would need a human product/design call rather than a mechanical rule. Not attempted. `App.css`'s size itself is tracked in TD-03.

---

## Resolved

_(move items here as they're closed, with date + what changed)_

### TD-01: OAuth documentation contradicts actual behavior
**Resolved:** 2026-07-16

`10_SECURITY.md` claimed PKCE flow as default and documented a specifically-retired workaround ("identity age fallback") as if still current, while `CODEX_CONTEXT.md` and mobile docs correctly described implicit flow on mobile and listed that same workaround as removed. This contradiction was traced to real recurring incidents in git history (`f6206fd`, `82a435f`, `bbcc86d` — repeated fixes for the same PKCE-vs-implicit mistake).

**What changed:** Rewrote `10_SECURITY.md`'s OAuth section (replacing "Google OAuth — Critical Rules") with a single platform-specific section: a Web-vs-Mobile flow table with the *why*, the web state machine (states A–D, cross-checked against the live `GET /me` / `POST /oauth/complete-profile` handlers in `backend/app/routes/auth.py`), the mobile `handleOAuthSuccess()` flow-detection logic (cross-checked against `mobile/app/auth/login.tsx`) with its five known fragile points and their fixes in priority-check order, and an explicit "Retired — do not reimplement" list for the two techniques that were tried and removed.

---

### TD-04: Exam Prep subscription model is ambiguous
**Resolved:** 2026-08-26 (verified in the working tree; confirm `git log` shows it committed before treating as permanent)

Two coexisting, contradictory gating mechanisms existed for Exam Prep content access: a legacy `exam_prep_subscriptions` table / `exam_prep_packs.py` route (per-exam pack purchases, only `jee_main`/`neet_ug`/`cuet_ug` — couldn't even represent SAT/IELTS/TOEFL, which were fully built out elsewhere) vs. the canonical `Feature.EXAM_PREP_CONTENT` check. Unclear from the code alone which was authoritative.

**What changed:** the legacy pack system was deleted outright rather than revived — per its own removal comment in `subscription_plans.py`, no customer ever held a pack. Removed: `backend/app/routes/exam_prep_packs.py`, `backend/tests/test_exam_prep_packs.py`, `frontend/src/api/examPrepPacks.js`, and the pack-aware helpers `get_active_packs()` / `check_exam_content_access_with_packs()` from `exam_prep_service.py`. The `exam_prep_subscriptions` table is left as an unread historic migration. Exam Prep access is now gated by exactly one mechanism: `exam_prep_service.check_exam_prep_content_access()` → canonical `Feature.EXAM_PREP_CONTENT` → `subscription_plan_settings.access_exam_prep`, satisfied by the new standalone **Exam Prep Center** plan (₹1,999/year, all 6 exams) or an admin/test-user override — no more per-exam partial access. See `03_SUBSCRIPTIONS.md`'s 2026-08-26 section and `FEATURE_MATRIX.md` for the user-facing description. A stale test comment referencing the deleted `check_exam_content_access_with_packs()` remains in `backend/tests/test_exam_prep.py:177` — cosmetic, worth a line-fix whenever this lands.

---

### TD-07: No rate limiting on any endpoint
**Resolved:** 2026-08-26, mostly — one residual gap tracked separately

`backend/requirements.txt` had no rate-limiting library; login, signup, and the username→email lookup endpoint (`/api/auth/lookup-email/{username}`) were open to brute-force/enumeration at unlimited request rates.

**What changed:** `backend/app/services/rate_limit_service.py`'s `RateLimiter` — Redis sliding-window via an atomic Lua script, automatic in-memory fallback if Redis is absent — now covers `POST /api/auth/login` (10/60s), `GET /api/auth/lookup-email/{username}` (8/60s, the exact endpoint originally named), `POST /api/auth/forgot-password` (3/300s), all four signup endpoints (5/60s each), and payment create/verify (dedicated limiters). Full detail and coverage table now live in `10_SECURITY.md`'s "Rate Limiting" section rather than here.

**Not covered — see TD-13:** `POST /api/auth/complete-signup` has no rate limiter and is reachable pre-payment-verification. Opened as its own item since it's a distinct endpoint with a distinct fix, not because TD-07's original scope is still open.

**Also noted, not blocking closure:** `chatbot.py` has a separate in-memory-only limiter, not on the shared Redis path — low severity (public FAQ bot), left as a minor inconsistency rather than its own tracked item.

---

### TD-06: Mobile duplicates web's subscription/access logic instead of importing it
**Resolved:** 2026-08-26

The hand-rolled `const isGradeLocked = studentGrade !== null && !hasFullAccess;` line was copy-pasted identically across 5 mobile screens (`formula.tsx`, `doubt.tsx`, `learn.tsx`, `mocktest.tsx`, `lessons.tsx`), with nothing enforcing the copies stayed in sync.

**What changed:** added `isGradeLocked(studentGrade, hasFullAccess)` to `shared/utils/resolveSubscription.js` — the module TD-06 itself pointed at as the intended single source of truth — and updated all 5 mobile screens to import and call it instead of re-deriving the expression locally. Each call site's local variable was renamed `gradeLocked` (the imported function keeps the name `isGradeLocked`) to avoid shadowing; verified with a full grep sweep per file that every downstream reference (JSX conditionals, the `GradeLabelRow` prop in `formula.tsx`, the per-grade-chip `locked` check in all 5) was updated consistently, not just the derivation line. `mobile/` has no type-check or lint script in `package.json` to run as a final gate (consistent with the zero-test-coverage gap noted in `12_TESTING.md`) — verified by manual reference-by-reference review instead.

---

### TD-14: Exam Prep admin visibility toggle is wired up but never read
**Resolved:** 2026-08-26

`backend/app/data/product_catalogue.py`'s `coaching_programs` visibility flag (JEE/NEET/CUET, all hardcoded `visible: False`, no entries for SAT/IELTS/TOEFL at all) was saved by the admin toggle but never read by `exam_prep.py`'s `/status` endpoint, which hardcoded every exam `active: True` unconditionally.

**What changed, and a second live bug found while fixing the first:**
1. Rewrote `coaching_programs` to the current 6-exam key set (`jee_main`/`neet_ug`/`cuet_ug`/`sat`/`ielts`/`toefl_ibt`, matching `exam_prep_service.EXAM_SUBJECTS_MAP` exactly), all `visible: True` — matching today's actual live state, so this alone is a zero-behavior-change data correction.
2. Added `get_live_visible_coaching_programs()` to `product_catalogue_service.py` (mirrors the existing `get_live_visible_grades()`), and wired `exam_prep.py`'s `/status` to compute each exam's `active` flag from it instead of a hardcoded `True`.
3. **Before trusting that wiring, checked what was actually in the connected Supabase's `admin_settings` row for `product_catalogue` — and it still had the *old* schema**: `coaching_programs` keyed `"JEE"`/`"NEET"`/`"CUET"` (all `visible: false`, no `sat`/`ielts`/`toefl_ibt` keys at all), saved before this 2026-08-26 rename. Shipping step 2 against that row as-is would have made `get_live_visible_coaching_programs()` return an empty set — i.e. every exam would have gone `active: false` in production the moment this deployed, and separately, the admin's own catalogue page (which reads the same row) would have kept showing the 3 dead keys, where toggling any of them still would have done nothing — TD-14 reappearing one layer up, via stale data instead of missing code.
4. Fixed at the root instead of patching around it: `load_product_catalogue()` now merges a stored row onto the current hardcoded defaults, key by key, per section — a canonical key **present** in the stored row keeps its stored value (a real admin choice, honored); a canonical key **absent** from the stored row (this exact case) falls back to the current default instead of vanishing; a stored key that isn't in the canonical set anymore (the old `"JEE"`/`"NEET"`/`"CUET"`) is dropped as orphaned. This is symmetric for both `grades` and `coaching_programs`, doesn't require a live DB write/migration to fix, and self-corrects the stored row for good the next time an admin saves anything on the catalogue page.
5. Verified: `GET /api/product-catalogue` (admin-facing) and `GET /api/exam-prep/status` (student-facing) now agree — both show all 6 exams, correctly keyed, all active, against the real (still-stale) DB row. Confirmed via the real `.venv` interpreter, not just static review. Added `backend/tests/test_product_catalogue_service.py` (4 tests: no-row default, stale-row healing reproducing the exact live row found, an explicit `visible:false` on a *current* key still being honored, and the `grades` section passing through untouched) plus 2 new tests in `test_exam_prep.py` covering `/status`'s default-all-active case and an admin-hidden-exam case. Full backend suite (2,527 tests) passed after the change.

**Also fixed on the same page, same session (not separately tracked):** `frontend/src/pages/AdminProductCataloguePage.jsx`'s Section B copy and "Feature Readiness Roadmap" both described Exam Prep as pre-launch ("hidden until dedicated subject content is uploaded and the coaching-mode UI is built" / "Phase 3, Content + UI needed") — directly contradicted by the fix above and by everything else this platform has shipped for Exam Prep since. Updated to reflect that all 6 exams are live; left the adjacent Grade 11/12 roadmap lines alone (separate claim, not verified this pass).

---

### TD-15: Duplicate hidden `premium` plan key alongside `starter`
**Resolved:** 2026-08-26 — not vestigial, was under-investigated; closed via documentation, not deletion

Re-investigated before touching anything, since this item explicitly said "confirm before deleting." Found `"premium"` is live, referenced code: `subscription_resolver_service._canonical_plan_key()` (and its JS mirror, `shared/utils/resolveSubscription.js`'s `_canonicalPlanKey()`) map both `"starter"` and `"premium"` to the same canonical `PREMIUM` tier — the identical pattern already used and already documented for `"free"` meaning legacy Nano. Two tests (`Grade1112Access.test.jsx`, `FormulaSheetRevamp.test.jsx`) exercise `subscriptionPlan: "premium"` directly. `shared/config/subscriptionPlans.js` already carried a (terse) comment — "Hidden alias kept for backwards-compatibility with admin flows" — that TD-15's original investigation apparently didn't find or didn't find convincing enough to close the question.

**What changed:** no code deleted. Added a clear explanation at all four locations that reference this key (`backend/app/data/subscription_plans.py`'s `"premium"` entry, `subscription_resolver_service._canonical_plan_key()`'s docstring, `shared/config/subscriptionPlans.js`'s `premium` entry, `shared/utils/resolveSubscription.js`'s `_canonicalPlanKey()`) so a future pass doesn't re-open this as "purpose unconfirmed" and delete something load-bearing. Genuinely unresolved and stated as such in the new comments: whether any live profile row still carries `subscription_plan="premium"` isn't verifiable from this repo — the mapping stays either way, since keeping a legacy-key normalization branch that turns out to be unused costs nothing, while deleting one that turns out to still be needed breaks plan resolution for whoever hits it.
