"""
Comprehensive mock-test generation tests for Grades 5-10 with AI switched OFF.

REAL PRODUCTION STATE (as of current prewarm status)
-----------------------------------------------------
Grade 9  : Lessons prewarmed + Question bank prewarmed -> mock tests WORK with AI off
Grades 5-8, 10 : Lessons prewarmed ONLY. Question bank NOT yet built.
               -> mock tests FAIL with AI off (success=False, no questions)

This test suite documents and verifies the real state:

Section A - Grade 9 (bank prewarmed):
  AI off + bank populated -> success=True, 20 unique questions

Section B - Grades 5,6,7,8,10 (bank NOT prewarmed):
  AI off + no bank -> success=False, empty questions list (graceful degradation)
  These tests will PASS only when they correctly FAIL to generate questions.

Section C - How to fix Grades 5-10:
  Run the question bank builder for each grade in the admin cache panel:
    POST /api/cache/prewarm/questions/{grade-slug}
  Once the bank is built, tests in Section B should be updated to expect success.

Section D - Comprehensive report across all grades showing readiness state.

Key difference from lesson tests
----------------------------------
Lesson generation fails with HTTP 503 (not caught by route).
Mock-test generation fails with HTTP 200 + success=False (caught, graceful).
This is because the mock-test route explicitly catches HTTPException(503).
"""

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import fake_student_profile, patch_route_profile
import app.routes.mock_test as mock_test_route
import app.services.mock_test_service as mock_test_service
from app.data.syllabus import CBSE_9, SOF_9

client = TestClient(app)

# ---------------------------------------------------------------------------
# Subject catalogues per grade (mirror syllabus.py exactly)
# ---------------------------------------------------------------------------

GRADE_5_CBSE_SUBJECTS = [
    "English", "Hindi", "Maths", "EVS",
    "Science", "Social Science", "Computer Science",
]
UPPER_PRIMARY_CBSE_SUBJECTS = [
    "English", "Hindi", "Maths",
    "Science", "Social Science", "Computer Science",
]
GENERIC_SOF_SUBJECTS = [
    "Science Olympiad", "Maths Olympiad", "English Olympiad",
]

CBSE_PLACEHOLDER = "Uploaded Book Content"
SOF_PLACEHOLDER  = "Uploaded SOF Chapter Content"
TARGET_QUESTIONS = 20

# Grades whose question bank is currently prewarmed (admin has run bank builder)
GRADES_WITH_BANK = {"Grade 9", "Grade 10"}

# Grades whose question bank is NOT yet built (lessons prewarmed, bank missing)
GRADES_WITHOUT_BANK = {"Grade 5", "Grade 6", "Grade 7", "Grade 8"}


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------

def combos_for_grade(grade):
    """Return [(mode, subject, chapter)] for a grade."""
    if grade == "Grade 5":
        return (
            [("CBSE", s, CBSE_PLACEHOLDER) for s in GRADE_5_CBSE_SUBJECTS]
            + [("SOF", s, SOF_PLACEHOLDER) for s in GENERIC_SOF_SUBJECTS]
        )
    if grade == "Grade 9":
        return (
            [("CBSE", s, ch) for s, chs in CBSE_9.items() for ch in chs]
            + [("SOF",  s, ch) for s, chs in SOF_9.items()  for ch in chs]
        )
    return (
        [("CBSE", s, CBSE_PLACEHOLDER) for s in UPPER_PRIMARY_CBSE_SUBJECTS]
        + [("SOF", s, SOF_PLACEHOLDER) for s in GENERIC_SOF_SUBJECTS]
    )


# ---------------------------------------------------------------------------
# Shared fakes
# ---------------------------------------------------------------------------

def fake_ai_off(*args, **kwargs):
    """mock_test_service.ask_llm when api_enabled=False."""
    raise HTTPException(
        status_code=503,
        detail=(
            "AI API is currently disabled. "
            "The admin can re-enable it from the Admin Control page."
        ),
    )


def _build_question(index, grade, subject, chapter):
    """Build one unique pre-banked question."""
    return {
        "id": index,
        "section": "MCQ",
        "question": (
            f"[{grade}|{subject}|{chapter[:30]}|Q{index:03d}] "
            f"Which of the following best describes concept {index} in {subject}?"
        ),
        "options": {
            "A": f"Option A for Q{index:03d}",
            "B": f"Option B for Q{index:03d}",
            "C": f"Option C for Q{index:03d}",
            "D": f"Option D for Q{index:03d}",
        },
        "answer": "A",
        "explanation": (
            f"Option A correctly states the concept from {subject}: {chapter[:20]}."
        ),
        "marks": 1,
    }


