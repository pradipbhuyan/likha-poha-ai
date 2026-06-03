import { useEffect, useState } from "react";
import { Percent, Save, Tags } from "lucide-react";

import {
  getAdminSubscriptionPlans,
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

function listToText(items = []) {
  /** Convert stored feature arrays into newline text for admin editing. */
  return items.join("\n");
}

function textToList(value) {
  /** Convert textarea content back into clean feature arrays for saving. */
  return String(value || "")
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
}

function AdminSubscriptionSettingsPage({ user }) {
  /** Admin page for editing public plan pricing, discounts, access, and feature copy. */
  const [plans, setPlans] = useState(SUBSCRIPTION_PLANS);
  const [planOrder, setPlanOrder] = useState(SUBSCRIPTION_PLAN_ORDER);
  const [settingsSource, setSettingsSource] = useState("defaults");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadPlans() {
      /** Load persisted plan settings and merge them with local defaults for missing fields. */
      try {
        const result = await getAdminSubscriptionPlans(user.accessToken);
        const loadedPlans = mergeSubscriptionPlans(result.plans || {});

        setPlans(loadedPlans);
        setPlanOrder(result.plan_order?.length ? result.plan_order : SUBSCRIPTION_PLAN_ORDER);
        setSettingsSource(result.source || (result.persisted ? "database" : "defaults"));
      } catch (err) {
        console.error(err);
        setError("Unable to load subscription plan settings. Showing defaults.");
      } finally {
        setLoading(false);
      }
    }

    if (user?.accessToken) {
      loadPlans();
    }
  }, [user?.accessToken]);

  function updatePlan(planKey, field, value) {
    /** Update one editable field on one subscription plan draft. */
    setPlans((prev) => ({
      ...prev,
      [planKey]: {
        ...prev[planKey],
        [field]: value,
      },
    }));
  }

  function updateComparison(planKey, field, value) {
    /** Update one comparison-table value while preserving the rest of the plan metadata. */
    setPlans((prev) => ({
      ...prev,
      [planKey]: {
        ...prev[planKey],
        comparison: {
          ...(prev[planKey].comparison || {}),
          [field]: value,
        },
      },
    }));
  }

  async function savePlans() {
    /** Persist all plan settings and reconcile the UI with the saved response. */
    setSaving(true);
    setMessage("");
    setError("");

    try {
      const draftPlans = plans;
      const draftPlanOrder = planOrder;
      const result = await updateAdminSubscriptionPlans(
        {
          plans: draftPlanOrder.map((planKey, index) =>
            serializeSubscriptionPlan({
              ...draftPlans[planKey],
              displayOrder: index + 1,
            })
          ),
        },
        user.accessToken
      );

      const loadedPlans = mergeSubscriptionPlans(result.plans || {});
      const loadedPlanOrder = result.plan_order?.length
        ? result.plan_order
        : draftPlanOrder;

      setPlans((currentPlans) => {
        /** Keep optimistic discount edits if the backend response falls back to stale defaults. */
        return loadedPlanOrder.reduce((nextPlans, planKey) => {
          const draftPlan =
            draftPlans[planKey] || currentPlans[planKey] || SUBSCRIPTION_PLANS[planKey];
          const loadedPlan = loadedPlans[planKey] || draftPlan;
          const loadedHasDiscount =
            Number(loadedPlan?.discountPercent || 0) > 0 ||
            (loadedPlan?.discountLabel || "").trim();

          nextPlans[planKey] = {
            ...loadedPlan,
            ...draftPlan,
            ...(loadedHasDiscount
              ? {
                  discountPercent: loadedPlan.discountPercent,
                  discountLabel: loadedPlan.discountLabel,
                }
              : {
                  discountPercent: draftPlan.discountPercent,
                  discountLabel: draftPlan.discountLabel,
                }),
          };

          return nextPlans;
        }, {});
      });
      setPlanOrder(loadedPlanOrder);
      setSettingsSource(result.source || (result.persisted ? "database" : "saved"));

      if (result.persisted === false || result.load_error) {
        setError(
          "Saved locally, but Supabase settings could not be confirmed. Parent pages may still show default prices."
        );
        return;
      }

      setMessage("Subscription plan settings saved and applied.");
    } catch (err) {
      console.error(err);
      setError(err.message || "Unable to save subscription plan settings.");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return <p>Loading subscription settings...</p>;
  }

  return (
    <div className="premium-page admin-subscription-page">
      <section className="premium-section">
        <div className="premium-header">
          <p className="eyebrow">Admin Pricing</p>
          <h2>Subscription Settings</h2>
          <p>
            Change plan prices, discount labels, public visibility, and the
            feature lists parents see on the Subscription page.
          </p>
          <small className="admin-settings-source">
            Settings source: {settingsSource}
          </small>
        </div>
      </section>

      {message && <div className="info-box">{message}</div>}
      {error && <div className="error-box">{error}</div>}

      <section className="admin-plan-grid">
        {planOrder.map((planKey) => {
          const plan = plans[planKey];
          const displayPrice = getPlanDisplayPrice(plan);

          return (
            <article key={plan.key} className="premium-section admin-plan-card">
              <div className="admin-plan-card-head">
                <div>
                  <h3>{plan.label}</h3>
                  <p>{plan.key}</p>
                </div>

                <span className="admin-plan-price-preview">
                  {formatPlanPrice(displayPrice)}
                </span>
              </div>

              <div className="form-grid premium-rag-form-grid">
                <label>
                  Plan Label
                  <input
                    value={plan.label}
                    onChange={(e) => updatePlan(planKey, "label", e.target.value)}
                  />
                </label>

                <label>
                  Short Label
                  <input
                    value={plan.shortLabel}
                    onChange={(e) =>
                      updatePlan(planKey, "shortLabel", e.target.value)
                    }
                  />
                </label>

                <label>
                  Price
                  <input
                    type="number"
                    min="0"
                    value={plan.price}
                    onChange={(e) =>
                      updatePlan(planKey, "price", Number(e.target.value || 0))
                    }
                  />
                </label>

                <label>
                  Billing Label
                  <input
                    value={plan.billingLabel}
                    onChange={(e) =>
                      updatePlan(planKey, "billingLabel", e.target.value)
                    }
                  />
                </label>

                <label>
                  Discount %
                  <input
                    type="number"
                    min="0"
                    max="100"
                    value={plan.discountPercent}
                    onChange={(e) =>
                      updatePlan(
                        planKey,
                        "discountPercent",
                        Number(e.target.value || 0)
                      )
                    }
                  />
                </label>

                <label>
                  Discount Label
                  <input
                    value={plan.discountLabel}
                    placeholder="Summer offer"
                    onChange={(e) =>
                      updatePlan(planKey, "discountLabel", e.target.value)
                    }
                  />
                </label>

                <label>
                  Badge
                  <input
                    value={plan.badge}
                    placeholder="Recommended"
                    onChange={(e) => updatePlan(planKey, "badge", e.target.value)}
                  />
                </label>

                <label>
                  Daily Tokens
                  <input
                    type="number"
                    min="0"
                    value={plan.daily_token_limit}
                    onChange={(e) =>
                      updatePlan(
                        planKey,
                        "daily_token_limit",
                        Number(e.target.value || 0)
                      )
                    }
                  />
                </label>

                <label>
                  Monthly Tokens
                  <input
                    type="number"
                    min="0"
                    value={plan.monthly_token_limit}
                    onChange={(e) =>
                      updatePlan(
                        planKey,
                        "monthly_token_limit",
                        Number(e.target.value || 0)
                      )
                    }
                  />
                </label>
              </div>

              <label className="admin-plan-full-label">
                Parent-Facing Description
                <textarea
                  rows={3}
                  value={plan.audience}
                  onChange={(e) => updatePlan(planKey, "audience", e.target.value)}
                />
              </label>

              <div className="admin-plan-toggle-row">
                <label>
                  <input
                    type="checkbox"
                    checked={plan.isPublic !== false}
                    onChange={(e) =>
                      updatePlan(planKey, "isPublic", e.target.checked)
                    }
                  />{" "}
                  Show to parents
                </label>

                <label>
                  <input
                    type="checkbox"
                    checked={!!plan.recommended}
                    onChange={(e) =>
                      updatePlan(planKey, "recommended", e.target.checked)
                    }
                  />{" "}
                  Recommended
                </label>
              </div>

              <div className="admin-plan-list-grid">
                <label>
                  Included Features
                  <textarea
                    rows={6}
                    value={listToText(plan.included)}
                    onChange={(e) =>
                      updatePlan(planKey, "included", textToList(e.target.value))
                    }
                  />
                </label>

                <label>
                  Not Included Features
                  <textarea
                    rows={6}
                    value={listToText(plan.notIncluded)}
                    onChange={(e) =>
                      updatePlan(planKey, "notIncluded", textToList(e.target.value))
                    }
                  />
                </label>
              </div>

              <div className="admin-plan-comparison-grid">
                {[
                  ["children", "Child profiles"],
                  ["aiUsage", "AI usage"],
                  ["cbse", "CBSE"],
                  ["sof", "SOF"],
                  ["ragSof", "RAG SOF"],
                  ["parentDashboard", "Parent dashboard"],
                ].map(([field, label]) => (
                  <label key={field}>
                    {label}
                    <input
                      value={plan.comparison?.[field] || ""}
                      onChange={(e) =>
                        updateComparison(planKey, field, e.target.value)
                      }
                    />
                  </label>
                ))}
              </div>
            </article>
          );
        })}
      </section>

      <div className="admin-subscription-save-bar">
        <div>
          <strong>
            <Tags size={18} strokeWidth={2.5} /> Plan settings
          </strong>
          <span>
            <Percent size={16} strokeWidth={2.5} /> Discounts update parent
            pricing after save.
          </span>
        </div>

        <button className="primary-btn" onClick={savePlans} disabled={saving}>
          <Save size={18} strokeWidth={2.5} />
          {saving ? "Saving..." : "Save Subscription Settings"}
        </button>
      </div>
    </div>
  );
}

export default AdminSubscriptionSettingsPage;
