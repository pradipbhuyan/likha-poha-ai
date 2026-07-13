# Codex Bootstrap

Codex and other AI coding agents must read this file before changing the repository.

## Quickstart

**For any task, start by reading `docs/CODEX_CONTEXT.md`** — it is a single file that contains all the critical context needed: product overview, subscription rules, feature authorization, security rules, canonical service map, and what NOT to do.

After reading `CODEX_CONTEXT.md`, read the role-specific docs below as needed.

## Required Reading

For every meaningful change, read:

- `docs/CODEX_CONTEXT.md` ← **START HERE** (single context file for agents)
- `docs/01_PRODUCT_CONTEXT.md`
- `docs/02_ARCHITECTURE.md`
- `docs/03_SUBSCRIPTIONS.md`
- `docs/FEATURE_MATRIX.md`
- `docs/10_SECURITY.md`
- `docs/12_TESTING.md`
- `docs/13_DEVELOPMENT_GUIDE.md`

For role-specific changes also read:

- Admin: `docs/05_ADMIN_PLATFORM.md`
- Teacher: `docs/06_TEACHER_PLATFORM.md`
- Parent: `docs/07_PARENT_PLATFORM.md`
- Student: `docs/08_STUDENT_PLATFORM.md`
- AI/content: `docs/09_AI_PLATFORM.md`

## Non-Negotiable Rules

1. Do not duplicate subscription or access logic.
2. Use the canonical subscription resolver and feature authorization rules.
3. Backend enforces authorization. Frontend restrictions are never sufficient.
4. Free Tier users must never access premium-only features through UI, direct URL, or direct API.
5. Do not expose secrets, tokens, service-role keys, JWTs, passwords, temporary passwords, Razorpay secrets, or raw webhook payloads.
6. Keep payments and webhooks idempotent.
7. Keep admin-only endpoints server-side protected.
8. Audit sensitive actions and sanitize metadata.
9. Keep migrations idempotent and additive unless explicitly approved.
10. Add or update tests for behavior changes.
11. Update docs when product rules, API contracts, permissions, or architecture change.

## Mobile App Rules (expo-router / React Native)

- **Never place data-only `.ts` files in `mobile/app/`** — expo-router treats every file there as a potential route.
- **Never combine `href: null` with `tabBarButton`** in a `Tabs.Screen options` block — use `href: null` alone to suppress a screen from the tab bar.
- **Never pass raw markdown to `<Markdown>`** — always use `<MathAwareMarkdown>` so LaTeX is converted to Unicode before rendering.
- **Google OAuth on mobile** uses `expo-auth-session` + `makeRedirectUri` → backend `/api/auth/mobile/google` (exchanges code for session). Never use `supabase.auth.signInWithOAuth` directly on mobile (requires browser redirect, breaks native app flow).
- **`mobile/lib/`** is for shared utilities and data modules. **`mobile/app/`** is exclusively for expo-router screens and layouts.

## Implementation Style

- Prefer small additive changes.
- Preserve legacy compatibility unless explicitly instructed otherwise.
- Ask targeted questions before changing data model or business rules.
- Keep mobile-first UX.
- Avoid making large monolithic files larger; extract components/services.
- Return safe, structured error states instead of raw backend errors.

## Definition of Done

A change is done only when:

- Backend behavior is correct and authorized.
- Frontend renders correct states on desktop and mobile.
- Relevant regression tests are added.
- Existing tests pass.
- Sensitive data is not exposed.
- Audit/metrics/timeline behavior is updated where applicable.
- Documentation is updated if rules changed.
