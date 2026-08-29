/**
 * PrincipalSignupPage.jsx — Dedicated self-serve signup path for school principals.
 *
 * Mirrors TeacherSignupPage.jsx's shape: a separate, unlinked-from-the-main-
 * flow page (reached via /principal-signup), submitting to its own backend
 * endpoint (POST /api/auth/principal-signup). Accounts created here start as
 * account_status="pending_verification" until an admin confirms the school
 * is real, so this page shows a confirmation screen rather than signing the
 * user in immediately.
 *
 * Deliberately email/password only for now — no Google OAuth option, so this
 * page adds zero new branches to App.jsx's existing OAuth role-picker wizard.
 */
import { useState } from "react";
import { Eye, EyeOff, Check } from "lucide-react";
import logo from "../assets/AITutorLogo1.png";
import "./SignupPage.css";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export default function PrincipalSignupPage({ onBackToLogin }) {
  const [name, setName]           = useState("");
  const [email, setEmail]         = useState("");
  const [schoolName, setSchoolName] = useState("");
  const [udiseCode, setUdiseCode] = useState("");
  const [city, setCity]           = useState("");
  const [stateName, setStateName] = useState("");
  const [password, setPassword]   = useState("");
  const [showPw, setShowPw]       = useState(false);
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState("");
  const [done, setDone]           = useState(false);
  const [schoolCode, setSchoolCode] = useState("");

  function validate() {
    if (!name.trim())        { setError("Full name is required."); return false; }
    if (!email.trim())       { setError("Email address is required."); return false; }
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email.trim())) {
                               setError("Please enter a valid email address."); return false; }
    if (!schoolName.trim())  { setError("School name is required."); return false; }
    if (!password)           { setError("Password is required."); return false; }
    if (password.length < 8) { setError("Password must be at least 8 characters."); return false; }
    return true;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    if (!validate()) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/auth/principal-signup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: name.trim(),
          email: email.trim(),
          school_name: schoolName.trim(),
          udise_code: udiseCode.trim() || null,
          city: city.trim(),
          state: stateName.trim(),
          password,
        }),
      });
      const data = await res.json();
      if (!res.ok || !data.success) {
        const raw = data.detail || data.message || "";
        if (res.status === 409 || raw.toLowerCase().includes("already") || raw.toLowerCase().includes("exists")) {
          setError("This email (or UDISE code) is already registered. Please sign in instead.");
        } else if (raw.toLowerCase().includes("rate limit")) {
          setError("Too many signup attempts. Please wait a few minutes and try again.");
        } else if (raw) {
          setError(raw);
        } else {
          setError("We couldn't create your account. Please try again.");
        }
        return;
      }
      setSchoolCode(data.school_code || "");
      setDone(true);
    } catch (err) {
      console.error("[principal-signup] Unexpected error:", err.message);
      setError("We couldn't create your account. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  if (done) {
    return (
      <div className="ait-login-page signup-page-wrapper" data-testid="principal-signup-done" style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "100vh" }}>
        <div style={{ textAlign: "center", color: "#fff", padding: 32, maxWidth: 460 }}>
          <div style={{ marginBottom: 16, color: "#6366f1", display: "flex", justifyContent: "center" }}><Check size={40} strokeWidth={1.8} /></div>
          <h2 style={{ margin: "0 0 8px", fontSize: "1.3rem", fontWeight: 800 }}>Account created!</h2>
          <p style={{ color: "rgba(255,255,255,.7)", fontSize: ".9rem", lineHeight: 1.5 }}>
            Our team will verify your school details before your Principal
            Command Center unlocks. You can sign in any time to check status.
          </p>
          {schoolCode && (
            <div style={{ marginTop: 18, padding: "14px 18px", borderRadius: 10, background: "rgba(99,102,241,.12)", border: "1px dashed rgba(99,102,241,.5)" }}>
              <div style={{ fontSize: ".72rem", color: "rgba(255,255,255,.6)", marginBottom: 4 }}>Your school code — share it with teachers and students once verified</div>
              <div style={{ fontFamily: "monospace", fontWeight: 700, fontSize: "1.1rem", letterSpacing: ".04em" }}>{schoolCode}</div>
            </div>
          )}
          <button
            type="button"
            onClick={onBackToLogin}
            className="ait-btn-primary"
            style={{ marginTop: 20, padding: "10px 24px", borderRadius: 9, fontWeight: 700, background: "#6366f1", color: "#fff", border: "none", cursor: "pointer" }}
          >
            Go to sign in
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="ait-login-page signup-page-wrapper" data-testid="principal-signup-page">
      <div className="ait-login-shell signup-shell">

        {/* Left — branding */}
        <div className="ait-login-left signup-left-panel">
          <img src={logo} alt="Likhapoha AI" className="ait-login-logo" />
          <h1>For school principals.</h1>
          <p>
            See your whole school in one place — teachers, students, free vs.
            paid tiers, and the rewards your school earns as more students
            get full access.
          </p>
          <div className="ait-feature-list">
            {["School-wide Dashboard", "Teacher &amp; Student Rosters", "Free vs. Paid Tracking", "School Incentive Program"].map(f => (
              <div key={f} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                <Check size={15} style={{ color: "#6366f1", flexShrink: 0 }} strokeWidth={2.5} />
                <span style={{ fontSize: ".88rem", color: "rgba(255,255,255,.85)" }} dangerouslySetInnerHTML={{ __html: f }} />
              </div>
            ))}
          </div>
        </div>

        {/* Right — form */}
        <div className="ait-login-right signup-right-panel">
          <div className="ait-form-card" data-testid="principal-signup-form-card">
            <h2 style={{ marginBottom: 4 }}>Create your principal account</h2>
            <p style={{ marginBottom: 20, color: "var(--text-muted,#64748b)", fontSize: ".88rem" }}>
              New schools are reviewed before the dashboard unlocks.
            </p>

            <form onSubmit={handleSubmit} noValidate>
              <div style={{ marginBottom: 12 }}>
                <label style={{ fontSize: ".8rem", fontWeight: 600, display: "block", marginBottom: 4 }}>Full Name *</label>
                <input
                  data-testid="principal-signup-name"
                  type="text"
                  placeholder="Enter your full name"
                  value={name}
                  onChange={ev => { setName(ev.target.value); setError(""); }}
                  required
                  className="ait-input"
                  style={{ width: "100%", boxSizing: "border-box" }}
                />
              </div>

              <div style={{ marginBottom: 12 }}>
                <label style={{ fontSize: ".8rem", fontWeight: 600, display: "block", marginBottom: 4 }}>Email Address *</label>
                <input
                  data-testid="principal-signup-email"
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={ev => { setEmail(ev.target.value); setError(""); }}
                  required
                  className="ait-input"
                  style={{ width: "100%", boxSizing: "border-box" }}
                />
              </div>

              <div style={{ marginBottom: 12 }}>
                <label style={{ fontSize: ".8rem", fontWeight: 600, display: "block", marginBottom: 4 }}>School Name *</label>
                <input
                  data-testid="principal-signup-school"
                  type="text"
                  placeholder="Enter your school's name"
                  value={schoolName}
                  onChange={ev => { setSchoolName(ev.target.value); setError(""); }}
                  required
                  className="ait-input"
                  style={{ width: "100%", boxSizing: "border-box" }}
                />
              </div>

              <div style={{ display: "flex", gap: 10, marginBottom: 12 }}>
                <div style={{ flex: 1 }}>
                  <label style={{ fontSize: ".8rem", fontWeight: 600, display: "block", marginBottom: 4 }}>City</label>
                  <input
                    data-testid="principal-signup-city"
                    type="text"
                    placeholder="City"
                    value={city}
                    onChange={ev => setCity(ev.target.value)}
                    className="ait-input"
                    style={{ width: "100%", boxSizing: "border-box" }}
                  />
                </div>
                <div style={{ flex: 1 }}>
                  <label style={{ fontSize: ".8rem", fontWeight: 600, display: "block", marginBottom: 4 }}>State</label>
                  <input
                    data-testid="principal-signup-state"
                    type="text"
                    placeholder="State"
                    value={stateName}
                    onChange={ev => setStateName(ev.target.value)}
                    className="ait-input"
                    style={{ width: "100%", boxSizing: "border-box" }}
                  />
                </div>
              </div>

              <div style={{ marginBottom: 12 }}>
                <label style={{ fontSize: ".8rem", fontWeight: 600, display: "block", marginBottom: 4 }}>UDISE Code (optional)</label>
                <input
                  data-testid="principal-signup-udise"
                  type="text"
                  placeholder="Your school's official UDISE+ code, if known"
                  value={udiseCode}
                  onChange={ev => setUdiseCode(ev.target.value)}
                  className="ait-input"
                  style={{ width: "100%", boxSizing: "border-box" }}
                />
                <div style={{ fontSize: ".7rem", color: "var(--text-muted,#94a3b8)", marginTop: 3 }}>
                  Helps our team verify your school faster.
                </div>
              </div>

              <div style={{ marginBottom: 16 }}>
                <label style={{ fontSize: ".8rem", fontWeight: 600, display: "block", marginBottom: 4 }}>Password *</label>
                <div style={{ position: "relative" }}>
                  <input
                    data-testid="principal-signup-password"
                    type={showPw ? "text" : "password"}
                    placeholder="Create a strong password"
                    value={password}
                    onChange={ev => { setPassword(ev.target.value); setError(""); }}
                    required
                    className="ait-input"
                    style={{ width: "100%", boxSizing: "border-box", paddingRight: 36 }}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPw(p => !p)}
                    style={{ position: "absolute", right: 8, top: "50%", transform: "translateY(-50%)", background: "none", border: "none", cursor: "pointer", color: "var(--text-muted,#64748b)", padding: 0 }}
                  >
                    {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
                <div style={{ fontSize: ".7rem", color: "var(--text-muted,#94a3b8)", marginTop: 3 }}>
                  At least 8 characters
                </div>
              </div>

              {error && (
                <div data-testid="principal-signup-error" style={{ color: "#dc2626", fontSize: ".82rem", marginBottom: 12, padding: "8px 12px", background: "rgba(239,68,68,.07)", border: "1px solid #fca5a5", borderRadius: 7 }}>
                  {error}
                </div>
              )}

              <button
                data-testid="principal-signup-submit"
                type="submit"
                disabled={loading}
                className="ait-btn-primary"
                style={{ width: "100%", padding: "11px", borderRadius: 9, fontWeight: 700, fontSize: "1rem", cursor: loading ? "not-allowed" : "pointer", opacity: loading ? 0.7 : 1, background: "#6366f1", color: "#fff", border: "none" }}
              >
                {loading ? "Creating account…" : "Create Principal Account"}
              </button>

              <div style={{ textAlign: "center", marginTop: 16, fontSize: ".83rem", color: "var(--text-muted,#64748b)" }}>
                Already have an account?{" "}
                <button
                  data-testid="principal-signup-signin-link"
                  type="button"
                  onClick={onBackToLogin}
                  style={{ background: "none", border: "none", color: "#6366f1", fontWeight: 700, cursor: "pointer", fontFamily: "inherit", fontSize: ".83rem" }}
                >
                  Sign in
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
