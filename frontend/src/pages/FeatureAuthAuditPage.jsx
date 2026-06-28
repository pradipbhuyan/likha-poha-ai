/**
 * FeatureAuthAuditPage.jsx — Feature Authorization Audit
 * Admin-only module in Platform QA Center.
 * Runs audit_feature_authorization.py engine via /api/admin/qa/feature-authorization/*
 * Shows matrix results, failed checks, and remediation hints.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { authFetch } from "../api/authClient";

const SEV_COLOR = { critical:"#ef4444", high:"#f59e0b", pass:"#22c55e", info:"#6366f1" };

function SevBadge({ sev }) {
  const col = SEV_COLOR[sev] || "#94a3b8";
  return <span style={{ fontSize:".68rem", fontWeight:700, padding:"1px 7px", borderRadius:8,
    background:col+"20", color:col }}>{sev}</span>;
}
function StatusBadge({ status }) {
  const col = status==="PASS"?"#22c55e":status==="CRITICAL"?"#ef4444":"#f59e0b";
  return <span style={{ fontWeight:800, fontSize:".85rem", color:col }}>{status}</span>;
}
function Card({ children, testid, style }) {
  return <div data-testid={testid} style={{ background:"var(--panel,#fff)",
    border:"1px solid var(--border,#e5e7eb)", borderRadius:12, padding:"16px 18px", ...style }}>
    {children}
  </div>;
}

function FailedCheckRow({ check }) {
  const [open, setOpen] = useState(false);
  return (
    <div style={{ borderBottom:"1px solid var(--border,#f1f5f9)", padding:"5px 0" }}>
      <div style={{ display:"flex", alignItems:"center", gap:8, cursor:"pointer" }}
        onClick={() => setOpen(o => !o)}>
        <SevBadge sev={check.severity || (check.passed ? "pass" : "high")}/>
        <span style={{ fontSize:".76rem", fontWeight:600, flex:1 }}>{check.scenario}</span>
        <span style={{ fontSize:".7rem", color:"var(--text-muted,#94a3b8)" }}>
          {check.feature} · {check.plan}
        </span>
        <span style={{ color:"#6366f1", fontSize:".72rem" }}>{open?"▲":"▼"}</span>
      </div>
      {open && (
        <div style={{ marginTop:5, padding:"6px 10px", background:"var(--surface2,#f8fafc)", borderRadius:7, fontSize:".73rem" }}>
          <div><b>Expected:</b> {check.expected}  <b>Actual:</b> {check.actual}</div>
          {check.detail && <div style={{ marginTop:3, color:"var(--text-muted,#64748b)" }}>{check.detail}</div>}
          {check.severity === "critical" && (
            <div style={{ marginTop:4, color:"#ef4444", fontWeight:700 }}>
              ⚠️ Critical: This may indicate a Free Tier premium leakage regression.
              Verify feature_authorization_service and subscription resolver immediately.
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function FeatureAuthAuditPage({ user: _user }) {
  const [report, setReport]   = useState(null);
  const [loading, setLoading] = useState(true);
  const [mode, setMode]       = useState("sample");
  const [job, setJob]         = useState(null);
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState(null);
  const [sevFilter, setSevFilter] = useState("");
  const pollRef = useRef(null);

  const loadLatest = useCallback(async () => {
    setLoading(true);
    try {
      const r = await authFetch("/api/admin/qa/feature-authorization/latest");
      setReport(r?.available ? r : null);
    } catch { setReport(null); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { loadLatest(); }, [loadLatest]);

  function startPoll(jobId) {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const r = await authFetch(`/api/admin/qa/feature-authorization/status/${jobId}`);
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

  async function handleRun() {
    setRunError(null); setRunning(true); setJob(null);
    try {
      const r = await authFetch(`/api/admin/qa/feature-authorization/run?mode=${mode}`, { method: "POST" });
      if (r?.success && r?.job_id) {
        setJob({ id: r.job_id, status: "queued", mode });
        startPoll(r.job_id);
      } else {
        setRunError(r?.message || "Failed to start audit.");
        setRunning(false);
      }
    } catch { setRunError("Could not start audit."); setRunning(false); }
  }

  function handleDownload(fmt) {
    authFetch(`/api/admin/qa/feature-authorization/report?format=${fmt}`)
      .then(text => {
        const blob = new Blob([typeof text==="string" ? text : JSON.stringify(text,null,2)]);
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = `feature_authorization_report.${fmt}`;
        a.click();
      }).catch(() => {});
  }

  const summary = report?.summary || {};
  const failedChecks = (report?.failed_checks || []).filter(c =>
    !sevFilter || c.severity === sevFilter
  );

  return (
    <div data-testid="feature-auth-audit-page" style={{ maxWidth:1100, margin:"0 auto", padding:"0 0 60px", overflowX:"hidden" }}>

      {/* Header */}
      <div style={{ marginBottom:16 }}>
        <h2 style={{ fontWeight:800, fontSize:"1.15rem", margin:"0 0 3px" }}>🔐 Feature Authorization Audit</h2>
        <div style={{ fontSize:".85rem", color:"var(--text-muted,#64748b)" }}>
          Verifies feature access matches the canonical matrix across all plans, roles, and scenarios.
          Designed to catch Free Tier premium leakage regressions.
        </div>
      </div>

      {/* Run panel + status */}
      <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fit,minmax(280px,1fr))", gap:14, marginBottom:20 }}>
        <Card testid="fa-run-panel">
          <div style={{ fontWeight:700, fontSize:".88rem", marginBottom:10 }}>Run Authorization Audit</div>
          <div style={{ display:"flex", gap:8, marginBottom:12 }}>
            {["sample","full"].map(m => (
              <button key={m} data-testid={"fa-mode-"+m} onClick={() => setMode(m)}
                style={{ padding:"5px 14px", borderRadius:7, border:"none", cursor:"pointer",
                  fontFamily:"inherit", fontWeight:600, fontSize:".77rem",
                  background:mode===m?"#6366f1":"var(--surface2,#f1f5f9)",
                  color:mode===m?"#fff":"var(--text,#374151)" }}>
                {m==="sample" ? "Sample (fast)" : "Full Audit"}
              </button>
            ))}
          </div>
          {mode==="full" && (
            <div style={{ fontSize:".72rem", color:"#f59e0b", marginBottom:8 }}>
              Full audit checks all features × all plans. May take 30–60s.
            </div>
          )}
          <div style={{ fontSize:".73rem", color:"var(--text-muted,#64748b)", marginBottom:10 }}>
            Checks: Free Tier restrictions · Paid plan access · Expired plan fallback · parentId safety
          </div>
          <button data-testid="fa-run-btn" onClick={handleRun} disabled={running}
            style={{ width:"100%", padding:"9px", borderRadius:8, border:"none",
              background:running?"#94a3b8":"#6366f1", color:"#fff", fontWeight:700,
              fontSize:".85rem", cursor:running?"not-allowed":"pointer", fontFamily:"inherit" }}>
            {running ? "Audit running…" : "▶ Run Authorization Audit"}
          </button>
          {runError && <div style={{ marginTop:6, color:"#dc2626", fontSize:".76rem" }}>{runError}</div>}
        </Card>

        <Card testid="fa-job-status">
          <div style={{ fontWeight:700, fontSize:".88rem", marginBottom:8 }}>Job Status</div>
          {!job ? (
            <div style={{ color:"var(--text-muted,#94a3b8)", fontSize:".82rem" }}>No job started yet.</div>
          ) : (
            <div>
              <div style={{ display:"flex", gap:8, alignItems:"center", marginBottom:6 }}>
                <span style={{ fontWeight:700, fontSize:".82rem" }}>
                  {job.id ? job.id.slice(0,8) : ""}...
                </span>
                <span style={{ fontSize:".72rem", fontWeight:700, padding:"2px 8px", borderRadius:8,
                  background:job.status==="completed"?"#dcfce7":job.status==="failed"?"#fee2e2":"#ede9fe",
                  color:job.status==="completed"?"#16a34a":job.status==="failed"?"#dc2626":"#6366f1" }}>
                  {job.status}
                </span>
                {job.overall && <StatusBadge status={job.overall}/>}
              </div>
              {job.status==="running" && <div style={{ fontSize:".73rem", color:"#6366f1" }}>Running checks... polling every 2s</div>}
              {job.total && <div style={{ fontSize:".73rem", marginTop:3 }}>
                {job.passed}/{job.total} passed · {job.critical||0} critical
              </div>}
              {job.error_message && <div style={{ fontSize:".72rem", color:"#dc2626", marginTop:4 }}>
                {job.error_message.slice(0,150)}
              </div>}
            </div>
          )}
        </Card>
      </div>

      {/* Summary cards */}
      {!loading && report && (
        <div>
          <div data-testid="fa-summary-cards"
            style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(120px,1fr))", gap:10, marginBottom:16 }}>
            {[
              ["Overall",summary.overall,summary.overall==="PASS"?"#22c55e":summary.overall==="CRITICAL"?"#ef4444":"#f59e0b"],
              ["Total",summary.total,"#6366f1"],
              ["Passed",summary.passed,"#22c55e"],
              ["Failed",summary.failed,"#ef4444"],
              ["Critical",summary.critical,"#ef4444"],
              ["Pass Rate",(summary.pass_rate!=null?summary.pass_rate+"%":null),"#6366f1"],
            ].map(([label,value,color]) => (
              <Card key={label} testid={"fa-stat-"+label.toLowerCase().replace(/ /g,"-")}>
                <div style={{ fontWeight:800, fontSize:"1.1rem", color }}>{value ?? "—"}</div>
                <div style={{ fontSize:".72rem", color:"var(--text-muted,#64748b)" }}>{label}</div>
              </Card>
            ))}
          </div>

          {/* Failed checks */}
          <Card testid="fa-failed-checks" style={{ marginBottom:14 }}>
            <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:10, flexWrap:"wrap", gap:8 }}>
              <div style={{ fontWeight:700, fontSize:".88rem" }}>
                Failed Checks ({failedChecks.length})
                {summary.overall==="PASS" && <span style={{ color:"#22c55e", marginLeft:8, fontSize:".78rem" }}>✓ All checks passed</span>}
              </div>
              <select data-testid="fa-sev-filter" value={sevFilter} onChange={e=>setSevFilter(e.target.value)}
                style={{ padding:"4px 8px", borderRadius:6, border:"1px solid var(--border,#e5e7eb)", fontSize:".75rem", fontFamily:"inherit" }}>
                <option value="">All Severities</option>
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="pass">Pass</option>
              </select>
            </div>
            {failedChecks.length===0 ? (
              <div style={{ color:"var(--text-muted,#94a3b8)", fontSize:".82rem" }}>
                {sevFilter ? "No issues matching filter." : "No failed checks."}
              </div>
            ) : failedChecks.map((c,i) => <FailedCheckRow key={i} check={c}/>)}
          </Card>

          {/* Downloads */}
          <div style={{ display:"flex", gap:8, marginBottom:12 }}>
            <div style={{ fontSize:".78rem", color:"var(--text-muted,#64748b)", alignSelf:"center" }}>Download:</div>
            {["json","md","csv"].map(fmt => (
              <button key={fmt} data-testid={"fa-download-"+fmt} onClick={() => handleDownload(fmt)}
                style={{ padding:"5px 12px", borderRadius:7, border:"1px solid var(--border,#e5e7eb)",
                  background:"transparent", color:"#6366f1", fontSize:".75rem", fontWeight:600,
                  cursor:"pointer", fontFamily:"inherit" }}>
                {fmt.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
      )}

      {!loading && !report && (
        <Card testid="fa-no-report" style={{ textAlign:"center", padding:40 }}>
          <div style={{ fontSize:"2rem", marginBottom:8 }}>🔐</div>
          <div style={{ fontWeight:700, fontSize:".95rem", marginBottom:6 }}>No feature authorization audit has been run yet.</div>
          <div style={{ fontSize:".82rem", color:"var(--text-muted,#64748b)" }}>
            Click Run Authorization Audit to verify feature access across all plans and roles.
          </div>
        </Card>
      )}

      {loading && <div style={{ textAlign:"center", padding:40, color:"var(--text-muted,#94a3b8)" }}>Loading...</div>}
    </div>
  );
}
