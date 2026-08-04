#!/usr/bin/env python3
"""Render report_data.json + curated results.jsonl rows into the final HTML
QA report artifact.

Usage:
    ./venv/bin/python build_report.py
    ./venv/bin/python build_report.py --baseline baseline_2026-08-03/report_data.json
"""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT_PATH = HERE / "e2e_report.html"

_parser = argparse.ArgumentParser()
_parser.add_argument("--baseline", default=None, help="Path to an earlier report_data.json to diff against")
_args = _parser.parse_args()

DATA = json.loads((HERE / "report_data.json").read_text(encoding="utf-8"))
BASELINE = json.loads(Path(_args.baseline).read_text(encoding="utf-8")) if _args.baseline else None

ACTION_LABELS = {
    "lesson_generate": "Lesson launch",
    "lesson_followup_doubt": "End-of-lesson doubt",
    "ask_doubt_page": "Ask Doubt page",
    "mock_test_mcq_unit_test": "Mock Test — Class Test (1 chapter)",
    "mock_test_mcq_mid_term": "Mock Test — Mid Term (multi-chapter)",
    "mock_test_mcq_annual": "Mock Test — Annual Exam (full syllabus)",
    "mock_test_written_generate": "Mock Test — Written Practice (generate)",
    "mock_test_written_evaluate": "Mock Test — Written Practice (AI grading)",
}
ACTION_ORDER = list(ACTION_LABELS.keys())

FE_EXAM_TYPE = {
    "mock_test_mcq_unit_test": "Class Test",
    "mock_test_mcq_mid_term": "Mid Term",
    "mock_test_mcq_annual": "Annual Exam",
    "mock_test_written_generate": "Class Test",
    "mock_test_written_evaluate": "Class Test",
}

REASON_LABELS = {
    "no_bank_content_for_chapter": "No questions in bank for this chapter",
    "bank_smaller_than_requested_count": "Bank has fewer questions than requested",
    "malformed_question_options": "Question missing options A-D",
    "malformed_question_answer_key": "Invalid answer key",
    "malformed_question_explanation": "Empty explanation",
    "skipped_upstream_lesson_failure": "Skipped — lesson generation failed first",
    "skipped_upstream_written_gen_failure": "Skipped — written question generation failed first",
    "empty_generation_reported_success": "Reported success but returned 0 questions",
    "auth_error": "Authentication error",
    "server_error_5xx": "Server error (5xx)",
    "access_denied_403": "Access denied (403)",
    "network_error": "Network / connection error",
    "other": "Other",
}


def esc(s):
    return html.escape(str(s if s is not None else ""))


def pct(ok, total):
    return 0 if not total else round(100 * ok / total, 1)


def delta_badge(current_pct, baseline_ok, baseline_total):
    """Small ▲/▼/— badge comparing current_pct against a baseline ok/total pair."""
    if baseline_total is None:
        return ""
    base_pct = pct(baseline_ok, baseline_total)
    diff = round(current_pct - base_pct, 1)
    if diff > 0:
        return f'<span class="delta delta-up">&#9650; +{diff}</span>'
    if diff < 0:
        return f'<span class="delta delta-down">&#9660; {diff}</span>'
    return '<span class="delta delta-flat">&mdash;</span>'


def sev_class(p):
    if p >= 95:
        return "sev-ok"
    if p >= 80:
        return "sev-warn"
    return "sev-bad"


def repro_lesson_steps(grade, subject, chapter):
    return [
        f"Log in as a {esc(grade)} student.",
        "Open <strong>Lessons</strong> in the sidebar (Learn group).",
        f"Select subject <strong>{esc(subject)}</strong> → chapter <strong>{esc(chapter)}</strong>.",
        "Open the “Concept introduction” step.",
    ]


def repro_followup_steps(grade, subject, chapter, question):
    steps = repro_lesson_steps(grade, subject, chapter)
    steps.append("Scroll to “Ask about this chapter” at the bottom of the step.")
    if question:
        steps.append(f"Type: “{esc(question)}” and submit.")
    return steps


def repro_askdoubt_steps(grade, subject, chapter, question):
    steps = [
        f"Log in as a {esc(grade)} student.",
        "Open <strong>Ask Doubt</strong> in the sidebar (Learn group).",
        f"Select subject <strong>{esc(subject)}</strong> → chapter <strong>{esc(chapter)}</strong>.",
    ]
    if question:
        steps.append(f"Type: “{esc(question)}” and submit.")
    return steps