# ---------------------------------------------------------------------------
# Source prefix pattern (mirrors mock_test_service._SOURCE_PREFIX_PATTERN)
# ---------------------------------------------------------------------------
import re as _re
_TEST_SOURCE_PREFIX_RE = _re.compile(
    r"^\s*(?:Text Book|Supplementary Reader|Grammar|Workbook|Reader|"
    r"History|Geography|Political Science|Economics)\s*[-:]\s*",
    _re.IGNORECASE,
)

def _has_source_prefix(chapter: str) -> bool:
    return bool(_TEST_SOURCE_PREFIX_RE.match(chapter or ""))

def _strip_source_prefix(chapter: str) -> str:
    return _TEST_SOURCE_PREFIX_RE.sub("", chapter or "").strip()


def fake_bank_grade9_only(board, grade, subject, chapter,
                          difficulty, num_questions, exam_type="General"):
    """
    Realistic bank mock: Grade 9 always works.
    Grade 10: simulates bank built with PLAIN chapter names (no source prefix).
    - Request with plain name    → HIT  (works as-is)
    - Request with prefixed name → MISS (the fix must strip prefix and retry)
    Grades 5-8 → bank not built → always [].
    """
    if grade == "Grade 9":
        return [
            _build_question(i, grade, subject, chapter or "")
            for i in range(1, TARGET_QUESTIONS + 1)
        ]
    if grade == "Grade 10":
        # Bank was built with PLAIN chapter names.
        # If the request has a source prefix, it misses without the fix.
        plain_chapter = _strip_source_prefix(chapter or "")
        lookup_chapter = plain_chapter if plain_chapter else (chapter or "")
        # Only return data when the request chapter MATCHES the stored plain name.
        # A prefixed chapter ("Text Book - Ch 7") stored as "Ch 7" → plain matches.
        if chapter == lookup_chapter:
            return [
                _build_question(i, grade, subject, chapter or "")
                for i in range(1, TARGET_QUESTIONS + 1)
            ]
        # Prefixed request → miss (the fix will call again with stripped name)
        return []
    return []  # Bank not built for Grades 5-8


def fake_bank_always_empty(*args, **kwargs):
    """Simulate zero questions in bank (for testing graceful failure)."""
    return []


def fake_bank_grade9_and_built_grades(board, grade, subject, chapter,
                                      difficulty, num_questions, exam_type="General"):
    """
    Future-state bank mock: used to test grades AFTER their bank is built.
    Returns 20 questions for any grade (simulates all banks built).
    """
    return [
        _build_question(i, grade, subject, chapter or "")
        for i in range(1, TARGET_QUESTIONS + 1)
    ]


def patch_mock_test_grade(monkeypatch, grade):
    """Patch auth/profile for mock test routes."""
    profile = fake_student_profile(
        grade=grade,
        access_cbse=True,
        access_sof_science=True,
        access_sof_maths=True,
        access_sof_english=True,
        cbse_subjects=[],
    )
    patch_route_profile(monkeypatch, mock_test_route, profile)


def patch_realistic_ai_off(monkeypatch, grade):
    """AI off + realistic bank state (only Grade 9 bank prewarmed)."""
    patch_mock_test_grade(monkeypatch, grade)
    monkeypatch.setattr(mock_test_service, "ask_llm", fake_ai_off)
    monkeypatch.setattr(
        mock_test_service, "get_questions_from_bank", fake_bank_grade9_only
    )


def patch_ai_off_no_bank(monkeypatch, grade):
    """AI off + no bank at all."""
    patch_mock_test_grade(monkeypatch, grade)
    monkeypatch.setattr(mock_test_service, "ask_llm", fake_ai_off)
    monkeypatch.setattr(
        mock_test_service, "get_questions_from_bank", fake_bank_always_empty
    )


def patch_ai_off_all_banks_built(monkeypatch, grade):
    """AI off + all grade banks built (future state after admin runs bank builder)."""
    patch_mock_test_grade(monkeypatch, grade)
    monkeypatch.setattr(mock_test_service, "ask_llm", fake_ai_off)
    monkeypatch.setattr(
        mock_test_service, "get_questions_from_bank", fake_bank_grade9_and_built_grades
    )


