/**
 * AdminLearningSimulationPage.jsx — Admin Learning Simulation
 * ─────────────────────────────────────────────────────────────────────────────
 * Admin-only page to run end-to-end platform validation simulations.
 * Simulates Vijay (student) + Manish/Manisha (parents) using the platform
 * for 7-day cycles. Detects anomalies and creates Product Bug reports.
 * ─────────────────────────────────────────────────────────────────────────────
 */
import { useCallback, useEffect, useState } from "react";
import {
  setupSimulationUsers,
  getSimulationStatus,
  runSimulation,
  resetSimulation,
  listSimulationRuns,
  getSimulationAnomalies,
  createBugForAnomaly,
} from "../api/learningSimulation";

// ── Design tokens ─────────────────────────────────────────────────────────────
const C = {
  indigo: "#6366f1", purple: "#8b5cf6", green: "#22c55e",
  orange: "#f59e0b", red: "#ef4444", blue: "#3b82f6",
  muted: "#94a3b8", text: "var(--text,#374151)",
  border: "var(--border,#e5e7eb)", panel: "var(--panel,#fff)",
  surface: "var(--surface2,#f8fafc)",
};
const card = (extra = {}) => ({
  background: C.panel, border: `1px solid ${C.border}`,
  borderRadius: 14, padding: "16px 20px",
  boxShadow: "0 1px 4px rgba(0,0,0,.06)", ...extra,
});
const SEV_COLOR = { critical: C.red, high: C.orange, medium: C.blue, low: C.muted };

// ── Summary Card ──────────────────────────────────────────────────────────────
function StatCard({ label, value, color = C.indigo, testid }) {
  return (
    <div data-testid={testid} style={{ ...card(), textAlign: "center", minWidth: 110 }}>
      <div style={{ fontSize: "1.6rem", fontWeight: 800, color }}>{value ?? "—"}</div>
      <div style={{ fontSize: ".72rem", color: C.muted, marginTop: 3 }}>{label}</div>
    </div>
  );
}

// ── Anomaly Row ───────────────────────────────────────────────────────────────
function AnomalyRow({ anomaly, onCreateBug }) {
  const [creating, setCreating] = useState(false);
  const color = SEV_COLOR[anomaly.severity] || C.muted;
  return (
    <div style={{
      display: "flex", alignItems: "flex-start", gap: 10,
      padding: "8px 12px", borderBottom: `1px solid ${C.border}`,
      fontSize: ".8rem",
    }}>
      <span style={{ minWidth: 60, fontWeight: 700, color }}>{anomaly.severity}</span>
      <span style={{ flex: 1, color: C.text }}>{anomaly.message}</span>
      <span style={{ minWidth: 80, color: C.muted, fontSize: ".72rem" }}>
        {anomaly.anomaly_type?.replace(/_/g, " ")}
      </span>
      {anomaly.status === "bug_created" ? (
        <span style={{ fontSize: ".72rem", color: C.green }}>✓ Bug created</span>
      ) : (
        <button
          onClick={async () => { setCreating(true); await onCreateBug(anomaly.id); setCreating(false); }}
          disabled={creating}
          style={{
            padding: "3px 10px", borderRadius: 6, border: "none",
            background: creating ? C.muted : C.red, color: "#fff",
            fontSize: ".72rem", fontWeight: 600, cursor: creating ? "not-allowed" : "pointer",
            fontFamily: "inherit", whiteSpace: "nowrap",
          }}>
          {creating ? "…" : "Create Bug"}
        </button>
      )}
    </div>
  );
}

