#!/usr/bin/env python3
"""
Grade 5 Lesson Content PDF Generator
======================================
Generates one PDF/HTML report per subject for Grade 5, covering:

  • All chapters and lesson steps (What We Learn / Worked Examples / Recap)
  • Full lesson content from lesson_cache, styled with Option A card colours
  • RAG coverage flags — chapters where source material is missing
  • All LKB (Lesson Knowledge Base) chips per step with quality rating
  • All DKB (Doubt Knowledge Base) Q&A entries per chapter with quality rating

Output (one file per subject):
  reports/grade5_lessons/Grade5_English.html
  reports/grade5_lessons/Grade5_Maths.html
  reports/grade5_lessons/Grade5_EVS.html
  reports/grade5_lessons/Grade5_Hindi.html

Run:
    cd backend
    python3 scripts/generate_grade5_lesson_pdfs.py
    python3 scripts/generate_grade5_lesson_pdfs.py --subject English
    python3 scripts/generate_grade5_lesson_pdfs.py --pdf          # also convert to PDF
"""
from __future__ import annotations

import argparse
import html as _html
import json
import logging
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.auth_service import admin_client  # noqa: E402
from app.services.grade_db_router import get_content_db  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
_log = logging.getLogger("grade5_pdf")

GRADE = "Grade 5"
LESSON_STEPS = ["What We Learn", "Worked Examples", "Recap"]

# ── Card colours (matching Option A mockup) ───────────────────────────────────
STEP_COLOURS = {
    "What We Learn":  {"bg": "#eff6ff", "border": "#bfdbfe", "icon": "🎯", "tag": "Introduction"},
    "Worked Examples":{"bg": "#f0fdf4", "border": "#86efac", "icon": "🧪", "tag": "Examples"},
    "Recap":          {"bg": "#faf5ff", "border": "#d8b4fe", "icon": "📌", "tag": "Summary"},
}
WARN_STYLE = {"bg": "#fff7ed", "border": "#fdba74", "icon": "⚠️"}
QA_COLOURS = {
    "lkb": {"bg": "#eff6ff", "border": "#bfdbfe", "label": "LKB Chip", "icon": "💡"},
    "dkb": {"bg": "#f0fdf4", "border": "#86efac", "label": "DKB Q&A", "icon": "💬"},
}
RATING_COLOURS = {
    5: "#16a34a", 4: "#65a30d", 3: "#ca8a04", 2: "#dc2626", 1: "#9f1239",
}


# ── Data fetching ─────────────────────────────────────────────────────────────

def fetch_lesson_cache(grade: str) -> list[dict]:
    """Fetch all active lesson steps for a grade, ordered by subject → chapter → step."""
    db = get_content_db(grade)
    try:
        resp = (
            db.table("lesson_cache")
            .select("id, grade, subject, chapter, step_title, lesson_content, status, access_count, created_at")
            .eq("grade", grade)
            .eq("status", "active")
            .order("subject")
            .order("chapter")
            .order("step_title")
            .limit(2000)
            .execute()
        )
        return resp.data or []
    except Exception as exc:
        _log.error("Failed to fetch lesson_cache: %s", exc)
        return []


def fetch_lkb_chips(grade: str) -> list[dict]:
    """Fetch all active LKB chips for a grade."""
    db = get_content_db(grade)
    try:
        resp = (
            db.table("lesson_kb")
            .select("id, grade, subject, chapter, step_title, question, answer, hit_count, source, created_at")
            .eq("grade", grade)
            .eq("status", "active")
            .order("subject")
            .order("chapter")
            .order("step_title")
            .order("hit_count", desc=True)
            .limit(5000)
            .execute()
        )
        return resp.data or []
    except Exception as exc:
        _log.error("Failed to fetch lesson_kb: %s", exc)
        return []


def fetch_dkb_entries(grade: str) -> list[dict]:
    """Fetch all active DKB entries for a grade."""
    db = get_content_db(grade)
    try:
        resp = (
            db.table("doubt_kb")
            .select("id, grade, subject, chapter, question, answer, hit_count, source, created_at")
            .eq("grade", grade)
            .eq("status", "active")
            .order("subject")
            .order("chapter")
            .order("hit_count", desc=True)
            .limit(5000)
            .execute()
        )
        return resp.data or []
    except Exception as exc:
        _log.error("Failed to fetch doubt_kb: %s", exc)
        return []


