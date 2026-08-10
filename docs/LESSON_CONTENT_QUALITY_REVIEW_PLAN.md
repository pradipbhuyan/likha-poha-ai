# Lesson Content Quality Review & Remediation Plan
**(Grades 9–12, all subjects — starting with Grade 11 Chemistry "Structure of Atom")**

> Use this document as context for a fresh Claude/Cline session. It captures the
> original problem report, the codebase investigation findings, the root cause,
> and a concrete phased plan to fix lesson content quality across the platform.

---

## 0. Project Conditions / Constraints (set by the user — binding for all phases)

These conditions govern how every phase below must be executed. They were
set explicitly by the user and take precedence over any convenience
shortcut described elsewhere in this document.

1. **Goal: automate the review process, with limited manual review.**
   Manual effort should be reserved for spot-checks, approvals, and
   plugging specific content gaps — not for re-authoring every chapter by
   hand from scratch.
2. **Claude (via this coding assistant) does the implementation work** —
   building manifests, audit scripts, and remediation content — and should
   acquire/synthesize the best available content itself wherever grounding
   material allows.
3. **The user will separately use a GPT-5.5 chat session** to retrieve
   supplementary content to plug specific identified gaps. That content
   will be handed back in for integration.
4. **No free-tier API/LLM licenses for anything that touches lesson
   content quality.** Free-tier models are explicitly disallowed for
   content generation, repair, or review in this workflow because quality
   cannot be guaranteed — this applies to Tier B LLM review, Track A/B
   remediation generation, and any manifest-authoring assistance.
5. **Existing NCERT-based RAG content must be used and respected as the
   primary grounding source** for all subjects. Do not discard or ignore
   the already-uploaded RAG chunks — the manifest and remediation work
   should build on top of them, not replace them.
6. **Subject-specific augmentation policy (important — asymmetric rule):**
   - **Science & Mathematics** (Physics, Chemistry, Biology, Mathematics):
     content **may be augmented** with relevant material from other
     textbooks and international sources (e.g. international
     equivalents, Khan Academy-style explanations, other national curricula)
     **because these subjects are universal** — the underlying facts,
     formulas, and models don't change by textbook or country.
   - **All other subjects** (English, Hindi, History, Geography, Political
     Science, Economics, Business Studies, Accountancy, etc.): content
     **must be strictly grounded to the NCERT textbook**. No augmentation
     from outside sources. These subjects are curriculum-specific,
     interpretation-specific, and often exam-board-specific — outside
     material is not acceptable.
7. **Review methodology for non-Science/Maths subjects — "teacher reading
   the PDF word by word":** Review and validation of these subjects must
   go through the **actual source PDFs** (already present in the local
   `RAG DB/` folder and/or `rag_documents`/`rag_chunks` tables), reading
   and cross-checking **word by word**, the way a teacher would while
   preparing a lesson from the textbook. The generated lesson must
   **faithfully reflect exactly what is written in the PDF** — **no AI
   creativity, no paraphrasing that changes meaning, no invented examples
   not present in or directly derivable from the text.**
8. **Science & Maths lessons may still be creatively explained/re-worded**
   for pedagogy (simpler language, additional worked examples, diagrams),
   but any *added facts* (e.g. a fact not in NCERT) must come from a
   credible external source explicitly identified in the manifest/citation,
   never invented.

These constraints directly shape Phase 0 (manifest content must cite NCERT
PDF page/section for humanities/languages, and may cite external sources
for Science/Maths), Phase 1 (Tier B LLM review must use a paid-tier model
only), and Phase 3 (remediation content authoring must follow the
grounding rules above per subject).

---

## 1. Origin of this document

The user manually reviewed the Grade 11 Chemistry chapter **"Structure of Atom"**
as delivered by the platform and found it was **not ready for student use**. The
lesson mixed content from **at least four different NCERT chapters**:

- Structure of Atom
- Classification of Elements and Periodicity in Properties
- Some Basic Concepts of Chemistry
- Thermodynamics

It also contained scientifically incorrect statements (e.g. "helium is a
p-block element"), irrelevant worked examples (density calculation, a
dimensionally-broken nitrogen-gas "percentage" problem), missing core
syllabus content (cathode-ray experiment, Rutherford scattering, Bohr model,
quantum numbers, Aufbau principle, etc.), and unanswered "quick check"
questions with no feedback.

**Full text of the original manual review is preserved below in Appendix A**
so a fresh session has the complete rubric the user used to judge quality.

The user's ask: figure out the best way to **review every chapter in Grades
9–12 academically**, and **implement fixes**, including **manually adding
content via JSON files** the same way it was previously done for Q&A content.

---

## 2. Codebase investigation — what already exists

Project root: `/Users/a0247716/Pradips_Project/cbse-tutor-platform`

### 2.1 How lesson content is actually produced (critical finding)

Lesson content is **NOT stored as static/manual JSON files** for normal
delivery. It is generated **live by an LLM** and cached per
`grade + subject + chapter + step_title` key in a Supabase table called
`lesson_cache`.

Relevant files:
- `backend/app/services/tutor_service.py` — system prompts (`TUTOR_SYSTEM`,
  `PROSE_LITERATURE_SYSTEM`, `POEM_SYSTEM`, `detect_chapter_type()`) that
  instruct the LLM how to teach a given step/sub-topic.
- `backend/app/services/lesson_cache_service.py` — `make_lesson_cache_key()`,
  `get_cached_lesson()`, `store_lesson_cache()`.
- `backend/app/services/prewarm_service.py` — background pre-generation of
  lessons ("prewarming") so students get instant cached content instead of
  live LLM calls.
- `backend/app/services/lesson_kb_service.py` — lesson knowledge-base
  logic tied to RAG (retrieval-augmented generation) chunks from uploaded
  NCERT PDFs.
- `backend/app/services/rag_service.py` — `search_textbook_content()` pulls
  relevant textbook chunks (from Supabase `rag_documents` / `rag_chunks`)
  that get stuffed into the LLM prompt as grounding context.

**Root cause of the mixed-chapter problem:** the LLM is given a
`chapter` string (e.g. "Structure of Atom") and some RAG-retrieved textbook
chunks, but **there is no explicit, enforced topic boundary / banned-topic
list** telling it what does *not* belong in this chapter. When RAG retrieval
pulls in adjacent-chapter chunks (very plausible for Chemistry Class 11
Unit 1–3, which are conceptually close), the LLM blends them together
un-flagged.

### 2.2 Existing "Platform QA Center" (admin-only) — six tools already built

Router: `backend/app/routes/admin_qa.py`. Six independent audit/repair
subsystems already exist:

| # | Tool | Script | What it checks | What it MISSES |
|---|------|--------|-----------------|-----------------|
| 1 | **Lesson Quality Audit** | `backend/scripts/audit_lesson_quality.py` → `reports/lesson_quality_grade{N}/lesson_quality_report.json` | Pedagogy score, formula quality, MCQ quality, "student flow", generic structure findings (e.g. "lacks real-world context") | **Chapter relevance / scientific accuracy** — Structure of Atom scored 94/100 overall despite the four-chapters-mixed-together problem. This is the report the user's manual review exposed as insufficient. |
| 2 | **Lesson Sections Audit** | `backend/scripts/audit_lesson_sections.py` → `reports/lesson_sections/lesson_sections_report.json` | Presence/word-count of the canonical 8 sections (Introduction, What You Will Learn, Simple Explanation, Step-by-Step Breakdown, Worked Example, Common Mistake, Quick Check Question, Summary) | Same — structural completeness only, no subject-matter correctness |
| 3 | **Lesson Content Audit** | `backend/scripts/audit_lesson_content.py` | Regex-based: truncated content, broken LaTeX, control chars, missing section headings, placeholder text (`[INSERT]`, `TODO`, etc.), too-short content | No semantic/curricular checks at all |
| 4 | **NCERT vs Platform Audit** | `backend/scripts/audit_ncert_vs_platform.py` | Compares NCERT chapter *list* (from local PDFs) vs what's uploaded to the RAG DB — **only wired for Grades 5–10** | Does not check *lesson* content, only whether a chapter's source PDF was uploaded to RAG. Not extended to 11/12 yet. |
| 5 | **Feature Authorization Audit** | `backend/scripts/audit_feature_authorization.py` | Access-control / subscription-gating checks | Unrelated to content quality |
| 6 | **Lesson Repair Engine** | `backend/app/services/lesson_repair_service.py` + admin UI | Admin-triggered LLM rewrite of any failed lesson; validates the repaired draft against the 8-section schema (`validate_repaired_draft()`); **never auto-publishes** — requires admin approval (`publish_repaired_task()`) | Repair prompt (`_REPAIR_SYSTEM_PROMPT` / `_REPAIR_USER_TEMPLATE`) has **no concept of chapter scope/boundaries** either — it will just as happily "repair" a lesson while keeping the wrong topics in it, because nothing tells it what's out-of-scope. |

### 2.3 Manual content authoring precedent (closest match to "Q&A JSON" approach)

`backend/scripts/chatgpt_lesson_helper.py` — a **2-step manual workflow**:
1. `python3 scripts/chatgpt_lesson_helper.py prompt --grade ... --subject ... --chapter ... --step ...`
   → prints the exact system+user prompt (including RAG context) to paste into
   ChatGPT Desktop by hand.
2. Copy ChatGPT's response, then
   `python3 scripts/chatgpt_lesson_helper.py store --grade ... --subject ... --chapter ... --step ... --file lesson_output.txt`
   → writes the human-reviewed content **directly into `lesson_cache`**,
   bypassing live LLM generation entirely for that step.

This is the existing mechanism most similar to "manually adding content the
way we did for Q&A" — it is **not** a JSON content store, but it lets a human
inject vetted content straight into the same table the live system reads
from, with no LLM risk at read time.

### 2.4 Q&A / Question Bank subsystem (separate from lessons)

- `backend/app/services/question_bank_service.py`,
  `backend/scripts/build_question_bank.py`,
  `backend/sql/add_question_bank.sql` — a Supabase table `question_bank`
  storing MCQs (question/options/answer/explanation/marks) per
  grade/subject/chapter, built via LLM (`build_question_bank_for_chapter()`),
  admin-triggerable, with a `needs_review` status flag.
- This is **not** JSON-file-based either — it's DB-backed. If the user's
  "we did it for Q&A in JSON files" refers to something outside this repo
  (e.g. a spreadsheet/JSON export workflow used ad hoc), that should be
  clarified with the user — see Open Questions (§6).

### 2.5 Chapter list ("syllabus") — confirmed correct, not the problem

`backend/scripts/seed_grade1112_syllabus_overrides.py` contains a hand-typed
`CHAPTER_OVERRIDES` dict per NCERT book code, confirming:
```python
"kech1": {1:"Some Basic Concepts of Chemistry", 2:"Structure of Atom",
          3:"Classification of Elements and Periodicity in Properties",
          4:"Chemical Bonding and Molecular Structure", 5:"Thermodynamics",
          6:"Equilibrium"}
```
**Structure of Atom is correctly scoped as its own, separate chapter** in the
syllabus data. The corruption happens purely at **lesson-content-generation
time**, not in the chapter/syllabus metadata.

### 2.6 No pre-existing "chapter topic manifest" or scope-boundary data of any kind

Searched extensively — there is no JSON, YAML, or DB table anywhere in the
codebase that defines, per chapter, "these are the in-scope topics, these are
explicitly out-of-scope, these are must-include keywords." **This does not
exist yet and needs to be built.**

---

## 3. Root cause summary

1. Lessons are generated live by an LLM per `(grade, subject, chapter, step)`,
   grounded by RAG-retrieved textbook chunks.
2. RAG retrieval for closely related Class 11 Chemistry Unit 1–3 topics
   (Basic Concepts → Structure of Atom → Periodicity) can pull chunks across
   chapter boundaries.
3. Nothing in the system prompt or retrieval pipeline enforces a hard
   chapter-scope boundary or flags topics that must NOT appear.
4. All 6 existing QA tools check **structure/formatting/pedagogy scores**,
   never **curricular correctness or chapter boundary compliance** — so a
   badly-scoped-but-well-formatted lesson (like Structure of Atom, scoring
   94/100) sails through every existing audit clean.
5. There is no manifest of "what belongs in this chapter" anywhere in the
   system for any grade/subject — this affects **all** Grade 9–12 chapters,
   not just Chemistry, and likely Grade 5–8 too, though the user's review
   sample was Grade 11 Chemistry.

---

## 4. Recommended remediation plan (phased)

### Phase 0 — Chapter Topic Manifest (new JSON data layer)

Create one JSON file per `(grade, subject, chapter)` describing the
authoritative scope. Suggested location:
`backend/app/data/chapter_manifests/<grade>/<subject>/<chapter_slug>.json`

Example for Grade 11 Chemistry → Structure of Atom:

```json
{
  "grade": "Grade 11",
  "subject": "Chemistry",
  "chapter": "Structure of Atom",
  "central_question": "How did scientists develop the modern model of the atom, and how are electrons arranged inside it?",
  "in_scope_units": [
    "Discovery of the electron, proton, neutron",
    "Cathode-ray discharge experiment; charge-to-mass ratio",
    "Millikan oil-drop experiment",
    "Thomson's atomic model",
    "Rutherford's alpha-particle scattering experiment and nuclear model",
    "Limitations of Rutherford's model",
    "Electromagnetic radiation; wavelength, frequency, speed of light (c = νλ)",
    "Planck's quantum theory; photoelectric effect",
    "Atomic spectra; hydrogen line spectrum; Rydberg equation",
    "Bohr's atomic model: postulates, energy levels, transitions, limitations",
    "de Broglie relationship; Heisenberg uncertainty principle",
    "Quantum-mechanical model; orbitals and probability distribution",
    "Quantum numbers (n, l, m, s)",
    "Shapes of s, p, d orbitals; nodes",
    "Aufbau principle (n+l rule); Pauli exclusion principle; Hund's rule",
    "Electronic configurations; stability of half-filled/filled subshells"
  ],
  "banned_topics": [
    "Density calculation from mass and volume",
    "Gas-volume / molar volume at STP calculations",
    "Percentage composition calculations",
    "Analytical balances / lab equipment for mass measurement",
    "Mass vs weight lab discussion",
    "Reactions at high temperature (unrelated context)",
    "Second law of thermodynamics",
    "Detailed periodic classification history (Döbereiner, Newlands, Mendeleev) — belongs to 'Classification of Elements' chapter",
    "s-block/p-block/d-block/f-block classification — belongs to 'Classification of Elements' chapter"
  ],
  "must_include_keywords": [
    "cathode ray", "Millikan", "Thomson", "Rutherford", "nucleus",
    "electromagnetic radiation", "Planck", "photoelectric effect",
    "Rydberg", "Bohr", "energy level", "de Broglie", "Heisenberg",
    "orbital", "quantum number", "Aufbau", "Pauli", "Hund",
    "electronic configuration"
  ],
  "known_pitfalls": [
    {
      "claim": "Helium is a p-block element because it is in Group 18",
      "correction": "Helium's electronic configuration is 1s², so by subshell it is s-block. It sits in Group 18 with noble gases because its valence shell is complete and its chemical behaviour resembles theirs, not because of its block."
    },
    {
      "claim": "Electrons orbit the nucleus in fixed circular paths (stated as final fact)",
      "correction": "This is only true within the Bohr model. The modern quantum-mechanical model describes electrons via orbitals — 3-D probability regions — not fixed circular orbits."
    }
  ],
  "recommended_example_progression": [
    "L1: Identify particles (protons/neutrons/electrons) from given counts",
    "L2: Ion formation (e.g. 12 protons, 10 electrons → cation identity + charge)",
    "L3: Isotopes comparison (e.g. Cl-35 vs Cl-37)",
    "L4: Quantum number validity checks",
    "L5: Electronic configuration incl. ions (e.g. Fe, Fe2+)",
    "L6: Spectral calculations using c = νλ",
    "L7: de Broglie / Bohr model hydrogen-like species calculations"
  ]
}
```

