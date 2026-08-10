# LikhaPoha AI — CI/CD Setup Guide

## Overview

The pipeline has 3 workflows:

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `ci.yml` | Push/PR to `main` | Lint → Test → Build |
| `cd.yml` | CI passes on `main` | Deploy → Smoke test → Notify |
| `security.yml` | Push to `main` + Weekly | Dependency audit + secret scan |

## Pipeline Flow

```
Push to main
     │
     ▼
┌─────────────────────────────────┐
│  CI Workflow                    │
│  ├─ 🐍 Backend Lint (Ruff)      │
│  ├─ 🐍 Backend Tests (pytest)   │
│  ├─ ⚛️ Frontend Lint (ESLint)   │
│  ├─ ⚛️ Frontend Tests (Vitest)  │
│  └─ ⚛️ Frontend Build (Vite)    │
└────────────────┬────────────────┘
                 │ All pass
                 ▼
┌─────────────────────────────────┐
│  CD Workflow                    │
│  ├─ 🚀 Trigger Render deploy    │
│  ├─ ⏳ Wait for health check    │
│  ├─ 🔍 Smoke tests              │
│  └─ 📣 Slack notification       │
└─────────────────────────────────┘
```

---

## Step 1 — Add GitHub Secrets

Go to: **GitHub repo → Settings → Secrets and variables → Actions → New repository secret**

### Required secrets for CD:

| Secret Name | Where to get it |
|-------------|----------------|
| `RENDER_BACKEND_DEPLOY_HOOK_URL` | Render → Backend service → Settings → Deploy Hook → Copy URL |
| `RENDER_FRONTEND_DEPLOY_HOOK_URL` | Render → Frontend service → Settings → Deploy Hook → Copy URL |
| `RENDER_API_KEY` | Render → Account Settings → API Keys → Create API Key |
| `PRODUCTION_URL` | `https://likhapoha.in` |

### Optional secrets:

| Secret Name | Purpose |
|-------------|---------|
| `SLACK_WEBHOOK_URL` | Get from Slack → Apps → Incoming Webhooks → Add to workspace |

---

## Step 2 — Enable Branch Protection (IMPORTANT)

Go to: **GitHub repo → Settings → Branches → Add rule → `main`**

Enable these:
- ✅ **Require a pull request before merging**
- ✅ **Require status checks to pass before merging**
  - Add: `✅ CI Passed` (the summary job in ci.yml)
- ✅ **Require branches to be up to date before merging**
- ✅ **Do not allow bypassing the above settings**

This ensures **no code reaches production without passing all CI gates**.

---

## Step 3 — Get Render Deploy Hooks

1. Log in to [render.com](https://render.com)
2. Open your **backend service** → Settings → scroll to **Deploy Hook**
3. Copy the URL → paste as `RENDER_BACKEND_DEPLOY_HOOK_URL` in GitHub Secrets
4. Repeat for frontend service → `RENDER_FRONTEND_DEPLOY_HOOK_URL`

**Note:** If you use Vercel for the frontend, the CD workflow skips the frontend Render hook automatically. Vercel auto-deploys on push to `main` by default.

---

## Step 4 — Disable Render Auto-Deploy (Optional but Recommended)

Once the CD pipeline is live, you want **GitHub Actions to control deploys**, not Render's auto-deploy. Otherwise every push triggers 2 deploys.

Render → Service → Settings → **Auto-Deploy** → Set to **No**

The CD workflow will call the deploy hook explicitly after CI passes.

---

## Workflow Details

### `ci.yml`

**Jobs (in order):**
1. `backend-lint` — Ruff linting (E,F,W rules)
2. `backend-tests` — pytest with coverage report (uploaded as artefact)
3. `frontend-lint` — ESLint (max 50 warnings)
4. `frontend-tests` — Vitest unit tests
5. `frontend-build` — `npm run build` (catches broken imports/types)
6. `ci-passed` — summary gate (required for branch protection)

**Artefacts saved:**
- `backend-coverage` — coverage.xml (7 day retention)
- `frontend-dist` — production build (7 day retention)

### `cd.yml`

**Triggered by:** `CI` workflow completing successfully on `main`

**Jobs:**
1. `deploy` — triggers Render deploy hooks via API, then polls `/api/health` for up to 5 minutes
2. `smoke-test` — verifies `/api/health`, `/api/syllabus/grades`, and the landing page
3. `notify` — sends Slack message on success or failure

### `security.yml`

**Triggered by:** push to `main` + every Monday 02:00 UTC

**Jobs:**
1. `python-deps` — `pip-audit` checks for CVEs in Python packages
2. `node-deps` — `npm audit` checks for high/critical Node vulnerabilities
3. `secrets-scan` — Gitleaks scans full git history for leaked secrets

---

## Current Maturity Score: 9/10 ✅

| Area | Before | After |
|------|--------|-------|
| Tests run on PR | ✅ | ✅ |
| Lint blocking | ❌ | ✅ |
| Build verification | ❌ | ✅ |
| Automated deployment | ❌ | ✅ |
| Health check after deploy | ❌ | ✅ |
| Smoke tests post-deploy | ❌ | ✅ |
| Deploy notifications | ❌ | ✅ |
| Security scanning | ❌ | ✅ |
| PR template | ❌ | ✅ |
| Branch protection | ❌ | 🔧 Manual setup needed |

---

## Next Steps (to reach 10/10)

1. **Playwright E2E in CI** — add login + lesson flow test to `ci.yml`
2. **Coverage threshold** — raise `--cov-fail-under=0` to `30` then `60` over time
3. **Staging environment** — add a `staging` branch that deploys to a staging Render service
4. **Dependabot** — auto-create PRs for dependency updates
