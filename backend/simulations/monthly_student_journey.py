"""
Monthly Student Journey Simulation

This script simulates a student using the AI Tutor platform over a month.

It is not a normal unit test. It is a scenario simulation that calls the
backend APIs and checks whether platform state changes as expected.

Run from the backend folder:

    ./venv/bin/python simulations/monthly_student_journey.py

Before running, make sure the backend server is running:

    ./venv/bin/python -m uvicorn app.main:app --reload
"""

import requests
from pprint import pprint
from datetime import datetime, timezone



BASE_URL = "http://localhost:8000"

SIM_USER = f"monthly_sim_student_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

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


def post(path, payload):
    """
    Helper function for POST requests.
    """
    url = f"{BASE_URL}{path}"
    response = requests.post(url, json=payload, timeout=60)

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
    response = requests.get(url, timeout=60)

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


def generate_lesson(subject, chapter, step_title):
    """
    Simulate a student generating a lesson.
    """
    return post(
        "/api/lesson/generate",
        {
            "username": SIM_USER,
            "grade": "Grade 9",
            "mode": "CBSE",
            "subject": subject,
            "chapter": chapter,
            "step_title": step_title,
            "teacher_persona": "friendly",
        },
    )


def save_progress(subject, chapter, step_index, completed, lesson):
    """
    Simulate saving chapter progress.
    """
    return post(
        "/api/progress/save",
        {
            "username": SIM_USER,
            "grade": "Grade 9",
            "mode": "CBSE",
            "subject": subject,
            "chapter": chapter,
            "current_step_index": step_index,
            "completed": completed,
            "last_lesson": lesson,
        },
    )


def ask_doubt(subject, chapter):
    """
    Simulate a student asking a doubt.
    """
    return post(
        "/api/doubt/answer",
        {
            "username": SIM_USER,
            "grade": "Grade 9",
            "mode": "CBSE",
            "subject": subject,
            "chapter": chapter,
            "question": f"Can you explain one important concept from {chapter}?",
        },
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
            "ideal_context": f"{chapter} contains important concepts for Grade 9 {subject}.",
        },
    )


def generate_practice_questions(subject, chapter):
    """
    Simulate practice question generation.
    """
    return post(
        "/api/evaluation/practice-questions",
        {
            "username": SIM_USER,
            "question": chapter,
            "student_answer": "Practice answer placeholder.",
            "ideal_context": f"Lesson context for {chapter} in {subject}.",
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
            "mode": "CBSE" if mock_type != "SOF Olympiad Mock Test" else "Olympiad",
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


def generate_sof_test():
    """
    Simulate taking an SOF Olympiad mock test.
    """
    return post(
        "/api/mock-test/generate",
        {
            "username": SIM_USER,
            "grade": "Grade 9",
            "mode": "Olympiad",
            "subject": "Science Olympiad",
            "chapter": "General Science",
            "mock_type": "SOF Olympiad Mock Test",
            "exam_type": "Olympiad",
            "question_count": 3,
            "difficulty": "medium",
        },
    )


def get_dashboard_snapshots():
    """
    Fetch final platform state after the simulated month.
    """
    profile = get(f"/api/profile/{SIM_USER}")
    usage = get(f"/api/usage/summary?username={SIM_USER}")
    recommendations = get(f"/api/recommendations/{SIM_USER}")

    return {
        "profile": profile,
        "usage": usage,
        "recommendations": recommendations,
    }


def run_monthly_simulation():
    """
    Run the full simulated month.
    """
    print("\nStarting monthly student journey simulation")
    print(f"Student: {SIM_USER}")

    for index, item in enumerate(MONTHLY_PLAN, start=1):
        subject = item["subject"]
        chapter = item["chapter"]
        step_title = item["step_title"]

        print("\n" + "=" * 80)
        print(f"Activity {index}: {subject} - {chapter}")

        lesson_response = generate_lesson(subject, chapter, step_title)
        lesson = lesson_response.get("lesson") or f"Generated lesson for {chapter}"

        save_progress(
            subject=subject,
            chapter=chapter,
            step_index=1,
            completed=True,
            lesson=lesson,
        )
        
        log_activity("lesson_completed")

        ask_doubt(subject, chapter)
        evaluate_answer(subject, chapter)
        
        generate_practice_questions(subject, chapter)
        log_activity("quiz_attempted")

        generate_cbse_mock_test(subject, chapter)
        log_activity("mock_test_taken")

        # Save a realistic test score so recommendations can use test_history.
        # Scores are intentionally varied to produce useful recommendations.
        score_plan = {
            "Matter in Our Surroundings": 2,
            "Tissues": 3,
            "Number Systems": 3,
            "Polynomials": 2,
            "Reading Comprehension": 1,
        }

        final_score = score_plan.get(chapter, 2)
        max_score = 3

        save_test_history(
            subject=subject,
            chapter=chapter,
            mock_type="CBSE Mock Test",
            exam_type="Class Test",
            difficulty="medium",
            final_score=final_score,
            max_score=max_score,
        )

    print("\n" + "=" * 80)
    print("Taking SOF Olympiad mock test")
    generate_sof_test()
    log_activity("mock_test_taken")

    save_test_history(
        subject="Science Olympiad",
        chapter="General Science",
        mock_type="SOF Olympiad Mock Test",
        exam_type="Olympiad",
        difficulty="medium",
        final_score=3,
        max_score=3,
    )

    print("\n" + "=" * 80)
    print("Fetching dashboard snapshots")
    snapshots = get_dashboard_snapshots()
    
    profile = snapshots["profile"]["profile"]
    recommendations = snapshots["recommendations"]["recommendations"]
    usage_totals = snapshots["usage"]["totals"]

    assert profile["lessons_completed"] >= 5
    assert profile["quizzes_attempted"] >= 5
    assert profile["mock_tests_taken"] >= 6
    assert profile["xp_points"] > 0
    assert len(recommendations) > 0
    assert usage_totals["requests"] > 0

    print("\nFinal Simulation Summary")
    pprint(snapshots)

    print("\nMonthly simulation completed successfully")


if __name__ == "__main__":
    run_monthly_simulation()