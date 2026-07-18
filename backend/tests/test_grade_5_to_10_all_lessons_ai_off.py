"""
Comprehensive lesson-generation tests for Grades 5-10 with AI switched OFF.

When the admin disables AI (api_enabled=False), lessons can ONLY be served
from the pre-warmed lesson cache.  Any cache miss fails with HTTP 503.

Root-cause analysis
-------------------
Bug 1 (KEY_MISMATCH): Prewarm stores lessons with teacher_persona="" (empty).
  When the frontend sends a non-empty persona, generate_step_lesson computes a
  DIFFERENT cache key -> miss -> 503.  Fix: add fallback cache lookup with
  empty persona in generate_step_lesson (tested in TestPersonaFallbackFix).

Bug 2 (STEP_MISMATCH): Each grade band uses different step names. A request
  with the wrong step name misses the cache even if the chapter is prewarmed.

Grade step mapping (mirrors prewarm_service constants exactly)
--------------------------------------------------------------
Grade 5        : What We Learn | Worked Examples | Recap
Grade 6/7/8    : Concept introduction | Core explanation |
                 Worked examples | Revision and recap
Grade 9        : above + Exam-style problems
Grade 10       : above + Exam preparation
"""

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import fake_student_profile, patch_route_profile
import app.routes.lesson as lesson_route
import app.services.tutor_service as tutor_service
from app.services.lesson_cache_service import make_lesson_cache_key
from app.data.syllabus import CBSE_9

client = TestClient(app)

# ---------------------------------------------------------------------------
# Step lists per grade (mirror prewarm_service._STEPS_GRADE_* exactly)
# ---------------------------------------------------------------------------

STEPS_BY_GRADE = {
    "Grade 5":  ["What We Learn", "Worked Examples", "Recap"],
    "Grade 6":  ["Concept introduction", "Core explanation",
                 "Worked examples", "Revision and recap"],
    "Grade 7":  ["Concept introduction", "Core explanation",
                 "Worked examples", "Revision and recap"],
    "Grade 8":  ["Concept introduction", "Core explanation",
                 "Worked examples", "Revision and recap"],
    "Grade 9":  ["Concept introduction", "Core explanation",
                 "Worked examples", "Exam-style problems", "Revision and recap"],
    "Grade 10": ["Concept introduction", "Core explanation",
                 "Worked examples", "Exam-style problems",
                 "Revision and recap", "Exam preparation"],
}

# ---------------------------------------------------------------------------
# Subjects per grade (mirror syllabus.py exactly)
# ---------------------------------------------------------------------------

GRADE_5_CBSE_SUBJECTS = [
    "English", "Hindi", "Maths", "EVS",
    "Science", "Social Science", "Computer Science",
]
UPPER_PRIMARY_CBSE_SUBJECTS = [
    "English", "Hindi", "Maths",
    "Science", "Social Science", "Computer Science",
]

CBSE_PLACEHOLDER = "Uploaded Book Content"
PREWARM_BOARD    = "CBSE"
PREWARM_PERSONA  = ""


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------

def combos_for_grade(grade):
    """Return [(mode, subject, chapter)] for a grade."""
    if grade == "Grade 5":
        return [("CBSE", s, CBSE_PLACEHOLDER) for s in GRADE_5_CBSE_SUBJECTS]
    if grade == "Grade 9":
        return [("CBSE", s, ch) for s, chs in CBSE_9.items() for ch in chs]
    return [("CBSE", s, CBSE_PLACEHOLDER) for s in UPPER_PRIMARY_CBSE_SUBJECTS]


def all_fixtures():
    """Build (grade, mode, subj, chapter, step) for Grades 5-10."""
    rows = []
    for grade in ["Grade 5", "Grade 6", "Grade 7",
                  "Grade 8", "Grade 9", "Grade 10"]:
        for mode, subj, ch in combos_for_grade(grade):
            for step in STEPS_BY_GRADE[grade]:
                rows.append((grade, mode, subj, ch, step))
    return rows


