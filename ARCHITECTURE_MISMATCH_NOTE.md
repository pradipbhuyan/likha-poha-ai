# Lesson Plan Upgrade — Architecture Discovery & Scoping Note

This note records what was actually found in the codebase before implementing
changes, because the originally requested spec assumes an architecture (live
LLM generation at request time, a `lesson_plans` DB table, teacher edit
tracking, draft/published statuses, background job queues, bulk DB
migration/backfill tooling) that **does not exist** in this codebase.

## A. Actual architecture discovered

1. **No live LLM call at request time.** `POST /api/teacher/lesson-plan/generate`
   (`app/routes/teacher.py`) calls `lesson_plan_bank_service.get_lesson_plan()`,
   which reads a static JSON file from disk. No LLM API call happens in this
   request path.
2. **Lesson plans are files, not database rows**, at
   `backend/app/data/lesson_plan_bank/<grade_slug>/<subject_slug>/<chapter_slug>.json`,
   each holding `{grade, subject, chapter, lesson_plan_markdown}`.
3. **Authoring is an offline, human-in-the-loop workflow**:
   `scripts/prepare_gpt55_lesson_plan_prompts.py` builds a prompt per chapter
   (from `app/services/lesson_plan_pedagogy.py`), a human pastes it into a
   GPT-5.5 chat session, and `scripts/ingest_gpt55_lesson_plan_output.py`
   validates + runs `app/services/lesson_plan_quality_checks.py` before
   writing the bank file. No queue, no worker.
4. **Grade/subject-adaptive pedagogy already exists** in
   `lesson_plan_pedagogy.py` (grade bands, teacher-talk cap per band, subject
   categories with distinct pedagogy blocks, objective/timing/differentiation/
   assessment/grounding/variety rules).
5. **Deterministic quality checks already exist** in
   `lesson_plan_quality_checks.py`, blocking bad handouts from being written,
   with a regression test locking in a real historical fix.
6. **Tests already exist** for the prompt builder and quality checks,
   parametrized across many grade/subject combinations.
7. **No teacher-editing of lesson plans exists anywhere** — no edit UI, no
   PATCH route, no edit-history. Every bank file is 100% AI-authored and
   QC-passed; the "preserve teacher edits" problem does not apply here.
8. **No `lesson_plans` DB table, no status/versioning columns, no job queue**
   exists for this feature.
9. **PDF generation is client-side only** (`frontend/src/utils/lessonPlanPdf.js`).

## B. Spec assumptions that don't map to this codebase

| Spec assumption | Reality |
|---|---|
| Live LLM call at request time | Static file lookup only |
| `lesson_plans` DB table w/ edit history | No such table; files on disk |
| Teacher can edit a generated plan | No edit feature exists |
| Background job queue for bulk regen | No queue infra for this feature |
| DB backfill CLI w/ dry-run/resume | Not applicable — no DB rows |
| Draft/published/approved statuses | Not applicable — file exists or doesn't |

## C. Scoped, honest plan actually implemented

Given the above, the realistic equivalent of the spec's intent is:

1. **Strengthen the shared prompt template** (`lesson_plan_pedagogy.py`) to
   require: student-friendly "I can..." success criteria tied to each
   objective, formative-check guidance at each lesson stage (not just at
   closure), and an "anticipated difficulty + teacher prompt" pattern for
   the core activity — while preserving full backward compatibility with the
   existing 8-section schema (no breaking change to already-shipped handouts
   or the frontend's H2_ICONS/H3_ICONS heading map).
2. **Add a `generation_version` field** to newly ingested bank files, so
   future tooling can tell pre-upgrade vs post-upgrade content apart without
   guessing. Existing files are untouched (no bulk overwrite).
3. **Add an audit script** (`scripts/audit_lesson_plan_bank.py`) that scans
   the entire bank read-only and reports counts by `generation_version`
   presence — the dry-run-equivalent "who needs regenerating" report, since
   there is no automated regeneration path (every handout still requires a
   human pasting into GPT-5.5).
4. **Extend the deterministic quality checks** to verify the new
   success-criteria/formative-check requirements on any newly authored
   handout, with tests.
5. **Fix a PDF pagination bug** discovered in `lessonPlanPdf.js` (headings
   could render as the last line on a page with their content pushed to the
   next page).

No existing bank file is silently overwritten. No LLM is called by this
implementation. No chapter content is fabricated.
