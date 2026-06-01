import { useEffect, useState } from "react";
import {
  getAdminFamilies,
  createAdminParent,
  createAdminChild,
  updateChildAccess,
  updateChildLimits,
  deleteUser,
} from "../api/adminControl";

const PLAN_PRESETS = {
    free: {
      label: "Free",
      access_cbse: true,
      access_sof_science: false,
      access_sof_maths: false,
      access_sof_english: false,
      daily_token_limit: 50000,
      monthly_token_limit: 1000000,
    },
    starter: {
      label: "Starter",
      access_cbse: true,
      access_sof_science: false,
      access_sof_maths: false,
      access_sof_english: false,
      daily_token_limit: 75000,
      monthly_token_limit: 1500000,
    },
    premium: {
      label: "Premium",
      access_cbse: true,
      access_sof_science: true,
      access_sof_maths: true,
      access_sof_english: true,
      daily_token_limit: 100000,
      monthly_token_limit: 3000000,
    },
    family_premium: {
      label: "Family Premium",
      access_cbse: true,
      access_sof_science: true,
      access_sof_maths: true,
      access_sof_english: true,
      daily_token_limit: 150000,
      monthly_token_limit: 5000000,
    },
  };

function AdminControlPage({ user }) {
  const [families, setFamilies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const [parentForm, setParentForm] = useState({
    email: "",
    password: "",
    username: "",
  });

  const [childForms, setChildForms] = useState({});

  async function loadFamilies() {
    try {
      const data = await getAdminFamilies(user.accessToken);
      setFamilies(data.families || []);
    } catch (err) {
      console.error(err);
      setError("Unable to load admin control data.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (user?.accessToken) {
      loadFamilies();
    }
  }, [user?.accessToken]);

  async function handleCreateParent(e) {
    e.preventDefault();
    setMessage("");
    setError("");

    try {
      await createAdminParent(parentForm, user.accessToken);

      setParentForm({
        email: "",
        password: "",
        username: "",
      });

      await loadFamilies();
      setMessage("Parent created successfully.");
    } catch (err) {
      console.error(err);
      setError(err.message || "Unable to create parent.");
    }
  }

  async function handleCreateChild(e, familyId, parentId) {
    e.preventDefault();
    setMessage("");
    setError("");

    const form = childForms[parentId] || {
      email: "",
      password: "",
      username: "",
    };

    try {
      await createAdminChild(
        {
          ...form,
          parent_id: parentId,
          family_id: familyId,
        },
        user.accessToken
      );

      setChildForms((prev) => ({
        ...prev,
        [parentId]: {
          email: "",
          password: "",
          username: "",
        },
      }));

      await loadFamilies();
      setMessage("Child created successfully.");
    } catch (err) {
      console.error(err);
      setError(err.message || "Unable to create child.");
    }
  }

  async function saveAccess(child) {
    setMessage("");
    setError("");

    try {
      await updateChildAccess(
        child.id,
        {
          access_cbse: !!child.access_cbse,
          access_sof_science: !!child.access_sof_science,
          access_sof_maths: !!child.access_sof_maths,
          access_sof_english: !!child.access_sof_english,
          subscription_plan: child.subscription_plan || "free",
          account_status: child.account_status || "active",
        },
        user.accessToken
      );

      await loadFamilies();
      setMessage(`Access saved for ${child.username}.`);
    } catch (err) {
      console.error(err);
      setError("Unable to save access.");
    }
  }

  async function suspendChild(child) {
    const updatedChild = {
      ...child,
      account_status: "suspended",
    };
  
    await savePlan(updatedChild);
  }
  
  async function reactivateChild(child) {
    const updatedChild = {
      ...child,
      account_status: "active",
    };
  
    await savePlan(updatedChild);
  }

  async function savePlan(child) {
    setMessage("");
    setError("");
  
    try {
      await updateChildAccess(
        child.id,
        {
          access_cbse: !!child.access_cbse,
          access_sof_science: !!child.access_sof_science,
          access_sof_maths: !!child.access_sof_maths,
          access_sof_english: !!child.access_sof_english,
          subscription_plan: child.subscription_plan || "free",
          account_status: child.account_status || "active",
        },
        user.accessToken
      );
  
      await updateChildLimits(
        child.id,
        {
          daily_token_limit: Number(child.daily_token_limit || 0),
          monthly_token_limit: Number(child.monthly_token_limit || 0),
        },
        user.accessToken
      );
  
      await loadFamilies();
      setMessage(`Plan saved for ${child.username}.`);
    } catch (err) {
      console.error(err);
      setError("Unable to save plan.");
    }
  }

  async function saveLimits(child) {
    setMessage("");
    setError("");

    try {
      await updateChildLimits(
        child.id,
        {
          daily_token_limit: Number(child.daily_token_limit || 0),
          monthly_token_limit: Number(child.monthly_token_limit || 0),
        },
        user.accessToken
      );

      await loadFamilies();
      setMessage(`Limits saved for ${child.username}.`);
    } catch (err) {
      console.error(err);
      setError("Unable to save limits.");
    }
  }

  async function removeUser(userId) {
    setMessage("");
    setError("");

    if (!window.confirm("Delete this user? This cannot be undone.")) return;

    try {
      await deleteUser(userId, user.accessToken);
      await loadFamilies();
      setMessage("User deleted successfully.");
    } catch (err) {
      console.error(err);
      setError("Unable to delete user.");
    }
  }

  function applyPlanPreset(familyId, childId, planName) {
    const preset = PLAN_PRESETS[planName];
  
    if (!preset) return;
  
    setFamilies((prev) =>
      prev.map((family) => {
        if (family.family_id !== familyId) return family;
  
        return {
          ...family,
          children: family.children.map((child) =>
            child.id === childId
              ? {
                  ...child,
                  subscription_plan: planName,
                  access_cbse: preset.access_cbse,
                  access_sof_science: preset.access_sof_science,
                  access_sof_maths: preset.access_sof_maths,
                  access_sof_english: preset.access_sof_english,
                  daily_token_limit: preset.daily_token_limit,
                  monthly_token_limit: preset.monthly_token_limit,
                }
              : child
          ),
        };
      })
    );
  }


  function updateLocalChild(familyId, childId, field, value) {
    setFamilies((prev) =>
      prev.map((family) => {
        if (family.family_id !== familyId) return family;

        return {
          ...family,
          children: family.children.map((child) =>
            child.id === childId ? { ...child, [field]: value } : child
          ),
        };
      })
    );
  }

  function updateChildForm(parentId, field, value) {
    setChildForms((prev) => ({
      ...prev,
      [parentId]: {
        email: "",
        password: "",
        username: "",
        ...(prev[parentId] || {}),
        [field]: value,
      },
    }));
  }

  if (loading) return <p>Loading admin control...</p>;

  return (
    <div className="premium-page">
      <section className="premium-section">
        <div className="premium-header">
          <p className="eyebrow">Admin Operations</p>
          <h2>🛠️ Admin Control Center</h2>
          <p>Manage families, children, learning access, and AI limits.</p>
        </div>
      </section>

      {message && <div className="info-box">{message}</div>}
      {error && <div className="error-box">{error}</div>}

      <section className="premium-section">
        <div className="premium-header">
          <h3>➕ Create New Parent</h3>
          <p>Create a new family with one parent account.</p>
        </div>

        <form
          onSubmit={handleCreateParent}
          className="form-grid premium-rag-form-grid"
        >
          <label>
            Parent Name
            <input
              type="text"
              value={parentForm.username}
              onChange={(e) =>
                updateLocalChild(
                  family.family_id,
                  child.id,
                  "account_status",
                  e.target.value
                )
              }
              required
            />
          </label>

          <label>
            Parent Email
            <input
              type="email"
              value={parentForm.email}
              onChange={(e) =>
                setParentForm((prev) => ({
                  ...prev,
                  email: e.target.value,
                }))
              }
              required
            />
          </label>

          <label>
            Temporary Password
            <input
              type="password"
              value={parentForm.password}
              onChange={(e) =>
                setParentForm((prev) => ({
                  ...prev,
                  password: e.target.value,
                }))
              }
              required
            />
          </label>

          <button className="primary-btn" type="submit">
            Create Parent
          </button>
        </form>
      </section>

      {families.map((family) => (
        <section key={family.family_id} className="premium-section">
          <div className="premium-header">
            <h3>Family: {family.family_id}</h3>
          </div>

          <h4>Parents</h4>

          {(family.parents || []).map((parent) => {
            const childForm = childForms[parent.id] || {
              email: "",
              password: "",
              username: "",
            };

            return (
              <div
                key={parent.id}
                className="premium-card"
                style={{ marginBottom: 18 }}
              >
                <div className="premium-rag-result-row success">
                  <div>
                    <strong>{parent.username}</strong>
                    <p>{parent.email}</p>
                    <small>{parent.role}</small>
                  </div>

                  <button
                    className="danger-btn"
                    onClick={() => removeUser(parent.id)}
                  >
                    Delete Parent
                  </button>
                </div>

                <div style={{ marginTop: 18 }}>
                  <h4>Create Child Under {parent.username}</h4>

                  <form
                    onSubmit={(e) =>
                      handleCreateChild(e, family.family_id, parent.id)
                    }
                    className="form-grid premium-rag-form-grid"
                  >
                    <label>
                      Child Name
                      <input
                        type="text"
                        value={childForm.username}
                        onChange={(e) =>
                          updateChildForm(parent.id, "username", e.target.value)
                        }
                        required
                      />
                    </label>

                    <label>
                      Child Email
                      <input
                        type="email"
                        value={childForm.email}
                        onChange={(e) =>
                          updateChildForm(parent.id, "email", e.target.value)
                        }
                        required
                      />
                    </label>

                    <label>
                      Temporary Password
                      <input
                        type="password"
                        value={childForm.password}
                        onChange={(e) =>
                          updateChildForm(parent.id, "password", e.target.value)
                        }
                        required
                      />
                    </label>

                    <button className="secondary-btn" type="submit">
                      Create Child
                    </button>
                  </form>
                </div>
              </div>
            );
          })}

          <h4 style={{ marginTop: 24 }}>Children</h4>

          {(family.children || []).map((child) => (
            <div
              key={child.id}
              className="premium-card"
              style={{ marginBottom: 18 }}
            >
              <h3>{child.username}</h3>
              <p>{child.email}</p>

              {child.activity && (
                <div
                  className="premium-card"
                  style={{
                    marginTop: 14,
                    marginBottom: 18,
                    padding: 16,
                  }}
                >
                  <h4>📊 Student Activity</h4>

                  <div className="form-grid premium-rag-form-grid">
                    <div>
                      <strong>{child.activity.lessons_generated || 0}</strong>
                      <p>Lessons</p>
                    </div>

                    <div>
                      <strong>{child.activity.doubts_asked || 0}</strong>
                      <p>Doubts</p>
                    </div>

                    <div>
                      <strong>
                        {child.activity.mock_tests_generated || 0}
                      </strong>
                      <p>Mock Tests</p>
                    </div>

                    <div>
                      <strong>{child.activity.requests_total || 0}</strong>
                      <p>Total AI Requests</p>
                    </div>

                    <div>
                      <strong>{child.activity.tokens_today || 0}</strong>
                      <p>Tokens Today</p>
                    </div>

                    <div>
                      <strong>{child.activity.tokens_this_month || 0}</strong>
                      <p>Tokens This Month</p>
                    </div>

                    <div>
                      <strong>{child.activity.tokens_total || 0}</strong>
                      <p>Total Tokens</p>
                    </div>

                    <div>
                      <strong>
                        ${Number(child.activity.cost_total || 0).toFixed(6)}
                      </strong>
                      <p>Total Cost</p>
                    </div>
                  </div>

                  <small>
                    Last Activity:{" "}
                    {child.activity.last_activity
                      ? child.activity.last_activity.slice(0, 19)
                      : "No activity yet"}
                  </small>
                </div>
              )}

              <div className="form-grid premium-rag-form-grid">
                <label>
                  Plan
                  <select
                    value={child.subscription_plan || "free"}
                    onChange={(e) =>
                      applyPlanPreset(
                        family.family_id,
                        child.id,
                        e.target.value
                      )
                    }
                  >
                    <option value="free">Free</option>
                    <option value="starter">Starter</option>
                    <option value="premium">Premium</option>
                    <option value="family_premium">Family Premium</option>
                  </select>
                </label>

                <label>
                  Status
                  <select
                    value={child.account_status || "active"}
                    onChange={(e) =>
                      setParentForm((prev) => ({
                        ...prev,
                        username: e.target.value,
                      }))
                    }
                  >
                    <option value="active">Active</option>
                    <option value="trial">Trial</option>
                    <option value="suspended">Suspended</option>
                    <option value="expired">Expired</option>
                  </select>
                </label>

                <label>
                  Daily Tokens
                  <input
                    type="number"
                    value={child.daily_token_limit || 0}
                    onChange={(e) =>
                      updateLocalChild(
                        family.family_id,
                        child.id,
                        "daily_token_limit",
                        e.target.value
                      )
                    }
                  />
                </label>

                <label>
                  Monthly Tokens
                  <input
                    type="number"
                    value={child.monthly_token_limit || 0}
                    onChange={(e) =>
                      updateLocalChild(
                        family.family_id,
                        child.id,
                        "monthly_token_limit",
                        e.target.value
                      )
                    }
                  />
                </label>
              </div>

              <div style={{ marginTop: 16 }}>
                {[
                  ["access_cbse", "CBSE"],
                  ["access_sof_science", "SOF Science"],
                  ["access_sof_maths", "SOF Maths"],
                  ["access_sof_english", "SOF English"],
                ].map(([field, label]) => (
                  <label
                    key={field}
                    style={{ display: "block", marginBottom: 8 }}
                  >
                    <input
                      type="checkbox"
                      checked={!!child[field]}
                      onChange={(e) =>
                        updateLocalChild(
                          family.family_id,
                          child.id,
                          field,
                          e.target.checked
                        )
                      }
                    />{" "}
                    {label}
                  </label>
                ))}
              </div>

              <div style={{ display: "flex", gap: 12, marginTop: 18 }}>
                <button className="primary-btn" onClick={() => savePlan(child)}>
                  💾 Save Plan
                </button>

                <button
                  className="primary-btn"
                  onClick={() => saveAccess(child)}
                >
                  Save Access
                </button>

                <button
                  className="secondary-btn"
                  onClick={() => saveLimits(child)}
                >
                  Save Limits
                </button>
                {child.account_status === "suspended" ? (
                  <button
                    className="primary-btn"
                    onClick={() => reactivateChild(child)}
                  >
                    🔓 Reactivate
                  </button>
                ) : (
                  <button
                    className="secondary-btn"
                    onClick={() => suspendChild(child)}
                  >
                    🔒 Suspend
                  </button>
                )}

                <button
                  className="danger-btn"
                  onClick={() => removeUser(child.id)}
                >
                  Delete Child
                </button>
              </div>
            </div>
          ))}
        </section>
      ))}
    </div>
  );
}

export default AdminControlPage;