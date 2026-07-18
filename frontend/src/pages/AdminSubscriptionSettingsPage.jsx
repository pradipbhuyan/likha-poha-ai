import { useEffect, useState } from "react";
import { Save } from "lucide-react";

import {
  getAdminSubscriptionContact,
  getAdminSubscriptionPlans,
  updateAdminSubscriptionContact,
  updateAdminSubscriptionPlans,
} from "../api/adminControl";
import {
  formatPlanPrice,
  getPlanDisplayPrice,
  mergeSubscriptionPlans,
  serializeSubscriptionPlan,
  SUBSCRIPTION_PLAN_ORDER,
  SUBSCRIPTION_PLANS,
} from "../config/subscriptionPlans";

// ── Helpers ───────────────────────────────────────────────────────────────────

function listToText(items = []) {
  if (!items) return "";
  if (typeof items === "string") return items;
  if (!Array.isArray(items)) return String(items);
  return items.join("\n");
}

function textToList(value) {
  return String(value || "")
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
}

const DEFAULT_CONTACT = {
  email: "likhapohaai@gmail.com",
  phone: "",
  whatsapp: "",
  availability: "We usually respond within one business day.",
  message: "Need help choosing a plan or activating access? Contact us and we will guide you.",
};

// Shared inline style tokens
const S = {
  card: { background: "var(--panel,#1e293b)", border: "1px solid var(--border,#334155)", borderRadius: 12, overflow: "hidden", marginBottom: 12 },
  inp: { background: "var(--surface2,#0f172a)", border: "1px solid var(--border,#334155)", borderRadius: 6, padding: "6px 10px", color: "var(--text,#e2e8f0)", fontSize: ".78rem", fontFamily: "inherit", width: "100%" },
  lbl: { fontSize: ".59rem", color: "var(--muted,#64748b)", fontWeight: 700, textTransform: "uppercase", letterSpacing: ".04em", display: "block", marginBottom: 3 },
  fg: { marginBottom: 9 },
  colHd: { fontSize: ".58rem", fontWeight: 800, textTransform: "uppercase", letterSpacing: ".07em", color: "#6366f1", marginBottom: 12, paddingBottom: 7, borderBottom: "1px solid rgba(99,102,241,.15)" },
  tog: { display: "flex", alignItems: "center", justifyContent: "space-between", padding: "7px 9px", background: "var(--surface2,#0f172a)", border: "1px solid var(--border,#334155)", borderRadius: 7, marginBottom: 6, cursor: "pointer" },
};

function Field({ label, children }) {
  return (
    <div style={S.fg}>
      <span style={S.lbl}>{label}</span>
      {children}
    </div>
  );
}

function Toggle({ label, desc, checked, onChange }) {
  return (
    <div style={S.tog} onClick={() => onChange(!checked)}>
      <div>
        <div style={{ fontSize: ".75rem", fontWeight: 600 }}>{label}</div>
        {desc && <div style={{ fontSize: ".58rem", color: "var(--muted,#64748b)", marginTop: 1 }}>{desc}</div>}
      </div>
      <div style={{
        width: 32, height: 18, borderRadius: 18, background: checked ? "#6366f1" : "#334155",
        position: "relative", flexShrink: 0, marginLeft: 10, transition: ".15s",
      }}>
        <div style={{
          position: "absolute", top: 3, left: checked ? 17 : 3,
          width: 12, height: 12, borderRadius: "50%",
          background: checked ? "#fff" : "#64748b", transition: ".15s",
        }} />
      </div>
    </div>
  );
}

// ── Plan edit panel (3 columns) ───────────────────────────────────────────────

