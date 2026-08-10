# GPT-5.5 Chapter Authoring Prompt (reusable, machine-processable output)

> Purpose: this is the prompt template the user runs manually in a GPT-5.5
> chat session (per Condition 3 of `docs/LESSON_CONTENT_QUALITY_REVIEW_PLAN.md`)
> to generate a chapter manifest + corrected lesson content for any Grade
> 9–12 chapter. The output is **strict JSON**, matching a fixed schema, so
> it can be fed directly into `backend/scripts/ingest_gpt55_chapter_output.py`
> (see §3 below) without any manual reformatting.

---

## 1. How to use this prompt

1. Pick the chapter to remediate (grade, subject, chapter name).
2. Open the source NCERT PDF for that chapter (from `RAG DB/` for Grades
   5–10, or `~/Desktop/cbse_ncert_pdfs/` for Grades 11–12) and copy its
   **full text**.
3. Copy the template below into GPT-5.5, filling in the 5 placeholders:
   `{{GRADE}}`, `{{SUBJECT}}`, `{{CHAPTER}}`, `{{SUBJECT_CLASS}}`,
   `{{CHAPTER_PDF_TEXT}}`.
4. Paste the entire filled-in prompt into a GPT-5.5 chat.
5. Copy GPT-5.5's response (should be pure JSON, no markdown fences) into a
   new file, e.g. `backend/gpt_output/grade9_science_cell.json`.
6. Run the ingestion script (see §3):
   ```
   cd backend
   python3 scripts/ingest_gpt55_chapter_output.py \
       --input gpt_output/grade9_science_cell.json \
       --force
   ```
   This writes the manifest to `chapter_manifests/...`, seeds all 5 lesson
   steps into `lesson_cache` (as `source_type = "MANUAL"`), and
   automatically re-runs the Tier A audit so you immediately see whether
   the output is clean.
7. **MANDATORY — run the page-image citation linker (see §6 below).**
   Every chapter authored via this pipeline cites specific NCERT
   Activities/Exercises/Examples but has NO way for the student to
   actually see them unless this step is run. Do not consider a chapter
   "done" until this has been run for it.

---

## 2. The prompt template (copy everything between the lines below)

