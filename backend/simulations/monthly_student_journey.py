"""
Monthly Student Journey Simulation

This script simulates a student using the AI Tutor platform over a month.

It is not a normal unit test. It is a scenario simulation that calls the
backend APIs and checks whether platform state changes as expected.

Run from the backend folder:

    SIM_STUDENT_TOKEN="your_token_here" ./venv/bin/python simulations/monthly_student_journey.py

Before running, make sure the backend server is running:

    ./venv/bin/python -m uvicorn app.main:app --reload

Important:
- This simulation may call real AI services.
- This simulation may write data to Supabase.
- This simulation uses the test user: monthly_sim_student.
"""

import os
from datetime import datetime, timezone
from pprint import pprint

import requests


BASE_URL = "http://localhost:8000"

SIM_USER = "monthly_sim_student"
STUDENT_TOKEN = os.getenv("SIM_STUDENT_TOKEN")


def auth_headers():
    """
    Return Authorization headers when SIM_STUDENT_TOKEN is provided.

    Protected backend routes require a logged-in student bearer token.
    """
    if not STUDENT_TOKEN:
        return {}

    return {
        "Authorization": f"Bearer {STUDENT_TOKEN}",
    }


MONTHLY_PLAN = [
    {
        "subject": "Science",
        "chapter": "Matter in Our Surroundings",
        "step_title": "What is matter?",
    },
    {
        "subject": "Science",
        "chapter": "Tissues",
        "step_title": "Plant tissues",
    },
    {
        "subject": "Mathematics",
        "chapter": "Number Systems",
        "step_title": "Rational and irrational numbers",
    },
    {
        "subject": "Mathematics",
        "chapter": "Polynomials",
        "step_title": "Introduction to polynomials",
    },
    {
        "subject": "English",
        "chapter": "Reading Comprehension",
        "step_title": "Understanding passages",
    },
]

SOF_PLAN = [
    {
        "subject": "Science Olympiad",
        "chapter": "General Science",
        "step_title": "Olympiad reasoning basics",
    }
]


def post(path, payload):
    """
    Helper function for POST requests.
    """
    url = f"{BASE_URL}{path}"

    response = requests.post(
        url,
        json=payload,
        headers=auth_headers(),
        timeout=90,
    )

    print(f"POST {path} -> {response.status_code}")

    try:
        data = response.json()
    except Exception:
        print(response.text)
        raise

    if response.status_code >= 400:
        pprint(data)
        raise RuntimeError(f"Request failed: {path}")

    return data


def get(path):
    """
    Helper function for GET requests.
    """
    url = f"{BASE_URL}{path}"

    response = requests.get(
        url,
        headers=auth_headers(),
        timeout=90,
    )

    print(f"GET {path} -> {response.status_code}")

    try:
        data = response.json()
    except Exception:
        print(response.text)
        raise

    if response.status_code >= 400:
        pprint(data)
        raise RuntimeError(f"Request failed: {path}")

    return data


def assert_success(response_data, label):
    """
    Verify that an API response contains success=True when that field exists.
    """
    if "success" in response_data and response_data["success"] is not True:
        pprint(response_data)
        raise AssertionError(f"{label} did not return success=True")


def generate_lesson(subject, chapter, step_title, mode="CBSE"):
    """
    Simulate a student generating a lesson.
    """
    return post(
        "/api/lesson/generate",
        {
            "username": SIM_USER,
            "grade": "Grade 9",
            "mode": mode,
            "subject": subject,
            "chapter": chapter,
            "step_title": step_title,
            "teacher_persona": "friendly",
        },
    )


def save_progress(subject, chapter, step_index, completed, lesson, mode="CBSE"):
    """
    Simulate saving chapter progress.
    """
    return post(
        "/api/progress/save",
        {
            "username": SIM_USER,
            "grade": "Grade 9",
            "mode": mode,
            "subject": subject,
            "chapter": chapter,
            "current_step_index": step_index,
            "completed": completed,
            "last_lesson": lesson,
            "step_lessons": {
                str(step_index): lesson,
            },
        },
    )


def ask_doubt(subject, chapter, doubt_number=1, mode="CBSE"):
    """
    Simulate a student asking a doubt.
    """
    return post(
        "/api/doubt/answer",
        {
            "username": SIM_USER,
            "grade": "Grade 9",
            "mode": mode,
            "subject": subject,
            "chapter": chapter,
            "question": (
                f"Doubt {doubt_number}: Can you explain one important "
                f"concept from {chapter}?"
            ),
        },
    )


def ask_multiple_doubts(subject, chapter, count=2, mode="CBSE"):
    """
    Ask a small number of doubts.

    The heavier family simulation can ask 5 doubts per chapter.
    This lightweight simulation keeps cost and runtime lower.
    """
    for doubt_number in range(1, count + 1):
        ask_doubt(
            subject=subject,
            chapter=chapter,
            doubt_number=doubt_number,
            mode=mode,
        )