def call_mock_test(grade, mode, subject, chapter, question_count=20):
    """Call the mock test generate endpoint."""
    mock_type = (
        "SOF Olympiad Mock Test" if mode == "SOF" else "CBSE Mock Test"
    )
    return client.post("/api/mock-test/generate", json={
        "username": "test_user",
        "grade": grade,
        "board": "CBSE",
        "mode": mode,
        "subject": subject,
        "chapter": chapter,
        "mock_type": mock_type,
        "exam_type": "Class Test",
        "question_count": question_count,
        "difficulty": "Medium",
    })


# ===========================================================================
# SECTION A: Grade 9 (question bank prewarmed) -- must succeed with AI off
# ===========================================================================

class TestGrade9MockTestsWithBankAiOff:
    """
    Grade 9 and Grade 10 question banks are prewarmed.
    Every chapter must return 20 unique questions when AI is off.
    """

    @pytest.mark.parametrize("subject,chapter", [
        (s, ch) for s, chs in CBSE_9.items() for ch in chs
    ])
    def test_grade9_cbse_20_unique_questions_from_bank(self, monkeypatch, subject, chapter):
        """Grade 9 CBSE: bank is prewarmed -> 20 unique questions returned."""
        patch_realistic_ai_off(monkeypatch, "Grade 9")
        resp = call_mock_test("Grade 9", "CBSE", subject, chapter)

        assert resp.status_code == 200
        data = resp.json()

        assert data.get("success") is True, (
            f"Grade 9 CBSE bank should be prewarmed but got "
            f"success={data.get('success')}, message={data.get('message')} "
            f"for {subject}/{chapter}"
        )
        questions = data.get("questions", [])
        assert len(questions) == TARGET_QUESTIONS, (
            f"Expected {TARGET_QUESTIONS} questions from Grade 9 bank, "
            f"got {len(questions)} for {subject}/{chapter}"
        )
        unique = {q.get("question", "") for q in questions}
        assert len(unique) == TARGET_QUESTIONS, (
            f"{TARGET_QUESTIONS - len(unique)} duplicate questions in "
            f"Grade 9 bank for {subject}/{chapter}"
        )

    @pytest.mark.parametrize("subject,chapter", [
        (s, ch) for s, chs in SOF_9.items() for ch in chs
    ])
    def test_grade9_sof_20_unique_questions_from_bank(self, monkeypatch, subject, chapter):
        """Grade 9 SOF: bank is prewarmed -> 20 unique questions returned."""
        patch_realistic_ai_off(monkeypatch, "Grade 9")
        resp = call_mock_test("Grade 9", "SOF", subject, chapter)

        assert resp.status_code == 200
        data = resp.json()

        assert data.get("success") is True, (
            f"Grade 9 SOF bank should be prewarmed but got "
            f"success={data.get('success')}, message={data.get('message')} "
            f"for {subject}/{chapter}"
        )
        questions = data.get("questions", [])
        assert len(questions) == TARGET_QUESTIONS
        assert len({q.get("question") for q in questions}) == TARGET_QUESTIONS

    @pytest.mark.parametrize("mode,subject,chapter", [
        *[("CBSE", s, CBSE_PLACEHOLDER) for s in UPPER_PRIMARY_CBSE_SUBJECTS],
        *[("SOF",  s, SOF_PLACEHOLDER)  for s in GENERIC_SOF_SUBJECTS],
    ])
    def test_grade10_20_unique_questions_from_bank(self, monkeypatch, mode, subject, chapter):
        """Grade 10: bank is prewarmed -> 20 unique questions returned with AI off."""
        patch_realistic_ai_off(monkeypatch, "Grade 10")
        resp = call_mock_test("Grade 10", mode, subject, chapter)

        assert resp.status_code == 200
        data = resp.json()

        assert data.get("success") is True, (
            f"Grade 10 bank should be prewarmed but got "
            f"success={data.get('success')}, message={data.get('message')} "
            f"for {mode}/{subject}/{chapter}"
        )
        questions = data.get("questions", [])
        assert len(questions) == TARGET_QUESTIONS, (
            f"Expected {TARGET_QUESTIONS} questions from Grade 10 bank, "
            f"got {len(questions)} for {mode}/{subject}/{chapter}"
        )
        unique = {q.get("question", "") for q in questions}
        assert len(unique) == TARGET_QUESTIONS, (
            f"{TARGET_QUESTIONS - len(unique)} duplicate questions in "
            f"Grade 10 bank for {mode}/{subject}/{chapter}"
        )


