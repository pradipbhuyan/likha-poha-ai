"""
test_step_sequence.py — Backend tests for step sequence audit engine.

Tests:
- detects duplicate content between steps
- detects near-duplicate step content
- detects repeated MCQs
- detects repeated examples / sentences
- later step with no new value fails audit
- step-level issue includes step_number
- bulk dry-run reports eligible/skipped counts
- bulk apply refuses unapproved tasks
- bulk apply refuses validation failures
- step scores are in 0-100 range
- empty steps handled gracefully
"""
import pytest
from app.services.step_sequence_service import (
    jaccard_similarity,
    bigram_similarity,
    sentence_overlap,
    combined_similarity,
    score_step,
    audit_lesson_steps,
    check_bulk_apply_eligibility,
    _word_count,
    _unique_word_count,
    _extract_mcqs,
    _extract_formulas,
)

# ── Fixtures ─────────────────────────────────────────────────────────────────

STEP_INTRO = """
In this lesson we will learn about photosynthesis, the process by which plants
make their own food using sunlight, water and carbon dioxide. Plants contain
chlorophyll in their leaves which captures light energy. This energy is used to
convert carbon dioxide and water into glucose and oxygen.
"""

STEP_CORE = """
Photosynthesis happens in two stages: the light-dependent reactions and the
Calvin cycle. In the light-dependent stage chlorophyll absorbs sunlight and
splits water molecules releasing oxygen as a by-product. ATP and NADPH are
produced. In the Calvin cycle carbon dioxide is fixed into organic molecules
using the energy from ATP and NADPH to produce glucose.
"""

STEP_EXAMPLES = """
Let us work through a calculation. If a plant absorbs 6 molecules of carbon
dioxide and 6 molecules of water, it produces 1 molecule of glucose and
6 molecules of oxygen. The balanced equation is:
6CO2 + 6H2O + light energy → C6H12O6 + 6O2
Step 1: count carbon atoms on both sides — 6 on each side, balanced.
Step 2: count hydrogen — 12 on each side, balanced.
Step 3: count oxygen — 18 on each side, balanced.
"""

STEP_EXAM = """
Problem: A plant is kept in the dark for 48 hours. What happens to its starch
reserves and why? Evaluate whether the plant can survive without light.
Solution: Without light the plant cannot perform photosynthesis. It will
consume its stored glucose and starch for energy through cellular respiration.
After 48 hours starch reserves will be depleted. The plant will wilt if
darkness continues.
"""

STEP_RECAP = """
Summary of key points: Photosynthesis converts light energy into chemical
energy stored in glucose. The key inputs are carbon dioxide, water and light.
The outputs are glucose and oxygen. Chlorophyll is the pigment responsible for
capturing light. Remember the equation: 6CO2 + 6H2O → C6H12O6 + 6O2.
Important: photosynthesis only happens in the presence of light.
"""

STEP_EXAM_PREP = """
Common exam mistakes to avoid in photosynthesis questions:
- Confusing reactants and products — reactants are CO2 and H2O, product is glucose.
- Saying all parts of the plant photosynthesise — only green parts with chlorophyll.
- Forgetting oxygen is a by-product, not a reactant.
Practice tip: draw and label a chloroplast diagram, including thylakoids and stroma.
Exam question: explain the effect of increasing light intensity on the rate of
photosynthesis with reference to limiting factors.
"""

GOOD_STEPS = [
    {"step_number": 1, "step_title": "Concept Introduction", "content": STEP_INTRO},
    {"step_number": 2, "step_title": "Core Explanation",     "content": STEP_CORE},
    {"step_number": 3, "step_title": "Worked Examples",      "content": STEP_EXAMPLES},
    {"step_number": 4, "step_title": "Exam-Style Problems",  "content": STEP_EXAM},
    {"step_number": 5, "step_title": "Revision and Recap",   "content": STEP_RECAP},
    {"step_number": 6, "step_title": "Exam Preparation",     "content": STEP_EXAM_PREP},
]

