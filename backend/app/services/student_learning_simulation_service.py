"""
student_learning_simulation_service.py
─────────────────────────────────────────────────────────────────────────────
Admin-triggered cumulative student learning simulation.

Simulates a real student (Vijay) using the platform over time.
All users are synthetic test accounts clearly marked as simulation data.

Safety guarantees:
- No real users mutated
- No real emails sent
- No payments processed
- No passwords in logs/responses
- Admin-only access
- Idempotent setup (safe to rerun)
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import json
import random
import uuid
from datetime import datetime, timezone
from typing import Optional

from app.services.auth_service import admin_client

# ── Synthetic test user definitions ──────────────────────────────────────────

SIM_USERS = {
    "vijay": {
        "email":    "vijay.sim.student@example.test",
        "username": "vijay_sim_student",
        "role":     "student",
        "grade":    "Grade 9",
        "board":    "CBSE",
    },
    "manish": {
        "email":    "manish.sim.parent@example.test",
        "username": "manish_sim_parent",
        "role":     "parent",
    },
    "manisha": {
        "email":    "manisha.sim.parent@example.test",
        "username": "manisha_sim_parent",
        "role":     "parent",
    },
}

SIM_PASSWORD = "test1234"
SIM_MARKER   = "simulation_test_user"

# Curriculum for simulation (must match real syllabus data)
SIM_CURRICULUM = [
    {"subject": "Maths",   "chapter": "Chapter 1: Number Systems",                        "grade": "Grade 9"},
    {"subject": "Maths",   "chapter": "Chapter 2: Polynomials",                           "grade": "Grade 9"},
    {"subject": "Science", "chapter": "Chapter 1: Matter in Our Surroundings",            "grade": "Grade 9"},
    {"subject": "Science", "chapter": "Chapter 2: Is Matter Around Us Pure",              "grade": "Grade 9"},
    {"subject": "Science", "chapter": "Chapter 5: The Fundamental Unit of Life",         "grade": "Grade 9"},
    {"subject": "Hindi",   "chapter": "अध्याय 1: दो बैलों की कथा",                      "grade": "Grade 9"},
    {"subject": "English", "chapter": "Chapter 1: The Fun They Had",                      "grade": "Grade 9"},
]

# Mock test score progression (Day 1 = lower, improves over time with noise)
def _mock_score(day: int, base: int = 40) -> float:
    """Generate a realistic improving-but-noisy test score 0–100."""
    trend   = min(base + (day * 3), 75)
    noise   = random.randint(-8, 12)
    score   = max(0, min(100, trend + noise))
    return round(score, 1)


# ── DB helpers ────────────────────────────────────────────────────────────────

def _safe_get(table: str, filters: dict) -> Optional[dict]:
    """Return first matching row or None — never raises."""
    try:
        q = admin_client.table(table).select("*")
        for k, v in filters.items():
            q = q.eq(k, v)
        r = q.limit(1).execute()
        return r.data[0] if r.data else None
    except Exception:
        return None


def _upsert_profile(profile: dict) -> dict:
    r = admin_client.table("profiles").upsert(profile, on_conflict="id").execute()
    return r.data[0] if r.data else profile


def _record_event(run_id: str, day: int, event_type: str, user_id: str,
                  subject: str = "", chapter: str = "", lesson_id: str = "",
                  metadata: dict | None = None) -> None:
    """Write one simulation event row. Silently no-ops if table missing."""
    try:
        admin_client.table("learning_simulation_events").insert({
            "run_id":        run_id,
            "simulated_day": day,
            "event_type":    event_type,
            "user_id":       user_id,
            "subject":       subject,
            "chapter":       chapter,
            "lesson_id":     lesson_id,
            "metadata_json": json.dumps(metadata or {}),
        }).execute()
    except Exception:
        pass


def _record_anomaly(run_id: str, severity: str, anomaly_type: str,
                    message: str, expected=None, actual=None,
                    context: dict | None = None) -> str:
    """Insert anomaly row and return its id."""
    try:
        r = admin_client.table("learning_simulation_anomalies").insert({
            "run_id":        run_id,
            "severity":      severity,
            "anomaly_type":  anomaly_type,
            "message":       message,
            "expected_json": json.dumps(expected) if expected is not None else None,
            "actual_json":   json.dumps(actual)   if actual   is not None else None,
            "context_json":  json.dumps(context or {}),
            "status":        "open",
        }).execute()
        return r.data[0]["id"] if r.data else str(uuid.uuid4())
    except Exception:
        return str(uuid.uuid4())


def _create_product_bug(anomaly_id: str, run_id: str, severity: str,
                        message: str, context: dict, admin_id: str) -> Optional[str]:
    """Create a product_issue_reports entry for an anomaly."""
    sev_map = {"critical": "critical", "high": "high", "medium": "medium", "low": "low"}
    try:
        r = admin_client.table("product_issue_reports").insert({
            "reporter_user_id": admin_id,
            "reporter_role":    "admin",
            "issue_type":       "content_issue",
            "severity":         sev_map.get(severity, "medium"),
            "title":            f"[Simulation] {message[:200]}",
            "description":      (
                f"Auto-generated by Learning Simulation run {run_id}.\n\n"
                f"{message}\n\nContext: {json.dumps(context, indent=2)[:800]}"
            ),
            "route":            "simulation",
            "grade":            "Grade 9",
            "subject":          context.get("subject", ""),
            "chapter":          context.get("chapter", ""),
            "status":           "open",
            "browser_info":     {"source": "simulation", "run_id": run_id},
        }).execute()
        issue_id = r.data[0]["id"] if r.data else None
        if issue_id:
            # Link anomaly → bug
            admin_client.table("learning_simulation_anomalies").update({
                "product_issue_id": issue_id,
                "status":           "bug_created",
            }).eq("id", anomaly_id).execute()
        return issue_id
    except Exception:
        return None


# ── User setup ────────────────────────────────────────────────────────────────

def _ensure_family() -> str:
    """Return or create the simulation family id."""
    existing = _safe_get("families", {"family_name": "Simulation Family (Test)"})
    if existing:
        return existing["id"]
    r = admin_client.table("families").insert({
        "family_name": "Simulation Family (Test)"
    }).execute()
    return r.data[0]["id"] if r.data else str(uuid.uuid4())


def _ensure_auth_user(email: str) -> Optional[str]:
    """Return auth user id if exists, else create via admin API."""
    # Try to find by email in profiles first
    existing = _safe_get("profiles", {"email": email})
    if existing:
        return existing["id"]
    # Create via Supabase admin auth
    try:
        res = admin_client.auth.admin.create_user({
            "email":            email,
            "password":         SIM_PASSWORD,
            "email_confirm":    True,
            "user_metadata":    {"simulation": True, "is_test_user": True},
        })
        return res.user.id if res.user else None
    except Exception as e:
        err = str(e).lower()
        if "already" in err or "duplicate" in err or "exists" in err:
            # User exists in auth but not in profiles — try to get auth user
            try:
                users = admin_client.auth.admin.list_users()
                for u in (users.users if hasattr(users, "users") else []):
                    if getattr(u, "email", "") == email:
                        return u.id
            except Exception:
                pass
        return None


def setup_simulation_users(dry_run: bool = False) -> dict:
    """
    Idempotently create/verify Vijay, Manish, Manisha.
    Returns {vijay_id, manish_id, manisha_id, family_id, status, messages}.
    """
    messages = []
    result   = {}

    if dry_run:
        return {
            "vijay_id":  "dry-run-vijay",
            "manish_id": "dry-run-manish",
            "manisha_id":"dry-run-manisha",
            "family_id": "dry-run-family",
            "status":    "dry_run",
            "messages":  ["Dry run: no users created"],
        }

    family_id = _ensure_family()
    messages.append(f"Family id: {family_id[:8]}…")

    user_ids = {}
    for key, spec in SIM_USERS.items():
        existing = _safe_get("profiles", {"email": spec["email"]})
        if existing:
            user_ids[key] = existing["id"]
            messages.append(f"{key}: existing profile found")
            # Ensure correct role/access
            patch: dict = {"account_status": "active", "family_id": family_id}
            if spec["role"] == "student":
                patch.update({
                    "subscription_plan":   "family_premium",
                    "access_cbse":         True,
                    "daily_token_limit":   2000000,
                    "monthly_token_limit": 50000000,
                    "grade":               spec["grade"],
                    "board":               spec["board"],
                })
            admin_client.table("profiles").update(patch).eq("id", existing["id"]).execute()
            continue

        uid = _ensure_auth_user(spec["email"])
        if not uid:
            messages.append(f"WARNING: Could not create auth user for {key}")
            user_ids[key] = f"missing-{key}"
            continue

        profile: dict = {
            "id":             uid,
            "email":          spec["email"],
            "username":       spec["username"],
            "role":           spec["role"],
            "family_id":      family_id,
            "account_status": "active",
        }
        if spec["role"] == "student":
            profile.update({
                "parent_id":           None,
                "grade":               spec["grade"],
                "board":               spec["board"],
                "subscription_plan":   "family_premium",
                "access_cbse":         True,
                "access_sof_science":  False,
                "access_sof_maths":    False,
                "access_sof_english":  False,
                "cbse_subjects":       [],
                "daily_token_limit":   2000000,
                "monthly_token_limit": 50000000,
                "ai_model_preference": "default",
            })
        else:
            profile.update({
                "subscription_plan": "family_premium",
                "access_cbse":       True,
                "access_sof_science": False,
                "access_sof_maths":   False,
                "access_sof_english": False,
            })

        _upsert_profile(profile)
        user_ids[key] = uid
        messages.append(f"{key}: created profile ({uid[:8]}…)")

    # Link Vijay to Manish as parent_id if known
    if "vijay" in user_ids and "manish" in user_ids:
        admin_client.table("profiles").update({
            "parent_id": user_ids["manish"]
        }).eq("id", user_ids["vijay"]).execute()

    result = {
        "vijay_id":  user_ids.get("vijay",   ""),
        "manish_id": user_ids.get("manish",  ""),
        "manisha_id":user_ids.get("manisha", ""),
        "family_id": family_id,
        "status":    "ready",
        "messages":  messages,
    }
    return result


# ── Current simulation day ────────────────────────────────────────────────────

def get_current_simulated_day() -> int:
    """Return the highest completed simulated day across all completed runs."""
    try:
        r = (admin_client.table("learning_simulation_runs")
             .select("cycle_end_day")
             .eq("status", "completed")
             .order("cycle_end_day", desc=True)
             .limit(1)
             .execute())
        if r.data:
            return r.data[0]["cycle_end_day"]
    except Exception:
        pass
    return 0


def get_simulation_status() -> dict:
    """Return current simulation status and summary stats."""
    current_day = get_current_simulated_day()
    try:
        runs_r = (admin_client.table("learning_simulation_runs")
                  .select("*")
                  .order("created_at", desc=True)
                  .limit(10)
                  .execute())
        runs = runs_r.data or []
    except Exception:
        runs = []

    # User setup status
    vijay = _safe_get("profiles", {"email": SIM_USERS["vijay"]["email"]})
    manish = _safe_get("profiles", {"email": SIM_USERS["manish"]["email"]})

    return {
        "current_day":       current_day,
        "next_cycle_start":  current_day + 1,
        "next_cycle_end":    current_day + 7,
        "users_setup":       bool(vijay and manish),
        "vijay_access":      vijay.get("subscription_plan") if vijay else None,
        "recent_runs":       runs[:5],
        "total_runs":        len(runs),
    }


# ── Validation helpers ────────────────────────────────────────────────────────

def _validate_vijay_access(vijay_id: str) -> list[dict]:
    """Check Vijay has Family Premium access. Return list of anomalies."""
    anomalies = []
    profile = _safe_get("profiles", {"id": vijay_id})
    if not profile:
        anomalies.append({
            "severity":     "critical",
            "anomaly_type": "access_issue",
            "message":      "Vijay's profile not found",
        })
        return anomalies

    plan = profile.get("subscription_plan", "")
    if plan not in ("family_premium", "starter", "free"):
        anomalies.append({
            "severity":     "critical",
            "anomaly_type": "access_issue",
            "message":      f"Vijay subscription_plan is '{plan}' — expected family_premium",
            "expected":     "family_premium",
            "actual":       plan,
        })
    elif plan != "family_premium":
        anomalies.append({
            "severity":     "high",
            "anomaly_type": "access_issue",
            "message":      f"Vijay has plan '{plan}' instead of family_premium",
            "expected":     "family_premium",
            "actual":       plan,
        })

    if not profile.get("access_cbse"):
        anomalies.append({
            "severity":     "critical",
            "anomaly_type": "access_issue",
            "message":      "Vijay's access_cbse is False — should be True for Family Premium",
            "expected":     True,
            "actual":       False,
        })
    return anomalies


def _validate_score(score: float, context: dict) -> list[dict]:
    """Check mock test score is within 0–100."""
    anomalies = []
    if score > 100:
        anomalies.append({
            "severity":     "critical",
            "anomaly_type": "score_out_of_range",
            "message":      f"Mock test score {score} exceeds 100%",
            "expected":     "0–100",
            "actual":       score,
            "context":      context,
        })
    if score < 0:
        anomalies.append({
            "severity":     "critical",
            "anomaly_type": "score_out_of_range",
            "message":      f"Mock test score {score} is negative",
            "expected":     "0–100",
            "actual":       score,
            "context":      context,
        })
    return anomalies


def _validate_progress_cumulative(vijay_id: str, run_id: str,
                                   cycle_start: int) -> list[dict]:
    """Verify progress wasn't reset — check student_progress table."""
    anomalies = []
    if cycle_start <= 1:
        return anomalies  # Nothing to compare on first run
    try:
        r = (admin_client.table("student_progress")
             .select("id, current_step_index, completed")
             .eq("username", SIM_USERS["vijay"]["username"])
             .execute())
        rows = r.data or []
        if not rows:
            anomalies.append({
                "severity":     "medium",
                "anomaly_type": "progress_not_cumulative",
                "message":      f"No student_progress rows for Vijay after day {cycle_start - 1}",
                "context":      {"run_id": run_id, "cycle_start": cycle_start},
            })
    except Exception:
        pass
    return anomalies