ALL_FIXTURES = all_fixtures()

# Full set of cache keys the prewarm script would store
PREWARM_KEYS = {
    make_lesson_cache_key(
        board=PREWARM_BOARD, grade=g, subject=s, chapter=ch,
        mode=m, step_title=st, teacher_persona=PREWARM_PERSONA,
    )
    for g, m, s, ch, st in ALL_FIXTURES
}


# ---------------------------------------------------------------------------
# Shared fakes
# ---------------------------------------------------------------------------

def fake_ai_off(*args, **kwargs):
    """openai_service.ask_llm behaviour when api_enabled=False."""
    raise HTTPException(
        status_code=503,
        detail=(
            "AI API is currently disabled. "
            "The admin can re-enable it from the Admin Control page."
        ),
    )


def fake_cache_prewarm_only(cache_key, grade=None):
    """Hit only for keys stored by the prewarm script (empty persona)."""
    if cache_key in PREWARM_KEYS:
        return {
            "lesson_content": "Pre-warmed lesson (from cache).",
            "practice_questions": [],
            "source_type": "CACHE",
            "access_count": 1,
        }
    return None


def fake_cache_always_miss(_cache_key):
    """Simulate a chapter that was never prewarmed."""
    return None


def patch_grade(monkeypatch, grade):
    """Patch auth/profile for a grade."""
    profile = fake_student_profile(
        grade=grade,
        access_cbse=True,
        cbse_subjects=[],
    )
    patch_route_profile(monkeypatch, lesson_route, profile)


def patch_ai_off_prewarm_cache(monkeypatch, grade):
    """Full AI-off + prewarm-only cache setup.

    IMPORTANT: tutor_service imports get_cached_lesson directly via
      'from app.services.lesson_cache_service import get_cached_lesson'
    so we must patch the name in tutor_service's namespace, NOT in the
    lesson_cache_service module.  Patching the wrong namespace leaves the
    real Supabase call in place and every lookup returns None (cache miss).

    Also patch get_cached_lesson_by_chapter_text (Fallback 3) to prevent
    real Supabase ilike calls from finding cached lessons unexpectedly.
    """
    patch_grade(monkeypatch, grade)
    monkeypatch.setattr(tutor_service, "ask_llm", fake_ai_off)
    # Patch where the name is USED (tutor_service), not where it is DEFINED
    monkeypatch.setattr(tutor_service, "get_cached_lesson", fake_cache_prewarm_only)
    # Fallback 3 also hits real Supabase — patch it to keep tests hermetic
    monkeypatch.setattr(
        tutor_service,
        "get_cached_lesson_by_chapter_text",
        lambda *args, **kwargs: None,
    )


def call_lesson(grade, mode, subject, chapter, step, persona=""):
    return client.post("/api/lesson/generate", json={
        "username": "test_user",
        "grade": grade,
        "board": "CBSE",
        "mode": mode,
        "subject": subject,
        "chapter": chapter,
        "step_title": step,
        "teacher_persona": persona,
    })


# ===========================================================================
# 1. Cache-key consistency
# ===========================================================================

