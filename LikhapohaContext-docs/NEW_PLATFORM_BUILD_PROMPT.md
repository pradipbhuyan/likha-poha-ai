# New Platform — Build Prompt (Multi-Board Learning Platform, From Scratch)

> Copy everything between the horizontal rules below and paste it as your
> opening message to Claude Code / Codex before describing anything else.
> Attach or paste `NEW_PLATFORM_CONTEXT.md` alongside it — this prompt
> tells the agent to read it first, but the agent can't unless you provide
> it. This is for a separate, greenfield build — not a task against the
> current Likha Poha AI codebase (use `IDEAL_CODEX_PROMPT.md` for that).

---

---

## SESSION BOOTSTRAP — Read This Before Writing Any Code

You are building a **multi-board, multi-textbook learning platform** from
scratch — Lessons, Ask Doubt (AI doubt-solving), and Mock Tests, across
more than one education board/curriculum. The explicit, non-negotiable
design goal is **100% content coverage, verifiable at any time, for every
board/grade/subject/chapter in scope** — not "coverage we'll audit for
later."

This is a greenfield build, but it is **not a clean-room design exercise**.
Every rule in the context doc traces back to a specific, real bug found
operating Likha Poha AI, a single-board reference platform, in production.
Treat that context doc as load-bearing, not as inspirational background
reading.

---

### STEP 1 — Read First (Non-Negotiable)

1. `NEW_PLATFORM_CONTEXT.md` — full schema, pipeline, gating rules, and
   definition of done. Read it completely before writing any code,
   including the schema section. Do not paraphrase it from memory after
   the first read — re-check it before implementing each phase below.

Do not propose an alternative schema for the catalog/content tables in
§3 of that doc without first explaining, specifically, which real bug
(§3 of the context doc lists them) your alternative still prevents. If it
doesn't clearly prevent one of them, use the schema as given.

---

### STEP 2 — Confirm Scope Before Generating Any Code

Ask me these before starting Phase 0. Do not assume defaults for any of
them:

1. **First board and grade/subject scope** — which single board (e.g.
   one country's national curriculum, one state board) and which
   grades/subjects should Phase 0–3 below actually populate first? Build
   the platform to be multi-board from the schema up, but the first real
   data pass should be narrow and complete, not broad and thin.
2. **Stack** — reuse Likha Poha AI's stack (FastAPI/Python backend,
   React+Vite frontend, Postgres/Supabase, pgvector for embeddings)
   unless told otherwise. Confirm before assuming.
3. **LLM provider(s)** for paid-tier authoring/review and for live
   doubt-synthesis — which provider/model, and confirm you have (or I
   will provide) API access before Phase 2.
4. **Hosting/infra target** — where this actually deploys (affects how
   the coverage service is scheduled — cron, a queue worker, a platform
   scheduler).

Wait for answers before Phase 0.

---

### STEP 3 — Build in Phases. Each Phase Must Be Independently Demoable.

Do not attempt to build lessons, doubt, mock-tests, and the coverage
dashboard simultaneously. Build in this order; each phase is a checkpoint
— stop and confirm the phase actually works before starting the next one,
even if I don't explicitly ask.

**Phase 0 — Schema + catalog population, nothing else.**
Implement §3 of the context doc exactly. Then populate `catalog_chapters`
for the confirmed scope (Step 2 above) from official curriculum sources
**only** — never third-party study/solution sites, even for convenience.
Ship zero lesson/doubt/question content in this phase. The correct end
state is a populated, empty-of-content catalog.

**Phase 1 — Coverage dashboard, against the still-empty catalog.**
Build the coverage service (§10) and an admin view showing per-board/
grade/subject percentages. It should read 0% everywhere at the end of
this phase — that is the correct, intended state, not a bug. This
dashboard is what makes every later phase's progress visible and honest;
do not defer it until content exists.

**Phase 2 — Authoring pipeline: binder → manifest → ingest → Tier A gate.**
Build §5 and §6 of the context doc in full, including the assertion/
refutation classification in the known-pitfall check — do not ship a
naive keyword-match version "for now." Run the Source Binder across the
whole Phase-0 catalog before authoring a single chapter; fix any
source/catalog mismatches it finds while they're still cheap to fix.

