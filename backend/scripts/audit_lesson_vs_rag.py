#!/usr/bin/env python3
"""
Lesson vs RAG Audit — Grade 5
==============================
Compares generated lesson content in lesson_cache against the source
textbook content in rag_chunks for every Grade 5 chapter and step.

Identifies:
  • Steps with good RAG coverage (lesson text closely reflects source)
  • Steps with poor coverage (lesson misses key concepts from textbook)
  • Steps where RAG wasn't used at all (LLM hallucination risk)
  • RAG chunks whose key concepts are absent from the lesson

Output:
  reports/lesson_rag_audit/lesson_rag_audit.md
  reports/lesson_rag_audit/lesson_rag_audit.csv

Run:
    cd backend
    python3 scripts/audit_lesson_vs_rag.py
    python3 scripts/audit_lesson_vs_rag.py --subject English
    python3 scripts/audit_lesson_vs_rag.py --grade 5 --subject Maths
"""
from __future__ import annotations

import argparse
import collections
import csv
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.grade_db_router import get_content_db

GRADE = "Grade 5"
LESSON_STEPS_G5 = ["What We Learn", "Worked Examples", "Recap"]


# ── Text utilities ────────────────────────────────────────────────────────────

def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip()).lower()


def word_freq(text: str) -> collections.Counter:
    return collections.Counter(re.findall(r"\b[a-z]{3,}\b", normalize(text)))


def cosine_sim(text_a: str, text_b: str) -> float:
    fa, fb = word_freq(text_a), word_freq(text_b)
    if not fa or not fb:
        return 0.0
    vocab = set(fa) | set(fb)
    va = [fa.get(w, 0) for w in vocab]
    vb = [fb.get(w, 0) for w in vocab]
    dot = sum(a * b for a, b in zip(va, vb))
    mag_a = math.sqrt(sum(a * a for a in va))
    mag_b = math.sqrt(sum(b * b for b in vb))
    return dot / (mag_a * mag_b) if mag_a and mag_b else 0.0


def key_terms(text: str, top_n: int = 15) -> list[str]:
    """Extract most distinctive content words (TF-based, exclude stopwords)."""
    stopwords = {
        "the","a","an","is","are","was","were","be","been","being","have","has","had",
        "do","does","did","will","would","could","should","may","might","shall","can",
        "not","and","or","but","if","in","on","at","to","for","of","with","by",
        "from","up","about","into","through","during","before","after","this","that",
        "these","those","it","its","their","they","them","we","our","you","your",
        "what","which","who","when","where","how","why","also","so","then","than",
        "each","all","both","any","more","most","other","such","even","just","very",
        "only","well","still","here","there","some","many","much","every","one","two",
    }
    freq = word_freq(text)
    filtered = [(w, c) for w, c in freq.items() if w not in stopwords and len(w) >= 4]
    return [w for w, _ in sorted(filtered, key=lambda x: -x[1])[:top_n]]


def coverage_pct(rag_terms: list[str], lesson_text: str) -> float:
    """% of key RAG terms that appear in the lesson."""
    if not rag_terms:
        return 100.0
    lesson_lower = normalize(lesson_text)
    found = sum(1 for t in rag_terms if t in lesson_lower)
    return round(found / len(rag_terms) * 100, 1)


def missing_terms(rag_terms: list[str], lesson_text: str) -> list[str]:
    lesson_lower = normalize(lesson_text)
    return [t for t in rag_terms if t not in lesson_lower]


# ── Data fetching ─────────────────────────────────────────────────────────────

def fetch_lessons(grade: str, subject: str | None = None) -> list[dict]:
    db = get_content_db(grade)
    q = (db.table("lesson_cache")
         .select("id, grade, subject, chapter, step_title, lesson_content, created_at")
         .eq("grade", grade).eq("status", "active"))
    if subject:
        q = q.eq("subject", subject)
    return (q.order("subject").order("chapter").order("step_title").limit(2000).execute().data or [])


def fetch_rag_chunks_for_chapter(grade: str, subject: str, chapter: str) -> list[dict]:
    """Fetch all RAG chunks for a chapter via rag_documents join."""
    db = get_content_db(grade)
    # Find rag_document ID(s) for this chapter
    docs = (db.table("rag_documents")
            .select("id, chapter")
            .eq("grade", grade).eq("subject", subject)
            .execute().data or [])
    
    # Match by exact or fuzzy chapter name
    ch_lower = chapter.lower()
    ch_words = [w for w in re.split(r"\W+", ch_lower) if len(w) >= 4]
    matching_ids = []
    for doc in docs:
        doc_ch = (doc.get("chapter") or "").lower()
        if doc_ch == ch_lower:
            matching_ids.append(doc["id"])
        elif ch_words and all(w in doc_ch for w in ch_words[:2]):
            matching_ids.append(doc["id"])
    
    if not matching_ids:
        return []
    
    chunks = []
    for doc_id in matching_ids:
        resp = (db.table("rag_chunks")
                .select("chunk_index, chunk_text")
                .eq("document_id", doc_id)
                .order("chunk_index")
                .execute().data or [])
        chunks.extend(resp)
    return chunks


