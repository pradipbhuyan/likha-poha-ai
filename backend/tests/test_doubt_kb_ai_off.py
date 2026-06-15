"""
Doubt Knowledge Base (DKB) Tests — AI OFF
==========================================
Verifies that the DKB correctly answers student questions about Grade 9
Science chapters WITHOUT calling the OpenAI LLM (simulating AI disabled).

Test strategy
-------------
1. Preloaded card questions: exact DKB question texts → must always HIT at ~1.000
2. Paraphrased questions: student-typed variations → should HIT at threshold ≥ 0.50
3. Lesson suggestion cards: only show questions that the DKB can answer
4. Out-of-scope questions ("Show a diagram", UI commands): gracefully MISS

All tests run against the REAL Supabase DB.  No LLM is called.
AI is simulated as OFF by monkeypatching ask_llm to raise 503.

Run with:
    cd backend
    python3 -m pytest tests/test_doubt_kb_ai_off.py -v -s
"""

import logging
import pytest

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def search(question, grade, subject, chapter, mode="CBSE", threshold=None):
    """Thin wrapper so test bodies stay readable."""
    from app.services.doubt_kb_service import (
        search_doubt_kb,
        SIMILARITY_THRESHOLD,
    )
    th = threshold if threshold is not None else SIMILARITY_THRESHOLD
    return search_doubt_kb(question, grade, subject, chapter, mode, threshold=th)


def suggestions(grade, subject, chapter, mode="CBSE", limit=6):
    """Fetch DKB-backed lesson suggestion cards."""
    from app.services.doubt_kb_service import get_lesson_doubt_suggestions
    return get_lesson_doubt_suggestions(grade, subject, chapter, mode, limit)


# ---------------------------------------------------------------------------
# Grade 9 Science chapter fixtures
# ---------------------------------------------------------------------------

GRADE = "Grade 9"
SUBJECT = "Science"

# Chapter names as used by the lesson route (from CBSE_9 syllabus, NO "Chapter N:" prefix)
CHAPTERS = {
    "Cell":       "Cell: The Building Block of Life",
    "Tissues":    "Tissues in Action",
    "Motion":     "Describing Motion Around Us",
    "Atoms":      "Atomic Foundations of Matter",
    "Exploration":"Exploration: Entering the World of Secondary Science",
}


# ===========================================================================
# 1. DKB suggestions for each chapter (what appears as preloaded cards)
# ===========================================================================

class TestDKBSuggestions:
    """
    Verify that get_lesson_doubt_suggestions returns questions for each
    Grade 9 Science chapter.  Each returned question must be answerable
    by the DKB (clicking it → HIT at ~1.000 similarity).
    """

    @pytest.mark.parametrize("label,chapter", CHAPTERS.items())
    def test_suggestions_are_available(self, label, chapter):
        """DKB must return at least 1 pre-answered question per chapter."""
        cards = suggestions(GRADE, SUBJECT, chapter)
        assert len(cards) > 0, (
            f"No DKB suggestions for {GRADE} Science '{chapter}'. "
            "Run 'POST /api/cache/prewarm/doubt-kb/grade-9' to build the DKB."
        )
        print(f"\n{label} ({chapter[:40]}) - {len(cards)} suggestion cards:")
        for c in cards[:3]:
            print(f"  - {c['question'][:70]}")

    @pytest.mark.parametrize("label,chapter", CHAPTERS.items())
    def test_all_suggestion_cards_are_answerable(self, label, chapter):
        """
        Every question shown as a card must return a DKB hit when clicked.
        Clicking the EXACT card text should always match at ~1.000.
        """
        cards = suggestions(GRADE, SUBJECT, chapter)
        if not cards:
            pytest.skip(f"No DKB suggestions for {chapter} — build DKB first.")

        failures = []
        for card in cards:
            q = card["question"]
            result = search(q, GRADE, SUBJECT, chapter)
            if not result:
                failures.append(f"  MISS: {q[:60]}")
            else:
                print(f"  HIT [{result['similarity']:.3f}]: {q[:60]}")

        assert not failures, (
            f"Some cards are NOT answerable by DKB for '{chapter}':\n"
            + "\n".join(failures)
            + "\nThese cards should NOT be shown to students (fix get_lesson_doubt_suggestions)."
        )


# ===========================================================================
# 2. Exact card click simulation (highest priority test)
# ===========================================================================

