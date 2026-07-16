# CBSE Tutor Platform Engineering Handbook

This documentation is the shared product and engineering source of truth for the CBSE Tutor Platform. It is intended for developers, maintainers, product owners, and AI coding agents such as Codex.

## Purpose

The handbook defines:

- Product vision and roles
- Subscription and feature-access rules
- Architecture and service boundaries
- Security and authorization standards
- UI/UX principles
- Testing and regression expectations
- Admin, teacher, parent, student, AI, and content platform direction
- Development and deployment standards

Future implementation prompts should reference these documents instead of repeating all context in chat.

## Document Index

| Document | Purpose |
|---|---|
| `CODEX_BOOTSTRAP.md` | First file for Codex/AI agents to read before any change. |
| `01_PRODUCT_CONTEXT.md` | Product vision, roles, business rules, and definition of done. |
| `02_ARCHITECTURE.md` | Technical architecture and canonical service boundaries. |
| `03_SUBSCRIPTIONS.md` | Subscription model, lifecycle, resolver, and feature authorization. |
| `04_USER_ROLES.md` | Parent, student, teacher, and admin responsibilities. |
| `05_ADMIN_PLATFORM.md` | Admin Console, Operations Dashboard, analytics, support, and tools. |
| `06_TEACHER_PLATFORM.md` | Teacher Workspace, classroom management, tasks, notes, timeline, interventions. |
| `07_PARENT_PLATFORM.md` | Parent portal expectations and roadmap. |
| `08_STUDENT_PLATFORM.md` | Student experience expectations and roadmap. |
| `09_AI_PLATFORM.md` | AI, lessons, question bank, exemplar, and content platform guidance. |
| `10_SECURITY.md` | Authentication, authorization, secrets, audit logs, payments, admin safeguards. |
| `11_DATABASE.md` | Migration, schema, idempotency, indexing, and RLS guidance. |
| `12_TESTING.md` | Regression strategy, authorization matrix tests, E2E, mobile, and performance tests. |
| `13_DEVELOPMENT_GUIDE.md` | Coding standards, API rules, documentation, CI, and Codex workflow. |
| `14_ROADMAP.md` | Completed work and future product/engineering roadmap. |
| `FEATURE_MATRIX.md` | Canonical feature-access matrix by plan and role. |
| `PLATFORM_GLOSSARY.md` | Canonical product terminology. |
| `API_GUIDELINES.md` | API response, error, pagination, and authorization standards. |
| `DECISION_LOG.md` | Major product and architecture decisions. |
| `TECH_DEBT.md` | Tracked architecture, security, and operational debt, with status and priority. |
| `MOBILE_APP.md` | Mobile app strategy, React Native/Expo setup, Play Store submission guide. |

## Guiding Principles

1. Use one canonical source of truth for business rules.
2. Backend owns authorization; frontend only renders decisions.
3. Subscription resolution and feature authorization must be centralized.
4. Mobile-first UI is mandatory.
5. Sensitive admin, payment, teacher, and support actions must be audited.
6. Payment and webhook flows must be idempotent.
7. All migrations must be safe and repeatable.
8. Every change that affects behavior must include regression tests.
9. Product terminology must be clear and consistent.
10. Documentation must evolve with the code.

## Codex Workflow

For any non-trivial change, ask Codex to read:

1. `docs/CODEX_BOOTSTRAP.md`
2. `docs/01_PRODUCT_CONTEXT.md`
3. `docs/02_ARCHITECTURE.md`
4. `docs/03_SUBSCRIPTIONS.md` if access, plans, payment, or authorization are affected
5. `docs/12_TESTING.md` before adding or changing tests

Prompt template:

```text
Read docs/CODEX_BOOTSTRAP.md and all referenced documents first.
Follow the documented business rules and architecture.
Then implement: <task>.
Add regression tests and update documentation if behavior changes.
```
