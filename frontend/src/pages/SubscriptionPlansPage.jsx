import { useEffect, useMemo, useState } from "react";
import {
  Check,
  CreditCard,
  Minus,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

import {
  getParentChildren,
  getParentSubscriptionPlans,
} from "../api/parentDashboard";
import {
  createPaymentOrder,
  getPaymentConfig,
  verifyPayment,
} from "../api/payments";
import {
  formatPlanPrice,
  getPlanDisplayPrice,
  getSubscriptionPlan,
  mergeSubscriptionPlans,
  SUBSCRIPTION_PLANS,
} from "../config/subscriptionPlans";

function SubscriptionPlansPage({ user }) {
  const [children, setChildren] = useState([]);
  const [selectedChildId, setSelectedChildId] = useState("");
  const [selectedPlanKey, setSelectedPlanKey] = useState("premium");
  const [plans, setPlans] = useState(SUBSCRIPTION_PLANS);
  const [planOrder, setPlanOrder] = useState(
    Object.values(SUBSCRIPTION_PLANS)
      .filter((plan) => plan.isPublic !== false)
      .sort((a, b) => a.displayOrder - b.displayOrder)
      .map((plan) => plan.key)
  );
  const [paymentConfig, setPaymentConfig] = useState({
    configured: false,
    provider: "razorpay",
  });
  const [paymentProcessing, setPaymentProcessing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadChildren() {
      try {
        const [childrenResult, planResult] = await Promise.all([
          getParentChildren(),
          getParentSubscriptionPlans(),
        ]);
        const paymentResult = await getPaymentConfig().catch((err) => {
          console.warn("Payment config unavailable", err);
          return { configured: false, provider: "razorpay" };
        });
        const loadedChildren = childrenResult.children || [];
        const loadedPlans = mergeSubscriptionPlans(planResult.plans || {});
        const loadedPlanOrder = (planResult.plan_order || []).filter(
          (planKey) => loadedPlans[planKey]?.isPublic !== false
        );

        setPlans(loadedPlans);
        if (loadedPlanOrder.length) {
          setPlanOrder(loadedPlanOrder);
        }
        if (planResult.persisted === false || planResult.load_error) {
          setError(
            "Subscription pricing settings could not load from Supabase, so default prices are shown. Please ask admin to check the subscription_plan_settings table."
          );
        }
        setPaymentConfig(paymentResult);
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

  const activePlan =
    plans[selectedChild?.subscription_plan] ||
    getSubscriptionPlan(selectedChild?.subscription_plan);
  const selectedPlan = plans[selectedPlanKey] || getSubscriptionPlan(selectedPlanKey);
  const isCurrentPlan = activePlan.key === selectedPlan.key;

  function handlePlanClick(planKey) {
    setSelectedPlanKey(planKey);
    setMessage("");
    setError("");
  }

  function loadRazorpayCheckout() {
    return new Promise((resolve, reject) => {
      if (window.Razorpay) {
        resolve(true);
        return;
      }

      const script = document.createElement("script");
      script.src = "https://checkout.razorpay.com/v1/checkout.js";
      script.async = true;
      script.onload = () => resolve(true);
      script.onerror = () => reject(new Error("Unable to load payment checkout."));
      document.body.appendChild(script);
    });
  }

  async function handlePaymentClick() {
    if (!selectedChild) {
      setError("Please select a child before choosing a plan.");
      return;
    }

    if (!paymentConfig.configured) {
      setMessage(
        `Online UPI payment is not enabled yet. Admin can activate ${selectedPlan.label} from Admin Control until Razorpay setup is complete.`
      );
      return;
    }

    setPaymentProcessing(true);
    setMessage("");
    setError("");

    try {
      await loadRazorpayCheckout();

      const orderResult = await createPaymentOrder({
        child_id: selectedChild.id,
        plan_key: selectedPlan.key,
      });

      const checkout = new window.Razorpay({
        key: orderResult.key_id,
        amount: orderResult.order.amount,
        currency: orderResult.order.currency,
        name: "Likha Poha AI",
        description: `${selectedPlan.label} subscription`,
        order_id: orderResult.order.id,
        prefill: {
          email: user?.email || "",
          name: user?.username || "",
        },
        notes: {
          child_id: selectedChild.id,
          plan_key: selectedPlan.key,
        },
        handler: async (response) => {
          try {
            await verifyPayment({
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature,
            });

            setMessage(
              `${selectedPlan.label} payment verified. Subscription access has been updated.`
            );
          } catch (err) {
            console.error(err);
            setError(err.message || "Payment verification failed.");
          } finally {
            setPaymentProcessing(false);
          }
        },
        modal: {
          ondismiss: () => {
            setPaymentProcessing(false);
          },
        },
        method: {
          upi: true,
        },
      });

      checkout.open();
    } catch (err) {
      console.error(err);
      setError(err.message || "Unable to start payment.");
      setPaymentProcessing(false);
    }
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
          <h2>Choose the right plan for your family</h2>
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
        {planOrder.map((planKey) => {
          const plan = plans[planKey];
          const isActive = activePlan.key === plan.key;
          const isSelected = selectedPlanKey === plan.key;
          const displayPrice = getPlanDisplayPrice(plan);
          const hasDiscount = Number(plan.discountPercent || 0) > 0;

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
                <strong>{formatPlanPrice(displayPrice)}</strong>
                <span>/ {plan.billingLabel}</span>
              </div>

              {hasDiscount && (
                <div className="subscription-discount-row">
                  <span>{formatPlanPrice(plan.price)}</span>
                  <strong>
                    {plan.discountLabel ||
                      `${plan.discountPercent}% off active`}
                  </strong>
                </div>
              )}

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
                  {planOrder.map((planKey) => (
                    <th key={planKey}>{plans[planKey].shortLabel}</th>
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
                    {planOrder.map((planKey) => (
                      <td key={planKey}>
                        {plans[planKey].comparison[key]}
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
              {selectedPlan.key === "family_premium"
                ? "2 children + CBSE + SOF + AI"
                : selectedPlan.access_sof_science
                  ? "CBSE + SOF + AI"
                  : "CBSE + AI"}
            </strong>
          </div>

          <div className="subscription-summary-line total">
            <span>Total today</span>
            <strong>{formatPlanPrice(getPlanDisplayPrice(selectedPlan))}</strong>
          </div>

          <button
            className="primary-btn"
            disabled={isCurrentPlan || !selectedChild || paymentProcessing}
            onClick={handlePaymentClick}
          >
            <Sparkles size={18} strokeWidth={2.5} />
            {isCurrentPlan
              ? "Current Plan Selected"
              : paymentProcessing
                ? "Opening Payment..."
                : paymentConfig.configured
                  ? "Pay with UPI"
                  : "Payment Setup Pending"}
          </button>

          <p className="subscription-payment-note">
            {paymentConfig.configured
              ? "UPI checkout opens through Razorpay. Subscription is activated only after payment verification."
              : "Online UPI payment is not enabled yet. Admin can activate plans manually without affecting current access."}
          </p>
        </aside>
      </section>
    </div>
  );
}

export default SubscriptionPlansPage;
