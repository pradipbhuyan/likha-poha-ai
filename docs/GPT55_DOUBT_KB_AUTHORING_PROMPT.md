# GPT-5.5 Doubt Knowledge Base (DKB) Authoring Prompt (reusable, machine-processable output)

> Purpose: this is the manual GPT-5.5 authoring workflow for the **Doubt
> Knowledge Base** (`doubt_kb` table — the cache behind "Ask Doubt" and the
> in-lesson follow-up box), mirroring
> `docs/GPT55_QUESTION_BANK_AUTHORING_PROMPT.md`. It exists because the
> existing in-app automatic DKB prewarm
> (`doubt_kb_service.prewarm_doubt_kb_for_grade`, gpt-4.1-nano, admin "Build"
> button) is fast and cheap but lower quality — this workflow lets a
> chapter's doubt bank be authored with GPT-5.5 quality, grounded directly in
> the same corrected lesson content the student sees, for a deliberate push
> toward near-full syllabus coverage.
>
> Both paths coexist: the nano auto-prewarm stays as the quick/cheap option;
> this workflow is for a deliberate, higher-quality coverage pass. It is
> purely additive to the DKB — the same table, same lookup
> (`doubt_kb_service.search_doubt_kb`), same zero-token-cost serving to
> students.
>
> Like the question-bank workflow, there is no manual PDF-copying step —
> `backend/scripts/prepare_gpt55_doubt_kb_prompts.py` pulls the chapter's
> already-authored `lesson_cache` content automatically and embeds it as the
> grounding text.

---

## 1. How to use this workflow

1. Pick the (grade, subject) to build DKB coverage for. The chapter must
   already have authored lesson content in `lesson_cache` — this workflow
   grounds Q&A pairs in that content, not raw PDF/RAG chunks. If a chapter
   has no authored lesson yet, run the lesson-authoring workflow for it
   first.
2. Generate the prompts (one `.txt` file per chapter):
   ```
   cd backend
   python3 scripts/prepare_gpt55_doubt_kb_prompts.py --grade "Grade 9" --subject Science
   ```
   Add `--chapters "Chapter 1: X,Chapter 3: Y"` to scope to specific
   chapters only, and `--questions-per-chapter 40` to change the default
   count (30). Output goes to
   `~/Downloads/GPT55_DKB_Prompts_<grade>_<subject>/` by default (or
   `--output-dir`), with a `00_README_and_index.txt` listing every chapter
   and its expected output filename.
3. For each `*_PROMPT.txt` file: open it, copy the full contents, paste into
   a fresh GPT-5.5 chat session, and save the JSON response as
   `<chapter_slug>_dkb.json` in the same folder.
4. Ingest everything in the folder in one command:
   ```
   cd backend
   python3 scripts/ingest_gpt55_doubt_kb_output.py --dir ~/Downloads/GPT55_DKB_Prompts_Grade_9_Science --dry-run
   python3 scripts/ingest_gpt55_doubt_kb_output.py --dir ~/Downloads/GPT55_DKB_Prompts_Grade_9_Science
   ```
   Always dry-run first. Unlike the question-bank ingester, this does **not**
   clear existing rows — see §4.

---

## 2. The prompt template

The literal template lives in `backend/scripts/prepare_gpt55_doubt_kb_prompts.py`
(`PROMPT_TEMPLATE`) — the script fills in `{grade}`, `{subject}`, `{chapter}`,
and `{chapter_lesson_text}` (the chapter's joined `lesson_cache` content)
automatically. Key structural points, for reference:

- **System role**: a strict CBSE tutor persona, grounded only in the
  provided `CHAPTER_LESSON_TEXT` — never invents facts/numbers.
- **Binding rules**: grounding, question-category diversity (definition /
  conceptual-"why" / application-"how" / common-misconception, spread evenly
  across the chapter's sub-topics), no repeated facts across questions,
  answers are 3–6 direct sentences in a tutor's voice (never "the textbook
  says" or a page reference), Grade-appropriate language.
- **Output schema** — a single JSON object, no markdown fences:
  ```json
  {
    "manifest": {"grade": "...", "subject": "...", "chapter": "..."},
    "qa_pairs": [
      {"question": "...", "answer": "..."}
    ]
  }
  ```
  This mirrors the answer voice `tutor_service.build_synthesized_doubt_answer`
  now uses for live, on-the-fly doubt synthesis, so a bulk-authored answer
  and a freshly-synthesized one read the same way to a student.

---

## 3. Ingestion — what `ingest_gpt55_doubt_kb_output.py` does

1. **Validates** every pair: `question` ≥10 chars, `answer` ≥15 chars.
   Invalid pairs are dropped individually with a printed reason — a few bad
   pairs in a batch don't fail the whole chapter.
2. **Resolves the canonical chapter name**: looks up the manifest's chapter
   string against the current `rag_documents` table for that grade/subject
   (exact match, then a normalized-core fallback), same logic as the
   question-bank ingester. Falls back to the manifest's own chapter string
   only if no `rag_documents` match is found.
3. **Dedupes against existing DKB rows** for that grade/subject/chapter —
   normalizes each incoming question (trim, collapse whitespace, strip a
   trailing "?", lowercase) and skips any pair that already matches an
   active row's question text. This makes re-running the ingest after
   regenerating a chapter's file, or after the nano auto-prewarm has already
   covered some of the same ground, safe — no duplicate rows.
4. **Inserts** via `app.services.doubt_kb_service.store_in_doubt_kb` (the
   same function every other DKB write path uses — live LLM answers, the
   nano auto-prewarm, and admin-approved unanswered-question reviews),
   tagged `source="gpt55"` so these entries are distinguishable in admin
   stats from `"llm"` (live-synthesized) and `"prewarmed"` (nano
   auto-prewarm) rows.

Supports `--input <file>` (single chapter), `--dir <folder>` (every `*.json`
in a folder — pairs naturally with the prompt script's output folder), or
`--files a.json b.json ...` (explicit list). Always supports `--dry-run`,
which prints exactly what would be inserted/skipped without writing
anything (duplicate detection still runs a real read query in dry-run mode
so the preview is accurate).

---

## 4. Why "dedupe then append" instead of "clear then replace"

The question-bank ingester clears a chapter's rows before inserting because
question banks are meant to be **replaced** wholesale by a fresh, better
set. The DKB is different: it's an accumulating cache serving live traffic
from multiple sources at once (this workflow, the nano auto-prewarm, live
student LLM fallbacks, admin-approved reviews) — clearing it would discard
real hit-count history and any entries not covered by this batch. Re-running
this workflow for a chapter you've already authored is a safe, cheap no-op
for anything already present, and only adds genuinely new coverage.
