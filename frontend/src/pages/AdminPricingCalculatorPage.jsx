import { useMemo, useState } from "react";

const SUBJECT_USAGE_PRESETS = [
  {
    key: "cbseScience",
    label: "CBSE Science",
    enabled: true,
    requests: 120,
    inputTokens: 1800,
    outputTokens: 1400,
    model: "gpt-4.1-mini",
  },
  {
    key: "cbseMaths",
    label: "CBSE Maths",
    enabled: true,
    requests: 120,
    inputTokens: 1600,
    outputTokens: 1300,
    model: "gpt-4.1-mini",
  },
  {
    key: "cbseEnglish",
    label: "CBSE English",
    enabled: false,
    requests: 60,
    inputTokens: 1400,
    outputTokens: 1200,
    model: "gpt-4.1-mini",
  },
  {
    key: "sofScience",
    label: "SOF Science",
    enabled: false,
    requests: 70,
    inputTokens: 2600,
    outputTokens: 2000,
    model: "gpt-5-mini",
  },
  {
    key: "sofMaths",
    label: "SOF Maths",
    enabled: false,
    requests: 70,
    inputTokens: 2400,
    outputTokens: 1900,
    model: "gpt-5-mini",
  },
  {
    key: "sofEnglish",
    label: "SOF English",
    enabled: false,
    requests: 50,
    inputTokens: 2200,
    outputTokens: 1800,
    model: "gpt-5-mini",
  },
];

const MODEL_COSTS = {
  "gpt-4.1-mini": {
    input: 0.3,
    output: 1.2,
  },
  "gpt-5-mini": {
    input: 0.25,
    output: 2,
  },
  "gpt-5": {
    input: 1.25,
    output: 10,
  },
};

function toNumber(value) {
  /** Convert form values to non-negative numbers for pricing math. */
  return Math.max(0, Number(value) || 0);
}

function formatRupees(value) {
  /** Format INR values for compact admin cost cards. */
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(value || 0);
}