def fetch_rag_documents(grade: str) -> list[dict]:
    """Fetch all RAG documents (chapter source materials) for a grade."""
    db = get_content_db(grade)
    try:
        resp = (
            db.table("rag_documents")
            .select("id, grade, subject, chapter, title, source_type, created_at")
            .eq("grade", grade)
            .order("subject")
            .order("chapter")
            .execute()
        )
        return resp.data or []
    except Exception as exc:
        _log.warning("Failed to fetch rag_documents: %s", exc)
        return []


def fetch_rag_chunk_counts(grade: str, rag_docs: list[dict]) -> dict[str, int]:
    """Return {doc_id: chunk_count} for all RAG docs. Avoids N+1 by batching."""
    db = get_content_db(grade)
    counts: dict[str, int] = {}
    # Batch in groups of 50
    doc_ids = [d["id"] for d in rag_docs if d.get("id")]
    for i in range(0, len(doc_ids), 50):
        batch = doc_ids[i:i + 50]
        try:
            resp = (
                db.table("rag_chunks")
                .select("document_id", count="exact")
                .in_("document_id", batch)
                .execute()
            )
            # Supabase doesn't group-count directly, so count per doc
            for doc_id in batch:
                c_resp = (
                    db.table("rag_chunks")
                    .select("id", count="exact")
                    .eq("document_id", doc_id)
                    .execute()
                )
                counts[doc_id] = c_resp.count or 0
        except Exception as exc:
            _log.debug("Chunk count batch failed: %s", exc)
    return counts


# ── Quality assessment ────────────────────────────────────────────────────────

def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def rate_question(question: str, chapter: str, subject: str) -> tuple[int, str]:
    """
    Rate a Q&A question 1–5 with reasoning.

    Criteria:
    1. Length (10–120 chars) — too short = vague, too long = unwieldy
    2. Contains a question word (what, why, how, when, where, who, define, explain)
    3. Specific to chapter (mentions chapter keywords or subject terms)
    4. Not a generic study-tip question
    5. Ends with '?'
    """
    q = _clean(question)
    score = 5
    issues = []

    if len(q) < 10:
        score -= 3; issues.append("Too short — not a real question")
    elif len(q) > 150:
        score -= 1; issues.append("Very long question — could be trimmed")

    q_lower = q.lower()
    if not re.search(r"\b(what|why|how|when|where|who|define|explain|describe|state|list|give|name|write)\b", q_lower):
        score -= 1; issues.append("No question word detected")

    if not q.endswith("?"):
        score -= 1; issues.append("Does not end with '?'")

    generic_phrases = ["study tips", "how to study", "how to score", "exam tips", "revision"]
    if any(p in q_lower for p in generic_phrases):
        score -= 2; issues.append("Generic study-tip question — not chapter-specific")

    # Bonus: references chapter keywords
    ch_words = [w.lower() for w in re.split(r"\W+", chapter) if len(w) >= 4]
    if any(w in q_lower for w in ch_words[:3]):
        pass  # specific — good, keep score
    else:
        score -= 1; issues.append("Question does not reference chapter content directly")

    score = max(1, min(5, score))
    reason = "; ".join(issues) if issues else "Well-formed, specific question"
    return score, reason


def rate_answer(answer: str, question: str) -> tuple[int, str]:
    """
    Rate an answer 1–5 with reasoning.

    Criteria:
    1. Length (50–2000 chars)
    2. Structured (bullets, numbered list, or multiple sentences)
    3. Contains factual terms (not just vague phrases)
    4. Directly responds to question type (definition/why/how)
    5. Not an error message or placeholder
    """
    a = _clean(answer)
    score = 5
    issues = []

    if len(a) < 30:
        score -= 4; issues.append("Answer too short — likely empty or error")
        return max(1, score), "; ".join(issues)

    if len(a) < 80:
        score -= 2; issues.append("Very brief — may lack sufficient explanation")
    elif len(a) > 3000:
        score -= 1; issues.append("Very long — may include unnecessary content")

    a_lower = a.lower()

    # Check for structure (bullets or multiple sentences)
    has_bullets = "- " in a or "• " in a or "\n" in a
    sentence_count = len(re.findall(r"[.!?]", a))
    if not has_bullets and sentence_count < 2:
        score -= 1; issues.append("Answer lacks structure — single sentence or no bullets")

    # Error/placeholder patterns
    error_phrases = ["could not", "unable to", "i don't know", "no answer", "error", "failed"]
    if any(p in a_lower for p in error_phrases):
        score -= 3; issues.append("Answer appears to be an error message or placeholder")

    # Factual content check
    factual_patterns = r"\b(is|are|was|were|means|defined|called|refers|process|example|because|therefore)\b"
    if not re.search(factual_patterns, a_lower):
        score -= 1; issues.append("Answer may lack factual content")

    score = max(1, min(5, score))
    reason = "; ".join(issues) if issues else "Well-structured, appropriately detailed answer"
    return score, reason


