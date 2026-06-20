import { useEffect, useState } from "react";
import logoImg from "../assets/AITutorLogo1.png";
import { SUBSCRIPTION_PLANS } from "../config/subscriptionPlans";
import { supabase } from "../api/supabaseClient";
import "./SignupPage.css";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const PLANS = [
  "free", "starter",
  "family_premium",
].map(k => SUBSCRIPTION_PLANS[k]).filter(Boolean);

// Platform currently supports Grade 5–10.
// To add new grades when the platform expands, add them here AND in:
//   - backend/app/data/product_catalogue.py (set visible: True)
//   - backend/app/routes/parent_dashboard.py (ParentDashboardPage grade list)
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
        <div style={{ fontSize:"1.6rem", fontWeight:900, lineHeight:1.1 }}>LikhaPoha AI</div>
        <div style={{ fontSize:".8rem", color:"#64748b", marginTop:3 }}>
          CBSE · Class 5–10 · AI Tutor
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
  const [useOfferCode, setUseOfferCode] = useState(_fromLink);
  const [offerCodeInput, setOfferCodeInput] = useState(_fromLink ? _urlCode : "");
  const [password, setPassword] = useState("");
  const [passwordSetLink, setPasswordSetLink] = useState("");

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
        }),
      });
      const data = await res.json();
      if (!res.ok || !data.success) {
        setError(data.detail || data.message || "Could not create account. Please check your offer code.");
        return;
      }
      // Direct-login flow: if a password was set, sign in immediately → go to dashboard
      if (password.trim() && onLogin) {
        await supabase.auth.signOut().catch(() => {});
        const { data: authData, error: authErr } = await supabase.auth.signInWithPassword({
          email: email.trim(),
          password: password.trim(),
        });
        if (!authErr && authData.session) {
          const { data: profile } = await supabase
            .from("profiles").select("*").eq("id", authData.user.id).single();
          if (profile) {
            onLogin({
              id: authData.user.id,
              email: authData.user.email,
              username: profile.username || authData.user.email,
              role: profile.role,
              grade: profile.grade || "Grade 9",
              board: profile.board || "CBSE",
              parentId: profile.parent_id,
              familyId: profile.family_id,
              accessToken: authData.session.access_token,
              accessCbse: !!profile.access_cbse,
              accessSofScience: !!profile.access_sof_science,
              accessSofMaths: !!profile.access_sof_maths,
              accessSofEnglish: !!profile.access_sof_english,
              cbseSubjects: Array.isArray(profile.cbse_subjects) ? profile.cbse_subjects : [],
              dailyTokenLimit: profile.daily_token_limit,
              monthlyTokenLimit: profile.monthly_token_limit,
              subscriptionPlan: profile.subscription_plan || "free",
              accountStatus: profile.account_status || "active",
              offerAccess: false,
            });
            return; // onLogin handles routing to dashboard
          }
        }
        // Sign-in failed after account creation — fall through to done screen
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

              {/* Offer code / payment toggle — always visible */}
              <div style={{ display:"flex", gap:0, background:"#111827", border:"1px solid #1e293b",
                            borderRadius:10, padding:3, marginBottom:20 }}>
                <button
                  onClick={() => { setUseOfferCode(false); setError(""); }}
                  style={{ flex:1, padding:"9px 10px", borderRadius:8, border:"none",
                           background: !useOfferCode ? "linear-gradient(135deg,#2563eb,#7c3aed)" : "transparent",
                           color: !useOfferCode ? "#fff" : "#64748b",
                           fontFamily:"inherit", fontSize:".82rem", fontWeight:600, cursor:"pointer" }}>
                  💳 Pay & Sign Up
                </button>
                <button
                  onClick={() => { setUseOfferCode(true); setError(""); }}
                  style={{ flex:1, padding:"9px 10px", borderRadius:8, border:"none",
                           background: useOfferCode ? "linear-gradient(135deg,#059669,#0d9488)" : "transparent",
                           color: useOfferCode ? "#fff" : "#64748b",
                           fontFamily:"inherit", fontSize:".82rem", fontWeight:600, cursor:"pointer" }}>
                  🎟️ I Have an Offer Code
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
                  <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:13 }}>
                    <div>
                      <label style={{ display:"block", fontSize:".85rem", fontWeight:600, color:"#cbd5e1", marginBottom:7 }}>Class *</label>
                      <select style={S.select} value={grade} onChange={e => setGrade(e.target.value)}>
                        {GRADES.map(g => <option key={g}>{g}</option>)}
                      </select>
                    </div>
                    <div>
                      <label style={{ display:"block", fontSize:".85rem", fontWeight:600, color:"#cbd5e1", marginBottom:7 }}>Board</label>
                      <select style={S.select}><option>CBSE</option></select>
                    </div>
                  </div>
                )}
                {role === "teacher" && (
                  <div>
                    <label style={{ display:"block", fontSize:".85rem", fontWeight:600, color:"#cbd5e1", marginBottom:7 }}>School Name</label>
                    <input style={S.input} type="text" placeholder="Name of your school (optional)"
                      value={school} onChange={e => setSchool(e.target.value)} />
                  </div>
                )}
                {useOfferCode && (
                  <>
                    <div>
                      <label style={{ display:"block", fontSize:".85rem", fontWeight:600, color:"#cbd5e1", marginBottom:7 }}>
                        Offer Code *
                      </label>
                      <input
                        style={{ ...S.input, fontFamily:"monospace", letterSpacing:4,
                                 textTransform:"uppercase", fontSize:"1.1rem", textAlign:"center" }}
                        type="text" maxLength={8} placeholder="XXXXXXXX"
                        value={offerCodeInput}
                        onChange={e => setOfferCodeInput(e.target.value.toUpperCase())}
                      />
                    </div>
                    <div>
                      <label style={{ display:"block", fontSize:".85rem", fontWeight:600, color:"#cbd5e1", marginBottom:7 }}>
                        Password *
                      </label>
                      <input
                        style={S.input} type="password" placeholder="Set your password (min 8 characters)"
                        value={password} onChange={e => setPassword(e.target.value)}
                        minLength={8}
                      />
                      <small style={{ color:"#64748b", fontSize:".75rem" }}>
                        You'll use this to log in after signup — no email verification needed.
                      </small>
                    </div>
                  </>
                )}
                {error && <div style={S.errorBox}>{error}</div>}
                {useOfferCode ? (
                  <>
                    <button
                      style={{ ...S.primBtn, background:"linear-gradient(135deg,#059669,#0d9488)" }}
                      disabled={loading || offerCodeInput.length !== 8 || !name.trim() || !email.trim() || password.length < 8}
                      onClick={handleOfferCodeSignup}
                    >
                      {loading ? "Creating account…" : "🎟️ Create Account & Go to Dashboard"}
                    </button>
                    <p style={{ textAlign:"center", marginTop:8, fontSize:".77rem", color:"#475569", cursor:"pointer" }}
                       onClick={() => { setUseOfferCode(false); setOfferCodeInput(""); setError(""); }}>
                      💳 Pay with Razorpay instead
                    </p>
                  </>
                ) : (
                  <button style={S.primBtn} onClick={() => { setError(""); setStep("plan"); }}>
                    Continue to Plan Selection →
                  </button>
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
