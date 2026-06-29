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

function IssueDrawer({ issue, onClose, onUpdate }) {
  const [notes, setNotes] = useState(issue?.admin_notes || "");
  const [status, setStatus] = useState(issue?.status || "open");
  const [saving, setSaving] = useState(false);
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
    </div>
  );
}
