# Testing Guide

![Tests](https://github.com/pradipbhuyan/cbse-tutor-platform/actions/workflows/tests.yml/badge.svg)

This project has three layers of tests:

1. Backend API tests using pytest
2. Frontend component tests using Vitest
3. End-to-end tests using Playwright

It also includes a longer monthly student journey simulation for realistic platform usage testing.

---

## Backend tests

Run these from the `backend` folder:

```bash
cd backend
./venv/bin/python -m pytest -v
```

---

## Backend coverage

Run this from the `backend` folder:

```bash
cd backend
./venv/bin/python -m pytest --cov=app --cov-report=term-missing
```

This shows backend test coverage and highlights missing lines that still need tests.

---

## Frontend component tests

Run these from the `frontend` folder:

```bash
cd frontend
npm test
```

Vitest runs in watch mode.

Press `q` to quit after tests pass.

Current frontend tests cover:

- LessonsPage loading saved lesson progress
- Practice question generation
- Practice mode disabling Ask AI follow-up

---

## Playwright E2E tests

Playwright tests require the frontend app to be running.

### Terminal 1: start frontend

```bash
cd frontend
npm run dev
```

Keep this terminal running.

### Terminal 2: run Playwright

Open another terminal:

```bash
cd frontend
npx playwright test
```

Current E2E tests cover:

- App loads
- Page renders non-empty content

---

## Monthly student journey simulation

This project also has a longer scenario simulation that behaves like a student using the platform over a month.

The script is:

```text
backend/simulations/monthly_student_journey.py
```

This simulation calls the real backend APIs and covers:

- Lesson generation
- Progress saving
- Profile activity and XP updates
- Doubt answering
- Answer evaluation
- Practice question generation
- CBSE mock test generation
- SOF Olympiad mock test generation
- Test history saving
- Recommendations
- Usage tracking

This is not a normal unit test. It may call real AI services and write data to Supabase.

### Terminal 1: start backend

```bash
cd backend
./venv/bin/python -m uvicorn app.main:app --reload
```

Keep this terminal running.

### Terminal 2: run the simulation

Open another terminal:

```bash
cd backend
./venv/bin/python simulations/monthly_student_journey.py
```

Expected result:

- API calls should return `200`
- Profile counters should increase
- XP should increase
- Usage summary should show requests and tokens
- Recommendations should be based on saved test history

---

## Recommended full test checklist

Before pushing important changes, run all three test layers.

### 1. Backend

```bash
cd backend
./venv/bin/python -m pytest -v
```

### 2. Frontend

```bash
cd frontend
npm test
```

Press `q` after tests pass.

### 3. E2E

Make sure the frontend dev server is running first:

```bash
cd frontend
npm run dev
```

Then in another terminal:

```bash
cd frontend
npx playwright test
```

### 4. Optional monthly simulation

Run this only when you want a realistic longer scenario test:

```bash
cd backend
./venv/bin/python simulations/monthly_student_journey.py
```

Make sure the backend server is already running before starting the simulation.

---

## Notes

- Backend tests use pytest and FastAPI `TestClient`.
- Frontend component tests use Vitest and React Testing Library.
- E2E tests use Playwright.
- The monthly student journey simulation calls real backend APIs and may write data to Supabase.
- The simulation may call real AI services, so avoid running it repeatedly unless needed.
- Vitest should not run Playwright tests. The `e2e` folder is excluded in `vite.config.js`.
- Some backend tests use mocks to avoid calling Supabase, OpenAI, or other external services.
- Generated files like `.coverage` should not be committed.