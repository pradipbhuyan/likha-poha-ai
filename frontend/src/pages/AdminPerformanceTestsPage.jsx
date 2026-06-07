import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  Clock,
  Gauge,
  Play,
  RefreshCcw,
  ShieldCheck,
} from "lucide-react";

import {
  getPerformanceRun,
  getPerformanceRuns,
  getPerformanceScenarios,
  startPerformanceRun,
} from "../api/performanceTests";
import "./AdminPerformanceTestsPage.css";


function formatMs(value) {
  /** Render latency values in a compact human-readable format. */
  const numberValue = Number(value || 0);
  if (numberValue >= 1000) return `${(numberValue / 1000).toFixed(1)}s`;
  return `${Math.round(numberValue)}ms`;
}


function formatPercent(value) {
  /** Render rates consistently across summary cards. */
  return `${Number(value || 0).toFixed(2)}%`;
}


function classificationClass(value) {
  /** Map backend classifications into stable CSS class names. */
  return String(value || "queued").toLowerCase();
}


function isActiveRun(run) {
  /** Identify runs that still need polling. */
  return ["queued", "running"].includes(run?.status);
}


function safeSummary(run) {
  /** Normalize optional JSON summary fields from Supabase. */
  return run?.summary && typeof run.summary === "object" ? run.summary : {};
}