def evaluate_answer(subject, chapter):
    """
    Simulate student answer evaluation.
    """
    return post(
        "/api/evaluation/evaluate",
        {
            "username": SIM_USER,
            "question": f"What did you learn in {chapter}?",
            "student_answer": f"I learned the main ideas of {chapter}.",
            "ideal_context": (
                f"{chapter} contains important concepts for Grade 9 {subject}."
            ),
        },
    )


def generate_practice_questions(subject, chapter, lesson=None):
    """
    Simulate practice question generation.
    """
    return post(
        "/api/evaluation/practice-questions",
        {
            "username": SIM_USER,
            "question": chapter,
            "student_answer": "Practice answer placeholder.",
            "ideal_context": lesson or f"Lesson context for {chapter} in {subject}.",
        },
    )


def log_activity(activity_type):
    """
    Log student activity so profile XP, streaks, and counters update.
    """
    return post(
        "/api/profile/activity",
        {
            "username": SIM_USER,
            "activity_type": activity_type,
        },
    )


def save_test_history(
    subject,
    chapter,
    mock_type,
    exam_type,
    difficulty,
    final_score,
    max_score,
    mode="CBSE",
):
    """
    Save a mock test result into test history.

    This is important because recommendations are based on test_history,
    not only on profile activity counters.
    """
    percentage = round((final_score / max_score) * 100, 2)

    return post(
        "/api/analytics/test-history",
        {
            "username": SIM_USER,
            "grade": "Grade 9",
            "mode": mode,
            "subject": subject,
            "chapter": chapter,
            "mockType": mock_type,
            "examType": exam_type,
            "difficulty": difficulty,
            "rawScore": final_score,
            "finalScore": final_score,
            "maxScore": max_score,
            "wrongCount": int(max_score - final_score),
            "penalty": 0,
            "percentage": percentage,
            "submittedAt": datetime.now(timezone.utc).isoformat(),
        },
    )


def generate_cbse_mock_test(subject, chapter):
    """
    Simulate taking a CBSE mock test.
    """
    return post(
        "/api/mock-test/generate",
        {
            "username": SIM_USER,
            "grade": "Grade 9",
            "mode": "CBSE",
            "subject": subject,
            "chapter": chapter,
            "mock_type": "CBSE Mock Test",
            "exam_type": "Class Test",
            "question_count": 3,
            "difficulty": "medium",
        },
    )


def generate_sof_test(subject="Science Olympiad", chapter="General Science"):
    """
    Simulate taking an SOF Olympiad mock test.
    """
    return post(
        "/api/mock-test/generate",
        {
            "username": SIM_USER,
            "grade": "Grade 9",
            "mode": "SOF",
            "subject": subject,
            "chapter": chapter,
            "mock_type": "SOF Olympiad Mock Test",
            "exam_type": "Olympiad",
            "question_count": 3,
            "difficulty": "medium",
        },
    )


def get_test_history():
    """
    Fetch saved test history for the simulated user.
    """
    return get(f"/api/analytics/test-history/{SIM_USER}")


def get_dashboard_snapshots():
    """
    Fetch final platform state after the simulated month.
    """
    profile = get(f"/api/profile/{SIM_USER}")
    usage = get(f"/api/usage/summary?username={SIM_USER}")
    recommendations = get(f"/api/recommendations/{SIM_USER}")
    test_history = get_test_history()

    return {
        "profile": profile,
        "usage": usage,
        "recommendations": recommendations,
        "test_history": test_history,
    }


def verify_test_history_has_entries():
    """
    Verify test_history is populated.

    Recommendations depend on test_history, so this check catches regressions
    where mock activity counters increase but actual test results are not saved.
    """
    data = get_test_history()
    assert_success(data, "Get test history")

    history = data.get("history") or []

    if not history:
        pprint(data)
        raise AssertionError(
            "Expected saved test_history entries, but none were found."
        )

    print(f"Verified test history entries: {len(history)}")


def verify_recommendations_are_not_fallback_only(recommendations_response):
    """
    Verify recommendations are based on test history, not only the fallback.

    The fallback recommendation is useful for brand-new users, but this
    simulation saves test_history, so recommendations should become personalized.
    """
    recommendations = recommendations_response.get("recommendations") or []

    if not recommendations:
        pprint(recommendations_response)
        raise AssertionError("Expected at least one recommendation.")

    fallback_only = (
        len(recommendations) == 1
        and recommendations[0].get("type") == "start"
    )

    if fallback_only:
        pprint(recommendations_response)
        raise AssertionError(
            "Recommendations still show fallback-only result even though "
            "test_history was saved."
        )

    print("Verified recommendations are based on saved activity/test history.")


def verify_usage_summary(usage_response):
    """
    Verify usage summary shows tracked activity.
    """
    totals = usage_response.get("totals") or {}

    if int(totals.get("requests") or 0) <= 0:
        pprint(usage_response)
        raise AssertionError("Expected usage summary to show requests > 0.")

    if int(totals.get("total_tokens") or 0) <= 0:
        pprint(usage_response)
        raise AssertionError("Expected usage summary to show tokens > 0.")

    print("Verified usage summary contains tracked requests and tokens.")