```
-----------------------------------------------------------------------------
SYSTEM ROLE

You are a senior CBSE curriculum expert and textbook author. You are
reviewing and rewriting ONE chapter of an NCERT textbook for an AI
tutoring platform. You must act like a strict, subject-matter-accurate
teacher who never invents facts, numbers, or examples that are not
present in — or a direct, standard consequence of — the provided source
text.

BINDING RULES (do not violate any of these):

1. GROUNDING: Every fact, definition, formula, and worked-example number
   you use MUST come from the CHAPTER_PDF_TEXT provided below, or (only if
   SUBJECT_CLASS = "science_or_maths") from a well-known, standard external
   fact that any qualified subject teacher would consider textbook-level
   common knowledge (e.g. the speed of light, standard atomic masses). If
   SUBJECT_CLASS = "humanities_or_language", you may use ONLY facts present
   in CHAPTER_PDF_TEXT — no external knowledge, no paraphrasing that
   changes meaning, no invented examples.
2. NO FABRICATED NUMBERS: Every worked example and quick-check question
   MUST cite/reuse actual activities, experiments, or end-of-chapter
   exercise numbers from CHAPTER_PDF_TEXT wherever the chapter has any
   (e.g. "NCERT Activity 2.2" or "NCERT Q7"). Never invent a numeric
   scenario (e.g. a fictional cell's exact diameter/timing) that does not
   appear in the source text.
3. CHAPTER BOUNDARY: Only include content that belongs to THIS chapter.
   Do NOT include content that would more naturally belong to an adjacent
   or different chapter (e.g. don't teach periodic table classification
   inside a "Structure of Atom" chapter). If you are not fully certain a
   topic is genuinely part of this chapter, leave it out.
4. FULL COVERAGE, NO TUNNEL VISION: Your `must_include_keywords` list and
   your 5 lesson steps together MUST proportionally cover EVERY major
   section/sub-heading that appears in CHAPTER_PDF_TEXT — do not let one
   topic (e.g. one type of numerical calculation) dominate 3+ of the 5
   steps while other major sections of the source text get little or no
   coverage.
5. NO PLACEHOLDER OR VAGUE TEXT: Every "quick_check" question must have a
   complete, correct, specific Answer and Explanation — never leave a
   question unanswered.
6. LANGUAGE LEVEL: Write for the given GRADE level — simple, clear,
   age-appropriate English, but scientifically/factually precise.

-----------------------------------------------------------------------------
USER TASK

GRADE: {{GRADE}}
SUBJECT: {{SUBJECT}}
CHAPTER: {{CHAPTER}}
SUBJECT_CLASS: {{SUBJECT_CLASS}}   (one of: "science_or_maths" | "humanities_or_language")

CHAPTER_PDF_TEXT:
"""
{{CHAPTER_PDF_TEXT}}
"""

Your task has two parts. Return ONLY a single valid JSON object (no
markdown fences, no commentary before or after) with exactly this shape:

{
  "manifest": {
    "grade": "{{GRADE}}",
    "subject": "{{SUBJECT}}",
    "chapter": "{{CHAPTER}}",
    "central_question": "<one sentence: what is the single unifying question this chapter answers?>",
    "in_scope_units": [
      "<one string per major section/sub-heading actually present in CHAPTER_PDF_TEXT, in the order they appear, each describing what that section covers>"
    ],
    "banned_topics": [
      "<any topic that a lesson on this chapter might mistakenly include but that actually belongs to a DIFFERENT chapter — infer this from context; if you cannot identify any with confidence, return an empty array>"
    ],
    "must_include_keywords": [
      "<15-40 specific terms/names/concepts that MUST appear somewhere across the 5 lesson steps combined, drawn from ALL major sections of CHAPTER_PDF_TEXT, not just one>"
    ],
    "known_pitfalls": [
      {
        "claim": "<a specific, plausible mistake a non-expert AI or student might make about this chapter's content>",
        "correction": "<the precise correct statement, grounded in CHAPTER_PDF_TEXT>"
      }
    ],
    "recommended_example_progression": [
      "<a short ordered list of worked-example ideas, each one explicitly citing which NCERT activity/exercise/example it is based on>"
    ],
    "ncert_end_of_chapter_exercises_reference": "<one sentence pointing to the actual end-of-chapter exercise section name/number range found in CHAPTER_PDF_TEXT, if present>"
  },
  "lessons": {
    "Concept introduction": "<full markdown lesson content, see FORMAT below>",
    "Core explanation": "<full markdown lesson content, see FORMAT below>",
    "Worked examples": "<full markdown lesson content, see FORMAT below>",
    "Exam-style problems": "<full markdown lesson content, see FORMAT below>",
    "Revision and recap": "<full markdown lesson content, see FORMAT below>"
  }
}

FORMAT for each value inside "lessons" (this must be a single markdown
string, using exactly these 7 headings in this order):

# <Step Title>: <Chapter Name>

## What you will learn
<2-4 sentences>

## Simple explanation
<a short, plain-language paragraph introducing the core idea(s) for this step>

## Step-by-step breakdown
- **<sub-topic>**: <explanation, grounded in CHAPTER_PDF_TEXT>
- **<sub-topic>**: <explanation, grounded in CHAPTER_PDF_TEXT>
  (as many bullet points as needed to cover this step's share of the chapter)

## Worked example
Question: <a question that cites a real NCERT activity/example/exercise number>

Solution:
- Step 1: ...
- Step 2: ...
- Final answer: ...

## Common mistake
<one specific, plausible misconception and its correction>

## Quick check question
Question: <a specific question>
Answer: <the correct, complete answer>
Explanation: <why this is correct>

## Summary
- <bullet 1>
- <bullet 2>
- <bullet 3>
(3-6 bullets recapping this step's key points)

IMPORTANT: split the chapter content across the 5 steps so that, combined,
they cover the WHOLE of CHAPTER_PDF_TEXT roughly proportionally to how
much space each major section takes in the original text — do NOT let any
single topic dominate more than 1-2 of the 5 steps.

Return ONLY the JSON object described above. No markdown code fences, no
explanation text before or after it.
-----------------------------------------------------------------------------
```

