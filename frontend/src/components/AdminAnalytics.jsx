/**
 * AdminAnalytics.jsx — Admin analytics dashboard with summary cards and trends.
 *
 * Each stat card renders one of four explicit states:
 *   ok             → numeric value (may be 0)
 *   table_missing  → "Not yet enabled"  (grey badge)
 *   query_error    → "Unable to load"   (amber badge)
 *   loading        → spinner placeholder
 *
 * Props: accessToken
 */
import { useCallback, useEffect, useState } from "react";

const API = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

// ── State constants (mirror backend) ─────────────────────────────────────────
const STATE_OK      = "ok";
const STATE_MISSING = "table_missing";
const STATE_ERROR   = "query_error";
const STATE_LOADING = "loading";

// ── StatCard ─────────────────────────────────────────────────────────────────

/**
 * @param {string}  label
 * @param {number|null} value      — numeric value when state=ok
 * @param {string}  state          — "ok" | "table_missing" | "query_error" | "loading"
 * @param {string}  [sub]          — subtitle / period label
 * @param {string}  [format]       — "number" | "percent" | "string"
 */
function StatCard({ label, value, state = STATE_OK, sub, format = "number" }) {
  let display;
  let badge = null;

  if (state === STATE_LOADING) {
    display = <span style={{ fontSize: ".75rem", color: "#94a3b8" }}>…</span>;
  } else if (state === STATE_MISSING) {
    display = null;
    badge = (
      <span data-testid="badge-not-enabled"
        style={{ display: "inline-block", fontSize: ".68rem", padding: "2px 6px", borderRadius: 4, background: "rgba(148,163,184,.15)", color: "#94a3b8", fontWeight: 600 }}>
        Not yet enabled
      </span>
    );
  } else if (state === STATE_ERROR) {
    display = null;
    badge = (
      <span data-testid="badge-error"
        style={{ display: "inline-block", fontSize: ".68rem", padding: "2px 6px", borderRadius: 4, background: "rgba(245,158,11,.12)", color: "#b45309", fontWeight: 600 }}>
        Unable to load
      </span>
    );
  } else {
    // STATE_OK — value must be defined; null means zero
    const v = value ?? 0;
    if (format === "percent") {
      display = <>{v}%</>;
    } else if (format === "string") {
      display = <>{v}</>;
    } else {
      display = <>{typeof v === "number" ? v.toLocaleString() : v}</>;
    }
  }

  return (
    <div
      data-testid={`stat-${label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}
      style={{
        background: "var(--panel,#fff)", border: "1px solid var(--border,#e5e7eb)",
        borderRadius: 10, padding: "12px 16px", flex: "1 1 130px", minWidth: 120,
      }}>
      <div style={{ fontSize: ".75rem", color: "#64748b", marginBottom: 4 }}>{label}</div>
      {badge || (
        <div style={{ fontSize: "1.4rem", fontWeight: 800, color: "var(--text,#1e293b)", lineHeight: 1.1 }}>
          {display}
        </div>
      )}
      {sub && state === STATE_OK && (
        <div style={{ fontSize: ".72rem", color: "#94a3b8", marginTop: 3 }}>{sub}</div>
      )}
    </div>
  );
}

// ── TrendChart ────────────────────────────────────────────────────────────────

function TrendChart({ title, data, state = STATE_OK, valueKey = "count", color = "#6366f1", height = 60 }) {
  let body;

  if (state === STATE_LOADING) {
    body = <div style={{ color: "#94a3b8", fontSize: ".78rem" }}>Loading…</div>;
  } else if (state === STATE_MISSING) {
    body = (
      <div data-testid="trend-not-enabled"
        style={{ fontSize: ".75rem", color: "#94a3b8", padding: "8px 0" }}>
        Not yet enabled
      </div>
    );
  } else if (state === STATE_ERROR) {
    body = (
      <div data-testid="trend-error"
        style={{ fontSize: ".75rem", color: "#b45309", padding: "8px 0" }}>
        Unable to load
      </div>
    );
  } else if (!data || data.length === 0) {
    body = (
      <div data-testid="trend-no-activity"
        style={{ fontSize: ".75rem", color: "#94a3b8", padding: "8px 0" }}>
        No activity during selected period
      </div>
    );
  } else {
    const max = Math.max(...data.map(d => d[valueKey] || 0), 1);
    body = (
      <div style={{ display: "flex", alignItems: "flex-end", gap: 2, height, overflowX: "auto" }}>
        {data.map((d, i) => (
          <div key={i} title={`${d.date}: ${d[valueKey]}`}
            style={{
              flex: "0 0 12px",
              height: `${Math.max(4, ((d[valueKey] || 0) / max) * height)}px`,
              background: color, borderRadius: "2px 2px 0 0", minWidth: 8, cursor: "default",
            }} />
        ))}
      </div>
    );
  }

  return (
    <div style={{ background: "var(--panel,#fff)", border: "1px solid var(--border,#e5e7eb)", borderRadius: 10, padding: "12px 14px" }}>
      <div style={{ fontSize: ".8rem", fontWeight: 600, marginBottom: 6 }}>{title}</div>
      {body}
    </div>
  );
}

// ── Section label ─────────────────────────────────────────────────────────────
function SectionLabel({ children }) {
  return (
    <div style={{ fontSize: ".8rem", fontWeight: 700, color: "#64748b", marginBottom: 6, textTransform: "uppercase", letterSpacing: ".04em" }}>
      {children}
    </div>
  );
}

// ── AdminAnalytics ────────────────────────────────────────────────────────────

export default function AdminAnalytics({ accessToken }) {
  const [days, setDays]       = useState(30);
  const [summary, setSummary] = useState(null);
  const [trends, setTrends]   = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);

  const load = useCallback(async () => {
    if (!accessToken) return;
    setLoading(true); setError(null);
    try {
      const [s, t] = await Promise.all([
        fetch(`${API}/api/admin/analytics/summary?days=${days}`, {
          headers: { Authorization: `Bearer ${accessToken}` },
        }).then(r => r.json()),
        fetch(`${API}/api/admin/analytics/trends?days=${days}`, {
          headers: { Authorization: `Bearer ${accessToken}` },
        }).then(r => r.json()),
      ]);
      setSummary(s);
      setTrends(t);
    } catch (e) {
      setError(e.message || "Network error");
    }
    setLoading(false);
  }, [accessToken, days]);

  useEffect(() => { load(); }, [load]);

  const cardState = loading ? STATE_LOADING : STATE_OK;

  const u   = summary?.users    || {};
  const p   = summary?.payments || {};
  const ai  = summary?.ai_usage || {};

  // Per-metric states from backend
  const usersState       = loading ? STATE_LOADING : (u.query_ok === false ? STATE_ERROR : STATE_OK);
  const paymentsState    = loading ? STATE_LOADING : (p.query_ok === false ? (p.query_state || STATE_ERROR) : STATE_OK);
  const offerState       = loading ? STATE_LOADING : (summary?.offer_redemptions_state || STATE_MISSING);
  const assignState      = loading ? STATE_LOADING : (summary?.teacher_assignments_state || STATE_MISSING);
  const aiState          = loading ? STATE_LOADING : (ai.state || STATE_MISSING);
  const mockState        = loading ? STATE_LOADING : (summary?.mock_tests_state || STATE_MISSING);

  return (
    <div data-testid="admin-analytics">
      {/* ── Header ────────────────────────────────────────────────────── */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 8, marginBottom: 16 }}>
        <h3 style={{ margin: 0, fontSize: ".95rem", fontWeight: 700 }}>📊 Admin Analytics</h3>
        <div style={{ display: "flex", gap: 4 }}>
          {[7, 30, 90].map(d => (
            <button key={d} onClick={() => setDays(d)}
              style={{
                padding: "4px 10px", borderRadius: 6, border: "1px solid var(--border,#e5e7eb)",
                background: days === d ? "#6366f1" : "var(--panel,#fff)",
                color: days === d ? "#fff" : "var(--text,#374151)",
                fontWeight: 600, fontSize: ".78rem", cursor: "pointer", fontFamily: "inherit",
              }}>
              {d}d
            </button>
          ))}
          <button onClick={load} disabled={loading}
            style={{ padding: "4px 10px", borderRadius: 6, border: "1px solid var(--border,#e5e7eb)", background: "var(--panel,#fff)", cursor: "pointer", fontSize: ".78rem", fontWeight: 600, fontFamily: "inherit", color: "#6366f1" }}>
            {loading ? "…" : "↺"}
          </button>
        </div>
      </div>

      {/* ── Fetch-level error (network / 5xx) ────────────────────────── */}
      {error && (
        <div style={{ color: "#dc2626", fontSize: ".82rem", marginBottom: 10 }}>⚠ {error}</div>
      )}

      {/* ── Users section ────────────────────────────────────────────── */}
      <SectionLabel>Users</SectionLabel>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 16 }}>
        <StatCard label="Total Users"     value={u.total}                    state={usersState} />
        <StatCard label="New Signups"     value={u.new_signups_in_period}    state={usersState} sub={`Last ${days}d`} />
        <StatCard label="Paid Active"     value={u.paid_active}              state={usersState} />
        <StatCard label="Admin Granted"   value={u.admin_granted_access}     state={usersState} />
        <StatCard label="Free (No Access)" value={u.free_no_access}          state={usersState} />
      </div>

      {/* ── Payments section ─────────────────────────────────────────── */}
      <SectionLabel>Payments</SectionLabel>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 16 }}>
        <StatCard label="Total Orders"  value={p.total_in_period}          state={paymentsState} sub={`Last ${days}d`} />
        <StatCard label="Paid"          value={p.paid}                      state={paymentsState} />
        <StatCard label="Failed"        value={p.failed}                    state={paymentsState} />
        <StatCard label="Success Rate"
          value={p.conversion_rate_percent != null ? p.conversion_rate_percent : 0}
          state={paymentsState}
          format="percent" />
      </div>

      {/* ── Mixed section ────────────────────────────────────────────── */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 16 }}>
        <StatCard label="Offer Redemptions"
          value={summary?.offer_redemptions_in_period}
          state={offerState}
          sub={`Last ${days}d`} />
        <StatCard label="Teacher Assignments"
          value={summary?.teacher_student_assignments_total}
          state={assignState}
          sub="Total" />
        <StatCard label="AI Requests"
          value={ai.requests_in_period}
          state={aiState}
          sub={`Last ${days}d`} />
        <StatCard label="AI Tokens"
          value={ai.tokens_in_period}
          state={aiState} />
        <StatCard label="Mock Tests"
          value={summary?.mock_tests_completed_in_period}
          state={mockState}
          sub={`Last ${days}d`} />
      </div>

      {/* ── Trend charts ─────────────────────────────────────────────── */}
      {(summary || loading) && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: 12 }}>
          <TrendChart
            title="Signups"
            data={trends?.signup_trend}
            state={loading ? STATE_LOADING : (trends?.signup_trend_state || STATE_OK)}
            color="#6366f1" />
          <TrendChart
            title="Payments Paid"
            data={trends?.payment_trend}
            state={loading ? STATE_LOADING : (trends?.payment_trend_state || STATE_OK)}
            valueKey="paid"
            color="#22c55e" />
          <TrendChart
            title="Offer Redemptions"
            data={trends?.offer_redemption_trend}
            state={loading ? STATE_LOADING : (trends?.offer_redemption_state || STATE_MISSING)}
            color="#8b5cf6" />
          <TrendChart
            title="AI Tokens Used"
            data={trends?.ai_usage_trend || []}
            state={loading ? STATE_LOADING : (trends?.ai_usage_trend_state || STATE_MISSING)}
            valueKey="tokens"
            color="#f59e0b" />
          <TrendChart
            title="Mock Tests"
            data={trends?.mock_test_trend || []}
            state={loading ? STATE_LOADING : (trends?.mock_test_trend_state || STATE_MISSING)}
            color="#0ea5e9" />
        </div>
      )}

      {/* ── Data availability note ───────────────────────────────────── */}
      {trends && !loading && (() => {
        const da = trends.data_availability || {};
        const missing = [];
        if (da.ai_usage_logs_state === STATE_MISSING)        missing.push("AI usage logs");
        if (da.test_history_state === STATE_MISSING)         missing.push("Mock test history");
        if (da.offer_redemptions_state === STATE_MISSING)    missing.push("Offer redemptions");
        if (da.subscription_timeline_state === STATE_MISSING) missing.push("Subscription timeline");
        const errors = [];
        if (da.ai_usage_logs_state === STATE_ERROR)          errors.push("AI usage logs");
        if (da.test_history_state === STATE_ERROR)           errors.push("Mock test history");
        if (missing.length === 0 && errors.length === 0) return null;
        return (
          <div style={{ marginTop: 10, display: "flex", flexWrap: "wrap", gap: 6 }}>
            {missing.map(name => (
              <span key={name}
                style={{ fontSize: ".72rem", color: "#94a3b8", background: "rgba(148,163,184,.08)", border: "1px solid rgba(148,163,184,.2)", borderRadius: 4, padding: "2px 7px" }}>
                {name}: not yet enabled
              </span>
            ))}
            {errors.map(name => (
              <span key={name}
                style={{ fontSize: ".72rem", color: "#b45309", background: "rgba(245,158,11,.08)", border: "1px solid rgba(245,158,11,.2)", borderRadius: 4, padding: "2px 7px" }}>
                {name}: unable to load
              </span>
            ))}
          </div>
        );
      })()}
    </div>
  );
}
