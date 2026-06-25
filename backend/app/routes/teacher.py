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
from app.services.model_routing_service import resolve_student_feature_model
from app.services.rag_service import search_textbook_content
from app.services.question_bank_service import get_questions_from_bank

_logger = logging.getLogger("likhapoha.teacher")
router = APIRouter()


def _get_profile(user_id: str) -> dict:
    """Return the full application profile for role and model-preference checks."""
    try:
        resp = admin_client.table("profiles").select("role,ai_model_preference,subscription_plan").eq("id", user_id).single().execute()
        return resp.data or {}
    except Exception:
        return {}


def _get_profile_role(user_id: str) -> str:
    """Return the application role ('teacher', 'admin', 'student', etc.) for a user."""
    return _get_profile(user_id).get("role") or ""


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


def _bank_questions_to_test_paper_format(bank_questions: list) -> list:
    """Convert question_bank row format to the test-paper MCQ format."""
    result = []
    for q in bank_questions:
        opts_dict = q.get("options") or {}
        if isinstance(opts_dict, dict):
            option_list = [opts_dict.get(k, "") for k in ("A", "B", "C", "D")]
        else:
            continue
        answer_letter = q.get("answer", "A")
        answer_text = opts_dict.get(answer_letter, option_list[0] if option_list else "")
        result.append({
            "question":    q.get("question", ""),
            "options":     option_list,
            "answer":      answer_text,
            "explanation": q.get("explanation", ""),
            "type":        "mcq",
            "source":      "question_bank",
        })
    return result


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
    profile = _get_profile(user.id)
    role = profile.get("role") or ""
    if role not in ("teacher", "admin"):
        raise HTTPException(status_code=403, detail="Only teachers can generate test papers.")

    # Use admin-configured model — honours whatever model admin has selected in Admin Control
    ai_model = resolve_student_feature_model(profile, feature="teacher_tool")

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

    try:
        client = get_openai_client()
    except Exception as exc:
        _logger.error("OpenAI client init failed: %s", exc)
        raise HTTPException(status_code=500, detail="AI service is not configured. Please check OPENAI_API_KEY on the server.")

    questions: list = []
    last_error: str = ""
    bank_source_count = 0

    # ── MCQ generation: question bank first → LLM for shortfall ──────────────
    if mcq_count > 0:
        # 1. Try the question bank — zero token cost
        bank_difficulty = data.difficulty if data.difficulty != "Mixed" else "Medium"
        try:
            bank_qs = get_questions_from_bank(
                board="CBSE",
                grade=data.grade,
                subject=data.subject,
                chapter=data.chapter,
                difficulty=bank_difficulty,
                num_questions=mcq_count,
            )
            bank_mcqs = _bank_questions_to_test_paper_format(bank_qs)
            if bank_mcqs:
                questions.extend(bank_mcqs[:mcq_count])
                bank_source_count = len(questions)
                _logger.info(
                    "test-paper: served %d/%d MCQs from question_bank for %s %s %s",
                    len(bank_mcqs), mcq_count, data.grade, data.subject, data.chapter[:40]
                )
        except Exception as exc:
            _logger.warning("Question bank lookup failed: %s — falling back to LLM", exc)

        # 2. Fill any shortfall with LLM
        llm_needed = mcq_count - len([q for q in questions if q.get("type") == "mcq"])
        if llm_needed > 0:
            try:
                resp = client.chat.completions.create(
                    model=ai_model,
                    messages=[{"role": "user", "content": _build_mcq_prompt(
                        data.grade, data.subject, data.chapter, data.difficulty, llm_needed, context
                    )}],
                    temperature=0.7,
                    max_tokens=4000,
                )
                raw = resp.choices[0].message.content or ""
                mcqs = _safe_parse_questions(raw, "mcq")
                if mcqs:
                    questions.extend(mcqs[:llm_needed])
                else:
                    last_error = f"MCQ LLM fallback parse failed. Model returned: {raw[:200]}"
                    _logger.warning("MCQ LLM parse empty. Raw: %s", raw[:300])
            except Exception as exc:
                last_error = str(exc)
                err_lower = last_error.lower()
                if "429" in last_error or "rate" in err_lower or "quota" in err_lower:
                    raise HTTPException(status_code=429, detail="AI service is busy. Please try again in a moment.")
                _logger.error("MCQ LLM generation failed: %s", exc)

    # Generate subjective questions
    if subj_count > 0:
        try:
            resp = client.chat.completions.create(
                model=ai_model,
                messages=[{"role": "user", "content": _build_subjective_prompt(
                    data.grade, data.subject, data.chapter, data.difficulty, subj_count, context
                )}],
                temperature=0.7,
                max_tokens=4000,
            )
            raw = resp.choices[0].message.content or ""
            subjs = _safe_parse_questions(raw, "subjective")
            if subjs:
                questions.extend(subjs[:subj_count])
            else:
                last_error = f"Subjective parsing failed. Model returned: {raw[:200]}"
                _logger.warning("Subjective parse empty. Raw: %s", raw[:300])
        except Exception as exc:
            last_error = str(exc)
            err_lower = last_error.lower()
            if "429" in last_error or "rate" in err_lower or "quota" in err_lower:
                raise HTTPException(status_code=429, detail="AI service is busy. Please try again in a moment.")
            _logger.error("Subjective generation failed: %s", exc)

    if not questions:
        detail = "Could not generate questions."
        if last_error:
            if "api key" in last_error.lower() or "authentication" in last_error.lower():
                detail = "AI service is not configured. Please check the server's OPENAI_API_KEY."
            elif "model" in last_error.lower():
                detail = f"AI model error: {last_error[:120]}"
            else:
                detail = f"Generation failed: {last_error[:120]}"
        raise HTTPException(status_code=500, detail=detail)

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


