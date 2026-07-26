import { useState } from "react";
import { supabase } from "../api/supabaseClient";

const STRENGTH_LEVELS = [
  null,
  { label: "Weak", color: "#dc2626" },
  { label: "Fair", color: "#f59e0b" },
  { label: "Good", color: "#0ea5e9" },
  { label: "Strong", color: "#16a34a" },
  { label: "Very strong", color: "#16a34a" },
];

function getPasswordStrength(pw) {
  /** Deterministic, transparent scoring — same rules the form itself enforces
   *  (8-char minimum), plus real length/variety signals. Never a guess. */
  if (!pw) return null;
  if (pw.length < 8) {
    return { score: 0, label: "Too short — needs 8+ characters", color: "#dc2626" };
  }
  let score = 1; // meets the 8-character minimum
  if (pw.length >= 12) score++;
  if (/[a-z]/.test(pw) && /[A-Z]/.test(pw)) score++;
  if (/\d/.test(pw)) score++;
  if (/[^A-Za-z0-9]/.test(pw)) score++;
  return { score, ...STRENGTH_LEVELS[score] };
}

function ChangePasswordPage({ user }) {
  /** Allows any signed-in user to change their password after re-entering the current one. */
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [showPasswords, setShowPasswords] = useState(false);

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
            <div className="change-password-field">
              <input
                type={showPasswords ? "text" : "password"}
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                autoComplete="current-password"
                required
              />
            </div>
          </label>

          <label>
            New Password
            <div className="change-password-field">
              <input
                type={showPasswords ? "text" : "password"}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                autoComplete="new-password"
                required
              />
            </div>
            {newPassword && (() => {
              const strength = getPasswordStrength(newPassword);
              return (
                <div className="password-strength" aria-live="polite">
                  <div className="password-strength-track">
                    {[1, 2, 3, 4, 5].map((i) => (
                      <span
                        key={i}
                        className="password-strength-seg"
                        style={{ background: i <= strength.score ? strength.color : "var(--border, #e5e7eb)" }}
                      />
                    ))}
                  </div>
                  <span className="password-strength-label" style={{ color: strength.color }}>
                    {strength.label}
                  </span>
                </div>
              );
            })()}
          </label>

          <label>
            Confirm New Password
            <div className="change-password-field">
              <input
                type={showPasswords ? "text" : "password"}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                autoComplete="new-password"
                required
              />
            </div>
          </label>

          <button
            type="button"
            className="change-password-toggle"
            style={{ justifySelf: "start" }}
            onClick={() => setShowPasswords((prev) => !prev)}
          >
            {showPasswords ? "🙈 Hide passwords" : "👁 Show passwords"}
          </button>

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