function AdminPerformanceTestsPage() {
  /** Admin-only console for backend performance probes and historical trends. */
  const [scenarios, setScenarios] = useState([]);
  const [runs, setRuns] = useState([]);
  const [selectedType, setSelectedType] = useState("browsing_baseline");
  const [concurrency, setConcurrency] = useState(1);
  const [durationSeconds, setDurationSeconds] = useState(30);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const selectedScenario = useMemo(
    () => scenarios.find((scenario) => scenario.key === selectedType),
    [scenarios, selectedType]
  );
  const latestRun = runs[0];
  const latestSummary = safeSummary(latestRun);
  const latestResults = Array.isArray(latestRun?.results) ? latestRun.results : [];

  async function loadAll() {
    /** Load scenario definitions and recent persisted run history together. */
    setLoading(true);
    setError("");
    try {
      const [scenarioResponse, runResponse] = await Promise.all([
        getPerformanceScenarios(),
        getPerformanceRuns(20),
      ]);
      const nextScenarios = scenarioResponse.scenarios || [];
      setScenarios(nextScenarios);
      setRuns(runResponse.runs || []);
      if (nextScenarios.length && !nextScenarios.some((item) => item.key === selectedType)) {
        setSelectedType(nextScenarios[0].key);
      }
    } catch (err) {
      setError(err.message || "Failed to load performance test data.");
    } finally {
      setLoading(false);
    }
  }

  async function refreshLatest() {
    /** Poll the active run without replacing unrelated history rows. */
    if (!latestRun?.id) return;
    try {
      const response = await getPerformanceRun(latestRun.id);
      const updatedRun = response.run;
      setRuns((currentRuns) =>
        currentRuns.map((run) => (run.id === updatedRun.id ? updatedRun : run))
      );
    } catch (err) {
      setError(err.message || "Failed to refresh latest performance run.");
    }
  }

  async function handleStartRun(event) {
    /** Queue a backend-run test after warning about AI quota when needed. */
    event.preventDefault();
    if (!selectedScenario) return;

    if (selectedScenario.uses_ai) {
      const confirmed = window.confirm(
        "This performance test calls AI endpoints and will consume OpenAI quota. Continue?"
      );
      if (!confirmed) return;
    }

    setSaving(true);
    setError("");
    setMessage("");
    try {
      const response = await startPerformanceRun({
        test_type: selectedType,
        concurrency,
        duration_seconds: durationSeconds,
      });
      setRuns((currentRuns) => [response.run, ...currentRuns].slice(0, 20));
      setMessage("Performance test queued. Results will refresh automatically.");
    } catch (err) {
      setError(err.message || "Failed to start performance test.");
    } finally {
      setSaving(false);
    }
  }

  useEffect(() => {
    loadAll();
  }, []);

  useEffect(() => {
    if (!isActiveRun(latestRun)) return undefined;
    const timer = window.setInterval(refreshLatest, 3000);
    return () => window.clearInterval(timer);
  }, [latestRun?.id, latestRun?.status]);

  useEffect(() => {
    if (!selectedScenario) return;
    if (concurrency > selectedScenario.safe_max_concurrency) {
      setConcurrency(selectedScenario.safe_max_concurrency);
    }
  }, [selectedScenario?.key]);

  const recentGood = runs.filter((run) => run.classification === "Good").length;
  const recentRisk = runs.filter((run) =>
    ["Degrading", "Critical"].includes(run.classification)
  ).length;

  return (
    <div className="admin-performance-page">
      {message && <div className="success-banner">{message}</div>}
      {error && <div className="error-banner">{error}</div>}

      <section className="performance-panel performance-hero">
        <div>
          <p className="eyebrow">Admin Performance Lab</p>
          <h2>Controlled Backend Performance Tests</h2>
          <p>
            Run small, repeatable probes using the same scenario definitions as
            the Locust suite. Results are saved for trend review.
          </p>
        </div>

        <div className="performance-badges">
          <span className="performance-badge">
            <ShieldCheck size={16} /> Admin only
          </span>
          <span className="performance-badge">
            <Activity size={16} /> Backend run
          </span>
          <span className="performance-badge">
            <Clock size={16} /> Persisted trends
          </span>
        </div>
      </section>

      <section className="performance-panel">
        <div className="performance-section-header">
          <div>
            <p className="eyebrow">Run Test</p>
            <h3>Scenario Controls</h3>
          </div>
          <button
            type="button"
            className="performance-refresh-button"
            onClick={loadAll}
            disabled={loading}
          >
            <RefreshCcw size={17} />
            Refresh
          </button>
        </div>

        <form className="performance-form" onSubmit={handleStartRun}>
          <div className="performance-form-grid">
            <label className="performance-field">
              <span>Test type</span>
              <select
                value={selectedType}
                onChange={(event) => setSelectedType(event.target.value)}
              >
                {scenarios.map((scenario) => (
                  <option key={scenario.key} value={scenario.key}>
                    {scenario.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="performance-field">
              <span>Concurrency</span>
              <input
                type="number"
                min="1"
                max={selectedScenario?.safe_max_concurrency || 1}
                value={concurrency}
                onChange={(event) => setConcurrency(Number(event.target.value))}
              />
              <small>
                Safe max: {selectedScenario?.safe_max_concurrency || 1}
              </small>
            </label>

            <label className="performance-field">
              <span>Duration</span>
              <input
                type="number"
                min="5"
                max="120"
                value={durationSeconds}
                onChange={(event) => setDurationSeconds(Number(event.target.value))}
              />
              <small>Stored for run context; first version runs bounded probes.</small>
            </label>
          </div>

          {selectedScenario && (
            <div className="performance-scenario-note">
              <Gauge size={18} />
              <span>{selectedScenario.description}</span>
              <strong>Target p95: {formatMs(selectedScenario.target_p95_ms)}</strong>
            </div>
          )}

          {selectedScenario?.uses_ai && (
            <div className="performance-warning">
              <AlertTriangle size={18} />
              AI checks call live lesson, doubt, or mock-test endpoints and consume quota.
            </div>
          )}

          <button
            type="submit"
            className="performance-run-button"
            disabled={saving || loading || !selectedScenario}
          >
            <Play size={18} />
            {saving ? "Starting..." : "Run Performance Test"}
          </button>
        </form>
      </section>

      <section className="performance-summary-grid">
        <article className="performance-card">
          <span>Latest health</span>
          <strong className={`performance-classification ${classificationClass(latestRun?.classification)}`}>
            {latestRun?.classification || "No runs"}
          </strong>
        </article>
        <article className="performance-card">
          <span>Recent runs</span>
          <strong>{runs.length}</strong>
        </article>
        <article className="performance-card">
          <span>Good runs</span>
          <strong>{recentGood}</strong>
        </article>
        <article className="performance-card">
          <span>Degrading / Critical</span>
          <strong>{recentRisk}</strong>
        </article>
      </section>

      <section className="performance-panel">
        <div className="performance-section-header">
          <div>
            <p className="eyebrow">Latest Run</p>
            <h3>{latestSummary.scenario || latestRun?.test_type || "No run yet"}</h3>
          </div>
          {latestRun && (
            <span className={`performance-status ${classificationClass(latestRun.status)}`}>
              {latestRun.status}
            </span>
          )}
        </div>

        {latestRun ? (
          <>
            <div className="performance-metrics-grid">
              <div>
                <span>p50</span>
                <strong>{formatMs(latestSummary.p50_ms)}</strong>
              </div>
              <div>
                <span>p95</span>
                <strong>{formatMs(latestSummary.p95_ms)}</strong>
              </div>
              <div>
                <span>Max</span>
                <strong>{formatMs(latestSummary.max_ms)}</strong>
              </div>
              <div>
                <span>Success</span>
                <strong>{latestSummary.success_count || 0}</strong>
              </div>
              <div>
                <span>Failures</span>
                <strong>{latestSummary.failure_count || 0}</strong>
              </div>
              <div>
                <span>Skipped</span>
                <strong>{latestSummary.skipped_count || 0}</strong>
              </div>
              <div>
                <span>Error rate</span>
                <strong>{formatPercent(latestSummary.error_rate)}</strong>
              </div>
            </div>

            {latestSummary.skipped_count > 0 && (
              <div className="performance-warning">
                <AlertTriangle size={18} />
                {latestSummary.skipped_count} protected probe(s) were skipped because
                no backend performance-test student token is configured.
              </div>
            )}

            {latestRun.error_message && (
              <div className="performance-warning critical">
                <AlertTriangle size={18} />
                {latestRun.error_message}
              </div>
            )}

            <div className="performance-results-table-wrap">
              <table className="performance-results-table">
                <thead>
                  <tr>
                    <th>Request</th>
                    <th>Method</th>
                    <th>Status</th>
                    <th>Time</th>
                    <th>Result</th>
                    <th>Error</th>
                  </tr>
                </thead>
                <tbody>
                  {latestResults.map((result, index) => (
                    <tr key={`${result.name}-${index}`}>
                      <td>{result.name}</td>
                      <td>{result.method}</td>
                      <td>{result.status_code || "-"}</td>
                      <td>{formatMs(result.elapsed_ms)}</td>
                      <td>{result.skipped ? "Skipped" : result.ok ? "Pass" : "Fail"}</td>
                      <td>{result.error || "-"}</td>
                    </tr>
                  ))}
                  {!latestResults.length && (
                    <tr>
                      <td colSpan="6">No detailed timings stored yet.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </>
        ) : (
          <p className="empty-state">No performance runs yet.</p>
        )}
      </section>

      <section className="performance-panel">
        <div className="performance-section-header">
          <div>
            <p className="eyebrow">Trend History</p>
            <h3>Recent Runs</h3>
          </div>
        </div>

        <div className="performance-history-list">
          {runs.map((run) => {
            const summary = safeSummary(run);
            return (
              <div className="performance-history-row" key={run.id}>
                <div>
                  <strong>{summary.scenario || run.test_type}</strong>
                  <span>
                    {run.status} • concurrency {run.concurrency} •{" "}
                    {new Date(run.created_at).toLocaleString()}
                  </span>
                </div>
                <div>
                  <span>p95 {formatMs(summary.p95_ms)}</span>
                  <strong className={`performance-classification ${classificationClass(run.classification)}`}>
                    {run.classification}
                  </strong>
                </div>
              </div>
            );
          })}
          {!runs.length && <p className="empty-state">No trend history yet.</p>}
        </div>
      </section>
    </div>
  );
}

export default AdminPerformanceTestsPage;