def overall_qa_rating(q_score: int, a_score: int) -> int:
    return round((q_score * 0.4 + a_score * 0.6))


def rating_label(score: int) -> str:
    return {5: "Excellent", 4: "Good", 3: "Average", 2: "Poor", 1: "Very Poor"}.get(score, "Unknown")


# ── RAG coverage analysis ─────────────────────────────────────────────────────

def build_rag_index(rag_docs: list[dict], chunk_counts: dict) -> dict[str, dict]:
    """
    Build a map: (subject_lower, chapter_lower) → {doc_id, chunk_count, has_content}.
    """
    index: dict[str, dict] = {}
    for doc in rag_docs:
        subj = (doc.get("subject") or "").lower().strip()
        ch = (doc.get("chapter") or "").lower().strip()
        doc_id = doc.get("id", "")
        chunks = chunk_counts.get(doc_id, 0) or chunk_counts.get(str(doc_id), 0)
        key = f"{subj}||{ch}"
        if key not in index or chunks > index[key]["chunk_count"]:
            index[key] = {
                "doc_id": doc_id,
                "chunk_count": chunks,
                "has_content": chunks > 0,
                "title": doc.get("title", ""),
            }
    return index


def check_rag_coverage(subject: str, chapter: str, rag_index: dict) -> tuple[bool, int, str]:
    """
    Check if a chapter has RAG source material.
    Returns (has_rag: bool, chunk_count: int, flag_message: str).
    """
    subj_l = subject.lower().strip()
    ch_l = chapter.lower().strip()
    key = f"{subj_l}||{ch_l}"

    # Exact match
    if key in rag_index:
        entry = rag_index[key]
        if entry["has_content"]:
            return True, entry["chunk_count"], ""
        return False, 0, "RAG document exists but has 0 chunks — upload may have failed"

    # Fuzzy: chapter name contained in key
    ch_words = [w for w in re.split(r"\W+", ch_l) if len(w) >= 4]
    for idx_key, entry in rag_index.items():
        idx_subj, idx_ch = idx_key.split("||", 1)
        if idx_subj == subj_l and ch_words and all(w in idx_ch for w in ch_words[:2]):
            if entry["has_content"]:
                return True, entry["chunk_count"], ""
            return False, 0, "Fuzzy match found but 0 chunks"

    return False, 0, "No RAG source material found — lesson is AI-only (not grounded in textbook)"


# ── HTML generation ───────────────────────────────────────────────────────────

def esc(text: str) -> str:
    return _html.escape(str(text or ""), quote=True)


def markdown_to_html(text: str) -> str:
    """Minimal markdown → HTML: bold, italic, bullets, headings, line breaks."""
    t = esc(text)
    # Headings
    t = re.sub(r"^###\s+(.+)$", r"<h4>\1</h4>", t, flags=re.MULTILINE)
    t = re.sub(r"^##\s+(.+)$", r"<h3>\1</h3>", t, flags=re.MULTILINE)
    t = re.sub(r"^#\s+(.+)$", r"<h2>\1</h2>", t, flags=re.MULTILINE)
    # Bold
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    # Italic
    t = re.sub(r"\*(.+?)\*", r"<em>\1</em>", t)
    # Bullet lines
    lines = t.split("\n")
    out_lines = []
    in_ul = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- ") or stripped.startswith("• "):
            if not in_ul:
                out_lines.append("<ul>")
                in_ul = True
            out_lines.append(f"<li>{stripped[2:]}</li>")
        else:
            if in_ul:
                out_lines.append("</ul>")
                in_ul = False
            if stripped:
                out_lines.append(f"<p>{stripped}</p>")
            else:
                out_lines.append("")
    if in_ul:
        out_lines.append("</ul>")
    return "\n".join(out_lines)


