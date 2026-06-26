/**
 * AdminAnalytics.jsx — Admin analytics dashboard with summary cards and trends.
 * Props: accessToken
 */
import { useCallback, useEffect, useState } from "react";

const API = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

function StatCard({ label, value, sub, available = true }) {
  return (
    <div style={{ background: "var(--panel,#fff)", border: "1px solid var(--border,#e5e7eb)", borderRadius: 10, padding: "12px 16px", flex: "1 1 130px", minWidth: 120 }}>
      <div style={{ fontSize: ".75rem", color: "#64748b", marginBottom: 3 }}>{label}</div>
      <div style={{ fontSize: "1.4rem", fontWeight: 800, color: "var(--text,#1e293b)" }}>
        {!available ? <span style={{ fontSize: ".8rem", color: "#94a3b8" }}>N/A</span> : (value ?? <span style={{ color: "#94a3b8" }}>—</span>)}
      </div>
      {sub && <div style={{ fontSize: ".72rem", color: "#94a3b8", marginTop: 2 }}>{sub}</div>}
    </div>
  );
}

function TrendBar({ data = [], valueKey = "count", dateKey = "date", color = "#6366f1", height = 60 }) {
  if (!data || data.length === 0) return <div style={{ color: "#94a3b8", fontSize: ".78rem" }}>No data in period.</div>;
  const max = Math.max(...data.map(d => d[valueKey] || 0), 1);
  return (
    <div style={{ display: "flex", alignItems: "flex-end", gap: 2, height, overflowX: "auto" }}>
      {data.map((d, i) => (
        <div key={i} title={`${d[dateKey]}: ${d[valueKey]}`}
          style={{ flex: "0 0 12px", height: `${Math.max(4, ((d[valueKey] || 0) / max) * height)}px`, background: color, borderRadius: "2px 2px 0 0", minWidth: 8, cursor: "default" }} />
      ))}
    </div>
  );
}

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
        fetch(`${API}/api/admin/analytics/summary?days=${days}`, { headers: { Authorization: `Bearer ${accessToken}` } }).then(r => r.json()),
        fetch(`${API}/api/admin/analytics/trends?days=${days}`, { headers: { Authorization: `Bearer ${accessToken}` } }).then(r => r.json()),
      ]);
      setSummary(s);
      setTrends(t);
    } catch (e) { setError(e.message); }
    setLoading(false);
  }, [accessToken, days]);

  useEffect(() => { load(); }, [load]);

  const u = summary?.users || {};
  const p = summary?.payments || {};
  const ai = summary?.ai_usage || {};

  return (
    <div data-testid="admin-analytics">
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 8, marginBottom: 16 }}>
        <h3 style={{ margin: 0, fontSize: ".95rem", fontWeight: 700 }}>📊 Admin Analytics</h3>
        <div style={{ display: "flex", gap: 4 }}>
          {[7, 30, 90].map(d => (
            <button key={d} onClick={() => setDays(d)}
              style={{ padding: "4px 10px", borderRadius: 6, border: "1px solid var(--border,#e5e7eb)", background: days === d ? "#6366f1" : "var(--panel,#fff)", color: days === d ? "#fff" : "var(--text,#374151)", fontWeight: 600, fontSize: ".78rem", cursor: "pointer", fontFamily: "inherit" }}>
              {d}d
            </button>
          ))}
          <button onClick={load} disabled={loading}
            style={{ padding: "4px 10px", borderRadius: 6, border: "1px solid var(--border,#e5e7eb)", background: "var(--panel,#fff)", cursor: "pointer", fontSize: ".78rem", fontWeight: 600, fontFamily: "inherit", color: "#6366f1" }}>
            {loading ? "…" : "↺"}
          </button>
        </div>
      </div>

      {error && <div style={{ color: "#dc2626", fontSize: ".82rem", marginBottom: 10 }}>⚠ {error}</div>}

      {/* Summary cards */}
      {summary && (
        <>
          <div style={{ fontSize: ".8rem", fontWeight: 700, color: "#64748b", marginBottom: 6, textTransform: "uppercase", letterSpacing: ".04em" }}>Users</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 16 }}>
            <StatCard label="Total Users" value={u.total} />
            <StatCard label="New Signups" value={u.new_signups_in_period} sub={`Last ${days}d`} />
            <StatCard label="Paid Active" value={u.paid_active} />
            <StatCard label="Admin Granted" value={u.admin_granted_access} />
            <StatCard label="Free (No Access)" value={u.free_no_access} />
          </div>

          <div style={{ fontSize: ".8rem", fontWeight: 700, color: "#64748b", marginBottom: 6, textTransform: "uppercase", letterSpacing: ".04em" }}>Payments</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 16 }}>
            <StatCard label="Total Orders" value={p.total_in_period} sub={`Last ${days}d`} />
            <StatCard label="Paid" value={p.paid} />
            <StatCard label="Failed" value={p.failed} />
            <StatCard label="Success Rate" value={p.conversion_rate_percent != null ? `${p.conversion_rate_percent}%` : "—"} />
          </div>

          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 16 }}>
            <StatCard label="Offer Redemptions" value={summary.offer_redemptions_in_period} sub={`Last ${days}d`} />
            <StatCard label="Teacher Assignments" value={summary.teacher_student_assignments_total} sub="Total" />
            <StatCard label="AI Requests" value={ai.requests_in_period} sub={`Last ${days}d`} available={ai.available} />
            <StatCard label="AI Tokens" value={ai.tokens_in_period != null ? ai.tokens_in_period.toLocaleString() : null} available={ai.available} />
            <StatCard label="Mock Tests Completed" value={summary.mock_tests_completed_in_period} sub={`Last ${days}d`} available={summary.mock_tests_completed_in_period !== null} />
          </div>
        </>
      )}

      {/* Trend charts */}
      {trends && (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: 12 }}>
            <div style={{ background: "var(--panel,#fff)", border: "1px solid var(--border,#e5e7eb)", borderRadius: 10, padding: "12px 14px" }}>
              <div style={{ fontSize: ".8rem", fontWeight: 600, marginBottom: 6 }}>Signups</div>
              <TrendBar data={trends.signup_trend} color="#6366f1" />
            </div>
            <div style={{ background: "var(--panel,#fff)", border: "1px solid var(--border,#e5e7eb)", borderRadius: 10, padding: "12px 14px" }}>
              <div style={{ fontSize: ".8rem", fontWeight: 600, marginBottom: 6 }}>Payments Paid</div>
              <TrendBar data={trends.payment_trend} valueKey="paid" color="#22c55e" />
            </div>
            <div style={{ background: "var(--panel,#fff)", border: "1px solid var(--border,#e5e7eb)", borderRadius: 10, padding: "12px 14px" }}>
              <div style={{ fontSize: ".8rem", fontWeight: 600, marginBottom: 6 }}>Offer Redemptions</div>
              <TrendBar data={trends.offer_redemption_trend} color="#8b5cf6" />
            </div>
            {trends.ai_usage_trend && (
              <div style={{ background: "var(--panel,#fff)", border: "1px solid var(--border,#e5e7eb)", borderRadius: 10, padding: "12px 14px" }}>
                <div style={{ fontSize: ".8rem", fontWeight: 600, marginBottom: 6 }}>AI Tokens Used</div>
                <TrendBar data={trends.ai_usage_trend} valueKey="tokens" color="#f59e0b" />
              </div>
            )}
            {trends.mock_test_trend && (
              <div style={{ background: "var(--panel,#fff)", border: "1px solid var(--border,#e5e7eb)", borderRadius: 10, padding: "12px 14px" }}>
                <div style={{ fontSize: ".8rem", fontWeight: 600, marginBottom: 6 }}>Mock Tests</div>
                <TrendBar data={trends.mock_test_trend} color="#0ea5e9" />
              </div>
            )}
          </div>
          {!trends.data_availability?.ai_usage_logs && (
            <div style={{ marginTop: 8, fontSize: ".72rem", color: "#94a3b8" }}>⚡ AI usage trends unavailable (ai_usage_logs table not migrated).</div>
          )}
        </>
      )}
    </div>
  );
}
