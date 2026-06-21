"""
Public chatbot endpoint — no authentication required.
Answers visitor questions about the LikhaPoha AI platform using a
pre-built FAQ knowledge base. Falls back to LLM with platform context
if no FAQ match is found.

Rate limited: 10 requests per minute per IP to prevent abuse.
"""
from __future__ import annotations

import time
from collections import defaultdict
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.services.chatbot_service import answer_chatbot_question

router = APIRouter()

# ── Simple in-memory rate limiter (resets on server restart) ──────────────────
_ip_requests: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT = 10       # max requests
RATE_WINDOW = 60.0    # per 60 seconds


def _check_rate_limit(ip: str) -> None:
    now = time.time()
    window_start = now - RATE_WINDOW
    # Remove old entries
    _ip_requests[ip] = [t for t in _ip_requests[ip] if t > window_start]
    if len(_ip_requests[ip]) >= RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please wait a moment before asking again.",
        )
    _ip_requests[ip].append(now)


class ChatRequest(BaseModel):
    question: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    answer: str
    source: str   # "faq" | "llm"
    suggestions: list[str] = []


@router.post("", response_model=ChatResponse)
async def chatbot(request: Request, body: ChatRequest) -> ChatResponse:
    """Answer a visitor question about the LikhaPoha AI platform."""
    ip = request.client.host if request.client else "unknown"
    _check_rate_limit(ip)

    question = (body.question or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    if len(question) > 500:
        raise HTTPException(status_code=400, detail="Question too long (max 500 characters).")

    result = answer_chatbot_question(question)
    return ChatResponse(
        answer=result["answer"],
        source=result["source"],
        suggestions=result.get("suggestions", []),
    )
