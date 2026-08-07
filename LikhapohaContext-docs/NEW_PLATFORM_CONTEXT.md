# New Platform — Context Doc (Multi-Board Learning Platform, From Scratch)

> Reference document for building a multi-board, multi-textbook learning
> platform from scratch. Paired with `NEW_PLATFORM_BUILD_PROMPT.md` — that
> file is what you paste as your opening message; this file is what it
> tells the agent to read first. This is a separate, greenfield design —
> not the current Likha Poha AI (CBSE-only) codebase documented in
> `CODEX_CONTEXT.md` / `IDEAL_CODEX_PROMPT.md`.

---

## 1. What this is

A learning platform — Lessons, Ask Doubt, Mock Tests — for multiple
education boards and their textbooks (not locked to one board/publisher).
The design goal stated up front: **reach and hold 100% content coverage**
across all three surfaces, for every board/grade/subject/chapter in scope,
without that number ever being a guess or a stale claim.

Every rule below exists because its absence caused a real, specific bug on
Likha Poha AI, the reference single-board (CBSE) platform this design
generalizes from. This is not generic best practice — treat every "never"
as load-bearing.

---

## 2. The one governing principle

**The full curriculum catalog is populated, from official sources, before
any content is authored.** Coverage is then always:

```
coverage = catalog_chapters_with_content / catalog_chapters_total
```

Never a scan of "whatever's in the content tables." Never a guess. Content
tables are children of the catalog, never the other way around.

---

## 3. Core schema (build this first, exactly, before any content work)

```sql
-- boards: one row per education board/curriculum authority
boards (
  id uuid PK,
  code text UNIQUE,              -- 'cbse', 'icse', 'state-mh', ...
  name text,
  country text,
  content_languages text[]       -- ['en'] or ['en','hi'], etc.
)

-- curriculum_editions: a board's syllabus as of a point in time.
-- A syllabus revision = a NEW row here, never an edit to an old one.
curriculum_editions (
  id uuid PK,
  board_id uuid FK -> boards,
  label text,
  valid_from date,
  valid_to date NULL,            -- NULL = current
  source_url text,               -- where this was verified, official only
  superseded_by uuid FK -> curriculum_editions NULL
)

-- catalog_chapters: THE single source of truth for "what should exist."
catalog_chapters (
  id uuid PK,
  edition_id uuid FK -> curriculum_editions,
  grade text,
  subject text,
  chapter_number int,
  canonical_title text,          -- ONE title field. No second "lookup" title.
  source_ref jsonb,              -- {publisher, book_code, pdf_url, page_range}
  status text,                   -- 'active' | 'deprecated' | 'planned'
  migrated_from uuid FK -> catalog_chapters NULL,
  UNIQUE (edition_id, grade, subject, chapter_number)
)

-- lesson_content
lesson_content (
  id uuid PK,
  chapter_id uuid FK -> catalog_chapters,   -- NEVER a chapter string
  step_key text,                 -- 'concept_intro' | 'core_explanation' |
                                  -- 'worked_examples' | 'exam_style_problems' |
                                  -- 'revision_recap'
  language text,
  body text,
  source_type text,              -- 'llm_generated' | 'human_authored'
  protected boolean DEFAULT false,
  status text,                   -- 'draft' | 'active' | 'needs_review' | 'archived'
  UNIQUE (chapter_id, step_key, language)
)

-- doubt_kb
doubt_kb (
  id uuid PK,
  chapter_id uuid FK -> catalog_chapters NULL,  -- NULL = subject-level entry
  question text,
  answer text,
  embedding vector(1536),
  language text,
  source text,                   -- 'authored' | 'extracted' | 'live_synthesis_cache'
  actor_class text DEFAULT 'real'  -- 'real' | 'synthetic' — see §7
)

-- question_bank
question_bank (
  id uuid PK,
  chapter_id uuid FK -> catalog_chapters,
  difficulty text,
  question text,
  options jsonb,
  answer text,
  explanation text,
  status text,
  actor_class text DEFAULT 'real'
)
```

**Non-negotiable properties of this schema:**
- Every content row's link to "which chapter" is a UUID FK, never a string
  comparison. There is no title-formatting convention to get inconsistent.
