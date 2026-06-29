/**
 * LessonSectionsAuditPage.jsx — 8-Section Lesson Compliance Audit
 * Shows compliance of lesson content with the 8 canonical sections.
 * Admin-only. Accessed from Platform QA Center.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { authFetch } from "../api/authClient";

const CANONICAL_SECTIONS = [
  "introduction", "what you will learn", "simple explanation",
  "step-by-step breakdown", "worked example", "common mistake",
  "quick check question", "summary",
];

const SEV_COLOR = { critical: "#ef4444", high: "#f97316", medium: "#f59e0b", low: "#94a3b8" };

function Badge({ label, color }) {
  return (
    <span style={{ fontSize: ".68rem", fontWeight: 700, padding: "2px 8px", borderRadius: 8,
      background: color + "20", color }}>{label}</span>
  );
}

function ScoreBar({ pct, color = "#6366f1" }) {
  return (
    <div style={{ height: 6, borderRadius: 3, background: "var(--border,#e5e7eb)", width: "100%" }}>
      <div style={{ height: "100%", borderRadius: 3, width: `${pct}%`,
        background: pct >= 90 ? "#22c55e" : pct >= 70 ? "#f59e0b" : "#ef4444", transition: "width .4s" }} />
    </div>
  );
}

export default function LessonSectionsAuditPage({ setActivePage: _setActivePage }) {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [job, setJob] = useState(null);
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState(null);
  const [grade, setGrade] = useState("");
  const [subject, setSubject] = useState("");
  const [sample, setSample] = useState(true);
  const [sevFilter, setSevFilter] = useState("");
  const [secFilter, setSecFilter] = useState("");
  const pollRef = useRef(null);

  const loadLatest = useCallback(async () => {
    setLoading(true);
    try {
      const r = await authFetch("/api/admin/qa/lesson-sections/latest");
      setReport(r?.available ? r : null);
    } catch { setReport(null); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { loadLatest(); }, [loadLatest]);

  function startPoll(jobId) {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const r = await authFetch(`/api/admin/qa/lesson-sections/status/${jobId}`);
        if (r?.job) {
          setJob(r.job);
          if (r.job.status === "completed" || r.job.status === "failed") {
            clearInterval(pollRef.current);
            setRunning(false);
            if (r.job.status === "completed") loadLatest();
          }
        }
      } catch { clearInterval(pollRef.current); setRunning(false); }
    }, 2500);
  }

  async function handleRun() {
    setRunError(null); setRunning(true); setJob(null);
    try {
      const params = new URLSearchParams({ sample: String(sample) });
      if (grade) params.append("grade", grade);
      if (subject) params.append("subject", subject);
      const r = await authFetch(`/api/admin/qa/lesson-sections/run?${params}`, { method: "POST" });
      if (r?.success && r?.job_id) {
        setJob({ id: r.job_id, status: "queued" });
        startPoll(r.job_id);
      } else { setRunError(r?.message || "Failed to start audit."); setRunning(false); }
    } catch { setRunError("Could not start audit. Please try again."); setRunning(false); }
  }

  function handleDownload(fmt) {
    authFetch(`/api/admin/qa/lesson-sections/report?format=${fmt}`)
      .then(text => {
        const blob = new Blob([typeof text === "string" ? text : JSON.stringify(text, null, 2)]);
        const a = document.createElement("a"); a.href = URL.createObjectURL(blob);
        a.download = `lesson_sections_report.${fmt}`; a.click();
      }).catch(() => {});
  }

  const allIssues = report?.all_issues || [];
  const filtered = allIssues.filter(i =>
    (!sevFilter || i.severity === sevFilter) &&
    (!secFilter || i.section === secFilter)
  );
  const sectionCompliance = report?.section_compliance || {};
  const grades = ["Grade 5","Grade 6","Grade 7","Grade 8","Grade 9","Grade 10","Grade 11","Grade 12"];
  const subjects = ["Mathematics","Science","Physics","Chemistry","English","Hindi","Social Science"];

  return (
    <div data-testid="lesson-sections-audit" style={{ maxWidth: 1100 }}>
      {/* Run panel */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(280px,1fr))", gap: 16, marginBottom: 20 }}>
        <div style={{ background: "var(--panel,#fff)", border: "1px solid var(--border,#e5e7eb)",
          borderRadius: 12, padding: "16px 18px" }} data-testid="sections-run-panel">
          <div style={{ fontWeight: 700, fontSize: ".9rem", marginBottom: 12 }}>Run 8-Section Compliance Audit</div>
          <div style={{ marginBottom: 10 }}>
            <div style={{ fontSize: ".75rem", fontWeight: 600, marginBottom: 3 }}>Grade (optional)</div>
            <select value={grade} onChange={e => setGrade(e.target.value)} data-testid="sections-grade-select"
              style={{ width: "100%", padding: "7px 10px", borderRadius: 7,
                border: "1px solid var(--border,#e5e7eb)", fontFamily: "inherit", fontSize: ".82rem" }}>
              <option value="">All grades</option>
              {grades.map(g => <option key={g} value={g}>{g}</option>)}
            </select>
          </div>
          <div style={{ marginBottom: 10 }}>
            <div style={{ fontSize: ".75rem", fontWeight: 600, marginBottom: 3 }}>Subject (optional)</div>
            <select value={subject} onChange={e => setSubject(e.target.value)} data-testid="sections-subject-select"
              style={{ width: "100%", padding: "7px 10px", borderRadius: 7,
                border: "1px solid var(--border,#e5e7eb)", fontFamily: "inherit", fontSize: ".82rem" }}>
              <option value="">All subjects</option>
              {subjects.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
            <input type="checkbox" id="sections-sample" checked={sample}
              onChange={e => setSample(e.target.checked)} />
            <label htmlFor="sections-sample" style={{ fontSize: ".78rem", fontWeight: 600 }}>
              Sample mode (15 random lessons)
            </label>
          </div>
          <button data-testid="run-sections-btn" onClick={handleRun} disabled={running}
            style={{ width: "100%", padding: "10px", borderRadius: 8, border: "none",
              background: running ? "#94a3b8" : "#6366f1", color: "#fff", fontWeight: 700,
              fontSize: ".85rem", cursor: running ? "not-allowed" : "pointer", fontFamily: "inherit" }}>
            {running ? "Audit running…" : "▶ Run Sections Audit"}
          </button>
          {runError && <div style={{ marginTop: 8, color: "#dc2626", fontSize: ".78rem" }}>{runError}</div>}
        </div>

        {/* Job status */}
        <div style={{ background: "var(--panel,#fff)", border: "1px solid var(--border,#e5e7eb)",
          borderRadius: 12, padding: "16px 18px" }} data-testid="sections-job-panel">
          <div style={{ fontWeight: 700, fontSize: ".9rem", marginBottom: 10 }}>Job Status</div>
          {!job ? (
            <div style={{ color: "#94a3b8", fontSize: ".82rem" }}>No audit running.</div>
          ) : (
            <div>
              <div style={{ fontSize: ".78rem", marginBottom: 6 }}>
                Job: <span style={{ fontWeight: 700 }}>{job.id?.slice(0,8)}...</span>
                {" "}<Badge label={job.status} color={job.status === "completed" ? "#22c55e" : job.status === "failed" ? "#ef4444" : "#6366f1"} />
              </div>
              {job.status === "running" && <div style={{ fontSize: ".75rem", color: "#6366f1" }}>Auditing lessons…</div>}
              {job.lessons_audited != null && <div style={{ fontSize: ".75rem" }}>Lessons: {job.lessons_audited}</div>}
              {job.section_compliance_pct != null && <div style={{ fontSize: ".75rem" }}>Section compliance: {job.section_compliance_pct}%</div>}
              {job.status === "completed" && <div style={{ fontSize: ".74rem", color: "#22c55e", marginTop: 6 }}>Report updated below ↓</div>}
              {job.error_message && <div style={{ fontSize: ".74rem", color: "#dc2626" }}>Error: {job.error_message.slice(0, 200)}</div>}
            </div>
          )}
        </div>
      </div>

      {loadingState(loading, report)}

      {report && (
        <>
          {/* Summary */}
          <div style={{ display: "flex", flexWrap: "wrap", gap: 10, marginBottom: 20 }}>
            {[
              { label: "Lessons Audited", value: report.lessons_audited, color: "#6366f1", tid: "stat-lessons-audited" },
              { label: "Avg Score", value: report.avg_overall_score != null ? report.avg_overall_score + "%" : "—", color: report.avg_overall_score >= 90 ? "#22c55e" : report.avg_overall_score >= 70 ? "#f59e0b" : "#ef4444", tid: "stat-avg-score" },
              { label: "Critical Issues", value: report.critical_issues, color: "#ef4444", tid: "stat-sections-critical" },
              { label: "Section Compliance", value: report.section_compliance_pct != null ? report.section_compliance_pct + "%" : "—", color: "#0ea5e9", tid: "stat-compliance-pct" },
              { label: "Overall", value: report.overall, color: report.overall === "PASS" ? "#22c55e" : "#ef4444", tid: "stat-overall-status" },
            ].map(({ label, value, color, tid }) => (
              <div key={tid} data-testid={tid} style={{ background: "var(--panel,#fff)",
                border: "1px solid var(--border,#e5e7eb)", borderRadius: 10, padding: "14px 18px",
                flex: "1 1 130px", minWidth: 120 }}>
                <div style={{ fontWeight: 800, fontSize: "1.4rem", color }}>{value ?? "—"}</div>
                <div style={{ fontSize: ".75rem", color: "#64748b", marginTop: 3 }}>{label}</div>
              </div>
            ))}
          </div>

          {/* Section compliance bars */}
          <div style={{ background: "var(--panel,#fff)", border: "1px solid var(--border,#e5e7eb)",
            borderRadius: 12, padding: "16px 18px", marginBottom: 20 }} data-testid="section-compliance-bars">
            <div style={{ fontWeight: 700, fontSize: ".88rem", marginBottom: 12 }}>Section Compliance (% of lessons with section)</div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(220px,1fr))", gap: 12 }}>
              {CANONICAL_SECTIONS.map(sec => {
                const pct = sectionCompliance[sec] ?? 0;
                return (
                  <div key={sec}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: ".76rem", marginBottom: 3 }}>
                      <span style={{ textTransform: "capitalize" }}>{sec}</span>
                      <span style={{ fontWeight: 700, color: pct >= 90 ? "#22c55e" : pct >= 70 ? "#f59e0b" : "#ef4444" }}>{pct}%</span>
                    </div>
                    <ScoreBar pct={pct} />
                  </div>
                );
              })}
            </div>
          </div>

          {/* Worst lessons */}
          {report.worst_lessons?.length > 0 && (
            <div style={{ background: "var(--panel,#fff)", border: "1px solid var(--border,#e5e7eb)",
              borderRadius: 12, padding: "16px 18px", marginBottom: 20 }} data-testid="worst-lessons">
              <div style={{ fontWeight: 700, fontSize: ".88rem", marginBottom: 10 }}>Lowest Scoring Lessons (Top 10)</div>
              {report.worst_lessons.map((w, i) => (
                <div key={i} style={{ display: "flex", gap: 10, alignItems: "center", padding: "6px 0",
                  borderBottom: "1px solid var(--border,#f1f5f9)", flexWrap: "wrap" }}>
                  <span style={{ fontSize: ".75rem", fontWeight: 700, color: w.overall_score < 50 ? "#ef4444" : "#f59e0b" }}>{w.overall_score}%</span>
                  <span style={{ fontSize: ".75rem", flex: 1 }}>{w.grade} · {w.subject} · {w.chapter}</span>
                  <span style={{ fontSize: ".72rem", color: "#64748b" }}>{w.step_title}</span>
                  {w.missing_sections?.length > 0 && (
                    <span style={{ fontSize: ".68rem", color: "#ef4444" }}>Missing: {w.missing_sections.join(", ")}</span>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Issues table */}
          <div style={{ background:"var(--panel,#fff)", border:"1px solid var(--border,#e5e7eb)",
            borderRadius:12, padding:"16px 18px", marginBottom:20 }} data-testid="sections-issues-table">
            <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:10, flexWrap:"wrap", gap:8 }}>
              <div style={{ fontWeight:700, fontSize:".88rem" }}>Issues ({filtered.length} critical + high)</div>
              <div style={{ display:"flex", gap:8 }}>
                <select value={sevFilter} onChange={e=>setSevFilter(e.target.value)} data-testid="sev-filter"
                  style={{ padding:"4px 8px", borderRadius:6, border:"1px solid var(--border,#e5e7eb)", fontSize:".76rem", fontFamily:"inherit" }}>
                  <option value="">All Severities</option>
                  {["critical","high"].map(s=><option key={s} value={s}>{s}</option>)}
                </select>
                <select value={secFilter} onChange={e=>setSecFilter(e.target.value)} data-testid="sec-filter"
                  style={{ padding:"4px 8px", borderRadius:6, border:"1px solid var(--border,#e5e7eb)", fontSize:".76rem", fontFamily:"inherit" }}>
                  <option value="">All Sections</option>
                  {CANONICAL_SECTIONS.map(s=><option key={s} value={s} style={{textTransform:"capitalize"}}>{s}</option>)}
                </select>
              </div>
            </div>
            {filtered.length === 0 ? (
              <div style={{ color:"#94a3b8", fontSize:".82rem" }}>No issues matching filters.</div>
            ) : (
              filtered.slice(0, 100).map((issue, i) => (
                <div key={i} style={{ padding:"7px 0", borderBottom:"1px solid var(--border,#f1f5f9)",
                  display:"flex", gap:10, alignItems:"flex-start", flexWrap:"wrap" }}>
                  <Badge label={issue.severity} color={SEV_COLOR[issue.severity] || "#94a3b8"} />
                  <span style={{ fontSize:".74rem", fontWeight:600, minWidth:120, textTransform:"capitalize" }}>{issue.section}</span>
                  <span style={{ fontSize:".74rem", flex:1 }}>{issue.issue}</span>
                  {issue.suggestion && (
                    <span style={{ fontSize:".72rem", color:"#0ea5e9", fontStyle:"italic" }}>💡 {issue.suggestion}</span>
                  )}
                </div>
              ))
            )}
          </div>

          {/* Downloads */}
          <div style={{ display:"flex", gap:8, marginBottom:10 }}>
            <div style={{ fontSize:".78rem", color:"#64748b", alignSelf:"center" }}>Download:</div>
            {["json","csv"].map(fmt => (
              <button key={fmt} data-testid={"download-sections-"+fmt} onClick={()=>handleDownload(fmt)}
                style={{ padding:"5px 12px", borderRadius:7, border:"1px solid var(--border,#e5e7eb)",
                  background:"transparent", color:"#6366f1", fontSize:".76rem", fontWeight:600,
                  cursor:"pointer", fontFamily:"inherit" }}>
                {fmt.toUpperCase()}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function loadingState(loading, report) {
  if (loading) return <div style={{ textAlign:"center", padding:40, color:"#94a3b8" }}>Loading...</div>;
  if (!loading && !report) return (
    <div style={{ textAlign:"center", padding:40 }} data-testid="sections-no-report">
      <div style={{ fontSize:"2rem", marginBottom:8 }}>📋</div>
      <div style={{ fontWeight:700 }}>No sections audit has been run yet.</div>
      <div style={{ fontSize:".82rem", color:"#64748b" }}>Click "Run Sections Audit" above to start.</div>
    </div>
  );
  return null;
}
