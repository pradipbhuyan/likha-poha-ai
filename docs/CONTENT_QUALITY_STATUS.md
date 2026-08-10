# Content Quality Status — Source of Truth

_Last updated: 2026-08-07_

This is the current, living answer to "how good is our content, everywhere,
right now." It covers all four student-facing content surfaces — Lessons,
Ask Doubt, Mock Tests, Exam Prep Center — across every grade (5–12) and
subject. For the detailed history of *how* the lesson-content pipeline was
built (manifests, Tier A/B audits, GPT-5.5 authoring), see
`docs/LESSON_CONTENT_QUALITY_REVIEW_PLAN.md`; this document is the
higher-level, more frequently updated status snapshot that plan file's
final section (§4s) now points to.

**Published report (visual, interactive):**
https://claude.ai/code/artifact/68f37ff6-ddcd-4028-9283-b76a0943c0be

---

## 1. Platform-wide numbers (as of 2026-08-07, post action-plan + 3 follow-up rounds)

| Surface | Coverage | What it measures |
|---|---|---|
| Lessons | **100%** | % of 707 tracked chapters (Grades 5–12) with all 5 lesson steps live (Concept introduction, Core explanation, Worked examples, Exam-style problems, Revision and recap) |
| Ask Doubt (DKB) | **100%** | % of chapters with at least one cached Doubt Knowledge Base entry (fast-path cache hit; see caveat below) |
| Mock Tests | **100%** | % of chapters with at least one active `question_bank` question |
| Exam Prep Center | separate axis | 7,361 published questions across JEE Main, NEET UG, CUET UG, SAT, IELTS, TOEFL iBT (Grade 11–12 only, scoped by exam board, not NCERT chapter) |

**Zero grade/subject combinations remain below 100% composite — 57 of 57 clean.**

Four rounds ran same-day on 2026-08-07: the original 5-phase action plan
(§6) took the platform from 99.0% / 91.5% / 97.5% to 99.9% / 97.3% /
99.2%; a same-day follow-up round (§6 Phase 6) closed the Hindi Ask Doubt
gap and got the remaining list down to 3; a GPT-5.5 batch return (§6
Phase 7) closed Mock Tests to 100% and got the list down to exactly 1;
a second GPT-5.5 return (§6 Phase 8) closed the last chapter, Grade 12
Hindi's "Silver Wedding," bringing the platform to 100/100/100.

**Important caveat on the Ask Doubt number:** it measures the *cache
fast-path* only. `search_doubt_kb()` already has a documented, working
fallback — if no chapter-scoped DKB entry exists, it broadens to a
subject-level semantic search, and if that also misses, the live
synthesis path (`build_synthesized_doubt_answer()`) answers the question
grounded in RAG-retrieved textbook chunks. Moot now that DKB coverage is
100% everywhere, but still true of how the metric works.

To regenerate these numbers: the pull script and rating computation live
in this session's scratchpad and are not yet checked into `backend/scripts/`
as a reusable tool — see §7 for what a checked-in version should guard
against.

---

## 2. History — false alarms found and fixed (2026, several weeks through 2026-08-07)

Three separate patterns of unreliable "quality alarm" were investigated
and fixed at the source over the preceding weeks. This section exists so
a fresh reviewer doesn't rediscover — or worse, re-trust — the same false
positives.

### 2.1 Tier A `known_pitfall` audit — confirmed systematic false-positive pattern