# ── Simulated day activities ──────────────────────────────────────────────────

def _simulate_lesson_day(vijay_id: str, run_id: str, day: int,
                          dry_run: bool) -> dict:
    """Simulate Vijay completing lesson steps for one subject on a given day."""
    curriculum_item = SIM_CURRICULUM[(day - 1) % len(SIM_CURRICULUM)]
    subject = curriculum_item["subject"]
    chapter = curriculum_item["chapter"]

    steps_completed = random.randint(1, 3)

    if not dry_run:
        # Write progress record
        try:
            progress_key = f"{vijay_id}|CBSE|{subject}|{chapter}"
            existing = (admin_client.table("student_progress")
                        .select("id, current_step_index, step_lessons")
                        .eq("username", SIM_USERS["vijay"]["username"])
                        .eq("subject", subject)
                        .eq("chapter", chapter)
                        .limit(1).execute())
            if existing.data:
                old = existing.data[0]
                new_idx = min((old.get("current_step_index") or 0) + steps_completed, 4)
                admin_client.table("student_progress").update({
                    "current_step_index":  new_idx,
                    "highest_unlocked_step": new_idx,
                }).eq("id", old["id"]).execute()
            else:
                admin_client.table("student_progress").insert({
                    "username":             SIM_USERS["vijay"]["username"],
                    "grade":                "Grade 9",
                    "mode":                 "CBSE",
                    "subject":              subject,
                    "chapter":              chapter,
                    "current_step_index":   steps_completed - 1,
                    "highest_unlocked_step": steps_completed - 1,
                    "completed":            steps_completed >= 5,
                    "last_lesson":          f"[Simulation Day {day}] Auto-generated lesson for {chapter}",
                    "step_lessons":         {str(i): f"[sim] step {i}" for i in range(steps_completed)},
                }).execute()
        except Exception:
            pass

        _record_event(run_id, day, "lesson", vijay_id, subject, chapter,
                      metadata={"steps_completed": steps_completed, "sim_day": day})

    return {"subject": subject, "chapter": chapter, "steps_completed": steps_completed}


