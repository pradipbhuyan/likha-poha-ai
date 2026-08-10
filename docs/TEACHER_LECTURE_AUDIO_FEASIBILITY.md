# Teacher Lecture Scripts + TTS Audio — Feasibility Plan

> Planning doc only — no code changes made. Written 2026-08-10 alongside the
> Grade 5-8 lesson-plan pedagogy rollout (see
> `docs/LESSON_PLAN_PEDAGOGY_ROLLOUT_STATUS.md`).

## Goal

For each (grade, subject, chapter), generate a **teacher lecture script**
derived from the chapter's lesson plan and lesson content, with an option to
convert it to audio using the TTS setup already in the app.

## Verdict

Feasible, and cheaper than a from-scratch feature — the two hard parts
(grounded lesson content, a working TTS pipeline) already exist. The real
work is one design decision (what the script should actually say) and one
broken wire (the old student-facing audio player) that needs reconnecting.

## What already exists (reusable as-is)

| Piece | Where | Status |
|---|---|---|
| Grounded lesson content per chapter | `lesson_cache` table | 4,595 rows across all grades — the raw material |
| Structured lesson plans per chapter | `backend/app/data/lesson_plan_bank/` | 220 re-authored under the new pedagogy rules (Grade 5-8); Grade 9-12 still on the old template or missing entirely |
| TTS engine | `backend/app/services/tts_service.py` | Microsoft Edge TTS (`edge_tts` package) — free, no API key required. `clean_text_for_tts()` (lines 12-302) already strips markdown/LaTeX/unicode math into speakable text |
| Audio caching | `backend/app/services/audio_cache_service.py` | Cloudflare R2 (10GB free tier, zero egress) + a `lesson_audio_cache` tracking table on Supabase. Cache key = `sha256(grade\|subject\|chapter\|step_title\|voice\|rate)` |
| Prewarm tooling | `backend/scripts/prewarm_lesson_audio.py` | Batch-generates + uploads audio offline; admin UI (`AdminCacheManagementPage.jsx`) already shows per-grade cache coverage and has a "Build Audio" trigger |
| Multi-voice support | `voice` param on `POST /api/tts/generate` (`backend/app/routes/tts.py:39`) | Already accepts arbitrary Edge TTS voice strings (default `en-IN-NeerjaNeural`). Passing `hi-IN-SwaraNeural` etc. for Hindi content works today — no new plumbing needed, just a mapping table |

**Real measured cost** (from the existing prewarm run, `prewarm_lesson_audio.py:20-22`): 155 audio files ≈ 240MB, ~18.7s average generation time per file. Scales roughly linearly with content length.

## The one thing that's broken regardless of scope

The student-facing "Listen" button was **removed in a prior refactor**.
`frontend/src/api/tts.js` still has working `generateSpeech()` /
`getCachedAudioUrl()` functions, but nothing in the current lesson UI
(`ChapterJourneyView.jsx`, `StudyRenderer.jsx`) calls them anymore — the only
test that covered it is `describe.skip`'d with a TODO
(`frontend/src/tests/LessonsPage.test.jsx:52-81`). So "add lecture audio"
isn't purely additive: a player UI needs to be rebuilt regardless of which
scope option below is chosen.

## The core design decision: what does the script actually say?

A lesson plan is a **teacher's planning document**, not a **spoken script**.
It contains structural noise a TTS voice shouldn't read verbatim — heading
labels ("Differentiation Strategies"), timing annotations ("(15 minutes)"),
and content that's an instruction *to the teacher* rather than something
said *to students* (e.g. the "For students needing additional support"
bullet). It also covers non-monologue time (pair work, waiting for student
answers) that can't become a straight narration.

Two approaches:

1. **Fresh LLM-authored script per chapter**, mirroring the lesson-plan
   pipeline (grounded prompt → author → validate → ingest). Highest
   quality/most natural delivery, but doubles the authoring effort just
   completed for lesson plans — 803 chapters, another full rollout cycle —
   and creates a second document that can drift out of sync with the lesson
   plan if either is edited later without the other.
