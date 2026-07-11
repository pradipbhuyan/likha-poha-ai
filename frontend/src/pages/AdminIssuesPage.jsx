/**
 * AdminIssuesPage.jsx — Product Bugs / Student Feedback
 * Admin-only. Shows all submitted issue reports with filters + detail drawer.
 */
import { useCallback, useEffect, useState } from "react";
import { authFetch } from "../api/authClient";

const STATUS_COLOR = {
  open: "#6366f1", triaged: "#f59e0b", in_progress: "#0ea5e9",
  fixed: "#22c55e", wont_fix: "#94a3b8", duplicate: "#cbd5e1",
};
const SEV_COLOR = { critical: "#ef4444", high: "#f97316", medium: "#f59e0b", low: "#94a3b8" };

const ISSUE_TYPE_LABELS = {
  content_issue: "Content Issue", wrong_explanation: "Wrong Explanation",
  missing_section: "Missing Section", wrong_formula: "Wrong Formula",
  wrong_answer: "Wrong Answer/MCQ", broken_page: "Broken Page",
  login_issue: "Login/Access", other: "Other",
};

function Badge({ label, color }) {
  return (
    <span style={{ fontSize: ".68rem", fontWeight: 700, padding: "2px 8px", borderRadius: 8,
      background: color + "20", color }}>{label}</span>
  );
}

function SummaryCard({ label, value, color = "#6366f1", testid }) {
  return (
    <div data-testid={testid} style={{ background: "var(--panel,#fff)",
      border: "1px solid var(--border,#e5e7eb)", borderRadius: 10, padding: "14px 18px",
      flex: "1 1 130px", minWidth: 120 }}>
      <div style={{ fontWeight: 800, fontSize: "1.5rem", color }}>{value ?? "—"}</div>
      <div style={{ fontSize: ".75rem", color: "#64748b", marginTop: 3 }}>{label}</div>
    </div>
  );
}

// Content issue types where lesson cache can be cleared + rewarmed
const CONTENT_ISSUE_TYPES = new Set([
  "content_issue", "wrong_explanation", "missing_section", "wrong_formula", "wrong_answer",
]);

