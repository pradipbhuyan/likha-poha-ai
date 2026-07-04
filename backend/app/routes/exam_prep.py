"""
exam_prep.py — JEE / NEET / CUET Exam Prep API
===============================================
Serves Previous Year Question (PYQ) paper data from Supabase 2 RAG.

Endpoints:
  GET  /api/exam-prep/papers?exam=jee          → list of PYQ documents
  GET  /api/exam-prep/paper/{doc_id}/chunks    → question chunks for a paper
  POST /api/exam-prep/explain                  → AI step-by-step explanation

All PYQ content is stored in Supabase 2 (grade_1112_client) as:
  grade:   "Grade 11" or "Grade 12"
  subject: "Physics" | "Chemistry" | "Mathematics" | "Biology"
  chapter: "PYQ: B Tech 2nd Apr 2026 Shift 1"
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.services.auth_service import get_current_user, require_admin
from app.services.logger_service import get_logger
from app.services.openai_service import ask_llm, get_effective_settings
from app.services.supabase_grade_1112_client import grade_1112_client

_log = get_logger("exam_prep")

router = APIRouter(prefix="/api/exam-prep", tags=["exam-prep"])

# ── Paper catalogue ────────────────────────────────────────────────────────────
# Maps exam key → chapter prefix patterns stored in rag_documents
EXAM_CHAPTER_PATTERNS = {
    "jee":  "PYQ: B Tech",
    "neet": "PYQ: NEET",
    "cuet": "PYQ: CUET",
    "all":  "PYQ:",
}


def _get_supabase():
    """Return Supabase 2 client or raise."""
    if grade_1112_client is None:
        raise HTTPException(503, "Exam prep content database not configured")
    return grade_1112_client


# ── GET /api/exam-prep/papers ──────────────────────────────────────────────────

@router.get("/papers")
def list_papers(
    exam: str = "jee",
    _user=Depends(get_current_user),
):
    """
    Return list of available PYQ papers for the given exam.
    Each paper = one rag_documents row with chapter starting with 'PYQ:'.
    """
    sb = _get_supabase()
    pattern = EXAM_CHAPTER_PATTERNS.get(exam.lower(), "PYQ:")

    try:
        r = (
            sb.table("rag_documents")
            .select("id, grade, subject, chapter, created_at")
            .like("chapter", f"{pattern}%")
            .order("chapter")
            .execute()
        )
        rows = r.data or []
    except Exception as exc:
        _log.error("exam_prep.list_papers failed", error=str(exc))
        raise HTTPException(500, "Failed to fetch papers") from exc

    # Deduplicate by chapter name (same paper appears for Grade 11 + 12)
    seen = {}
    for row in rows:
        ch = row["chapter"]
        if ch not in seen:
            seen[ch] = {
                "id":       row["id"],
                "chapter":  ch,
                "subject":  row["subject"],
                "grade":    row["grade"],
                "label":    ch.replace("PYQ: ", ""),
            }

    papers = list(seen.values())
    _log.info("exam_prep.list_papers", exam=exam, count=len(papers))
    return {"success": True, "papers": papers, "count": len(papers)}


# ── GET /api/exam-prep/paper/{doc_id}/chunks ──────────────────────────────────

@router.get("/paper/{doc_id}/chunks")
def get_paper_chunks(
    doc_id: str,
    limit: int = 50,
    _user=Depends(get_current_user),
):
    """
    Return the text chunks for a specific PYQ paper document.
    These are the actual question/passage chunks stored during RAG upload.
    """
    sb = _get_supabase()

    try:
        r = (
            sb.table("rag_chunks")
            .select("id, chunk_index, chunk_text")
            .eq("document_id", doc_id)
            .order("chunk_index")
            .limit(limit)
            .execute()
        )
        chunks = r.data or []
    except Exception as exc:
        _log.error("exam_prep.get_chunks failed", doc_id=doc_id, error=str(exc))
        raise HTTPException(500, "Failed to fetch paper content") from exc

    # Get doc metadata
    try:
        meta_r = (
            sb.table("rag_documents")
            .select("chapter, subject, grade")
            .eq("id", doc_id)
            .single()
            .execute()
        )
        meta = meta_r.data or {}
    except Exception:
        meta = {}

    return {
        "success": True,
        "doc_id":  doc_id,
        "chapter": meta.get("chapter", ""),
        "subject": meta.get("subject", ""),
        "grade":   meta.get("grade", ""),
        "chunks":  chunks,
        "count":   len(chunks),
    }


# ── POST /api/exam-prep/explain ───────────────────────────────────────────────

class ExplainRequest(BaseModel):
    question_text: str
    subject:       str = "Physics"
    exam:          str = "JEE Main"
    user_answer:   Optional[str] = None
    follow_up:     Optional[str] = None  # user's "Ask AI" follow-up question


@router.post("/explain")
async def explain_question(
    req: ExplainRequest,
    user=Depends(get_current_user),
):
    """
    Generate AI step-by-step explanation for a JEE/NEET/CUET question.
    Uses the question text + optional user answer + follow-up question.
    Returns structured explanation with correct answer, working, and JEE tip.
    """
    settings = get_effective_settings()

    if req.follow_up:
        prompt = f"""You are an expert {req.exam} tutor. A student is asking about this {req.subject} question:

QUESTION: {req.question_text}

STUDENT'S FOLLOW-UP QUESTION: {req.follow_up}

Answer the follow-up question clearly and concisely. If it involves calculation, show each step.
Keep the answer under 150 words. Use plain English — no LaTeX."""
    else:
        answer_context = f"\nSTUDENT SELECTED: {req.user_answer}" if req.user_answer else ""
        prompt = f"""You are an expert {req.exam} tutor helping a student prepare for the exam.

QUESTION ({req.subject}): {req.question_text}{answer_context}

Provide a clear step-by-step solution. Format your response EXACTLY as:

CORRECT_ANSWER: [state the correct answer value or option]

SOLUTION:
[numbered steps showing the working — max 5 steps, each under 30 words]

JEE_TIP: [one practical exam strategy tip for this type of question — max 25 words]

Keep everything concise. Use plain text, not LaTeX."""

    try:
        # get_current_user returns a Supabase auth user object
        username = getattr(user, "email", None) or "student"
        response = await ask_llm(
            prompt=prompt,
            username=username,
            feature="exam_prep",
            grade="Grade 12",
            max_tokens=300,
        )
        raw = response.get("content", "").strip()
    except Exception as exc:
        _log.error("exam_prep.explain failed", error=str(exc))
        raise HTTPException(500, "AI explanation failed") from exc

    # Parse structured response
    correct_answer = ""
    solution = ""
    tip = ""

    lines = raw.split("\n")
    section = None
    solution_lines = []

    for line in lines:
        line = line.strip()
        if line.startswith("CORRECT_ANSWER:"):
            correct_answer = line.replace("CORRECT_ANSWER:", "").strip()
        elif line.startswith("SOLUTION:"):
            section = "solution"
        elif line.startswith("JEE_TIP:"):
            tip = line.replace("JEE_TIP:", "").strip()
            section = None
        elif section == "solution" and line:
            solution_lines.append(line)

    solution = "\n".join(solution_lines)

    # Fallback: if parsing failed, return the raw text
    if not solution:
        solution = raw

    _log.info(
        "exam_prep.explain",
        subject=req.subject,
        exam=req.exam,
        user=getattr(user, "email", "unknown"),
    )

    return {
        "success":        True,
        "correct_answer": correct_answer,
        "solution":       solution,
        "tip":            tip,
        "raw":            raw,
    }
