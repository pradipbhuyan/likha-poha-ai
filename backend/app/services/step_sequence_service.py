"""
step_sequence_service.py — Step-to-Step Consistency Audit Engine
─────────────────────────────────────────────────────────────────────────────
Deterministic (no LLM) auditing of lesson step sequences.

Analyses:
  - Text similarity between steps (Jaccard on word n-grams)
  - Repeated sentences/paragraphs across steps
  - Repeated MCQ questions
  - Repeated formulas/equations
  - Word-count depth progression
  - Pedagogical role validation per step position
  - Step completeness (presence of meaningful content)

Scores (0–100, higher = better):
  step_uniqueness_score        — how unique this step is vs all others
  depth_progression_score      — does each step add more than the previous
  cross_step_repetition_score  — 100 = no repetition, 0 = fully repeated
  step_completeness_score      — does the step have sufficient content
  overall_step_sequence_score  — weighted composite

Severity thresholds:
  >90% pairwise similarity  → Critical
  >75% pairwise similarity  → High
  later step shorter + <25% new content → High
  step has <30 unique words  → Critical
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import re
import math
from typing import Any, Optional

# ── Pedagogical role expectations per step position (0-indexed) ──────────────
STEP_ROLES = {
    0: {"name": "Concept Introduction",     "expects": ["introduce", "define", "what", "concept"]},
    1: {"name": "Core Explanation",         "expects": ["explain", "how", "why", "because", "therefore"]},
    2: {"name": "Worked Examples",          "expects": ["example", "solution", "step", "calculate", "solve"]},
    3: {"name": "Exam-Style Problems",      "expects": ["problem", "find", "calculate", "evaluate", "determine"]},
    4: {"name": "Revision and Recap",       "expects": ["summary", "recap", "key", "remember", "important"]},
    5: {"name": "Exam Preparation",         "expects": ["exam", "tip", "common", "mistake", "avoid", "practice"]},
}

# Similarity thresholds
SIM_CRITICAL = 0.90
SIM_HIGH     = 0.75
SIM_WARN     = 0.50

MIN_UNIQUE_WORDS = 30   # below → Critical
MIN_WORDS_PER_STEP = 80 # below → step is too short

# ── Text normalisation ────────────────────────────────────────────────────────

def _normalise(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _word_set(text: str) -> set[str]:
    words = _normalise(text).split()
    return set(w for w in words if len(w) > 2)


def _bigrams(text: str) -> set[tuple]:
    words = _normalise(text).split()
    return set(zip(words[:-1], words[1:]))


def _sentences(text: str) -> list[str]:
    """Split text into sentences (simple heuristic)."""
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if len(p.strip()) > 20]


def _extract_mcqs(text: str) -> list[str]:
    """Extract MCQ-like question stems from text."""
    lines = text.split("\n")
    mcqs = []
    for line in lines:
        clean = line.strip()
        if re.search(r"\b[A-D]\b[\)\.:]", clean) or re.search(r"\(a\)|\(b\)|\(c\)|\(d\)", clean, re.I):
            mcqs.append(_normalise(clean))
        elif clean.endswith("?") and len(clean) > 20:
            mcqs.append(_normalise(clean))
    return mcqs


def _extract_formulas(text: str) -> list[str]:
    """Extract lines that look like math formulas."""
    lines = text.split("\n")
    formulas = []
    for line in lines:
        clean = line.strip()
        if re.search(r"[=+\-*/^√∑∫π]", clean) and len(clean) > 5:
            formulas.append(_normalise(clean))
    return formulas


def _word_count(text: str) -> int:
    return len(_normalise(text).split()) if text else 0


# ── Core similarity metrics ───────────────────────────────────────────────────

def jaccard_similarity(a: str, b: str) -> float:
    """Word-level Jaccard similarity between two texts (0.0–1.0)."""
    sa = _word_set(a)
    sb = _word_set(b)
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def bigram_similarity(a: str, b: str) -> float:
    """Bigram-level Jaccard similarity (captures phrase repetition)."""
    ba = _bigrams(a)
    bb = _bigrams(b)
    if not ba and not bb:
        return 1.0
    if not ba or not bb:
        return 0.0
    return len(ba & bb) / len(ba | bb)


def sentence_overlap(a: str, b: str) -> float:
    """Fraction of sentences in `a` that appear near-verbatim in `b`."""
    sents_a = _sentences(a)
    sents_b = _sentences(b)
    if not sents_a:
        return 0.0
    matches = 0
    for sa in sents_a:
        for sb in sents_b:
            if jaccard_similarity(sa, sb) > 0.80:
                matches += 1
                break
    return matches / len(sents_a)


def combined_similarity(a: str, b: str) -> float:
    """Weighted combination of word, bigram, and sentence similarities."""
    if not a.strip() or not b.strip():
        return 0.0
    j  = jaccard_similarity(a, b)
    bg = bigram_similarity(a, b)
    so = sentence_overlap(a, b)
    return round(0.4 * j + 0.35 * bg + 0.25 * so, 4)


# ── Step analysis ─────────────────────────────────────────────────────────────

def _unique_word_count(text: str, other_texts: list[str]) -> int:
    """Count words in `text` that do NOT appear in any of `other_texts`."""
    my_words = _word_set(text)
    other_words: set[str] = set()
    for t in other_texts:
        other_words |= _word_set(t)
    return len(my_words - other_words)


def _repeated_sentences_with(text: str, other_texts: list[str]) -> list[dict]:
    """Find sentences in `text` that repeat in other texts."""
    my_sents = _sentences(text)
    found = []
    for i, other in enumerate(other_texts):
        other_sents = _sentences(other)
        for s in my_sents:
            for os in other_sents:
                sim = jaccard_similarity(s, os)
                if sim >= 0.80:
                    found.append({
                        "sentence": s[:120],
                        "repeated_in_step_index": i,
                        "similarity": round(sim, 2),
                    })
                    break
    return found


def _repeated_mcqs(text: str, other_texts: list[str]) -> list[str]:
    my_mcqs = _extract_mcqs(text)
    repeated = []
    for mcq in my_mcqs:
        for other in other_texts:
            other_mcqs = _extract_mcqs(other)
            for omcq in other_mcqs:
                if jaccard_similarity(mcq, omcq) > 0.75:
                    repeated.append(mcq[:100])
                    break
    return list(set(repeated))


def _repeated_formulas(text: str, other_texts: list[str]) -> list[str]:
    my_fmls = _extract_formulas(text)
    repeated = []
    for fml in my_fmls:
        for other in other_texts:
            other_fmls = _extract_formulas(other)
            for ofml in other_fmls:
                if jaccard_similarity(fml, ofml) > 0.75:
                    repeated.append(fml[:80])
                    break
    return list(set(repeated))


# ── Per-step scoring ──────────────────────────────────────────────────────────

def score_step(
    step_index: int,
    step_text: str,
    all_steps: list[str],
) -> dict[str, Any]:
    """
    Score a single step for uniqueness, completeness, and role alignment.

    Returns a dict with scores and detected issues.
    """
    other_texts = [t for i, t in enumerate(all_steps) if i != step_index]
    prev_text   = all_steps[step_index - 1] if step_index > 0 else ""
    next_text   = all_steps[step_index + 1] if step_index < len(all_steps) - 1 else ""

    wc         = _word_count(step_text)
    unique_wc  = _unique_word_count(step_text, other_texts)
    rep_sents  = _repeated_sentences_with(step_text, [t for i, t in enumerate(other_texts)])
    rep_mcqs   = _repeated_mcqs(step_text, other_texts)
    rep_fmls   = _repeated_formulas(step_text, other_texts)

    # Pairwise similarity to every other step
    pairwise = {}
    for i, other in enumerate(all_steps):
        if i == step_index:
            continue
        pairwise[i] = round(combined_similarity(step_text, other), 3)

    max_sim = max(pairwise.values()) if pairwise else 0.0
    sim_to_prev = pairwise.get(step_index - 1, 0.0) if step_index > 0 else 0.0

    # ── step_uniqueness_score ─────────────────────────────────────────────────
    if wc == 0:
        uniqueness = 0
    else:
        unique_ratio = unique_wc / max(wc, 1)
        rep_sentence_penalty = min(0.5, len(rep_sents) * 0.1)
        uniqueness = round(max(0, min(100, (unique_ratio - rep_sentence_penalty) * 100)))

    # ── step_completeness_score ───────────────────────────────────────────────
    role = STEP_ROLES.get(step_index, {})
    role_keywords = role.get("expects", [])
    text_lower = step_text.lower()
    keyword_hits = sum(1 for kw in role_keywords if kw in text_lower)
    keyword_score = (keyword_hits / max(len(role_keywords), 1)) * 40
    length_score  = min(60, (wc / 200) * 60)  # 200 words = full 60 pts
    completeness  = round(min(100, keyword_score + length_score))

    # ── cross_step_repetition_score ───────────────────────────────────────────
    # Higher = better (less repetition)
    repetition_score = round(max(0, min(100, (1 - max_sim) * 100)))

    # ── depth_progression_score ───────────────────────────────────────────────
    # Does this step add more than the previous?
    if step_index == 0:
        # First step always gets baseline credit
        depth_score = max(50, completeness)
    else:
        prev_wc = _word_count(prev_text)
        wc_ratio = wc / max(prev_wc, 1)
        new_content_ratio = (unique_wc / max(wc, 1)) if wc > 0 else 0
        depth_score = round(min(100, max(0,
            # Adding more words is positive
            (min(1.2, wc_ratio) / 1.2) * 30 +
            # New content is most important
            new_content_ratio * 50 +
            # Low similarity to previous = good
            (1 - sim_to_prev) * 20
        )))

    # ── Issues ────────────────────────────────────────────────────────────────
    issues: list[dict] = []

    # Critical: very high similarity to any other step
    for other_idx, sim in pairwise.items():
        if sim >= SIM_CRITICAL:
            issues.append({
                "severity": "critical",
                "issue_type": "near_duplicate_step",
                "issue_message": f"Step {step_index + 1} is {int(sim*100)}% similar to Step {other_idx + 1} — near duplicate.",
                "repeated_with_step_number": other_idx + 1,
                "similarity": sim,
                "suggested_fix": (
                    f"Rewrite Step {step_index + 1} to add distinctly new content. "
                    f"It shares {int(sim*100)}% of its words with Step {other_idx + 1}. "
                    "Focus this step on the next pedagogical layer: deeper explanation, "
                    "new worked example, or exam-level application."
                ),
            })
        elif sim >= SIM_HIGH:
            issues.append({
                "severity": "high",
                "issue_type": "high_similarity_step",
                "issue_message": f"Step {step_index + 1} is {int(sim*100)}% similar to Step {other_idx + 1} — high overlap.",
                "repeated_with_step_number": other_idx + 1,
                "similarity": sim,
                "suggested_fix": (
                    f"Reduce overlap with Step {other_idx + 1}. Remove repeated sentences "
                    "and replace them with new examples, a different explanation angle, "
                    "or an exam-style application not covered in the overlapping step."
                ),
            })

    # Critical: too few unique words
    if unique_wc < MIN_UNIQUE_WORDS and wc > 0:
        issues.append({
            "severity": "critical",
            "issue_type": "no_unique_content",
            "issue_message": f"Step {step_index + 1} has only {unique_wc} unique words — adds no new value.",
            "suggested_fix": (
                "Substantially expand this step with content that does not appear in any "
                "other step. Introduce a new sub-concept, add a worked example, or "
                "present a practice problem with a full solution."
            ),
        })

    # High: later step shorter than previous and low new content
    if step_index > 0 and wc < _word_count(prev_text) * 0.7 and unique_wc / max(wc, 1) < 0.25:
        issues.append({
            "severity": "high",
            "issue_type": "no_depth_progression",
            "issue_message": f"Step {step_index + 1} is shorter and adds <25% new content compared to Step {step_index}.",
            "suggested_fix": (
                f"Expand Step {step_index + 1} so it clearly builds on Step {step_index}. "
                "Each later step must deepen the concept — add a harder example, "
                "introduce a formula application, address a common mistake, or add "
                "an exam-style question that could not have appeared in an earlier step."
            ),
        })

    # Medium: repeated sentences
    for rs in rep_sents[:3]:
        issues.append({
            "severity": "medium",
            "issue_type": "repeated_sentence",
            "issue_message": f"Sentence repeated from Step {rs['repeated_in_step_index'] + 1}: \"{rs['sentence'][:80]}…\"",
            "repeated_with_step_number": rs["repeated_in_step_index"] + 1,
            "suggested_fix": (
                "Remove or rephrase this sentence. If the concept is important to repeat, "
                "express it in different words and link it explicitly to the new material "
                "being introduced in this step."
            ),
        })

    # High: repeated MCQs
    for mcq in rep_mcqs[:2]:
        issues.append({
            "severity": "high",
            "issue_type": "repeated_mcq",
            "issue_message": f"MCQ question repeated in another step: \"{mcq}\"",
            "suggested_fix": (
                "Replace this MCQ with a new question that tests a concept or skill "
                "specific to this step's learning objective. MCQs must not be reused "
                "across steps."
            ),
        })

    # Medium: repeated formulas without new explanation
    for fml in rep_fmls[:2]:
        issues.append({
            "severity": "medium",
            "issue_type": "repeated_formula",
            "issue_message": f"Formula repeated without new application: \"{fml}\"",
            "suggested_fix": (
                "Either remove the repeated formula, or retain it only if you add a new "
                "application, derivation step, or worked example that uses it in a way "
                "not shown in the previous step."
            ),
        })

    # Medium: step too short
    if wc < MIN_WORDS_PER_STEP and wc > 0:
        issues.append({
            "severity": "medium",
            "issue_type": "step_too_short",
            "issue_message": f"Step {step_index + 1} has only {wc} words — too short to be useful.",
            "suggested_fix": (
                f"Expand this step to at least {MIN_WORDS_PER_STEP} words. Add a clear "
                "explanation, at least one concrete example, and a brief check question "
                "or summary point."
            ),
        })

    # ── Overall score ─────────────────────────────────────────────────────────
    overall = round(0.30 * uniqueness + 0.25 * depth_score + 0.25 * repetition_score + 0.20 * completeness)

    # Status
    has_critical = any(i["severity"] == "critical" for i in issues)
    has_high     = any(i["severity"] == "high"     for i in issues)
    status = "critical" if has_critical else "warning" if has_high else "pass"
    if len(issues) == 0:
        status = "pass"
    elif issues and not has_critical and not has_high:
        status = "warning"

    return {
        "step_index": step_index,
        "step_number": step_index + 1,
        "step_role": role.get("name", f"Step {step_index + 1}"),
        "word_count": wc,
        "unique_word_count": unique_wc,
        "unique_content_pct": round(unique_wc / max(wc, 1) * 100),
        "similarity_to_previous": sim_to_prev,
        "max_similarity_to_any": max_sim,
        "pairwise_similarities": pairwise,
        "repeated_sentences": rep_sents[:5],
        "repeated_mcqs": rep_mcqs[:3],
        "repeated_formulas": rep_fmls[:3],
        "step_uniqueness_score": uniqueness,
        "depth_progression_score": depth_score,
        "cross_step_repetition_score": repetition_score,
        "step_completeness_score": completeness,
        "overall_step_score": overall,
        "status": status,
        "issues": issues,
    }


# ── Full lesson sequence audit ────────────────────────────────────────────────

def audit_lesson_steps(
    grade: str,
    subject: str,
    chapter: str,
    steps: list[dict],
    lesson_id: str = "",
) -> dict[str, Any]:
    """
    Audit a full lesson step sequence.

    `steps` is a list of dicts: [{"step_number": 1, "step_title": "...", "content": "..."}]

    Returns comprehensive audit result including per-step scores,
    similarity matrix, and a list of repair tasks.
    """
    if not steps:
        return {"error": "No steps provided", "step_results": [], "summary": {}}

    texts = [s.get("content", "") for s in steps]
    n = len(texts)

    # Per-step analysis
    step_results = []
    for i, step in enumerate(steps):
        result = score_step(i, texts[i], texts)
        result["step_title"] = step.get("step_title", f"Step {i + 1}")
        result["lesson_id"]  = lesson_id
        result["grade"]      = grade
        result["subject"]    = subject
        result["chapter"]    = chapter
        step_results.append(result)

    # Full similarity matrix (n × n)
    sim_matrix = []
    for i in range(n):
        row = []
        for j in range(n):
            if i == j:
                row.append(1.0)
            elif j < i:
                row.append(sim_matrix[j][i])
            else:
                row.append(round(combined_similarity(texts[i], texts[j]), 3))
        sim_matrix.append(row)

    # Aggregate scores
    avg_uniqueness   = round(sum(r["step_uniqueness_score"]        for r in step_results) / max(n, 1))
    avg_depth        = round(sum(r["depth_progression_score"]      for r in step_results) / max(n, 1))
    avg_repetition   = round(sum(r["cross_step_repetition_score"]  for r in step_results) / max(n, 1))
    avg_completeness = round(sum(r["step_completeness_score"]      for r in step_results) / max(n, 1))
    overall          = round(0.30 * avg_uniqueness + 0.25 * avg_depth + 0.25 * avg_repetition + 0.20 * avg_completeness)

    all_issues = []
    for r in step_results:
        for issue in r["issues"]:
            all_issues.append({
                **issue,
                "step_number": r["step_number"],
                "step_title":  r["step_title"],
                "step_index":  r["step_index"],
                "lesson_id":   lesson_id,
                "grade": grade, "subject": subject, "chapter": chapter,
            })

    critical_count = sum(1 for i in all_issues if i["severity"] == "critical")
    high_count     = sum(1 for i in all_issues if i["severity"] == "high")
    steps_with_issues = len([r for r in step_results if r["issues"]])

    return {
        "lesson_id": lesson_id,
        "grade": grade,
        "subject": subject,
        "chapter": chapter,
        "num_steps": n,
        "step_results": step_results,
        "similarity_matrix": sim_matrix,
        "all_issues": all_issues,
        "summary": {
            "avg_step_uniqueness_score": avg_uniqueness,
            "depth_progression_score": avg_depth,
            "cross_step_repetition_score": avg_repetition,
            "avg_step_completeness_score": avg_completeness,
            "overall_step_sequence_score": overall,
            "total_issues": len(all_issues),
            "critical_issues": critical_count,
            "high_issues": high_count,
            "steps_with_issues": steps_with_issues,
            "eligible_for_bulk_apply": (
                critical_count == 0 and overall >= 85
            ),
        },
    }


# ── Repair task generation from audit ────────────────────────────────────────

def audit_to_repair_tasks(
    audit_result: dict,
    job_id: str,
    admin_id: str,
) -> list[dict]:
    """
    Convert an audit result into a list of repair task dicts ready for DB insert.

    One repair task is created per step that has at least one issue.
    """
    import uuid as _uuid
    from datetime import datetime, timezone

    tasks = []
    for step_r in audit_result.get("step_results", []):
        if not step_r.get("issues"):
            continue

        # Filter to only the issues for this step
        step_issues = [
            i for i in audit_result.get("all_issues", [])
            if i.get("step_index") == step_r["step_index"]
        ]

        task_id = str(_uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        tasks.append({
            "id": task_id,
            "job_id": job_id,
            "grade":      audit_result.get("grade", ""),
            "subject":    audit_result.get("subject", ""),
            "chapter":    audit_result.get("chapter", ""),
            "step_title": step_r.get("step_title", f"Step {step_r['step_number']}"),
            "original_lesson_cache_id": audit_result.get("lesson_id") or None,
            "status": "queued",
            "issues_json": step_issues,
            "original_content_json": {
                "step_content": "",   # to be filled from lesson_cache
                "step_number": step_r["step_number"],
                "step_title": step_r["step_title"],
                "step_uniqueness_score": step_r["step_uniqueness_score"],
                "depth_progression_score": step_r["depth_progression_score"],
                "cross_step_repetition_score": step_r["cross_step_repetition_score"],
                "step_completeness_score": step_r["step_completeness_score"],
                "overall_step_score": step_r["overall_step_score"],
                "similarity_to_previous": step_r["similarity_to_previous"],
                "unique_content_pct": step_r["unique_content_pct"],
            },
            "audit_before_score": step_r["overall_step_score"],
            "created_at": now,
            "updated_at": now,
        })

    return tasks


# ── Bulk apply eligibility check ──────────────────────────────────────────────

def check_bulk_apply_eligibility(tasks: list[dict], min_score: int = 90, min_depth: int = 85) -> dict:
    """
    Given a list of repair task dicts, determine which are eligible for bulk apply.

    Refuses tasks that:
    - are not in ready_for_review or approved status
    - have audit_after_score below min_score threshold
    - have validation_result_json.valid == False
    - have remaining critical issues in issues_json

    Returns a dry-run summary with per-task skip reasons.
    """
    eligible = []
    skipped  = []

    for task in tasks:
        reason = None
        if task.get("status") not in ("ready_for_review", "approved"):
            reason = f"Status is '{task.get('status')}' — must be ready_for_review or approved"
        elif task.get("audit_after_score") is not None and task["audit_after_score"] < min_score:
            reason = f"After score {task['audit_after_score']} < min {min_score}"
        elif task.get("validation_result_json", {}).get("valid") is False:
            reason = "Validation failed"
        else:
            # Check for remaining critical issues in issues_json
            issues = task.get("issues_json") or []
            remaining_criticals = [
                i for i in issues
                if isinstance(i, dict) and i.get("severity") == "critical"
            ]
            if remaining_criticals:
                reason = (
                    f"Has {len(remaining_criticals)} remaining critical issue(s) "
                    "— resolve all critical issues before bulk apply"
                )

        if reason:
            skipped.append({"task_id": task.get("id"), "reason": reason})
        else:
            eligible.append(task.get("id"))

    return {
        "total": len(tasks),
        "eligible": len(eligible),
        "eligible_task_ids": eligible,
        "skipped": len(skipped),
        "skipped_details": skipped,
        "can_bulk_apply": len(eligible) > 0,
    }


# ── Audit event helper ────────────────────────────────────────────────────────

def write_bulk_apply_audit_event(
    task_id: str,
    grade: str,
    subject: str,
    chapter: str,
    step_title: str,
    admin_id: str,
    published: bool,
    error: str = "",
) -> None:
    """
    Write a structured audit event for a bulk-apply publication.

    Attempts to insert into the admin_audit_log table (if it exists).
    Silently falls back to Python logger if DB is unavailable —
    never blocks a successful publish.
    """
    import logging as _logging
    from datetime import datetime, timezone as _tz

    _alog = _logging.getLogger("likhapoha.audit")
    event = {
        "event_type":  "bulk_apply_publish" if published else "bulk_apply_skip",
        "task_id":     task_id,
        "grade":       grade,
        "subject":     subject,
        "chapter":     chapter,
        "step_title":  step_title,
        "admin_id":    admin_id,
        "published":   published,
        "error":       error or None,
        "occurred_at": datetime.now(_tz.utc).isoformat(),
    }
    _alog.info("[audit:bulk_apply] %s", event)

    # Attempt DB write — silently ignore if table doesn't exist
    try:
        from app.services.auth_service import admin_client  # noqa: PLC0415
        admin_client.table("admin_audit_log").insert(event).execute()
    except Exception:
        pass  # Audit log failure must never block a publish
