"""
Family Monthly Journey Simulation

This script simulates a test family using the AI Tutor platform.

Test family:
- Parent username:  Pradip-TestParent
- Student username: Akshita-TestStudent

It supports two scenarios:

1. CBSE monthly simulation
   - Student studies CBSE subjects and chapters
   - Generates lessons
   - Saves progress
   - Asks 5 doubts per chapter
   - Evaluates answers
   - Generates practice questions
   - Takes CBSE mock tests
   - Saves test history

2. SOF monthly simulation
   - Student studies SOF / Olympiad subjects and chapters
   - Generates lessons
   - Saves progress
   - Asks 5 doubts per chapter
   - Takes SOF mock tests
   - Saves test history

Run from backend folder:

    ./venv/bin/python simulations/family_monthly_journey.py --scenario cbse
    ./venv/bin/python simulations/family_monthly_journey.py --scenario sof
    ./venv/bin/python simulations/family_monthly_journey.py --scenario all

Before running, make sure backend is running:

    ./venv/bin/python -m uvicorn app.main:app --reload

Optional environment variables:

    SIM_STUDENT_TOKEN=<student bearer token>
    SIM_ADMIN_TOKEN=<admin bearer token>
    SIM_DAYS=30
    SIM_MAX_CHAPTERS_PER_SUBJECT=0

Notes:
- SIM_MAX_CHAPTERS_PER_SUBJECT=0 means no chapter limit.
- This script may call real AI services and write real data to Supabase.
- A full 30-day run with 5 doubts per chapter can be expensive.
"""

import argparse
import os
from datetime import datetime, timedelta, timezone
from pprint import pprint

import requests


BASE_URL = "http://localhost:8000"

PARENT_USERNAME = "Pradip-TestParent"
STUDENT_USERNAME = "Akshita-TestStudent"

PARENT_EMAIL = "pradip.testparent@example.com"
STUDENT_EMAIL = "akshita.teststudent@example.com"

DEFAULT_GRADE = "Grade 9"

DOUBTS_PER_CHAPTER = 5

SIM_DAYS = int(os.getenv("SIM_DAYS", "30"))
SIM_MAX_CHAPTERS_PER_SUBJECT = int(
    os.getenv("SIM_MAX_CHAPTERS_PER_SUBJECT", "0")
)

STUDENT_TOKEN = os.getenv("SIM_STUDENT_TOKEN")
ADMIN_TOKEN = os.getenv("SIM_ADMIN_TOKEN")


def auth_headers(token=None):
    if not token:
        return {}

    return {
        "Authorization": f"Bearer {token}",
    }


def post(path, payload, token=None, timeout=90):
    url = f"{BASE_URL}{path}"

    response = requests.post(
        url,
        json=payload,
        headers=auth_headers(token),
        timeout=timeout,
    )

    print(f"POST {path} -> {response.status_code}")

    try:
        data = response.json()
    except Exception:
        print(response.text)
        raise

    if response.status_code >= 400:
        pprint(data)
        raise RuntimeError(f"Request failed: POST {path}")

    return data


def patch(path, payload, token=None, timeout=90):
    url = f"{BASE_URL}{path}"

    response = requests.patch(
        url,
        json=payload,
        headers=auth_headers(token),
        timeout=timeout,
    )

    print(f"PATCH {path} -> {response.status_code}")

    try:
        data = response.json()
    except Exception:
        print(response.text)
        raise

    if response.status_code >= 400:
        pprint(data)
        raise RuntimeError(f"Request failed: PATCH {path}")

    return data


def get(path, token=None, timeout=90):
    url = f"{BASE_URL}{path}"

    response = requests.get(
        url,
        headers=auth_headers(token),
        timeout=timeout,
    )

    print(f"GET {path} -> {response.status_code}")

    try:
        data = response.json()
    except Exception:
        print(response.text)
        raise

    if response.status_code >= 400:
        pprint(data)
        raise RuntimeError(f"Request failed: GET {path}")

    return data


def create_test_family_if_admin_token_available():
    """
    Create parent and child through admin APIs when SIM_ADMIN_TOKEN is available.

    If there is no admin token, the simulation still runs using STUDENT_USERNAME.
    This is useful when the test user already exists in Supabase.
    """
    if not ADMIN_TOKEN:
        print("\nSIM_ADMIN_TOKEN not set. Skipping family creation.")
        print("Make sure Akshita-TestStudent already exists and has access.")
        return None

    print("\nCreating test family through admin APIs")

    parent_response = post(
        "/api/admin/parents",
        {
            "email": PARENT_EMAIL,
            "password": "TestPassword123!",
            "username": PARENT_USERNAME,
        },
        token=ADMIN_TOKEN,
    )

    parent = parent_response.get("parent") or {}
    family_id = parent.get("family_id")
    parent_id = parent.get("id")

    if not family_id or not parent_id:
        raise RuntimeError("Parent creation did not return family_id/parent_id")

    child_response = post(
        "/api/admin/children",
        {
            "email": STUDENT_EMAIL,
            "password": "TestPassword123!",
            "username": STUDENT_USERNAME,
            "parent_id": parent_id,
            "family_id": family_id,
        },
        token=ADMIN_TOKEN,
    )

    child = child_response.get("child") or {}
    child_id = child.get("id")

    if not child_id:
        raise RuntimeError("Child creation did not return child id")

    patch(
        f"/api/admin/access/{child_id}",
        {
            "access_cbse": True,
            "access_sof_science": True,
            "access_sof_maths": True,
            "access_sof_english": True,
            "subscription_plan": "test_full_access",
            "account_status": "active",
        },
        token=ADMIN_TOKEN,
    )

    patch(
        f"/api/admin/limits/{child_id}",
        {
            "daily_token_limit": 500000,
            "monthly_token_limit": 10000000,
        },
        token=ADMIN_TOKEN,
    )

    return {
        "parent": parent,
        "child": child,
    }


