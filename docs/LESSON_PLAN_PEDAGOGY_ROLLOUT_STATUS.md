# Lesson Plan Pedagogy Rewrite — Rollout Status

> Context doc for picking this work up in a fresh session. Written 2026-08-10.
> **Status refreshed 2026-08-17: the rollout is complete.** This file spent a
> while claiming Grades 9-12 were "Not started" and the total was 220 chapters,
> long after all four had been authored and committed. Anyone planning work
> from the old table would have concluded three-quarters of the bank was
> missing. Counts below are read from disk, not carried forward.

## Background

The "Create Lesson Plan" teacher tool is **not a live LLM feature** — it's an
offline authoring pipeline. A script grounds a prompt in a chapter's already-
authored `lesson_cache` content; normally a human teacher pastes that prompt
into a GPT-5.5 chat and saves the JSON reply; an ingest script validates and
writes it into `backend/app/data/lesson_plan_bank/<grade>/<subject>/<chapter>.json`,
served statically at request time (zero LLM calls per request). Full workflow
doc: `docs/GPT55_LESSON_PLAN_AUTHORING_PROMPT.md`.

The original template produced low-quality plans (crammed objectives, 15-min
unbroken lectures, "slow learners" labelling, differentiation that deleted
core content, off-topic exit tickets, unrelated-trivia extensions — see the
old Grade 5 "The Frog" example for the canonical bad case). This work rewrote
the pedagogy rules and rolled out re-authored plans grade by grade.

## What was implemented (code — done and committed)

- **`backend/app/services/lesson_plan_pedagogy.py`** (new) — single source of
  the authoring prompt. `grade_band()` maps a grade to one of 4 pedagogy
  bands (1-2, 3-5, 6-8, 9-12) each with its own activity style and a
  teacher-talk-chunk cap; `subject_category()` routes any subject string to
  languages/mathematics/science/social_science/computer_science/skill_subject
  (keyword-based, generic fallback for anything unmapped); `build_lesson_plan_prompt()`
  assembles the full prompt. Nothing grade/subject/chapter-specific is
  hard-coded — new grades/subjects just need a bucket added here.
- **`backend/app/services/lesson_plan_quality_checks.py`** (new) — deterministic
  post-generation validator (`check_lesson_plan_markdown()`): required
  headings, 2-4 objectives with measurable verbs, stage-minute sum vs the
  40-45 min window, Direct Instruction vs the grade-band talk cap, practice
  time vs instruction time, differentiation labels (banned vs required) and a
  "does support scaffold or delete" heuristic, misconception count, and a
  keyword-overlap check that Assessment & Closure actually tests the stated
  objectives.
- **`backend/scripts/prepare_gpt55_lesson_plan_prompts.py`** — now calls
  `build_lesson_plan_prompt()` instead of a static template.
- **`backend/scripts/ingest_gpt55_lesson_plan_output.py`** — runs the quality
  pass before writing; `[ERROR]` blocks ingestion, `[WARNING]` prints only.
- **`docs/GPT55_LESSON_PLAN_AUTHORING_PROMPT.md`** — rewritten to describe the
  adaptive prompt and validation pass.
- **Tests**: `backend/tests/test_lesson_plan_pedagogy.py`,
  `backend/tests/test_lesson_plan_quality_checks.py` (includes a regression
  test against the re-authored Grade 5 "The Frog" file, checking every
  "should NOT" bullet from the original bad example).

Full suite passes (2236+ tests). Section headings were kept stable
(`## Lesson Plan (Step-by-Step)`, `### Direct Instruction (N minutes)`, etc.)
rather than renamed — `TeacherLessonPlanPage.jsx` maps exact heading strings
to icons (`H2_ICONS`/`H3_ICONS`), so renaming would silently break icons
across every banked file. Only the *content* rules changed.

## Also done: frontend fixes on `TeacherLessonPlanPage.jsx`

Unrelated to the pedagogy rewrite but done in the same session:
- Fixed "New Plan" button visibility/alignment (root cause: global
  `.primary-btn` CSS has a stray `margin-top: 18px` that misaligned it
  against sibling buttons in the same flex row).
- Added a stepwise "Creating your lesson plan…" reveal animation on Generate
  (shows `/likhapohaai.gif` + a live stepper through the plan's actual
  sections) since the bank lookup is instant and had nothing to visibly wait
  on before.
- Removed the "Regenerate" button — with bank-served content, regenerating
  the same grade/subject/chapter always returns byte-identical output, so it
  was a no-op with a misleading label.
- Fixed a stale "Differentiation for slow/fast learners" line in the
  empty-state tip.

Verified live via Playwright against the real running app (logged in as a
real teacher account through the actual login form).

## Rollout status by grade

