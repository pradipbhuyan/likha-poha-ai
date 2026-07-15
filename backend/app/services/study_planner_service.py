"""
study_planner_service.py — AI Study Planner business logic
===========================================================
Phases 1, 2, 3:
  Phase 1: Live exam countdown + "study today" recommendation
  Phase 2: LLM-generated week-by-week plan, saved to DB, adaptive after each test
  Phase 3: Daily task checklist with done/skipped tracking
"""

from __future__ import annotations

import json
import math
import re
from datetime import date, timedelta
from typing import Optional

from fastapi import HTTPException
from app.services.logger_service import get_logger

_log = get_logger("study_planner_service")

EXAM_DATES = {
    "jee_main":  date(2027, 1, 15),
    "neet_ug":   date(2027, 5, 4),
    "cuet_ug":   date(2027, 5, 20),
    "sat":       date(2027, 3, 8),
    "ielts":     date(2027, 2, 15),
    "toefl_ibt": date(2027, 2, 22),
}

EXAM_LABELS = {
    "jee_main":  "JEE Main",
    "neet_ug":   "NEET UG",
    "cuet_ug":   "CUET UG",
    "sat":       "SAT",
    "ielts":     "IELTS",
    "toefl_ibt": "TOEFL iBT",
}

EXAM_CHAPTERS = {
    "jee_main": {
        "Physics": ["Kinematics", "Laws of Motion", "Work Energy Power", "Rotational Motion",
                    "Gravitation", "Thermodynamics", "Waves & Oscillations", "Electrostatics",
                    "Current Electricity", "Magnetism", "Electromagnetic Induction",
                    "Optics", "Modern Physics"],
        "Chemistry": ["Chemical Bonding", "States of Matter", "Thermodynamics", "Equilibrium",
                      "Electrochemistry", "Chemical Kinetics", "Coordination Compounds",
                      "Haloalkanes", "Alcohols & Phenols", "Aldehydes & Ketones",
                      "Carboxylic Acids", "Amines", "p-Block Elements", "d-Block Elements"],
        "Mathematics": ["Algebra & Complex Numbers", "Matrices & Determinants",
                        "Permutations & Combinations", "Binomial Theorem",
                        "Sequences & Series", "Coordinate Geometry", "Calculus",
                        "Differential Equations", "Vectors & 3D Geometry", "Probability & Statistics"],
    },
    "neet_ug": {
        "Physics": ["Kinematics", "Laws of Motion", "Work Energy Power", "Thermal Properties",
                    "Thermodynamics", "Oscillations", "Electrostatics", "Current Electricity",
                    "Magnetism", "Optics", "Modern Physics"],
        "Chemistry": ["Chemical Bonding", "States of Matter", "Thermodynamics", "Equilibrium",
                      "Redox & Electrochemistry", "Chemical Kinetics", "Coordination Compounds",
                      "Biomolecules", "Polymers", "p-Block Elements", "d-Block Elements"],
        "Biology": ["Cell Structure & Function", "Genetics & Molecular Biology", "Human Physiology",
                    "Plant Physiology", "Reproduction", "Ecology & Environment",
                    "Biotechnology", "Evolution", "Diversity in Living World"],
    },
    "cuet_ug": {
        "English": ["Reading Comprehension", "Grammar & Usage", "Vocabulary", "Writing Skills"],
        "General Test": ["Quantitative Reasoning", "Logical Reasoning", "General Knowledge", "Data Interpretation"],
    },
    "sat": {
        "Reading & Writing": ["Reading Comprehension", "Vocabulary in Context", "Standard English Conventions",
                              "Expression of Ideas", "Rhetorical Synthesis", "Text Structure and Purpose"],
        "Mathematics": ["Algebra", "Advanced Mathematics", "Problem Solving & Data Analysis", "Geometry & Trigonometry"],
    },
    "ielts": {
        "Listening": ["Everyday Conversation", "Academic Discussion", "Lecture Comprehension", "MCQ & Form Completion"],
        "Reading": ["Matching Headings", "True/False/Not Given", "Sentence Completion", "Multiple Choice"],
        "Vocabulary & Grammar": ["Academic Vocabulary", "Grammar in Context", "Paraphrasing"],
    },
    "toefl_ibt": {
        "Reading": ["Reading Comprehension", "Vocabulary in Context", "Inference Questions"],
        "Listening": ["Lecture Comprehension", "Campus Conversations", "Purpose and Attitude"],
        "Integrated Skills": ["Integrated Writing Task", "Academic Discussion Writing"],
    },
}


