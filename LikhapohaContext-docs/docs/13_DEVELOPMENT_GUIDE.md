# Development Guide

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

## Codex Prompt Pattern

```text
Read docs/CODEX_BOOTSTRAP.md and referenced documents.
Implement <task>.
Do not violate product rules.
Add regression tests.
Update docs if behavior changes.
```
