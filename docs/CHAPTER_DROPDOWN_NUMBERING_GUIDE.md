# Chapter Dropdown Cleanup + Numbering Guide

**Purpose:** a reusable, step-by-step process for cleaning up any grade's
subject dropdowns to (a) show only the chapters that are actually in the
current NCERT textbook, and (b) prefix every chapter with a consistent
"Chapter N: " label, where N is its 1-based position in that textbook.

This process was first applied to **Grade 11** (all 13 subjects) on
2026-08-01, triggered by a student-visible bug report: the Grade 11
History dropdown showed 11 chapters when the current (rationalised)
textbook only has 7. The same underlying problem — extra/stale chapters
polluting the dropdown, and inconsistent (sometimes prefixed, sometimes
bare) chapter naming — is very likely present in Grade 12 and any other
grade with GPT-5.5-authored content, so use this guide to repeat the
fix there.

## Why chapters can end up wrong in the dropdown

Two independent problems compound:

1. **Extra/stale chapters.** A subject's `rag_documents` table can
   accumulate chapters that should NOT be student-selectable:
   - Old-edition chapters left over from before an NCERT syllabus
     rationalisation (e.g. Grade 11 History's "From the Beginning of
     Time", "The Central Islamic Lands", "Confrontation of Cultures",
     "The Industrial Revolution" — all real chapters in an *older*,
     pre-rationalisation 11-theme edition of the book, but not in the
     current 7-theme edition).
   - NCERT Exemplar supplementary chapters accidentally uploaded
     alongside the main textbook (e.g. "Exemplar: The Living World").
     These should be excluded from the dropdown, not offered as regular
     chapters.
   - A chapter that was never actually in the book at all, apparently
     due to a stale/wrong config entry (e.g. Grade 11 Accountancy's
     "Bill of Exchange" — no PDF file for it exists in this NCERT
     edition).
2. **Inconsistent naming.** Some subjects' chapters were ingested with a
   `"Chapter N: <title>"` prefix already baked into `rag_documents
   .chapter` (e.g. Grade 11 Mathematics), while others were ingested
   with a bare title (e.g. Grade 11 History, before this fix). Students
   see an inconsistent dropdown across subjects, and any code comparing
   chapter strings exactly (e.g. `syllabus_chapter_overrides`) must be
   kept in sync with whichever form is actually live.

## The two reusable scripts

Both live in `backend/scripts/` and were written for the Grade 11 fix,
but are grade-agnostic (just pass a different `--grade`).

### 1. `audit_grade_chapter_mismatches.py` (read-only)

Compares each subject's **live** `rag_documents.chapter` values against
the **verified ground-truth** chapter list in
`scripts/prepare_gpt55_prompts.py::CHAPTER_NAME_OVERRIDES` (this is the
same list already used elsewhere in the codebase to determine the
correct chapter order for image backfill — see
`docs/GPT55_LESSON_UPDATE_STATUS.md` for how that list itself gets
verified against actual PDF content before you trust it).

```bash
cd backend
python3 scripts/audit_grade_chapter_mismatches.py --grade "Grade 12"
# or for one subject:
python3 scripts/audit_grade_chapter_mismatches.py --grade "Grade 12" --subject History
```

For each subject it reports:
- **EXTRA**: chapters live in `rag_documents` but NOT in the ground
  truth list — these are the candidates to hide/delete.
- **MISSING**: chapters in ground truth with no live row yet — purely
  informational (nothing to fix, just not ingested).
- the correctly-ordered **keep** list.

**IMPORTANT — always review this report before running the fix script.**
If `CHAPTER_NAME_OVERRIDES` itself is stale or wrong for a subject (as
it was for Grade 11 Accountancy before that book's own fix — see
`docs/GPT55_LESSON_UPDATE_STATUS.md`), the audit's "EXTRA" list will be
wrong too. Cross-check any EXTRA chapter against the actual NCERT source
PDF before deleting it — do not blindly trust the ground-truth list
without spot-checking at least one flagged chapter per subject.

### 2. `number_and_fix_grade_chapters.py` (makes changes)

For every subject with ground truth configured for the given grade:

1. Deletes every EXTRA chapter's data cleanly, in dependency order:
   `rag_chunks` → `rag_visual_assets` → `lesson_cache` →
   `lesson_chapter_doc` → `rag_documents`.