This manifest is the single most important artifact to build. It doubles as:
- Ground truth for a deterministic contamination/completeness check (Phase 1).
- A grounding context to inject into both the live lesson-generation prompt
  and the Lesson Repair prompt (Phase 3), so the LLM is told explicitly what
  is and isn't allowed.
- A human-reviewable spec that subject experts can maintain independently of
  code.

**Coverage plan:** author manifests chapter-by-chapter, prioritised by
exam weight (Physics/Chemistry/Maths/Biology core NCERT chapters first for
Grades 11–12, then Grade 9–10 Science/Maths, then humanities/languages).

### Phase 1 — New audit: "Curriculum Boundary & Accuracy Audit"

Add as tool #7 in the Platform QA Center (`admin_qa.py` + a new
`backend/scripts/audit_chapter_boundary.py`), two tiers:

**Tier A — Deterministic (free, fast, run on every chapter with a manifest):**
- For each cached lesson matching a manifest's `(grade, subject, chapter)`:
  - Flag if any `banned_topics` phrase/keyword appears in the content
    (contamination detection — would have caught density/STP/thermodynamics
    instantly).
  - Flag if fewer than N% of `must_include_keywords` are present (coverage
    gap detection — would have caught the missing Bohr/quantum-number content).
  - Flag any `known_pitfalls.claim` pattern found verbatim/near-verbatim in
    the content (catches the helium p-block error class of mistake).
- Cheap enough to run on every lesson, every deploy, as a CI-style gate.

**Tier B — LLM-as-subject-expert review (admin-triggered, costs tokens):**
- Modeled directly on the rubric the user used in the original manual
  review (see Appendix A): student-friendly language, scientific accuracy,
  chapter relevance, sequencing/coherence, worked examples, exam-prep value.
- Prompt = lesson content + the chapter manifest + explicit rubric →
  returns structured JSON findings (severity, category, message, suggested
  fix), not just a score.
- Stored per chapter and surfaced in the admin QA dashboard next to the
  existing Lesson Quality scores, as a new "Curriculum Accuracy" column.

### Phase 2 — Triage all Grade 9–12 chapters

1. Run Tier A (deterministic) across every chapter that has a manifest.
2. For high-exam-weight subjects (Physics, Chemistry, Biology, Maths) in
   Grades 11–12, and Science/Maths in Grades 9–10, prioritise manifest
   authoring + Tier A scan first.
3. Produce a prioritised defect list (critical: chapter contamination or
   scientific errors; high: major syllabus gaps; medium: pedagogy/sequencing;
   low: cosmetic) exactly like the severity buckets already used by the
   existing Lesson Sections/Quality audits, so it slots into the same
   dashboard UX.

### Phase 3 — Remediation (two tracks, both human-approved before publish)

**Track A — Manual/human-authored content injection (the "Q&A JSON"-style
approach the user asked for):**
- For chapters flagged critical (Structure of Atom first), a subject
  expert authors corrected step-by-step lesson content directly (using the
  manifest's `recommended_example_progression` as the structure).
- Inject it via the existing `chatgpt_lesson_helper.py store` workflow (or a
  small new script `seed_manual_lesson_content.py` that reads a JSON file
  of `{grade, subject, chapter, step_title, content}` entries and calls
  `store_lesson_cache()` directly) — bypassing LLM generation entirely for
  that step, guaranteeing a vetted, syllabus-correct version.
- This is the most direct equivalent of "the way we did it for Q&A in JSON
  files" — a JSON (or set of JSON files) becomes the source of truth for
  specific steps/chapters that are too important or too broken to trust to
  live generation.

**Track B — Constrained LLM repair (scales cheaper for medium-severity fixes):**
- Extend `lesson_repair_service.py`'s `_REPAIR_SYSTEM_PROMPT` /
  `_REPAIR_USER_TEMPLATE` to accept the chapter manifest as a hard
  constraint block: "ONLY use these in-scope units. NEVER mention these
  banned topics. MUST include these keywords somewhere in the lesson."
- Run existing repair pipeline (LLM rewrite → `validate_repaired_draft()` →
  admin review → `publish_repaired_task()`), now also validated against
  Tier A manifest checks before being marked `ready_for_review`.
- Good for medium-severity, high-volume fixes (e.g. missing real-world
  context, weak "quick check" feedback) across many chapters at once.

### Phase 4 — Prevent regression (fix the generation pipeline itself)

- Inject the chapter manifest (`in_scope_units` + `banned_topics` +
  `must_include_keywords`) into the **live** `TUTOR_SYSTEM` prompt whenever
  a manifest exists for that chapter, so newly-generated (non-cached) steps
  are scoped correctly from the start, not just repaired after the fact.
- Add Tier A deterministic checks as a **pre-publish gate** in
  `prewarm_service.py` — if a freshly generated lesson trips a `banned_topics`
  or missing-keyword check, don't cache it as `active`; mark it
  `needs_review` (mirroring the `question_bank` table's existing
  `needs_review` status pattern) instead of silently serving it to students.

### Phase 5 — Answer-and-feedback completeness for "Quick Check" questions

- The user's review flagged quiz-style questions with no answer/explanation/
  misconception feedback. The 8-section schema *already* requires
  `quick_check_question: {question, answer, explanation}` structurally
  (see `lesson_repair_service.py` `REPAIR_MIN_WORDS` and
  `validate_repaired_draft()` which checks for missing `question`/`answer`
  keys). The gap is that **live-generated** (non-repaired) lessons are not
  currently held to this same structural bar — only lessons that go through
  the repair pipeline are validated this strictly. Recommendation: run the
  Lesson Sections Audit's `quick_check` structural check (already exists)
  as a blocking gate at prewarm time too, not just as a reporting audit.

---

## 4a. Phase 0 Pilot — COMPLETED (proof of concept validated)

**Status as of this update: Phase 0 pilot done for Grade 11 Chemistry —
Structure of Atom, and the results confirm the manifest + Tier A approach
works exactly as designed.**

What was built:
1. **Source PDF located and extracted word-by-word** (per Condition 7):
   `~/Desktop/cbse_ncert_pdfs/Grade_11/Chemistry/kech102.pdf` (NCERT Unit 2 —
   Structure of Atom). Full text was read directly from the PDF, not
   paraphrased or reconstructed from memory.
2. **Chapter manifest authored and saved**:
   `backend/app/data/chapter_manifests/grade_11/chemistry/structure_of_atom.json`
   — contains `in_scope_units` (6 NCERT sub-units, 2.1–2.6), `banned_topics`
   (9 out-of-chapter topics), `must_include_keywords` (22 core terms),
   `known_pitfalls` (3 patterns matching the user's original review:
   helium/p-block, "electrons orbit in fixed paths" stated as final fact,
   the broken nitrogen/STP example), and a `recommended_example_progression`
   citing actual NCERT end-of-chapter problem numbers (2.1–2.67) rather than
   invented numbers.
3. **Tier A deterministic audit script built and run**:
   `backend/scripts/audit_chapter_boundary.py` — loads manifests, connects to
   the live Supabase `lesson_cache` via `get_content_db()`, and scans cached
   lesson content for contamination / coverage gaps / known pitfalls.

**Actual audit run output** (against the real, currently-live lesson —
5 cached steps: Concept introduction, Core explanation, Worked examples,
Exam-style problems, Revision and recap):

- **24 critical findings, 0 false starts** — every single issue flagged by
  Tier A corresponds to a real problem in the original manual review:
  - Contamination hits for density/STP/percentage-composition (Some Basic
    Concepts of Chemistry), analytical balances / mass-vs-weight lab
    discussion, s/p/d/f-block classification and periodic-history topics
    (Classification of Elements chapter).
  - Coverage-gap findings of **91–100% missing required syllabus
    keywords** in every single step — confirming the chapter is "closer to
    a brief introduction than a complete chapter" exactly as the user's
    review concluded.
  - Known-pitfall hits for the helium/p-block claim (2 of 5 steps), the
    "electrons orbit in fixed circular paths" claim, and the broken
    nitrogen/STP percentage example.
- Full machine-readable report saved to
  `backend/reports/chapter_boundary/chapter_boundary_report.json`.

**Conclusion: the manifest-driven Tier A audit is validated as a working,
zero-LLM, zero-cost detector for exactly the class of problems identified in
the original manual review.** This de-risks Phase 1 (wiring Tier A into the
admin QA Center) and Phase 2 (scaling manifests to more chapters).

**UPDATE — Track A remediation also COMPLETED for this pilot chapter:**

1. Built `backend/scripts/seed_manual_lesson_content.py` — authors
   corrected, NCERT-grounded content for all 5 lesson steps (Concept
   introduction, Core explanation, Worked examples, Exam-style problems,
   Revision and recap), matching the platform's exact 8-subsection markdown
   template. Every worked example/quick-check cites a real NCERT problem
   number (2.1–2.6 etc.) — nothing invented. The known pitfalls (helium/
   p-block, "electrons orbit in fixed paths", broken nitrogen/STP example)
   are explicitly corrected in the "Common mistake" sections rather than
   repeated.
2. Ran the script live (`--force`) — successfully overwrote all 5
   `lesson_cache` rows for this chapter (source_type = "MANUAL"), bypassing
   LLM generation entirely per the Track A design.
3. **Fixed two false-positive bugs discovered in `audit_chapter_boundary.py`
   during re-validation** (an important process learning):
   - *Contamination check* originally fired on partial keyword overlap
     (e.g. "mass" alone triggering "density calculation"). Fixed to require
     ALL of a banned topic's significant words to co-occur, with an
     expanded stop-word list to exclude generic terms.
   - *Coverage-gap check* originally ran per-step, which is wrong — no
     single step should be expected to mention all 22 chapter keywords.
     Fixed to check keyword coverage across the WHOLE chapter (all steps
     combined) instead.
   - *Known-pitfall check* was flagging our own corrected explanations
     (e.g. "this is only true within the Bohr model...") as repeats of the
     mistake, because the correction text shares vocabulary with the claim
     it corrects. Fixed with a sentence-level heuristic that distinguishes
     "claim being asserted" from "claim being corrected."
4. **Re-ran the audit after both the content fix and the script fix**:
   `python3 scripts/audit_chapter_boundary.py --grade "Grade 11" --subject
   Chemistry --chapter "Structure of Atom"` →
   **0 critical findings, 0 high findings across all 5 steps.**

**This chapter is now fully remediated end-to-end and serves as the
reference implementation for the whole plan.** The full cycle — detect
(Tier A) → author corrected content grounded in the source PDF (Track A) →
inject directly into `lesson_cache` → re-audit to confirm clean — is proven
and repeatable.

**Immediate next steps (not yet done):**
- Wire `audit_chapter_boundary.py` into `admin_qa.py` as tool #7 (Phase 1)
  so this becomes a self-service admin dashboard job instead of a manual
  script run, and add it as a CI-style regression gate so this chapter
  cannot silently regress if it is ever re-generated live.
- Author manifests for the next highest-priority chapters (see Phase 2
  prioritisation) using the same word-by-word PDF extraction method, then
  run the same detect → author → inject → re-audit cycle for each.
- Consider batching: since the Tier A script and seed-script pattern are
  now proven, subsequent chapters should go faster — the main remaining
  manual-equivalent work per chapter is (a) extracting/reading the source
  PDF, (b) authoring the manifest, and (c) authoring corrected content
  (which can be sourced via the user's GPT-5.5 session per Condition 3 and
  then formatted into the same 8-subsection template used here).

---

## 4b. Design decision: should ALL lessons become static/polished content?

**Short answer: no — full static content for every Grade/Subject/Chapter/Step
does not scale within Condition 1 ("automate with limited manual review"),
and it is not necessary. The recommended target architecture is a
three-tier hybrid, not a full switch to static content.**

### Why "static everything" doesn't work
Grades 9–12 × ~10 subjects × ~15–20 chapters each × ~5 steps per chapter is
roughly **3,000–4,000 individual lesson entries**. Manually authoring and
verifying all of them (even with GPT-5.5 assistance per Condition 3) is a
huge, ongoing maintenance burden — every syllabus revision, every NCERT
textbook edition change, every new exam pattern would require re-touching
thousands of entries by hand. This directly conflicts with Condition 1.

### Recommended target architecture: three tiers

**Tier 1 — Static "golden" content (small, curated set).**
Reserved for chapters that are:
- High-traffic (heavily used by students), AND/OR
- Proven high-risk by Tier A/B audits (repeated contamination, scientific
  errors, or severe syllabus gaps — like Structure of Atom was), AND/OR
- High-stakes for exams (board-exam-weighted core Physics/Chemistry/
  Biology/Maths chapters in Grades 11–12).

These get the Track A treatment we just did: manifest → corrected content →
inject as `source_type = "MANUAL"` → protect from regeneration (see gap
below). This is intentionally a **small, hand-picked subset**, not "all
content" — probably 50–150 chapters platform-wide at full maturity, not
thousands of individual steps.

**Tier 2 — Constrained live generation (the default, for everything else).**
Most chapters stay on the existing live LLM + RAG pipeline
(`tutor_service.py`, `prewarm_service.py`), but **once a manifest exists for
a chapter**, it is injected into the generation prompt as a hard constraint
block (this is Phase 4, "Prevent regression," already in the plan above):
"ONLY use these in-scope units. NEVER mention these banned topics. MUST
include these keywords." This scales because writing a manifest (structured
facts + boundaries) is far cheaper than writing full polished lesson prose,
and one manifest constrains generation for that chapter indefinitely,
across every future regeneration.

**Tier 3 — Automated gating (applies to both Tier 1 and Tier 2).**
Tier A checks (`audit_chapter_boundary.py`) run automatically before any
lesson — freshly generated or cached — is marked "active" and served to
students. A lesson that fails is marked `needs_review` (mirroring the
existing `question_bank` status pattern) instead of silently reaching
students. This is the safety net that catches drift even in Tier 2 content
where no human has manually verified every word.

### A real gap this pilot exposed: MANUAL content has no protection today