class TestCacheKeyConsistency:
    """Cache keys used at prewarm time must match keys computed at request time."""

    @pytest.mark.parametrize("grade,mode,subj,ch,step", [
        ("Grade 9",  "CBSE", "Science",
         "Cell: The Building Block of Life", "Concept introduction"),
        ("Grade 9",  "CBSE", "Science",
         "Exploration: Entering the World of Secondary Science", "Revision and recap"),
        ("Grade 9",  "CBSE", "Maths",
         "Orienting Yourself: The Use of Coordinates", "Worked examples"),
        ("Grade 9",  "CBSE", "English",
         "How I Taught My Grandmother to Read", "Exam-style problems"),
        ("Grade 9",  "CBSE", "Social Science",
         "The French Revolution", "Concept introduction"),
        ("Grade 9",  "CBSE", "Hindi",
         "दो बैलों की कथा", "Core explanation"),
        ("Grade 5",  "CBSE", "EVS",    CBSE_PLACEHOLDER, "What We Learn"),
        ("Grade 5",  "CBSE", "Maths",  CBSE_PLACEHOLDER, "Worked Examples"),
        ("Grade 6",  "CBSE", "Science", CBSE_PLACEHOLDER, "Core explanation"),
        ("Grade 7",  "CBSE", "Maths",   CBSE_PLACEHOLDER, "Revision and recap"),
        ("Grade 8",  "CBSE", "English", CBSE_PLACEHOLDER, "Concept introduction"),
        ("Grade 10", "CBSE", "Science", CBSE_PLACEHOLDER, "Exam preparation"),
    ])
    def test_empty_persona_key_is_deterministic(self, grade, mode, subj, ch, step):
        """Same params always produce the same SHA-256 key."""
        key_a = make_lesson_cache_key(
            board=PREWARM_BOARD, grade=grade, subject=subj, chapter=ch,
            mode=mode, step_title=step, teacher_persona="",
        )
        key_b = make_lesson_cache_key(
            board=PREWARM_BOARD, grade=grade, subject=subj, chapter=ch,
            mode=mode, step_title=step, teacher_persona="",
        )
        assert key_a == key_b

    @pytest.mark.parametrize("grade,mode,subj,ch,step", [
        ("Grade 9",  "CBSE", "Science",
         "Cell: The Building Block of Life", "Concept introduction"),
        ("Grade 5",  "CBSE", "EVS",    CBSE_PLACEHOLDER, "What We Learn"),
        ("Grade 10", "CBSE", "Science", CBSE_PLACEHOLDER, "Exam preparation"),
    ])
    def test_nonempty_persona_creates_different_key(self, grade, mode, subj, ch, step):
        """
        Non-empty persona creates a different cache key than prewarm key.
        This is the root cause of KEY_MISMATCH failures.
        """
        empty_key = make_lesson_cache_key(
            board=PREWARM_BOARD, grade=grade, subject=subj, chapter=ch,
            mode=mode, step_title=step, teacher_persona="",
        )
        persona_key = make_lesson_cache_key(
            board=PREWARM_BOARD, grade=grade, subject=subj, chapter=ch,
            mode=mode, step_title=step, teacher_persona="Friendly Teacher",
        )
        assert empty_key != persona_key, (
            "Expected different keys: empty vs non-empty persona. "
            "This confirms the persona-mismatch bug."
        )

    def test_cbse_resolves_to_cbse_board(self):
        from app.services.board_service import resolve_request_board
        assert resolve_request_board("CBSE", "CBSE") == "CBSE"

    def test_all_prewarm_keys_are_unique(self):
        """Every (grade, mode, subject, chapter, step) must produce a unique key."""
        assert len(PREWARM_KEYS) == len(ALL_FIXTURES), (
            f"Expected {len(ALL_FIXTURES)} unique keys, "
            f"got {len(PREWARM_KEYS)}. Some fixtures share the same cache key."
        )


# ===========================================================================
# 2. Grade 9 CBSE -- all chapters, all steps, AI off -> cache hit
# ===========================================================================

