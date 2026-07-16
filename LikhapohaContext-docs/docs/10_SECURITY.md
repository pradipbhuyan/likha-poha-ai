# Security

_Last updated: 2026-07-16_

## Authentication

### Supabase Auth
- Email/password login: `username → profiles.email → signInWithPassword`
- Google OAuth: `supabase.auth.signInWithOAuth({ provider: "google" })`
- PKCE flow (default in Supabase v2): `?code=` returned in redirect URL

### Google OAuth

Flow differs by platform because of how each Supabase client is configured —
this is intentional, don't try to make them consistent.

| Platform | Flow     | Why |
|----------|----------|-----|
| Web      | PKCE     | Default Supabase v2 browser client behavior. `?code=` in the redirect URL, exchanged via `exchangeCodeForSession`. |
| Mobile   | Implicit | Tokens arrive in the redirect URL **hash** (`#access_token=...`), not a `?code=`. Calling `exchangeCodeForSession` on this fails with *"both auth code and code verifier should be non-empty"* — never use it as the primary path on mobile. |

#### Web: `frontend/src/App.jsx`

Reliability rule — the only heuristic in use, everything else was tried and removed (see Retired, below):

```js
const hasAppProfile = !!localStorage.getItem("tutor_user");
// SIGNED_IN + no app profile → always process as a fresh login, on any device
```

Explicit PKCE exchange happens before `onAuthStateChange` fires (not left to the listener alone):
`supabase.auth.exchangeCodeForSession(window.location.href)` on mount, with bounded session retry.

Backend state machine (`backend/app/routes/auth.py` — `GET /me`, `POST /oauth/complete-profile`):

| State | Condition | Frontend action |
|-------|-----------|------------------|
| A | `profile_complete=true` | Route to dashboard immediately |
| B | `needs_role_selection=true` (new user) | Show one-time role picker |
| C | `needs_role_selection=true` (no profile yet) | Show one-time role picker |
| D | `409 role_conflict` from `complete-profile` | Friendly error, block |

`oauth_profile_complete` (DB column, default `TRUE`) is the authoritative signal for this table — not identity age, not URL params.

#### Mobile: `mobile/app/auth/login.tsx` — `handleOAuthSuccess()`

Detects which flow actually arrived in the callback URL and branches:
- `#access_token=` present → implicit flow → `supabase.auth.setSession({ access_token, refresh_token })`
- `?code=` present, no hash tokens → PKCE flow (not the normal path here, but handled) → `supabase.auth.exchangeCodeForSession(callbackUrl)`

Known fragile points on mobile, each with a specific fix already in place — check these first if OAuth breaks again, in this order:

1. **Secure storage fails silently on an emulator without a lock screen.** Android Keystore requires a secure lock screen for `expo-secure-store`; without one, `setItemAsync` fails silently and the PKCE `code_verifier` (or session) is lost. Fixed by `RobustStorageAdapter` in `mobile/lib/supabase.ts` — writes to an in-memory `Map` first, then best-effort to `SecureStore`; reads try `SecureStore` first, fall back to the `Map`.
2. **Spurious `SIGNED_OUT` on session replacement.** Supabase fires `SIGNED_OUT` then `SIGNED_IN` when a new OAuth session replaces an old one — without a guard this routes the user back to login mid-flow. Fixed by the `wasAuthenticated` ref in `mobile/app/_layout.tsx`: once `authState` has reached `ready` or `needs_role`, a later `unauthenticated` state is never treated as a real logout (only an explicit `signOut()` resets it).
3. **Double token exchange.** Both `onNavigationStateChange` and `onShouldStartLoadWithRequest` can fire for the same redirect and both try to exchange it. Fixed by the `oauthExchangeInProgress` ref guard in `handleOAuthSuccess`.
4. **Post-OAuth routing timing.** Do NOT rely on `_layout.tsx`'s `onAuthStateChange` listener to route after login — `handleOAuthSuccess` calls `checkAuthState(session.access_token)` directly and routes explicitly (`needs_role_selection=true` → `/auth/role-select`, else → `/(tabs)`). Relying on the listener causes timing-conflict misroutes.
5. **Repeat sign-in auto-logs-in the cached Google account.** Fixed by `queryParams: { prompt: "select_account" }` on `signInWithOAuth` in `mobile/lib/auth.ts`, forcing the account picker every time.