While building this pilot, we found that `lesson_cache_service.py` has two
existing operations that would **silently destroy** a Tier 1 "golden"
manual fix:

- `invalidate_cache_for_chapter()` — sets `status = "stale"` for every row
  matching `(board, grade, subject, chapter)`, with **no filter on
  `source_type`**. This runs automatically whenever new RAG content is
  uploaded for a chapter.
- `archive_lesson_cache_for_grade()` — archives every row with
  `status in ("active", "stale")` for a grade, again with no `source_type`
  filter, when an admin clicks "Clear Lessons."

Both of these would catch our `source_type = "MANUAL"` rows exactly like
any live-generated row, silently regenerating them from the LLM on next
request and **undoing the fix** without any warning.

**Recommended fix (not yet implemented — next actionable item):**
Add a `protected: boolean` column (or reuse `source_type == "MANUAL"` as
the protection flag) to `lesson_cache`, and update both
`invalidate_cache_for_chapter()` and `archive_lesson_cache_for_grade()` to
skip rows where `source_type = "MANUAL"` unless an explicit
`force_include_manual=True` override is passed. This should be done before
scaling Tier 1 content to more chapters, otherwise every "golden" fix is
at risk of being silently reverted by unrelated admin/RAG operations.

### Summary answer to "will lesson retrieval become fully static?"

No — the end state should be: a **small, protected set of static/manual
"golden" chapters** (Tier 1) for the highest-risk/highest-stakes content,
layered on top of a **manifest-constrained live generation pipeline**
(Tier 2) for everything else, both continuously checked by an
**automated Tier A gate** (Tier 3). This gives quality where it matters
most while staying consistent with the "automate with limited manual
review" goal — full static content for all Grades and subjects would be
neither achievable nor maintainable at this scale.

---

## 4c. Best automated approach to correct ALL chapters, Grade 9–12 (full-scale design)

The pilot proved the mechanics work, but doing full manual Track A (author
+ inject full lesson content) for every one of ~600–800 chapters across
Grades 9–12 does not scale and conflicts with Condition 1. The pilot also
showed where the real manual bottleneck is: **not the audit, not the
injection — it's reading the PDF and authoring the manifest/content**.

The best automated approach is a **4-stage pipeline** that keeps manual
effort at the two narrowest possible points (manifest sign-off and a small
set of "golden" chapters), and automates everything else, including the
repair itself via the LLM (paid-tier only, per Condition 4).

### Stage 1 — Bulk, semi-automated manifest generation (biggest scale win)

Build `backend/scripts/generate_chapter_manifests.py`:
1. For every `(grade, subject, chapter)` in the syllabus
   (`seed_grade1112_syllabus_overrides.py` for 11–12, existing syllabus
   data for 9–10), locate the source NCERT PDF chapter file
   (`~/Desktop/cbse_ncert_pdfs/...` for 11–12, `RAG DB/` for 9–10 — both
   already exist locally).
2. Extract the PDF's full text programmatically (reuse the same
   `pdfplumber`/extraction approach already used in
   `audit_ncert_vs_platform.py` and the RAG upload scripts).
3. Feed the extracted text to a **paid-tier LLM** (per Condition 4) with a
   structured-output prompt that asks it to propose:
   `in_scope_units`, `must_include_keywords`, and a first-pass
   `recommended_example_progression` citing real end-of-chapter problem
   numbers found in the text — **not** `banned_topics` (see next point).
4. **Auto-derive `banned_topics` without any LLM call** — this is the key
   insight from the pilot: banned topics are just the `in_scope_units` of
   *adjacent* chapters in the same subject/grade (e.g. Structure of Atom's
   banned list = the in-scope units of "Some Basic Concepts of Chemistry,"
   "Classification of Elements," and "Thermodynamics" — all sibling
   chapters). Once even a few chapters in a subject have manifests, this
   list-comparison step is 100% deterministic and free.
5. Write the draft manifest JSON to `chapter_manifests/<grade>/<subject>/`
   with `"manifest_status": "draft_needs_review"`.
6. **Human/GPT-5.5 checkpoint (Condition 3)**: the user skims each draft
   manifest (a few minutes per chapter, not hours) and either approves it
   (`manifest_status: "approved"`) or corrects specific fields. This is the
   ONE deliberately-kept manual step — reviewing a ~1-page structured JSON
   is far faster than reviewing full lesson prose.

This turns "read + author a manifest for 600 chapters" from a multi-week
manual effort into a batch job + a lightweight review pass.

### Stage 2 — Bulk Tier A audit across everything (already built, just needs scaling)

Extend `audit_chapter_boundary.py` (already exists) with a `--all`
flag that loops over every approved manifest and every matching
`lesson_cache` chapter, producing one consolidated report — this requires
no new logic, just removing the single-chapter filter and adding
pagination/rate-limiting for hundreds of DB queries. Output: a ranked list
of every chapter by severity (critical contamination / coverage gaps /
known pitfalls), exactly the "Structure of Atom" report we already
produced, but for the whole platform at once.

### Stage 3 — Automated repair at scale via Track B (Constrained LLM repair)

This is the actual "correct all chapters" engine — it reuses the existing,
already-built `lesson_repair_service.py` (admin-triggered LLM rewrite +
`validate_repaired_draft()` + admin-approval gate), with one addition:

- Extend `_REPAIR_USER_TEMPLATE` to accept and inject the chapter's
  manifest as a hard constraint block: *"ONLY use these in-scope units:
  {in_scope_units}. NEVER mention or reference these topics: {banned_topics}.
  Your content MUST include these terms somewhere: {must_include_keywords}.
  Known pitfalls to explicitly avoid: {known_pitfalls}."*
- Extend the repair validation step to also run the (already-built) Tier A
  checks (`check_contamination`, `check_coverage_gap_for_chapter`,
  `check_known_pitfalls`) against the LLM's repaired draft — a repair that
  still contaminates or omits keywords is rejected automatically and
  retried or flagged, before it ever reaches `ready_for_review`.
- Run this in **bulk mode** across every chapter flagged critical/high by
  Stage 2 — the existing `admin_qa.py` job-queue pattern (`_JOBS` dict,
  background thread) already supports this; it just needs a "run for N
  chapters" loop instead of one chapter at a time.
- **This must use a paid-tier LLM** (Condition 4) — cost is the real
  constraint here, not engineering effort. Estimate: at ~2,000–4,000 tokens
  per repair call × 5 steps × several hundred chapters, this is a bounded,
  one-time, budgetable cost — far cheaper than manually authoring content.
- Every repaired draft still requires **admin approval before publish**
  (`publish_repaired_task()`) — this is not fully autonomous, by design,
  matching Condition 1's "limited manual review," but the review burden is
  now "approve/reject a diff" per chapter, not "write the chapter."

### Stage 4 — Promote only the worst/highest-stakes chapters to Tier 1 (manual, small set)

After Stage 3, most chapters will pass Tier A cleanly via automated
repair. Reserve full manual Track A (what we did for Structure of Atom)
only for:
- Chapters where automated repair still fails Tier A after 2–3 retries
  (LLM couldn't reliably follow the constraints — rare but possible for
  very content-dense chapters).
- The highest-exam-weight chapters platform-wide (e.g. board-critical
  Physics/Chemistry/Biology/Maths chapters in Grades 11–12), where the
  extra assurance of hand-verified content is worth the one-time cost.

This keeps the fully-manual tier small (tens, not hundreds, of chapters)
while still guaranteeing every chapter on the platform has passed at least
the automated Tier A gate.

### Stage 5 — Prevent regression (apply to everything, automatically)

Once manifests exist platform-wide (Stage 1), inject them into the live
`TUTOR_SYSTEM` generation prompt (Phase 4, already in this plan) so that
any future cache miss or regeneration is scoped correctly from the start —
this is the mechanism that keeps hundreds of chapters correct
*indefinitely* without repeating Stages 2–4 every time content drifts.

### Why this is "the best automated approach" given the constraints

| Constraint | How this pipeline satisfies it |
|---|---|
| Condition 1 — automate with limited manual review | Only 2 manual checkpoints: (a) manifest sign-off (~minutes/chapter, not hours), (b) approve/reject repaired diffs (not write-from-scratch) |
| Condition 4 — no free-tier LLM | Manifest generation (Stage 1) and repair (Stage 3) both explicitly required to use a paid-tier model only |
| Condition 5 — respect existing RAG content | Stage 1 extracts from the same NCERT PDFs already backing RAG; Stage 3's repair prompt still uses RAG-retrieved chunks as grounding, just with added manifest constraints |
| Condition 6 — asymmetric augmentation policy | Manifest generation prompt for Science/Maths may allow the LLM to reference standard external facts; for humanities/languages the prompt is restricted to NCERT-only content, matching the existing per-subject rule |
| Condition 7/8 — PDF-grounded, no invented facts | Stage 1's manifest-generation prompt is fed the actual extracted PDF text, not asked to recall from training data — this mirrors exactly what was done manually for the Structure of Atom pilot |
| Scale (600–800 chapters) | Stages 1–3 are fully batchable background jobs using the existing `admin_qa.py` job-queue pattern; only Stage 4 (a small "golden" subset) requires the full manual-authoring effort demonstrated in the pilot |
| Cost control | Bulk LLM calls (Stages 1 and 3) are one-time, budgetable, and far cheaper than manually authoring ~4,000 lesson entries; ongoing cost after rollout is near-zero because Stage 5 (manifest-constrained live generation) prevents most future regressions without new LLM repair calls |

### Recommended execution order for "correct all Grade 9–12 chapters"

1. **Finish wiring `audit_chapter_boundary.py` into `admin_qa.py`** as tool
   #7 (this was already the "immediate next step" from the pilot) — needed
   before Stage 2 can run at scale via the dashboard.
2. **Build and run Stage 1** (`generate_chapter_manifests.py`) for the
   highest-exam-weight subjects first: Grade 11–12 Physics, Chemistry,
   Biology, Mathematics — the same subjects most likely to have the
   RAG-chunk-blending problem, per the root-cause analysis in §3.
3. **Run Stage 2** (bulk Tier A audit) across those manifests to get a
   ranked defect list — this replaces guesswork about "which chapters need
   fixing" with hard data, exactly like the 24-critical-findings report we
   got for Structure of Atom, but platform-wide.
4. **Run Stage 3** (bulk constrained LLM repair) against every
   critical/high chapter from the ranked list, in batches, with admin
   approval as the review gate.
5. **Manually promote to Tier 1** only the small subset that fails Stage 3
   repeatedly or is judged too high-stakes to leave to automated repair.
6. **Extend Stage 1–3 to Grade 9–10 Science/Maths**, then to Grade 11–12
   non-Science/Maths subjects (Economics, Business Studies, Accountancy,
   History, Geography, Political Science, English, Hindi) — applying the
   Condition 6 augmentation rule so humanities/languages manifests and any
   repairs stay strictly NCERT-grounded.
7. **Turn on Stage 5** (manifest-injection into the live generation prompt)
   platform-wide once manifests are stable, so newly-generated content for
   any chapter — remediated or not yet remediated — is scoped correctly
   from that point forward.

This is the most automation-heavy path consistent with every stated
condition: it fixes the fleet of chapters using two lightweight human
checkpoints instead of thousands of individually hand-written lessons,
while still guaranteeing (via Tier A gating) that nothing reaches students
without at least a deterministic quality check having passed.

---

## 4d. Progress checkpoint — "how do we proceed on this?" (current status)

**Step 1 of the execution order (§4c) is DONE:** `audit_chapter_boundary.py`
is now wired into `admin_qa.py` as tool #7. Concretely:

- Added to `backend/app/routes/admin_qa.py`:
  `GET /api/admin/qa/chapter-boundary/latest`,
  `GET /api/admin/qa/chapter-boundary/history`,
  `POST /api/admin/qa/chapter-boundary/run` (optional `grade`/`subject`/
  `chapter` query params — omit all three to audit every manifest at
  once),
  `GET /api/admin/qa/chapter-boundary/status/{job_id}`,
  `GET /api/admin/qa/chapter-boundary/report`.
- Follows the exact same job-queue pattern as the other 6 tools
  (`_CHAPTER_BOUNDARY_JOBS` in-memory dict, background thread, JSON
  report) — no new architecture introduced.
- The router (`admin_qa_router`) is already mounted at `/api/admin/qa` in
  `backend/app/main.py`, so these new routes are live immediately with no
  further registration needed.
- Verified: Python syntax check passes; no duplicate route definitions.

**What this unlocks right now:** an admin can call
`POST /api/admin/qa/chapter-boundary/run` with no parameters to run Tier A
against every manifest currently in
`backend/app/data/chapter_manifests/` (today: just the one Structure of
Atom manifest) and see the ranked report via
`GET /api/admin/qa/chapter-boundary/latest`. As more manifests are added
(Stage 1), this same endpoint scales to audit the whole platform with zero
additional code changes.

### Immediate next action (Stage 1 of §4c — build the manifest generator)

The single highest-leverage next step is building
`backend/scripts/generate_chapter_manifests.py` (Stage 1 in §4c) — this is
what turns "one manifest, one chapter" into "hundreds of manifests,
automatically." Concretely, that script needs to:

1. Load the full Grade 9–12 chapter list (reuse
   `seed_grade1112_syllabus_overrides.py`'s `CHAPTER_OVERRIDES` for 11–12;
   locate/extend the equivalent syllabus source for 9–10).
2. For each chapter, locate its already-downloaded source PDF (the same
   `~/Desktop/cbse_ncert_pdfs/` structure used for the pilot) and extract
   full text (reuse `pdfplumber` logic already present in
   `audit_ncert_vs_platform.py`).
3. Call a **paid-tier LLM** (per Condition 4) with the extracted text to
   propose `in_scope_units`, `must_include_keywords`, and
   `recommended_example_progression` — mirroring exactly the manual
   process used for the Structure of Atom pilot manifest, just automated.
4. Auto-derive `banned_topics` by diffing against sibling chapters'
   `in_scope_units` within the same subject/grade (no LLM call needed for
   this part — pure list comparison, as described in Stage 1 of §4c).
5. Write each draft manifest to
   `chapter_manifests/<grade>/<subject>/<chapter_slug>.json` with
   `"manifest_status": "draft_needs_review"`.

Once this script exists, the very next action is to run it for the
highest-priority subject/grade combinations (Grade 11–12
Physics/Chemistry/Biology/Mathematics first), do a quick manifest
sign-off pass, then run the newly-wired
`POST /api/admin/qa/chapter-boundary/run` endpoint to get the first
platform-wide ranked defect report — the same kind of report we manually
produced for Structure of Atom, but for every chapter with a manifest, in
one call.

**Suggested order for the next session:**
1. Build `generate_chapter_manifests.py` (Stage 1).
2. Run it for Grade 11–12 Chemistry (all chapters) as a second pilot —
   validates the automation works across a whole subject, not just one
   chapter.
3. Manifest sign-off pass (quick review, not full authoring).
4. Run `chapter-boundary/run` with `subject=Chemistry` to get the ranked
   defect list for the whole subject.