class LessonPlanRequest(BaseModel):
    grade: str
    subject: str
    chapter: str
    duration_minutes: int = 45


_LESSON_PLAN_PROMPT = """You are an experienced CBSE school teacher creating a detailed lesson plan.

Grade: {grade}
Subject: {subject}
Chapter/Topic: {chapter}
Duration: {duration} minutes

{context}

Create a comprehensive, structured lesson plan in the following exact format (use Markdown):

## 📋 Lesson Overview
- **Topic:** {chapter}
- **Grade:** {grade}
- **Subject:** {subject}
- **Duration:** {duration} minutes
- **CBSE Unit:** (identify the unit/chapter from NCERT)

## 🎯 Learning Objectives
By the end of this lesson, students will be able to:
1. (recall/understand level objective)
2. (application level objective)
3. (analysis/evaluation level objective — HOTS)

## 📚 Prerequisites
Students should already know:
- (prerequisite 1)
- (prerequisite 2)

## 🛠️ Materials & Resources
- NCERT Textbook {grade} {subject}
- Blackboard / Whiteboard
- (additional materials specific to this topic)

## 📝 Lesson Plan (Step-by-Step)

### 🔔 Introduction & Hook (5 minutes)
- (attention-grabbing opening activity or question)
- Connect to prior knowledge

### 📖 Direct Instruction (15 minutes)
- (key concept explanation step by step)
- Include the main formula/rule/concept

### 🔬 Guided Practice (10 minutes)
- (worked example with student participation)
- Solve one problem together on the board

### 🏃 Student Activity (10 minutes)
- (individual or pair activity)
- Practice problems from NCERT

### ✅ Assessment & Closure (5 minutes)
- Quick oral questions to check understanding
- Summary of key points
- Exit ticket: (one question to assess learning)

## 📘 Homework Assignment
- NCERT Exercise: (specific exercise numbers)
- (any additional practice)

## 🎯 Differentiation Strategies
- **For slow learners:** (simplified approach or extra support)
- **For advanced learners:** (extension or HOTS challenge)

## 📌 Common Misconceptions to Address
1. (common student mistake 1)
2. (common student mistake 2)

## 🔗 NCERT Alignment
- Chapter reference, Exercise numbers, Example numbers

Keep it practical, concise, and classroom-ready. Use bullet points throughout."""


@router.post("/lesson-plan/generate")
async def generate_lesson_plan(data: LessonPlanRequest, user=Depends(get_current_user)):
    """
    Generate a structured CBSE lesson plan for a teacher.
    Returns Markdown that the frontend renders and can print as PDF.
    """
    profile = _get_profile(user.id)
    role = profile.get("role") or ""
    if role not in ("teacher", "admin"):
        raise HTTPException(status_code=403, detail="Only teachers can generate lesson plans.")

    # Use admin-configured model — honours whatever model admin has selected in Admin Control
    ai_model = resolve_student_feature_model(profile, feature="teacher_tool")

    # Pull RAG context for the chapter
    try:
        rag_results = search_textbook_content(
            query=f"{data.chapter} {data.subject} CBSE {data.grade} lesson",
            grade=data.grade,
            subject=data.subject,
            chapter=data.chapter,
            match_count=6,
        )
        context = "\n\n".join(r.get("chunk_text", "") for r in rag_results[:4] if r.get("chunk_text"))
        context = f"Reference textbook content:\n{context[:2000]}" if context else ""
    except Exception:
        context = ""

    prompt = _LESSON_PLAN_PROMPT.format(
        grade=data.grade,
        subject=data.subject,
        chapter=data.chapter,
        duration=data.duration_minutes,
        context=context,
    )

    try:
        client = get_openai_client()
        resp = client.chat.completions.create(
            model=ai_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
            max_tokens=3000,
        )
        plan = resp.choices[0].message.content or ""
    except Exception as exc:
        _logger.error("Lesson plan generation failed: %s", exc)
        raise HTTPException(status_code=500, detail="Could not generate lesson plan. Please try again.")

    return {
        "success": True,
        "grade": data.grade,
        "subject": data.subject,
        "chapter": data.chapter,
        "duration_minutes": data.duration_minutes,
        "lesson_plan": plan,
    }


@router.get("/student-analytics")
async def get_teacher_student_analytics(user=Depends(get_current_user)):
    """
    Return mock-test history for all students assigned to this teacher.

    The frontend uses this data to show a per-student progress view.
    """
    role = _get_profile_role(user.id)
    if role not in ("teacher", "admin"):
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