def run_cbse_activity(index, item):
    """
    Run one CBSE study activity.
    """
    subject = item["subject"]
    chapter = item["chapter"]
    step_title = item["step_title"]

    print("\n" + "=" * 80)
    print(f"CBSE Activity {index}: {subject} - {chapter}")

    lesson_response = generate_lesson(
        subject=subject,
        chapter=chapter,
        step_title=step_title,
        mode="CBSE",
    )

    assert_success(lesson_response, "Generate CBSE lesson")

    lesson = lesson_response.get("lesson") or f"Generated lesson for {chapter}"

    save_response = save_progress(
        subject=subject,
        chapter=chapter,
        step_index=1,
        completed=True,
        lesson=lesson,
        mode="CBSE",
    )

    assert_success(save_response, "Save CBSE progress")

    log_activity("lesson_completed")

    ask_multiple_doubts(
        subject=subject,
        chapter=chapter,
        count=2,
        mode="CBSE",
    )

    evaluation_response = evaluate_answer(subject, chapter)
    assert_success(evaluation_response, "Evaluate answer")

    practice_response = generate_practice_questions(subject, chapter, lesson)
    assert_success(practice_response, "Generate practice questions")

    log_activity("quiz_attempted")

    mock_response = generate_cbse_mock_test(subject, chapter)
    assert_success(mock_response, "Generate CBSE mock test")

    log_activity("mock_test_taken")

    score_plan = {
        "Matter in Our Surroundings": 2,
        "Tissues": 3,
        "Number Systems": 3,
        "Polynomials": 2,
        "Reading Comprehension": 1,
    }

    final_score = score_plan.get(chapter, 2)
    max_score = 3

    history_response = save_test_history(
        subject=subject,
        chapter=chapter,
        mock_type="CBSE Mock Test",
        exam_type="Class Test",
        difficulty="medium",
        final_score=final_score,
        max_score=max_score,
        mode="CBSE",
    )

    assert_success(history_response, "Save CBSE test history")


def run_sof_activity(index, item):
    """
    Run one SOF/Olympiad study activity.

    This intentionally exercises SOF mode for lesson, doubt, mock test,
    test history, and recommendations.
    """
    subject = item["subject"]
    chapter = item["chapter"]
    step_title = item["step_title"]

    print("\n" + "=" * 80)
    print(f"SOF Activity {index}: {subject} - {chapter}")

    lesson_response = generate_lesson(
        subject=subject,
        chapter=chapter,
        step_title=step_title,
        mode="SOF",
    )

    assert_success(lesson_response, "Generate SOF lesson")

    lesson = lesson_response.get("lesson") or f"Generated lesson for {chapter}"

    save_response = save_progress(
        subject=subject,
        chapter=chapter,
        step_index=1,
        completed=True,
        lesson=lesson,
        mode="SOF",
    )

    assert_success(save_response, "Save SOF progress")

    log_activity("lesson_completed")

    ask_multiple_doubts(
        subject=subject,
        chapter=chapter,
        count=2,
        mode="SOF",
    )

    practice_response = generate_practice_questions(subject, chapter, lesson)
    assert_success(practice_response, "Generate SOF practice questions")

    log_activity("quiz_attempted")

    mock_response = generate_sof_test(subject, chapter)
    assert_success(mock_response, "Generate SOF mock test")

    log_activity("mock_test_taken")

    history_response = save_test_history(
        subject=subject,
        chapter=chapter,
        mock_type="SOF Olympiad Mock Test",
        exam_type="Olympiad",
        difficulty="medium",
        final_score=3,
        max_score=3,
        mode="SOF",
    )

    assert_success(history_response, "Save SOF test history")


def run_monthly_simulation():
    """
    Run the full simulated month.
    """
    print("\nStarting monthly student journey simulation")
    print(f"Student: {SIM_USER}")

    if not STUDENT_TOKEN:
        raise RuntimeError(
            "SIM_STUDENT_TOKEN is missing. Login as the simulation student, "
            "copy the Supabase access_token from browser local storage, then run:\n"
            'SIM_STUDENT_TOKEN="your_token_here" '
            "./venv/bin/python simulations/monthly_student_journey.py"
        )

    for index, item in enumerate(MONTHLY_PLAN, start=1):
        run_cbse_activity(index, item)

    for index, item in enumerate(SOF_PLAN, start=1):
        run_sof_activity(index, item)

    print("\n" + "=" * 80)
    print("Verifying saved test history")
    verify_test_history_has_entries()

    print("\n" + "=" * 80)
    print("Fetching dashboard snapshots")
    snapshots = get_dashboard_snapshots()

    verify_usage_summary(snapshots["usage"])
    verify_recommendations_are_not_fallback_only(
        snapshots["recommendations"]
    )

    print("\nFinal Simulation Summary")
    pprint(snapshots)

    print("\nMonthly simulation completed successfully")


if __name__ == "__main__":
    run_monthly_simulation()