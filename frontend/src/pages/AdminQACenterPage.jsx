/**
 * AdminQACenterPage.jsx — Admin Platform QA Center
 * Supports internal module switching: Lesson Quality ↔ Authorization Audit
 * Admin-only. All API calls go to /api/admin/qa/* — require_admin enforced.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { authFetch } from "../api/authClient";
import FeatureAuthAuditPage from "./FeatureAuthAuditPage";
import LessonSectionsAuditPage from "./LessonSectionsAuditPage";

const GRADES = ["Grade 5","Grade 6","Grade 7","Grade 8","Grade 9","Grade 10","Grade 11","Grade 12"];
const SUBJECTS = ["Mathematics","Science","Physics","Chemistry","English","Hindi","Social Science"];
const SEV_COLOR = { critical:"#ef4444", high:"#f59e0b", medium:"#6366f1", low:"#94a3b8" };

function Card({ children, testid, style, onClick }) {
  return (
    <div data-testid={testid} onClick={onClick}
      style={{ background:"var(--panel,#fff)", border:"1px solid var(--border,#e5e7eb)",
        borderRadius:12, padding:"16px 18px", ...style }}>
      {children}
    </div>
  );
}
function SevBadge({ sev }) {
  return <span style={{ fontSize:".68rem", fontWeight:700, padding:"1px 7px", borderRadius:8,
    background:SEV_COLOR[sev]+"20", color:SEV_COLOR[sev] }}>{sev}</span>;
}
function StatCard({ label, value, color="#6366f1", testid }) {
  return (
    <Card testid={testid} style={{ textAlign:"center", minWidth:120 }}>
      <div style={{ fontWeight:800, fontSize:"1.5rem", color }}>{value ?? "—"}</div>
      <div style={{ fontSize:".75rem", color:"var(--text-muted,#64748b)", marginTop:3 }}>{label}</div>
    </Card>
  );
}
function FutureModule({ icon, name }) {
  return (
    <Card style={{ opacity:.55, display:"flex", alignItems:"center", gap:10 }}>
      <span style={{ fontSize:"1.3rem" }}>{icon}</span>
      <div>
        <div style={{ fontWeight:700, fontSize:".82rem" }}>{name}</div>
        <div style={{ fontSize:".7rem", color:"var(--text-muted,#94a3b8)" }}>Coming soon</div>
      </div>
    </Card>
  );
}
function IssueRow({ issue }) {
  const [open, setOpen] = useState(false);
  return (
    <div style={{ borderBottom:"1px solid var(--border,#f1f5f9)", padding:"6px 0" }}>
      <div style={{ display:"flex", alignItems:"center", gap:8, cursor:"pointer" }}
        onClick={() => setOpen(o => !o)}>
        <SevBadge sev={issue.severity}/>
        <span style={{ fontSize:".75rem", fontWeight:600 }}>{issue.grade} · {issue.subject} · {issue.chapter}</span>
        <span style={{ fontSize:".72rem", color:"var(--text-muted,#64748b)", flex:1 }}>{issue.message}</span>
        <span style={{ fontSize:".75rem", color:"#6366f1" }}>{open ? "▲" : "▼"}</span>
      </div>
      {open && (
        <div style={{ marginTop:5, padding:"6px 10px", background:"var(--surface2,#f8fafc)", borderRadius:7, fontSize:".74rem" }}>
          <div><b>Category:</b> {issue.category}</div>
          {issue.detail && <div style={{ marginTop:3, color:"var(--text-muted,#64748b)" }}>{issue.detail}</div>}
          <div style={{ marginTop:5, color:"#94a3b8", fontStyle:"italic" }}>Lesson editor: not yet available</div>
        </div>
      )}
    </div>
  );
}

export default function AdminQACenterPage({ user: _user, setActivePage }) {
  const [activeModule, setActiveModule] = useState("lessonQuality");
  const [report, setReport]         = useState(null);
  const [loadingReport, setLoadingReport] = useState(true);
  const [runForm, setRunForm]       = useState({ mode:"sample", grade:"", subject:"", use_llm:false });
  const [job, setJob]               = useState(null);
  const [running, setRunning]       = useState(false);
  const [runError, setRunError]     = useState(null);
  const [sevFilter, setSevFilter]   = useState("");
  const [catFilter, setCatFilter]   = useState("");
  const pollRef                     = useRef(null);

  const loadLatest = useCallback(async () => {
    setLoadingReport(true);
    try {
      const r = await authFetch("/api/admin/qa/lesson-quality/latest");
      setReport(r?.available ? r : null);
    } catch { setReport(null); }
    finally { setLoadingReport(false); }
  }, []);

  useEffect(() => { loadLatest(); }, [loadLatest]);

  function startPoll(jobId) {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const r = await authFetch(`/api/admin/qa/lesson-quality/status/${jobId}`);
        if (r?.job) {
          setJob(r.job);
          if (r.job.status === "completed" || r.job.status === "failed") {
            clearInterval(pollRef.current);
            setRunning(false);
            if (r.job.status === "completed") loadLatest();
          }
        }
      } catch { clearInterval(pollRef.current); setRunning(false); }
    }, 2000);
  }

  async function handleRunAudit() {
    setRunError(null); setRunning(true); setJob(null);
    try {
      const body = { mode: runForm.mode, use_llm: runForm.use_llm, use_e2e: false };
      if (runForm.grade) body.grade = runForm.grade;
      if (runForm.subject) body.subject = runForm.subject;
      const r = await authFetch("/api/admin/qa/lesson-quality/run", { method: "POST", body: JSON.stringify(body) });
      if (r?.success && r?.job_id) {
        setJob({ id: r.job_id, status: "queued", mode: runForm.mode });
        startPoll(r.job_id);
      } else {
        setRunError(r?.message || "Failed to start audit.");
        setRunning(false);
      }
    } catch { setRunError("Could not start audit. Please try again."); setRunning(false); }
  }

  function handleDownload(fmt) {
    authFetch(`/api/admin/qa/lesson-quality/report?format=${fmt}`)
      .then(text => {
        const blob = new Blob([typeof text === "string" ? text : JSON.stringify(text, null, 2)]);
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob); a.download = `lesson_quality_report.${fmt}`; a.click();
      }).catch(() => {});
  }

  const allIssues = report?.all_issues || [];
  const filtered = allIssues.filter(i => (!sevFilter || i.severity === sevFilter) && (!catFilter || i.category === catFilter));

  return (
    <div data-testid="admin-qa-center" style={{ maxWidth:1100, margin:"0 auto", padding:"0 0 60px", overflowX:"hidden" }}>

      {/* Header */}
      <div style={{ marginBottom:20 }}>
        <h2 style={{ fontWeight:800, fontSize:"1.2rem", margin:"0 0 3px" }}>🧪 Platform QA Center</h2>
        <div style={{ fontSize:".85rem", color:"var(--text-muted,#64748b)" }}>Automated quality audits for lesson content, formulas, and student flows.</div>
      </div>

      {/* Module selector grid */}
      <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(200px,1fr))", gap:10, marginBottom:24 }}>
        <Card testid="module-lesson-quality"
          style={{ borderLeft:"4px solid #6366f1", cursor:"pointer",
            background:activeModule==="lessonQuality"?"#6366f115":"var(--panel,#fff)" }}
          onClick={() => setActiveModule("lessonQuality")}>
          <div style={{ fontWeight:700, fontSize:".85rem" }}>📖 Lesson Quality</div>
          <div style={{ fontSize:".7rem", color:"#22c55e", marginTop:2 }}>
            ● Active{activeModule==="lessonQuality" ? " · Selected" : ""}
          </div>
        </Card>
        <Card testid="module-lesson-sections"
          style={{ borderLeft:"4px solid #22c55e", cursor:"pointer",
            background:activeModule==="lessonSections"?"#22c55e15":"var(--panel,#fff)" }}
          onClick={() => setActiveModule("lessonSections")}>
          <div style={{ fontWeight:700, fontSize:".85rem" }}>📋 8-Section Audit</div>
          <div style={{ fontSize:".7rem", color:"#22c55e", marginTop:2 }}>
            ● Active{activeModule==="lessonSections" ? " · Selected" : ""}
          </div>
        </Card>
        <FutureModule icon="📐" name="Formula Sheet Audit"/>
        <Card testid="module-feature-auth"
          style={{ borderLeft:"4px solid #0ea5e9", cursor:"pointer",
            background:activeModule==="featureAuth"?"#0ea5e915":"var(--panel,#fff)" }}
          onClick={() => setActiveModule("featureAuth")}>
          <div style={{ fontWeight:700, fontSize:".85rem" }}>🔐 Authorization Audit</div>
          <div style={{ fontSize:".7rem", color:"#0ea5e9", marginTop:2 }}>
            ● Active{activeModule==="featureAuth" ? " · Selected" : ""}
          </div>
        </Card>
        <FutureModule icon="💳" name="Payment Flow Audit"/>
        <FutureModule icon="👨‍👩‍👧" name="Parent Flow Audit"/>
        <FutureModule icon="🎓" name="Student Flow Audit"/>
        <FutureModule icon="🌐" name="Browser E2E Tests"/>
        <FutureModule icon="⚡" name="Performance Tests"/>
      </div>

      {/* Feature Authorization Audit — renders inline when selected */}
      {activeModule === "featureAuth" && (
        <div data-testid="module-content-feature-auth">
          <div style={{ display:"flex", alignItems:"center", gap:10, marginBottom:14 }}>
            <button data-testid="back-to-lesson-quality"
              onClick={() => setActiveModule("lessonQuality")}
              style={{ background:"none", border:"1px solid var(--border,#e5e7eb)", borderRadius:7,
                padding:"5px 12px", cursor:"pointer", fontFamily:"inherit", fontSize:".76rem",
                color:"var(--text-muted,#64748b)" }}>
              ← Lesson Quality
            </button>
            <span style={{ fontSize:".82rem", color:"var(--text-muted,#64748b)" }}>
              Platform QA Center → 🔐 Authorization Audit
            </span>
          </div>
          <FeatureAuthAuditPage setActivePage={setActivePage} />
        </div>
      )}

      {/* Lesson Sections Audit module */}
      {activeModule === "lessonSections" && (
        <div data-testid="module-content-lesson-sections">
          <div style={{ display:"flex", alignItems:"center", gap:10, marginBottom:14 }}>
            <button data-testid="back-from-sections"
              onClick={() => setActiveModule("lessonQuality")}
              style={{ background:"none", border:"1px solid var(--border,#e5e7eb)", borderRadius:7,
                padding:"5px 12px", cursor:"pointer", fontFamily:"inherit", fontSize:".76rem",
                color:"var(--text-muted,#64748b)" }}>
              ← Lesson Quality
            </button>
            <span style={{ fontSize:".82rem", color:"var(--text-muted,#64748b)" }}>
              Platform QA Center → 📋 8-Section Audit
            </span>
          </div>
          <LessonSectionsAuditPage setActivePage={setActivePage} />
        </div>
      )}

      {/* Lesson Quality Audit — renders inline when selected */}
      {activeModule === "lessonQuality" && (
        <div data-testid="module-content-lesson-quality">
          <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fit,minmax(280px,1fr))", gap:16, alignItems:"flex-start" }}>
            <Card testid="run-audit-panel">
              <div style={{ fontWeight:700, fontSize:".9rem", marginBottom:12 }}>Run Lesson Quality Audit</div>
              <div style={{ marginBottom:10 }}>
                <div style={{ fontSize:".75rem", fontWeight:600, marginBottom:4 }}>Mode</div>
                <div style={{ display:"flex", gap:6, flexWrap:"wrap" }}>
                  {["sample","grade","subject","full"].map(m => (
                    <button key={m} data-testid={`mode-${m}`}
                      onClick={() => setRunForm(p => ({...p, mode:m}))}
                      style={{ padding:"4px 12px", borderRadius:7, border:"none", cursor:"pointer",
                        fontFamily:"inherit", fontWeight:600, fontSize:".77rem",
                        background:runForm.mode===m?"#6366f1":"var(--surface2,#f1f5f9)",
                        color:runForm.mode===m?"#fff":"var(--text,#374151)" }}>
                      {m==="sample"?"Sample (20)":m.charAt(0).toUpperCase()+m.slice(1)}
                    </button>
                  ))}
                </div>
                {runForm.mode==="full" && (
                  <div style={{ marginTop:6, fontSize:".74rem", color:"#f59e0b", fontStyle:"italic" }}>
                    Full audit may take several minutes.
                  </div>
                )}
              </div>
              {runForm.mode==="grade" && (
                <div style={{ marginBottom:10 }}>
                  <div style={{ fontSize:".75rem", fontWeight:600, marginBottom:3 }}>Grade</div>
                  <select data-testid="grade-selector" value={runForm.grade}
                    onChange={e => setRunForm(p => ({...p, grade:e.target.value}))}
                    style={{ padding:"7px 10px", borderRadius:7, border:"1px solid var(--border,#e5e7eb)", fontFamily:"inherit", fontSize:".82rem", width:"100%" }}>
                    <option value="">All grades</option>
                    {GRADES.map(g => <option key={g} value={g}>{g}</option>)}
                  </select>
                </div>
              )}
              {runForm.mode==="subject" && (
                <div style={{ marginBottom:10 }}>
                  <div style={{ fontSize:".75rem", fontWeight:600, marginBottom:3 }}>Subject</div>
                  <select data-testid="subject-selector" value={runForm.subject}
                    onChange={e => setRunForm(p => ({...p, subject:e.target.value}))}
                    style={{ padding:"7px 10px", borderRadius:7, border:"1px solid var(--border,#e5e7eb)", fontFamily:"inherit", fontSize:".82rem", width:"100%" }}>
                    <option value="">All subjects</option>
                    {SUBJECTS.map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
              )}
              <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:12 }}>
                <input type="checkbox" id="use_llm" checked={runForm.use_llm}
                  onChange={e => setRunForm(p => ({...p, use_llm:e.target.checked}))}/>
                <label htmlFor="use_llm" style={{ fontSize:".78rem", fontWeight:600 }}>LLM Review</label>
                {runForm.use_llm && (
                  <span data-testid="llm-warning" style={{ fontSize:".7rem", color:"#f59e0b" }}>
                    LLM review may use tokens and incur cost.
                  </span>
                )}
              </div>

              <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:14 }}>
                <input type="checkbox" id="use_e2e" disabled/>
                <label htmlFor="use_e2e" style={{ fontSize:".78rem", color:"var(--text-muted,#94a3b8)" }}>Browser E2E Journey</label>
                <span data-testid="e2e-not-configured" style={{ fontSize:".7rem", color:"#94a3b8", fontStyle:"italic" }}>(Not configured yet)</span>
              </div>
              <button data-testid="run-audit-btn" onClick={handleRunAudit} disabled={running}
                style={{ width:"100%", padding:"10px", borderRadius:8, border:"none",
                  background:running?"#94a3b8":"#6366f1", color:"#fff", fontWeight:700,
                  fontSize:".85rem", cursor:running?"not-allowed":"pointer", fontFamily:"inherit" }}>
                {running ? "Audit running..." : "Run Audit"}
              </button>
              {runError && <div style={{ marginTop:8, color:"#dc2626", fontSize:".78rem" }}>{runError}</div>}
            </Card>
            <Card testid="job-status-panel">
              <div style={{ fontWeight:700, fontSize:".9rem", marginBottom:10 }}>Job Status</div>
              {!job ? (
                <div style={{ color:"var(--text-muted,#94a3b8)", fontSize:".82rem" }}>No audit job started yet.</div>
              ) : (
                <div>
                  <div style={{ display:"flex", gap:10, alignItems:"center", marginBottom:8 }}>
                    <span style={{ fontWeight:700, fontSize:".85rem" }}>Job {job.id ? job.id.slice(0,8) : ""}...</span>
                    <span style={{ fontSize:".75rem", fontWeight:700, padding:"2px 8px", borderRadius:8,
                      background:job.status==="completed"?"#dcfce7":job.status==="failed"?"#fee2e2":job.status==="running"?"#ede9fe":"#f1f5f9",
                      color:job.status==="completed"?"#16a34a":job.status==="failed"?"#dc2626":job.status==="running"?"#6366f1":"#94a3b8" }}>
                      {job.status}
                    </span>
                  </div>
                  {job.status==="running" && <div style={{ fontSize:".75rem", color:"#6366f1" }}>Audit in progress... polling every 2s</div>}
                  {job.lessons_audited && <div style={{ fontSize:".75rem", marginTop:4 }}>Lessons: {job.lessons_audited} Score: {job.overall_score}/100</div>}
                  {job.critical_count != null && <div style={{ fontSize:".75rem", color:"#ef4444" }}>Critical: {job.critical_count}</div>}
                  {job.error_message && <div style={{ fontSize:".74rem", color:"#dc2626", marginTop:6 }}>Error: {job.error_message.slice(0,200)}</div>}
                  {job.status==="completed" && <div style={{ fontSize:".74rem", color:"#22c55e", marginTop:6 }}>Report updated below</div>}
                </div>
              )}
            </Card>
          </div>

          {!loadingReport && report && (
            <div style={{ marginTop:24 }}>
              <div style={{ fontWeight:700, fontSize:".9rem", marginBottom:10 }}>Latest Audit Summary</div>
              <div data-testid="summary-cards" style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(130px,1fr))", gap:10, marginBottom:16 }}>
                <StatCard label="Overall Score" value={report.overall_score != null ? report.overall_score+"%" : null} color="#6366f1" testid="stat-overall"/>
                <StatCard label="Critical" value={report.critical_count} color="#ef4444" testid="stat-critical"/>
                <StatCard label="High" value={report.high_count} color="#f59e0b" testid="stat-high"/>
                <StatCard label="Medium" value={report.medium_count} color="#6366f1" testid="stat-medium"/>
                <StatCard label="Low" value={report.low_count} color="#94a3b8" testid="stat-low"/>
                <StatCard label="Lessons Audited" value={report.lessons_audited} testid="stat-lessons"/>
              </div>
              <Card testid="issues-panel" style={{ marginBottom:16 }}>
                <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:10, flexWrap:"wrap", gap:8 }}>
                  <div style={{ fontWeight:700, fontSize:".88rem" }}>All Issues ({filtered.length})</div>
                  <div style={{ display:"flex", gap:8 }}>
                    <select data-testid="sev-filter" value={sevFilter} onChange={e=>setSevFilter(e.target.value)}
                      style={{ padding:"4px 8px", borderRadius:6, border:"1px solid var(--border,#e5e7eb)", fontSize:".76rem", fontFamily:"inherit" }}>
                      <option value="">All Severities</option>
                      {["critical","high","medium","low"].map(s=><option key={s} value={s}>{s}</option>)}
                    </select>
                    <select data-testid="cat-filter" value={catFilter} onChange={e=>setCatFilter(e.target.value)}
                      style={{ padding:"4px 8px", borderRadius:6, border:"1px solid var(--border,#e5e7eb)", fontSize:".76rem", fontFamily:"inherit" }}>
                      <option value="">All Categories</option>
                      {["structure","formula","mcq","pedagogy","flow"].map(ct=><option key={ct} value={ct}>{ct}</option>)}
                    </select>
                  </div>
                </div>
                {filtered.length===0 ? (
                  <div style={{ color:"var(--text-muted,#94a3b8)", fontSize:".82rem" }}>No issues matching filters.</div>
                ) : (
                  filtered.slice(0,100).map((issue,i)=><IssueRow key={i} issue={issue}/>)
                )}
              </Card>
            </div>
          )}

          {!loadingReport && !report && (
            <Card testid="no-report-state" style={{ marginTop:24, textAlign:"center", padding:40 }}>
              <div style={{ fontSize:"2rem", marginBottom:8 }}>📊</div>
              <div style={{ fontWeight:700, fontSize:".95rem", marginBottom:6 }}>No lesson quality audit has been run yet.</div>
              <div style={{ fontSize:".82rem", color:"var(--text-muted,#64748b)" }}>Click Run Audit to start a sample audit.</div>
            </Card>
          )}

          {loadingReport && <div style={{ textAlign:"center", padding:40, color:"var(--text-muted,#94a3b8)" }}>Loading...</div>}

          <Card testid="quality-gates" style={{ marginTop:16 }}>
            <div style={{ fontWeight:700, fontSize:".85rem", marginBottom:8 }}>Quality Gates (defaults)</div>
            <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(160px,1fr))", gap:8, fontSize:".76rem" }}>
              {[["Overall Score",">= 90%"],["Critical Issues","= 0"],["MCQ Score",">= 80%"],["Formula Score",">= 90%"],["Pedagogy Score",">= 85%"]].map(([k,v])=>(
                <div key={k} style={{ padding:"6px 10px", background:"var(--surface2,#f8fafc)", borderRadius:7 }}>
                  <div style={{ fontWeight:600 }}>{k}</div>
                  <div style={{ color:"#6366f1", fontWeight:700 }}>{v}</div>
                </div>
              ))}
            </div>
          </Card>

          {report && (
            <div style={{ display:"flex", gap:8, marginTop:12 }}>
              <div style={{ fontSize:".78rem", color:"var(--text-muted,#64748b)", alignSelf:"center" }}>Download:</div>
              {["json","md","csv"].map(fmt=>(
                <button key={fmt} data-testid={"download-"+fmt} onClick={()=>handleDownload(fmt)}
                  style={{ padding:"5px 12px", borderRadius:7, border:"1px solid var(--border,#e5e7eb)",
                    background:"transparent", color:"#6366f1", fontSize:".76rem", fontWeight:600,
                    cursor:"pointer", fontFamily:"inherit" }}>
                  {fmt.toUpperCase()}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
