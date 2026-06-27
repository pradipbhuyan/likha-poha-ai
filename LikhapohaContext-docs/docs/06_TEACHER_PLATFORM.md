# Teacher Platform

## Vision

The Teacher Portal should be an actionable classroom workspace. A teacher should know within seconds:

- which students need attention
- what tasks are pending
- which invitations need action
- which classrooms are struggling
- which parents may need communication

## Core Sections

- Overview
- Students
- Invitations
- Classrooms
- Tasks
- Insights

## Student Workspace

Student Workspace includes:

- Overview
- Progress
- Assessments
- Notes
- Activity
- Parent
- Settings

Private notes must never be exposed to students or parents.

## Teacher Assistant

Rule-based assistant summarizing:

- students needing attention
- open high-priority tasks
- pending/expiring invitations
- recommended next actions

No external AI is required for this summary.

## Interventions

Use teacher-friendly labels:

- Needs Immediate Attention
- Needs Review
- Low Priority / Doing Well

Interventions should be actionable: view student, create task, add note, reset password, email login details if paid, message parent if available.

## Tasks

Teacher tasks support manual creation and suggested tasks from interventions. Tasks have priority, status, optional student, due date, and source.

## Classroom Management

Teachers can create, rename, archive classrooms, and assign/remove students. Classroom analytics should show available metrics and “Not available yet” for missing sources.

## Invitations

Teachers can create, resend, cancel, and track invitations. Invitations expire after configured period.

## Teacher Dashboard — Command Center UX (Phase 3)

The teacher dashboard is a single-page productivity command center (Notion × Linear × Google Classroom style):

- **Dashboard tab** (default): hero greeting + KPI cards + attention queue + today's tasks + pending invitations + student preview
- **Students tab**: full roster with search, health indicators, opens StudentWorkspace
- **Classrooms tab**: create/manage + per-classroom analytics (ClassroomAnalyticsCard)
- **Invitations tab**: CRUD with status filter
- **Tasks tab**: open/completed/dismissed with badge count

Key UX rule: critical insights (attention queue, tasks, pending invitations) are visible WITHOUT clicking tabs.

## Frontend Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `TeacherDashboardPage.jsx` | `frontend/src/pages/` | Main command center |
| `StudentWorkspace.jsx` | `frontend/src/components/teacher/` | 7-section student detail |
| `TeacherAssistantCard.jsx` | `frontend/src/components/teacher/` | Rule-based summary |
| `InterventionQueue.jsx` | `frontend/src/components/teacher/` | Critical/medium/low groups |
| `SuggestedTaskModal.jsx` | `frontend/src/components/teacher/` | Pre-filled task from intervention |
| `ClassroomAnalyticsCard.jsx` | `frontend/src/components/teacher/` | Per-classroom metrics |

## Backend Phase 2 Endpoints

All at `/api/teacher/*`, require `role=teacher`:

```
GET  /students/{id}/timeline         — unified student timeline
GET  /interventions                   — prioritized queue
GET  /tasks                          — teacher tasks
POST /tasks                          — create task
PATCH /tasks/{id}                    — update task
POST /tasks/{id}/complete            — mark done
POST /tasks/{id}/dismiss             — dismiss
GET  /classrooms/{id}/analytics      — classroom metrics
GET  /students/{id}/notes            — private notes
POST /students/{id}/notes            — add note
PATCH /students/{id}/notes/{note_id} — edit note
DELETE /students/{id}/notes/{note_id} — soft-delete note
GET  /students/{id}/parent-contact   — parent info (has_email only, never raw email)
POST /students/{id}/message-parent   — send message
```

## DB Tables (Phase 2)

- `teacher_tasks` — title, priority, status, due_date, source, student_id
- `teacher_student_notes` — note, visibility (teacher_private), soft-delete
- `teacher_parent_messages` — subject, message, status (sent/failed/no_email)

## Plan Rules

- Free teacher: 10 students
- Paid teacher: 30 students
- Email login details: paid-only
- Backend must enforce limits and permissions

## Audit Events

Audit student creation/update/archive, password reset, credentials emailed, invitations, classroom changes, tasks, notes, and parent messages with sanitized metadata.
