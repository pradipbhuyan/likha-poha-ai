/**
 * AdminOperationsPage.jsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Operations Dashboard — admin-only monitoring page for the Admin Console.
 *
 * Sections:
 *   1. System Health
 *   2. Payment Monitoring
 *   3. Webhook Monitoring
 *   4. Subscription Monitoring
 *   5. User & Usage Metrics
 *   6. Alerts & Incidents
 *   7. Expiry Job
 *
 * Date-range filter: today | 7d | 30d
 * All sections show loading / error / empty states.
 * In-memory metrics are clearly labelled as process-local.
 */

import { useCallback, useEffect, useState } from "react";
import {
  getOperationsSummary,
  getOperationsHealth,
  getOperationsPayments,
  getOperationsWebhooks,
  getOperationsSubscriptions,
  getOperationsUsage,
  getOperationsAlerts,
  getExpiryJobStatus,
  runExpiryJob,
} from "../api/adminOperations";

// ── Helpers ──────────────────────────────────────────────────────────────────

const DATE_OPTIONS = [
  { label: "Today", days: 1 },
  { label: "7 days", days: 7 },
  { label: "30 days", days: 30 },
];

function StatCard({ label, value, sub, note }) {
  return (
    <div
      style={{
        background: "var(--panel, #fff)",
        border: "1px solid var(--border, #e5e7eb)",
        borderRadius: 10,
        padding: "14px 18px",
        minWidth: 120,
        flex: "1 1 130px",
      }}
    >
      <div style={{ fontSize: ".78rem", color: "#64748b", marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: "1.5rem", fontWeight: 800, color: "var(--text, #1e293b)" }}>
        {value ?? <span style={{ color: "#94a3b8" }}>—</span>}
      </div>
      {sub && <div style={{ fontSize: ".74rem", color: "#94a3b8", marginTop: 2 }}>{sub}</div>}
      {note && (
        <div style={{ fontSize: ".68rem", color: "#f59e0b", marginTop: 4, fontStyle: "italic" }}>
          ⚡ {note}
        </div>
      )}
    </div>
  );
}

function SectionHeader({ title, icon }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
      <span style={{ fontSize: "1.2rem" }}>{icon}</span>
      <h3 style={{ margin: 0, fontSize: "1rem", fontWeight: 700, color: "var(--text, #1e293b)" }}>
        {title}
      </h3>
    </div>
  );
}

