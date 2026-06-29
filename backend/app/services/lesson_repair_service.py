"""
lesson_repair_service.py — Admin Lesson Repair Engine
─────────────────────────────────────────────────────────────────────────────
Core logic for the Admin Lesson Repair workflow.

Responsibilities:
  1. Read latest lesson_sections audit report
  2. Identify failed lessons (missing / empty / placeholder / short sections)
  3. Create repair tasks (one per failed lesson)
  4. LLM-based repair generation (admin-triggered only — never automatic)
  5. Validate repaired drafts against the canonical 8-section schema
  6. Re-audit repaired draft — must score ≥ 90 overall / ≥ 85 depth
  7. Persist jobs + tasks to DB with graceful in-memory fallback

Safety rules:
  - NEVER overwrite original lesson content directly
  - NEVER run LLM automatically — only when use_llm=True and admin-triggered
  - If LLM fails / JSON invalid / validation fails → mark task failed, keep original
  - original_content_json is preserved always
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

_log = logging.getLogger("likhapoha.lesson_repair")

SECTIONS_REPORT_PATH = Path("reports/lesson_sections/lesson_sections_report.json")

# ── Canonical 8 sections (matches audit_lesson_sections.py exactly) ───────────
CANONICAL_SECTIONS = [
    "introduction",
    "what you will learn",
    "simple explanation",
    "step-by-step breakdown",
    "worked example",
    "common mistake",
    "quick check question",
    "summary",
]

# Keys used in the LLM JSON output
SECTION_KEYS = [
    "introduction",
    "what_you_will_learn",
    "simple_explanation",
    "step_by_step_breakdown",
    "worked_example",
    "common_mistake",
    "quick_check_question",
    "summary",
]

# Minimum thresholds for repair validation (stricter than the audit thresholds)
REPAIR_MIN_WORDS = {
    "introduction": 80,
    "what_you_will_learn": 30,
    "simple_explanation": 150,
    "step_by_step_breakdown": 50,
    "worked_example": 60,
    "common_mistake": 40,
    "quick_check_question": 30,
    "summary": 40,
}

REPAIR_THRESHOLDS = {
    "min_overall_score": 90,
    "min_depth_score": 85,
    "max_critical_issues": 0,
    "max_missing_sections": 0,
    "min_section_compliance": 100,
}

FILLER_PATTERNS = [
    r"coming soon", r"\btbd\b", r"lorem ipsum", r"to be added",
    r"placeholder", r"^\s*-+\s*$", r"^\s*\.\.\.\s*$", r"\[insert",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _word_count(text: str) -> int:
    if not text:
        return 0
    return len(re.findall(r"\b\w+\b", str(text)))


def _has_filler(text: str) -> bool:
    for p in FILLER_PATTERNS:
        if re.search(p, str(text), re.IGNORECASE | re.MULTILINE):
            return True
    return False


def _flatten_section(value) -> str:
    """Flatten a section value to plain text for word-count / filler checks."""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(str(v) for v in value)
    if isinstance(value, dict):
        return " ".join(str(v) for v in value.values())
    return str(value) if value else ""


# ── Repair validation ─────────────────────────────────────────────────────────

def validate_repaired_draft(draft: dict) -> dict:
    """
    Validate a repaired lesson draft against the canonical 8-section schema.

    Returns:
        {
          "valid": bool,
          "issues": [ {"section": ..., "severity": ..., "issue": ...} ],
          "section_compliance": 0-100,
          "depth_score": 0-100,
          "overall_score": 0-100,
          "critical_count": int,
          "missing_sections": [...]
        }
    """
    issues = []
    sections = draft.get("sections", {})
    missing = []
    present = 0

    for key in SECTION_KEYS:
        value = sections.get(key)
        text = _flatten_section(value)

        if not text or not text.strip():
            missing.append(key)
            issues.append({
                "section": key,
                "severity": "critical",
                "issue": f"Section '{key}' is missing or empty in repaired draft.",
            })
            continue

        present += 1

        if _has_filler(text):
            issues.append({
                "section": key,
                "severity": "critical",
                "issue": f"Section '{key}' contains placeholder/filler text.",
            })

        min_wc = REPAIR_MIN_WORDS.get(key, 30)
        wc = _word_count(text)
        if wc < min_wc:
            issues.append({
                "section": key,
                "severity": "high",
                "issue": f"Section '{key}' is too short ({wc} words, needs {min_wc}).",
            })

    # Section-specific structural checks
    we = sections.get("worked_example", {})
    if isinstance(we, dict):
        if not we.get("problem") or not we.get("final_answer"):
            issues.append({
                "section": "worked_example",
                "severity": "critical",
                "issue": "worked_example missing 'problem' or 'final_answer'.",
            })

    cm = sections.get("common_mistake", {})
    if isinstance(cm, dict):
        if not cm.get("mistake") or not cm.get("correction"):
            issues.append({
                "section": "common_mistake",
                "severity": "high",
                "issue": "common_mistake missing 'mistake' or 'correction'.",
            })

    qcq = sections.get("quick_check_question", {})
    if isinstance(qcq, dict):
        if not qcq.get("question") or not qcq.get("answer"):
            issues.append({
                "section": "quick_check_question",
                "severity": "high",
                "issue": "quick_check_question missing 'question' or 'answer'.",
            })

    wyl = sections.get("what_you_will_learn", [])
    if isinstance(wyl, list) and len(wyl) < 3:
        issues.append({
            "section": "what_you_will_learn",
            "severity": "high",
            "issue": f"what_you_will_learn has only {len(wyl)} objectives (need ≥ 3).",
        })

    ssb = sections.get("step_by_step_breakdown", [])
    if isinstance(ssb, list) and len(ssb) < 3:
        issues.append({
            "section": "step_by_step_breakdown",
            "severity": "high",
            "issue": f"step_by_step_breakdown has only {len(ssb)} steps (need ≥ 3).",
        })

    summ = sections.get("summary", [])
    if isinstance(summ, list) and len(summ) < 3:
        issues.append({
            "section": "summary",
            "severity": "high",
            "issue": f"summary has only {len(summ)} takeaways (need ≥ 3).",
        })

    critical_count = sum(1 for i in issues if i["severity"] == "critical")
    high_count = sum(1 for i in issues if i["severity"] == "high")
    total_sections = len(SECTION_KEYS)
    section_compliance = round(present / total_sections * 100)
    depth_score = max(0, 100 - critical_count * 25 - high_count * 10)
    overall_score = round((section_compliance + depth_score) / 2)

    valid = (
        critical_count == 0
        and len(missing) == 0
        and section_compliance == 100
        and overall_score >= REPAIR_THRESHOLDS["min_overall_score"]
        and depth_score >= REPAIR_THRESHOLDS["min_depth_score"]
    )

    return {
        "valid": valid,
        "issues": issues,
        "section_compliance": section_compliance,
        "depth_score": depth_score,
        "overall_score": overall_score,
        "critical_count": critical_count,
        "missing_sections": missing,
    }


# ── Audit report reader ────────────────────────────────────────────────────────

def load_latest_audit_report() -> Optional[dict]:
    """Load latest lesson_sections audit report from disk."""
    if not SECTIONS_REPORT_PATH.exists():
        return None
    try:
        return json.loads(SECTIONS_REPORT_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        _log.error("Failed to load audit report: %s", e)
        return None


def extract_failed_lessons(
    report: dict,
    grade: Optional[str] = None,
    subject: Optional[str] = None,
    chapter: Optional[str] = None,
    sample: bool = False,
    sample_size: int = 10,
) -> list[dict]:
    """
    Extract lessons that failed the audit (have any critical or high issues).

    Filters by grade/subject/chapter if provided. If sample=True returns at
    most sample_size randomly-chosen failures.
    """
    lessons = report.get("lessons", [])
    failed = []

    for lesson in lessons:
        # Apply filters
        if grade and lesson.get("grade") != grade:
            continue
        if subject and lesson.get("subject", "").lower() != subject.lower():
            continue
        if chapter and lesson.get("chapter", "").lower() != chapter.lower():
            continue

        # Include only lessons with at least one issue
        counts = lesson.get("issue_counts", {})
        if counts.get("critical", 0) > 0 or counts.get("high", 0) > 0:
            failed.append(lesson)

    if sample and len(failed) > sample_size:
        import random
        failed = random.sample(failed, sample_size)

    return failed


# ── LLM repair prompt ─────────────────────────────────────────────────────────

_REPAIR_SYSTEM_PROMPT = """You are an expert CBSE curriculum author specialising in Grades 5-12 science and mathematics.
You will receive a lesson that failed quality checks. Your task is to repair it by rewriting
all 8 canonical sections with high-quality, curriculum-aligned content.

