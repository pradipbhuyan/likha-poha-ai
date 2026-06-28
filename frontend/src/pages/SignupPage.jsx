/**
 * SignupPage.jsx — Single-Step Card-Based Signup (Option 1)
 * All new accounts start on Free Tier. No payment or offer code in signup.
 * Business rules: access_cbse=false, role=parent|student|teacher
 */
import { useState } from "react";
import { Eye, EyeOff } from "lucide-react";
import logo from "../assets/AITutorLogo1.png";
import { supabase } from "../api/supabaseClient";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const ROLES = [
  { key:"parent",  label:"Parent",  desc:"Manage your child's learning and track progress" },
  { key:"student", label:"Student", desc:"Access AI lessons, mock tests and doubt solving" },
  { key:"teacher", label:"Teacher", desc:"Monitor students and provide personalised guidance" },
];

export default function SignupPage({ onLogin, onBack }) {
  const [role, setRole]         = useState("parent");
  const [name, setName]         = useState("");
  const [email, setEmail]       = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw]     = useState(false);
  const [agreed, setAgreed]     = useState(false);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState("");
  const [info, setInfo]         = useState("");

  function validate() {
    if (!role)               { setError("Please choose a role."); return false; }
    if (!name.trim())        { setError("Full name is required."); return false; }
    if (!email.trim())       { setError("Email address is required."); return false; }
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email.trim())) {
                               setError("Please enter a valid email address."); return false; }
    if (!password)           { setError("Password is required."); return false; }
    if (password.length < 8) { setError("Password must be at least 8 characters."); return false; }
    if (!agreed)             { setError("Please agree to the Terms of Service to continue."); return false; }
    return true;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(""); setInfo("");
    if (!validate()) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/auth/signup-free`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role, name: name.trim(), email: email.trim(), password }),
      });
      const data = await res.json();
      if (!res.ok || !data.success) {
        const raw = data.detail || data.message || "";
        if (res.status === 409 || raw.toLowerCase().includes("already") || raw.toLowerCase().includes("exists")) {
          setError("This email is already registered. Please sign in instead.");
        } else if (raw.toLowerCase().includes("rate limit") || raw.toLowerCase().includes("over_email")) {
          setError("Too many signup attempts. Please wait a few minutes and try again.");
        } else if (raw && !raw.toLowerCase().includes("supabase") && !raw.toLowerCase().includes("token")) {
          setError(raw);
        } else {
          console.error("[signup] API error:", raw);
          setError("We couldn't create your account. Please try again.");
        }
        return;
      }
      await supabase.auth.signOut().catch(() => {});
      const { data: authData, error: authErr } = await supabase.auth.signInWithPassword({
        email: email.trim(), password,
      });
      if (authErr) {
        if (authErr.message?.toLowerCase().includes("not confirmed")) {
          setInfo("Account created! Please check your inbox for a confirmation email, then sign in.");
        } else {
          console.error("[signup] Auto sign-in failed:", authErr.message);
          setInfo("Account created! Please sign in with your new credentials.");
        }
        if (onBack) setTimeout(onBack, 2000);
        return;
      }
      if (!authData?.session) {
        setInfo("Account created! Please confirm your email then sign in.");
        if (onBack) setTimeout(onBack, 2000);
        return;
      }
      let profile = null;
      for (let attempt = 0; attempt < 6; attempt++) {
        const { data: pd } = await supabase.from("profiles").select("*").eq("id", authData.user.id).maybeSingle();
        if (pd) { profile = pd; break; }
        await new Promise(r => setTimeout(r, 500));
      }
      const targetPage =
        role === "parent" ? "parentDashboard" :
        role === "teacher" ? "teacherDashboard" : "dashboard";
      const userData = {
        id: authData.user.id,
        email: email.trim(),
        username: profile?.username || name.trim(),
        role: profile?.role || role,
        grade: profile?.grade || "Grade 9",
        board: "CBSE",
        parentId: profile?.parent_id || null,
        familyId: profile?.family_id || null,
        accessToken: authData.session.access_token,
        accessCbse: false,
        accessSofScience: false,
        accessSofMaths: false,
        accessSofEnglish: false,
        cbseSubjects: [],
        subscriptionPlan: "free",
        accountStatus: "active",
        offerAccess: false,
      };
      if (onLogin) {
        onLogin({ ...userData, _targetPage: targetPage });
      } else {
        localStorage.setItem("tutor_user", JSON.stringify(userData));
        localStorage.setItem("tutor_active_page", targetPage);
        window.location.reload();
      }
    } catch (err) {
      console.error("[signup] Unexpected error:", err.message);
      setError("We couldn't create your account. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  const cardBase = {
    padding: "12px 8px", borderRadius: 10, cursor: "pointer", textAlign: "center",
    display: "flex", flexDirection: "column", alignItems: "center", gap: 5,
    transition: "border-color .15s,background .15s", fontFamily: "inherit",
  };

  const roleIcons = {
    parent: (
      <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
        <circle cx="9" cy="7" r="4"/>
        <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
        <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
      </svg>
    ),
    student: (
      <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M22 10v6M2 10l10-5 10 5-10 5z"/>
        <path d="M6 12v5c3 3 9 3 12 0v-5"/>
      </svg>
    ),
    teacher: (
      <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="2" y="3" width="20" height="14" rx="2"/>
        <path d="M8 21h8"/>
        <path d="M12 17v4"/>
      </svg>
    ),
  };

  return (
    <div className="ait-login-page" data-testid="signup-page">
      <div className="ait-login-shell">

        {/* Left — branding */}
        <div className="ait-login-left">
          <img src={logo} alt="Likhapoha AI" className="ait-login-logo" />
          <h1>Learn smarter with AI.</h1>
          <p>
            Personalized CBSE preparation with AI-powered lessons, quizzes,
            analytics, narration, and doubt solving. Class 5–10.
          </p>
          <div className="ait-feature-list">
            {["Personalized Lessons", "Smart Doubt Solving", "Practice & Tests", "Progress Analytics"].map(f => (
              <div key={f} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                <span style={{ color: "#7c3aed" }}>✦</span>
                <span style={{ fontSize: ".88rem", color: "rgba(255,255,255,.85)" }}>{f}</span>
              </div>
            ))}
          </div>
          <div style={{ marginTop: "auto", paddingTop: 24, fontSize: ".78rem", color: "rgba(255,255,255,.5)" }}>
            Free Tier · No credit card required
          </div>
        </div>

        {/* Right — form */}
        <div className="ait-login-right">
          <div className="ait-form-card" data-testid="signup-form-card">

            <h2 style={{ marginBottom: 4 }}>Create your account</h2>
            <p style={{ marginBottom: 20, color: "var(--text-muted,#64748b)", fontSize: ".88rem" }}>
              Choose your role and get started. Free forever.
            </p>

            {/* Role cards */}
            <div style={{ marginBottom: 20 }}>
              <label style={{ fontSize: ".8rem", fontWeight: 600, color: "var(--text-muted,#64748b)", display: "block", marginBottom: 8 }}>
                I am signing up as *
              </label>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 8 }} data-testid="role-cards">
                {ROLES.map(r => (
                  <button
                    key={r.key}
                    type="button"
                    data-testid={"role-card-" + r.key}
                    onClick={() => { setRole(r.key); setError(""); }}
                    style={{
                      ...cardBase,
                      border: "2px solid " + (role === r.key ? "#7c3aed" : "var(--border,#e2e8f0)"),
                      background: role === r.key ? "rgba(124,58,237,.12)" : "var(--surface2,#f8fafc)",
                    }}
                  >
                    <span style={{ color: role === r.key ? "#7c3aed" : "var(--text-muted,#64748b)" }}>
                      {roleIcons[r.key]}
                    </span>
                    <span style={{ fontWeight: 700, fontSize: ".82rem", color: "var(--text,#1e293b)" }}>{r.label}</span>
                    <span style={{ fontSize: ".67rem", color: "var(--text-muted,#94a3b8)", lineHeight: 1.3 }}>{r.desc}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Fields */}
            <form onSubmit={handleSubmit} noValidate>
              <div style={{ marginBottom: 12 }}>
                <label style={{ fontSize: ".8rem", fontWeight: 600, display: "block", marginBottom: 4 }}>Full Name *</label>
                <input
                  data-testid="signup-name"
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
                  data-testid="signup-email"
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={ev => { setEmail(ev.target.value); setError(""); }}
                  required
                  className="ait-input"
                  style={{ width: "100%", boxSizing: "border-box" }}
                />
              </div>

              <div style={{ marginBottom: 16 }}>
                <label style={{ fontSize: ".8rem", fontWeight: 600, display: "block", marginBottom: 4 }}>Password *</label>
                <div style={{ position: "relative" }}>
                  <input
                    data-testid="signup-password"
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

              {/* Terms */}
              <div style={{ marginBottom: 16, display: "flex", alignItems: "flex-start", gap: 8 }}>
                <input
                  id="signup-terms-cb"
                  type="checkbox"
                  data-testid="signup-terms"
                  checked={agreed}
                  onChange={ev => { setAgreed(ev.target.checked); setError(""); }}
                  style={{ marginTop: 2, flexShrink: 0 }}
                />
                <label htmlFor="signup-terms-cb" style={{ fontSize: ".78rem", color: "var(--text-muted,#64748b)", lineHeight: 1.4 }}>
                  I agree to the{" "}
                  <a href="/terms" target="_blank" rel="noreferrer" style={{ color: "#7c3aed" }}>Terms of Service</a>
                  {" "}and{" "}
                  <a href="/privacy" target="_blank" rel="noreferrer" style={{ color: "#7c3aed" }}>Privacy Policy</a>
                </label>
              </div>

              {error && (
                <div data-testid="signup-error" style={{ color: "#dc2626", fontSize: ".82rem", marginBottom: 12, padding: "8px 12px", background: "rgba(239,68,68,.07)", border: "1px solid #fca5a5", borderRadius: 7 }}>
                  {error}
                </div>
              )}
              {info && (
                <div data-testid="signup-info" style={{ color: "#166534", fontSize: ".82rem", marginBottom: 12, padding: "8px 12px", background: "rgba(34,197,94,.07)", border: "1px solid #86efac", borderRadius: 7 }}>
                  {info}
                </div>
              )}

              <button
                data-testid="signup-submit"
                type="submit"
                disabled={loading}
                className="ait-btn-primary"
                style={{ width: "100%", padding: "11px", borderRadius: 9, fontWeight: 700, fontSize: "1rem", cursor: loading ? "not-allowed" : "pointer", opacity: loading ? 0.7 : 1 }}
              >
                {loading ? "Creating account…" : "Start for Free"}
              </button>

              <div style={{ textAlign: "center", marginTop: 16, fontSize: ".83rem", color: "var(--text-muted,#64748b)" }}>
                Already have an account?{" "}
                <button
                  data-testid="signup-signin-link"
                  type="button"
                  onClick={onBack}
                  style={{ background: "none", border: "none", color: "#7c3aed", fontWeight: 700, cursor: "pointer", fontFamily: "inherit", fontSize: ".83rem" }}
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
