# Exemplar Research Content Status — Source of Truth

_Last updated: 2026-08-15_

This is the current, living answer to "why is Exemplar Research vague, what
are we doing about it, and where do things stand right now." Companion to
`docs/CONTENT_QUALITY_STATUS.md` (which covers Lessons/Ask Doubt/Mock
Tests/Exam Prep — Exemplar Research is a separate content surface with its
own pipeline, tracked here instead).

**Published audit report (visual, interactive):**
https://claude.ai/code/artifact/088f5db1-004a-4dd8-abbc-c14c098c4e85

---

## 1. Why this work started

A user report — "most of the explanation is vague / no content available"
in Exemplar Research — led to a full audit of all 168 topic cards
(`frontend/src/pages/ExemplarResearchPage.jsx`'s `TOPIC_CARDS`, Grades
8–12). Confirmed and root-caused: **108 of 168 cards (64%) had zero
grounded source content**, spanning 9 of 14 grade/subject sections
entirely.

**Root cause:** unlike Lessons/Mock Tests/Lesson Plans, Exemplar Research
had no pre-authored answer bank. Every card triggered a *live* AI call at
click time (`POST /api/doubt/answer`, chapter tagged `"Exemplar: {chapter}"`)
grounded in whatever NCERT Exemplar PDF content had been chunked, embedded,
and stored in `rag_documents`/`rag_chunks` beforehand. For the 108 affected
cards, that embedding step was simply never run — the PDFs existed on disk
in most cases, but were never uploaded to RAG.

## 2. Decision: move to pre-authored content (like everything else)

Rather than just filling the RAG embedding gap, the decision was made to
move Exemplar Research onto the same pattern already used for Lessons and
Mock Tests: pre-authored via GPT-5.5 handover (human pastes a prompt
grounded in real source material into a GPT-5.5 session, output is
validated and ingested), served instantly forever instead of a live LLM
call on every click. Reasons:

- Exemplar Research was the *only* remaining feature still doing a live,
  uncached LLM call per student click — real repeat OpenAI cost with no
  cross-student caching at all.
- GPT-5.5 authoring with the **full** PDF chapter as context produces
  better-grounded, more detailed output than live RAG's small-chunk
  retrieval + terse 5-line template.
- Removes the embeddings dependency for this content going forward.

The in-progress embeddings-based fix (`upload_ncert_exemplar_rag.py`) was
stopped mid-run once this decision was made. It had already completed for
Grade 8 Maths (13 chapters, real chunks, still sitting in `rag_documents` as
a harmless unused fallback) before being killed — left in place, not
cleaned up, since it doesn't hurt and may still serve as a RAG fallback
path.

## 3. What's fixable at all — 132 of 168 cards

Not every gap is closeable. NCERT simply never published Exemplar problem
books for 3 of the 14 sections — confirmed via live 404s against
`ncert.nic.in`, not just a missing-ingestion issue:

- **Grade 11 Physics** (12 cards) — no PDF exists
- **Grade 11 Chemistry** (12 cards) — no PDF exists
- **Grade 12 Chemistry** (12 cards) — no PDF exists