2. **Deterministic extraction from the already-structured
   `lesson_plan_markdown`** (recommended). Every plan already has parseable
   sections (`## Learning Objectives`, `### Introduction & Hook`, etc.) — a
   template pass can pull the teacher-facing spoken content (hook question,
   chunked direct-instruction explanation, worked examples) and drop the
   meta-content (differentiation notes, timing labels, misconception
   headers). No new LLM authoring pipeline required, stays in sync with the
   lesson plan by construction since it's derived from it, and reuses
   `clean_text_for_tts()` for the final markdown-to-speech cleanup. Lower
   "natural flow" than a bespoke script; an optional light LLM smoothing
   pass (one cheap call per chapter) can fix transitions without
   re-authoring content from scratch.

## Scale reality check

| Grade band | Chapters | Notes |
|---|---|---|
| 5-8 | 220 | Lesson plans already exist under the new rules — extraction-based script generation is close to free here |
| 9-12 | 559 | Lesson plans not yet re-authored — script generation would need to wait for, or be bundled with, that rollout |
| **Total** | **~803 chapters** | Measured directly from `lesson_cache` (distinct grade/subject/chapter), 2026-08-10 |

Per-grade chapter counts (`lesson_cache`, `mode=CBSE`, `status=active`):
Grade 5: 47 · Grade 6: 68 · Grade 7: 62 · Grade 8: 67 · Grade 9: 103 ·
Grade 10: 137 · Grade 11: 160 · Grade 12: 159.

**Audio storage**: extrapolating from the measured ~1.55MB average per
`lesson_cache` step to a full chapter-length narration lands around
1.5-2MB per chapter. Full rollout (803 chapters) is roughly **8-12GB** —
right at or slightly over the R2 free tier's 10GB ceiling. Not a blocker,
but worth knowing before generating all 803 at once; mp3 bitrate reduction
or prioritizing Grade 5-8 first comfortably avoids it.

## Recommended shape of the work (in order)

1. **Decide scope**: is this a *teacher rehearsal tool* ("hear a model
   delivery before class") or a *student-facing narration channel*
   (replacing/supplementing the dead "Listen" feature)? This changes where
   the player lives in the UI and whether Hindi-voice selection is a
   nice-to-have or a hard requirement.
2. Build the deterministic plan→script extractor (pure Python, no LLM) —
   natural home is alongside `backend/app/services/lesson_plan_quality_checks.py`,
   since that module already parses the same section structure.
3. Add a `subject/grade → voice` mapping (Hindi subject → an `hi-IN-*` Edge
   TTS voice, else the existing default) — a small addition to
   `tts_service.py` / `audio_cache_service.py`, no architecture change.
4. Reuse `audio_cache_service.py` unmodified — add a new cache-key dimension
   (or a `content_type: "lecture"` field) so lecture audio doesn't collide
   with the existing per-step `lesson_cache` audio cache keys.
5. Rebuild a minimal player component — start on the teacher's lesson-plan
   page (`TeacherLessonPlanPage.jsx`) rather than the student lesson page,
   since that's lower-risk and directly serves a "hear the lecture" teacher
   workflow without touching the student-facing experience.
6. Prewarm Grade 5-8 first (220 chapters, lesson-plan content already
   exists) using a script modeled on `prewarm_lesson_audio.py`. Treat Grade
   9-12 as blocked on the lesson-plan rewrite reaching those grades.

## Open questions to resolve before building

- Teacher rehearsal tool vs. student-facing narration channel (drives UI
  placement and voice-selection priority).
- Extraction-based script vs. fresh LLM-authored script (cost/effort vs.
  naturalness trade-off above).
- Whether to gate full-rollout audio generation on staying under the R2
  10GB free tier, or accept a small paid tier if it's exceeded.