5. Decide, chapter by chapter, whether each critical/high finding goes to
   Track B (automated LLM repair, Stage 3) or is promoted to Track A/Tier 1
   (manual, like Structure of Atom) — using the severity + exam-weight
   criteria from Stage 4 of §4c.
6. Once Chemistry is fully triaged, repeat Stages 1–4 for Physics,
   Biology, Mathematics, then Grade 9–10 Science/Maths, then humanities/
   languages (respecting Condition 6's asymmetric augmentation rule).

---

## 4e. Pilot #2 — Grade 9 Science, Chapter 2: "Cell: The Building Block of Life"
### COMPLETED — reveals a NEW defect pattern Tier A did/did not catch

Per user request, a second pilot chapter was run end-to-end (detect →
manifest → audit → remediate → re-audit) to test the process against a
chapter that is **not** contaminated with other-chapter content (unlike
Structure of Atom), to see what other kinds of defects exist platform-wide.

**What was built:**
1. Source PDF located and extracted word-by-word:
   `RAG DB/Science/iesc102.pdf` (NCERT Grade 9 Science Exploration series,
   Chapter 2).
2. Manifest authored:
   `backend/app/data/chapter_manifests/grade_9/science/cell_the_building_block_of_life.json`
   — `in_scope_units` covering all 5 real NCERT sub-sections (2.1 how to
   study cells, 2.2 membrane/wall/osmosis, 2.3 organelles, 2.4 cell
   division, 2.5 Cell Theory), `must_include_keywords` (32 terms spanning
   the whole chapter, not just cell division), and `known_pitfalls`
   describing the specific defects found by manual review (see below).

**BEFORE state (manual review of the live content, since this is a NEW
defect class Tier A's existing checks were not designed to catch):**

Unlike Structure of Atom, this chapter had **no cross-chapter
contamination** — all content was topically about cells. However, manual
inspection revealed a different problem: **severe "syllabus tunnel
vision."** 4 of the 5 lesson steps (Worked examples, Exam-style problems,
Revision and recap, and Core explanation) were almost entirely about
mitosis/meiosis and cell division, while:
- The cell membrane, fluid-mosaic model, and osmosis (NCERT section
  2.2, with a full dedicated experiment, Activity 2.2) received almost no
  coverage.
- The cell wall (section 2.2.2) was essentially unmentioned.
- Section 2.3.1 — individually describing the nucleus, ribosomes, ER
  (RER/SER), Golgi apparatus, lysosomes, mitochondria, plastids, and
  vacuoles — is the single LARGEST section in the real NCERT chapter, yet
  had almost no dedicated coverage in the lesson content.
- One lesson step ("Core explanation") contained a **fabricated numeric
  worked example** — a scenario about a skin cell of a specific diameter
  dividing every exact hour, used to compute 2^5 = 32 cells. This exact
  scenario does not exist anywhere in the NCERT source text, violating
  Condition 7/8 (no invented facts/examples). NCERT's own worked examples
  for this chapter are the onion-cell-size estimation (Activity 2.1) and
  the potato osmosis experiment (Activity 2.2) — neither of these NCERT
  activities appeared anywhere in the original content.

**Tier A audit run against this BEFORE content:**
```
python3 scripts/audit_chapter_boundary.py --grade "Grade 9" --subject Science \
  --chapter "Chapter 2: Cell: The Building Block of Life"
-> 0 critical findings, 1 HIGH finding: "48% of required syllabus keywords
   are missing across the WHOLE chapter (all steps combined)."
```

**Important process learning — Tier A's blind spot confirmed:** Tier A's
`check_contamination` and `check_known_pitfalls` checks correctly reported
**zero** findings, because there was no banned-topic phrase to match and
no *previously known* pitfall pattern registered yet (the fabricated
worked-example pitfall was only added to the manifest *after* manual
review discovered it — Tier A cannot discover *new* problems on its own,
only check for problems a human/manifest has already told it to look
for). Only the **coverage-gap** check (which is purely mechanical keyword
counting) caught anything — and it correctly flagged the 48% gap as HIGH
severity. This confirms a key limitation documented in §4c: **Tier A is a
deterministic checklist, not a substitute for a human/Tier-B review that
can notice things like "this chapter is unbalanced" or "this example is
invented" for the first time.** Every chapter's first pass still benefits
from a manual/Tier-B read-through to seed the manifest's `known_pitfalls`
and `banned_topics` — after that, Tier A can catch recurrences cheaply
forever.

**Remediation (Track A):**
- Built `backend/scripts/seed_manual_lesson_content_g9_cell.py` —
  corrected, NCERT-grounded content for all 5 steps, rebalanced so that
  each of the 5 real NCERT sections gets its own dedicated step:
  Concept introduction (microscopy/resolution/Hooke), Core explanation
  (cell membrane, cell wall, osmosis, Activity 2.2 potato experiment),
  Worked examples (all 8 organelles individually, matching-function
  exercise), Exam-style problems (prokaryotic vs eukaryotic, mitosis vs
  meiosis at NCERT's conceptual level, Cell Theory), Revision and recap
  (full-chapter summary tying all sections together).
- Every worked example/quick-check now cites a real NCERT activity or
  end-of-chapter question (Activity 2.1 cell-size estimation, Activity
  2.2 potato osmosis, organelle-function matching from Q3, bacterial vs
  animal cell structure table from Q9) — the fabricated skin-cell example
  was removed entirely.
- Ran live (`--force`) — all 5 rows updated, `source_type = "MANUAL"`.

**Re-audit after remediation:**
```
-> 0 critical findings, 0 high findings across all 5 steps.
```
The 48% coverage gap dropped to 0% because keyword coverage is now spread
across the whole chapter instead of concentrated in one topic area.

**Key takeaway for scaling (Stage 1 of §4c):** when building
`generate_chapter_manifests.py`, the automated manifest-generation prompt
should explicitly ask the LLM to check that `must_include_keywords`
represent **every major section heading** of the source PDF (not just
whichever topic the existing lesson happens to emphasise), specifically
to catch this "tunnel vision" pattern automatically at manifest-creation
time, before a human even has to notice it manually — this makes pilot
#2's manual-discovery step something Stage 1 can bake in from the start
for every future chapter.

---

## 4f. GPT-5.5 chapter-authoring prompt + ingestion pipeline — BUILT

Per Condition 3 (the user runs a GPT-5.5 chat session to retrieve
supplementary content), a **reusable, machine-processable prompt** was
built so this workflow no longer requires custom hand-authoring per
chapter (as was done manually for the two pilots above).

**New artifacts:**
- `docs/GPT55_CHAPTER_AUTHORING_PROMPT.md` — the full copy-pasteable
  prompt template. It bakes in every Binding Rule this plan requires:
  strict PDF grounding, no fabricated numeric examples, chapter-boundary
  discipline, full-coverage/no-tunnel-vision (directly encoding the §4e
  learning), mandatory answered quick-checks, and the `SUBJECT_CLASS`
  toggle that enforces Condition 6's asymmetric augmentation rule
  (science/maths may use standard external facts; humanities/languages
  must stay strictly NCERT-only).
- The prompt's output schema is **strict JSON**: one `manifest` object
  (same shape as the two pilot manifests) plus one `lessons` object with
  all 5 step keys, each an 8-subsection markdown string.
- `backend/scripts/ingest_gpt55_chapter_output.py` — validates the JSON
  schema (rejects missing keys, too-short content, or malformed JSON with
  a clear error and non-zero exit code), writes the manifest file, seeds
  all 5 lesson steps into `lesson_cache` via the same
  `make_lesson_cache_key()`/`store_lesson_cache()` mechanism used by the
  two pilot seed scripts, and **automatically re-runs the Tier A audit**
  for that exact chapter so the user immediately sees pass/fail without a
  separate manual step.

**Verified working end-to-end** with both a valid synthetic payload
(dry-run confirmed correct manifest path derivation and all 5 lesson
steps parsed/would-be-stored) and a deliberately malformed payload
(correctly rejected with a clear "Manifest is missing required keys"
error and exit code 1).

**New workflow for any future chapter** (replaces the fully-manual
process used for the two pilots):
1. Copy the chapter's source PDF text.
2. Fill in the 5 placeholders in the prompt template and paste into
   GPT-5.5.
3. Save GPT-5.5's JSON response to `backend/gpt_output/<name>.json`.
4. Run `python3 scripts/ingest_gpt55_chapter_output.py --input
   gpt_output/<name>.json --force` — one command replaces what previously
   required a bespoke Python seed script per chapter.
5. Read the automatic Tier A audit output; if clean, done; if not, feed
   the findings back into another GPT-5.5 round or fix manually.

This closes the gap between "detect problems" (Tier A, built) and "author
fixes at scale" (previously fully manual) — the manual-authoring burden
per chapter is now: read PDF, run one prompt, save one file, run one
command. This is the concrete mechanism Stage 1 of §4c can build on when
automating manifest generation via a direct paid-tier API call instead
of a manual GPT-5.5 chat session, since the schema is already identical.

---

## 4g. Bulk prompt-preparation script — BUILT and RUN for Grade 9 Science

To make the GPT-5.5 workflow (§4f) usable for many chapters at once
without manually copying PDF text and filling in the template each time,
`backend/scripts/prepare_gpt55_prompts.py` was built and run for the
full Grade 9 Science subject (all 13 chapters).

**What it does:**
1. Reads the ordered chapter list for a grade/subject straight from
   `backend/app/data/syllabus.py` (`SYLLABUS["Grade 9"]["CBSE"]["Science"]`),
   so chapter names always match the platform's own syllabus data exactly.
2. Maps each chapter to its NCERT source PDF using the book-code +
   chapter-number convention already used elsewhere in the codebase
   (`iesc101.pdf` .. `iesc113.pdf` for Grade 9 Science, in
   `RAG DB/Science/`).
3. Extracts each PDF's full text with `pdfplumber` and fills it into the
   exact prompt template from `docs/GPT55_CHAPTER_AUTHORING_PROMPT.md`.
4. Writes one ready-to-paste `<NN>_<chapter_slug>_PROMPT.txt` file and
   copies the matching `<NN>_<chapter_slug>_source.pdf` alongside it, into
   a single local output folder.
5. Writes a `00_README_and_index.txt` with the exact next-step commands
   (paste into GPT-5.5 → save JSON → run `ingest_gpt55_chapter_output.py`)
   for every chapter.

**Run for Grade 9 Science — result:**
```
python3 scripts/prepare_gpt55_prompts.py --grade "Grade 9" --subject Science
```
Produced **27 files** (13 prompt `.txt` files + 13 source `.pdf` files +
1 README/index) in:
```
~/Downloads/GPT55_Prompts_grade_9_science/
```
covering all 13 Grade 9 Science chapters: Exploration (intro chapter),
Cell: The Building Block of Life, Tissues in Action, Describing Motion
Around Us, Exploring Mixtures and their Separation, How Forces Affect
Motion, Work Energy and Simple Machines, Journey Inside the Atom, Atomic
Foundations of Matter, Sound Waves, Reproduction, Patterns in Life
(Diversity and Classification), and Earth as a System.

The folder was opened in Finder for the user. This gives a fully
self-contained, offline-ready bundle: for each chapter, the user only
needs to open the `_PROMPT.txt`, copy its contents, paste into GPT-5.5,
save the JSON response, and run one ingestion command — no further PDF
handling, text extraction, or manual template-filling required.

**Reusability:** the same script works for any grade/subject already
configured in `BOOK_SOURCES` inside `prepare_gpt55_prompts.py`. Extending
to other Grade 9 subjects, or Grade 10–12, only requires adding one more
entry to that dict (PDF folder path, book code, chapter count, subject
class) — no other code changes needed.

---

## 4h. First real end-to-end GPT-5.5 run — VALIDATED (milestone)

The user took the `02_cell_the_building_block_of_life_PROMPT.txt` file
generated in §4g, pasted it into a real GPT-5.5 chat session, and
provided the resulting JSON output. This was ingested through the
pipeline built in §4f with **zero manual editing**:

```
python3 scripts/ingest_gpt55_chapter_output.py \
    --input gpt_output/grade9_science_cell_gpt_output.json --force
```

**Result:**
- Schema validation passed cleanly (all required manifest keys, all 5
  lesson steps present, all 7 required markdown headings present in every
  step).
- Manifest written to
  `backend/app/data/chapter_manifests/grade_9/science/cell_the_building_block_of_life.json`
  — **this overwrote the earlier hand-authored pilot manifest from §4e**,
  now replaced by GPT-5.5's own version (589–778 words per lesson step,
  broader `must_include_keywords` list of 47 terms vs the original 32,
  and 10 `known_pitfalls` vs the original 3 — GPT-5.5 proactively found
  additional misconceptions such as confusing magnification with
  resolution, and ribosomes being mistaken for membrane-bound organelles).
- All 5 lesson steps seeded into `lesson_cache` as `source_type =
  "MANUAL"`.
- **Automatic Tier A follow-up audit: 0 critical findings, 0 high
  findings across all 5 steps** — GPT-5.5's output passed cleanly on the
  first attempt, with no additional manual authoring, no retries, and no
  hand-fixing required.

**Why this is a milestone:** every previous "clean" result in this plan
(§4a Structure of Atom, §4e Cell pilot #2) required a human (me) to
manually write every word of the corrected lesson content. This is the
**first time the actual content-generation step was fully automated**
via a real paid-tier LLM call, with the only human involvement being:
(1) running `prepare_gpt55_prompts.py` once, (2) pasting the prompt into
GPT-5.5, (3) running one ingestion command. This validates the entire
§4c "best automated approach" thesis in practice, not just in design —
confirming that Stage 1 (manifest generation) and the equivalent of
Stage 3 (content generation) can both be satisfied by a single GPT-5.5
prompt/response cycle per chapter, with Tier A as the automated
pass/fail gate, exactly as designed.

**Immediate next step:** repeat this exact cycle (paste prompt → save
JSON → run ingest command) for the remaining 12 Grade 9 Science chapter
prompts already sitting in
`~/Downloads/GPT55_Prompts_grade_9_science/`, then move on to other
subjects/grades using `prepare_gpt55_prompts.py` with a new
`BOOK_SOURCES` entry.

---

## 4i. Critical bug found and fixed — stale `lesson_chapter_doc` cache layer bypassed the fix

After the §4h milestone, the user reported the corrected content was **not
appearing in the live app** — the UI still showed the old fabricated
content, AND the UI rendering itself had changed from the expected
step-by-step navigation (Previous/Next buttons, "Step X of 5") to a
single-scroll "Chapter Journey" layout with a left-side outline
("ON THIS CHAPTER: Concept introduction / Core explanation / ... / Wrap-up")
and no navigation buttons at all.

**Root cause — TWO separate issues, both now fixed:**

1. **Chapter-name mismatch created duplicate `lesson_cache` rows.**
   `prepare_gpt55_prompts.py` pulled the chapter name from `syllabus.py`
   (`"Cell: The Building Block of Life"`, no "Chapter 2:" prefix), but the
   live app's actual chapter selector uses `"Chapter 2: Cell: The Building
   Block of Life"` (with the prefix — the original naming convention
   already baked into the live cache). Since the cache key is a hash of
   the exact chapter string, this created a **second, disconnected set of
   `lesson_cache` rows** that the live app never queried, while the
   original ("Chapter 2:"-prefixed) rows — which WERE correctly updated in
   §4h — sat right there in the database.

2. **The real blocker: a separate, un-invalidated `lesson_chapter_doc`
   cache layer.** This is the actual reason the fix appeared invisible.
   The frontend (`LessonsPage.jsx`) has a newer rendering path — the
   "Chapter Journey" pilot (`CHAPTER_JOURNEY_PILOT_GRADES` includes Grade
   9) — which, before falling back to the classic step-by-step
   Previous/Next UI, first calls `GET /api/lesson/chapter-doc`. That
   endpoint (`chapter_doc_service.get_or_convert_chapter_doc()`) checks a
   **separate Supabase table, `lesson_chapter_doc`**, for a previously
   *stored, converted* single-document version of the whole chapter. If a
   stored doc already exists there, it is served directly and
   **`lesson_cache` is never re-read** — the conversion from step-markdown
   to structured JSON blocks only happens once and is then cached
   indefinitely in this second table.
   Because a `lesson_chapter_doc` row for this chapter had been built
   **before** our Track A/GPT-5.5 remediation, it was frozen with the old
   fabricated content, and updating `lesson_cache` alone had zero effect
   on what students actually saw — this doc-level cache silently shadowed
   every content fix made in §4a–§4h.

**Fix applied:**
- Deleted both stale `lesson_chapter_doc` rows (one for each of the two
  chapter-name variants) directly from Supabase.
- Verified via `get_or_convert_chapter_doc()` that reconversion from the
  current `lesson_cache` content now produces a clean 5-milestone document
  with **zero occurrences** of the previously fabricated content markers
  (`"30 micrometers"`, `"skin cell"`, `"Prophase"`, `"Metaphase"`,
  `"Anaphase"`, `"Telophase"`) — confirming the corrected GPT-5.5 content
  is now what will actually be served on next page load.

**Process learning — a new mandatory step for every future
Track A/GPT-5.5 content fix:** whenever `lesson_cache` rows are
overwritten (via `seed_manual_lesson_content*.py` or
`ingest_gpt55_chapter_output.py`), the corresponding `lesson_chapter_doc`
row(s) for that exact `(grade, subject, chapter, mode)` **must also be
deleted or invalidated**, otherwise the Chapter Journey UI will keep
serving the pre-fix converted document indefinitely. This should be
automated: `ingest_gpt55_chapter_output.py` and the seed scripts should
call `db.table("lesson_chapter_doc").delete().eq(...)` for the target
chapter immediately after writing to `lesson_cache`, so no fix is ever
silently shadowed by this second cache layer again. **This fix has not
yet been applied to the scripts — only manually run once for this one
chapter.** Adding it to the scripts is the immediate next action.

**Also clarified for the user — why the UI changed shape (not a bug):**
The single-scroll "Chapter Journey" layout (left outline: Concept
introduction → Core explanation → ... → Wrap-up, no Previous/Next
buttons) is the **intended, newer UI** for Grade 9 (and Grades 5-12) once
a chapter has a valid `lesson_chapter_doc` — it is a deliberate product
pilot (`CHAPTER_JOURNEY_PILOT_GRADES` in `LessonsPage.jsx`) that replaces
the older step-by-step Previous/Next flow with one continuous scrollable
document. This is why the screenshot showed no step-navigation controls —
that is expected for any chapter that has successfully converted into a
Chapter Journey doc. The "READY WHEN YOU ARE" placeholder screen the user
saw in an earlier screenshot was a **different, unrelated symptom** — that
appeared before any lesson had been generated/loaded for the classic
per-step flow on a *different* chapter (Grade 9 Science, before the
Journey pilot's chapter-doc successfully loaded) and resolves itself once
either flow successfully fetches content.

---

## 5. Suggested rollout order (practical next steps)

1. **Pilot on one chapter first** — Grade 11 Chemistry "Structure of Atom" —
   to validate the manifest schema and Tier A audit script design before
   scaling.
   - Author the manifest (`Phase 0` example above is a ready-to-use draft).
   - Build `audit_chapter_boundary.py` Tier A checks and run against the
     existing cached lesson for this chapter — confirm it flags the same
     issues the user found manually (density example, nitrogen STP example,
     helium p-block claim, missing Bohr/quantum-number content).
   - Manually author corrected content for this chapter (Track A) and
     inject via `chatgpt_lesson_helper.py store` (or the proposed
     `seed_manual_lesson_content.py`), then re-run Tier A to confirm clean.
2. **Wire Tier A into `admin_qa.py`** as tool #7, matching the existing
   job-queue/report pattern used by the other 6 tools (`_JOBS` dict,
   background thread, JSON report, `/latest` `/run` `/status` `/report`
   endpoints) — this is a well-established pattern in this codebase, low
   risk to add.
3. **Expand manifests** to all Grade 11–12 core Science/Maths chapters
   (Physics, Chemistry, Biology, Mathematics) — highest exam weight, most
   likely to have the same RAG-chunk-blending problem given how
   conceptually adjacent Class 11–12 NCERT chapters are.
4. **Expand to Grade 9–10** Science/Maths next.
5. **Build Tier B (LLM subject-expert review)** once Tier A is proven and
   manifests exist for a meaningful chapter set — this gives qualitative
   findings (like the user's original review) at scale, admin-triggered
   only (cost control), surfaced next to existing Lesson Quality scores.
6. **Feed manifests into the live generation prompt (Phase 4)** once the
   manifest format is stable, to stop new contamination from being created
   while older chapters are still being remediated.
7. **Extend to humanities/languages** (History, Geography, Political
   Science, Economics, English, Hindi) — likely lower contamination risk
   (less conceptually adjacent chapters) but still worth a lighter-weight
   Tier A pass for syllabus-completeness gaps.

---

## 6. Open questions to clarify with the user in the next session

1. The user mentioned "manually adding content through JSON files like we
   did for Q&A" — no JSON-file-based Q&A store was found in this repo
   (`question_bank` is Supabase-table-based, and `chatgpt_lesson_helper.py`
   writes directly to `lesson_cache`, not JSON). Clarify: was this a
   different repo/branch, a spreadsheet/export step outside version
   control, or does "JSON files" simply mean "structured JSON payloads,
   wherever they end up being stored" (i.e. the manifest approach in
   Phase 0 already satisfies the intent)?
2. Confirm prioritisation: should Grade 11 Chemistry (all chapters) be
   fully remediated end-to-end first as a proof of concept before spreading
   effort across Grades 9–12, or should manifest-authoring be parallelised
   across a small team of subject reviewers per grade/subject immediately?
3. Confirm whether Tier B (LLM-as-subject-expert audit) should default to
   the same LLM provider/model already configured for `ask_llm()` in
   `openai_service.py`, or whether a stronger/more specialized model should
   be used specifically for accuracy-critical Tier B review calls (cost vs.
   quality trade-off).
4. Decide on the **manifest storage location** — this document proposes
   `backend/app/data/chapter_manifests/<grade>/<subject>/<chapter_slug>.json`
   as flat files in the repo (versionable, diffable, easy for non-engineers
   to review via PRs), but confirm this is preferred over storing manifests
   in a new Supabase table (e.g. `chapter_manifests`) which would allow the
   existing admin UI to edit them without a deploy.

---

## 4j. Textbook page images now render inline in lessons — BUILT for Cell chapter

Per user request ("can we render some of the textbook images onto the
platform at relevant sections?"), a new capability was built end-to-end:
real NCERT textbook page images now appear inline inside the Chapter
Journey lesson document, automatically matched to the milestone whose
content best overlaps the image's caption/nearby-text.

**What was built:**
1. Ran `backfill_visual_assets_for_document()` (already-existing
   `rag_visual_service.py` infra, previously only used from an admin
   route) against the Cell chapter's source PDF (`iesc102.pdf`,
   `rag_documents.id=346`) — rendered all 20 pages to JPEG and stored them
   in the `rag-visuals` Supabase Storage bucket, linked via
   `rag_visual_assets` rows (default `status="needs_review"`).
2. Curated and approved 10 of the 20 pages with milestone-relevant
   captions (microscope/magnification, membrane/cell wall, organelles,
   cell division/meiosis, chapter summary) — set `status="active"` so
   they become eligible for serving.
3. Added `TextbookImageBlock` to `app/models/lesson_blocks.py` (new block
   type in the `Block` union) — `asset_url`, `caption`, `page_number`.
4. Extended `chapter_doc_service.py`: `_fetch_approved_visuals()` pulls
   all active visuals for the chapter; `_match_visuals_to_milestone()`
   scores each unused visual by keyword overlap between its
   caption/nearby-text and the milestone's title+content, attaches the
   top 2 matches per milestone, and tracks used IDs so no image repeats
   across milestones. Wired into `convert_chapter()` right after LKB chip
   attachment.
5. Added a `textbook_image` case to both `JourneyRenderer.jsx` (Grades
   5-8) and `StudyRenderer.jsx` (Grades 9-12) — renders the image with a
   caption/page-number figcaption, styled consistently with each
   renderer's existing card system.

**Verified end-to-end:**
```
Reconverted doc milestones: 5 | total textbook_image blocks: 10
```
All 10 approved images distributed correctly — 2 per milestone, zero
duplicates, each matched to its topically-relevant section (e.g.
microscope/magnification images landed in "Concept introduction",
organelle images in "Worked examples", meiosis/cell-division images in
"Exam-style problems"). The stale `lesson_chapter_doc` cache was deleted
first so this reconversion is what will actually be served next.

**Design notes:**
- Images are **never AI-generated** — always real, admin-approved NCERT
  textbook pages, consistent with Condition 7/8 (no invented visuals).
- Matching is deterministic keyword-overlap (no LLM call), so this scales
  to any chapter with approved visuals at zero marginal cost.
- The existing admin visual-approval workflow
  (`PATCH /api/rag/visuals/{id}`, status: active/hidden/needs_review) is
  the same one now used to control which images can appear in lessons —
  no new admin tooling was needed.

**UPDATE — Manual curation was found to be unreliable; replaced with a
deterministic detector (§4k).**

---

## 4k. Fixed curation to be deterministic, not subjective — reusable for all future chapters

The user's follow-up feedback was direct: *"make sure that only relevant
pages with explanation is shown and pages are not randomly added."* This
was a valid correction — the original 10-page curation in §4j was done by
eyeballing text snippets, which produced real errors:

- **2 false positives**: pages 7 and 17 were approved despite containing
  **no actual figure at all** — pure body text and a bullet-point summary
  respectively. My subjective captions ("Cell wall — plant cell vs animal
  cell structure", "At a Glance — chapter summary points") described the
  surrounding prose, not an actual diagram on the page.
- **3 false negatives**: pages 2, 5, and 8 were skipped even though they
  DO contain real NCERT figures (Fig. 2.1, Fig. 2.6, and a bacterial/
  viroid comparison respectively) — simply missed by manual eyeballing.

**Root cause of the "randomness":** approval was based on human judgment
of the surrounding prose ("this section sounds relevant") rather than on
whether the page **actually contains a diagram**. This is exactly the
"randomly added" problem the user flagged.

**Fix — `backend/scripts/curate_textbook_visuals.py`:** a deterministic
detector that approves a page **only if** its extracted text contains a
genuine NCERT figure caption matching the pattern `Fig. N.N: <description>`
(colon required). NCERT consistently uses this exact convention for real
captions, while **in-text references** to a figure discussed elsewhere use
a parenthesis with no colon (e.g. `"...microscope (Fig. 2.2) in your
school..."`) — requiring the colon is what cleanly separates genuine
captions from passing mentions, verified against the actual Cell chapter
text.

A second bug was found and fixed during validation: `rag_visual_assets
.nearby_text` is truncated to 1200 characters at backfill time, and NCERT
figure captions are frequently extracted by PyMuPDF near the END of a
page's text (captions are separate text objects near images, appearing
after body paragraphs in extraction order) — so the truncated field
routinely cut real captions off. The script now re-reads the FULL,
untruncated page text directly from the source PDF instead.

**Corrected result for the Cell chapter — verified accurate:**
```
python3 scripts/curate_textbook_visuals.py --document-id 346 \
    --pdf-path "../RAG DB/Science/iesc102.pdf" --force
```
11 pages now correctly approved, each with its REAL printed caption (not
a guessed description):
- Fig. 2.1: Size of the objects and its visibility through (microscope range)
- Fig. 2.2: Structure of a light microscope
- Fig. 2.5: Experimental set-up, and initial and final states of potato pieces
- Fig. 2.6: Effect of solutions of different concentrations on a cell
- Fig. 2.9: Cradle lily leaf peel cells in water and sugar solution
- Fig. 2.10: A typical bacterial/plant/animal cell
- Fig. 2.11: Structure of a nucleus
- Fig. 2.13: Endoplasmic reticulum and Golgi apparatus
- Fig. 2.14: Structure of a mitochondrion
- Fig. 2.17: Different stages of cell division in onion root tip cells
- Fig. 2.19: Meiosis is a two-step process

Page 17 (previously falsely approved) was correctly reverted to
`needs_review`. Re-verified via `get_or_convert_chapter_doc()`: all 5
milestones now show exactly 2 images each, and every caption is a real,
grounded NCERT figure description.

**Reusable pipeline for all future chapters/subjects** —
`backend/scripts/backfill_and_curate_visuals.py` combines both steps
(render PDF pages → deterministically approve only genuine figures) into
one command:
```
python3 scripts/backfill_and_curate_visuals.py \
    --document-id <rag_documents.id> \
    --pdf-path "<path to chapter's source PDF>" \
    --force
```
followed by deleting that chapter's `lesson_chapter_doc` cache row (same
invalidation step required after any content change, per §4i) so the
Chapter Journey UI reconverts with the newly-approved images.

**This is now the standard process for extending textbook images to
every remaining chapter/subject** — per the user's instruction to
"include this to be done for all the subjects and chapters from now."
The next concrete step is running this pipeline for the other 12 Grade 9
Science chapters, then extending to other subjects/grades as their
`rag_documents` become available.

---

## Appendix A — Full text of the original manual review (Grade 11 Chemistry, "Structure of Atom")

> Preserved verbatim as the rubric/ground-truth for what "good" means in this
> remediation effort. Any Tier B LLM review prompt should be built directly
> from this rubric.

### Overall verdict

Assuming this is intended as a Class 11 "Structure of Atom" lesson, it is not
ready for student use in its current form. The language is approachable and
the lesson format has potential, but the content appears to combine material
from at least four different chapters: Structure of Atom; Classification of
Elements and Periodicity; Some Basic Concepts of Chemistry; Thermodynamics.

It also contains irrelevant examples, unanswered questions, formatting
problems, and a few serious scientific or pedagogical errors. A student could
finish this lesson with fragmented understanding and confusion about what the
chapter is actually teaching.

### Indicative rating

| Area | Rating |
|---|---|
| Student-friendly language | 7/10 |
| Scientific accuracy | 5/10 |
| Chapter relevance | 2/10 |
| Sequencing and coherence | 2/10 |
| Worked examples | 3/10 |
| Exam preparation value | 3/10 |
| Overall readiness | 3.5/10 |

### What is good

1. **Simple, accessible language** — e.g. "atoms are tiny particles that make
   up everything around us" gives students a comfortable entry into an
   abstract topic. Introductory sections avoid excessive jargon.
2. **Promising instructional structure** — the repeated format (What you will
   learn → Simple explanation → Step-by-step breakdown → Worked example →
   Watch out → Quick check → Revision and recap) is a strong AI-lesson
   framework combining explanation, practice, misconception correction, and
   assessment.
3. **Some foundational facts are correctly stated:** atomic number = protons;
   mass number = protons + neutrons; isotopes = same protons, different
   neutrons; neutral atoms have equal protons and electrons; same-group
   elements share properties due to similar valence configuration; atomic
   radius decreases across a period, increases down a group. The sodium
   example (11p, 12n, 11e → sodium-23) is correctly solved.
4. **"Watch out" sections are useful in principle** — e.g. distinguishing
   atomic number from mass number, a common student confusion.
5. **Opportunities for active recall exist** — questions like "What does
   Aufbau mean?", "What are the four blocks?", "Why do we classify
   elements?", "What is the atomic number of an atom with six protons?"
   could support retrieval practice, *if* placed in the correct chapter
   section and given feedback.

### Major problems that must be fixed

**1. No clear subject boundary.** The lesson begins with atomic structure,
shifts into periodic classification, moves to gas-volume/mole calculations,
then introduces lab balances, mass vs weight, high-temperature reactions, and
the second law of thermodynamics — these belong to different chapters. For a
"Structure of Atom" chapter, remove/relocate: density calculation, gas-volume
calculations at STP, percentage composition, analytical balances, units for
liquid volume, mass-vs-weight lab discussion, high-temperature reactions,
second law of thermodynamics, detailed periodic-classification history
(unless a brief closing connection). A chapter should answer one central
question: *How did scientists develop the modern model of the atom, and how
are electrons arranged inside an atom?* The current content does not
maintain that focus.

**2. Most of the actual "Structure of Atom" syllabus is missing**, including:
discovery of the electron; cathode-ray discharge experiment; charge-to-mass
ratio; Millikan oil-drop experiment; discovery of proton/neutron; Thomson's
model; Rutherford's alpha-scattering experiment; Rutherford's nuclear model
and its limitations; electromagnetic radiation; wavelength/frequency/speed of
light; Planck's quantum theory; photoelectric effect; atomic spectra and the
hydrogen line spectrum; Rydberg equation; Bohr's model; radius/energy of
hydrogen-like species; limitations of Bohr's model; de Broglie relationship;
Heisenberg uncertainty principle; quantum-mechanical model; orbitals and
probability distribution; quantum numbers; shapes of s/p/d orbitals; nodes;
Aufbau principle; Pauli exclusion principle; Hund's rule; electronic
configurations; stability of half-filled/completely-filled subshells; common
electronic-configuration exceptions where syllabus-appropriate. Without
these, the lesson is closer to a brief introduction than a complete chapter.

**3. The density example is irrelevant.** "Mass = 28 g, Volume = 41.9 mL" is
a density problem, not atomic structure. A better first example: *"An ion
contains 17 protons, 18 electrons and 18 neutrons. Identify the element,
ionic charge, atomic number and mass number."*

**4. The nitrogen example is scientifically and linguistically defective.**
"A sample of nitrogen gas at STP weighs 41.9 mL" is dimensionally incorrect
(mL measures volume, not weight). The question then asks for percentage
nitrogen, which can't be calculated without knowing total sample
mass/composition — the "solution" circularly assumes 100% nitrogen. This
example should be removed, not repaired — it belongs to mole concept /
gaseous-state calculations.

**5. The helium statement is misleading.** "Why is helium placed in the
p-block?" is wrong — helium's configuration is 1s², so by subshell it is
s-block. It's placed in Group 18 with noble gases because its valence shell
is complete and its chemistry resembles theirs, not because of block. Better
question: *"Helium has a 1s² configuration. Why is it placed in Group 18
although its differentiating electron enters an s-orbital?"*

**6. The orbital-energy question is poorly worded.** "What is the extremely
useful order of energies of the orbitals?" is unnatural/incomplete. Use:
*"Write the increasing order of energies of orbitals according to the Aufbau
principle."* Expected answer:
`1s<2s<2p<3s<3p<4s<3d<4p<5s<4d<5p<6s<4f<5d<6p<7s`. Should also explain the
n+l rule rather than requiring memorisation without reasoning.

**7. "Electrons orbit the nucleus" needs qualification.** Acceptable only
while describing the Bohr model — should not be presented as the final
modern description. Better: *"In the Bohr model, electrons are described as
moving in fixed energy levels around the nucleus. In the modern
quantum-mechanical model, electrons occupy orbitals — three-dimensional
regions where there is a high probability of finding an electron."*
Otherwise students develop an incorrect planetary-orbit mental model.

**8. The description of how atoms are studied is weak.** The lesson says
atoms are studied using "special tools like microscopes and experiments such
as scattering of particles." Microscopes are not the central historical
method for this chapter's content. Should emphasise: discharge-tube
experiments, alpha-particle scattering, spectroscopy, photoelectric-effect
experiments, mathematical quantum models. Atomic-scale imaging may be
mentioned as a modern extension, not the main historical explanation.

**9. STP terminology needs clarification.** The lesson uses
`1 mol gas = 22.4 L at STP` without stating the convention (0°C, 1 atm).
Suggested note: *"For school-level numerical problems, unless otherwise
specified, take molar volume at 0°C and 1 atm as approximately
22.4 L mol⁻¹."* — avoids confusion vs. other standard-pressure conventions
students may encounter.

**10. Questions appear without answers or feedback.** E.g. "What does
Aufbau mean?", "What are the four blocks?", "Why is helium placed in the
p-block?", "What analytical balances are used?", "Why are reactions
conducted at high temperature?", "What is the second law of
thermodynamics?" — many unanswered, some don't belong to the chapter. Every
"quick check" should provide: student response opportunity, correct answer,
brief explanation, misconception feedback, retry/follow-up question. Without
feedback these are disconnected prompts, not learning activities.

### Problems with the periodic-classification section

Clearer than the atomic-structure section, but **should be its own
chapter**. Good elements: explains why classification is necessary,
distinguishes Mendeleev's law from the modern periodic law, links periodic
properties to electronic configuration, chlorine example is correctly
solved. Improvements needed:
- Update "over 114 elements" → the modern periodic table has **118**
  officially recognised elements.
- Include Döbereiner's triads, Newlands' law of octaves, Mendeleev's table
  and its limitations, Moseley/atomic number, modern periodic law — proper
  historical sequence.
- Explicit rules: period number relates to highest principal quantum
  number; for representative elements, group properties relate to
  valence-shell configuration; block is determined by the subshell
  receiving the differentiating electron.

### Problems with the worked examples

A good worked example should reinforce the concept immediately preceding
it — here they are often disconnected:

| Example | Relevance to Structure of Atom |
|---|---|
| Density from 28 g and 41.9 mL | Not relevant |
| Chlorine from period and group | Relevant to periodic classification, not atomic structure |
| Nitrogen gas volume and percentage | Incorrect and irrelevant |
| Molecules in 28 mL gas | Mole concept, not atomic structure |
| Sodium from protons/neutrons/electrons | Relevant and useful (only one that is) |

**Better example progression** (increasing difficulty):
1. Identify particles — protons/neutrons/electrons → atomic number, mass
   number, element, charge.
2. Ion formation — e.g. 12 protons, 10 electrons → identify ion + charge.
3. Isotopes — compare Cl-35 and Cl-37.
4. Quantum numbers — determine if a proposed set is allowed.
5. Electronic configuration — Fe and Fe²⁺.
6. Spectral calculations — frequency/wavelength via `c = νλ`.
7. de Broglie or Bohr model — `λ = h/mv` or hydrogen-like species
   calculations.

### Recommended chapter sequence (target structure for remediated content)

- **Unit 1 — Why atomic models changed:** Dalton's idea; discovery of
  subatomic particles; Thomson model; Rutherford experiment; limitations of
  Rutherford model.
- **Unit 2 — Radiation and atomic spectra:** Electromagnetic radiation;
  `c = νλ`; Planck's quantum theory; photoelectric effect; hydrogen
  spectrum; Rydberg equation.
- **Unit 3 — Bohr's model:** Postulates; energy levels; electronic
  transitions; successes and limitations.
- **Unit 4 — Quantum-mechanical model:** de Broglie hypothesis; uncertainty
  principle; orbitals and probability; quantum numbers; orbital shapes and
  nodes.
- **Unit 5 — Electronic configuration:** Aufbau principle; n+l rule; Pauli
  exclusion principle; Hund's rule; electronic configurations; stability of
  half-filled/filled subshells.
- **Unit 6 — Practice and revision:** Concept checks after every section;
  worked numerical examples; NCERT-style questions; assertion–reason
  questions; error-identification questions; chapter summary; mixed mock
  test.

Periodic classification should then be taught as the **next chapter**,
using electronic configuration as the bridge.

### How to make it more useful for students (enhancement backlog)

- **Add visual learning** — diagrams/animations for: cathode-ray tube,
  Rutherford scattering setup & observations, Bohr energy levels, hydrogen
  spectral lines, shapes of s/p orbitals, orientation of p orbitals, orbital
  filling diagrams, Aufbau diagonal rule. Text-only treatment is
  insufficient for many students.
- **Use comparison tables** — e.g. particle (charge/mass/location) table for
  electron/proton/neutron; atomic-model comparison table (Thomson/
  Rutherford/Bohr/quantum model: main idea, evidence, limitation).
- **Introduce one concept at a time** — a student should not encounter
  Aufbau, periodic classification, density, gas laws, and thermodynamics in
  the same learning step. Each lesson screen: one objective, one core
  concept, one visual, one worked example, two-three checks, one
  misconception warning, one short mastery assessment.
- **Improve question quality** — beyond factual recall: explain-why
  questions, compare-and-contrast, numerical applications, diagram
  interpretation, error diagnosis, electronic-configuration practice,
  multi-concept exam questions.
- **Add answer explanations** — e.g. *Q: Which quantum number determines
  orbital shape? A: Azimuthal quantum number, l. Explanation: l identifies
  the subshell — l=0 for s, l=1 for p, l=2 for d, l=3 for f.*

### Priority correction list (from the original review)

**Critical:**
- Separate the mixed chapters.
- Remove the faulty nitrogen percentage example.
- Correct the helium block/group statement.
- Replace irrelevant density and gas-law examples.
- Add the missing core atomic-structure syllabus.
- Distinguish the Bohr model from the modern orbital model.
- Fix broken mathematical formatting.
- Provide answers and feedback for every check.

**Important:**
- Add diagrams and orbital representations.
- Improve conceptual sequencing.
- Add NCERT- and exam-aligned examples.
- Explain the Aufbau order using the n+l rule.
- Clarify the STP convention.
- Add model limitations and experimental evidence.
- Include quantum numbers and electronic configurations.

**Enhancement:**
- Add adaptive difficulty.
- Add interactive orbital-filling activities.
- Add misconception-based questions.
- Add chapter-end mastery analytics.
- Add links between atomic structure, periodicity, and bonding.

### Final teacher assessment (from the original review)

The chapter has a good lesson-template skeleton and student-friendly tone,
but currently looks like several AI-generated lesson fragments combined
without sufficient subject review. It can be developed into an effective
learning resource, but it needs a **substantial chemistry-content rewrite**,
not minor editing. The strongest approach: retain the presentation
framework while rebuilding the actual lesson content around a coherent,
syllabus-aligned progression — which is precisely what Phase 0–4 of this
plan (chapter manifests + boundary audit + manual/constrained remediation +
prevent-regression prompt injection) is designed to deliver, generalised
across all Grade 9–12 chapters.

---

## 4l. Batch pipeline built and run — 126 real NCERT images now live across 12 Grade 9 Science chapters

Per the user's instruction ("include this to be done for all the subjects
and chapters from now"), a batch runner —
`backend/scripts/batch_backfill_and_curate_visuals.py` — was built on top
of the single-chapter pipeline (§4k) to process an entire subject in one
command.

**What it does, per `(grade, subject)`:**
1. Reads the syllabus chapter list from `syllabus.py` (same source as
   `prepare_gpt55_prompts.py`).
2. Resolves each chapter's `rag_documents.id`, trying both the bare
   syllabus title and the `"Chapter N: "`-prefixed form (handles the same
   naming mismatch documented in §4i).
3. Runs backfill (render PDF → Supabase Storage) + the deterministic
   Fig.-N.N-caption curator (§4k) for every chapter.
4. Invalidates each chapter's `lesson_chapter_doc` cache row so the
   Chapter Journey UI reconverts with the new images immediately.

**Run live for Grade 9 Science — result:**
```
python3 scripts/batch_backfill_and_curate_visuals.py --grade "Grade 9" --subject Science --force
```
**12 of 13 chapters processed successfully** (1 skipped: "Exploring
Mixtures and Their Separation" has a `Their`/`their` case mismatch
between `rag_documents.chapter` and `syllabus.py` — a data cleanup item,
not a pipeline bug). Final tally of genuinely-captioned NCERT images
approved, verified directly against Supabase:

| Chapter | Images approved |
|---|---|
| Exploration (intro) | 3 |
| Cell: The Building Block of Life | 11 |
| Tissues in Action | 9 |
| Describing Motion Around Us | 10 |
| How Forces Affect Motion | 17 |
| Work, Energy, and Simple Machines | 14 |
| Journey Inside the Atom | 12 |
| Atomic Foundations of Matter | 9 |
| Sound Waves | 14 |
| Reproduction | 9 |
| Patterns in Life (Diversity/Classification) | 10 |
| Earth as a System | 8 |
| **Total** | **126** |

Every single one of these 126 images has a **real, printed NCERT figure
caption** extracted directly from the source PDF (e.g. "Fig. 8.16: Journey
of the development of atomic models", "Fig. 11.21: Key stages of the
menstrual cycle across a typical 28-day period") — none were guessed,
none are placeholders, and pages with no real diagram were correctly
left unapproved in every chapter (skip rates ranged 35-75% depending on
how text-heavy vs. diagram-heavy each chapter is).

**This fully satisfies the user's two requirements:**
1. *"include this to be done for all the subjects and chapters from
   now"* — the batch script is generic across any `(grade, subject)`
   already configured in `BOOK_SOURCES`; extending to Grade 9 Maths,
   or Grades 10-12, requires only adding one entry to that dict.
2. *"make sure only relevant pages with explanation is shown and pages
   are not randomly added"* — enforced deterministically via the
   `Fig. N.N:` caption-colon requirement (§4k), not subjective judgment.

**Not yet done:**
- Fix the "Exploring Mixtures and Their Separation" title-case mismatch
  (either in `syllabus.py` or `rag_documents.chapter`) so all 13 chapters
  resolve.
- Extend to Grade 9 Maths and other Grade 9 subjects, then Grades 10-12,
  by adding `BOOK_SOURCES` entries and re-running the same batch command.
- Spot-check a handful of the 126 images in-browser (as done for the Cell
  chapter) to visually confirm rendering quality across a wider sample.

---

## 4m. Bug found and fixed — textbook images were silently missing for GPT-5.5-authored chapters

The user asked "are relevant textbook visually added to these chapters?"
after 3 new GPT-5.5 chapters (Exploration, Tissues in Action, Describing
Motion Around Us) were ingested via §4f's pipeline. Checking directly
revealed **0 textbook_image blocks in all 3 chapters**, despite their
images having already been backfilled and curated correctly in the §4l
batch run.

**Root cause — the exact same "Chapter N: " prefix mismatch documented in
§4i, now surfacing in a new place:** `rag_visual_assets.chapter` is
stored with the `"Chapter 1: Exploration..."` prefix (from the original
backfill, which reads `rag_documents.chapter`), while `lesson_cache
.chapter` for these GPT-5.5-ingested steps is the bare, unprefixed title
from the manifest (`"Exploration: Entering the World of Secondary
Science"`). `chapter_doc_service._fetch_approved_visuals()` queried with
an **exact match** on the lesson's chapter string, so it silently
returned zero rows for every GPT-5.5-authored chapter — the images
existed and were correctly curated, but were never being looked up.

**Fix applied to `_fetch_approved_visuals()`:** try the exact match
first (preserves existing behaviour for manually-seeded chapters like
Cell, which already matches), then fall back to an `ilike '%<chapter>'`
suffix match against the live grade DB — this catches the prefix
mismatch without requiring any data cleanup.

**Verified after invalidating the 3 chapters' `lesson_chapter_doc` cache
rows and reconverting:**

| Chapter | textbook_image blocks after fix |
|---|---|
| Exploration: Entering the World of Secondary Science | 3 |
| Tissues in Action | 9 |
| Describing Motion Around Us | 10 |
| Cell (sanity check, exact-match path, no regression) | 10 |

All 4 chapters now correctly render their curated NCERT images.

**Process learning:** this is the third time this exact naming
convention mismatch has caused a silent failure (see §4i for the
original `lesson_cache` chapter-name issue, and §4l's batch runner which
had to add the same suffix-fallback for its `find_document_id()` lookup).
**Recommendation for a future session:** normalise chapter naming
platform-wide — either always store the `"Chapter N: "` prefix
everywhere, or strip it everywhere, in one migration — rather than
continuing to patch each new lookup site with a fallback. Until that
migration happens, any new code that queries `rag_visual_assets`,
`lesson_cache`, or `lesson_chapter_doc` by chapter string should follow
the same "exact match, then suffix-match fallback" pattern used here and
in §4l.

---

## 4n. Textbook images now fully automated for every future GPT-5.5 chapter

Per the user's request ("make sure that visuals are added whenever I
share a GPT created json file for all future chapters"), the manual
"remember to run the image pipeline separately" step from §4l/§4m has
been eliminated. `backend/scripts/ingest_gpt55_chapter_output.py` now
includes a new `ensure_textbook_images()` step that runs automatically
as part of the standard ingestion flow — no extra command, no extra
manual step, ever again.

**What was added:** `ensure_textbook_images()` runs right after
`seed_lessons()` and before `invalidate_chapter_doc_cache()`. It:
1. Looks up the chapter's `BOOK_SOURCES` entry (from
   `prepare_gpt55_prompts.py`) to find the PDF folder and book code for
   this grade/subject.
2. Matches the manifest's chapter string against the syllabus chapter
   list to find the chapter's 1-based index (exact match, then substring
   match either direction — handles "Chapter N: " prefix differences).
