import { useEffect, useState } from "react";
import {
  getAdminFamilies,
  updateChildAccess,
  updateChildLimits,
  deleteUser,
} from "../api/adminControl";

function AdminControlPage({ user }) {
  const [families, setFamilies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

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

      {families.map((family) => (
        <section key={family.family_id} className="premium-section">
          <div className="premium-header">
            <h3>Family: {family.family_id}</h3>
          </div>

          <h4>Parents</h4>

          {(family.parents || []).map((parent) => (
            <div key={parent.id} className="premium-rag-result-row success">
              <div>
                <strong>{parent.username}</strong>
                <p>{parent.email}</p>
                <small>{parent.role}</small>
              </div>

              <button
                className="danger-btn"
                onClick={() => removeUser(parent.id)}
              >
                Delete
              </button>
            </div>
          ))}

          <h4 style={{ marginTop: 24 }}>Children</h4>

          {(family.children || []).map((child) => (
            <div
              key={child.id}
              className="premium-card"
              style={{ marginBottom: 18 }}
            >
              <h3>{child.username}</h3>
              <p>{child.email}</p>

              <div className="form-grid premium-rag-form-grid">
                <label>
                  Plan
                  <select
                    value={child.subscription_plan || "free"}
                    onChange={(e) =>
                      updateLocalChild(
                        family.family_id,
                        child.id,
                        "subscription_plan",
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
                      updateLocalChild(
                        family.family_id,
                        child.id,
                        "account_status",
                        e.target.value
                      )
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