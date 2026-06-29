"""
audit_lesson_sections.py — 8-Section Lesson Consistency Audit
─────────────────────────────────────────────────────────────────────────────
Audits every lesson for the 8 canonical sections with depth checks.

Expected sections:
  1. Introduction
  2. What you will learn
  3. Simple Explanation
  4. Step-by-step Breakdown
  5. Worked Example
  6. Common Mistake
  7. Quick Check Question
  8. Summary

CLI:
  cd backend
  .venv/bin/python scripts/audit_lesson_sections.py --grade 9 --subject Science
  .venv/bin/python scripts/audit_lesson_sections.py --sample
  .venv/bin/python scripts/audit_lesson_sections.py --all
  .venv/bin/python scripts/audit_lesson_sections.py --fail-critical

Reports: reports/lesson_sections/
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.services.auth_service import admin_client
from app.services.grade_db_router import get_content_db

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
_log = logging.getLogger("audit_lesson_sections")
REPORT_DIR = Path("reports/lesson_sections")

# ── Canonical 8 sections ──────────────────────────────────────────────────────
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

SECTION_ALIASES = {
    "introduction": ["intro", "overview", "beginning"],
    "what you will learn": ["learning objectives", "objectives", "goals", "by the end"],
    "simple explanation": ["explanation", "core explanation", "concept", "understanding"],
    "step-by-step breakdown": ["step by step", "steps", "breakdown", "procedure", "method"],
    "worked example": ["example", "solved example", "worked out", "practice example"],
    "common mistake": ["common mistakes", "mistakes", "pitfalls", "watch out", "caution"],
    "quick check question": ["quick check", "check question", "check your understanding", "practice question", "mcq"],
    "summary": ["recap", "key points", "takeaways", "conclusion", "in summary"],
}

SECTION_MIN_WORDS = {
    "introduction": 80,
    "what you will learn": 20,
    "simple explanation": 150,
    "step-by-step breakdown": 50,
    "worked example": 60,
    "common mistake": 40,
    "quick check question": 30,
    "summary": 40,
}

FILLER_PATTERNS = [
    r"coming soon", r"tbd", r"lorem ipsum", r"to be added", r"placeholder",
    r"^\s*-+\s*$", r"^\s*\.\.\.\s*$",
]


# ── Section detection ─────────────────────────────────────────────────────────

def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


def _find_section(content: str, section_name: str) -> Optional[str]:
    """Find a section in lesson content by name or alias. Returns section text."""
    lines = content.splitlines()
    aliases = [section_name] + SECTION_ALIASES.get(section_name, [])

    for i, line in enumerate(lines):
        norm_line = _normalize(re.sub(r"[#*\d.\-]", " ", line))
        for alias in aliases:
            if alias in norm_line:
                # Collect text until next heading
                section_lines = []
                for j in range(i + 1, len(lines)):
                    next_line = lines[j]
                    # Stop at next heading
                    if re.match(r"^#{1,4}\s", next_line) or re.match(r"^\*\*\d+\.", next_line):
                        break
                    section_lines.append(next_line)
                return "\n".join(section_lines).strip()
    return None


def _word_count(text: str) -> int:
    """Count meaningful words (not punctuation-only tokens)."""
    if not text:
        return 0
    words = re.findall(r"\b\w+\b", text)
    return len(words)


def _has_filler(text: str) -> bool:
    for pattern in FILLER_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE | re.MULTILINE):
            return True
    return False


# ── Section-level checks ──────────────────────────────────────────────────────

class SectionIssue:
    def __init__(self, severity: str, section: str, issue: str, suggestion: str = ""):
        self.severity = severity
        self.section = section
        self.issue = issue
        self.suggestion = suggestion

    def to_dict(self) -> dict:
        return {"severity": self.severity, "section": self.section,
                "issue": self.issue, "suggestion": self.suggestion}


def _audit_section(section_name: str, content: Optional[str]) -> list[SectionIssue]:
    issues = []
    if content is None:
        issues.append(SectionIssue(
            "critical", section_name,
            f"Section '{section_name}' is missing.",
            f"Add a '{section_name}' section with adequate content."
        ))
        return issues

    wc = _word_count(content)

    if not content.strip():
        issues.append(SectionIssue(
            "critical", section_name,
            f"Section '{section_name}' exists but is empty.",
            "Add substantive content to this section."
        ))
        return issues

    if _has_filler(content):
        issues.append(SectionIssue(
            "critical", section_name,
            f"Section '{section_name}' contains placeholder/filler text.",
            "Replace placeholder text with real content."
        ))

    min_words = SECTION_MIN_WORDS.get(section_name, 50)
    if wc < min_words:
        issues.append(SectionIssue(
            "high", section_name,
            f"Section '{section_name}' is too short ({wc} words, minimum {min_words}).",
            f"Expand '{section_name}' to at least {min_words} meaningful words."
        ))

    # Section-specific checks
    if section_name == "what you will learn":
        objectives = len(re.findall(r"(?:^|\n)\s*[-•*]\s+\w", content))
        if objectives < 2:
            issues.append(SectionIssue(
                "high", section_name,
                "Learning objectives section has fewer than 2 bullet-point objectives.",
                "List at least 3 concrete, measurable learning objectives."
            ))

    if section_name == "step-by-step breakdown":
        steps = len(re.findall(r"(?:step\s*\d+|^\d+[\.\)]\s)", content, re.IGNORECASE | re.MULTILINE))
        if steps < 2:
            issues.append(SectionIssue(
                "high", section_name,
                "Step-by-step breakdown has fewer than 2 numbered steps.",
                "Present at least 3 ordered steps with explanations."
            ))

    if section_name == "worked example":
        has_answer = bool(re.search(r"answer|solution|result|=\s*\d", content, re.IGNORECASE))
        if not has_answer:
            issues.append(SectionIssue(
                "critical", section_name,
                "Worked example is missing a final answer or solution.",
                "Include problem, solution steps, and clearly stated final answer."
            ))

    if section_name == "common mistake":
        has_correction = bool(re.search(r"correct|instead|should|right way|actually", content, re.IGNORECASE))
        if not has_correction:
            issues.append(SectionIssue(
                "high", section_name,
                "Common mistake section is missing the correction or right approach.",
                "Include: what the mistake is, why it is wrong, and the correct approach."
            ))

    if section_name == "quick check question":
        has_answer_key = bool(re.search(r"answer|correct|explanation|solution", content, re.IGNORECASE))
        if not has_answer_key:
            issues.append(SectionIssue(
                "high", section_name,
                "Quick Check Question is missing the answer explanation.",
                "Include the correct answer with a clear explanation."
            ))

    if section_name == "summary":
        bullets = len(re.findall(r"(?:^|\n)\s*[-•*]\s+\w", content))
        if bullets < 2:
            issues.append(SectionIssue(
                "high", section_name,
                "Summary has fewer than 3 key takeaway points.",
                "List at least 3 specific, lesson-relevant key takeaways."
            ))

    return issues


# ── Lesson audit ──────────────────────────────────────────────────────────────

def audit_lesson_content(row: dict) -> dict:
    """Audit a single lesson step for 8-section compliance."""
    content = row.get("lesson_content", "") or ""
    step_title = row.get("step_title", "?")
    grade = row.get("grade", "?")
    subject = row.get("subject", "?")
    chapter = row.get("chapter", "?")

    all_issues: list[SectionIssue] = []
    section_results = {}
    found_sections = []

    for sec in CANONICAL_SECTIONS:
        sec_content = _find_section(content, sec)
        sec_issues = _audit_section(sec, sec_content)
        all_issues.extend(sec_issues)
        wc = _word_count(sec_content) if sec_content else 0
        section_results[sec] = {
            "found": sec_content is not None,
            "word_count": wc,
            "issues": [i.to_dict() for i in sec_issues],
        }
        if sec_content is not None:
            found_sections.append(sec)

    # Scores
    total_sections = len(CANONICAL_SECTIONS)
    present_count = len(found_sections)
    critical_count = sum(1 for i in all_issues if i.severity == "critical")
    high_count = sum(1 for i in all_issues if i.severity == "high")

    presence_score = round(present_count / total_sections * 100)
    depth_score = max(0, 100 - critical_count * 25 - high_count * 10)
    overall = round((presence_score + depth_score) / 2)

    return {
        "grade": grade, "subject": subject, "chapter": chapter,
        "step_title": step_title,
        "sections_found": present_count,
        "sections_total": total_sections,
        "missing_sections": [s for s in CANONICAL_SECTIONS if s not in found_sections],
        "section_results": section_results,
        "scores": {
            "section_presence_score": presence_score,
            "section_depth_score": depth_score,
            "overall_lesson_score": overall,
        },
        "issue_counts": {
            "critical": critical_count, "high": high_count,
            "total": len(all_issues),
        },
        "all_issues": [i.to_dict() for i in all_issues],
        "audited_at": datetime.now(timezone.utc).isoformat(),
    }


# ── Fetch + run ───────────────────────────────────────────────────────────────

def _fetch_lessons(grade: Optional[str], subject: Optional[str], sample: bool) -> list[dict]:
    try:
        db = get_content_db(grade)
        q = (db.table("lesson_cache")
             .select("grade,subject,chapter,step_title,lesson_content,status")
             .eq("status", "active")
             .order("grade").order("subject").order("chapter"))
        if grade:
            q = q.eq("grade", grade)
        if subject:
            q = q.eq("subject", subject)
        rows = q.execute().data or []
        if sample and len(rows) > 15:
            import random
            rows = random.sample(rows, 15)
        return rows
    except Exception as e:
        _log.error("Failed to fetch lessons: %s", e)
        return []


def run_sections_audit(grade=None, subject=None, sample=False, fail_critical=False):
    if grade and not grade.startswith("Grade "):
        grade = "Grade " + grade
    rows = _fetch_lessons(grade, subject, sample)
    if not rows:
        _log.warning("No lessons found.")
        return {}

    results = [audit_lesson_content(r) for r in rows]
    total_issues = sum(r["issue_counts"]["total"] for r in results)
    total_critical = sum(r["issue_counts"]["critical"] for r in results)
    avg_score = round(sum(r["scores"]["overall_lesson_score"] for r in results) / max(len(results), 1))

    summary = {
        "lessons_audited": len(results),
        "total_issues": total_issues,
        "critical_issues": total_critical,
        "avg_overall_score": avg_score,
        "section_compliance_pct": round(
            sum(r["sections_found"] for r in results) /
            max(sum(r["sections_total"] for r in results), 1) * 100, 1
        ),
        "overall": "PASS" if total_critical == 0 else "CRITICAL",
    }

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    # JSON
    p = REPORT_DIR / "lesson_sections_report.json"
    p.write_text(json.dumps({"audited_at": datetime.now(timezone.utc).isoformat(),
                              "summary": summary, "lessons": results}, indent=2))
    # CSV
    csv_p = REPORT_DIR / "lesson_sections_summary.csv"
    with open(csv_p, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["grade","subject","chapter","step_title",
            "sections_found","sections_total","missing_sections",
            "overall_score","critical","high","audited_at"])
        w.writeheader()
        for r in results:
            w.writerow({
                "grade": r["grade"], "subject": r["subject"],
                "chapter": r["chapter"], "step_title": r["step_title"],
                "sections_found": r["sections_found"],
                "sections_total": r["sections_total"],
                "missing_sections": ";".join(r["missing_sections"]),
                "overall_score": r["scores"]["overall_lesson_score"],
                "critical": r["issue_counts"]["critical"],
                "high": r["issue_counts"]["high"],
                "audited_at": r["audited_at"],
            })

    _log.info("Reports: %s/", REPORT_DIR)

    sep = "=" * 60
    _log.info(sep)
    _log.info("LESSON SECTIONS AUDIT COMPLETE")
    _log.info("Lessons audited : %s", len(results))
    _log.info("Avg score       : %s/100", avg_score)
    _log.info("Critical issues : %s", total_critical)
    _log.info("Section compliance: %s%%", summary["section_compliance_pct"])
    _log.info("Overall status  : %s", summary["overall"])
    _log.info(sep)

    if fail_critical and total_critical > 0:
        sys.exit(1)

    return {"summary": summary, "lessons": results}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Lesson 8-Section Audit")
    parser.add_argument("--grade", help="e.g. 9 or 'Grade 9'")
    parser.add_argument("--subject", help="e.g. Science")
    parser.add_argument("--sample", action="store_true", help="Audit 15 random lessons")
    parser.add_argument("--all", dest="run_all", action="store_true", help="Audit all lessons")
    parser.add_argument("--fail-critical", action="store_true", help="Exit code 1 if critical issues found")
    args = parser.parse_args()

    run_sections_audit(
        grade=args.grade,
        subject=args.subject,
        sample=args.sample,
        fail_critical=args.fail_critical,
    )