function PlanEditPanel({ planKey, plan, onUpdate, onUpdateComparison }) {
  const chargeAmount = getPlanDisplayPrice(plan);
  const inp = (field, type = "text", extra = {}) => (
    <input
      style={S.inp}
      type={type}
      value={plan[field] ?? ""}
      onChange={(e) => onUpdate(planKey, field, type === "number" ? (e.target.value === "" ? null : Number(e.target.value)) : e.target.value)}
      {...extra}
    />
  );

  return (
    <div style={{ background: "var(--panel,#1e293b)", border: "2px solid #6366f1", borderRadius: 12, overflow: "hidden" }}>
      {/* Panel header */}
      <div style={{ background: "rgba(99,102,241,.08)", borderBottom: "1px solid #334155", padding: "12px 18px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <div style={{ fontSize: ".88rem", fontWeight: 800 }}>
            Editing: {plan.label}&nbsp;
            <code style={{ background: "var(--surface2,#0f172a)", padding: "2px 6px", borderRadius: 4, fontSize: ".66rem", color: "var(--muted,#64748b)" }}>{planKey}</code>
          </div>
          <div style={{ marginTop: 4, display: "flex", gap: 5, flexWrap: "wrap" }}>
            {plan.isPublic !== false && <span style={{ fontSize: ".58rem", background: "rgba(34,197,94,.12)", color: "#4ade80", border: "1px solid rgba(34,197,94,.2)", padding: "1px 7px", borderRadius: 20, fontWeight: 700 }}>✅ Visible</span>}
            {plan.access_exam_prep !== false && <span style={{ fontSize: ".58rem", background: "rgba(245,158,11,.1)", color: "#fbbf24", border: "1px solid rgba(245,158,11,.2)", padding: "1px 7px", borderRadius: 20, fontWeight: 700 }}>🎓 Exam Prep</span>}
            {plan.access_exemplar !== false && <span style={{ fontSize: ".58rem", background: "rgba(99,102,241,.12)", color: "#a5b4fc", border: "1px solid rgba(99,102,241,.2)", padding: "1px 7px", borderRadius: 20, fontWeight: 700 }}>📖 Exemplar</span>}
          </div>
        </div>
        <div style={{ textAlign: "right" }}>
          <div style={{ fontSize: "1.7rem", fontWeight: 900, color: "#a5b4fc", lineHeight: 1 }}>{formatPlanPrice(chargeAmount)}</div>
          <div style={{ fontSize: ".58rem", color: "var(--muted,#64748b)", marginTop: 2 }}>Razorpay charges this</div>
        </div>
      </div>

      {/* 3-column body */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr" }}>

        {/* Col 1: Pricing & Validity */}
        <div style={{ padding: "16px 18px", borderRight: "1px solid var(--border,#334155)" }}>
          <div style={S.colHd}>💰 Pricing & Validity</div>

          {/* Live charge calculator */}
          <div style={{ background: "rgba(99,102,241,.07)", border: "1px solid rgba(99,102,241,.18)", borderRadius: 7, padding: "8px 11px", marginBottom: 10 }}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: ".63rem", color: "var(--muted,#64748b)", marginBottom: 2 }}>
              <span>Base price</span><span>₹{plan.price || 0}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: ".63rem", color: "var(--muted,#64748b)", marginBottom: 2 }}>
              <span>Discount</span><span>{plan.discountPercent || 0}%</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: ".72rem", fontWeight: 800, color: "#a5b4fc" }}>
              <span>Razorpay charge</span><span>₹{chargeAmount}</span>
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 9 }}>
            <Field label="Price (₹)">{inp("price", "number", { min: 0 })}</Field>
            <Field label="Discount %">{inp("discountPercent", "number", { min: 0, max: 100 })}</Field>
          </div>
          <Field label="Discount Label">{inp("discountLabel", "text", { placeholder: "e.g. Summer offer" })}</Field>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 9 }}>
            <Field label="Duration (days)" >{inp("duration_days", "number", { min: 1, placeholder: "overrides billing label" })}</Field>
            <Field label="Billing Label">{inp("billingLabel")}</Field>
          </div>
          <Field label="Badge">{inp("badge", "text", { placeholder: "Most Popular" })}</Field>

          <Toggle
            label="Show to parents"
            desc="Visible on subscription page"
            checked={plan.isPublic !== false}
            onChange={(v) => onUpdate(planKey, "isPublic", v)}
          />
          <Toggle
            label="Recommended"
            desc="Highlighted on plans page"
            checked={!!plan.recommended}
            onChange={(v) => onUpdate(planKey, "recommended", v)}
          />
        </div>

        {/* Col 2: Display & Limits */}
        <div style={{ padding: "16px 18px", borderRight: "1px solid var(--border,#334155)" }}>
          <div style={S.colHd}>🏷️ Display & Limits</div>
          <Field label="Plan Label">{inp("label")}</Field>
          <Field label="Short Label">{inp("shortLabel")}</Field>
          <Field label="Audience Description">
            <textarea
              style={{ ...S.inp, height: 52, resize: "vertical" }}
              value={plan.audience || ""}
              onChange={(e) => onUpdate(planKey, "audience", e.target.value)}
            />
          </Field>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 9 }}>
            <Field label="Daily Tokens">{inp("daily_token_limit", "number", { min: 0 })}</Field>
            <Field label="Monthly Tokens">{inp("monthly_token_limit", "number", { min: 0 })}</Field>
          </div>
          <Field label="Included Features (one per line)">
            <textarea
              style={{ ...S.inp, height: 84, resize: "vertical" }}
              value={listToText(plan.included)}
              onChange={(e) => onUpdate(planKey, "included", textToList(e.target.value))}
            />
          </Field>
          <Field label="Not Included (one per line)">
            <textarea
              style={{ ...S.inp, height: 60, resize: "vertical" }}
              value={listToText(plan.notIncluded)}
              onChange={(e) => onUpdate(planKey, "notIncluded", textToList(e.target.value))}
            />
          </Field>
        </div>

        {/* Col 3: Feature Flags & Comparison */}
        <div style={{ padding: "16px 18px" }}>
          <div style={S.colHd}>🎛️ Feature Flags & Comparison</div>
          <Toggle
            label="🎓 Exam Prep (JEE/NEET/CUET)"
            desc="Grants access to Exam Prep Center"
            checked={plan.access_exam_prep !== false}
            onChange={(v) => onUpdate(planKey, "access_exam_prep", v)}
          />
          <Toggle
            label="📖 Exemplar Access"
            desc="Exemplar Research & Lessons"
            checked={plan.access_exemplar !== false}
            onChange={(v) => onUpdate(planKey, "access_exemplar", v)}
          />

          <div style={{ marginTop: 12, marginBottom: 8, fontSize: ".58rem", fontWeight: 700, color: "var(--muted,#64748b)", textTransform: "uppercase", letterSpacing: ".04em" }}>
            Comparison Table Values
          </div>
          {[
            ["children", "Child Profiles"],
            ["aiUsage", "AI Usage"],
            ["cbse", "CBSE Access"],
            ["parentDashboard", "Parent Dashboard"],
          ].map(([field, label]) => (
            <Field key={field} label={label}>
              <input
                style={S.inp}
                value={plan.comparison?.[field] || ""}
                onChange={(e) => onUpdateComparison(planKey, field, e.target.value)}
              />
            </Field>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function AdminSubscriptionSettingsPage({ user }) {
  const [plans, setPlans] = useState(SUBSCRIPTION_PLANS);
  const [planOrder, setPlanOrder] = useState(SUBSCRIPTION_PLAN_ORDER);
  const [contact, setContact] = useState(DEFAULT_CONTACT);
  const [settingsSource, setSettingsSource] = useState("defaults");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savingContact, setSavingContact] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [editingPlan, setEditingPlan] = useState(null); // which plan's side panel is open

  useEffect(() => {
    async function load() {
      try {
        const [result, contactResult] = await Promise.all([
          getAdminSubscriptionPlans(user.accessToken),
          getAdminSubscriptionContact(user.accessToken).catch(() => ({ contact: DEFAULT_CONTACT })),
        ]);
        setPlans(mergeSubscriptionPlans(result.plans || {}));
        setPlanOrder(result.plan_order?.length ? result.plan_order : SUBSCRIPTION_PLAN_ORDER);
        setContact({ ...DEFAULT_CONTACT, ...(contactResult.contact || {}) });
        setSettingsSource(result.source || (result.persisted ? "database" : "defaults"));
      } catch (err) {
        console.error(err);
        setError("Unable to load subscription plan settings. Showing defaults.");
      } finally {
        setLoading(false);
      }
    }
    if (user?.accessToken) load();
  }, [user?.accessToken]);

  function updatePlan(planKey, field, value) {
    setPlans((prev) => ({ ...prev, [planKey]: { ...prev[planKey], [field]: value } }));
  }

  function updateComparison(planKey, field, value) {
    setPlans((prev) => ({
      ...prev,
      [planKey]: { ...prev[planKey], comparison: { ...(prev[planKey].comparison || {}), [field]: value } },
    }));
  }

  function updateContact(field, value) {
    setContact((prev) => ({ ...prev, [field]: value }));
  }

  async function savePlans() {
    setSaving(true); setMessage(""); setError("");
    try {
      const result = await updateAdminSubscriptionPlans(
        { plans: planOrder.map((k, i) => serializeSubscriptionPlan({ ...plans[k], displayOrder: i + 1 })) },
        user.accessToken
      );
      const loaded = mergeSubscriptionPlans(result.plans || {});
      const order = result.plan_order?.length ? result.plan_order : planOrder;
      setPlans((cur) => order.reduce((acc, k) => {
        const d = plans[k] || cur[k]; const l = loaded[k] || d;
        const hasDisc = Number(l?.discountPercent || 0) > 0 || (l?.discountLabel || "").trim();
        acc[k] = { ...l, ...d, ...(hasDisc ? { discountPercent: l.discountPercent, discountLabel: l.discountLabel } : { discountPercent: d.discountPercent, discountLabel: d.discountLabel }) };
        return acc;
      }, {}));
      setPlanOrder(order);
      setSettingsSource(result.source || (result.persisted ? "database" : "saved"));
      if (result.persisted === false || result.load_error) { setError("Saved, but Supabase could not confirm. Pages may show stale prices."); return; }
      setMessage("Subscription plan settings saved and applied.");
    } catch (err) {
      const msg = err?.message ? (typeof err.message === "string" ? err.message : JSON.stringify(err.message)) : "Unable to save.";
      setError(msg);
    } finally { setSaving(false); }
  }

  async function saveContact() {
    setSavingContact(true); setMessage(""); setError("");
    try {
      const result = await updateAdminSubscriptionContact(contact, user.accessToken);
      setContact({ ...DEFAULT_CONTACT, ...(result.contact || {}) });
      if (result.persisted === false || result.load_error) { setError("Contact saved, but Supabase could not confirm."); return; }
      setMessage("Contact details saved.");
    } catch (err) { setError(err.message || "Unable to save contact."); }
    finally { setSavingContact(false); }
  }

  if (loading) return <div className="premium-page"><section className="premium-section"><p style={{ color: "var(--muted,#64748b)" }}>Loading subscription settings…</p></section></div>;

  const PLAN_LABELS = { free: "Nano", starter: "Premium", family_premium: "Family Premium", standard_6month: "6-Month", standard_annual: "Annual", family_annual: "Family Annual", free_tier: "Free Tier", premium: "Premium (hidden)" };

  return (
    <div className="premium-page">
      <section className="premium-section" style={{ paddingBottom: 0 }}>

        {/* Page header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16, flexWrap: "wrap", gap: 10 }}>
          <div>
            <h2 style={{ fontSize: "1.2rem", fontWeight: 800, margin: 0 }}>⚙️ Subscription Settings</h2>
            <p style={{ color: "var(--muted,#64748b)", fontSize: ".78rem", marginTop: 3 }}>
              Manage pricing, validity, features and content for all tiers.
            </p>
            <span style={{ display: "inline-flex", background: "rgba(34,197,94,.1)", border: "1px solid rgba(34,197,94,.25)", color: "#4ade80", padding: "2px 9px", borderRadius: 20, fontSize: ".6rem", fontWeight: 700, marginTop: 5 }}>
              ✅ Source: {settingsSource}
            </span>
          </div>
          <button
            onClick={savePlans}
            disabled={saving}
            style={{ padding: "10px 22px", background: saving ? "#334155" : "linear-gradient(135deg,#6366f1,#8b5cf6)", border: "none", borderRadius: 9, color: "#fff", fontWeight: 700, fontSize: ".85rem", cursor: saving ? "not-allowed" : "pointer", fontFamily: "inherit", display: "flex", alignItems: "center", gap: 7 }}
          >
            <Save size={15} />
            {saving ? "Saving…" : "Save All Plans"}
          </button>
        </div>

        {message && <div className="info-box" style={{ marginBottom: 10 }}>{message}</div>}
        {error && <div className="error-box" style={{ marginBottom: 10 }}>{error}</div>}

        {/* Contact bar */}
        <div style={{ background: "var(--panel,#1e293b)", border: "1px solid var(--border,#334155)", borderRadius: 10, padding: "10px 16px", marginBottom: 14, display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
          <span style={{ fontSize: ".65rem", fontWeight: 700, color: "var(--muted,#64748b)", textTransform: "uppercase", letterSpacing: ".05em", whiteSpace: "nowrap" }}>💬 Support Contact</span>
          <input style={{ ...S.inp, flex: 1, minWidth: 170 }} value={contact.email} placeholder="Email" onChange={(e) => updateContact("email", e.target.value)} />
          <input style={{ ...S.inp, flex: 1, minWidth: 130 }} value={contact.whatsapp} placeholder="WhatsApp" onChange={(e) => updateContact("whatsapp", e.target.value)} />
          <input style={{ ...S.inp, flex: 1, minWidth: 120 }} value={contact.phone} placeholder="Phone" onChange={(e) => updateContact("phone", e.target.value)} />
          <button
            onClick={saveContact}
            disabled={savingContact}
            style={{ padding: "5px 13px", border: "1px solid rgba(99,102,241,.3)", background: "rgba(99,102,241,.1)", borderRadius: 6, color: "#a5b4fc", fontSize: ".71rem", fontWeight: 700, cursor: "pointer", fontFamily: "inherit", whiteSpace: "nowrap" }}
          >
            {savingContact ? "Saving…" : "Save"}
          </button>
        </div>

        {/* Plans overview table */}
        <div style={{ background: "var(--panel,#1e293b)", border: "1px solid var(--border,#334155)", borderRadius: 12, overflow: "hidden", marginBottom: editingPlan ? 0 : 0 }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ background: "var(--surface2,#0f172a)" }}>
                {["Plan", "Price", "Discount", "Duration", "Exam Prep", "Exemplar", "Visible", ""].map((h) => (
                  <th key={h} style={{ padding: "9px 14px", fontSize: ".58rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: ".05em", color: "var(--muted,#64748b)", textAlign: "left", borderBottom: "1px solid var(--border,#334155)" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {planOrder.map((planKey) => {
                const plan = plans[planKey];
                if (!plan) return null;
                const charge = getPlanDisplayPrice(plan);
                const isEditing = editingPlan === planKey;
                return (
                  <tr
                    key={planKey}
                    style={{ background: isEditing ? "rgba(99,102,241,.06)" : "transparent", borderBottom: "1px solid var(--border,#334155)", cursor: "pointer" }}
                    onClick={() => setEditingPlan(isEditing ? null : planKey)}
                  >
                    <td style={{ padding: "11px 14px" }}>
                      <div style={{ fontWeight: 700, fontSize: ".82rem" }}>{PLAN_LABELS[planKey] || plan.label}</div>
                      <div style={{ fontSize: ".62rem", color: "var(--muted,#64748b)", marginTop: 1 }}>{planKey}</div>
                    </td>
                    <td style={{ padding: "11px 14px", fontWeight: 700, color: "#a5b4fc" }}>{formatPlanPrice(charge)}</td>
                    <td style={{ padding: "11px 14px", fontSize: ".78rem", color: "var(--muted,#64748b)" }}>
                      {plan.discountPercent > 0 ? (
                        <span style={{ color: "#4ade80", fontWeight: 700 }}>{plan.discountPercent}% off</span>
                      ) : "—"}
                    </td>
                    <td style={{ padding: "11px 14px", fontSize: ".78rem" }}>
                      {plan.duration_days ? `${plan.duration_days}d` : plan.billingLabel || "—"}
                    </td>
                    <td style={{ padding: "11px 14px" }}>
                      <span style={{ fontSize: ".65rem", fontWeight: 700, padding: "2px 8px", borderRadius: 20, background: plan.access_exam_prep !== false ? "rgba(34,197,94,.1)" : "rgba(239,68,68,.1)", color: plan.access_exam_prep !== false ? "#4ade80" : "#f87171" }}>
                        {plan.access_exam_prep !== false ? "✅ ON" : "❌ OFF"}
                      </span>
                    </td>
                    <td style={{ padding: "11px 14px" }}>
                      <span style={{ fontSize: ".65rem", fontWeight: 700, padding: "2px 8px", borderRadius: 20, background: plan.access_exemplar !== false ? "rgba(34,197,94,.1)" : "rgba(239,68,68,.1)", color: plan.access_exemplar !== false ? "#4ade80" : "#f87171" }}>
                        {plan.access_exemplar !== false ? "✅ ON" : "❌ OFF"}
                      </span>
                    </td>
                    <td style={{ padding: "11px 14px" }}>
                      <span style={{ fontSize: ".65rem", fontWeight: 700, padding: "2px 8px", borderRadius: 20, background: plan.isPublic !== false ? "rgba(34,197,94,.1)" : "rgba(100,116,139,.1)", color: plan.isPublic !== false ? "#4ade80" : "#94a3b8" }}>
                        {plan.isPublic !== false ? "✅ Yes" : "👁 Hidden"}
                      </span>
                    </td>
                    <td style={{ padding: "11px 14px", textAlign: "right" }}>
                      <button
                        onClick={(e) => { e.stopPropagation(); setEditingPlan(isEditing ? null : planKey); }}
                        style={{ padding: "5px 13px", background: isEditing ? "rgba(99,102,241,.25)" : "rgba(99,102,241,.1)", border: `1px solid ${isEditing ? "#6366f1" : "rgba(99,102,241,.25)"}`, borderRadius: 6, color: "#a5b4fc", fontSize: ".68rem", fontWeight: 700, cursor: "pointer", fontFamily: "inherit" }}
                      >
                        {isEditing ? "Close ✕" : "Edit ✏"}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Inline edit panel — appears below the row */}
        {editingPlan && plans[editingPlan] && (
          <div style={{ marginTop: 8 }}>
            <PlanEditPanel
              planKey={editingPlan}
              plan={plans[editingPlan]}
              onUpdate={updatePlan}
              onUpdateComparison={updateComparison}
            />
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 8 }}>
              <button
                onClick={() => setEditingPlan(null)}
                style={{ padding: "7px 16px", background: "var(--surface2,#0f172a)", border: "1px solid var(--border,#334155)", borderRadius: 7, color: "var(--muted,#94a3b8)", fontWeight: 600, fontSize: ".78rem", cursor: "pointer", fontFamily: "inherit" }}
              >
                Close Panel
              </button>
              <button
                onClick={savePlans}
                disabled={saving}
                style={{ padding: "7px 18px", background: "linear-gradient(135deg,#6366f1,#8b5cf6)", border: "none", borderRadius: 7, color: "#fff", fontWeight: 700, fontSize: ".78rem", cursor: "pointer", fontFamily: "inherit", display: "flex", alignItems: "center", gap: 6 }}
              >
                <Save size={13} />
                {saving ? "Saving…" : "Save All Plans"}
              </button>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
