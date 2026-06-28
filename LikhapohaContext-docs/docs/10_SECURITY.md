# Security

_Last updated: 2026-06-28_

## Authentication

### Supabase Auth
- Email/password login with lookup-email flow: `username → profiles.email → signInWithPassword`
- Google OAuth supported — full OAuth processing only runs on actual redirect URLs (not page reload with existing session)
- `email_confirm=True` (default) for admin-created accounts — immediately active
- Parent-invited parents use `invite_user_by_email` for email verification

### Child Accounts
- Children log in with their display name (username) as login ID
- Synthetic email generated: `{username}@child.likhapoha.in` if no real email provided
- `email_confirm=True` so child can log in immediately after parent creates account
- `login_id` and `login_email` returned to parent in `create_student` response
- Temporary password shown once in credentials panel — never stored in profile

### Session Management
- Session recovery on app boot: verify Supabase session → refresh token → fetch fresh profile
- Expired Supabase session → clear localStorage → redirect to login
- `handleLogin` fetches fresh `/api/auth/profile` for ALL roles
- Technical auth errors logged to console only — never shown to users

## Authorization

### Role-Based Access
| Role | Access |
|---|---|
| `admin` | Full platform access |
| `teacher` | Own students only |
| `parent` | Own linked children only |
| `student` | Own data only |

### Critical Rules

1. **`parentId` alone NEVER implies paid access** — only `access_cbse=true` grants paid features
2. **Feature access from canonical service only** — `get_feature_summary(user_id)`, never from raw `subscription_plan`
3. **Child owned by parent** — all parent endpoints verify `parent_id` match via `_verify_child_ownership()`
4. **Student owns own data** — `require_student` dependency enforces this
5. **Teacher-private notes NEVER exposed to parents** — never included in parent endpoints
6. **Admin audit metadata NEVER exposed to parents/students** — `platform_audit_logs` is admin-only

### Free Tier Restrictions
- `access_cbse=false` → Free Tier
- Exemplar: Locked
- Mock Tests: Limited (5/day)
- Ask Doubts: Limited
- Unlimited mock tests: Locked
- All new signups start with `access_cbse=false`
- Expired paid plans fall back to Free Tier restrictions

## Error Messages

### User-Facing (Friendly)
- Session expired: "Your session has expired. Please sign in again."
- No token: "Your session has expired. Please sign in again."
- Session read error: "Your session could not be read. Please sign in again."
- 401/403 API: "Your session has expired. Please sign in again."
- 500 API: "We're having trouble right now. Please try again in a moment."
- Safe business error (400): shown as-is if no Supabase/JWT keywords

### Hidden from Users (Console Only)
- Raw JWT details
- Supabase internals (RLS, policy names)
- Bearer tokens
- Raw server error details for 500s
- Any error containing "supabase", "token", "JWT", "bearer"

## Data Exposure Rules

### Never Expose
- Teacher-private notes
- Admin audit logs (`platform_audit_logs`)
- Raw Supabase session tokens in responses
- Other users' data
- Admin override details in user-facing UI

### Safe to Expose
- User's own profile fields
- Canonical subscription status (plan_name, has_full_access, status_label)
- Feature access summary (locked/limited/full per feature)
- Mock test percentages (0-100 only, via `_normalize_score_pct`)

## Score Normalization

`_normalize_score_pct(percentage, raw_score, max_score)` in `parent_dashboard_v2.py`:
- `percentage` in [0,100] → use directly
- `percentage` > 100 → invalid, try `raw_score / max_score * 100`
- `max_score = 0` → return None (no division by zero)
- No valid data → return None → UI shows "Score not available"
- **Never multiply `percentage` by 100 again**

## Notification Metadata Sanitization

`parent_notifications.metadata` — stripped of dangerous keys on read:
- `token`, `secret`, `key`, `password`, `audit_detail` removed
- Safe metadata keys preserved
