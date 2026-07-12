# Development Guide

_Last updated: 2026-07-12_

## General Rules

- Keep business logic in backend services.
- Keep frontend components focused and modular.
- Use API clients consistently; know whether helpers return parsed JSON.
- Do not enlarge monolithic pages; extract components.
- Prefer clear product terminology.

## API Rules

- Use structured JSON responses.
- Use 403 for authorization failure.
- Use 429 for rate limits.
- Return safe error messages.
- Do not expose raw Supabase/PostgREST errors to UI.
- Add pagination/date filters for large data.

## UI Rules

- Mobile-first.
- Touch-friendly buttons.
- Responsive cards.
- Horizontal table scroll only when card conversion is impractical.
- Friendly empty/loading/error states.
- Accessible labels and roles.

## Documentation Rules

Update docs when changing:

- subscription rules
- feature access
- roles/permissions
- API contracts
- admin/teacher/parent/student workflows
- security posture
- roadmap commitments

## Local Development — Shell Shortcuts

After cloning, add these shortcuts to `~/.zshrc` so you can start the dev server from **any directory**:

```bash
# ── Likhapoha AI dev shortcuts ────────────────────────────────────────────────
export LIKHAPOHA="$HOME/Pradips_Project/cbse-tutor-platform"

# Start backend only (kills existing process on :8000 first)
lp-backend() {
  kill $(lsof -ti :8000) 2>/dev/null; sleep 0.5
  echo "🚀 Starting backend on :8000..."
  cd "$LIKHAPOHA/backend" && .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
}

# Start frontend only
lp-frontend() {
  echo "🎨 Starting frontend on :5173..."
  cd "$LIKHAPOHA/frontend" && npm run dev
}

# Start both — backend in background, frontend in foreground
# Ctrl+C stops frontend and automatically kills backend too
lp-dev() {
  kill $(lsof -ti :8000) 2>/dev/null; sleep 0.3
  echo "🚀 Starting backend + frontend..."
  cd "$LIKHAPOHA/backend" && .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > /tmp/lp-backend.log 2>&1 &
  LP_BACKEND_PID=$!
  echo "  Backend PID: $LP_BACKEND_PID  (logs: tail -f /tmp/lp-backend.log)"
  cd "$LIKHAPOHA/frontend" && npm run dev
  kill $LP_BACKEND_PID 2>/dev/null
}

# Kill everything on port 8000 + 5173
lp-stop() {
  kill $(lsof -ti :8000 :5173) 2>/dev/null
  echo "✅ Stopped backend (8000) and frontend (5173)"
}

# Follow backend logs (when running lp-dev)
lp-logs() {
  tail -f /tmp/lp-backend.log
}
```

After editing `~/.zshrc`, activate with:
```bash
source ~/.zshrc
```

### Command reference

| Command | What it does |
|---|---|
| `lp-dev` | Starts **both** backend + frontend. Ctrl+C stops both. |
| `lp-backend` | Backend only on `:8000` (hot-reload) |
| `lp-frontend` | Frontend only on `:5173` |
| `lp-stop` | Kill both servers |
| `lp-logs` | `tail -f` backend log (when running `lp-dev`) |

All commands work from **any directory** — they use the absolute `$LIKHAPOHA` path internally.

### Typical daily workflow

```bash
lp-dev          # start both servers

# In a second terminal tab:
lp-logs         # watch backend output

# When done:
lp-stop
```

### Kill and restart backend manually

```bash
kill $(lsof -ti :8000)   # kill old process
# wait 1 second, then:
lp-backend               # start fresh
```

---

## Codex Prompt Pattern

```text
Read docs/CODEX_BOOTSTRAP.md and referenced documents.
Implement <task>.
Do not violate product rules.
Add regression tests.
Update docs if behavior changes.
```
