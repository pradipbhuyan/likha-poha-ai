/**
 * AdminViewAsUser.jsx — Frontend-only read-only View-as-User mode.
 * No JWT exchange. Admin sees user context with a persistent banner.
 * Props: accessToken, onNavigateTab(tab)
 */
import { useRef, useState } from "react";

const API = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function apiFetch(path, token) {
  const r = await fetch(`${API}${path}`, { headers: { Authorization: `Bearer ${token}` } });
  return r.json();
}
async function apiPost(path, body, token) {
  const r = await fetch(`${API}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify(body),
  });
  return r.json();
}

export default function AdminViewAsUser({ accessToken }) {
  const [query, setQuery]         = useState("");
  const [results, setResults]     = useState([]);
  const [viewAsCtx, setViewAsCtx] = useState(null);  // active view-as context
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState(null);
  const searchRef                 = useRef(null);

  async function doSearch() {
    if (!query.trim()) return;
    setLoading(true); setError(null);
    try {
      const d = await apiFetch(`/api/admin/support/user-search?q=${encodeURIComponent(query)}&limit=10`, accessToken);
      setResults(d.users || []);
      if (d.error) setError(d.error);
    } catch (e) { setError(e.message); }
    setLoading(false);
  }

  async function startViewAs(user) {
    setLoading(true); setError(null);
    try {
      const d = await apiFetch(`/api/admin/support/view-as/${user.id}`, accessToken);
      if (!d.success) { setError(d.error); setLoading(false); return; }
      setViewAsCtx(d);
      setResults([]);
      setQuery("");
    } catch (e) { setError(e.message); }
    setLoading(false);
  }

  async function exitViewAs() {
    if (viewAsCtx?.view_as?.user_id) {
      await apiPost("/api/admin/support/log-impersonation-event", {
        event_type: "impersonation.ended",
        target_user_id: viewAsCtx.view_as.user_id,
      }, accessToken).catch(() => {});
    }
    setViewAsCtx(null);
    setError(null);
  }

  const ROLE_COLOR = { student: "#6366f1", parent: "#10b981", teacher: "#f59e0b" };

  return (
    <div data-testid="admin-view-as-user">
      {/* Persistent banner when in view-as mode */}
      {viewAsCtx && (
        <div
          data-testid="view-as-banner"
          style={{
            position: "sticky", top: 0, zIndex: 50,
            background: "#f59e0b", color: "#1e293b",
            padding: "10px 16px",
            display: "flex", alignItems: "center", justifyContent: "space-between",
            flexWrap: "wrap", gap: 8,
            borderRadius: 8, marginBottom: 16,
            boxShadow: "0 2px 8px rgba(245,158,11,.3)",
          }}>
          <span style={{ fontWeight: 700, fontSize: ".85rem" }}>
            👁 {viewAsCtx.banner}
          </span>
          <button
            onClick={exitViewAs}
            data-testid="exit-view-as-btn"
            style={{
              background: "#1e293b", color: "#fff", border: "none", borderRadius: 6,
              padding: "5px 14px", fontWeight: 700, fontSize: ".82rem", cursor: "pointer", fontFamily: "inherit",
            }}>
            ✕ Exit View-as Mode
          </button>
        </div>
      )}

      {!viewAsCtx && (
        <>
          <h3 style={{ margin: "0 0 12px", fontSize: ".95rem", fontWeight: 700 }}>👁 View as User</h3>
          <p style={{ color: "var(--muted, #64748b)", fontSize: ".82rem", marginBottom: 12 }}>
            Search for a user to start a read-only view of their context. No JWT exchange — admin actions are fully restricted while viewing.
          </p>

          <div style={{ display: "flex", gap: 8, marginBottom: 12, flexWrap: "wrap" }}>
            <input
              ref={searchRef}
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={e => e.key === "Enter" && doSearch()}
              placeholder="Search by name or email…"
              data-testid="view-as-search-input"
              style={{
                flex: 1, minWidth: 200, padding: "8px 10px", borderRadius: 7,
                border: "1px solid var(--border, #e5e7eb)", fontFamily: "inherit", fontSize: ".85rem",
                background: "var(--surface2, #f8fafc)", color: "var(--text, #1e293b)",
              }}
            />
            <button onClick={doSearch} disabled={loading || !query.trim()}
              className="primary-btn">
              {loading ? "Searching…" : "Search"}
            </button>
          </div>

          {error && <div style={{ color: "#dc2626", fontSize: ".82rem", marginBottom: 8 }}>⚠ {error}</div>}

          {results.map(u => (
            <div key={u.id}
              data-testid={`view-as-result-${u.id}`}
              style={{
                display: "flex", alignItems: "center", justifyContent: "space-between",
                padding: "10px 14px", borderRadius: 8,
                background: "var(--surface2, #f8fafc)",
                border: "1px solid var(--border, #e5e7eb)", marginBottom: 6,
                flexWrap: "wrap", gap: 8,
              }}>
              <div>
                <strong style={{ fontSize: ".85rem" }}>{u.username}</strong>
                <span style={{ marginLeft: 8, fontSize: ".75rem",
                  background: `${ROLE_COLOR[u.role] || "#94a3b8"}22`,
                  color: ROLE_COLOR[u.role] || "#64748b",
                  padding: "2px 7px", borderRadius: 5, fontWeight: 600 }}>
                  {u.role}
                </span>
                <div style={{ fontSize: ".72rem", color: "var(--muted, #94a3b8)", marginTop: 2 }}>{u.email} · {u.grade || "—"}</div>
              </div>
              <button
                onClick={() => startViewAs(u)}
                data-testid={`start-view-as-${u.id}`}
                style={{
                  padding: "5px 12px", borderRadius: 6, border: "1px solid #f59e0b",
                  background: "rgba(245,158,11,.1)", color: "#92400e", fontWeight: 600,
                  fontSize: ".8rem", cursor: "pointer", fontFamily: "inherit",
                }}>
                👁 View as {u.username}
              </button>
            </div>
          ))}
        </>
      )}

      {/* View-as context panel */}
      {viewAsCtx && (
        <div data-testid="view-as-context">
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(160px,1fr))", gap: 10, marginBottom: 16 }}>
            {[
              ["Username", viewAsCtx.view_as?.username],
              ["Role", viewAsCtx.view_as?.role],
              ["Grade", viewAsCtx.view_as?.grade || "—"],
              ["Plan", viewAsCtx.view_as?.subscription_plan],
              ["CBSE Access", viewAsCtx.view_as?.access_cbse ? "✓ Yes" : "✗ No"],
              ["Status", viewAsCtx.view_as?.account_status],
            ].map(([k, v]) => (
              <div key={k} style={{ background: "var(--panel,#fff)", border: "1px solid var(--border,#e5e7eb)", borderRadius: 9, padding: "10px 12px" }}>
                <div style={{ fontSize: ".72rem", color: "#64748b" }}>{k}</div>
                <div style={{ fontSize: ".88rem", fontWeight: 700, marginTop: 2 }}>{v ?? "—"}</div>
              </div>
            ))}
          </div>

          {viewAsCtx.resolved_subscription && (
            <div style={{ background: "var(--surface2, #f8fafc)", border: "1px solid var(--border, #e5e7eb)", borderRadius: 9, padding: "12px 14px", marginBottom: 12 }}>
              <h4 style={{ margin: "0 0 8px", fontSize: ".85rem" }}>Resolved Subscription State</h4>
              <pre style={{ fontSize: ".75rem", margin: 0, overflow: "auto", maxHeight: 160, color: "var(--text, #374151)" }}>
                {JSON.stringify(viewAsCtx.resolved_subscription, null, 2)}
              </pre>
            </div>
          )}

          <div style={{ padding: "10px 14px", background: "#fef3c7", border: "1px solid #fde68a", borderRadius: 8, fontSize: ".78rem", color: "#92400e" }}>
            <strong>Restrictions active:</strong> {viewAsCtx.restrictions?.join(", ")}
          </div>
        </div>
      )}
    </div>
  );
}
