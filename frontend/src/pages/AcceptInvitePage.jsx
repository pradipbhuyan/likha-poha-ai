import { useEffect, useState } from "react";
import { User, Lock, Eye, EyeOff, CheckCircle2 } from "lucide-react";
import logo from "../assets/AITutorLogo1.png";
import { getInvitationByToken, acceptInvitation } from "../api/teacherDashboard";

function getTokenFromUrl() {
  return new URLSearchParams(window.location.search).get("token") || "";
}

function AcceptInvitePage({ onBackToLogin }) {
  /**
   * Public landing page for a teacher's student invitation email.
   * The student sets a username + password here; the account is created
   * on submit and auto-assigned to the inviting teacher.
   */
  const [token] = useState(getTokenFromUrl);
  const [loadingInvite, setLoadingInvite] = useState(true);
  const [invite, setInvite] = useState(null);
  const [loadError, setLoadError] = useState("");

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const [accepted, setAccepted] = useState(false);

  useEffect(() => {
    async function loadInvite() {
      if (!token) {
        setLoadError("This invitation link is missing its token. Please use the link from your email.");
        setLoadingInvite(false);
        return;
      }
      try {
        const data = await getInvitationByToken(token);
        if (!data.success) {
          setLoadError(data.error || "This invitation could not be found.");
        } else {
          setInvite(data.invitation);
          setUsername((data.invitation?.student_name || "").trim());
        }
      } catch {
        setLoadError("Unable to reach the server. Please try again in a moment.");
      } finally {
        setLoadingInvite(false);
      }
    }
    loadInvite();
  }, [token]);

  async function handleAccept(e) {
    e.preventDefault();
    setSubmitError("");

    if (!username.trim()) {
      setSubmitError("Please choose a username.");
      return;
    }
    if (password.length < 6) {
      setSubmitError("Password must be at least 6 characters.");
      return;
    }
    if (password !== confirmPassword) {
      setSubmitError("Passwords do not match.");
      return;
    }

    setSubmitting(true);
    try {
      await acceptInvitation(token, { username: username.trim(), password });
      setAccepted(true);
    } catch (err) {
      setSubmitError(err.message || "Unable to accept invitation.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="ait-login-page">
      <div className="ait-login-shell ait-auth-shell">
        <div className="ait-login-left">
          <img src={logo} alt="AI Tutor" className="ait-login-logo" />
          <h1>You've been invited.</h1>
          <p>
            Your teacher has invited you to join their classroom on Likha
            Poha AI. Set a username and password to get started.
          </p>
        </div>

        <div className="ait-login-right">
          <div className="ait-form-card">
            <h2>Accept Invitation</h2>

            {loadingInvite && <p>Checking your invitation…</p>}

            {!loadingInvite && loadError && (
              <>
                <div className="error-box">{loadError}</div>
                <button className="ait-link-button" type="button" onClick={onBackToLogin}>
                  Back to sign in
                </button>
              </>
            )}

            {!loadingInvite && !loadError && accepted && (
              <>
                <div className="info-box">
                  Account created! You can now sign in with your new username and password.
                </div>
                <button className="ait-signin-btn" type="button" onClick={onBackToLogin}>
                  Go to sign in
                </button>
              </>
            )}

            {!loadingInvite && !loadError && !accepted && invite && (
              <>
                <p>
                  Invited by <strong>{invite.teacher_name}</strong>
                  {invite.grade ? <> for <strong>{invite.grade}</strong></> : null}.
                  {invite.email ? <> Signing in email: <strong>{invite.email}</strong></> : null}
                </p>

                <form onSubmit={handleAccept}>
                  <div className="ait-input-row">
                    <span className="ait-input-icon"><User size={20} strokeWidth={2} /></span>
                    <input
                      type="text"
                      placeholder="Choose a username"
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      required
                    />
                  </div>

                  <div className="ait-input-row">
                    <span className="ait-input-icon"><Lock size={20} strokeWidth={2} /></span>
                    <input
                      type={showPassword ? "text" : "password"}
                      placeholder="Create a password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                    />
                    <button
                      type="button"
                      className="password-toggle"
                      onClick={() => setShowPassword(!showPassword)}
                      aria-label={showPassword ? "Hide password" : "Show password"}
                    >
                      {showPassword ? <EyeOff size={20} strokeWidth={2} /> : <Eye size={20} strokeWidth={2} />}
                    </button>
                  </div>

                  <div className="ait-input-row">
                    <span className="ait-input-icon"><CheckCircle2 size={20} strokeWidth={2} /></span>
                    <input
                      type={showPassword ? "text" : "password"}
                      placeholder="Confirm password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      required
                    />
                  </div>

                  <button className="ait-signin-btn" type="submit" disabled={submitting}>
                    {submitting ? "Creating account..." : "Accept & Create Account"}
                  </button>
                </form>

                <button className="ait-link-button" type="button" onClick={onBackToLogin}>
                  Back to sign in
                </button>

                {submitError && <div className="error-box">{submitError}</div>}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default AcceptInvitePage;