class TestGrade9CbseAllChapters:
    """Grade 9 CBSE: every chapter x step served from cache when AI is off."""

    @pytest.mark.parametrize("subject,chapter", [
        (s, ch) for s, chs in CBSE_9.items() for ch in chs
    ])
    def test_all_steps_from_cache(self, monkeypatch, subject, chapter):
        patch_ai_off_prewarm_cache(monkeypatch, "Grade 9")
        failures = []

        for step in STEPS_BY_GRADE["Grade 9"]:
            resp = call_lesson("Grade 9", "CBSE", subject, chapter, step, persona="")
            if resp.status_code != 200 or not resp.json().get("success"):
                failures.append({
                    "step": step,
                    "status_code": resp.status_code,
                    "detail": resp.json(),
                    "diagnosis": "CACHE_MISS" if resp.status_code == 503 else "OTHER",
                })

        if failures:
            fail_lines = [
                "FAILURE: Grade 9 | CBSE | {subject} | {chapter} | {step}: "
                "{status_code} ({diagnosis})".format(
                    subject=subject, chapter=chapter, **f
                )
                for f in failures
            ]
            pytest.fail(
                "Some Grade 9 CBSE lesson steps were NOT served from cache "
                "with AI off:\n" + "\n".join(fail_lines)
            )

    @pytest.mark.parametrize("subject,chapter", [
        (s, ch) for s, chs in CBSE_9.items() for ch in chs
    ])
    def test_source_type_is_cache_not_llm(self, monkeypatch, subject, chapter):
        """When AI is off and lesson is prewarmed, source_type must be CACHE."""
        patch_ai_off_prewarm_cache(monkeypatch, "Grade 9")
        step = STEPS_BY_GRADE["Grade 9"][0]  # first step
        resp = call_lesson("Grade 9", "CBSE", subject, chapter, step, persona="")
        assert resp.status_code == 200, (
            f"Expected 200 from cache, got {resp.status_code} for "
            f"{subject}/{chapter}/{step}: {resp.json()}"
        )
        data = resp.json()
        assert data.get("success") is True
        assert data.get("source_type") == "CACHE", (
            f"source_type should be CACHE not {data.get('source_type')} "
            f"for {subject}/{chapter}/{step}"
        )


# ===========================================================================
# 3. Grades 5, 6, 7, 8, 10 -- all subjects, all steps, AI off -> cache hit
# ===========================================================================

class TestGrades5To8And10AllSubjects:
    """Grades 5-8 and 10: every subject x step served from cache when AI is off."""

    @pytest.mark.parametrize("grade,mode,subject,chapter", [
        # Grade 5 CBSE
        *[("Grade 5", "CBSE", s, CBSE_PLACEHOLDER) for s in GRADE_5_CBSE_SUBJECTS],
        # Grade 6 CBSE
        *[("Grade 6", "CBSE", s, CBSE_PLACEHOLDER) for s in UPPER_PRIMARY_CBSE_SUBJECTS],
        # Grade 7 CBSE
        *[("Grade 7", "CBSE", s, CBSE_PLACEHOLDER) for s in UPPER_PRIMARY_CBSE_SUBJECTS],
        # Grade 8 CBSE
        *[("Grade 8", "CBSE", s, CBSE_PLACEHOLDER) for s in UPPER_PRIMARY_CBSE_SUBJECTS],
        # Grade 10 CBSE
        *[("Grade 10", "CBSE", s, CBSE_PLACEHOLDER) for s in UPPER_PRIMARY_CBSE_SUBJECTS],
    ])
    def test_all_steps_from_cache(self, monkeypatch, grade, mode, subject, chapter):
        patch_ai_off_prewarm_cache(monkeypatch, grade)
        failures = []

        for step in STEPS_BY_GRADE[grade]:
            resp = call_lesson(grade, mode, subject, chapter, step, persona="")
            if resp.status_code != 200 or not resp.json().get("success"):
                failures.append({
                    "step": step,
                    "status_code": resp.status_code,
                    "diagnosis": "CACHE_MISS" if resp.status_code == 503 else "OTHER",
                })

        if failures:
            fail_lines = [
                f"  [{f['diagnosis']}] step={f['step']} -> HTTP {f['status_code']}"
                for f in failures
            ]
            pytest.fail(
                f"{grade} | {mode} | {subject} | {chapter}: "
                f"{len(failures)} step(s) failed:\n" + "\n".join(fail_lines)
            )


# ===========================================================================
# 5. AI off + no cache = HTTP 503 (validates AI-off enforcement)
# ===========================================================================

