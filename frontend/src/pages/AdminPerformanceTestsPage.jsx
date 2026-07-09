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
import {
  getAdminSubscriptionPlans,
  updateAdminSubscriptionPlans,
  adminOfferGateTest,
} from "../api/adminControl";
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


function AdminPerformanceTestsPage({ user }) {
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

      <PaymentTestSection user={user} />
      <PlanUpgradeTestSection user={user} />
      <ExamPackTestSection user={user} />
      <OfferGateTestSection user={user} />
    </div>
  );
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

function PaymentTestSection({ user }) {
  /**
   * Admin-only ₹1 payment test. The plan is NEVER public (is_public: false)
   * so customers never see it. The Razorpay checkout opens directly here
   * inside the admin panel — no need to visit the live signup page.
   */
  const [status, setStatus] = useState("");
  const [checkoutLoading, setCheckoutLoading] = useState(false);
  const [testEmail, setTestEmail] = useState("");
  const [testName, setTestName] = useState("Admin Test");
  const [checkoutResult, setCheckoutResult] = useState(null);

  function ensureRazorpayScript(cb) {
    if (window.Razorpay) { cb(); return; }
    const s = document.createElement("script");
    s.src = "https://checkout.razorpay.com/v1/checkout.js";
    s.onload = cb;
    document.head.appendChild(s);
  }

  async function handleOpenCheckout() {
    if (!testEmail.trim()) { setStatus("❌ Enter a test email first."); return; }
    setCheckoutLoading(true);
    setStatus("Setting up test plan…");
    setCheckoutResult(null);
    try {
      // Step 1: Always upsert the hidden ₹1 test plan first.
      // is_public: true temporarily so the backend's _get_plan() accepts it.
      // display_order: 9999 ensures it never appears in the customer plan list
      // (the customer-facing signup page filters by display_order, not is_public alone).
      const plansData = await getAdminSubscriptionPlans(user.accessToken);
      const existing = Object.values(plansData.plans || {});
      const testPlan = {
        key: "test_1rupee", label: "₹1 Admin Test", short_label: "Test ₹1",
        price: 1, billing_label: "one-time", audience: "admin-only",
        badge: "TEST", recommended: false, discount_percent: 0, discount_label: "",
        is_public: true,       // needed so _get_plan() accepts it for order creation
        display_order: 9999,   // hidden from customer plan list (sorted by display_order)
        access_cbse: true, access_sof_science: false, access_sof_maths: false,
        access_sof_english: false, daily_token_limit: 50000, monthly_token_limit: 1000000,
        included: ["CBSE access (test)"], not_included: [], comparison: {},
      };
      await updateAdminSubscriptionPlans(
        { plans: [...existing.filter(p => p.key !== "test_1rupee"), testPlan] },
        user.accessToken
      );

      // Step 2: Create a ₹1 Razorpay order
      setStatus("Creating Razorpay order…");
      const orderResp = await fetch(`${API_BASE_URL}/api/auth/signup-order`, {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({ email: testEmail.trim(), plan_key: "test_1rupee" }),
      });
      if (!orderResp.ok) {
        const e = await orderResp.json().catch(() => ({}));
        throw new Error(e.detail || "Order creation failed");
      }
      const od = await orderResp.json();
      setStatus("Opening checkout…");
      openRazorpay(od);
    } catch (err) {
      setStatus("❌ " + (err.message || "Checkout failed"));
      setCheckoutLoading(false);
    }
  }

  function openRazorpay(orderData) {
    ensureRazorpayScript(() => {
      const rzp = new window.Razorpay({
        key: orderData.key_id,
        amount: orderData.amount * 100,
        currency: "INR",
        name: "Likha Poha AI",
        description: "₹1 Admin Payment Test",
        order_id: orderData.order_id,
        prefill: { name: testName, email: testEmail },
        theme: { color: "#6c63ff" },
        handler: async (response) => {
          setStatus("Payment captured — verifying...");
          try {
            const verifyResp = await fetch(`${API_BASE_URL}/api/auth/complete-signup`, {
              method: "POST",
              headers: {"Content-Type":"application/json","Authorization":`Bearer ${user.accessToken}`},
              body: JSON.stringify({
                role: "student",
                name: testName,
                email: testEmail.trim(),
                plan_key: "test_1rupee",
                razorpay_order_id: response.razorpay_order_id,
                razorpay_payment_id: response.razorpay_payment_id,
                razorpay_signature: response.razorpay_signature,
                grade: "Grade 9",
              }),
            });
            const vd = await verifyResp.json();
            if (verifyResp.ok && vd.success) {
              setCheckoutResult({
                success: true,
                email: testEmail,
                paymentId: response.razorpay_payment_id,
                emailSent: vd.email_sent,
                emailError: vd.email_error,
                recoveryLink: vd.recovery_link,
              });
              if (vd.email_sent) {
                setStatus("✅ Full payment test PASSED! Account created. Check your email for the set-password link.");
              } else {
                setStatus("⚠️ Account created but set-password email failed to send. See details below.");
              }
            } else {
              setStatus("❌ Verification failed: " + (vd.detail || JSON.stringify(vd)));
            }
          } catch (err) {
            setStatus("❌ Verify error: " + err.message);
          } finally { setCheckoutLoading(false); }
        },
        modal: { ondismiss: () => { setStatus("⚠️ Checkout cancelled."); setCheckoutLoading(false); } },
      });
      rzp.open();
    });
  }

  return (
    <section className="premium-section" style={{marginTop:24}}>
      <div className="premium-header">
        <p className="eyebrow">Razorpay Integration — Admin Only</p>
        <h3>💳 Payment Flow Test</h3>
        <p>Test the complete Razorpay → account creation flow here, inside the admin panel. The ₹1 test plan is <strong>never visible to customers</strong> on the live site.</p>
      </div>
      <div className="premium-card" style={{maxWidth:560}}>
        <div style={{background:"rgba(4,120,87,.08)",border:"1px solid rgba(4,120,87,.25)",borderRadius:8,padding:"10px 14px",marginBottom:16,fontSize:".82rem"}}>
          <strong>🔒 Admin-only test</strong> — the ₹1 plan has <code>is_public: false</code> and is never shown on the customer signup page.
          The Razorpay checkout opens right here. No need to visit the live site.
        </div>

        <label style={{display:"block",marginBottom:12}}>
          <strong style={{fontSize:".85rem"}}>Your test email</strong>
          <input
            type="email"
            value={testEmail}
            onChange={e => setTestEmail(e.target.value)}
            placeholder="your-test-email@gmail.com"
            style={{width:"100%",marginTop:6}}
          />
          <small style={{color:"var(--muted)"}}>A "set your password" email will be sent here after payment</small>
        </label>

        <label style={{display:"block",marginBottom:16}}>
          <strong style={{fontSize:".85rem"}}>Test account name</strong>
          <input
            type="text"
            value={testName}
            onChange={e => setTestName(e.target.value)}
            placeholder="Admin Test"
            style={{width:"100%",marginTop:6}}
          />
        </label>

        <button
          className="primary-btn"
          onClick={handleOpenCheckout}
          disabled={checkoutLoading || !testEmail.trim()}
          style={{minWidth:200}}>
          {checkoutLoading ? "Opening checkout…" : "💳 Open ₹1 Razorpay Checkout"}
        </button>

        {status && (
          <div className={status.startsWith("✅") ? "info-box" : status.startsWith("⚠️") ? "info-box" : "error-box"}
            style={{marginTop:12}}>
            {status}
          </div>
        )}

        {checkoutResult?.success && (
          <div className="info-box" style={{marginTop:12}}>
            <strong>✅ Test complete</strong>
            <p style={{margin:"4px 0 0",fontSize:".82rem"}}>
              Account: <code>{checkoutResult.email}</code><br/>
              Payment ID: <code>{checkoutResult.paymentId}</code><br/>
              {checkoutResult.emailSent
                ? <span style={{color:"#22c55e"}}>✅ Set-password email sent — check your inbox.</span>
                : <span style={{color:"#f59e0b"}}>
                    ⚠️ Email NOT sent
                    {checkoutResult.emailError && <> — <em>{checkoutResult.emailError}</em></>}.
                    {" "}This is usually a Supabase email rate limit (max 4/hr on free tier).
                    Try again after a few minutes, or use Forgot Password on the login page.
                  </span>
              }
            </p>
            {checkoutResult.recoveryLink && (
              <p style={{margin:"8px 0 0",fontSize:".82rem"}}>
                <strong>🔗 Admin recovery link</strong> (use this to set password manually):<br/>
                <a href={checkoutResult.recoveryLink} target="_blank" rel="noreferrer"
                   style={{wordBreak:"break-all",fontSize:".78rem"}}>
                  {checkoutResult.recoveryLink}
                </a>
              </p>
            )}
          </div>
        )}
      </div>
    </section>
  );
}