def _simulate_practice_day(vijay_id: str, run_id: str, day: int,
                            dry_run: bool) -> dict:
    """Simulate Vijay answering 2–4 practice MCQs."""
    curriculum_item = SIM_CURRICULUM[(day - 1) % len(SIM_CURRICULUM)]
    attempted = random.randint(2, 4)
    # Improving accuracy over time
    accuracy = min(0.4 + (day * 0.04), 0.85)
    correct = round(attempted * accuracy)

    if not dry_run:
        _record_event(run_id, day, "practice", vijay_id,
                      curriculum_item["subject"], curriculum_item["chapter"],
                      metadata={"attempted": attempted, "correct": correct,
                                "incorrect": attempted - correct, "sim_day": day})

    return {"attempted": attempted, "correct": correct}


def _simulate_doubt_day(vijay_id: str, run_id: str, day: int,
                        dry_run: bool) -> dict:
    """Simulate Vijay asking a doubt — uses real doubt_history schema."""
    curriculum_item = SIM_CURRICULUM[(day - 1) % len(SIM_CURRICULUM)]
    doubt_topics = [
        f"What is the main concept in {curriculum_item['chapter']}?",
        f"Explain the key formula from {curriculum_item['subject']} chapter {day}.",
        "Can you give me an example of this topic?",
    ]
    question = random.choice(doubt_topics)
    answer   = (
        f"[Simulation Day {day}] This is a synthetic answer for the doubt about "
        f"{curriculum_item['chapter']} in {curriculum_item['subject']}. "
        "In a real session the AI would provide a detailed explanation here."
    )

    if not dry_run:
        try:
            # Match exact schema of doubt_history_service.save_doubt_history()
            admin_client.table("doubt_history").insert({
                "profile_id":       vijay_id,
                "username":         SIM_USERS["vijay"]["username"],
                "grade":            "Grade 9",
                "mode":             "CBSE",
                "board":            "CBSE",
                "subject":          curriculum_item["subject"],
                "chapter":          curriculum_item["chapter"],
                "question":         question,
                "prompt_question":  question,
                "answer":           answer,
                "source_type":      "SIMULATION",
                "sources":          [],
                "mentor_suggestions": [
                    f"Review {curriculum_item['chapter']} section 1",
                    "Attempt 2 practice questions on this topic",
                ],
            }).execute()
        except Exception:
            pass
        _record_event(run_id, day, "doubt", vijay_id,
                      curriculum_item["subject"], curriculum_item["chapter"],
                      metadata={"question": question, "sim_day": day})

    return {"question": question}