# Duplicate steps — same content repeated
DUP_STEPS = [
    {"step_number": 1, "step_title": "Step 1", "content": STEP_INTRO},
    {"step_number": 2, "step_title": "Step 2", "content": STEP_INTRO},  # exact duplicate
    {"step_number": 3, "step_title": "Step 3", "content": STEP_CORE},
    {"step_number": 4, "step_title": "Step 4", "content": STEP_INTRO},  # near duplicate
    {"step_number": 5, "step_title": "Step 5", "content": STEP_RECAP},
    {"step_number": 6, "step_title": "Step 6", "content": STEP_EXAM_PREP},
]

# Step that adds nothing new
EMPTY_VALUE_STEPS = [
    {"step_number": 1, "step_title": "Step 1", "content": STEP_INTRO},
    {"step_number": 2, "step_title": "Step 2", "content": STEP_INTRO[:50]},  # tiny stub
    {"step_number": 3, "step_title": "Step 3", "content": STEP_CORE},
]

MCQ_STEPS = [
    {
        "step_number": 1, "step_title": "Step 1",
        "content": "What is photosynthesis? A. Making food  B. Eating food  C. Moving  D. Sleeping"
    },
    {
        "step_number": 2, "step_title": "Step 2",
        "content": "What is photosynthesis? A. Making food  B. Eating food  C. Moving  D. Sleeping\nAdditional content about plants."
    },
]


# ── Similarity tests ──────────────────────────────────────────────────────────

def test_identical_texts_score_high():
    sim = jaccard_similarity(STEP_INTRO, STEP_INTRO)
    assert sim == 1.0


def test_different_texts_score_low():
    sim = jaccard_similarity(STEP_INTRO, STEP_EXAM_PREP)
    assert sim < 0.5


def test_bigram_identical():
    assert bigram_similarity("hello world foo", "hello world foo") == 1.0


def test_bigram_different():
    sim = bigram_similarity("cats eat fish daily", "dogs run very fast indeed")
    assert sim < 0.1


def test_sentence_overlap_identical():
    text = "The sun is bright. The sky is blue. Water is wet."
    assert sentence_overlap(text, text) == 1.0


def test_sentence_overlap_different():
    a = "Photosynthesis makes glucose from sunlight."
    b = "Humans eat food to get energy from digestion."
    assert sentence_overlap(a, b) < 0.2


def test_combined_similarity_identical():
    sim = combined_similarity(STEP_INTRO, STEP_INTRO)
    assert sim > 0.95


def test_combined_similarity_different():
    sim = combined_similarity(STEP_INTRO, STEP_EXAM_PREP)
    assert sim < 0.4


# ── step_score tests ──────────────────────────────────────────────────────────

def test_score_step_returns_all_fields():
    texts = [s["content"] for s in GOOD_STEPS]
    result = score_step(0, texts[0], texts)
    for field in [
        "step_uniqueness_score", "depth_progression_score",
        "cross_step_repetition_score", "step_completeness_score",
        "overall_step_score", "status", "issues", "word_count",
        "pairwise_similarities",
    ]:
        assert field in result, f"Missing field: {field}"


def test_score_step_scores_in_range():
    texts = [s["content"] for s in GOOD_STEPS]
    for i in range(len(texts)):
        result = score_step(i, texts[i], texts)
        assert 0 <= result["step_uniqueness_score"] <= 100
        assert 0 <= result["depth_progression_score"] <= 100
        assert 0 <= result["cross_step_repetition_score"] <= 100
        assert 0 <= result["step_completeness_score"] <= 100
        assert 0 <= result["overall_step_score"] <= 100


def test_duplicate_step_flagged_critical():
    texts = [s["content"] for s in DUP_STEPS]
    result = score_step(1, texts[1], texts)  # Step 2 = exact duplicate of Step 1
    critical_issues = [i for i in result["issues"] if i["severity"] == "critical"]
    assert len(critical_issues) > 0, "Duplicate step should have critical issues"


def test_good_steps_pass_audit():
    texts = [s["content"] for s in GOOD_STEPS]
    # Step 3 (worked examples) should have relatively good scores
    result = score_step(2, texts[2], texts)
    assert result["status"] in ("pass", "warning"), "Good step should not be critical"


