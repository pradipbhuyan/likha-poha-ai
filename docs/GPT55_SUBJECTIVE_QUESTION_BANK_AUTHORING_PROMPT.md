# GPT-5.5 Subjective Question-Bank Authoring Prompt (reusable, machine-processable output)

> Purpose: this is the manual GPT-5.5 authoring workflow for the
> **subjective (short/long-answer) half** of Create Test Paper
> (`subjective_question_bank` table) — the sibling of
> `docs/GPT55_QUESTION_BANK_AUTHORING_PROMPT.md`, which covers the MCQ half
> (`question_bank`). Together they let Create Test Paper serve both its MCQ
> and subjective sections entirely from pre-authored content, with zero LLM
> calls at request time — mirroring exactly how Mock Test's MCQ mode already
> works, extended to cover subjective questions too.
>
> Like the MCQ workflow, there is no manual PDF-copying step here —
> `backend/scripts/prepare_gpt55_subjective_question_prompts.py` pulls the
> chapter's already-authored `lesson_cache` content automatically and embeds
> it as the grounding text.

---

## 1. How to use this workflow

1. Pick the (grade, subject) to author subjective question banks for. The
   chapter must already have authored lesson content in `lesson_cache`.
2. Generate the prompts (one `.txt` file per chapter):
   ```
   cd backend
   python3 scripts/prepare_gpt55_subjective_question_prompts.py --grade "Grade 9" --subject "Social Science"
   ```
   Add `--chapters "Chapter 1: X,Chapter 3: Y"` to scope to specific
   chapters only, and `--questions-per-chapter 20` to change the default
   count (20 = a mix of 2-3 mark short-answer and 4-5 mark long-answer
   questions). Output goes to
   `~/Downloads/GPT55_Subjective_Prompts_<grade>_<subject>/` by default (or
   `--output-dir`), with a `00_README_and_index.txt` listing every chapter.
3. For each `*_PROMPT.txt` file: open it, copy the full contents, paste into
   a fresh GPT-5.5 chat session, and save the JSON response as
   `<chapter_slug>_subjective.json` in the same folder.
4. Ingest everything in the folder in one command:
   ```
   cd backend
   python3 scripts/ingest_gpt55_subjective_question_bank_output.py --dir ~/Downloads/GPT55_Subjective_Prompts_Grade_9_Social_Science --dry-run
   python3 scripts/ingest_gpt55_subjective_question_bank_output.py --dir ~/Downloads/GPT55_Subjective_Prompts_Grade_9_Social_Science
   ```
   Always dry-run first. The live run clears any existing
   `subjective_question_bank` rows for that exact chapter before inserting
   the new set, so old/stale questions don't linger — see §4.

---

## 2. The prompt template

The literal template lives in
`backend/scripts/prepare_gpt55_subjective_question_prompts.py`
(`PROMPT_TEMPLATE`) — the script fills in `{grade}`, `{subject}`,
`{chapter}`, and `{chapter_lesson_text}` automatically. Key structural
points, for reference:

- **System role**: a strict CBSE question-setter persona, grounded only in
  the provided `CHAPTER_LESSON_TEXT` — never invents facts.
- **Binding rules**: grounding, a mix of short-answer (2-3 marks, 3-5
  sentence expected answer) and long-answer (4-5 marks, detailed
  multi-point answer) questions, difficulty-band definitions matching the
  MCQ workflow (Easy/Medium/Hard), each question paired with a complete
  `model_answer` a teacher can use directly as an answer key (not just
  bullet hints), and 3-5 `expected_keywords` per question for future
  auto-grading use.
- **Output schema** — a single JSON object, no markdown fences:
  ```json
  {
    "manifest": {"grade": "...", "subject": "...", "chapter": "..."},
    "questions": [
      {
        "question": "...",
        "marks": 3,
        "model_answer": "...",
        "expected_keywords": ["...", "...", "..."],
        "difficulty": "Medium"
      }
    ]
  }
  ```

---

## 3. Ingestion — what `ingest_gpt55_subjective_question_bank_output.py` does

1. **Validates** every question: `question` ≥10 chars, `model_answer` ≥15
   chars, `marks` a positive integer, `difficulty` in
   `{Easy, Medium, Hard}`. Invalid questions are dropped individually with a
   printed reason — a few bad questions in a batch don't fail the whole
   chapter.
2. **Resolves the canonical chapter name** against `rag_documents`, the
   same resolution `ingest_gpt55_question_bank_output.py` already does, so
   bank rows are stored under whatever chapter string the syllabus dropdown
   will actually send at request time.
3. **Clears old content for that chapter**
   (`subjective_question_bank_service.clear_subjective_bank_for_chapter`,
   hard delete, matched via the same normalized-core logic as the MCQ
   workflow) before inserting the new set.
4. **Inserts** via
   `app.services.subjective_question_bank_service.add_questions_to_subjective_bank`,
   which applies its own dedup-by-question-text pass as a second safety net.

Supports `--input <file>`, `--dir <folder>`, or `--files <file1> <file2> ...`.
Always supports `--dry-run`, which prints exactly what would be
cleared/inserted without writing anything.

---

## 4. Why "clear then insert" instead of "append"

Unlike `question_bank`, there is no in-app automatic builder for subjective
questions — this manual GPT-5.5 workflow is the *only* way the bank gets
populated. "Clear then insert" is still the right default so a re-authored
chapter fully **replaces** its question set with the newest, freshest
content instead of silently accumulating duplicates from an earlier,
lower-quality authoring pass.