def rating_badge(score: int) -> str:
    colour = RATING_COLOURS.get(score, "#6b7280")
    label = rating_label(score)
    return (
        f'<span style="background:{colour};color:#fff;border-radius:99px;'
        f'padding:2px 10px;font-size:.7rem;font-weight:700;white-space:nowrap">'
        f"★ {score}/5 — {label}</span>"
    )


def stars(score: int) -> str:
    return "★" * score + "☆" * (5 - score)


def css() -> str:
    return """
    <style>
    *{box-sizing:border-box;margin:0;padding:0}
    body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
         background:#f3f4f6;color:#111827;font-size:14px;line-height:1.6}
    .page-wrap{max-width:900px;margin:0 auto;padding:24px 20px 60px}
    /* Subject header */
    .subject-header{background:linear-gradient(135deg,#4f46e5,#7c3aed);color:#fff;
                    border-radius:16px;padding:28px 32px;margin-bottom:28px}
    .subject-header .eyebrow{font-size:.7rem;text-transform:uppercase;letter-spacing:.1em;opacity:.75;margin-bottom:4px}
    .subject-header h1{font-size:1.6rem;font-weight:900;margin-bottom:6px}
    .subject-header .meta{font-size:.82rem;opacity:.75}
    .subject-header .stats{display:flex;gap:16px;margin-top:14px;flex-wrap:wrap}
    .subject-header .stat{background:rgba(255,255,255,.15);border-radius:8px;
                          padding:6px 14px;font-size:.78rem;font-weight:600}
    /* Chapter block */
    .chapter-block{background:#fff;border-radius:14px;border:1px solid #e5e7eb;
                   margin-bottom:24px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.06)}
    .chapter-header{padding:16px 20px;background:#f8f9fa;border-bottom:1px solid #e5e7eb;
                    display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px}
    .chapter-title{font-size:1rem;font-weight:800;color:#111827}
    .chapter-meta{font-size:.72rem;color:#6b7280;display:flex;gap:8px;flex-wrap:wrap}
    .chapter-meta span{background:#f3f4f6;border-radius:99px;padding:2px 9px}
    /* RAG flag */
    .rag-flag{margin:12px 20px 0;padding:10px 14px;background:#fff7ed;border:1px solid #fdba74;
              border-radius:9px;font-size:.78rem;color:#92400e;display:flex;gap:8px;align-items:flex-start}
    .rag-flag.ok{background:#f0fdf4;border-color:#86efac;color:#14532d}
    .rag-flag .flag-icon{flex-shrink:0;font-size:1rem}
    /* Lesson step card */
    .step-card{margin:14px 20px;border-radius:12px;padding:16px 18px;border:1.5px solid}
    .step-card h3{font-size:.88rem;font-weight:700;color:#111827;margin-bottom:10px;
                  display:flex;align-items:center;gap:7px}
    .step-card .step-tag{font-size:.62rem;text-transform:uppercase;letter-spacing:.09em;
                         color:#6b7280;font-weight:700;margin-left:auto}
    .step-card .lesson-body{font-size:.85rem;line-height:1.7;color:#374151}
    .step-card .lesson-body h2,.step-card .lesson-body h3,.step-card .lesson-body h4{
        font-size:.9rem;font-weight:700;color:#111827;margin:10px 0 4px}
    .step-card .lesson-body p{margin-bottom:6px}
    .step-card .lesson-body ul{padding-left:1.3em;margin-bottom:6px}
    .step-card .lesson-body li{margin-bottom:3px}
    .step-card .lesson-body strong{color:#111827}
    .missing-badge{display:inline-block;background:#fee2e2;color:#991b1b;border-radius:6px;
                   padding:3px 10px;font-size:.7rem;font-weight:700;margin-bottom:8px}
    /* Q&A section */
    .qa-section{margin:14px 20px 20px;border-top:2px dashed #f3f4f6;padding-top:14px}
    .qa-section-title{font-size:.78rem;font-weight:700;text-transform:uppercase;
                      letter-spacing:.09em;color:#6b7280;margin-bottom:10px}
    .qa-item{border-radius:10px;padding:12px 14px;margin-bottom:10px;border:1px solid}
    .qa-item .qa-header{display:flex;align-items:flex-start;gap:8px;margin-bottom:8px;flex-wrap:wrap}
    .qa-item .qa-icon{font-size:1rem;flex-shrink:0}
    .qa-item .qa-label{font-size:.62rem;text-transform:uppercase;letter-spacing:.09em;
                       font-weight:700;color:#6b7280;margin-right:auto}
    .qa-item .qa-hits{font-size:.68rem;color:#9ca3af}
    .qa-item .qa-q{font-size:.86rem;font-weight:700;color:#111827;margin-bottom:6px}
    .qa-item .qa-a{font-size:.83rem;color:#374151;line-height:1.6}
    .qa-item .qa-a ul{padding-left:1.3em;margin-top:4px}
    .qa-item .qa-a li{margin-bottom:3px}
    .qa-item .qa-rating{margin-top:8px;display:flex;align-items:center;gap:8px;flex-wrap:wrap}
    .qa-item .qa-reason{font-size:.72rem;color:#6b7280;font-style:italic;margin-top:3px}
    /* Summary table */
    .summary-table{width:100%;border-collapse:collapse;margin:14px 20px 20px;
                   width:calc(100% - 40px);font-size:.8rem}
    .summary-table th{text-align:left;padding:7px 10px;background:#f8f9fa;color:#6b7280;
                      border-bottom:2px solid #e5e7eb;font-size:.7rem;text-transform:uppercase;letter-spacing:.07em}
    .summary-table td{padding:7px 10px;border-bottom:1px solid #f3f4f6;vertical-align:top}
    .summary-table tr:hover td{background:#f9fafb}
    /* Chapter separator */
    .chapter-sep{height:1px;background:#e5e7eb;margin:8px 20px}
    /* Page break for print */
    @media print{
        .chapter-block{break-inside:avoid;page-break-inside:avoid}
        body{background:#fff}
        .page-wrap{padding:12px}
    }
    /* TOC */
    .toc{background:#fff;border-radius:12px;border:1px solid #e5e7eb;padding:20px;
         margin-bottom:24px}
    .toc h2{font-size:.85rem;font-weight:700;text-transform:uppercase;letter-spacing:.08em;
            color:#6b7280;margin-bottom:12px}
    .toc ol{padding-left:1.4em}
    .toc li{margin-bottom:5px;font-size:.85rem}
    .toc a{color:#6366f1;text-decoration:none}
    .toc a:hover{text-decoration:underline}
    .toc .toc-meta{font-size:.72rem;color:#9ca3af;margin-left:6px}
    </style>
    """


