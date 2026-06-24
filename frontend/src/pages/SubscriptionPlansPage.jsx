import { useEffect, useMemo, useState } from "react";
import { supabase } from "../api/supabaseClient";
import { redeemOfferCode } from "../api/adminControl";
import {
  Check,
  CreditCard,
  Mail,
  MessageCircle,
  Minus,
  Phone,
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
  getStudentPaymentConfig,
  createStudentPaymentOrder,
  verifyStudentPayment,
} from "../api/payments";
import {
  formatPlanPrice,
  getPlanDisplayPrice,
  getSubscriptionPlan,
  mergeSubscriptionPlans,
  SUBSCRIPTION_PLANS,
} from "../config/subscriptionPlans";

const DEFAULT_SUBSCRIPTION_CONTACT = {
  email: "lilhapohaai@gmail.com",
  phone: "",
  whatsapp: "",
  availability: "We usually respond within one business day.",
  message:
    "Need help choosing a plan or activating access? Contact us and we will guide you.",
};

function cleanContactNumber(value = "") {
  /** Strip spaces/symbols for tel and WhatsApp links while preserving leading +. */
  const trimmed = String(value || "").trim();
  const prefix = trimmed.startsWith("+") ? "+" : "";
  return `${prefix}${trimmed.replace(/[^\d]/g, "")}`;
}

