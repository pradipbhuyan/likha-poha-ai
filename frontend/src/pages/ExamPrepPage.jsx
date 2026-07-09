/**
 * ExamPrepPage.jsx — JEE / NEET / CUET Exam Prep Center
 * ======================================================
 * New access model (2026-07-09):
 *   - All Grade 11/12 students see the landing/preview page
 *   - Access to each exam (JEE/NEET/CUET) requires a separate pack purchase
 *   - Pack purchase is independent of CBSE subscription tier (Free/Premium)
 *   - Admin and test users (akshita.teststudent) get all packs for free
 *   - Pack prices are managed by admin via Subscription Settings
 */

import React, { useEffect, useState, useRef } from "react";
import { Loader, CheckCircle, XCircle, Lock, ShoppingCart } from "lucide-react";
import {
  getExamPrepSubjects,
  getExamPrepTopics,
  getExamPrepQuestions,
  submitQuestionAnswer,
  startSimulatedTest,
  submitSimulatedTest,
} from "../api/examPrep";
import { getMyPacks, getPackPrices, createPackOrder, verifyPackPayment } from "../api/examPrepPacks";

// ── Constants ──────────────────────────────────────────────────────────────────

const EXAMS = {
  jee_main: { label: "JEE Main",  icon: "📐", color: "#6366f1", subLabel: "Engineering entrance" },
  neet_ug:  { label: "NEET UG",   icon: "🔬", color: "#10b981", subLabel: "Medical entrance" },
  cuet_ug:  { label: "CUET UG",   icon: "🏛️", color: "#f59e0b", subLabel: "Central university entrance" },
};

const EXAM_SIM_CONFIG = {
  jee_main: { subjects: ["Physics", "Chemistry", "Mathematics"], duration: 180, questions: 90, marking: "+4 / -1" },
  neet_ug:  { subjects: ["Physics", "Chemistry", "Biology"],     duration: 200, questions: 200, marking: "+4 / -1" },
  cuet_ug:  { subjects: ["English", "General Test", "Domain Subject"], duration: 195, questions: 150, marking: "+5 / -1" },
};

const SUBJECT_ICONS  = { Physics: "⚛️", Chemistry: "🧪", Mathematics: "📐", Biology: "🌿" };
const SUBJECT_COLORS = { Physics: "#6366f1", Chemistry: "#10b981", Mathematics: "#f59e0b", Biology: "#22c55e" };
const DIFFICULTY_COLORS = { easy: "#22c55e", medium: "#f59e0b", hard: "#ef4444" };

// ── Math/Chemistry formatter ──────────────────────────────────────────────────
function formatMathText(text) {
  if (!text) return "";
  let t = text;
  t = t.replace(/\\times/g, "×"); t = t.replace(/\\cdot/g, "·"); t = t.replace(/\\pm/g, "±");
  t = t.replace(/\\alpha/g, "α"); t = t.replace(/\\beta/g, "β"); t = t.replace(/\\gamma/g, "γ");
  t = t.replace(/\\delta/g, "δ"); t = t.replace(/\\Delta/g, "Δ"); t = t.replace(/\\mu/g, "μ");
  t = t.replace(/\\pi/g, "π"); t = t.replace(/\\theta/g, "θ"); t = t.replace(/\\lambda/g, "λ");
  t = t.replace(/\\Omega/g, "Ω"); t = t.replace(/\\omega/g, "ω");
  t = t.replace(/\\rightarrow/g, "→"); t = t.replace(/\\leftarrow/g, "←");
  t = t.replace(/\\approx/g, "≈"); t = t.replace(/\\neq/g, "≠"); t = t.replace(/\\geq/g, "≥"); t = t.replace(/\\leq/g, "≤");
  t = t.replace(/\\infty/g, "∞");
  t = t.replace(/\\sqrt\{([^}]+)\}/g, "√($1)");
  t = t.replace(/\\frac\{([^}]+)\}\{([^}]+)\}/g, "($1)/($2)");
  t = t.replace(/\^\{([^}]+)\}/g, (_, e) => `<sup>${e}</sup>`);
  t = t.replace(/\^([+-]?\d+)/g, (_, e) => `<sup>${e}</sup>`);
  t = t.replace(/\^([a-zA-Z])/g, (_, e) => `<sup>${e}</sup>`);
  t = t.replace(/_\{([^}]+)\}/g, (_, s) => `<sub>${s}</sub>`);
  t = t.replace(/_(\d+)/g, (_, s) => `<sub>${s}</sub>`);
  t = t.replace(/([A-Z][a-z]?)(\d+)(?![^<]*>)/g, (_, el, n) => `${el}<sub>${n}</sub>`);
  return t;
}

