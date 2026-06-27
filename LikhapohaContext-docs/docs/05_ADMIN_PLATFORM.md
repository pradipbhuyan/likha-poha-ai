# Admin Platform

## Admin Console Structure

The Admin Console is mobile-friendly and organized into sections/tabs:

- Overview
- Accounts
- Families & Access
- Associations
- Offers
- AI & Settings
- Operations
- Bulk Tools / Support / Analytics as available

## Operations Dashboard

Admin-only dashboard showing:

- System health
- Payment monitoring
- Webhook monitoring
- Subscription monitoring
- Usage metrics
- Alerts/incidents
- Expiry job status and manual run

Operations endpoints must not expose secrets and must label process-local metrics clearly.

## Admin Productivity Features

- Quick Actions
- Global Search
- Favorites/Pinned Actions
- Recent Activity
- Notification Center
- Saved Views
- Analytics
- Support Tools
- Bulk Tools
- View as User read-only simulation

## Platform Access Terminology

Use “Platform Access” and “Platform Access (Admin Override)” in admin UI. Avoid “CBSE Access”.

## Support Tools

Support tools should provide:

- user search
- resolved subscription state
- subscription history
- sanitized audit history
- payment summary
- parent/teacher/student associations
- resend welcome/credential actions where supported
- reset temporary password with secure one-time handling

## View as User

Use frontend/read-only simulation. Do not issue user JWTs. Always show a banner and block destructive/payment/admin actions.

## Admin Safety

- Audit sensitive admin actions.
- Require confirmation for destructive/bulk actions.
- Never expose secrets or plaintext passwords.
- Keep mobile layouts usable.