// ── Run Row ───────────────────────────────────────────────────────────────────
function RunRow({ run, onSelect, selected }) {
  const status_color = run.status === "completed" ? C.green : run.status === "failed" ? C.red : C.orange;
  return (
    <div
      onClick={() => onSelect(run.id)}
      style={{
        display: "flex", gap: 10, alignItems: "center", padding: "8px 12px",
        borderBottom: `1px solid ${C.border}`, cursor: "pointer", fontSize: ".8rem",
        background: selected ? "rgba(99,102,241,.07)" : C.panel,
      }}>
      <span style={{ fontWeight: 700, color: status_color, minWidth: 70 }}>{run.status}</span>
      <span style={{ flex: 1, color: C.text }}>
        Day {run.cycle_start_day}–{run.cycle_end_day}
        {run.dry_run ? " (dry run)" : ""}
      </span>
      <span style={{ color: C.muted, fontSize: ".72rem" }}>
        {run.anomalies_count || 0} anomalies · {run.bugs_created_count || 0} bugs
      </span>
      <span style={{ color: C.muted, fontSize: ".68rem" }}>
        {run.created_at ? new Date(run.created_at).toLocaleDateString() : ""}
      </span>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────
export default function AdminLearningSimulationPage({ user: _user }) {
  const [status, setStatus]     = useState(null);
  const [runs, setRuns]         = useState([]);
  const [anomalies, setAnomalies] = useState([]);
  const [selectedRun, setSelectedRun] = useState(null);
  const [loading, setLoading]   = useState(true);
  const [running, setRunning]   = useState(false);
  const [resetting, setResetting] = useState(false);
  const [msg, setMsg]           = useState(null);
  const [lastResult, setLastResult] = useState(null);

  // Controls
  const [cycleDays, setCycleDays]     = useState(7);
  const [dryRun, setDryRun]           = useState(false);
  const [createBugs, setCreateBugs]   = useState(true);
  const [strictVal, setStrictVal]     = useState(true);
  const [showReset, setShowReset]     = useState(false);
  const [settingUp, setSettingUp]     = useState(false);

  const loadStatus = useCallback(async () => {
    try {
      const s = await getSimulationStatus();
      setStatus(s);
    } catch (e) { setMsg("Error loading status: " + e.message); }
    finally { setLoading(false); }
  }, []);

  const loadRuns = useCallback(async () => {
    try {
      const r = await listSimulationRuns();
      setRuns(r.runs || []);
    } catch { setRuns([]); }
  }, []);

  const loadAnomalies = useCallback(async (runId) => {
    try {
      const a = await getSimulationAnomalies(runId);
      setAnomalies(a.anomalies || []);
    } catch { setAnomalies([]); }
  }, []);

  useEffect(() => {
    loadStatus();
    loadRuns();
  }, [loadStatus, loadRuns]);

  async function handleRun() {
    setRunning(true);
    setMsg(null);
    setLastResult(null);
    try {
      const result = await runSimulation({
        cycle_days:        cycleDays,
        dry_run:           dryRun,
        create_bugs:       createBugs,
        strict_validation: strictVal,
      });
      setLastResult(result);
      setMsg(`✅ Simulation ${dryRun ? "(dry run) " : ""}completed — Day ${result.cycle_start_day}–${result.cycle_end_day}`);
      await loadStatus();
      await loadRuns();
      if (result.run_id) {
        setSelectedRun(result.run_id);
        await loadAnomalies(result.run_id);
      }
    } catch (e) {
      setMsg("❌ " + e.message);
    } finally {
      setRunning(false);
    }
  }

  async function handleReset() {
    setResetting(true);
    setMsg(null);
    try {
      const r = await resetSimulation();
      setMsg("✅ Simulation data reset. " + (r.message || ""));
      setRuns([]);
      setAnomalies([]);
      setLastResult(null);
      setSelectedRun(null);
      await loadStatus();
    } catch (e) {
      setMsg("❌ Reset failed: " + e.message);
    } finally {
      setResetting(false);
      setShowReset(false);
    }
  }

  async function handleSelectRun(runId) {
    setSelectedRun(runId);
    await loadAnomalies(runId);
  }

  async function handleCreateBug(anomalyId) {
    try {
      await createBugForAnomaly(anomalyId);
      await loadAnomalies(selectedRun);
    } catch (e) {
      setMsg("❌ Could not create bug: " + e.message);
    }
  }

  async function handleSetupUsers() {
    setSettingUp(true);
    setMsg(null);
    try {
      const r = await setupSimulationUsers();
      const msgs = r.messages?.join(" · ") || "";
      setMsg(`✅ Users ready. ${msgs}`);
      await loadStatus();
    } catch (e) {
      setMsg("❌ Setup failed: " + e.message);
    } finally {
      setSettingUp(false);
    }
  }

  if (loading) return <div style={{ padding: 40, textAlign: "center", color: C.muted }}>Loading simulation status…</div>;

  const currentDay = status?.current_day || 0;
  const vijay = status?.vijay_profile;
  const latestRun = runs[0];

  return (
    <div data-testid="admin-learning-simulation-page"
      style={{ maxWidth: 1200, margin: "0 auto", padding: "0 14px 60px", fontFamily: "inherit" }}>

      {/* Header */}
      <div style={{ marginBottom: 20 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <span style={{
            padding: "2px 10px", borderRadius: 99, background: "rgba(99,102,241,.12)",
            color: C.indigo, fontSize: ".72rem", fontWeight: 800,
          }}>🔬 ADMIN ONLY</span>
          <h2 style={{ margin: 0, fontWeight: 800, fontSize: "1.1rem" }}>Learning Simulation</h2>
        </div>
        <p style={{ margin: "4px 0 0", fontSize: ".82rem", color: C.muted }}>
          Simulate Vijay (student) + Manish/Manisha (parents) over 7-day cycles.
          Validates dashboards, detects anomalies, creates Product Bugs.
          All users are synthetic test accounts — no real users affected.
        </p>
      </div>

      {msg && (
        <div style={{
          padding: "8px 14px", borderRadius: 9, marginBottom: 14, fontSize: ".82rem",
          background: msg.startsWith("✅") ? "rgba(34,197,94,.08)" : "rgba(239,68,68,.08)",
          color: msg.startsWith("✅") ? "#166534" : C.red,
          border: `1px solid ${msg.startsWith("✅") ? "rgba(34,197,94,.3)" : "rgba(239,68,68,.25)"}`,
        }}>{msg}</div>
      )}

      {/* Summary cards */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 10, marginBottom: 22 }}>
        <StatCard label="Simulated Day" value={currentDay} color={C.indigo} testid="stat-sim-day" />
        <StatCard label="Next Cycle" value={`${status?.next_cycle_start}–${status?.next_cycle_end}`} color={C.purple} />
        <StatCard label="Total Runs" value={status?.total_runs || 0} color={C.blue} />
        <StatCard label="Vijay Plan" value={vijay?.subscription_plan || "—"} color={vijay?.subscription_plan === "family_premium" ? C.green : C.red} />
        <StatCard label="CBSE Access" value={vijay?.access_cbse ? "✓ Yes" : "✗ No"} color={vijay?.access_cbse ? C.green : C.red} />
        <StatCard label="Last Anomalies" value={latestRun?.anomalies_count ?? "—"} color={C.orange} />
        <StatCard label="Bugs Created" value={latestRun?.bugs_created_count ?? "—"} color={C.red} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "340px 1fr", gap: 16, alignItems: "start" }}>

        {/* ── Left: Controls ── */}
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>

              {/* Step 1: Setup Users */}
          <div style={card({ borderColor: status?.users_setup ? "rgba(34,197,94,.3)" : "rgba(99,102,241,.4)" })}>
            <h4 style={{ margin: "0 0 6px", fontSize: ".85rem", fontWeight: 800 }}>
              Step 1: Create Simulation Users
            </h4>
            <p style={{ margin: "0 0 10px", fontSize: ".75rem", color: C.muted }}>
              Creates Vijay (student), Manish + Manisha (parents) in Supabase with Family Premium access.
              Safe to run multiple times — idempotent.
            </p>
            {status?.users_setup ? (
              <div style={{ fontSize: ".78rem", color: C.green, fontWeight: 700, marginBottom: 8 }}>
                ✅ Users ready — Vijay can login at <code style={{ fontSize: ".72rem", background: "rgba(0,0,0,.1)", padding: "1px 4px", borderRadius: 4 }}>vijay.sim.student@example.test</code> / <code style={{ fontSize: ".72rem", background: "rgba(0,0,0,.1)", padding: "1px 4px", borderRadius: 4 }}>test1234</code>
              </div>
            ) : (
              <div style={{ fontSize: ".78rem", color: C.orange, fontWeight: 600, marginBottom: 8 }}>
                ⚠ Users not yet created — click below first
              </div>
            )}
            <button
              data-testid="setup-users-btn"
              onClick={handleSetupUsers}
              disabled={settingUp}
              style={{
                width: "100%", padding: "9px", borderRadius: 9,
                border: `1px solid ${status?.users_setup ? "rgba(34,197,94,.4)" : "transparent"}`,
                background: settingUp ? C.muted : status?.users_setup ? "rgba(34,197,94,.15)" : C.indigo,
                color: status?.users_setup ? C.green : "#fff",
                fontSize: ".82rem", fontWeight: 700,
                cursor: settingUp ? "not-allowed" : "pointer", fontFamily: "inherit",
              }}>
              {settingUp ? "⏳ Creating users…" : status?.users_setup ? "✓ Re-run Setup (safe)" : "⚡ Create Vijay, Manish, Manisha"}
            </button>
          </div>

          {/* Step 2: Run controls */}
          <div style={card()}>
            <h4 style={{ margin: "0 0 14px", fontSize: ".9rem", fontWeight: 800 }}>Step 2: Run Simulation</h4>

            <label style={{ fontSize: ".78rem", fontWeight: 600, display: "block", marginBottom: 4 }}>
              Cycle Days
            </label>
            <div style={{ display: "flex", gap: 6, marginBottom: 12 }}>
              {[1, 7, 14].map(d => (
                <button key={d} onClick={() => setCycleDays(d)} style={{
                  flex: 1, padding: "6px", borderRadius: 8, fontFamily: "inherit",
                  fontSize: ".78rem", fontWeight: 700, cursor: "pointer",
                  border: `1.5px solid ${cycleDays === d ? C.indigo : C.border}`,
                  background: cycleDays === d ? "rgba(99,102,241,.1)" : C.panel,
                  color: cycleDays === d ? C.indigo : C.text,
                }}>{d}d</button>
              ))}
            </div>

            {[
              { key: "dryRun", val: dryRun, set: setDryRun, label: "Dry Run (no data written)" },
              { key: "createBugs", val: createBugs, set: setCreateBugs, label: "Create Product Bugs for Anomalies" },
              { key: "strictVal", val: strictVal, set: setStrictVal, label: "Strict Validation" },
            ].map(({ key, val, set, label }) => (
              <label key={key} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10, cursor: "pointer", fontSize: ".8rem" }}>
                <input type="checkbox" checked={val} onChange={e => set(e.target.checked)} />
                {label}
              </label>
            ))}

            <button
              data-testid="run-simulation-btn"
              onClick={handleRun}
              disabled={running}
              style={{
                width: "100%", padding: "11px", borderRadius: 10, border: "none",
                background: running ? C.muted : C.indigo,
                color: "#fff", fontSize: ".9rem", fontWeight: 700,
                cursor: running ? "not-allowed" : "pointer", fontFamily: "inherit",
              }}>
              {running ? "⏳ Simulating…" : `▶ Run ${cycleDays}-Day Cycle${dryRun ? " (Dry)" : ""}`}
            </button>
          </div>

          {/* Links */}
          <div style={card()}>
            <h4 style={{ margin: "0 0 10px", fontSize: ".85rem", fontWeight: 800 }}>Quick Links</h4>
            {[
              { label: "🎓 Vijay Student Dashboard", href: "/student-dashboard" },
              { label: "👨‍👩‍👦 Manish Parent Dashboard", href: "/parent-dashboard" },
              { label: "🐛 Product Bugs (simulation)", href: "/admin-issues?source=simulation" },
            ].map(({ label, href }) => (
              <a key={href} href={href} target="_blank" rel="noreferrer" style={{
                display: "block", padding: "6px 0", fontSize: ".8rem",
                color: C.indigo, textDecoration: "none",
              }}>{label}</a>
            ))}
          </div>

          {/* Reset */}
          <div style={card({ borderColor: "rgba(239,68,68,.3)" })}>
            <h4 style={{ margin: "0 0 8px", fontSize: ".85rem", fontWeight: 800, color: C.red }}>⚠ Reset Simulation</h4>
            <p style={{ margin: "0 0 10px", fontSize: ".75rem", color: C.muted }}>
              Clears all synthetic simulation data. Preserves user profiles.
            </p>
            {!showReset ? (
              <button onClick={() => setShowReset(true)} data-testid="show-reset-btn" style={{
                width: "100%", padding: "8px", borderRadius: 8, border: `1px solid ${C.red}`,
                background: "transparent", color: C.red, fontSize: ".8rem", fontWeight: 700,
                cursor: "pointer", fontFamily: "inherit",
              }}>Reset Simulation Data</button>
            ) : (
              <div style={{ display: "flex", gap: 8 }}>
                <button onClick={handleReset} disabled={resetting} data-testid="confirm-reset-btn" style={{
                  flex: 1, padding: "8px", borderRadius: 8, border: "none",
                  background: C.red, color: "#fff", fontSize: ".8rem", fontWeight: 700,
                  cursor: resetting ? "not-allowed" : "pointer", fontFamily: "inherit",
                }}>{resetting ? "Resetting…" : "Confirm Reset"}</button>
                <button onClick={() => setShowReset(false)} style={{
                  flex: 1, padding: "8px", borderRadius: 8, border: `1px solid ${C.border}`,
                  background: C.panel, color: C.muted, fontSize: ".8rem", fontWeight: 700,
                  cursor: "pointer", fontFamily: "inherit",
                }}>Cancel</button>
              </div>
            )}
          </div>
        </div>

        {/* ── Right: Results ── */}
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>

          {/* Last run summary */}
          {lastResult && (
            <div style={card()} data-testid="last-run-summary">
              <h4 style={{ margin: "0 0 10px", fontSize: ".9rem", fontWeight: 800 }}>
                Latest Run — Day {lastResult.cycle_start_day}–{lastResult.cycle_end_day}
                {lastResult.dry_run && <span style={{ marginLeft: 8, color: C.orange, fontSize: ".75rem" }}>DRY RUN</span>}
              </h4>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8, fontSize: ".8rem" }}>
                <span style={{ color: C.text }}><b>{lastResult.total_events || 0}</b> events</span>
                <span style={{ color: C.orange }}><b>{lastResult.anomalies?.length || 0}</b> anomalies</span>
                <span style={{ color: C.red }}><b>{lastResult.bugs_created || 0}</b> bugs created</span>
                <span style={{ color: C.green }}><b>{lastResult.total_days || cycleDays}</b> days simulated</span>
              </div>
              {lastResult.days?.slice(0, 7).map(d => (
                <div key={d.day} style={{
                  marginTop: 8, padding: "6px 10px", borderRadius: 8,
                  background: C.surface, fontSize: ".75rem",
                }}>
                  <b>Day {d.day}</b>
                  {d.events?.map((e, i) => (
                    <span key={i} style={{ marginLeft: 8, color: C.muted }}>
                      {e.type === "lesson" ? `📖 ${e.subject}` :
                       e.type === "mock_test" ? `📝 ${e.score}%` :
                       e.type === "practice" ? `✏️ ${e.correct}/${e.attempted}` :
                       e.type === "formula" ? `📐 Formula` :
                       e.type === "exemplar" ? `🔬 Exemplar` :
                       e.type === "doubt" ? `💬 Doubt` : e.type}
                    </span>
                  ))}
                </div>
              ))}
            </div>
          )}

          {/* Run history */}
          <div style={card()}>
            <h4 style={{ margin: "0 0 10px", fontSize: ".9rem", fontWeight: 800 }}>Run History</h4>
            {runs.length === 0 ? (
              <p style={{ color: C.muted, fontSize: ".8rem", margin: 0 }}>No runs yet. Click "Run Simulation" to start.</p>
            ) : runs.map(run => (
              <RunRow key={run.id} run={run} onSelect={handleSelectRun} selected={selectedRun === run.id} />
            ))}
          </div>

          {/* Anomalies */}
          <div style={card()} data-testid="anomaly-table">
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
              <h4 style={{ margin: 0, fontSize: ".9rem", fontWeight: 800 }}>
                Anomalies {selectedRun ? `(${anomalies.length})` : ""}
              </h4>
              {selectedRun && anomalies.length > 0 && (
                <span style={{ fontSize: ".72rem", color: C.muted }}>Click a run to filter</span>
              )}
            </div>
            {!selectedRun && (
              <p style={{ color: C.muted, fontSize: ".8rem", margin: 0 }}>
                Select a run from history to view its anomalies.
              </p>
            )}
            {selectedRun && anomalies.length === 0 && (
              <p style={{ color: C.green, fontSize: ".8rem", margin: 0 }}>✅ No anomalies detected for this run.</p>
            )}
            {anomalies.map(a => (
              <AnomalyRow key={a.id} anomaly={a} onCreateBug={handleCreateBug} />
            ))}
          </div>

        </div>
      </div>
    </div>
  );
}