**36 cards total — permanently unfixable via any content pipeline** unless
sourced differently (e.g. non-Exemplar reference material, with different
framing/copy admitting it isn't from the Exemplar book). This needs a
separate product decision — not a content or code fix.

The other **132 cards across 11 sections** (Grade 8/9/10 Maths+Science,
Grade 11 Maths+Biology, Grade 12 Maths+Physics+Biology) all have a real,
downloaded NCERT Exemplar PDF and are fixable.

## 4. The new authoring pipeline

**Script:** `backend/scripts/prepare_gpt55_exemplar_explanation_prompts.py`

- One prompt per topic card (not per chapter — 165 of 168 cards map to a
  unique chapter 1:1, so chapter-batching wouldn't meaningfully reduce
  prompt count).
- Grounds each prompt in the **full extracted text** of the actual
  downloaded NCERT Exemplar PDF for that chapter (not chunked/embedded —
  GPT-5.5's context window doesn't need that).
- Requests a much richer structure than the old live template: 3–5 sentence
  real concept explanation, 3–6 key rules/formulas, 2–4 worked examples
  **pulled from actual Exemplar problems** (not invented), an explicit
  "what makes Exemplar questions on this topic harder" section, 3–5 common
  mistakes with root causes, a problem-solving strategy, quick recall, and
  a held-back practice problem. Returns structured JSON (matches the
  validate-then-ingest pattern used everywhere else in this codebase).
- Binding rules bake in every anti-fabrication and anti-template lesson
  learned from the subjective-question-bank authoring rounds earlier this
  session (see `docs/GPT55_SUBJECTIVE_QUESTION_BANK_AUTHORING_PROMPT.md` /
  git history around 2026-08-14 for that saga) — grounding required, no
  reused sentence skeletons, no inventing a fixed personal roster of
  question types.
- `--list-missing-sources` flag reports the 36 permanently-unfixable cards.

**Bug found and fixed along the way:** some Exemplar PDFs render bold text
as stacked/overlapping glyphs, which `pdfplumber` extracts as each letter
repeated ~5x (`"perfect"` → `"pppppeeeeerrrrrfffffeeeeecccccttttt"`). Fixed
in `_fix_bold_text_artifact()` — collapses any 3+ run of the same letter to
one instance; verified safe against numbers (digits excluded from the
character class) and against legitimate content (no false hits found across
all 132 generated prompts).

**Output:** `~/Downloads/GPT55_Exemplar_Explanation_Prompts_Grade_{N}_{subject}/`,
one folder per section, 12 prompts each (132 total). Generated 2026-08-14.

**Not yet built:** the ingest/validation script (mirroring
`ingest_gpt55_subjective_question_bank_output.py`'s pattern — schema
validation, template-phrase rejection, cross-chapter templating detector),
the storage location (leaning file-based like
`app/data/lesson_plan_bank/` rather than a new DB table, to avoid a schema
migration — not yet decided), the backend route to serve pre-authored
explanations, and the frontend change to `ExemplarResearchPage.jsx`
swapping `explainTopic()` from a live `/api/doubt/answer` call to fetching
stored content. Deferred until real GPT-5.5 output existed to validate the
format against — which surfaced the much bigger issue below.

## 5. CRITICAL — PDF↔chapter-name catalogue integrity bug (2026-08-15)

Processing the first returned batch (`grade8_maths_exemplar_research_all_12.zip`)
surfaced a serious, previously-unknown bug: **4 of 12 cards came back with
GPT-5.5 correctly refusing to answer**, reporting that the embedded source
PDF text didn't match the requested topic at all (e.g. asked for
"Mensuration," the actual source text was "Exponents and Powers").

This is not a prompt-generation bug — GPT-5.5 did exactly the right thing.
**The underlying chapter-name catalogues used to map PDF filenames to
chapter names are themselves wrong**, in `download_ncert_exemplar.py`'s
`EXEMPLAR_UNIT_NAMES` (Grade 8–10) and
`download_ncert_exemplar_grade1112.py`'s `CHAPTER_NAMES` (Grade 11–12).
Both scripts are used by the OLD embeddings pipeline too, so this bug
predates this session's work.

### 5a. Confirmed real (verified via each PDF's own self-declared "CHAPTER N" header or unambiguous body content)

| Section | Scope | Live impact |
|---|---|---|
| **Grade 12 Biology** | ≥10 of 16 chapters mislabeled | **Already live** — one of the original "60 covered" cards in the very first audit. Real students have been shown explanations for the wrong chapter. Root cause: the catalogue is missing an entire chapter ("Reproduction in Organisms," the real Chapter 1) and the whole numbering cascades wrong from there. Confirmed e.g. `leep404.pdf` self-declares "CHAPTER 4 — REPRODUCTIVE HEALTH" but the catalogue claims position 4 is "Principles of Inheritance and Variation." |
| **Grade 8 Maths** | 6 of 13 chapters mislabeled (heep206, 208, 209, 210, 211, 213) | Not yet live — caught by GPT-5.5 before ingestion. Full corrected mapping already derived by content-reading all 13 files (see below). |
| **Grade 8 Science** | ≥5 of 18 chapters mislabeled (heep109, 110, 111, 113, 117 confirmed; heep104/105/106/108/112/115/116/118 unconfirmed — no self-declared header text extracted yet, page-header-only) | Not yet live |