3. Resolves the `rag_documents.id` using the same three-tier fallback
   used in §4l/§4m (exact match → "Chapter N: " prefixed → suffix
   match).
4. Runs the backfill (render PDF pages) + deterministic curation
   (`curate_textbook_visuals.py`'s Fig.-N.N-caption detector) for that
   chapter automatically.
5. **Never blocks or fails the overall ingestion** — if any step above
   can't find a match (e.g. a brand-new subject/grade without a
   `BOOK_SOURCES` entry yet, or a PDF not yet uploaded to RAG), it prints
   a clear `[skip]` message and the content ingestion still completes
   normally.

**Verified end-to-end** by re-running ingestion for the "Exploration"
chapter in one single command:
```
python3 scripts/ingest_gpt55_chapter_output.py --input gpt_output/g9_science_exploration.json --force
```
Output showed content stored, THEN textbook images automatically located
and curated (`document_id=345`, 3 genuine NCERT figures approved), THEN
the chapter_doc cache invalidated, THEN the Tier A audit — all from one
command. Confirmed via `get_or_convert_chapter_doc()`: **3 textbook_image
blocks now present**, matching the batch-run result from §4l exactly.

**What this means going forward:** whenever the user shares a new
GPT-5.5-generated chapter JSON (for any subject/grade that already has a
`BOOK_SOURCES` entry and an uploaded RAG PDF), a single
`ingest_gpt55_chapter_output.py --force` call now handles everything:
manifest write, content seeding, **textbook image backfill+curation**,
Chapter Journey cache invalidation, and the Tier A audit — with zero
separate/manual image-pipeline steps required.