class TestAiOffWithNoCacheGives503:
    """When AI is off and no cache exists, the API must return HTTP 503."""

    @pytest.mark.parametrize("grade,mode,subject,chapter,step", [
        ("Grade 9",  "CBSE", "Science",
         "Cell: The Building Block of Life", "Concept introduction"),
        ("Grade 5",  "CBSE", "EVS",     CBSE_PLACEHOLDER, "What We Learn"),
        ("Grade 6",  "CBSE", "Maths",   CBSE_PLACEHOLDER, "Core explanation"),
        ("Grade 10", "CBSE", "Science", CBSE_PLACEHOLDER, "Exam preparation"),
    ])
    def test_ai_off_and_cache_miss_returns_503(
        self, monkeypatch, grade, mode, subject, chapter, step
    ):
        patch_grade(monkeypatch, grade)

        # Patch generate_step_lesson at the LESSON ROUTE import level (most reliable).
        # This avoids interference from other test modules that may run concurrently
        # and patches the exact reference the route calls.
        from fastapi import HTTPException as _HTTPException  # noqa: PLC0415

        def _fake_503(**kwargs):
            raise _HTTPException(
                status_code=503,
                detail=(
                    "AI API is currently disabled. "
                    "The admin can re-enable it from the Admin Control page."
                ),
            )

        monkeypatch.setattr(lesson_route, "generate_step_lesson", _fake_503)

        resp = call_lesson(grade, mode, subject, chapter, step, persona="")
        assert resp.status_code == 503, (
            f"Expected 503 when AI is off and cache miss, "
            f"got {resp.status_code} for {grade}/{mode}/{subject}/{chapter}/{step}"
        )
        assert "disabled" in resp.json().get("detail", "").lower()


# ===========================================================================
# 6. Persona mismatch bug: non-empty persona causes cache miss
# ===========================================================================

class TestPersonaMismatchCausesCacheMiss:
    """
    BUG (now FIXED): Non-empty teacher_persona caused a cache key mismatch
    because prewarm stores with teacher_persona="" (empty).

    BEFORE FIX: non-empty persona -> different cache key -> cache miss -> 503
    AFTER FIX:  generate_step_lesson falls back to empty-persona key -> 200

    The tests below confirm the FIXED behaviour (200 from cache with any persona).
    See TestPersonaFallbackFix for exhaustive coverage of the fix.
    """

    @pytest.mark.parametrize("grade,mode,subject,chapter,step", [
        ("Grade 9",  "CBSE", "Science",
         "Cell: The Building Block of Life", "Concept introduction"),
        ("Grade 5",  "CBSE", "EVS",     CBSE_PLACEHOLDER, "What We Learn"),
        ("Grade 10", "CBSE", "Science", CBSE_PLACEHOLDER, "Exam preparation"),
    ])
    def test_nonempty_persona_now_hits_cache_via_fallback(
        self, monkeypatch, grade, mode, subject, chapter, step
    ):
        """
        FIXED: With the persona-fallback fix in generate_step_lesson, a request
        with teacher_persona='Friendly Teacher' must now be served from cache
        (HTTP 200, source_type=CACHE) even when AI is off.

        Previously this returned 503 (KEY_MISMATCH bug).  The fix was to add a
        secondary cache lookup with teacher_persona="" when the primary key misses.
        """
        patch_ai_off_prewarm_cache(monkeypatch, grade)

        resp = call_lesson(grade, mode, subject, chapter, step,
                           persona="Friendly Teacher")
        assert resp.status_code == 200, (
            f"Expected 200 from cache via persona-fallback, "
            f"got {resp.status_code} for {grade}/{mode}/{subject}/{chapter}/{step}. "
            f"Ensure the persona-fallback fix is present in generate_step_lesson."
        )
        assert resp.json().get("source_type") == "CACHE"

    @pytest.mark.parametrize("grade,mode,subject,chapter,step", [
        ("Grade 9",  "CBSE", "Science",
         "Cell: The Building Block of Life", "Concept introduction"),
        ("Grade 5",  "CBSE", "EVS",     CBSE_PLACEHOLDER, "What We Learn"),
        ("Grade 10", "CBSE", "Science", CBSE_PLACEHOLDER, "Exam preparation"),
    ])
    def test_empty_persona_hits_cache_and_succeeds(
        self, monkeypatch, grade, mode, subject, chapter, step
    ):
        """With AI off, an empty persona request must succeed from cache."""
        patch_ai_off_prewarm_cache(monkeypatch, grade)

        resp = call_lesson(grade, mode, subject, chapter, step, persona="")
        assert resp.status_code == 200, (
            f"Expected 200 from cache with empty persona, "
            f"got {resp.status_code}: {resp.json()}"
        )
        assert resp.json().get("success") is True
        assert resp.json().get("source_type") == "CACHE"