STRICT RULES:
1. Return ONLY valid JSON — no markdown fences, no explanation, no preamble.
2. Every section must be substantive and chapter-specific.
3. No placeholder text (no "TBD", "coming soon", "[insert]", etc.).
4. introduction: at least 80 words.
5. what_you_will_learn: exactly a list of 3-5 concrete, measurable objectives as strings.
6. simple_explanation: at least 150 words, uses real concepts from the chapter.
7. step_by_step_breakdown: a list of at least 3 strings, each describing one numbered step.
8. worked_example: object with keys "problem", "solution_steps" (list), "final_answer".
9. common_mistake: object with keys "mistake", "why_wrong", "correction".
10. quick_check_question: object with keys "question", "answer", "explanation".
11. summary: a list of at least 3 specific key takeaways as strings.
12. Use grade-appropriate language and correct mathematical/scientific notation.
13. Content must be specific to the given grade, subject, and chapter — not generic.
"""

_REPAIR_USER_TEMPLATE = """Repair this CBSE lesson. Return ONLY the JSON structure shown.

Grade: {grade}
Subject: {subject}
Chapter: {chapter}
Step/Topic: {step_title}

Issues found in original lesson:
{issues_text}

Return ONLY this JSON (no markdown, no extra text):
{{
  "grade": "{grade}",
  "subject": "{subject}",
  "chapter": "{chapter}",
  "step_title": "{step_title}",
  "sections": {{
    "introduction": "string - at least 80 words",
    "what_you_will_learn": ["objective 1", "objective 2", "objective 3"],
    "simple_explanation": "string - at least 150 words",
    "step_by_step_breakdown": ["Step 1: ...", "Step 2: ...", "Step 3: ..."],
    "worked_example": {{
      "problem": "Clear problem statement",
      "solution_steps": ["Step 1: ...", "Step 2: ..."],
      "final_answer": "The final answer is ..."
    }},
    "common_mistake": {{
      "mistake": "Describe the mistake students make",
      "why_wrong": "Explain why this is wrong",
      "correction": "The correct approach is ..."
    }},
    "quick_check_question": {{
      "question": "A multiple-choice or short-answer question",
      "answer": "The correct answer",
      "explanation": "Explanation of why this is correct"
    }},
    "summary": ["Key takeaway 1", "Key takeaway 2", "Key takeaway 3"]
  }}
}}"""


def build_repaired_content_from_sections(draft: dict) -> str:
    """
    Convert repaired JSON draft → markdown lesson content string.
    This is written back to lesson_cache.lesson_content when publishing.
    """
    s = draft.get("sections", {})
    lines = []

    lines.append(f"# {draft.get('step_title', 'Lesson')}\n")

    lines.append("## Introduction\n")
    lines.append(str(s.get("introduction", "")) + "\n")

    lines.append("## What You Will Learn\n")
    for obj in (s.get("what_you_will_learn") or []):
        lines.append(f"- {obj}")
    lines.append("")

    lines.append("## Simple Explanation\n")
    lines.append(str(s.get("simple_explanation", "")) + "\n")

    lines.append("## Step-by-Step Breakdown\n")
    for i, step in enumerate(s.get("step_by_step_breakdown") or [], 1):
        lines.append(f"**Step {i}.** {step}")
    lines.append("")

    lines.append("## Worked Example\n")
    we = s.get("worked_example", {})
    if isinstance(we, dict):
        lines.append(f"**Problem:** {we.get('problem', '')}\n")
        for step in (we.get("solution_steps") or []):
            lines.append(f"- {step}")
        lines.append(f"\n**Answer:** {we.get('final_answer', '')}")
    lines.append("")

    lines.append("## Common Mistake\n")
    cm = s.get("common_mistake", {})
    if isinstance(cm, dict):
        lines.append(f"**Mistake:** {cm.get('mistake', '')}\n")
        lines.append(f"**Why it is wrong:** {cm.get('why_wrong', '')}\n")
        lines.append(f"**Correction:** {cm.get('correction', '')}")
    lines.append("")

    lines.append("## Quick Check Question\n")
    qcq = s.get("quick_check_question", {})
    if isinstance(qcq, dict):
        lines.append(f"**Question:** {qcq.get('question', '')}\n")
        lines.append(f"**Answer:** {qcq.get('answer', '')}\n")
        lines.append(f"**Explanation:** {qcq.get('explanation', '')}")
    lines.append("")

    lines.append("## Summary\n")
    for point in (s.get("summary") or []):
        lines.append(f"- {point}")
    lines.append("")

    return "\n".join(lines)


# ── LLM repair executor ───────────────────────────────────────────────────────

def run_llm_repair(
    lesson_audit: dict,
    admin_username: str = "admin",
    override_api_key: str | None = None,
) -> dict:
    """
    Call the configured LLM to repair a single failed lesson.

    Returns a dict with keys: success, draft (or None), error.
    NEVER raises — all errors are caught and returned in the result.

    override_api_key: session-only key override. NEVER logged. NEVER stored.
    """
    from app.services.openai_service import ask_llm, get_effective_settings, get_chat_client  # noqa: PLC0415
    from openai import OpenAI  # noqa: PLC0415

    grade = lesson_audit.get("grade", "")
    subject = lesson_audit.get("subject", "")
    chapter = lesson_audit.get("chapter", "")
    step_title = lesson_audit.get("step_title", "")

    issues_text = "\n".join(
        f"- [{i.get('severity','?').upper()}] {i.get('section','?')}: {i.get('issue','')}"
        for i in (lesson_audit.get("all_issues") or [])
    ) or "- Multiple sections missing or have insufficient content"

    user_prompt = _REPAIR_USER_TEMPLATE.format(
        grade=grade,
        subject=subject,
        chapter=chapter,
        step_title=step_title,
        issues_text=issues_text,
    )

    try:
        if override_api_key and override_api_key.strip():
            # Use the override key for this call only — do not log the key
            settings = get_effective_settings()
            provider = settings.get("provider", "openai")
            model_map = {
                "openai":    "gpt-4.1-nano",
                "groq":      settings.get("groq_model") or "llama-3.3-70b-versatile",
                "cerebras":  settings.get("cerebras_model") or "gpt-oss-120b",
                "gemini":    settings.get("gemini_model") or "gemini-2.5-flash",
                "sambanova": settings.get("sambanova_model") or "Meta-Llama-3.3-70B-Instruct",
                "venice":    settings.get("venice_model") or "llama-3.3-70b",
            }
            base_url_map = {
                "openai":    None,  # default
                "groq":      "https://api.groq.com/openai/v1",
                "cerebras":  "https://api.cerebras.ai/v1",
                "gemini":    "https://generativelanguage.googleapis.com/v1beta/openai/",
                "sambanova": "https://api.sambanova.ai/v1",
                "venice":    "https://api.venice.ai/api/v1",
            }
            active_model = model_map.get(provider, "gpt-4.1-nano")
            base_url = base_url_map.get(provider)
            client_kwargs = {"api_key": override_api_key.strip(), "timeout": 90.0}
            if base_url:
                client_kwargs["base_url"] = base_url
            tmp_client = OpenAI(**client_kwargs)
            messages = [
                {"role": "system", "content": _REPAIR_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ]
            response = tmp_client.chat.completions.create(
                model=active_model, messages=messages, temperature=0.4,
            )
            raw = response.choices[0].message.content
        else:
            raw = ask_llm(
                system_prompt=_REPAIR_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                username=admin_username,
                feature="lesson_repair",
            )
    except Exception as exc:
        return {"success": False, "draft": None, "error": f"LLM call failed: {str(exc)[:300]}"}

    # Strip any markdown fences the model may have added despite instructions
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw.strip())

    try:
        draft = json.loads(raw)
    except json.JSONDecodeError as e:
        return {"success": False, "draft": None, "error": f"LLM returned invalid JSON: {e}. Raw (first 300 chars): {raw[:300]}"}

    # Basic structural check
    if "sections" not in draft:
        return {"success": False, "draft": None, "error": "LLM JSON missing 'sections' key."}

    return {"success": True, "draft": draft, "error": None}


# ── DB persistence helpers ────────────────────────────────────────────────────

def _db_insert_job(job: dict) -> bool:
    """Insert a repair job row. Returns True on success."""
    try:
        from app.services.auth_service import admin_client  # noqa: PLC0415
        admin_client.table("lesson_repair_jobs").insert(job).execute()
        return True
    except Exception as e:
        _log.warning("Could not insert repair job to DB: %s", e)
        return False


def _db_update_job(job_id: str, updates: dict) -> bool:
    try:
        from app.services.auth_service import admin_client  # noqa: PLC0415
        admin_client.table("lesson_repair_jobs").update(updates).eq("id", job_id).execute()
        return True
    except Exception as e:
        _log.warning("Could not update repair job %s: %s", job_id, e)
        return False


def _db_insert_task(task: dict) -> bool:
    try:
        from app.services.auth_service import admin_client  # noqa: PLC0415
        admin_client.table("lesson_repair_tasks").insert(task).execute()
        return True
    except Exception as e:
        _log.warning("Could not insert repair task: %s", e)
        return False


def _db_update_task(task_id: str, updates: dict) -> bool:
    try:
        from app.services.auth_service import admin_client  # noqa: PLC0415
        admin_client.table("lesson_repair_tasks").update(updates).eq("id", task_id).execute()
        return True
    except Exception as e:
        _log.warning("Could not update repair task %s: %s", task_id, e)
        return False


def _db_get_job(job_id: str) -> Optional[dict]:
    try:
        from app.services.auth_service import admin_client  # noqa: PLC0415
        r = admin_client.table("lesson_repair_jobs").select("*").eq("id", job_id).limit(1).execute()
        return (r.data or [None])[0]
    except Exception:
        return None


def _db_get_tasks(job_id: str, status: Optional[str] = None) -> list[dict]:
    try:
        from app.services.auth_service import admin_client  # noqa: PLC0415
        q = admin_client.table("lesson_repair_tasks").select("*").eq("job_id", job_id)
        if status:
            q = q.eq("status", status)
        r = q.order("created_at").execute()
        return r.data or []
    except Exception:
        return []


def _db_get_task(task_id: str) -> Optional[dict]:
    try:
        from app.services.auth_service import admin_client  # noqa: PLC0415
        r = admin_client.table("lesson_repair_tasks").select("*").eq("id", task_id).limit(1).execute()
        return (r.data or [None])[0]
    except Exception:
        return None


def _db_list_jobs(limit: int = 20) -> list[dict]:
    try:
        from app.services.auth_service import admin_client  # noqa: PLC0415
        r = (admin_client.table("lesson_repair_jobs")
             .select("id,status,mode,grade,subject,chapter,use_llm,total_tasks,"
                     "completed_tasks,failed_tasks,approved_tasks,published_tasks,"
                     "started_at,completed_at,created_at,error_summary")
             .order("created_at", desc=True).limit(limit).execute())
        return r.data or []
    except Exception:
        return []


# ── Fetch original lesson content from lesson_cache ───────────────────────────

def _fetch_original_content(grade: str, subject: str, chapter: str, step_title: str) -> Optional[dict]:
    """
    Fetch the original lesson content from lesson_cache for preservation.
    Returns dict with {id, lesson_content, status} or None.
    """
    try:
        from app.services.auth_service import admin_client  # noqa: PLC0415
        from app.services.grade_db_router import get_content_db  # noqa: PLC0415
        db = get_content_db(grade)
        r = (db.table("lesson_cache")
             .select("id, grade, subject, chapter, step_title, lesson_content, status")
             .eq("grade", grade)
             .ilike("subject", subject)
             .ilike("chapter", chapter)
             .ilike("step_title", step_title)
             .limit(1)
             .execute())
        rows = r.data or []
        return rows[0] if rows else None
    except Exception as e:
        _log.warning("Could not fetch original lesson content for %s/%s/%s: %s",
                     grade, subject, step_title, e)
        return None


# ── Main repair job runner ────────────────────────────────────────────────────

def run_repair_job(
    job_id: str,
    admin_id: str,
    mode: str,
    use_llm: bool,
    grade: Optional[str] = None,
    subject: Optional[str] = None,
    chapter: Optional[str] = None,
    override_api_key: Optional[str] = None,
    in_memory_jobs: Optional[dict] = None,
    in_memory_tasks: Optional[dict] = None,
) -> None:
    """
    Execute a full repair job in a background thread.

    Steps:
    1. Load latest audit report
    2. Extract failed lessons matching filters
    3. Create repair tasks (one per failed lesson)
    4. For each task:
       a. Fetch original content
       b. If use_llm: call LLM, parse JSON, validate
       c. If validation passes: mark ready_for_review
       d. If LLM fails / validation fails: mark validation_failed
    5. Update job counters throughout
    """
    now = datetime.now(timezone.utc).isoformat()

    def _update_job(updates: dict) -> None:
        if in_memory_jobs is not None:
            in_memory_jobs[job_id] = {**(in_memory_jobs.get(job_id) or {}), **updates}
        _db_update_job(job_id, updates)

    def _update_task(task_id: str, updates: dict) -> None:
        if in_memory_tasks is not None:
            in_memory_tasks[task_id] = {**(in_memory_tasks.get(task_id) or {}), **updates}
        _db_update_task(task_id, updates)

    _update_job({"status": "running", "started_at": now})

    try:
        # ── Step 1: Load audit report ─────────────────────────────────────
        _log.info("[repair:%s] Loading audit report...", job_id)
        report = load_latest_audit_report()
        if not report:
            _update_job({
                "status": "failed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "error_summary": "No lesson_sections audit report found. Run audit first.",
            })
            return

        # ── Step 2: Extract failed lessons ────────────────────────────────
        is_sample = (mode == "sample")
        failed = extract_failed_lessons(
            report, grade=grade, subject=subject, chapter=chapter,
            sample=is_sample, sample_size=10,
        )
        if not failed:
            _update_job({
                "status": "completed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "total_tasks": 0,
                "error_summary": "No failed lessons found matching the selected filters.",
            })
            return

        _update_job({"total_tasks": len(failed)})
        _log.info("[repair:%s] Found %d failed lessons.", job_id, len(failed))

        # ── Step 3: Create repair tasks ───────────────────────────────────
        task_records = []
        for lesson_audit in failed:
            task_id = str(uuid.uuid4())
            original_row = _fetch_original_content(
                lesson_audit.get("grade", ""),
                lesson_audit.get("subject", ""),
                lesson_audit.get("chapter", ""),
                lesson_audit.get("step_title", ""),
            )
            task = {
                "id": task_id,
                "job_id": job_id,
                "grade": lesson_audit.get("grade", ""),
                "subject": lesson_audit.get("subject", ""),
                "chapter": lesson_audit.get("chapter", ""),
                "step_title": lesson_audit.get("step_title", ""),
                "original_lesson_cache_id": (original_row or {}).get("id"),
                "status": "queued",
                "issues_json": lesson_audit.get("all_issues") or [],
                "original_content_json": {
                    "lesson_content": (original_row or {}).get("lesson_content", ""),
                    "cache_status": (original_row or {}).get("status", ""),
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                },
                "audit_before_score": lesson_audit.get("scores", {}).get("overall_lesson_score"),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            task_records.append((task_id, lesson_audit, task))
            if in_memory_tasks is not None:
                in_memory_tasks[task_id] = task
            _db_insert_task(task)

        # ── Step 4: Process each task ─────────────────────────────────────
        completed = 0
        failed_count = 0

        for task_id, lesson_audit, task in task_records:
            _update_task(task_id, {"status": "running"})

            if not use_llm:
                # No LLM — just create the task with issues for admin to review
                _update_task(task_id, {
                    "status": "ready_for_review",
                    "validation_result_json": {
                        "note": "LLM repair not requested. Task created for manual review.",
                        "issues": lesson_audit.get("all_issues") or [],
                    },
                })
                completed += 1
                continue

            # LLM repair path
            _log.info("[repair:%s] Running LLM repair for task %s...", job_id, task_id)
            repair_result = run_llm_repair(
                lesson_audit,
                admin_username=f"admin:{admin_id}",
                override_api_key=override_api_key,
            )

            if not repair_result["success"]:
                _update_task(task_id, {
                    "status": "failed",
                    "error_message": repair_result["error"],
                })
                failed_count += 1
                continue

            draft = repair_result["draft"]
            validation = validate_repaired_draft(draft)
            audit_after = validation.get("overall_score", 0)

            if validation["valid"]:
                _update_task(task_id, {
                    "status": "ready_for_review",
                    "repaired_content_json": draft,
                    "validation_result_json": validation,
                    "audit_after_score": audit_after,
                })
                completed += 1
            else:
                _update_task(task_id, {
                    "status": "validation_failed",
                    "repaired_content_json": draft,
                    "validation_result_json": validation,
                    "audit_after_score": audit_after,
                })
                failed_count += 1

            # Update running counters on job
            _update_job({
                "completed_tasks": completed,
                "failed_tasks": failed_count,
            })

        # ── Step 5: Mark job complete ─────────────────────────────────────
        _update_job({
            "status": "completed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "completed_tasks": completed,
            "failed_tasks": failed_count,
        })
        _log.info("[repair:%s] Completed. %d repaired, %d failed.", job_id, completed, failed_count)

    except Exception as exc:
        sanitised = str(exc)[:500].replace("\n", " ")
        _log.error("[repair:%s] Job failed with exception: %s", job_id, sanitised)
        _update_job({
            "status": "failed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "error_summary": sanitised,
        })


# ── Publish helper: write repaired content back to lesson_cache ───────────────

def publish_repaired_task(task: dict) -> dict:
    """
    Publish an approved repair task back to lesson_cache.

    Safety:
    - Only works if task.status == 'approved'
    - Writes to lesson_cache only if original_lesson_cache_id is available
    - original_content_json is preserved in the task row (never deleted)
    - Returns {success, message}
    """
    if task.get("status") != "approved":
        return {"success": False, "message": "Task must be approved before publishing."}

    repaired = task.get("repaired_content_json")
    if not repaired:
        return {"success": False, "message": "No repaired content available for this task."}

    # Build markdown lesson content from repaired sections
    new_content = build_repaired_content_from_sections(repaired)

    cache_id = task.get("original_lesson_cache_id")
    if not cache_id:
        return {"success": False, "message": "No lesson_cache ID found — cannot publish without original reference."}

    try:
        from app.services.grade_db_router import get_content_db  # noqa: PLC0415
        db = get_content_db(task.get("grade", ""))
        db.table("lesson_cache").update({
            "lesson_content": new_content,
            "status": "active",
        }).eq("id", cache_id).execute()
        return {"success": True, "message": "Lesson published successfully."}
    except Exception as e:
        return {"success": False, "message": f"Publish failed: {str(e)[:200]}"}