def repro_mocktest_steps(grade, subject, chapter, action, extra=None):
    exam_type = FE_EXAM_TYPE.get(action, "Class Test")
    steps = [
        f"Log in as a {esc(grade)} student.",
        "Open <strong>Mock Test</strong> in the sidebar (Practise &amp; Prepare group).",
        f"Select subject <strong>{esc(subject)}</strong>.",
        f"Set Exam Type to <strong>“{exam_type}”</strong>.",
    ]
    if "written" in action:
        steps.append("Set format to <strong>“Written Practice”</strong>.")
    steps.append(f"Select chapter: <strong>{esc(chapter)}</strong>.")
    steps.append("Click <strong>Generate</strong>.")
    if extra:
        steps.append(extra)
    return steps


def render_steps(steps):
    return "<ol class=\"repro\">" + "".join(f"<li>{s}</li>" for s in steps) + "</ol>"


def build_stat_tiles():
    tiles = []
    for a in ACTION_ORDER:
        ok, total = DATA["overall"][a]
        p = pct(ok, total)
        baseline_ok, baseline_total = (BASELINE["overall"][a] if BASELINE and a in BASELINE["overall"] else (None, None))
        badge = delta_badge(p, baseline_ok, baseline_total) if BASELINE else ""
        tiles.append(f"""
        <div class="tile">
          <div class="tile-label">{esc(ACTION_LABELS[a])}</div>
          <div class="tile-value-row">
            <div class="tile-value {sev_class(p)}">{p}%</div>
            {badge}
          </div>
          <div class="tile-bar"><div class="tile-bar-fill {sev_class(p)}" style="width:{p}%"></div></div>
          <div class="tile-frac">{ok:,} / {total:,}</div>
        </div>""")
    return "".join(tiles)


def build_matrix_table():
    grades = DATA["grade_order"]
    head = "<th class=\"rowhead\">Grade</th>" + "".join(f"<th>{esc(ACTION_LABELS[a])}</th>" for a in ACTION_ORDER)
    rows = []
    for g in grades:
        cells = [f"<td class=\"rowhead\">{esc(g)}</td>"]
        for a in ACTION_ORDER:
            cell = DATA["matrix"].get(g, {}).get(a)
            if not cell:
                cells.append("<td class=\"muted\">—</td>")
                continue
            ok, total = cell
            p = pct(ok, total)
            badge = ""
            if BASELINE:
                base_cell = BASELINE.get("matrix", {}).get(g, {}).get(a)
                if base_cell:
                    badge = delta_badge(p, base_cell[0], base_cell[1])
            cells.append(f'<td class="mcell {sev_class(p)}"><span class="mcell-pct">{p}%</span>'
                          f'<span class="mcell-frac">{ok}/{total}</span>{badge}</td>')
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return f"<table class=\"matrix\"><thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table>"


def build_doubt_quality():
    labels = {
        "dkb_direct_match": "Curated answer (DKB) match",
        "rag_excerpt": "Textbook excerpt (RAG) match",
        "other_direct": "Direct answer returned",
        "fallback_no_direct_answer": "No direct match — generic NCERT-reference fallback",
        "error": "Error",
        "unknown": "Unclassified",
    }
    blocks = []
    for action in ("lesson_followup_doubt", "ask_doubt_page"):
        dist = DATA["doubt_quality"].get(action, {})
        total = sum(dist.values())
        rows = []
        for key in ("dkb_direct_match", "rag_excerpt", "other_direct", "fallback_no_direct_answer", "error", "unknown"):
            n = dist.get(key, 0)
            if n == 0:
                continue
            p = pct(n, total)
            rows.append(f"""
            <div class="qrow">
              <div class="qrow-label">{labels[key]}</div>
              <div class="qrow-bar"><div class="qrow-bar-fill" style="width:{p}%"></div></div>
              <div class="qrow-val">{n:,} <span class="muted">({p}%)</span></div>
            </div>""")
        blocks.append(f"""
        <div class="card">
          <h3>{esc(ACTION_LABELS[action])} — answer quality among successful responses</h3>
          {''.join(rows)}
        </div>""")
    return "".join(blocks)


