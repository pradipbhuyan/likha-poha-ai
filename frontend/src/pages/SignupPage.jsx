import { useEffect, useState } from "react";
import logoImg from "../assets/AITutorLogo1.png";
import { SUBSCRIPTION_PLANS } from "../config/subscriptionPlans";
import { supabase } from "../api/supabaseClient";
import "./SignupPage.css";

/** Initiates Google OAuth redirect via Supabase. */
async function signInWithGoogle() {
  await supabase.auth.signInWithOAuth({
    provider: "google",
    options: {
      redirectTo: window.location.origin,
      queryParams: { access_type: "offline", prompt: "select_account" },
    },
  });
}

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const PLANS = [
  "free", "starter",
  "family_premium",
].map(k => SUBSCRIPTION_PLANS[k]).filter(Boolean);

// Platform publicly supports Grade 5–10. Grade 11 & 12 hidden until content is fully ready.
// To re-enable: add "Grade 11","Grade 12" back to GRADES array and restore stream picker UI.
import { GRADE_11_12_STREAMS, getSubjectsForStream, isStreamGrade } from "../utils/streamSubjects";

const GRADES = ["Grade 5","Grade 6","Grade 7","Grade 8","Grade 9","Grade 10"];

const PLAN_FILTER_GROUPS = {
  monthly:   ["free", "starter", "family_premium"],
};

function loadRazorpay() {
  return new Promise(resolve => {
    if (window.Razorpay) { resolve(true); return; }
    const s = document.createElement("script");
    s.src = "https://checkout.razorpay.com/v1/checkout.js";
    s.onload = () => resolve(true);
    s.onerror = () => resolve(false);
    document.body.appendChild(s);
  });
}

/** Shared inline styles */
const S = {
  page:    { fontFamily:"-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif",
             background:"#0f172a", color:"#f8fafc", minHeight:"100vh", display:"flex", flexDirection:"column" },
  nav:     { display:"flex", alignItems:"center", justifyContent:"space-between",
             padding:"14px 40px", borderBottom:"1px solid rgba(255,255,255,.06)",
             background:"rgba(15,23,42,.97)", backdropFilter:"blur(12px)",
             position:"sticky", top:0, zIndex:99 },
  brand:   { display:"flex", alignItems:"center", gap:12, fontWeight:700, fontSize:"1.1rem" },
  loginBtn:{ background:"transparent", border:"1px solid #334155", color:"#93c5fd",
             padding:"7px 16px", borderRadius:"8px", fontSize:".85rem", cursor:"pointer",
             fontFamily:"inherit" },
  shell:   { flex:1, display:"grid", gridTemplateColumns:"1fr 1fr" },
  left:    { background:"linear-gradient(140deg,#1e1b4b 0%,#0f172a 55%,#1a3a5c 100%)",
             padding:"48px 52px", display:"flex", flexDirection:"column",
             justifyContent:"center", position:"relative", overflow:"hidden" },
  right:   { padding:"48px 52px", display:"flex", flexDirection:"column",
             justifyContent:"center", background:"#0f172a" },
  input:   { width:"100%", background:"#111827", border:"2px solid #1e293b",
             borderRadius:"11px", padding:"13px 15px", color:"#f8fafc",
             fontFamily:"inherit", fontSize:".93rem", outline:"none" },
  select:  { width:"100%", background:"#111827", border:"2px solid #1e293b",
             borderRadius:"11px", padding:"13px 15px", color:"#f8fafc",
             fontFamily:"inherit", fontSize:".93rem", outline:"none" },
  primBtn: { width:"100%", padding:"14px", borderRadius:"11px", border:"none",
             background:"linear-gradient(135deg,#2563eb,#7c3aed)", color:"#fff",
             fontSize:".95rem", fontWeight:700, cursor:"pointer", fontFamily:"inherit" },
  errorBox:{ background:"rgba(239,68,68,.1)", border:"1px solid rgba(239,68,68,.3)",
             color:"#fca5a5", borderRadius:"10px", padding:"11px 14px",
             fontSize:".87rem", marginBottom:"12px" },
};

/** Left panel logo + brand */
function LeftBrand() {
  return (
    <div style={{ display:"flex", alignItems:"center", gap:16, marginBottom:36 }}>
      <img src={logoImg} alt="LikhaPoha AI"
        style={{ width:72, height:72, borderRadius:16, objectFit:"cover",
                 background:"#fff", boxShadow:"0 4px 20px rgba(37,99,235,.35)" }} />
      <div>
        <div style={{ fontSize:"1rem", fontWeight:700, color:"#f1f5f9", lineHeight:1.2 }}>
          Your Personal Tutor
        </div>
        <div style={{ fontSize:".82rem", color:"#94a3b8", marginTop:3 }}>
          AI Powered
        </div>
      </div>
    </div>
  );
}

/** Visual step progress bar */
function StepBar({ step }) {
  const dots = [1,2,3];
  return (
    <div style={{ display:"flex", alignItems:"center", gap:0, marginBottom:8 }}>
      {dots.map((n, i) => (
        <div key={n} style={{ display:"flex", alignItems:"center", flex: i < 2 ? "1 0 auto" : "0 0 auto" }}>
          <div style={{
            width:28, height:28, borderRadius:"50%", display:"flex", alignItems:"center",
            justifyContent:"center", fontSize:".72rem", fontWeight:700, flexShrink:0,
            background: n < step ? "#10b981" : n === step ? "#2563eb" : "#1e293b",
            color: n <= step ? "#fff" : "#475569",
            border: n > step ? "2px solid #334155" : "none",
            boxShadow: n === step ? "0 0 0 4px rgba(37,99,235,.22)" : "none",
          }}>
            {n < step ? "✓" : n}
          </div>
          {i < 2 && (
            <div style={{ height:2, flex:1, background: n < step ? "#10b981" : "#1e293b" }} />
          )}
        </div>
      ))}
    </div>
  );
}