2. Renames every KEPT chapter's stored label to `"Chapter N: <title>"`
   (N = 1-based position in ground truth), across **all four** tables
   that store a `chapter` column: `rag_documents`, `lesson_cache`,
   `lesson_chapter_doc`, `rag_visual_assets`.
3. Rewrites the `syllabus_chapter_overrides` row for
   `(grade, "CBSE", subject)` with the new numbered, ordered list — this
   is the row the student-facing dropdown actually reads from (see
   `app/routes/syllabus.py::apply_syllabus_overrides`).

```bash
cd backend
# ALWAYS dry-run first and read the full output before applying:
python3 scripts/number_and_fix_grade_chapters.py --grade "Grade 12" --dry-run
# then apply:
python3 scripts/number_and_fix_grade_chapters.py --grade "Grade 12" --force
```

You can also target one subject at a time with `--subject <Name>` for
either mode — useful for reviewing/fixing subjects incrementally rather
than the whole grade in one shot.

## Why renaming is SAFE for retrieval (do not skip this reasoning)

Before trusting this process, verify these two things are true for your
codebase (they were both true when this guide was written):

1. **`rag_chunks` (actual RAG-retrieved content chunks) are keyed by
   `document_id`, never by the `chapter` text column.** Renaming
   `rag_documents.chapter` does NOT require touching `rag_chunks` at
   all — confirmed via `app/services/rag_service.py`:
   `db.table("rag_chunks").delete().eq("document_id", document_id)` is
   the only chapter-scoped rag_chunks operation in the codebase; chunk
   *retrieval* filters by `filter_chapter` only as an RPC parameter
   passed straight through to `match_rag_chunks`, and
   `strip_chapter_display_prefix()` in the same file already strips a
   `"Part N - "` display prefix before that RPC call — this is a
   pre-existing, unrelated prefix-stripping mechanism, separate from the
   "Chapter N: " numbering this guide adds.