def build_failure_causes():
    rows = []
    for action in ACTION_ORDER:
        buckets = DATA["failure_buckets"].get(action, {})
        for reason, count in sorted(buckets.items(), key=lambda x: -x[1]):
            rows.append(f"""
            <tr>
              <td>{esc(ACTION_LABELS[action])}</td>
              <td>{esc(REASON_LABELS.get(reason, reason))}</td>
              <td class="num">{count:,}</td>
            </tr>""")
    if not rows:
        return "<p class=\"muted\">No failures recorded.</p>"
    return f"""
    <table class="simple">
      <thead><tr><th>Action</th><th>Root cause</th><th class="num">Count</th></tr></thead>
      <tbody>{''.join(rows)}</tbody>
    </table>"""


def build_worst_subjects():
    sm = sorted(DATA["subject_matrix"], key=lambda x: (x["ok"] / x["total"] if x["total"] else 1))
    baseline_index = {}
    if BASELINE:
        baseline_index = {(r["grade"], r["subject"]): r for r in BASELINE.get("subject_matrix", [])}
    rows = []
    for row in sm[:20]:
        p = pct(row["ok"], row["total"])
        badge = ""
        base_row = baseline_index.get((row["grade"], row["subject"]))
        if base_row:
            badge = delta_badge(p, base_row["ok"], base_row["total"])
        rows.append(f"""
        <tr>
          <td>{esc(row['grade'])}</td>
          <td>{esc(row['subject'])}</td>
          <td class="num {sev_class(p)}">{p}% {badge}</td>
          <td class="num">{row['ok']}/{row['total']}</td>
        </tr>""")
    return f"""
    <table class="simple">
      <thead><tr><th>Grade</th><th>Subject</th><th class="num">Class Test pass rate</th><th class="num">Chapters ok</th></tr></thead>
      <tbody>{''.join(rows)}</tbody>
    </table>"""


def build_examples():
    blocks = []
    for bucket_key, items in DATA["examples"].items():
        action, reason = bucket_key.split("::")
        title = f"{ACTION_LABELS[action]} — {REASON_LABELS.get(reason, reason)}"
        total_in_bucket = DATA["failure_buckets"].get(action, {}).get(reason, len(items))
        rows = []
        for ex in items:
            if "mock_test" in action:
                steps = repro_mocktest_steps(ex["grade"], ex["subject"], ex["chapter"], action)
            else:
                steps = repro_lesson_steps(ex["grade"], ex["subject"], ex["chapter"])
            rows.append(f"""
            <div class="example">
              <div class="example-head">
                <span class="chip">{esc(ex['grade'])}</span>
                <span class="chip">{esc(ex['subject'])}</span>
                <span class="chip chapter">{esc(ex['chapter'])}</span>
              </div>
              <div class="example-error">{esc(ex.get('error') or '')}</div>
              {render_steps(steps)}
            </div>""")
        blocks.append(f"""
        <details class="failgroup">
          <summary>{esc(title)} <span class="muted">({total_in_bucket:,} occurrences, {len(items)} shown)</span></summary>
          {''.join(rows)}
        </details>""")
    return "".join(blocks)


def build_fallback_examples():
    blocks = []
    for action, items in DATA["fallback_examples"].items():
        if not items:
            continue
        rows = []
        for ex in items:
            steps = (repro_followup_steps(ex["grade"], ex["subject"], ex["chapter"], ex.get("question"))
                     if action == "lesson_followup_doubt"
                     else repro_askdoubt_steps(ex["grade"], ex["subject"], ex["chapter"], ex.get("question")))
            rows.append(f"""
            <div class="example">
              <div class="example-head">
                <span class="chip">{esc(ex['grade'])}</span>
                <span class="chip">{esc(ex['subject'])}</span>
                <span class="chip chapter">{esc(ex['chapter'])}</span>
              </div>
              <div class="example-q">Q: {esc(ex.get('question'))}</div>
              <div class="example-a">A: {esc((ex.get('answer_preview') or '')[:220])}…</div>
              {render_steps(steps)}
            </div>""")
        blocks.append(f"""
        <details class="failgroup">
          <summary>{esc(ACTION_LABELS[action])} — generic fallback, no direct match found
            <span class="muted">({len(items)} shown)</span></summary>
          {''.join(rows)}
        </details>""")
    return "".join(blocks)