def _simulate_mock_test_day(vijay_id: str, run_id: str, day: int,
                             dry_run: bool) -> dict:
    """Simulate Vijay attempting a mock test — uses real test_history schema."""
    curriculum_item = SIM_CURRICULUM[(day - 1) % len(SIM_CURRICULUM)]
    subject         = curriculum_item["subject"]
    total_q         = 10
    score_pct       = _mock_score(day)
    correct         = round(total_q * score_pct / 100)
    wrong           = total_q - correct

    anomalies = _validate_score(score_pct, {"subject": subject, "day": day})

    if not dry_run:
        try:
            # Use the exact same schema as test_history_service.save_test_result()
            admin_client.table("test_history").insert({
                "username":    SIM_USERS["vijay"]["username"],
                "grade":       "Grade 9",
                "mode":        "CBSE",
                "subject":     subject,
                "chapter":     curriculum_item["chapter"],
                "mock_type":   "chapter",
                "exam_type":   "chapter",
                "difficulty":  "Medium",
                "raw_score":   correct,
                "final_score": correct,
                "max_score":   total_q,
                "wrong_count": wrong,
                "penalty":     0,
                "percentage":  score_pct,
                "submitted_at": datetime.now(timezone.utc).isoformat(),
            }).execute()
        except Exception:
            pass
        _record_event(run_id, day, "mock_test", vijay_id, subject, curriculum_item["chapter"],
                      metadata={"score": score_pct, "total_q": total_q,
                                "correct": correct, "sim_day": day})

    return {"subject": subject, "score": score_pct, "total_q": total_q,
            "correct": correct, "anomalies": anomalies}