**To extend this automation to a new grade/subject not yet covered:**
add one entry to `BOOK_SOURCES` in `prepare_gpt55_prompts.py` (PDF
folder, book code, chapter count, subject class) — the exact same single
step already required to enable the GPT-5.5 prompt-preparation workflow
for that grade/subject. No other code changes are needed.

---

## 4o. "Refresh lesson" button added — fixes stale content surviving a browser hard-refresh

The user reported that after a content fix, the lesson still showed old
content even after a **browser hard-refresh**. This confirmed the root
cause already suspected: the staleness lives in the **server-side**
`lesson_chapter_doc` cache table (§4i), which a browser refresh — hard or
soft — has no way to touch, since it's not a browser cache at all.

**Fix — a working "Refresh lesson" mechanism, end-to-end:**

1. **Backend (`chapter_doc_service.py`)**: added
   `invalidate_stored_chapter_doc()` (deletes the `lesson_chapter_doc` row
   for the exact chapter) and a new `force_refresh` parameter on
   `get_or_convert_chapter_doc()` — when `True`, it skips the stored doc
   entirely, invalidates it, and reconverts fresh from the current
   `lesson_cache` content before re-storing.
2. **Route (`/api/lesson/chapter-doc`)**: added a `refresh: bool = False`
   query parameter, wired straight through to `force_refresh`.