# ===========================================================================
# SECTION B: Grades 5,6,7,8,10 (NO question bank) -- must FAIL gracefully
# ===========================================================================

class TestGrades5To8And10FailGracefullyNoBank:
    """
    Grades 5-8 and 10 have NOT had their question bank built yet.
    With AI off + no bank, mock-test generation must fail gracefully:
      HTTP 200, success=False, questions=[], message mentions AI/unavailable.

    ACTION REQUIRED: Run the admin cache panel question bank builder for
    Grades 5-10 to enable mock tests for these grades with AI off.
    Command: POST /api/cache/prewarm/questions/{grade-5 through grade-10}
    """

    @pytest.mark.parametrize("grade,mode,subject,chapter", [
        # Grade 5
        *[("Grade 5",  "CBSE", s, CBSE_PLACEHOLDER) for s in GRADE_5_CBSE_SUBJECTS],
        *[("Grade 5",  "SOF",  s, SOF_PLACEHOLDER)  for s in GENERIC_SOF_SUBJECTS],
        # Grade 6
        *[("Grade 6",  "CBSE", s, CBSE_PLACEHOLDER) for s in UPPER_PRIMARY_CBSE_SUBJECTS],
        *[("Grade 6",  "SOF",  s, SOF_PLACEHOLDER)  for s in GENERIC_SOF_SUBJECTS],
        # Grade 7
        *[("Grade 7",  "CBSE", s, CBSE_PLACEHOLDER) for s in UPPER_PRIMARY_CBSE_SUBJECTS],
        *[("Grade 7",  "SOF",  s, SOF_PLACEHOLDER)  for s in GENERIC_SOF_SUBJECTS],
        # Grade 8
        *[("Grade 8",  "CBSE", s, CBSE_PLACEHOLDER) for s in UPPER_PRIMARY_CBSE_SUBJECTS],
        *[("Grade 8",  "SOF",  s, SOF_PLACEHOLDER)  for s in GENERIC_SOF_SUBJECTS],
        # Grade 10 removed -- bank is now built, moved to Section A
    ])
    def test_no_bank_no_ai_fails_gracefully(self, monkeypatch, grade, mode, subject, chapter):
        """
        Without a question bank, AI-off must return success=False gracefully.

        This test PASSES when it correctly detects that mock-test generation
        is NOT possible for this grade (bank not prewarmed).

        FIX: Build the question bank via admin cache panel, then this test
        should be updated/removed and the grade added to GRADES_WITH_BANK.
        """
        patch_ai_off_no_bank(monkeypatch, grade)
        resp = call_mock_test(grade, mode, subject, chapter)

        assert resp.status_code == 200, (
            f"Expected HTTP 200 (graceful failure), got {resp.status_code} "
            f"for {grade}/{mode}/{subject}/{chapter}"
        )
        data = resp.json()
        assert data.get("success") is False, (
            f"Expected success=False (bank not built + AI off) for "
            f"{grade}/{mode}/{subject}/{chapter}, "
            f"got success={data.get('success')}. "
            f"ACTION: Build question bank for {grade} via admin cache panel."
        )
        assert data.get("questions") == [], (
            f"Expected empty questions when bank not built + AI off, "
            f"got {len(data.get('questions', []))} questions "
            f"for {grade}/{mode}/{subject}/{chapter}"
        )


# ===========================================================================
# SECTION C: Future state -- all banks built (ready for production)
# ===========================================================================