---

## 3. Processing GPT-5.5's output (ingestion script)

Once you have GPT-5.5's JSON response saved to a file (e.g.
`backend/gpt_output/grade9_science_cell.json`), run:

```bash
cd backend
python3 scripts/ingest_gpt55_chapter_output.py --input gpt_output/grade9_science_cell.json --force
```

This script (see `backend/scripts/ingest_gpt55_chapter_output.py`) will:
1. Validate the JSON against the expected schema (manifest keys + 5 lesson
   step keys) — rejects and reports clearly if GPT-5.5 returned malformed
   JSON, extra commentary, or missing fields.
2. Write the `manifest` object to
   `backend/app/data/chapter_manifests/<grade_slug>/<subject_slug>/<chapter_slug>.json`.
3. For each of the 5 entries in `lessons`, compute the correct
   `cache_key` (via `make_lesson_cache_key()`) and call
   `store_lesson_cache()` with `source_type = "MANUAL"` — same mechanism
   used for the Structure of Atom and Cell pilots.
4. Automatically re-run `audit_chapter_boundary.py` for this exact
   grade/subject/chapter and print the resulting critical/high finding
   counts, so you know immediately whether GPT-5.5's output passed the
   deterministic Tier A checks or needs another round.

---

## 4. Example: filled-in prompt header for the two completed pilots

For reference, here is what the placeholders looked like for the two
chapters already completed manually (useful as a sanity check when
filling in a new chapter):

**Pilot #1 — Grade 11 Chemistry, Structure of Atom:**
```
GRADE: Grade 11
SUBJECT: Chemistry
CHAPTER: Structure of Atom
SUBJECT_CLASS: science_or_maths
```

**Pilot #2 — Grade 9 Science, Cell: The Building Block of Life:**
```
GRADE: Grade 9
SUBJECT: Science
CHAPTER: Chapter 2: Cell: The Building Block of Life
SUBJECT_CLASS: science_or_maths
```

For a humanities/language chapter (e.g. Grade 10 History), you would set:
```
SUBJECT_CLASS: humanities_or_language
```
which switches BINDING RULE 1 to strict NCERT-only grounding, per
Condition 6/7 of the main plan document.

---

## 5. Why this prompt design satisfies the project conditions

| Condition | How this prompt satisfies it |
|---|---|
| Condition 1 (automate, limited manual review) | The only manual steps are: copying the PDF text in, pasting the response out, and running one ingestion command — everything else (manifest authoring, all 5 lesson steps, Tier A re-audit) is automatic |
| Condition 3 (GPT-5.5 for gap-filling) | This *is* the GPT-5.5 workflow — one prompt run produces both the manifest AND the corrected content in one pass |
| Condition 4 (no free-tier LLM) | This workflow assumes GPT-5.5 (a paid-tier model) is used manually by the user, satisfying the "no free-tier" rule without needing a paid API key wired into the codebase |
| Condition 6 (asymmetric augmentation) | `SUBJECT_CLASS` placeholder directly toggles the grounding strictness rule inside the prompt itself |
| Condition 7/8 (PDF-grounded, no invented facts) | Binding Rules 1–2 explicitly forbid fabricated numeric examples and require every fact to trace back to `CHAPTER_PDF_TEXT` |
| Consistency with existing pilots | Output schema maps 1:1 onto the exact JSON manifest structure and 8-subsection lesson format already used in the two completed pilot chapters, so `ingest_gpt55_chapter_output.py` can reuse the same `store_lesson_cache()` / `audit_chapter_boundary.py` pipeline with zero changes |

---

## 6. MANDATORY final step for every chapter: page-image citation linking

**This step must be run for every chapter, in every subject, after
ingestion — no exceptions.** Skipping it was the root cause of two
separate live bugs reported by the user (Grade 10 Science citation
popups showing garbled/misaligned text, then Grade 9 Science Chapter 2
citing "Activity 2.1" with zero way for the student to see it).

### Why this exists