function IssueDrawer({ issue, onClose, onUpdate }) {
  const [notes, setNotes] = useState(issue?.admin_notes || "");
  const [status, setStatus] = useState(issue?.status || "open");
  const [saving, setSaving] = useState(false);
  const [rewarming, setRewarming] = useState(false);
  const [autoFixing, setAutoFixing] = useState(false);
  const [msg, setMsg] = useState(null);

  useEffect(() => {
    if (issue) { setNotes(issue.admin_notes || ""); setStatus(issue.status); }
  }, [issue]);

  async function handleSave() {
    setSaving(true); setMsg(null);
    try {
      const r = await authFetch(`/api/admin/issues/${issue.id}`, {
        method: "PATCH",
        body: JSON.stringify({ status, admin_notes: notes }),
      });
      if (r.success) { setMsg("Saved"); onUpdate(r.issue); }
    } catch (e) { setMsg("Error: " + e.message); }
    finally { setSaving(false); }
  }

  if (!issue) return null;

  const STATUSES = ["open","triaged","in_progress","fixed","wont_fix","duplicate"];

  return (
    <div data-testid="issue-drawer" style={{
      position: "fixed", right: 0, top: 0, bottom: 0, width: 400, maxWidth: "95vw",
      background: "var(--panel,#fff)", boxShadow: "-8px 0 30px rgba(0,0,0,0.15)",
      zIndex: 1000, overflowY: "auto", padding: "20px 22px",
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h3 style={{ margin: 0, fontWeight: 800, fontSize: ".95rem" }}>Issue Details</h3>
        <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", fontSize: "1.2rem", color: "#94a3b8" }}>✕</button>
      </div>

      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 14 }}>
        <Badge label={issue.severity} color={SEV_COLOR[issue.severity] || "#94a3b8"} />
        <Badge label={issue.status?.replace("_"," ")} color={STATUS_COLOR[issue.status] || "#94a3b8"} />
        <Badge label={ISSUE_TYPE_LABELS[issue.issue_type] || issue.issue_type} color="#6366f1" />
      </div>

      {issue.title && <p style={{ fontWeight: 700, margin: "0 0 8px", fontSize: ".9rem" }}>{issue.title}</p>}

      <div style={{ background: "var(--surface2,#f8fafc)", borderRadius: 8, padding: "10px 12px", marginBottom: 14 }}>
        <div style={{ fontSize: ".72rem", fontWeight: 600, color: "#64748b", marginBottom: 4 }}>DESCRIPTION</div>
        <p style={{ margin: 0, fontSize: ".83rem", lineHeight: 1.6 }}>{issue.description}</p>
      </div>

      {/* Screenshot — shown if browser_info.screenshotDataUrl is present */}
      {issue.browser_info?.screenshotDataUrl && (
        <div style={{ marginBottom: 14 }}>
          <div style={{ fontSize: ".72rem", fontWeight: 700, color: "#64748b", marginBottom: 6 }}>
            SCREENSHOT
          </div>
          <img src={issue.browser_info.screenshotDataUrl} alt="Issue screenshot"
            data-testid="issue-screenshot"
            style={{ width: "100%", borderRadius: 8, border: "1px solid var(--border,#e5e7eb)",
              display: "block", maxHeight: 280, objectFit: "contain", background: "#000" }} />
        </div>
      )}

      {/* Context */}
      <div style={{ background: "var(--surface2,#f8fafc)", borderRadius: 8, padding: "10px 12px", marginBottom: 14, fontSize: ".78rem" }}>
        <div style={{ fontWeight: 600, color: "#64748b", marginBottom: 6 }}>CONTEXT</div>
        {[
          ["Role", issue.reporter_role],
          ["Grade", issue.grade],
          ["Subject", issue.subject],
          ["Chapter", issue.chapter],
          ["Lesson Step", issue.lesson_step],
          ["Route", issue.route],
          ["Viewport", issue.browser_info?.viewportWidth ? (issue.browser_info.viewportWidth + "x" + issue.browser_info.viewportHeight) : null],
          ["DPR", issue.browser_info?.devicePixelRatio ? String(issue.browser_info.devicePixelRatio) : null],
          ["Platform", issue.browser_info?.platform || null],
          ["Font (lesson)", issue.browser_info?.computedFont ? issue.browser_info.computedFont.split(",")[0].trim() : null],
          ["JS Errors", issue.browser_info?.recentJsErrors?.length > 0 ? (issue.browser_info.recentJsErrors.length + " logged") : null],
          ["Reported", issue.created_at ? new Date(issue.created_at).toLocaleString() : null],
        ].filter(([, v]) => v).map(([k, v]) => (
          <div key={k} style={{ display: "flex", gap: 6, marginBottom: 3 }}>
            <span style={{ fontWeight: 600, minWidth: 80 }}>{k}:</span>
            <span style={{ color: "#374151" }}>{v}</span>
          </div>
        ))}
      </div>

      {/* Status update */}
      <div style={{ marginBottom: 12 }}>
        <label style={{ fontSize: ".78rem", fontWeight: 600, display: "block", marginBottom: 4 }}>Status</label>
        <select value={status} onChange={e => setStatus(e.target.value)} data-testid="issue-status-select"
          style={{ width: "100%", padding: "8px", borderRadius: 7, border: "1px solid var(--border,#e5e7eb)",
            fontFamily: "inherit", fontSize: ".82rem" }}>
          {STATUSES.map(s => <option key={s} value={s}>{s.replace("_"," ")}</option>)}
        </select>
      </div>

      {/* Admin notes */}
      <div style={{ marginBottom: 14 }}>
        <label style={{ fontSize: ".78rem", fontWeight: 600, display: "block", marginBottom: 4 }}>Admin Notes</label>
        <textarea value={notes} onChange={e => setNotes(e.target.value)} rows={4}
          data-testid="admin-notes-input"
          placeholder="Add internal notes about this issue..."
          style={{ width: "100%", padding: "8px 10px", borderRadius: 7,
            border: "1px solid var(--border,#e5e7eb)", fontFamily: "inherit", fontSize: ".82rem",
            resize: "vertical", boxSizing: "border-box" }} />
      </div>

      <button onClick={handleSave} disabled={saving} data-testid="save-issue-btn"
        style={{ width: "100%", padding: "10px", borderRadius: 8, border: "none",
          background: saving ? "#94a3b8" : "#6366f1", color: "#fff", fontWeight: 700,
          fontSize: ".85rem", cursor: saving ? "not-allowed" : "pointer", fontFamily: "inherit" }}>
        {saving ? "Saving…" : "Save Changes"}
      </button>
      {msg && <div style={{ marginTop: 8, fontSize: ".78rem", color: msg.startsWith("Error") ? "#dc2626" : "#22c55e" }}>{msg}</div>}

      {/* Fix with AI + Rewarm — only for content issues with lesson context */}
      {CONTENT_ISSUE_TYPES.has(issue.issue_type) && issue.grade && issue.subject && issue.chapter && (
        <div style={{ marginTop: 14, borderTop: "1px solid var(--border,#e5e7eb)", paddingTop: 14 }}>
          <div style={{ fontSize: ".76rem", fontWeight: 600, color: "#64748b", marginBottom: 6 }}>
            🔧 Fix Content Issue
          </div>
          <p style={{ fontSize: ".74rem", color: "#64748b", margin: "0 0 10px", lineHeight: 1.5 }}>
            Clears the cached lesson for <strong>{issue.chapter}</strong>
            {issue.lesson_step ? ` (step: ${issue.lesson_step})` : " (all steps)"}
            , regenerates with the corrected AI prompt, and marks this issue as fixed — all in one cycle.
          </p>
          <button
            data-testid="fix-and-rewarm-btn"
            disabled={rewarming || issue.status === "fixed"}
            onClick={async () => {
              if (!window.confirm(`Clear lesson cache and regenerate "${issue.chapter}" for ${issue.grade} ${issue.subject}? This will mark the issue as fixed.`)) return;
              setRewarming(true); setMsg(null);
              try {
                const r = await authFetch(`/api/admin/issues/${issue.id}/fix-and-rewarm`, { method: "POST" });
                if (r.success) {
                  setMsg(`✅ ${r.message}`);
                  onUpdate(r.issue);
                }
              } catch (e) { setMsg("Error: " + e.message); }
              finally { setRewarming(false); }
            }}
            style={{
              width: "100%", padding: "10px", borderRadius: 8, border: "none",
              background: rewarming || issue.status === "fixed" ? "#94a3b8" : "#10b981",
              color: "#fff", fontWeight: 700, fontSize: ".85rem",
              cursor: rewarming || issue.status === "fixed" ? "not-allowed" : "pointer",
              fontFamily: "inherit",
            }}>
            {rewarming ? "⏳ Clearing cache + queuing rewarm…" : issue.status === "fixed" ? "✓ Already Fixed" : "🔧 Fix with AI + Rewarm Lesson"}
          </button>
        </div>
      )}

      {/* ── Cosmetic Auto-Fix ── */}
      {issue.status !== "fixed" && issue.status !== "wont_fix" && (
        <div style={{ marginTop: 14, borderTop: "1px solid var(--border,#e5e7eb)", paddingTop: 14 }}>
          <div style={{ fontSize: ".76rem", fontWeight: 600, color: "#64748b", marginBottom: 6 }}>
            ⚡ Cosmetic Auto-Fix
          </div>
          <p style={{ fontSize: ".74rem", color: "#64748b", margin: "0 0 10px", lineHeight: 1.5 }}>
            Automatically detect and fix cosmetic issues (font, layout, colour, mobile rendering)
            using keyword matching. Marks the issue as <strong>fixed</strong> with a detailed note.
          </p>
          <button
            data-testid="auto-fix-btn"
            disabled={autoFixing}
            onClick={async () => {
              setAutoFixing(true); setMsg(null);
              try {
                const r = await authFetch(`/api/admin/issues/${issue.id}/auto-fix`, { method: "POST" });
                if (r.success && r.auto_fixable) {
                  setMsg(`✅ Auto-fixed (${r.rule_applied}): ${r.fix_note.slice(0, 120)}…`);
                  setNotes(r.fix_note);
                  setStatus("fixed");
                  onUpdate(r.issue);
                } else if (r.success === false && r.auto_fixable === false) {
                  setMsg(`⚠️ Not auto-fixable: ${r.message}`);
                } else {
                  setMsg(r.message || "Unknown response");
                }
              } catch (e) { setMsg("❌ " + e.message); }
              finally { setAutoFixing(false); }
            }}
            style={{
              width: "100%", padding: "10px", borderRadius: 8, border: "none",
              background: autoFixing ? "#94a3b8" : "linear-gradient(135deg,#f59e0b,#d97706)",
              color: "#fff", fontWeight: 700, fontSize: ".85rem",
              cursor: autoFixing ? "not-allowed" : "pointer", fontFamily: "inherit",
            }}>
            {autoFixing ? "⏳ Analysing and applying fix…" : "⚡ Apply Cosmetic Auto-Fix"}
          </button>
        </div>
      )}

      {/* Copy for Codex */}
      <div style={{ marginTop:16, borderTop:"1px solid var(--border,#e5e7eb)", paddingTop:14 }}>
        <div style={{ fontSize:".76rem", fontWeight:600, color:"#64748b", marginBottom:8 }}>
          🤖 Fix with AI (Copy for Codex)
        </div>
        <button data-testid="copy-for-codex-btn"
          onClick={() => {
            const bi = issue.browser_info || {};
            const prompt = [
              "# Bug Report — Likhapoha AI Platform",
              "",
              `**Issue Type:** ${issue.issue_type?.replace("_"," ")}`,
              `**Severity:** ${issue.severity}`,
              `**Status:** ${issue.status}`,
              `**Reported:** ${issue.created_at ? new Date(issue.created_at).toLocaleString() : "unknown"}`,
              "",
              "## Description",
              issue.description || "",
              "",
              "## Context",
              `- **Route/Page:** ${issue.route || bi.url || "unknown"}`,
              `- **Role:** ${issue.reporter_role || "unknown"}`,
              `- **Grade:** ${issue.grade || bi.grade || "unknown"}`,
              `- **Subject:** ${issue.subject || bi.subject || "unknown"}`,
              `- **Chapter:** ${issue.chapter || bi.chapter || "unknown"}`,
              `- **Lesson Step:** ${issue.lesson_step || bi.lessonStep || "unknown"}`,
              bi.lessonStepIndex != null ? `- **Step Index:** ${Number(bi.lessonStepIndex)+1} of ${bi.totalSteps}` : null,
              "",
              "## Browser / Device",
              `- **Browser:** ${(bi.userAgent || "").split(" ").slice(-2).join(" ")}`,
              `- **Platform:** ${bi.platform || "unknown"}`,
              `- **Viewport:** ${bi.viewportWidth}x${bi.viewportHeight}`,
              `- **Screen:** ${bi.screenWidth}x${bi.screenHeight}`,
              `- **DPR:** ${bi.devicePixelRatio}`,
              `- **Online:** ${bi.online}`,
              `- **Page Load:** ${bi.pageLoadMs ? bi.pageLoadMs + "ms" : "unknown"}`,
              bi.screenshotCaptured ? "- **Screenshot:** Captured (check sessionStorage last_report_screenshot)" : null,
              "",
              bi.recentJsErrors?.length > 0 ? [
                "## Recent JS Errors",
                ...(bi.recentJsErrors||[]).map(e => `- ${e.ts?.slice(11,19)||""} [${e.filename||"?"}:${e.lineno||"?"}] ${e.message||""}`), "",

              ].join("\n") : null,
              bi.recentApiErrors?.length > 0 ? [
                "## Recent API Errors",
                ...(bi.recentApiErrors||[]).map(e => `- ${e.ts?.slice(11,19)||""} ${e.status||""} ${e.url||""}: ${e.message||""}`), "",

              ].join("\n") : null,
              "## Admin Notes",
              issue.admin_notes || "(none)",
              "",
              "---",
              "Please investigate and fix the above issue. The platform is Likhapoha AI, a CBSE learning platform built with React + FastAPI + Supabase.",
            ].filter(x => x !== null).join("\n");


            navigator.clipboard?.writeText(prompt).then(() => {
              setMsg("✅ Copied to clipboard — paste into Codex/Claude");
            }).catch(() => {
              // Fallback: open in textarea
              const ta = document.createElement("textarea");
              ta.value = prompt;
              document.body.appendChild(ta);
              ta.select();
              document.execCommand("copy");
              document.body.removeChild(ta);
              setMsg("✅ Copied to clipboard — paste into Codex/Claude");
            });
          }}
          style={{ width:"100%", padding:"9px", borderRadius:8, border:"1px solid #6366f1",
            background:"transparent", color:"#6366f1", fontWeight:700, fontSize:".82rem",
            cursor:"pointer", fontFamily:"inherit" }}>
          📋 Copy Bug Report for Codex
        </button>
      </div>
    </div>
  );
}