- `protected` is its own boolean, never inferred from `source_type`. Any
  bulk mutation (cache invalidation, regeneration, archival) MUST filter
  `WHERE protected = false` — enforce this in the service layer, not by
  convention.
- A syllabus revision never edits `catalog_chapters` rows in place. It
  creates a new `curriculum_editions` row and new `catalog_chapters` rows
  with `migrated_from` set.

---

## 4. Required shared utility (build before any bulk-read code)

```python
def fetch_all(table, filters):
    """The ONLY sanctioned way to bulk-read a content table for coverage,
    audits, or admin tooling. Pages past whatever the backend's default
    row cap is. Every script/service that needs a full table scan MUST
    use this — never write a second ad hoc paginated (or worse,
    unpaginated) fetch. One tested implementation, used everywhere,
    means a pagination bug gets caught once, not rediscovered per script."""
    rows, cursor = [], None
    while True:
        page, cursor = db.select(table, filters, after=cursor)
        rows += page
        if cursor is None:
            return rows
```

This is not optional scaffolding — an unpaginated bulk query on Likha
Poha AI silently capped at 1,000 rows and reported false 0% coverage for
an already-fixed subject, twice, in the same investigation.

---

## 5. Authoring pipeline (build order: binder → prompt-gen → ingest → gate)

1. **Source Binder** — for a `catalog_chapters` row, extract the source
   document's own heading text (`source_ref`) and verify it matches
   `canonical_title` (fuzzy match on title + author/book metadata) BEFORE
   generating any prompt. A mismatch blocks the pipeline and is surfaced
   as a catalog data-quality flag. Do not pair source documents to
   chapters by list position or file order — content-based matching only.

2. **Manifest generator** — per chapter, builds:
   ```json
   {
     "chapter_id": "...",
     "in_scope_units": [...],
     "banned_topics": [...],          // auto-derived from SIBLING chapters'
                                       // in_scope_units — no extra authoring
     "must_include_keywords": [...],  // derived from source headings
     "known_pitfalls": [...],         // seeded once per subject, reused
     "language": "hi",
     "section_markers": {             // REQUIRED per language, not optional
       "worked_example": "...",       // the literal heading text this
       "quick_check": "..."           // language's authored content uses
     }
   }
   ```
   `section_markers` must exist for every language a board declares in
   `content_languages` before that language is authored. A free-text
   extraction tool that hardcodes one language's heading string will
   silently return zero results for every other language — not an error,
   just quietly nothing. This bit Likha Poha AI for months on one
   language before anyone noticed the coverage numbers weren't moving.

3. **Human-in-the-loop authoring session** — paid-tier LLM only (§8).
   Output schema requires the model to self-report whether its grounding
   text actually matches the requested chapter (`source_match` field,
   required, not optional) — this is a real, cheap safety net: a model
   asked to ground strictly in supplied text will refuse to fabricate
   when the supplied text doesn't match, if you ask it to check and say so.

4. **Ingestion Gateway → Tier A gate (below) → Content Store.** Nothing
   reaches `status = 'active'` without passing Tier A. Ever.

---

## 6. Verification gate (Tier A required, Tier B sampled)

**Tier A — deterministic, free, runs on every single ingestion:**
- **Contamination**: does this chapter mention another chapter's
  `in_scope_units` vocabulary (the auto-derived `banned_topics`)?
- **Coverage gap**: % of `must_include_keywords` present across the WHOLE
  chapter (all steps combined) — not per-step. Per-step checking produces
  false gaps for chapters that legitimately concentrate one topic in one
  step.
- **Known-pitfall, with assertion/refutation classification**: a keyword
  match alone is not a defect. Classify each match using local sentence
  structure (negation, contrast markers, explicit correction framing) into
  `asserts` vs `refutes` before surfacing it. Every finding carries the
  matched span and a confidence score — never a bare pass/fail. This is
  the single most repeated false-positive class observed on Likha Poha
  AI; do not ship the naive version of this check.

**Tier B — LLM review, sampled, paid-tier only.** Not run on every
chapter (cost-prohibitive at catalog scale). Reserve for: chapters Tier A
flags as high-risk, chapters with high exam weight, and a rotating
periodic-audit sample. Tier A is unconditional; Tier B is targeted.

---

## 7. Test-data hygiene (enforce at the write path, not by convention)