def get_syllabus():
    data = get("/api/syllabus")
    return data.get("syllabus") or data


def get_subject_chapter_plan(mode):
    syllabus = get_syllabus()

    grade_data = syllabus.get(DEFAULT_GRADE)
    if not grade_data:
        raise RuntimeError(f"Syllabus missing grade: {DEFAULT_GRADE}")

    mode_data = grade_data.get(mode)
    if not mode_data:
        raise RuntimeError(f"Syllabus missing mode: {mode}")

    plan = []

    for subject, chapters in mode_data.items():
        selected_chapters = chapters

        if SIM_MAX_CHAPTERS_PER_SUBJECT > 0:
            selected_chapters = chapters[:SIM_MAX_CHAPTERS_PER_SUBJECT]

        for chapter in selected_chapters:
            plan.append(
                {
                    "grade": DEFAULT_GRADE,
                    "mode": mode,
                    "subject": subject,
                    "chapter": chapter,
                }
            )

    return plan


def generate_lesson(item, step_title):
    return post(
        "/api/lesson/generate",
        {
            "username": STUDENT_USERNAME,
            "grade": item["grade"],
            "mode": item["mode"],
            "subject": item["subject"],
            "chapter": item["chapter"],
            "step_title": step_title,
            "teacher_persona": "friendly",
        },
        token=STUDENT_TOKEN,
    )


def save_progress(item, step_index, completed, lesson):
    return post(
        "/api/progress/save",
        {
            "username": STUDENT_USERNAME,
            "grade": item["grade"],
            "mode": item["mode"],
            "subject": item["subject"],
            "chapter": item["chapter"],
            "current_step_index": step_index,
            "completed": completed,
            "last_lesson": lesson,
            "step_lessons": {
                str(step_index): lesson,
            },
        },
        token=STUDENT_TOKEN,
    )


def log_activity(activity_type):
    return post(
        "/api/profile/activity",
        {
            "username": STUDENT_USERNAME,
            "activity_type": activity_type,
        },
        token=STUDENT_TOKEN,
    )


def ask_doubt(item, doubt_number):
    question = (
        f"Doubt {doubt_number}: Please explain an important concept from "
        f"{item['chapter']} in {item['subject']} with one example."
    )

    return post(
        "/api/doubt/answer",
        {
            "username": STUDENT_USERNAME,
            "grade": item["grade"],
            "mode": item["mode"],
            "subject": item["subject"],
            "chapter": item["chapter"],
            "question": question,
        },
        token=STUDENT_TOKEN,
    )


def evaluate_answer(item):
    return post(
        "/api/evaluation/evaluate",
        {
            "username": STUDENT_USERNAME,
            "question": f"What did you learn in {item['chapter']}?",
            "student_answer": (
                f"I learned the main concepts of {item['chapter']} "
                f"in {item['subject']}."
            ),
            "ideal_context": (
                f"{item['chapter']} contains important concepts for "
                f"{item['grade']} {item['subject']}."
            ),
        },
        token=STUDENT_TOKEN,
    )


def generate_practice_questions(item, lesson):
    return post(
        "/api/evaluation/practice-questions",
        {
            "username": STUDENT_USERNAME,
            "question": item["chapter"],
            "student_answer": "Practice answer placeholder.",
            "ideal_context": lesson or f"Lesson context for {item['chapter']}.",
        },
        token=STUDENT_TOKEN,
    )


def generate_cbse_mock_test(item):
    return post(
        "/api/mock-test/generate",
        {
            "username": STUDENT_USERNAME,
            "grade": item["grade"],
            "mode": "CBSE",
            "subject": item["subject"],
            "chapter": item["chapter"],
            "mock_type": "CBSE Mock Test",
            "exam_type": "Class Test",
            "question_count": 5,
            "difficulty": "medium",
        },
        token=STUDENT_TOKEN,
    )


def generate_sof_mock_test(item):
    return post(
        "/api/mock-test/generate",
        {
            "username": STUDENT_USERNAME,
            "grade": item["grade"],
            "mode": "SOF",
            "subject": item["subject"],
            "chapter": item["chapter"],
            "mock_type": "SOF Olympiad Mock Test",
            "exam_type": "Olympiad",
            "question_count": 5,
            "difficulty": "medium",
        },
        token=STUDENT_TOKEN,
    )