def build_subject_html(
    subject: str,
    chapters_data: dict,       # chapter → {steps, lkb, dkb, rag_ok, rag_chunks, rag_flag}
    generated_at: str,
    grade: str = GRADE,
) -> str:
    """Build a complete HTML document for one subject."""
    total_chapters = len(chapters_data)
    total_steps = sum(
        sum(1 for s in d["steps"].values() if s)
        for d in chapters_data.values()
    )
    total_lkb = sum(len(d["lkb"]) for d in chapters_data.values())
    total_dkb = sum(len(d["dkb"]) for d in chapters_data.values())
    missing_rag = sum(1 for d in chapters_data.values() if not d["rag_ok"])

    # TOC
    toc_items = []
    for i, ch in enumerate(chapters_data.keys(), 1):
        d = chapters_data[ch]
        flag = " ⚠️" if not d["rag_ok"] else ""
        toc_items.append(
            f'<li><a href="#ch{i}">{esc(ch)}</a>'
            f'<span class="toc-meta">{len(d["lkb"])} LKB · {len(d["dkb"])} DKB{flag}</span></li>'
        )

    toc_html = f"""
    <div class="toc">
      <h2>📋 Table of Contents — {esc(subject)}</h2>
      <ol>{"".join(toc_items)}</ol>
    </div>"""

    # Chapter blocks
    chapter_blocks = []
    for i, (chapter, data) in enumerate(chapters_data.items(), 1):
        rag_ok = data["rag_ok"]
        rag_chunks = data["rag_chunks"]
        rag_flag_msg = data["rag_flag"]

        # RAG flag
        if rag_ok:
            rag_div = (
                f'<div class="rag-flag ok">'
                f'<span class="flag-icon">✅</span>'
                f'<span>RAG source material found — <strong>{rag_chunks} chunks</strong> indexed from textbook PDF.</span></div>'
            )
        else:
            rag_div = (
                f'<div class="rag-flag">'
                f'<span class="flag-icon">⚠️</span>'
                f'<span><strong>RAG MISSING:</strong> {esc(rag_flag_msg)} — '
                f'Lessons for this chapter are AI-generated without textbook grounding. '
                f'Accuracy and NCERT alignment cannot be guaranteed.</span></div>'
            )

        # Step cards
        step_cards = []
        steps = data["steps"]
        for step_title in LESSON_STEPS:
            content = steps.get(step_title, "")
            colours = STEP_COLOURS.get(step_title, {"bg": "#f9fafb", "border": "#e5e7eb", "icon": "📚", "tag": ""})
            if content:
                body_html = markdown_to_html(content[:4000])
                card_inner = (
                    f'<div class="lesson-body">{body_html}</div>'
                )
            else:
                card_inner = (
                    f'<span class="missing-badge">❌ MISSING — No lesson generated for this step</span>'
                    f'<p style="font-size:.82rem;color:#9ca3af">This step has not been generated yet in lesson_cache.</p>'
                )

            # LKB chips for this step
            step_lkb = [c for c in data["lkb"] if c.get("step_title") == step_title]
            lkb_html = ""
            if step_lkb:
                lkb_items = []
                for chip in step_lkb:
                    q = chip.get("question", "")
                    a = chip.get("answer", "")
                    hits = chip.get("hit_count", 0)
                    q_sc, q_rsn = rate_question(q, chapter, subject)
                    a_sc, a_rsn = rate_answer(a, q)
                    overall = overall_qa_rating(q_sc, a_sc)
                    lkb_items.append(
                        f'<div class="qa-item" style="background:#eff6ff;border-color:#bfdbfe">'
                        f'<div class="qa-header">'
                        f'<span class="qa-icon">💡</span>'
                        f'<span class="qa-label">LKB Chip · {esc(step_title)}</span>'
                        f'<span class="qa-hits">👁 {hits} hits</span>'
                        f'</div>'
                        f'<div class="qa-q">Q: {esc(q)}</div>'
                        f'<div class="qa-a">{markdown_to_html(a)}</div>'
                        f'<div class="qa-rating">'
                        f'<span style="font-size:.72rem;color:#6b7280">Q: {rating_badge(q_sc)} A: {rating_badge(a_sc)} Overall: {rating_badge(overall)}</span>'
                        f'</div>'
                        f'<div class="qa-reason">Q: {esc(q_rsn)} | A: {esc(a_rsn)}</div>'
                        f'</div>'
                    )
                lkb_html = (
                    f'<div style="margin-top:10px;padding:10px 0 0">'
                    f'<div style="font-size:.68rem;font-weight:700;text-transform:uppercase;letter-spacing:.09em;color:#1d4ed8;margin-bottom:8px">💡 LKB Chips for this step ({len(step_lkb)})</div>'
                    + "".join(lkb_items)
                    + "</div>"
                )

            step_cards.append(
                f'<div class="step-card" style="background:{colours["bg"]};border-color:{colours["border"]}">'
                f'<h3><span>{colours["icon"]}</span> {esc(step_title)}'
                f'<span class="step-tag">{colours["tag"]}</span></h3>'
                + card_inner
                + lkb_html
                + "</div>"
            )

        # DKB section for this chapter
        dkb_items_html = []
        for entry in data["dkb"]:
            q = entry.get("question", "")
            a = entry.get("answer", "")
            hits = entry.get("hit_count", 0)
            source = entry.get("source", "")
            q_sc, q_rsn = rate_question(q, chapter, subject)
            a_sc, a_rsn = rate_answer(a, q)
            overall = overall_qa_rating(q_sc, a_sc)
            src_badge = (
                '<span style="font-size:.65rem;background:#dcfce7;color:#14532d;'
                'border-radius:4px;padding:1px 6px;font-weight:700">prewarmed</span>'
                if source == "prewarmed" else
                '<span style="font-size:.65rem;background:#fef3c7;color:#92400e;'
                'border-radius:4px;padding:1px 6px;font-weight:700">AI-generated</span>'
            )
            dkb_items_html.append(
                f'<div class="qa-item" style="background:#f0fdf4;border-color:#86efac">'
                f'<div class="qa-header">'
                f'<span class="qa-icon">💬</span>'
                f'<span class="qa-label">DKB Entry {src_badge}</span>'
                f'<span class="qa-hits">👁 {hits} hits</span>'
                f'</div>'
                f'<div class="qa-q">Q: {esc(q)}</div>'
                f'<div class="qa-a">{markdown_to_html(a)}</div>'
                f'<div class="qa-rating">'
                f'<span style="font-size:.72rem;color:#6b7280">Q: {rating_badge(q_sc)} A: {rating_badge(a_sc)} Overall: {rating_badge(overall)}</span>'
                f'</div>'
                f'<div class="qa-reason">Q: {esc(q_rsn)} | A: {esc(a_rsn)}</div>'
                f'</div>'
            )

        dkb_section = ""
        if dkb_items_html:
            dkb_section = (
                f'<div class="qa-section">'
                f'<div class="qa-section-title">💬 DKB Q&A Entries for this chapter ({len(dkb_items_html)})</div>'
                + "".join(dkb_items_html)
                + "</div>"
            )
        elif not dkb_items_html:
            dkb_section = (
                '<div class="qa-section">'
                '<div class="qa-section-title">💬 DKB Q&A</div>'
                '<p style="font-size:.8rem;color:#9ca3af;padding:8px 0">No DKB entries found for this chapter.</p>'
                '</div>'
            )

        # LKB per-chapter summary
        lkb_count = len(data["lkb"])
        expected_lkb = len(LESSON_STEPS) * 5
        lkb_status = "✅" if lkb_count >= expected_lkb else f"⚠️ Only {lkb_count}/{expected_lkb}"

        chapter_blocks.append(
            f'<div class="chapter-block" id="ch{i}">'
            f'<div class="chapter-header">'
            f'<div class="chapter-title">📖 {esc(chapter)}</div>'
            f'<div class="chapter-meta">'
            f'<span>{"✅ RAG" if rag_ok else "⚠️ No RAG"} ({rag_chunks} chunks)</span>'
            f'<span>LKB: {lkb_status}</span>'
            f'<span>DKB: {len(data["dkb"])} entries</span>'
            f'</div></div>'
            + rag_div
            + "".join(step_cards)
            + dkb_section
            + "</div>"
        )

    # Stats header
    header_html = f"""
    <div class="subject-header">
      <div class="eyebrow">Grade 5 · CBSE · Lesson Content Report</div>
      <h1>📚 {esc(subject)}</h1>
      <div class="meta">Generated {generated_at} · Read-only audit report</div>
      <div class="stats">
        <div class="stat">📖 {total_chapters} chapters</div>
        <div class="stat">📝 {total_steps} lesson steps cached</div>
        <div class="stat">💡 {total_lkb} LKB chips</div>
        <div class="stat">💬 {total_dkb} DKB entries</div>
        <div class="stat">{"⚠️ " + str(missing_rag) + " chapters missing RAG" if missing_rag else "✅ RAG coverage OK"}</div>
      </div>
    </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Grade 5 {esc(subject)} — Lesson Content Report</title>
{css()}
</head>
<body>
<div class="page-wrap">
{header_html}
{toc_html}
{"".join(chapter_blocks)}
<div style="margin-top:32px;padding:16px;background:#1e293b;color:#94a3b8;border-radius:12px;font-size:.75rem;text-align:center">
  Generated by generate_grade5_lesson_pdfs.py · {generated_at} · Likha Poha Platform QA
</div>
</div>
</body>
</html>"""