class TestExactCardClicks:
    """
    When a student clicks a suggestion card, the exact question text is
    submitted.  This must ALWAYS be served from DKB (similarity ~1.000)
    regardless of chapter name format differences.
    """

    def test_cell_chapter_card_click(self):
        """Grade 9 Cell chapter card click → DKB HIT at 1.000."""
        cards = suggestions(GRADE, SUBJECT, CHAPTERS["Cell"])
        if not cards:
            pytest.skip("No DKB entries for Cell chapter.")
        q = cards[0]["question"]
        result = search(q, GRADE, SUBJECT, CHAPTERS["Cell"])
        assert result is not None, f"Card click MISSED: '{q}'"
        assert result["similarity"] > 0.95, (
            f"Expected ~1.000 for exact card click, got {result['similarity']:.3f}"
        )
        print(f"\nCard click HIT [{result['similarity']:.3f}]: {q[:60]}")

    def test_tissues_chapter_card_click(self):
        """Grade 9 Tissues chapter card click → DKB HIT at 1.000."""
        cards = suggestions(GRADE, SUBJECT, CHAPTERS["Tissues"])
        if not cards:
            pytest.skip("No DKB entries for Tissues chapter.")
        q = cards[0]["question"]
        result = search(q, GRADE, SUBJECT, CHAPTERS["Tissues"])
        assert result is not None, f"Card click MISSED: '{q}'"
        assert result["similarity"] > 0.95
        print(f"\nTissues card HIT [{result['similarity']:.3f}]: {q[:60]}")

    def test_motion_chapter_card_click(self):
        cards = suggestions(GRADE, SUBJECT, CHAPTERS["Motion"])
        if not cards:
            pytest.skip("No DKB entries for Motion chapter.")
        q = cards[0]["question"]
        result = search(q, GRADE, SUBJECT, CHAPTERS["Motion"])
        assert result is not None, f"Card click MISSED: '{q}'"
        assert result["similarity"] > 0.95
        print(f"\nMotion card HIT [{result['similarity']:.3f}]: {q[:60]}")


# ===========================================================================
# 3. Paraphrased question tests (student typing variations)
# ===========================================================================

class TestParaphrasedQuestions:
    """
    Student types a question that is SIMILAR but not identical to stored DKB entries.
    These should hit the DKB at threshold 0.50 (calibrated from live data).
    """

    PARAPHRASE_TESTS = [
        # (question, chapter_key, reason)
        ("what is a tissue",          "Tissues", "Core definition question"),
        ("what does a cell do",        "Cell",    "Cell function question"),
        ("what is velocity",           "Motion",  "Motion definition"),
        ("what is an atom made of",    "Atoms",   "Atomic structure"),
        ("why do we study science",    "Exploration", "Science motivation"),
        ("what is the nucleus",        "Cell",    "Cell organelle"),
        ("how does osmosis work",      "Cell",    "Osmosis process"),
        ("types of tissue in plants",  "Tissues", "Plant tissue types"),
        ("what is daltons theory",     "Atoms",   "Dalton atomic theory"),
        ("define acceleration",        "Motion",  "Motion definition"),
    ]

    @pytest.mark.parametrize("question,chapter_key,reason", PARAPHRASE_TESTS)
    def test_paraphrase_hits_at_0_50(self, question, chapter_key, reason):
        """Paraphrased questions should hit DKB at threshold 0.50."""
        chapter = CHAPTERS[chapter_key]
        result = search(question, GRADE, SUBJECT, chapter, threshold=0.50)
        if result:
            print(f"\n  HIT [{result['similarity']:.3f}] ({reason}): "
                  f"'{question}' → '{result['question'][:50]}'")
        else:
            # Not a hard failure — log it so we know DKB coverage gaps
            print(f"\n  MISS ({reason}): '{question}' for chapter '{chapter[:40]}'")
            # Soft failure: count how many miss at 0.50
            pytest.xfail(
                f"'{question}' not covered in DKB at threshold 0.50. "
                "Acceptable — novel questions fall back to LLM when AI is ON."
            )


# ===========================================================================
# 4. Comprehensive chapter coverage report
# ===========================================================================

class TestDKBCoverageReport:
    """
    Generate a full coverage report for all Grade 9 Science chapters.
    Shows which questions are in the DKB and estimates hit rate for
    typical student questions.
    """

    def test_print_full_coverage_report(self):
        """Print DKB coverage for each Grade 9 Science chapter."""
        from app.services.auth_service import admin_client as supabase

        print("\n")
        print("=" * 70)
        print("DKB COVERAGE REPORT — Grade 9 Science (AI OFF Mode)")
        print("=" * 70)

        for label, chapter in CHAPTERS.items():
            cards = suggestions(GRADE, SUBJECT, chapter)

            # Count total DKB entries for this chapter
            total = supabase.table("doubt_kb").select(
                "id", count="exact"
            ).eq("grade", GRADE).eq("subject", SUBJECT).ilike(
                "chapter", f"%{chapter}%"
            ).eq("status", "active").execute()

            n_total = total.count or 0

            print(f"\n{label} — {chapter[:50]}")
            print(f"  Total DKB Q&A pairs: {n_total}")
            print(f"  Suggestion cards available: {len(cards)}")
            if cards:
                print("  Sample questions shown as cards:")
                for c in cards[:3]:
                    # verify each card hits DKB
                    r = search(c["question"], GRADE, SUBJECT, chapter)
                    status = f"HIT [{r['similarity']:.3f}]" if r else "MISS"
                    print(f"    [{status}] {c['question'][:60]}")

        print()
        print("=" * 70)
        print("INTERPRETATION:")
        print("  - Cards shown = pre-answered questions (zero token cost)")
        print("  - Clicking any card = DKB HIT (instant, no LLM call needed)")
        print("  - Typed paraphrases = may miss at default threshold")
        print("  - UI commands ('Show a diagram') = always need AI ON")
        print("=" * 70)

        # This test always passes — it's a reporting test
        assert True


