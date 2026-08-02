"""
Analyze results.jsonl from doubt_qa_harness.py and print a summary report.

Run from backend/: ../venv/bin/python scripts/doubt_qa_analyze.py
"""
import json
from collections import defaultdict

PATH = "/private/tmp/claude-501/-Users-a0247716/0ff84df7-214d-4ae0-a83b-8c9062438dbc/scratchpad/doubt_qa_harness/results.jsonl"


def load():
    rows = []
    with open(PATH) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def pct(n, d):
    return round(100 * n / d, 1) if d else 0.0


def main():
    rows = load()
    doubt_rows = [r for r in rows if r["surface"] == "ask_doubt_page"]
    followup_rows = [r for r in rows if r["surface"] == "lesson_follow_up"]

    print(f"Total records: {len(rows)} ({len(doubt_rows)} Ask Doubt, {len(followup_rows)} lesson follow-up)\n")

    # --- Overall source_type distribution (Ask Doubt page = primary signal) ---
    dist = defaultdict(int)
    for r in doubt_rows:
        dist[r.get("source_type", "?")] += 1
    print("=== Overall Ask Doubt page source_type distribution ===")
    for k, v in sorted(dist.items(), key=lambda x: -x[1]):
        print(f"  {k:<20} {v:>5}  ({pct(v, len(doubt_rows))}%)")
    print()

    # --- Per grade ---
    by_grade = defaultdict(lambda: defaultdict(int))
    sims_by_grade = defaultdict(list)
    for r in doubt_rows:
        by_grade[r["grade"]][r.get("source_type", "?")] += 1
        if r.get("top_similarity") is not None:
            sims_by_grade[r["grade"]].append(r["top_similarity"])

    print("=== Per grade (Ask Doubt page) ===")
    print(f"{'Grade':<10}{'Total':<8}{'DKB%':<8}{'EXCERPT%':<10}{'FALLBACK%':<11}{'ERROR%':<8}{'AvgSim':<8}")
    for grade in sorted(by_grade, key=lambda g: int(g.split()[1])):
        d = by_grade[grade]
        total = sum(d.values())
        avg_sim = round(sum(sims_by_grade[grade]) / len(sims_by_grade[grade]), 3) if sims_by_grade[grade] else 0
        print(f"{grade:<10}{total:<8}{pct(d.get('DOUBT_KB',0), total):<8}"
              f"{pct(d.get('TEXTBOOK_EXCERPT',0), total):<10}"
              f"{pct(d.get('NO_MATCH_FALLBACK',0), total):<11}"
              f"{pct(d.get('ERROR',0), total):<8}{avg_sim:<8}")
    print()

    # --- Per subject (grade, subject) ---
    by_subj = defaultdict(lambda: defaultdict(int))
    sims_by_subj = defaultdict(list)
    for r in doubt_rows:
        key = (r["grade"], r["subject"])
        by_subj[key][r.get("source_type", "?")] += 1
        if r.get("top_similarity") is not None:
            sims_by_subj[key].append(r["top_similarity"])

    print("=== Per subject (Ask Doubt page), sorted by fallback rate desc ===")
    print(f"{'Grade':<10}{'Subject':<24}{'Total':<7}{'DKB%':<7}{'EXCERPT%':<10}{'FALLBACK%':<11}{'ERR%':<6}{'AvgSim':<7}")
    subj_stats = []
    for key, d in by_subj.items():
        total = sum(d.values())
        fb_pct = pct(d.get('NO_MATCH_FALLBACK', 0), total)
        avg_sim = round(sum(sims_by_subj[key]) / len(sims_by_subj[key]), 3) if sims_by_subj[key] else 0
        subj_stats.append((key, total, d, fb_pct, avg_sim))
    subj_stats.sort(key=lambda x: -x[3])
    for (grade, subject), total, d, fb_pct, avg_sim in subj_stats:
        print(f"{grade:<10}{subject:<24}{total:<7}{pct(d.get('DOUBT_KB',0), total):<7}"
              f"{pct(d.get('TEXTBOOK_EXCERPT',0), total):<10}{fb_pct:<11}{pct(d.get('ERROR',0), total):<6}{avg_sim:<7}")
    print()

    # --- Worst chapters (highest fallback rate, min 3 questions) ---
    by_chapter = defaultdict(lambda: defaultdict(int))
    for r in doubt_rows:
        key = (r["grade"], r["subject"], r["chapter"])
        by_chapter[key][r.get("source_type", "?")] += 1

    worst = []
    for key, d in by_chapter.items():
        total = sum(d.values())
        fb = d.get("NO_MATCH_FALLBACK", 0)
        if fb >= 3:  # majority or all fallback
            worst.append((key, total, fb))
    worst.sort(key=lambda x: -x[2])
    print(f"=== Chapters with >=3/5 NO_MATCH_FALLBACK answers ({len(worst)} chapters) ===")
    for (grade, subject, chapter), total, fb in worst[:60]:
        print(f"  {grade:<10}{subject:<22}{chapter[:50]:<52} {fb}/{total} fallback")
    if len(worst) > 60:
        print(f"  ... and {len(worst) - 60} more")
    print()

    # --- Errors ---
    errors = [r for r in rows if r.get("source_type") == "ERROR"]
    print(f"=== Errors ({len(errors)}) ===")
    for r in errors[:30]:
        print(f"  {r['surface']} {r['grade']} {r['subject']} {r['chapter'][:40]!r} -> {r.get('error')}")
    print()

    # --- Lesson follow-up parity vs Ask Doubt page (same first question) ---
    doubt_first_q = {}
    for r in doubt_rows:
        key = (r["grade"], r["subject"], r["chapter"])
        if key not in doubt_first_q:
            doubt_first_q[key] = r
    mismatches = 0
    for r in followup_rows:
        key = (r["grade"], r["subject"], r["chapter"])
        d = doubt_first_q.get(key)
        if d and d.get("source_type") != r.get("source_type"):
            mismatches += 1
    print(f"=== Surface parity: {mismatches}/{len(followup_rows)} chapters where lesson-widget source_type "
          f"differs from Ask-Doubt-page source_type on the same question ===")

    # --- Timing ---
    times = [r["elapsed_s"] for r in rows if "elapsed_s" in r]
    if times:
        print(f"\nAvg call latency: {round(sum(times)/len(times), 2)}s  "
              f"(min {min(times)}s, max {max(times)}s)")


if __name__ == "__main__":
    main()