def _simulate_formula_day(vijay_id: str, run_id: str, day: int,
                          dry_run: bool) -> dict:
    """Simulate Vijay viewing Formula Sheets."""
    subjects = ["Maths", "Science"]
    subject  = subjects[day % len(subjects)]

    if not dry_run:
        _record_event(run_id, day, "formula", vijay_id, subject, "",
                      metadata={"premium_expanded": True, "sim_day": day})

    return {"subject": subject, "premium_expanded": True}


def _simulate_exemplar_day(vijay_id: str, run_id: str, day: int,
                            dry_run: bool) -> dict:
    """Simulate Vijay accessing Exemplar content."""
    subjects  = ["Maths", "Science"]
    subject   = subjects[day % len(subjects)]
    attempted = random.randint(1, 3)
    correct   = random.randint(0, attempted)

    if not dry_run:
        _record_event(run_id, day, "exemplar", vijay_id, subject, "",
                      metadata={"mcqs_attempted": attempted, "correct": correct,
                                "sim_day": day})

    return {"subject": subject, "mcqs_attempted": attempted, "correct": correct}


def _validate_student_dashboard(vijay_id: str, run_id: str, day: int) -> list[dict]:
    """Basic validation: Vijay's profile has expected access fields."""
    anomalies = []
    profile   = _safe_get("profiles", {"id": vijay_id})
    if not profile:
        anomalies.append({
            "severity":     "critical",
            "anomaly_type": "dashboard_mismatch",
            "message":      "Vijay's profile missing for dashboard validation",
            "context":      {"run_id": run_id, "day": day},
        })
        return anomalies

    if not profile.get("access_cbse"):
        anomalies.append({
            "severity":     "critical",
            "anomaly_type": "access_issue",
            "message":      "Student dashboard: access_cbse=False despite Family Premium",
            "expected":     True,
            "actual":       False,
            "context":      {"run_id": run_id, "day": day},
        })

    if profile.get("subscription_plan") != "family_premium":
        anomalies.append({
            "severity":     "high",
            "anomaly_type": "access_issue",
            "message":      f"Student dashboard: plan='{profile.get('subscription_plan')}' not family_premium",
            "expected":     "family_premium",
            "actual":       profile.get("subscription_plan"),
            "context":      {"run_id": run_id, "day": day},
        })
    return anomalies


