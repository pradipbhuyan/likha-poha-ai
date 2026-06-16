import { useEffect, useState } from "react";
import logoImg from "../assets/AITutorLogo1.png";
import { SUBSCRIPTION_PLANS } from "../config/subscriptionPlans";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const PLANS = ["free","starter","family_premium"].map(k => SUBSCRIPTION_PLANS[k]).filter(Boolean);
const GRADES = ["Grade 5","Grade 6","Grade 7","Grade 8","Grade 9","Grade 10"];

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

export default function SignupPage({ onBackToLogin, initialPlan }) {
  const [step, setStep] = useState("role");
  const [role, setRole] = useState("");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [grade, setGrade] = useState("Grade 9");
  const [school, setSchool] = useState("");
  const [planKey, setPlanKey] = useState(initialPlan || "free");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [useOfferCode, setUseOfferCode] = useState(false);
  const [offerCodeInput, setOfferCodeInput] = useState("");

  useEffect(() => { loadRazorpay(); }, []);

  function selectRole(r) { setRole(r); setStep("form"); setError(""); }

  async function handleOfferCodeSignup(e) {
    e.preventDefault();
    setError("");
    if (!name.trim() || !email.trim()) { setError("Please fill in your name and email."); return; }
    if (offerCodeInput.trim().length !== 8) { setError("Offer code must be exactly 8 characters."); return; }
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/auth/signup-with-offer-code`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          role,
          name: name.trim(),
          email: email.trim(),
          offer_code: offerCodeInput.trim().toUpperCase(),
          grade: role === "student" ? grade : undefined,
          school: role === "teacher" ? school.trim() : undefined,
        }),
      });
      const data = await res.json();
      if (!res.ok || !data.success) {
        setError(data.detail || data.message || "Could not create account. Please check your offer code.");
        return;
      }
      setStep("done");
    } catch (err) {
      setError(err.message || "Signup failed. Please try again.");
    } finally {
      setLoading(false); }
  }

  async function handlePayAndSignup(e) {
    e.preventDefault();
    setError("");
    if (!name.trim() || !email.trim()) { setError("Please fill in all required fields."); return; }
    setLoading(true);
    try {
      const orderRes = await fetch(`${API_BASE}/api/auth/signup-order`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim(), plan_key: planKey }),
      });
      const orderData = await orderRes.json();
      if (!orderRes.ok || !orderData.success) {
        setError(orderData.detail || orderData.message || "Could not initiate payment. Please try again.");
        return;
      }
      await loadRazorpay();
      const plan = PLANS.find(p => p.key === planKey) || PLANS[0];
      await new Promise((resolve, reject) => {
        const rzp = new window.Razorpay({
          key: orderData.key_id,
          amount: orderData.amount * 100,
          currency: orderData.currency,
          name: "LikhaPoha AI",
          description: `${plan.label} Plan`,
          order_id: orderData.order_id,
          prefill: { name: name.trim(), email: email.trim() },
          theme: { color: "#2563eb" },
          handler: async function(response) {
            try {
              const completeRes = await fetch(`${API_BASE}/api/auth/complete-signup`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                  role, name: name.trim(), email: email.trim(), plan_key: planKey,
                  razorpay_order_id: response.razorpay_order_id,
                  razorpay_payment_id: response.razorpay_payment_id,
                  razorpay_signature: response.razorpay_signature,
                  grade: role === "student" ? grade : undefined,
                  school: role === "teacher" ? school.trim() : undefined,
                }),
              });
              const completeData = await completeRes.json();
              if (!completeRes.ok || !completeData.success) {
                setError(completeData.detail || completeData.message || "Account creation failed after payment. Please contact support.");
                reject(new Error("complete-signup failed")); return;
              }
              setStep("done"); resolve();
            } catch(err) {
              setError("Account creation failed. Contact support with payment ID: " + response.razorpay_payment_id);
              reject(err);
            }
          },
          modal: { ondismiss: function() { reject(new Error("dismissed")); } },
        });
        rzp.open();
      });
    } catch(err) {
      if (err.message !== "dismissed") setError(err.message || "Signup failed. Please try again.");
    } finally { setLoading(false); }
  }

  const planObj = PLANS.find(p => p.key === planKey) || PLANS[0];
  const navStyle = {display:"flex",alignItems:"center",justifyContent:"space-between",padding:"16px 48px",background:"rgba(15,23,42,.97)",backdropFilter:"blur(16px)",borderBottom:"1px solid #1e293b",position:"sticky",top:0,zIndex:99};
  const inputStyle = {width:"100%",background:"#111827",border:"2px solid #1e293b",borderRadius:12,padding:"15px 18px",color:"#f8fafc",fontFamily:"inherit",fontSize:"1.05rem",boxSizing:"border-box",outline:"none"};

  return (
    <div style={{fontFamily:"Inter,sans-serif",background:"#0f172a",color:"#f8fafc",minHeight:"100vh",display:"flex",flexDirection:"column"}}>
      <nav style={navStyle}>
        <button onClick={onBackToLogin} style={{display:"flex",alignItems:"center",gap:10,background:"transparent",border:"none",color:"#f8fafc",cursor:"pointer",fontFamily:"inherit"}}>
          <img src={logoImg} alt="LikhaPoha AI" style={{width:42,height:42,borderRadius:10,objectFit:"cover",background:"#fff"}} />
          <span style={{fontSize:"1.08rem",fontWeight:700}}>LikhaPoha AI</span>
        </button>
        <button onClick={onBackToLogin} style={{background:"transparent",border:"1px solid #334155",color:"#93c5fd",padding:"8px 18px",borderRadius:8,fontSize:".88rem",cursor:"pointer",fontFamily:"inherit"}}>
          Already have an account? Login
        </button>
      </nav>
      <div style={{flex:1,display:"flex",alignItems:"center",justifyContent:"center",padding:"40px 20px"}}>
        <div style={{width:"100%",maxWidth:520}}>

          {step === "role" && (
            <div>
              <div style={{textAlign:"center",marginBottom:44}}>
                <div style={{display:"inline-flex",alignItems:"center",background:"rgba(37,99,235,.18)",border:"1px solid rgba(37,99,235,.35)",color:"#93c5fd",fontSize:".8rem",fontWeight:700,padding:"6px 16px",borderRadius:99,marginBottom:20,textTransform:"uppercase",letterSpacing:".1em"}}>Create Account</div>
                <h1 style={{fontSize:"clamp(2rem,5vw,2.8rem)",fontWeight:900,lineHeight:1.1,marginBottom:14}}>I am signing up as a...</h1>
                <p style={{color:"#94a3b8",fontSize:"1.05rem"}}>Choose your role to get started</p>
              </div>
              <div style={{display:"grid",gridTemplateColumns:"repeat(3,1fr)",gap:18,marginBottom:28}}>
                {[
                  {r:"parent",icon:"👨‍👩‍👧",label:"Parent",desc:"Manage child learning and track progress"},
                  {r:"student",icon:"🎓",label:"Student",desc:"Access CBSE lessons, mock tests, doubt solving"},
                  {r:"teacher",icon:"📋",label:"Teacher",desc:"Monitor students and provide guidance"},
                ].map(({r,icon,label,desc}) => (
                  <button key={r} onClick={() => selectRole(r)}
                    style={{background:"#0f172a",border:"2px solid #1e293b",borderRadius:20,padding:"28px 16px",cursor:"pointer",textAlign:"center",fontFamily:"inherit",color:"#f8fafc",transition:"all .2s"}}
                    onMouseEnter={e=>{e.currentTarget.style.borderColor="#2563eb";e.currentTarget.style.background="rgba(37,99,235,.12)";e.currentTarget.style.transform="translateY(-3px)";}}
                    onMouseLeave={e=>{e.currentTarget.style.borderColor="#1e293b";e.currentTarget.style.background="#0f172a";e.currentTarget.style.transform="none";}}>
                    <div style={{fontSize:"2.8rem",marginBottom:14}}>{icon}</div>
                    <div style={{fontWeight:800,fontSize:"1.1rem",marginBottom:8,color:"#f1f5f9"}}>{label}</div>
                    <div style={{fontSize:".85rem",color:"#64748b",lineHeight:1.5}}>{desc}</div>
                  </button>
                ))}
              </div>
              <p style={{textAlign:"center",color:"#475569",fontSize:".88rem",borderTop:"1px solid #1e293b",paddingTop:20}}>🔒 All accounts require a paid plan &middot; Secure Razorpay checkout</p>
            </div>
          )}

          {step === "form" && (
            /* Render ONE top-level form — either offer-code or Razorpay, never nested */
            <form onSubmit={useOfferCode ? handleOfferCodeSignup : handlePayAndSignup}>
              <button type="button" onClick={() => { setStep("role"); setError(""); }}
                style={{background:"transparent",border:"none",color:"#93c5fd",cursor:"pointer",fontFamily:"inherit",fontSize:".88rem",marginBottom:20,padding:0}}>
                ← Back
              </button>
              <h2 style={{fontSize:"2rem",fontWeight:900,marginBottom:8}}>
                {role === "parent" ? "👨‍👩‍👧 Parent Account" : role === "student" ? "🎓 Student Account" : "📋 Teacher Account"}
              </h2>
              <p style={{color:"#64748b",fontSize:"1rem",marginBottom:32}}>Fill in your details and select a plan</p>
              <div style={{display:"grid",gap:20,marginBottom:32}}>
                <div>
                  <label style={{display:"block",fontSize:"1rem",fontWeight:600,color:"#cbd5e1",marginBottom:10}}>Full Name *</label>
                  <input value={name} onChange={e => setName(e.target.value)} required placeholder="Enter your full name" style={inputStyle} />
                </div>
                <div>
                  <label style={{display:"block",fontSize:"1rem",fontWeight:600,color:"#cbd5e1",marginBottom:10}}>Email Address *</label>
                  <input value={email} onChange={e => setEmail(e.target.value)} required type="email" placeholder="your@email.com" style={inputStyle} />
                </div>
                {role === "student" && (
                  <div>
                    <label style={{display:"block",fontSize:"1rem",fontWeight:600,color:"#cbd5e1",marginBottom:10}}>Class *</label>
                    <select value={grade} onChange={e => setGrade(e.target.value)} style={inputStyle}>
                      {GRADES.map(g => <option key={g}>{g}</option>)}
                    </select>
                  </div>
                )}
                {role === "teacher" && (
                  <div>
                    <label style={{display:"block",fontSize:"1rem",fontWeight:600,color:"#cbd5e1",marginBottom:10}}>School Name</label>
                    <input value={school} onChange={e => setSchool(e.target.value)} placeholder="Name of your school (optional)" style={inputStyle} />
                  </div>
                )}
              </div>
              <div style={{marginBottom:32}}>
                <label style={{display:"block",fontSize:"1rem",fontWeight:600,color:"#cbd5e1",marginBottom:14}}>Choose Your Plan *</label>
                <div style={{display:"grid",gap:12}}>
                  {PLANS.map(plan => {
                    const sel = planKey === plan.key;
                    return (
                      <div key={plan.key} onClick={() => setPlanKey(plan.key)}
                        style={{display:"grid",gridTemplateColumns:"auto 1fr auto",alignItems:"center",gap:16,
                          background: sel ? "rgba(37,99,235,.18)" : "#0f172a",
                          border: sel ? "2px solid #3b82f6" : "2px solid #1e293b",
                          borderRadius:14,padding:"18px 20px",cursor:"pointer",
                          boxShadow: sel ? "0 4px 20px rgba(37,99,235,.2)" : "none",
                          transition:"all .2s"}}>
                        <div style={{width:22,height:22,borderRadius:"50%",border: sel?"none":"2px solid #334155",
                          background: sel?"linear-gradient(135deg,#2563eb,#7c3aed)":"transparent",
                          display:"flex",alignItems:"center",justifyContent:"center",flexShrink:0}}>
                          {sel && <div style={{width:8,height:8,borderRadius:"50%",background:"#fff"}}/>}
                        </div>
                        <div style={{minWidth:0}}>
                          <div style={{fontWeight:700,fontSize:"1rem",color:sel?"#f1f5f9":"#94a3b8",display:"flex",alignItems:"center",gap:8,flexWrap:"wrap"}}>
                            {plan.label}
                            {plan.badge && <span style={{fontSize:".72rem",background:"rgba(37,99,235,.25)",color:"#93c5fd",padding:"3px 8px",borderRadius:99,fontWeight:700}}>{plan.badge}</span>}
                          </div>
                          <div style={{fontSize:".85rem",color:"#475569",marginTop:4}}>{plan.included?.[0] || plan.audience}</div>
                        </div>
                        <div style={{fontWeight:900,fontSize:"1.2rem",color:sel?"#f8fafc":"#64748b",whiteSpace:"nowrap",textAlign:"right"}}>
                          &#8377;{plan.price}
                          <div style={{fontWeight:400,color:"#475569",fontSize:".78rem"}}>/{plan.billingLabel}</div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
              {error && <div style={{background:"rgba(239,68,68,.1)",border:"1px solid rgba(239,68,68,.3)",color:"#fca5a5",borderRadius:10,padding:"12px 14px",marginBottom:16,fontSize:".88rem"}}>{error}</div>}
              {/* Offer code toggle */}
              <div style={{borderTop:"1px solid #1e293b",paddingTop:20,marginBottom:8}}>
                <button type="button"
                  onClick={() => { setUseOfferCode(v => !v); setError(""); }}
                  style={{background:"transparent",border:"1px solid #334155",color:"#93c5fd",padding:"8px 16px",borderRadius:8,fontSize:".88rem",cursor:"pointer",fontFamily:"inherit",width:"100%"}}>
                  {useOfferCode ? "← Pay with Razorpay instead" : "🎟️ Have an offer code? Skip payment"}
                </button>
              </div>

              {useOfferCode ? (
                <>
                  <div style={{marginBottom:16}}>
                    <label style={{display:"block",fontSize:"1rem",fontWeight:600,color:"#cbd5e1",marginBottom:10}}>Offer Code *</label>
                    <input
                      value={offerCodeInput}
                      onChange={e => setOfferCodeInput(e.target.value.toUpperCase())}
                      required maxLength={8} placeholder="XXXXXXXX"
                      style={{...inputStyle,fontFamily:"monospace",letterSpacing:4,textTransform:"uppercase",fontSize:"1.2rem",textAlign:"center"}}
                    />
                    <p style={{marginTop:8,fontSize:".8rem",color:"#64748b"}}>Enter your 8-character offer code to create a free account.</p>
                  </div>
                  {/* error is already shown above — no duplicate here */}
                  <button type="submit" disabled={loading || offerCodeInput.length !== 8}
                    style={{width:"100%",background:"linear-gradient(135deg,#059669,#0d9488)",color:"#fff",border:"none",borderRadius:12,padding:"15px",fontSize:"1rem",fontWeight:700,cursor:loading?"not-allowed":"pointer",fontFamily:"inherit",opacity:(loading||offerCodeInput.length!==8)?0.6:1}}>
                    {loading ? "Creating account…" : "Create Account with Offer Code"}
                  </button>
                  <p style={{textAlign:"center",marginTop:14,color:"#64748b",fontSize:".78rem"}}>
                    You will receive a verification email after signup
                  </p>
                </>
              ) : (
                <>
                  <button type="submit" disabled={loading}
                    style={{width:"100%",background:"linear-gradient(135deg,#2563eb,#7c3aed)",color:"#fff",border:"none",borderRadius:12,padding:"15px",fontSize:"1rem",fontWeight:700,cursor:loading?"not-allowed":"pointer",fontFamily:"inherit",opacity:loading?0.7:1}}>
                    {loading ? "Processing..." : `Pay \u20B9${planObj?.price} & Create Account`}
                  </button>
                  <p style={{textAlign:"center",marginTop:14,color:"#64748b",fontSize:".78rem"}}>
                    Secure payment via Razorpay &middot; You will receive a verification email after payment
                  </p>
                </>
              )}
            </form>
          )}

          {step === "done" && (
            <div style={{textAlign:"center",padding:"40px 20px"}}>
              <div style={{fontSize:"4rem",marginBottom:20}}>&#10004;&#65039;</div>
              <h2 style={{fontSize:"1.8rem",fontWeight:900,marginBottom:14}}>
                {useOfferCode ? "Account Created!" : "Payment Confirmed!"}
              </h2>
              {useOfferCode && (
                <div style={{background:"rgba(5,150,105,.15)",border:"1px solid rgba(5,150,105,.4)",borderRadius:12,padding:"14px 18px",marginBottom:20,fontSize:".9rem",color:"#6ee7b7",textAlign:"left"}}>
                  ✅ Your account is ready! Your offer code access is valid until {/* shown in message */}<strong style={{color:"#f8fafc"}}>check email for expiry date</strong>.<br/>
                  <strong style={{color:"#f8fafc"}}>Next step:</strong> Check your email for a <strong style={{color:"#f8fafc"}}>Set Password</strong> link. Click it to set your password, then log in.
                </div>
              )}
              <p style={{color:"#cbd5e1",lineHeight:1.7,marginBottom:28,fontSize:"1rem"}}>
                Your account has been created{useOfferCode ? " using your offer code" : " and payment is confirmed"}.<br />
                <strong style={{color:"#f8fafc"}}>Please check your email</strong> {useOfferCode ? "for a Set Password link" : "for a verification link"} from LikhaPoha AI.<br />
                {useOfferCode ? "Click it to set your password, then come back to " : "Click the link to verify your email and set your password, then come back to "}
                <strong style={{color:"#f8fafc"}}>Login</strong>.
              </p>
              <div style={{background:"#111827",border:"1px solid #334155",borderRadius:14,padding:"16px 20px",marginBottom:28,fontSize:".88rem",color:"#94a3b8",textAlign:"left"}}>
                <div style={{marginBottom:8}}>&#128274; Check your spam folder if you don't see the email</div>
                <div>&#128337; The verification link expires in 24 hours</div>
              </div>
              <button onClick={onBackToLogin}
                style={{background:"linear-gradient(135deg,#2563eb,#7c3aed)",color:"#fff",border:"none",borderRadius:12,padding:"14px 32px",fontSize:"1rem",fontWeight:700,cursor:"pointer",fontFamily:"inherit"}}>
                Go to Login
              </button>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
