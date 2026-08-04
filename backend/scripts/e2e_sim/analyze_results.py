#!/usr/bin/env python3
"""Analyze results.jsonl from the E2E student journey sweep and produce
structured JSON for the tabular report: per-grade/action accuracy, doubt
source-type distribution, failure root-cause buckets, and curated examples."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS_PATH = HERE / "results.jsonl"
OUT_PATH = HERE / "report_data.json"

GRADE_ORDER = [f"Grade {g}" for g in range(5, 13)]


def load():
    rows = []
    with RESULTS_PATH.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def classify_source_type(st):
    if not st:
        return "unknown"
    s = st.upper()
    if s == "ERROR":
        return "error"
    if "NO_MATCH" in s or "FALLBACK" in s:
        return "fallback_no_direct_answer"
    if "DKB" in s:
        return "dkb_direct_match"
    if "RAG" in s:
        return "rag_excerpt"
    return "other_direct"


def classify_failure_reason(row):
    err = (row.get("error") or row.get("message") or "").lower()
    if "too small for a" in err:
        return "bank_smaller_than_requested_count"
    if "still being prepared" in err or "no questions" in err:
        return "no_bank_content_for_chapter"
    if "missing options" in err:
        return "malformed_question_options"
    if "invalid answer key" in err:
        return "malformed_question_answer_key"
    if "empty explanation" in err:
        return "malformed_question_explanation"
    if "skipped: lesson generation failed" in err:
        return "skipped_upstream_lesson_failure"
    if "skipped: written question generation failed" in err:
        return "skipped_upstream_written_gen_failure"
    if row.get("returned_count") == 0 and "generated successfully" in err:
        return "empty_generation_reported_success"
    if row.get("status") == 401:
        return "auth_error"
    if row.get("status") and row.get("status") >= 500:
        return "server_error_5xx"
    if row.get("status") == 403:
        return "access_denied_403"
    if row.get("status") is None:
        return "network_error"
    return "other"


def main():
    rows = load()
    actions = sorted(set(r["action"] for r in rows))

    # 1) grade x action accuracy matrix
    matrix = defaultdict(lambda: defaultdict(lambda: [0, 0]))  # grade -> action -> [ok, total]
    for r in rows:
        cell = matrix[r["grade"]][r["action"]]
        cell[1] += 1
        if r.get("ok"):
            cell[0] += 1

    matrix_out = {}
    for grade in GRADE_ORDER:
        if grade not in matrix:
            continue
        matrix_out[grade] = {a: matrix[grade][a] for a in actions if a in matrix[grade]}

    # 2) overall per-action accuracy
    overall = defaultdict(lambda: [0, 0])
    for r in rows:
        overall[r["action"]][1] += 1
        if r.get("ok"):
            overall[r["action"]][0] += 1

    # 3) doubt source_type distribution (quality signal beyond binary ok/fail)
    doubt_quality = defaultdict(lambda: Counter())
    for r in rows:
        if r["action"] in ("lesson_followup_doubt", "ask_doubt_page") and r.get("ok"):
            doubt_quality[r["action"]][classify_source_type(r.get("source_type"))] += 1

    # 4) failure root-cause buckets, per action
    failure_buckets = defaultdict(lambda: Counter())
    for r in rows:
        if not r.get("ok"):
            failure_buckets[r["action"]][classify_failure_reason(r)] += 1

    # 5) per-grade x per-subject mock test unit test accuracy (the noisiest action)
    subject_matrix = defaultdict(lambda: [0, 0])  # (grade,subject) -> [ok,total]
    for r in rows:
        if r["action"] == "mock_test_mcq_unit_test":
            key = (r["grade"], r["subject"])
            subject_matrix[key][1] += 1
            if r.get("ok"):
                subject_matrix[key][0] += 1

    subject_matrix_out = [
        {"grade": g, "subject": s, "ok": v[0], "total": v[1]}
        for (g, s), v in subject_matrix.items()
    ]

    # 6) curated failure examples: up to 3 per (action, failure_reason) bucket, spread across grades
    examples = defaultdict(list)
    seen_per_bucket = Counter()
    for r in rows:
        if r.get("ok"):
            continue
        reason = classify_failure_reason(r)
        bucket_key = f"{r['action']}::{reason}"
        if seen_per_bucket[bucket_key] >= 4:
            continue
        seen_per_bucket[bucket_key] += 1
        examples[bucket_key].append({
            "grade": r["grade"], "subject": r["subject"], "chapter": r["chapter"],
            "action": r["action"], "reason": reason, "status": r.get("status"),
            "error": r.get("error") or r.get("message"),
            "question": r.get("question") or r.get("sample_question"),
        })

    # 7) doubt fallback examples (technically "ok" but weak -- no direct answer found)
    fallback_examples = defaultdict(list)
    for r in rows:
        if r.get("ok") and r["action"] in ("lesson_followup_doubt", "ask_doubt_page"):
            if classify_source_type(r.get("source_type")) == "fallback_no_direct_answer":
                key = r["action"]
                if len(fallback_examples[key]) < 6:
                    fallback_examples[key].append({
                        "grade": r["grade"], "subject": r["subject"], "chapter": r["chapter"],
                        "question": r.get("question"), "answer_preview": r.get("answer_preview"),
                    })

    out = {
        "total_records": len(rows),
        "grade_order": [g for g in GRADE_ORDER if g in matrix],
        "actions": actions,
        "matrix": matrix_out,
        "overall": {a: overall[a] for a in actions},
        "doubt_quality": {k: dict(v) for k, v in doubt_quality.items()},
        "failure_buckets": {k: dict(v) for k, v in failure_buckets.items()},
        "subject_matrix": subject_matrix_out,
        "examples": {k: v for k, v in examples.items()},
        "fallback_examples": {k: v for k, v in fallback_examples.items()},
    }
    OUT_PATH.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Wrote analysis to {OUT_PATH}")
    print(f"\nOverall accuracy:")
    for a in actions:
        ok, total = overall[a]
        print(f"  {a}: {ok}/{total} ({100*ok/total:.1f}%)")


if __name__ == "__main__":
    main()
