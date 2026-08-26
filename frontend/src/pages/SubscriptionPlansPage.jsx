import { useEffect, useMemo, useState } from "react";
import { supabase } from "../api/supabaseClient";
import { redeemOfferCode } from "../api/adminControl";
import {
  CreditCard,
  Mail,
  MessageCircle,
  Phone,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { resolveSubscription, ACCESS_SOURCE } from "../utils/resolveSubscription";
import NoticeboardPricingTable from "../components/NoticeboardPricingTable";

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
  getExamPrepUpgradeDiscount,
  EXAM_PREP_ELIGIBLE_GRADES,
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

function StudentSubscriptionView({ user, plans, planOrder, contact, loading, onSubscriptionComplete }) {
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

  // ── Canonical subscription resolver ─────────────────────────────────────
  // Single source of truth for what plan/tier to display. Both the "current
  // access" card and the validity banner derive from this — they can never
  // disagree with each other.
  const resolvedSub = resolveSubscription(user, offerAccess);
  const currentPlanLabel =
    resolvedSub.accessSource === ACCESS_SOURCE.OFFER_CODE
      ? "Offer / Free Access"
      : resolvedSub.accessSource === ACCESS_SOURCE.NONE
        ? "Free Tier"
        : resolvedSub.planName;

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
      // Always get a fresh token — the token stored in user.accessToken at login
      // may have expired, especially for new Google OAuth users.
      const { data: { session } } = await supabase.auth.getSession();
      const freshToken = session?.access_token || user.accessToken;
      const res = await redeemOfferCode(offerCodeInput, freshToken);
      setOfferCodeMsg(res.message || "✅ Offer code applied! Your access has been activated.");
      setOfferCodeInput("");
      // Refresh offer access display — reuse freshToken already obtained above
      if (freshToken) {
        const r = await fetch(`${import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"}/api/offer/my-access`, {
          headers: { Authorization: `Bearer ${freshToken}` },
        });
        if (r.ok) { const d = await r.json(); if (d) setOfferAccess(d); }
      }
      // Notify App shell to refresh user profile and unlock platform
      if (typeof onSubscriptionComplete === "function") {
        setTimeout(onSubscriptionComplete, 800);
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

  // Exam Prep Center upgrade nudge (feature: notify free-tier Gr 11/12 students
  // picking Premium) + loyalty discount preview (feature: ₹200 off for existing
  // Premium/Family Premium Gr 11/12 subscribers upgrading to Exam Prep Center).
  const isFreeTierPlan = !user?.subscriptionPlan || user.subscriptionPlan === "free_tier";
  const examPrepNudgeVisible =
    selectedPlanKey === "starter" && isFreeTierPlan && EXAM_PREP_ELIGIBLE_GRADES.has(user?.grade);
  const examPrepDiscount =
    selectedPlanKey === "exam_prep_center"
      ? getExamPrepUpgradeDiscount(user?.subscriptionPlan, user?.grade)
      : 0;

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
              `✅ ${plan.label} activated! Taking you to your dashboard…`
            );
            // Notify App shell to refresh user profile and unlock platform
            if (typeof onSubscriptionComplete === "function") {
              setTimeout(onSubscriptionComplete, 1200);
            }
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
              {resolvedSub.accessSource === ACCESS_SOURCE.PAID
                ? resolvedSub.validUntil
                  ? `✅ ${resolvedSub.planName} · ${resolvedSub.daysRemaining ?? ""} days remaining`
                  : `✅ ${resolvedSub.planName} active`
                : resolvedSub.accessSource === ACCESS_SOURCE.ADMIN_GRANT
                  ? "✅ CBSE access active"
                  : resolvedSub.accessSource === ACCESS_SOURCE.OFFER_CODE && resolvedSub.validUntil
                    ? resolvedSub.expiringSoon
                      ? `⚠️ Expires in ${resolvedSub.daysRemaining} day${resolvedSub.daysRemaining !== 1 ? "s" : ""} — ${new Date(resolvedSub.validUntil).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })}`
                      : `🟢 Valid until ${new Date(resolvedSub.validUntil).toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" })} · ${resolvedSub.daysRemaining} days remaining`
                    : offerAccess?.expired_on
                      ? `🔴 Expired on ${new Date(offerAccess.expired_on).toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" })}`
                      : "active"}
            </small>
          </div>
        </div>
      </section>

      {/* ── Canonical subscription validity banner ─────────────────────────
          Uses resolvedSub (from resolveSubscription utility) so this banner
          and the "current access" card above always show the same state.

          Scenarios:
            PAID        → "✨ Premium Nano active" / "✨ Premium active" (with expiry)
            OFFER_CODE  → "🎟️ Offer access active" (NOT "Premium Nano")
            expired     → "🔴 Free trial expired" (from offerAccess.expired_on)
      ──────────────────────────────────────────────────────────────────── */}

      {/* Active paid subscription banner */}
      {resolvedSub.accessSource === ACCESS_SOURCE.PAID && resolvedSub.validUntil && (
        <div style={{
          margin: "0 0 24px", padding: "14px 20px", borderRadius: 12,
          display: "flex", alignItems: "center", gap: 14, flexWrap: "wrap",
          background: resolvedSub.expiringSoon
            ? "rgba(245,158,11,.1)" : "rgba(99,102,241,.1)",
          border: `1px solid ${resolvedSub.expiringSoon ? "rgba(245,158,11,.35)" : "rgba(99,102,241,.35)"}`,
        }}>
          <span style={{ fontSize: "1.4rem" }}>{resolvedSub.expiringSoon ? "⚠️" : "✨"}</span>
          <div style={{ flex: 1 }}>
            <strong style={{ color: resolvedSub.expiringSoon ? "#fbbf24" : "#a5b4fc", display: "block", marginBottom: 2 }}>
              {resolvedSub.expiringSoon
                ? `⚠️ ${resolvedSub.planName} expires in ${resolvedSub.daysRemaining} day${resolvedSub.daysRemaining !== 1 ? "s" : ""}`
                : `✨ ${resolvedSub.planName} active`}
            </strong>
            <span style={{ color: "#94a3b8", fontSize: ".88rem" }}>
              Valid until {new Date(resolvedSub.validUntil).toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" })}
              {resolvedSub.daysRemaining > 7 ? ` · ${resolvedSub.daysRemaining} days remaining` : ""}
              {resolvedSub.expiringSoon ? " — upgrade now to keep your access" : ""}
            </span>
          </div>
        </div>
      )}

      {/* Expired offer banner — shown only when offer has expired and no paid plan */}
      {offerAccess?.expired_on && !offerAccess.has_offer_access
        && resolvedSub.accessSource !== ACCESS_SOURCE.PAID && (
        <div style={{
          margin: "0 0 24px", padding: "14px 20px", borderRadius: 12,
          display: "flex", alignItems: "center", gap: 14, flexWrap: "wrap",
          background: "rgba(239,68,68,.1)",
          border: "1px solid rgba(239,68,68,.35)",
        }}>
          <span style={{ fontSize: "1.4rem" }}>🔴</span>
          <div style={{ flex: 1 }}>
            <strong style={{ color: "#f87171", display: "block", marginBottom: 2 }}>
              Free trial expired
            </strong>
            <span style={{ color: "#94a3b8", fontSize: ".88rem" }}>
              Your free access expired on {new Date(offerAccess.expired_on).toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" })}
              {" "}— upgrade to a paid plan to regain full access
            </span>
          </div>
        </div>
      )}

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

      {/* Parent-linked (non-standalone): no selectable cards or CTAs — just a
          static notice to ask their parent, plus the read-only comparison
          table below. Standalone students select a plan directly from the
          comparison table's CTA row (see the NoticeboardPricingTable call
          below), which replaced the old separate plan-card grid. */}
      {!isStandaloneStudent && (
        <div style={{
          padding: "10px 14px",
          background: "rgba(99,102,241,.06)",
          borderRadius: 8,
          fontSize: ".82rem",
          color: "var(--text-muted)",
          textAlign: "center",
          marginBottom: 20,
        }}>
          🔒 Ask your parent to activate a plan
        </div>
      )}

      {/* Standalone student: full plan comparison + payment panel */}
      {isStandaloneStudent && (
        <section className="subscription-bottom-grid subscription-bottom-grid--stacked">
          <div className="premium-section subscription-compare">
            <div className="subscription-section-heading">
              <ShieldCheck size={22} strokeWidth={2.4} />
              <h3>Compare plans</h3>
            </div>
            <div style={{ marginTop: 12 }}>
              <NoticeboardPricingTable
                theme="light"
                showFreeCta={false}
                onChoosePlan={(planKey) => { if (plans[planKey]) setSelectedPlanKey(planKey); }}
              />
            </div>
          </div>

          <aside className="premium-section subscription-payment-panel">
            {examPrepNudgeVisible && (
              <div style={{
                marginBottom: 16, padding: "12px 14px", borderRadius: 10,
                background: "rgba(59,130,246,.1)", border: "1px solid rgba(59,130,246,.35)",
              }}>
                <strong style={{ display: "block", marginBottom: 4, color: "#60a5fa" }}>
                  💡 Better value available
                </strong>
                <p style={{ margin: "0 0 8px", fontSize: ".82rem", color: "var(--text-muted)" }}>
                  Exam Prep Center gives you 12 months of Premium-equivalent access
                  <strong> plus</strong> JEE, NEET, CUET, SAT, IELTS & TOEFL prep —
                  not included in Premium — for ₹1,999/year.
                </p>
                <button
                  className="secondary-btn"
                  style={{ fontSize: ".78rem", padding: "6px 12px" }}
                  onClick={() => setSelectedPlanKey("exam_prep_center")}
                >
                  Switch to Exam Prep Center
                </button>
              </div>
            )}
            <div className="subscription-section-heading">
              <CreditCard size={22} strokeWidth={2.4} />
              <h3>Payment summary</h3>
            </div>
            <div className="subscription-summary-line">
              <span>Selected plan</span>
              <strong>{plans[selectedPlanKey]?.label || "—"}</strong>
            </div>
            {examPrepDiscount > 0 && (
              <div className="subscription-summary-line">
                <span>🎉 Loyalty discount</span>
                <strong style={{ color: "#10b981" }}>-{formatPlanPrice(examPrepDiscount)}</strong>
              </div>
            )}
            <div className="subscription-summary-line total">
              <span>Total today</span>
              <strong>
                {examPrepDiscount > 0 && (
                  <span style={{ textDecoration: "line-through", color: "var(--text-muted)", fontWeight: 400, marginRight: 8 }}>
                    {formatPlanPrice(getPlanDisplayPrice(plans[selectedPlanKey] || {}))}
                  </span>
                )}
                {formatPlanPrice(Math.max(0, getPlanDisplayPrice(plans[selectedPlanKey] || {}) - examPrepDiscount))}
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

      {/* Offer code redeem widget — below the Payment summary card */}
      <div className="subscription-hero" style={{ marginBottom: 24, padding: "20px 24px" }}>
        <div style={{ flex: 1 }}>
          <h4 style={{ margin: "0 0 4px", fontSize: "0.95rem" }}>
            🎟️ Have an Offer Code?
          </h4>
          <p style={{ margin: "0 0 14px", fontSize: "0.84rem", color: "var(--text-muted)" }}>
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
                letterSpacing: 4,
                textTransform: "uppercase",
                flex: 1,
                minWidth: 160,
                maxWidth: 220,
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
      </div>

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

function SubscriptionPlansPage({ user, onSubscriptionComplete }) {
  /** Parent-facing plan comparison and payment entry page. */
  const [children, setChildren] = useState([]);
  const [selectedChildId, setSelectedChildId] = useState("");
  // Offer validity — fetch for all parents regardless of access_cbse value
  const [, setParentOfferAccess] = useState(
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
  const [selectedPlanKey, setSelectedPlanKey] = useState("starter");
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
          (planKey) => loadedPlans[planKey] && loadedPlans[planKey].isPublic !== false
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
            (planKey) => loadedPlans[planKey] && loadedPlans[planKey].isPublic !== false
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

  // Exam Prep Center upgrade nudge + loyalty discount preview (see
  // StudentSubscriptionView above for the standalone-student equivalent).
  const childIsFreeTierPlan =
    !selectedChild?.subscription_plan || selectedChild.subscription_plan === "free_tier";
  const examPrepNudgeVisible =
    selectedPlanKey === "starter"
    && childIsFreeTierPlan
    && EXAM_PREP_ELIGIBLE_GRADES.has(selectedChild?.grade);
  const examPrepDiscount =
    selectedPlanKey === "exam_prep_center"
      ? getExamPrepUpgradeDiscount(selectedChild?.subscription_plan, selectedChild?.grade)
      : 0;

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

            // Refresh this child's plan so activePlan/isCurrentPlan reflect the
            // new entitlement immediately — without this, the pay button stays
            // enabled on the just-purchased plan until a manual page reload,
            // risking an accidental second charge.
            try {
              const refreshed = await getParentChildren();
              setChildren(refreshed.children || []);
            } catch (refreshErr) {
              console.error(refreshErr);
            }

            // Notify App shell to refresh the parent's own profile too.
            if (typeof onSubscriptionComplete === "function") {
              setTimeout(onSubscriptionComplete, 1200);
            }
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
        onSubscriptionComplete={onSubscriptionComplete}
      />
    );
  }

  if (user?.role === "teacher") {
    const supportEmail = contact.email || DEFAULT_SUBSCRIPTION_CONTACT.email;
    const supportPhone = cleanContactNumber(contact.phone);
    const supportWhatsapp = cleanContactNumber(contact.whatsapp);
    const isFree = !user?.subscriptionPlan || user.subscriptionPlan === "free";

    const teacherPlans = [
      { key: "free_trial", name: "Free Trial", price: "₹0", period: "forever", note: "Try it out", color: "#64748b" },
      { key: "paid_teacher", name: "Paid Teacher", price: "Contact us", period: "", note: "Full toolkit", color: "#7c3aed", tag: "Recommended" },
    ];

    const teacherGroups = [
      { title: "Content Creation", rows: [
        ["Test Paper Generator", "2 / day", "Unlimited"],
        ["Lesson Plan Creator", "2 / day", "Unlimited"],
        ["Listen to Lecture (AI audio)", "2 / day", "Unlimited"],
      ]},
      { title: "Exam Prep & Insights", rows: [
        ["Question Bank (for test papers)", "Available", "Full bank"],
        ["Student Analytics Dashboard", true, true],
      ]},
      { title: "Coverage", rows: [
        ["All CBSE Grade 5–12", true, true],
      ]},
      { title: "Communication", rows: [
        ["Direct Chat (Students & Parents)", true, true],
      ]},
    ];

    return (
      <div className="premium-page subscription-page">
        {/* Hero */}
        <section className="subscription-hero" style={{ marginBottom: 32 }}>
          <div>
            <p className="eyebrow">Teacher Subscription</p>
            <h2>Unlock the full Teacher Toolkit</h2>
            <p>You are currently on the <strong>{isFree ? "Free Tier" : "Paid"}</strong> plan.
              Upgrade to get unlimited test papers, lesson plans, and lecture audio.</p>
          </div>
          <div className="subscription-current-panel">
            <div className="subscription-current-plan">
              <span>Your current plan</span>
              <strong>{isFree ? "Free Tier" : "Paid Teacher"}</strong>
              <small>{isFree ? "🔒 Limited daily access" : "✅ Full access active"}</small>
            </div>
          </div>
        </section>

        {/* Free vs Paid comparison table */}
        <section className="premium-section" style={{ marginBottom: 32 }}>
          <div className="subscription-section-heading">
            <ShieldCheck size={22} strokeWidth={2.4} />
            <h3>Free Trial vs Paid — Feature Comparison</h3>
          </div>

          <div style={{ marginTop: 16 }}>
            <NoticeboardPricingTable
              theme="light"
              plans={teacherPlans}
              groups={teacherGroups}
              showCta={false}
              footnote={<span>✓ / ✗ show what&rsquo;s included &middot; Paid Teacher is activated after contacting our team below</span>}
            />
          </div>
        </section>

        {/* What's included in paid */}
        <section className="premium-section" style={{ marginBottom: 32 }}>
          <div className="subscription-section-heading">
            <Sparkles size={22} strokeWidth={2.4} />
            <h3>What paid teachers get</h3>
          </div>
          <div className="premium-grid premium-grid-4" style={{ marginTop: 16 }}>
            <div className="premium-card premium-glow-card glow-blue">
              <h3>📝 Unlimited Test Papers</h3>
              <p>Generate as many test papers as you need daily — MCQ, Subjective, or Mixed for any CBSE chapter.</p>
            </div>
            <div className="premium-card premium-glow-card glow-purple">
              <h3>📋 Unlimited Lesson Plans</h3>
              <p>Create detailed CBSE-aligned lesson plans for any chapter, instantly downloadable as PDF.</p>
            </div>
            <div className="premium-card premium-glow-card glow-red">
              <h3>🎧 Unlimited Lecture Audio</h3>
              <p>Turn any lesson plan into a ready-to-play AI narrated lecture — no more daily cap on Listen to Lecture.</p>
            </div>
            <div className="premium-card premium-glow-card glow-green">
              <h3>📊 Full Question Bank</h3>
              <p>Access the complete pre-authored question bank for any CBSE chapter to build richer test papers.</p>
            </div>
          </div>
        </section>

        {/* Contact to upgrade */}
        <section className="premium-section subscription-contact-card">
          <div>
            <p className="eyebrow">Ready to upgrade?</p>
            <h3>Contact us to activate your Teacher Plan</h3>
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
              <a href={`https://wa.me/${supportWhatsapp.replace("+","")}`} target="_blank" rel="noreferrer">
                <MessageCircle size={20} strokeWidth={2.4} />
                <span>WhatsApp<strong>{contact.whatsapp}</strong></span>
              </a>
            ) : null}
          </div>
        </section>
      </div>
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
          <p className="eyebrow">Your Subscription</p>
          <h2>Choose the right plan for your family</h2>
          <p>
            Compare plans and pay directly with UPI. Your child's
            access is activated instantly after payment.
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
            <span>Your current access</span>
            <strong>{activePlan.label}</strong>
            <small>{selectedChild?.account_status || "active"}</small>
          </div>
        </div>
      </section>

      {message && <div className="info-box">{message}</div>}
      {error && <div className="error-box">{error}</div>}

      {/* Plan comparison + selection — same NoticeboardPricingTable pattern as
          the student view (StudentSubscriptionView above): parents pick a
          plan directly from the comparison table's CTA row instead of a
          separate card grid. */}
      <section className="subscription-bottom-grid subscription-bottom-grid--stacked">
        <div className="premium-section subscription-compare">
          <div className="subscription-section-heading">
            <ShieldCheck size={22} strokeWidth={2.4} />
            <h3>Compare plans</h3>
          </div>
          <div style={{ marginTop: 12 }}>
            <NoticeboardPricingTable
              theme="light"
              showFreeCta={false}
              onChoosePlan={handlePlanClick}
            />
          </div>
        </div>

        <aside className="premium-section subscription-payment-panel">
          {examPrepNudgeVisible && (
            <div style={{
              marginBottom: 16, padding: "12px 14px", borderRadius: 10,
              background: "rgba(59,130,246,.1)", border: "1px solid rgba(59,130,246,.35)",
            }}>
              <strong style={{ display: "block", marginBottom: 4, color: "#60a5fa" }}>
                💡 Better value available
              </strong>
              <p style={{ margin: "0 0 8px", fontSize: ".82rem", color: "var(--text-muted)" }}>
                Exam Prep Center gives {selectedChild?.username || "your child"} 12 months
                of Premium-equivalent access <strong>plus</strong> JEE, NEET, CUET, SAT,
                IELTS & TOEFL prep — not included in Premium — for ₹1,999/year.
              </p>
              <button
                className="secondary-btn"
                style={{ fontSize: ".78rem", padding: "6px 12px" }}
                onClick={() => handlePlanClick("exam_prep_center")}
              >
                Switch to Exam Prep Center
              </button>
            </div>
          )}
          <div className="subscription-section-heading">
            <CreditCard size={22} strokeWidth={2.4} />
            <h3>Payment summary</h3>
          </div>

          <div className="subscription-summary-line">
            <span>Selected child</span>
            <strong>{selectedChild?.username || "No child selected"}</strong>
          </div>

          <div className="subscription-summary-line">
            <span>Selected plan</span>
            <strong>{selectedPlan.label}</strong>
          </div>

          {examPrepDiscount > 0 && (
            <div className="subscription-summary-line">
              <span>🎉 Loyalty discount</span>
              <strong style={{ color: "#10b981" }}>-{formatPlanPrice(examPrepDiscount)}</strong>
            </div>
          )}

          <div className="subscription-summary-line total">
            <span>Total today</span>
            <strong>
              {examPrepDiscount > 0 && (
                <span style={{ textDecoration: "line-through", color: "var(--text-muted)", fontWeight: 400, marginRight: 8 }}>
                  {formatPlanPrice(getPlanDisplayPrice(selectedPlan))}
                </span>
              )}
              {formatPlanPrice(Math.max(0, getPlanDisplayPrice(selectedPlan) - examPrepDiscount))}
            </strong>
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
          <p className="eyebrow">Questions?</p>
          <h3>Contact us to learn more</h3>
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
