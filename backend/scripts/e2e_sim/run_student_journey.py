#!/usr/bin/env python3
"""
End-to-end student journey simulation.

For each test student (one per Grade 5-12, created by create_test_students.py),
walks every (subject, chapter) that has real lesson_cache content for that
grade and, through the real HTTP API (same routes the frontend calls):

  1. Launches the lesson ("Concept introduction" step)
  2. Asks an end-of-lesson follow-up doubt
  3. Asks a doubt via the Ask Doubt page
  4. Generates a Unit Test (single chapter, MCQ)

Once per (grade, subject), additionally:
  5. Generates a Mid Term test (multi-chapter MCQ)
  6. Generates an Annual test (full-syllabus MCQ)
  7. Generates a written/subjective test and evaluates an answer against it

Every action is logged as one JSON line to results.jsonl, success/failure
classified, with enough detail (question text, response preview, status code,
error) to reconstruct what happened without re-running anything.

Resumable: on restart, already-logged (action, grade, subject, chapter)
combinations are skipped.

Run:
    ./venv/bin/python scripts/e2e_sim/run_student_journey.py [--grade "Grade 9"] [--limit-chapters N]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import os
import requests
from supabase import create_client

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from app.services.auth_service import admin_client, SUPABASE_URL  # noqa: E402

BASE_URL = "http://localhost:8000"
HERE = Path(__file__).resolve().parent
STUDENTS_PATH = HERE / "students.json"
RESULTS_PATH = HERE / "results.jsonl"

# Supabase access tokens expire (~1hr). A full sweep runs for hours, so tokens
# are refreshed proactively rather than obtained once at the start.
PASSWORD = "E2ESimTest#2026"  # must match create_test_students.py
TOKEN_MAX_AGE_SECONDS = 40 * 60
_anon_client = create_client(SUPABASE_URL, os.getenv("SUPABASE_ANON_KEY"))
_token_cache = {}  # grade -> (token, issued_at_epoch)


def get_token(student):
    grade = student["grade"]
    cached = _token_cache.get(grade)
    if cached and (time.time() - cached[1]) < TOKEN_MAX_AGE_SECONDS:
        return cached[0]
    auth_resp = _anon_client.auth.sign_in_with_password(
        {"email": student["email"], "password": PASSWORD}
    )
    token = auth_resp.session.access_token
    _token_cache[grade] = (token, time.time())
    return token

MID_TERM_MAX_CHAPTERS = 12
ANNUAL_MAX_CHAPTERS = 25
UNIT_TEST_COUNT = 8
MID_TERM_COUNT = 20
ANNUAL_COUNT = 30
WRITTEN_COUNT = 3


def fetch_all(qb, page=1000):
    rows, start = [], 0
    while True:
        r = qb().range(start, start + page - 1).execute()
        d = r.data or []
        rows.extend(d)
        if len(d) < page:
            break
        start += page
    return rows


def get_grade_syllabus():
    """{grade: {subject: [chapters...]}} built from lesson_cache -- the ground
    truth for 'has real content', same source used all session for auditing."""
    rows = fetch_all(lambda: admin_client.table("lesson_cache").select("grade,subject,chapter")
                      .eq("status", "active").eq("mode", "CBSE"))
    tree = defaultdict(lambda: defaultdict(set))
    for r in rows:
        tree[r["grade"]][r["subject"]].add(r["chapter"])
    return {g: {s: sorted(chs) for s, chs in subs.items()} for g, subs in tree.items()}


def load_students():
    return json.loads(STUDENTS_PATH.read_text(encoding="utf-8"))


def load_done_keys():
    """(action, grade, subject, chapter) tuples already logged -- for resumability."""
    done = set()
    if RESULTS_PATH.exists():
        with RESULTS_PATH.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                done.add((d.get("action"), d.get("grade"), d.get("subject"), d.get("chapter")))
    return done


def http(method, path, token, json_body=None, timeout=60):
    t0 = time.time()
    try:
        resp = requests.request(method, f"{BASE_URL}{path}", json=json_body,
                                 headers={"Authorization": f"Bearer {token}"}, timeout=timeout)
        elapsed = round(time.time() - t0, 2)
        try:
            data = resp.json()
        except Exception:
            data = {"_raw_text": resp.text[:500]}
        return {"status": resp.status_code, "elapsed": elapsed, "data": data, "error": None}
    except Exception as e:
        return {"status": None, "elapsed": round(time.time() - t0, 2), "data": None, "error": str(e)}


def record(fh, **kwargs):
    kwargs["ts"] = datetime.now(timezone.utc).isoformat()
    fh.write(json.dumps(kwargs, default=str) + "\n")
    fh.flush()


def run_lesson_and_doubts(fh, done, student, subject, chapter, step_title="Concept introduction"):
    token, grade, username = get_token(student), student["grade"], student["username"]
    key_lesson = ("lesson_generate", grade, subject, chapter)
    key_followup = ("lesson_followup_doubt", grade, subject, chapter)
    key_ask = ("ask_doubt_page", grade, subject, chapter)

    lesson_text = None
    if key_lesson not in done:
        body = {"username": username, "grade": grade, "board": "CBSE", "mode": "CBSE",
                 "subject": subject, "chapter": chapter, "step_title": step_title,
                 "teacher_persona": "friendly"}
        r = http("POST", "/api/lesson/generate", token, body)
        d = r["data"] if isinstance(r["data"], dict) else {}
        lesson_text = d.get("lesson")
        ok = r["status"] == 200 and d.get("success") and len((lesson_text or "")) > 50
        record(fh, action="lesson_generate", grade=grade, subject=subject, chapter=chapter,
               step_title=step_title, ok=ok, status=r["status"], elapsed=r["elapsed"], error=r["error"],
               source_type=d.get("source_type"), from_cache=d.get("from_cache"),
               message=d.get("message"), lesson_len=len(lesson_text or ""))
    else:
        ok = True  # assume prior success; re-fetch lesson text for the doubt calls below if needed

    if key_followup not in done or key_ask not in done:
        if lesson_text is None:
            # Need lesson text for the follow-up call; re-generate quickly (cache hit expected).
            body = {"username": username, "grade": grade, "board": "CBSE", "mode": "CBSE",
                     "subject": subject, "chapter": chapter, "step_title": step_title,
                     "teacher_persona": "friendly"}
            r = http("POST", "/api/lesson/generate", token, body)
            d = r["data"] if isinstance(r["data"], dict) else {}
            lesson_text = d.get("lesson")
            ok = r["status"] == 200 and d.get("success") and len((lesson_text or "")) > 50

        if not ok or not lesson_text:
            if key_followup not in done:
                record(fh, action="lesson_followup_doubt", grade=grade, subject=subject, chapter=chapter,
                       ok=False, status=None, elapsed=0, error="skipped: lesson generation failed",
                       source_type=None, question=None)
            if key_ask not in done:
                record(fh, action="ask_doubt_page", grade=grade, subject=subject, chapter=chapter,
                       ok=False, status=None, elapsed=0, error="skipped: lesson generation failed",
                       source_type=None, question=None)
            return

        if key_followup not in done:
            followup_q = f"Can you explain the most important idea in {chapter} with a simple example?"
            body = {"username": username, "grade": grade, "board": "CBSE", "mode": "CBSE",
                     "subject": subject, "chapter": chapter, "step_title": step_title,
                     "lesson": lesson_text, "question": followup_q}
            r2 = http("POST", "/api/lesson/follow-up", token, body)
            d2 = r2["data"] if isinstance(r2["data"], dict) else {}
            ok2 = r2["status"] == 200 and d2.get("success") and bool((d2.get("answer") or "").strip())
            record(fh, action="lesson_followup_doubt", grade=grade, subject=subject, chapter=chapter,
                   ok=ok2, status=r2["status"], elapsed=r2["elapsed"], error=r2["error"],
                   source_type=d2.get("source_type"), question=followup_q,
                   answer_preview=(d2.get("answer") or "")[:300])

        if key_ask not in done:
            ask_q = f"I am confused about {chapter} in {subject}. What is the key concept I should understand?"
            body = {"username": username, "grade": grade, "board": "CBSE", "mode": "CBSE",
                     "subject": subject, "chapter": chapter, "question": ask_q}
            r3 = http("POST", "/api/doubt/answer", token, body)
            d3 = r3["data"] if isinstance(r3["data"], dict) else {}
            ok3 = r3["status"] == 200 and d3.get("success") and bool((d3.get("answer") or "").strip())
            record(fh, action="ask_doubt_page", grade=grade, subject=subject, chapter=chapter,
                   ok=ok3, status=r3["status"], elapsed=r3["elapsed"], error=r3["error"],
                   source_type=d3.get("source_type"), question=ask_q,
                   answer_preview=(d3.get("answer") or "")[:300])


def validate_mcq_questions(questions):
    if not questions:
        return False, "no questions returned"
    for q in questions:
        opts = q.get("options") or {}
        if not all(k in opts for k in ["A", "B", "C", "D"]):
            return False, f"question missing options A-D: {str(q.get('question',''))[:80]}"
        if q.get("answer") not in ("A", "B", "C", "D"):
            return False, f"invalid answer key {q.get('answer')!r} for: {str(q.get('question',''))[:80]}"
        if not str(q.get("explanation") or "").strip():
            return False, f"empty explanation for: {str(q.get('question',''))[:80]}"
    return True, None


def run_mock_test_mcq(fh, done, student, subject, chapters, exam_type, question_count, chapter_key):
    action = f"mock_test_mcq_{exam_type.lower().replace(' ', '_')}"
    key = (action, student["grade"], subject, chapter_key)
    if key in done:
        return
    token, grade, username = get_token(student), student["grade"], student["username"]
    body = {"username": username, "grade": grade, "board": "CBSE", "mode": "CBSE", "subject": subject,
             "mock_type": "CBSE Mock Test", "exam_type": exam_type, "question_count": question_count,
             "difficulty": "Medium", "question_format": "mcq"}
    if len(chapters) == 1:
        body["chapter"] = chapters[0]
    else:
        body["chapters"] = chapters
    r = http("POST", "/api/mock-test/generate", token, body, timeout=90)
    d = r["data"] if isinstance(r["data"], dict) else {}
    questions = d.get("questions") or []
    if r["status"] == 200 and d.get("success"):
        struct_ok, struct_err = validate_mcq_questions(questions)
    else:
        struct_ok, struct_err = False, d.get("message")
    ok = r["status"] == 200 and d.get("success") and struct_ok
    record(fh, action=action, grade=grade, subject=subject, chapter=chapter_key,
           ok=ok, status=r["status"], elapsed=r["elapsed"], error=r["error"] or struct_err,
           requested_count=question_count, returned_count=len(questions), num_chapters=len(chapters),
           sample_question=(str(questions[0].get("question"))[:200] if questions else None))


def run_mock_test_written(fh, done, student, subject, chapter):
    token, grade, username = get_token(student), student["grade"], student["username"]
    key_gen = ("mock_test_written_generate", grade, subject, chapter)
    key_eval = ("mock_test_written_evaluate", grade, subject, chapter)
    if key_gen in done and key_eval in done:
        return

    body = {"username": username, "grade": grade, "board": "CBSE", "mode": "CBSE", "subject": subject,
             "chapter": chapter, "mock_type": "CBSE Mock Test", "exam_type": "Unit Test",
             "question_count": WRITTEN_COUNT, "difficulty": "Medium", "question_format": "written"}
    r = http("POST", "/api/mock-test/generate", token, body, timeout=120)
    d = r["data"] if isinstance(r["data"], dict) else {}
    questions = d.get("questions") or []
    gen_ok = r["status"] == 200 and d.get("success") and len(questions) > 0
    if key_gen not in done:
        record(fh, action="mock_test_written_generate", grade=grade, subject=subject, chapter=chapter,
               ok=gen_ok, status=r["status"], elapsed=r["elapsed"], error=r["error"] or d.get("message"),
               requested_count=WRITTEN_COUNT, returned_count=len(questions))

    if key_eval in done:
        return
    if not gen_ok:
        record(fh, action="mock_test_written_evaluate", grade=grade, subject=subject, chapter=chapter,
               ok=False, status=None, elapsed=0, error="skipped: written question generation failed")
        return

    q = questions[0]
    keywords = q.get("expected_keywords") or []
    student_answer = ", ".join(keywords) if keywords else (q.get("answer") or "This is my answer.")
    eval_body = {"username": username, "grade": grade, "mode": "CBSE", "subject": subject, "chapter": chapter,
                  "question": q.get("question", ""), "student_answer": student_answer,
                  "ideal_context": q.get("explanation") or f"{chapter} key concepts",
                  "step_title": "Concept introduction", "question_type": "descriptive",
                  "expected_keywords": keywords, "correct_answer": q.get("answer") or ""}
    r2 = http("POST", "/api/evaluation/evaluate", token, eval_body)
    d2 = r2["data"] if isinstance(r2["data"], dict) else {}
    ok2 = r2["status"] == 200 and bool(d2.get("success"))
    record(fh, action="mock_test_written_evaluate", grade=grade, subject=subject, chapter=chapter,
           ok=ok2, status=r2["status"], elapsed=r2["elapsed"], error=r2["error"] or (None if ok2 else d2.get("message")),
           score=d2.get("score"), passed=d2.get("passed"), had_keywords=bool(keywords))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--grade", default=None, help="Only run this grade, e.g. 'Grade 9'")
    parser.add_argument("--limit-chapters", type=int, default=0, help="Cap chapters per subject (0 = no cap)")
    args = parser.parse_args()

    students = {s["grade"]: s for s in load_students()}
    syllabus = get_grade_syllabus()
    done = load_done_keys()

    grades = [args.grade] if args.grade else sorted(students, key=lambda g: int(g.split()[-1]))

    with RESULTS_PATH.open("a", encoding="utf-8") as fh:
        for grade in grades:
            student = students.get(grade)
            if not student:
                print(f"No test student for {grade}, skipping")
                continue
            subjects = syllabus.get(grade, {})
            print(f"\n{'='*80}\n{grade} ({student['username']}): {len(subjects)} subjects\n{'='*80}")

            for subject, chapters in subjects.items():
                chs = chapters[: args.limit_chapters] if args.limit_chapters else chapters
                print(f"  {subject}: {len(chs)} chapters")

                for chapter in chs:
                    run_lesson_and_doubts(fh, done, student, subject, chapter)
                    run_mock_test_mcq(fh, done, student, subject, [chapter], "Unit Test",
                                       UNIT_TEST_COUNT, chapter_key=chapter)

                mid_chapters = chapters[: MID_TERM_MAX_CHAPTERS] if len(chapters) > 1 else chapters
                run_mock_test_mcq(fh, done, student, subject, mid_chapters, "Mid Term",
                                   MID_TERM_COUNT, chapter_key="__MID_TERM__")

                annual_chapters = chapters[:ANNUAL_MAX_CHAPTERS]
                run_mock_test_mcq(fh, done, student, subject, annual_chapters, "Annual",
                                   ANNUAL_COUNT, chapter_key="__ANNUAL__")

                run_mock_test_written(fh, done, student, subject, chapters[0])

    print(f"\nDone. Results appended to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