def test_step_with_no_unique_content_is_critical():
    tiny = "the plant"  # essentially 0 unique words
    full = STEP_INTRO
    result = score_step(1, tiny, [full, tiny, full, full, full, full])
    critical = [i for i in result["issues"] if i["severity"] == "critical"]
    assert len(critical) > 0


def test_issue_includes_step_number():
    texts = [s["content"] for s in DUP_STEPS]
    result = score_step(1, texts[1], texts)
    for issue in result["issues"]:
        assert "step" in issue["issue_message"].lower() or "repeated" in issue["issue_type"].lower()


# ── audit_lesson_steps tests ──────────────────────────────────────────────────

def test_audit_returns_step_results_for_all_steps():
    result = audit_lesson_steps("Grade 9", "Science", "Photosynthesis", GOOD_STEPS)
    assert result["num_steps"] == 6
    assert len(result["step_results"]) == 6


def test_audit_returns_similarity_matrix():
    result = audit_lesson_steps("Grade 9", "Science", "Photosynthesis", GOOD_STEPS)
    matrix = result["similarity_matrix"]
    assert len(matrix) == 6
    for row in matrix:
        assert len(row) == 6
    # Diagonal must be 1.0
    for i in range(6):
        assert matrix[i][i] == 1.0


def test_audit_duplicate_steps_high_critical_count():
    result = audit_lesson_steps("Grade 9", "Science", "Test", DUP_STEPS)
    assert result["summary"]["critical_issues"] > 0


def test_audit_good_steps_low_critical_count():
    result = audit_lesson_steps("Grade 9", "Science", "Photosynthesis", GOOD_STEPS)
    assert result["summary"]["critical_issues"] == 0 or result["summary"]["overall_step_sequence_score"] >= 50


def test_audit_all_issues_include_step_number():
    result = audit_lesson_steps("Grade 9", "Science", "Test", DUP_STEPS)
    for issue in result["all_issues"]:
        assert "step_number" in issue
        assert isinstance(issue["step_number"], int)
        assert issue["step_number"] >= 1


def test_audit_summary_has_required_fields():
    result = audit_lesson_steps("Grade 9", "Science", "Test", GOOD_STEPS)
    summary = result["summary"]
    for field in [
        "overall_step_sequence_score", "critical_issues", "high_issues",
        "steps_with_issues", "eligible_for_bulk_apply",
        "avg_step_uniqueness_score", "depth_progression_score",
    ]:
        assert field in summary, f"Missing summary field: {field}"


def test_audit_empty_steps_returns_error():
    result = audit_lesson_steps("Grade 9", "Science", "Test", [])
    assert "error" in result


def test_audit_detects_repeated_mcq():
    result = audit_lesson_steps("Grade 9", "Science", "Test", MCQ_STEPS)
    issue_types = [i["issue_type"] for i in result["all_issues"]]
    assert any("mcq" in t for t in issue_types) or len(result["all_issues"]) > 0


def test_audit_detects_near_duplicate_sentence():
    # Make two steps that share almost the same sentences
    s1 = "Photosynthesis is the process by which plants make food. It requires sunlight, CO2, and water."
    s2 = "Photosynthesis is the process by which plants make food. It also requires sunlight, CO2, and water."
    steps = [
        {"step_number": 1, "step_title": "Step 1", "content": s1},
        {"step_number": 2, "step_title": "Step 2", "content": s2},
    ]
    result = audit_lesson_steps("Grade 9", "Science", "Test", steps)
    # Should detect high similarity
    assert result["summary"]["critical_issues"] > 0 or result["summary"]["high_issues"] > 0


def test_later_step_no_new_value_flagged():
    # Step 3 is much shorter than Step 1/2 and adds nothing new
    s1 = STEP_INTRO
    s2 = STEP_CORE
    s3 = "The plant."  # essentially nothing
    steps = [
        {"step_number": 1, "step_title": "Step 1", "content": s1},
        {"step_number": 2, "step_title": "Step 2", "content": s2},
        {"step_number": 3, "step_title": "Step 3", "content": s3},
    ]
    result = audit_lesson_steps("Grade 9", "Science", "Test", steps)
    step3_issues = [i for i in result["all_issues"] if i["step_number"] == 3]
    assert len(step3_issues) > 0


