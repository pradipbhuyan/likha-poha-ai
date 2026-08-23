# Profile ID ownership rollout

The application treats `profiles.id` as the ownership key. `username` remains
a mutable display and audit snapshot; it must not authorize or join account
data.

## Deployment order

1. Apply `backend/migrations/20260821_profile_id_ownership.sql` (already applied).
2. Apply `backend/migrations/20260822_email_delivery_observability.sql` (additive).
3. Deploy the application release containing profile-ID reads and writes.
4. Apply `backend/migrations/20260822_profile_id_hardening.sql`.
5. Run `select * from public.profile_id_orphan_counts()` with the service role.
6. Run the **Tenant Isolation Smoke** workflow against staging.

## Orphan policy

Historical rows with no matching profile stay `NULL`-owned and are invisible
to authenticated RLS reads. Do not attach them by similar spelling. Retain or
delete them according to the data-retention policy after reviewing their exact
origin. New account-owned rows are rejected when `profile_id` cannot be set.
AI telemetry is the exception because it also records intentional system jobs;
those rows may remain unowned but are not returned by account dashboards.

## Rename, reassignment, and deletion

- Username changes do not move data: reads remain keyed by `profile_id`.
- A teacher loses access when their active assignment is archived or removed.
- Profile-owned rows have validated foreign keys with `ON DELETE CASCADE`.
- Parent/teacher application access is checked both in route guards and RLS.

## Protected accounts

The rollout does not rename, delete, or recreate `admin@tutor.com` or
`akshita.teststudent@mail.com`. The deployed smoke suite uses randomly named
temporary accounts and removes them in a `finally` block.