export default function AdminIssuesPage({ user: _user }) {
  const [summary, setSummary] = useState(null);
  const [issues, setIssues] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedIssue, setSelectedIssue] = useState(null);
  const [filters, setFilters] = useState({ status: "", severity: "", issue_type: "", grade: "", subject: "" });

  const loadSummary = useCallback(async () => {
    try {
      const r = await authFetch("/api/admin/issues/summary");
      if (r.success) setSummary(r);
    } catch { setSummary(null); }
  }, []);

  const loadIssues = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      Object.entries(filters).forEach(([k, v]) => { if (v) params.append(k, v); });
      const r = await authFetch("/api/admin/issues?" + params.toString());
      if (r.success) setIssues(r.issues || []);
    } catch { setIssues([]); }
    finally { setLoading(false); }
  }, [filters]);

  useEffect(() => { loadSummary(); }, [loadSummary]);
  useEffect(() => { loadIssues(); }, [loadIssues]);

  function handleUpdate(updated) {
    setIssues(prev => prev.map(i => i.id === updated.id ? updated : i));
    setSelectedIssue(updated);
    loadSummary();
  }

  const sel = { background: "var(--panel,#fff)", padding: "7px 10px", borderRadius: 7,
    border: "1px solid var(--border,#e5e7eb)", fontFamily: "inherit", fontSize: ".8rem" };

  return (
    <div data-testid="admin-issues-page" style={{ maxWidth: 1100, margin: "0 auto", padding: "0 0 60px" }}>
      <div style={{ marginBottom: 20 }}>
        <h2 style={{ fontWeight: 800, fontSize: "1.2rem", margin: "0 0 3px" }}>🐛 Product Bugs / Student Feedback</h2>
        <div style={{ fontSize: ".85rem", color: "#64748b" }}>Issue reports submitted by students and users.</div>
      </div>

      {/* Summary cards */}
      {summary && (
        <div data-testid="issue-summary-cards" style={{ display: "flex", flexWrap: "wrap", gap: 10, marginBottom: 24 }}>
          <SummaryCard label="Open" value={summary.open} color="#6366f1" testid="stat-open" />
          <SummaryCard label="Critical" value={summary.critical} color="#ef4444" testid="stat-critical" />
          <SummaryCard label="High" value={summary.high} color="#f97316" testid="stat-high" />
          <SummaryCard label="Content Issues" value={summary.content_issues} color="#0ea5e9" testid="stat-content" />
          <SummaryCard label="Fixed This Week" value={summary.fixed_this_week} color="#22c55e" testid="stat-fixed" />
        </div>
      )}

      {/* Filters */}
      <div data-testid="issue-filters" style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 16 }}>
        {[
          { key: "status", opts: ["", "open", "triaged", "in_progress", "fixed", "wont_fix", "duplicate"], label: "Status" },
          { key: "severity", opts: ["", "critical", "high", "medium", "low"], label: "Severity" },
          { key: "issue_type", opts: ["", ...Object.keys(ISSUE_TYPE_LABELS)], label: "Type" },
        ].map(({ key, opts, label }) => (
          <select key={key} value={filters[key]} style={sel}
            data-testid={`filter-${key}`}
            onChange={e => setFilters(p => ({ ...p, [key]: e.target.value }))}>
            <option value="">{label}</option>
            {opts.filter(Boolean).map(o => (
              <option key={o} value={o}>{ISSUE_TYPE_LABELS[o] || o.replace("_"," ")}</option>
            ))}
          </select>
        ))}
        <input placeholder="Grade (e.g. Grade 9)" value={filters.grade} style={{ ...sel, minWidth: 140 }}
          data-testid="filter-grade"
          onChange={e => setFilters(p => ({ ...p, grade: e.target.value }))} />
        <input placeholder="Subject" value={filters.subject} style={{ ...sel, minWidth: 120 }}
          data-testid="filter-subject"
          onChange={e => setFilters(p => ({ ...p, subject: e.target.value }))} />
        <button onClick={() => setFilters({ status: "", severity: "", issue_type: "", grade: "", subject: "" })}
          style={{ ...sel, cursor: "pointer", color: "#6366f1", fontWeight: 600 }}>
          Clear
        </button>
      </div>

      {/* Issue table */}
      {loading ? (
        <div style={{ textAlign: "center", padding: 40, color: "#94a3b8" }}>Loading…</div>
      ) : issues.length === 0 ? (
        <div data-testid="no-issues" style={{ textAlign: "center", padding: 40 }}>
          <div style={{ fontSize: "2rem" }}>✅</div>
          <p style={{ fontWeight: 600 }}>No issues found matching filters.</p>
        </div>
      ) : (
        <div style={{ border: "1px solid var(--border,#e5e7eb)", borderRadius: 10, overflow: "hidden" }}>
          {/* Table header */}
          <div style={{ display: "grid", gridTemplateColumns: "80px 90px 140px 1fr 100px 90px",
            background: "var(--surface2,#f8fafc)", padding: "8px 14px",
            fontSize: ".72rem", fontWeight: 700, color: "#64748b", textTransform: "uppercase", letterSpacing: ".04em" }}>
            <span>Severity</span><span>Status</span><span>Type</span>
            <span>Description</span><span>Context</span><span>Date</span>
          </div>
          {issues.map(issue => (
            <div key={issue.id} data-testid="issue-row"
              onClick={() => setSelectedIssue(issue)}
              style={{ display: "grid", gridTemplateColumns: "80px 90px 140px 1fr 100px 90px",
                padding: "10px 14px", borderTop: "1px solid var(--border,#f1f5f9)",
                cursor: "pointer", alignItems: "center",
                background: selectedIssue?.id === issue.id ? "var(--surface2,#f0f0ff)" : "var(--panel,#fff)",
              }}>
              <span><Badge label={issue.severity} color={SEV_COLOR[issue.severity] || "#94a3b8"} /></span>
              <span><Badge label={issue.status?.replace("_"," ")} color={STATUS_COLOR[issue.status] || "#94a3b8"} /></span>
              <span style={{ fontSize: ".78rem" }}>{ISSUE_TYPE_LABELS[issue.issue_type] || issue.issue_type}</span>
              <span style={{ fontSize: ".78rem", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {issue.title || issue.description?.slice(0, 80)}
              </span>
              <span style={{ fontSize: ".72rem", color: "#64748b" }}>
                {[issue.grade, issue.subject].filter(Boolean).join(" · ") || "—"}
              </span>
              <span style={{ fontSize: ".72rem", color: "#94a3b8" }}>
                {issue.created_at ? new Date(issue.created_at).toLocaleDateString() : "—"}
              </span>
            </div>
          ))}
        </div>
      )}

      {selectedIssue && (
        <IssueDrawer
          issue={selectedIssue}
          onClose={() => setSelectedIssue(null)}
          onUpdate={handleUpdate}
        />
      )}

      <ReporterAccessPanel />
    </div>
  );
}