function StudentSubscriptionView({ user, plans, planOrder, contact, loading }) {
  /**
   * Student subscription page — branches on whether the student has a parent.
   *
   * Standalone students (parentId === null, self-registered):
   *   Full self-service plan selection + Razorpay payment.
   *
   * Parent-linked students (parentId !== null, added by parent):
   *   Read-only view with "Talk to your parent to upgrade" message.
   */
  const isStandaloneStudent = !user?.parentId;
  const supportEmail = contact.email || DEFAULT_SUBSCRIPTION_CONTACT.email;
  const supportPhone = cleanContactNumber(contact.phone);
  const supportWhatsapp = cleanContactNumber(contact.whatsapp);

  // Access level display
  const hasCbse = user?.accessCbse;
  const hasSof = user?.accessSofScience || user?.accessSofMaths || user?.accessSofEnglish;
  const currentPlanLabel = hasCbse
    ? hasSof ? "CBSE + SOF Plan" : "CBSE Plan"
    : "Offer / Free Access";

  // Offer validity state
  // Primary: read from user object (stored at login time in buildLoginUser — no fetch needed)
  // Fallback: fetch fresh from API (handles sessions cached before offerValidUntil was added)
  const [offerAccess, setOfferAccess] = useState(
    user?.offerAccess && user?.offerValidUntil
      ? {
          has_offer_access: user.offerAccess,
          valid_until: user.offerValidUntil,
          days_remaining: user.offerDaysRemaining ?? null,
          expiring_soon: !!user.offerExpiringSoon,
          expired_on: user.offerExpiredOn || null,
        }
      : user?.offerExpiredOn
        ? { has_offer_access: false, valid_until: null, days_remaining: 0, expiring_soon: false, expired_on: user.offerExpiredOn }
        : null
  );

  useEffect(() => {
    // If full offer data already present from login, no fetch needed
    if (user?.offerAccess && user?.offerValidUntil) return;
    // Fallback: fetch with a fresh Supabase session token (avoids stale JWT issue)
    async function fetchOfferAccess() {
      try {
        const { data: { session } } = await supabase.auth.getSession();
        const token = session?.access_token || user?.accessToken;
        if (!token) return;
        const r = await fetch(`${import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"}/api/offer/my-access`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (r.ok) {
          const data = await r.json();
          if (data) setOfferAccess(data);
        }
      } catch {
        // Offer validity is a display feature — never block the page
      }
    }
    fetchOfferAccess();
  }, [user?.offerValidUntil]);

  // Offer code redeem state (students only)
  const [offerCodeInput, setOfferCodeInput] = useState("");
  const [offerCodeMsg, setOfferCodeMsg] = useState("");
  const [offerCodeErr, setOfferCodeErr] = useState("");
  const [offerCodeLoading, setOfferCodeLoading] = useState(false);

  async function handleRedeemOfferCode() {
    if (offerCodeInput.length !== 8) return;
    setOfferCodeLoading(true);
    setOfferCodeMsg("");
    setOfferCodeErr("");
    try {
      const res = await redeemOfferCode(offerCodeInput, user.accessToken);
      setOfferCodeMsg(res.message || "✅ Offer code applied! Your access has been activated.");
      setOfferCodeInput("");
      // Refresh offer access display
      const { data: { session } } = await supabase.auth.getSession();
      const token = session?.access_token || user?.accessToken;
      if (token) {
        const r = await fetch(`${import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"}/api/offer/my-access`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (r.ok) { const d = await r.json(); if (d) setOfferAccess(d); }
      }
    } catch (err) {
      setOfferCodeErr(err.message || "Invalid or expired offer code.");
    } finally {
      setOfferCodeLoading(false);
    }
  }

  // Self-service payment state (standalone students only)
  const [selectedPlanKey, setSelectedPlanKey] = useState(planOrder[0] || "premium");
  const [paymentConfig, setPaymentConfig] = useState({ configured: false });
  const [paymentProcessing, setPaymentProcessing] = useState(false);
  const [paymentMessage, setPaymentMessage] = useState("");
  const [paymentError, setPaymentError] = useState("");

  useEffect(() => {
    if (!isStandaloneStudent) return;
    getStudentPaymentConfig()
      .then(setPaymentConfig)
      .catch(() => setPaymentConfig({ configured: false }));
  }, [isStandaloneStudent]);

  function loadRazorpayScript() {
    return new Promise((resolve, reject) => {
      if (window.Razorpay) { resolve(true); return; }
      const s = document.createElement("script");
      s.src = "https://checkout.razorpay.com/v1/checkout.js";
      s.async = true;
      s.onload = () => resolve(true);
      s.onerror = () => reject(new Error("Unable to load payment checkout."));
      document.body.appendChild(s);
    });
  }

  async function handleStudentPayment() {
    const plan = plans[selectedPlanKey];
    if (!plan) return;

    if (!paymentConfig.configured) {
      setPaymentMessage(
        `Online UPI payment is not enabled yet. Contact us to activate ${plan.label}.`
      );
      return;
    }

    setPaymentProcessing(true);
    setPaymentMessage("");
    setPaymentError("");

    try {
      await loadRazorpayScript();
      const orderResult = await createStudentPaymentOrder({ plan_key: plan.key });

      const checkout = new window.Razorpay({
        key: orderResult.key_id,
        amount: orderResult.order.amount,
        currency: orderResult.order.currency,
        name: "Likha Poha AI",
        description: `${plan.label} subscription`,
        order_id: orderResult.order.id,
        prefill: { email: user?.email || "", name: user?.username || "" },
        handler: async (response) => {
          try {
            await verifyStudentPayment({
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature,
            });
            setPaymentMessage(
              `✅ ${plan.label} activated! Refresh the page to see your updated access.`
            );
          } catch (err) {
            setPaymentError(err.message || "Payment verification failed.");
          } finally {
            setPaymentProcessing(false);
          }
        },
        modal: { ondismiss: () => setPaymentProcessing(false) },
        method: { upi: true },
      });
      checkout.open();
    } catch (err) {
      setPaymentError(err.message || "Unable to start payment.");
      setPaymentProcessing(false);
    }
  }

  if (loading) return <p>Loading subscription plans...</p>;

  return (
    <div className="premium-page subscription-page">
      {/* Hero */}
      <section className="subscription-hero">
        <div>
          <p className="eyebrow">
            {isStandaloneStudent ? "Your Subscription" : "Upgrade Your Learning"}
          </p>
          <h2>
            {isStandaloneStudent
              ? "Choose the right plan for you"
              : "Unlock full AI tutoring for every subject"}
          </h2>
          <p>
            {isStandaloneStudent
              ? "Compare plans and pay directly with UPI. Your access is activated instantly after payment."
              : "See what each plan includes. Ask your parent to subscribe to unlock everything."}
          </p>
        </div>
        <div className="subscription-current-panel">
          <div className="subscription-current-plan">
            <span>Your current access</span>
            <strong>{currentPlanLabel}</strong>
            <small>
              {hasCbse
                ? "✅ CBSE access active"
                : offerAccess?.has_offer_access && offerAccess?.valid_until
                  ? offerAccess.expiring_soon
                    ? `⚠️ Expires in ${offerAccess.days_remaining} day${offerAccess.days_remaining !== 1 ? "s" : ""} — ${new Date(offerAccess.valid_until).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })}`
                    : `🟢 Valid until ${new Date(offerAccess.valid_until).toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" })} · ${offerAccess.days_remaining} days remaining`
                  : offerAccess?.expired_on
                    ? `🔴 Expired on ${new Date(offerAccess.expired_on).toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" })}`
                    : "🔒 Limited — upgrade to unlock all features"}
            </small>
          </div>
        </div>
      </section>

      {/* Offer validity banner — shown when user has a free-trial offer redemption */}
      {offerAccess && (offerAccess.has_offer_access || offerAccess.expired_on) && (
        <div style={{
          margin: "0 0 24px",
          padding: "14px 20px",
          borderRadius: 12,
          display: "flex", alignItems: "center", gap: 14, flexWrap: "wrap",
          background: offerAccess.expired_on && !offerAccess.has_offer_access
            ? "rgba(239,68,68,.1)"
            : offerAccess.expiring_soon
            ? "rgba(245,158,11,.1)"
            : "rgba(16,185,129,.1)",
          border: `1px solid ${
            offerAccess.expired_on && !offerAccess.has_offer_access
              ? "rgba(239,68,68,.35)"
              : offerAccess.expiring_soon
              ? "rgba(245,158,11,.35)"
              : "rgba(16,185,129,.35)"
          }`,
        }}>
          <span style={{ fontSize: "1.4rem" }}>
            {offerAccess.expired_on && !offerAccess.has_offer_access ? "🔴" : offerAccess.expiring_soon ? "⚠️" : "🎟️"}
          </span>
          <div style={{ flex: 1 }}>
            {offerAccess.has_offer_access ? (
              <>
                <strong style={{ color: offerAccess.expiring_soon ? "#fbbf24" : "#34d399", display: "block", marginBottom: 2 }}>
                  {offerAccess.expiring_soon
                    ? `⚠️ Your free trial expires in ${offerAccess.days_remaining} day${offerAccess.days_remaining !== 1 ? "s" : ""}`
                    : "Free trial access active"}
                </strong>
                <span style={{ color: "#94a3b8", fontSize: ".88rem" }}>
                  Valid until {new Date(offerAccess.valid_until).toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" })}
                  {offerAccess.days_remaining > 7 ? ` · ${offerAccess.days_remaining} days remaining` : ""}
                  {offerAccess.expiring_soon ? " — upgrade now to keep your access" : ""}
                </span>
              </>
            ) : (
              <>
                <strong style={{ color: "#f87171", display: "block", marginBottom: 2 }}>
                  Free trial expired
                </strong>
                <span style={{ color: "#94a3b8", fontSize: ".88rem" }}>
                  Your free access expired on {new Date(offerAccess.expired_on).toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" })}
                  {" "}— upgrade to a paid plan to regain full access
                </span>
              </>
            )}
          </div>
        </div>
      )}

      {/* Offer code redeem widget */}
      <div style={{
        margin: "0 0 24px",
        padding: "16px 20px",
        borderRadius: 12,
        background: "rgba(99,102,241,.06)",
        border: "1px solid rgba(99,102,241,.2)",
      }}>
        <h4 style={{ margin: "0 0 6px", fontSize: "0.95rem", color: "var(--text-primary, #f8fafc)" }}>
          🎟️ Have an Offer Code?
        </h4>
        <p style={{ margin: "0 0 12px", fontSize: "0.82rem", color: "var(--text-muted, #94a3b8)" }}>
          Enter your 8-character offer code to unlock platform access for the code's validity period.
        </p>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
          <input
            type="text"
            maxLength={8}
            value={offerCodeInput}
            onChange={(e) => setOfferCodeInput(e.target.value.toUpperCase())}
            placeholder="XXXXXXXX"
            style={{
              fontFamily: "monospace",
              letterSpacing: 3,
              textTransform: "uppercase",
              flex: 1,
              minWidth: 160,
              maxWidth: 220,
              padding: "8px 12px",
              borderRadius: 8,
              border: "1px solid rgba(99,102,241,.35)",
              background: "var(--card-bg, #1e293b)",
              color: "var(--text-primary, #f8fafc)",
              fontSize: "1rem",
            }}
          />
          <button
            className="primary-btn"
            disabled={offerCodeLoading || offerCodeInput.length !== 8}
            onClick={handleRedeemOfferCode}
            style={{ whiteSpace: "nowrap" }}
          >
            {offerCodeLoading ? "Applying…" : "Apply Code"}
          </button>
        </div>
        {offerCodeMsg && <div className="info-box" style={{ marginTop: 10 }}>{offerCodeMsg}</div>}
        {offerCodeErr && <div className="error-box" style={{ marginTop: 10 }}>{offerCodeErr}</div>}
      </div>

      {/* Parent-linked: read-only notice */}
      {!isStandaloneStudent && (
        <div className="info-box" style={{ marginBottom: 24 }}>
          <strong>📢 How to upgrade:</strong> Your account is managed by your parent.
          Ask them to log in and activate a plan for you. Subscriptions for parent-linked
          accounts are managed by the parent.
        </div>
      )}

      {/* Standalone: payment messages */}
      {isStandaloneStudent && paymentMessage && (
        <div className="info-box" style={{ marginBottom: 16 }}>{paymentMessage}</div>
      )}
      {isStandaloneStudent && paymentError && (
        <div className="error-box" style={{ marginBottom: 16 }}>{paymentError}</div>
      )}

      {/* Plan cards */}
      <section className="subscription-plan-grid">
        {planOrder.map((planKey) => {
          const plan = plans[planKey];
          const displayPrice = getPlanDisplayPrice(plan);
          const hasDiscount = Number(plan.discountPercent || 0) > 0;
          const isSelected = selectedPlanKey === plan.key;

          return (
            <article
              key={plan.key}
              className={[
                "subscription-plan-card",
                plan.recommended ? "recommended" : "",
                isStandaloneStudent && isSelected ? "selected" : "",
              ]
                .filter(Boolean)
                .join(" ")}
            >
              <div className="subscription-plan-topline">
                <div>
                  <h3>{plan.label}</h3>
                  <p>{plan.audience}</p>
                </div>
                {plan.badge && <span className="plan-badge">{plan.badge}</span>}
              </div>

              <div className="subscription-price-row">
                <strong>{formatPlanPrice(displayPrice)}</strong>
                <span>/ {plan.billingLabel}</span>
              </div>

              {hasDiscount && (
                <div className="subscription-discount-row">
                  <span>{formatPlanPrice(plan.price)}</span>
                  <strong>
                    {plan.discountLabel || `${plan.discountPercent}% off`}
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

              {isStandaloneStudent ? (
                <button
                  className={plan.recommended ? "primary-btn" : "secondary-btn"}
                  onClick={() => setSelectedPlanKey(plan.key)}
                >
                  {isSelected ? `✓ ${plan.shortLabel} Selected` : `Choose ${plan.shortLabel}`}
                </button>
              ) : (
                <div style={{
                  padding: "10px 14px",
                  background: "rgba(99,102,241,.06)",
                  borderRadius: 8,
                  fontSize: ".82rem",
                  color: "var(--text-muted)",
                  textAlign: "center",
                }}>
                  🔒 Ask your parent to activate this plan
                </div>
              )}
            </article>
          );
        })}
      </section>

      {/* Standalone student: payment panel */}
      {isStandaloneStudent && (
        <section className="subscription-bottom-grid">
          <div className="premium-section subscription-compare">
            <div className="subscription-section-heading">
              <ShieldCheck size={22} strokeWidth={2.4} />
              <h3>What you get</h3>
            </div>
            <div className="premium-grid premium-grid-3" style={{ marginTop: 12 }}>
              <div className="premium-card premium-glow-card glow-blue">
                <h3>📚 All Lessons</h3>
                <p>5-step AI lessons for every CBSE chapter, Grade 5–10.</p>
              </div>
              <div className="premium-card premium-glow-card glow-purple">
                <h3>❓ Unlimited Doubts</h3>
                <p>Ask any question — textbook-aligned AI answers instantly.</p>
              </div>
              <div className="premium-card premium-glow-card glow-green">
                <h3>🧪 Mock Tests</h3>
                <p>Chapter-wise timed tests with scoring and revision guidance.</p>
              </div>
            </div>
          </div>

          <aside className="premium-section subscription-payment-panel">
            <div className="subscription-section-heading">
              <CreditCard size={22} strokeWidth={2.4} />
              <h3>Payment summary</h3>
            </div>
            <div className="subscription-summary-line">
              <span>Selected plan</span>
              <strong>{plans[selectedPlanKey]?.label || "—"}</strong>
            </div>
            <div className="subscription-summary-line total">
              <span>Total today</span>
              <strong>
                {formatPlanPrice(getPlanDisplayPrice(plans[selectedPlanKey] || {}))}
              </strong>
            </div>
            <button
              className="primary-btn"
              disabled={paymentProcessing}
              onClick={handleStudentPayment}
            >
              <Sparkles size={18} strokeWidth={2.5} />
              {paymentProcessing
                ? "Opening Payment..."
                : paymentConfig.configured
                  ? "Pay with UPI"
                  : "Payment Setup Pending"}
            </button>
            <p className="subscription-payment-note">
              {paymentConfig.configured
                ? "UPI checkout opens through Razorpay. Access is activated after payment verification."
                : "Online UPI payment is not yet enabled. Contact us to activate your plan."}
            </p>
          </aside>
        </section>
      )}

      {/* Parent-linked: CTA */}
      {!isStandaloneStudent && (
        <section className="premium-section" style={{ marginTop: 24 }}>
          <div className="premium-header">
            <p className="eyebrow">Ready to unlock everything?</p>
            <h3>👨‍👩‍👧 Ask your parent to subscribe</h3>
            <p style={{ maxWidth: 560 }}>
              Your parent can log in with their parent account and activate a plan
              in minutes. Once done, you'll have unlimited AI lessons, doubt solving,
              practice questions, and mock tests for all your subjects.
            </p>
          </div>
        </section>
      )}

      {/* Contact section */}
      <section className="premium-section subscription-contact-card">
        <div>
          <p className="eyebrow">Questions?</p>
          <h3>Contact us to learn more</h3>
          <p>{contact.message || DEFAULT_SUBSCRIPTION_CONTACT.message}</p>
          <small>{contact.availability || DEFAULT_SUBSCRIPTION_CONTACT.availability}</small>
        </div>
        <div className="subscription-contact-actions">
          <a href={`mailto:${supportEmail}`}>
            <Mail size={20} strokeWidth={2.4} />
            <span>Email<strong>{supportEmail}</strong></span>
          </a>
          {supportPhone ? (
            <a href={`tel:${supportPhone}`}>
              <Phone size={20} strokeWidth={2.4} />
              <span>Call<strong>{contact.phone}</strong></span>
            </a>
          ) : null}
          {supportWhatsapp ? (
            <a
              href={`https://wa.me/${supportWhatsapp.replace("+", "")}`}
              target="_blank"
              rel="noreferrer"
            >
              <MessageCircle size={20} strokeWidth={2.4} />
              <span>WhatsApp<strong>{contact.whatsapp}</strong></span>
            </a>
          ) : null}
        </div>
      </section>
    </div>
  );
}

function SubscriptionPlansPage({ user }) {
  /** Parent-facing plan comparison and payment entry page. */
  const [children, setChildren] = useState([]);
  const [selectedChildId, setSelectedChildId] = useState("");
  // Offer validity — fetch for all parents regardless of access_cbse value
  const [parentOfferAccess, setParentOfferAccess] = useState(
    user?.offerAccess && user?.offerValidUntil
      ? {
          has_offer_access: user.offerAccess,
          valid_until: user.offerValidUntil,
          days_remaining: user.offerDaysRemaining ?? null,
          expiring_soon: !!user.offerExpiringSoon,
          expired_on: user.offerExpiredOn || null,
        }
      : user?.offerExpiredOn
        ? { has_offer_access: false, valid_until: null, days_remaining: 0, expiring_soon: false, expired_on: user.offerExpiredOn }
        : null
  );
  const [selectedPlanKey, setSelectedPlanKey] = useState("premium");
  const [plans, setPlans] = useState(SUBSCRIPTION_PLANS);
  const [contact, setContact] = useState(DEFAULT_SUBSCRIPTION_CONTACT);
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
      /** Load children, current plan settings, and payment readiness in one page bootstrap. */
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
        const loadedContact = {
          ...DEFAULT_SUBSCRIPTION_CONTACT,
          ...(planResult.contact || {}),
        };

        setPlans(loadedPlans);
        setContact(loadedContact);
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
    } else if (user?.role === "student") {
      // Students get read-only plan data — no children or payment config needed
      getParentSubscriptionPlans()
        .then((planResult) => {
          const loadedPlans = mergeSubscriptionPlans(planResult.plans || {});
          const loadedPlanOrder = (planResult.plan_order || []).filter(
            (planKey) => loadedPlans[planKey]?.isPublic !== false
          );
          const loadedContact = {
            ...DEFAULT_SUBSCRIPTION_CONTACT,
            ...(planResult.contact || {}),
          };
          setPlans(loadedPlans);
          setContact(loadedContact);
          if (loadedPlanOrder.length) setPlanOrder(loadedPlanOrder);
        })
        .catch(() => {
          // Fall back to defaults silently — student view still works
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, [user?.role]);

  // Fallback fetch for parent offer validity — must be a top-level useEffect, not nested
  useEffect(() => {
    if (user?.role !== "parent") return;
    if (user?.offerAccess && user?.offerValidUntil) return;
    async function fetchParentOffer() {
      try {
        const { data: { session } } = await supabase.auth.getSession();
        const token = session?.access_token || user?.accessToken;
        if (!token) return;
        const r = await fetch(`${import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"}/api/offer/my-access`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (r.ok) {
          const d = await r.json();
          if (d) setParentOfferAccess(d);
        }
      } catch { /* non-critical */ }
    }
    fetchParentOffer();
  }, [user?.role, user?.offerValidUntil]);

  const selectedChild = useMemo(
    () => children.find((child) => child.id === selectedChildId),
    [children, selectedChildId]
  );

  const activePlan =
    plans[selectedChild?.subscription_plan] ||
    getSubscriptionPlan(selectedChild?.subscription_plan);
  const selectedPlan = plans[selectedPlanKey] || getSubscriptionPlan(selectedPlanKey);
  const isCurrentPlan = activePlan.key === selectedPlan.key;
  const supportEmail = contact.email || DEFAULT_SUBSCRIPTION_CONTACT.email;
  const supportPhone = cleanContactNumber(contact.phone);
  const supportWhatsapp = cleanContactNumber(contact.whatsapp);

  function handlePlanClick(planKey) {
    /** Select the plan card the parent wants to review or purchase. */
    setSelectedPlanKey(planKey);
    setMessage("");
    setError("");
  }

  function loadRazorpayCheckout() {
    /** Lazily inject Razorpay Checkout so normal browsing is unaffected until payment starts. */
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
    /** Start a payment order when Razorpay is configured, otherwise show a non-blocking setup message. */
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

  if (user?.role === "student") {
    return (
      <StudentSubscriptionView
        user={user}
        plans={plans}
        planOrder={planOrder}
        contact={contact}
        loading={loading}
      />
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

      {/* Offer validity banner — shows parent's free-trial access + expiry date */}
      {parentOfferAccess && (parentOfferAccess.has_offer_access || parentOfferAccess.expired_on) && (
        <div style={{
          marginBottom: 24, padding: "14px 20px", borderRadius: 12,
          display: "flex", alignItems: "center", gap: 14, flexWrap: "wrap",
          background: parentOfferAccess.expired_on && !parentOfferAccess.has_offer_access
            ? "rgba(239,68,68,.1)" : parentOfferAccess.expiring_soon ? "rgba(245,158,11,.1)" : "rgba(16,185,129,.1)",
          border: `1px solid ${parentOfferAccess.expired_on && !parentOfferAccess.has_offer_access ? "rgba(239,68,68,.35)" : parentOfferAccess.expiring_soon ? "rgba(245,158,11,.35)" : "rgba(16,185,129,.35)"}`,
        }}>
          <span style={{ fontSize: "1.4rem" }}>
            {parentOfferAccess.expired_on && !parentOfferAccess.has_offer_access ? "🔴" : parentOfferAccess.expiring_soon ? "⚠️" : "🎟️"}
          </span>
          <div style={{ flex: 1 }}>
            {parentOfferAccess.has_offer_access ? (
              <>
                <strong style={{ color: parentOfferAccess.expiring_soon ? "#fbbf24" : "#34d399", display: "block", marginBottom: 2 }}>
                  {parentOfferAccess.expiring_soon
                    ? `⚠️ Your free trial expires in ${parentOfferAccess.days_remaining} day${parentOfferAccess.days_remaining !== 1 ? "s" : ""}`
                    : "Free trial access active"}
                </strong>
                <span style={{ color: "#94a3b8", fontSize: ".88rem" }}>
                  Valid until {new Date(parentOfferAccess.valid_until).toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" })}
                  {parentOfferAccess.days_remaining > 7 ? ` · ${parentOfferAccess.days_remaining} days remaining` : ""}
                  {parentOfferAccess.expiring_soon ? " — upgrade to a paid plan to keep access" : ""}
                </span>
              </>
            ) : (
              <>
                <strong style={{ color: "#f87171", display: "block", marginBottom: 2 }}>Free trial expired</strong>
                <span style={{ color: "#94a3b8", fontSize: ".88rem" }}>
                  Your free access expired on {new Date(parentOfferAccess.expired_on).toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" })}
                  {" "}— subscribe to a paid plan to restore access for your children.
                </span>
              </>
            )}
          </div>
        </div>
      )}

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

      <section className="premium-section subscription-contact-card">
        <div>
          <p className="eyebrow">Need help?</p>
          <h3>Contact us before choosing a plan</h3>
          <p>{contact.message || DEFAULT_SUBSCRIPTION_CONTACT.message}</p>
          <small>{contact.availability || DEFAULT_SUBSCRIPTION_CONTACT.availability}</small>
        </div>

        <div className="subscription-contact-actions">
          <a href={`mailto:${supportEmail}`}>
            <Mail size={20} strokeWidth={2.4} />
            <span>
              Email
              <strong>{supportEmail}</strong>
            </span>
          </a>

          {supportPhone ? (
            <a href={`tel:${supportPhone}`}>
              <Phone size={20} strokeWidth={2.4} />
              <span>
                Call
                <strong>{contact.phone}</strong>
              </span>
            </a>
          ) : (
            <div className="subscription-contact-placeholder">
              <Phone size={20} strokeWidth={2.4} />
              <span>
                Call
                <strong>Support number will be added soon</strong>
              </span>
            </div>
          )}

          {supportWhatsapp ? (
            <a
              href={`https://wa.me/${supportWhatsapp.replace("+", "")}`}
              target="_blank"
              rel="noreferrer"
            >
              <MessageCircle size={20} strokeWidth={2.4} />
              <span>
                WhatsApp
                <strong>{contact.whatsapp}</strong>
              </span>
            </a>
          ) : (
            <div className="subscription-contact-placeholder">
              <MessageCircle size={20} strokeWidth={2.4} />
              <span>
                WhatsApp
                <strong>Optional contact channel</strong>
              </span>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

export default SubscriptionPlansPage;
