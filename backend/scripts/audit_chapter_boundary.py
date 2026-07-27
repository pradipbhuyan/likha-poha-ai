#!/usr/bin/env python3
"""
Chapter Boundary & Accuracy Audit (Tier A — deterministic)
============================================================
Phase 0/1 of the Lesson Content Quality Review Plan
(see docs/LESSON_CONTENT_QUALITY_REVIEW_PLAN.md).

Loads per-chapter "manifests" from
    backend/app/data/chapter_manifests/<grade>/<subject>/<chapter_slug>.json
and scans matching cached lessons (Supabase `lesson_cache` table) for:

  1. CONTAMINATION  — banned_topics phrases whose full set of significant
                       terms appear together in a single lesson step
                       (i.e. content that belongs to a DIFFERENT chapter).
  2. COVERAGE_GAP   — must_include_keywords missing across the WHOLE
                       chapter (all steps combined), indicating the
                       chapter is incomplete vs the syllabus. This is
                       checked at chapter level, not per-step, because a
                       single step (e.g. "Worked examples") is not
                       expected to mention every syllabus keyword.
  3. KNOWN_PITFALL  — known_pitfalls.claim patterns found in a step,
                       while making sure we are not just detecting our
                       own correction text (which often shares words
                       with the claim it is correcting).

This is a read-only, zero-cost, zero-LLM audit (Tier A). It is meant to be
run before any Tier B (LLM-as-subject-expert) review, and to be wired into
admin_qa.py as tool #7 in a later step.

Usage:
    cd backend
    python3 scripts/audit_chapter_boundary.py
    python3 scripts/audit_chapter_boundary.py --grade "Grade 11" --subject Chemistry
    python3 scripts/audit_chapter_boundary.py --chapter "Structure of Atom"
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

MANIFEST_ROOT = Path(__file__).resolve().parents[1] / "app" / "data" / "chapter_manifests"
REPORT_DIR = Path(__file__).resolve().parents[1] / "reports" / "chapter_boundary"


# ── Manifest loading ──────────────────────────────────────────────────────────

def load_all_manifests() -> list[dict]:
    """Recursively load every *.json manifest under chapter_manifests/."""
    manifests = []
    if not MANIFEST_ROOT.exists():
        return manifests
    for path in sorted(MANIFEST_ROOT.rglob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            data["_manifest_path"] = str(path)
            manifests.append(data)
        except Exception as e:
            print(f"  [warn] Could not parse manifest {path}: {e}")
    return manifests


# ── Lesson fetch ──────────────────────────────────────────────────────────────

def fetch_lessons_for_chapter(grade: str, subject: str, chapter: str) -> list[dict]:
    """Fetch all active lesson_cache rows for a given grade/subject/chapter."""
    try:
        from app.services.grade_db_router import get_content_db  # noqa: PLC0415
        db = get_content_db(grade)
        result = (
            db.table("lesson_cache")
            .select("id, grade, subject, chapter, step_title, lesson_content, status")
            .eq("grade", grade)
            .ilike("subject", subject)
            .ilike("chapter", chapter)
            .eq("status", "active")
            .execute()
        )
        return result.data or []
    except Exception as e:
        print(f"  [error] Could not fetch lessons for {grade}/{subject}/{chapter}: {e}")
        return []


# ── Tier A checks ──────────────────────────────────────────────────────────────

# Common English / generic words that should never count as "significant"
# evidence of topic overlap — without this filter, words like "from",
# "with", "chapter", "modern" cause false-positive matches on completely
# unrelated content.
_STOPWORDS = {
    "that", "this", "with", "from", "have", "being", "stated", "final",
    "into", "were", "when", "than", "then", "also", "such", "some", "does",
    "each", "only", "more", "most", "which", "these", "those", "about",
    "there", "their", "would", "could", "should", "because", "belongs",
    "chapter", "topic", "modern", "chemistry", "elements", "classification",
    "periodicity", "properties", "basic", "concepts", "general", "context",
    "unrelated", "discussion", "equipment", "measurement", "period",
    "electron", "electrons", "atom", "atoms", "atomic",
}


def _significant_words(phrase: str, min_len: int = 5) -> list[str]:
    """Extract distinguishing words from a phrase, filtering stop-words."""
    words = re.findall(rf"[A-Za-z]{{{min_len},}}", phrase)
    return [w for w in words if w.lower() not in _STOPWORDS]


def _keyword_present(text: str, keyword: str) -> bool:
    """Case-insensitive substring match, tolerant of minor punctuation."""
    pattern = re.escape(keyword.strip())
    return re.search(pattern, text, re.IGNORECASE) is not None


def check_contamination(content: str, banned_topics: list[str]) -> list[dict]:
    """
    Flag a banned_topics phrase only if ALL of its significant terms appear
    together in this single lesson step's content. Requiring all terms
    (not just 2) avoids false positives from generic overlapping words.
    """
    findings = []
    for topic in banned_topics:
        core_phrase = re.split(r"\(", topic)[0].strip()
        words = _significant_words(core_phrase)
        if len(words) < 2:
            continue
        hits = [w for w in words if _keyword_present(content, w)]
        if len(hits) == len(words):
            findings.append({
                "severity": "critical",
                "category": "contamination",
                "message": f"Possible out-of-scope content detected: '{topic}'",
                "detail": f"All significant terms ({', '.join(hits)}) found together in this step's content.",
            })
    return findings


def check_coverage_gap_for_chapter(combined_content: str, must_include_keywords: list[str]) -> dict | None:
    """
    Flag if a large fraction of must_include_keywords are missing across
    the ENTIRE chapter (all steps combined). Returns a single finding dict
    (chapter-level), or None if coverage is acceptable.
    """
    missing = [kw for kw in must_include_keywords if not _keyword_present(combined_content, kw)]
    total = len(must_include_keywords) or 1
    missing_pct = round(len(missing) / total * 100)
    if missing_pct >= 30:
        return {
            "severity": "high" if missing_pct < 60 else "critical",
            "category": "coverage_gap",
            "message": f"{missing_pct}% of required syllabus keywords are missing across the WHOLE chapter (all steps combined).",
            "detail": f"Missing: {', '.join(missing[:20])}" + (" ..." if len(missing) > 20 else ""),
        }
    return None


def check_known_pitfalls(content: str, known_pitfalls: list[dict]) -> list[dict]:
    """
    Flag if a known incorrect claim pattern appears in the content, while
    avoiding false positives where the text is actually stating the
    CORRECTION (not the mistaken claim). We do this by requiring a strong
    overlap with the claim's distinguishing words AND checking that the
    correction's own distinguishing words are not dominating the same
    sentence window (a crude but effective heuristic).
    """
    findings = []
    for pitfall in known_pitfalls:
        claim = pitfall.get("claim", "")
        correction = pitfall.get("correction", "")
        claim_words = _significant_words(claim, min_len=5)
        correction_words = set(w.lower() for w in _significant_words(correction, min_len=6))
        if len(claim_words) < 2:
            continue

        # Find sentence-ish windows around any claim-word hit and check
        # whether that same window ALSO contains correction-only language
        # (e.g. "only", "model", "however", "this is only true within the
        # bohr model") — if so, treat it as the correction being present,
        # not the mistaken claim.
        sentences = re.split(r"(?<=[.!?])\s+", content)
        claim_hit_sentences = [
            s for s in sentences
            if sum(1 for w in claim_words if _keyword_present(s, w)) >= min(3, len(claim_words))
        ]
        if not claim_hit_sentences:
            continue

        # If every claim-hit sentence also contains a correction-specific
        # word not present in the claim itself, treat this as "correction
        # text", not a repeated mistake — skip it.
        claim_only_words = set(w.lower() for w in claim_words) - correction_words
        genuinely_mistaken = False
        for s in claim_hit_sentences:
            s_lower = s.lower()
            has_correction_language = any(
                cw in s_lower for cw in correction_words if cw not in claim_only_words
            )
            if not has_correction_language:
                genuinely_mistaken = True
                break

        if genuinely_mistaken:
            findings.append({
                "severity": "critical",
                "category": "known_pitfall",
                "message": f"Content may repeat a known scientific/pedagogical error: \"{claim}\"",
                "detail": f"Correction: {correction}",
            })
    return findings


def audit_chapter(manifest: dict, rows: list[dict]) -> list[dict]:
    """
    Run Tier A checks:
      - contamination + known_pitfalls per lesson step (row)
      - coverage_gap once for the whole chapter (all rows combined)
    Returns a list of per-row result dicts, with the chapter-level
    coverage_gap finding attached to every row that has any findings
    (and also attached as its own "chapter" pseudo-row for visibility).
    """
    banned_topics = manifest.get("banned_topics", [])
    must_include_keywords = manifest.get("must_include_keywords", [])
    known_pitfalls = manifest.get("known_pitfalls", [])

    combined_content = "\n\n".join(r.get("lesson_content") or "" for r in rows)
    chapter_coverage_finding = check_coverage_gap_for_chapter(combined_content, must_include_keywords)

    results = []
    for row in rows:
        content = row.get("lesson_content") or ""
        findings = []
        findings += check_contamination(content, banned_topics)
        findings += check_known_pitfalls(content, known_pitfalls)

        critical = sum(1 for f in findings if f["severity"] == "critical")
        high = sum(1 for f in findings if f["severity"] == "high")

        results.append({
            "lesson_cache_id": row.get("id"),
            "grade": row.get("grade"),
            "subject": row.get("subject"),
            "chapter": row.get("chapter"),
            "step_title": row.get("step_title"),
            "manifest_path": manifest.get("_manifest_path"),
            "findings": findings,
            "critical_count": critical,
            "high_count": high,
            "content_length": len(content),
        })

    # Attach the chapter-level coverage finding to a synthetic summary row
    # so it is visible once per chapter, not duplicated per step.
    if chapter_coverage_finding:
        results.append({
            "lesson_cache_id": None,
            "grade": manifest.get("grade"),
            "subject": manifest.get("subject"),
            "chapter": manifest.get("chapter"),
            "step_title": "(WHOLE CHAPTER — combined coverage check)",
            "manifest_path": manifest.get("_manifest_path"),
            "findings": [chapter_coverage_finding],
            "critical_count": 1 if chapter_coverage_finding["severity"] == "critical" else 0,
            "high_count": 1 if chapter_coverage_finding["severity"] == "high" else 0,
            "content_length": len(combined_content),
        })

    return results


# ── Runner ─────────────────────────────────────────────────────────────────────

def run_audit(grade_filter: str | None, subject_filter: str | None,
              chapter_filter: str | None) -> dict:
    manifests = load_all_manifests()
    if grade_filter:
        manifests = [m for m in manifests if m.get("grade", "").lower() == grade_filter.lower()]
    if subject_filter:
        manifests = [m for m in manifests if m.get("subject", "").lower() == subject_filter.lower()]
    if chapter_filter:
        manifests = [m for m in manifests if m.get("chapter", "").lower() == chapter_filter.lower()]

    print(f"\nLoaded {len(manifests)} chapter manifest(s).")

    all_results = []
    for manifest in manifests:
        grade = manifest.get("grade", "")
        subject = manifest.get("subject", "")
        chapter = manifest.get("chapter", "")
        print(f"\n  Auditing: {grade} / {subject} / {chapter}")
        rows = fetch_lessons_for_chapter(grade, subject, chapter)
        print(f"    Found {len(rows)} cached lesson step(s) for this chapter.")
        if not rows:
            continue

        chapter_results = audit_chapter(manifest, rows)
        all_results.extend(chapter_results)

        for result in chapter_results:
            if result["findings"]:
                print(f"    [{result['step_title']}] -> {len(result['findings'])} finding(s) "
                      f"(critical={result['critical_count']}, high={result['high_count']})")
                for f in result["findings"]:
                    print(f"        - [{f['severity'].upper()}] {f['category']}: {f['message']}")
            else:
                print(f"    [{result['step_title']}] -> clean (no Tier A findings)")

    total_critical = sum(r["critical_count"] for r in all_results)
    total_high = sum(r["high_count"] for r in all_results)

    report = {
        "audited_at": datetime.now(timezone.utc).isoformat(),
        "manifests_used": len(manifests),
        "lessons_audited": len(all_results),
        "total_critical_findings": total_critical,
        "total_high_findings": total_high,
        "results": all_results,
    }

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = REPORT_DIR / "chapter_boundary_report.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\nReport written: {out_path}")
    print(f"Summary: {len(all_results)} row(s) audited, "
          f"{total_critical} critical finding(s), {total_high} high finding(s).\n")

    return report


def main():
    parser = argparse.ArgumentParser(description="Tier A chapter boundary/accuracy audit")
    parser.add_argument("--grade", default=None, help='e.g. "Grade 11"')
    parser.add_argument("--subject", default=None, help='e.g. "Chemistry"')
    parser.add_argument("--chapter", default=None, help='e.g. "Structure of Atom"')
    args = parser.parse_args()

    run_audit(
        grade_filter=args.grade,
        subject_filter=args.subject,
        chapter_filter=args.chapter,
    )


if __name__ == "__main__":
    main()
