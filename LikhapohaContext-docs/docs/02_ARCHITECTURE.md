# Architecture

## High-Level Architecture

```text
React/Vite frontend
  -> API client/authFetch
  -> FastAPI backend
  -> domain routes
  -> services
  -> Supabase/Postgres/Auth
  -> Razorpay
  -> AI providers
```

## Architectural Principles

1. Backend owns business rules and authorization.
2. Frontend renders state and calls APIs; it must not be the only access-control layer.
3. Subscription state is resolved by a canonical resolver.
4. Feature access is determined by a canonical feature matrix/authorization layer.
5. Sensitive actions are audited.
6. Payments and webhooks are idempotent.
7. Dashboards use canonical summary endpoints where possible.
8. UI components must remain modular and mobile-friendly.

## Backend

The backend uses FastAPI with route modules grouped by domain. Important domains include:

- Authentication
- Subscriptions
- Payments
- Admin control
- Admin operations
- Analytics
- Teacher dashboard/classroom
- Parent dashboard
- Student learning
- AI/doubt services

Service modules contain reusable domain logic such as authentication, subscription resolution, audit logging, metrics, expiry jobs, and timeline events.

## Frontend

The frontend uses React/Vite. API access should go through API client modules and shared auth-aware fetch helpers. Components should not reimplement backend business rules.

Important frontend areas:

- Admin Console
- Admin Operations Dashboard
- Teacher Dashboard / Student Workspace
- Parent Dashboard
- Student learning experience
- Subscription and plan UI

## Canonical Services

### Subscription Resolver

Resolves current plan/access state using legacy compatibility, paid plan status, expiry, offer-code fallback, admin grants, and role.

### Feature Authorization

Determines whether a user can access a feature. It must sit on top of the subscription resolver.

### Payment Service

Creates and verifies Razorpay orders, handles admin test payments, ensures signature verification and idempotency.

### Audit Log Service

Writes sanitized, non-blocking audit events for sensitive actions.

### Subscription Timeline Service

Writes append-only subscription lifecycle events with idempotency keys.

### Metrics Service

Provides lightweight process-local counters and structured logs. These counters reset on restart and are not global across multiple app instances.

### Expiry Job Service

Finds expired paid subscriptions and applies safe fallback. Must be idempotent and must not revoke admin grants.

## Data Flow: Access Decision

```text
Request/User
  -> authenticate
  -> subscription resolver
  -> feature authorization
  -> endpoint executes or returns 403
  -> frontend renders allowed/restricted state
```

## Data Flow: Payment Upgrade

```text
User selects plan
  -> create Razorpay order
  -> payment completed
  -> verify signature
  -> idempotency guard
  -> activate intended plan
  -> write audit event
  -> write subscription timeline event
  -> resolver reflects new plan
```

## Data Flow: Teacher Workspace

```text
Teacher login
  -> teacher dashboard summary
  -> roster/invitations/classrooms/tasks/interventions
  -> student workspace detail
  -> timeline/notes/parent-contact/actions
```

## Admin Operations

Admin Operations Dashboard reads from:

- health/readiness checks
- subscription payments
- webhooks/audit logs
- subscription timeline
- profiles
- teacher-student assignments
- offer redemptions
- metrics service counters

Operations endpoints must be admin-only and must never expose secrets.

## Dashboard Rule

Every dashboard should have a canonical summary endpoint:

- Admin: admin operations/summary
- Teacher: teacher dashboard/summary
- Parent: parent dashboard/summary
- Student: student dashboard/summary

Top-level KPI cards should use one summary source rather than independent duplicate queries.
