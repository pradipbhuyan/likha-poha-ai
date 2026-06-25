"""
Teacher Routes
==============
Endpoints specific to teacher accounts:
  POST /api/teacher/test-paper/generate  — AI-generated test paper (MCQ + subjective)
  GET  /api/teacher/student-analytics    — progress across all assigned students
"""
import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.services.auth_service import get_current_user, admin_client
from app.services.openai_service import get_openai_client
from app.services.rag_service import search_textbook_content

_logger = logging.getLogger("likhapoha.teacher")
router = APIRouter()


# ── Schemas ────────────────────────────────────────────────────────────────────

class TestPaperRequest(BaseModel):
    grade: str
    subject: str
    chapter: str
    difficulty: str = "Medium"
    mcq_count: int = 6
    subjective_count: int = 4


# ── Helpers ────────────────────────────────────────────────────────────────────

_DIFFICULTY_GUIDE = {
    "Easy":   "straightforward recall and identification questions suitable for average students",
    "Medium": "application and understanding questions that require moderate thinking",
    "Hard":   "analysis, evaluation and HOTS (Higher Order Thinking Skills) questions",
    "Mixed":  "a variety covering easy (30%), medium (40%), and hard (30%) questions",
}


def _build_mcq_prompt(grade: str, subject: str, chapter: str, difficulty: str, count: int, context: str) -> str:
    guide = _DIFFICULTY_GUIDE.get(difficulty, _DIFFICULTY_GUIDE["Medium"])
    return f"""You are an experienced CBSE school teacher for {grade} creating a multiple-choice test.

Chapter: {chapter}
Subject: {subject}
Grade: {grade}
Difficulty: {difficulty} — {guide}

{f'Reference content:{chr(10)}{context[:2000]}' if context else ''}

Generate exactly {count} MCQ questions. Each must have:
- A clear question statement
- Exactly 4 distinct options (A, B, C, D as plain text without labels)
- One correct answer (matching one of the options exactly)

Respond ONLY with a valid JSON array:
[
  {{
    "question": "...",
    "options": ["option A text", "option B text", "option C text", "option D text"],
    "answer": "option A text",
    "type": "mcq"
  }},
  ...
]
No markdown, no explanation, only the JSON array."""


def _build_subjective_prompt(grade: str, subject: str, chapter: str, difficulty: str, count: int, context: str) -> str:
    guide = _DIFFICULTY_GUIDE.get(difficulty, _DIFFICULTY_GUIDE["Medium"])
    return f"""You are an experienced CBSE school teacher for {grade} creating subjective questions.

Chapter: {chapter}
Subject: {subject}
Grade: {grade}
Difficulty: {difficulty} — {guide}

{f'Reference content:{chr(10)}{context[:2000]}' if context else ''}

Generate exactly {count} subjective questions. Mix short-answer (2-3 marks) and long-answer (4-5 marks) as appropriate.

Respond ONLY with a valid JSON array:
[
  {{
    "question": "...",
    "answer": "A concise model answer for the teacher to reference.",
    "marks": 3,
    "lines": 4,
    "type": "subjective"
  }},
  ...
]
No markdown, no explanation, only the JSON array."""