def save_test_history(
    item,
    mock_type,
    exam_type,
    final_score,
    max_score,
    submitted_at,
):
    percentage = round((final_score / max_score) * 100, 2)

    return post(
        "/api/analytics/test-history",
        {
            "username": STUDENT_USERNAME,
            "grade": item["grade"],
            "mode": item["mode"],
            "subject": item["subject"],
            "chapter": item["chapter"],
            "mockType": mock_type,
            "examType": exam_type,
            "difficulty": "medium",
            "rawScore": final_score,
            "finalScore": final_score,
            "maxScore": max_score,
            "wrongCount": int(max_score - final_score),
            "penalty": 0,
            "percentage": percentage,
            "submittedAt": submitted_at.isoformat(),
        },
        token=STUDENT_TOKEN,
    )


def score_for_day(day_index, max_score):
    """
    Create varied but realistic scores across the month.

    Early days are weaker, later days improve.
    """
    pattern = [0.45, 0.55, 0.65, 0.75, 0.85, 0.9]
    ratio = pattern[day_index % len(pattern)]
    score = round(max_score * ratio)

    return max(1, min(score, max_score))


def run_item_for_day(item, day_index, scenario):
    simulated_date = datetime.now(timezone.utc) - timedelta(
        days=(SIM_DAYS - day_index - 1)
    )

    print("\n" + "=" * 80)
    print(
        f"Day {day_index + 1}/{SIM_DAYS}: "
        f"{item['mode']} - {item['subject']} - {item['chapter']}"
    )

    step_title = "Concept introduction"

    lesson_response = generate_lesson(item, step_title)
    lesson = lesson_response.get("lesson") or (
        f"Generated lesson for {item['chapter']}"
    )

    save_progress(
        item=item,
        step_index=day_index % 5,
        completed=(day_index % 5 == 4),
        lesson=lesson,
    )

    log_activity("lesson_completed")

    for doubt_number in range(1, DOUBTS_PER_CHAPTER + 1):
        ask_doubt(item, doubt_number)

    evaluate_answer(item)

    generate_practice_questions(item, lesson)
    log_activity("quiz_attempted")

    if scenario == "cbse":
        generate_cbse_mock_test(item)
        log_activity("mock_test_taken")

        save_test_history(
            item=item,
            mock_type="CBSE Mock Test",
            exam_type="Class Test",
            final_score=score_for_day(day_index, 5),
            max_score=5,
            submitted_at=simulated_date,
        )

    if scenario == "sof":
        generate_sof_mock_test(item)
        log_activity("mock_test_taken")

        save_test_history(
            item=item,
            mock_type="SOF Olympiad Mock Test",
            exam_type="Olympiad",
            final_score=score_for_day(day_index, 5),
            max_score=5,
            submitted_at=simulated_date,
        )


def run_monthly_scenario(scenario):
    if scenario == "cbse":
        plan = get_subject_chapter_plan("CBSE")
    elif scenario == "sof":
        plan = get_subject_chapter_plan("SOF")
    else:
        raise ValueError(f"Unsupported scenario: {scenario}")

    if not plan:
        raise RuntimeError(f"No syllabus plan found for scenario: {scenario}")

    print("\n" + "#" * 80)
    print(f"Starting {scenario.upper()} monthly family simulation")
    print(f"Parent:  {PARENT_USERNAME}")
    print(f"Student: {STUDENT_USERNAME}")
    print(f"Days:    {SIM_DAYS}")
    print(f"Items:   {len(plan)}")
    print("#" * 80)

    for day_index in range(SIM_DAYS):
        item = plan[day_index % len(plan)]
        run_item_for_day(item, day_index, scenario)


def get_final_snapshots():
    print("\n" + "=" * 80)
    print("Fetching final dashboard snapshots")

    profile = get(f"/api/profile/{STUDENT_USERNAME}", token=STUDENT_TOKEN)
    usage = get(
        f"/api/usage/summary?username={STUDENT_USERNAME}",
        token=STUDENT_TOKEN,
    )
    recommendations = get(
        f"/api/recommendations/{STUDENT_USERNAME}",
        token=STUDENT_TOKEN,
    )
    history = get(
        f"/api/analytics/test-history/{STUDENT_USERNAME}",
        token=STUDENT_TOKEN,
    )

    return {
        "profile": profile,
        "usage": usage,
        "recommendations": recommendations,
        "test_history": history,
    }


def run():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--scenario",
        choices=["cbse", "sof", "all"],
        default="all",
        help="Which monthly scenario to run.",
    )

    args = parser.parse_args()

    print("\nStarting family monthly journey simulation")
    print(f"Scenario: {args.scenario}")
    print(f"Parent:   {PARENT_USERNAME}")
    print(f"Student:  {STUDENT_USERNAME}")

    create_test_family_if_admin_token_available()

    if args.scenario in ["cbse", "all"]:
        run_monthly_scenario("cbse")

    if args.scenario in ["sof", "all"]:
        run_monthly_scenario("sof")

    snapshots = get_final_snapshots()

    print("\nFinal Simulation Summary")
    pprint(snapshots)

    print("\nFamily monthly simulation completed successfully")


if __name__ == "__main__":
    run()