#### Retired — do not reimplement

- ~~Identity age fallback~~ (`session.user.identities[0].created_at < 5min`) — unreliable, removed 2026-06-29.
- ~~URL param detection~~ (checking for `?code=` presence in `onAuthStateChange`) — Supabase clears the URL before the handler runs, so this never worked reliably.

### Child Accounts
- Children log in with username (display name) as login ID
- Synthetic email: `{username}@child.likhapoha.in`
- `email_confirm=True` so child can login immediately
- `login_id` + `login_email` returned to parent in `create_student` response
- Temporary password shown once in credentials panel — never stored in profile

### Session Management
- Session recovery on boot: verify → refresh → fetch fresh profile
- Expired Supabase session → clear localStorage → redirect to login
- `handleLogin` fetches fresh `/api/auth/profile` for ALL roles

## Authorization

### Role-Based Access
| Role | Access |
|---|---|
| `admin` | Full platform + Platform QA Center |
| `teacher` | Own students only |
| `parent` | Own linked children only |
| `student` | Own data only |

### Critical Rules

1. **`parentId` alone NEVER implies paid access** — only `access_cbse=true`
2. **Feature access from `get_feature_summary(user_id)` only** — never raw `subscription_plan`
3. **Child ownership** — `_verify_child_ownership(parent_id, child_id)` on all parent endpoints
4. **Admin-only QA endpoints** — all `/api/admin/qa/*` require `require_admin`
5. **Teacher-private notes NEVER exposed to parents**
6. **Admin audit metadata NEVER exposed to parents/students**

### Formula Sheet Access
- Formula Sheet page: open to all authenticated users
- Formula expansion (examples, memory tips, MCQs): `FORMULA_SHEET_PREMIUM` required
- Free Tier: preview only (first 3 formulas per chapter, name + expression + description)

### Feature Authorization Audit
- `scripts/audit_feature_authorization.py` — verifies 42+ scenarios
- Catches: Free Tier premium leakage, expired plan fallback, parentId-only access
- All checks must pass before release

## Error Messages

### User-Facing (Friendly)
- Session expired / no token → "Your session has expired. Please sign in again."
- Session read error → "Your session could not be read. Please sign in again."
- 401/403 → "Your session has expired. Please sign in again."
- 500 → "We're having trouble right now. Please try again in a moment."
- Business errors (400) without auth keywords → shown as-is

### Hidden from Users (Console Only)
- Raw JWT details
- Supabase internals (RLS, policy names)
- Bearer tokens
- Raw server error details for 500s

## Score Normalization

`_normalize_score_pct(percentage, raw_score, max_score)`:
- `percentage` in [0,100] → use directly
- `percentage` > 100 → invalid, fallback to `raw/max*100`
- `max_score = 0` → return None
- No data → return None → UI shows "Score not available"
- **Never multiply `percentage` by 100 again**

## QA Center Security

All `/api/admin/qa/*` endpoints:
- `require_admin` dependency on every endpoint
- No secrets, API keys, or student PII in report responses
- Background audit errors sanitized to 500 chars, newlines removed
- LLM API key only used in background thread, never returned to frontend
- Report files never include SUPABASE_SERVICE_ROLE_KEY or OPENAI_API_KEY

---

## Exemplar Lesson Access Control — 2026-06-30

### Rule
Exemplar chapters are premium-only. Free-tier students cannot generate lessons for any chapter containing "Exemplar:".

### Implementation
**Backend (`lesson.py`):**
```python
if "exemplar:" in _chapter_name.lower():
    # authorize Feature.EXEMPLAR — raises 403 for free users
```
Admins, teachers, all-access test accounts are exempt.

**Frontend (`LessonsPage.jsx`):**
```js
const isExemplarChapter = chapter?.includes("Exemplar:");
const isExemplarLocked = isExemplarChapter && !hasPaidAccessForLessons;
```
When locked: 🔐 notice shown, Generate button disabled.

### Important: Chapter Name Format
The syllabus route may add "Part N - " prefix (e.g. "Part 1 - Exemplar: Rational Numbers"). Always use `includes("Exemplar:")`, never `startsWith("Exemplar:")`.

Backend `syllabus.py` `create_part_display_label()` is configured to skip "Part N - " for exemplar chapters, so after server restart chapters will show as clean "Exemplar: Name". But the `includes()` check ensures safety before restart too.