HTML = f"""<title>Student Journey QA Sweep — Grade 5-12</title>
<style>
:root {{
  --bg: #f5f7fb;
  --panel: #ffffff;
  --ink: #161b24;
  --muted: #5b6478;
  --border: #dce1ec;
  --accent: #2f4a8c;
  --accent-soft: #e7ecfa;
  --ok: #1e8a5a;
  --ok-soft: #e3f4ea;
  --warn: #b8790f;
  --warn-soft: #faf0dd;
  --bad: #c13b3b;
  --bad-soft: #fbe8e6;
  --mono: ui-monospace, "SF Mono", "Cascadia Code", "Roboto Mono", "Consolas", monospace;
  --sans: -apple-system, BlinkMacSystemFont, "Segoe UI", "Helvetica Neue", Arial, sans-serif;
}}
@media (prefers-color-scheme: dark) {{
  :root {{
    --bg: #10141c; --panel: #161b24; --ink: #e7eaf2; --muted: #97a1b8; --border: #2a3244;
    --accent: #7e9ae0; --accent-soft: #1c2740;
    --ok: #49b98a; --ok-soft: #142a22;
    --warn: #d9a23b; --warn-soft: #2c2413;
    --bad: #e36f66; --bad-soft: #2c1817;
  }}
}}
:root[data-theme="dark"] {{
  --bg: #10141c; --panel: #161b24; --ink: #e7eaf2; --muted: #97a1b8; --border: #2a3244;
  --accent: #7e9ae0; --accent-soft: #1c2740;
  --ok: #49b98a; --ok-soft: #142a22;
  --warn: #d9a23b; --warn-soft: #2c2413;
  --bad: #e36f66; --bad-soft: #2c1817;
}}
:root[data-theme="light"] {{
  --bg: #f5f7fb; --panel: #ffffff; --ink: #161b24; --muted: #5b6478; --border: #dce1ec;
  --accent: #2f4a8c; --accent-soft: #e7ecfa;
  --ok: #1e8a5a; --ok-soft: #e3f4ea;
  --warn: #b8790f; --warn-soft: #faf0dd;
  --bad: #c13b3b; --bad-soft: #fbe8e6;
}}
* {{ box-sizing: border-box; }}
body {{
  background: var(--bg); color: var(--ink); font-family: var(--sans);
  margin: 0; padding: 2.5rem 1.5rem 6rem; line-height: 1.5;
}}
.wrap {{ max-width: 68rem; margin: 0 auto; }}
header.page {{ margin-bottom: 2.25rem; }}
.eyebrow {{
  font-family: var(--mono); font-size: .72rem; letter-spacing: .09em; text-transform: uppercase;
  color: var(--accent); margin: 0 0 .5rem;
}}
h1 {{ font-size: 1.85rem; margin: 0 0 .4rem; text-wrap: balance; letter-spacing: -.01em; }}
.subtitle {{ color: var(--muted); font-size: 1rem; max-width: 46rem; margin: 0 0 1rem; }}
.meta {{
  display: flex; flex-wrap: wrap; gap: .5rem 1.25rem; font-family: var(--mono); font-size: .78rem;
  color: var(--muted); border-top: 1px solid var(--border); padding-top: .85rem;
}}
.meta b {{ color: var(--ink); font-weight: 600; }}

h2 {{ font-size: 1.15rem; margin: 0 0 .9rem; letter-spacing: -.005em; }}
h3 {{ font-size: .95rem; margin: 0 0 .75rem; }}
section {{ margin-bottom: 2.5rem; }}
.card {{
  background: var(--panel); border: 1px solid var(--border); border-radius: 8px;
  padding: 1.25rem 1.4rem; margin-bottom: 1rem;
}}

.tiles {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: .75rem; }}
@media (max-width: 900px) {{ .tiles {{ grid-template-columns: repeat(2, 1fr); }} }}
.tile {{ background: var(--panel); border: 1px solid var(--border); border-radius: 8px; padding: .95rem 1.05rem; }}
.tile-label {{ font-size: .74rem; color: var(--muted); margin-bottom: .45rem; min-height: 2.1em; }}
.tile-value-row {{ display: flex; align-items: baseline; gap: .5rem; flex-wrap: wrap; }}
.tile-value {{ font-family: var(--mono); font-size: 1.55rem; font-weight: 600; font-variant-numeric: tabular-nums; }}
.delta {{ font-family: var(--mono); font-size: .74rem; font-weight: 600; padding: .1rem .4rem; border-radius: 4px; white-space: nowrap; }}
.delta-up {{ color: var(--ok); background: var(--ok-soft); }}
.delta-down {{ color: var(--bad); background: var(--bad-soft); }}
.delta-flat {{ color: var(--muted); background: var(--accent-soft); }}
.mcell .delta {{ display: block; margin-top: .15rem; }}
.tile-bar {{ height: 4px; background: var(--border); border-radius: 2px; margin: .5rem 0 .4rem; overflow: hidden; }}
.tile-bar-fill {{ height: 100%; border-radius: 2px; }}
.tile-frac {{ font-family: var(--mono); font-size: .74rem; color: var(--muted); font-variant-numeric: tabular-nums; }}

.sev-ok {{ color: var(--ok); }}
.sev-warn {{ color: var(--warn); }}
.sev-bad {{ color: var(--bad); }}
.tile-bar-fill.sev-ok {{ background: var(--ok); }}
.tile-bar-fill.sev-warn {{ background: var(--warn); }}
.tile-bar-fill.sev-bad {{ background: var(--bad); }}

table {{ border-collapse: collapse; width: 100%; font-variant-numeric: tabular-nums; }}
.tablewrap {{ overflow-x: auto; border: 1px solid var(--border); border-radius: 8px; background: var(--panel); }}
table.matrix {{ min-width: 62rem; }}
table.matrix th, table.matrix td {{ padding: .55rem .7rem; border-bottom: 1px solid var(--border); font-size: .82rem; text-align: center; }}
table.matrix th {{ font-family: var(--mono); font-size: .68rem; text-transform: uppercase; letter-spacing: .04em; color: var(--muted); font-weight: 600; text-align: center; }}
table.matrix .rowhead {{ text-align: left; font-family: var(--sans); font-weight: 600; font-size: .84rem; }}
table.matrix th.rowhead {{ text-transform: none; letter-spacing: 0; font-family: var(--sans); }}
.mcell {{ font-family: var(--mono); }}
.mcell-pct {{ display: block; font-weight: 700; font-size: .92rem; }}
.mcell-frac {{ display: block; font-size: .68rem; opacity: .75; }}
.mcell.sev-ok {{ background: var(--ok-soft); }}
.mcell.sev-warn {{ background: var(--warn-soft); }}
.mcell.sev-bad {{ background: var(--bad-soft); }}
.muted {{ color: var(--muted); }}

table.simple {{ width: 100%; }}
table.simple th {{ text-align: left; font-size: .72rem; text-transform: uppercase; letter-spacing: .05em; color: var(--muted); padding: .6rem .9rem; border-bottom: 1px solid var(--border); }}
table.simple td {{ padding: .55rem .9rem; border-bottom: 1px solid var(--border); font-size: .87rem; }}
table.simple tr:last-child td {{ border-bottom: none; }}
td.num {{ font-family: var(--mono); text-align: right; }}
th.num {{ text-align: right; }}

.qrow {{ display: grid; grid-template-columns: 15rem 1fr 8rem; align-items: center; gap: .75rem; margin-bottom: .5rem; font-size: .84rem; }}
.qrow-bar {{ height: 6px; background: var(--border); border-radius: 3px; overflow: hidden; }}
.qrow-bar-fill {{ height: 100%; background: var(--accent); border-radius: 3px; }}
.qrow-val {{ font-family: var(--mono); text-align: right; font-size: .82rem; }}

details.failgroup {{
  background: var(--panel); border: 1px solid var(--border); border-radius: 8px;
  padding: .1rem 1.1rem; margin-bottom: .65rem;
}}
details.failgroup summary {{
  cursor: pointer; padding: .85rem 0; font-weight: 600; font-size: .92rem; list-style: none;
}}
details.failgroup summary::-webkit-details-marker {{ display: none; }}
details.failgroup summary::before {{ content: "\\25B8"; display: inline-block; margin-right: .5rem; color: var(--accent); transition: transform .15s; }}
details.failgroup[open] summary::before {{ transform: rotate(90deg); }}
details.failgroup summary .muted {{ font-weight: 400; }}

.example {{ border-top: 1px solid var(--border); padding: 1rem 0; }}
.example-head {{ display: flex; gap: .4rem; flex-wrap: wrap; margin-bottom: .55rem; }}
.chip {{
  font-family: var(--mono); font-size: .72rem; padding: .18rem .55rem; border-radius: 4px;
  background: var(--accent-soft); color: var(--accent); border: 1px solid var(--border);
}}
.chip.chapter {{ background: transparent; color: var(--ink); font-weight: 600; }}
.example-error {{ font-family: var(--mono); font-size: .8rem; color: var(--bad); background: var(--bad-soft);
  padding: .5rem .7rem; border-radius: 6px; margin-bottom: .7rem; }}
.example-q {{ font-size: .85rem; margin-bottom: .3rem; }}
.example-a {{ font-size: .85rem; color: var(--muted); margin-bottom: .7rem; }}
ol.repro {{ margin: 0; padding-left: 1.3rem; font-size: .84rem; }}
ol.repro li {{ margin-bottom: .3rem; }}
ol.repro strong {{ font-weight: 600; }}

footer {{ margin-top: 3rem; padding-top: 1.25rem; border-top: 1px solid var(--border); font-size: .78rem; color: var(--muted); }}
footer p {{ margin: 0 0 .5rem; max-width: 48rem; }}
a {{ color: var(--accent); }}
</style>

<div class="wrap">
  <header class="page">
    <p class="eyebrow">Platform QA — Student Journey Sweep</p>
    <h1>Does the platform actually work, grade by grade?</h1>
    <p class="subtitle">One real student account per Grade 5–12 walked every subject and chapter with lesson
      content, through the live API: launched the lesson, asked a follow-up doubt, asked the same doubt again via
      the Ask Doubt page, then generated a Class Test, Mid Term, Annual Exam, and Written Practice test for every
      subject. {DATA['total_records']:,} actions recorded end to end.</p>
    <div class="meta">
      <span><b>Scope:</b> 8 grades &middot; 865 chapters with lesson content &middot; 60 (grade, subject) pairs</span>
      <span><b>Environment:</b> live backend + live database, real test accounts</span>
      <span><b>Method:</b> real HTTP calls to the same routes the frontend uses — not a UI click-through</span>
      {f'<span><b>Comparing against:</b> {esc(_args.baseline)}</span>' if BASELINE else ''}
    </div>
  </header>

  <section>
    <h2>Pass rate by step</h2>
    <div class="tiles">{build_stat_tiles()}</div>
  </section>

  <section>
    <h2>Pass rate by grade</h2>
    <div class="tablewrap">{build_matrix_table()}</div>
  </section>

  <section>
    <h2>Doubt answer quality</h2>
    <p class="subtitle" style="margin-bottom:1rem;">A doubt call can technically succeed (return text) without
      giving a real answer — the retrieval pipeline falls back to a generic “consult your NCERT
      textbook” message when nothing matches. This breaks down what successful answers actually contained.</p>
    {build_doubt_quality()}
  </section>

  <section>
    <h2>Mock test failure causes</h2>
    {build_failure_causes()}
  </section>

  <section>
    <h2>Worst-performing subjects (Class Test)</h2>
    <p class="subtitle" style="margin-bottom:1rem;">Bottom 20 of 60 (grade, subject) pairs by Class Test pass rate
      across their chapters.</p>
    <div class="tablewrap">{build_worst_subjects()}</div>
  </section>

  <section>
    <h2>Failure examples &amp; how to reproduce</h2>
    <p class="subtitle" style="margin-bottom:1rem;">Up to 4 examples per failure category. Steps use the real
      sidebar labels (Lessons / Ask Doubt / Mock Test) and dropdown options.</p>
    {build_examples()}
  </section>

  <section>
    <h2>Weak doubt answers (fallback, not wrong)</h2>
    <p class="subtitle" style="margin-bottom:1rem;">These calls succeeded but returned the generic no-match
      fallback rather than a real answer — worth reviewing even though they don't count as failures above.</p>
    {build_fallback_examples()}
  </section>

  <footer>
    <p><strong>Notes:</strong> "Class Test" / "Mid Term" / "Annual Exam" are the platform's real exam-type labels
      (this report's internal names “Unit Test” / “Annual” map to “Class Test” /
      “Annual Exam”). Mid Term sampled up to 12 chapters per subject, Annual Exam up to 25, both capped
      below the full syllabus for very large subjects to bound run time — not because of any platform limit.
      One Written Practice test was generated per subject (first chapter only), grading validated by submitting
      the question's own expected keywords back as the answer.</p>
    <p>Test accounts: <span style="font-family:var(--mono)">E2ESim-Grade5</span> through
      <span style="font-family:var(--mono)">E2ESim-Grade12</span>, full CBSE access, left in place per your
      request. Source data: <span style="font-family:var(--mono)">backend/scripts/e2e_sim/results.jsonl</span>
      ({DATA['total_records']:,} records).</p>
  </footer>
</div>
"""

OUT_PATH.write_text(HTML, encoding="utf-8")
print(f"Wrote {OUT_PATH} ({len(HTML):,} bytes)")