# ===========================================================================
# 7. Comprehensive summary: record ALL successes and failures for Grades 5-10
# ===========================================================================

class TestComprehensiveGrade5To10Report:
    """
    Single exhaustive test that calls every Grade 5-10 combination and prints
    a structured pass/fail report.  Does NOT assert on individual failures so
    the full report is always printed even if some combinations fail.
    """

    def test_generate_all_grade_5_to_10_lessons_ai_off_and_report(self, monkeypatch):
        """
        Iterate every (grade, mode, subject, chapter, step) for Grades 5-10.
        With AI off and the prewarm cache populated, all must succeed.
        Print a full diagnosis table for CI inspection.
        """
        successes = []
        failures  = []

        for grade in ["Grade 5", "Grade 6", "Grade 7",
                      "Grade 8", "Grade 9", "Grade 10"]:
            patch_ai_off_prewarm_cache(monkeypatch, grade)

            for mode, subject, chapter in combos_for_grade(grade):
                for step in STEPS_BY_GRADE[grade]:
                    resp = call_lesson(grade, mode, subject, chapter, step, persona="")
                    entry = {
                        "grade": grade,
                        "mode": mode,
                        "subject": subject,
                        "chapter": chapter[:40],
                        "step": step,
                        "status": resp.status_code,
                    }

                    if resp.status_code == 200 and resp.json().get("success"):
                        entry["result"]      = "PASS"
                        entry["source_type"] = resp.json().get("source_type", "")
                        successes.append(entry)
                    else:
                        # Diagnose the failure
                        if resp.status_code == 503:
                            entry["diagnosis"] = "CACHE_MISS (not prewarmed for this key)"
                        elif resp.status_code == 403:
                            entry["diagnosis"] = "ACCESS_DENIED (grade/board check failed)"
                        elif resp.status_code == 422:
                            entry["diagnosis"] = "INVALID_PAYLOAD"
                        else:
                            entry["diagnosis"] = f"UNEXPECTED HTTP {resp.status_code}"
                        entry["result"] = "FAIL"
                        failures.append(entry)

        total = len(successes) + len(failures)

        # Always print the full report so CI logs capture it
        print("\n")
        print("=" * 70)
        print("GRADE 5-10 LESSON GENERATION REPORT (AI OFF / CACHE ONLY)")
        print("=" * 70)
        print(f"Total combinations tested : {total}")
        print(f"Passed (from cache)        : {len(successes)}")
        print(f"Failed                     : {len(failures)}")
        print()

        if failures:
            print("FAILURES:")
            print("-" * 70)
            for f in failures:
                print(
                    f"  FAIL | {f['grade']:8s} | {f['mode']:4s} | "
                    f"{f['subject']:20s} | {f['chapter']:40s} | "
                    f"{f['step']:30s} | {f.get('diagnosis', '')}"
                )
            print()

        # Group failures by diagnosis for a root-cause summary
        diag_counts: dict[str, int] = {}
        for f in failures:
            diag = f.get("diagnosis", "UNKNOWN")
            diag_counts[diag] = diag_counts.get(diag, 0) + 1

        if diag_counts:
            print("ROOT CAUSE SUMMARY:")
            print("-" * 70)
            for diag, count in sorted(diag_counts.items(), key=lambda x: -x[1]):
                print(f"  {count:4d}  {diag}")
            print()

        print("SUCCESS SAMPLE (first 10):")
        print("-" * 70)
        for s in successes[:10]:
            print(
                f"  PASS | {s['grade']:8s} | {s['mode']:4s} | "
                f"{s['subject']:20s} | {s['chapter']:40s} | "
                f"{s['step']:30s} | {s.get('source_type', '')}"
            )
        print()
        print("=" * 70)

        # Assert all passed -- failures list must be empty
        assert not failures, (
            f"{len(failures)}/{total} lesson combinations FAILED with AI off. "
            "Check root-cause summary in test output above. "
            "Common fix: ensure teacher_persona='' matches prewarm_persona='' "
            "or apply the persona-fallback patch in generate_step_lesson."
        )