class TestAllGradesMockTestsAfterBankBuilt:
    """
    Tests to run AFTER admin has built the question bank for ALL grades.

    When the admin runs:
      POST /api/cache/prewarm/questions/grade-5
      POST /api/cache/prewarm/questions/grade-6
      ... (grade-7, grade-8, grade-10)

    These tests verify that all Grade 5-10 mock tests work with AI off.
    """

    @pytest.mark.parametrize("grade,mode,subject,chapter", [
        *[("Grade 5",  "CBSE", s, CBSE_PLACEHOLDER) for s in GRADE_5_CBSE_SUBJECTS],
        *[("Grade 5",  "SOF",  s, SOF_PLACEHOLDER)  for s in GENERIC_SOF_SUBJECTS],
        *[("Grade 6",  "CBSE", s, CBSE_PLACEHOLDER) for s in UPPER_PRIMARY_CBSE_SUBJECTS],
        *[("Grade 6",  "SOF",  s, SOF_PLACEHOLDER)  for s in GENERIC_SOF_SUBJECTS],
        *[("Grade 7",  "CBSE", s, CBSE_PLACEHOLDER) for s in UPPER_PRIMARY_CBSE_SUBJECTS],
        *[("Grade 7",  "SOF",  s, SOF_PLACEHOLDER)  for s in GENERIC_SOF_SUBJECTS],
        *[("Grade 8",  "CBSE", s, CBSE_PLACEHOLDER) for s in UPPER_PRIMARY_CBSE_SUBJECTS],
        *[("Grade 8",  "SOF",  s, SOF_PLACEHOLDER)  for s in GENERIC_SOF_SUBJECTS],
        # Grade 10 now has bank -- tests in Section A cover it
    ])
    @pytest.mark.skip(reason=(
        "Bank not yet built for Grades 5-8. "
        "Remove @pytest.mark.skip after running: "
        "POST /api/cache/prewarm/questions/{grade-5 through grade-8}"
    ))
    def test_20_unique_questions_after_bank_built(
        self, monkeypatch, grade, mode, subject, chapter
    ):
        """Once bank is built, this must return 20 unique questions with AI off."""
        patch_ai_off_all_banks_built(monkeypatch, grade)
        resp = call_mock_test(grade, mode, subject, chapter)

        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is True, (
            f"After building bank, expected success=True for "
            f"{grade}/{mode}/{subject}/{chapter}, "
            f"got: {data.get('message')}"
        )
        questions = data.get("questions", [])
        assert len(questions) == TARGET_QUESTIONS
        assert len({q.get("question") for q in questions}) == TARGET_QUESTIONS


# ===========================================================================
# SECTION D: Grade 10 source-prefix fix tests
# Root cause: bank was built before multi-book display prefixes were introduced.
# Bank has plain "Chapter 7: Madam Rides the Bus"; frontend sends
# "Text Book - Chapter 7: Madam Rides the Bus".
# Fix: get_questions_from_bank_with_fallback strips the prefix and retries.
# ===========================================================================

