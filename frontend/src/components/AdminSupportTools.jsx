/**
 * AdminSupportTools.jsx — Admin support tools for user lookup, subscription history,
 * audit history, and password reset.
 * Props: accessToken
 */
import { useState } from "react";

const API = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function apiFetch(path, token) {
  const r = await fetch(`${API}${path}`, { headers: { Authorization: `Bearer ${token}` } });
  return r.json();
}
async function apiPost(path, token) {
  const r = await fetch(`${API}${path}`, { method: "POST", headers: { Authorization: `Bearer ${token}` } });
  return r.json();
}

const TAG = { fontSize: ".72rem", padding: "2px 7px", borderRadius: 5, fontWeight: 600 };
const ROLE_COLOR = { student: "#6366f1", parent: "#10b981", teacher: "#f59e0b", admin: "#ef4444" };

function Section({ title, children }) {
  return (
    <div style={{ background: "var(--panel,#fff)", border: "1px solid var(--border,#e5e7eb)", borderRadius: 10, padding: "14px 16px", marginBottom: 12 }}>
      <h4 style={{ margin: "0 0 10px", fontSize: ".88rem", fontWeight: 700 }}>{title}</h4>
      {children}
    </div>
  );
}

export default function AdminSupportTools({ accessToken }) {
  const [query, setQuery]       = useState("");
  const [results, setResults]   = useState([]);
  const [selected, setSelected] = useState(null);
  const [summary, setSummary]   = useState(null);
  const [subHistory, setSubHist]= useState(null);
  const [auditHist, setAudit]   = useState(null);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState(null);
  const [actionMsg, setActionMsg]= useState(null);
  const [resetResult, setResetResult] = useState(null);

  async function doSearch() {
    if (!query.trim()) return;
    setLoading(true); setError(null);
    const d = await apiFetch(`/api/admin/support/user-search?q=${encodeURIComponent(query)}&limit=15`, accessToken).catch(e => ({ error: e.message }));
    setResults(d.users || []);
    if (d.error) setError(d.error);
    setLoading(false);
  }

  async function loadUser(user) {
    setSelected(user); setSummary(null); setSubHist(null); setAudit(null);
    setActionMsg(null); setResetResult(null);
    const [s, sh, ah] = await Promise.all([
      apiFetch(`/api/admin/support/users/${user.id}/summary`, accessToken).catch(() => null),
      apiFetch(`/api/admin/support/users/${user.id}/subscription-history`, accessToken).catch(() => null),
      apiFetch(`/api/admin/support/users/${user.id}/audit-history`, accessToken).catch(() => null),
    ]);
    setSummary(s);
    setSubHist(sh);
    setAudit(ah);
  }

  async function doResetPassword() {
    if (!selected) return;
    if (!window.confirm(`Reset password for ${selected.username}? A new temp password will be shown once only.`)) return;
    setResetResult(null);
    const d = await apiPost(`/api/admin/support/students/${selected.id}/reset-password`, accessToken).catch(e => ({ success: false, error: e.message }));
    setResetResult(d);
  }

  async function doResendWelcome() {
    if (!selected) return;
    setActionMsg(null);
    const d = await apiPost(`/api/admin/support/users/${selected.id}/resend-welcome`, accessToken).catch(e => ({ success: false, error: e.message }));
    setActionMsg(d.invite_sent ? "✅ Welcome invite sent." : `ℹ ${d.note || d.error || "Done."}`);
  }

  const isStudent = selected?.role === "student" || selected?.role === "child";
  const rs = summary?.resolved_subscription;

  return (
    <div data-testid="admin-support-tools">
      <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
        <input
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === "Enter" && doSearch()}
          placeholder="Search user by name or email…"
          data-testid="support-search-input"
          style={{
            flex: 1, minWidth: 200, padding: "8px 10px", borderRadius: 7,
            border: "1px solid var(--border,#e5e7eb)", fontFamily: "inherit", fontSize: ".85rem",
            background: "var(--surface2,#f8fafc)", color: "var(--text,#1e293b)",
          }}
        />
        <button onClick={doSearch} disabled={loading || !query.trim()} className="primary-btn">
          {loading ? "…" : "Search"}
        </button>
        {selected && (
          <button onClick={() => { setSelected(null); setSummary(null); setSubHist(null); setAudit(null); }}
            style={{ padding: "6px 12px", borderRadius: 6, border: "1px solid var(--border,#e5e7eb)", background: "var(--panel,#fff)", cursor: "pointer", fontFamily: "inherit", fontSize: ".82rem" }}>
            ← Back
          </button>
        )}
      </div>

      {error && <div style={{ color: "#dc2626", fontSize: ".82rem", marginBottom: 8 }}>⚠ {error}</div>}

      {/* Search results */}
      {!selected && results.map(u => (
        <div key={u.id}
          data-testid={`support-result-${u.id}`}
          style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "9px 14px", borderRadius: 8, background: "var(--surface2,#f8fafc)", border: "1px solid var(--border,#e5e7eb)", marginBottom: 6, flexWrap: "wrap", gap: 6 }}>
          <div>
            <strong style={{ fontSize: ".85rem" }}>{u.username}</strong>
            <span style={{ ...TAG, marginLeft: 8, background: `${ROLE_COLOR[u.role] || "#94a3b8"}22`, color: ROLE_COLOR[u.role] || "#64748b" }}>{u.role}</span>
            <div style={{ fontSize: ".72rem", color: "var(--muted,#94a3b8)", marginTop: 2 }}>{u.email} · {u.grade || "—"} · {u.subscription_plan}</div>
          </div>
          <button onClick={() => loadUser(u)}
            style={{ padding: "4px 10px", borderRadius: 6, border: "1px solid #6366f1", background: "rgba(99,102,241,.08)", color: "#6366f1", fontWeight: 600, fontSize: ".78rem", cursor: "pointer", fontFamily: "inherit" }}>
            Open
          </button>
        </div>
      ))}

      {/* User detail view */}
      {selected && summary && (
        <>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14, flexWrap: "wrap" }}>
            <h3 style={{ margin: 0, fontSize: "1rem" }}>{selected.username}</h3>
            <span style={{ ...TAG, background: `${ROLE_COLOR[selected.role] || "#94a3b8"}22`, color: ROLE_COLOR[selected.role] || "#64748b" }}>{selected.role}</span>
            <span style={{ fontSize: ".78rem", color: "var(--muted,#94a3b8)" }}>{selected.email}</span>
          </div>

          {/* Resolved subscription */}
          {rs && (
            <Section title="Resolved Subscription State">
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                {[["Plan", rs.plan_name || rs.subscription_plan], ["Access CBSE", rs.access_cbse ? "✓" : "✗"], ["Source", rs.source], ["Expires", rs.expires_at ? rs.expires_at.slice(0,10) : "No expiry"]].map(([k,v]) => (
                  <div key={k} style={{ background: "var(--surface2,#f8fafc)", border: "1px solid var(--border,#e5e7eb)", borderRadius: 7, padding: "7px 12px", minWidth: 90 }}>
                    <div style={{ fontSize: ".7rem", color: "#64748b" }}>{k}</div>
                    <div style={{ fontSize: ".85rem", fontWeight: 700 }}>{v ?? "—"}</div>
                  </div>
                ))}
              </div>
            </Section>
          )}

          {/* Subscription history */}
          {subHistory?.timeline_events?.length > 0 && (
            <Section title="Subscription Timeline">
              <div style={{ maxHeight: 200, overflowY: "auto" }}>
                {subHistory.timeline_events.map((e, i) => (
                  <div key={i} style={{ display: "flex", gap: 8, padding: "4px 0", borderBottom: "1px solid var(--border,#f1f5f9)", fontSize: ".78rem" }}>
                    <span style={{ color: "var(--muted,#94a3b8)", minWidth: 90 }}>{(e.created_at || "").slice(0,16)}</span>
                    <span style={{ fontWeight: 600 }}>{e.event_type}</span>
                    {e.from_plan && <span style={{ color: "var(--muted,#94a3b8)" }}>{e.from_plan} → {e.to_plan}</span>}
                    {e.source && <span style={{ color: "var(--muted,#94a3b8)" }}>({e.source})</span>}
                  </div>
                ))}
              </div>
            </Section>
          )}

          {/* Payment history */}
          {subHistory?.payment_history?.length > 0 && (
            <Section title="Payment History">
              <div style={{ maxHeight: 180, overflowY: "auto" }}>
                {subHistory.payment_history.map((p, i) => (
                  <div key={i} style={{ display: "flex", gap: 10, padding: "4px 0", borderBottom: "1px solid var(--border,#f1f5f9)", fontSize: ".78rem" }}>
                    <span style={{ color: "var(--muted,#94a3b8)", minWidth: 90 }}>{(p.created_at || "").slice(0,10)}</span>
                    <span style={{ fontWeight: 600, color: p.status === "paid" ? "#166534" : "#dc2626" }}>{p.status}</span>
                    <span>{p.plan_key}</span>
                    {p.amount && <span style={{ color: "var(--muted,#94a3b8)" }}>₹{p.amount}</span>}
                  </div>
                ))}
              </div>
            </Section>
          )}

          {/* Audit history */}
          {auditHist?.audit_events?.length > 0 && (
            <Section title="Audit History (sanitised)">
              <p style={{ fontSize: ".72rem", color: "var(--muted,#94a3b8)", margin: "0 0 6px" }}>{auditHist.note}</p>
              <div style={{ maxHeight: 180, overflowY: "auto" }}>
                {auditHist.audit_events.map((e, i) => (
                  <div key={i} style={{ display: "flex", gap: 8, padding: "4px 0", borderBottom: "1px solid var(--border,#f1f5f9)", fontSize: ".78rem" }}>
                    <span style={{ color: "var(--muted,#94a3b8)", minWidth: 90 }}>{(e.created_at || "").slice(0,16)}</span>
                    <span style={{ fontWeight: 600 }}>{e.event_type}</span>
                    {e.entity_type && <span style={{ color: "var(--muted,#94a3b8)" }}>{e.entity_type}</span>}
                  </div>
                ))}
              </div>
            </Section>
          )}

          {/* Actions */}
          <Section title="Actions">
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <button onClick={doResendWelcome} className="secondary-btn">📧 Resend Welcome</button>
              {isStudent && (
                <button onClick={doResetPassword} className="danger-btn">🔑 Reset Password</button>
              )}
            </div>
            {actionMsg && <div style={{ marginTop: 8, fontSize: ".82rem", color: "#166534" }}>{actionMsg}</div>}
            {resetResult && (
              <div style={{ marginTop: 8, padding: "8px 12px", borderRadius: 7, background: resetResult.success ? "#f0fdf4" : "#fef2f2", border: `1px solid ${resetResult.success ? "#bbf7d0" : "#fecaca"}`, fontSize: ".82rem" }}>
                {resetResult.success ? (
                  <span>🔑 New temp password for <strong>{resetResult.username}</strong>: <code style={{ color: "#f59e0b", fontWeight: 700 }}>{resetResult.temp_password}</code><br/><small style={{ color: "#64748b" }}>{resetResult.warning}</small></span>
                ) : (
                  <span style={{ color: "#dc2626" }}>✗ {resetResult.error}</span>
                )}
              </div>
            )}
          </Section>
        </>
      )}
    </div>
  );
}