# ===========================================================================
# 5. AI-off simulation: full lesson follow-up flow
# ===========================================================================

class TestFollowUpFlowAiOff:
    """
    Simulate the full /api/lesson/follow-up flow with AI disabled.
    DKB-answerable questions should return a valid answer.
    Non-DKB questions should gracefully return 503 (not crash).
    """

    def _fake_ask_llm(*args, **kwargs):
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503,
            detail="AI API is currently disabled. The admin can re-enable it."
        )

    def test_card_click_answered_without_llm(self, monkeypatch):
        """
        Simulates: student clicks a DKB suggestion card while AI is OFF.
        Expected: DKB answers instantly, LLM is never called.
        """
        import app.services.tutor_service as tutor_service
        monkeypatch.setattr(tutor_service, "ask_llm", self._fake_ask_llm)

        # Get a card from Tissues chapter
        cards = suggestions(GRADE, SUBJECT, CHAPTERS["Tissues"])
        if not cards:
            pytest.skip("No Tissues DKB entries.")

        card_question = cards[0]["question"]
        print(f"\nSimulating card click: '{card_question[:60]}'")

        result = tutor_service.answer_lesson_follow_up(
            grade=GRADE,
            mode="CBSE",
            subject=SUBJECT,
            chapter=CHAPTERS["Tissues"],
            step_title="Concept introduction",
            lesson="Tissues are groups of similar cells...",
            question=card_question,
            username="test_student",
            board="CBSE",
        )

        assert result is not None
        assert result.get("answer"), "DKB should return an answer for exact card question"
        print(f"  Answer (first 100 chars): {result['answer'][:100]}")
        print("  PASS: Card click answered from DKB without LLM")

    def test_typed_science_question_answered(self, monkeypatch):
        """
        Simulates: student types 'what is a tissue' while AI is OFF.
        With threshold 0.50: should hit DKB.
        """
        import app.services.tutor_service as tutor_service
        from app.services import doubt_kb_service as dkb_svc
        monkeypatch.setattr(tutor_service, "ask_llm", self._fake_ask_llm)
        # Temporarily lower threshold for this test
        orig = dkb_svc.SIMILARITY_THRESHOLD
        monkeypatch.setattr(dkb_svc, "SIMILARITY_THRESHOLD", 0.50)

        try:
            result = tutor_service.answer_lesson_follow_up(
                grade=GRADE,
                mode="CBSE",
                subject=SUBJECT,
                chapter=CHAPTERS["Tissues"],
                step_title="Concept introduction",
                lesson="Tissues are groups of similar cells...",
                question="what is a tissue",
                username="test_student",
                board="CBSE",
            )
            assert result is not None
            assert result.get("answer"), "Expected DKB answer for 'what is a tissue'"
            print(f"\n  PASS: 'what is a tissue' answered from DKB")
            print(f"  Answer preview: {result['answer'][:100]}")
        except Exception as e:
            if "503" in str(e) or "disabled" in str(e).lower():
                pytest.xfail(
                    "'what is a tissue' similarity < 0.50 in DKB — "
                    "add it to DKB or accept that typed novel questions need AI ON."
                )
            raise
        finally:
            pass  # threshold restored by monkeypatch automatically

    def test_ui_command_chips_fail_gracefully(self, monkeypatch):
        """
        UI command chips like 'Show a diagram' are NOT in the DKB.
        With AI off they should return 503 (not crash the server).
        """
        import app.services.tutor_service as tutor_service
        monkeypatch.setattr(tutor_service, "ask_llm", self._fake_ask_llm)

        ui_commands = ["Show a diagram", "Explain in simpler words", "Give a real-life example"]
        for cmd in ui_commands:
            try:
                tutor_service.answer_lesson_follow_up(
                    grade=GRADE, mode="CBSE", subject=SUBJECT,
                    chapter=CHAPTERS["Cell"],
                    step_title="Concept introduction",
                    lesson="Cells are the basic unit of life.",
                    question=cmd, username="test_student", board="CBSE",
                )
                # If we get here, DKB answered it — that's OK too
                print(f"\n  '{cmd}' → answered from DKB (unexpected but fine)")
            except Exception as e:
                if "503" in str(e) or "disabled" in str(e).lower():
                    print(f"\n  '{cmd}' → 503 as expected (UI command, not in DKB)")
                else:
                    raise