function ReporterAccessPanel() {
  const [reporters, setReporters] = useState([]);
  const [loadingRep, setLoadingRep] = useState(false);
  const [searchUser, setSearchUser] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [toggling, setToggling] = useState({});
  const [msg, setMsg] = useState(null);

  async function loadReporters() {
    setLoadingRep(true);
    try {
      const r = await authFetch("/api/admin/users/issue-reporters");
      if (r.success) setReporters(r.reporters || []);
    } catch { setReporters([]); }
    finally { setLoadingRep(false); }
  }

  async function searchUsers() {
    if (!searchUser.trim()) return;
    setSearching(true);
    setMsg(null);
    try {
      const r = await authFetch(`/api/admin/users/search?q=${encodeURIComponent(searchUser)}&limit=10`);
      if (r.success) {
        setSearchResults(r.users || []);
        if (!r.users || r.users.length === 0) setMsg("No users found matching that search.");
      } else {
        setSearchResults([]);
        setMsg("Search failed: " + (r.error || "Unknown error"));
      }
    } catch (e) {
      setSearchResults([]);
      setMsg("Search error: " + e.message);
    }
    finally { setSearching(false); }
  }

  async function toggleAccess(userId, enabled) {
    setToggling(p => ({...p, [userId]: true}));
    setMsg(null);
    try {
      const r = await authFetch(`/api/admin/users/${userId}/can-report-issues?enabled=${enabled}`, { method: "PATCH" });
      if (r.success) {
        setMsg(`✅ ${enabled ? "Granted" : "Revoked"} report access for user.`);
        loadReporters();
        setSearchResults(prev => prev.map(u => u.id === userId ? {...u, can_report_issues: enabled} : u));
      }
    } catch (e) {
      if (e.message && e.message.includes("Migration not applied")) {
        setMsg("⚠️ DB migration needed. Run migrations/20260629_can_report_issues.sql in Supabase Studio first.");
      } else {
        setMsg("❌ " + e.message);
      }
    }
    finally { setToggling(p => ({...p, [userId]: false})); }
  }

  const inp = { padding:"7px 10px", borderRadius:7, border:"1px solid var(--border,#e5e7eb)",
    fontFamily:"inherit", fontSize:".82rem", background:"var(--panel,#fff)" };

  return (
    <div data-testid="reporter-access-panel" style={{ marginTop:32, padding:"20px 22px",
      background:"var(--panel,#fff)", border:"1px solid var(--border,#e5e7eb)", borderRadius:12 }}>
      <div style={{ fontWeight:700, fontSize:".95rem", marginBottom:4 }}>🔐 Report Issue Access</div>
      <div style={{ fontSize:".82rem", color:"#64748b", marginBottom:16 }}>
        Control which users can see the "Report Issue" button. Off by default.
      </div>

      {/* Search + grant */}
      <div style={{ display:"flex", gap:8, marginBottom:14, flexWrap:"wrap" }}>
        <input value={searchUser} onChange={e=>setSearchUser(e.target.value)}
          placeholder="Search by username or email..."
          style={{...inp, flex:"1 1 200px"}}
          data-testid="reporter-search-input"
          onKeyDown={e=>{ if(e.key==="Enter") searchUsers(); }} />
        <button onClick={searchUsers} disabled={searching}
          style={{...inp, cursor:"pointer", background:"#6366f1", color:"#fff", border:"none", fontWeight:600}}>
          {searching ? "Searching…" : "Search"}
        </button>
        <button onClick={loadReporters}
          style={{...inp, cursor:"pointer", color:"#6366f1", fontWeight:600}}>
          Refresh List
        </button>
      </div>

      {msg && <div style={{ marginBottom:10, fontSize:".8rem", color:msg.startsWith("✅")?"#22c55e":"#dc2626" }}>{msg}</div>}

      {/* Search results */}
      {searchResults.length > 0 && (
        <div style={{ marginBottom:16 }}>
          <div style={{ fontSize:".76rem", fontWeight:600, color:"#64748b", marginBottom:6 }}>SEARCH RESULTS</div>
          {searchResults.map(u => (
            <div key={u.id} style={{ display:"flex", alignItems:"center", gap:10, padding:"6px 0",
              borderBottom:"1px solid var(--border,#f1f5f9)", flexWrap:"wrap" }}>
              <span style={{ fontSize:".8rem", flex:1 }}>{u.username || u.email} <span style={{color:"#94a3b8"}}>({u.role})</span></span>
              <button onClick={() => toggleAccess(u.id, !u.can_report_issues)}
                disabled={toggling[u.id]}
                data-testid={`toggle-reporter-${u.id}`}
                style={{ padding:"4px 12px", borderRadius:7, border:"none", cursor:"pointer",
                  fontFamily:"inherit", fontWeight:600, fontSize:".76rem",
                  background: u.can_report_issues ? "#fef2f2" : "#f0fdf4",
                  color: u.can_report_issues ? "#dc2626" : "#16a34a" }}>
                {toggling[u.id] ? "…" : u.can_report_issues ? "Revoke Access" : "Grant Access"}
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Current reporters */}
      <div>
        <div style={{ fontSize:".76rem", fontWeight:600, color:"#64748b", marginBottom:6 }}>
          USERS WITH REPORT ACCESS ({reporters.length})
        </div>
        {loadingRep ? (
          <div style={{ color:"#94a3b8", fontSize:".8rem" }}>Loading…</div>
        ) : reporters.length === 0 ? (
          <div style={{ color:"#94a3b8", fontSize:".8rem" }}>No users have report access yet.</div>
        ) : (
          reporters.map(u => (
            <div key={u.id} style={{ display:"flex", alignItems:"center", gap:10, padding:"5px 0",
              borderBottom:"1px solid var(--border,#f1f5f9)", flexWrap:"wrap" }}>
              <span style={{ fontSize:".8rem", flex:1 }}>{u.username || u.email} <span style={{color:"#94a3b8"}}>({u.role})</span></span>
              <button onClick={() => toggleAccess(u.id, false)} disabled={toggling[u.id]}
                style={{ padding:"4px 12px", borderRadius:7, border:"none", cursor:"pointer",
                  fontFamily:"inherit", fontWeight:600, fontSize:".76rem",
                  background:"#fef2f2", color:"#dc2626" }}>
                {toggling[u.id] ? "…" : "Revoke"}
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
