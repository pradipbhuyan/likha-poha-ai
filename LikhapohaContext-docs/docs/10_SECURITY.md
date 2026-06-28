# Security

_Last updated: 2026-06-28_

## Authentication

### Supabase Auth
- Email/password login: `username → profiles.email → signInWithPassword`
- Google OAuth: `supabase.auth.signInWithOAuth({ provider: "google" })`
- PKCE flow (default in Supabase v2): `?code=` returned in redirect URL

### Google OAuth — Critical Rules

**Race condition prevention:**
- Session recovery `useEffect` MUST skip when `?code=` or `#access_token=` is in URL
- Both would call `getSession()` + `refreshSession()` concurrently → second refresh invalidates first
- Guard: `if (savedUser && !_isOAuthReturn) { /* session recovery */ }`

**isOAuthRedirect check order:**
- Check `isOAuthRedirect` FIRST in `onAuthStateChange` before `localStorage.getItem("tutor_user")`
- User with existing session clicking Google → found localStorage → returned early (WRONG)
- Fix: localStorage shortcut only for non-OAuth page reloads

**Identity age fallback:**
- Supabase PKCE exchanges `?code=` in `getSession()` and cleans URL
- By the time `onAuthStateChange` fires, `window.location.search` has no `code=`
- Fallback: if `session.user.identities[0].created_at < 5 minutes`, treat as fresh OAuth

**authFetch post-OAuth retry:**
- After `handleLogin()`, pages call `authFetch()` immediately
- `getSession()` may return null in the 0-800ms window after OAuth exchange
- Fix: 3-step retrieval — `getSession()` → `refreshSession()` → wait 800ms + retry

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