**Phase 3 — Author content, chapter by chapter, gated by Tier A on every
ingestion.** Prioritize by exam weight/enrollment within the confirmed
scope. A chapter is not "done" until it passes the per-chapter definition
of done in §12 of the context doc — lessons AND doubt AND mock-test
content, together, before moving to the next chapter. Do not author all
lessons for a subject first and circle back for doubt/mock-test content
later — that produced Likha Poha AI's largest, longest-lived coverage
gaps.

**Phase 4 — Ask Doubt live serving (§9 of the context doc).**
Free tier must have no code path that reaches an LLM on a DKB miss —
verify this by reading the code, not by testing the happy path. Paid-tier
RAG synthesis with the reference-fallback safety net.

**Phase 5 — Tier B sampling + scheduled re-verification.**
Not a one-time step. Set up the recurring job before declaring any phase
"launch-ready."

---

### STEP 4 — Hard Rules (Violations Break Coverage Integrity)

| Rule | Why |
|---|---|
| Content rows reference `chapter_id` (UUID FK), never a chapter title string | String-matching chapter identity was the single most repeated bug class on Likha Poha AI |
| All bulk reads go through the one shared `fetch_all()` (§4) | An unpaginated query silently truncated at 1,000 rows and produced a false 0%-coverage reading, twice, in the same investigation |
| `protected` is checked by every bulk-mutation code path | A hand-verified fix was silently overwritten by an unrelated bulk cache-invalidation operation on Likha Poha AI |
| `actor_class='synthetic'` writes are refused, not flagged, at the data-access layer for `doubt_kb`/`question_bank` | Synthetic test data reached real students for months before being caught by a screenshot, not by any system |
| `section_markers` required per declared language before that language is authored | A hardcoded-English extraction tool silently returned zero results for every non-English chapter, with no error |
| Source binding is content-based (extracted heading vs. `canonical_title`), never position/filename-based | Position-based pairing silently matched a chapter to the wrong source book when two related config lists were reordered independently |
| Known-pitfall checks classify assertion vs. refutation before flagging | Naive keyword matching flagged content for *correcting* a mistake as if it stated the mistake — the most repeated false-positive class observed |
| No free-tier LLM anywhere in authoring or review code paths | Quality on the actual product (what a student is taught) cannot be guaranteed from a free-tier model; enforce via allowlist + CI lint, not a comment |
| A syllabus revision creates a new `curriculum_editions` + `catalog_chapters` rows, never an in-place edit | In-place renumbering left duplicate content at stale offsets and served wrong-numbered chapters to students for an extended period on Likha Poha AI |

---

### STEP 5 — What NOT To Do

| Anti-pattern | Do this instead |
|---|---|
| Computing "does chapter X exist" by scanning content tables | Query `catalog_chapters` — it is the only source of truth for existence |
| A second, quick, unpaginated query "just for this one admin script" | Use `fetch_all()`. Every time. No exceptions for scripts. |
| Flagging a known-pitfall match without checking if the sentence refutes it | Run the assertion/refutation classifier; surface the matched span, not a bare boolean |
| Authoring a subject's lessons, shipping it, and coming back for Ask Doubt/mock-tests later | Gate "done" per chapter on all three surfaces together (§12) |
| Pairing a new chapter to a source PDF by list position or file order | Bind by extracted heading text vs. `canonical_title` (§5.1) |
| Letting a QA/E2E script authenticate as a normal user and write through the normal path | Route synthetic actors to a separate test schema; let the data-access layer refuse them on the real tables |
| Treating a curriculum revision as "update the chapter numbers" | New `curriculum_editions` row + `migrated_from` lineage (§3) |
| Building the lesson viewer before the coverage dashboard | Dashboard first, against an honestly-empty catalog (Phase 1 before Phase 3) |

---

### STEP 6 — Definition of Done

Use §12 of `NEW_PLATFORM_CONTEXT.md` verbatim — per-chapter and
platform-wide checklists. Do not consider any phase complete until every
box in the relevant checklist is genuinely checked, not assumed.

---

### NOW

1. Confirm you've read `NEW_PLATFORM_CONTEXT.md` in full.
2. Answer the Step 2 scoping questions back to me.
3. Wait for my answers before starting Phase 0.

---