function MathText({ text, style }) {
  const html = React.useMemo(() => formatMathText(text || ""), [text]);
  return <span dangerouslySetInnerHTML={{ __html: html }} style={style} />;
}

// ── Watermark ─────────────────────────────────────────────────────────────────
function embedWatermark(text, username) {
  if (!text || !username) return text;
  try {
    const bits = username.split("").map(c => c.charCodeAt(0).toString(2).padStart(8,"0")).join("");
    const wm = "\u200D" + bits.split("").map(b => b==="1" ? "\u200C" : "\u200B").join("") + "\u200D";
    const dot = text.indexOf(". ");
    return dot > 0 ? text.slice(0, dot+2) + wm + text.slice(dot+2) : text + wm;
  } catch { return text; }
}

// ── Pack Purchase Modal ───────────────────────────────────────────────────────
function PackPurchaseModal({ examType, prices, user, onSuccess, onClose }) {
  const exam = EXAMS[examType];
  const priceInfo = prices?.[examType] || {};
  const [step, setStep] = useState("confirm"); // confirm | paying | success | error
  const [errMsg, setErrMsg] = useState("");

  async function handleBuy() {
    setStep("paying");
    setErrMsg("");
    try {
      const orderData = await createPackOrder(examType, user.accessToken);
      // Load Razorpay script if not loaded
      if (!window.Razorpay) {
        await new Promise((res, rej) => {
          const s = document.createElement("script");
          s.src = "https://checkout.razorpay.com/v1/checkout.js";
          s.onload = res; s.onerror = rej;
          document.body.appendChild(s);
        });
      }
      const rzp = new window.Razorpay({
        key: orderData.key_id,
        amount: orderData.amount * 100,
        currency: "INR",
        order_id: orderData.order_id,
        name: "Likha Poha AI",
        description: orderData.plan_label,
        image: "/loading-logo.gif",
        prefill: { email: user.email || "", name: user.username || "" },
        theme: { color: exam.color },
        handler: async (response) => {
          try {
            await verifyPackPayment({
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature,
              exam_type: examType,
            }, user.accessToken);
            setStep("success");
            setTimeout(() => { onSuccess(examType); }, 2000);
          } catch (e) {
            setStep("error"); setErrMsg(e.message || "Payment verification failed.");
          }
        },
        modal: { ondismiss: () => setStep("confirm") },
      });
      rzp.open();
    } catch (e) {
      setStep("error"); setErrMsg(e.message || "Could not start payment.");
    }
  }

  return (
    <div style={{ position:"fixed", inset:0, zIndex:10000, background:"rgba(0,0,0,.75)", display:"flex", alignItems:"center", justifyContent:"center", padding:20 }}>
      <div style={{ background:"#1e293b", border:`2px solid ${exam.color}`, borderRadius:16, padding:32, maxWidth:440, width:"100%", boxShadow:"0 20px 60px rgba(0,0,0,.6)", fontFamily:"inherit" }}>

        {step === "confirm" && (<>
          <div style={{ textAlign:"center", marginBottom:20 }}>
            <div style={{ fontSize:"2.5rem", marginBottom:8 }}>{exam.icon}</div>
            <h2 style={{ fontSize:"1.2rem", fontWeight:800, color:"#f1f5f9", margin:"0 0 4px" }}>{exam.label} Prep Pack</h2>
            <p style={{ fontSize:".82rem", color:"#64748b" }}>Unlock full access to {exam.label} preparation</p>
          </div>

          {/* What's included */}
          <div style={{ background:"rgba(99,102,241,.07)", border:"1px solid rgba(99,102,241,.2)", borderRadius:10, padding:"12px 14px", marginBottom:16 }}>
            {(priceInfo.included || []).map(f => (
              <div key={f} style={{ display:"flex", alignItems:"center", gap:7, fontSize:".78rem", color:"#94a3b8", marginBottom:4 }}>
                <CheckCircle size={13} color="#22c55e" /> {f}
              </div>
            ))}
          </div>

          {/* Price */}
          <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:20 }}>
            <div>
              <div style={{ fontSize:"1.6rem", fontWeight:900, color:exam.color }}>₹{priceInfo.charge || priceInfo.price || 0}</div>
              {priceInfo.discount_pct > 0 && (
                <div style={{ fontSize:".68rem", color:"#4ade80" }}>{priceInfo.discount_pct}% off — was ₹{priceInfo.price}</div>
              )}
            </div>
            <div style={{ textAlign:"right" }}>
              <div style={{ fontSize:".72rem", color:"#64748b" }}>Valid for</div>
              <div style={{ fontSize:".85rem", fontWeight:700, color:"#f1f5f9" }}>{priceInfo.duration_days || 120} days</div>
            </div>
          </div>

          <button onClick={handleBuy} style={{ width:"100%", padding:"13px", background:`linear-gradient(135deg,${exam.color},${exam.color}cc)`, border:"none", borderRadius:10, color:"#fff", fontWeight:800, fontSize:".95rem", cursor:"pointer", fontFamily:"inherit", display:"flex", alignItems:"center", justifyContent:"center", gap:8 }}>
            <ShoppingCart size={16} /> Buy Now — ₹{priceInfo.charge || priceInfo.price || 0}
          </button>
          <button onClick={onClose} style={{ width:"100%", marginTop:8, padding:"9px", background:"transparent", border:"1px solid #334155", borderRadius:10, color:"#64748b", fontSize:".8rem", cursor:"pointer", fontFamily:"inherit" }}>
            Maybe later
          </button>
        </>)}

        {step === "paying" && (
          <div style={{ textAlign:"center", padding:"20px 0" }}>
            <Loader size={36} style={{ animation:"spin 1s linear infinite", color:exam.color, marginBottom:16 }} />
            <p style={{ color:"#94a3b8", fontSize:".88rem" }}>Opening payment…</p>
            <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
          </div>
        )}

        {step === "success" && (
          <div style={{ textAlign:"center", padding:"20px 0" }}>
            <CheckCircle size={48} color="#22c55e" style={{ marginBottom:16 }} />
            <h3 style={{ fontSize:"1.1rem", fontWeight:800, color:"#f1f5f9", margin:"0 0 8px" }}>Pack Activated! 🎉</h3>
            <p style={{ color:"#94a3b8", fontSize:".82rem" }}>You now have full access to {exam.label} preparation. Loading…</p>
          </div>
        )}

        {step === "error" && (
          <div style={{ textAlign:"center", padding:"20px 0" }}>
            <XCircle size={36} color="#ef4444" style={{ marginBottom:12 }} />
            <p style={{ color:"#fca5a5", fontSize:".85rem", marginBottom:16 }}>{errMsg}</p>
            <button onClick={() => setStep("confirm")} style={{ padding:"9px 20px", background:exam.color, border:"none", borderRadius:8, color:"#fff", fontWeight:700, cursor:"pointer", fontFamily:"inherit" }}>Try Again</button>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Landing/Preview Page ──────────────────────────────────────────────────────
function ExamPrepLanding({ packs, prices, onEnterExam, onBuyPack }) {
  return (
    <div className="premium-page">
      <section className="premium-section">
        <div style={{ textAlign:"center", maxWidth:600, margin:"0 auto 32px" }}>
          <div style={{ fontSize:"2.5rem", marginBottom:12 }}>🎯</div>
          <h2 style={{ fontSize:"1.5rem", fontWeight:900, margin:"0 0 8px" }}>Exam Prep Center</h2>
          <p style={{ color:"var(--muted,#64748b)", fontSize:".88rem", lineHeight:1.6 }}>
            JEE Main · NEET UG · CUET UG — AI-powered practice questions, simulated full tests, and step-by-step explanations.
          </p>
          <div style={{ display:"inline-flex", background:"rgba(245,158,11,.1)", border:"1px solid rgba(245,158,11,.25)", color:"#fbbf24", padding:"4px 12px", borderRadius:20, fontSize:".7rem", fontWeight:700, marginTop:10 }}>
            Grade 11 & 12 only — purchase the pack to access
          </div>
        </div>

        {/* Exam Pack Cards */}
        <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fit,minmax(280px,1fr))", gap:16 }}>
          {Object.entries(EXAMS).map(([examType, exam]) => {
            const pack = packs?.[examType] || {};
            const price = prices?.[examType] || {};
            const owned = pack.active;
            return (
              <div key={examType} style={{ background:"var(--panel,#1e293b)", border:`2px solid ${owned ? exam.color : "var(--border,#334155)"}`, borderRadius:14, overflow:"hidden", transition:"all .15s" }}>
                {/* Card header */}
                <div style={{ background:`${exam.color}12`, padding:"18px 20px", display:"flex", justifyContent:"space-between", alignItems:"flex-start" }}>
                  <div>
                    <div style={{ fontSize:"1.8rem", marginBottom:4 }}>{exam.icon}</div>
                    <div style={{ fontWeight:800, fontSize:"1rem" }}>{exam.label}</div>
                    <div style={{ fontSize:".72rem", color:"var(--muted,#64748b)", marginTop:2 }}>{exam.subLabel}</div>
                  </div>
                  {owned ? (
                    <span style={{ background:"rgba(34,197,94,.15)", color:"#4ade80", border:"1px solid rgba(34,197,94,.3)", padding:"3px 10px", borderRadius:20, fontSize:".6rem", fontWeight:700 }}>✅ Active</span>
                  ) : (
                    <span style={{ background:"rgba(100,116,139,.1)", color:"#94a3b8", border:"1px solid #334155", padding:"3px 10px", borderRadius:20, fontSize:".6rem", fontWeight:700 }}>🔒 Locked</span>
                  )}
                </div>

                {/* What's inside preview */}
                <div style={{ padding:"14px 20px 0" }}>
                  {["Practice questions (Easy → Hard)", "AI step-by-step explanations", "Full simulated tests", "Weak topic tracker"].map(f => (
                    <div key={f} style={{ display:"flex", alignItems:"center", gap:7, fontSize:".75rem", color: owned ? "#94a3b8" : "#475569", marginBottom:6 }}>
                      {owned ? <CheckCircle size={12} color="#22c55e" /> : <Lock size={12} color="#475569" />}
                      {f}
                    </div>
                  ))}
                </div>

                {/* Action */}
                <div style={{ padding:"14px 20px 18px" }}>
                  {owned ? (
                    <div>
                      <button onClick={() => onEnterExam(examType)} style={{ width:"100%", padding:"11px", background:`linear-gradient(135deg,${exam.color},${exam.color}cc)`, border:"none", borderRadius:9, color:"#fff", fontWeight:700, fontSize:".88rem", cursor:"pointer", fontFamily:"inherit" }}>
                        Go to {exam.label} Prep →
                      </button>
                      {pack.expires_at && (
                        <div style={{ textAlign:"center", fontSize:".62rem", color:"var(--muted,#64748b)", marginTop:6 }}>
                          Valid until {new Date(pack.expires_at).toLocaleDateString("en-IN", { day:"numeric", month:"short", year:"numeric" })}
                        </div>
                      )}
                    </div>
                  ) : (
                    <div>
                      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:10 }}>
                        <span style={{ fontSize:"1.3rem", fontWeight:900, color:exam.color }}>₹{price.charge || price.price || "—"}</span>
                        <span style={{ fontSize:".7rem", color:"var(--muted,#64748b)" }}>{price.duration_days || 120} days</span>
                      </div>
                      <button onClick={() => onBuyPack(examType)} style={{ width:"100%", padding:"11px", background:exam.color, border:"none", borderRadius:9, color:"#fff", fontWeight:700, fontSize:".88rem", cursor:"pointer", fontFamily:"inherit", display:"flex", alignItems:"center", justifyContent:"center", gap:7 }}>
                        <ShoppingCart size={15} /> Unlock {exam.label}
                      </button>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Combo note */}
        <div style={{ marginTop:20, background:"rgba(99,102,241,.06)", border:"1px solid rgba(99,102,241,.2)", borderRadius:10, padding:"12px 16px", fontSize:".78rem", color:"var(--muted,#64748b)", textAlign:"center" }}>
          💡 You can buy 1, 2, or all 3 packs — each pack is independent. CBSE subscription not required.
        </div>
      </section>
    </div>
  );
}

// ── Exam Practice UI ─────────────────────────────────────────────────────────
function QuestionCard({ question, selectedOption, onSelect, feedback, showFeedback, username }) {
  const opts = question.options_json || [];
  const isCorrect = (key) => showFeedback && feedback?.correct_option === key;
  const isWrong   = (key) => showFeedback && selectedOption === key && !feedback?.is_correct;
  const watermarked = React.useMemo(() => embedWatermark(question.question_text, username), [question.question_text, username]);
  return (
    <div className="qprotect" onCopy={e => e.preventDefault()} onContextMenu={e => e.preventDefault()}
      style={{ padding:16, borderBottom:"1px solid var(--border,#334155)", userSelect:"none", WebkitUserSelect:"none" }}>
      <div style={{ display:"flex", gap:7, marginBottom:10, flexWrap:"wrap" }}>
        <span style={{ fontSize:".6rem", fontWeight:700, background:`${DIFFICULTY_COLORS[question.difficulty]||"#94a3b8"}22`, color:DIFFICULTY_COLORS[question.difficulty]||"#94a3b8", padding:"2px 8px", borderRadius:20 }}>{question.difficulty}</span>
        {question.topic && <span style={{ fontSize:".6rem", color:"var(--muted,#64748b)", background:"rgba(255,255,255,.05)", padding:"2px 8px", borderRadius:20 }}>{question.topic}</span>}
        {question.marks && <span style={{ fontSize:".6rem", color:"#fbbf24", background:"rgba(251,191,36,.08)", padding:"2px 8px", borderRadius:20 }}>+{question.marks} / -{question.negative_marks}</span>}
      </div>
      <MathText text={watermarked} style={{ fontSize:".85rem", color:"var(--text,#e2e8f0)", lineHeight:1.6, marginBottom:14, display:"block" }} />
      <div style={{ display:"flex", flexDirection:"column", gap:7 }}>
        {opts.map(opt => {
          const sel = selectedOption === opt.key;
          const correct = isCorrect(opt.key); const wrong = isWrong(opt.key);
          return (
            <div key={opt.key} onClick={() => !showFeedback && onSelect(opt.key)}
              style={{ display:"flex", alignItems:"flex-start", gap:10, padding:"10px 12px", borderRadius:8, cursor:showFeedback?"default":"pointer", background:correct?"rgba(34,197,94,.12)":wrong?"rgba(239,68,68,.1)":sel?"rgba(99,102,241,.12)":"rgba(0,0,0,.02)", border:`1px solid ${correct?"#22c55e":wrong?"#ef4444":sel?"#6366f1":"var(--border,#334155)"}`, transition:"all .1s" }}>
              <span style={{ width:22, height:22, borderRadius:"50%", border:`2px solid ${correct?"#22c55e":wrong?"#ef4444":sel?"#6366f1":"#64748b"}`, display:"flex", alignItems:"center", justifyContent:"center", flexShrink:0, fontSize:".68rem", fontWeight:700, color:correct?"#22c55e":wrong?"#ef4444":sel?"#6366f1":"#64748b" }}>{opt.key}</span>
              <MathText text={opt.text} style={{ fontSize:".8rem", color:"var(--text,#e2e8f0)", lineHeight:1.5, flex:1 }} />
              {correct && <CheckCircle size={14} color="#22c55e" />}
              {wrong && <XCircle size={14} color="#ef4444" />}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Main ExamPrepPage ─────────────────────────────────────────────────────────
export default function ExamPrepPage({ user }) {
  const [packs, setPacks]           = useState(null);  // null = loading
  const [prices, setPrices]         = useState({});
  const [activeExam, setActiveExam] = useState(null);  // null = landing, string = inside exam
  const [purchaseModal, setPurchaseModal] = useState(null); // exam type to show modal for
  const [loading, setLoading]       = useState(true);

  // Practice state
  const [subjects, setSubjects]         = useState([]);
  const [selectedSubject, setSelectedSubject] = useState(null);
  const [questions, setQuestions]       = useState([]);
  const [selectedOptions, setSelectedOptions] = useState({});
  const [feedbacks, setFeedbacks]       = useState({});
  const [loadingQ, setLoadingQ]         = useState(false);
  const [activeMode, setActiveMode]     = useState("practice");
  const [testSession, setTestSession]   = useState(null);
  const [testAnswers, setTestAnswers]   = useState({});
  const [testResult, setTestResult]     = useState(null);
  const [testLoading, setTestLoading]   = useState(false);
  const testStartRef = useRef(null);

  const grade = user?.grade || "";
  const isAdmin = user?.role === "admin";
  const isTestUser = user?.username === "akshita.teststudent";
  const gradeEligible = grade === "Grade 11" || grade === "Grade 12" || isAdmin || isTestUser;

  const accessToken = user?.accessToken;

  useEffect(() => {
    if (!accessToken) return;
    let cancelled = false;
    (async () => {
      try {
        const [packsData, pricesData] = await Promise.all([
          getMyPacks(accessToken),
          getPackPrices(),
        ]);
        if (cancelled) return;
        setPacks(packsData.packs || {});
        setPrices(pricesData.prices || {});
      } catch { /* non-critical — packs default to empty */ }
      finally { if (!cancelled) setLoading(false); }
    })();
    return () => { cancelled = true; };
  }, [accessToken]);

  function loadPacks() {
    if (!user?.accessToken) return;
    setLoading(true);
    Promise.all([getMyPacks(user.accessToken), getPackPrices()])
      .then(([pd, pr]) => { setPacks(pd.packs || {}); setPrices(pr.prices || {}); })
      .catch(() => { /* non-critical */ })
      .finally(() => setLoading(false));
  }

  // Grade gate
  if (!gradeEligible) {
    return (
      <div className="premium-page">
        <section className="premium-section" style={{ textAlign:"center", padding:"60px 20px" }}>
          <div style={{ fontSize:"3rem", marginBottom:16 }}>🔒</div>
          <h3 style={{ fontSize:"1.2rem", fontWeight:800, marginBottom:8 }}>Exam Prep Center</h3>
          <p style={{ color:"var(--muted,#64748b)", maxWidth:380, margin:"0 auto" }}>Available for Grade 11 & 12 students only.</p>
        </section>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="premium-page">
        <section className="premium-section" style={{ display:"flex", alignItems:"center", justifyContent:"center", minHeight:200 }}>
          <Loader size={20} style={{ animation:"spin 1s linear infinite", color:"var(--muted,#64748b)" }} />
          <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
        </section>
      </div>
    );
  }

  // Handle pack purchase success
  function handlePackSuccess(examType) {
    setPurchaseModal(null);
    loadPacks(); // refresh packs
    setActiveExam(examType); // immediately enter exam
  }

  // Enter an exam — check pack first
  function handleEnterExam(examType) {
    const owned = packs?.[examType]?.active;
    if (owned) {
      setActiveExam(examType);
      setActiveMode("practice");
      setTestResult(null); setTestSession(null);
      setSubjects([]); setQuestions([]);
      // Load subjects
      getExamPrepSubjects(user.accessToken, examType)
        .then(d => setSubjects(d.subjects || []))
        .catch(() => {});
    } else {
      setPurchaseModal(examType);
    }
  }

  // Exam practice functions
  async function handleSelectSubject(name) {
    if (selectedSubject === name) { setSelectedSubject(null); setQuestions([]); return; }
    setSelectedSubject(name);
    setLoadingQ(true);
    try {
      const [, questionsData] = await Promise.all([
        getExamPrepTopics(user.accessToken, activeExam, name),
        getExamPrepQuestions(user.accessToken, { exam: activeExam, subject: name, limit: 20 }),
      ]);
      setQuestions(questionsData.questions || []);
    } catch { setQuestions([]); }
    finally { setLoadingQ(false); }
  }

  async function handleSelectOption(qid, opt) {
    if (feedbacks[qid]) return;
    setSelectedOptions(p => ({ ...p, [qid]: opt }));
    try {
      const data = await submitQuestionAnswer(user.accessToken, qid, { selectedOption: opt });
      setFeedbacks(p => ({ ...p, [qid]: data }));
    } catch { /* non-critical */ }
  }

  async function handleStartTest() {
    setTestLoading(true);
    try {
      const data = await startSimulatedTest(user.accessToken, activeExam);
      setTestSession(data);
      const now = Date.now(); testStartRef.current = now;
      setTestAnswers({});
      setActiveMode("test");
      const qData = await getExamPrepQuestions(user.accessToken, { exam: activeExam, limit: 90 });
      setQuestions(qData.questions || []);
    } catch (e) { alert(e.message || "Failed to start test"); }
    finally { setTestLoading(false); }
  }

  async function handleSubmitTest() {
    if (!testSession?.test_id) return;
    setTestLoading(true);
    const timeSpent = testStartRef.current ? Math.round((Date.now()-testStartRef.current)/1000) : 0;
    const answers = Object.entries(testAnswers).map(([qid, opt]) => ({ question_id: qid, selected_option: opt, time_taken_seconds: 60 }));
    try {
      const result = await submitSimulatedTest(user.accessToken, testSession.test_id, { answers, timeSpentSeconds: timeSpent });
      setTestResult(result); setActiveMode("result");
    } catch (e) { alert(e.message || "Failed to submit"); }
    finally { setTestLoading(false); }
  }

  const examInfo = EXAMS[activeExam] || {};

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <>
      {/* Pack purchase modal */}
      {purchaseModal && (
        <PackPurchaseModal
          examType={purchaseModal}
          prices={prices}
          user={user}
          onSuccess={handlePackSuccess}
          onClose={() => setPurchaseModal(null)}
        />
      )}

      {/* Landing page — no active exam */}
      {!activeExam && (
        <ExamPrepLanding
          packs={packs}
          prices={prices}
          onEnterExam={handleEnterExam}
          onBuyPack={(et) => setPurchaseModal(et)}
        />
      )}

      {/* Inside an exam */}
      {activeExam && (
        <div className="premium-page">
          <section className="premium-section" style={{ paddingBottom:0 }}>
            {/* Top bar */}
            <div style={{ display:"flex", gap:10, alignItems:"center", marginBottom:16, flexWrap:"wrap" }}>
              <button onClick={() => setActiveExam(null)} style={{ padding:"6px 14px", background:"rgba(99,102,241,.1)", border:"1px solid rgba(99,102,241,.25)", borderRadius:8, color:"#a5b4fc", fontSize:".78rem", fontWeight:700, cursor:"pointer", fontFamily:"inherit" }}>
                ← All Exams
              </button>
              <div style={{ display:"flex", alignItems:"center", gap:8 }}>
                <span style={{ fontSize:"1.2rem" }}>{examInfo.icon}</span>
                <span style={{ fontWeight:800, fontSize:".95rem" }}>{examInfo.label} Prep</span>
                {packs?.[activeExam]?.expires_at && (
                  <span style={{ fontSize:".62rem", color:"var(--muted,#64748b)" }}>
                    · Valid until {new Date(packs[activeExam].expires_at).toLocaleDateString("en-IN", { day:"numeric", month:"short" })}
                  </span>
                )}
              </div>
              {/* Mode tabs */}
              <div style={{ marginLeft:"auto", display:"flex", gap:6 }}>
                {[{k:"practice",l:"⚡ Practice"},{k:"test",l:"📝 Simulated Test"}].map(m => (
                  <button key={m.k} onClick={() => setActiveMode(m.k)}
                    style={{ padding:"6px 14px", borderRadius:7, border:`1px solid ${activeMode===m.k?"#6366f1":"var(--border,#334155)"}`, background:activeMode===m.k?"rgba(99,102,241,.12)":"var(--panel,#1e293b)", color:activeMode===m.k?"#a5b4fc":"var(--muted,#94a3b8)", fontWeight:700, fontSize:".78rem", cursor:"pointer", fontFamily:"inherit" }}>
                    {m.l}
                  </button>
                ))}
              </div>
            </div>
          </section>

          {/* Practice mode */}
          {activeMode === "practice" && (
            <section className="premium-section" style={{ paddingTop:0 }}>
              {/* Subject selector */}
              <div style={{ display:"flex", gap:8, flexWrap:"wrap", marginBottom:14 }}>
                {subjects.map(s => (
                  <button key={s.name} onClick={() => handleSelectSubject(s.name)}
                    style={{ padding:"6px 14px", borderRadius:8, border:`2px solid ${selectedSubject===s.name?(SUBJECT_COLORS[s.name]||"#6366f1"):"var(--border,#334155)"}`, background:selectedSubject===s.name?`${SUBJECT_COLORS[s.name]||"#6366f1"}18`:"var(--panel,#1e293b)", color:selectedSubject===s.name?(SUBJECT_COLORS[s.name]||"#6366f1"):"var(--muted,#94a3b8)", fontWeight:700, fontSize:".78rem", cursor:"pointer", fontFamily:"inherit" }}>
                    {SUBJECT_ICONS[s.name]||"📚"} {s.name}
                  </button>
                ))}
                {subjects.length === 0 && <div style={{ fontSize:".78rem", color:"var(--muted,#64748b)" }}>Loading subjects…</div>}
              </div>

              {loadingQ ? (
                <div style={{ display:"flex", alignItems:"center", gap:8, color:"var(--muted,#64748b)", fontSize:".8rem" }}>
                  <Loader size={14} style={{ animation:"spin 1s linear infinite" }} /> Loading questions…
                  <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
                </div>
              ) : questions.length === 0 && selectedSubject ? (
                <div style={{ background:"var(--panel,#1e293b)", border:"1px solid var(--border,#334155)", borderRadius:10, padding:24, textAlign:"center" }}>
                  <div style={{ fontSize:"2rem", marginBottom:8 }}>📭</div>
                  <div style={{ fontSize:".85rem", fontWeight:700, marginBottom:6 }}>No questions yet</div>
                  <div style={{ fontSize:".75rem", color:"var(--muted,#64748b)" }}>Questions are being added. Check back soon!</div>
                </div>
              ) : questions.length > 0 ? (
                <div style={{ background:"var(--panel,#1e293b)", border:"1px solid var(--border,#334155)", borderRadius:12, overflow:"hidden" }}>
                  {questions.map(q => (
                    <QuestionCard key={q.id} question={q} selectedOption={selectedOptions[q.id]} onSelect={opt => handleSelectOption(q.id, opt)} feedback={feedbacks[q.id]} showFeedback={!!feedbacks[q.id]} username={user?.username} />
                  ))}
                </div>
              ) : !selectedSubject ? (
                <div style={{ textAlign:"center", padding:"40px 20px", color:"var(--muted,#64748b)" }}>
                  <div style={{ fontSize:"2rem", marginBottom:12 }}>👆</div>
                  <div style={{ fontSize:".85rem" }}>Select a subject above to start practicing</div>
                </div>
              ) : null}
            </section>
          )}

          {/* Simulated test mode */}
          {activeMode === "test" && !testResult && (
            <section className="premium-section" style={{ paddingTop:0 }}>
              {!testSession ? (
                <div style={{ maxWidth:500, margin:"0 auto", textAlign:"center", padding:"40px 20px" }}>
                  <div style={{ fontSize:"2.5rem", marginBottom:16 }}>{examInfo.icon}</div>
                  <h3 style={{ fontSize:"1.2rem", fontWeight:800, marginBottom:8 }}>Start {examInfo.label} Simulation</h3>
                  <p style={{ color:"var(--muted,#64748b)", fontSize:".85rem", marginBottom:24, lineHeight:1.6 }}>
                    Full {examInfo.label} test with {EXAM_SIM_CONFIG[activeExam]?.questions} questions · {EXAM_SIM_CONFIG[activeExam]?.duration} min · {EXAM_SIM_CONFIG[activeExam]?.marking}
                  </p>
                  <button onClick={handleStartTest} disabled={testLoading}
                    style={{ padding:"13px 32px", background:`linear-gradient(135deg,${examInfo.color},${examInfo.color}cc)`, border:"none", borderRadius:12, color:"#fff", fontWeight:800, fontSize:".95rem", cursor:"pointer", fontFamily:"inherit", opacity:testLoading?.7:1 }}>
                    {testLoading ? "Starting…" : `🚀 Start ${examInfo.label} Simulation`}
                  </button>
                </div>
              ) : (
                <div style={{ textAlign:"center", padding:32, color:"var(--muted,#64748b)" }}>
                  <div style={{ fontSize:"1.5rem", marginBottom:12 }}>📝</div>
                  <div style={{ fontSize:".88rem", marginBottom:16 }}>{questions.length} questions loaded · Timer running</div>
                  <button onClick={handleSubmitTest} disabled={testLoading}
                    style={{ padding:"10px 24px", background:"#22c55e", border:"none", borderRadius:9, color:"#fff", fontWeight:700, cursor:"pointer", fontFamily:"inherit" }}>
                    {testLoading ? "Submitting…" : "Submit Test ✓"}
                  </button>
                </div>
              )}
            </section>
          )}

          {/* Test result */}
          {activeMode === "result" && testResult && (
            <section className="premium-section" style={{ paddingTop:0 }}>
              <div style={{ maxWidth:600, margin:"0 auto", textAlign:"center" }}>
                <div style={{ fontSize:"3rem", marginBottom:8 }}>{(testResult.score_normalized||0) >= 60 ? "🏆" : "📚"}</div>
                <h3 style={{ fontSize:"1.3rem", fontWeight:800, marginBottom:4 }}>Test Complete!</h3>
                <div style={{ fontSize:"2rem", fontWeight:900, color:examInfo.color, marginBottom:16 }}>{(testResult.score_normalized||0).toFixed(1)}<span style={{ fontSize:"1rem", color:"var(--muted,#64748b)" }}>/100</span></div>
                <div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:10, marginBottom:20 }}>
                  {[["✅","Correct",testResult.correct],["❌","Wrong",testResult.wrong],["⏭","Skipped",testResult.skipped],["📋","Total",testResult.total_questions]].map(([ic,l,v]) => (
                    <div key={l} style={{ background:"var(--panel,#1e293b)", border:"1px solid var(--border,#334155)", borderRadius:9, padding:"12px 8px" }}>
                      <div style={{ fontSize:"1.2rem", marginBottom:4 }}>{ic}</div>
                      <div style={{ fontSize:"1.1rem", fontWeight:800 }}>{v||0}</div>
                      <div style={{ fontSize:".62rem", color:"var(--muted,#64748b)" }}>{l}</div>
                    </div>
                  ))}
                </div>
                <div style={{ display:"flex", gap:10, justifyContent:"center" }}>
                  <button onClick={() => { setActiveMode("test"); setTestResult(null); setTestSession(null); }} style={{ padding:"10px 22px", background:`linear-gradient(135deg,${examInfo.color},${examInfo.color}cc)`, border:"none", borderRadius:9, color:"#fff", fontWeight:700, cursor:"pointer", fontFamily:"inherit" }}>Try Again</button>
                  <button onClick={() => { setActiveMode("practice"); setTestResult(null); setTestSession(null); }} style={{ padding:"10px 22px", background:"var(--surface2,rgba(0,0,0,.04))", border:"1px solid var(--border,#334155)", borderRadius:9, color:"var(--text,#e2e8f0)", fontWeight:700, cursor:"pointer", fontFamily:"inherit" }}>Practice More</button>
                </div>
              </div>
            </section>
          )}
        </div>
      )}
    </>
  );
}