| Grade | Status | Chapters | Notes |
|---|---|---|---|
| 5 | ✅ Done, ingested | 47/47 (English 10, Hindi 12, Maths 15, EVS 10) | Includes the hand-corrected "The Frog" regression fixture |
| 6 | ✅ Done, ingested | 54/54 (English 5, Hindi 13, Maths 10, Science 12, Social Science 14) | Social Science was 28 raw chapters in `lesson_cache` but only 14 unique — 2 duplicate naming-prefix variants per chapter (`"1. X"` vs `"Text Book - Part 1 - 1. X"` vs `"History - Part 4 - ..."`); deduped before authoring |
| 7 | ✅ Done, ingested | 62/62 (English 5, Hindi 10, Maths 15, Science 12, Social Science 20) | |
| 8 | ✅ Done, ingested | 57/57 (English 5, Hindi 10, Maths 14, Science 13, Social Science 15) | **10 NCERT "Exemplar" chapters excluded per explicit instruction** — supplementary problem-book content that isn't a real syllabus chapter. See "Known issues" below. |
| 9 | ✅ Done, ingested | 84 (Advanced Maths, Advanced Science, English, English Supplementary Reader, Hindi, Maths, Science, Social Science) | Includes `social_science/democracy.json`, referenced by `tests/test_teacher_tools.py` — check that test before touching it |
| 10 | ✅ Done, ingested | 60 (English, Maths, Science, Social Science) | |
| 11 | ✅ Done, ingested | 191 (Accountancy, Biology, Business Studies, Chemistry, Economics, English, Geography, Hindi, History, Mathematics, Physics, Political Science, Psychology, Sociology) | Widest subject spread of any grade |
| 12 | ✅ Done, ingested | 158 (Accountancy, Biology, Business Studies, Chemistry, Economics, English, Geography, Hindi, History, Mathematics, Physics, Political Science) | |

**Total live in the bank right now: 713 chapters across all eight grades**
(5:47 · 6:54 · 7:62 · 8:57 · 9:84 · 10:60 · 11:191 · 12:158).

**All committed.** `git ls-files` and the on-disk count agree at 713/713.

## How the Grade 6-8 rollout was actually done (repeat this for Grade 9-12)

1. Generate grounded prompts per (grade, subject):
   ```
   cd backend
   python3 scripts/prepare_gpt55_lesson_plan_prompts.py --grade "Grade 9" --subject "English" --output-dir <scratch>/Grade_9_English
   ```
   Repeat for each subject. **Check for duplicate chapters first** (like the
   Grade 6 Social Science case) by comparing raw `lesson_cache` chapter count
   vs `normalize_chapter_core()`-deduped count before generating prompts —
   see the dedup snippet used for Grade 6 Social Science if needed.
   **Also check for Exemplar chapters** (`'exemplar' in chapter.lower()`, or
   more robustly `chapter.strip().lower().startswith("exemplar:")` per
   `is_exemplar_chapter()` in `app/routes/syllabus.py`) and exclude them —
   they are supplementary content, not real syllabus chapters, and Grade 9-12
   Science/Maths/Physics/Biology are exactly where the `is_exemplar_chapter`
   docstring says most of them live (179 rows across 11 grade/subject combos).
2. Instead of the documented human-pastes-into-GPT-5.5 step, an agent (or
   Claude directly) reads each `*_PROMPT.txt` — which is a complete,
   self-contained authoring brief — and writes the JSON output itself,
   following the binding rules in the prompt file. This was done via ~20-27
   parallel background agents split by subject (and split further within
   large subjects, ~6-12 chapters per agent) to keep individual batches
   manageable. See this session's transcript for the exact agent prompt
   template if reusing the pattern.
3. Each output is saved as `<name>_lesson_plan.json` next to its
   `_PROMPT.txt`, then validated immediately via:
   ```python
   from app.services.lesson_plan_quality_checks import check_lesson_plan_markdown, has_errors
   ```
4. Once all files in a batch are written, independently re-validate the
   whole batch (don't just trust each agent's self-report), then:
   ```
   python3 scripts/ingest_gpt55_lesson_plan_output.py --dir <scratch>/Grade_9_English --dry-run
   python3 scripts/ingest_gpt55_lesson_plan_output.py --dir <scratch>/Grade_9_English
   ```

**Watch for platform-side transient failures**: during the Grade 6-8 run,
many agents hit session usage limits and transient "connection closed
mid-stream" API errors partway through. When an agent fails, check exactly
which files it already wrote (`ls <folder> | grep lesson_plan.json`) before
resuming — resuming with `SendMessage` preserves its transcript/context
(much faster than restarting), but you must tell it precisely which files
are still missing or it may redo work or skip files. If an agent shows as
"stopped by the user" (not failed), the system will refuse to resume it —
you must launch a fresh agent for the remaining files in that case.

## Known issues found along the way (not fixed, flagged for the user)

1. **Teacher self-signup is broken in production.**
   `POST /api/auth/teacher-signup` (`backend/app/routes/auth.py`) inserts a
   `school_name` column into `profiles` that does not exist in the actual
   Supabase schema (confirmed via `admin_client.table('profiles').select('*')`
   — no `school_name` key in any row). Every self-signup attempt creates an
   orphaned Supabase auth user (no profile row) and then 500s with a generic
   "We're having trouble right now" message. Never fixed this session —
   discovered while creating a throwaway QA test account (which was cleaned
   up afterward).
2. **`is_exemplar_chapter()` may have a matching gap.** It checks
   `chapter.strip().lower().startswith("exemplar:")`, but the Grade 8 Maths
   Exemplar rows are labeled `"Part 1 - Exemplar: ..."` — which does **not**
   match that prefix check. If so, those 10 chapters may currently be
   selectable in the real teacher/student dropdown despite the function's
   documented intent to hide Exemplar content everywhere. Worth verifying
   and fixing the regex/prefix check if confirmed.

## Immediate next steps

1. Decide whether to commit the Grade 5-8 rewrite (nothing is committed yet).
2. Continue the same process for Grade 9, 10, 11, 12 if wanted — Grade 9-12
   subjects are more numerous (Physics/Chemistry/Biology split out from
   Science, Economics/History/Geography/Political Science split out from
   Social Science, plus stream-specific subjects), so expect a larger
   chapter count than Grade 6-8 and budget for correspondingly more parallel
   agents.
3. Consider fixing the two known issues above (separate from this task).