function EventTable({ rows, columns }) {
  if (!rows || rows.length === 0) {
    return (
      <div style={{ color: "#94a3b8", fontSize: ".82rem", padding: "10px 0" }}>
        No events in this period.
      </div>
    );
  }
  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: ".82rem" }}>
        <thead>
          <tr>
            {columns.map((c) => (
              <th
                key={c.key}
                style={{
                  textAlign: "left",
                  padding: "5px 8px",
                  borderBottom: "1px solid var(--border, #e5e7eb)",
                  color: "#64748b",
                  fontWeight: 600,
                  whiteSpace: "nowrap",
                }}
              >
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} style={{ borderBottom: "1px solid var(--border, #f1f5f9)" }}>
              {columns.map((c) => (
                <td key={c.key} style={{ padding: "5px 8px", color: "var(--text, #374151)", whiteSpace: "nowrap" }}>
                  {row[c.key] ?? "—"}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Section({ children, error }) {
  return (
    <div
      style={{
        background: "var(--panel, #fff)",
        border: "1px solid var(--border, #e5e7eb)",
        borderRadius: 12,
        padding: "18px 20px",
        marginBottom: 16,
      }}
    >
      {error && (
        <div
          style={{
            background: "#fef2f2",
            border: "1px solid #fecaca",
            borderRadius: 8,
            padding: "8px 12px",
            marginBottom: 12,
            fontSize: ".8rem",
            color: "#dc2626",
          }}
        >
          ⚠ {error}
        </div>
      )}
      {children}
    </div>
  );
}

function InMemoryNote() {
  return (
    <div
      style={{
        background: "#fffbeb",
        border: "1px solid #fde68a",
        borderRadius: 6,
        padding: "6px 10px",
        fontSize: ".74rem",
        color: "#92400e",
        marginBottom: 10,
      }}
    >
      ⚡ <strong>In-memory counters</strong> are process-local and reset on server restart. Historical counts come from the database.
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────

export default function AdminOperationsPage() {
  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(true);
  const [refreshKey, setRefreshKey] = useState(0);

  const [_summary, setSummary] = useState(null);
  const [health, setHealth] = useState(null);
  const [payments, setPayments] = useState(null);
  const [webhooks, setWebhooks] = useState(null);
  const [subscriptions, setSubscriptions] = useState(null);
  const [usage, setUsage] = useState(null);
  const [alerts, setAlerts] = useState(null);
  const [expiryStatus, setExpiryStatus] = useState(null);

  const [expiryRunning, setExpiryRunning] = useState(false);
  const [expiryResult, setExpiryResult] = useState(null);
  const [expiryConfirm, setExpiryConfirm] = useState(false);

  const [errors, setErrors] = useState({});

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setErrors({});
    const errs = {};
    const safe = async (key, fn) => {
      try {
        return await fn();
      } catch (e) {
        errs[key] = e?.message || String(e);
        return null;
      }
    };
    // authFetch already returns parsed JSON — no .json() call needed
    const [s, h, p, w, sub, u, a, es] = await Promise.all([
      safe("summary", () => getOperationsSummary()),
      safe("health", () => getOperationsHealth()),
      safe("payments", () => getOperationsPayments(days)),
      safe("webhooks", () => getOperationsWebhooks(days)),
      safe("subscriptions", () => getOperationsSubscriptions(days)),
      safe("usage", () => getOperationsUsage()),
      safe("alerts", () => getOperationsAlerts(days)),
      safe("expiryStatus", () => getExpiryJobStatus()),
    ]);
    setSummary(s);
    setHealth(h);
    setPayments(p);
    setWebhooks(w);
    setSubscriptions(sub);
    setUsage(u);
    setAlerts(a);
    setExpiryStatus(es);
    setErrors(errs);
    setLoading(false);
  }, [days, refreshKey]);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  const handleRunExpiryJob = async () => {
    setExpiryConfirm(false);
    setExpiryRunning(true);
    setExpiryResult(null);
    try {
      // authFetch already returns parsed JSON
      const data = await runExpiryJob();
      setExpiryResult(data);
      setRefreshKey((k) => k + 1);
    } catch (e) {
      setExpiryResult({ error: e?.message || "Unknown error" });
    } finally {
      setExpiryRunning(false);
    }
  };

  return (
    <div
      className="premium-section"
      style={{ maxWidth: 1100, margin: "0 auto", padding: "20px 16px" }}
      data-testid="admin-operations-page"
    >
      {/* ── Header ── */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: 12,
          marginBottom: 20,
        }}
      >
        <div>
          <p className="eyebrow">Admin Console</p>
          <h2 style={{ margin: 0 }}>🖥️ Operations Dashboard</h2>
          <p style={{ color: "#64748b", marginTop: 4, fontSize: ".88rem" }}>
            System health, payments, subscriptions, and operational metrics.
          </p>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          {/* Date filter */}
          <div style={{ display: "flex", gap: 4 }}>
            {DATE_OPTIONS.map((o) => (
              <button
                key={o.days}
                onClick={() => setDays(o.days)}
                style={{
                  padding: "5px 12px",
                  borderRadius: 7,
                  border: "1px solid var(--border, #e5e7eb)",
                  background: days === o.days ? "var(--primary, #6366f1)" : "var(--panel, #fff)",
                  color: days === o.days ? "#fff" : "var(--text, #374151)",
                  fontWeight: 600,
                  fontSize: ".82rem",
                  cursor: "pointer",
                  fontFamily: "inherit",
                }}
              >
                {o.label}
              </button>
            ))}
          </div>
          <button
            onClick={() => setRefreshKey((k) => k + 1)}
            disabled={loading}
            style={{
              padding: "5px 14px",
              borderRadius: 7,
              border: "1px solid var(--border, #e5e7eb)",
              background: "var(--panel, #fff)",
              cursor: loading ? "not-allowed" : "pointer",
              fontSize: ".82rem",
              fontWeight: 600,
              fontFamily: "inherit",
              color: "var(--primary, #6366f1)",
            }}
          >
            {loading ? "Loading…" : "↺ Refresh"}
          </button>
        </div>
      </div>

      {loading && (
        <div style={{ textAlign: "center", color: "#94a3b8", padding: 40, fontSize: ".9rem" }}>
          Loading operations data…
        </div>
      )}

      {!loading && (
        <>
          {/* ── 1. System Health ── */}
          <Section error={errors.health}>
            <SectionHeader title="System Health" icon="❤️" />
            <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
              <StatCard
                label="App Status"
                value={health?.app?.status === "ok" ? "Healthy" : "Unknown"}
                sub={`Python ${health?.app?.python_version ?? "?"}`}
              />
              <StatCard
                label="Database"
                value={health?.database?.connected ? "Connected" : "Error"}
                sub={health?.database?.error || "Supabase OK"}
              />
              <StatCard
                label="Critical Config"
                value={health?.config_critical_ok ? "Ready" : "Missing"}
                sub="Supabase URL + Service Key"
              />
            </div>
            {health?.config && (
              <div style={{ marginTop: 14, display: "flex", gap: 8, flexWrap: "wrap" }}>
                {Object.entries(health.config).map(([k, v]) => (
                  <span
                    key={k}
                    style={{
                      padding: "2px 9px",
                      borderRadius: 6,
                      fontSize: ".74rem",
                      fontWeight: 600,
                      background: v ? "#f0fdf4" : "#fef2f2",
                      color: v ? "#166534" : "#dc2626",
                      border: `1px solid ${v ? "#bbf7d0" : "#fecaca"}`,
                    }}
                  >
                    {k}: {v ? "✓" : "✗"}
                  </span>
                ))}
              </div>
            )}
            <div style={{ fontSize: ".74rem", color: "#94a3b8", marginTop: 10 }}>
              Last checked: {health?.checked_at ? new Date(health.checked_at).toLocaleString() : "—"}
            </div>
          </Section>

          {/* ── 2. Payment Monitoring ── */}
          <Section error={errors.payments}>
            <SectionHeader title="Payment Monitoring" icon="💳" />
            <InMemoryNote />
            <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 14 }}>
              <StatCard label="Total Payments" value={payments?.summary?.total_payments} sub={`Last ${days}d`} />
              <StatCard label="Successful" value={payments?.summary?.paid} sub="Paid" />
              <StatCard label="Failed" value={payments?.summary?.failed} sub="Sig. failure" />
              <StatCard
                label="Success Rate"
                value={payments?.summary?.success_rate_percent != null ? `${payments.summary.success_rate_percent}%` : "—"}
                sub="Paid / Total"
              />
              <StatCard
                label="Pending"
                value={payments?.summary?.created_pending}
                sub="Awaiting verify"
              />
              <StatCard
                label="Verified (session)"
                value={payments?.in_memory_counters?.["payment.verified"]}
                note="In-memory"
              />
            </div>
            {payments?.recent_failures?.length > 0 && (
              <>
                <div style={{ fontWeight: 600, fontSize: ".82rem", color: "#dc2626", marginBottom: 6 }}>
                  Recent Failures
                </div>
                <EventTable
                  rows={payments.recent_failures}
                  columns={[
                    { key: "created_at", label: "Time" },
                    { key: "status", label: "Status" },
                    { key: "plan_key", label: "Plan" },
                    { key: "amount", label: "₹" },
                    { key: "order_id", label: "Order ID" },
                  ]}
                />
              </>
            )}
          </Section>

          {/* ── 3. Webhook Monitoring ── */}
          <Section error={errors.webhooks}>
            <SectionHeader title="Webhook Monitoring" icon="🔔" />
            <InMemoryNote />
            <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 14 }}>
              <StatCard
                label="Webhook Confirmed"
                value={webhooks?.webhook_confirmed_via_db}
                sub={`DB source · last ${days}d`}
              />
              <StatCard
                label="Last Received"
                value={webhooks?.last_received ? "Recent" : "None"}
                sub={webhooks?.last_received || "No data"}
              />
            </div>
            {webhooks?.recent_webhook_audit_events?.length > 0 && (
              <EventTable
                rows={webhooks.recent_webhook_audit_events}
                columns={[
                  { key: "created_at", label: "Time" },
                  { key: "event_type", label: "Event" },
                ]}
              />
            )}
          </Section>

          {/* ── 4. Subscription Monitoring ── */}
          <Section error={errors.subscriptions}>
            <SectionHeader title="Subscription Monitoring" icon="📋" />
            <InMemoryNote />
            <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 14 }}>
              {subscriptions?.active_subscriptions &&
                Object.entries(subscriptions.active_subscriptions).map(([plan, count]) => (
                  <StatCard key={plan} label={plan} value={count} sub="Active users" />
                ))}
              <StatCard
                label="Expired (session)"
                value={subscriptions?.in_memory_counters?.["subscription.expired"]}
                note="In-memory"
              />
              <StatCard
                label="Fallbacks (session)"
                value={subscriptions?.in_memory_counters?.["subscription.fallback_applied"]}
                note="In-memory"
              />
            </div>
            {subscriptions?.recent_timeline_events?.length > 0 && (
              <>
                <div style={{ fontWeight: 600, fontSize: ".82rem", marginBottom: 6, color: "#374151" }}>
                  Recent Timeline Events
                </div>
                <EventTable
                  rows={subscriptions.recent_timeline_events}
                  columns={[
                    { key: "created_at", label: "Time" },
                    { key: "event_type", label: "Event" },
                    { key: "from_plan", label: "From" },
                    { key: "to_plan", label: "To" },
                    { key: "source", label: "Source" },
                  ]}
                />
              </>
            )}
          </Section>

          {/* ── 5. User & Usage Metrics ── */}
          <Section error={errors.usage}>
            <SectionHeader title="User & Usage Metrics" icon="👥" />
            <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 14 }}>
              <StatCard label="Total Users" value={usage?.users?.total} sub="All roles" />
              <StatCard label="Students" value={usage?.users?.student} />
              <StatCard label="Parents" value={usage?.users?.parent} />
              <StatCard label="Teachers" value={usage?.users?.teacher} />
              <StatCard label="Assignments" value={usage?.teacher_student_assignments} sub="Teacher→Student" />
              <StatCard label="Offer Redemptions" value={usage?.offer_redemptions} />
            </div>
            <InMemoryNote />
            <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
              <StatCard
                label="Rate Limit Hits"
                value={usage?.in_memory_counters?.["rate_limit.exceeded"]}
                note="In-memory"
              />
              <StatCard
                label="Login Failures"
                value={usage?.in_memory_counters?.["login.failure"]}
                note="In-memory"
              />
              <StatCard
                label="Students Created"
                value={usage?.in_memory_counters?.["teacher.student_created"]}
                note="In-memory"
              />
            </div>
          </Section>

          {/* ── 6. Alerts & Incidents ── */}
          <Section error={errors.alerts}>
            <SectionHeader title="Alerts & Incidents" icon="🚨" />
            <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 14 }}>
              {alerts?.alert_counts &&
                Object.entries(alerts.alert_counts).map(([type, count]) => (
                  <StatCard key={type} label={type} value={count} sub={`Last ${days}d`} />
                ))}
              {(!alerts?.alert_counts || Object.keys(alerts.alert_counts).length === 0) && (
                <div style={{ color: "#64748b", fontSize: ".85rem", padding: "8px 0" }}>
                  No alerts in this period.
                </div>
              )}
            </div>
            {alerts?.recent_alerts?.length > 0 && (
              <EventTable
                rows={alerts.recent_alerts}
                columns={[
                  { key: "created_at", label: "Time" },
                  { key: "event_type", label: "Event" },
                  { key: "entity_type", label: "Entity Type" },
                  { key: "entity_id", label: "Entity ID" },
                ]}
              />
            )}
          </Section>

          {/* ── 7. Expiry Job ── */}
          <Section error={errors.expiryStatus}>
            <SectionHeader title="Expiry Job" icon="⏰" />
            <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 14 }}>
              <StatCard
                label="Last Run"
                value={expiryStatus?.last_run ? new Date(expiryStatus.last_run).toLocaleString() : "Never"}
                sub="From audit log"
              />
              <StatCard
                label="Users Inspected"
                value={expiryStatus?.last_run_summary?.users_inspected ?? "—"}
                sub="Last run"
              />
              <StatCard
                label="Users Revoked"
                value={expiryStatus?.last_run_summary?.users_revoked ?? "—"}
                sub="Last run"
              />
              <StatCard
                label="Errors"
                value={expiryStatus?.last_run_summary?.errors ?? "—"}
                sub="Last run"
              />
              <StatCard
                label="Runs (session)"
                value={expiryStatus?.in_memory_counters?.["expiry_job.ran"]}
                note="In-memory"
              />
            </div>

            {/* Run button */}
            <div style={{ marginTop: 10 }}>
              {!expiryConfirm && !expiryRunning && (
                <button
                  onClick={() => setExpiryConfirm(true)}
                  data-testid="run-expiry-job-btn"
                  style={{
                    padding: "7px 18px",
                    background: "#f59e0b",
                    color: "#fff",
                    border: "none",
                    borderRadius: 8,
                    fontWeight: 700,
                    fontSize: ".85rem",
                    cursor: "pointer",
                    fontFamily: "inherit",
                  }}
                >
                  ▶ Run Expiry Job Now
                </button>
              )}
              {expiryConfirm && (
                <div
                  style={{
                    background: "#fffbeb",
                    border: "1px solid #fde68a",
                    borderRadius: 8,
                    padding: "12px 16px",
                    display: "flex",
                    alignItems: "center",
                    gap: 12,
                    flexWrap: "wrap",
                  }}
                >
                  <span style={{ fontSize: ".85rem", color: "#92400e" }}>
                    ⚠ This will revoke expired subscriptions. Confirm?
                  </span>
                  <button
                    onClick={handleRunExpiryJob}
                    data-testid="confirm-expiry-job-btn"
                    style={{
                      padding: "5px 14px",
                      background: "#ef4444",
                      color: "#fff",
                      border: "none",
                      borderRadius: 6,
                      fontWeight: 700,
                      fontSize: ".82rem",
                      cursor: "pointer",
                      fontFamily: "inherit",
                    }}
                  >
                    Yes, Run
                  </button>
                  <button
                    onClick={() => setExpiryConfirm(false)}
                    style={{
                      padding: "5px 14px",
                      background: "var(--panel, #fff)",
                      border: "1px solid var(--border, #e5e7eb)",
                      borderRadius: 6,
                      fontWeight: 600,
                      fontSize: ".82rem",
                      cursor: "pointer",
                      fontFamily: "inherit",
                    }}
                  >
                    Cancel
                  </button>
                </div>
              )}
              {expiryRunning && (
                <div style={{ color: "#64748b", fontSize: ".85rem" }}>Running expiry job…</div>
              )}
              {expiryResult && (
                <div
                  data-testid="expiry-job-result"
                  style={{
                    marginTop: 10,
                    background: expiryResult.error ? "#fef2f2" : "#f0fdf4",
                    border: `1px solid ${expiryResult.error ? "#fecaca" : "#bbf7d0"}`,
                    borderRadius: 8,
                    padding: "10px 14px",
                    fontSize: ".82rem",
                    color: expiryResult.error ? "#dc2626" : "#166534",
                  }}
                >
                  {expiryResult.error ? (
                    <span>✗ Error: {expiryResult.error}</span>
                  ) : (
                    <span>
                      ✓ Completed — Inspected: {expiryResult.users_inspected ?? 0},
                      Revoked: {expiryResult.users_revoked ?? 0},
                      Skipped: {expiryResult.users_skipped_already_revoked ?? 0},
                      Errors: {expiryResult.errors ?? 0}
                    </span>
                  )}
                </div>
              )}
            </div>
          </Section>
        </>
      )}
    </div>
  );
}
