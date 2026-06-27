# AI Agent Instructions

Before making changes to this repository, read `docs/CODEX_BOOTSTRAP.md` first.

Core rules:
- Preserve documented business rules.
- Use canonical services for subscription and feature access.
- Backend owns authorization; frontend renders decisions.
- Do not expose secrets, passwords, tokens, service-role keys, raw payment payloads, or temporary passwords.
- Prefer additive, backward-compatible changes.
- Add or update regression tests for every behavior change.
- Update documentation when business rules, permissions, or architecture change.