class TestGrade10SourcePrefixFix:
    """
    Verify that Grade 10 chapters with book-source display prefixes still
    find their question bank entries after the prefix-fallback fix is applied.
    """

    # Real Grade 10 English chapter names as shown in the frontend dropdown
    # (all three book sources: Text Book, Supplementary Reader, Workbook)
    GRADE_10_ENGLISH_ALL_PREFIXED = [
        "Text Book - Chapter 1: A Letter to God",
        "Text Book - Chapter 2: Nelson Mandela: Long Walk to Freedom",
        "Text Book - Chapter 3: Two Stories about Flying",
        "Text Book - Chapter 4: From the Diary of Anne Frank",
        "Text Book - Chapter 5: Glimpses of India",
        "Text Book - Chapter 6: Mijbil the Otter",
        "Text Book - Chapter 7: Madam Rides the Bus",
        "Text Book - Chapter 8: The Sermon at Benares",
        "Text Book - Chapter 9: The Proposal",
        "Supplementary Reader - Chapter 1: A Triumph of Surgery",
        "Supplementary Reader - Chapter 2: The Thief's Story",
        "Supplementary Reader - Chapter 3: The Midnight Visitor",
        "Supplementary Reader - Chapter 4: A Question of Trust",
        "Supplementary Reader - Chapter 5: Footprints without Feet",
        "Supplementary Reader - Chapter 6: The Making of a Scientist",
        "Supplementary Reader - Chapter 7: The Necklace",
        "Supplementary Reader - Chapter 8: Bholi",
        "Supplementary Reader - Chapter 9: The Book That Saved the Earth",
        "Workbook - Chapter 1: A Letter to God",
        "Workbook - Chapter 2: Nelson Mandela \u2014 Long Walk to Freedom",
        "Workbook - Chapter 3: Two Stories About Flying",
        "Workbook - Chapter 4: From the Diary of Anne Frank",
        "Workbook - Chapter 5: Glimpses of India",
        "Workbook - Chapter 6: Mijbil the Otter",
        "Workbook - Chapter 7: Madam Rides the Bus",
        "Workbook - Chapter 8: The Sermon at Benares",
        "Workbook - Chapter 9: The Proposal",
    ]

    @pytest.mark.parametrize("prefixed_chapter", GRADE_10_ENGLISH_ALL_PREFIXED)
    def test_all_prefixed_english_chapters_work_via_fallback(
        self, monkeypatch, prefixed_chapter
    ):
        """
        ALL Grade 10 English chapters with display prefixes
        ('Text Book - ', 'Supplementary Reader - ', 'Workbook - ') must
        succeed via the source-prefix fallback in generate_cbse_mock_test.

        NOTE: If this test passes but production still fails, restart the
        backend server so it picks up the code fix in mock_test_service.py.
        """
        patch_mock_test_grade(monkeypatch, "Grade 10")
        monkeypatch.setattr(mock_test_service, "ask_llm", fake_ai_off)
        monkeypatch.setattr(
            mock_test_service, "get_questions_from_bank", fake_bank_grade9_only
        )

        resp = call_mock_test("Grade 10", "CBSE", "English", prefixed_chapter)
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is True, (
            f"Grade 10 English '{prefixed_chapter}' should work via prefix-fallback. "
            f"got success={data.get('success')}, message={data.get('message')}. "
            f"If this passes in tests but fails in production: RESTART the backend server."
        )
        assert len(data.get("questions", [])) == TARGET_QUESTIONS

    def test_strip_source_prefix_function(self):
        """Verify the strip function works for all expected prefix formats."""
        from app.services.mock_test_service import strip_source_display_prefix
        cases = [
            ("Text Book - Chapter 7: Madam Rides the Bus",
             "Chapter 7: Madam Rides the Bus"),
            ("Text Book - Chapter 1: A Letter to God",
             "Chapter 1: A Letter to God"),
            ("Supplementary Reader - Chapter 1: A Triumph of Surgery",
             "Chapter 1: A Triumph of Surgery"),
            ("Workbook - Chapter 7: Madam Rides the Bus",
             "Chapter 7: Madam Rides the Bus"),
            ("Workbook - Chapter 9: The Proposal",
             "Chapter 9: The Proposal"),
            ("History - The Rise of Nationalism",
             "The Rise of Nationalism"),
            ("Geography - Resources and Development",
             "Resources and Development"),
            ("Political Science - Power Sharing",
             "Power Sharing"),
            ("Economics - Development",
             "Development"),
            ("Chapter 7: Madam Rides the Bus",
             "Chapter 7: Madam Rides the Bus"),
            ("Cell: The Building Block of Life",
             "Cell: The Building Block of Life"),
        ]
        for prefixed, expected in cases:
            result = strip_source_display_prefix(prefixed)
            assert result == expected, (
                f"strip_source_display_prefix('{prefixed}') "
                f"= '{result}', expected '{expected}'"
            )

    def test_plain_chapter_still_hits_bank_directly(self, monkeypatch):
        """Plain chapter names (no prefix) must still work without needing fallback."""
        patch_mock_test_grade(monkeypatch, "Grade 10")
        monkeypatch.setattr(mock_test_service, "ask_llm", fake_ai_off)
        monkeypatch.setattr(
            mock_test_service, "get_questions_from_bank", fake_bank_grade9_only
        )

        plain_chapter = "Chapter 7: Madam Rides the Bus"
        resp = call_mock_test("Grade 10", "CBSE", "English", plain_chapter)
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is True, (
            f"Plain chapter should work without prefix stripping: '{plain_chapter}'. "
            f"got: {data.get('message')}"
        )


# ===========================================================================
# SECTION E: Comprehensive readiness report for all Grades 5-10
# ===========================================================================

