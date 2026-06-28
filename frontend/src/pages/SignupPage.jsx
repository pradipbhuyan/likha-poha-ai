/**
 * SignupPage.jsx — Single-Step Card-Based Signup (Option 1)
 * All new accounts start on Free Tier. No payment or offer code in signup.
 * Business rules: access_cbse=false, role=parent|student|teacher
 */
import { useState } from "react";
import { Eye, EyeOff } from "lucide-react";
import logo from "../assets/AITutorLogo1.png";
import { supabase } from "../api/supabaseClient";
import "./SignupPage.css";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function signInWithGoogle() {
  await supabase.auth.signInWithOAuth({
    provider: "google",
    options: {
      redirectTo: window.location.origin,
      queryParams: { prompt: "select_account" },
    },
  });
}

const ROLES = [
  { key:"parent",  label:"Parent",  desc:"Manage your child's learning and track progress" },
  { key:"student", label:"Student", desc:"Access AI lessons, mock tests and doubt solving" },
];

const GRADES = [
  "Grade 1","Grade 2","Grade 3","Grade 4","Grade 5",
  "Grade 6","Grade 7","Grade 8","Grade 9","Grade 10",
];

export default function SignupPage({ onLogin, onBack, onBackToLogin }) {
  const handleBack = onBackToLogin || onBack;
  const [role, setRole]         = useState("parent");
  const [grade, setGrade]       = useState("Grade 9");
  const [name, setName]         = useState("");
  const [email, setEmail]       = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw]     = useState(false);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState("");
  const [info, setInfo]         = useState("");
  const [settingUp, setSettingUp] = useState(false);
  const [settingUpRole, setSettingUpRole] = useState("");

  function validate() {
    if (!role)               { setError("Please choose a role."); return false; }
    if (!name.trim())        { setError("Full name is required."); return false; }
    if (!email.trim())       { setError("Email address is required."); return false; }
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email.trim())) {
                               setError("Please enter a valid email address."); return false; }
    if (!password)           { setError("Password is required."); return false; }
    if (password.length < 8) { setError("Password must be at least 8 characters."); return false; }
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
        body: JSON.stringify({ role, name: name.trim(), email: email.trim(), password, grade: role === "student" ? grade : undefined }),
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
        if (handleBack) setTimeout(handleBack, 2000);
        return;
      }
      if (!authData?.session) {
        setInfo("Account created! Please confirm your email then sign in.");
        if (handleBack) setTimeout(handleBack, 2000);
        return;
      }
      let profile = null;
      for (let attempt = 0; attempt < 6; attempt++) {
        const { data: pd } = await supabase.from("profiles").select("*").eq("id", authData.user.id).maybeSingle();
        if (pd) { profile = pd; break; }
        await new Promise(r => setTimeout(r, 500));
      }
      const targetPage = role === "parent" ? "parentDashboard" : "dashboard";
      const userData = {
        id: authData.user.id,
        email: email.trim(),
        username: profile?.username || name.trim(),
        role: profile?.role || role,
        grade: profile?.grade || (role === "student" ? grade : "Grade 9"),
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
      localStorage.setItem("tutor_user", JSON.stringify(userData));
      localStorage.setItem("tutor_active_page", targetPage);
      setSettingUp(true);
      setSettingUpRole(role);
      setLoading(false);
      // Show "Setting up your account…" for 1.5s then reload to fresh dashboard
      setTimeout(() => window.location.reload(), 1500);
      return;
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

  };

  // Show account creation screen while setting up
  if (settingUp) {
    return (
      <div className="ait-login-page" data-testid="signup-setting-up" style={{display:"flex",alignItems:"center",justifyContent:"center",minHeight:"100vh",background:"var(--bg,#0f172a)"}}>
        <div style={{textAlign:"center",color:"#fff",padding:32}}>
          <div style={{fontSize:"2rem",marginBottom:16}}>✨</div>
          <h2 style={{margin:"0 0 8px",fontSize:"1.3rem",fontWeight:800}}>Setting up your {settingUpRole} account…</h2>
          <p style={{color:"rgba(255,255,255,.6)",fontSize:".9rem"}}>Just a moment while we get everything ready.</p>
          <div style={{marginTop:20,width:40,height:40,border:"3px solid rgba(255,255,255,.2)",borderTop:"3px solid #7c3aed",borderRadius:"50%",animation:"spin 0.8s linear infinite",margin:"20px auto"}} />
        </div>
      </div>
    );
  }

  return (
    <div className="ait-login-page signup-page-wrapper" data-testid="signup-page">
      <div className="ait-login-shell signup-shell">

        {/* Left — branding */}
        <div className="ait-login-left signup-left-panel">
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

        </div>

        {/* Right — form */}
        <div className="ait-login-right signup-right-panel">
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
              <div style={{ display: "grid", gridTemplateColumns: "repeat(2,1fr)", gap: 10 }} data-testid="role-cards">
                {ROLES.map(r => (
                  <button
                    key={r.key}
                    type="button"
                    data-testid={"role-card-" + r.key}
                    onClick={() => { setRole(r.key); setError(""); }}
                    style={{
                      ...cardBase,
                      border: "2px solid " + (role === r.key ? "#7c3aed" : "var(--border,#e2e8f0)"),
                      background: role === r.key ? "rgba(99,58,210,.85)" : "var(--surface2,#f8fafc)",
                    }}
                  >
                    <span style={{ color: role === r.key ? "#7c3aed" : "var(--text-muted,#64748b)" }}>
                      {roleIcons[r.key]}
                    </span>
                    <span style={{ fontWeight: 700, fontSize: ".82rem", color: role === r.key ? "#fff" : "var(--text,#1e293b)" }}>{r.label}</span>
                    <span style={{ fontSize: ".67rem", color: role === r.key ? "rgba(255,255,255,.75)" : "var(--text-muted,#94a3b8)", lineHeight: 1.3 }}>{r.desc}</span>
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

              {/* Grade selector — shown only for students */}
              {role === "student" && (
                <div style={{ marginBottom: 16 }}>
                  <label style={{ fontSize: ".8rem", fontWeight: 600, display: "block", marginBottom: 4 }}>Grade *</label>
                  <select
                    data-testid="signup-grade"
                    value={grade}
                    onChange={ev => setGrade(ev.target.value)}
                    className="ait-input"
                    style={{ width: "100%", boxSizing: "border-box" }}
                  >
                    {GRADES.map(g => <option key={g} value={g}>{g}</option>)}
                  </select>
                </div>
              )}

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
                style={{ width: "100%", padding: "11px", borderRadius: 9, fontWeight: 700, fontSize: "1rem", cursor: loading ? "not-allowed" : "pointer", opacity: loading ? 0.7 : 1, background: "#6366f1", color: "#fff", border: "none" }}
              >
                {loading ? "Creating account…" : "Start for Free"}
              </button>

              {/* Divider */}
              <div style={{ display: "flex", alignItems: "center", gap: 8, margin: "16px 0 12px" }}>
                <div style={{ flex: 1, height: 1, background: "var(--border,#e2e8f0)" }} />
                <span style={{ fontSize: ".75rem", color: "var(--text-muted,#94a3b8)" }}>or</span>
                <div style={{ flex: 1, height: 1, background: "var(--border,#e2e8f0)" }} />
              </div>

              {/* Google Sign Up */}
              <button
                data-testid="signup-google"
                type="button"
                onClick={signInWithGoogle}
                style={{
                  width: "100%", display: "flex", alignItems: "center", justifyContent: "center",
                  gap: 10, padding: "10px 16px", borderRadius: 10,
                  border: "1px solid #dadce0", background: "#fff", color: "#3c4043",
                  fontSize: ".88rem", fontWeight: 500, cursor: "pointer",
                  fontFamily: "inherit", boxShadow: "0 1px 3px rgba(0,0,0,.08)",
                  marginBottom: 8,
                }}
              >
                <svg width="18" height="18" viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg">
                  <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615Z" fill="#4285F4"/>
                  <path d="M9 18c2.43 0 4.467-.806 5.956-2.184l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18Z" fill="#34A853"/>
                  <path d="M3.964 10.706A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.706V4.962H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.038l3.007-2.332Z" fill="#FBBC05"/>
                  <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.962L3.964 7.294C4.672 5.163 6.656 3.58 9 3.58Z" fill="#EA4335"/>
                </svg>
                Continue with Google
              </button>

              <div style={{ textAlign: "center", marginTop: 16, fontSize: ".83rem", color: "var(--text-muted,#64748b)" }}>
                Already have an account?{" "}
                <button
                  data-testid="signup-signin-link"
                  type="button"
                  onClick={handleBack}
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