**Grade 8 Maths corrected mapping** (position → chapter name → actual file
containing it, content-verified):

| Position | Chapter | File |
|---|---|---|
| 6 | Comparing Quantities | `heep209.pdf` |
| 8 | Mensuration | `heep211.pdf` |
| 9 | Playing with Numbers | `heep213.pdf` |
| 10 | Visualising Solid Shapes | `heep206.pdf` |
| 11 | Exponents and Powers | `heep208.pdf` |
| 13 | Direct and Inverse Proportions | `heep210.pdf` |

Positions 1–5, 7, 12 confirmed correct as originally catalogued.

**Grade 8 Science** — partial mapping confirmed via each file's own leading
`"N Title"` text (NCERT's own numbering, self-consistent — same evidence
type used for Grade 12 Biology):

| Position (as originally catalogued) | Actual chapter (per file's own header) | File |
|---|---|---|
| dict pos "8" (Reproduction in Animals) | actually Chapter 9 | `heep109.pdf` |
| dict pos "9" (Force and Pressure) | actually Chapter 11 | `heep111.pdf` |
| dict pos "10" (Friction) | actually Chapter 10 is "Reaching the Age of Adolescence" | `heep110.pdf` |
| dict pos "11" (Sound) | actually Chapter 13 | `heep113.pdf` |
| dict pos "15" (Stars and the Solar System) | actually Chapter 17 | `heep117.pdf` |

Chapters 1, 2, 3, 7 confirmed correct. Chapters 4, 5, 6, 8, 12, 15, 16, 18
still unconfirmed — their files only yielded a running page-header
("EXEMPLAR PROBLEMS") on page 1, not a clean unit title; need a body-content
read (same technique used for Grade 12 Biology's garbled-header files) to
finish this section.

### 5b. Ruled out as false positives (no real bug)

An automated first-pass scan (keyword-overlap heuristic: does any
distinctive word from the expected chapter name appear on the PDF's first
page?) flagged 40 of 179 files total. Manual verification confirmed most of
the non-Grade-8/non-Grade-12-Biology flags were **heuristic false
positives** — the content was correct, it just didn't literally restate the
chapter title in the first few lines (e.g. an MCQ about epithelium/adipose
tissue types is genuinely "Structural Organisation in Animals" content, it
just doesn't say those words on page 1). Verified clean:

- ~~**Grade 11 Biology** — all 22 chapters confirmed correctly
  self-sequential (file N = NCERT's own "CHAPTER N", checked every file).~~
  **CORRECTED 2026-08-15 — this was wrong.** "Self-sequential" only meant
  each file declares itself "CHAPTER N"; it did NOT mean the catalogued
  chapter *name* at position N matched N's real content. Positions 11-22
  were in fact a scrambled block (12 of 22 chapters mislabeled) — see §5d.
  Left here struck through rather than deleted, as a concrete example of
  why "file declares itself CHAPTER N" and "catalogued name is correct for
  CHAPTER N" are two different claims that both need checking.
- **Grade 9 Science** (ieep105, ieep114 flags) and **Grade 10 Science**
  (jeep118 flag) — spot-checked, content matches expected topic.
- The Grade 9/10 "last unit" flags (ieep216, ieep116, jeep118, jeep215) are
  a different, benign case: these are bonus **sample question papers**
  appended to the download range, not real numbered chapters. Not a bug,
  just an extra catalogue entry beyond the real chapter count — doesn't
  affect any real `TOPIC_CARDS` card since none reference these.

### 5c. Done (2026-08-15, this round)

- **Strategy note:** confirmed with user that Exemplar Research is moving
  fully to the GPT-5.5 pre-authored pipeline (§2) — live RAG is being
  phased out, not patched. The Grade 12 Biology "live database" RAG fix
  originally planned here was **deliberately not run** for that reason
  (a corrected dry-run was verified against real prod credentials and is
  ready to go — `python3 scripts/upload_ncert_exemplar_grade1112_rag.py
  --grade 12 --subjects Biology --force` — if the live RAG path needs a
  stopgap fix before the GPT-5.5 swap ships).
- Grade 12 Biology `CHAPTER_NAMES["leep4"]` in
  `download_ncert_exemplar_grade1112.py` — fixed, all 16 chapters
  content-verified directly against each PDF's own self-declared
  "CHAPTER N" header (leep401–leep416). Root cause confirmed: "Reproduction
  in Organisms" (real Chapter 1) was missing entirely, cascading an
  off-by-one shift through the rest; "Animal Husbandry" at old position 16
  was fabricated — no such chapter exists in this book, real Ch16 is
  "Environmental Issues".
- **New bug found, independent of the catalogue:** `TOPIC_CARDS` in
  `ExemplarResearchPage.jsx` itself had a card titled "Reproduction in
  Organisms" whose `chapter` field pointed at "Sexual Reproduction in
  Flowering Plants" — fixed (line ~239). This was a frontend-layer mismatch
  on top of the PDF-catalogue one; the two bugs happened to compound.
- Grade 8 Maths `EXEMPLAR_UNIT_NAMES` in `download_ncert_exemplar.py` —
  fixed, all 13 chapters content-verified. Confirmed the doc's previously
  "derived" table was correct via independent re-verification (body-content
  read, since these PDFs mostly lack a clean self-declared header). Cyclic
  mislabeling among heep206/208/209/210/211/213. Cross-checked against
  `TOPIC_CARDS`: only 4 of the 12 cards reference an affected chapter
  (Mensuration, Comparing Quantities, Direct and Inverse Proportions,
  Playing with Numbers) — exactly explains the doc's "4 of 12 refused"
  finding; the other 2 mislabeled chapters (Visualising Solid Shapes,
  Exponents and Powers) aren't referenced by any card.
- Grade 8 Science `EXEMPLAR_UNIT_NAMES` — fixed, **all 18** chapters
  content-verified (every file has a clean self-declared "N ChapterTitle"
  header, unlike Grade 8 Maths). The scramble was worse than previously
  known: **positions 8–18 (11 of 18 chapters) were mislabeled**, not just
  the 5 earlier confirmed — 1–7 were correct. Cross-checked against
  `TOPIC_CARDS`: **8 of 12 cards affected** (Cell, Force and Pressure,
  Sound, Light, Pollution of Air and Water, Reproduction in Animals,
  Friction, Stars and the Solar System); only 4 unaffected (Microorganisms,
  Conservation of Plants and Animals, Combustion and Flame, Metals and
  Non-Metals).
- Regenerated GPT-5.5 prompts for all 12 now-affected cards (4 Grade 8
  Maths + 8 Grade 8 Science) with the corrected catalogue, spot-checked
  the grounding text for correctness:
  `~/Downloads/GPT55_Exemplar_Explanation_Prompts_Grade_8_maths_CORRECTED/`,
  `~/Downloads/GPT55_Exemplar_Explanation_Prompts_Grade_8_science_CORRECTED/`.
  The other 8 Grade 8 Maths + 4 Grade 8 Science cards were already correctly
  grounded and don't need regeneration — including the batch already in
  flight (`grade8_maths_exemplar_research_all_12.zip`, being processed
  concurrently by another session as of this writing): its 8 non-refused
  answers are fine to ingest as-is, only the 4 refused ones needed the
  regenerated prompts above.

### 5d. Storage + serving pipeline built (2026-08-15)

The pieces §4 flagged as "not yet built" now exist:

- **Storage**: `backend/app/data/exemplar_research_bank/<grade_slug>/<subject_slug>/<topic_slug>.json`,
  file-based (mirrors `lesson_plan_bank/`, no DB migration). Keyed by
  **topic**, not chapter — a few topic cards share a chapter (e.g. Grade 8
  Maths "Squares and Square Roots" / "Cubes and Cube Roots" both cite
  chapter "Square-Square Root and Cube-Cube Root") and each card gets its
  own authored content, so chapter-keying would collide.
- **Service**: `backend/app/services/exemplar_research_bank_service.py` —
  `get_exemplar_explanation(grade, subject, topic)`, same shape as
  `lesson_plan_bank_service.get_lesson_plan()` (reuses its `_slugify`),
  returns `None` if unauthored (no live LLM fallback).
- **Route**: `POST /api/teacher/exemplar-research/explain` in
  `backend/app/routes/teacher.py`, alongside the lesson-plan route it
  mirrors. Auth via `require_teacher_or_admin`; free-tier teachers get a
  403 with the same `EXEMPLAR_RESEARCH` paid-plan message the old
  `/api/doubt/answer` gate used (that gate is now dead code — harmless,
  not yet removed, since Exemplar Research no longer calls that endpoint).
- **Ingest script**: `backend/scripts/ingest_gpt55_exemplar_research_output.py`
  — schema validation (manifest + 8 content keys, min lengths/counts),
  refusal detection (rejects GPT-5.5's "source doesn't cover this topic"
  responses rather than ingesting them), and a cross-topic templating
  detector adapted from `ingest_gpt55_subjective_question_bank_output.py`'s
  `detect_cross_chapter_templating()` (same reused-opener-sentence signal,
  applied to `concept_overview` instead of question text). Renders the 8
  structured JSON fields into one markdown document per topic — matches
  `lesson_plan_bank`'s single-markdown-field shape, so the frontend needed
  no new rendering logic, just a different fetch target.
- **Frontend**: `ExemplarResearchPage.jsx`'s `explainTopic()` now calls the
  new route instead of live `/api/doubt/answer` — the old ~50-line
  hand-built live-tutor prompt is gone, replaced by a plain
  `{grade, subject, chapter, topic}` POST, with `data.success`/`data.message`
  checked the same way `TeacherLessonPlanPage.jsx` does. `handleSearch()`
  and `generatePractice()` on the same page still call live
  `/api/doubt/answer` deliberately — those are open-ended/on-demand
  features, not part of the 168 fixed topic cards, out of scope for this
  swap.
- **First real content live**: ingested the 4 valid Grade 8 Science cards
  from `grade8_science_exemplar_research.zip` (Microorganisms, Conservation
  of Plants and Animals, Combustion and Flame, Metals and Non-Metals) —
  quality-checked (no templating, real per-chapter grounding, all schema
  checks pass) and now served end-to-end (verified via FastAPI TestClient:
  200/success for authored topics, 200/success:false for unauthored,
  403 for free-tier teachers). Existing backend test suite (214 tests
  under `teacher`/`lesson_plan`) still green.
- **`grade8_exemplar_research_batch2_all_5.zip` (2026-08-15) processed** —
  all 5 of the corrected prompts run through GPT-5.5: the 4 Grade 8 Maths
  cards (Mensuration, Comparing Quantities, Direct and Inverse Proportions,
  Playing with Numbers) and 1 of the 8 Grade 8 Science cards (Cell —
  Structure and Functions). All 5 passed validation (grounding
  spot-checked correct — Mensuration content is genuinely perimeter/area,
  Cell content is genuinely cell biology, not the old wrong sources) and
  are now ingested and serving. First pass at this only ingested the 5
  corrected files and initially claimed Grade 8 Maths was "fully covered"
  — checking the actual bank directory (not assuming) showed only 4 Maths
  files present, since the other 8 originally-unaffected Grade 8 Maths
  cards from `grade8_maths_exemplar_research_all_12.zip` had never been
  run through this ingest script (it didn't exist yet when that zip was
  processed). Unzipped that original zip, confirmed the same 8-ok/4-refused
  split predicted in §5c, and ingested the 8 valid ones (no regeneration
  needed — they were always correctly grounded). **Confirmed via directory
  listing: Grade 8 Maths bank now holds all 12/12 files.** Grade 8 Science
  bank holds 5/12 (4 originally-ok cards from the first zip + the
  regenerated Cell card).
- **`grade9_science_exemplar_research_all_12.zip` (2026-08-15) processed**
  — all 12 passed validation cleanly (no refusals, no cross-topic
  templating), consistent with Grade 9 Science already being confirmed
  clean in §5b. Spot-checked grounding on Motion and Tissues (both cite
  real numbered Exemplar problems, on-topic). Ingested; confirmed via
  directory listing (12/12 files) and a live route call.
  **Grade 9 Science bank is now 12/12 — fully covered.**
- **`grade10_maths_exemplar_research_all_12.zip` (2026-08-15) processed —
  found a genuine new catalogue bug.** 10 of 12 cards passed validation
  cleanly and were ingested. The other 2 (Statistics, Probability) failed
  structural validation (too few key_rules_formulas), and the batch's own
  QA note (`grade10_maths_exemplar_research_qa.txt`, included in the zip)
  had already caught it: their supplied source text was "SET-I"/"SET-II
  DESIGN OF THE QUESTION PAPER" — a sample-paper blueprint, not the real
  chapter. Root-caused: `EXEMPLAR_UNIT_NAMES` in `download_ncert_exemplar.py`
  had `"jeep214": "Statistics"` / `"jeep215": "Probability"` as fabricated
  entries — those two files are sample-paper blueprints, not chapters at
  all. Grade 10 Maths' real Chapter 13 (content-verified via its own
  self-declared "CHAPTER 13" header) is a single combined **"Statistics
  and Probability"** chapter (`jeep213`) — but `ExemplarResearchPage.jsx`
  has it split into two separate cards. Since the filename->name catalogue
  dict can only hold one name per file, fixed this with a small,
  explicitly-scoped alias mechanism (`MULTI_CARD_CHAPTER_ALIASES` in
  `prepare_gpt55_exemplar_explanation_prompts.py`) so both "Statistics"
  and "Probability" card lookups resolve to the one real combined-chapter
  PDF instead of the fabricated split. Regenerated both prompts, confirmed
  genuinely grounded (grouped-data mean/median formulas, not sample-paper
  design text) — sitting in
  `~/Downloads/GPT55_Exemplar_Explanation_Prompts_Grade_10_maths_Statistics_Probability_CORRECTED/`,
  waiting on a GPT-5.5 run. **Grade 10 Maths bank is 10/12**; the other
  Grade 9/10 "last unit" bonus-file entries this same pattern could apply
  to (`ieep216`, `jeep118`, etc. — see §5b) were previously assumed benign
  because no card referenced them, but that assumption held only by
  coincidence here until it didn't — worth a deliberate re-check, not
  just trusting the earlier "doesn't affect any card" note.
- **`grade10_exemplar_research_all_14.zip` (2026-08-15) processed** — the
  2 corrected Statistics/Probability prompts plus the full 12-card Grade 10
  Science section, all 14 in one batch. All passed validation cleanly (no
  refusals, no templating); spot-checked Statistics/Probability grounding
  (genuine grouped-data/equally-likely-outcomes content, confirming last
  round's catalogue alias fix works) plus one Science card (Electricity).
  Ingested; confirmed via directory listing and live route calls.
  **Grade 10 Maths: 12/12. Grade 10 Science: 12/12 — both fully covered.**
- **`grade11_exemplar_research_all_12.zip` (2026-08-15) processed** — all
  12 Grade 11 Maths cards passed validation cleanly (no refusals, no
  templating). Spot-checked 3 (Sets, Conic Sections, Permutations and
  Combinations) — genuinely grounded, no sign of the catalogue-mismatch
  pattern found elsewhere. This is a partial answer to the "re-verify
  Grade 11 Maths with the same rigor" item below — real authored content
  came back clean, though that's evidence from spot-checking 3 of 12, not
  a full independent header-by-header audit of the catalogue itself.
  Ingested; confirmed via directory listing (12/12) and a live route call.
  **Grade 11 Maths bank is now 12/12 — fully covered.**
- **`grade11_biology_exemplar_research_all_12.zip` (2026-08-15) processed
  — the §5c/§5e "re-verify the other already-live sections" concern paid
  off.** 7 of 12 cards passed and were ingested. The other 5 (Transport in
  Plants, Mineral Nutrition, Photosynthesis, Respiration in Plants, Plant
  Growth and Development) were refused by GPT-5.5, each correctly
  identifying it had been given a different chapter's content. Verified
  directly against all 22 PDFs' own self-declared "CHAPTER N" headers:
  **positions 11-22 (12 of 22 chapters) were a scrambled block** — far
  worse than the earlier doc note claiming "all 22 chapters confirmed
  correctly self-sequential." That earlier check only confirmed each file
  declares itself "CHAPTER N" (true) without checking whether the
  catalogued NAME at position N actually matches chapter N's real content
  (false, for more than half the book). Fixed `CHAPTER_NAMES["keep4"]` in
  `download_ncert_exemplar_grade1112.py` with the full corrected 22-entry
  list. No frontend-level card/chapter mismatch this time (unlike Grade 12
  Biology) — `TOPIC_CARDS` chapter fields were already internally
  consistent with their topics, the catalogue alone was wrong. Regenerated
  the 5 affected prompts, spot-checked one (Transport in Plants — now
  genuinely reverse-osmosis/transpiration/stomata content, not the earlier
  mismatched chapter) — sitting in
  `~/Downloads/GPT55_Exemplar_Explanation_Prompts_Grade_11_biology_CORRECTED/`,
  waiting on a GPT-5.5 run. **Grade 11 Biology bank is 7/12.**
  **Standing-rule update:** "file N self-declares CHAPTER N" is necessary
  but not sufficient evidence the catalogue is correct — must also check
  the catalogued NAME against that chapter's actual content, not just its
  number. Re-verifying Grade 12 Maths/Physics with this stricter bar is
  still open (§5e).
- **`grade12_maths_exemplar_research_all_12.zip` (2026-08-15) processed
  — the other "already live, unverified" section, and this one held up.**
  Before trusting the "0 refusals" signal alone (which wasn't sufficient
  evidence in Grade 11 Biology's case — GPT-5.5 didn't refuse the cards
  whose real content merely *resembled* the requested topic), independently
  read all 13 PDFs' own self-declared headers directly. Unlike the Biology
  PDFs (garbled/interleaved due to the bold-text-artifact and running-header
  overlap issues from §4), Grade 12 Maths' PDFs have a clean, unambiguous
  "N Chapter TITLE" header on page 1 of every file — all 13 matched the
  current catalogue exactly. Also spot-checked 3 cards' actual authored
  content (Matrices, Vector Algebra, Probability) — all genuinely on-topic.
  Ingested all 12; confirmed via directory listing and a live route call.
  **Grade 12 Maths bank is 12/12 — fully covered, and genuinely verified
  clean this time (not just assumed).**
- **`grade12_physics_exemplar_research_all_12.zip` (2026-08-15) processed
  — the last "already live, unverified" section, and it's genuinely
  clean.** All 12 cards passed validation with no refusals. Independently
  verified all 15 PDFs' own self-declared "Chapter One"/"Chapter Two"/etc.
  headers before trusting the clean result (same discipline applied to
  Grade 12 Maths) — all 15 matched the catalogue exactly. Spot-checked 3
  cards including the two the batch's own QA note flagged with source-scope
  caveats (Electromagnetic Waves: no fabricated wavelength-range table;
  Semiconductor: Zener-regulation-infeasibility handled honestly rather
  than fudged) — both hold up. Ingested all 12; confirmed via directory
  listing and a live route call (as a student profile, matching the
  2026-08-15 auth-gate fix). **Grade 12 Physics bank is 12/12 — fully
  covered.**

  **Every section originally flagged in §5c as "already live, needs the
  same rigor as Grade 12 Biology" has now actually been checked** (Grade
  11 Maths, Grade 12 Maths, Grade 12 Physics — all genuinely clean; Grade
  11 Biology was the one that wasn't and got fixed in this round).
- **Still pending:** the remaining 7 of 8 corrected Grade 8 Science
  prompts (Force and Pressure, Sound, Light, Pollution of Air and Water,
  Reproduction in Animals, Friction, Stars and the Solar System) —
  regenerated prompts already sit in
  `~/Downloads/GPT55_Exemplar_Explanation_Prompts_Grade_8_science_CORRECTED/`,
  waiting on a GPT-5.5 handover run. Grade 9 Maths (already 11/12 in the
  bank via concurrent work, unverified by this session), the 5 corrected
  Grade 11 Biology prompts above, and **Grade 12 Biology** (fixable —
  catalogue already corrected early this session per §5, has real PDFs,
  just no GPT-5.5 batch generated/processed yet — don't confuse with
  Grade 12 **Chemistry**, which is the permanently-unfixable one with no
  PDF at all, per §3) round out what's left.

- **2026-08-16 — consolidated every remaining prompt into one folder, then
  processed a partial batch back.** Ground-truth directory check found
  Grade 9 Maths was actually already 12/12 (the earlier "11/12" note was
  stale). Generated Grade 12 Biology's 12 prompts for the first time ever
  (using the corrected catalogue from §5 — confirmed the "Reproduction in
  Organisms" card, previously broken by both the catalogue bug AND the
  frontend chapter-mismatch bug, is now genuinely grounded in the right
  content). Combined with the still-pending 7 Grade 8 Science + 5 Grade 11
  Biology corrected prompts into
  `~/Downloads/GPT55_Exemplar_Explanation_Prompts_ALL_REMAINING_2026-08-16/`
  (24 total).
  **`mixed_exemplar_research_all_20.zip` processed** — the first 20 of
  those 24 (all of Grade 8 Science + Grade 11 Biology, 8 of 12 Grade 12
  Biology). All 20 passed validation cleanly; spot-checked 3 including
  the two the batch's own QA note flagged with honest scope limits (Grade
  8 Light: reflection only, no refraction numerics in source; Grade 12
  Evolution: Darwinism/Hardy-Weinberg only, no speciation-isolation
  mechanisms) — both held up. Ingested; confirmed via directory listing
  and live route calls. **Grade 8 Science: 12/12. Grade 11 Biology:
  12/12. Grade 12 Biology: 8/12** (4 cards — Biotechnology Principles and
  Processes, Biotechnology and Its Applications, Ecosystem, Biodiversity
  and Conservation — still need their own GPT-5.5 run; prompts for them
  already exist in the ALL_REMAINING folder above, files 21-24).

- **`grade12_biology_exemplar_research_batch3_all_4.zip` (2026-08-16)
  processed — the last 4 cards.** All 4 passed validation cleanly, spot-
  checked grounding (Biotechnology, Ecosystem — both genuinely on-topic),
  ingested and confirmed via directory listing and a live route call.

  **🎉 Every fixable Exemplar Research section is now 12/12 — 132/132
  cards, the entire content pipeline is complete.** Full sweep of
  `exemplar_research_bank/*/*/`: Grade 8 Maths/Science, Grade 9
  Maths/Science, Grade 10 Maths/Science, Grade 11 Maths/Biology, Grade 12
  Maths/Physics/Biology — all 12/12. Existing backend test suite (214
  tests under `teacher`/`lesson_plan`) still green throughout.

  The only remaining gaps are the 3 sections with **no NCERT Exemplar PDF
  published at all** (36 cards, confirmed via live 404s against
  ncert.nic.in — not a content-pipeline problem, see §3): Grade 11
  Physics, Grade 11 Chemistry, Grade 12 Chemistry. Fixing those requires
  a separate product decision (different source material, different
  framing/copy admitting it isn't from the Exemplar book, or dropping
  those cards) — not more authoring.

### 5e. Not yet done
- Decide whether to also re-verify Grade 11 Maths, Grade 12 Maths, Grade 12
  Physics (the other "already live" sections) with the same rigor applied
  to Grade 12 Biology/Grade 8 — they weren't flagged by the automated scan,
  but that scan already proved unreliable in both directions. Given Grade 8
  Science turned out far worse than its initial partial scan suggested,
  don't assume a clean scan on these three means they're actually clean.
- A reusable, standalone header-based verifier script was not built as a
  separate artifact — verification this round was done with inline
  one-off Python (extract page 1 self-declared header via the same
  bold-text-artifact regex from §4, fall back to page 2 or body-content
  read when page 1 is a bare running header). Same technique, just not
  packaged into a script — worth doing if more sections need this treatment.

## 6. Standing rules learned this round

1. A PDF's own self-declared "CHAPTER N" header (or, when that's garbled by
   the bold-text extraction bug, its unambiguous body content) is more
   trustworthy ground truth than any hand-maintained catalogue dict. Treat
   `EXEMPLAR_UNIT_NAMES`/`CHAPTER_NAMES` as a lead to verify, not a fact,
   for any grade/subject not already confirmed in §5.
2. An automated content-matching check needs manual follow-up either way —
   both false negatives (Grade 12 Biology wasn't flagged as strongly as
   Grade 8 in the original ad-hoc checks that started this) and false
   positives (§5b) are possible. Don't trust a clean scan as proof of
   correctness, and don't trust a flag as proof of a bug, without reading
   the actual PDF.
3. GPT-5.5 refusing to answer when given mismatched source material is the
   system working correctly, not a prompt-quality failure — it's the same
   "verify before reporting" discipline this whole content pipeline
   depends on, just applied by the model itself this time.