function StepLabels({ step }) {
  const labels = ["Role","Your Details","Plan & Pay"];
  return (
    <div style={{ display:"flex", justifyContent:"space-between", marginBottom:32 }}>
      {labels.map((l,i) => (
        <span key={l} style={{
          fontSize:".67rem", fontWeight: i+1 === step ? 700 : 400,
          color: i+1 < step ? "#10b981" : i+1 === step ? "#93c5fd" : "#475569",
        }}>
          {i+1 < step ? `✓ ${l}` : l}
        </span>
      ))}
    </div>
  );
}

/** Trust bullet row */
function TrustRow({ icon, title, sub, bg }) {
  return (
    <div style={{ display:"flex", alignItems:"flex-start", gap:11 }}>
      <div style={{ width:34, height:34, borderRadius:9, background:bg,
                    display:"flex", alignItems:"center", justifyContent:"center",
                    fontSize:".95rem", flexShrink:0 }}>{icon}</div>
      <div>
        <div style={{ fontSize:".84rem", color:"#e2e8f0", fontWeight:600, marginBottom:2 }}>{title}</div>
        <div style={{ fontSize:".75rem", color:"#64748b" }}>{sub}</div>
      </div>
    </div>
  );
}

export default function SignupPage({ onBackToLogin, onLogin, initialPlan }) {
  // Read URL params once at init time (lazy state) — avoids useEffect setState pattern
  const _urlParams = new URLSearchParams(window.location.search);
  const _urlCode = (_urlParams.get("code") || "").toUpperCase();
  const _urlRole = (_urlParams.get("role") || "").toLowerCase();
  const _fromLink = _urlCode.length === 8;
  const _validRoles = ["parent", "student", "teacher"];

  const [step, setStep] = useState(() => (_fromLink && _validRoles.includes(_urlRole)) ? "form" : "role");
  const [role, setRole] = useState(() => (_fromLink && _validRoles.includes(_urlRole)) ? _urlRole : "");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [grade, setGrade] = useState("Grade 9");
  const [school, setSchool] = useState("");
  const [planKey, setPlanKey] = useState(initialPlan || "starter");
  const [planFilter, setPlanFilter] = useState("monthly");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  // signupMode: "free" | "pay" | "offer"
  // Default: "free" (no payment or offer code required for basic access)
  const [signupMode, setSignupMode] = useState(_fromLink ? "offer" : "free");
  const [useOfferCode, setUseOfferCode] = useState(_fromLink);
  const [offerCodeInput, setOfferCodeInput] = useState(_fromLink ? _urlCode : "");
  const [password, setPassword] = useState("");
  const [passwordSetLink, setPasswordSetLink] = useState("");
  const [showSignupPassword, setShowSignupPassword] = useState(false);
  const [stream, setStream] = useState("");
  const [settingUp, setSettingUp] = useState(false); // "Setting up your dashboard..." screen
  const [settingUpRole, setSettingUpRole] = useState("");

  useEffect(() => { loadRazorpay(); }, []);

  const selectedPlan = PLANS.find(p => p.key === planKey) || PLANS[1];
  const visiblePlans = PLANS.filter(p => PLAN_FILTER_GROUPS[planFilter]?.includes(p.key));

  const ROLES = [
    { r:"parent",  icon:"👨‍👩‍👧", label:"Parent",
      desc:"Manage your child's learning, track progress and weak areas, and activate subscriptions" },
    { r:"student", icon:"🎓", label:"Student",
      desc:"Access CBSE AI lessons, instant doubt solving, mock tests, and your learning analytics" },
    { r:"teacher", icon:"📋", label:"Teacher",
      desc:"Monitor assigned students, view their progress reports, and provide personalised guidance" },
  ];

  async function handleFreeSignup(e) {
    if (e && e.preventDefault) e.preventDefault();
    setError("");
    if (!role) { setError("Please select your role first."); setStep("role"); return; }
    if (!name.trim() || !email.trim()) { setError("Please fill in your name and email."); return; }
    if (password && password.length > 0 && password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/auth/signup-free`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          role, name: name.trim(), email: email.trim(),
          grade: role === "student" ? grade : undefined,
          school: role === "teacher" ? school.trim() : undefined,
          password: password.trim() || undefined,
        }),
      });
      const data = await res.json();
      if (!res.ok || !data.success) {
        setError(data.detail || data.message || "Could not create account. Please try again.");
        return;
      }
      // Direct-login flow: sign in immediately if password was provided
      if (password.trim() && onLogin) {
        await supabase.auth.signOut().catch(() => {});
        const { data: authData, error: authErr } = await supabase.auth.signInWithPassword({
          email: email.trim(), password: password.trim(),
        });
        if (!authErr && authData.session) {
          const signupRole = role;
          setSettingUpRole(signupRole);
          setSettingUp(true);
          setLoading(false);
          let profile = null;
          for (let attempt = 0; attempt < 6; attempt++) {
            const { data: pd } = await supabase.from("profiles").select("*").eq("id", authData.user.id).maybeSingle();
            if (pd) { profile = pd; break; }
            await new Promise(r => setTimeout(r, 500));
          }
          const targetPage = signupRole === "parent" ? "parentDashboard" : signupRole === "teacher" ? "teacherDashboard" : "dashboard";
          const userData = {
            id: authData.user.id,
            email: email.trim(),
            username: profile ? (profile.username || name.trim()) : name.trim(),
            role: profile ? profile.role : signupRole,
            grade: profile ? (profile.grade || grade || "Grade 9") : (grade || "Grade 9"),
            board: "CBSE",
            parentId: profile?.parent_id || null,
            familyId: profile?.family_id || null,
            accessToken: authData.session.access_token,
            accessCbse: false, // Free Tier
            accessSofScience: false, accessSofMaths: false, accessSofEnglish: false,
            cbseSubjects: [],
            subscriptionPlan: "free",
            accountStatus: "active",
            offerAccess: false,
          };
          localStorage.setItem("tutor_user", JSON.stringify(userData));
          localStorage.setItem("tutor_active_page", targetPage);
          setTimeout(() => window.location.reload(), 1800);
          return;
        }
        setError("Account created but auto-login failed. Please log in manually.");
      }
      if (data.password_set_link) setPasswordSetLink(data.password_set_link);
      setStep("done");
    } catch (err) {
      setError(err.message || "Signup failed. Please try again.");
    } finally { setLoading(false); }
  }

  async function handleOfferCodeSignup(e) {
    if (e && e.preventDefault) e.preventDefault();
    setError("");
    if (!role) { setError("Please select your role first."); setStep("role"); return; }
    if (!name.trim() || !email.trim()) { setError("Please fill in your name and email."); return; }
    if (offerCodeInput.trim().length !== 8) { setError("Offer code must be exactly 8 characters."); return; }
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/auth/signup-with-offer-code`, {
        method:"POST", headers:{"Content-Type":"application/json"},
        body: JSON.stringify({
          role, name:name.trim(), email:email.trim(),
          offer_code:offerCodeInput.trim().toUpperCase(),
          grade: role==="student" ? grade : undefined,
          school: role==="teacher" ? school.trim() : undefined,
          password: password.trim() || undefined,
          // Pass stream-derived subjects so backend saves them to cbse_subjects
          cbse_subjects: (role==="student" && isStreamGrade(grade) && stream)
            ? getSubjectsForStream(stream)
            : undefined,
        }),
      });
      const data = await res.json();
      if (!res.ok || !data.success) {
        setError(data.detail || data.message || "Could not create account. Please check your offer code.");
        return;
      }
      // Direct-login flow: sign in → build user from form data → store in localStorage → reload
      // Most reliable approach — bypasses all profile-fetch timing/race conditions.
      // On reload, App.jsx reads tutor_user from localStorage and routes to correct dashboard.
      if (password.trim() && onLogin) {
        await supabase.auth.signOut().catch(() => {});
        const { data: authData, error: authErr } = await supabase.auth.signInWithPassword({
          email: email.trim(),
          password: password.trim(),
        });

        if (!authErr && authData.session) {
          // Show the "Setting you up..." screen immediately
          const signupRole = role;
          setSettingUpRole(signupRole);
          setSettingUp(true);
          setLoading(false);

          // Best-effort profile fetch (up to 3s) — richer data if available
          let profile = null;
          for (let attempt = 0; attempt < 6; attempt++) {
            const { data: pd } = await supabase
              .from("profiles").select("*").eq("id", authData.user.id).maybeSingle();
            if (pd) { profile = pd; break; }
            await new Promise(r => setTimeout(r, 500));
          }

          const targetPage =
            signupRole === "parent"  ? "parentDashboard" :
            signupRole === "teacher" ? "teacherDashboard" :
            "dashboard";

          // Build user object (profile if fetched, else fallback from form data)
          const userData = {
            id: authData.user.id,
            email: email.trim(),
            username: profile ? (profile.username || name.trim()) : name.trim(),
            role: profile ? profile.role : signupRole,
            grade: profile ? (profile.grade || grade || "Grade 9") : (grade || "Grade 9"),
            board: profile ? (profile.board || "CBSE") : "CBSE",
            parentId: profile?.parent_id || null,
            familyId: profile?.family_id || null,
            accessToken: authData.session.access_token,
            accessCbse: profile ? !!profile.access_cbse : false,
            accessSofScience: false,
            accessSofMaths: false,
            accessSofEnglish: false,
            cbseSubjects: profile && Array.isArray(profile.cbse_subjects) ? profile.cbse_subjects : [],
            dailyTokenLimit: profile?.daily_token_limit || null,
            monthlyTokenLimit: profile?.monthly_token_limit || null,
            subscriptionPlan: profile ? (profile.subscription_plan || "free") : "free",
            accountStatus: profile ? (profile.account_status || "active") : "active",
            offerAccess: true,  // they just redeemed a valid offer code
          };

          // Persist to localStorage so App.jsx reads it on reload
          localStorage.setItem("tutor_user", JSON.stringify(userData));
          localStorage.setItem("tutor_active_page", targetPage);

          // Reload — App.jsx reads tutor_user + active_page → routes to correct dashboard
          setTimeout(() => window.location.reload(), 1800);
          return;
        }

        // Sign-in failed — fall through to done screen with set-password link
        setError("Account created but auto-login failed. Please log in manually.");
      }
      if (data.password_set_link) setPasswordSetLink(data.password_set_link);
      setStep("done");
    } catch (err) {
      setError(err.message || "Signup failed. Please try again.");
    } finally { setLoading(false); }
  }

  async function handlePayAndSignup(e) {
    e.preventDefault();
    setError("");
    if (!name.trim() || !email.trim()) { setError("Please fill in all required fields."); return; }
    setLoading(true);
    try {
      const orderRes = await fetch(`${API_BASE}/api/auth/signup-order`, {
        method:"POST", headers:{"Content-Type":"application/json"},
        body: JSON.stringify({ email:email.trim(), plan_key:planKey }),
      });
      const orderData = await orderRes.json();
      if (!orderRes.ok || !orderData.success) {
        setError(orderData.detail || orderData.message || "Could not initiate payment.");
        return;
      }
      await loadRazorpay();
      await new Promise((resolve, reject) => {
        const rzp = new window.Razorpay({
          key: orderData.key_id, amount: orderData.amount*100, currency: orderData.currency,
          name:"LikhaPoha AI", description:`${selectedPlan.label} Plan`,
          order_id: orderData.order_id,
          prefill:{ name:name.trim(), email:email.trim() },
          theme:{ color:"#2563eb" },
          handler: async function(response) {
            try {
              const completeRes = await fetch(`${API_BASE}/api/auth/complete-signup`, {
                method:"POST", headers:{"Content-Type":"application/json"},
                body: JSON.stringify({
                  role, name:name.trim(), email:email.trim(), plan_key:planKey,
                  razorpay_order_id:response.razorpay_order_id,
                  razorpay_payment_id:response.razorpay_payment_id,
                  razorpay_signature:response.razorpay_signature,
                  grade: role==="student" ? grade : undefined,
                  school: role==="teacher" ? school.trim() : undefined,
                }),
              });
              const completeData = await completeRes.json();
              if (!completeRes.ok || !completeData.success) {
                setError(completeData.detail || completeData.message || "Account creation failed after payment.");
                reject(new Error("complete-signup failed")); return;
              }
              setStep("done"); resolve();
            } catch(err) {
              setError("Account creation failed. Contact support with payment ID: "+response.razorpay_payment_id);
              reject(err);
            }
          },
          modal:{ ondismiss:() => reject(new Error("dismissed")) },
        });
        rzp.open();
      });
    } catch(err) {
      if (err.message !== "dismissed") setError(err.message || "Signup failed. Please try again.");
    } finally { setLoading(false); }
  }

  const stepNum = step === "role" ? 1 : step === "form" ? 2 : step === "plan" ? 3 : 4;

  const glow1 = { position:"absolute", width:380, height:380, borderRadius:"50%",
                  background:"radial-gradient(circle,rgba(99,102,241,.18) 0%,transparent 70%)",
                  top:-90, left:-90, pointerEvents:"none" };
  const glow2 = { position:"absolute", width:260, height:260, borderRadius:"50%",
                  background:"radial-gradient(circle,rgba(16,185,129,.13) 0%,transparent 70%)",
                  bottom:-70, right:-50, pointerEvents:"none" };

  /* ── SETTING UP SCREEN — shown while storing session + waiting for reload ── */
  if (settingUp) {
    const dashboardLabel =
      settingUpRole === "parent"  ? "Parent Dashboard" :
      settingUpRole === "teacher" ? "Teacher Dashboard" :
      "Student Dashboard";
    const roleIcon =
      settingUpRole === "parent"  ? "👨‍👩‍👧" :
      settingUpRole === "teacher" ? "📋" : "🎓";
    return (
      <div style={{ ...S.page, alignItems:"center", justifyContent:"center", gap:28 }}>
        {/* Pulsing ring spinner */}
        <div style={{
          width:72, height:72, borderRadius:"50%",
          border:"5px solid rgba(99,102,241,.2)",
          borderTopColor:"#6366f1",
          animation:"spin 0.9s linear infinite",
        }} />
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>

        <div style={{ textAlign:"center" }}>
          <div style={{ fontSize:"2.8rem", marginBottom:10 }}>{roleIcon}</div>
          <h2 style={{ fontSize:"1.6rem", fontWeight:900, marginBottom:8, color:"#f8fafc" }}>
            Setting up your account…
          </h2>
          <p style={{ color:"#94a3b8", fontSize:"1rem", marginBottom:6 }}>
            You will be taken to your{" "}
            <strong style={{ color:"#a5b4fc" }}>{dashboardLabel}</strong>{" "}
            in just a moment.
          </p>
          <p style={{ color:"#475569", fontSize:".82rem" }}>
            Please do not close this tab.
          </p>
        </div>
      </div>
    );
  }

  /* ── DONE SCREEN ── */
  if (step === "done") {
    return (
      <div style={S.page}>
        <nav style={S.nav}>
          <div style={S.brand}>
            <img src={logoImg} alt="LikhaPoha AI"
              style={{ width:38, height:38, borderRadius:9, objectFit:"cover", background:"#fff" }} />
            LikhaPoha AI
          </div>
        </nav>
        <div style={{ flex:1, display:"flex", alignItems:"center", justifyContent:"center", padding:"40px 20px" }}>
          <div style={{ width:"100%", maxWidth:520, textAlign:"center" }}>
            <div style={{ fontSize:"4rem", marginBottom:20 }}>✅</div>
            <h2 style={{ fontSize:"1.8rem", fontWeight:900, marginBottom:14 }}>
              {useOfferCode ? "Account Created!" : "Payment Confirmed!"}
            </h2>
            {useOfferCode && passwordSetLink && (
              <div style={{ background:"rgba(16,185,129,.15)", border:"1px solid rgba(16,185,129,.4)",
                            borderRadius:12, padding:"14px 18px", marginBottom:20,
                            fontSize:".9rem", color:"#6ee7b7", textAlign:"center" }}>
                ✅ Account ready! Click below to set your password:
                <br /><br />
                <a href={passwordSetLink}
                  style={{ display:"inline-block", background:"linear-gradient(135deg,#059669,#0d9488)",
                           color:"#fff", borderRadius:10, padding:"11px 24px",
                           fontWeight:700, textDecoration:"none", fontSize:"1rem" }}>
                  🔑 Set My Password Now
                </a>
              </div>
            )}
            {useOfferCode && !passwordSetLink && (
              <div style={{ background:"rgba(16,185,129,.15)", border:"1px solid rgba(16,185,129,.4)",
                            borderRadius:12, padding:"14px 18px", marginBottom:20,
                            fontSize:".9rem", color:"#6ee7b7", textAlign:"left" }}>
                ✅ Account created! Check your email for a <strong style={{ color:"#f8fafc" }}>Set Password</strong> link.
              </div>
            )}
            {!useOfferCode && (
              <p style={{ color:"#cbd5e1", lineHeight:1.7, marginBottom:28 }}>
                Payment confirmed. Check your email for a verification link to set your password and log in.
              </p>
            )}
            <button onClick={onBackToLogin}
              style={{ ...S.primBtn, width:"auto", padding:"13px 36px" }}>
              Go to Login →
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={S.page}>
      {/* NAV */}
      <nav style={S.nav}>
        <div style={S.brand}>
          <img src={logoImg} alt="LikhaPoha AI"
            style={{ width:38, height:38, borderRadius:9, objectFit:"cover", background:"#fff" }} />
          LikhaPoha AI
        </div>
        <button style={S.loginBtn} onClick={onBackToLogin}>
          Already have an account? Login
        </button>
      </nav>

      {/* SPLIT SHELL */}
      <div className="signup-shell" style={S.shell}>

        {/* ── LEFT PANEL ── */}
        <div className="signup-left-panel" style={S.left}>
          <div style={glow1} />
          <div style={glow2} />
          <div style={{ position:"relative", zIndex:1 }}>
            <LeftBrand />
            {stepNum > 1 && (
              <>
                <StepBar step={stepNum} />
                <StepLabels step={stepNum} />
              </>
            )}
            {step === "role" && (
              <>
                <div style={{ fontSize:"clamp(1.7rem,3vw,2.3rem)", fontWeight:900,
                              lineHeight:1.15, marginBottom:12 }}>
                  Your child's{" "}
                  <span style={{ background:"linear-gradient(135deg,#6366f1,#10b981)",
                                 WebkitBackgroundClip:"text", WebkitTextFillColor:"transparent" }}>
                    personal AI tutor
                  </span>
                  {" "}is ready.
                </div>
                <p style={{ color:"#94a3b8", fontSize:".92rem", lineHeight:1.7, marginBottom:28 }}>
                  Step-wise NCERT lessons, instant doubt answers, mock tests, and real-time parent tracking.
                </p>
                <div style={{ display:"flex", flexDirection:"column", gap:11 }}>
                  <TrustRow icon="📚" bg="rgba(37,99,235,.2)" title="700+ Chapters covered" sub="All CBSE subjects, Grade 5–10" />
                  <TrustRow icon="🧠" bg="rgba(16,185,129,.2)" title="70,000+ Practice Questions" sub="Instantly available for mock tests" />
                  <TrustRow icon="🔒" bg="rgba(124,58,237,.2)" title="Safe for children" sub="Academic guardrail blocks off-topic content" />
                  <TrustRow icon="👨‍👩‍👧" bg="rgba(245,158,11,.2)" title="Real-time parent insights" sub="Weak-area alerts, score trends, usage tracking" />
                </div>
              </>
            )}
            {step === "form" && (
              <>
                <div style={{ fontSize:"clamp(1.6rem,3vw,2.2rem)", fontWeight:900, lineHeight:1.15, marginBottom:12 }}>
                  Almost there —{" "}
                  <span style={{ background:"linear-gradient(135deg,#6366f1,#10b981)",
                                 WebkitBackgroundClip:"text", WebkitTextFillColor:"transparent" }}>
                    tell us about yourself
                  </span>
                </div>
                <p style={{ color:"#94a3b8", fontSize:".9rem", lineHeight:1.7, marginBottom:24 }}>
                  Your account will be ready in 2 minutes.
                </p>
                <div style={{ display:"flex", flexDirection:"column", gap:11 }}>
                  <TrustRow icon="🔒" bg="rgba(37,99,235,.2)" title="Your data is private" sub="We never share your details with third parties" />
                  <TrustRow icon="📧" bg="rgba(16,185,129,.2)" title="Verify your email" sub="A link to set your password will be sent after signup" />
                  <TrustRow icon="🚀" bg="rgba(124,58,237,.2)" title="Access in minutes" sub="Start your first lesson right after verifying" />
                </div>
              </>
            )}
            {step === "plan" && (
              <>
                <div style={{ fontSize:"clamp(1.6rem,3vw,2.2rem)", fontWeight:900, lineHeight:1.15, marginBottom:12 }}>
                  Choose how long{" "}
                  <span style={{ background:"linear-gradient(135deg,#6366f1,#10b981)",
                                 WebkitBackgroundClip:"text", WebkitTextFillColor:"transparent" }}>
                    you want to learn
                  </span>
                </div>
                <p style={{ color:"#94a3b8", fontSize:".9rem", lineHeight:1.7, marginBottom:24 }}>
                  All plans include unlimited CBSE lessons, doubt solving, and mock tests.
                </p>
                <div style={{ display:"flex", flexDirection:"column", gap:11 }}>
                  <TrustRow icon="✅" bg="rgba(16,185,129,.2)" title="Instant access after payment" sub="Set your password and start studying right away" />
                  <TrustRow icon="💳" bg="rgba(37,99,235,.2)" title="Secure Razorpay checkout" sub="UPI, cards, net banking accepted" />
                  <TrustRow icon="🎁" bg="rgba(124,58,237,.2)" title="Have an offer code?" sub="Skip payment and activate with your code instead" />
                  <TrustRow icon="📞" bg="rgba(245,158,11,.2)" title="Need help?" sub="Contact us to activate your plan manually" />
                </div>
              </>
            )}
          </div>
        </div>

        {/* ── RIGHT PANEL ── */}
        <div className="signup-right-panel" style={S.right}>

          {/* STEP 1 — Role selection */}
          {step === "role" && (
            <div>
              <p style={{ fontSize:".71rem", fontWeight:700, letterSpacing:".1em",
                          textTransform:"uppercase", color:"#6366f1", marginBottom:8 }}>
                Step 1 of 3 — Choose your role
              </p>
              <h2 style={{ fontSize:"1.8rem", fontWeight:900, marginBottom:6 }}>
                Welcome! I am signing up as a…
              </h2>
              <p style={{ color:"#64748b", fontSize:".9rem", marginBottom:28 }}>
                Select your role to personalise your experience
              </p>
              <div style={{ display:"flex", flexDirection:"column", gap:14 }}>
                {ROLES.map(({ r, icon, label, desc }) => (
                  <div key={r}
                    onClick={() => { setRole(r); setStep("form"); setError(""); }}
                    style={{ display:"flex", alignItems:"center", gap:18,
                             background: role===r ? "rgba(99,102,241,.1)" : "#111827",
                             border:`2px solid ${role===r?"#6366f1":"#1e293b"}`,
                             borderRadius:16, padding:"20px 22px", cursor:"pointer",
                             transition:"all .18s" }}
                    onMouseEnter={e => { e.currentTarget.style.borderColor="#6366f1"; e.currentTarget.style.transform="translateX(4px)"; }}
                    onMouseLeave={e => { e.currentTarget.style.borderColor=role===r?"#6366f1":"#1e293b"; e.currentTarget.style.transform="none"; }}
                  >
                    <div style={{ width:50, height:50, borderRadius:13, flexShrink:0,
                                  display:"flex", alignItems:"center", justifyContent:"center",
                                  fontSize:"1.4rem",
                                  background: r==="parent"  ? "linear-gradient(135deg,rgba(37,99,235,.3),rgba(37,99,235,.1))"
                                            : r==="student" ? "linear-gradient(135deg,rgba(16,185,129,.3),rgba(16,185,129,.1))"
                                            : "linear-gradient(135deg,rgba(245,158,11,.3),rgba(245,158,11,.1))" }}>
                      {icon}
                    </div>
                    <div style={{ flex:1 }}>
                      <div style={{ fontWeight:700, fontSize:"1rem", color:"#f1f5f9", marginBottom:3 }}>{label}</div>
                      <div style={{ fontSize:".8rem", color:"#64748b", lineHeight:1.5 }}>{desc}</div>
                    </div>
                    <div style={{ fontSize:"1.2rem", color:"#334155", flexShrink:0 }}>→</div>
                  </div>
                ))}
              </div>
              <p style={{ textAlign:"center", marginTop:20, color:"#475569", fontSize:".78rem" }}>
                🔒 Secure Razorpay checkout &nbsp;·&nbsp;
                <span style={{ color:"#6366f1", cursor:"pointer" }} onClick={() => { setUseOfferCode(true); setStep("form"); }}>
                  Have an offer code? Skip payment →
                </span>
              </p>
            </div>
          )}

          {/* STEP 2 — Details form */}
          {step === "form" && (
            <div>
              <p style={{ fontSize:".71rem", fontWeight:700, letterSpacing:".1em",
                          textTransform:"uppercase", color:"#6366f1", marginBottom:8 }}>
                {useOfferCode ? "Step 2 of 2 — Your Details" : "Step 2 of 3 — Account Details"}
              </p>
              <h2 style={{ fontSize:"1.75rem", fontWeight:900, marginBottom:6 }}>Create your account</h2>

              {/* Google OAuth quick-signup */}
              <button
                type="button"
                onClick={signInWithGoogle}
                style={{
                  width: "100%",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 10,
                  padding: "12px 16px",
                  borderRadius: 11,
                  border: "1.5px solid #334155",
                  background: "transparent",
                  color: "#f8fafc",
                  fontSize: "0.9rem",
                  fontWeight: 600,
                  cursor: "pointer",
                  fontFamily: "inherit",
                  marginBottom: 16,
                  transition: "background 0.15s",
                }}
                onMouseEnter={e => e.currentTarget.style.background = "rgba(99,102,241,.12)"}
                onMouseLeave={e => e.currentTarget.style.background = "transparent"}
              >
                <svg width="18" height="18" viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg">
                  <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615Z" fill="#4285F4"/>
                  <path d="M9 18c2.43 0 4.467-.806 5.956-2.184l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18Z" fill="#34A853"/>
                  <path d="M3.964 10.706A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.706V4.962H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.038l3.007-2.332Z" fill="#FBBC05"/>
                  <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.962L3.964 7.294C4.672 5.163 6.656 3.58 9 3.58Z" fill="#EA4335"/>
                </svg>
                Continue with Google
              </button>
              <div style={{ textAlign: "center", color: "#475569", fontSize: "0.78rem", marginBottom: 16 }}>
                — or sign up with email —
              </div>

              {/* Signup mode selector — Free (default), Pay, Offer Code */}
              <div style={{ display:"flex", gap:0, background:"#111827", border:"1px solid #1e293b",
                            borderRadius:10, padding:3, marginBottom:20 }}>
                <button
                  onClick={() => { setSignupMode("free"); setUseOfferCode(false); setError(""); }}
                  style={{ flex:1, padding:"9px 6px", borderRadius:8, border:"none",
                           background: signupMode==="free" ? "linear-gradient(135deg,#10b981,#059669)" : "transparent",
                           color: signupMode==="free" ? "#fff" : "#64748b",
                           fontFamily:"inherit", fontSize:".78rem", fontWeight:600, cursor:"pointer" }}>
                  🆓 Start Free
                </button>
                <button
                  onClick={() => { setSignupMode("pay"); setUseOfferCode(false); setError(""); }}
                  style={{ flex:1, padding:"9px 6px", borderRadius:8, border:"none",
                           background: signupMode==="pay" ? "linear-gradient(135deg,#2563eb,#7c3aed)" : "transparent",
                           color: signupMode==="pay" ? "#fff" : "#64748b",
                           fontFamily:"inherit", fontSize:".78rem", fontWeight:600, cursor:"pointer" }}>
                  💳 Pay & Sign Up
                </button>
                <button
                  onClick={() => { setSignupMode("offer"); setUseOfferCode(true); setError(""); }}
                  style={{ flex:1, padding:"9px 6px", borderRadius:8, border:"none",
                           background: signupMode==="offer" ? "linear-gradient(135deg,#059669,#0d9488)" : "transparent",
                           color: signupMode==="offer" ? "#fff" : "#64748b",
                           fontFamily:"inherit", fontSize:".78rem", fontWeight:600, cursor:"pointer" }}>
                  🎟️ Offer Code
                </button>
              </div>
              <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
                <div>
                  <label style={{ display:"block", fontSize:".85rem", fontWeight:600, color:"#cbd5e1", marginBottom:7 }}>Full Name *</label>
                  <input style={S.input} type="text" placeholder="Enter your full name"
                    value={name} onChange={e => setName(e.target.value)} />
                </div>
                <div>
                  <label style={{ display:"block", fontSize:".85rem", fontWeight:600, color:"#cbd5e1", marginBottom:7 }}>Email Address *</label>
                  <input style={S.input} type="email" placeholder="your@email.com"
                    value={email} onChange={e => setEmail(e.target.value)} />
                </div>
                {role === "student" && (
                  <>
                  <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:13 }}>
                    <div>
                      <label style={{ display:"block", fontSize:".85rem", fontWeight:600, color:"#cbd5e1", marginBottom:7 }}>Class *</label>
                      <select style={S.select} value={grade} onChange={e => { setGrade(e.target.value); setStream(""); }}>
                        {GRADES.map(g => <option key={g}>{g}</option>)}
                      </select>
                    </div>
                    <div>
                      <label style={{ display:"block", fontSize:".85rem", fontWeight:600, color:"#cbd5e1", marginBottom:7 }}>Board</label>
                      <select style={S.select}><option>CBSE</option></select>
                    </div>
                  </div>
                  {isStreamGrade(grade) && (
                    <div>
                      <label style={{ display:"block", fontSize:".85rem", fontWeight:600, color:"#cbd5e1", marginBottom:7 }}>Stream *</label>
                      <select
                        style={S.select}
                        value={stream}
                        onChange={e => setStream(e.target.value)}
                        required
                      >
                        <option value="">— Select your stream —</option>
                        {GRADE_11_12_STREAMS.map(s => <option key={s}>{s}</option>)}
                      </select>
                      <small style={{ color:"#64748b", fontSize:".75rem", marginTop:4, display:"block" }}>
                        Your stream determines which subjects appear in your lessons.
                      </small>
                    </div>
                  )}
                  </>
                )}
                {role === "teacher" && (
                  <div>
                    <label style={{ display:"block", fontSize:".85rem", fontWeight:600, color:"#cbd5e1", marginBottom:7 }}>School Name</label>
                    <input style={S.input} type="text" placeholder="Name of your school (optional)"
                      value={school} onChange={e => setSchool(e.target.value)} />
                  </div>
                )}
                {/* Free signup: password field (optional) */}
                {signupMode === "free" && (
                  <div>
                    <label style={{ display:"block", fontSize:".85rem", fontWeight:600, color:"#cbd5e1", marginBottom:7 }}>
                      Password <span style={{ color:"#64748b", fontWeight:400 }}>(optional — or we'll email you a link)</span>
                    </label>
                    <div style={{ position:"relative" }}>
                      <input
                        style={{ ...S.input, paddingRight:40 }}
                        type={showSignupPassword ? "text" : "password"}
                        placeholder="Set your password (min 8 characters)"
                        value={password}
                        onChange={e => setPassword(e.target.value)}
                      />
                      <button type="button"
                        onClick={() => setShowSignupPassword(p => !p)}
                        style={{ position:"absolute", right:10, top:"50%", transform:"translateY(-50%)", background:"none", border:"none", cursor:"pointer", color:"#64748b", fontSize:"1.1rem", padding:0, lineHeight:1 }}>
                        {showSignupPassword ? "🙈" : "👁️"}
                      </button>
                    </div>
                    <small style={{ color:"#64748b", fontSize:".75rem" }}>
                      Enter a password to log in instantly, or skip and we'll email you a login link.
                    </small>
                  </div>
                )}

                {/* Offer code fields */}
                {signupMode === "offer" && (
                  <>
                    <div>
                      <label style={{ display:"block", fontSize:".85rem", fontWeight:600, color:"#cbd5e1", marginBottom:7 }}>
                        Offer Code *
                      </label>
                      <input
                        style={{ ...S.input, fontFamily:"monospace", letterSpacing:4, textTransform:"uppercase", fontSize:"1.1rem", textAlign:"center" }}
                        type="text" maxLength={8} placeholder="XXXXXXXX"
                        value={offerCodeInput}
                        onChange={e => setOfferCodeInput(e.target.value.toUpperCase())}
                      />
                    </div>
                    <div>
                      <label style={{ display:"block", fontSize:".85rem", fontWeight:600, color:"#cbd5e1", marginBottom:7 }}>
                        Password *
                      </label>
                      <div style={{ position:"relative" }}>
                        <input
                          style={{ ...S.input, paddingRight:40 }}
                          type={showSignupPassword ? "text" : "password"}
                          placeholder="Set your password (min 8 characters)"
                          value={password}
                          onChange={e => setPassword(e.target.value)}
                          minLength={8}
                        />
                        <button type="button"
                          onClick={() => setShowSignupPassword(p => !p)}
                          style={{ position:"absolute", right:10, top:"50%", transform:"translateY(-50%)", background:"none", border:"none", cursor:"pointer", color:"#64748b", fontSize:"1.1rem", padding:0, lineHeight:1 }}>
                          {showSignupPassword ? "🙈" : "👁️"}
                        </button>
                      </div>
                      <small style={{ color:"#64748b", fontSize:".75rem" }}>
                        You'll use this to log in after signup — no email verification needed.
                      </small>
                    </div>
                  </>
                )}

                {error && <div style={S.errorBox}>{error}</div>}

                {/* Action buttons based on signup mode */}
                {signupMode === "free" && (
                  <>
                    <button
                      style={{ ...S.primBtn, background:"linear-gradient(135deg,#10b981,#059669)" }}
                      disabled={loading || !name.trim() || !email.trim()}
                      onClick={handleFreeSignup}
                    >
                      {loading ? "Creating account…" : "🆓 Start for Free →"}
                    </button>
                    <p style={{ textAlign:"center", marginTop:6, fontSize:".74rem", color:"#475569" }}>
                      Free Tier access · Upgrade anytime
                    </p>
                  </>
                )}
                {signupMode === "pay" && (
                  <button style={S.primBtn} onClick={() => { setError(""); setStep("plan"); }}>
                    Continue to Plan Selection →
                  </button>
                )}
                {signupMode === "offer" && (
                  <>
                    <button
                      style={{ ...S.primBtn, background:"linear-gradient(135deg,#059669,#0d9488)" }}
                      disabled={loading || offerCodeInput.length !== 8 || !name.trim() || !email.trim() || password.length < 8}
                      onClick={handleOfferCodeSignup}
                    >
                      {loading ? "Creating account…" : "🎟️ Create Account & Go to Dashboard"}
                    </button>
                    <p style={{ textAlign:"center", marginTop:8, fontSize:".77rem", color:"#475569", cursor:"pointer" }}
                       onClick={() => { setSignupMode("pay"); setUseOfferCode(false); setOfferCodeInput(""); setError(""); }}>
                      💳 Pay with Razorpay instead
                    </p>
                  </>
                )}
              </div>
              <p style={{ textAlign:"center", marginTop:14, color:"#475569", fontSize:".78rem", cursor:"pointer" }}
                onClick={() => setStep("role")}>← Back to role selection</p>
              <p style={{ textAlign:"center", marginTop:8, color:"#475569", fontSize:".74rem" }}>
                🔒 Your information is encrypted and never shared
              </p>
            </div>
          )}

          {/* STEP 3 — Plan & Pay */}
          {step === "plan" && (
            <div style={{ paddingTop:8, paddingBottom:8 }}>
              <p style={{ fontSize:".71rem", fontWeight:700, letterSpacing:".1em",
                          textTransform:"uppercase", color:"#6366f1", marginBottom:8 }}>
                Step 3 of 3 — Choose Your Plan
              </p>
              <h2 style={{ fontSize:"1.5rem", fontWeight:900, marginBottom:5 }}>Select a subscription plan</h2>
              <p style={{ color:"#64748b", fontSize:".88rem", marginBottom:16 }}>All plans include all CBSE subjects and unlimited doubts</p>

              {/* Plan filter tabs */}
              <div style={{ display:"flex", background:"#111827", border:"1px solid #1e293b",
                            borderRadius:9, padding:3, marginBottom:14, gap:3 }}>
                {[["monthly","Monthly"]].map(([k,l]) => (
                  <button key={k} onClick={() => { setPlanFilter(k); }}
                    style={{ flex:1, padding:"7px 6px", borderRadius:7, border:"none",
                             background: planFilter===k ? "#1e293b" : "transparent",
                             color: planFilter===k ? "#f8fafc" : "#64748b",
                             fontFamily:"inherit", fontSize:".76rem", fontWeight:600, cursor:"pointer" }}>
                    {l}
                  </button>
                ))}
              </div>

              {/* Plan cards */}
              <div style={{ display:"flex", flexDirection:"column", gap:8, maxHeight:260, overflowY:"auto" }}>
                {visiblePlans.map(plan => {
                  const sel = planKey === plan.key;
                  return (
                    <div key={plan.key} onClick={() => setPlanKey(plan.key)}
                      style={{ display:"flex", alignItems:"center", gap:12,
                               background: sel ? "rgba(99,102,241,.08)" : "#111827",
                               border:`2px solid ${sel?"#6366f1":"#1e293b"}`,
                               borderRadius:11, padding:"12px 14px", cursor:"pointer" }}>
                      <div style={{ width:17, height:17, borderRadius:"50%",
                                    border:`2px solid ${sel?"#6366f1":"#334155"}`,
                                    background: sel ? "#6366f1" : "transparent",
                                    flexShrink:0, display:"flex", alignItems:"center", justifyContent:"center" }}>
                        {sel && <div style={{ width:6, height:6, borderRadius:"50%", background:"#fff" }} />}
                      </div>
                      <div style={{ flex:1 }}>
                        {plan.badge && (
                          <span style={{ fontSize:".62rem", fontWeight:700, padding:"2px 6px",
                                         borderRadius:5, marginRight:6,
                                         background:"rgba(16,185,129,.2)", color:"#34d399" }}>
                            {plan.badge}
                          </span>
                        )}
                        <div style={{ fontSize:".87rem", fontWeight:700, color:"#e2e8f0", display:"inline" }}>{plan.label}</div>
                        {plan.discountLabel && (
                          <div style={{ fontSize:".7rem", color:"#64748b", marginTop:1 }}>{plan.discountLabel}</div>
                        )}
                      </div>
                      <div style={{ textAlign:"right", flexShrink:0 }}>
                        <div style={{ fontWeight:800, fontSize:".95rem", color:"#f8fafc" }}>₹{plan.price.toLocaleString("en-IN")}</div>
                        <div style={{ fontSize:".67rem", color:"#64748b" }}>/ {plan.billingLabel}</div>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Payment summary */}
              <div style={{ background:"#111827", border:"1px solid #1e293b", borderRadius:11, padding:14, marginTop:14 }}>
                <div style={{ display:"flex", justifyContent:"space-between", fontSize:".82rem", color:"#94a3b8", marginBottom:6 }}>
                  <span>Selected plan</span><span>{selectedPlan?.label}</span>
                </div>
                <div style={{ display:"flex", justifyContent:"space-between", fontSize:".9rem",
                              fontWeight:700, color:"#f8fafc", borderTop:"1px solid #1e293b", paddingTop:9 }}>
                  <span>Total today</span>
                  <span>₹{selectedPlan?.price?.toLocaleString("en-IN")} / {selectedPlan?.billingLabel}</span>
                </div>
              </div>

              {error && <div style={{ ...S.errorBox, marginTop:12 }}>{error}</div>}

              {!useOfferCode ? (
                <>
                  <button style={{ ...S.primBtn, marginTop:12 }} disabled={loading} onClick={handlePayAndSignup}>
                    {loading ? "Processing..." : `💳 Pay ₹${selectedPlan?.price?.toLocaleString("en-IN")} & Create Account`}
                  </button>
                  <p style={{ textAlign:"center", marginTop:10, fontSize:".77rem", color:"#475569", cursor:"pointer" }}
                    onClick={() => { setUseOfferCode(true); setError(""); }}>
                    🎟️ Have an offer code? Skip payment →
                  </p>
                </>
              ) : (
                <form onSubmit={handleOfferCodeSignup} style={{ marginTop:12 }}>
                  <label style={{ display:"block", fontSize:".85rem", fontWeight:600, color:"#cbd5e1", marginBottom:7 }}>Offer Code *</label>
                  <input style={{ ...S.input, fontFamily:"monospace", letterSpacing:4,
                                  textTransform:"uppercase", fontSize:"1.1rem", textAlign:"center", marginBottom:10 }}
                    type="text" maxLength={8} placeholder="XXXXXXXX"
                    value={offerCodeInput} onChange={e => setOfferCodeInput(e.target.value.toUpperCase())} />
                  <button type="submit" style={{ ...S.primBtn, background:"linear-gradient(135deg,#059669,#0d9488)" }}
                    disabled={loading || offerCodeInput.length !== 8}>
                    {loading ? "Creating account…" : "Create Account with Offer Code"}
                  </button>
                  <p style={{ textAlign:"center", marginTop:8, fontSize:".77rem", color:"#475569", cursor:"pointer" }}
                    onClick={() => { setUseOfferCode(false); setError(""); }}>
                    ← Pay with Razorpay instead
                  </p>
                </form>
              )}

              <p style={{ textAlign:"center", marginTop:10, color:"#475569", fontSize:".74rem", cursor:"pointer" }}
                onClick={() => { setStep("form"); setError(""); }}>← Back to account details</p>
              <p style={{ textAlign:"center", marginTop:6, color:"#475569", fontSize:".72rem" }}>
                🔒 Secured by Razorpay · You will receive a verification email after payment
              </p>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
