import { useEffect, useMemo, useState } from "react";
import {
  Check,
  CreditCard,
  Minus,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

import { getParentChildren } from "../api/parentDashboard";
import {
  getSubscriptionPlan,
  PARENT_PLAN_ORDER,
  SUBSCRIPTION_PLANS,
} from "../config/subscriptionPlans";

function SubscriptionPlansPage({ user }) {
  const [children, setChildren] = useState([]);
  const [selectedChildId, setSelectedChildId] = useState("");
  const [selectedPlanKey, setSelectedPlanKey] = useState("premium");
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadChildren() {
      try {
        const result = await getParentChildren();
        const loadedChildren = result.children || [];

        setChildren(loadedChildren);
        setSelectedChildId(loadedChildren[0]?.id || "");
      } catch (err) {
        console.error(err);
        setError("Unable to load children for subscription plans.");
      } finally {
        setLoading(false);
      }
    }

    if (user?.role === "parent") {
      loadChildren();
    } else {
      setLoading(false);
    }
  }, [user?.role]);

  const selectedChild = useMemo(
    () => children.find((child) => child.id === selectedChildId),
    [children, selectedChildId]
  );

  const activePlan = getSubscriptionPlan(selectedChild?.subscription_plan);
  const selectedPlan = getSubscriptionPlan(selectedPlanKey);
  const isCurrentPlan = activePlan.key === selectedPlan.key;

  function handlePlanClick(planKey) {
    setSelectedPlanKey(planKey);
    setMessage("");
    setError("");
  }

  function handlePaymentClick() {
    if (!selectedChild) {
      setError("Please select a child before choosing a plan.");
      return;
    }

    setMessage(
      `Payment gateway is ready to connect for ${selectedPlan.label}. Admin can activate this plan from Admin Control until payment integration is enabled.`
    );
  }

  if (user?.role !== "parent") {
    return (
      <div className="premium-page subscription-page">
        <section className="premium-section premium-parent-empty">
          <h2>Subscription is available for parent accounts.</h2>
          <p>Login as a parent to view and choose plans.</p>
        </section>
      </div>
    );
  }

  if (loading) {
    return <p>Loading subscription plans...</p>;
  }

  return (
    <div className="premium-page subscription-page">
      <section className="subscription-hero">
        <div>
          <p className="eyebrow">Parent Subscription</p>
          <h2>Choose the right plan for your child</h2>
          <p>
            Compare CBSE access, SOF preparation, AI limits, and parent controls
            before activating a plan.
          </p>
        </div>

        <div className="subscription-current-panel">
          <label>
            Child
            <select
              value={selectedChildId}
              onChange={(e) => setSelectedChildId(e.target.value)}
            >
              {children.length === 0 ? (
                <option value="">No child profiles</option>
              ) : (
                children.map((child) => (
                  <option key={child.id} value={child.id}>
                    {child.username || child.email}
                  </option>
                ))
              )}
            </select>
          </label>

          <div className="subscription-current-plan">
            <span>Current plan</span>
            <strong>{activePlan.label}</strong>
            <small>{selectedChild?.account_status || "active"}</small>
          </div>
        </div>
      </section>

      {message && <div className="info-box">{message}</div>}
      {error && <div className="error-box">{error}</div>}

      <section className="subscription-plan-grid">
        {PARENT_PLAN_ORDER.map((planKey) => {
          const plan = SUBSCRIPTION_PLANS[planKey];
          const isActive = activePlan.key === plan.key;
          const isSelected = selectedPlanKey === plan.key;

          return (
            <article
              key={plan.key}
              className={[
                "subscription-plan-card",
                plan.recommended ? "recommended" : "",
                isSelected ? "selected" : "",
              ]
                .filter(Boolean)
                .join(" ")}
            >
              <div className="subscription-plan-topline">
                <div>
                  <h3>{plan.label}</h3>
                  <p>{plan.audience}</p>
                </div>

                {(plan.badge || isActive) && (
                  <span className={isActive ? "plan-badge active" : "plan-badge"}>
                    {isActive ? "Current" : plan.badge}
                  </span>
                )}
              </div>

              <div className="subscription-price-row">
                <strong>{plan.priceLabel}</strong>
                <span>/ {plan.billingLabel}</span>
              </div>

              <ul className="subscription-feature-list">
                {plan.included.map((feature) => (
                  <li key={feature}>
                    <Check size={18} strokeWidth={2.6} />
                    <span>{feature}</span>
                  </li>
                ))}

                {plan.notIncluded.map((feature) => (
                  <li key={feature} className="muted-feature">
                    <Minus size={18} strokeWidth={2.6} />
                    <span>{feature}</span>
                  </li>
                ))}
              </ul>

              <button
                className={plan.recommended ? "primary-btn" : "secondary-btn"}
                onClick={() => handlePlanClick(plan.key)}
              >
                {isActive ? "Review Current Plan" : `Choose ${plan.shortLabel}`}
              </button>
            </article>
          );
        })}
      </section>

      <section className="subscription-bottom-grid">
        <div className="premium-section subscription-compare">
          <div className="subscription-section-heading">
            <ShieldCheck size={22} strokeWidth={2.4} />
            <h3>Compare plans</h3>
          </div>

          <div className="subscription-table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Feature</th>
                  {PARENT_PLAN_ORDER.map((planKey) => (
                    <th key={planKey}>{SUBSCRIPTION_PLANS[planKey].shortLabel}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {[
                  ["Child profiles", "children"],
                  ["AI lessons and doubts", "aiUsage"],
                  ["CBSE mock tests", "cbse"],
                  ["SOF Science, Maths, English", "sof"],
                  ["RAG-based SOF mock tests", "ragSof"],
                  ["Parent dashboard", "parentDashboard"],
                ].map(([label, key]) => (
                  <tr key={key}>
                    <td>{label}</td>
                    {PARENT_PLAN_ORDER.map((planKey) => (
                      <td key={planKey}>
                        {SUBSCRIPTION_PLANS[planKey].comparison[key]}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <aside className="premium-section subscription-payment-panel">
          <div className="subscription-section-heading">
            <CreditCard size={22} strokeWidth={2.4} />
            <h3>Payment preview</h3>
          </div>

          <div className="subscription-summary-line">
            <span>Selected child</span>
            <strong>{selectedChild?.username || "No child selected"}</strong>
          </div>

          <div className="subscription-summary-line">
            <span>Selected plan</span>
            <strong>{selectedPlan.label}</strong>
          </div>

          <div className="subscription-summary-line">
            <span>Includes</span>
            <strong>
              {selectedPlan.access_sof_science ? "CBSE + SOF + AI" : "CBSE + AI"}
            </strong>
          </div>

          <div className="subscription-summary-line total">
            <span>Total today</span>
            <strong>{selectedPlan.priceLabel}</strong>
          </div>

          <button
            className="primary-btn"
            disabled={isCurrentPlan || !selectedChild}
            onClick={handlePaymentClick}
          >
            <Sparkles size={18} strokeWidth={2.5} />
            {isCurrentPlan ? "Current Plan Selected" : "Proceed to Payment"}
          </button>

          <p className="subscription-payment-note">
            Admin-configured inclusions and limits power this page. Payment
            gateway activation can be connected to this button.
          </p>
        </aside>
      </section>
    </div>
  );
}

export default SubscriptionPlansPage;
