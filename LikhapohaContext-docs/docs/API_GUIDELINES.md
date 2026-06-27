# API Guidelines

## Authorization

Every protected endpoint must enforce role and ownership server-side.

## Responses

Prefer consistent shapes:

```json
{
  "success": true,
  "data": {},
  "message": "Optional human-readable message"
}
```

Errors should be safe:

```json
{
  "error": "FEATURE_RESTRICTED",
  "message": "This feature is available with Premium.",
  "feature": "EXEMPLAR",
  "currentPlan": "FREE_TIER"
}
```

## Pagination

Large lists should support `page`, `page_size`, and date filters where useful.

## Auth Fetch Contract

Frontend API helpers should consistently return parsed JSON or raw `Response`, not both. Existing `authFetch` returns parsed JSON; do not call `.json()` on its result.

## Sensitive Data

Never return secrets, passwords, service-role keys, raw tokens, or raw webhook payloads.
