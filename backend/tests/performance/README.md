# Likha Poha AI Performance Tests

These Locust scripts provide the first safe load-test baseline for the FastAPI backend.

## What This Tests

- `StudentBrowsingUser`: health, syllabus, resources, leaderboard, progress reads, and progress saves.
- `StudentMixedUser`: realistic browsing plus optional AI lesson and doubt calls.
- `StudentAIHeavyUser`: expensive lesson, Ask Doubt, and mock-test generation.

AI calls are guarded by `ENABLE_AI_TASKS=true` so a smoke test does not accidentally consume OpenAI quota.

## Setup

From the `backend` directory:

```bash
python3 -m pip install locust
```

Recommended: configure a backend-only test student login in `backend/.env` so
each run gets a fresh Supabase access token:

```bash
PERFORMANCE_TEST_EMAIL=akshita.teststudent@example.com
PERFORMANCE_TEST_PASSWORD=...
PERFORMANCE_TEST_USERNAME=akshita.teststudent
PERFORMANCE_TEST_GRADE=Grade 9
PERFORMANCE_TEST_BOARD=CBSE
PERFORMANCE_TEST_MODE=CBSE
PERFORMANCE_TEST_SUBJECT=Science
PERFORMANCE_TEST_CHAPTER=Atoms and Molecules
```

Keep this in backend env only. Do not expose it in the frontend.

Alternative: use a static local token file.

Create a local test users file from the example:

```bash
cp tests/performance/test_users.example.json tests/performance/test_users.json
```

Edit `tests/performance/test_users.json` and paste Supabase access tokens for real test student accounts.

Do not commit `test_users.json`.

## Smoke Test: Local Backend, No AI Cost

Start the backend in another terminal:

```bash
python3 -m uvicorn app.main:app --reload
```

Run a cheap baseline:

```bash
locust -f tests/performance/locustfile.py --host http://localhost:8000
```

Open:

```text
http://localhost:8089
```

Start with:

- Users: `5`
- Spawn rate: `1`
- User classes: `StudentBrowsingUser`

## Recommended First Runs

### 1. Browsing Baseline

No OpenAI cost.

```bash
locust -f tests/performance/locustfile.py --host http://localhost:8000 StudentBrowsingUser
```

Try:

- 5 users for smoke
- 25 users
- 50 users
- 100 users

### 2. Mixed Student Journey

AI stays disabled unless you opt in.

```bash
locust -f tests/performance/locustfile.py --host http://localhost:8000 StudentMixedUser
```

To include AI calls:

```bash
ENABLE_AI_TASKS=true locust -f tests/performance/locustfile.py --host http://localhost:8000 StudentMixedUser
```

Try:

- 5 users first
- 10 users
- 25 users
- 50 users

### 3. AI-Heavy Spike

This spends OpenAI quota. Use only with test accounts and a clear budget.

```bash
ENABLE_AI_TASKS=true locust -f tests/performance/locustfile.py --host http://localhost:8000 StudentAIHeavyUser
```

Try:

- 2 users
- 5 users
- 10 users
- 25 users only after the earlier runs are stable

## Success Targets

| Area | First target |
| --- | ---: |
| Dashboard/read APIs p95 | under 1 second |
| Progress save p95 | under 1 second |
| Lesson/Ask Doubt p95 | under 15-30 seconds |
| Mock test p95 | under 30-45 seconds |
| Error rate | under 1% |

## Notes

- Run true capacity tests against a deployed test backend, not only a laptop.
- AI-heavy tests are limited by backend workers, OpenAI latency/rate limits, and Supabase round trips.
- Keep separate results for browsing, mixed, and AI-heavy runs. Blending them hides the actual bottleneck.