# ── Audit logic ───────────────────────────────────────────────────────────────

def audit_step(
    lesson_row: dict,
    rag_chunks: list[dict],
) -> dict:
    chapter = lesson_row.get("chapter", "")
    step = lesson_row.get("step_title", "")
    lesson_text = lesson_row.get("lesson_content", "")
    rag_text = " ".join(c.get("chunk_text", "") for c in rag_chunks)

    lesson_words = len(lesson_text.split())
    rag_words = len(rag_text.split())

    if not rag_text:
        return {
            "chapter": chapter, "step": step,
            "lesson_words": lesson_words, "rag_words": 0,
            "cosine": 0.0, "term_coverage_pct": None,
            "missing_terms": [], "rag_available": False,
            "status": "NO_RAG", "notes": "No RAG chunks found for this chapter.",
        }

    cos = cosine_sim(lesson_text, rag_text)
    rag_kw = key_terms(rag_text, top_n=20)
    cov = coverage_pct(rag_kw, lesson_text)
    missing = missing_terms(rag_kw[:15], lesson_text)

    # Status classification
    if cos >= 0.25 and cov >= 60:
        status = "GOOD"
    elif cos >= 0.15 or cov >= 40:
        status = "PARTIAL"
    else:
        status = "POOR"

    # Build notes
    notes_parts = []
    if lesson_words < 100:
        notes_parts.append(f"Lesson very short ({lesson_words} words)")
    if cos < 0.10:
        notes_parts.append("Very low similarity to RAG text — likely AI-only generation")
    if missing:
        notes_parts.append(f"Missing key RAG terms: {', '.join(missing[:6])}")
    if rag_words > 0 and lesson_words < rag_words * 0.3:
        notes_parts.append(f"Lesson ({lesson_words}w) much shorter than RAG content ({rag_words}w)")

    return {
        "chapter": chapter, "step": step,
        "lesson_words": lesson_words, "rag_words": rag_words,
        "cosine": round(cos, 3), "term_coverage_pct": cov,
        "missing_terms": missing, "rag_available": True,
        "status": status, "notes": "; ".join(notes_parts) if notes_parts else "OK",
    }


# ── Report generation ─────────────────────────────────────────────────────────

def write_markdown(results: list[dict], out_dir: Path, grade: str, subject: str | None) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    
    good = [r for r in results if r["status"] == "GOOD"]
    partial = [r for r in results if r["status"] == "PARTIAL"]
    poor = [r for r in results if r["status"] == "POOR"]
    no_rag = [r for r in results if r["status"] == "NO_RAG"]

    lines = [
        f"# Lesson vs RAG Audit — {grade}{' · ' + subject if subject else ''}",
        f"_Generated: {ts}_", "",
        "## Summary",
        f"| Status | Count | Meaning |",
        f"|---|---|---|",
        f"| ✅ GOOD | {len(good)} | Lesson closely reflects RAG textbook content |",
        f"| ⚠️ PARTIAL | {len(partial)} | Lesson partially covers RAG content — some gaps |",
        f"| ❌ POOR | {len(poor)} | Lesson has very low RAG alignment — likely AI-only |",
        f"| 🔴 NO_RAG | {len(no_rag)} | No RAG chunks found for this chapter |",
        "", "---", "",
        "## All Steps (sorted by quality)",
        "",
        "| Chapter | Step | Status | Cosine | Term Coverage | Lesson Words | RAG Words | Notes |",
        "|---|---|---|---|---|---|---|---|",
    ]

    # Sort: POOR first, then PARTIAL, then GOOD, then NO_RAG
    order = {"POOR": 0, "PARTIAL": 1, "NO_RAG": 2, "GOOD": 3}
    for r in sorted(results, key=lambda x: (order.get(x["status"], 9), -x.get("cosine", 0))):
        status_icon = {"GOOD": "✅", "PARTIAL": "⚠️", "POOR": "❌", "NO_RAG": "🔴"}.get(r["status"], "?")
        cov = f"{r['term_coverage_pct']}%" if r['term_coverage_pct'] is not None else "N/A"
        lines.append(
            f"| {r['chapter'][:40]} | {r['step']} | {status_icon} {r['status']} "
            f"| {r['cosine']} | {cov} | {r['lesson_words']} | {r['rag_words']} "
            f"| {r['notes'][:80] if r['notes'] != 'OK' else ''} |"
        )

    # Detail section for POOR/PARTIAL
    lines += ["", "---", "", "## Steps Needing Attention (POOR + PARTIAL)", ""]
    for r in sorted([x for x in results if x["status"] in ("POOR", "PARTIAL")],
                    key=lambda x: (x["chapter"], x["step"])):
        icon = "❌" if r["status"] == "POOR" else "⚠️"
        lines.append(f"### {icon} {r['chapter']} / {r['step']}")
        lines.append(f"- **Cosine similarity:** {r['cosine']} | **Term coverage:** {r['term_coverage_pct']}%")
        lines.append(f"- **Lesson words:** {r['lesson_words']} | **RAG words:** {r['rag_words']}")
        if r["notes"] and r["notes"] != "OK":
            lines.append(f"- **Issues:** {r['notes']}")
        if r["missing_terms"]:
            lines.append(f"- **Missing RAG terms:** `{'`, `'.join(r['missing_terms'][:10])}`")
        lines.append(f"- **Fix:** Refresh this lesson step (click 'Refresh lesson') so it regenerates with RAG context.")
        lines.append("")

    lines += ["---", "_Generated by audit_lesson_vs_rag.py_"]

    p = out_dir / "lesson_rag_audit.md"
    p.write_text("\n".join(lines), encoding="utf-8")
    return p


