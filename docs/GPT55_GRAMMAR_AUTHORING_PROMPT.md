# GPT-5.5 Grammar Authoring Prompt (Grade 9 & 10 English Grammar)

> Purpose: this is the prompt template for generating CBSE Grade 9 & 10
> English **Grammar** topics as new dropdown chapters, using the same
> GPT-5.5 pipeline already used for literature chapters and Advanced
> Science/Maths — but tailored specifically for grammar (rules, forms,
> transformation-style worked examples) rather than literary analysis.

---

## 1. Why Grammar needs a different pipeline

Unlike literature chapters, CBSE does not publish a single "Grammar
chapter" PDF — grammar is taught through workbook exercises spread
across the year, following a fixed, well-established topic list. So
instead of extracting text from a source PDF (like
`prepare_gpt55_prompts.py` / `prepare_gpt55_prompts_advanced.py` do),
this pipeline uses **hand-written grounding reference text** — the
actual grammar rules, forms, and common errors a qualified CBSE English
teacher would teach — as the equivalent of `CHAPTER_PDF_TEXT`.

Three new files implement this:

| File | Purpose |
|---|---|
| `backend/scripts/grammar_reference_data.py` | 16 topics (8 Grade 9 + 8 Grade 10) with hand-written grounding reference text for each |
| `backend/scripts/prepare_gpt55_prompts_grammar.py` | Generates ready-to-paste GPT-5.5 prompts from the reference text |
| `backend/scripts/seed_grammar_rag_documents.py` | Inserts a minimal `rag_documents` row per topic so it appears in the student-facing chapter dropdown (the dropdown is 100% RAG-driven for Grades 1-10 — a chapter with no `rag_documents` row is silently invisible, even with content in `lesson_cache`) |

---

## 2. The topic list

**Grade 9 (8 topics):**
1. Grammar: Tenses
2. Grammar: Modals
3. Grammar: Subject-Verb Concord
4. Grammar: Determiners
5. Grammar: Reported Speech (Statements and Questions)
6. Grammar: Commands, Requests and Exclamations in Reported Speech
7. Grammar: Clauses (Noun, Adjective and Adverb Clauses)
8. Grammar: Active and Passive Voice

**Grade 10 (8 topics — advanced/exam-pattern versions):**
1. Grammar: Tenses (Advanced Usage)
2. Grammar: Modals (Advanced Usage)
3. Grammar: Subject-Verb Concord (Advanced Rules)
4. Grammar: Determiners (Advanced Usage)
5. Grammar: Reported Speech (All Sentence Types)
6. Grammar: Clauses and Sentence Transformation
7. Grammar: Active and Passive Voice (Advanced Usage)
8. Grammar: Editing and Omission (Error Correction) — the CBSE Grade 10
   exam-specific editing/omission question type

---

## 3. How to use this pipeline

### Step 1 — Generate the prompts
```bash
cd backend
python3 scripts/prepare_gpt55_prompts_grammar.py --grade "Grade 9"
python3 scripts/prepare_gpt55_prompts_grammar.py --grade "Grade 10"
```
Output goes to `~/Downloads/GPT55_Grammar_Prompts_Grade_9/` and
`~/Downloads/GPT55_Grammar_Prompts_Grade_10/`, one `*_PROMPT.txt` file
per topic (16 total).

Optional: generate just one topic's prompt:
```bash
python3 scripts/prepare_gpt55_prompts_grammar.py --grade "Grade 9" --topic "Grammar: Tenses"
```

### Step 2 — Paste into GPT-5.5
Paste each `*_PROMPT.txt` file's full content into a GPT-5.5 chat
session (one topic per session/message). No PDF attachment is needed —
the grounding text is already embedded in the prompt itself. Save
GPT-5.5's JSON response as `backend/gpt_output/g9_grammar_tenses.json`
(or similar).

### Step 3 — Seed the dropdown entry (once per grade, before ingesting)
```bash
cd backend
python3 scripts/seed_grammar_rag_documents.py --grade "Grade 9" --dry-run   # preview
python3 scripts/seed_grammar_rag_documents.py --grade "Grade 9"             # live
python3 scripts/seed_grammar_rag_documents.py --grade "Grade 10"
```
This inserts one lightweight `rag_documents` row per topic (no PDF
content, just enough metadata for the dropdown to show the chapter).
Safe to re-run — it skips any topic that already has a row.

### Step 4 — Ingest GPT-5.5's output (same as every other chapter)
```bash
cd backend
python3 scripts/ingest_gpt55_chapter_output.py --input gpt_output/g9_grammar_tenses.json --force
```
This writes the manifest, seeds all 5 lesson_cache steps, invalidates
the Chapter Journey cache, and runs the Tier A quality audit — exactly
like the literature/Advanced-chapter pipelines. It will print a
harmless `[skip] No BOOK_SOURCES entry` message for the textbook-image
step (expected — grammar topics have no textbook page images) and
continue normally.

---

## 4. Prompt design differences vs the literature/Advanced pipelines

| Aspect | Literature/Advanced pipeline | Grammar pipeline |
|---|---|---|
| Grounding source | Extracted PDF text (`CHAPTER_PDF_TEXT`) | Hand-written reference text (`GRAMMAR_REFERENCE_TEXT`) |
| Worked examples | Cite a real Example/Activity/Exercise number | Must be a real transformation/fill-in/error-correction task (matching actual CBSE exam patterns) |
| "Common mistake" | A conceptual misconception | A specific, plausible grammar error (wrong tense, wrong article, etc.) |
| Citation popups | `extract-ref` fences citing Example/Activity numbers | Not applicable — grammar rules don't cite numbered source items |
| Textbook images | Backfilled from the source PDF's pages | Not applicable — no textbook page exists |
| Subject class | `science_or_maths` / `humanities_or_language` | `grammar_topic` (new) |

The core binding rule is the same across all three pipelines: **never
invent a fact/rule not grounded in the provided source text.** For
grammar this specifically means every rule and example sentence must be
consistent with `GRAMMAR_REFERENCE_TEXT`, and every example sentence
must itself be grammatically correct (unless explicitly labelled
"Incorrect:" for contrast).

---

## 5. Extending to other grades or new topics

To add more grammar topics (e.g. Grade 6-8 grammar, or a missing Grade
9/10 topic), extend `grammar_reference_data.py`:
1. Add the new topic name to `GRADE_9_TOPICS` / `GRADE_10_TOPICS` (or a
   new `GRADE_N_TOPICS` list).
2. Write its hand-written `REFERENCE_TEXT[topic] = """..."""` entry,
   following the same format: numbered rule/form list with example
   sentences, followed by a `COMMON ERRORS:` section.
3. Register the new grade in `prepare_gpt55_prompts_grammar.py`'s
   `TOPIC_LISTS` dict and `seed_grammar_rag_documents.py`'s
   `TOPIC_LISTS` dict.
4. Run the same 4-step workflow above.

---

## 6. Not yet built / next session TODO

- The 16 prompt files have been generated
  (`~/Downloads/GPT55_Grammar_Prompts_Grade_9/`,
  `~/Downloads/GPT55_Grammar_Prompts_Grade_10/`) but have not yet been
  run through GPT-5.5 or ingested — this is the next concrete step.
- `rag_documents` rows have NOT yet been seeded live (only dry-run
  tested) — run `seed_grammar_rag_documents.py` for real once ready to
  ingest, so the dropdown and content appear together.
