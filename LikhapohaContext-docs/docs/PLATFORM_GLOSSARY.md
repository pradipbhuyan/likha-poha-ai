# Platform Glossary

Use these terms consistently in UI, code comments, docs, and prompts.

| Term | Meaning |
|---|---|
| Platform Access | Access to the learning platform features. This replaces the user-facing term “CBSE Access”. |
| Free Tier | Default plan for all new signups. Limited access. |
| Premium Nano / Nano | Paid ₹99 plan, valid for 8 days, full platform access. |
| Premium | Paid ₹299 plan, valid for 30 days, full platform access, one child profile. |
| Family Premium | Paid ₹499 plan, valid for 30 days, full platform access, two child profiles. |
| Offer Code | Legacy or marketing access mechanism. It must not be required for signup. |
| Admin Override | Manual platform access granted by admin without payment. It must be distinguishable from paid subscription access. |
| Subscription Resolver | Canonical backend service that resolves the user’s current plan/access state. |
| Feature Authorization | Canonical service/matrix that determines whether a user can access a feature. |
| Student Workspace | Teacher’s detailed view of a student: overview, progress, assessments, notes, activity, parent, settings. |
| Teacher Assistant | Rule-based dashboard assistant that summarizes interventions, tasks, invitations, and recommended actions. |
| Operations Dashboard | Admin-only dashboard for health, payments, webhooks, subscriptions, usage, alerts, and expiry job. |
| Audit Log | Append-only record of sensitive business actions. Must not contain secrets or plaintext passwords. |
| Subscription Timeline | Append-only subscription history for support and analytics. |
| Feature Matrix | Canonical table defining which plans and roles can access each feature. |
| Admin Console | Admin workspace for accounts, access, associations, offers, AI settings, operations, analytics, support, and tools. |