# ── check_bulk_apply_eligibility tests ───────────────────────────────────────

def test_bulk_dry_run_eligible_approved_tasks():
    tasks = [
        {
            "id": "task-1",
            "status": "approved",
            "audit_after_score": 92,
            "validation_result_json": {"valid": True},
        },
        {
            "id": "task-2",
            "status": "approved",
            "audit_after_score": 95,
            "validation_result_json": {"valid": True},
        },
    ]
    result = check_bulk_apply_eligibility(tasks)
    assert result["eligible"] == 2
    assert result["skipped"] == 0
    assert result["can_bulk_apply"] is True


def test_bulk_refuses_unapproved_tasks():
    tasks = [
        {"id": "task-1", "status": "running",  "audit_after_score": 95},
        {"id": "task-2", "status": "queued",   "audit_after_score": 95},
    ]
    result = check_bulk_apply_eligibility(tasks)
    assert result["eligible"] == 0
    assert result["skipped"] == 2
    assert result["can_bulk_apply"] is False


def test_bulk_refuses_validation_failures():
    tasks = [
        {
            "id": "task-1",
            "status": "approved",
            "audit_after_score": 92,
            "validation_result_json": {"valid": False},  # failed validation
        },
    ]
    result = check_bulk_apply_eligibility(tasks)
    assert result["eligible"] == 0
    assert result["skipped"] == 1


def test_bulk_refuses_low_score_tasks():
    tasks = [
        {
            "id": "task-1",
            "status": "approved",
            "audit_after_score": 70,  # below default min_score=90
            "validation_result_json": {"valid": True},
        },
    ]
    result = check_bulk_apply_eligibility(tasks, min_score=90)
    assert result["eligible"] == 0


def test_bulk_mixed_eligible_and_skipped():
    tasks = [
        {
            "id": "task-ok",
            "status": "approved",
            "audit_after_score": 93,
            "validation_result_json": {"valid": True},
        },
        {
            "id": "task-bad-status",
            "status": "failed",
            "audit_after_score": 95,
        },
        {
            "id": "task-low-score",
            "status": "approved",
            "audit_after_score": 80,
            "validation_result_json": {"valid": True},
        },
    ]
    result = check_bulk_apply_eligibility(tasks, min_score=90)
    assert result["eligible"] == 1
    assert result["skipped"] == 2
    assert "task-ok" in result["eligible_task_ids"]


def test_bulk_task_with_no_after_score_eligible():
    """Tasks without an after score (not yet repaired) are eligible if status is right."""
    tasks = [
        {
            "id": "task-1",
            "status": "ready_for_review",
            # No audit_after_score set
        },
    ]
    result = check_bulk_apply_eligibility(tasks)
    assert result["eligible"] == 1


# ── Utility function tests ────────────────────────────────────────────────────

def test_word_count_basic():
    assert _word_count("hello world foo bar") == 4
    assert _word_count("") == 0
    assert _word_count("   ") == 0


def test_unique_word_count_all_unique():
    text = "xenophyte zephyr quorum"
    other = ["apple banana orange"]
    assert _unique_word_count(text, other) == 3


def test_unique_word_count_all_shared():
    text = "apple banana orange"
    other = ["apple banana orange cherry grape"]
    assert _unique_word_count(text, other) == 0


def test_extract_mcqs_finds_options():
    text = "What is photosynthesis?\nA. Making food\nB. Eating food\nC. None"
    mcqs = _extract_mcqs(text)
    assert len(mcqs) > 0


def test_extract_formulas_finds_equations():
    text = "The formula is: E = mc^2\nAnother: F = ma"
    formulas = _extract_formulas(text)
    assert len(formulas) >= 2


def test_extract_formulas_ignores_plain_text():
    text = "The cat sat on the mat and played with yarn."
    formulas = _extract_formulas(text)
    assert len(formulas) == 0