def write_csv(results: list[dict], out_dir: Path) -> Path:
    p = out_dir / "lesson_rag_audit.csv"
    fields = ["chapter", "step", "status", "cosine", "term_coverage_pct",
              "lesson_words", "rag_words", "rag_available", "missing_terms", "notes"]
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in results:
            row = {k: r.get(k, "") for k in fields}
            row["missing_terms"] = ", ".join(r.get("missing_terms", []))
            w.writerow(row)
    return p


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Audit lesson content vs RAG source")
    parser.add_argument("--grade", default="Grade 5")
    parser.add_argument("--subject", help="Filter by subject")
    parser.add_argument("--output", default="reports/lesson_rag_audit")
    args = parser.parse_args()

    grade = args.grade
    if not grade.startswith("Grade "):
        grade = "Grade " + grade

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    import logging
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    log = logging.getLogger("audit_rag")

    log.info("Fetching lessons for %s%s...", grade, f" / {args.subject}" if args.subject else "")
    lessons = fetch_lessons(grade, args.subject)
    log.info("  %d lesson steps found", len(lessons))

    # Deduplicate chapters for RAG fetch cache
    chapter_rag_cache: dict[tuple, list] = {}

    results = []
    processed = set()

    for row in lessons:
        subj = row.get("subject", "")
        ch = row.get("chapter", "")
        step = row.get("step_title", "")
        key = (subj, ch, step)
        if key in processed:
            continue
        processed.add(key)

        rag_key = (subj, ch)
        if rag_key not in chapter_rag_cache:
            chunks = fetch_rag_chunks_for_chapter(grade, subj, ch)
            chapter_rag_cache[rag_key] = chunks
            log.info("  %s / %s → %d RAG chunks", subj, ch[:40], len(chunks))

        result = audit_step(row, chapter_rag_cache[rag_key])
        result["subject"] = subj
        results.append(result)

    if not results:
        log.warning("No results — nothing to report.")
        return

    # Write reports
    md_path = write_markdown(results, out_dir, grade, args.subject)
    csv_path = write_csv(results, out_dir)
    log.info("Markdown: %s", md_path)
    log.info("CSV:      %s", csv_path)

    # Print summary
    good = sum(1 for r in results if r["status"] == "GOOD")
    partial = sum(1 for r in results if r["status"] == "PARTIAL")
    poor = sum(1 for r in results if r["status"] == "POOR")
    no_rag = sum(1 for r in results if r["status"] == "NO_RAG")
    total = len(results)

    print()
    print("=" * 60)
    print(f"  LESSON vs RAG AUDIT — {grade}")
    print("=" * 60)
    print(f"  Total steps audited : {total}")
    print(f"  ✅ GOOD             : {good}  ({round(good/total*100)}%)")
    print(f"  ⚠️  PARTIAL          : {partial}  ({round(partial/total*100)}%)")
    print(f"  ❌ POOR             : {poor}  ({round(poor/total*100)}%)")
    print(f"  🔴 NO_RAG           : {no_rag}")
    print(f"  Reports in          : {out_dir.resolve()}/")
    print("=" * 60)
    print()

    if poor + partial > 0:
        print(f"  {poor + partial} steps need attention — see lesson_rag_audit.md")
        print("  To fix: use 'Refresh lesson' in the admin/student UI for each flagged step.")
    else:
        print("  All steps are well-aligned with RAG content. 🎉")
    print()


if __name__ == "__main__":
    main()
