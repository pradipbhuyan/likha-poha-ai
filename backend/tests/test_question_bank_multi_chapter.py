"""
Multi-chapter mock-test sampling (Mid Term / Annual Exam papers).

A Class Test draws from a single chapter. Mid Term and Annual Exam papers
draw from several chapters at once. These tests verify:

  1. Questions are actually spread across the selected chapters (not all
     pulled from just one).
  2. No question repeats within a single generated test — including across
     chapters, since a repeated question text/id from any chapter would be
     just as much a duplicate to the student as a repeat within one chapter.
  3. A combined-capacity shortfall across the selected chapters is reported
     instead of silently serving a shorter test.
"""

import app.services.question_bank_service as question_bank_service


def _fake_bank_question(chapter, index):
    """A distinct fake bank question, tagged with its source chapter."""
    return {
        "id": index,
        "db_id": f"{chapter}-{index}",
        "section": "MCQ",
        "question": f"[{chapter}] question {index}: which option is correct?",
        "options": {"A": "One", "B": "Two", "C": "Three", "D": "Four"},
        "answer": "A",
        "explanation": "Option A is correct because the bank says so clearly.",
        "marks": 1,
    }


def _fake_bank(capacities):
    """
    Build a fake bank keyed by chapter -> list of distinct fake questions,
    one per unit of capacity.
    """
    return {
        chapter: [_fake_bank_question(chapter, i) for i in range(1, capacity + 1)]
        for chapter, capacity in capacities.items()
    }


def _patch_bank(monkeypatch, capacities):
    """Patch get_bank_capacity / get_questions_from_bank against a fake in-memory bank."""
    bank = _fake_bank(capacities)

    def fake_get_bank_capacity(board, grade, subject, chapter, difficulty):
        return len(bank.get(chapter, []))

    def fake_get_questions_from_bank(
        board, grade, subject, chapter, difficulty, num_questions,
        exam_type="General", excluded_ids=None,
    ):
        pool = bank.get(chapter, [])
        if len(pool) < num_questions:
            return []
        # Mimic real sampling: no-replacement, and never mutate the fake bank.
        return [dict(q) for q in pool[:num_questions]]

    monkeypatch.setattr(question_bank_service, "get_bank_capacity", fake_get_bank_capacity)
    monkeypatch.setattr(question_bank_service, "get_questions_from_bank", fake_get_questions_from_bank)


def test_multi_chapter_spreads_questions_across_all_selected_chapters(monkeypatch):
    _patch_bank(monkeypatch, {"Chapter 1": 20, "Chapter 2": 20, "Chapter 3": 20})

    questions = question_bank_service.get_questions_from_bank_multi_chapter(
        board="CBSE", grade="Grade 9", subject="Science",
        chapters=["Chapter 1", "Chapter 2", "Chapter 3"],
        difficulty="Medium", num_questions=40,
    )

    assert len(questions) == 40

    sources = {q["question"].split("]")[0].strip("[") for q in questions}
    assert sources == {"Chapter 1", "Chapter 2", "Chapter 3"}


def test_multi_chapter_never_repeats_a_question_within_one_test(monkeypatch):
    _patch_bank(monkeypatch, {"Chapter 1": 15, "Chapter 2": 15, "Chapter 3": 15})

    questions = question_bank_service.get_questions_from_bank_multi_chapter(
        board="CBSE", grade="Grade 9", subject="Science",
        chapters=["Chapter 1", "Chapter 2", "Chapter 3"],
        difficulty="Medium", num_questions=40,
    )

    assert len(questions) == 40

    db_ids = [q["db_id"] for q in questions]
    question_texts = [q["question"] for q in questions]

    assert len(set(db_ids)) == len(db_ids), "duplicate db_id within one test"
    assert len(set(question_texts)) == len(question_texts), "duplicate question text within one test"


def test_multi_chapter_renumbers_ids_sequentially_after_merging(monkeypatch):
    _patch_bank(monkeypatch, {"Chapter 1": 10, "Chapter 2": 10})

    questions = question_bank_service.get_questions_from_bank_multi_chapter(
        board="CBSE", grade="Grade 9", subject="Science",
        chapters=["Chapter 1", "Chapter 2"],
        difficulty="Medium", num_questions=16,
    )

    assert sorted(q["id"] for q in questions) == list(range(1, 17))


def test_multi_chapter_caps_a_small_chapter_and_fills_the_rest_elsewhere(monkeypatch):
    # Chapter 1 can only supply 2; the other 38 must come from the two big chapters.
    _patch_bank(monkeypatch, {"Chapter 1": 2, "Chapter 2": 30, "Chapter 3": 30})

    questions = question_bank_service.get_questions_from_bank_multi_chapter(
        board="CBSE", grade="Grade 9", subject="Science",
        chapters=["Chapter 1", "Chapter 2", "Chapter 3"],
        difficulty="Medium", num_questions=40,
    )

    assert len(questions) == 40
    db_ids = [q["db_id"] for q in questions]
    assert len(set(db_ids)) == len(db_ids)

    from_chapter_1 = [q for q in questions if q["question"].startswith("[Chapter 1]")]
    assert len(from_chapter_1) == 2  # capped at Chapter 1's own capacity


def test_multi_chapter_reports_shortfall_when_combined_capacity_too_small(monkeypatch):
    _patch_bank(monkeypatch, {"Chapter 1": 5, "Chapter 2": 5})

    questions = question_bank_service.get_questions_from_bank_multi_chapter(
        board="CBSE", grade="Grade 9", subject="Science",
        chapters=["Chapter 1", "Chapter 2"],
        difficulty="Medium", num_questions=40,
    )

    assert questions == []


def test_multi_chapter_deduplicates_repeated_chapter_selection(monkeypatch):
    # Selecting the same chapter twice (e.g. duplicate frontend selection)
    # must not double-count its capacity or sample it twice.
    _patch_bank(monkeypatch, {"Chapter 1": 10})

    questions = question_bank_service.get_questions_from_bank_multi_chapter(
        board="CBSE", grade="Grade 9", subject="Science",
        chapters=["Chapter 1", "Chapter 1"],
        difficulty="Medium", num_questions=10,
    )

    assert len(questions) == 10
    db_ids = [q["db_id"] for q in questions]
    assert len(set(db_ids)) == 10