`backend/scripts/audit_chapter_boundary.py`'s post-ingest audit flags a
lesson step CRITICAL when it contains vocabulary matching a registered
"known pitfall" pattern. Across every GPT-5.5 authoring batch processed in
this period, **every single CRITICAL `known_pitfall` finding was manually
spot-checked against the actual generated prose, and every one was a false
positive** — the content correctly *refuted* the misconception rather than
asserting it (e.g. flagged for "a wholly owned subsidiary is automatically
the best entry mode," the actual sentence read "the chapter does not
present one mode as universally best"). The check fires on topic/vocabulary
proximity, not on assertion vs. refutation — a known limitation first
documented in the pilot (`LESSON_CONTENT_QUALITY_REVIEW_PLAN.md` §4a) that
evidently still applies.

**Standing rule:** a Tier A CRITICAL `known_pitfall` flag is a prompt to
go read the actual passage, not a verdict. The contamination and
coverage-gap checks in the same audit are mechanical (keyword presence,
banned-phrase co-occurrence) and have not shown this failure mode — treat
those as reliable.

### 2.2 Doubt Knowledge Base pollution from internal test traffic

Internal QA/E2E test scripts (synthetic usernames, run against the same
`answer_doubt()` / `answer_lesson_follow_up()` code path as real students)
were writing their test questions into the live `doubt_kb` table via the
normal `store_in_doubt_kb()` caching call. Those synthetic Q&A pairs were
then served to real students as if they were genuine prior answers —
this is what produced the garbled, cross-subject "Ask Doubt" answers and
nonsensical suggested-question chips a screenshot review surfaced.

**Fix (in `backend/app/services/tutor_service.py`):**
```python
_TEST_HARNESS_USERNAME_PREFIXES = ("E2ESim-",)
_TEST_HARNESS_USERNAMES = {"qa_harness"}

def _is_e2e_sim_user(username: str) -> bool: ...
```
Both DKB-write call sites now check `not _is_e2e_sim_user(username)` before
storing. ~314 already-polluted rows were retroactively deleted.

### 2.3 Fabricated "Previous Year Question" chapters in the mock-test bank

The same class of test-harness leakage had written fictitious PYQ-labeled
chapter entries into `question_bank`, surfacing as real-looking but
invented exam-history questions. ~630 fake rows (same non-realistic-
username signature as 2.2) were identified and removed once the DKB root
cause was traced.

### 2.4 NCERT curriculum-alignment audit — chapter *lists*, not chapter content

Separately from the two pollution bugs above, a full audit compared every
one of the 57 grade/subject chapter lists against the current official
NCERT textbook — fetched directly from **ncert.nic.in only**, never
third-party exam-prep or solution sites (this was a hard rule throughout,
enforced after early drafts nearly leaned on secondary sources for
convenience). Found: chapters dropped by the 2023 NCERT curriculum
rationalization that were still live on the platform, current chapters
missing entirely, and several stale/garbled titles. All findings were
fixed — deprecated content removed (after checking `student_progress` for
real student data first — none was ever lost), missing chapters authored
via the GPT-5.5 handover pipeline and ingested, titles corrected. Detailed
per-subject log lives in the published audit report referenced from
`LESSON_CONTENT_QUALITY_REVIEW_PLAN.md` §4s.

**A bug caught mid-fix, worth keeping as a general lesson:** ingesting a
new "International Trade" chapter for Grade 12 Geography nearly overwrote
an unrelated, already-correct chapter (the companion book's own,
differently-scoped "International Trade" chapter) because both chapters'
*raw* titles hashed to the same `lesson_cache` cache key — the existing
chapter's cache key had been frozen from before it was relabeled with a
"Chapter N:" prefix, so the new bare-titled chapter's key collided with
it. Caught by computing the cache key before ingest and checking for an
existing match. **Any future chapter ingest for a subject with duplicate-
sounding titles across companion books should do this check first.**

---

## 3. Bugs caught while building *this* report (2026-08-07)

Documented here deliberately, because they are the same category of
mistake as everything in §2 — an automated number that looked authoritative
but wasn't, caught only by cross-checking against known ground truth
before trusting it.

1. **Unpaginated Supabase query silently truncated results past 1,000
   rows.** The first data pull queried `lesson_cache` for all of Grade
   11's active rows (14 subjects) in one unfiltered request and got back
   exactly 1,000 rows — Supabase's default page cap. This silently
   dropped Political Science, Sociology, and Psychology entirely,
   reporting a false "0% lesson coverage" for a subject (Political
   Science) that had been fully fixed earlier the same day. Caught by
   spot-checking a subject already known-good against the report's
   output — they disagreed, which is what surfaced the bug. Fixed by
   paginating every bulk fetch (`lesson_cache`, `doubt_kb`,
   `question_bank`, `exam_prep_questions`) with `.range()` loops.
2. **Bare-vs-prefixed chapter-label mismatch undercounted Ask Doubt
   coverage.** `doubt_kb` frequently stores chapter names without the
   "Chapter N:" prefix used everywhere else (e.g. "Laws of Motion" vs.
   "Chapter 5: Laws of Motion"), which made Grade 11/12 DKB coverage look
   near-zero even for subjects with hundreds of cached entries.
   `search_doubt_kb()` already handles this gracefully at query time (see
   its docstring — it falls back from an exact chapter filter to a
   subject-level search specifically because of this known inconsistency).
   The report's own chapter-matching logic was updated to strip the same
   prefix before comparing, to avoid reporting a formatting difference as
   a content gap.

**Both bugs are the same shape:** an aggregate number was trusted before
being checked against a known-good data point. The standing rule from
§2.1 — verify before reporting — applied to the report itself, not just
to the content it was reporting on.

---

## 4. Standing verification rules (apply to all future content/quality work)

1. Any automated "critical" flag is read against the actual source
   passage/data before being reported as a real defect. This applies to
   Tier A `known_pitfall` findings and to any future automated audit —
   treat a flag as a lead, not a conclusion.
2. NCERT chapter lists are verified only against the official
   `ncert.nic.in` PDFs — never third-party exam-prep or solution sites.
3. Bulk DB reads paginate explicitly past Supabase's 1,000-row default
   cap; never trust an unfiltered `.execute().data` length as a true
   total without checking. This bug recurred twice in one day even after
   being documented in §3 — treat any ad-hoc one-off Python check as
   suspect by default and default to a paginated helper, not just the
   promoted report script.
4. Chapter-label matching normalizes known formatting inconsistencies
   (bare vs. "Chapter N:"-prefixed, book-part prefixes) before treating a
   mismatch as a real gap.
5. Before deleting any content, `student_progress` is checked for real
   (non-synthetic) student data first; genuine records are preserved even
   when the underlying chapter content is retired.
6. Before ingesting new chapter content, compute its cache key and check
   for a live collision first — especially for subjects where companion
   books share similarly-named chapters.
7. In `prepare_gpt55_prompts.py`, `CHAPTER_NAME_OVERRIDES`'s title order
   and `BOOK_SOURCES`'s `parts` PDF-processing order must stay in sync
   for any multi-book subject — they're paired by position, not by name.
   Whenever one is reordered (e.g. to fix chapter numbering), check the
   other. Don't just trust a generated prompt's grounding text matches
   its claimed chapter — for new/rarely-touched chapters in multi-book
   subjects, spot-check that the source PDF is actually about the
   claimed topic before sending the prompt out.

---

## 5. Full gap inventory — before, through each phase, and now

**Before action plan** (57 subjects audited, 22 below 100% composite),
**after Phase 1–5** (7 remaining), **after Phase 6** (3 remaining), and
**after Phase 7** (1 remaining, Grade 12 Hindi at composite 98.1 — Lessons
94.4%, DKB 100%, Mock Test 100%): all preserved in git history of this
file — not repeated here since every row closed.

**After Phase 8: zero gaps remain. 57 of 57 subjects at 100/100/100.**

Grade 12 Hindi's Chapter 16 "Silver Wedding" — the one remaining gap —
was authored, verified, and ingested in Phase 8. See §6 Phase 8 for the
full account, including the transport-corruption issue that delayed it
by one round and the visual-asset spot-check that confirmed the ingest
was clean.

---

## 6. Action plan — executed 2026-08-07 (same day as drafted)

All 5 phases ran the same day this plan was written. Platform composite
moved from 99.0% / 91.5% / 97.5% to 99.9% / 97.3% / 99.2% (Lessons / Ask
Doubt / Mock Tests).

### Phase 1 — DKB backfill from existing lesson content — DONE, 2,965 new entries

`seed_doubt_kb_from_lessons.py --all-grades` (dry-run first, confirmed
counts matched, then live): scanned 5,027 active lesson rows across all
8 grades, extracted 6,542 candidate Q&A pairs, stored 2,965 new (3,577
already existed and were skipped — the dedup happens on question text
*before* any embedding call, so no wasted API cost on duplicates from
earlier DKB work). Distribution matched the gap analysis exactly: 1,127
new in Grade 11, 1,517 in Grade 12. Re-ran targeted for Grade 9 after
Phase 3 landed new grammar chapters, picking up 48 more.

### Phase 2 — Grade 11 Mathematics mock-test gap — DONE, 240 questions

All 8 missing chapters (Chapter 7 Binomial Theorem through Chapter 14
Probability) authored via `prepare_gpt55_question_prompts.py` →
GPT-5.5 → `ingest_gpt55_question_bank_output.py`, 30 questions each (10
Easy / 10 Medium / 10 Hard). All 8 dry-run-verified before the live
ingest. Grade 11 Mathematics mock-test coverage: 64.3% → 100%.

### Phase 3 — Grade 9 English grammar topics — DONE, 5 chapters authored

All 5 (Determiners, Reported Speech (Statements and Questions), Commands/
Requests/Exclamations in Reported Speech, Clauses, Active and Passive
Voice) authored via `prepare_gpt55_prompts_grammar.py` → GPT-5.5 →
`ingest_gpt55_chapter_output.py`. Tier A audit: 4 of 5 clean, 2
`known_pitfall` flags spot-checked and confirmed false positives (same
established pattern — the content corrects the error, doesn't assert it).
One real, minor finding: "Reported Speech" is thinner on question-
transformation examples than statement examples (a `coverage_gap` flag,
which has been a reliable check type all session, unlike `known_pitfall`)
— not severe enough to block, but a genuine candidate for a future
top-up pass, not a false alarm. Grade 9 English lesson coverage: 68.8% →
100%.

### Phase 4 — Small remaining tails — DONE

Grade 9 Maths Ch4: the archived "Exam-style problems" row turned out to
be legitimate, correctly-scoped content that had simply never been
reactivated (verified by reading it — factually correct, on-topic,
covers factorization/expansion via algebraic identities as expected) —
reactivated directly via a `status` flip, no re-authoring needed. This
was a different situation from the similar-looking Grade 9 Maths Ch1
case, which turned out to already have an active bare-titled duplicate —
each was checked individually rather than assuming the pattern was the
same. Grade 11/12 Biology, Grade 7 Social Science, Grade 8 Maths
mock-test gaps: all authored and ingested (240 more questions across 7
chapters, same pipeline as Phase 2).

**Unplanned but important find, caught mid-phase — Grade 11 Biology
Chapters 17–19 were broken for students, not just missing mock-test
questions.** Generating the question-bank prompts for these 3 chapters
failed with "no authored lesson content (or the string didn't match
exactly)." Investigation found the content existed but was mislabeled:
`lesson_cache` had "Locomotion and Movement" / "Neural Control and
Coordination" / "Chemical Coordination and Integration" filed as Chapters
20/21/22, while `rag_documents` — which drives the student-facing chapter
dropdown — already correctly listed them as Chapters 17/18/19. Since
`lesson_cache` lookups are exact-match by cache key (no fuzzy fallback,
unlike DKB), any student opening those 3 chapters was hitting a permanent
cache miss. There were also 6 dead duplicate-content rows squatting on
the correct 13/14/15/17/18/19 labels (duplicating content that already
existed correctly at 11/12/13/14/15/16). Checked `student_progress`
first, per standing rule: 3 unrelated pre-rationalization chapters
("Transport in Plants," "Mineral Nutrition," "Digestion and Absorption" —
not in the current syllabus at all) had one real record each and were
left untouched; everything else affected had zero progress rows and was
safe to modify. **Fix:** deleted the 6 dead duplicates, relabeled
20/21/22 → 17/18/19 across `lesson_cache`, `doubt_kb`, `question_bank`,
and `rag_visual_assets`, cleared the stale `lesson_chapter_doc` cache.
Grade 11 Biology is now a clean, fully-working 19/19 — and its 3
previously-inaccessible chapters now also have mock-test questions
(Phase 4's original goal for this subject).

### Phase 5 — Verify and re-baseline — DONE (this document + the published report)

Coverage pull re-run after each batch (Phase 1, after Phase 4's Biology
fix, and after Phase 3's grammar chapters landed). Every Tier A
`known_pitfall` flag raised during this round's ingests was individually
read against the actual generated prose before being trusted — all
false positives, consistent with §2.1.

### Phase 6 — Follow-up round, same day — DONE, DKB now 100%, gaps 7 → 3

Run immediately after Phase 5, closing out the remaining 7-item gap list
from §5.

**Hindi Ask Doubt gap fixed at the source, not just prompted around.**
Direct inspection (`lesson_cache` content for Grades 6, 7, 8, 9, 12
Hindi) confirmed: Hindi lessons translate section *headers* to Hindi
("## हल किया गया उदाहरण" for Worked example, "## शीघ्र जाँच प्रश्न" for
Quick check question) but keep the internal `Question:`/`Answer:`/
`Explanation:` field labels in English. `seed_doubt_kb_from_lessons.py`'s
two extraction regexes only matched the English header, so Phase 1 found
zero extractable pairs for Hindi despite the content being fully
extractable. Patched both regexes to accept either header language:

```python
r"##\s*(?:Worked example|हल किया गया उदाहरण)\s*\n(.*?)(?=\n##\s|\Z)"
r"##\s*(?:Quick check question|शीघ्र जाँच प्रश्न)\s*\n(.*?)(?=\n##\s|\Z)"
```

Dry-run confirmed the impact per grade before going live (540–2,008
candidate pairs extracted per grade depending on chapter count). Ran live
across all 5 affected grades: **574 new DKB entries** (130 + 100 + 100 +
120 + 124 across Grades 6/7/8/9/12 respectively). Platform Ask Doubt
coverage: 97.3% → **100%**.

**Grade 12 Hindi's missing chapter identified and prompted.** Chapter 16
"Silver Wedding" (from the Vitan supplementary reader — position 3 in
this subject's `CHAPTER_NAME_OVERRIDES`, i.e. genuinely the 16th chapter
once Aroh's 15 come first) was confirmed absent from `lesson_cache` with
no mislabeled duplicate elsewhere in the subject, unlike the Grade 11
Biology case in Phase 4 — a different failure mode (never authored,
not mislabeled) that needed checking individually rather than assumed
the same. Prompt + source PDF generated and delivered.

**Grade 9 English grammar mock-test prompts generated for all 5
chapters**, working around a script limitation: two chapter titles
containing commas ("Commands, Requests and Exclamations in Reported
Speech" and "Clauses (Noun, Adjective and Adverb Clauses)") broke
`prepare_gpt55_question_prompts.py`'s naive `--chapters` comma-split CLI
parsing. Worked around by importing and calling the script's `run()`
function directly with a proper Python list, rather than patching the
CLI parser for a one-off need.

**Another pagination false alarm — caught before it caused damage, same
bug class as §3.** A quick unpaginated spot-check of Grade 12 Business
Studies' `question_bank` suggested 4 chapters were missing mock-test
questions (Directing, Controlling, Financial Management, Marketing)
instead of the 1 the report already showed. Recognized the same
1,000-row Supabase page cap from §3's earlier finding, re-checked with
the paginated helper, and confirmed only **Chapter 10 "Marketing"** is
actually missing — the original report was correct, the fast recheck
was wrong. This is the second time in the same document that an
unpaginated query produced a false reading; **any ad-hoc DB spot-check
during this kind of work should default to the paginated helper, not
just the bulk report script.** Prompt generated for the correct single
chapter.

All 3 remaining gaps (§5) are now GPT-5.5 prompts delivered and awaiting
authoring — none require further investigation.

### Phase 7 — GPT-5.5 batch (`prompt_outputs_7_json.zip`) returned — DONE, Mock Test now 100%, gaps 3 → 1

A 7-file batch covering all 3 Phase 6 prompts (5 grammar MCQ, 1
Marketing MCQ, 1 Silver Wedding lesson) came back the same day. The
batch's own validation report flagged one file with a WARNING (not an
error): the "Silver Wedding" lesson prompt's manifest said chapter
`Silver Wedding`, but the supplied source text was actually Kunwar
Narayan's "Kavita ke Bahane" and "Baat Seedhi Thi Par" — two different
Aroh poems. GPT-5.5 correctly refused to fabricate Silver Wedding content
and instead generated output grounded only in the (wrong) supplied text,
flagging the mismatch rather than silently producing plausible-looking
but fabricated content under the right chapter label.

**Root cause, found in `backend/scripts/prepare_gpt55_prompts.py`:** this
subject's `CHAPTER_NAME_OVERRIDES` list was ordered Vitan-first (`Jujh`,
`Ateet Mein Dabe Paon`, `Silver Wedding`, then the 15 Aroh titles), but
its `BOOK_SOURCES` entry lists `parts` Aroh-first (`lhar1`, 15 chapters,
then `lhvt1`, 3 chapters). `get_chapter_list()` returns titles in
override-list order; `_resolve_pdf_path_for_chapter()` resolves the
Nth PDF by walking `parts` in their listed order. Position 3 in the
title list ("Silver Wedding") therefore resolved to the 3rd PDF in
`parts` order — `lhar103.pdf`, the 3rd **Aroh** chapter — instead of
`lhvt101.pdf`, the correct Vitan PDF.

**Why "Jujh" and "Ateet Mein Dabe Paon" (positions 1–2) never hit this
bug:** both were already correctly ingested from an earlier point when
the two lists were still mutually consistent (both Vitan-first) — the
inconsistency was only introduced later, when `parts` was reordered
Aroh-first (as part of the earlier numbering fix — see
`LESSON_CONTENT_QUALITY_REVIEW_PLAN.md`) without correspondingly
reordering `CHAPTER_NAME_OVERRIDES`. This only surfaced now because
"Silver Wedding" was the first *new* prompt generated for this subject
since the lists diverged.

**Fix:** verified the correct chapter identity of each Vitan PDF by
reading their raw extracted text directly — `lhvt101.pdf` is "सिल्वर
वेडिंग" (Silver Wedding, Manohar Shyam Joshi), `lhvt102.pdf` is "जूझ"
(Jujh), `lhvt103.pdf` is "अतीत में दबे पाँव" (Ateet Mein Dabe Paon) —
confirming both the correct assignment and that the two already-live
chapters had, in fact, been correctly matched all along. Reordered
`CHAPTER_NAME_OVERRIDES` to Aroh-first (15) then Vitan-in-lhvt101/102/
103-order (3), matching `BOOK_SOURCES`. Regenerated the Silver Wedding
prompt with the corrected config and verified its bundled source PDF's
MD5 hash matches `lhvt101.pdf` exactly before redelivering it.

**The other 6 files were clean** — dry-run verified, then ingested live:
180 new mock-test questions (30 each × 5 grammar chapters + Marketing).
Platform Mock Test coverage: 99.2% → **100%**. Combined with Phase 6's
DKB fix, only Grade 12 Hindi's Chapter 16 lesson content remains open
(§5), with a corrected, verified prompt already delivered.

The full backend regression suite (2,137 tests) was re-run after the
Phase 6 script patch and passed clean before this phase began.

### Phase 8 — Corrected Silver Wedding output returned — DONE, platform at 100/100/100

The first attempt to deliver the corrected "Silver Wedding" GPT-5.5
output was pasted directly into the conversation rather than provided as
a file. It was unusable: diagnosed the garbled Devanagari as genuine
byte-level data loss during transport, not a simple encoding mismatch.
Confirmed by decoding the raw bytes — a UTF-8 continuation byte for a
Devanagari combining mark (virama/matra) was missing mid-sequence,
producing an invalid byte pattern (`e0 a5` directly followed by a space
instead of the required continuation byte). This wasn't reversible by
swapping encodings; reconstructing the intended character would have
meant guessing, which risks silently writing fabricated Hindi text into
a live student-facing lesson — exactly the failure mode this whole
report exists to catch, not cause. Declined to process it and asked for
the file to be delivered as an actual upload instead, matching every
other batch this session.

The re-delivered package (`16_silver_wedding_package.zip`) parsed clean
with correct Devanagari throughout. Its own validation report confirmed
`"source_match": "Correct: the supplied PDF is Silver Wedding by Manohar
Shyam Joshi"` — the Phase 7 config fix held on the regenerated prompt.
Dry-run confirmed resolution to `document_id=1366` / `lhvt101.pdf`, the
already-verified-correct source. Ingested live: **0 Tier A findings
across all 5 lesson steps.**

The ingest's image-curation step flagged all 20 PDF pages via its
"photo-essay fallback" mode (used when a PDF has no explicit `Fig N.N`
captions to derive precise labels from) with a generic "Photograph"
caption on every page — worth verifying rather than assuming, since 20/20
pages flagged as "photographs" in a prose short story is exactly the
shape of a fallback-heuristic false positive. Downloaded and visually
inspected two pages directly (the chapter-opening page and a mid-chapter
page): both are genuine, correctly-matched illustrations/page-design
elements from the actual right PDF — the fallback's *page selection* was
correct, only its generic *caption* is imprecise ("Photograph" instead of
e.g. "decorative border" or "chapter illustration"). Not a content-
accuracy defect, left as a minor cosmetic item, not blocking.

Relabeled from the bare authoring title "Silver Wedding" to
`Chapter 16: Silver Wedding` to match the subject's numbering convention
across `lesson_cache`, `doubt_kb`, `question_bank`, `rag_visual_assets`.
This relabel also carried forward 25 pre-existing `doubt_kb` rows dated
2026-06-25 (`source: "prewarmed"`, English-language) from an earlier
admin DKB-prewarm run that predates this chapter ever having lesson
content — topically correct but inconsistent with the subject's Hindi-
language convention. Pre-existing, not introduced by this work, and out
of scope for this round — left as-is, noted here for a future pass.

**Final coverage pull: 100% Lessons, 100% Ask Doubt, 100% Mock Tests —
0 of 57 grade/subject combinations below 100% composite.** All 707
tracked chapters across Grades 5–12 are fully covered on every surface.

---

## 7. Not yet done (process, not content)

- The data-pull script that produced §1's numbers lives in a scratch
  location from this session, not yet checked into `backend/scripts/` as
  a reusable, re-runnable tool. Promoting it (with the pagination and
  label-normalization fixes already baked in) would let this report — and
  the Phase 5 re-baseline step above — be regenerated on demand instead of
  manually re-run each time.
- This report's coverage metric is deliberately deterministic (does the
  content exist and reach students), not a full Tier-B LLM semantic
  re-grade of every chapter platform-wide — that remains cost-prohibitive
  at ~700 chapters × 5 steps (see `LESSON_CONTENT_QUALITY_REVIEW_PLAN.md`
  §4c's cost analysis, which still applies).
- Grade 12 Hindi's "Silver Wedding" chapter carries 25 `doubt_kb` rows in
  English from a 2026-06-25 admin prewarm run (§6 Phase 8) — topically
  correct but inconsistent with the subject's Hindi-language convention.
  Not urgent (coverage is 100%, answers are correct), but a candidate for
  a future audit of whether other Hindi/language-subject DKB rows have
  the same pre-dating-content, wrong-language pattern.
