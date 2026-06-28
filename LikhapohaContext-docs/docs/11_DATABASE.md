# Database

_Last updated: 2026-06-28_

## Key Tables

### Authentication & Profiles
| Table | Purpose |
|---|---|
| `auth.users` | Supabase auth users |
| `profiles` | User profiles (student, parent, teacher, admin) |
| `families` | Family groupings for parent-child relationships |

### Learning
| Table | Purpose | Key Columns |
|---|---|---|
| `student_progress` | Lesson progress per chapter | `username`, `subject`, `chapter`, `completed`, `current_step_index`, `updated_at` |
| `test_history` | Mock test results | `username`, `percentage` (0-100), `raw_score`, `max_score`, `subject`, `chapter`, `created_at` |
| `weak_area_alerts` | Identified weak topics | `username`, `subject`, `chapter`, `best_score`, `status` |
| `ai_usage_logs` | AI feature usage tracking | `username`, `feature`, `created_at`, `total_tokens` |
| `quiz_history` | Quiz attempt records | — |

### Parent Platform
| Table | Purpose |
|---|---|
| `parent_notifications` | Persistent notifications for parents |

### Teacher Platform
| Table | Purpose |
|---|---|
| `teacher_student_assignments` | Teacher-student relationships |
| `teacher_classrooms` | Classroom groupings |

### Payments & Subscriptions
| Table | Purpose |
|---|---|
| `payments` | Payment records |
| `subscription_timeline` | Subscription history |
| `offer_redemptions` | Offer code usage |

### Admin
| Table | Purpose |
|---|---|
| `platform_audit_logs` | Admin audit trail (never exposed to parents/students) |

## Tables That Do NOT Exist

The following tables are **not in the database** — do not attempt to query them:

| Table | Status | Alternative |
|---|---|---|
| `chapter_progress` | ❌ Does not exist | Use `student_progress` |
| `lesson_progress` | ❌ Does not exist | Use `student_progress` |
| `homework` | ❌ Not yet created | Return `available: false` |
| `exam_schedule` | ❌ Not yet created | Return `available: false` |
| `ai_conversation_logs` | ❌ Does not exist | Use `ai_usage_logs` |
| `student_activity` | ❌ Does not exist | Use `ai_usage_logs` |
| `lesson_history` | ❌ Does not exist | Use `student_progress` |

## Column Notes

### test_history
- **Use `percentage`** — stored as 0-100 float. `raw_score / max_score * 100` already computed.
- `score` column does **NOT** exist.
- `total_questions` column does **NOT** exist.
- Always use `_normalize_score_pct(percentage, raw_score, max_score)` for safe display.

### profiles
- `access_cbse` — boolean, canonical paid access flag
- `subscription_expires_at` — nullable, expiry date
- `subscription_plan` — string, but use canonical resolver, not this field directly
- `parent_id` — nullable, set when parent creates child
- `family_id` — nullable, family grouping

## Migrations

All migrations in `/backend/migrations/` use `IF NOT EXISTS` for idempotency:
- `20260627_parent_notifications.sql` — `parent_notifications` table

## Safety Rules

1. Never expose `platform_audit_logs` to parents or students.
2. Never expose teacher-private fields (`teacher_student_notes`) to parents.
3. Missing tables return graceful empty (never crash) — use `_safe_query()`.
4. Student data access gated by `require_student` dependency.
5. Parent data access gated by `require_parent` + `_verify_child_ownership()`.