# ── Main orchestration ────────────────────────────────────────────────────────

def build_chapters_data(
    subject: str,
    lessons: list[dict],
    lkb_all: list[dict],
    dkb_all: list[dict],
    rag_index: dict,
) -> dict:
    """Organise all data for one subject into a chapters dict."""
    # Filter to subject
    subj_lessons = [r for r in lessons if r.get("subject") == subject]
    subj_lkb = [r for r in lkb_all if r.get("subject") == subject]
    subj_dkb = [r for r in dkb_all if r.get("subject") == subject]

    # Collect all chapters from lessons
    chapters: dict[str, dict] = {}
    for row in subj_lessons:
        ch = row.get("chapter", "Unknown")
        if ch not in chapters:
            rag_ok, rag_chunks, rag_flag = check_rag_coverage(subject, ch, rag_index)
            chapters[ch] = {
                "steps": {},
                "lkb": [],
                "dkb": [],
                "rag_ok": rag_ok,
                "rag_chunks": rag_chunks,
                "rag_flag": rag_flag,
            }
        step = row.get("step_title", "")
        if step:
            chapters[ch]["steps"][step] = row.get("lesson_content", "")

    # Assign LKB chips
    for chip in subj_lkb:
        ch = chip.get("chapter", "")
        if ch in chapters:
            chapters[ch]["lkb"].append(chip)

    # Assign DKB entries
    for entry in subj_dkb:
        ch = entry.get("chapter", "")
        # Try exact match first
        if ch in chapters:
            chapters[ch]["dkb"].append(entry)
        else:
            # Fuzzy: find best chapter match
            ch_l = ch.lower()
            for known_ch in chapters:
                kc_l = known_ch.lower()
                if ch_l in kc_l or kc_l in ch_l:
                    chapters[known_ch]["dkb"].append(entry)
                    break

    return chapters


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Grade 5 lesson content HTML reports")
    parser.add_argument("--subject", help="Generate for one subject only (e.g. English)")
    parser.add_argument("--pdf", action="store_true", help="Also convert HTML to PDF via weasyprint")
    parser.add_argument("--output", default="reports/grade5_lessons", help="Output directory")
    args = parser.parse_args()

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    _log.info("Fetching Grade 5 data from Supabase...")

    lessons = fetch_lesson_cache(GRADE)
    _log.info("  lesson_cache: %d rows", len(lessons))

    lkb_all = fetch_lkb_chips(GRADE)
    _log.info("  lesson_kb:    %d chips", len(lkb_all))

    dkb_all = fetch_dkb_entries(GRADE)
    _log.info("  doubt_kb:     %d entries", len(dkb_all))

    rag_docs = fetch_rag_documents(GRADE)
    _log.info("  rag_documents:%d docs", len(rag_docs))

    _log.info("Counting RAG chunks (this may take 30-60s)...")
    chunk_counts = fetch_rag_chunk_counts(GRADE, rag_docs)
    rag_index = build_rag_index(rag_docs, chunk_counts)
    _log.info("  RAG index built: %d entries", len(rag_index))

    # Discover subjects
    all_subjects = sorted(set(r.get("subject", "") for r in lessons if r.get("subject")))
    if args.subject:
        subjects = [s for s in all_subjects if args.subject.lower() in s.lower()]
        if not subjects:
            _log.error("Subject '%s' not found. Available: %s", args.subject, all_subjects)
            sys.exit(1)
    else:
        subjects = all_subjects

    _log.info("Subjects to generate: %s", subjects)

    for subject in subjects:
        _log.info("Building report for %s...", subject)
        chapters_data = build_chapters_data(subject, lessons, lkb_all, dkb_all, rag_index)
        html_content = build_subject_html(subject, chapters_data, generated_at)

        safe_name = re.sub(r"[^\w\s-]", "", subject).replace(" ", "_")
        html_path = out_dir / f"Grade5_{safe_name}.html"
        html_path.write_text(html_content, encoding="utf-8")
        _log.info("  HTML saved: %s", html_path)

        if args.pdf:
            try:
                import weasyprint  # noqa: PLC0415
                pdf_path = out_dir / f"Grade5_{safe_name}.pdf"
                weasyprint.HTML(filename=str(html_path)).write_pdf(str(pdf_path))
                _log.info("  PDF  saved: %s", pdf_path)
            except ImportError:
                _log.warning("  weasyprint not installed — skipping PDF conversion.")
                _log.warning("  Install with: pip install weasyprint")
                _log.warning("  Or open the HTML in Chrome and use File → Print → Save as PDF")
            except Exception as exc:
                _log.warning("  PDF conversion failed: %s", exc)

    # Print summary
    sep = "=" * 65
    print()
    print(sep)
    print("  GRADE 5 LESSON REPORT GENERATION COMPLETE")
    print(sep)
    for subject in subjects:
        safe_name = re.sub(r"[^\w\s-]", "", subject).replace(" ", "_")
        html_path = out_dir / f"Grade5_{safe_name}.html"
        size_kb = round(html_path.stat().st_size / 1024) if html_path.exists() else 0
        print(f"  {subject:<22} → {html_path.name}  ({size_kb} KB)")
    print(f"  Output directory : {out_dir.resolve()}")
    print(sep)
    print()
    print("  To view: open the HTML files in Chrome, then")
    print("  File -> Print -> Save as PDF (for best results)")
    print()


if __name__ == "__main__":
    main()
