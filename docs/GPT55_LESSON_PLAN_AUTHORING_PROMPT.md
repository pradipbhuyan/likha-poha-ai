# GPT-5.5 Lesson-Plan Handout Authoring Prompt (reusable, machine-processable output)

> Purpose: this is the manual GPT-5.5 authoring workflow for the **Create
> Lesson Plan** teacher tool (`lesson_plan_bank/` static files), mirroring
> the question-bank workflow in
> `docs/GPT55_QUESTION_BANK_AUTHORING_PROMPT.md`. It exists because Create
> Lesson Plan used to call an LLM live on every click (RAG lookup + a full
> chat completion), with only a client-side, bypassable 2/day cap guarding
> the cost. This workflow authors one duration-agnostic handout per
> (grade, subject, chapter) up front, grounded in the same corrected lesson
> content the student sees, so serving it at request time is a zero-cost
> file lookup — no LLM call, ever.
>
> Like the question-bank workflow (and unlike the original chapter-lesson
> workflow), there is no manual PDF-copying step —
> `backend/scripts/prepare_gpt55_lesson_plan_prompts.py` pulls the chapter's
> already-authored `lesson_cache` content automatically and embeds it as the
> grounding text.
>
> **Duration-agnostic by design**: the old live-generation tool let a
> teacher pick a 30–90 minute duration and shaped the plan around it. A
> single static handout can't vary by that, so this workflow authors one
> plan sized for a standard ~40-45 minute CBSE period — the "Create Lesson
> Plan" page no longer offers a duration picker.

---

## 1. How to use this workflow

1. Pick the (grade, subject) to author lesson-plan handouts for. The
   chapter must already have authored lesson content in `lesson_cache` —
   this workflow grounds the handout in that content. If a chapter has no
   authored lesson yet, run the chapter-lesson-authoring workflow for it
   first (`docs/GPT55_CHAPTER_AUTHORING_PROMPT.md`).
2. Generate the prompts (one `.txt` file per chapter):
   ```
   cd backend
   python3 scripts/prepare_gpt55_lesson_plan_prompts.py --grade "Grade 9" --subject "Social Science"
   ```
   Add `--chapters "Chapter 1: X,Chapter 3: Y"` to scope to specific
   chapters only. Output goes to
   `~/Downloads/GPT55_Lesson_Plan_Prompts_<grade>_<subject>/` by default (or
   `--output-dir`), with a `00_README_and_index.txt` listing every chapter
   and its expected output filename.
3. For each `*_PROMPT.txt` file: open it, copy the full contents, paste into
   a fresh GPT-5.5 chat session, and save the JSON response as
   `<chapter_slug>_lesson_plan.json` in the same folder.
4. Ingest everything in the folder in one command:
   ```
   cd backend
   python3 scripts/ingest_gpt55_lesson_plan_output.py --dir ~/Downloads/GPT55_Lesson_Plan_Prompts_Grade_9_Social_Science --dry-run
   python3 scripts/ingest_gpt55_lesson_plan_output.py --dir ~/Downloads/GPT55_Lesson_Plan_Prompts_Grade_9_Social_Science
   ```
   Always dry-run first. The live run overwrites any existing handout file
   for that exact chapter, so a re-authored chapter fully replaces its old
   plan.

---

## 2. The prompt template — grade/subject-adaptive pedagogy

The prompt is assembled by `build_lesson_plan_prompt()` in
`backend/app/services/lesson_plan_pedagogy.py` — that module is the single
source of the pedagogy rules, and `prepare_gpt55_lesson_plan_prompts.py`
just calls it with `grade`, `subject`, `chapter`, and `chapter_lesson_text`.
Nothing about a specific grade, subject, or chapter is hard-coded in the
prompt-building script itself; adding a new grade or subject means adding a
bucket to `lesson_plan_pedagogy.py`, not editing prompt strings inline.

The prompt adapts automatically along two axes:

- **Grade band** (`grade_band()`: 1-2, 3-5, 6-8, 9-12) — controls activity
  style (oral/pictures/movement for 1-2 → structured discussion for 6-8 →
  analytical/case-based for 9-12) and the maximum minutes of uninterrupted
  teacher talk before a question/response beat is required
  (`GRADE_BAND_TEACHER_TALK_CAP_MINUTES`).
- **Subject category** (`subject_category()`: languages, mathematics,
  science, social_science, computer_science, skill_subject, or a
  `general_academic` fallback) — controls which activity types are
  prioritized (e.g. worked example + error analysis for Mathematics vs.
  timelines/source interpretation for Social Science), via
  `SUBJECT_PEDAGOGY`.

On top of that, every prompt carries the same binding rules regardless of
grade/subject:

