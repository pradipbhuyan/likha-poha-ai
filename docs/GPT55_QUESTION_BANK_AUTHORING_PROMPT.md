# GPT-5.5 Question-Bank Authoring Prompt (reusable, machine-processable output)

> Purpose: this is the manual GPT-5.5 authoring workflow for the Mock Test
> **question bank** (`question_bank` table), mirroring the chapter-lesson
> workflow in `docs/GPT55_CHAPTER_AUTHORING_PROMPT.md`. It exists because the
> question bank was found to be stale relative to this year's corrected
> lesson content, and the in-app automatic builder (`ask_llm` via
> `backend/app/services/prewarm_service.py`) uses a cheaper model — this
> workflow lets a chapter's MCQ bank be authored with GPT-5.5 quality,
> grounded directly in the same corrected lesson content the student sees.
>
> Unlike the lesson-authoring workflow, there is no manual PDF-copying step
> here — `backend/scripts/prepare_gpt55_question_prompts.py` pulls the
> chapter's already-authored `lesson_cache` content automatically and embeds
> it as the grounding text.

---

## 1. How to use this workflow

1. Pick the (grade, subject) to author question banks for. The chapter must
   already have authored lesson content in `lesson_cache` — this workflow
   grounds questions in that content, not raw PDF/RAG chunks. If a chapter
   has no authored lesson yet, run the lesson-authoring workflow for it
   first.
2. Generate the prompts (one `.txt` file per chapter):
   ```
   cd backend
   python3 scripts/prepare_gpt55_question_prompts.py --grade "Grade 11" --subject Biology
   ```
   Add `--chapters "Chapter 1: X,Chapter 3: Y"` to scope to specific
   chapters only, and `--questions-per-chapter 30` to change the default
   count (30 = 10 Easy / 10 Medium / 10 Hard). Output goes to
   `~/Downloads/GPT55_Question_Prompts_<grade>_<subject>/` by default (or
   `--output-dir`), with a `00_README_and_index.txt` listing every chapter
   and its expected output filename.
3. For each `*_PROMPT.txt` file: open it, copy the full contents, paste into
   a fresh GPT-5.5 chat session, and save the JSON response as
   `<chapter_slug>_questions.json` in the same folder.
4. Ingest everything in the folder in one command:
   ```
   cd backend
   python3 scripts/ingest_gpt55_question_bank_output.py --dir ~/Downloads/GPT55_Question_Prompts_Grade_11_Biology --dry-run
   python3 scripts/ingest_gpt55_question_bank_output.py --dir ~/Downloads/GPT55_Question_Prompts_Grade_11_Biology
   ```
   Always dry-run first. The live run clears any existing `question_bank`
   rows for that exact chapter (any display-prefix format) before
   inserting the new ones, so old/stale questions don't linger alongside
   the fresh set — see §4.

---

## 2. The prompt template

The literal template lives in `backend/scripts/prepare_gpt55_question_prompts.py`
(`PROMPT_TEMPLATE`) — the script fills in `{grade}`, `{subject}`, `{chapter}`,
and `{chapter_lesson_text}` (the chapter's joined `lesson_cache` content)
automatically, so there is no manual copy-paste-and-fill-in step like the
PDF-based lesson workflow. Key structural points, for reference:

- **System role**: a strict CBSE question-setter persona, grounded only in
  the provided `CHAPTER_LESSON_TEXT` — never invents facts/numbers.
- **Binding rules**: grounding, exactly 4 options (A–D) with one correct
  answer, no ambiguous questions, difficulty-band definitions (Easy =
  direct recall, Medium = connecting two ideas or straightforward
  application, Hard = multi-step reasoning — all three still fully
  answerable from the provided text, never requiring outside knowledge),
  explanations that justify (not just restate) the answer, no repeated
  facts across questions, Grade-appropriate CBSE exam phrasing.
- **Output schema** — a single JSON object, no markdown fences:
  ```json
  {
    "manifest": {"grade": "...", "subject": "...", "chapter": "..."},
    "questions": [
      {
        "question": "...",
        "options": {"A": "...", "B": "...", "C": "...", "D": "..."},
        "answer": "A",
        "explanation": "...",
        "difficulty": "Easy",
        "marks": 1
      }
    ]
  }
  ```

---

## 3. Ingestion — what `ingest_gpt55_question_bank_output.py` does

1. **Validates** every question: exactly 4 options keyed A–D (not ≥4 — a
   5-option question is rejected, not silently truncated), all options
   non-empty, `answer` in A–D, `question` ≥10 chars, `explanation` ≥15
   chars, `difficulty` in `{Easy, Medium, Hard}`. Invalid questions are
   dropped individually with a printed reason — a few bad questions in a
   batch don't fail the whole chapter.
2. **Resolves the canonical chapter name**: looks up the manifest's chapter
   string against the current `rag_documents` table for that grade/subject
   (exact match, then a normalized-core fallback) and writes the bank rows
   under whatever `rag_documents` currently uses — e.g. the
   `"Chapter N: Title"` display format — so freshly-ingested content never
   reintroduces the chapter-name mismatch bug this workflow exists partly
   to fix. Falls back to the manifest's own chapter string only if no
   `rag_documents` match is found.
3. **Clears old content for that chapter** (`clear_question_bank_for_chapter`,
   hard delete, matched via the same normalized-core logic — catches rows
   stored under any prior display-prefix format) before inserting the new
   set, so a re-authored chapter fully replaces its old questions instead
   of accumulating duplicates under two different chapter-string variants.
4. **Inserts** via `app.services.question_bank_service.add_questions_to_bank`
   (same function the in-app automatic builder uses), which applies its own
   dedup-by-question-text pass as a second safety net.

Supports `--input <file>` (single chapter), `--dir <folder>` (every `*.json`
in a folder — pairs naturally with the prompt script's output folder), or
`--files a.json b.json ...` (explicit list). Always supports `--dry-run`,
which prints exactly what would be cleared/inserted without writing
anything.

---

## 4. Why "clear then insert" instead of "append"

The in-app automatic builder (`build_question_bank_for_chapter`) skips
regeneration once a chapter/difficulty already has 60 questions — so simply
re-running it after fixing lesson content is a no-op. This manual workflow
is meant to fully **replace** a chapter's question set with GPT-5.5-quality,
freshly-grounded content, not add to it, so it clears first. If you want to
keep the old questions available for admin review instead of deleting them,
use `invalidate_bank_for_chapter()` (soft-marks `needs_review`) before
ingesting, or ingest into a chapter you've confirmed is safe to fully
replace.