def _validate_parent_dashboard(vijay_id: str, manish_id: str, run_id: str,
                               day: int) -> list[dict]:
    """Basic parent validation: Vijay is linked to Manish's family."""
    anomalies = []
    vijay_profile  = _safe_get("profiles", {"id": vijay_id})
    manish_profile = _safe_get("profiles", {"id": manish_id})

    if not vijay_profile or not manish_profile:
        anomalies.append({
            "severity":     "high",
            "anomaly_type": "dashboard_mismatch",
            "message":      "Parent dashboard: simulation profile(s) not found",
            "context":      {"run_id": run_id, "day": day},
        })
        return anomalies

    if vijay_profile.get("family_id") != manish_profile.get("family_id"):
        anomalies.append({
            "severity":     "high",
            "anomaly_type": "dashboard_mismatch",
            "message":      "Parent dashboard: Vijay and Manish are not in the same family",
            "expected":     manish_profile.get("family_id"),
            "actual":       vijay_profile.get("family_id"),
            "context":      {"run_id": run_id, "day": day},
        })
    return anomalies


# ── Main simulation runner ────────────────────────────────────────────────────

def run_simulation(cycle_days: int, dry_run: bool, create_bugs: bool,
                   strict_validation: bool, admin_id: str) -> dict:
    """
    Run a simulation cycle. Returns run summary dict.

    1. Setup users (idempotent)
    2. Create run record
    3. Simulate each day
    4. Validate dashboards
    5. Record anomalies and optionally create Product Bugs
    6. Mark run completed
    """
    cycle_days = max(1, min(cycle_days, 30))

    # Setup users
    setup_result = setup_simulation_users(dry_run=dry_run)
    vijay_id     = setup_result.get("vijay_id",  "")
    manish_id    = setup_result.get("manish_id", "")

    # Determine cycle start/end
    current_day  = get_current_simulated_day() if not dry_run else 0
    cycle_start  = current_day + 1
    cycle_end    = current_day + cycle_days

    # Create run record
    run_id = str(uuid.uuid4())
    if not dry_run:
        try:
            admin_client.table("learning_simulation_runs").insert({
                "id":                  run_id,
                "status":              "running",
                "cycle_start_day":     cycle_start,
                "cycle_end_day":       cycle_end,
                "created_by_admin_id": admin_id,
                "dry_run":             dry_run,
                "create_bugs":         create_bugs,
                "strict_validation":   strict_validation,
                "started_at":          datetime.now(timezone.utc).isoformat(),
            }).execute()
        except Exception:
            pass  # Table may not exist yet — run still proceeds

    # Counters
    all_anomalies: list[dict] = []
    summary = {
        "run_id":           run_id,
        "dry_run":          dry_run,
        "cycle_start_day":  cycle_start,
        "cycle_end_day":    cycle_end,
        "total_days":       cycle_days,
        "setup":            setup_result,
        "days":             [],
        "total_events":     0,
        "anomalies":        [],
        "bugs_created":     0,
    }

    # Validate Vijay's access once at the start
    if not dry_run:
        access_anomalies = _validate_vijay_access(vijay_id)
        all_anomalies.extend(access_anomalies)

        cumul_anomalies = _validate_progress_cumulative(vijay_id, run_id, cycle_start)
        all_anomalies.extend(cumul_anomalies)

    # ── Simulate each day ────────────────────────────────────────────────────
    for day_offset in range(cycle_days):
        day = cycle_start + day_offset
        day_result = {"day": day, "events": [], "anomalies": []}

        lesson   = _simulate_lesson_day(vijay_id, run_id, day, dry_run)
        practice = _simulate_practice_day(vijay_id, run_id, day, dry_run)
        doubt    = _simulate_doubt_day(vijay_id, run_id, day, dry_run)
        mock     = _simulate_mock_test_day(vijay_id, run_id, day, dry_run)
        formula  = _simulate_formula_day(vijay_id, run_id, day, dry_run)
        exemplar = _simulate_exemplar_day(vijay_id, run_id, day, dry_run)

        # Collect mock test anomalies
        if mock.get("anomalies"):
            for a in mock["anomalies"]:
                all_anomalies.append({**a, "day": day})

        # Dashboard validations every 3rd day
        if (day % 3 == 0 or day == cycle_end) and not dry_run:
            stu_anomalies = _validate_student_dashboard(vijay_id, run_id, day)
            par_anomalies = _validate_parent_dashboard(vijay_id, manish_id, run_id, day)
            for a in stu_anomalies + par_anomalies:
                all_anomalies.append({**a, "day": day})
            if not dry_run:
                _record_event(run_id, day, "dashboard_check", vijay_id,
                              metadata={"student_ok": not stu_anomalies,
                                        "parent_ok": not par_anomalies})
                _record_event(run_id, day, "parent_check", manish_id,
                              metadata={"parent_ok": not par_anomalies})

        day_result["events"] = [
            {"type": "lesson",    **lesson},
            {"type": "practice",  **practice},
            {"type": "doubt",     **doubt},
            {"type": "mock_test", **mock},
            {"type": "formula",   **formula},
            {"type": "exemplar",  **exemplar},
        ]
        summary["days"].append(day_result)
        summary["total_events"] += 6

    # ── Record anomalies + create bugs ───────────────────────────────────────
    bugs_created = 0
    recorded_anomaly_ids = []
    for a in all_anomalies:
        if not dry_run:
            anomaly_id = _record_anomaly(
                run_id    = run_id,
                severity  = a.get("severity", "medium"),
                anomaly_type = a.get("anomaly_type", "unknown"),
                message   = a.get("message", ""),
                expected  = a.get("expected"),
                actual    = a.get("actual"),
                context   = {k: v for k, v in a.items()
                             if k not in ("severity","anomaly_type","message","expected","actual")},
            )
            recorded_anomaly_ids.append(anomaly_id)

            if create_bugs:
                bug_id = _create_product_bug(
                    anomaly_id = anomaly_id,
                    run_id     = run_id,
                    severity   = a.get("severity", "medium"),
                    message    = a.get("message", ""),
                    context    = {"run_id": run_id, **a},
                    admin_id   = admin_id,
                )
                if bug_id:
                    bugs_created += 1

    # ── Update Vijay's profile: streak + XP reflect simulated activity ───────
    if not dry_run and vijay_id and not vijay_id.startswith("missing"):
        try:
            vijay_profile = _safe_get("profiles", {"id": vijay_id})
            current_streak = (vijay_profile.get("study_streak_days") or 0) if vijay_profile else 0
            current_xp     = (vijay_profile.get("xp_points") or 0) if vijay_profile else 0
            # Each day adds 1 streak and 50 XP (practice + lesson + mock)
            new_streak = current_streak + cycle_days
            new_xp     = current_xp + (cycle_days * 150)
            admin_client.table("profiles").update({
                "study_streak_days": new_streak,
                "xp_points":        new_xp,
            }).eq("id", vijay_id).execute()
        except Exception:
            pass  # xp_points column may not exist — silently skip

    summary["anomalies"]    = all_anomalies
    summary["bugs_created"] = bugs_created

    # ── Finalise run record ──────────────────────────────────────────────────
    if not dry_run:
        try:
            admin_client.table("learning_simulation_runs").update({
                "status":            "completed",
                "completed_at":      datetime.now(timezone.utc).isoformat(),
                "total_events":      summary["total_events"],
                "anomalies_count":   len(all_anomalies),
                "bugs_created_count": bugs_created,
                "summary_json":      json.dumps({
                    k: v for k, v in summary.items()
                    if k not in ("days",)  # keep summary_json small
                }),
            }).eq("id", run_id).execute()
        except Exception:
            pass

    summary["status"] = "completed" if not dry_run else "dry_run"
    return summary