def _safe_parse_questions(raw: str, expected_type: str) -> list:
    """Extract a JSON array from the LLM response robustly."""
    text = raw.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    # Find first '[' and last ']'
    start = text.find("[")
    end   = text.rfind("]")
    if start == -1 or end == -1:
        return []
    try:
        items = json.loads(text[start:end + 1])
        # Ensure each item has the correct type field
        for item in items:
            item["type"] = expected_type
        return items
    except Exception:
        return []


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.post("/test-paper/generate")
async def generate_test_paper(data: TestPaperRequest, user=Depends(get_current_user)):
    """
    Generate an AI test paper for the given grade/subject/chapter.

    Called by the Teacher Test Paper page. Returns structured question objects
    that the frontend formats as a printable HTML page.
    """
    if user.role not in ("teacher", "admin"):
        raise HTTPException(status_code=403, detail="Only teachers can generate test papers.")

    mcq_count  = min(max(int(data.mcq_count or 0), 0), 30)
    subj_count = min(max(int(data.subjective_count or 0), 0), 20)

    if mcq_count + subj_count == 0:
        raise HTTPException(status_code=400, detail="At least one question is required.")

    # Pull RAG context to ground the questions in the textbook content
    try:
        rag_results = search_textbook_content(
            query=f"{data.chapter} {data.subject} CBSE {data.grade}",
            grade=data.grade,
            subject=data.subject,
            chapter=data.chapter,
            match_count=8,
        )
        context = "\n\n".join(r.get("chunk_text", "") for r in rag_results[:5] if r.get("chunk_text"))
    except Exception:
        context = ""

    client = get_openai_client()
    questions: list = []

    # Generate MCQs
    if mcq_count > 0:
        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": _build_mcq_prompt(
                    data.grade, data.subject, data.chapter, data.difficulty, mcq_count, context
                )}],
                temperature=0.7,
                max_tokens=4000,
            )
            mcqs = _safe_parse_questions(resp.choices[0].message.content, "mcq")
            questions.extend(mcqs[:mcq_count])
        except Exception as exc:
            _logger.error("MCQ generation failed: %s", exc)

    # Generate subjective questions
    if subj_count > 0:
        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": _build_subjective_prompt(
                    data.grade, data.subject, data.chapter, data.difficulty, subj_count, context
                )}],
                temperature=0.7,
                max_tokens=4000,
            )
            subjs = _safe_parse_questions(resp.choices[0].message.content, "subjective")
            questions.extend(subjs[:subj_count])
        except Exception as exc:
            _logger.error("Subjective generation failed: %s", exc)

    if not questions:
        raise HTTPException(status_code=500, detail="Could not generate questions. Please try again.")

    return {
        "success": True,
        "grade": data.grade,
        "subject": data.subject,
        "chapter": data.chapter,
        "difficulty": data.difficulty,
        "questions": questions,
        "total": len(questions),
        "mcq_count": sum(1 for q in questions if q.get("type") == "mcq"),
        "subjective_count": sum(1 for q in questions if q.get("type") == "subjective"),
    }


@router.get("/student-analytics")
async def get_teacher_student_analytics(user=Depends(get_current_user)):
    """
    Return mock-test history for all students assigned to this teacher.

    The frontend uses this data to show a per-student progress view.
    """
    if user.role not in ("teacher", "admin"):
        raise HTTPException(status_code=403, detail="Only teachers can view student analytics.")

    try:
        # Get assignments for this teacher
        assignments_resp = (
            admin_client
            .table("teacher_assignments")
            .select("student_id, grade, subject, section")
            .eq("teacher_id", user.id)
            .execute()
        )
        assignments = assignments_resp.data or []
        student_ids = list({a["student_id"] for a in assignments if a.get("student_id")})

        if not student_ids:
            return {"success": True, "students": []}

        # Fetch profiles
        profiles_resp = (
            admin_client
            .table("profiles")
            .select("id, username, email, grade")
            .in_("id", student_ids)
            .execute()
        )
        profiles = {p["id"]: p for p in (profiles_resp.data or [])}

        # Fetch test history for all students
        history_resp = (
            admin_client
            .table("test_history")
            .select("user_id, subject, chapter, percentage, created_at, difficulty")
            .in_("user_id", student_ids)
            .order("created_at", desc=True)
            .limit(500)
            .execute()
        )
        all_history = history_resp.data or []

        # Group history by student
        history_by_student: dict = {}
        for h in all_history:
            uid = h.get("user_id")
            if uid:
                history_by_student.setdefault(uid, []).append(h)

        students_data = []
        for sid in student_ids:
            profile = profiles.get(sid, {})
            history = history_by_student.get(sid, [])
            scores = [float(h.get("percentage") or 0) for h in history]

            # Per-subject stats
            subject_stats: dict = {}
            for h in history:
                subj = h.get("subject") or "Unknown"
                score = float(h.get("percentage") or 0)
                if subj not in subject_stats:
                    subject_stats[subj] = {"scores": [], "latest": score}
                subject_stats[subj]["scores"].append(score)
                subject_stats[subj]["latest"] = score

            subject_performance = [
                {
                    "subject": s,
                    "best":    max(d["scores"]),
                    "average": round(sum(d["scores"]) / len(d["scores"])),
                    "latest":  d["latest"],
                    "tests":   len(d["scores"]),
                }
                for s, d in subject_stats.items()
            ]

            students_data.append({
                "id": sid,
                "username": profile.get("username", "Unknown"),
                "email": profile.get("email", ""),
                "grade": profile.get("grade") or assignments[0].get("grade", "Grade 9") if assignments else "Grade 9",
                "total_tests": len(history),
                "average_score": round(sum(scores) / len(scores)) if scores else 0,
                "best_score": max(scores) if scores else 0,
                "latest_score": scores[0] if scores else 0,
                "subject_performance": subject_performance,
                "recent_history": history[:10],
            })

        return {"success": True, "students": students_data}

    except Exception as exc:
        _logger.error("teacher student analytics error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