Every write to `doubt_kb` or `question_bank` resolves `actor_class` from
the authenticated caller's identity. Writes with `actor_class = 'synthetic'`
(matched against a reserved test-harness identity pattern, configured
once, centrally) are **refused outright** by the data-access layer for
these tables — not accepted-then-flagged. A QA/E2E script that needs to
exercise the write path writes to a separate, clearly-labeled test schema.

Reference incident this prevents: on Likha Poha AI, internal test scripts
wrote synthetic Q&A into the live Doubt Knowledge Base through the same
code path real traffic used; those entries were served to real students
for months, caught only by a manual screenshot review.

---

## 8. Cost/quality tiering (enforce, don't just document)

| Operation | Tier | Enforcement |
|---|---|---|
| Chapter authoring (all 3 surfaces) | Paid-tier LLM, human-in-the-loop | Ingestion gateway reads model ID from an allowlist; CI lints authoring code paths for hardcoded free-tier model names |
| Tier A checks | Deterministic, free | N/A — no model involved |
| Tier B review | Paid-tier LLM, sampled | Same allowlist |
| DKB backfill from existing lessons | Free — embeddings only | Extraction, not generation; content already reviewed at authoring time |
| Free-tier Ask Doubt | DKB cache only | Free-tier request path has no code branch that reaches an LLM — not a permission check, an absent code path |
| Paid-tier Ask Doubt | DKB → RAG-grounded LLM synthesis, last resort | Cost incurred only on genuine cache miss |

---

## 9. Ask Doubt flow

```
question → DKB exact/semantic match?
  hit  → answer instantly (cache, ~free)
  miss → free tier?  → show upgrade prompt, STOP (no LLM reachable)
         paid tier?  → RAG chunks above threshold?
                          yes → LLM synthesis grounded in retrieved chunks
                          no  → warm reference fallback (no LLM, no fabrication risk)
         → on synthesis, write back to DKB cache (actor_class='real' only)
```

DKB coverage (% chapters with ≥1 cached entry) measures the cache
fast-path only — a 0% subject still answers correctly for paid users via
synthesis, just without the cache hit. Any dashboard showing this number
must say so next to it; a bare percentage reads as "no answer," which
isn't true.

---

## 10. Coverage service

Scheduled job (not on-demand-only — a scheduled job can be monitored and
alerted if it stops running). For every `(board, edition, grade, subject)`,
joins `catalog_chapters` against each content table on `chapter_id` using
`fetch_all()` (§4). Produces three percentages: lesson coverage (all
required `step_key`s active), DKB coverage, mock-test coverage. Never
computed by string-matching a chapter title.

---

## 11. Multi-board rules

- Nothing in application code hardcodes a board name or ID. Every service
  takes `board_id`.
- Source-document binding is content-based (§5.1), never filename
  convention — different publishers name files differently or not at all.
- A new board's language is a `content_languages` + `section_markers`
  configuration change (§3, §5.2), never a code change.
- "Does chapter X exist" has exactly one answer for every board: a
  `catalog_chapters` row with `status='active'`. Do not let different
  grades or boards answer this question from different tables.

---

## 12. Definition of done (per catalog chapter)

A chapter is launch-ready only when **all three** are true simultaneously
— not lesson-complete-now/doubt-later-someday:
- [ ] All required `lesson_content.step_key`s at `status='active'`
- [ ] ≥1 `doubt_kb` row for this `chapter_id`
- [ ] ≥1 `question_bank` row at `status='active'` for this `chapter_id`
- [ ] Passed Tier A with zero unresolved findings
- [ ] Source binding verified (§5.1) — no unresolved mismatch flag

## Definition of done (platform-wide, per board rollout)

- [ ] `catalog_chapters` fully populated for the board/grade/subject scope,
      from official sources only, before any authoring began
- [ ] Coverage dashboard live against that catalog before authoring began
- [ ] Every chapter meets the per-chapter definition of done above
- [ ] No `protected=true` row has been overwritten by a bulk operation
      (verify: bulk mutation code paths all filter `protected=false`)
- [ ] No `actor_class='synthetic'` row exists in `doubt_kb` or
      `question_bank`
- [ ] Coverage service has run on schedule with no pagination-related
      discrepancies against a manual spot-check