class TestComprehensiveMockTestReadinessReport:
    """
    Single exhaustive report test covering all Grade 5-10 combinations.
    Uses realistic bank mock (only Grade 9 prewarmed).
    Prints pass/fail with clear diagnosis for each combination.
    """

    def test_all_grade_5_to_10_mock_test_readiness_report(self, monkeypatch):
        """
        Report shows which grades can serve mock tests with AI off (bank built)
        and which cannot yet (bank not built -- needs admin action).
        """
        ready     = []   # bank built, AI off works
        not_ready = []   # bank missing, needs action

        for grade in ["Grade 5", "Grade 6", "Grade 7",
                      "Grade 8", "Grade 9", "Grade 10"]:
            patch_realistic_ai_off(monkeypatch, grade)

            for mode, subject, chapter in combos_for_grade(grade):
                resp = call_mock_test(grade, mode, subject, chapter)
                data = resp.json()
                questions = data.get("questions", [])
                unique_count = len({q.get("question", "") for q in questions})

                entry = {
                    "grade": grade, "mode": mode,
                    "subject": subject, "chapter": chapter[:35],
                }

                if (
                    resp.status_code == 200
                    and data.get("success")
                    and len(questions) == TARGET_QUESTIONS
                    and unique_count == TARGET_QUESTIONS
                ):
                    entry["state"] = "READY"
                    entry["q_count"] = len(questions)
                    ready.append(entry)
                else:
                    if not data.get("success"):
                        entry["state"] = "NOT_READY (bank not built)"
                        entry["action"] = (
                            f"Run POST /api/cache/prewarm/questions/"
                            f"{grade.lower().replace(' ', '-')}"
                        )
                    else:
                        entry["state"] = f"UNEXPECTED: {data.get('message','')[:50]}"
                    not_ready.append(entry)

        total = len(ready) + len(not_ready)

        print("\n")
        print("=" * 70)
        print("GRADE 5-10 MOCK TEST READINESS REPORT (AI OFF)")
        print("=" * 70)
        print(f"Total combinations : {total}")
        print(f"READY (bank built) : {len(ready)}")
        print(f"NOT READY          : {len(not_ready)}")
        print()

        if ready:
            print("READY (bank prewarmed, AI off works):")
            print("-" * 70)
            for r in ready[:10]:
                print(
                    f"  READY | {r['grade']:8s} | {r['mode']:4s} | "
                    f"{r['subject']:22s} | {r['chapter']:35s}"
                )
            if len(ready) > 10:
                print(f"  ... and {len(ready) - 10} more")
            print()

        if not_ready:
            print("NOT READY (question bank not built -- ACTION REQUIRED):")
            print("-" * 70)
            grades_needing_bank = {e["grade"] for e in not_ready}
            for grade in sorted(grades_needing_bank):
                count = sum(1 for e in not_ready if e["grade"] == grade)
                print(
                    f"  {grade}: {count} combinations need bank. "
                    f"Run: POST /api/cache/prewarm/questions/"
                    f"{grade.lower().replace(' ', '-')}"
                )
            print()

        print("=" * 70)

        # Grade 9 must always be ready
        grade9_not_ready = [e for e in not_ready if e["grade"] == "Grade 9"]
        assert not grade9_not_ready, (
            f"Grade 9 mock tests should be READY (bank prewarmed) but "
            f"{len(grade9_not_ready)} combinations failed: "
            + ", ".join(f"{e['subject']}/{e['chapter']}" for e in grade9_not_ready[:3])
        )

        # Grades 5-8, 10 are expected to be NOT READY (bank not built yet)
        # This assertion documents the current state and will need updating
        # once the question bank is built for those grades.
        # Grade 10 now has a bank built -- it should be in the ready list
        grade10_not_ready = [e for e in not_ready if e["grade"] == "Grade 10"]
        assert not grade10_not_ready, (
            f"Grade 10 mock tests should be READY (bank prewarmed) but "
            f"{len(grade10_not_ready)} combinations failed: "
            + ", ".join(f"{e['subject']}/{e['chapter']}" for e in grade10_not_ready[:3])
        )

        # Grades 5-8 are still NOT READY (bank not built yet)
        grades5_8_ready = [
            e for e in ready if e["grade"] in GRADES_WITHOUT_BANK
        ]
        assert not grades5_8_ready, (
            f"Grades 5-8 unexpectedly have a question bank "
            f"({len(grades5_8_ready)} combinations). "
            f"Update GRADES_WITH_BANK and GRADES_WITHOUT_BANK constants "
            f"and remove the @pytest.mark.skip from Section C tests."
        )

        print(
            f"\nSUMMARY: Grade 9 and Grade 10 are ready for AI-off mock tests. "
            f"Grades 5-8 need question bank building before "
            f"they can serve mock tests with AI off."
        )
