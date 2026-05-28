# Testing Guide

This project has three layers of tests:

1. Backend API tests using pytest
2. Frontend component tests using Vitest
3. End-to-end tests using Playwright

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

---

## Notes

- Backend tests use pytest and FastAPI `TestClient`.
- Frontend component tests use Vitest and React Testing Library.
- E2E tests use Playwright.
- Vitest should not run Playwright tests. The `e2e` folder is excluded in `vite.config.js`.
- Some backend tests use mocks to avoid calling Supabase, OpenAI, or other external services.
- Generated files like `.coverage` should not be committed.