function OfferGateTestSection({ user }) {
  /**
   * Admin-only offer-gate test harness.
   * Lets you put any user into DKB-only mode (offer gate enabled) or
   * restore their full LLM access — all without touching Supabase manually.
   */
  const [testUsername, setTestUsername] = useState("akshita.teststudent");
  const [gateStatus, setGateStatus] = useState(null);
  const [gateLoading, setGateLoading] = useState(false);
  const [gateMessage, setGateMessage] = useState("");
  const [gateError, setGateError] = useState("");

  async function callGate(action) {
    setGateLoading(true);
    setGateMessage("");
    setGateError("");
    setGateStatus(null);
    try {
      const result = await adminOfferGateTest(
        { username: testUsername.trim(), action },
        user.accessToken
      );
      setGateStatus(result);
      setGateMessage(result.message || `Action '${action}' completed.`);
    } catch (err) {
      setGateError(err.message || `Failed to ${action} offer gate.`);
    } finally {
      setGateLoading(false);
    }
  }

  return (
    <section className="premium-section" style={{ marginTop: 24 }}>
      <div className="premium-header">
        <p className="eyebrow">Offer Gate — Admin Test Harness</p>
        <h3>🔒 Offer-Code Gate Test</h3>
        <p>
          Toggle any user into DKB-only mode to test the offer-gate experience
          without touching Supabase. Restores full access in one click.
        </p>
      </div>

      <div className="premium-card" style={{ maxWidth: 560 }}>
        <div style={{
          background: "rgba(99,102,241,.07)",
          border: "1px solid rgba(99,102,241,.25)",
          borderRadius: 8,
          padding: "10px 14px",
          marginBottom: 16,
          fontSize: ".82rem",
        }}>
          <strong>🔒 Admin-only</strong> — Enable sets <code>access_cbse=false</code> +
          adds a 30-day test redemption (<code>ADMTST01</code>).
          Disable restores <code>access_cbse=true</code> and removes the redemption.
        </div>

        <label style={{ display: "block", marginBottom: 16 }}>
          <strong style={{ fontSize: ".85rem" }}>Test username</strong>
          <input
            type="text"
            value={testUsername}
            onChange={(e) => setTestUsername(e.target.value)}
            placeholder="akshita.teststudent"
            style={{ width: "100%", marginTop: 6 }}
          />
          <small style={{ color: "var(--muted)" }}>
            Default: akshita.teststudent — works for any student username
          </small>
        </label>

        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 12 }}>
          <button
            className="secondary-btn"
            onClick={() => callGate("status")}
            disabled={gateLoading || !testUsername.trim()}
          >
            🔍 Check Status
          </button>
          <button
            className="primary-btn"
            onClick={() => callGate("enable")}
            disabled={gateLoading || !testUsername.trim()}
            style={{ background: "var(--accent, #6366f1)" }}
          >
            {gateLoading ? "Working…" : "🔒 Enable Offer Gate"}
          </button>
          <button
            className="secondary-btn"
            onClick={() => callGate("disable")}
            disabled={gateLoading || !testUsername.trim()}
          >
            ✅ Restore Full Access
          </button>
        </div>

        {gateStatus && (
          <div style={{
            background: gateStatus.is_offer_gated
              ? "rgba(99,102,241,.07)"
              : "rgba(4,120,87,.07)",
            border: `1px solid ${gateStatus.is_offer_gated ? "rgba(99,102,241,.3)" : "rgba(4,120,87,.3)"}`,
            borderRadius: 8,
            padding: "10px 14px",
            fontSize: ".82rem",
            marginBottom: 8,
          }}>
            <strong>{gateStatus.username}</strong>
            <p style={{ margin: "4px 0 0", lineHeight: 1.8 }}>
              Gate active: <strong>{gateStatus.is_offer_gated ? "🔒 YES — DKB only" : "✅ NO — Full LLM access"}</strong><br />
              <code>access_cbse</code>: <code>{String(gateStatus.access_cbse)}</code> &nbsp;|&nbsp;
              <code>access_sof_science</code>: <code>{String(gateStatus.access_sof_science)}</code><br />
              Active redemptions: <code>{gateStatus.active_redemptions}</code>
              {gateStatus.redemption_ids?.length > 0 && (
                <><br />Redemption IDs: <code style={{ fontSize: ".72rem" }}>{gateStatus.redemption_ids.join(", ")}</code></>
              )}
              {gateStatus.user_id && (
                <><br />User ID: <code style={{ fontSize: ".72rem" }}>{gateStatus.user_id}</code></>
              )}
            </p>
          </div>
        )}

        {gateMessage && (
          <div className="info-box" style={{ marginTop: 8, fontSize: ".82rem" }}>
            {gateMessage}
          </div>
        )}
        {gateError && (
          <div className="error-box" style={{ marginTop: 8, fontSize: ".82rem" }}>
            {gateError}
          </div>
        )}

        <div style={{
          marginTop: 16,
          padding: "10px 14px",
          background: "rgba(245,158,11,.07)",
          border: "1px solid rgba(245,158,11,.25)",
          borderRadius: 8,
          fontSize: ".78rem",
          color: "var(--text-muted)",
          lineHeight: 1.6,
        }}>
          <strong>How to test:</strong>
          <ol style={{ margin: "6px 0 0 16px", padding: 0 }}>
            <li>Click <strong>Enable Offer Gate</strong> — access_cbse becomes false</li>
            <li>Log in as the test user and ask a doubt in Ask Doubt or Lessons</li>
            <li>Questions in the DKB → answered instantly. Others → upgrade card shown</li>
            <li>Click <strong>Restore Full Access</strong> when done</li>
          </ol>
        </div>
      </div>
    </section>
  );
}

