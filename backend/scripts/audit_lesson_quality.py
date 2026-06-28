"""
audit_lesson_quality.py — Lesson Quality Audit Framework
─────────────────────────────────────────────────────────────────────────────
Walks through lesson_cache content like a student reading each lesson step
and evaluates quality across completeness, pedagogy, formula quality, MCQs,
and student flow.

Usage:
  cd backend
  .venv/bin/python scripts/audit_lesson_quality.py --grade 9 --subject Science
  .venv/bin/python scripts/audit_lesson_quality.py --all
  .venv/bin/python scripts/audit_lesson_quality.py --sample
  .venv/bin/python scripts/audit_lesson_quality.py --use-llm

Modes:
  --sample       20 random lessons, deterministic only (fast, CI-safe)
  --all          All lessons, deterministic only
  --use-llm      + LLM review (cached, expensive, manual/scheduled only)
  --grade N      Filter by grade (e.g. --grade 9)
  --subject S    Filter by subject
  --chapter C    Filter by chapter
  --output DIR   Output directory (default: reports/lesson_quality/)
  --fail-critical Exit code 1 if critical issues found (for CI)

Output:
  reports/lesson_quality/lesson_quality_report.json
  reports/lesson_quality/lesson_quality_report.md
  reports/lesson_quality/lesson_quality_summary.csv
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.auth_service import admin_client  # noqa: E402
from app.services.grade_db_router import get_content_db  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
_log = logging.getLogger("audit_lesson_quality")

# ── Constants ─────────────────────────────────────────────────────────────────
EXPECTED_STEP_KEYWORDS = [
    "introduction", "concept", "formula", "example", "practice",
    "summary", "recap", "revision",
]
MIN_EXPLANATION_LENGTH = 80    # chars — anything shorter is suspicious
MIN_FORMULA_LENGTH = 3
MIN_MCQ_OPTIONS = 4
LLM_CACHE_FILE = Path("reports/lesson_quality/.llm_cache.json")

# ── Findings ─────────────────────────────────────────────────────────────────

class Finding:
    def __init__(self, severity: str, category: str, message: str, detail: str = ""):
        self.severity = severity   # critical / high / medium / low
        self.category = category   # structure / formula / mcq / flow / pedagogy
        self.message  = message
        self.detail   = detail

    def to_dict(self):
        return {
            "severity": self.severity,
            "category": self.category,
            "message":  self.message,
            "detail":   self.detail[:300] if self.detail else "",
        }


# ── Deterministic checks ──────────────────────────────────────────────────────

def _check_lesson_content(row: dict) -> list[Finding]:
    findings = []
    content = row.get("lesson_content") or ""
    step    = row.get("step_title", "?")

    # 1. Empty or very short content
    if not content or len(content.strip()) < MIN_EXPLANATION_LENGTH:
        findings.append(Finding(
            "critical", "structure",
            f"Step '{step}' has missing or very short lesson content ({len(content)} chars).",
            content[:80],
        ))
        return findings  # no further checks on empty

    # 2. Missing title/heading
    has_heading = bool(re.search(r"(?i)(#+\s|\*\*.{3,}\*\*|<h[123])", content[:500]))
    if not has_heading:
        findings.append(Finding("medium", "structure", f"Step '{step}' may lack a clear title/heading."))

    # 3. No example
    has_example = bool(re.search(r"(?i)(example|solved|e\.g\.|for instance|consider|suppose)", content))
    step_lower  = step.lower()
    needs_example = any(w in step_lower for w in ["concept", "formula", "application", "worked"])
    if needs_example and not has_example:
        findings.append(Finding("high", "pedagogy", f"Step '{step}' likely needs an example but none found."))

    # 4. No real-world context for Science/Math concept steps
    has_context = bool(re.search(r"(?i)(real.?world|everyday|daily life|in practice|imagine|think about)", content))
    if "concept" in step_lower and not has_context:
        findings.append(Finding("low", "pedagogy", f"Step '{step}' lacks real-world context."))

    # 5. Formula steps — check variable definitions
    if "formula" in step_lower:
        has_where = bool(re.search(r"(?i)(where\s+[a-zA-Z]|variables|let\s+[a-zA-Z]|\b[a-zA-Z]\s*=\s*)", content))
        if not has_where:
            findings.append(Finding("high", "formula", f"Step '{step}' formula section lacks variable definitions."))

        # Check formula notation quality
        formula_lines = [l.strip() for l in content.splitlines() if "=" in l and len(l.strip()) > MIN_FORMULA_LENGTH]
        for fl in formula_lines[:5]:
            # Flag raw Python-style ^ without explicit LaTeX alternative
            if "^" in fl and "\\^" not in fl and "$$" not in fl and "\\(" not in fl:
                findings.append(Finding(
                    "medium", "formula",
                    f"Step '{step}' formula may need proper math rendering: '{fl[:60]}'",
                ))
                break  # one finding per step

    # 6. No summary in summary steps
    if "summary" in step_lower or "recap" in step_lower:
        has_summary = bool(re.search(r"(?i)(in summary|key (points|takeaway)|to summarize|remember that|learned)", content))
        if not has_summary:
            findings.append(Finding("medium", "structure", f"Step '{step}' summary section lacks clear summary language."))

    return findings


def _check_mcqs(row: dict) -> list[Finding]:
    findings = []
    raw  = row.get("practice_questions") or []
    step = row.get("step_title", "?")

    if not raw:
        # Not all steps need MCQs — flag only if step looks like it should have them
        step_lower = step.lower()
        if any(w in step_lower for w in ["practice", "mcq", "quiz", "check", "assessment"]):
            findings.append(Finding("high", "mcq", f"Step '{step}' is a practice step but has no MCQs."))
        return findings

    # parse if stored as JSON string
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            findings.append(Finding("critical", "mcq", f"Step '{step}' practice_questions is invalid JSON."))
            return findings

    if not isinstance(raw, list):
        raw = [raw]

    seen_questions: set[str] = set()

    for i, q in enumerate(raw[:20]):  # audit up to 20 MCQs
        qi = f"Step '{step}' MCQ #{i+1}"

        if not isinstance(q, dict):
            findings.append(Finding("critical", "mcq", f"{qi} is not a dict object."))
            continue

        question_text = str(q.get("question") or q.get("q") or "")
        options       = q.get("options") or q.get("choices") or []
        correct       = q.get("correct_answer") or q.get("correct") or q.get("answer")
        explanation   = q.get("explanation") or q.get("explain") or ""

        # Missing question text
        if not question_text or len(question_text.strip()) < 10:
            findings.append(Finding("critical", "mcq", f"{qi} has missing/empty question text."))
            continue

        # Duplicate question
        qnorm = question_text.strip().lower()
        if qnorm in seen_questions:
            findings.append(Finding("high", "mcq", f"{qi} is a duplicate question."))
        seen_questions.add(qnorm)

        # Correct number of options
        if not options or len(options) < MIN_MCQ_OPTIONS:
            findings.append(Finding("high", "mcq", f"{qi} has fewer than 4 options ({len(options)})."))
        elif len(options) > 6:
            findings.append(Finding("low", "mcq", f"{qi} has more than 6 options — consider trimming."))

        # Duplicate options
        opt_texts = [str(o).strip().lower() for o in options]
        if len(opt_texts) != len(set(opt_texts)):
            findings.append(Finding("high", "mcq", f"{qi} has duplicate option text."))

        # No correct answer
        if correct is None or str(correct).strip() == "":
            findings.append(Finding("critical", "mcq", f"{qi} has no correct answer specified."))

        # Answer leakage — correct answer text appears in question
        if correct and question_text and str(correct).lower() in question_text.lower():
            findings.append(Finding("high", "mcq", f"{qi} may have answer leakage in question text."))

        # Missing explanation
        if not explanation or len(str(explanation).strip()) < 10:
            findings.append(Finding("medium", "mcq", f"{qi} lacks an answer explanation."))

    return findings


def _check_student_flow(rows: list[dict]) -> list[Finding]:
    """Simulate a student reading the lesson steps in order."""
    findings = []
    if not rows:
        return [Finding("critical", "flow", "No lesson steps found for this lesson.")]

    # Check step ordering
    titles = [r.get("step_title", "") for r in rows]

    # Check for empty titles
    for i, t in enumerate(titles):
        if not t or not t.strip():
            findings.append(Finding("critical", "structure", f"Step {i+1} has no step_title."))

    # Check for duplicate steps
    seen: set[str] = set()
    for t in titles:
        tl = (t or "").lower().strip()
        if tl in seen:
            findings.append(Finding("high", "flow", f"Duplicate step title '{t}' in lesson."))
        seen.add(tl)

    return findings


# ── Scoring ───────────────────────────────────────────────────────────────────

def _compute_scores(findings: list[Finding]) -> dict:
    """Compute 0-100 quality scores from findings list."""
    def deduct(base: int, findings_in_category: list, weights: dict) -> int:
        score = base
        for f in findings_in_category:
            score -= weights.get(f.severity, 0)
        return max(0, score)

    weights = {"critical": 25, "high": 10, "medium": 5, "low": 2}

    structure_f  = [f for f in findings if f.category in ("structure", "flow")]
    formula_f    = [f for f in findings if f.category == "formula"]
    mcq_f        = [f for f in findings if f.category == "mcq"]
    pedagogy_f   = [f for f in findings if f.category == "pedagogy"]

    completeness = deduct(100, structure_f, weights)
    formula_q    = deduct(100, formula_f, weights) if formula_f else 90  # no formulas = neutral
    mcq_q        = deduct(100, mcq_f, weights) if mcq_f else 80  # no MCQs = slightly penalized
    pedagogy     = deduct(100, pedagogy_f, weights)
    flow         = deduct(100, [f for f in findings if f.category == "flow"], weights)

    overall = round((completeness + formula_q + mcq_q + pedagogy + flow) / 5)

    return {
        "completeness_score": completeness,
        "formula_quality_score": formula_q,
        "mcq_quality_score":   mcq_q,
        "pedagogy_score":      pedagogy,
        "student_flow_score":  flow,
        "overall_score":       overall,
    }


# ── LLM review (optional, cached) ────────────────────────────────────────────

def _llm_cache_key(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def _llm_review_lesson(row: dict, model: str = "gpt-4o-mini") -> list[Finding]:
    """Optional LLM review — returns findings. Cached by content hash."""
    content = (row.get("lesson_content") or "") + str(row.get("practice_questions") or "")
    cache_key = _llm_cache_key(content)

    # Check cache
    LLM_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    cache: dict = {}
    if LLM_CACHE_FILE.exists():
        try:
            cache = json.loads(LLM_CACHE_FILE.read_text())
        except Exception:
            cache = {}

    if cache_key in cache:
        _log.debug("LLM cache hit for %s", cache_key)
        raw = cache[cache_key]
    else:
        try:
            import openai  # type: ignore
            client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            prompt = f"""You are a CBSE curriculum quality auditor.