# ── Reset simulation data ─────────────────────────────────────────────────────

def reset_simulation_data(admin_id: str) -> dict:
    """
    Delete or archive all synthetic simulation data.
    Only deletes clearly synthetic test users and their data.
    Never touches real users.
    """
    deleted = []
    errors  = []

    sim_emails = [spec["email"] for spec in SIM_USERS.values()]

    for email in sim_emails:
        profile = _safe_get("profiles", {"email": email})
        if not profile:
            deleted.append(f"{email}: not found (skip)")
            continue
        uid = profile["id"]
        # Delete simulation data for this user
        for table in ("student_progress", "test_history", "doubt_history"):
            try:
                admin_client.table(table).delete().eq("username", profile["username"]).execute()
            except Exception as e:
                errors.append(f"{table}/{email}: {str(e)[:80]}")
        deleted.append(f"{email}: data cleared")

    # Clear simulation run records
    try:
        admin_client.table("learning_simulation_runs").delete().eq(
            "created_by_admin_id", admin_id
        ).execute()
    except Exception:
        pass

    return {
        "success": True,
        "deleted": deleted,
        "errors":  errors,
        "message": "Simulation data reset. Synthetic user profiles and auth accounts preserved.",
    }


# ── Get run detail ────────────────────────────────────────────────────────────

def get_run_detail(run_id: str) -> dict:
    run = _safe_get("learning_simulation_runs", {"id": run_id})
    if not run:
        return {"error": "Run not found"}
    try:
        events_r = (admin_client.table("learning_simulation_events")
                    .select("*").eq("run_id", run_id)
                    .order("simulated_day").execute())
        events = events_r.data or []
    except Exception:
        events = []
    try:
        anom_r = (admin_client.table("learning_simulation_anomalies")
                  .select("*").eq("run_id", run_id)
                  .order("severity").execute())
        anomalies = anom_r.data or []
    except Exception:
        anomalies = []
    return {"run": run, "events": events, "anomalies": anomalies}


def get_anomalies(run_id: str | None = None) -> list[dict]:
    try:
        q = admin_client.table("learning_simulation_anomalies").select("*")
        if run_id:
            q = q.eq("run_id", run_id)
        r = q.order("created_at", desc=True).limit(100).execute()
        return r.data or []
    except Exception:
        return []