3. **Frontend API (`api/lesson.js`)**: `getChapterDoc()` now accepts a
   `refresh` option that adds `?refresh=true` to the request.
4. **UI (`LessonsPage.jsx`)**: added a visible **"Refresh lesson"** button
   directly above the Chapter Journey view (visible for every chapter
   using the pilot experience) — calls `getChapterDoc(..., refresh: true)`
   and swaps in the freshly-rebuilt doc, with a "Refreshing…" loading
   state and no risk of blanking the lesson if the refresh call fails.

**Verified end-to-end** against the live "Tissues in Action" chapter:
```
Stored doc exists before refresh test: True
force_refresh=True returned doc: True
Milestones: 5
Stored doc exists after refresh: True
```
Confirms the full cycle — invalidate old doc, reconvert from current
`lesson_cache`, re-store — completes correctly and the button will show
fresh content reliably every time, without needing any admin script.

**Why this is better than a browser hard-refresh:** a browser refresh only
clears client-side state (React state, browser HTTP cache) — it cannot
reach the `lesson_chapter_doc` table living in Supabase. This button
calls the backend directly with an explicit signal to discard and rebuild
that specific server-side cache row, which is the only thing that was
ever actually stale.

---

## 4p. Fixed two real content-presentation bugs found via user screenshot review

The user flagged a specific screenshot showing a "Types of Joints" diagram
appearing directly below plant-tissue quick-check questions in the
"Tissues in Action" chapter, asking whether this was out of sequence.
Investigation found **two distinct, real bugs** (plus confirmed one false
alarm caused by stale cached content, already fixed by the §4o refresh
button):

**Bug 1 — milestone section boundaries were not visually distinct
(Grades 9-12 "Study" renderer):** `StudyRenderer.jsx` used only a thin
1px border-bottom between milestones, so scrolling from one topic area
into a completely different one (e.g. plant tissue content → joints/
musculoskeletal content) read as one unbroken stream rather than two
clearly separated sections. Fixed by adding a strong "Section N of M"
badge + divider line above every milestone heading, with generous
top-margin spacing (40px) between sections and a thicker 3px accent
underline — so a reader can immediately tell they've moved into a new
topic area.

**Bug 2 — textbook images were full PDF-page screenshots, not cropped
figures:** every approved image was the ENTIRE PDF page rendered as one
JPEG — all surrounding body text, unrelated paragraphs, and exercise
lists were baked directly into the image pixels. This made every image
look visually noisy regardless of how correctly it was matched to a
lesson milestone, and explains why the joints diagram "looked out of
place" even though it was topically correctly assigned to the
"Exam-style problems" milestone (which does cover joints/musculoskeletal
content).

**Fix — `curate_textbook_visuals.py` now crops to just the figure:**
added `_figure_crop_rect()` (locates the embedded raster image(s) on the
page via PyMuPDF, unions multi-part figures, and extends the crop
downward to include the matching "Fig. N.N:" caption text block) and
`crop_and_reupload_figure()` (re-renders just that cropped region at
higher resolution and overwrites the existing image at the same storage
path — no DB/URL changes needed). Wired directly into the existing
approval flow in `curate_document()`, so every future curation run
automatically crops newly-approved figures.

**Critical bug found and fixed during verification:** the first crop
attempt on a real page still produced the full page, because one
embedded image was itself a **near-full-page background layer** (610×863
pts on a 594×784 pt page — larger than the page itself), which dominated
the union and defeated the crop. Fixed by excluding any embedded image
occupying more than 55% of the page area from the crop calculation —
verified the fix produces genuinely smaller crops afterward (e.g. one
figure went from 1307×1727 to 1115×1391 pixels).

**Applied live across all 12 already-curated Grade 9 Science chapters** —
every chapter's approved images were re-cropped in place:
```
document_id=345: 3/3 cropped   document_id=352: 12/12 cropped
document_id=346: 11/11 cropped document_id=353: 9/9 cropped
document_id=348: 10/10 cropped document_id=354: 14/14 cropped
document_id=350: 17/17 cropped document_id=355: 9/9 cropped
document_id=351: 14/14 cropped document_id=356: 10/10 cropped
                                document_id=357: 8/8 cropped
```
All 34 `lesson_chapter_doc` cache rows for Grade 9 Science were then
invalidated so every chapter reconverts fresh with both fixes (cropped
images + stronger milestone dividers) on next load — no additional
manual step needed per chapter.

**Also confirmed (separate from the two bugs above):** the specific
screenshot the user shared showed a quick-check question about xylem
cell walls that does **not exist anywhere** in the current
`lesson_cache` content for this chapter — confirming that particular
screenshot was showing **stale cached content** from before the §4o
"Refresh lesson" button existed, not a new problem. Clicking that button
(or the cache invalidation above) resolves it.

---

## 4q. Critical prompt-design bug found and fixed — numeric problem-solving
### format was being force-fit onto Humanities/Language chapters