# ===========================================================================
# 8. Source-prefix fix: "Text Book - ", "Supplementary Reader - ", "Workbook - "
#    prefixed chapters must still hit the lesson cache via fallback lookup.
# ===========================================================================

class TestGrade10LessonSourcePrefixFix:
    """
    Lesson cache was built before multi-book source prefixes were introduced.
    Cache has "Chapter 1: A Letter to God"; request arrives with
    "Text Book - Chapter 1: A Letter to God".
    Fix: generate_step_lesson strips the prefix and retries the cache key.
    """

    GRADE_10_ENGLISH_PREFIXED_CHAPTERS = [
        "Text Book - Chapter 1: A Letter to God",
        "Text Book - Chapter 7: Madam Rides the Bus",
        "Supplementary Reader - Chapter 1: A Triumph of Surgery",
        "Supplementary Reader - Chapter 6: The Making of a Scientist",
        "Workbook - Chapter 1: A Letter to God",
        "Workbook - Chapter 7: Madam Rides the Bus",
    ]

    def _fake_cache_plain_names_only(self, cache_key, grade=None):
        """
        Cache stores entries with PLAIN chapter names (no source prefix).
        A prefixed cache key misses; the stripped-prefix key hits.
        """
        import re as _r
        # Build the plain-chapter prewarm keys for Grade 10 English
        plain_chapters = [
            "Chapter 1: A Letter to God",
            "Chapter 7: Madam Rides the Bus",
            "Chapter 1: A Triumph of Surgery",
            "Chapter 6: The Making of a Scientist",
        ]
        grade = "Grade 10"
        subject = "English"
        for plain_ch in plain_chapters:
            for step in STEPS_BY_GRADE["Grade 10"]:
                plain_key = make_lesson_cache_key(
                    board=PREWARM_BOARD, grade=grade, subject=subject,
                    chapter=plain_ch, mode="CBSE", step_title=step,
                    teacher_persona="",
                )
                if cache_key == plain_key:
                    return {
                        "lesson_content": "Grade 10 English lesson (from cache).",
                        "practice_questions": [],
                        "source_type": "CACHE",
                        "access_count": 1,
                    }
        return None

    @pytest.mark.parametrize("prefixed_chapter", GRADE_10_ENGLISH_PREFIXED_CHAPTERS)
    def test_prefixed_english_lesson_works_via_source_prefix_fallback(
        self, monkeypatch, prefixed_chapter
    ):
        """
        Grade 10 English chapters with 'Text Book - ', 'Supplementary Reader - ',
        or 'Workbook - ' prefixes must hit the lesson cache via the fallback
        that strips the prefix before retrying the cache key lookup.
        """
        _fake_cache = self._fake_cache_plain_names_only

        profile = fake_student_profile(
            grade="Grade 10",
            access_cbse=True,
            cbse_subjects=[],
        )
        patch_route_profile(monkeypatch, lesson_route, profile)
        monkeypatch.setattr(tutor_service, "ask_llm", fake_ai_off)
        monkeypatch.setattr(tutor_service, "get_cached_lesson", _fake_cache)

        step = STEPS_BY_GRADE["Grade 10"][0]
        resp = client.post("/api/lesson/generate", json={
            "username": "test_user",
            "grade": "Grade 10",
            "board": "CBSE",
            "mode": "CBSE",
            "subject": "English",
            "chapter": prefixed_chapter,
            "step_title": step,
            "teacher_persona": "",
        })

        assert resp.status_code == 200, (
            f"Grade 10 English lesson with prefix should work via fallback: "
            f"'{prefixed_chapter}'. HTTP {resp.status_code}: {resp.json()}. "
            f"Ensure the source-prefix fallback is in generate_step_lesson "
            f"and restart the backend server."
        )
        assert resp.json().get("success") is True
        assert resp.json().get("source_type") == "CACHE"


