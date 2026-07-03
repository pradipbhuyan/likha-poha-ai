import { useEffect, useMemo, useState } from "react";
import { BadgeIndianRupee, Handshake, TrendingUp, Users } from "lucide-react";

import {
  createSalesAttribution,
  createSalesPerson,
  getSalesSummary,
} from "../api/sales";
import {
  SUBSCRIPTION_PLAN_ORDER,
  SUBSCRIPTION_PLANS,
  getPlanDisplayPrice,
} from "../config/subscriptionPlans";


function formatRupees(value) {
  /** Format sales and incentive amounts in INR for compact dashboard cards. */
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(Number(value || 0));
}


function planOptions() {
  /** Build selectable packages from the current subscription defaults. */
  return SUBSCRIPTION_PLAN_ORDER.map((key) => {
    const plan = SUBSCRIPTION_PLANS[key];
    return {
      key,
      label: plan.label,
      amount: getPlanDisplayPrice(plan),
    };
  });
}


const PACKAGE_OPTIONS = planOptions();


function SalesIncentivePage({ user }) {
  /** Admin/sales workspace for onboarding sales users and tracking incentives. */
  const isAdmin = user?.role === "admin";
  const [summary, setSummary] = useState({});
  const [salesPeople, setSalesPeople] = useState([]);
  const [students, setStudents] = useState([]);
  const [attributions, setAttributions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [salesForm, setSalesForm] = useState({
    username: "",
    email: "",
    password: "",
    salesperson_type: "independent",
    region: "",
    phone: "",
    status: "active",
    default_incentive_percent: 5,
  });
  const [attributionForm, setAttributionForm] = useState({
    sales_profile_id: "",
    student_id: "",
    package_key: "starter",
    package_label: "Premium",
    package_amount: 499,
    incentive_percent: 5,
    status: "pending",
    notes: "",
  });

  async function loadSalesData() {
    /** Refresh sales dashboard and assignment data from the backend. */
    setLoading(true);
    setError("");

    try {
      const data = await getSalesSummary();
      setSummary(data.summary || {});
      setSalesPeople(data.sales_people || []);
      setStudents(data.students || []);
      setAttributions(data.attributions || []);

      setAttributionForm((current) => ({
        ...current,
        sales_profile_id:
          current.sales_profile_id || data.sales_people?.[0]?.id || "",
        student_id: current.student_id || data.students?.[0]?.id || "",
      }));
    } catch (err) {
      console.error(err);
      setError(err.message || "Unable to load sales incentives.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadSalesData();
  }, []);

  const salespersonById = useMemo(
    () => Object.fromEntries(salesPeople.map((person) => [person.id, person])),
    [salesPeople]
  );
  const studentById = useMemo(
    () => Object.fromEntries(students.map((student) => [student.id, student])),
    [students]
  );

  function updateSalesForm(field, value) {
    /** Update one salesperson onboarding field. */
    setSalesForm((prev) => ({
      ...prev,
      [field]: value,
    }));
  }

  function updateAttributionForm(field, value) {
    /** Update one attribution field and sync package amount for known plans. */
    setAttributionForm((prev) => {
      if (field === "package_key") {
        const plan = PACKAGE_OPTIONS.find((item) => item.key === value);

        return {
          ...prev,
          package_key: value,
          package_label: plan?.label || value,
          package_amount: plan?.amount ?? prev.package_amount,
        };
      }

      return {
        ...prev,
        [field]: value,
      };
    });
  }

  async function handleCreateSalesPerson(e) {
    /** Submit the admin-only salesperson onboarding form. */
    e.preventDefault();
    setSaving(true);
    setMessage("");
    setError("");

    try {
      await createSalesPerson({
        ...salesForm,
        default_incentive_percent: Number(
          salesForm.default_incentive_percent || 5
        ),
      });
      setSalesForm({
        username: "",
        email: "",
        password: "",
        salesperson_type: "independent",
        region: "",
        phone: "",
        status: "active",
        default_incentive_percent: 5,
      });
      await loadSalesData();
      setMessage("Salesperson created.");
    } catch (err) {
      console.error(err);
      setError(err.message || "Unable to create salesperson.");
    } finally {
      setSaving(false);
    }
  }

  async function handleCreateAttribution(e) {
    /** Submit the admin-only student/package attribution form. */
    e.preventDefault();
    setSaving(true);
    setMessage("");
    setError("");

    try {
      await createSalesAttribution({
        ...attributionForm,
        package_amount: Number(attributionForm.package_amount || 0),
        incentive_percent: Number(attributionForm.incentive_percent || 5),
      });
      await loadSalesData();
      setMessage("Student sale tracked.");
    } catch (err) {
      console.error(err);
      setError(err.message || "Unable to save student sale.");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return <p>Loading sales incentives...</p>;
  }

  return (
    <div className="premium-page sales-incentive-page">
      <section className="premium-section sales-hero-section">
        <div className="premium-header">
          <p className="eyebrow">Sales Incentives</p>
          <h2>🤝 Sales Partner Center</h2>
          <p>
            Create salesperson logins, track student package onboarding, and
            calculate 5-10% incentives without mixing sales records into family
            administration.
          </p>
        </div>
      </section>

      {message && <div className="info-box">{message}</div>}
      {error && <div className="error-box">{error}</div>}

      <section className="premium-grid premium-grid-4 premium-parent-stats">
        <div className="premium-card">
          <div className="dashboard-stat-icon blue">
            <Users size={22} />
          </div>
          <h3>{summary.sales_people || salesPeople.length}</h3>
          <p>Salespeople</p>
        </div>

        <div className="premium-card">
          <div className="dashboard-stat-icon green">
            <Handshake size={22} />
          </div>
          <h3>{summary.tracked_students || attributions.length}</h3>
          <p>Tracked Students</p>
        </div>

        <div className="premium-card">
          <div className="dashboard-stat-icon purple">
            <TrendingUp size={22} />
          </div>
          <h3>{formatRupees(summary.total_revenue)}</h3>
          <p>Tracked Revenue</p>
        </div>

        <div className="premium-card">
          <div className="dashboard-stat-icon red">
            <BadgeIndianRupee size={22} />
          </div>
          <h3>{formatRupees(summary.incentive_payable)}</h3>
          <p>Incentive Payable</p>
        </div>
      </section>

      {isAdmin && (
        <section className="premium-section sales-admin-grid">
          <form className="sales-form-card" onSubmit={handleCreateSalesPerson}>
            <div className="premium-header">
              <h3>Onboard Salesperson</h3>
              <p>Create the login they will use to view only their own sales.</p>
            </div>

            <div className="sales-form-grid">
              <label>
                Name
                <input
                  value={salesForm.username}
                  onChange={(e) => updateSalesForm("username", e.target.value)}
                  required
                />
              </label>
              <label>
                Email
                <input
                  type="email"
                  value={salesForm.email}
                  onChange={(e) => updateSalesForm("email", e.target.value)}
                  required
                />
              </label>
              <label>
                Temporary Password
                <input
                  type="password"
                  value={salesForm.password}
                  onChange={(e) => updateSalesForm("password", e.target.value)}
                  required
                />
              </label>
              <label>
                Type
                <select
                  value={salesForm.salesperson_type}
                  onChange={(e) =>
                    updateSalesForm("salesperson_type", e.target.value)
                  }
                >
                  <option value="independent">Independent</option>
                  <option value="school">School Channel</option>
                  <option value="partner">Partner</option>
                </select>
              </label>
              <label>
                Region
                <input
                  value={salesForm.region}
                  onChange={(e) => updateSalesForm("region", e.target.value)}
                  placeholder="Guwahati, Assam"
                />
              </label>
              <label>
                Default Incentive %
                <input
                  type="number"
                  min="5"
                  max="10"
                  step="0.5"
                  value={salesForm.default_incentive_percent}
                  onChange={(e) =>
                    updateSalesForm("default_incentive_percent", e.target.value)
                  }
                />
              </label>
            </div>

            <button className="primary-btn" type="submit" disabled={saving}>
              Create Salesperson
            </button>
          </form>

          <form className="sales-form-card" onSubmit={handleCreateAttribution}>
            <div className="premium-header">
              <h3>Track Student Sale</h3>
              <p>Attach a student and package to a salesperson incentive.</p>
            </div>

            <div className="sales-form-grid">
              <label>
                Salesperson
                <select
                  value={attributionForm.sales_profile_id}
                  onChange={(e) =>
                    updateAttributionForm("sales_profile_id", e.target.value)
                  }
                  required
                >
                  <option value="">Select salesperson</option>
                  {salesPeople.map((person) => (
                    <option key={person.id} value={person.id}>
                      {person.username}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Student
                <select
                  value={attributionForm.student_id}
                  onChange={(e) =>
                    updateAttributionForm("student_id", e.target.value)
                  }
                  required
                >
                  <option value="">Select student</option>
                  {students.map((student) => (
                    <option key={student.id} value={student.id}>
                      {student.username} - {student.grade || "Grade not set"}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Package
                <select
                  value={attributionForm.package_key}
                  onChange={(e) =>
                    updateAttributionForm("package_key", e.target.value)
                  }
                >
                  {PACKAGE_OPTIONS.map((plan) => (
                    <option key={plan.key} value={plan.key}>
                      {plan.label}
                    </option>
                  ))}
                  <option value="custom">Custom Package</option>
                </select>
              </label>
              <label>
                Package Amount
                <input
                  type="number"
                  min="0"
                  value={attributionForm.package_amount}
                  onChange={(e) =>
                    updateAttributionForm("package_amount", e.target.value)
                  }
                />
              </label>
              <label>
                Incentive %
                <input
                  type="number"
                  min="5"
                  max="10"
                  step="0.5"
                  value={attributionForm.incentive_percent}
                  onChange={(e) =>
                    updateAttributionForm("incentive_percent", e.target.value)
                  }
                />
              </label>
              <label>
                Status
                <select
                  value={attributionForm.status}
                  onChange={(e) => updateAttributionForm("status", e.target.value)}
                >
                  <option value="pending">Pending</option>
                  <option value="active">Active</option>
                  <option value="paid">Paid</option>
                  <option value="cancelled">Cancelled</option>
                </select>
              </label>
            </div>

            <label>
              Notes
              <textarea
                value={attributionForm.notes}
                onChange={(e) => updateAttributionForm("notes", e.target.value)}
                placeholder="Lead source, payment note, school contact, etc."
              />
            </label>

            <button className="primary-btn" type="submit" disabled={saving}>
              Save Student Sale
            </button>
          </form>
        </section>
      )}

      <section className="premium-section">
        <div className="premium-header">
          <h3>{isAdmin ? "Sales Attribution Ledger" : "My Sales Ledger"}</h3>
          <p>
            Each row stores the package amount and commission percent used for
            the incentive calculation.
          </p>
        </div>

        <div className="sales-ledger-table">
          <div className="sales-ledger-row sales-ledger-head">
            <span>Salesperson</span>
            <span>Student</span>
            <span>Package</span>
            <span>Amount</span>
            <span>Incentive</span>
            <span>Status</span>
          </div>

          {attributions.length === 0 && (
            <div className="sales-empty-state">
              No student sales tracked yet.
            </div>
          )}

          {attributions.map((item) => {
            const salesperson =
              item.salesperson?.username ||
              salespersonById[item.sales_profile_id]?.username ||
              "Salesperson";
            const student =
              item.student?.username ||
              studentById[item.student_id]?.username ||
              "Student";

            return (
              <div key={item.id || `${item.sales_profile_id}-${item.student_id}`} className="sales-ledger-row">
                <span>{salesperson}</span>
                <span>{student}</span>
                <span>{item.package_label}</span>
                <span>{formatRupees(item.package_amount)}</span>
                <span>
                  {item.incentive_percent}% · {formatRupees(item.incentive_amount)}
                </span>
                <span className={`sales-status-pill ${item.status || "pending"}`}>
                  {item.status || "pending"}
                </span>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}

export default SalesIncentivePage;