2. **`chapter_doc_service.py` already has built-in fallback logic for
   exactly this "Chapter N: <title>" vs bare-title mismatch**, added
   2026-07-31 specifically because Grade 11 Mathematics/Biology chapters
   were ingested with the prefix already baked in while others weren't.
   See `_strip_display_prefixes()` and the `_query_suffix()` /
   `bare`/`candidates` logic inside `_fetch_step_rows()` and the
   `rag_visual_assets` lookup function in that file — both `lesson_cache`
   and `rag_visual_assets` lookups already try BOTH the exact dropdown
   label AND the bare (prefix-stripped) form, so even a *partially*
   completed rename (e.g. you've fixed 3 of 5 subjects) will not break
   any chapter's lessons or images.

Because of (2), this rename is safe to apply gradually, subject by
subject, without any risk of a half-migrated state breaking retrieval.
Renaming every table consistently (as `number_and_fix_grade_chapters.py`
does) is still strongly preferred — it keeps the stored data itself
correct and stops relying on the fallback logic as a safety net — but a
partial/interrupted run will not corrupt anything in the meantime.

## CRITICAL gotcha: don't compare with the fuzzy `normalize()` function
when deciding whether to actually perform a rename

`audit_grade_chapter_mismatches.py::normalize()` strips "Chapter N: "
prefixes for *fuzzy matching* purposes (so it can tell that live
`"Sets"` matches ground-truth `"Chapter 1: Sets"`). This is correct and
necessary for detecting EXTRA/MISSING/keep_ordered chapters.

**But `number_and_fix_grade_chapters.py::rename_chapter_everywhere()`
must NOT use that same fuzzy `normalize()` function to decide whether a
rename is a no-op.** Doing so was an actual bug hit live during the
Grade 11 fix: for a subject like Mathematics, where ground truth already
has `"Chapter 1: Sets"` baked in but the live `rag_documents.chapter`
was still bare `"Sets"`, `normalize("Sets") == normalize("Chapter 1:
Sets")` evaluates `True`, so the rename was silently skipped — leaving
the actual database untouched even though the dropdown override (which
IS written unconditionally) already showed the numbered form. The fix
was to compare the **exact, non-normalized** strings
(`old_label == new_label`) to decide whether a real rename is needed,
and to make sure `keep_ordered` (the list passed into the renamer)
always contains the **actual live label**, not the ground-truth label —
see the code comments in both scripts for the exact reasoning, dated
2026-08-01.

**Always run `audit_grade_chapter_mismatches.py` again immediately after
applying the fix** to confirm 0 EXTRA remain and every kept chapter now
matches ground truth exactly (which it always will after a correct
rename, since ground truth is now the literal stored value).

## CRITICAL: you MUST restart the backend server afterward

`app/routes/syllabus.py` maintains an **in-process** cache
(`_RAG_CACHE`) of `rag_documents` rows with a 30-minute TTL, used to
build every dropdown. Editing the database directly (as both scripts
above do) has **zero effect on an already-running backend server's
warm cache** — a one-off script invocation runs in its own separate,
short-lived Python process and its own fresh cache, which tells you
nothing about what the actual running server (that the frontend talks
to) will serve.

After running `number_and_fix_grade_chapters.py --force`:

```bash
# Find and kill whatever is holding port 8000 (adjust the port if different):
lsof -ti:8000 | xargs kill -9

# Restart uvicorn. NOTE: invoking venv/bin/uvicorn directly can fail with
# "No such file or directory" if this venv's script shebang has a stale
# absolute path baked in (confirmed on this machine) -- use `python3 -m
# uvicorn` to route around a broken shebang entirely:
cd backend
nohup ./venv/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 \
    --app-dir "$(pwd)" > /tmp/backend_server.log 2>&1 &

# Confirm it started cleanly:
sleep 5 && cat /tmp/backend_server.log
```

Only after this restart will `curl http://localhost:8000/api/syllabus`
(or the actual frontend dropdown) reflect the fix.

## Full step-by-step checklist (copy this for each new grade)

1. Confirm `CHAPTER_NAME_OVERRIDES` in `scripts/prepare_gpt55_prompts.py`
   has an entry for `(grade, subject)` for every subject you intend to
   fix. If a subject is missing, you must first verify and add its
   ground-truth chapter list there (cross-check against the actual
   source PDF's own printed chapter headings — do not trust an
   assumption).
2. Run `audit_grade_chapter_mismatches.py --grade "<Grade>"` (no
   `--subject` = all configured subjects) and read the FULL output.
3. For every subject reporting EXTRA chapters, spot-check at least one
   flagged chapter directly against the source PDF (or against
   `rag_documents`'s own history/creation date) to confirm it really is
   stale/wrong, not a legitimate chapter that's simply missing from
   `CHAPTER_NAME_OVERRIDES`.
4. Run `number_and_fix_grade_chapters.py --grade "<Grade>" --dry-run`
   and read the FULL output — confirm every planned rename and deletion
   looks correct (especially watch for any `'X: Y' -> 'X: X: Y'`
   double-prefix pattern, which indicates the ground-truth list itself
   already has a baked-in "Chapter N: " prefix for that subject — the
   scripts already strip this via `strip_existing_chapter_prefix()`,
   but re-verify after any future edits to the ground-truth list).
5. Run `number_and_fix_grade_chapters.py --grade "<Grade>" --force`.
6. Run `audit_grade_chapter_mismatches.py --grade "<Grade>"` again —
   confirm 0 EXTRA remain and every subject reports "Clean".
7. Spot-check `rag_documents`, `lesson_cache`, `lesson_chapter_doc`, and
   `rag_visual_assets` directly for 2-3 subjects to confirm the
   `chapter` column was actually updated in every table (not just the
   dropdown override) — see the Python snippets used during the Grade
   11 fix for the exact query pattern.
8. Restart the backend server (see above) and verify via
   `curl http://localhost:8000/api/syllabus` that the dropdown for each
   fixed subject now shows the correct, numbered chapter list.
9. Spot-check `get_or_convert_chapter_doc(...)` for 3-4 chapters across
   different subjects (using their NEW numbered chapter names) to
   confirm lessons and images still load correctly after the rename.
10. Run the regression suite:
    `pytest -k "syllabus or chapter_doc or rag" -q` — must show 0
    failures.
11. Document the fix (extras removed, subjects affected, any
    ground-truth corrections needed) in
    `docs/GPT55_LESSON_UPDATE_STATUS.md`, following the same format used
    for the Grade 11 fix.

## Known good/bad chapters found during the Grade 11 fix (for reference)

Not exhaustive — re-run the audit for the current state of any grade
before relying on this list, since more content may have been ingested
since this was written.

| Grade | Subject | Extra chapters removed | Notes |
|---|---|---|---|
| 11 | History | From the Beginning of Time; The Central Islamic Lands; Confrontation of Cultures; The Industrial Revolution | Pre-rationalisation 11-theme edition chapters; current book has only 7 themes |
| 11 | Accountancy | Bill of Exchange | No PDF for this chapter exists in the current edition at all |
| 11 | Biology | 22 "Exemplar: ..." chapters | NCERT Exemplar supplementary book, not the main textbook |
| 11 | Mathematics | 16 "Exemplar: ..." chapters | Same as above; also had inconsistent bare-vs-prefixed naming across chapters before this fix |
| 11 | Psychology | (none — 0 live chapters) | No content ingested yet for this subject; nothing to number |


## Additional gotcha found during the Grade 9/10 fix (2026-08-01)

**Always check for multiple `syllabus_chapter_overrides` rows across
different `mode` values (e.g. "CBSE" vs "State Board") for the
SAME subject before treating an audit EXTRA finding as real.** The
current audit script does not filter by mode, so a subject that
legitimately serves two different chapter sets to two different board
modes (confirmed for Grade 9 English: "CBSE" mode serves the newer
Kaveri reader, "State Board" mode serves the older Beehive reader)
will have the second mode's real, correct chapters flagged as EXTRA
against the first mode's ground truth. Deleting these would be a serious
mistake -- always run:

```python
admin_client.table("syllabus_chapter_overrides").select("mode,chapters").eq("grade", grade).eq("subject", subject).execute()
```

and check for more than one row before deleting ANY chapter the audit
flags as EXTRA.

**Grade 9's ground truth lives directly in `app.data.syllabus.SYLLABUS`
(no override needed), unlike Grade 10/11/12** which only have a
placeholder ("Uploaded Book Content") in syllabus.py and therefore
need a `CHAPTER_NAME_OVERRIDES` entry instead. Both scripts now check
`CHAPTER_NAME_OVERRIDES` first and fall back to a real (non-placeholder)
`syllabus.py` entry via `get_ground_truth()`/`discover_subjects()` --
this matches the same precedence order already used elsewhere in the
codebase.

**If a subject uses a non-Latin script (e.g. Hindi), make sure
`normalize()` strips that language's own word for "Chapter N:"**, not
just the English form -- Hindi uses "अध्याय N:" ("अध्याय" =
"chapter"). Confirmed missing for Hindi during the Grade 9 fix; check
for other languages (e.g. Sanskrit) before trusting the audit's EXTRA/
MISSING output for any non-English subject.


## Third gotcha found during the Grade 5-8 fix (2026-08-01)

**Before deleting ANY chapter the audit flags as EXTRA, manually inspect
its title character-by-character against the closest-matching MISSING
ground-truth entry -- the ground-truth list itself can simply be wrong
(a spelling/OCR-transcription error), not the live data.** Confirmed for
several Hindi chapters across Grade 6/7/8: CHAPTER_NAME_OVERRIDES
contained garbled Devanagari text (broken conjuncts, transposed
characters) that did not match the live, correctly-spelled chapter
titles at all, even though both clearly refer to the same real chapter.
Also confirmed for Grade 7 English ("Chapter Travel and Adventure"
in ground truth vs "Unit 4: Travel and Adventure" live -- a known,
already-documented naming inconsistency elsewhere in the codebase).

**Rule of thumb**: an EXTRA + a MISSING entry that are clearly the SAME
chapter (same approximate meaning/position, just spelled/formatted
differently) is a ground-truth data problem, NOT a stale-chapter
problem -- do not delete. A genuine stale/extra chapter has NO
corresponding MISSING entry at all (it is simply not part of the
ground-truth book), which is how the real Grade 5 Maths ("The Fish
Tale", "Shapes and Angles" -- leftover unrelated test chapters) and
all the Exemplar-chapter cases were correctly distinguished from this
new spelling-error class of false positive.