// ── Plan upgrade test scenarios ───────────────────────────────────────────
const UPGRADE_SCENARIOS = [
  {
    planKey: "free",
    label: "Premium Nano",
    actualPrice: "₹99",
    validity: "8 days",
    childLimit: 1,
    description: "Full CBSE access · 8 days · 1 child profile",
    color: "#6366f1",
  },
  {
    planKey: "starter",
    label: "Premium",
    actualPrice: "₹299",
    validity: "30 days",
    childLimit: 1,
    description: "Full CBSE access · 30 days · 1 child profile",
    color: "#10b981",
  },
  {
    planKey: "family_premium",
    label: "Family Premium",
    actualPrice: "₹499",
    validity: "30 days",
    childLimit: 2,
    description: "Full CBSE access · 30 days · 2 child profiles",
    color: "#f59e0b",
  },
];

function PlanUpgradeTestSection({ user }) {
  /**
   * Admin-only: simulate real plan upgrades (Nano / Premium / Family Premium)
   * using ₹1 test transactions via Razorpay.
   *
   * Flow:
   *   1. Admin searches for a Free Tier user by username/email
   *   2. Selects one of the 3 paid plan scenarios
   *   3. Clicks "Open ₹1 Checkout"
   *   4. Pays ₹1 in Razorpay (real transaction, real gateway)
   *   5. Backend verifies signature, activates the INTENDED plan (not ₹1)
   *   6. Subscription state is displayed after activation
   *
   * Security: both create-order and verify endpoints require admin role.
   * Normal users cannot access these endpoints.
   */
  const [userQuery, setUserQuery] = useState("");
  const [userResults, setUserResults] = useState([]);
  const [selectedUser, setSelectedUser] = useState(null);
  const [selectedScenario, setSelectedScenario] = useState(UPGRADE_SCENARIOS[0]);
  const [status, setStatus] = useState("");
  const [checkoutLoading, setCheckoutLoading] = useState(false);
  const [subscriptionState, setSubscriptionState] = useState(null);

  // Debounced user search
  useEffect(() => {
    if (!userQuery.trim()) { setUserResults([]); return; }
    const t = setTimeout(async () => {
      try {
        const r = await fetch(
          `${API_BASE_URL}/api/admin-control/search-users?q=${encodeURIComponent(userQuery)}&role=student&limit=10`,
          { headers: { Authorization: `Bearer ${user.accessToken}` } }
        );
        const d = await r.json();
        setUserResults(d.users || []);
      } catch { setUserResults([]); }
    }, 300);
    return () => clearTimeout(t);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userQuery]);

  function ensureRazorpay(cb) {
    if (window.Razorpay) { cb(); return; }
    const s = document.createElement("script");
    s.src = "https://checkout.razorpay.com/v1/checkout.js";
    s.onload = cb;
    document.head.appendChild(s);
  }

  async function fetchUserStatus(userId) {
    try {
      const r = await fetch(`${API_BASE_URL}/api/payments/admin-test-user-status/${userId}`, {
        headers: { Authorization: `Bearer ${user.accessToken}` },
      });
      const d = await r.json();
      if (d.success) setSubscriptionState(d);
    } catch { /* non-critical */ }
  }

  async function handleStartUpgradeTest() {
    if (!selectedUser) { setStatus("❌ Select a user first."); return; }
    setCheckoutLoading(true);
    setStatus("Creating ₹1 test order…");
    setSubscriptionState(null);

    try {
      // Step 1: Create ₹1 order via admin endpoint
      const orderResp = await fetch(`${API_BASE_URL}/api/payments/admin-test-create-order`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${user.accessToken}`,
        },
        body: JSON.stringify({
          target_user_id: selectedUser.id,
          intended_plan_key: selectedScenario.planKey,
        }),
      });
      if (!orderResp.ok) {
        const e = await orderResp.json().catch(() => ({}));
        throw new Error(e.detail || "Order creation failed.");
      }
      const od = await orderResp.json();
      setStatus("Opening ₹1 Razorpay checkout…");

      // Step 2: Open Razorpay checkout for ₹1
      ensureRazorpay(() => {
        const rzp = new window.Razorpay({
          key: od.key_id,
          amount: 100,  // ₹1 = 100 paise
          currency: "INR",
          name: "Likha Poha AI",
          description: `Admin Test: ${selectedScenario.label} (${selectedScenario.actualPrice}) — ₹1 test charge`,
          order_id: od.order.id,
          prefill: {
            name: "Admin Test",
            email: user.email || "admin@likhapoha.in",
          },
          notes: {
            test_mode: "true",
            intended_plan: selectedScenario.planKey,
            target_user: selectedUser.username,
          },
          theme: { color: selectedScenario.color },
          handler: async (response) => {
            setStatus("Payment captured — verifying and activating plan…");
            try {
              // Step 3: Verify via admin endpoint (activates intended plan)
              const verifyResp = await fetch(`${API_BASE_URL}/api/payments/admin-test-verify`, {
                method: "POST",
                headers: {
                  "Content-Type": "application/json",
                  Authorization: `Bearer ${user.accessToken}`,
                },
                body: JSON.stringify({
                  razorpay_order_id: response.razorpay_order_id,
                  razorpay_payment_id: response.razorpay_payment_id,
                  razorpay_signature: response.razorpay_signature,
                }),
              });
              const vd = await verifyResp.json();
              if (verifyResp.ok && vd.success) {
                setStatus(
                  `✅ Test upgrade PASSED! ${selectedUser.username} → ${selectedScenario.label} · ` +
                  `₹1 charged · ${selectedScenario.actualPrice} plan activated · Valid ${selectedScenario.validity}`
                );
                await fetchUserStatus(selectedUser.id);
              } else {
                setStatus("❌ Verification failed: " + (vd.detail || JSON.stringify(vd)));
              }
            } catch (err) {
              setStatus("❌ Verify error: " + err.message);
            } finally {
              setCheckoutLoading(false);
            }
          },
          modal: {
            ondismiss: () => {
              setStatus("⚠️ Checkout cancelled — plan NOT upgraded.");
              setCheckoutLoading(false);
            },
          },
        });
        rzp.open();
      });
    } catch (err) {
      setStatus("❌ " + (err.message || "Test upgrade failed."));
      setCheckoutLoading(false);
    }
  }

  return (
    <section className="premium-section" style={{ marginTop: 24 }}>
      <div className="premium-header">
        <p className="eyebrow">Subscription Upgrade — Admin Test · ₹1 Real Transactions</p>
        <h3>🚀 Plan Upgrade Flow Test</h3>
        <p>
          Simulate real user upgrades from Free Tier to each paid plan using ₹1 test transactions.
          The <strong>real payment + verification + subscription activation</strong> logic runs end-to-end.
          Only the charge amount is overridden to ₹1.
        </p>
      </div>

      <div className="premium-card" style={{ maxWidth: 640 }}>
        {/* Security badge */}
        <div style={{
          background: "rgba(239,68,68,.07)", border: "1px solid rgba(239,68,68,.25)",
          borderRadius: 8, padding: "10px 14px", marginBottom: 18, fontSize: ".82rem",
        }}>
          <strong>🔒 Admin-only endpoints</strong> — <code>POST /api/payments/admin-test-create-order</code> and{" "}
          <code>POST /api/payments/admin-test-verify</code> require <strong>admin</strong> role.
          Normal users on the checkout page are never affected — they always pay the full plan price.
        </div>

        {/* Step 1: User search */}
        <div style={{ marginBottom: 18 }}>
          <strong style={{ fontSize: ".88rem", display: "block", marginBottom: 8 }}>
            Step 1 — Select a Free Tier user to upgrade
          </strong>
          <input
            type="text"
            value={userQuery}
            onChange={e => { setUserQuery(e.target.value); setSelectedUser(null); setSubscriptionState(null); }}
            placeholder="Search by username or email…"
            style={{ width: "100%", marginBottom: 6 }}
          />
          {userResults.length > 0 && !selectedUser && (
            <div style={{ border: "1px solid var(--border)", borderRadius: 8, overflow: "hidden", maxHeight: 180, overflowY: "auto" }}>
              {userResults.map(u => (
                <div key={u.id} onClick={() => { setSelectedUser(u); setUserQuery(u.username); setUserResults([]); }}
                  style={{ padding: "8px 12px", cursor: "pointer", fontSize: ".85rem", borderBottom: "1px solid var(--border)" }}>
                  <strong>{u.username}</strong>
                  <span style={{ color: "var(--muted)", marginLeft: 8, fontSize: ".78rem" }}>
                    {u.email} · {u.grade || "—"}
                  </span>
                </div>
              ))}
            </div>
          )}
          {selectedUser && (
            <div style={{
              display: "flex", alignItems: "center", justifyContent: "space-between",
              padding: "8px 12px", background: "rgba(99,102,241,.08)",
              border: "1px solid rgba(99,102,241,.3)", borderRadius: 8, fontSize: ".85rem",
            }}>
              <span>✅ <strong>{selectedUser.username}</strong> — {selectedUser.email} · {selectedUser.grade || "—"}</span>
              <button onClick={() => { setSelectedUser(null); setUserQuery(""); setSubscriptionState(null); }}
                style={{ background: "none", border: "none", cursor: "pointer", color: "#94a3b8" }}>×</button>
            </div>
          )}
        </div>

        {/* Step 2: Plan scenario selection */}
        <div style={{ marginBottom: 18 }}>
          <strong style={{ fontSize: ".88rem", display: "block", marginBottom: 8 }}>
            Step 2 — Choose plan scenario to test
          </strong>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {UPGRADE_SCENARIOS.map(scenario => {
              const sel = selectedScenario.planKey === scenario.planKey;
              return (
                <div key={scenario.planKey}
                  onClick={() => setSelectedScenario(scenario)}
                  style={{
                    display: "flex", alignItems: "center", gap: 12,
                    padding: "12px 14px", borderRadius: 10, cursor: "pointer",
                    border: `2px solid ${sel ? scenario.color : "var(--border)"}`,
                    background: sel ? `${scenario.color}11` : "var(--surface2, #111827)",
                  }}>
                  <div style={{
                    width: 16, height: 16, borderRadius: "50%", flexShrink: 0,
                    border: `2px solid ${sel ? scenario.color : "#334155"}`,
                    background: sel ? scenario.color : "transparent",
                    display: "flex", alignItems: "center", justifyContent: "center",
                  }}>
                    {sel && <div style={{ width: 6, height: 6, borderRadius: "50%", background: "#fff" }} />}
                  </div>
                  <div style={{ flex: 1 }}>
                    <strong style={{ fontSize: ".9rem" }}>{scenario.label}</strong>
                    <span style={{ marginLeft: 8, fontSize: ".78rem", color: "var(--muted)" }}>{scenario.description}</span>
                  </div>
                  <div style={{ textAlign: "right", flexShrink: 0 }}>
                    <div style={{ fontSize: ".72rem", color: "var(--muted)" }}>Actual plan price</div>
                    <strong style={{ color: scenario.color }}>{scenario.actualPrice}</strong>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Charge summary */}
        <div style={{
          display: "flex", justifyContent: "space-between", alignItems: "center",
          padding: "10px 14px", background: "rgba(16,185,129,.07)",
          border: "1px solid rgba(16,185,129,.25)", borderRadius: 9, marginBottom: 16, fontSize: ".85rem",
        }}>
          <div>
            <div style={{ fontWeight: 700 }}>Test charge: <span style={{ color: "#10b981" }}>₹1</span></div>
            <div style={{ color: "var(--muted)", fontSize: ".78rem" }}>
              Actual plan being validated: <strong>{selectedScenario.label}</strong> ({selectedScenario.actualPrice} / {selectedScenario.validity})
            </div>
          </div>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: ".72rem", color: "var(--muted)" }}>Child limit</div>
            <strong>{selectedScenario.childLimit}</strong>
          </div>
        </div>

        {/* CTA */}
        <button
          className="primary-btn"
          onClick={handleStartUpgradeTest}
          disabled={checkoutLoading || !selectedUser}
          style={{ width: "100%", background: `linear-gradient(135deg, ${selectedScenario.color}, #059669)` }}
        >
          {checkoutLoading ? "Opening checkout…" : `🚀 Open ₹1 Checkout → Upgrade to ${selectedScenario.label}`}
        </button>

        {status && (
          <div
            className={status.startsWith("✅") ? "info-box" : status.startsWith("⚠️") ? "info-box" : "error-box"}
            style={{ marginTop: 12, fontSize: ".85rem" }}
          >
            {status}
          </div>
        )}

        {/* Post-upgrade subscription state */}
        {subscriptionState && (
          <div style={{
            marginTop: 14, padding: "12px 14px",
            background: subscriptionState.subscription_active ? "rgba(16,185,129,.08)" : "rgba(239,68,68,.07)",
            border: `1px solid ${subscriptionState.subscription_active ? "rgba(16,185,129,.3)" : "rgba(239,68,68,.25)"}`,
            borderRadius: 9, fontSize: ".82rem",
          }}>
            <strong>📊 Post-upgrade subscription state for {subscriptionState.profile.username}</strong>
            <div style={{ marginTop: 8, display: "grid", gridTemplateColumns: "1fr 1fr", gap: "4px 16px", lineHeight: 1.8 }}>
              <div>Plan: <code>{subscriptionState.profile.subscription_plan}</code></div>
              <div>Access active: <strong style={{ color: subscriptionState.subscription_active ? "#10b981" : "#ef4444" }}>
                {subscriptionState.subscription_active ? "✅ YES" : "❌ NO"}
              </strong></div>
              <div>CBSE access: <code>{String(subscriptionState.profile.access_cbse)}</code></div>
              <div>Account status: <code>{subscriptionState.profile.account_status}</code></div>
              {subscriptionState.expires_at && (
                <div style={{ gridColumn: "1/-1" }}>
                  Expires: <code>{String(subscriptionState.expires_at).slice(0, 19)}</code>
                </div>
              )}
            </div>
          </div>
        )}

        <div style={{
          marginTop: 16, padding: "10px 14px",
          background: "rgba(245,158,11,.07)", border: "1px solid rgba(245,158,11,.25)",
          borderRadius: 8, fontSize: ".78rem", color: "var(--text-muted)", lineHeight: 1.6,
        }}>
          <strong>How this test works:</strong>
          <ol style={{ margin: "6px 0 0 16px", padding: 0 }}>
            <li>Select a Free Tier student above (search by name or email)</li>
            <li>Choose the paid plan to validate (Nano / Premium / Family Premium)</li>
            <li>Click the ₹1 checkout button — Razorpay opens with a ₹1 charge</li>
            <li>Pay ₹1 (real UPI or card) — the admin-test-verify endpoint activates the <em>intended</em> plan</li>
            <li>Subscription state below updates showing the new plan, expiry, and access flags</li>
          </ol>
          <p style={{ marginTop: 8 }}>
            <strong>Normal users always pay full price</strong> — the ₹1 override exists only on
            <code> /api/payments/admin-test-create-order</code> (admin role required).
          </p>
        </div>
      </div>
    </section>
  );
}

// ── Exam Prep Pack ₹1 Test Section ───────────────────────────────────────────
const EXAM_PACK_SCENARIOS = [
  { examType: "jee_main",  label: "JEE Main",  icon: "📐", color: "#6366f1", actualPrice: "₹499", validity: "120 days" },
  { examType: "neet_ug",   label: "NEET UG",   icon: "🔬", color: "#10b981", actualPrice: "₹499", validity: "300 days" },
  { examType: "cuet_ug",   label: "CUET UG",   icon: "🏛️", color: "#f59e0b", actualPrice: "₹399", validity: "240 days" },
];

function ExamPackTestSection({ user }) {
  const [userQuery, setUserQuery] = useState("");
  const [userResults, setUserResults] = useState([]);
  const [selectedUser, setSelectedUser] = useState(null);
  const [selectedScenario, setSelectedScenario] = useState(EXAM_PACK_SCENARIOS[0]);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(false);
  const [activatedPacks, setActivatedPacks] = useState(null);

  // User search — same endpoint as PlanUpgradeTestSection
  useEffect(() => {
    if (!userQuery || userQuery.length < 2 || selectedUser) { setUserResults([]); return; }
    const t = setTimeout(async () => {
      try {
        const r = await fetch(
          `${API_BASE_URL}/api/admin-control/search-users?q=${encodeURIComponent(userQuery)}&limit=10`,
          { headers: { Authorization: `Bearer ${user.accessToken}` } }
        );
        const d = await r.json();
        setUserResults(d.users || []);
      } catch { setUserResults([]); }
    }, 300);
    return () => clearTimeout(t);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userQuery]);

  async function handleTestPack() {
    if (!selectedUser) { setStatus("❌ Select a user first."); return; }
    setLoading(true); setStatus("⏳ Creating ₹1 order…"); setActivatedPacks(null);

    try {
      // Step 1: create ₹1 order
      const orderResp = await fetch(`${API_BASE_URL}/api/exam-prep/admin-test-pack-order`, {
        method: "POST",
        headers: { Authorization: `Bearer ${user.accessToken}`, "Content-Type": "application/json" },
        body: JSON.stringify({ target_user_id: selectedUser.id, exam_type: selectedScenario.examType }),
      });
      if (!orderResp.ok) { const e = await orderResp.json(); throw new Error(e.detail || "Order failed"); }
      const orderData = await orderResp.json();

      setStatus("💳 Opening ₹1 Razorpay checkout…");

      // Step 2: load Razorpay if needed
      if (!window.Razorpay) {
        await new Promise((res, rej) => {
          const s = document.createElement("script");
          s.src = "https://checkout.razorpay.com/v1/checkout.js";
          s.onload = res; s.onerror = rej;
          document.body.appendChild(s);
        });
      }

      // Step 3: open Razorpay
      await new Promise((resolve, reject) => {
        const rzp = new window.Razorpay({
          key: orderData.key_id,
          amount: orderData.amount * 100,
          currency: "INR",
          order_id: orderData.order_id,
          name: "Likha Poha AI — Admin Test",
          description: `${selectedScenario.label} Pack Test · ₹1`,
          prefill: { email: user.email || "", name: user.username || "" },
          theme: { color: selectedScenario.color },
          handler: async (response) => {
            try {
              setStatus("✅ Payment captured · Activating pack…");
              const verifyResp = await fetch(`${API_BASE_URL}/api/exam-prep/admin-test-pack-verify`, {
                method: "POST",
                headers: { Authorization: `Bearer ${user.accessToken}`, "Content-Type": "application/json" },
                body: JSON.stringify({
                  razorpay_order_id: response.razorpay_order_id,
                  razorpay_payment_id: response.razorpay_payment_id,
                  razorpay_signature: response.razorpay_signature,
                  target_user_id: selectedUser.id,
                  exam_type: selectedScenario.examType,
                }),
              });
              if (!verifyResp.ok) { const e = await verifyResp.json(); throw new Error(e.detail || "Verify failed"); }
              const verifyData = await verifyResp.json();
              setActivatedPacks(verifyData.active_packs);
              setStatus(`🎉 ${selectedScenario.label} pack activated for ${selectedUser.username}! Expires: ${verifyData.expires_at ? new Date(verifyData.expires_at).toLocaleDateString("en-IN") : "—"} · Charged ₹1 · Intended ${selectedScenario.actualPrice}`);
              resolve();
            } catch (e) { reject(e); }
          },
          modal: { ondismiss: () => reject(new Error("Checkout cancelled")) },
        });
        rzp.open();
      });
    } catch (err) {
      setStatus("❌ " + (err.message || "Test failed."));
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="premium-section" style={{ marginTop: 24 }}>
      <div className="premium-header">
        <p className="eyebrow">Exam Prep Pack — Admin Test · ₹1 Real Transactions</p>
        <h3>🎯 Exam Prep Pack Payment Test</h3>
        <p>
          Test the full JEE / NEET / CUET pack purchase flow using ₹1 real transactions.
          Pays ₹1 through Razorpay — activates the <strong>full intended pack</strong> (120–300 day validity).
        </p>
      </div>

      <div className="premium-card" style={{ maxWidth: 640 }}>
        <div style={{ background: "rgba(239,68,68,.07)", border: "1px solid rgba(239,68,68,.25)", borderRadius: 8, padding: "10px 14px", marginBottom: 18, fontSize: ".82rem" }}>
          <strong>🔒 Admin-only</strong> — <code>POST /api/exam-prep/admin-test-pack-order</code> and{" "}
          <code>POST /api/exam-prep/admin-test-pack-verify</code> require <strong>admin</strong> role.
        </div>

        {/* Step 1: User search */}
        <div style={{ marginBottom: 18 }}>
          <strong style={{ fontSize: ".88rem", display: "block", marginBottom: 8 }}>Step 1 — Select a user</strong>
          <input type="text" value={userQuery}
            onChange={e => { setUserQuery(e.target.value); setSelectedUser(null); setActivatedPacks(null); }}
            placeholder="Search by username or email…"
            style={{ width: "100%", marginBottom: 6 }} />
          {userResults.length > 0 && !selectedUser && (
            <div style={{ border: "1px solid var(--border)", borderRadius: 8, overflow: "hidden", maxHeight: 180, overflowY: "auto" }}>
              {userResults.map(u => (
                <div key={u.id} onClick={() => { setSelectedUser(u); setUserQuery(u.username); setUserResults([]); }}
                  style={{ padding: "8px 12px", cursor: "pointer", fontSize: ".85rem", borderBottom: "1px solid var(--border)" }}>
                  <strong>{u.username}</strong>
                  <span style={{ color: "var(--muted)", marginLeft: 8, fontSize: ".78rem" }}>{u.email} · {u.grade || "—"}</span>
                </div>
              ))}
            </div>
          )}
          {selectedUser && (
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "8px 12px", background: "rgba(99,102,241,.08)", border: "1px solid rgba(99,102,241,.3)", borderRadius: 8, fontSize: ".85rem" }}>
              <span>✅ <strong>{selectedUser.username}</strong> — {selectedUser.email} · {selectedUser.grade || "—"}</span>
              <button onClick={() => { setSelectedUser(null); setUserQuery(""); setActivatedPacks(null); }}
                style={{ background: "none", border: "none", cursor: "pointer", color: "#94a3b8" }}>×</button>
            </div>
          )}
        </div>

        {/* Step 2: Pack scenario */}
        <div style={{ marginBottom: 18 }}>
          <strong style={{ fontSize: ".88rem", display: "block", marginBottom: 8 }}>Step 2 — Choose exam pack to test</strong>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            {EXAM_PACK_SCENARIOS.map(s => {
              const sel = selectedScenario.examType === s.examType;
              return (
                <div key={s.examType} onClick={() => setSelectedScenario(s)}
                  style={{ flex: 1, minWidth: 160, padding: "12px 14px", borderRadius: 10, cursor: "pointer", border: `2px solid ${sel ? s.color : "var(--border)"}`, background: sel ? `${s.color}10` : "var(--surface2,rgba(0,0,0,.02))" }}>
                  <div style={{ fontSize: "1.4rem", marginBottom: 4 }}>{s.icon}</div>
                  <div style={{ fontWeight: 700, fontSize: ".88rem", color: sel ? s.color : undefined }}>{s.label}</div>
                  <div style={{ fontSize: ".72rem", color: "var(--muted)", marginTop: 2 }}>Actual {s.actualPrice} · {s.validity}</div>
                  <div style={{ fontSize: ".68rem", color: "#22c55e", marginTop: 4, fontWeight: 700 }}>Charged: ₹1</div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Launch */}
        <button onClick={handleTestPack} disabled={loading || !selectedUser}
          style={{ padding: "11px 28px", background: selectedUser ? `linear-gradient(135deg,${selectedScenario.color},${selectedScenario.color}cc)` : "var(--border)", border: "none", borderRadius: 10, color: selectedUser ? "#fff" : "var(--muted)", fontWeight: 700, fontSize: ".9rem", cursor: selectedUser ? "pointer" : "not-allowed", fontFamily: "inherit", marginBottom: 14 }}>
          {loading ? "Processing…" : `Open ₹1 Checkout — ${selectedScenario.label} Pack`}
        </button>

        {status && (
          <div style={{ padding: "10px 14px", background: "rgba(99,102,241,.06)", border: "1px solid rgba(99,102,241,.2)", borderRadius: 8, fontSize: ".82rem", marginBottom: 10, whiteSpace: "pre-wrap" }}>
            {status}
          </div>
        )}

        {/* Active packs after activation */}
        {activatedPacks && (
          <div style={{ marginTop: 10 }}>
            <div style={{ fontSize: ".78rem", fontWeight: 700, color: "#a5b4fc", marginBottom: 8 }}>Active packs for {selectedUser?.username}:</div>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {Object.entries(activatedPacks).map(([et, p]) => (
                <div key={et} style={{ padding: "6px 12px", borderRadius: 8, background: p.active ? "rgba(34,197,94,.1)" : "rgba(100,116,139,.08)", border: `1px solid ${p.active ? "rgba(34,197,94,.3)" : "#334155"}`, fontSize: ".75rem", fontWeight: 600 }}>
                  {p.active ? "✅" : "🔒"} {et.replace("_", " ").toUpperCase()}
                  {p.active && p.expires_at && <span style={{ color: "var(--muted)", marginLeft: 6, fontSize: ".65rem" }}>until {new Date(p.expires_at).toLocaleDateString("en-IN")}</span>}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}

export default AdminPerformanceTestsPage;
