import { useState } from "react";
import { supabase } from "../api/supabaseClient";

function ChangePasswordPage({ user }) {
  /** Allows any signed-in user to change their password after re-entering the current one. */
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function handleChangePassword(e) {
    /** Reauthenticate and then update the Supabase Auth password. */
    e.preventDefault();
    setMessage("");
    setError("");

    if (!currentPassword) {
      setError("Enter your current password.");
      return;
    }

    if (newPassword.length < 8) {
      setError("New password must be at least 8 characters.");
      return;
    }

    if (newPassword !== confirmPassword) {
      setError("New passwords do not match.");
      return;
    }

    if (currentPassword === newPassword) {
      setError("New password must be different from the current password.");
      return;
    }

    setLoading(true);

    try {
      const { error: signInError } = await supabase.auth.signInWithPassword({
        email: user.email,
        password: currentPassword,
      });

      if (signInError) {
        setError("Current password is not correct.");
        return;
      }

      const { error: updateError } = await supabase.auth.updateUser({
        password: newPassword,
      });

      if (updateError) {
        setError(updateError.message || "Unable to change password.");
        return;
      }

      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setMessage("Password changed successfully.");
    } catch (err) {
      setError(err.message || "Unable to change password.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="premium-page change-password-page">
      {/* Compact context bar — removes redundant page title duplication */}
      <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "12px 0 4px", flexWrap: "wrap" }}>
        <span style={{ fontSize: "1rem" }}>🔐</span>
        <span style={{ fontSize: "0.85rem", color: "var(--muted)" }}>
          Updating password for <strong style={{ color: "var(--text, #e5e7eb)" }}>{user.email}</strong>
          {" "}— use at least 8 characters, different from your current password
        </span>
      </div>

      <section className="premium-section change-password-card">
        <form onSubmit={handleChangePassword} className="form-grid">
          <label>
            Current Password
            <input
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </label>

          <label>
            New Password
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              autoComplete="new-password"
              required
            />
          </label>

          <label>
            Confirm New Password
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              autoComplete="new-password"
              required
            />
          </label>

          <button className="primary-btn" type="submit" disabled={loading}>
            {loading ? "Changing..." : "Change Password"}
          </button>
        </form>

        {error && <div className="error-box">{error}</div>}
        {message && <div className="info-box">{message}</div>}
      </section>
    </div>
  );
}

export default ChangePasswordPage;