Review this lesson step content for Grade {row.get('grade')} {row.get('subject')} — {row.get('chapter')}, step: '{row.get('step_title')}'.

LESSON CONTENT:
{content[:2000]}

Return ONLY a JSON array of findings. Each finding: {{"severity": "critical|high|medium|low", "category": "structure|formula|mcq|pedagogy|flow", "message": "...", "detail": "..."}}
Return [] if no issues. No markdown, just JSON array."""

            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=600,
            )
            raw = json.loads(resp.choices[0].message.content or "[]")
            cache[cache_key] = raw
            LLM_CACHE_FILE.write_text(json.dumps(cache, indent=2))
        except Exception as e:
            _log.warning("LLM review failed for step '%s': %s", row.get("step_title"), e)
            return []

    return [Finding(f.get("severity","low"), f.get("category","pedagogy"), f.get("message",""), f.get("detail","")) for f in raw if isinstance(f, dict)]


# ── Fetching lessons ──────────────────────────────────────────────────────────

def _fetch_lessons(grade: str | None, subject: str | None, chapter: str | None, sample: bool) -> list[dict]:
    """Fetch lesson_cache rows matching filters."""


def _fetch_lessons(grade: str | None, subject: str | None, chapter: str | None, sample: bool) -> list[dict]:
    """Fetch lesson_cache rows matching filters."""
    try:
        db = get_content_db(grade)
        q = db.table("lesson_cache").select(
            "cache_key, grade, subject, chapter, step_title, mode, "
            "lesson_content, practice_questions, source_type, status, access_count"
        ).eq("status", "active")
        if grade:
            q = q.eq("grade", grade)
        if subject:
            q = q.eq("subject", subject)
        if chapter:
            q = q.eq("chapter", chapter)
        result = q.order("grade").order("subject").order("chapter").order("step_title").execute()
        rows = result.data or []
        if sample and len(rows) > 20:
            import random
            rows = random.sample(rows, 20)
        return rows
    except Exception as e:
        _log.error("Failed to fetch lessons: %s", e)
        return []


# ── Group rows into lessons ───────────────────────────────────────────────────

def _group_by_lesson(rows: list[dict]) -> dict[str, list[dict]]:
    """Group rows by grade+subject+chapter as a logical lesson."""
    groups: dict[str, list[dict]] = {}
    for r in rows:
        key = f"{r.get('grade','?')}|{r.get('subject','?')}|{r.get('chapter','?')}"
        groups.setdefault(key, []).append(r)
    return groups


# ── Audit one lesson ──────────────────────────────────────────────────────────

def audit_lesson(key: str, rows: list[dict], use_llm: bool) -> dict:
    """Audit all steps in a lesson. Returns a lesson result dict."""
    grade, subject, chapter = (key.split("|") + ["?","?","?"])[:3]
    all_findings: list[Finding] = []
    step_results = []

    # Student flow check across all steps
    all_findings.extend(_check_student_flow(rows))

    for row in rows:
        step = row.get("step_title", "?")
        step_findings: list[Finding] = []

        # Deterministic checks
        step_findings.extend(_check_lesson_content(row))
        step_findings.extend(_check_mcqs(row))

        # Optional LLM check (never propagate LLM errors)
        if use_llm:
            try:
                step_findings.extend(_llm_review_lesson(row))
            except Exception as _e:
                _log.warning("LLM review failed for step %s: %s", row.get("step_title"), _e)

        all_findings.extend(step_findings)
        step_results.append({
            "step_title": step,
            "findings": [f.to_dict() for f in step_findings],
            "finding_count": len(step_findings),
        })

    scores = _compute_scores(all_findings)
    critical = [f for f in all_findings if f.severity == "critical"]

    return {
        "grade": grade,
        "subject": subject,
        "chapter": chapter,
        "step_count": len(rows),
        "total_findings": len(all_findings),
        "critical_count": len(critical),
        "findings_summary": {
            "critical": len([f for f in all_findings if f.severity == "critical"]),
            "high":     len([f for f in all_findings if f.severity == "high"]),
            "medium":   len([f for f in all_findings if f.severity == "medium"]),
            "low":      len([f for f in all_findings if f.severity == "low"]),
        },
        "scores": scores,
        "findings": [f.to_dict() for f in all_findings],
        "steps": step_results,
        "audited_at": datetime.now(timezone.utc).isoformat(),
    }


# ── Report generation ─────────────────────────────────────────────────────────

def _write_json(results: list[dict], out_dir: Path) -> None:
    p = out_dir / "lesson_quality_report.json"
    p.write_text(json.dumps({"audited_at": datetime.now(timezone.utc).isoformat(), "lessons": results}, indent=2))
    _log.info("JSON report: %s", p)


def _write_markdown(results: list[dict], out_dir: Path) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    total_findings = sum(r["total_findings"] for r in results)
    total_critical = sum(r["critical_count"] for r in results)
    avg_score = round(sum(r["scores"]["overall_score"] for r in results) / max(len(results), 1))

    lines = [
        "# Lesson Quality Audit Report",
        "",
        f"_Generated: {ts} UTC_",
        "",
        f"**Lessons audited:** {len(results)}",
        f"**Total findings:** {total_findings}",
        f"**Critical issues:** {total_critical}",
        f"**Average overall score:** {avg_score}%",
        "",
        "---",
        "",
    ]

    # Worst lessons
    worst = sorted(results, key=lambda r: r["scores"]["overall_score"])[:10]
    lines.append("## Worst 10 Lessons")
    lines.append("")
    lines.append("| Grade | Subject | Chapter | Steps | Overall | Critical | High |")
    lines.append("|---|---|---|---|---|---|---|")
    for r in worst:
        sc = r["scores"]
        fs = r["findings_summary"]
        lines.append(
            f"| {r['grade']} | {r['subject']} | {r['chapter']} "
            f"| {r['step_count']} | {sc['overall_score']} "
            f"| {fs['critical']} | {fs['high']} |"
        )

    # Critical issues
    lines.append("")
    lines.append("## Critical Issues")
    lines.append("")
    for r in results:
        criticals = [f for f in r["findings"] if f["severity"] == "critical"]
        if criticals:
            lines.append(f"### {r['grade']} · {r['subject']} · {r['chapter']}")
            for f in criticals:
                lines.append(f"- **{f['category']}**: {f['message']}")
                if f.get("detail"):
                    lines.append(f"  > {f['detail'][:150]}")
            lines.append("")

    # Score summary by grade/subject
    lines.append("")
    lines.append("## Score Summary by Grade/Subject")
    lines.append("")
    lines.append("| Grade | Subject | Lessons | Avg Overall | Avg Completeness | Avg MCQ | Critical |")
    lines.append("|---|---|---|---|---|---|---|")
    from collections import defaultdict
    groups: dict = defaultdict(list)
    for r in results:
        groups[f"{r['grade']}|{r['subject']}"].append(r)
    for k, rlist in sorted(groups.items()):
        g, s = k.split("|")
        avg_o  = round(sum(x["scores"]["overall_score"] for x in rlist) / len(rlist))
        avg_c  = round(sum(x["scores"]["completeness_score"] for x in rlist) / len(rlist))
        avg_m  = round(sum(x["scores"]["mcq_quality_score"] for x in rlist) / len(rlist))
        crit   = sum(x["critical_count"] for x in rlist)
        lines.append(f"| {g} | {s} | {len(rlist)} | {avg_o} | {avg_c} | {avg_m} | {crit} |")

    lines.append("")
    lines.append("---")
    lines.append("_Generated by `audit_lesson_quality.py`._")

    p = out_dir / "lesson_quality_report.md"
    p.write_text("\n".join(lines))
    _log.info("Markdown report: %s", p)


def _write_csv(results: list[dict], out_dir: Path) -> None:
    p = out_dir / "lesson_quality_summary.csv"
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "grade", "subject", "chapter", "step_count",
            "overall_score", "completeness_score", "formula_quality_score",
            "mcq_quality_score", "pedagogy_score", "student_flow_score",
            "critical", "high", "medium", "low", "audited_at",
        ])
        w.writeheader()
        for r in results:
            sc = r["scores"]
            fs = r["findings_summary"]
            w.writerow({
                "grade": r["grade"], "subject": r["subject"], "chapter": r["chapter"],
                "step_count": r["step_count"],
                "overall_score": sc["overall_score"],
                "completeness_score": sc["completeness_score"],
                "formula_quality_score": sc["formula_quality_score"],
                "mcq_quality_score": sc["mcq_quality_score"],
                "pedagogy_score": sc["pedagogy_score"],
                "student_flow_score": sc["student_flow_score"],
                "critical": fs["critical"], "high": fs["high"],
                "medium": fs["medium"], "low": fs["low"],
                "audited_at": r["audited_at"],
            })
    _log.info("CSV report: %s", p)


# ── CLI entry point ───────────────────────────────────────────────────────────


def main():  # noqa: C901
    parser = argparse.ArgumentParser(description="Lesson Quality Audit")
    parser.add_argument("--grade", help="Filter by grade (e.g. 9 or Grade 9)")
    parser.add_argument("--subject", help="Filter by subject")
    parser.add_argument("--chapter", help="Filter by chapter")
    parser.add_argument("--sample", action="store_true", help="Sample 20 lessons only")
    parser.add_argument("--all", action="store_true", help="Audit all lessons")
    parser.add_argument("--use-llm", action="store_true", help="Enable LLM review (cached)")
    parser.add_argument("--fail-critical", action="store_true", help="Exit 1 on critical issues")
    parser.add_argument("--output", default="reports/lesson_quality", help="Output directory")
    args = parser.parse_args()

    grade = args.grade
    if grade and not grade.startswith("Grade "):
        grade = "Grade " + grade

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    _log.info("Fetching lessons (grade=%s, subject=%s, chapter=%s, sample=%s)...",
              grade, args.subject, args.chapter, args.sample)

    rows = _fetch_lessons(grade, args.subject, args.chapter, args.sample)

    if not rows:
        _log.warning("No lessons found matching filters. Nothing to audit.")
        sys.exit(0)

    _log.info("Found %d lesson steps. Grouping by chapter...", len(rows))
    lessons = _group_by_lesson(rows)
    _log.info("Auditing %d lessons (%s LLM)...", len(lessons), "WITH" if args.use_llm else "WITHOUT")

    results = []
    for key, lesson_rows in lessons.items():
        result = audit_lesson(key, lesson_rows, use_llm=args.use_llm)
        results.append(result)
        sc = result["scores"]
        _log.info("  %s -- %d steps, score=%d, critical=%d",
                  key.replace("|", " / "), len(lesson_rows),
                  sc["overall_score"], result["critical_count"])

    _write_json(results, out_dir)
    _write_markdown(results, out_dir)
    _write_csv(results, out_dir)

    total_critical = sum(r["critical_count"] for r in results)
    avg_score = round(sum(r["scores"]["overall_score"] for r in results) / max(len(results), 1))

    sep = "=" * 60
    print("")
    print(sep)
    print("LESSON QUALITY AUDIT COMPLETE")
    print("  Lessons audited : " + str(len(results)))
    print("  Average score   : " + str(avg_score) + "/100")
    print("  Critical issues : " + str(total_critical))
    print("  Reports in      : " + str(out_dir) + "/")
    print(sep)
    print("")

    if args.fail_critical and total_critical > 0:
        _log.error("%d critical issue(s) found. Exiting with code 1.", total_critical)
        sys.exit(1)


if __name__ == "__main__":
    main()