- **Depth over breadth**: 2-4 core learning objectives (a 4th only if the
  lesson genuinely supports it), using measurable verbs (identify, describe,
  explain, compare, classify, solve, demonstrate, create, interpret,
  justify, apply) — never vague ones (know, learn, understand everything
  about, become familiar with).
- **Timing**: stage minutes must sum to the standard 40-45 minute period,
  computed for that specific lesson rather than copied from a fixed split;
  practice time should usually be at least as much as direct-instruction
  time; Direct Instruction must be written as short interactive chunks
  (explain → ask → respond → clarify → example), not one lecture block.
- **Differentiation**: bullet labels are "For students needing additional
  support" / "For students ready for extension" — never "slow learners" /
  "weak students" / "dull students". Support scaffolds the same core
  objectives (word banks, sentence starters, MCQ support, fewer questions,
  etc.) rather than deleting them; extension deepens the same
  concept/topic rather than pivoting to an unrelated fact or trivia.
- **Grounding**: every activity/example/reference must come from
  `CHAPTER_LESSON_TEXT` — no invented NCERT exercise/example numbers, page
  references, or curriculum-alignment claims beyond what the source
  supports.
- **A quality-control checklist** the model is asked to self-check against
  before returning its answer (objectives, timing, activity feasibility,
  assessment alignment, differentiation, relevance, grade/subject fit,
  grounding) — mirrored by the deterministic checks in §3 below, since a
  self-check instruction alone isn't enforcement.

- **Output schema** — a single JSON object, no markdown fences:
  ```json
  {
    "grade": "...",
    "subject": "...",
    "chapter": "...",
    "lesson_plan_markdown": "## Lesson Overview\n- **Topic:** ...\n..."
  }
  ```
  `lesson_plan_markdown` uses the same section structure the old live-
  generated plans used (Lesson Overview, Learning Objectives, Prerequisites,
  Materials & Resources, Step-by-Step Lesson Plan, Homework Assignment,
  Differentiation Strategies, Common Misconceptions, NCERT Alignment) so the
  frontend's existing `ReactMarkdown` rendering and print/PDF handler in
  `TeacherLessonPlanPage.jsx` need no changes. Headings must stay **plain
  text** (no emoji) — `TeacherLessonPlanPage.jsx` maps each exact heading
  string to a Lucide icon via a custom `h2`/`h3` renderer
  (`H2_ICONS`/`H3_ICONS`), so a reworded or emoji-prefixed heading will
  silently lose its icon instead of erroring. (This is also why the section
  headings themselves were kept stable while the pedagogy rules were
  rewritten — only the content requirements changed, not the heading text.)

---

## 3. Ingestion — what `ingest_gpt55_lesson_plan_output.py` does

1. **Validates** the JSON has all four required top-level keys (`grade`,
   `subject`, `chapter`, `lesson_plan_markdown`) and that
   `lesson_plan_markdown` is a non-trivial string (≥200 chars).
2. **Runs the pedagogy quality-control pass**
   (`backend/app/services/lesson_plan_quality_checks.py`,
   `check_lesson_plan_markdown()`) — a deterministic, rule-based check of the
   markdown itself: required section headings present, 2-4 core objectives,
   stage minutes summing to the 40-45 minute period, Direct Instruction
   within the grade band's teacher-talk cap, practice time vs. direct
   instruction, the correct (non-banned) differentiation labels present and
   the support bullet not reading like it deletes core content, 1-3
   misconceptions, and a rough keyword-overlap check that the Assessment &
   Closure stage actually tests the stated objectives. Issues print as
   `[ERROR]` or `[WARNING]`; any `[ERROR]` blocks ingestion (fix and re-paste
   into GPT-5.5, or hand-edit the JSON, then re-run).
3. **Resolves the canonical chapter name**: looks up the chapter string
   against the current `rag_documents` table for that grade/subject (exact
   match, then a normalized-core fallback), the same resolution
   `ingest_gpt55_question_bank_output.py` already does, so the handout file
   name matches how the syllabus dropdown will send the chapter string at
   request time.
4. **Writes** `backend/app/data/lesson_plan_bank/<grade_slug>/<subject_slug>/<chapter_slug>.json`
   (same slugify rule as `chapter_manifests/`, via
   `lesson_plan_bank_service._slugify()`), overwriting any existing file for
   that chapter.

Supports `--input <file>` (single chapter), `--dir <folder>` (every `*.json`
in a folder), or `--files <file1> <file2> ...`. Always supports `--dry-run`,
which prints what would be written without touching disk (including the
quality-control findings, so you can preview issues before overwriting a
live handout).

Note: the quality-control pass is a set of deterministic heuristics, not a
substitute for reading the plan — it can't verify grounding against
`CHAPTER_LESSON_TEXT` (that a fact or NCERT reference actually appears in
the source), so still skim each handout before treating it as final.