def _get_db():
    from app.services.supabase_grade_1112_client import grade_1112_client  # noqa: PLC0415
    if grade_1112_client is None:
        raise HTTPException(503, "Study Planner database not configured.")
    return grade_1112_client


def _weeks_remaining(exam_type: str) -> int:
    exam_date = EXAM_DATES.get(exam_type)
    if not exam_date:
        return 30
    delta = (exam_date - date.today()).days
    return max(1, math.ceil(delta / 7))


def _get_weak_topics(user_id: str, exam_type: str) -> list[str]:
    db = _get_db()
    try:
        result = (
            db.table("exam_prep_simulated_tests")
            .select("weak_topics")
            .eq("user_id", user_id)
            .eq("exam_type", exam_type)
            .eq("status", "submitted")
            .order("submitted_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = result.data or []
        if rows and rows[0].get("weak_topics"):
            return rows[0]["weak_topics"]
    except Exception as exc:
        _log.warning("study_planner.weak_topics.fetch", error=str(exc))
    return []


# ── Phase 1 ────────────────────────────────────────────────────────────────────

def get_countdown_info(exam_type: str) -> dict:
    exam_date = EXAM_DATES.get(exam_type)
    today = date.today()
    label = EXAM_LABELS.get(exam_type, exam_type)
    if exam_date:
        days_remaining = max(0, (exam_date - today).days)
        weeks_remaining = max(0, math.ceil(days_remaining / 7))
        exam_date_str = exam_date.strftime("%B %d, %Y")
    else:
        days_remaining = 180
        weeks_remaining = 26
        exam_date_str = "TBD"
    return {
        "exam_type": exam_type,
        "exam_label": label,
        "exam_date": exam_date_str,
        "days_remaining": days_remaining,
        "weeks_remaining": weeks_remaining,
    }


# ── Phase 2 ────────────────────────────────────────────────────────────────────

def _build_llm_prompt(exam_type: str, exam_label: str, weeks: int, daily_hours: int, weak_topics: list[str]) -> tuple[str, str]:
    chapters = EXAM_CHAPTERS.get(exam_type, {})
    subjects_str = json.dumps(chapters, indent=2)
    weak_str = ", ".join(weak_topics) if weak_topics else "None identified yet"
    exam_dt = EXAM_DATES.get(exam_type, date.today() + timedelta(weeks=weeks))
    phase1 = max(1, weeks - 4) if weeks >= 8 else max(1, weeks - 2)
    phase2 = max(phase1, weeks - 2) if weeks >= 8 else weeks - 1
    phase3 = weeks - 1 if weeks >= 4 else weeks

    system_prompt = (
        f"You are an expert {exam_label} study planner for Indian Grade 11/12 students.\n"
        f"Rules:\n"
        f"1. Cover ALL subjects and chapters listed.\n"
        f"2. Prioritise weak topics in first {max(1, phase1 // 3)} weeks.\n"
        f"3. Alternate subjects daily.\n"
        f"4. Phase 1 (Weeks 1-{phase1}): Learning + weak topics.\n"
        f"5. Phase 2 (Weeks {phase1+1}-{phase2}): Full revision.\n"
        f"6. Phase 3 (Week {phase3}): Mock tests only (task_type='mock_test').\n"
        f"7. Final week: Light revision (task_type='light_revision').\n"
        f"8. Each week = 7 days. Generate tasks for ALL 7 days.\n"
        f"9. Daily time: {daily_hours}h = {daily_hours * 60} min. Split into tasks.\n"
        f"10. task_type: revise | practice | formula_review | mock_test | light_revision\n"
        f"OUTPUT: Return ONLY a valid JSON array. No markdown, no text before or after.\n"
        f"Schema: [{{\"week\":1,\"theme\":\"...\",\"tasks\":[{{\"day\":1,\"subject\":\"...\","
        f"\"topic\":\"...\",\"task_type\":\"revise\",\"description\":\"...\",\"duration_minutes\":60}}]}}]"
    )
    user_prompt = (
        f"Exam: {exam_label}\nExam Date: {exam_dt.strftime('%B %d, %Y')}\n"
        f"Weeks: {weeks}\nDaily Hours: {daily_hours}\nWeak Topics: {weak_str}\n\n"
        f"Chapters:\n{subjects_str}\n\n"
        f"Generate ALL {weeks} weeks. Return JSON array only."
    )
    return system_prompt, user_prompt


def _fallback_weeks(exam_type: str, start_week: int, end_week: int, daily_hours: int) -> list[dict]:
    """Generate simple fallback weeks when LLM fails."""
    chapters = EXAM_CHAPTERS.get(exam_type, {})
    subjects = list(chapters.keys()) or ["General"]
    result = []
    for w in range(start_week, end_week + 1):
        tasks = []
        for d in range(1, 8):
            subj = subjects[(w + d) % len(subjects)]
            ch_list = chapters.get(subj, ["Self Study"])
            topic = ch_list[d % len(ch_list)]
            tasks.append({
                "day": d,
                "subject": subj,
                "topic": topic,
                "task_type": "revise",
                "description": f"Study {topic} ({subj}). Read NCERT notes, solve examples.",
                "duration_minutes": (daily_hours * 60) // 2,
            })
        result.append({"week": w, "theme": f"Week {w} — Study Plan", "tasks": tasks})
    return result


def generate_plan(user_id: str, exam_type: str, daily_hours: int = 4) -> dict:
    """Generate (or regenerate) a study plan via LLM. Save to DB. Return full plan."""
    db = _get_db()
    from app.services.openai_service import ask_llm  # noqa: PLC0415

    weeks = _weeks_remaining(exam_type)
    weak_topics = _get_weak_topics(user_id, exam_type)
    exam_label = EXAM_LABELS.get(exam_type, exam_type)
    exam_dt = EXAM_DATES.get(exam_type)

    system_prompt, _ = _build_llm_prompt(exam_type, exam_label, weeks, daily_hours, weak_topics)

    # Generate in batches of 6 weeks to avoid LLM timeouts
    BATCH = 6
    all_weeks: list[dict] = []
    batch_start = 1
    remaining = weeks

    while remaining > 0:
        batch_size = min(BATCH, remaining)
        batch_end = batch_start + batch_size - 1
        _, batch_user = _build_llm_prompt(exam_type, exam_label, weeks, daily_hours, weak_topics)
        batch_user = (
            f"Generate ONLY weeks {batch_start} to {batch_end} ({batch_size} weeks).\n"
            + batch_user
        )
        try:
            raw = ask_llm(
                system_prompt=system_prompt,
                user_prompt=batch_user,
                username=user_id,
                feature="study_planner",
            )
            raw = raw.strip()
            if "```" in raw:
                parts = raw.split("```")
                raw = parts[1] if len(parts) > 1 else raw
                if raw.startswith("json"):
                    raw = raw[4:]
            raw = raw.strip()
            start = raw.find("[")
            end = raw.rfind("]")
            if start != -1 and end > start:
                raw = raw[start: end + 1]
            raw = re.sub(r",\s*([}\]])", r"\1", raw)
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                all_weeks.extend(parsed)
            else:
                all_weeks.extend(_fallback_weeks(exam_type, batch_start, batch_end, daily_hours))
        except Exception as exc:
            _log.warning("study_planner.llm_batch", start=batch_start, error=str(exc))
            all_weeks.extend(_fallback_weeks(exam_type, batch_start, batch_end, daily_hours))
        batch_start += batch_size
        remaining -= batch_size

    # ── Delete old plan + tasks ────────────────────────────────────────────────
    try:
        old = db.table("study_plans").select("id").eq("user_id", user_id).eq("exam_type", exam_type).execute()
        for row in (old.data or []):
            db.table("study_plan_tasks").delete().eq("plan_id", row["id"]).execute()
            db.table("study_plans").delete().eq("id", row["id"]).execute()
    except Exception as exc:
        _log.warning("study_planner.delete_old", error=str(exc))

    # ── Save new plan ──────────────────────────────────────────────────────────
    plan_row = {
        "user_id": user_id,
        "exam_type": exam_type,
        "exam_date": exam_dt.isoformat() if exam_dt else None,
        "weeks_remaining": weeks,
        "daily_hours": daily_hours,
        "weak_topics": weak_topics,
        "plan_json": all_weeks,
        "version": 1,
    }
    try:
        result = db.table("study_plans").insert(plan_row).execute()
        plan_id = result.data[0]["id"] if result.data else None
    except Exception as exc:
        _log.warning("study_planner.save_plan", error=str(exc))
        plan_id = None

    # ── Save daily tasks ───────────────────────────────────────────────────────
    if plan_id:
        today = date.today()
        # Week 1 starts today; each week is 7 days forward
        task_rows = []
        for week_data in all_weeks:
            w = week_data.get("week", 1)
            week_offset = (w - 1) * 7  # days from today to start of this week
            for task in week_data.get("tasks", []):
                day = task.get("day", 1)
                task_date = today + timedelta(days=week_offset + day - 1)
                task_rows.append({
                    "user_id": user_id,
                    "exam_type": exam_type,
                    "plan_id": plan_id,
                    "week_number": w,
                    "task_date": task_date.isoformat(),
                    "task_type": task.get("task_type", "revise"),
                    "subject": task.get("subject", ""),
                    "topic": task.get("topic", ""),
                    "description": task.get("description", ""),
                    "duration_minutes": task.get("duration_minutes", 60),
                    "status": "pending",
                })
        # Insert in batches of 100
        CHUNK = 100
        for i in range(0, len(task_rows), CHUNK):
            try:
                db.table("study_plan_tasks").insert(task_rows[i: i + CHUNK]).execute()
            except Exception as exc:
                _log.warning("study_planner.save_tasks", chunk=i, error=str(exc))

    return get_plan(user_id, exam_type)


# ── Phase 3 ────────────────────────────────────────────────────────────────────

def get_plan(user_id: str, exam_type: str) -> dict:
    """
    Return the full plan for a user × exam including:
    - countdown info (Phase 1)
    - weekly plan (Phase 2)
    - today's tasks (Phase 3)
    - all tasks grouped by week (Phase 3)
    """
    db = _get_db()
    countdown = get_countdown_info(exam_type)

    # Fetch plan
    plan_row = None
    try:
        result = (
            db.table("study_plans")
            .select("*")
            .eq("user_id", user_id)
            .eq("exam_type", exam_type)
            .order("generated_at", desc=True)
            .limit(1)
            .execute()
        )
        if result.data:
            plan_row = result.data[0]
    except Exception as exc:
        _log.warning("study_planner.get_plan", error=str(exc))

    if not plan_row:
        return {
            "has_plan": False,
            "countdown": countdown,
            "plan_id": None,
            "daily_hours": 4,
            "weak_topics": _get_weak_topics(user_id, exam_type),
            "today_tasks": [],
            "weeks": [],
        }

    plan_id = plan_row["id"]
    daily_hours = plan_row.get("daily_hours", 4)
    weak_topics = plan_row.get("weak_topics") or []

    # Fetch all tasks
    today_str = date.today().isoformat()
    today_tasks = []
    all_tasks = []
    try:
        t_result = (
            db.table("study_plan_tasks")
            .select("*")
            .eq("plan_id", plan_id)
            .order("task_date")
            .execute()
        )
        all_tasks = t_result.data or []
        today_tasks = [t for t in all_tasks if t.get("task_date") == today_str]
    except Exception as exc:
        _log.warning("study_planner.get_tasks", error=str(exc))

    # Group tasks by week
    weeks_map: dict[int, dict] = {}
    plan_json = plan_row.get("plan_json") or []
    for week_data in plan_json:
        w = week_data.get("week", 1)
        weeks_map[w] = {"week": w, "theme": week_data.get("theme", f"Week {w}"), "tasks": []}
    for task in all_tasks:
        w = task.get("week_number", 1)
        if w not in weeks_map:
            weeks_map[w] = {"week": w, "theme": f"Week {w}", "tasks": []}
        weeks_map[w]["tasks"].append(task)

    # Completion stats
    total_tasks = len(all_tasks)
    done_tasks = sum(1 for t in all_tasks if t.get("status") == "done")
    completion_pct = round(done_tasks / total_tasks * 100) if total_tasks > 0 else 0

    today_done = sum(1 for t in today_tasks if t.get("status") == "done")
    today_total = len(today_tasks)

    return {
        "has_plan": True,
        "plan_id": plan_id,
        "daily_hours": daily_hours,
        "weak_topics": weak_topics,
        "generated_at": plan_row.get("generated_at", ""),
        "countdown": countdown,
        "today_tasks": today_tasks,
        "today_done": today_done,
        "today_total": today_total,
        "total_tasks": total_tasks,
        "done_tasks": done_tasks,
        "completion_pct": completion_pct,
        "weeks": sorted(weeks_map.values(), key=lambda x: x["week"]),
    }


def update_task_status(task_id: str, user_id: str, status: str) -> dict:
    """Mark a task as done or skipped. Only the task owner can update."""
    if status not in ("done", "skipped", "pending"):
        raise HTTPException(400, "status must be 'done', 'skipped', or 'pending'")
    db = _get_db()
    from datetime import datetime, timezone  # noqa: PLC0415
    try:
        result = (
            db.table("study_plan_tasks")
            .update({"status": status, "updated_at": datetime.now(timezone.utc).isoformat()})
            .eq("id", task_id)
            .eq("user_id", user_id)
            .execute()
        )
        if not result.data:
            raise HTTPException(404, "Task not found or not owned by user")
        return result.data[0]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, "Failed to update task") from exc


def run_migration(user_id: str) -> dict:
    """Create study_plans and study_plan_tasks tables if they don't exist."""
    db = _get_db()
    sql = """
CREATE TABLE IF NOT EXISTS study_plans (
  id                uuid    DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id           uuid    NOT NULL,
  exam_type         text    NOT NULL,
  exam_date         date,
  weeks_remaining   int     NOT NULL DEFAULT 0,
  daily_hours       int     NOT NULL DEFAULT 4,
  weak_topics       text[]  DEFAULT '{}',
  plan_json         jsonb   DEFAULT '[]'::jsonb,
  version           int     DEFAULT 1,
  generated_at      timestamptz DEFAULT now(),
  created_at        timestamptz DEFAULT now()
);
CREATE TABLE IF NOT EXISTS study_plan_tasks (
  id               uuid    DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id          uuid    NOT NULL,
  exam_type        text    NOT NULL,
  plan_id          uuid    REFERENCES study_plans(id) ON DELETE CASCADE,
  week_number      int     NOT NULL DEFAULT 1,
  task_date        date,
  task_type        text    NOT NULL DEFAULT 'revise',
  subject          text    NOT NULL,
  topic            text    NOT NULL,
  description      text    DEFAULT '',
  duration_minutes int     DEFAULT 60,
  status           text    DEFAULT 'pending',
  created_at       timestamptz DEFAULT now(),
  updated_at       timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_study_plans_user_exam ON study_plans(user_id, exam_type);
CREATE INDEX IF NOT EXISTS idx_study_plan_tasks_user_exam_date ON study_plan_tasks(user_id, exam_type, task_date);
"""
    try:
        db.rpc("exec_sql", {"sql": sql}).execute()
        return {"success": True, "message": "Study Planner tables ready."}
    except Exception:
        # Try a simple select to verify tables exist
        try:
            db.table("study_plans").select("id").limit(1).execute()
            db.table("study_plan_tasks").select("id").limit(1).execute()
            return {"success": True, "message": "Tables already exist."}
        except Exception as exc:
            return {
                "success": False,
                "message": f"Run the SQL migration manually: {str(exc)[:200]}",
            }