function AdminPricingCalculatorPage() {
  /** Estimate plan economics from token usage and shared monthly platform costs. */
  const [subjectRows, setSubjectRows] = useState(SUBJECT_USAGE_PRESETS);
  const [assumptions, setAssumptions] = useState({
    subscriberCount: 100,
    fxRate: 84,
    platformMonthly: 2500,
    databaseMonthly: 2000,
    domainAnnual: 1200,
    otherMonthly: 1000,
    targetMargin: 35,
    plannedPrice: 299,
  });

  const totals = useMemo(() => {
    /** Calculate per-student monthly cost and margin from current assumptions. */
    const subscriberCount = Math.max(1, toNumber(assumptions.subscriberCount));
    const fxRate = toNumber(assumptions.fxRate);
    const tokenUsd = subjectRows
      .filter((row) => row.enabled)
      .reduce((sum, row) => {
        const modelCost = MODEL_COSTS[row.model] || MODEL_COSTS["gpt-4.1-mini"];
        const inputCost =
          (toNumber(row.requests) * toNumber(row.inputTokens) * modelCost.input) /
          1_000_000;
        const outputCost =
          (toNumber(row.requests) * toNumber(row.outputTokens) * modelCost.output) /
          1_000_000;

        return sum + inputCost + outputCost;
      }, 0);
    const tokenInr = tokenUsd * fxRate;
    const fixedMonthly =
      toNumber(assumptions.platformMonthly) +
      toNumber(assumptions.databaseMonthly) +
      toNumber(assumptions.otherMonthly) +
      toNumber(assumptions.domainAnnual) / 12;
    const fixedPerStudent = fixedMonthly / subscriberCount;
    const totalCost = tokenInr + fixedPerStudent;
    const marginPercent = Math.min(95, toNumber(assumptions.targetMargin));
    const suggestedPrice = totalCost / (1 - marginPercent / 100);
    const plannedPrice = toNumber(assumptions.plannedPrice);
    const plannedMargin = plannedPrice - totalCost;
    const plannedMarginPercent = plannedPrice
      ? (plannedMargin / plannedPrice) * 100
      : 0;

    return {
      tokenInr,
      fixedPerStudent,
      totalCost,
      suggestedPrice,
      plannedMargin,
      plannedMarginPercent,
    };
  }, [assumptions, subjectRows]);

  function updateAssumption(field, value) {
    /** Update one cost assumption used by the pricing calculator. */
    setAssumptions((prev) => ({
      ...prev,
      [field]: value,
    }));
  }

  function updateSubjectRow(key, field, value) {
    /** Update one subject usage row without changing other calculator rows. */
    setSubjectRows((prev) =>
      prev.map((row) =>
        row.key === key
          ? {
              ...row,
              [field]: field === "enabled" ? value : value,
            }
          : row
      )
    );
  }

  return (
    <div className="premium-page admin-pricing-calculator-page">
      <section className="premium-section admin-pricing-hero">
        <div className="premium-header">
          <p className="eyebrow">Pricing Readiness</p>
          <h2>🧮 Pricing Calculator</h2>
          <p>
            Estimate monthly cost per student from enabled subjects, model
            usage, platform costs, database costs, and domain fees.
          </p>
        </div>

        <div className="pricing-result-grid">
          <div className="pricing-result-card">
            <span>Token Cost</span>
            <strong>{formatRupees(totals.tokenInr)}</strong>
            <small>Per student / month</small>
          </div>

          <div className="pricing-result-card">
            <span>Platform Share</span>
            <strong>{formatRupees(totals.fixedPerStudent)}</strong>
            <small>Hosting + DB + domain</small>
          </div>

          <div className="pricing-result-card">
            <span>Total Cost</span>
            <strong>{formatRupees(totals.totalCost)}</strong>
            <small>Break-even floor</small>
          </div>

          <div className="pricing-result-card recommended">
            <span>Suggested Price</span>
            <strong>{formatRupees(totals.suggestedPrice)}</strong>
            <small>{assumptions.targetMargin}% target margin</small>
          </div>
        </div>
      </section>

      <section className="premium-section pricing-calculator-grid">
        <div>
          <div className="premium-header">
            <h3>Cost Assumptions</h3>
            <p>Update these as your vendor invoices and subscriber base change.</p>
          </div>

          <div className="pricing-assumption-grid">
            {[
              ["subscriberCount", "Paid subscribers"],
              ["fxRate", "USD to INR"],
              ["platformMonthly", "Platform / hosting monthly"],
              ["databaseMonthly", "Database monthly"],
              ["domainAnnual", "Domain annual"],
              ["otherMonthly", "Other monthly overhead"],
              ["targetMargin", "Target margin %"],
              ["plannedPrice", "Planned price"],
            ].map(([field, label]) => (
              <label key={field}>
                {label}
                <input
                  type="number"
                  value={assumptions[field]}
                  onChange={(e) => updateAssumption(field, e.target.value)}
                />
              </label>
            ))}
          </div>
        </div>

        <div className="pricing-margin-panel">
          <p className="eyebrow">At Planned Price</p>
          <h3>{formatRupees(assumptions.plannedPrice)}</h3>
          <p>
            Estimated margin is{" "}
            <strong
              className={
                totals.plannedMargin >= 0
                  ? "pricing-positive"
                  : "pricing-negative"
              }
            >
              {formatRupees(totals.plannedMargin)} (
              {totals.plannedMarginPercent.toFixed(1)}%)
            </strong>
            .
          </p>
          <small>
            Model prices are editable defaults. Keep them aligned with your
            actual provider invoice rates before final pricing.
          </small>
        </div>
      </section>

      <section className="premium-section">
        <div className="premium-header">
          <h3>Subject Usage Mix</h3>
          <p>
            Enable the subjects included in a plan and adjust expected monthly
            requests/tokens per student.
          </p>
        </div>

        <div className="pricing-usage-table">
          <div className="pricing-usage-header">
            <span>Include</span>
            <span>Subject</span>
            <span>Requests</span>
            <span>Input tokens</span>
            <span>Output tokens</span>
            <span>Model</span>
          </div>

          {subjectRows.map((row) => (
            <div className="pricing-usage-row" key={row.key}>
              <label className="pricing-checkbox-label">
                <input
                  type="checkbox"
                  checked={row.enabled}
                  onChange={(e) =>
                    updateSubjectRow(row.key, "enabled", e.target.checked)
                  }
                />
              </label>

              <strong>{row.label}</strong>

              <input
                type="number"
                value={row.requests}
                onChange={(e) =>
                  updateSubjectRow(row.key, "requests", e.target.value)
                }
              />

              <input
                type="number"
                value={row.inputTokens}
                onChange={(e) =>
                  updateSubjectRow(row.key, "inputTokens", e.target.value)
                }
              />

              <input
                type="number"
                value={row.outputTokens}
                onChange={(e) =>
                  updateSubjectRow(row.key, "outputTokens", e.target.value)
                }
              />

              <select
                value={row.model}
                onChange={(e) =>
                  updateSubjectRow(row.key, "model", e.target.value)
                }
              >
                {Object.keys(MODEL_COSTS).map((modelName) => (
                  <option key={modelName} value={modelName}>
                    {modelName}
                  </option>
                ))}
              </select>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

export default AdminPricingCalculatorPage;
