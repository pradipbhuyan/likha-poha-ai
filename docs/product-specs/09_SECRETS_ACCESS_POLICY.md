# Secrets & Access Policy — Likha Poha AI

_Written 2026-07-19. Companion to `07_ARCHITECTURE_ASSESSMENT.md` §3.9 ("No secrets rotation or access-scoping story documented"). This is a lightweight inventory + policy recommendation, not an audit of actual current access — the "who has access today" columns are placeholders for you to fill in, since that's account-level information not visible from the codebase._

---

## 1. Where secrets actually live

Confirmed from the codebase (not assumed):

- **Backend runtime secrets**: Railway dashboard and/or Render dashboard environment variables — `.github/workflows/cd.yml` deploys to both in parallel (Render primary via `RENDER_BACKEND_DEPLOY_HOOK_URL`, Railway as a secondary/migration target via `RAILWAY_BACKEND_DEPLOY_HOOK_URL`). Neither platform's env vars are version-controlled; `backend/.env.example` is the only in-repo record of what's expected, and it contains no real values.
- **CI/CD secrets**: GitHub Actions repo secrets (`Settings → Secrets and variables → Actions`), referenced in `.github/workflows/cd.yml` and `ci.yml`.
- **Frontend build-time vars**: Vercel (or wherever `frontend/` deploys) environment variables, `VITE_*` prefix — these are bundled into the client JS at build time, so treat anything with this prefix as **public**, never a secret, by construction.
- **Mobile build-time vars**: `EXPO_PUBLIC_*` prefix — same rule, bundled into the app binary, public by construction. `mobile/.env.example` already documents this correctly ("EXPO_PUBLIC_* variables are safe to bundle — never put secrets here").

## 2. Secret inventory, by blast radius

**Critical** — full account/data compromise if leaked. Rotate immediately on any suspected exposure or team-access change; review at least quarterly.

| Secret | What it unlocks | Where it's read |
|---|---|---|
| `SUPABASE_SERVICE_ROLE_KEY` / `SUPABASE_SERVICE_KEY` | Bypasses RLS entirely on the primary Supabase project — full read/write on every table, including all user/auth data | `auth_service.py` (`admin_client`) |
| `SUPABASE_GRADE_1112_SERVICE_KEY` | Same, for the second Supabase project (Grade 11/12 content) | `supabase_grade_1112_client.py` |
| `ADMIN_PASSWORD`, `PRADIP_PASSWORD`, `AKSHITA_PASSWORD` | Direct login credentials for named privileged accounts | `auth_service.py` / seed scripts |
| `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET` | Payment verification + webhook signature — leak enables forged "payment succeeded" webhooks | `payments.py` |
| `R2_SECRET_ACCESS_KEY` | Write access to the lesson-audio object storage bucket | audio generation/storage service |
| `RENDER_API_KEY` | Full Render account API access (used in CD workflow) | `.github/workflows/cd.yml` |
| `GITHUB_TOKEN` (if a custom PAT, not the auto-provided Actions token) | Repo access at whatever scope the token was granted | `.github/workflows/security.yml` |

**High** — cost-abuse or spoofing risk, not direct data compromise. Rotate on team-access change; review semi-annually.

| Secret | Risk if leaked |
|---|---|
| `OPENAI_API_KEY`, `VENICE_API_KEY`, `GROQ_API_KEY`, `CEREBRAS_API_KEY`, `NVIDIA_API_KEY`, `SAMBANOVA_API_KEY`, `OLLAMA_CLOUD_API_KEY` | Someone else runs LLM usage on your account/bill |
| `RESEND_API_KEY` | Spam/phishing sent from your verified domain |
| `ALERT_SMTP_PASSWORD` | Gmail App Password — sends mail as your alert account |
| `RAILWAY_BACKEND_DEPLOY_HOOK_URL`, `RENDER_BACKEND_DEPLOY_HOOK_URL`, `RENDER_FRONTEND_DEPLOY_HOOK_URL` | Triggers a deploy — abuse is a nuisance/DoS vector more than data risk, but a hook URL alone can't push arbitrary code (it just re-deploys `main`) |

**Medium / low** — limited or by-design-public blast radius.

| Secret | Note |
|---|---|
| `SUPABASE_KEY` / `SUPABASE_ANON_KEY` | Anon/publishable key — RLS-protected by design, already exposed to the frontend client |
| `RAZORPAY_KEY_ID` | Publishable ID, not the secret half |
| `MARKETING_*_PASSWORD` | Already isolated per `.env.example`'s own note ("isolated from production users, email prefix: marketing.") |
| `SENTRY_DSN` | Conventionally semi-public (write-only ingestion endpoint) |
| `SLACK_WEBHOOK_URL` | Spam risk only |

## 3. Recommended policy

This is a recommendation to adopt or adjust, not a description of current practice:

1. **Rotate on team-access change.** Any time someone who had dashboard/repo access leaves or changes role, rotate every Critical secret they could have viewed, at minimum.
2. **Fill in an access roster.** For each of Railway, Render, Supabase (both projects), GitHub repo secrets, and Razorpay — record who currently has access. This table doesn't exist yet; the first pass is just writing down who already has access today, before deciding whether that's the right list.
3. **Never widen `SUPABASE_SERVICE_ROLE_KEY` exposure.** It's already correctly backend-only (confirmed: no `SUPABASE_SERVICE_ROLE_KEY` reference in `frontend/` or `mobile/`). Keep it that way — any future feature needing elevated DB access from a client should go through a backend endpoint, not a relaxed RLS policy plus a leaked key.
4. **Quarterly review for Critical, semi-annual for High.** A calendar reminder is enough at this scale — this doesn't need tooling.
5. **`.env.example` is doing real work already** — it documents purpose and source for every variable and flags the dangerous ones inline ("NEVER expose this value publicly"). Keep maintaining it as the source of truth for *what* exists; this doc is for *who can see it and how often it turns over*, which `.env.example` can't capture.

## 4. What this doc deliberately does not do

Per the original assessment's own framing ("worth a lightweight audit, not a rebuild"): this is not a secrets-manager migration, not a proposal to move off dashboard-based env vars, and not an IAM overhaul. At current team size, the fix is a written policy someone actually follows — not new infrastructure.
