/**
 * AdminViewAsUser.jsx — Frontend-only read-only View-as-User mode.
 * No JWT exchange. Admin sees user context with a persistent banner.
 *
 * UI states: idle | loading | results | no-results | error
 * Props: accessToken
 */
import { useState } from "react";

const API = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function apiFetch(path, token) {
  const r = await fetch(`${API}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!r.ok) {
    const body = await r.json().catch(() => ({}));
    throw new Error(body.detail || body.error || `HTTP ${r.status}`);
  }
  return r.json();
}

async function apiPost(path, body, token) {
  const r = await fetch(`${API}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const b = await r.json().catch(() => ({}));
    throw new Error(b.detail || b.error || `HTTP ${r.status}`);
  }
  return r.json();
}

const S_IDLE       = "idle";
const S_LOADING    = "loading";
const S_RESULTS    = "results";
const S_NO_RESULTS = "no_results";
const S_ERROR      = "error";

const ROLE_COLOR = { student: "#6366f1", parent: "#10b981", teacher: "#f59e0b" };

export default function AdminViewAsUser({ accessToken }) {
  const [query, setQuery]         = useState("");
  const [searchState, setSearchState] = useState(S_IDLE);
  const [searchErr, setSearchErr] = useState(null);
  const [results, setResults]     = useState([]);
  const [lastQuery, setLastQuery] = useState("");
  const [viewAsCtx, setViewAsCtx] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);

  // ── Search ──────────────────────────────────────────────────────────────────
  async function doSearch() {
    const q = query.trim();
    if (!q) return;
    setSearchState(S_LOADING);
    setSearchErr(null);
    setLastQuery(q);
    try {
      const d = await apiFetch(
        `/api/admin/support/user-search?q=${encodeURIComponent(q)}&limit=10`,
        accessToken,
      );
      const users = d.users || [];
      setResults(users);
      setSearchState(users.length > 0 ? S_RESULTS : S_NO_RESULTS);
    } catch (e) {
      setSearchErr(e.message || "Search failed");
      setSearchState(S_ERROR);
      setResults([]);
    }
  }

  // ── Start view-as ───────────────────────────────────────────────────────────
  async function startViewAs(user) {
    setActionLoading(true);
    setSearchErr(null);
    try {
      const d = await apiFetch(`/api/admin/support/view-as/${user.id}`, accessToken);
      if (!d.success) {
        setSearchErr(d.error || "Could not start view-as");
        setActionLoading(false);
        return;
      }
      setViewAsCtx(d);
      setResults([]);
      setQuery("");
      setSearchState(S_IDLE);
    } catch (e) {
      setSearchErr(e.message);
    }
    setActionLoading(false);
  }

  // ── Exit view-as ────────────────────────────────────────────────────────────
  async function exitViewAs() {
    if (viewAsCtx?.view_as?.user_id) {
      await apiPost(
        "/api/admin/support/log-impersonation-event",
        { event_type: "impersonation.ended", target_user_id: viewAsCtx.view_as.user_id },
        accessToken,
      ).catch(() => {});
    }
    setViewAsCtx(null);
    setSearchErr(null);
    setSearchState(S_IDLE);
  }

  return (
    <div data-testid="admin-view-as-user">

      {/* ── Persistent banner when in view-as mode ──────────────────────── */}
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

      {/* ── Search section (hidden while in view-as) ─────────────────────── */}
      {!viewAsCtx && (
        <>
          <div style={{ display: "flex", gap: 8, marginBottom: 12, flexWrap: "wrap" }}>
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && doSearch()}
              placeholder="Search by name or email…"
              data-testid="view-as-search-input"
              style={{
                flex: 1, minWidth: 200, padding: "8px 10px", borderRadius: 7,
                border: "1px solid var(--border, #e5e7eb)", fontFamily: "inherit", fontSize: ".85rem",
                background: "var(--surface2, #f8fafc)", color: "var(--text, #1e293b)",
              }}
            />
            <button
              onClick={doSearch}
              disabled={searchState === S_LOADING || !query.trim()}
              className="primary-btn"
              aria-label="search">
              {searchState === S_LOADING ? "Searching…" : "Search"}
            </button>
          </div>

          {/* ── Search state messages ──────────────────────────────────── */}
          {searchState === S_IDLE && (
            <div data-testid="view-as-idle"
              style={{ color: "var(--muted,#94a3b8)", fontSize: ".82rem", padding: "8px 0" }}>
              Enter a name or email address to find a user to view as.
            </div>
          )}

          {searchState === S_LOADING && (
            <div data-testid="view-as-loading"
              style={{ color: "var(--muted,#94a3b8)", fontSize: ".82rem", padding: "8px 0" }}>
              Searching…
            </div>
          )}

          {searchState === S_ERROR && (
            <div data-testid="view-as-error"
              style={{ color: "#dc2626", fontSize: ".82rem", marginBottom: 8, padding: "8px 12px", background: "rgba(239,68,68,.07)", borderRadius: 7, border: "1px solid rgba(239,68,68,.2)" }}>
              ⚠ {searchErr}
            </div>
          )}

          {searchState === S_NO_RESULTS && (
            <div data-testid="view-as-no-results"
              style={{ color: "var(--muted,#94a3b8)", fontSize: ".82rem", padding: "10px 14px", background: "var(--surface2,#f8fafc)", borderRadius: 8, border: "1px solid var(--border,#e5e7eb)" }}>
              No users found matching <strong>"{lastQuery}"</strong>. Try a different name or email.
            </div>
          )}

          {/* Action error (e.g. tried to view-as admin) */}
          {searchState !== S_ERROR && searchErr && (
            <div style={{ color: "#dc2626", fontSize: ".82rem", marginBottom: 8 }}>⚠ {searchErr}</div>
          )}

          {/* ── Results ────────────────────────────────────────────────── */}
          {searchState === S_RESULTS && results.map((u) => (
            <div
              key={u.id}
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
                <span style={{
                  marginLeft: 8, fontSize: ".75rem",
                  background: `${ROLE_COLOR[u.role] || "#94a3b8"}22`,
                  color: ROLE_COLOR[u.role] || "#64748b",
                  padding: "2px 7px", borderRadius: 5, fontWeight: 600,
                }}>
                  {u.role}
                </span>
                <div style={{ fontSize: ".72rem", color: "var(--muted, #94a3b8)", marginTop: 2 }}>
                  {u.email} · {u.grade || "—"}
                </div>
              </div>
              <button
                onClick={() => startViewAs(u)}
                disabled={actionLoading}
                data-testid={`start-view-as-${u.id}`}
                style={{
                  padding: "5px 12px", borderRadius: 6, border: "1px solid #f59e0b",
                  background: "rgba(245,158,11,.1)", color: "#92400e", fontWeight: 600,
                  fontSize: ".8rem", cursor: actionLoading ? "not-allowed" : "pointer", fontFamily: "inherit",
                }}>
                {actionLoading ? "…" : `👁 View as ${u.username}`}
              </button>
            </div>
          ))}
        </>
      )}

      {/* ── View-as context panel ─────────────────────────────────────────── */}
      {viewAsCtx && (
        <div data-testid="view-as-context">
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(160px,1fr))", gap: 10, marginBottom: 16 }}>
            {[
              ["Username", viewAsCtx.view_as?.username],
              ["Role", viewAsCtx.view_as?.role],
              ["Grade", viewAsCtx.view_as?.grade || "—"],
              ["Plan", viewAsCtx.view_as?.subscription_plan],
              ["CBSE Access", viewAsCtx.view_as?.access_cbse ? "✓ Enabled" : "✗ Restricted (free tier)"],
              ["Status", viewAsCtx.view_as?.account_status],
            ].map(([k, v]) => (
              <div key={k} style={{ background: "var(--panel,#fff)", border: "1px solid var(--border,#e5e7eb)", borderRadius: 9, padding: "10px 12px" }}>
                <div style={{ fontSize: ".72rem", color: "#64748b" }}>{k}</div>
                <div style={{ fontSize: ".88rem", fontWeight: 700, marginTop: 2 }}>{v ?? "—"}</div>
              </div>
            ))}
          </div>

          {/* Subscription state — human-readable cards */}
          {viewAsCtx.resolved_subscription && (
            <div style={{ background: "var(--surface2, #f8fafc)", border: "1px solid var(--border, #e5e7eb)", borderRadius: 9, padding: "12px 14px", marginBottom: 12 }}>
              <h4 style={{ margin: "0 0 10px", fontSize: ".85rem", fontWeight: 700 }}>📋 Subscription Details</h4>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                {[
                  ["Source", viewAsCtx.resolved_subscription.source],
                  ["Plan", viewAsCtx.resolved_subscription.plan_name || viewAsCtx.resolved_subscription.subscription_plan || "free"],
                  ["Days Left", viewAsCtx.resolved_subscription.days_remaining != null ? `${viewAsCtx.resolved_subscription.days_remaining}d` : "—"],
                  ["Valid Until", viewAsCtx.resolved_subscription.valid_until ? viewAsCtx.resolved_subscription.valid_until.slice(0,10) : "No expiry"],
                  ["Expiring Soon", viewAsCtx.resolved_subscription.expiring_soon ? "⚠ Yes" : "No"],
                ].map(([k, v]) => (
                  <div key={k} style={{ background: "var(--panel,#fff)", border: "1px solid var(--border,#e5e7eb)", borderRadius: 7, padding: "6px 10px", minWidth: 80 }}>
                    <div style={{ fontSize: ".68rem", color: "#64748b" }}>{k}</div>
                    <div style={{ fontSize: ".82rem", fontWeight: 700 }}>{v ?? "—"}</div>
                  </div>
                ))}
              </div>
              {viewAsCtx.resolved_subscription.restrictions?.length > 0 && (
                <div style={{ marginTop: 8, fontSize: ".72rem", color: "#94a3b8" }}>
                  Feature limits: {viewAsCtx.resolved_subscription.restrictions.join(", ")}
                </div>
              )}
            </div>
          )}

          {/* Activity stats */}
          {viewAsCtx.activity && (
            <div style={{ background: "var(--surface2, #f8fafc)", border: "1px solid var(--border, #e5e7eb)", borderRadius: 9, padding: "12px 14px", marginBottom: 12 }}>
              <h4 style={{ margin: "0 0 10px", fontSize: ".85rem", fontWeight: 700 }}>📊 Recent Activity</h4>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(110px,1fr))", gap: 8 }}>
                {[
                  ["📖 Lessons", viewAsCtx.activity.lessons_generated ?? 0],
                  ["❓ Doubts", viewAsCtx.activity.doubts_asked ?? 0],
                  ["📝 Mock Tests", viewAsCtx.activity.mock_tests_generated ?? 0],
                  ["⚡ Tokens Today", (viewAsCtx.activity.tokens_today ?? 0).toLocaleString()],
                  ["📅 Tokens Month", (viewAsCtx.activity.tokens_this_month ?? 0).toLocaleString()],
                  ["💰 Total Cost", `$${(viewAsCtx.activity.cost_total ?? 0).toFixed(4)}`],
                ].map(([label, val]) => (
                  <div key={label} style={{ background: "var(--panel,#fff)", border: "1px solid var(--border,#e5e7eb)", borderRadius: 7, padding: "8px 10px", textAlign: "center" }}>
                    <div style={{ fontSize: ".78rem", fontWeight: 700, color: "var(--text,#1e293b)" }}>{val}</div>
                    <div style={{ fontSize: ".65rem", color: "#64748b", marginTop: 2 }}>{label}</div>
                  </div>
                ))}
              </div>
              {viewAsCtx.activity.last_activity && (
                <div style={{ marginTop: 8, fontSize: ".72rem", color: "#94a3b8" }}>
                  Last active: {new Date(viewAsCtx.activity.last_activity).toLocaleString()}
                </div>
              )}
              {!viewAsCtx.activity.last_activity && (
                <div style={{ marginTop: 8, fontSize: ".72rem", color: "#94a3b8" }}>No recent activity recorded.</div>
              )}
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