Every lesson generated by this pipeline cites specific NCERT
`Activity N.N`, `Exercise N.N`, `Example N`, or `Figure N.N` numbers
(per Binding Rule 2 above) but the raw lesson markdown gives the
student nothing to actually look at for that citation — just a bare
mention like "In Activity 2.1, a student places a transparent ruler...".
An earlier approach tried to solve this by extracting the activity's
text directly from the PDF and showing it in a popup, but this
repeatedly produced garbled, misaligned output (decorative NCERT fonts
rendering as repeated characters, Private-Use-Area glyphs rendering as
block symbols, bullet-point glyphs rendering as stray "n" characters)
across several rounds of fixes. The current, correct approach instead
shows the student the **actual scanned textbook page image** — every
page of every uploaded NCERT PDF is already rendered as a full-page
image and stored in Supabase Storage (via the existing textbook-image
backfill pipeline, recorded in `rag_visual_assets` with columns
`document_id`, `page_number`, `asset_url`, `nearby_text`), so there is
no need to re-extract or clean any text at all.

### How to run it

```bash
cd backend
# Scope to exactly the grade/subject you just ingested:
python3 scripts/inject_page_refs_universal.py --grade "Grade 9" --subject "Science"

# Or scope to a single chapter:
python3 scripts/inject_page_refs_universal.py --grade "Grade 9" --subject "Science" --chapter "Chapter 2: Cell: The Building Block of Life"

# Always dry-run first if you're unsure what it will change:
python3 scripts/inject_page_refs_universal.py --grade "Grade 9" --subject "Science" --dry-run
```

This single script (`backend/scripts/inject_page_refs_universal.py`) is
**database-driven and works for any grade/subject with zero
modification** — it does NOT need local PDF files at all, because it
resolves citation → page number → image URL entirely from
`rag_visual_assets.nearby_text` and `rag_documents`. It:

1. Scans all 5 lesson_cache steps of a chapter for citation patterns
   (`Activity N.N`, `Exercise N.N`, `Example N`/`N.N`, `Case Study N`,
   `Figure N.N`).
2. Looks up which page of the source PDF each citation appears on via
   `rag_visual_assets.nearby_text` (already populated for every
   uploaded document, regardless of curation status).
3. Injects a ` ```extract-ref``` ` fence containing that page's
   `asset_url` immediately after every line mentioning the citation.
   The frontend (`ExtractPopupBlock.jsx`) renders this as a clickable
   pill that opens a modal showing the real scanned textbook page, with
   a link to view it full-size.

### Two confirmed gotchas to know about (both already handled by the script, documented here so they aren't "rediscovered" every session)

1. **Chapter-naming mismatch**: `rag_documents.chapter` is usually
   stored in the prefixed form (`"Chapter 2: Cell: The Building Block
   of Life"`), but `lesson_cache.chapter` for the same chapter is
   frequently stored in the bare/unprefixed form (`"Cell: The Building
   Block of Life"`). The script's `find_document_ids()` tries an exact
   match first, then falls back to a bare-title suffix match — this is
   the same recurring issue already documented in
   `GPT55_LESSON_UPDATE_STATUS.md` for Hindi chapters 7-12, now handled
   generically for all subjects.
2. **Board mismatch**: `rag_documents.board` can legitimately differ
   from `lesson_cache.board` for the same real-world book (confirmed:
   Grade 9 English "Kaveri" is stored as `board='State Board'` in
   `rag_documents` but its `lesson_cache` rows were seeded with
   `board='CBSE'`). The script therefore does NOT filter by `board`
   when looking up `rag_documents` — only by grade+subject+chapter,
   which is already a sufficiently specific key.

### What "no match" chapters mean (not a bug)

Many chapters will report `no_citations_found` (correct — humanities/
language chapters, and grammar-only chapters, genuinely don't cite
NCERT Activity/Exercise numbers) or `citations_found_no_page_match`
(the citation text wasn't found verbatim in any page's `nearby_text` —
usually because that specific page wasn't OCR'd cleanly, or the
citation is a `Figure N.N` reference that's already covered by an
inline `textbook_image` block elsewhere in the lesson). Neither case
indicates a bug — the script only ever adds real, verified links; it
never fabricates one.