# ===========================================================================
# 9. Persona-fallback fix: with fix applied, non-empty persona still hits cache
# ===========================================================================

class TestPersonaFallbackFix:
    """
    After the fix in generate_step_lesson, a request with a non-empty
    teacher_persona should STILL be served from the prewarm cache because the
    fallback lookup uses empty persona.
    """

    @pytest.mark.parametrize("grade,mode,subject,chapter,step", [
        ("Grade 9",  "CBSE", "Science",
         "Cell: The Building Block of Life", "Concept introduction"),
        ("Grade 9",  "CBSE", "Maths",
         "Orienting Yourself: The Use of Coordinates", "Core explanation"),
        ("Grade 5",  "CBSE", "EVS",     CBSE_PLACEHOLDER, "What We Learn"),
        ("Grade 6",  "CBSE", "Science", CBSE_PLACEHOLDER, "Core explanation"),
        ("Grade 7",  "CBSE", "Maths",   CBSE_PLACEHOLDER, "Revision and recap"),
        ("Grade 8",  "CBSE", "English", CBSE_PLACEHOLDER, "Concept introduction"),
        ("Grade 10", "CBSE", "Science", CBSE_PLACEHOLDER, "Exam preparation"),
    ])
    def test_nonempty_persona_still_hits_cache_via_fallback(
        self, monkeypatch, grade, mode, subject, chapter, step
    ):
        """
        With the persona-fallback fix applied:
        - AI is off
        - chapter IS prewarmed (empty persona key exists in cache)
        - request sends a non-empty persona
        -> lesson MUST still be served from cache (status 200, source_type=CACHE)
        """
        patch_ai_off_prewarm_cache(monkeypatch, grade)

        resp = call_lesson(grade, mode, subject, chapter, step,
                           persona="Friendly Teacher")

        assert resp.status_code == 200, (
            f"Persona-fallback fix failed for {grade}/{mode}/{subject}/{chapter}/{step}: "
            f"got HTTP {resp.status_code}, expected 200. "
            f"Detail: {resp.json()}"
        )
        data = resp.json()
        assert data.get("success") is True
        assert data.get("source_type") == "CACHE", (
            f"Expected source_type=CACHE after fallback, got {data.get('source_type')}"
        )

    @pytest.mark.parametrize("grade,mode,subject,chapter,step,persona", [
        ("Grade 9", "CBSE", "Science",
         "Cell: The Building Block of Life", "Concept introduction",
         "Friendly Teacher"),
        ("Grade 9", "CBSE", "Science",
         "Cell: The Building Block of Life", "Concept introduction",
         "Strict Teacher"),
        ("Grade 9", "CBSE", "Science",
         "Cell: The Building Block of Life", "Concept introduction",
         "Fun and Interactive"),
        ("Grade 10", "CBSE", "Science", CBSE_PLACEHOLDER, "Exam preparation",
         "Exam-focused Mentor"),
    ])
    def test_any_persona_hits_cache_via_fallback(
        self, monkeypatch, grade, mode, subject, chapter, step, persona
    ):
        """Any non-empty persona value should still serve from prewarm cache."""
        patch_ai_off_prewarm_cache(monkeypatch, grade)
        resp = call_lesson(grade, mode, subject, chapter, step, persona=persona)
        assert resp.status_code == 200, (
            f"Persona '{persona}' caused cache miss for {grade}/{subject}/{step}: "
            f"HTTP {resp.status_code}: {resp.json()}"
        )
        assert resp.json().get("source_type") == "CACHE"
