import { useEffect, useState } from "react";
import logo from "../assets/AITutorLogo1.png";
import { supabase } from "../api/supabaseClient";

function isStrongEnough(password) {
  /** Keep password rules simple and readable for parents/students. */
  return password.length >= 8;
}

function ResetPasswordPage({ onBackToLogin }) {
  /** Handles the Supabase recovery-link landing page and stores a new password. */
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionReady, setSessionReady] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    async function initializeRecoverySession() {
      /** Exchange a recovery code if present, then detect the active Supabase session. */
      setError("");

      try {
        const code = new URLSearchParams(window.location.search).get("code");

        if (code && supabase.auth.exchangeCodeForSession) {
          await supabase.auth.exchangeCodeForSession(code);
          window.history.replaceState({}, "", "/reset-password");
        }

        const { data } = await supabase.auth.getSession();
        setSessionReady(!!data.session);
      } catch {
        setSessionReady(false);
      }
    }

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event) => {
      if (event === "PASSWORD_RECOVERY" || event === "SIGNED_IN") {
        setSessionReady(true);
      }
    });

    initializeRecoverySession();

    return () => subscription.unsubscribe();
  }, []);

  async function handleResetPassword(e) {
    /** Validate and save the new password using the active recovery session. */
    e.preventDefault();
    setError("");
    setMessage("");

    if (!isStrongEnough(password)) {
      setError("Password must be at least 8 characters.");
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setLoading(true);

    try {
      const { error: updateError } = await supabase.auth.updateUser({
        password,
      });

      if (updateError) {
        setError(updateError.message || "Unable to reset password.");
        return;
      }

      await supabase.auth.signOut();
      localStorage.removeItem("tutor_user");
      localStorage.removeItem("tutor_active_page");
      setMessage("Password updated. Please sign in with your new password.");
      setPassword("");
      setConfirmPassword("");
    } catch (err) {
      setError(err.message || "Unable to reset password.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="ait-login-page">
      <div className="ait-login-shell ait-auth-shell">
        <div className="ait-login-left">
          <img src={logo} alt="AI Tutor" className="ait-login-logo" />
          <h1>Reset your password.</h1>
          <p>
            Create a new password for your Likha Poha AI account, then sign in
            again from the login page.
          </p>
        </div>

        <div className="ait-login-right">
          <div className="ait-form-card">
            <h2>Set New Password</h2>
            <p>
              Use the reset link from your email. Links can expire, so request a
              fresh one if this page says the session is not ready.
            </p>

            {!sessionReady && !message && (
              <div className="error-box">
                Reset session is not ready. Open the latest password reset link
                from your email.
              </div>
            )}

            <form onSubmit={handleResetPassword}>
              <div className="ait-input-row">
                <span>🔒</span>
                <input
                  type="password"
                  placeholder="New password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </div>

              <div className="ait-input-row">
                <span>✅</span>
                <input
                  type="password"
                  placeholder="Confirm new password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                />
              </div>

              <button
                className="ait-signin-btn"
                type="submit"
                disabled={loading || !sessionReady}
              >
                {loading ? "Updating..." : "Update Password"}
              </button>
            </form>

            <button
              className="ait-link-button"
              type="button"
              onClick={onBackToLogin}
            >
              Back to sign in
            </button>

            {error && <div className="error-box">{error}</div>}
            {message && <div className="info-box">{message}</div>}
          </div>
        </div>
      </div>
    </div>
  );
}

export default ResetPasswordPage;