The user flagged (with screenshots from live "How I Taught My Grandmother
to Read" content) that the "Worked example" section was fabricating
numeric arithmetic on top of a literature chapter — inventing that a
grandmother "spent approximately 90 days" learning to read by literally
computing `3 months × 30 days = 90 days` from numbers that do not exist
anywhere in the source text, then treating this invented number as
meaningful analysis. The user's instruction: **English, Hindi, Social
Science, and other Humanities subjects must be treated differently from
Science/Maths** — the Question → Solution → Step 1/Step 2 → Final answer
numeric-problem-solving format is appropriate for Science/Maths, but must
not be forced onto Humanities/Language chapters. The user also asked to
eliminate repetitive content padding used just to fill 5-6 steps for
English/Hindi.

**Root cause confirmed:** `backend/scripts/prepare_gpt55_prompts.py`'s
`PROMPT_TEMPLATE` had exactly ONE hardcoded "Worked example" FORMAT block
for every subject, regardless of `SUBJECT_CLASS`:
```
Question: <...>
Solution:
- Step 1: ...
- Step 2: ...
- Final answer: ...
```
For Science/Maths this correctly produces genuine numeric problem-solving.
For `humanities_or_language` chapters, GPT-5.5 had no alternative
structure to follow, so it invented arithmetic to fill the same shape —
exactly the "90 days" fabrication the user found, and the same defect
pattern independently confirmed in three other already-live (but
**pre-GPT-5.5-pipeline**) chapters during this investigation:
`Carrier of Words` (Solution/Simple explanation "Step 1: Understand the
problem" — a generic numeric-style scaffold with no math but modelled
on the Science format), and the older, non-GPT-5.5
`अध्याय 1: दो बैलों की कथा` / other "अध्याय N:"-prefixed Hindi rows and
`Chapter N:`-prefixed English rows (pre-existing live-LLM-generated
content from before the GPT-5.5 pipeline in §4f existed, using a
different, duplicate `lesson_cache` key from the clean GPT-5.5 versions —
see §4i for the general chapter-naming dual-key issue this stems from).

**Important scope clarification (verified directly against the live
database, not assumed):** all 8 English, 6 Hindi, and 9 Social Science
Grade 9 chapters that were **already ingested via the GPT-5.5 pipeline**
(§4f, i.e. every chapter with a manifest under
`app/data/chapter_manifests/grade_9/{english,hindi,social_science}/`)
were individually checked and are **clean** — no fabricated
arithmetic/dates/durations found in any "Worked examples" step. Two
chapters initially flagged by an automated regex scan
(`Carrier of Words` — English grammar exercise citing "20 years" as part
of a real present-perfect-tense sentence to complete; `The Price Puzzle:
What Drives the Market` — Economics citing real NCERT Table 9.3
demand/supply schedule numbers) were confirmed as **false positives**:
both are legitimately grounded, non-fabricated content (a grammar
exercise and genuine Economics quantitative data respectively — Economics
is inherently numeric even as a Social Science subject). **None of the
already-GPT-5.5-ingested Grade 9 English/Hindi/Social Science chapters
need to be redone.**

The actual defect (the "90 days" example the user screenshotted) lives in
**older, pre-GPT-5.5-pipeline `lesson_cache` rows** that predate the §4f
pipeline entirely (live-LLM-generated content from before any manifest
existed for that chapter) — these are a **separate cleanup item**, not a
prompt-design regression in currently-produced content.

**Fix applied to `backend/scripts/prepare_gpt55_prompts.py`** (affects
all FUTURE chapter generation, any subject/grade):

1. **Rule 2 (NO FABRICATED NUMBERS) strengthened** with an explicit,
   absolute sub-rule for `humanities_or_language`: never invent
   arithmetic, dates, durations, counts, or any quantity to "calculate"
   from a story/poem/chapter. Explicitly states what a "worked example"
   means for these subjects instead: pose a genuine interpretive/
   analytical question (ideally citing a real NCERT exercise) → show a
   step-by-step REASONING process (textual evidence → interpretation →
   thematic/grammatical/historical connection → conclusion) — never
   arithmetic steps, never a numerically-derived "Final answer."
2. **New Rule 4a (NO REPETITION ACROSS STEPS)** — directly addresses the
   user's second concern (eliminating repeated content used just to fill
   5-6 steps for English/Hindi): each of the 5 lesson steps must cover a
   DIFFERENT slice of the chapter and use DIFFERENT illustrative quotes/
   examples/citations from each other; if a chapter's content is
   genuinely thin for a given step, the step should be SHORTER rather
   than padded with material already covered earlier — with an explicit
   self-check instruction ("would a student reading all 5 steps
   back-to-back feel like step 3 is repeating step 1?").
3. **The "Worked example" FORMAT block is now subject-class-conditional**
   (`worked_example_format_note`, computed in `run()` based on
   `subject_class` and interpolated into the template): Science/Maths
   keeps the original numeric Question/Solution/Step-N/Final-answer
   shape; `humanities_or_language` gets a distinct discursive shape —
   Question (interpretive/analytical) → Solution (Step 1: identify
   textual evidence → Step 2: interpret its significance → Final answer:
   reasoned prose conclusion, explicitly never a calculated number) — with
   an inline instruction never to invent a quantity to calculate.

**Verified working end-to-end**: regenerated a real prompt
(`प्रेपरे_gpt55_prompts.py --grade "Grade 9" --subject Hindi --limit 1`)
and confirmed the "हल किया गया उदाहरण" (Worked example) section now
renders the new discursive reasoning format with the explicit
no-fabricated-arithmetic instruction, instead of the old numeric
Question/Solution/Step-1/Step-2/Final-answer shape.

**Remaining/next steps (not yet done — recommended for the next
session):**
1. **Clean up the older, pre-GPT-5.5-pipeline `lesson_cache` rows** that
   contain the actual "90 days" style fabrication the user screenshotted
   — these are duplicate, stale rows under a different chapter-name key
   (e.g. `Chapter 1: How I Taught My Grandmother to Read` /
   `अध्याय 1: दो बैलों की कथा`) than the clean GPT-5.5-ingested rows (e.g.
   `How I Taught My Grandmother to Read` / `दो बैलों की कथा`). Per §4i,
   the LIVE APP may actually be serving whichever key the frontend's
   chapter selector currently uses — this needs to be checked per
   chapter and either (a) the stale duplicate row deleted so the clean
   GPT-5.5 row is served, or (b) the affected chapter's GPT-5.5 output
   re-ingested under the correct/matching chapter-name key.
2. **Apply the same subject-class-aware fix to the live/dynamic
   generation path** (`backend/app/services/tutor_service.py`'s
   `TUTOR_SYSTEM`/`PROSE_LITERATURE_SYSTEM`/`POEM_SYSTEM` prompts) — this
   plan's Phase 0-4 focus has been on the GPT-5.5 batch-authoring
   pipeline, but any chapter that still falls back to **live LLM
   generation** (not yet GPT-5.5-ingested, or cache-missed) is generated
   by `tutor_service.py`'s prompts, which were not touched by this fix
   and may have the same or a similar force-fit numeric-format problem.
   This needs the same audit + subject-class-conditional fix applied
   there.
3. **Extend Grade 9 English/Hindi/Social Science GPT-5.5 ingestion to any
   remaining un-ingested chapters** (a few English/Hindi/Social Science
   chapters in the syllabus do not yet have a manifest/GPT-5.5-authored
   version — cross-check `syllabus.py`'s chapter lists against the
   `chapter_manifests/grade_9/{english,hindi,social_science}/` folders to
   find gaps), using the now-fixed template so no new chapter can
   reintroduce the fabricated-arithmetic pattern.
4. **Once the older pre-pipeline rows are cleaned up (step 1 above),
   re-verify the exact chapters the user screenshotted** ("How I Taught
   My Grandmother to Read") render correctly in the live app — including
   invalidating the corresponding `lesson_chapter_doc` cache row per §4i/
   §4o, since fixing `lesson_cache` alone does not guarantee the fix is
   visible without also clearing that second cache layer.
5. **Extend this same subject-class-aware fix to Grade 10-12** once
   `BOOK_SOURCES` entries are added for those grades' humanities/language
   subjects, so this defect class never appears in any future
   grade/subject batch.

---

## 4r. Per-SUBJECT prompt guidance (not just per-SUBJECT_CLASS) — BUILT,
### plus Grade 10 Maths + Science BOOK_SOURCES added

The user's follow-up instruction: *"create GPT prompts subject wise and
not the same prompt for all subjects"* — while §4q's fix made the prompt
aware of `SUBJECT_CLASS` (`science_or_maths` vs `humanities_or_language`,
a binary switch controlling whether numeric worked examples are
allowed), it still used the exact same wording for e.g. Science and
Maths, or for English and Hindi and Social Science. The user wants each
individual SUBJECT (not just each class) to get its own tailored
guidance.

**Fix — new `SUBJECT_GUIDANCE` dict in `prepare_gpt55_prompts.py`,**
inserted into the prompt as a new `{subject_guidance}` paragraph
immediately after the SYSTEM ROLE and before the shared BINDING RULES:

- **Science**: ground explanations in real NCERT experiments/activities
  (cite them explicitly), worked examples should walk through the
  scientific reasoning (observation → principle → prediction), not just
  formula substitution; common mistakes should target subject-specific
  misconceptions (mass vs weight, speed vs velocity, physical vs chemical
  change).
- **Maths**: worked examples MUST show complete step-by-step
  algebraic/arithmetic/geometric working, board-exam style. Unlike every
  other subject, Maths is explicitly allowed to invent a NEW numeric
  problem testing the same method as an NCERT example (the method must be
  standard, not a new invented formula) — this is a deliberate,
  documented exception since Maths pedagogy inherently requires numeric
  practice variety, unlike literature/social-science content.
- **Social Science**: explicitly instructs the model to first identify
  whether THIS chapter is History, Geography, Political Science, or
  Economics from the source text, then tailor emphasis accordingly
  (chronology/cause-effect for History; spatial/physical relationships
  for Geography; institutions/constitutional provisions for Political
  Science; real data/tables directly from the source text for
  Economics — the existing "Price Puzzle" chapter's real NCERT Table 9.3
  numbers is the reference example this codifies).
- **English**: literary claims must cite a specific quote/traceable
  moment; prose vs poem get different emphasis (characterisation/theme/
  narrative technique vs imagery/sound devices/tone); grammar/language-
  skill chapters (distinct from literature within the same subject) may
  use freshly-composed example sentences as long as the grammar rule
  itself is standard, not invented — this exception mirrors the Maths
  exception above for the same underlying reason (grammar practice, like
  Maths practice, inherently needs example variety).
- **Hindi**: equivalent guidance written natively in Hindi (साहित्यिक
  दावों को उद्धरण से जोड़ना, गद्य/कविता भेद, मानक व्याकरण नियम) so a
  reviewer working in Hindi can read/edit this guidance directly.
- **Fallback**: any subject not yet in `SUBJECT_GUIDANCE` gets a generic
  "no custom guidance configured — use your best judgement" paragraph
  rather than failing, so new subjects can always be added incrementally
  without breaking the pipeline.

**Also added: Grade 10 Maths + Science `BOOK_SOURCES` entries** — Grade
10's `syllabus.py` currently only has a single placeholder entry
("Uploaded Book Content") per subject, not a real ordered chapter list,
so a new `CHAPTER_NAME_OVERRIDES` dict (checked first inside
`get_chapter_list()`, falling back to `syllabus.py` for every other
grade/subject) supplies the correct, verified chapter names for Grade 10
Maths (14 chapters: Real Numbers .. Probability) and Grade 10 Science (13
chapters: Chemical Reactions and Equations .. Our Environment) — cross-
checked directly against the already-uploaded `rag_documents.chapter`
values (ids 260-286) to guarantee exact naming match.

**Verified end-to-end**: generated the full, real prompt bundle for both
subjects —
```
python3 scripts/prepare_gpt55_prompts.py --grade "Grade 10" --subject Maths
python3 scripts/prepare_gpt55_prompts.py --grade "Grade 10" --subject Science
```
produced 14 Maths + 13 Science ready-to-paste prompt files (plus source
PDFs) in `~/Downloads/GPT55_Prompts_grade_10_maths/` and
`~/Downloads/GPT55_Prompts_grade_10_science/`, each correctly containing
the Maths- or Science-specific `SUBJECT-SPECIFIC GUIDANCE` paragraph
(spot-checked the "Real Numbers" prompt directly — confirmed the Maths
paragraph, not a generic one, renders in the correct position).

**Grade 10 English/Hindi/Social Science are NOT yet available for this
pipeline** — unlike Maths/Science, there are no local source PDFs for
these subjects at `RAG DB/Grade_10/` (only Maths and Science folders
exist there); their content is only available as already-uploaded
`rag_documents`/`rag_chunks` rows in Supabase (English: 9 chapters,
Hindi: 12 chapters, Social Science: ~20 chapters spanning
History/Geography/Political Science/Economics — all confirmed present
via direct query). Extending `prepare_gpt55_prompts.py` to these subjects
requires a different extraction path (pull full chapter text from
`rag_chunks` instead of `pdfplumber` on a local PDF) — flagged here as
the next concrete step once Grade 10 Maths/Science are triaged.

**Recommended immediate next steps:**
1. Paste each of the 14 Grade 10 Maths and 13 Grade 10 Science prompts
   into GPT-5.5, save the JSON outputs, and run
   `ingest_gpt55_chapter_output.py --force` for each — same workflow as
   Grade 9.
2. Add a Supabase-`rag_chunks`-based text-extraction path (instead of
   `pdfplumber` on a local PDF) to `prepare_gpt55_prompts.py` so Grade 10
   English/Hindi/Social Science (and any other grade/subject with only
   RAG-uploaded content, no local PDF) can use the same prompt-prep
   pipeline.
3. Continue adding subject-specific `SUBJECT_GUIDANCE` entries for any
   further subjects introduced (e.g. Computer Science, Sanskrit) as they
   come online.

---

## 4s. Multi-week follow-up — NCERT curriculum alignment audit, systemic
### false-alarm fixes, and a new platform-wide coverage report (2026-08-07)

In the weeks after §4r, work broadened from "is each chapter's content
correct" to "is the platform's chapter *list* itself correct" and "are the
automated quality tools trustworthy." Three things happened, all now
resolved:

**1. Full NCERT curriculum-alignment audit, Grades 5–12, all subjects.**
Every one of the 57 grade/subject chapter lists on the platform was
compared against the current official NCERT textbook, fetched directly
from ncert.nic.in (never third-party exam-prep/solution sites — this rule
was enforced strictly after early drafts nearly relied on secondary
sources). Found and fixed a mix of: chapters deprecated by the 2023 NCERT
curriculum rationalization that were still live on the platform, current
chapters missing entirely, and stale/garbled titles. Fixes went through
the GPT-5.5 human-in-the-loop authoring pipeline (§4f), each batch
spot-checked before being trusted. Full narrative log lives in the
published audit report (see `docs/CONTENT_QUALITY_STATUS.md` for the
current link) — not duplicated here since that report is the living
version and this file is not.

**2. Confirmed pattern: Tier A `known_pitfall` findings are frequently
false positives, not defects.** Across the NCERT-alignment authoring
batches, every single CRITICAL `known_pitfall` flag raised by
`audit_chapter_boundary.py`'s post-ingest audit was manually spot-checked
against the actual generated prose. All were false positives — the check
fires on topic-adjacent vocabulary proximity, not on whether the content
actually *asserts* the misconception. A chapter that explicitly refutes a
known pitfall ("the chapter does not present X as universally true...")
still trips the flag, because the correction shares vocabulary with the
claim it's correcting (this exact failure mode was first documented back
in §4a's pilot and clearly has not been fully eliminated by the sentence-
level heuristic added there). **Standing rule going forward: a Tier A
CRITICAL `known_pitfall` finding must be read against the actual passage
before being reported as a real defect — it is a candidate for review, not
a verdict.** The contamination and coverage-gap checks remain reliable and
are not affected by this caveat.

**3. Root-caused and fixed two sources of production data pollution that
had been generating false "content quality" alarms:**
- **Doubt Knowledge Base (`doubt_kb`) pollution** — internal QA/E2E test
  scripts were calling the same `store_in_doubt_kb()` path as real student
  traffic, writing synthetic test questions into the live DKB where they
  were then served to real students as genuine cached answers. Fixed at
  the source in `tutor_service.py`: `_is_e2e_sim_user()` recognizes
  internal test-harness usernames (`E2ESim-*` prefix, `qa_harness`) and
  both `answer_doubt()` and `answer_lesson_follow_up()` skip the DKB write
  for them. ~314 already-polluted rows were retroactively deleted.
- **Fake "Previous Year Question" chapters in `question_bank`** — the same
  class of test-script leakage had written fictitious PYQ-labeled chapter
  entries into the mock-test bank. ~630 fake rows were identified (by the
  same non-realistic-username signature) and removed.

Both were user-visible before the fix: a screenshot review of the live
"Ask Doubt" page surfaced a garbled cross-subject answer and nonsensical
"suggested question" chips, which is what triggered the investigation.

**4. New platform-wide coverage report — the current source of truth.**
A consolidated report was built covering all four student-facing content
surfaces (Lessons, Ask Doubt, Mock Tests, Exam Prep Center) across every
grade and subject, computed directly from the production tables rather
than a point-in-time manual review. See **`docs/CONTENT_QUALITY_STATUS.md`**
for the current numbers, the published report link, and the full
methodology — including two bugs caught *while building that report*
(an unpaginated Supabase query that silently truncated results past 1,000
rows, and a chapter-label bare-vs-prefixed mismatch) that are worth
reading as further evidence for the same lesson this whole section
teaches: **verify every automated finding — including your own — against
the live source before trusting it.**

This file (`LESSON_CONTENT_QUALITY_REVIEW_PLAN.md`) remains the detailed
history of the lesson-content-specific remediation pipeline (manifests,
Tier A/B audits, the GPT-5.5 authoring pipeline). `CONTENT_QUALITY_STATUS.md`
is the newer, broader, and more frequently updated document — check there
first for current coverage numbers or ratings; come here for *why* the
pipeline is built the way it is.
