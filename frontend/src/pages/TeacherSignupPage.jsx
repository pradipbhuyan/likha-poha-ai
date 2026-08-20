/**
 * TeacherSignupPage.jsx — Dedicated self-serve signup path for teachers.
 *
 * Deliberately separate from SignupPage.jsx (which only offers Parent/Student)
 * so the main signup flow stays simple. Not linked from SignupPage/LoginPage —
 * reached only via a direct URL (/teacher-signup), shared through the landing
 * page footer, sales outreach, or school partnerships.
 *
 * Accounts created here start as account_status="pending_verification" on the
 * backend (POST /api/auth/teacher-signup) until an admin approves them, so
 * this page does not auto sign the user in — it shows a confirmation screen
 * and sends them to the normal login page.
 */
import { useState } from "react";
import { Eye, EyeOff, Check } from "lucide-react";
import logo from "../assets/AITutorLogo1.png";
import { supabase } from "../api/supabaseClient";
import "./SignupPage.css";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export default function TeacherSignupPage({ onBackToLogin }) {
  const [name, setName]         = useState("");
  const [email, setEmail]       = useState("");
  const [school, setSchool]     = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw]     = useState(false);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState("");
  const [done, setDone]         = useState(false);

  function validate() {
    if (!name.trim())        { setError("Full name is required."); return false; }
    if (!email.trim())       { setError("Email address is required."); return false; }
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email.trim())) {
                               setError("Please enter a valid email address."); return false; }
    if (!school.trim())      { setError("School name is required."); return false; }
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
      const res = await fetch(`${API_BASE}/api/auth/teacher-signup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: name.trim(),
          email: email.trim(),
          school: school.trim(),
          password,
        }),
      });
      const data = await res.json();
      if (!res.ok || !data.success) {
        const raw = data.detail || data.message || "";
        if (res.status === 409 || raw.toLowerCase().includes("already") || raw.toLowerCase().includes("exists")) {
          setError("This email is already registered. Please sign in instead.");
        } else if (raw.toLowerCase().includes("rate limit")) {
          setError("Too many signup attempts. Please wait a few minutes and try again.");
        } else if (raw) {
          setError(raw);
        } else {
          setError("We couldn't create your account. Please try again.");
        }
        return;
      }
      setDone(true);
    } catch (err) {
      console.error("[teacher-signup] Unexpected error:", err.message);
      setError("We couldn't create your account. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  if (done) {
    return (
      <div className="ait-login-page signup-page-wrapper" data-testid="teacher-signup-done" style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "100vh", background: "var(--bg,#0f172a)" }}>
        <div style={{ textAlign: "center", color: "#fff", padding: 32, maxWidth: 420 }}>
          <div style={{ marginBottom: 16, color: "#7c3aed", display: "flex", justifyContent: "center" }}><Check size={40} strokeWidth={1.8} /></div>
          <h2 style={{ margin: "0 0 8px", fontSize: "1.3rem", fontWeight: 800 }}>Account created!</h2>
          <p style={{ color: "rgba(255,255,255,.7)", fontSize: ".9rem", lineHeight: 1.5 }}>
            Our team will verify your school details before your teacher dashboard
            unlocks. You can sign in any time to check your account status.
          </p>
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
    <div className="ait-login-page signup-page-wrapper" data-testid="teacher-signup-page">
      <div className="ait-login-shell signup-shell">

        {/* Left — branding */}
        <div className="ait-login-left signup-left-panel">
          <img src={logo} alt="Likhapoha AI" className="ait-login-logo" />
          <h1>For schools &amp; teachers.</h1>
          <p>
            Track assigned students, generate lesson plans and test papers,
            and monitor classroom progress — all powered by AI.
          </p>
          <div className="ait-feature-list">
            {["Classroom Analytics", "Lesson Plan Generator", "Test Paper Builder", "Student Progress Tracking"].map(f => (
              <div key={f} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                <Check size={15} style={{ color: "#7c3aed", flexShrink: 0 }} strokeWidth={2.5} />
                <span style={{ fontSize: ".88rem", color: "rgba(255,255,255,.85)" }}>{f}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Right — form */}
        <div className="ait-login-right signup-right-panel">
          <div className="ait-form-card" data-testid="teacher-signup-form-card">
            <h2 style={{ marginBottom: 4 }}>Create your teacher account</h2>
            <p style={{ marginBottom: 20, color: "var(--text-muted,#64748b)", fontSize: ".88rem" }}>
              New accounts are reviewed before dashboard access unlocks.
            </p>

            <form onSubmit={handleSubmit} noValidate>
              <div style={{ marginBottom: 12 }}>
                <label style={{ fontSize: ".8rem", fontWeight: 600, display: "block", marginBottom: 4 }}>Full Name *</label>
                <input
                  data-testid="teacher-signup-name"
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
                  data-testid="teacher-signup-email"
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
                  data-testid="teacher-signup-school"
                  type="text"
                  placeholder="Enter your school's name"
                  value={school}
                  onChange={ev => { setSchool(ev.target.value); setError(""); }}
                  required
                  className="ait-input"
                  style={{ width: "100%", boxSizing: "border-box" }}
                />
              </div>

              <div style={{ marginBottom: 16 }}>
                <label style={{ fontSize: ".8rem", fontWeight: 600, display: "block", marginBottom: 4 }}>Password *</label>
                <div style={{ position: "relative" }}>
                  <input
                    data-testid="teacher-signup-password"
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
                <div data-testid="teacher-signup-error" style={{ color: "#dc2626", fontSize: ".82rem", marginBottom: 12, padding: "8px 12px", background: "rgba(239,68,68,.07)", border: "1px solid #fca5a5", borderRadius: 7 }}>
                  {error}
                </div>
              )}

              <button
                data-testid="teacher-signup-submit"
                type="submit"
                disabled={loading}
                className="ait-btn-primary"
                style={{ width: "100%", padding: "11px", borderRadius: 9, fontWeight: 700, fontSize: "1rem", cursor: loading ? "not-allowed" : "pointer", opacity: loading ? 0.7 : 1, background: "#6366f1", color: "#fff", border: "none" }}
              >
                {loading ? "Creating account…" : "Create Teacher Account"}
              </button>

              <div style={{ textAlign: "center", marginTop: 16, fontSize: ".83rem", color: "var(--text-muted,#64748b)" }}>
                Already have an account?{" "}
                <button
                  data-testid="teacher-signup-signin-link"
                  type="button"
                  onClick={onBackToLogin}
                  style={{ background: "none", border: "none", color: "#7c3aed", fontWeight: 700, cursor: "pointer", fontFamily: "inherit", fontSize: ".83rem" }}
                >
                  Sign in
                </button>
              </div>

              {/* Google Sign-Up divider */}
              <div style={{ margin: "16px 0 12px", textAlign: "center", color: "var(--text-muted,#64748b)", fontSize: "0.82rem" }}>
                — or sign up with —
              </div>

              {/* Google Sign-Up button — official Google button style.
                  Stores an intended-role hint so the shared OAuth role picker
                  (App.jsx) skips straight to the school-name step for teachers. */}
              <button
                type="button"
                data-testid="teacher-signup-google"
                onClick={async () => {
                  sessionStorage.setItem("oauth_intended_role", "teacher");
                  await supabase.auth.signInWithOAuth({
                    provider: "google",
                    options: {
                      redirectTo: window.location.origin,
                      queryParams: { access_type: "offline", prompt: "select_account" },
                    },
                  });
                }}
                style={{
                  width: "100%",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 10,
                  padding: "11px 16px",
                  borderRadius: 10,
                  border: "1px solid #dadce0",
                  background: "#fff",
                  color: "#3c4043",
                  fontSize: "0.9rem",
                  fontWeight: 500,
                  cursor: "pointer",
                  fontFamily: "'Google Sans', Roboto, Arial, sans-serif",
                  transition: "box-shadow 0.15s, background 0.15s",
                  boxShadow: "0 1px 3px rgba(0,0,0,.08)",
                }}
                onMouseEnter={e => { e.currentTarget.style.boxShadow = "0 2px 8px rgba(0,0,0,.18)"; e.currentTarget.style.background = "#f8f9fa"; }}
                onMouseLeave={e => { e.currentTarget.style.boxShadow = "0 1px 3px rgba(0,0,0,.08)"; e.currentTarget.style.background = "#fff"; }}
              >
                <svg width="18" height="18" viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg">
                  <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615Z" fill="#4285F4"/>
                  <path d="M9 18c2.43 0 4.467-.806 5.956-2.184l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18Z" fill="#34A853"/>
                  <path d="M3.964 10.706A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.706V4.962H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.038l3.007-2.332Z" fill="#FBBC05"/>
                  <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.962L3.964 7.294C4.672 5.163 6.656 3.58 9 3.58Z" fill="#EA4335"/>
                </svg>
                Sign up with Google
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
