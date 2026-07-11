/**
 * ExamPrepPage.jsx — JEE / NEET / CUET Exam Prep Center
 * ======================================================
 * Access: admin | Grade 11/12 students | akshita.teststudent
 *
 * Sections:
 *   1. Exam tabs (JEE active, NEET/CUET coming soon)
 *   2. Stats cards
 *   3. Subject cards → Topic priority cards
 *   4. Quick Practice (question list + AI explanation panel)
 *   5. Simulated Test mode
 *   6. Test Result page
 *   7. Resource links
 */

import React, { useEffect, useState, useRef } from "react";
import { Loader, CheckCircle, XCircle } from "lucide-react";
import {
  getExamPrepDashboard,
  getExamPrepSubjects,
  getExamPrepTopics,
  getExamPrepQuestions,
  submitQuestionAnswer,
  askFollowUp,
  startSimulatedTest,
  submitSimulatedTest,
  getSimTestHistory,
} from "../api/examPrep";

// ── Constants ──────────────────────────────────────────────────────────────────

// NOTE: Frontend does NOT infer Exam Prep access from plan strings.
// All access decisions come from GET /api/exam-prep/access-check (canonical backend).
const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const TEST_ACCESS_USERS = new Set(["akshita.teststudent"]);

const EXAMS = {
  jee_main:   { label: "JEE Main",   icon: "📐",  color: "#6366f1", active: true },
  neet_ug:    { label: "NEET UG",    icon: "🔬",  color: "#10b981", active: true },
  cuet_ug:    { label: "CUET UG",    icon: "🏛️",  color: "#f59e0b", active: true },
  sat:        { label: "SAT",        icon: "🎓",  color: "#3b82f6", active: true },
  ielts:      { label: "IELTS",      icon: "🌐",  color: "#8b5cf6", active: true },
  toefl_ibt:  { label: "TOEFL iBT", icon: "📡",  color: "#06b6d4", active: true },
};

// Exam-specific simulation config — aligned to NTA 2024–2026 official patterns
const EXAM_SIM_CONFIG = {
  // JEE Main: 75 questions (25/subject = 20 MCQ + 5 Numerical), 180 min, 300 marks, +4/−1
  sat:       { subjects: ["Reading & Writing", "Mathematics"], duration: 134, questions: 98, questionsPerSubject: null, marking: "+1 / 0 (No negative)", totalMarks: 1600 },
  ielts:     { subjects: ["Listening", "Reading", "Vocabulary & Grammar"], duration: 100, questions: 80, questionsPerSubject: null, marking: "+1 / 0 (Band 0–9)", totalMarks: 9 },
  toefl_ibt: { subjects: ["Reading", "Listening", "Integrated Skills"], duration: 71, questions: 48, questionsPerSubject: null, marking: "+1 / 0 (Score 0–120)", totalMarks: 120 },
  jee_main: { subjects: ["Physics", "Chemistry", "Mathematics"], duration: 180, questions: 75, questionsPerSubject: 25, marking: "+4 / −1 (MCQ & Numerical)", totalMarks: 300 },
  // NEET UG: 180 questions (45/subject), 180 min, 720 marks, +4/−1, Botany & Zoology separate
  neet_ug:  { subjects: ["Physics", "Chemistry", "Botany", "Zoology"], duration: 180, questions: 180, questionsPerSubject: 45, marking: "+4 / −1", totalMarks: 720 },
  // CUET UG: varies by subject selection, +5/−1
  cuet_ug:  { subjects: ["English", "General Test", "Domain Subject"], duration: 195, questions: 150, marking: "+5 / −1", totalMarks: null },
};

// ── CUET UG — NTA 2024 subject combination presets ────────────────────────────
// Section IA: Language (English mandatory) · Section II: Domain Subjects (2–6)
// Section III: General Test · Marking: +5 / -1
const CUET_DOMAIN_SUBJECTS = [
  "Physics (Domain)", "Chemistry (Domain)", "Mathematics (Domain)", "Biology (Domain)",
  "History", "Geography", "Political Science", "Economics",
  "Accountancy", "Business Studies", "Sociology", "Psychology", "Legal Studies",
  "English (Domain)", "Hindi (Domain)",
];
const CUET_PRESETS = [
  { id: "science_pcm",  label: "Science — PCM",  icon: "📐", color: "#6366f1", popular: true,
    desc: "Physics, Chemistry, Mathematics + English + General Test",
    subjects: ["English", "Physics (Domain)", "Chemistry (Domain)", "Mathematics (Domain)", "General Test"] },
  { id: "science_pcb",  label: "Science — PCB",  icon: "🔬", color: "#10b981", popular: true,
    desc: "Physics, Chemistry, Biology + English + General Test",
    subjects: ["English", "Physics (Domain)", "Chemistry (Domain)", "Biology (Domain)", "General Test"] },
  { id: "science_pcmb", label: "Science — PCMB", icon: "⚛️", color: "#8b5cf6", popular: false,
    desc: "Physics, Chemistry, Maths, Biology + English + General Test",
    subjects: ["English", "Physics (Domain)", "Chemistry (Domain)", "Mathematics (Domain)", "Biology (Domain)", "General Test"] },
  { id: "commerce",     label: "Commerce",        icon: "📊", color: "#f59e0b", popular: true,
    desc: "Accountancy, Business Studies, Economics + English + General Test",
    subjects: ["English", "Accountancy", "Business Studies", "Economics", "General Test"] },
  { id: "humanities",   label: "Humanities",      icon: "🏛️", color: "#ec4899", popular: true,
    desc: "History, Geography, Political Science + English + General Test",
    subjects: ["English", "History", "Geography", "Political Science", "General Test"] },
  { id: "custom",       label: "Custom",          icon: "⚙️", color: "#64748b", popular: false,
    desc: "Choose your own subject combination",
    subjects: [] },
];
const CUET_SUBJECT_ICONS = {
  "English": "📝", "General Test": "🧩",
  "Physics (Domain)": "⚛️", "Chemistry (Domain)": "🧪", "Mathematics (Domain)": "📐", "Biology (Domain)": "🌿",
  "History": "🏺", "Geography": "🌍", "Political Science": "🏛️", "Economics": "📊",
  "Accountancy": "📒", "Business Studies": "💼", "Sociology": "👥", "Psychology": "🧠", "Legal Studies": "⚖️",
  "English (Domain)": "📖", "Hindi (Domain)": "📜",
};

// ── Content protection — invisible zero-width character watermarking ───────────
// Encodes the user's username into the question text using zero-width characters
// (invisible to the eye, survives copy-paste). If a student shares a question,
// decoding the watermark reveals which account leaked it → account termination.
// 0 = U+200B (zero-width space), 1 = U+200C (ZWNJ), delimiter = U+200D (ZWJ)
function embedWatermark(text, username) {
  if (!text || !username) return text;
  try {
    const bits = username.split("").map(c => c.charCodeAt(0).toString(2).padStart(8, "0")).join("");
    const wm = "\u200D" + bits.split("").map(b => b === "1" ? "\u200C" : "\u200B").join("") + "\u200D";
    // Insert watermark after the first sentence (not at start, harder to notice)
    const dot = text.indexOf(". ");
    if (dot > 0) return text.slice(0, dot + 2) + wm + text.slice(dot + 2);
    return text + wm;
  } catch { return text; }
}

// ── Math/Chemistry text formatter ────────────────────────────────────────────
// Converts common notation to proper HTML superscripts/subscripts.
// Examples: H2O → H₂O  |  10^23 → 10²³  |  mol^-1 → mol⁻¹  |  \times → ×
function formatMathText(text) {
  if (!text) return "";
  let t = text;

  // LaTeX symbols
  t = t.replace(/\\times/g, "×");
  t = t.replace(/\\cdot/g, "·");
  t = t.replace(/\\pm/g, "±");
  t = t.replace(/\\alpha/g, "α");
  t = t.replace(/\\beta/g, "β");
  t = t.replace(/\\gamma/g, "γ");
  t = t.replace(/\\delta/g, "δ");
  t = t.replace(/\\Delta/g, "Δ");
  t = t.replace(/\\mu/g, "μ");
  t = t.replace(/\\pi/g, "π");
  t = t.replace(/\\theta/g, "θ");
  t = t.replace(/\\lambda/g, "λ");
  t = t.replace(/\\Omega/g, "Ω");
  t = t.replace(/\\omega/g, "ω");
  t = t.replace(/\\rightarrow/g, "→");
  t = t.replace(/\\leftarrow/g, "←");
  t = t.replace(/\\approx/g, "≈");
  t = t.replace(/\\neq/g, "≠");
  t = t.replace(/\\geq/g, "≥");
  t = t.replace(/\\leq/g, "≤");
  t = t.replace(/\\infty/g, "∞");
  t = t.replace(/\\sqrt\{([^}]+)\}/g, "√($1)");
  t = t.replace(/\\frac\{([^}]+)\}\{([^}]+)\}/g, "($1)/($2)");

  // Superscripts: ^{...} or ^X (single char/digit/sign)
  t = t.replace(/\^\{([^}]+)\}/g, (_, exp) => `<sup>${exp}</sup>`);
  t = t.replace(/\^([+-]?\d+)/g, (_, exp) => `<sup>${exp}</sup>`);
  t = t.replace(/\^([a-zA-Z])/g, (_, exp) => `<sup>${exp}</sup>`);

  // Subscripts: _{...} or _X
  t = t.replace(/_\{([^}]+)\}/g, (_, sub) => `<sub>${sub}</sub>`);
  t = t.replace(/_(\d+)/g, (_, sub) => `<sub>${sub}</sub>`);

  // Chemistry formulas: number after uppercase letter (e.g., H2O, CO2, NH3, CH4)
  // Only convert if not already wrapped in sub/sup tags
  t = t.replace(/([A-Z][a-z]?)(\d+)(?![^<]*>)/g, (_, el, num) => `${el}<sub>${num}</sub>`);

  return t;
}

// Component to safely render formatted math/chemistry text
function MathText({ text, style }) {
  const html = React.useMemo(() => formatMathText(text || ""), [text]);
  return <span dangerouslySetInnerHTML={{ __html: html }} style={style} />;
}

// ── CSS print block (added to document head once) ────────────────────────────
if (typeof document !== "undefined" && !document.getElementById("_qp_print_block")) {
  const s = document.createElement("style");
  s.id = "_qp_print_block";
  s.textContent = `@media print { .qprotect { display: none !important; } body::before { content: "© Likha Poha AI — Printing exam content is not permitted."; display:block; font-size:18px; padding:40px; text-align:center; } }`;
  document.head.appendChild(s);
}

const SUBJECT_ICONS = { Physics: "⚛️", Chemistry: "🧪", Mathematics: "📐", Biology: "🌿", Botany: "🌱", Zoology: "🦎" };
const SUBJECT_COLORS = { Physics: "#6366f1", Chemistry: "#10b981", Mathematics: "#f59e0b", Biology: "#22c55e", Botany: "#16a34a", Zoology: "#0891b2" };
const PRIORITY_COLORS = { HIGH: "#ef4444", MED: "#f59e0b", LOW: "#22c55e" };
const DIFFICULTY_COLORS = { easy: "#22c55e", medium: "#f59e0b", hard: "#ef4444" };

// ── Sub-components ─────────────────────────────────────────────────────────────

function StatCard({ value, label, icon, color = "#6366f1" }) {
  return (
    <div style={{ background: "var(--panel,#1e293b)", border: "1px solid var(--border,#334155)", borderRadius: 10, padding: "14px 16px", display: "flex", flexDirection: "column", gap: 4 }}>
      <div style={{ fontSize: "1.6rem", fontWeight: 800, color }}>{value}</div>
      <div style={{ fontSize: ".68rem", color: "var(--muted,#64748b)", display: "flex", alignItems: "center", gap: 4 }}>
        {icon && <span>{icon}</span>}
        {label}
      </div>
    </div>
  );
}

function SubjectCard({ subject, onClick, selected }) {
  const color = SUBJECT_COLORS[subject.name] || "#6366f1";
  return (
    <div onClick={onClick} className="premium-card" style={{ background: selected ? `${color}18` : undefined, border: `2px solid ${selected ? color : "var(--border,#334155)"}`, borderRadius: 12, padding: "16px", cursor: "pointer", transition: "all .15s", marginBottom: 0 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 10 }}>
        <span style={{ fontSize: "1.6rem" }}>{SUBJECT_ICONS[subject.name] || "📚"}</span>
        <span style={{ fontSize: ".65rem", fontWeight: 700, background: `${color}22`, color, padding: "2px 8px", borderRadius: 20 }}>{subject.weightage_pct}%</span>
      </div>
      <div style={{ fontWeight: 800, fontSize: ".9rem", marginBottom: 4 }}>{subject.name}</div>
      <div style={{ fontSize: ".7rem", color: "var(--muted,#64748b)", marginBottom: 10 }}>
        {subject.chapters} chapters · {subject.topic_count} topics
      </div>
      <div style={{ background: "rgba(99,102,241,.1)", borderRadius: 6, height: 4, overflow: "hidden" }}>
        <div style={{ width: `${Math.min(100, (subject.question_count / 50) * 100)}%`, height: "100%", background: `linear-gradient(90deg, ${color}, ${color}88)`, borderRadius: 6 }} />
      </div>
      <div style={{ fontSize: ".6rem", color: "var(--muted,#64748b)", marginTop: 5, display: "flex", justifyContent: "space-between" }}>
        <span>{subject.question_count} questions</span>
        <span style={{ color: selected ? color : "var(--muted,#64748b)" }}>{selected ? "▾ Topics" : "See topics →"}</span>
      </div>
    </div>
  );
}

function TopicCard({ topic, onPractice }) {
  const priorityColor = PRIORITY_COLORS[topic.priority] || "#94a3b8";
  return (
    <div className="premium-card" style={{ borderRadius: 10, padding: "14px 16px", marginBottom: 0 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
        <div style={{ fontWeight: 700, fontSize: ".85rem", flex: 1 }}>{topic.name}</div>
        <span style={{ fontSize: ".58rem", fontWeight: 800, background: `${priorityColor}22`, color: priorityColor, padding: "2px 7px", borderRadius: 20, marginLeft: 8, whiteSpace: "nowrap" }}>
          {topic.priority}
        </span>
      </div>
      <div style={{ fontSize: ".7rem", color: "var(--muted,#64748b)", marginBottom: 6 }}>{topic.ncert_chapter}</div>
      <div style={{ display: "flex", gap: 4, flexWrap: "wrap", marginBottom: 10 }}>
        {(topic.subtopics || []).slice(0, 3).map(s => (
          <span key={s} style={{ fontSize: ".6rem", background: "rgba(99,102,241,.1)", color: "#a5b4fc", padding: "2px 6px", borderRadius: 6 }}>{s}</span>
        ))}
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ fontSize: ".65rem", color: "var(--muted,#64748b)" }}>~{topic.weightage_pct}% weightage</span>
        <button onClick={() => onPractice(topic)} style={{ background: "#6366f1", border: "none", borderRadius: 6, padding: "5px 12px", color: "#fff", fontSize: ".7rem", fontWeight: 700, cursor: "pointer", fontFamily: "inherit" }}>
          Practice →
        </button>
      </div>
    </div>
  );
}

function QuestionCard({ question, selectedOption, onSelect, feedback, showFeedback, username }) {
  const opts = question.options_json || [];
  const isCorrect = (key) => showFeedback && feedback?.correct_option === key;
  const isWrong = (key) => showFeedback && selectedOption === key && !feedback?.is_correct;

  // Watermarked question text (invisible to eye, traceable if copied)
  const watermarkedText = React.useMemo(
    () => embedWatermark(question.question_text, username),
    [question.question_text, username]
  );

  function blockCopy(e) {
    e.preventDefault();
    // Silent block — don't alert (alerting annoys students who copy for legit reasons)
  }

  return (
    <div
      className="qprotect"
      onCopy={blockCopy}
      onContextMenu={e => e.preventDefault()}
      style={{ padding: "16px", borderBottom: "1px solid var(--border,#334155)", userSelect: "none", WebkitUserSelect: "none" }}>
      <div style={{ display: "flex", gap: 8, marginBottom: 10, flexWrap: "wrap" }}>
        <span style={{ fontSize: ".6rem", fontWeight: 700, background: `${DIFFICULTY_COLORS[question.difficulty] || "#94a3b8"}22`, color: DIFFICULTY_COLORS[question.difficulty] || "#94a3b8", padding: "2px 8px", borderRadius: 20 }}>{question.difficulty}</span>
        <span style={{ fontSize: ".6rem", color: "var(--muted,#64748b)", background: "rgba(255,255,255,.05)", padding: "2px 8px", borderRadius: 20 }}>{question.topic}</span>
        {question.marks && <span style={{ fontSize: ".6rem", color: "#fbbf24", background: "rgba(251,191,36,.08)", padding: "2px 8px", borderRadius: 20 }}>+{question.marks} / -{question.negative_marks}</span>}
      </div>
      <MathText text={watermarkedText} style={{ fontSize: ".85rem", color: "var(--text,#1e293b)", lineHeight: 1.6, marginBottom: 14, display: "block" }} />
      <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
        {opts.map(opt => {
          const isSelected = selectedOption === opt.key;
          const correct = isCorrect(opt.key);
          const wrong = isWrong(opt.key);
          return (
            <div key={opt.key} onClick={() => !showFeedback && onSelect(opt.key)}
              style={{ display: "flex", alignItems: "flex-start", gap: 10, padding: "10px 12px", borderRadius: 8, cursor: showFeedback ? "default" : "pointer", background: correct ? "rgba(34,197,94,.12)" : wrong ? "rgba(239,68,68,.1)" : isSelected ? "rgba(99,102,241,.12)" : "var(--surface2,rgba(0,0,0,.02))", border: `1px solid ${correct ? "#22c55e" : wrong ? "#ef4444" : isSelected ? "#6366f1" : "var(--border,#e2e8f0)"}`, transition: "all .1s" }}>
              <span style={{ width: 22, height: 22, borderRadius: "50%", border: `2px solid ${correct ? "#22c55e" : wrong ? "#ef4444" : isSelected ? "#6366f1" : "var(--border,#94a3b8)"}`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, fontSize: ".68rem", fontWeight: 700, color: correct ? "#22c55e" : wrong ? "#ef4444" : isSelected ? "#6366f1" : "var(--muted,#64748b)" }}>
                {opt.key}
              </span>
              <MathText text={opt.text} style={{ fontSize: ".8rem", color: "var(--text,#1e293b)", lineHeight: 1.5, flex: 1 }} />
              {correct && <CheckCircle size={14} color="#22c55e" style={{ flexShrink: 0, marginTop: 2 }} />}
              {wrong && <XCircle size={14} color="#ef4444" style={{ flexShrink: 0, marginTop: 2 }} />}
            </div>
          );
        })}
      </div>
      {question.ncert_reference && (
        <div style={{ marginTop: 8, fontSize: ".62rem", color: "var(--muted,#64748b)" }}>📖 {question.ncert_reference}</div>
      )}
    </div>
  );
}

function AIPanel({ question, feedback, user }) {
  const [followUp, setFollowUp] = useState("");
  const [fuLoading, setFuLoading] = useState(false);
  const [fuAnswer, setFuAnswer] = useState("");

  useEffect(() => { setFollowUp(""); setFuAnswer(""); }, [question?.id]);

  async function handleFollowUp(e) {
    e.preventDefault();
    if (!followUp.trim()) return;
    setFuLoading(true);
    try {
      const data = await askFollowUp(user.accessToken, {
        questionText: question.question_text,
        subject: question.subject || "Physics",
        exam: "JEE Main",
        followUp: followUp,
      });
      setFuAnswer(data.answer || "");
    } catch { setFuAnswer("Could not get AI answer. Try again."); }
    finally { setFuLoading(false); }
  }

  if (!question) {
    return (
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", padding: 24, color: "var(--muted,#64748b)", fontSize: ".78rem", textAlign: "center", gap: 12 }}>
        <div style={{ fontSize: "2.5rem" }}>🤖</div>
        <div>Select a question to get AI step-by-step explanation</div>
      </div>
    );
  }

  return (
    <div style={{ padding: 16, overflowY: "auto", height: "100%", fontSize: ".78rem", lineHeight: 1.6, color: "var(--text,#1e293b)" }}>
      {/* Question preview */}
      <div style={{ background: "var(--surface2,#f8fafc)", border: "1px solid var(--border,#e2e8f0)", borderRadius: 8, padding: 10, marginBottom: 12, fontSize: ".72rem", color: "var(--text-muted,#64748b)", fontStyle: "italic" }}>
        {question.question_text.length > 200 ? question.question_text.slice(0, 200) + "…" : question.question_text}
      </div>

      {/* Feedback */}
      {feedback && (
        <>
          <div style={{ background: feedback.is_correct ? "rgba(34,197,94,.1)" : "rgba(239,68,68,.08)", border: `1px solid ${feedback.is_correct ? "rgba(34,197,94,.3)" : "rgba(239,68,68,.25)"}`, borderRadius: 8, padding: "8px 12px", marginBottom: 10, display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ fontSize: "1rem" }}>{feedback.is_correct ? "✅" : "❌"}</span>
            <div>
              <div style={{ fontWeight: 700, fontSize: ".75rem", color: feedback.is_correct ? "#4ade80" : "#f87171" }}>
                {feedback.is_correct ? "Correct!" : "Incorrect"} · {feedback.marks_awarded > 0 ? "+" : ""}{feedback.marks_awarded} marks
              </div>
              <div style={{ fontSize: ".7rem", color: "var(--muted,#94a3b8)" }}>
                  Correct answer: <strong style={{ color: "#f1f5f9" }}>{feedback.correct_option}</strong>
                </div>
            </div>
          </div>

          {feedback.explanation && (
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: ".7rem", fontWeight: 700, color: "#a5b4fc", marginBottom: 6 }}>Explanation:</div>
              <div style={{ background: "rgba(99,102,241,.07)", border: "1px solid rgba(99,102,241,.2)", borderRadius: 8, padding: 10, fontSize: ".75rem", lineHeight: 1.9, color: "var(--text,#1e293b)" }}>
                {/* Split on "Step N:" or "Option X:" patterns so each step renders on its own line */}
                {feedback.explanation
                  .replace(/\s+(Step\s+\d+[:.])/g, '\n$1')
                  .replace(/\s+(Option\s+[A-D]:)/g, '\n$1')
                  .replace(/\s+(Therefore\b)/g, '\nTherefore')
                  .split('\n')
                  .filter(s => s.trim())
                  .map((line, i) => (
                    <div key={i} style={{ marginBottom: i < feedback.explanation.split('\n').length - 1 ? 4 : 0 }}>
                      {line.trim()}
                    </div>
                  ))
                }
              </div>
            </div>
          )}

          {feedback.formula_used && (
            <div style={{ background: "rgba(245,158,11,.06)", border: "1px solid rgba(245,158,11,.2)", borderRadius: 8, padding: "8px 10px", marginBottom: 10, fontSize: ".7rem" }}>
              <strong style={{ color: "#fbbf24" }}>Formula: </strong>{feedback.formula_used}
            </div>
          )}

          {/* Follow-up */}
          <form onSubmit={handleFollowUp} style={{ display: "flex", gap: 6, marginTop: 10 }}>
            <input value={followUp} onChange={e => setFollowUp(e.target.value)}
              placeholder="Ask AI: Why does this apply here?"
              style={{ flex: 1, background: "var(--surface2,#f8fafc)", border: "1px solid var(--border,#e2e8f0)", borderRadius: 6, padding: "6px 9px", color: "var(--text,#1e293b)", fontSize: ".72rem", fontFamily: "inherit" }} />
            <button type="submit" disabled={fuLoading || !followUp.trim()}
              style={{ padding: "6px 11px", background: "#6366f1", border: "none", borderRadius: 6, color: "#fff", fontWeight: 700, fontSize: ".72rem", cursor: "pointer", opacity: fuLoading ? .6 : 1, fontFamily: "inherit" }}>
              {fuLoading ? <Loader size={12} /> : "Ask ✦"}
            </button>
          </form>
          {fuAnswer && (
            <div style={{ background: "rgba(99,102,241,.06)", border: "1px solid rgba(99,102,241,.18)", borderRadius: 8, padding: 10, marginTop: 8, fontSize: ".72rem", lineHeight: 1.6, whiteSpace: "pre-wrap" }}>
              {fuAnswer}
            </div>
          )}
        </>
      )}

      {!feedback && (
        <div style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--muted,#64748b)", fontSize: ".75rem" }}>
          <Loader size={13} style={{ animation: "spin 1s linear infinite" }} />
          Select an option to get instant feedback & explanation
          <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
        </div>
      )}
    </div>
  );
}

// ── On-screen Calculator (basic — matches NTA JEE exam interface) ─────────────

function OnScreenCalc({ onClose }) {
  const [d, setD] = React.useState("0");
  const [p, setP] = React.useState(null);
  const [op, setOp] = React.useState(null);
  const [fr, setFr] = React.useState(true);

  function press(v) {
    if (v === "C")   { setD("0"); setP(null); setOp(null); setFr(true); return; }
    if (v === "+/-") { setD(x => String(-parseFloat(x) || 0)); return; }
    if (v === "%")   { setD(x => String(parseFloat(x) / 100)); return; }
    if (["÷", "×", "-", "+"].includes(v)) { setP(parseFloat(d)); setOp(v); setFr(true); return; }
    if (v === "=") {
      if (p === null || op === null) return;
      const a = p, b = parseFloat(d);
      const r = op==="+" ? a+b : op==="-" ? a-b : op==="×" ? a*b : (op==="÷"&&b!==0) ? a/b : "Err";
      setD(String(r)); setP(null); setOp(null); setFr(true); return;
    }
    if (v === ".") {
      if (fr) { setD("0."); setFr(false); return; }
      if (!d.includes(".")) setD(x => x + "."); return;
    }
    setD(fr ? v : d === "0" ? v : d + v);
    setFr(false);
  }

  const rows = [["%","C","+/-","÷"],["7","8","9","×"],["4","5","6","-"],["1","2","3","+"],[null,"0",".","="]];
  const orange = ["÷","×","-","+","="];
  const grey   = ["%","C","+/-"];

  return (
    <div style={{ position:"fixed", bottom:80, right:20, zIndex:10000, background:"#1c1c1e",
      border:"1px solid #3a3a3c", borderRadius:18, padding:14, width:218,
      boxShadow:"0 12px 40px rgba(0,0,0,.85)" }}>
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:8 }}>
        <span style={{ fontSize:".7rem", fontWeight:700, color:"#8e8e93" }}>Calculator (basic — no scientific in JEE)</span>
        <button onClick={onClose} style={{ background:"none", border:"none", color:"#8e8e93", cursor:"pointer", fontSize:"1rem", lineHeight:1 }}>✕</button>
      </div>
      <div style={{ background:"#000", borderRadius:10, padding:"8px 12px", marginBottom:10, textAlign:"right" }}>
        <div style={{ fontSize:".62rem", color:"#8e8e93", minHeight:16 }}>{op ? String(p) + " " + op : ""}</div>
        <div style={{ fontSize:"1.7rem", fontWeight:300, color:"#fff", overflow:"hidden", textOverflow:"ellipsis", letterSpacing:"-.02em" }}>{d}</div>
      </div>
      <div style={{ display:"flex", flexDirection:"column", gap:5 }}>
        {rows.map((row, ri) => (
          <div key={ri} style={{ display:"grid", gridTemplateColumns: ri===4 ? "2fr 1fr 1fr" : "1fr 1fr 1fr 1fr", gap:5 }}>
            {(ri === 4 ? ["0", ".", "="] : row).map(b => b === null ? null : (
              <button key={b} onClick={() => press(b)}
                style={{ padding:"13px 0", borderRadius:50, border:"none",
                  background: orange.includes(b) ? "#ff9f0a" : grey.includes(b) ? "#636366" : "#2c2c2e",
                  color:"#fff", fontWeight:500, fontSize:".9rem", cursor:"pointer", fontFamily:"inherit" }}>
                {b}
              </button>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

// ── NTA-style Test View (one question at a time + palette + section tabs) ───────

function NTATestView({ questions, testSession, testAnswers, setTestAnswers, onSubmit, testLoading, startTimestamp, examLabel: _examLabel, examColor: _examColor, cuetSubjects, username }) {
  // For CUET: use the subjects the student actually selected (passed via cuetSubjects).
  // For JEE/NEET: derive from EXAM_SIM_CONFIG by exam type (use examLabel to identify).
  // Fallback: match by duration — but note JEE (180min) and CUET (195min) differ, so this is safer.
  const isCuet = cuetSubjects && cuetSubjects.length > 0;
  const cfg = isCuet ? null : (
    _examLabel === "NEET UG" ? EXAM_SIM_CONFIG.neet_ug :
    _examLabel === "JEE Main" ? EXAM_SIM_CONFIG.jee_main :
    Object.values(EXAM_SIM_CONFIG).find(c => c.duration === testSession?.duration_minutes) || EXAM_SIM_CONFIG.jee_main
  );
  const subjects = isCuet ? cuetSubjects : cfg.subjects;
  const perSubj = Math.max(1, Math.ceil(questions.length / subjects.length));
  const [qIdx, setQIdx] = React.useState(0);
  const [marked, setMarked] = React.useState({});
  const [section, setSection] = React.useState(subjects[0]);
  const [showCalc, setShowCalc] = React.useState(false);
  const startTime = startTimestamp;

  function subjOf(i) {
    for (let s = 0; s < subjects.length; s++) if (i < (s+1)*perSubj || s === subjects.length-1) return subjects[s];
    return subjects[0];
  }

  const q = questions[qIdx];
  const opts = q?.options_json || [];
  const answered = Object.keys(testAnswers).filter(id => testAnswers[id]).length;

  function goTo(i) { setQIdx(i); setSection(subjOf(i)); }
  function saveNext() { if (qIdx+1 < questions.length) goTo(qIdx+1); }
  function markNext() { if (q) { setMarked(m => ({...m,[q.id]:!m[q.id]})); } saveNext(); }
  function clearAns() { if (q) setTestAnswers(p => { const n={...p}; delete n[q.id]; return n; }); }
  function doSubmit() {
    const left = questions.length - answered;
    if (left > 0 && !window.confirm(left + " unanswered. Submit test?")) return;
    onSubmit();
  }

  function qBtn(i) {
    const qid = questions[i]?.id;
    if (!qid) return { bg:"var(--panel,#1e293b)", color:"var(--muted,#94a3b8)", border:"1px solid var(--border,#334155)" };
    if (marked[qid] && testAnswers[qid]) return { bg:"#8b5cf6", color:"#fff", border:"none" };
    if (marked[qid]) return { bg:"rgba(139,92,246,.4)", color:"#c4b5fd", border:"1px solid #8b5cf6" };
    if (testAnswers[qid]) return { bg:"#22c55e", color:"#fff", border:"none" };
    if (i === qIdx) return { bg:"rgba(99,102,241,.2)", color:"#a5b4fc", border:"2px solid #6366f1" };
    return { bg:"var(--panel,#1e293b)", color:"var(--muted,#94a3b8)", border:"1px solid var(--border,#334155)" };
  }

  if (!questions.length) return (
    <div style={{ textAlign:"center", padding:48, color:"var(--muted,#64748b)" }}>
      <div style={{ fontSize:"2rem", marginBottom:12 }}>📭</div>
      <div style={{ fontWeight:700, marginBottom:6 }}>No questions yet</div>
      <button onClick={onSubmit} style={{ marginTop:16, padding:"10px 22px", background:"#6366f1", border:"none", borderRadius:8, color:"#fff", fontWeight:700, cursor:"pointer", fontFamily:"inherit" }}>End Test</button>
    </div>
  );

  return (
    <div>
      {/* Floating countdown timer */}
      <FloatingTimer startTime={startTime} durationMins={testSession?.duration_minutes||180} onExpire={doSubmit} />

      {showCalc && <OnScreenCalc onClose={()=>setShowCalc(false)} />}

      {/* Section tabs */}
      <div style={{ display:"flex", gap:6, marginBottom:14, flexWrap:"wrap" }}>
        {subjects.map(s => {
          const cnt = questions.filter((_,i) => subjOf(i)===s).length;
          const ans = questions.filter((_,i) => subjOf(i)===s && testAnswers[questions[i]?.id]).length;
          const act = section===s;
          const sc = SUBJECT_COLORS[s]||"#6366f1";
          return (
            <button key={s} onClick={()=>setSection(s)}
              style={{ padding:"7px 14px", borderRadius:10, border:"2px solid "+(act?sc:"var(--border,#334155)"), background:act?sc+"18":"var(--panel,#1e293b)", color:act?sc:"var(--muted,#94a3b8)", fontWeight:700, fontSize:".78rem", cursor:"pointer", fontFamily:"inherit", display:"flex", alignItems:"center", gap:6 }}>
              <span>{SUBJECT_ICONS[s]||"📚"}</span><span>{s}</span>
              <span style={{ fontSize:".6rem", background:act?sc+"22":"rgba(255,255,255,.06)", color:act?sc:"var(--muted,#64748b)", padding:"1px 6px", borderRadius:10 }}>{ans}/{cnt}</span>
            </button>
          );
        })}
      </div>

      {/* Main: question | palette */}
      <div style={{ display:"grid", gridTemplateColumns:"1fr 210px", gap:14, alignItems:"start" }}>

        {/* Question pane */}
        <div style={{ background:"var(--panel,#1e293b)", border:"1px solid var(--border,#334155)", borderRadius:12, overflow:"hidden" }}>
          {/* Header */}
          <div style={{ padding:"11px 16px", background:"rgba(99,102,241,.07)", borderBottom:"1px solid var(--border,#334155)", display:"flex", justifyContent:"space-between", alignItems:"center" }}>
            <div style={{ display:"flex", alignItems:"center", gap:10 }}>
              <span style={{ fontSize:".82rem", fontWeight:800 }}>Q {qIdx+1}</span>
              <span style={{ fontSize:".65rem", color:"var(--muted,#64748b)" }}>of {questions.length}</span>
              {marked[q?.id] && <span style={{ fontSize:".6rem", background:"rgba(139,92,246,.2)", color:"#a78bfa", padding:"1px 7px", borderRadius:20 }}>🚩 Marked</span>}
            </div>
            <div style={{ fontSize:".65rem", color:"var(--muted,#64748b)" }}>✅ {answered} / {questions.length} answered</div>
          </div>

          {/* Question body — copy protected */}
          <div
            className="qprotect"
            onCopy={e => e.preventDefault()}
            onContextMenu={e => e.preventDefault()}
            style={{ padding:"18px 20px", userSelect:"none", WebkitUserSelect:"none" }}>
            <div style={{ display:"flex", gap:7, marginBottom:12, flexWrap:"wrap" }}>
              <span style={{ fontSize:".6rem", fontWeight:700, background:(DIFFICULTY_COLORS[q?.difficulty]||"#94a3b8")+"22", color:DIFFICULTY_COLORS[q?.difficulty]||"#94a3b8", padding:"2px 8px", borderRadius:20 }}>{q?.difficulty}</span>
              {q?.topic && <span style={{ fontSize:".6rem", color:"var(--muted,#64748b)", background:"rgba(255,255,255,.05)", padding:"2px 8px", borderRadius:20 }}>{q.topic}</span>}
              {q?.marks && <span style={{ fontSize:".6rem", color:"#fbbf24", background:"rgba(251,191,36,.08)", padding:"2px 8px", borderRadius:20 }}>+{q.marks} / -{q.negative_marks}</span>}
            </div>
            <MathText text={embedWatermark(q?.question_text, username)} style={{ fontSize:".9rem", color:"var(--text,#1e293b)", lineHeight:1.65, marginBottom:18, display:"block" }} />
            <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
              {opts.map(opt => {
                const sel = testAnswers[q?.id] === opt.key;
                return (
                  <div key={opt.key} onClick={()=>{ if(q) setTestAnswers(p=>({...p,[q.id]:opt.key})); }}
                    style={{ display:"flex", alignItems:"flex-start", gap:10, padding:"11px 14px", borderRadius:9, cursor:"pointer", background:sel?"rgba(99,102,241,.12)":"var(--surface2,rgba(0,0,0,.02))", border:"1px solid "+(sel?"#6366f1":"var(--border,#e2e8f0)"), transition:"all .1s" }}>
                    <span style={{ width:24, height:24, borderRadius:"50%", border:"2px solid "+(sel?"#6366f1":"var(--border,#94a3b8)"), display:"flex", alignItems:"center", justifyContent:"center", flexShrink:0, fontSize:".7rem", fontWeight:700, color:sel?"#6366f1":"var(--muted,#64748b)", background:sel?"rgba(99,102,241,.15)":"transparent" }}>{opt.key}</span>
                    <MathText text={opt.text} style={{ fontSize:".85rem", color:"var(--text,#1e293b)", lineHeight:1.5 }} />
                  </div>
                );
              })}
            </div>
          </div>

          {/* Action buttons */}
          <div style={{ padding:"12px 16px", borderTop:"1px solid var(--border,#334155)", display:"flex", gap:8, flexWrap:"wrap", background:"var(--panel,#1e293b)", alignItems:"center" }}>
            {qIdx > 0 && <button onClick={()=>goTo(qIdx-1)} style={{ padding:"8px 14px", background:"rgba(255,255,255,.06)", border:"1px solid var(--border,#334155)", borderRadius:8, color:"var(--muted,#94a3b8)", fontSize:".78rem", cursor:"pointer", fontFamily:"inherit" }}>← Prev</button>}
            <button onClick={clearAns} style={{ padding:"8px 14px", background:"transparent", border:"1px solid rgba(239,68,68,.3)", borderRadius:8, color:"#f87171", fontSize:".78rem", cursor:"pointer", fontFamily:"inherit" }}>Clear</button>
            <button onClick={markNext} style={{ padding:"8px 14px", background:"rgba(139,92,246,.12)", border:"1px solid rgba(139,92,246,.3)", borderRadius:8, color:"#a78bfa", fontWeight:700, fontSize:".78rem", cursor:"pointer", fontFamily:"inherit" }}>🚩 Mark & Next</button>
            {/* Calculator button — inline so it's never hidden by other widgets */}
            <button onClick={()=>setShowCalc(v=>!v)} title="Basic Calculator"
              style={{ padding:"8px 13px", background:showCalc?"rgba(245,158,11,.15)":"rgba(99,102,241,.1)", border:"1px solid "+(showCalc?"rgba(245,158,11,.4)":"rgba(99,102,241,.3)"), borderRadius:8, color:showCalc?"#f59e0b":"#a5b4fc", fontWeight:700, fontSize:".82rem", cursor:"pointer", fontFamily:"inherit" }}>
              🔢 Calc
            </button>
            <button onClick={saveNext} style={{ padding:"8px 18px", background:"linear-gradient(135deg,#6366f1,#8b5cf6)", border:"none", borderRadius:8, color:"#fff", fontWeight:700, fontSize:".78rem", cursor:"pointer", fontFamily:"inherit", marginLeft:"auto" }}>Save & Next →</button>
          </div>
        </div>

        {/* Question palette */}
        <div style={{ background:"var(--panel,#1e293b)", border:"1px solid var(--border,#334155)", borderRadius:12, overflow:"hidden" }}>
          <div style={{ padding:"10px 12px", borderBottom:"1px solid var(--border,#334155)", fontSize:".7rem", fontWeight:700, color:"var(--muted,#64748b)" }}>Question Palette</div>
          {/* Legend */}
          <div style={{ padding:"8px 12px", borderBottom:"1px solid var(--border,#334155)", display:"flex", flexDirection:"column", gap:4 }}>
            {[{c:"#22c55e",l:"Answered"},{c:"#8b5cf6",l:"Marked for Review"},{c:"var(--panel,#1e293b)",l:"Not Answered"}].map(({c,l})=>(
              <div key={l} style={{ display:"flex", alignItems:"center", gap:6 }}>
                <div style={{ width:12, height:12, borderRadius:3, background:c, border:"1px solid var(--border,#334155)", flexShrink:0 }} />
                <span style={{ fontSize:".6rem", color:"var(--muted,#64748b)" }}>{l}</span>
              </div>
            ))}
          </div>
          {/* Number grid */}
          <div style={{ padding:"10px 12px", display:"grid", gridTemplateColumns:"repeat(5,1fr)", gap:5, maxHeight:320, overflowY:"auto" }}>
            {questions.map((_,i) => {
              const bs = qBtn(i);
              return (
                <button key={i} onClick={()=>goTo(i)}
                  style={{ padding:"7px 0", borderRadius:7, fontSize:".72rem", fontWeight:700, cursor:"pointer", fontFamily:"inherit", background:bs.bg, color:bs.color, border:bs.border }}>
                  {i+1}
                </button>
              );
            })}
          </div>
          {/* Submit */}
          <div style={{ padding:"12px" }}>
            <button onClick={doSubmit} disabled={testLoading}
              style={{ width:"100%", padding:"10px 0", background:"#22c55e", border:"none", borderRadius:9, color:"#fff", fontWeight:800, fontSize:".82rem", cursor:"pointer", fontFamily:"inherit", opacity:testLoading?.6:1 }}>
              {testLoading ? "Submitting…" : "Submit Test ✓"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Floating Timer ─────────────────────────────────────────────────────────────

function FloatingTimer({ startTime, durationMins, onExpire }) {
  const [left, setLeft] = React.useState(durationMins * 60);
  React.useEffect(() => {
    const id = setInterval(() => {
      const r = Math.max(0, durationMins * 60 - Math.floor((Date.now() - startTime) / 1000));
      setLeft(r);
      if (r === 0) { clearInterval(id); if (onExpire) onExpire(); }
    }, 1000);
    return () => clearInterval(id);
  }, [startTime, durationMins, onExpire]);
  const m = Math.floor(left / 60), s = left % 60;
  const pct = left / (durationMins * 60);
  const clr = pct > 0.33 ? "#22c55e" : pct > 0.15 ? "#f59e0b" : "#ef4444";
  return (
    <div style={{ position:"fixed", top:68, right:16, zIndex:9999, background:"var(--panel,#1e293b)", border:"2px solid "+clr, borderRadius:14, padding:"9px 15px", display:"flex", alignItems:"center", gap:10, boxShadow:"0 4px 20px "+clr+"55", animation:pct<0.15?"_btimer 1s infinite":undefined }}>
      <style>{"@keyframes _btimer{0%,100%{opacity:1}50%{opacity:.6}}"}</style>
      <span style={{ fontSize:"1.3rem" }}>⏱</span>
      <div>
        <div style={{ fontSize:"1.1rem", fontWeight:900, color:clr, letterSpacing:".04em" }}>{String(m).padStart(2,"0")}:{String(s).padStart(2,"0")}</div>
        <div style={{ fontSize:".55rem", color:"var(--muted,#64748b)" }}>Remaining</div>
      </div>
    </div>
  );
}

// ── Test Result Component ──────────────────────────────────────────────────────

function TestResultPage({ result, onRetake, onClose }) {
  const score = result?.score_normalized ?? 0;
  const scoreColor = score >= 60 ? "#22c55e" : score >= 40 ? "#f59e0b" : "#ef4444";

  return (
    <div className="premium-section" style={{ maxWidth: 720, margin: "0 auto" }}>
      <div style={{ textAlign: "center", marginBottom: 28 }}>
        <div style={{ fontSize: "3rem", marginBottom: 8 }}>{score >= 60 ? "🏆" : score >= 40 ? "💪" : "📚"}</div>
        <h3 style={{ margin: "0 0 4px", fontSize: "1.3rem", fontWeight: 800 }}>Test Complete!</h3>
        <p style={{ color: "var(--muted,#64748b)", fontSize: ".85rem" }}>{result?.exam_type?.replace("_", " ").toUpperCase()} Simulated Test</p>
      </div>

      {/* Score circle */}
      <div style={{ display: "flex", justifyContent: "center", marginBottom: 24 }}>
        <div style={{ width: 120, height: 120, borderRadius: "50%", border: `6px solid ${scoreColor}`, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", background: `${scoreColor}12` }}>
          <div style={{ fontSize: "2rem", fontWeight: 900, color: scoreColor }}>{score.toFixed(1)}</div>
          <div style={{ fontSize: ".62rem", color: "var(--muted,#64748b)" }}>out of 100</div>
        </div>
      </div>

      {/* Stats grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10, marginBottom: 20 }}>
        <StatCard value={result?.total_questions || 0} label="Questions" icon="📋" color="#6366f1" />
        <StatCard value={result?.correct || 0} label="Correct" icon="✅" color="#22c55e" />
        <StatCard value={result?.wrong || 0} label="Wrong" icon="❌" color="#ef4444" />
        <StatCard value={result?.skipped || 0} label="Skipped" icon="⏭️" color="#94a3b8" />
      </div>

      {/* Subject scores */}
      {result?.subject_scores && Object.keys(result.subject_scores).length > 0 && (
        <div style={{ background: "var(--panel,#1e293b)", border: "1px solid var(--border,#334155)", borderRadius: 10, padding: 16, marginBottom: 16 }}>
          <div style={{ fontSize: ".75rem", fontWeight: 700, color: "#a5b4fc", marginBottom: 12 }}>Subject-wise Score</div>
          {Object.entries(result.subject_scores).map(([subj, data]) => {
            const subjectScore = data.score || 0;
            const maxScore = data.max_score || 1;
            const pct = Math.max(0, Math.min(100, (subjectScore / maxScore) * 100));
            const color = SUBJECT_COLORS[subj] || "#6366f1";
            return (
              <div key={subj} style={{ marginBottom: 10 }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                  <span style={{ fontSize: ".75rem", fontWeight: 600 }}>{subj}</span>
                  <span style={{ fontSize: ".72rem", color: "var(--muted,#64748b)" }}>{data.correct}✓ {data.wrong}✗ | {subjectScore.toFixed(1)} / {maxScore.toFixed(1)}</span>
                </div>
                <div style={{ background: "var(--surface2,rgba(0,0,0,.07))", borderRadius: 6, height: 6 }}>
                  <div style={{ width: `${pct}%`, height: "100%", background: `linear-gradient(90deg, ${color}, ${color}88)`, borderRadius: 6, transition: "width .5s" }} />
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Weak topics */}
      {result?.weak_topics?.length > 0 && (
        <div style={{ background: "rgba(239,68,68,.05)", border: "1px solid rgba(239,68,68,.2)", borderRadius: 10, padding: 14, marginBottom: 16 }}>
          <div style={{ fontSize: ".75rem", fontWeight: 700, color: "#f87171", marginBottom: 8 }}>⚠️ Weak Topics — Needs Revision</div>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            {result.weak_topics.map(t => (
              <span key={t} style={{ fontSize: ".65rem", background: "rgba(239,68,68,.1)", color: "#f87171", padding: "3px 9px", borderRadius: 20 }}>{t}</span>
            ))}
          </div>
        </div>
      )}

      {/* AI recommendations */}
      {result?.ai_recommendations?.length > 0 && (
        <div style={{ background: "rgba(99,102,241,.05)", border: "1px solid rgba(99,102,241,.2)", borderRadius: 10, padding: 14, marginBottom: 20 }}>
          <div style={{ fontSize: ".75rem", fontWeight: 700, color: "#a5b4fc", marginBottom: 8 }}>🤖 AI Recommendations</div>
          <ul style={{ margin: 0, paddingLeft: 16 }}>
            {result.ai_recommendations.map((r, i) => (
              <li key={i} style={{ fontSize: ".75rem", color: "var(--text,#1e293b)", marginBottom: 4, lineHeight: 1.5 }}>{r}</li>
            ))}
          </ul>
        </div>
      )}

      <div style={{ display: "flex", gap: 10, justifyContent: "center" }}>
        <button onClick={onRetake} style={{ padding: "11px 24px", background: "linear-gradient(135deg,#6366f1,#8b5cf6)", border: "none", borderRadius: 10, color: "#fff", fontWeight: 700, fontSize: ".88rem", cursor: "pointer", fontFamily: "inherit" }}>
          Try Again
        </button>
        <button onClick={onClose} style={{ padding: "11px 24px", background: "var(--surface2,rgba(0,0,0,.04))", border: "1px solid var(--border,#e2e8f0)", borderRadius: 10, color: "var(--text,#1e293b)", fontWeight: 700, fontSize: ".88rem", cursor: "pointer", fontFamily: "inherit" }}>
          Back to Dashboard
        </button>
      </div>
    </div>
  );
}

// ── CUET Test Setup ───────────────────────────────────────────────────────────
function CUETTestSetup({ onStart, testLoading }) {
  const [presetId, setPresetId] = React.useState("science_pcm");
  const [customSubjs, setCustomSubjs] = React.useState(["English", "General Test"]);
  const [step, setStep] = React.useState("preset");

  const activePreset = CUET_PRESETS.find(p => p.id === presetId);
  const finalSubjects = presetId === "custom" ? customSubjs : (activePreset?.subjects || []);
  const duration = finalSubjects.reduce((acc, s) => acc + (s === "General Test" ? 60 : 45), 0);
  const canStart = finalSubjects.length >= 2 && finalSubjects.includes("English");

  function toggleCustom(s) {
    if (s === "English") return;
    setCustomSubjs(prev => prev.includes(s) ? prev.filter(x => x !== s) : [...prev, s]);
  }

  return (
    <div style={{ maxWidth: 680, margin: "0 auto", padding: "10px 0 20px" }}>
      <div style={{ textAlign: "center", marginBottom: 20 }}>
        <div style={{ fontSize: "2.2rem", marginBottom: 6 }}>🏛️</div>
        <h3 style={{ fontSize: "1.1rem", fontWeight: 800, margin: "0 0 4px" }}>CUET UG — Choose Your Subject Combination</h3>
        <p style={{ color: "var(--muted,#64748b)", fontSize: ".78rem", margin: 0 }}>
          Based on NTA CUET UG structure · English (mandatory) + Domain Subjects + General Test · <strong>+5 / -1</strong> marking
        </p>
      </div>

      {/* Section info */}
      <div style={{ background: "rgba(245,158,11,.06)", border: "1px solid rgba(245,158,11,.2)", borderRadius: 9, padding: "8px 14px", marginBottom: 18, display: "flex", gap: 14, flexWrap: "wrap", fontSize: ".7rem", color: "var(--muted,#64748b)" }}>
        <span>📝 <strong style={{ color: "#f59e0b" }}>Section IA</strong> — Language (English, mandatory)</span>
        <span>📚 <strong style={{ color: "#6366f1" }}>Section II</strong> — Domain Subjects (2–6)</span>
        <span>🧩 <strong style={{ color: "#8b5cf6" }}>Section III</strong> — General Test (most universities require)</span>
      </div>

      {/* Preset step */}
      {step === "preset" && (
        <>
          <div style={{ fontSize: ".68rem", fontWeight: 700, color: "var(--muted,#64748b)", textTransform: "uppercase", letterSpacing: ".05em", marginBottom: 10 }}>Select Your Stream</div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(190px,1fr))", gap: 9, marginBottom: 18 }}>
            {CUET_PRESETS.map(preset => {
              const sel = presetId === preset.id;
              return (
                <div key={preset.id}
                  onClick={() => { setPresetId(preset.id); if (preset.id === "custom") setStep("custom"); }}
                  style={{ background: sel ? `${preset.color}12` : "var(--panel,#1e293b)", border: `2px solid ${sel ? preset.color : "var(--border,#334155)"}`, borderRadius: 9, padding: "12px 12px", cursor: "pointer", position: "relative" }}>
                  {preset.popular && (
                    <span style={{ position: "absolute", top: 7, right: 7, fontSize: ".52rem", background: "#22c55e22", color: "#22c55e", padding: "1px 5px", borderRadius: 8, fontWeight: 700 }}>Popular</span>
                  )}
                  <div style={{ fontSize: "1.3rem", marginBottom: 5 }}>{preset.icon}</div>
                  <div style={{ fontWeight: 800, fontSize: ".82rem", marginBottom: 3, color: sel ? preset.color : "var(--text,#1e293b)" }}>{preset.label}</div>
                  <div style={{ fontSize: ".65rem", color: "var(--muted,#64748b)", lineHeight: 1.4 }}>{preset.desc}</div>
                </div>
              );
            })}
          </div>

          {presetId !== "custom" && activePreset && (
            <div style={{ background: "var(--panel,#1e293b)", border: "1px solid var(--border,#334155)", borderRadius: 9, padding: "12px 14px", marginBottom: 18 }}>
              <div style={{ fontSize: ".68rem", fontWeight: 700, color: "#a5b4fc", marginBottom: 8 }}>{activePreset.label} — Sections in This Simulation</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 10 }}>
                {activePreset.subjects.map(s => (
                  <div key={s} style={{ display: "flex", alignItems: "center", gap: 5, background: s === "English" ? "rgba(99,102,241,.1)" : s === "General Test" ? "rgba(139,92,246,.1)" : "rgba(245,158,11,.07)", border: `1px solid ${s === "English" ? "rgba(99,102,241,.25)" : s === "General Test" ? "rgba(139,92,246,.25)" : "rgba(245,158,11,.2)"}`, borderRadius: 7, padding: "5px 9px", fontSize: ".7rem", fontWeight: 600 }}>
                    <span>{CUET_SUBJECT_ICONS[s] || "📚"}</span>
                    <span>{s}</span>
                    <span style={{ fontSize: ".58rem", color: "var(--muted,#64748b)" }}>{s === "General Test" ? "50Q" : "40Q"}</span>
                  </div>
                ))}
              </div>
              <div style={{ display: "flex", gap: 14, fontSize: ".68rem", color: "var(--muted,#64748b)" }}>
                <span>⏱ <strong>{duration} min</strong></span>
                <span>📋 <strong>~{finalSubjects.length * 40} questions</strong></span>
                <span>📊 <strong>+5 / -1</strong></span>
                <span>🎯 <strong>{activePreset.subjects.length} sections</strong></span>
              </div>
            </div>
          )}
        </>
      )}

      {/* Custom step */}
      {step === "custom" && (
        <>
          <button onClick={() => { setStep("preset"); setPresetId("science_pcm"); }}
            style={{ background: "none", border: "none", color: "#6366f1", cursor: "pointer", fontSize: ".78rem", fontFamily: "inherit", padding: 0, marginBottom: 14 }}>
            ← Back to presets
          </button>

          <div style={{ marginBottom: 12 }}>
            <div style={{ fontSize: ".68rem", fontWeight: 700, color: "#6366f1", textTransform: "uppercase", letterSpacing: ".05em", marginBottom: 6 }}>Section IA — Language (Mandatory)</div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, background: "rgba(99,102,241,.1)", border: "1px solid rgba(99,102,241,.25)", borderRadius: 7, padding: "8px 12px" }}>
              <span>📝</span><span style={{ fontSize: ".8rem", fontWeight: 700 }}>English</span>
              <span style={{ fontSize: ".62rem", color: "#6366f1", marginLeft: "auto" }}>Required · 40 Qs · 45 min</span>
            </div>
          </div>

          <div style={{ marginBottom: 12 }}>
            <div style={{ fontSize: ".68rem", fontWeight: 700, color: "#f59e0b", textTransform: "uppercase", letterSpacing: ".05em", marginBottom: 6 }}>Section II — Domain Subjects (Choose 2–6)</div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(185px,1fr))", gap: 5 }}>
              {CUET_DOMAIN_SUBJECTS.map(s => {
                const chk = customSubjs.includes(s);
                return (
                  <div key={s} onClick={() => toggleCustom(s)}
                    style={{ display: "flex", alignItems: "center", gap: 7, background: chk ? "rgba(245,158,11,.08)" : "var(--panel,#1e293b)", border: `1px solid ${chk ? "rgba(245,158,11,.35)" : "var(--border,#334155)"}`, borderRadius: 7, padding: "7px 10px", cursor: "pointer" }}>
                    <div style={{ width: 13, height: 13, borderRadius: 3, border: `2px solid ${chk ? "#f59e0b" : "#64748b"}`, background: chk ? "#f59e0b" : "transparent", flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center" }}>
                      {chk && <span style={{ color: "#fff", fontSize: ".55rem", fontWeight: 900 }}>✓</span>}
                    </div>
                    <span style={{ fontSize: ".68rem", fontWeight: chk ? 700 : 400 }}>{CUET_SUBJECT_ICONS[s] || "📚"} {s}</span>
                  </div>
                );
              })}
            </div>
          </div>

          <div style={{ marginBottom: 14 }}>
            <div style={{ fontSize: ".68rem", fontWeight: 700, color: "#8b5cf6", textTransform: "uppercase", letterSpacing: ".05em", marginBottom: 6 }}>Section III — General Test</div>
            <div onClick={() => toggleCustom("General Test")}
              style={{ display: "flex", alignItems: "center", gap: 8, background: customSubjs.includes("General Test") ? "rgba(139,92,246,.08)" : "var(--panel,#1e293b)", border: `1px solid ${customSubjs.includes("General Test") ? "rgba(139,92,246,.35)" : "var(--border,#334155)"}`, borderRadius: 7, padding: "8px 12px", cursor: "pointer" }}>
              <div style={{ width: 13, height: 13, borderRadius: 3, border: `2px solid ${customSubjs.includes("General Test") ? "#8b5cf6" : "#64748b"}`, background: customSubjs.includes("General Test") ? "#8b5cf6" : "transparent", flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center" }}>
                {customSubjs.includes("General Test") && <span style={{ color: "#fff", fontSize: ".55rem", fontWeight: 900 }}>✓</span>}
              </div>
              <span style={{ fontSize: ".8rem", fontWeight: 700 }}>🧩 General Test</span>
              <span style={{ fontSize: ".62rem", color: "var(--muted,#64748b)", marginLeft: "auto" }}>50 Qs · 60 min</span>
            </div>
          </div>

          {finalSubjects.length >= 2 && (
            <div style={{ background: "rgba(99,102,241,.06)", border: "1px solid rgba(99,102,241,.2)", borderRadius: 8, padding: "9px 12px", marginBottom: 14, fontSize: ".7rem" }}>
              <strong style={{ color: "#a5b4fc" }}>Selected:</strong> {finalSubjects.length} sections · <strong>{duration} min</strong> · <strong>~{finalSubjects.length * 40} questions</strong> · +5 / -1
            </div>
          )}
        </>
      )}

      <button
        onClick={() => canStart && onStart(finalSubjects)}
        disabled={testLoading || !canStart}
        style={{ padding: "12px 28px", background: canStart ? "linear-gradient(135deg,#f59e0b,#d97706)" : "var(--border,#334155)", border: "none", borderRadius: 10, color: canStart ? "#fff" : "var(--muted,#64748b)", fontWeight: 800, fontSize: ".9rem", cursor: canStart ? "pointer" : "not-allowed", fontFamily: "inherit", display: "flex", alignItems: "center", gap: 10, opacity: testLoading ? .7 : 1 }}>
        {testLoading ? <><Loader size={16} style={{ animation: "spin 1s linear infinite" }} /> Starting…</> : `🚀 Start CUET Simulation (${finalSubjects.length} sections · ${duration} min)`}
      </button>
      {!canStart && !testLoading && (
        <div style={{ fontSize: ".68rem", color: "var(--muted,#64748b)", marginTop: 6 }}>Select at least 2 subjects (English is mandatory)</div>
      )}
    </div>
  );
}

// ── Quick Reference Data — static, hardcoded per exam × subject ───────────────
// No backend call needed. Organized by exam key → subject name → sections.
// Each section: formulas[], constants[], traps[], mnemonics[], revision[]
const QUICK_REFERENCE = {
  jee_main: {
    subjects: ["Physics", "Chemistry", "Mathematics"],
    Physics: {
      formulas: [
        { expr: "v = u + at", desc: "Kinematics · time-based velocity" },
        { expr: "s = ut + ½at²", desc: "Kinematics · displacement" },
        { expr: "v² = u² + 2as", desc: "Kinematics · time-independent" },
        { expr: "F = ma", desc: "Newton's 2nd Law · net force = mass × acceleration" },
        { expr: "W_net = ΔKE", desc: "Work-Energy theorem · net work = change in kinetic energy" },
        { expr: "p = mv · J = FΔt = Δp", desc: "Momentum and Impulse" },
        { expr: "KE = ½mv²", desc: "Kinetic energy · for rotation: KE = ½Iω²" },
        { expr: "PE = mgh", desc: "Gravitational PE · elastic: PE = ½kx²" },
        { expr: "F = GMm/r²", desc: "Gravitation · G = 6.67 × 10⁻¹¹ N m² kg⁻²" },
        { expr: "v_esc = √(2GM/R)", desc: "Escape velocity · for Earth ≈ 11.2 km/s" },
        { expr: "T = 2π√(l/g)", desc: "Simple pendulum · mass independent!" },
        { expr: "x = A sin(ωt + φ) · a = −ω²x", desc: "SHM displacement and acceleration" },
        { expr: "PV = nRT · PV/T = const", desc: "Ideal Gas · R = 8.314 J mol⁻¹ K⁻¹" },
        { expr: "η = 1 − T_cold/T_hot", desc: "Carnot efficiency · max possible heat engine efficiency" },
        { expr: "F = kq₁q₂/r²", desc: "Coulomb's Law · k = 9 × 10⁹ N m² C⁻²" },
        { expr: "C = Q/V · C_parallel = ε₀A/d", desc: "Capacitance · parallel plate" },
        { expr: "V = IR · P = I²R = V²/R", desc: "Ohm's Law and power" },
        { expr: "F = qvB sinθ · F = BIL sinθ", desc: "Magnetic force on charge and current" },
        { expr: "ε = −dΦ/dt = −NdΦ/dt", desc: "Faraday's law of EMI" },
        { expr: "V₁/V₂ = N₁/N₂ = I₂/I₁", desc: "Transformer · ideal (no losses)" },
        { expr: "n₁ sinθ₁ = n₂ sinθ₂", desc: "Snell's law · at interface of two media" },
        { expr: "1/f = 1/v + 1/u", desc: "Mirror/Lens formula" },
        { expr: "KE_max = hf − φ", desc: "Photoelectric effect · φ = work function" },
        { expr: "N = N₀ e^(−λt) · t½ = 0.693/λ", desc: "Radioactive decay · half-life" },
        { expr: "E = hf = hc/λ", desc: "Photon energy · λ = h/p (de Broglie)" },
      ],
      constants: [
        { name: "g (Earth)", value: "9.8 m/s² — use 10 m/s² in JEE" },
        { name: "c (light speed)", value: "3 × 10⁸ m/s" },
        { name: "h (Planck)", value: "6.63 × 10⁻³⁴ J·s" },
        { name: "e (electron charge)", value: "1.6 × 10⁻¹⁹ C" },
        { name: "m_e (electron mass)", value: "9.1 × 10⁻³¹ kg" },
        { name: "ε₀ (permittivity)", value: "8.85 × 10⁻¹² C² N⁻¹ m⁻²" },
        { name: "k (Coulomb constant)", value: "9 × 10⁹ N m² C⁻²" },
        { name: "Boltzmann constant (k_B)", value: "1.38 × 10⁻²³ J K⁻¹" },
      ],
      traps: [
        "Deceleration → a is NEGATIVE. Always fix sign convention at start.",
        "Projectile: horizontal v is CONSTANT — gravity acts only vertically.",
        "At max height: v_y = 0 but v_x unchanged — particle still moving.",
        "SHM: a = −ω²x — acceleration is always towards mean position (negative of displacement).",
        "Lenz's Law: induced current OPPOSES change in flux — not flux itself.",
        "In circular motion: centripetal force is not a new force — it's the NET inward force.",
        "Mirror formula sign convention: distances from pole; real object → u is negative.",
        "Transformer works ONLY on AC, not DC.",
        "Escape velocity is independent of mass of the object.",
        "Carnot efficiency is the MAXIMUM — real engines are less efficient.",
      ],
      mnemonics: [
        "SUVAT — S=disp, U=initial, V=final, A=accel, T=time",
        "ROFL — Resistors in parallel: reciprocals add; series: direct sum",
        "Right Hand Rule — thumb=current, fingers curl = magnetic field direction",
        "FLINT — Faraday, Lenz, Induction, N-S poles, Transformer",
      ],
      revision: [
        "Projectile range max at 45° · T = 2u sinθ/g · R = u² sin2θ/g",
        "Series: R_total = ΣR · C_total = 1/ΣC⁻¹ · V same",
        "Parallel: 1/R = Σ1/R · C_total = ΣC · I same per branch",
        "Work done by conservative force = −ΔPE · non-conservative → ΔKE + ΔPE = W_nc",
        "Angular momentum L = Iω = mvr · L is conserved when τ_net = 0",
        "Bohr model: r_n = n²a₀ · E_n = −13.6/n² eV · a₀ = 0.529 Å",
        "Nuclear: mass number = P + N · atomic number = P · isotopes same Z, diff A",
      ],
    },
    Chemistry: {
      formulas: [
        { expr: "n = m/M · N = n × Nₐ", desc: "Mole concept — fundamental" },
        { expr: "PV = nRT · (P+a/V²)(V−b) = nRT", desc: "Ideal gas and Van der Waals" },
        { expr: "ΔG = ΔH − TΔS · ΔG° = −RT ln K", desc: "Gibbs energy and equilibrium" },
        { expr: "Kp = Kc(RT)^Δn", desc: "Relation between Kp and Kc · Δn = Δmoles of gas" },
        { expr: "E = E° − (0.0591/n) log Q", desc: "Nernst equation at 25°C" },
        { expr: "ΔG° = −nFE°cell · E°cell = E°cathode − E°anode", desc: "Cell EMF and Gibbs" },
        { expr: "m = (M/nF)It", desc: "Faraday's law of electrolysis · m=mass, M=molar mass" },
        { expr: "Rate = k[A]^m[B]^n", desc: "Rate law · order from experiment, NEVER from equation" },
        { expr: "t½ = 0.693/k (1st order)", desc: "Half-life · first order is most important in JEE" },
        { expr: "k = Ae^(−Ea/RT)", desc: "Arrhenius equation · ln k vs 1/T gives straight line" },
        { expr: "pH = −log[H⁺] · pOH = −log[OH⁻] · pH + pOH = 14", desc: "Acid-base" },
        { expr: "pH = pKa + log([A⁻]/[HA])", desc: "Henderson-Hasselbalch for buffer" },
        { expr: "ΔTf = Kf × m × i · ΔTb = Kb × m × i", desc: "Depression/elevation colligative properties" },
        { expr: "π = iCRT", desc: "Osmotic pressure · i = van't Hoff factor" },
        { expr: "M₁V₁ = M₂V₂", desc: "Dilution formula · moles conserved" },
      ],
      constants: [
        { name: "Avogadro (Nₐ)", value: "6.022 × 10²³ mol⁻¹" },
        { name: "Faraday (F)", value: "96500 C mol⁻¹" },
        { name: "R (gas)", value: "8.314 J mol⁻¹ K⁻¹ · 0.0821 L·atm mol⁻¹ K⁻¹" },
        { name: "STP", value: "0°C (273 K), 1 atm · 22.4 L per mol" },
        { name: "Kw (water, 25°C)", value: "10⁻¹⁴ mol² L⁻²" },
        { name: "pKw", value: "14 at 25°C" },
      ],
      traps: [
        "Rate order from EXPERIMENT only — never from stoichiometry.",
        "Kp = Kc only when Δn = 0 (equal moles gas on both sides).",
        "Colligative properties depend on NUMBER of solute particles, not identity.",
        "Kf for water = 1.86 K kg mol⁻¹ · Kb for water = 0.52 K kg mol⁻¹.",
        "Arrhenius: higher Ea → more temperature-sensitive rate.",
        "Hybridisation determines shape — sp = linear, sp² = trigonal planar, sp³ = tetrahedral, sp³d = trigonal bipyramidal.",
        "Benzene (aromatic): 6 π electrons, delocalized, Hückel 4n+2 rule (n=1).",
        "SN2 = inversion (Walden), second order · SN1 = racemic, first order.",
        "Markovnikov's rule: H adds to carbon with more H (or less substituted carbon).",
        "Oxidation state of O is usually −2 (except peroxides −1, OF₂ +2).",
      ],
      mnemonics: [
        "OIL RIG — Oxidation Is Loss, Reduction Is Gain",
        "LEO GER — Lose Electrons Oxidation, Gain Electrons Reduction",
        "SHOP — Strong acids/bases: HCl, HBr, HI, H₂SO₄, HNO₃, HClO₄, NaOH, KOH, Ca(OH)₂",
        "ACID = Accepts electrons (Lewis) / Donates H⁺ (Brønsted)",
        "Periodic trends: EN increases → F>O>N>Cl; atomic radius increases ↓ and ←",
      ],
      revision: [
        "Electronegativity: F > O > N > Cl > Br — key for bond polarity",
        "First ionisation energy: decreases down group, increases across period (with exceptions at group 2→3 and 5→6)",
        "d-block: transition metals · f-block: lanthanides (57-71) and actinides (89-103)",
        "Amino acids: have both −NH₂ and −COOH · proteins = polypeptides",
        "Aldol: α-H required · Cannizzaro: no α-H, disproportionation",
        "Grignard reagent (RMgX): strong nucleophile, reacts with carbonyl compounds",
        "Named reactions to know: Aldol, Cannizzaro, Reimer-Tiemann, Williamson ether, Kolbe, Clemmensen, Wolff-Kishner",
      ],
    },
    Mathematics: {
      formulas: [
        { expr: "sin²θ + cos²θ = 1", desc: "Identity 1 · also: 1+tan²θ=sec²θ, 1+cot²θ=cosec²θ" },
        { expr: "sin(A+B) = sinA cosB + cosA sinB", desc: "Compound angle — derive cos(A+B) and tan(A+B)" },
        { expr: "sin 2A = 2 sinA cosA · cos 2A = cos²A−sin²A", desc: "Double angle formulas" },
        { expr: "d/dx(xⁿ)=nxⁿ⁻¹ · d/dx(eˣ)=eˣ · d/dx(ln x)=1/x", desc: "Standard derivatives" },
        { expr: "d/dx(sin x)=cos x · d/dx(cos x)=−sin x · d/dx(tan x)=sec²x", desc: "Trig derivatives" },
        { expr: "∫xⁿ dx = xⁿ⁺¹/(n+1)+C · ∫eˣ dx=eˣ+C · ∫1/x dx=ln|x|+C", desc: "Standard integrals" },
        { expr: "∫₀^a f(x)dx = ∫₀^a f(a−x)dx", desc: "King's property — very frequent in JEE" },
        { expr: "lim(x→0) sinx/x = 1 · lim(x→0)(1+x)^(1/x) = e", desc: "Standard limits" },
        { expr: "x = (−b ± √D)/2a · D = b²−4ac", desc: "Quadratic formula and discriminant" },
        { expr: "nCr = n!/r!(n−r)! · nPr = n!/(n−r)!", desc: "Combinations and permutations" },
        { expr: "|z|² = a²+b² · arg(z) = arctan(b/a)", desc: "Complex number modulus and argument" },
        { expr: "e^(iθ) = cosθ + i sinθ", desc: "Euler's formula — key for complex numbers" },
        { expr: "det(A) = ad−bc (2×2) · A⁻¹ = adj(A)/det(A)", desc: "Matrix determinant and inverse" },
        { expr: "a·b = |a||b|cosθ · a×b = |a||b|sinθ n̂", desc: "Dot product (scalar) and cross product (vector)" },
        { expr: "Σn = n(n+1)/2 · Σn² = n(n+1)(2n+1)/6", desc: "Sum of natural numbers — very frequent" },
        { expr: "P(A|B) = P(A∩B)/P(B) · Bayes: P(A|B) = P(B|A)P(A)/P(B)", desc: "Conditional probability and Bayes" },
        { expr: "Circle: (x−h)²+(y−k)²=r²", desc: "Standard form · centre (h,k), radius r" },
        { expr: "Parabola: y²=4ax · focus(a,0) · directrix x=−a", desc: "Standard parabola" },
        { expr: "Ellipse: x²/a²+y²/b²=1 · c²=a²−b²", desc: "Standard ellipse · eccentricity e=c/a < 1" },
      ],
      constants: [
        { name: "e (Euler)", value: "2.718... · ln(e)=1 · d/dx(eˣ)=eˣ" },
        { name: "π (pi)", value: "3.14159... · sin(π)=0 · cos(π)=−1" },
        { name: "Golden ratio φ", value: "(1+√5)/2 ≈ 1.618" },
      ],
      traps: [
        "ILATE for integration by parts: ∫u dv = uv − ∫v du (choose u in ILATE order).",
        "Definite integral ≠ area when function is negative — take |f(x)| for actual area.",
        "Permutation vs Combination: nPr when ORDER matters; nCr when it doesn't.",
        "Discriminant D=0 → equal roots · D>0 → two real roots · D<0 → no real roots.",
        "log(a+b) ≠ log a + log b. Only log(ab) = log a + log b.",
        "∫₀^2a f(x)dx = 2∫₀^a f(x)dx ONLY IF f(2a−x)=f(x); else 0 if f(2a−x)=−f(x).",
        "Inverse trig: domain of sin⁻¹ is [−1,1], range is [−π/2,π/2].",
        "Matrices: AB ≠ BA in general (non-commutative). Also |AB|=|A||B|.",
      ],
      mnemonics: [
        "ILATE — Inverse trig > Log > Algebraic > Trigonometric > Exponential",
        "SOH CAH TOA — Sin=Opp/Hyp, Cos=Adj/Hyp, Tan=Opp/Adj",
        "CAST rule — All positive Q1, Sin positive Q2, Tan positive Q3, Cos positive Q4",
        "AP sum: S = n/2 × (first + last) = n/2 × (2a + (n−1)d)",
      ],
      revision: [
        "sin(A+B)=sinAcosB+cosAsinB · cos(A+B)=cosAcosB−sinAsinB",
        "sin2A=2sinAcosA · cos2A=1−2sin²A=2cos²A−1 · tan2A=2tanA/(1−tan²A)",
        "Sum of GP: S=a(rⁿ−1)/(r−1) for r≠1 · Infinite GP: S=a/(1−r) for |r|<1",
        "Parabola max/min: vertex of y=ax²+bx+c is at x=−b/2a",
        "Binomial: (a+b)ⁿ = Σ nCr × aⁿ⁻ʳ × bʳ · general term: T_{r+1} = nCr × aⁿ⁻ʳ × bʳ",
        "Probability: P(A∪B)=P(A)+P(B)−P(A∩B) · P(A')=1−P(A)",
        "Vectors: |a×b| = area of parallelogram · a·b=0 → perpendicular",
      ],
    },
  },
  neet_ug: {
    subjects: ["Physics", "Chemistry", "Botany", "Zoology"],
    Physics: {
      formulas: [
        { expr: "v = u + at · s = ut + ½at²", desc: "SUVAT kinematics — same as JEE" },
        { expr: "F = ma · W = mg", desc: "Newton · g = 9.8 m/s² ≈ 10 for NEET" },
        { expr: "P = W/t = Fv", desc: "Power · P in Watts, W in Joules, t in seconds" },
        { expr: "V = IR · P = I²R = V²/R", desc: "Ohm's Law and power in circuits" },
        { expr: "1/f = 1/v + 1/u", desc: "Lens/Mirror formula — learn sign convention carefully" },
        { expr: "λ = h/mv", desc: "de Broglie wavelength — h = 6.63 × 10⁻³⁴ J·s" },
      ],
      constants: [
        { name: "g", value: "9.8 m/s² (use 10 in NEET)" },
        { name: "h (Planck)", value: "6.63 × 10⁻³⁴ J·s" },
        { name: "c", value: "3 × 10⁸ m/s" },
      ],
      traps: [
        "NEET Physics is from Class 11 & 12 NCERT only — focus on NCERT examples and exercises.",
        "Lenz's law: induced current opposes the CHANGE in flux, not the flux itself.",
        "In ray optics: real images are on the same side as the object for mirrors.",
      ],
      mnemonics: ["SUVAT covers all kinematics", "OIL RIG for redox (same in Chemistry)"],
      revision: [
        "Ohm's law: V = IR · Series: same current · Parallel: same voltage",
        "KVL: sum of voltages in a loop = 0 · KCL: sum of currents at a node = 0",
        "Nuclear decay: α loses 4 mass, 2 atomic number · β⁻ gains atomic number by 1",
      ],
    },
    Chemistry: {
      formulas: [
        { expr: "n = m/M · N = n × Nₐ", desc: "Mole concept — most fundamental in chemistry" },
        { expr: "pH = −log[H⁺]", desc: "Strong acid: [H⁺] = molarity · Weak acid: use Ka" },
        { expr: "ΔG = ΔH − TΔS", desc: "Spontaneity · ΔG < 0 → spontaneous at that T" },
        { expr: "Rate = k[A]^m[B]^n", desc: "Rate law — order from experiment, not equation" },
      ],
      constants: [
        { name: "Nₐ", value: "6.022 × 10²³ mol⁻¹" },
        { name: "STP", value: "0°C, 1 atm · molar volume = 22.4 L" },
      ],
      traps: [
        "NEET Chemistry: 85% questions from NCERT text — read every line of NCERT.",
        "Colligative properties depend on NUMBER of particles, not their nature.",
        "Aromatic compounds require: planar, cyclic, 4n+2 π electrons (Hückel's rule).",
      ],
      mnemonics: ["OIL RIG — Oxidation Is Loss, Reduction Is Gain", "LEO GER — Lose Electrons Oxidation, Gain Electrons Reduction"],
      revision: [
        "Electronegativity order: F > O > N > Cl — essential for bond polarity",
        "Hybridisation: sp = linear · sp² = trigonal planar · sp³ = tetrahedral",
        "Benzene: 6π electrons, all bonds equal, planar ring",
        "SN2 = inversion (backside attack) · SN1 = racemic mixture (carbocation)",
      ],
    },
    Botany: {
      formulas: [
        { expr: "6CO₂ + 6H₂O + light → C₆H₁₂O₆ + 6O₂", desc: "Photosynthesis — overall equation · Z-scheme for light reactions" },
        { expr: "3CO₂ + 3RuBP → 6PGA → 1G3P (Calvin cycle)", desc: "Calvin cycle (C3) — 3 turns per G3P · occurs in stroma" },
        { expr: "C4 pathway: CO₂ → OAA → malate → bundle sheath → Calvin", desc: "C4 plants (maize, sugarcane) — less photorespiration" },
        { expr: "Transpiration pull — water column cohesion-tension theory", desc: "Ascent of water: transpiration pull > root pressure" },
        { expr: "Hardy-Weinberg: p² + 2pq + q² = 1 · p + q = 1", desc: "Genetic equilibrium — 5 conditions required" },
      ],
      constants: [
        { name: "Cells discovered by", value: "Robert Hooke (1665) — cork cells under microscope" },
        { name: "Cell theory", value: "Schleiden & Schwann (1838-39) · Virchow added omnis cellula e cellula" },
        { name: "Photosynthesis site", value: "Light reactions: thylakoid membrane · Calvin: stroma" },
        { name: "C3 vs C4 first product", value: "C3 = 3-phosphoglycerate · C4 = oxaloacetate (OAA)" },
        { name: "DNA replication", value: "S phase of cell cycle · semi-conservative (Meselson-Stahl)" },
      ],
      traps: [
        "Glycolysis: cytoplasm, not mitochondria — produces 2 ATP (net), 2 NADH, 2 pyruvate.",
        "Krebs cycle: mitochondrial matrix · ETC: inner mitochondrial membrane.",
        "C4 plants fix CO₂ into OAA in MESOPHYLL first, then Calvin in BUNDLE SHEATH.",
        "Transpiration is water loss · Guttation is water drops from hydathodes (cool nights).",
        "Gymnosperms have naked seeds · Angiosperms have seeds in fruit.",
        "Mitosis: 2 identical diploid cells · Meiosis: 4 genetically different haploid cells.",
        "Apical meristem = primary growth (length) · Lateral meristem = secondary growth (girth).",
        "Xylem: unidirectional, dead cells · Phloem: bidirectional, living cells.",
      ],
      mnemonics: [
        "PMAT — Prophase, Metaphase, Anaphase, Telophase (cell division stages)",
        "KPCOFGS — King Philip Came Over For Good Soup (Kingdom, Phylum, Class, Order, Family, Genus, Species)",
        "ATP synthase: F0-F1 complex — F1 is the catalytic part (CF1 in chloroplasts)",
        "ETC order: NADH → Complex I → CoQ → Complex III → Cyt c → Complex IV → O₂",
      ],
      revision: [
        "Photosystems: PS-II absorbs 680nm · PS-I absorbs 700nm · Z-scheme connects them",
        "Meristematic tissue: actively dividing · Permanent tissue: differentiated (no more division)",
        "Xylem: tracheids + vessels + fibers + parenchyma · conducts water and minerals",
        "Phloem: sieve tubes + companion cells + fibers + parenchyma · conducts sugars (source to sink)",
        "Mendelian ratios: 3:1 (monohybrid) · 9:3:3:1 (dihybrid) · 1:2:1 (incomplete dominance F2)",
        "DNA: anti-parallel double helix · A-T (2 H-bonds) · G-C (3 H-bonds) · 3.4 nm per turn",
        "High-weight chapters: Photosynthesis · Respiration · Plant Growth · Genetics · Ecology",
      ],
    },
    Zoology: {
      formulas: [
        { expr: "C₆H₁₂O₆ + 6O₂ → 6CO₂ + 6H₂O + 38 ATP", desc: "Aerobic respiration · net ATP: glycolysis=2 + Krebs=2 + ETC=34" },
        { expr: "Cardiac output = Heart rate × Stroke volume", desc: "Normal CO = 72 × 70 = ~5L/min" },
        { expr: "GFR = ~125 mL/min in healthy kidneys", desc: "Ultrafiltration in Bowman's capsule" },
        { expr: "Hardy-Weinberg: p² + 2pq + q² = 1", desc: "Population genetics — violation = evolution" },
        { expr: "BMI = weight(kg) / height(m)²", desc: "Body Mass Index — not in NEET but useful" },
      ],
      constants: [
        { name: "Normal blood glucose", value: "70–110 mg/dL (fasting) · insulin lowers, glucagon raises" },
        { name: "RBC lifespan", value: "120 days · made in red bone marrow · destroyed in spleen" },
        { name: "Normal BP", value: "120/80 mmHg (systolic/diastolic)" },
        { name: "ATP yield (aerobic)", value: "1 glucose = ~36-38 ATP (38 theoretical)" },
        { name: "DNA structure", value: "Double helix · Watson & Crick 1953 · B-form most common" },
      ],
      traps: [
        "Krebs cycle occurs in MITOCHONDRIAL MATRIX, not cytoplasm.",
        "ETC (oxidative phosphorylation) occurs on INNER mitochondrial MEMBRANE.",
        "Insulin: lowers blood glucose (beta cells) · Glucagon: raises blood glucose (alpha cells).",
        "Nephron: glomerulus → Bowman's capsule → PCT → Loop of Henle → DCT → collecting duct.",
        "ADH (vasopressin): increases water reabsorption · Aldosterone: increases Na⁺ reabsorption.",
        "Antibody structure: 2 heavy + 2 light chains · Y-shaped · produced by B lymphocytes.",
        "Innate immunity: non-specific, fast · Adaptive immunity: specific, slower, has memory.",
        "DNA is antiparallel: one strand 5'→3', the complementary strand 3'→5'.",
      ],
      mnemonics: [
        "PMAT — Prophase, Metaphase, Anaphase, Telophase (cell division)",
        "AT·GC — A pairs T (2 bonds), G pairs C (3 bonds) in DNA",
        "ETC order: NADH → CI → CoQ → CIII → Cyt c → CIV → O₂ (NADH→I→Q→III→c→IV→O₂)",
        "Blood cells: RBC (erythrocyte) · WBC (leukocyte) · Platelets (thrombocyte)",
      ],
      revision: [
        "Krebs cycle: 1 acetyl-CoA → 3 NADH + 1 FADH₂ + 1 GTP + 2 CO₂ per turn",
        "Digestion enzymes: amylase (starch) · pepsin (protein) · lipase (fats) · trypsin (protein)",
        "Blood groups: AB = universal recipient (no antibodies) · O = universal donor (both antibodies)",
        "Endocrine glands: pituitary (master) · thyroid (T3/T4) · adrenal (adrenaline/cortisol) · pancreas (insulin/glucagon)",
        "Muscle types: striated/voluntary (skeletal) · smooth/involuntary · cardiac (striated, involuntary)",
        "High-weight chapters: Human Physiology · Genetics · Biotechnology · Ecology · Evolution",
        "Mendelian laws: Segregation (monohybrid 3:1) · Independent Assortment (dihybrid 9:3:3:1)",
      ],
    },
  },
  cuet_ug: {
    subjects: ["English", "General Test"],
    English: {
      formulas: [
        { expr: "Active → Passive: Object + be(tense) + V3 + by + Subject", desc: "Voice change rule" },
        { expr: "Direct → Indirect: change pronouns + tense (backshift) + remove quotes", desc: "Reported speech" },
        { expr: "Conditional Type 1: If + present simple, will + base verb", desc: "Real/possible future condition" },
        { expr: "Conditional Type 2: If + past simple, would + base verb", desc: "Unreal/hypothetical present" },
      ],
      constants: [
        { name: "Articles", value: "a (before consonant sounds) · an (before vowel sounds) · the (specific/unique)" },
        { name: "Prepositions of time", value: "at (clock time) · on (days/dates) · in (months/years/periods)" },
        { name: "Degrees of comparison", value: "Positive / Comparative (-er/more) / Superlative (-est/most)" },
      ],
      traps: [
        "Its (possessive) vs It's (it is) — extremely common CUET trap.",
        "Effect (noun) vs Affect (verb) — 'The effect was great' vs 'It affected me'.",
        "'Less' for uncountable nouns · 'Fewer' for countable nouns.",
        "Lie (to recline, intransitive) vs Lay (to place, transitive) — lay needs an object.",
      ],
      mnemonics: [
        "FANBOYS — For, And, Nor, But, Or, Yet, So (coordinating conjunctions)",
        "BEING — Be, Been, Being, Is, Are, Am, Was, Were (auxiliary verbs of 'be')",
      ],
      revision: [
        "Reading comprehension: skim for main idea → scan for specific answers",
        "Vocabulary: learn word roots — struct (build), port (carry), aud (hear), vis (see)",
        "Sentence correction: check subject-verb agreement first, then tense, then pronoun",
        "Spotting errors: read each part separately, identify grammatical category of error",
      ],
    },
    "General Test": {
      formulas: [
        { expr: "Simple Interest = PRT/100", desc: "P=principal, R=rate%, T=time(years)" },
        { expr: "Compound Interest = P(1 + R/100)ᵀ − P", desc: "Grows faster than SI — common in CUET QA" },
        { expr: "Profit% = (Profit/CP) × 100", desc: "Always % on Cost Price unless specified" },
        { expr: "Speed = Distance/Time", desc: "Average speed = total distance / total time (not average of speeds)" },
        { expr: "Work done in 1 day = 1/n (if n days to complete)", desc: "Combined rate: 1/A + 1/B = 1/T" },
        { expr: "Probability = Favourable outcomes / Total outcomes", desc: "P(A or B) = P(A) + P(B) − P(A and B)" },
      ],
      constants: [
        { name: "Divisibility by 3", value: "Sum of digits divisible by 3" },
        { name: "Divisibility by 9", value: "Sum of digits divisible by 9" },
        { name: "Square roots to memorise", value: "√2=1.414 · √3=1.732 · √5=2.236" },
      ],
      traps: [
        "Average speed ≠ (speed1 + speed2) / 2. Use: 2s1s2 / (s1+s2) for equal distances.",
        "Compound interest: if compounded half-yearly, halve rate and double time.",
        "Seating arrangements: circular = (n-1)! · Linear = n!",
        "Percentage change = (New − Old)/Old × 100",
      ],
      mnemonics: [
        "BODMAS — Brackets, Of, Division, Multiplication, Addition, Subtraction (operation order)",
        "DMAS for quick calculation: Division → Multiplication → Addition → Subtraction",
      ],
      revision: [
        "LCM × HCF = Product of two numbers (only for two numbers)",
        "Sum of first n natural numbers = n(n+1)/2",
        "For partnership: profit ratio = capital × time ratio",
        "Distance = Speed × Time · Time = Distance / Speed · Speed = Distance / Time",
        "If A can do work in x days and B in y days: together = xy/(x+y) days",
      ],
    },
  },
  sat: {
    subjects: ["Reading & Writing", "Mathematics"],
    "Reading & Writing": {
      formulas: [
        { expr: "Active → Passive: Object + be(tense) + V3 + by + Subject", desc: "Voice conversion — very frequent in SAT grammar" },
        { expr: "Subject + Verb + Object (SVO) — base sentence structure", desc: "Check subject-verb agreement before all else" },
        { expr: "Parallel structure: A, B, and C must match grammatical form", desc: "Lists must be grammatically parallel" },
        { expr: "Modifier must be adjacent to what it modifies", desc: "Misplaced modifier trap in SAT sentence completion" },
      ],
      constants: [
        { name: "No negative marking", value: "Every question answered = no penalty. Always answer all 54 R&W questions." },
        { name: "Section structure", value: "2 modules × 27 questions each · Module 2 adapts based on Module 1" },
        { name: "Adaptive scoring", value: "High M1 score → harder M2 → higher score ceiling (~700–800)" },
        { name: "Time per question", value: "~71 seconds per R&W question · skim first, then scan for answer" },
      ],
      traps: [
        "Vocabulary in context: choose the word that fits the PASSAGE meaning, not just the most common definition.",
        "True/False questions: 'Not Given' ≠ 'False' — if the passage doesn't say it, it's Not Given.",
        "Transition words: but/however = contrast · therefore/thus = result · for example = illustration.",
        "Apostrophe traps: its (possessive) vs it's (it is) · their vs they're vs there.",
        "Pronoun agreement: singular subject → singular pronoun. 'Everyone' → 'their' is now widely accepted on SAT.",
        "Verb tense consistency: once you set the tense, don't switch without reason.",
      ],
      mnemonics: [
        "FANBOYS — For, And, Nor, But, Or, Yet, So (coordinating conjunctions that join independent clauses)",
        "ACES — Answer, Citation, Explanation, So what? (SAT evidence-based reading response structure)",
        "MICE — Main idea, Inference, Context vocabulary, Evidence (4 core R&W question types)",
      ],
      revision: [
        "Skim passage for main idea → answer big-picture questions without re-reading",
        "Scan for specific details → go back to passage for evidence questions",
        "Eliminate 2 wrong answers first, then choose between remaining 2",
        "SAT Reading rewards inference — the correct answer is implied, not always stated",
        "Grammar priority order: 1) Subject-verb agreement 2) Pronoun case 3) Modifier placement 4) Parallel structure",
        "Rhetorical synthesis: identify the student's claim → find evidence that best supports it",
      ],
    },
    Mathematics: {
      formulas: [
        { expr: "Linear: y = mx + b · slope = (y₂−y₁)/(x₂−x₁)", desc: "Algebra — ~35% of Maths section" },
        { expr: "Systems: { ax+by=c, dx+ey=f } — substitution or elimination", desc: "Linear systems — very frequent" },
        { expr: "Quadratic: x = (−b ± √(b²−4ac)) / 2a · vertex: (−b/2a, f(−b/2a))", desc: "Advanced Math — ~35%" },
        { expr: "Exponential: f(x) = a·b^x · growth if b>1, decay if 0<b<1", desc: "Exponential functions — common in word problems" },
        { expr: "Mean = Σx/n · Median = middle value · Standard deviation ≈ spread", desc: "Statistics — Data Analysis ~15%" },
        { expr: "Probability = favourable/total · P(A and B) = P(A)×P(B) if independent", desc: "Probability — Data Analysis" },
        { expr: "Area circle = πr² · Circumference = 2πr · Arc = (θ/360)×2πr", desc: "Geometry — ~15% of Maths section" },
        { expr: "sin θ = opp/hyp · cos θ = adj/hyp · tan θ = opp/adj", desc: "Trigonometry — right triangle ratios" },
        { expr: "Pythagorean theorem: a² + b² = c²", desc: "Geometry — very frequent" },
        { expr: "Distance = √((x₂−x₁)² + (y₂−y₁)²) · Midpoint = ((x₁+x₂)/2, (y₁+y₂)/2)", desc: "Coordinate geometry" },
      ],
      constants: [
        { name: "No negative marking", value: "Answer every question — a wrong answer costs nothing on Digital SAT" },
        { name: "Calculator allowed", value: "Desmos graphing calculator built-in throughout the Math section" },
        { name: "Section structure", value: "2 modules × 22 questions each · Module 2 adapts based on Module 1" },
        { name: "Question types", value: "~75% Multiple Choice · ~25% Student-Produced Response (grid-in)" },
        { name: "SAT Math focus", value: "Algebra + Advanced Math = 70% of score. Master these first." },
      ],
      traps: [
        "Word problems: identify what the question is ACTUALLY asking before calculating.",
        "Exponent trap: x² = 9 → x = ±3 (not just +3).",
        "Percent trap: 'X% more than Y' = Y × (1 + X/100), not Y + X.",
        "Function notation: f(g(x)) ≠ f(x) × g(x). Evaluate from inside out.",
        "Absolute value: |x − 3| = 5 gives TWO solutions: x = 8 and x = −2.",
        "Average trap: if average of n numbers is A, the SUM is n×A.",
        "System of equations: if no solution → parallel lines (same slope, diff intercept). If infinite → same line.",
      ],
      mnemonics: [
        "SOHCAHTOA — Sin=Opp/Hyp, Cos=Adj/Hyp, Tan=Opp/Adj",
        "FOIL — First, Outer, Inner, Last (for multiplying two binomials)",
        "PEMDAS — Parentheses, Exponents, Multiplication/Division, Addition/Subtraction",
        "Vertex form: f(x) = a(x−h)² + k → vertex at (h, k); a>0 opens up, a<0 opens down",
      ],
      revision: [
        "Use Desmos for any graph question — plug in values to verify",
        "Check units in word problems — rates, percentages, and ratios have units",
        "Grid-in answers: if your answer is a fraction, leave it as a fraction (not decimal) unless it repeats",
        "Algebra tip: if stuck, plug in a simple number (like x=2) to check which answer works",
        "Data analysis: always read axes labels and units on charts before answering",
        "Geometry: if a diagram looks like a specific shape, the SAT usually tells you — don't assume",
      ],
    },
  },
  ielts: {
    subjects: ["Listening", "Reading", "Vocabulary & Grammar"],
    Listening: {
      formulas: [
        { expr: "Gap-fill: answer = exact word(s) from recording (max 2–3 words or a number)", desc: "Follow word limit strictly — 'cat and dog' → wrong if limit is 2 words" },
        { expr: "MCQ: read options BEFORE audio plays · predict word category", desc: "Pre-reading maximises comprehension speed" },
        { expr: "Matching: read all options first → cross off matched ones during audio", desc: "Systematic elimination technique" },
        { expr: "Note-completion: predict WORD TYPE (noun/verb/number) before audio", desc: "Predicting type narrows candidates to 1–2 words" },
      ],
      constants: [
        { name: "Duration", value: "30 min + 10 min transfer time (Paper-based only)" },
        { name: "Questions", value: "40 questions across 4 recordings" },
        { name: "Band scoring", value: "40 correct = Band 9 · 35 = Band 8 · 30 = Band 7 · 23 = Band 6" },
        { name: "Word limit", value: "Gap-fill: 'NO MORE THAN X WORDS' — exceeding → wrong even if answer is correct" },
        { name: "Spellings", value: "British English spellings accepted (colour/color) — but must be correct spelling" },
      ],
      traps: [
        "Distractors: speaker often says the wrong answer first, then corrects it. Wait for the final answer.",
        "Word limit: 'one word and/or a number' — writing 2 words = wrong.",
        "Spelling: all gap-fill answers must be spelled correctly. Misspelt = wrong.",
        "Negatives: 'the lecture is NOT on Tuesday' — students write 'Tuesday' because they heard it.",
        "Plurals: 'students' ≠ 'student' — the recording may say either, check if the gap needs plural.",
        "Predictions: if you predicted 'Paris' but the audio says 'France', write 'France' — follow the audio.",
      ],
      mnemonics: [
        "CUPS — Copy, Underline (key words), Predict word type, Scan (next question while listening)",
        "PAWN — Predict, Attend, Write (exact words), Note (next question during pause)",
        "4 recordings: Social/everyday → Social/training → Monologue/general → Academic lecture",
      ],
      revision: [
        "Practice with authentic BBC Radio, TED Talks, and ETS TOEFL lecture samples",
        "Train yourself to listen for signposting phrases: 'However', 'In contrast', 'The main reason is'",
        "Map/diagram tasks: identify compass directions and room names before audio",
        "Form completion: read ALL fields before audio — the recording follows the form order",
        "Section 4 (academic lecture) has NO pause — full concentration required",
        "Speed tip: you hear each section ONCE only — no replay. Note-taking is essential.",
      ],
    },
    Reading: {
      formulas: [
        { expr: "True/False/Not Given: True = passage confirms it · False = passage contradicts it · NG = not mentioned", desc: "Most important distinction — NG ≠ False" },
        { expr: "Matching Headings: read heading list → skim each paragraph for main idea → match", desc: "Never match a heading from a detail — headings = main idea" },
        { expr: "Sentence completion: word must fit grammatically AND factually from passage", desc: "Two conditions both required" },
        { expr: "Scanning speed formula: title → intro/conclusion → topic sentences → details (only if needed)", desc: "Skimming sequence for academic IELTS passages" },
      ],
      constants: [
        { name: "Duration", value: "60 min — no extra transfer time (unlike Listening)" },
        { name: "Structure", value: "3 passages, increasing difficulty · 40 questions total · 13–14 per passage" },
        { name: "Band scoring", value: "40 correct = Band 9 · 35 = Band 8 · 30 = Band 7 · 23 = Band 6" },
        { name: "Question order", value: "Answers generally follow passage order — use this to locate quickly" },
        { name: "Passage themes", value: "Academic topics: science, history, social science, environment, technology" },
      ],
      traps: [
        "True/False/Not Given: 'The study found' + your knowledge = you may write True when it's NG because you know the fact is true in real life.",
        "Yes/No/Not Given: Yes/No tests OPINIONS, not facts. Same NG logic applies.",
        "Matching headings: subheadings, examples, and data ≠ main idea. Don't match on these.",
        "Paragraph letters: sections may be labelled A, B, C, not paragraphs — watch for this.",
        "Paraphrase: the correct answer uses different words than the passage. If exact same words → likely a trap.",
        "Time management: if stuck on a question after 2 minutes, mark it and move on.",
      ],
      mnemonics: [
        "TFNG — True: Text Firmly Nods (passage agrees) · False: Text Firmly Negates · NG: Text Never Goes there",
        "SQR3 — Survey, Question, Read, Recall, Review (academic reading strategy)",
        "SKIM → SCAN → SOLVE: first pass for main idea, second pass for specific answer, third to check",
      ],
      revision: [
        "Daily reading: The Economist, BBC News Science, National Geographic — 1 article/day",
        "True/False/Not Given: underline the key claim → find in passage → compare carefully",
        "Matching headings: cover all options → summarise each paragraph in 3 words → match",
        "Time allocation: ~18-20 min per passage · if a question takes >2 min, skip and return",
        "Difficult vocabulary: use context clues — prefix/suffix/sentence structure to infer meaning",
        "Academic word list (AWL): learn top 200 academic words — they appear in every IELTS passage",
      ],
    },
    "Vocabulary & Grammar": {
      formulas: [
        { expr: "Collocation: make a decision (not 'do a decision') · do homework (not 'make homework')", desc: "Verb-noun collocations are tested in writing and speaking" },
        { expr: "Cohesive devices: addition (furthermore) · contrast (however) · result (therefore) · example (for instance)", desc: "Essential for Writing Task 2 coherence score" },
        { expr: "Complex sentence: [Main clause] + [subordinating conjunction] + [subordinate clause]", desc: "Required for Band 7+ grammar in Writing" },
        { expr: "Passive voice: be + past participle — used to de-emphasise actor or when actor unknown", desc: "Academic style often uses passive" },
      ],
      constants: [
        { name: "Lexical resource", value: "IELTS Writing/Speaking bands reward varied vocabulary and collocations" },
        { name: "Accuracy vs range", value: "Band 6: some errors but understandable · Band 7: few errors · Band 8: natural, flexible" },
        { name: "Academic word list", value: "570 word families cover ~10% of academic text. Learn these for band 7+." },
        { name: "Spelling", value: "Must be correct in Writing. American OR British English accepted — but be consistent." },
      ],
      traps: [
        "Confusables: affect (verb) vs effect (noun) · principal (main) vs principle (rule) · complement vs compliment.",
        "Over-formal vs under-formal: choose vocabulary appropriate to the context (academic vs casual).",
        "Collocation errors: 'make a mistake' not 'do a mistake' · 'strong tea' not 'powerful tea'.",
        "Preposition errors: 'interested IN' not 'interested ON' · 'depend ON' not 'depend OF'.",
        "Tense trap: present perfect ('has increased') vs simple past ('increased') — wrong tense loses marks.",
      ],
      mnemonics: [
        "CALF — Cohesion, Accuracy, Lexis (vocab), Fluency (the 4 IELTS writing/speaking criteria)",
        "AWL (Academic Word List): analyse, approach, concept, constitute, context, data, define, significant, structure, theory",
        "Discourse markers: Addition=Furthermore · Contrast=Nevertheless · Result=Consequently · Example=To illustrate",
      ],
      revision: [
        "Topic vocabulary sets: environment, education, health, technology, crime — learn 15 words per theme",
        "Paraphrase practice: take any IELTS task question → rewrite it 3 ways using synonyms",
        "Sentence types: simple (1 clause) · compound (2 independent) · complex (main + subordinate)",
        "Writing Task 2: PEEL — Point, Evidence, Explain, Link back to question",
        "Commonly misspelled: necessary (1 c, 2 s) · occurrence (2 c, 2 r) · accommodation (2 c, 2 m)",
        "Band 7 vocabulary checklist: varied vocabulary, some idiomatic language, few spelling errors",
      ],
    },
  },
  toefl_ibt: {
    subjects: ["Reading", "Listening", "Integrated Skills"],
    Reading: {
      formulas: [
        { expr: "Passage structure: Introduction → Body paragraphs → Conclusion (academic article format)", desc: "Expect TOEFL passages to follow this pattern — helps predict content" },
        { expr: "Factual detail: scan for the specific fact asked → verify against surrounding context", desc: "Most common question type (~30% of Reading)" },
        { expr: "Vocabulary in context: substitute each option → select the best fit for that context", desc: "Look at how the word is used, not just dictionary meaning" },
        { expr: "Insert sentence: read before and after target position → check pronoun and logical flow", desc: "The sentence must logically and grammatically follow what precedes it" },
      ],
      constants: [
        { name: "Duration", value: "35 min · 2 passages · 10 questions each" },
        { name: "Scoring", value: "0–30 per section · scaled score" },
        { name: "Passage length", value: "~700 words each · academic texts from university courses" },
        { name: "No negative marking", value: "Always answer — leave no blanks" },
        { name: "Categories", value: "Factual (~30%), Inference (~20%), Vocabulary (~20%), Summary/purpose (~30%)" },
      ],
      traps: [
        "Prose summary: choose 3 of 6 statements — wrong choices are either details (not main ideas) or not in passage.",
        "Inference questions: the answer must be STRONGLY implied by the passage — not just plausible.",
        "Vocabulary: the correct answer replaces the word in the SENTENCE context, not just as a synonym.",
        "Negative factual: 'According to the passage, which is NOT mentioned?' — these are easy to rush and get wrong.",
        "Rhetorical purpose: 'Why does the author mention X?' — look for the function in the paragraph, not just what X is.",
        "Sentence insertion: watch for demonstrative pronouns (this, these, such) — they must refer to something in the preceding sentence.",
      ],
      mnemonics: [
        "FLIP — Factual, Logic/inference, Idea (main), Purpose (rhetorical) — the 4 TOEFL Reading question families",
        "3Rs — Skim for the Road (structure) → Read for the River (flow) → Return for the Rocks (detail questions)",
      ],
      revision: [
        "Daily reading: Scientific American, Nature News, The Atlantic — academic English with complex structure",
        "Prose summary tip: eliminate choices that are true but too specific (supporting detail not main idea)",
        "Vocabulary strategy: substitute each option into the sentence and read it aloud — choose the most natural",
        "Time management: spend ~3 min per question max · flag and return if stuck",
        "Practice with ETS Official TOEFL Prep — the authentic source matches actual test style closely",
      ],
    },
    Listening: {
      formulas: [
        { expr: "Lecture structure: topic → background → main argument → supporting evidence → conclusion", desc: "Predict the flow to stay oriented during listening" },
        { expr: "Conversation structure: problem/situation → discussion → solution/decision", desc: "Campus service conversations follow this pattern" },
        { expr: "Note-taking: abbreviate key terms → use arrows (→) for cause/effect · use = for definition", desc: "Efficient shorthand is critical — you cannot replay audio" },
        { expr: "Purpose questions: 'Why does the student visit...?' → answer = the problem/goal stated explicitly", desc: "Listen for the reason stated in the OPENING of the conversation" },
      ],
      constants: [
        { name: "Duration", value: "36 min · 3 lectures (6 Qs each) + 2 conversations (5 Qs each)" },
        { name: "Scoring", value: "0–30 · scaled score" },
        { name: "Lecture length", value: "~3–5 min each · complex academic topics" },
        { name: "Conversation length", value: "~2–3 min · campus/office settings" },
        { name: "No replay", value: "Each audio plays ONCE — note-taking is essential" },
      ],
      traps: [
        "Connecting content: 'What is the relationship between X and Y?' — must understand the LOGICAL link, not just the facts.",
        "Stance and attitude: 'What is the professor's attitude toward...?' — listen for hedging language (perhaps, might, tends to).",
        "Function questions: 'Why does the professor say X?' — focus on the discourse function (example, contrast, correction), not the content.",
        "Gist purpose: 'What is the main purpose of this lecture?' — choose the most GENERAL accurate description.",
        "Details: pay attention when professor says 'importantly', 'note that', 'this is key' — these signal testable details.",
        "Distractors: conversations often present a problem and then RESOLVE it — don't answer based on the initial problem.",
      ],
      mnemonics: [
        "NOTE — Note key terms, Organize logically, Track transitions, Extract main idea each paragraph",
        "LAPS — Listen for Label (topic), Attitude, Purpose, Support (evidence) in every lecture",
        "Signal phrases to write down: 'In contrast', 'As a result', 'The main point is', 'To summarize'",
      ],
      revision: [
        "Practice with TED-Ed, Coursera lectures, and PBS Learning Media — academic English in real contexts",
        "Note-taking drill: listen to any 3-min audio → summarize in 5 bullets → compare to transcript",
        "Transition signals: addition (also/furthermore), contrast (however/on the other hand), causation (therefore/as a result)",
        "Predict question types: after each lecture note, ask yourself — main idea? detail? professor's opinion? example purpose?",
        "Upgrade from general English to ACADEMIC English: Lexico Academic Word List is the top resource",
      ],
    },
    "Integrated Skills": {
      formulas: [
        { expr: "Integrated Writing: Read (3 min) → Listen (2 min) → Write (20 min, 150–225 words)", desc: "Structure: intro + 3 body paragraphs (one per lecture point vs reading)" },
        { expr: "Academic Discussion Writing: Read prompt + 2 classmates' posts → Respond (10 min, 100+ words)", desc: "Add NEW information or a well-reasoned opinion — don't just agree" },
        { expr: "Integrated template: 'The reading claims X. However, the lecture argues Y by stating Z.'", desc: "This structure guarantees coverage of both sources" },
      ],
      constants: [
        { name: "Integrated Writing", value: "Read (3 min) + Listen → Write 150–225 words in 20 min" },
        { name: "Academic Discussion", value: "Read prompt → Write 100+ words in 10 min" },
        { name: "Total Writing time", value: "29 min · scored 0–30" },
        { name: "Scoring criteria", value: "Development (accuracy of lecture points) + Language use (grammar/vocabulary)" },
        { name: "Integrated task goal", value: "Summarise how the LECTURE challenges/supports the READING — do NOT give your opinion" },
      ],
      traps: [
        "Integrated Writing: students often summarise the READING instead of explaining how the LECTURE addresses it. Focus on the lecture.",
        "Do NOT include your own opinion in Integrated Writing — only report what the reading and lecture say.",
        "Academic Discussion: generic statements score low. Add a specific reason, example, or counter-argument.",
        "Word count: aim for 200–230 words for Integrated, 120–150 words for Academic Discussion.",
        "Vocabulary: 'the passage mentions' / 'the lecture states' / 'the professor argues' — use varied attribution verbs.",
      ],
      mnemonics: [
        "IDEAL for Integrated Writing: Introduce (the topic) → Describe (reading claim) → Explain (lecture challenge) → Amplify (with details) → Link (conclusion)",
        "3C for Academic Discussion: Claim (your view) → Concrete example → Connect (to classmate or question)",
      ],
      revision: [
        "Integrated Writing practice: read any Wikipedia article for 3 min → listen to a related podcast → write 200 words comparing them",
        "Academic Discussion: practice responding to opinion prompts in 10 min with a specific example from current events or your studies",
        "Connectors to use: 'The lecture contradicts the reading by...' / 'This challenges the reading's claim that...' / 'In contrast to the reading...'",
        "Proofread in last 2 min: check for subject-verb agreement, article use (a/an/the), and run-on sentences",
        "ETS official scoring rubric: 5 = complete, accurate, coherent · 4 = minor omissions or language errors · 3 = key point missing or significant errors",
      ],
    },
  },
};

// ── Resource Links ─────────────────────────────────────────────────────────────
const RESOURCES = [
  { icon: "📖", label: "NCERT Chapters", desc: "Grade 11 & 12 textbooks", color: "#6366f1", onClick: null },
  { icon: "📐", label: "Formula Sheets", desc: "Chapter-wise formulas", color: "#10b981", onClick: "formulaSheet" },
  { icon: "🧪", label: "Topic Tests", desc: "Quick 10-question tests", color: "#f59e0b", onClick: null },
  { icon: "🤖", label: "Ask AI Tutor", desc: "Instant doubt solving", color: "#8b5cf6", onClick: "doubt" },
  { icon: "📝", label: "Mock Tests", desc: "CBSE-style full tests", color: "#06b6d4", onClick: "mockTest" },
  { icon: "📅", label: "Study Planner", desc: "AI-driven revision plan", color: "#ec4899", onClick: null },
];

// ── Main Page ──────────────────────────────────────────────────────────────────

export default function ExamPrepPage({ user, setActivePage }) {
  const [selectedExam, setSelectedExam] = useState("jee_main");
  const [dashboard, setDashboard] = useState(null);
  const [subjects, setSubjects] = useState([]);
  const [selectedSubject, setSelectedSubject] = useState(null);
  const [topics, setTopics] = useState([]);
  const [questions, setQuestions] = useState([]);
  const [selectedQuestion, setSelectedQuestion] = useState(null);
  const [selectedOptions, setSelectedOptions] = useState({});
  const [feedbacks, setFeedbacks] = useState({});
  const [loadingQuestions, setLoadingQuestions] = useState(false);
  const [loadingTopics, setLoadingTopics] = useState(false);
  const [loadingDash, setLoadingDash] = useState(true);
  const [activeMode, setActiveMode] = useState("learn"); // learn | practice | test | reference | result
  const [refSubject, setRefSubject] = useState(""); // selected subject in Quick Reference tab
  const [testSession, setTestSession] = useState(null);
  const [testAnswers, setTestAnswers] = useState({});
  const [testResult, setTestResult] = useState(null);
  const [testLoading, setTestLoading] = useState(false);
  const [filterTopic, setFilterTopic] = useState(null);
  const testStartRef = useRef(null);
  const [testStartTimestamp, setTestStartTimestamp] = useState(0);
  // CUET: stores the subjects the student selected in CUETTestSetup
  const [cuetSelectedSubjects, setCuetSelectedSubjects] = useState([]);

  // Sim test history for Cutoff Oracle
  const [simHistory, setSimHistory] = useState([]);
  const [simHistoryLoading, setSimHistoryLoading] = useState(false);

  const isTestUser = TEST_ACCESS_USERS.has(user?.username);
  const isAdmin = user?.role === "admin";

  // ── Canonical access check from backend ────────────────────────────────────
  const [accessCheck, setAccessCheck] = useState(null);  // null = loading
  useEffect(() => {
    if (!user?.accessToken) return;
    fetch(`${API_BASE}/api/exam-prep/access-check`, {
      headers: { Authorization: `Bearer ${user.accessToken}` },
    })
      .then(r => r.json())
      .then(d => setAccessCheck(d))
      .catch(() => setAccessCheck({ grade_eligible: false, has_access: false, preview_only: true, reason: "error" }));
  }, [user?.accessToken]);

  // ── Fetch sim history when oracle tab is active ────────────────────────────
  useEffect(() => {
    if (activeMode !== "oracle" || !user?.accessToken || !accessCheck?.has_access) return;
    setSimHistoryLoading(true);
    getSimTestHistory(user.accessToken, selectedExam, 10)
      .then(d => setSimHistory(d.history || []))
      .catch(() => setSimHistory([]))
      .finally(() => setSimHistoryLoading(false));
  }, [activeMode, selectedExam, user?.accessToken, accessCheck?.has_access]);

  // ── Load dashboard ─────────────────────────────────────────────────────────
  useEffect(() => {
    if (!user?.accessToken) return;
    setLoadingDash(true);
    getExamPrepDashboard(user.accessToken, selectedExam)
      .then(data => setDashboard(data))
      .catch(() => setDashboard(null))
      .finally(() => setLoadingDash(false));

    getExamPrepSubjects(user.accessToken, selectedExam)
      .then(data => setSubjects(data.subjects || []))
      .catch(() => setSubjects([]));
  }, [selectedExam, user?.accessToken]);

  // ── Select subject ─────────────────────────────────────────────────────────
  async function handleSelectSubject(subjectName) {
    if (selectedSubject === subjectName) { setSelectedSubject(null); setTopics([]); setQuestions([]); setFilterTopic(null); return; }
    setSelectedSubject(subjectName);
    setFilterTopic(null);
    setLoadingTopics(true);
    try {
      const data = await getExamPrepTopics(user.accessToken, selectedExam, subjectName);
      setTopics(data.topics || []);
    } catch { setTopics([]); }
    finally { setLoadingTopics(false); }
    loadQuestions(subjectName, null);
  }

  // ── Load questions ─────────────────────────────────────────────────────────
  async function loadQuestions(subject, topic) {
    setLoadingQuestions(true);
    setSelectedQuestion(null);
    try {
      const data = await getExamPrepQuestions(user.accessToken, { exam: selectedExam, subject, topic, limit: 20 });
      setQuestions(data.questions || []);
    } catch { setQuestions([]); }
    finally { setLoadingQuestions(false); }
  }

  // ── Practice a topic ───────────────────────────────────────────────────────
  function handlePracticeTopic(topic) {
    setFilterTopic(topic.name);
    loadQuestions(selectedSubject, topic.name);
  }

  // ── Answer selection ───────────────────────────────────────────────────────
  async function handleSelectOption(questionId, optionKey) {
    if (feedbacks[questionId]) return;
    setSelectedOptions(prev => ({ ...prev, [questionId]: optionKey }));
    try {
      const data = await submitQuestionAnswer(user.accessToken, questionId, { selectedOption: optionKey });
      setFeedbacks(prev => ({ ...prev, [questionId]: data }));
    } catch { /* non-critical */ }
  }

  // ── Start simulated test ───────────────────────────────────────────────────
  async function handleStartTest(subjects) {
    setTestLoading(true);
    // For CUET, store and use the subjects the student selected
    const subjsToUse = subjects && subjects.length > 0 ? subjects : cuetSelectedSubjects;
    if (subjects) setCuetSelectedSubjects(subjects);
    try {
      const data = await startSimulatedTest(user.accessToken, selectedExam);
      setTestSession(data);
      const now = Date.now();
      testStartRef.current = now;
      setTestStartTimestamp(now);
      setTestAnswers({});
      setActiveMode("test");
      // For CUET: fetch questions per selected subject so only chosen subjects appear
      if (selectedExam === "cuet_ug" && subjsToUse.length > 0) {
        const allQ = [];
        for (const subj of subjsToUse) {
          const qData = await getExamPrepQuestions(user.accessToken, {
            exam: selectedExam, subject: subj, limit: 40,
          });
          allQ.push(...(qData.questions || []));
        }
        setQuestions(allQ);
      } else if (data.question_ids?.length > 0) {
        // Fetch per-subject to match the real exam structure (JEE: 25/subj, NEET: 45/subj)
        const cfg = EXAM_SIM_CONFIG[selectedExam] || EXAM_SIM_CONFIG.jee_main;
        const allQ = [];
        for (const subj of cfg.subjects) {
          const perSubjLimit = cfg.questionsPerSubject || Math.round(cfg.questions / cfg.subjects.length);
          const qData = await getExamPrepQuestions(user.accessToken, {
            exam: selectedExam, subject: subj, limit: perSubjLimit,
          });
          allQ.push(...(qData.questions || []));
        }
        setQuestions(allQ);
      } else {
        setQuestions([]);
      }
    } catch (e) {
      alert(e.message || "Failed to start test");
    } finally { setTestLoading(false); }
  }

  // ── Submit simulated test ──────────────────────────────────────────────────
  async function handleSubmitTest() {
    if (!testSession?.test_id) return;
    setTestLoading(true);
    const timeSpent = testStartRef.current ? Math.round((Date.now() - testStartRef.current) / 1000) : 0;
    const answers = Object.entries(testAnswers).map(([qid, opt]) => ({
      question_id: qid,
      selected_option: opt,
      time_taken_seconds: 60,
    }));
    try {
      const result = await submitSimulatedTest(user.accessToken, testSession.test_id, { answers, timeSpentSeconds: timeSpent });
      setTestResult(result);
      setActiveMode("result");
    } catch (e) {
      alert(e.message || "Failed to submit test");
    } finally { setTestLoading(false); }
  }

  // ── Access guard: loading ──────────────────────────────────────────────────
  if (!accessCheck) {
    return (
      <div className="premium-page">
        <section className="premium-section" style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: 200 }}>
          <Loader size={20} style={{ animation: "spin 1s linear infinite", color: "var(--muted,#64748b)" }} />
          <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
        </section>
      </div>
    );
  }

  // ── Access guard: grade ineligible ─────────────────────────────────────────
  if (!accessCheck.grade_eligible) {
    return (
      <div className="premium-page">
        <section className="premium-section" style={{ textAlign: "center", padding: "60px 20px" }}>
          <div style={{ fontSize: "3rem", marginBottom: 16 }}>🔒</div>
          <h3 style={{ fontSize: "1.2rem", fontWeight: 800, marginBottom: 8 }}>Exam Prep Center</h3>
          <p style={{ color: "var(--muted,#64748b)", maxWidth: 380, margin: "0 auto 0" }}>
            Available for Grade 11 & 12 students only. Check back soon!
          </p>
        </section>
      </div>
    );
  }

  // ── Premium gate — free/nano tier sees locked preview (canonical from backend) ──
  if (accessCheck.preview_only) {
    const isNano = accessCheck.reason === "nano";
    return (
      <div className="premium-page">
        <section className="premium-section" style={{ paddingBottom: 0 }}>
          <div style={{ background: "rgba(99,102,241,.07)", border: "1px solid rgba(99,102,241,.3)", borderRadius: 10, padding: "9px 14px", fontSize: ".8rem", marginBottom: 16, display: "flex", alignItems: "center", gap: 9 }}>
            <span>🎓</span>
            <span><strong>Grade 11 & 12 — Competitive Exam Prep.</strong> JEE Main · NEET UG · CUET UG</span>
          </div>
          {/* Exam tabs (disabled visual only) */}
          <div style={{ display: "flex", gap: 8, marginBottom: 20, flexWrap: "wrap", opacity: 0.5, pointerEvents: "none" }}>
            {Object.entries(EXAMS).map(([key, exam]) => (
              <button key={key} style={{ padding: "9px 18px", borderRadius: 10, border: `2px solid ${key === "jee_main" ? exam.color : "var(--border,#334155)"}`, background: key === "jee_main" ? `${exam.color}18` : "var(--panel,#1e293b)", color: key === "jee_main" ? exam.color : "var(--muted,#94a3b8)", fontWeight: 700, fontSize: ".82rem", fontFamily: "inherit", display: "flex", alignItems: "center", gap: 7 }}>
                <span>{exam.icon}</span><span>{exam.label}</span>
              </button>
            ))}
          </div>
        </section>

        {/* Lock screen */}
        <section className="premium-section" style={{ paddingTop: 0 }}>
          <div style={{ background: "linear-gradient(135deg,rgba(99,102,241,.08),rgba(139,92,246,.06))", border: "1px solid rgba(99,102,241,.25)", borderRadius: 16, padding: "40px 32px", textAlign: "center", maxWidth: 560, margin: "0 auto" }}>
            <div style={{ fontSize: "3rem", marginBottom: 16 }}>🔐</div>
            <h3 style={{ fontSize: "1.25rem", fontWeight: 800, marginBottom: 8, background: "linear-gradient(135deg,#6366f1,#8b5cf6)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
              Exam Prep Center — Premium Feature
            </h3>
            <p style={{ color: "var(--muted,#64748b)", fontSize: ".88rem", lineHeight: 1.6, marginBottom: 24, maxWidth: 420, margin: "0 auto 24px" }}>
              {isNano
                ? "The Exam Prep Center is available on Premium and higher plans. Your current Premium Nano plan includes CBSE lessons for Grade 5–10 but not JEE/NEET/CUET prep."
                : "JEE Main, NEET UG & CUET UG preparation — AI-powered practice questions, simulated full tests, topic-wise analysis, and instant AI explanations. Upgrade to access."}
            </p>
            {/* Feature preview */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 28, textAlign: "left" }}>
              {[
                { icon: "📐", label: "JEE Main prep", desc: "Physics, Chem, Maths" },
                { icon: "🔬", label: "NEET UG prep", desc: "Physics, Chem, Biology" },
                { icon: "🏛️", label: "CUET UG prep", desc: "All streams" },
                { icon: "📊", label: "Simulated tests", desc: "Full 3-hour test series" },
                { icon: "🤖", label: "AI explanations", desc: "Step-by-step solutions" },
                { icon: "🎯", label: "Weak topic tracker", desc: "Personalized analytics" },
              ].map(f => (
                <div key={f.label} style={{ display: "flex", gap: 8, alignItems: "center", background: "rgba(255,255,255,.03)", borderRadius: 8, padding: "8px 10px" }}>
                  <span style={{ fontSize: "1.1rem" }}>{f.icon}</span>
                  <div>
                    <div style={{ fontSize: ".75rem", fontWeight: 700 }}>{f.label}</div>
                    <div style={{ fontSize: ".62rem", color: "var(--muted,#64748b)" }}>{f.desc}</div>
                  </div>
                </div>
              ))}
            </div>
            <button
              disabled
              style={{ padding: "13px 32px", background: "var(--border,#334155)", border: "none", borderRadius: 12, color: "var(--muted,#64748b)", fontWeight: 800, fontSize: ".95rem", cursor: "not-allowed", fontFamily: "inherit", marginBottom: 10 }}
            >
              Coming Soon
            </button>
          </div>
        </section>
      </div>
    );
  }

  // ── Result mode ────────────────────────────────────────────────────────────
  if (activeMode === "result" && testResult) {
    return (
      <div className="premium-page">
        <TestResultPage
          result={testResult}
          onRetake={() => { setActiveMode("practice"); setTestResult(null); setTestSession(null); }}
          onClose={() => { setActiveMode("practice"); setTestResult(null); setTestSession(null); }}
        />
      </div>
    );
  }

  const examInfo = EXAMS[selectedExam] || EXAMS.jee_main;

  return (
    <div className="premium-page">
      {/* Access banner */}
      <section className="premium-section" style={{ paddingBottom: 0 }}>
        <div style={{ background: isTestUser ? "rgba(99,102,241,.07)" : "rgba(245,158,11,.07)", border: `1px solid ${isTestUser ? "rgba(99,102,241,.3)" : "rgba(245,158,11,.3)"}`, borderRadius: 10, padding: "9px 14px", fontSize: ".8rem", marginBottom: 16, display: "flex", alignItems: "center", gap: 9 }}>
          <span>{isTestUser ? "🧪" : isAdmin ? "🔒" : "🎓"}</span>
          <span>
            {isTestUser ? <><strong>Test Access.</strong> Early access before student launch.</> :
             isAdmin ? <><strong>Admin Preview.</strong> Not yet visible to students.</> :
             <><strong>Grade 11 & 12 — Competitive Exam Prep.</strong> JEE Main · NEET UG · CUET UG</>}
          </span>
        </div>

        {/* Exam tabs — stream-aware: JEE for PCM/PCMB, NEET for PCB/PCMB */}
        <div style={{ display: "flex", gap: 8, marginBottom: 20, flexWrap: "wrap" }}>
          {Object.entries(EXAMS).map(([key, exam]) => {
            const elig = accessCheck?.exam_eligibility?.[key];
            const ineligible = elig && !elig.eligible && !elig.coming_soon;
            const comingSoon = elig?.coming_soon;
            return (
              <button key={key}
                onClick={() => !comingSoon && !ineligible && setSelectedExam(key)}
                title={ineligible ? elig.reason : comingSoon ? "Coming Soon" : ""}
                style={{
                  padding: "9px 18px", borderRadius: 10,
                  border: `2px solid ${selectedExam === key ? exam.color : ineligible ? "var(--border,#1e293b)" : "var(--border,#334155)"}`,
                  background: selectedExam === key ? `${exam.color}18` : "var(--panel,#1e293b)",
                  color: selectedExam === key ? exam.color : ineligible ? "var(--muted,#475569)" : "var(--muted,#94a3b8)",
                  fontWeight: 700, fontSize: ".82rem",
                  cursor: (comingSoon || ineligible) ? "default" : "pointer",
                  fontFamily: "inherit",
                  opacity: ineligible ? 0.4 : comingSoon ? 0.55 : 1,
                  display: "flex", alignItems: "center", gap: 7,
                }}>
                <span>{exam.icon}</span>
                <span>{exam.label}</span>
                {comingSoon && <span style={{ fontSize: ".6rem", background: "rgba(245,158,11,.2)", color: "#fbbf24", padding: "1px 6px", borderRadius: 10 }}>Soon</span>}
                {ineligible && <span style={{ fontSize: ".6rem", background: "rgba(100,116,139,.2)", color: "#64748b", padding: "1px 6px", borderRadius: 10 }}>N/A</span>}
              </button>
            );
          })}
        </div>

        {/* Stats row */}
        {loadingDash ? (
          <div style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--muted,#64748b)", fontSize: ".8rem", marginBottom: 20 }}>
            <Loader size={14} style={{ animation: "spin 1s linear infinite" }} /> Loading stats…
            <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
          </div>
        ) : dashboard && (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(130px,1fr))", gap: 10, marginBottom: 24 }}>
            <StatCard value={`${dashboard.weeks_to_exam}w`} label={`Weeks to ${examInfo.label}`} icon="📅" color="#6366f1" />
            <StatCard value={dashboard.total_questions} label="Questions Available" icon="❓" color="#10b981" />
            <StatCard value={dashboard.questions_attempted} label="Practiced" icon="✅" color="#f59e0b" />
            <StatCard value={`${dashboard.accuracy_pct}%`} label="Accuracy" icon="🎯" color={dashboard.accuracy_pct >= 60 ? "#22c55e" : "#ef4444"} />
            <StatCard value={dashboard.total_topics} label="Topics" icon="📚" color="#8b5cf6" />
          </div>
        )}

        {/* Mode tabs — 5 tabs */}
        <div style={{ display: "flex", gap: 8, marginBottom: 20, flexWrap: "wrap" }}>
          {[
            { key: "learn",     label: "Structured Learning", icon: "📖" },
            { key: "practice",  label: "Practice",            icon: "⚡" },
            { key: "test",      label: "Simulated Test",      icon: "📝" },
            { key: "reference", label: "Quick Reference",     icon: "📋" },
            { key: "oracle",    label: "Cutoff Oracle",       icon: "🔮" },
          ].map(m => (
            <button key={m.key}
              onClick={() => {
                setActiveMode(m.key);
                // When opening reference, default to first subject of current exam
                if (m.key === "reference") {
                  const examRef = QUICK_REFERENCE[selectedExam];
                  if (examRef) setRefSubject(examRef.subjects?.[0] || "");
                }
              }}
              style={{ padding: "8px 16px", borderRadius: 8, border: `1px solid ${activeMode === m.key ? (m.key === "oracle" ? "#8b5cf6" : m.key === "reference" ? "#10b981" : "#6366f1") : "var(--border,#334155)"}`, background: activeMode === m.key ? (m.key === "oracle" ? "rgba(139,92,246,.12)" : m.key === "reference" ? "rgba(16,185,129,.12)" : "rgba(99,102,241,.12)") : "var(--panel,#1e293b)", color: activeMode === m.key ? (m.key === "oracle" ? "#a78bfa" : m.key === "reference" ? "#34d399" : "#a5b4fc") : "var(--muted,#94a3b8)", fontWeight: 700, fontSize: ".8rem", cursor: "pointer", fontFamily: "inherit" }}>
              {m.icon} {m.label}
            </button>
          ))}
        </div>
      </section>

      {/* ── Cutoff Oracle mode ── */}
      {activeMode === "oracle" && (() => {
        // Static last-5-year cutoff data (NTA/JoSAA/MCC 2021-2025, General category)
        const ORACLE_DATA = {
          jee_main: {
            title: "JEE Main → NIT / IIIT / GFTI Admission",
            subtitle: "Score → Percentile → College mapping (JoSAA 2021–2025, General category, Home State)",
            note: "Percentile and ranks vary by session. Data reflects 5-year averages. NIT CS/IT is most competitive.",
            scoreKey: "Score (out of 300)",
            maxScore: 300,
            bands: [
              { range: "270–300", label: "Elite", color: "#22c55e", emoji: "🏆",
                colleges: ["NIT Trichy – CSE", "NIT Warangal – CSE", "NIT Surathkal – CSE", "IIIT Hyderabad – CSE", "NIT Calicut – CSE"],
                percentile: "99.5–100", rank: "Top 1,000 (CRL)", tip: "JEE Advanced qualifier range" },
              { range: "230–270", label: "Top-Tier", color: "#3b82f6", emoji: "🎯",
                colleges: ["NIT Trichy – ECE/Mech", "NIT Warangal – ECE", "IIIT Allahabad – CSE", "NIT Rourkela – CSE", "NIT Calicut – ECE"],
                percentile: "99.0–99.5", rank: "1,000–5,000 (CRL)", tip: "Target top NITs for non-CS branches" },
              { range: "190–230", label: "Strong", color: "#f59e0b", emoji: "💪",
                colleges: ["NIT Bhopal – CSE", "NIT Durgapur – CSE", "NIT Jamshedpur – CSE", "IIIT Jabalpur – CSE", "MNIT Jaipur – ECE"],
                percentile: "97–99", rank: "5,000–20,000 (CRL)", tip: "Good range for mid-tier NITs CSE" },
              { range: "150–190", label: "Moderate", color: "#f97316", emoji: "📈",
                colleges: ["NIT Agartala – CSE", "IIIT Vadodara", "NIT Manipur – CSE", "GFTIs – CSE", "DTU Delhi (state quota)"],
                percentile: "93–97", rank: "20,000–60,000 (CRL)", tip: "Explore GFTIs and state-level NITs" },
              { range: "100–150", label: "Qualifying", color: "#ef4444", emoji: "🔑",
                colleges: ["GFTIs – Non-CS branches", "State engineering colleges (top tier)", "IIIT Una / Kurnool – ECE"],
                percentile: "83–93", rank: "60,000–1,50,000 (CRL)", tip: "Qualify for lower GFTIs; focus on state counselling" },
              { range: "Below 100", label: "Limited", color: "#94a3b8", emoji: "📚",
                colleges: ["State engineering colleges", "Private colleges", "Repeat for better score"],
                percentile: "Below 83", rank: "1,50,000+ (CRL)", tip: "Consider state-level JOSAA alternatives or repeat" },
            ],
            categories: [
              { cat: "General", note: "Highest cutoff. All NIT seats via CRL." },
              { cat: "OBC-NCL", note: "~10–15% lower rank than General." },
              { cat: "SC", note: "~50–60% lower rank than General." },
              { cat: "ST", note: "~70% lower rank than General." },
            ],
            footer: "Source: JoSAA 2021–2025 opening/closing ranks (Round 6). Ranks are approximate and vary by institute & branch.",
          },
          neet_ug: {
            title: "NEET UG → MBBS / BDS / AYUSH Admission",
            subtitle: "Score → College tier mapping (MCC/State counselling 2021–2025, All India Quota)",
            note: "720 marks total. Biology (360 marks) is the deciding factor. State quota has different cutoffs.",
            scoreKey: "Score (out of 720)",
            maxScore: 720,
            bands: [
              { range: "650–720", label: "Elite", color: "#22c55e", emoji: "🏆",
                colleges: ["AIIMS Delhi", "AIIMS Jodhpur/Bhopal/Patna", "JIPMER Puducherry", "Maulana Azad (MAMC) Delhi"],
                percentile: "99.9+", rank: "Top 500 (AIR)", tip: "AIIMS cutoff General: ~695–715 (varies by year)" },
              { range: "610–650", label: "Top-Tier", color: "#3b82f6", emoji: "🎯",
                colleges: ["State AIIMS (Rishikesh/Nagpur/Raipur)", "JNMC Aligarh", "Seth GS Medical Mumbai", "Grant Medical College"],
                percentile: "99.5–99.9", rank: "500–3,000 (AIR)", tip: "Top government medical colleges accessible" },
              { range: "550–610", label: "Strong", color: "#f59e0b", emoji: "💪",
                colleges: ["State government MBBS (top states)", "BHU MBBS", "Lady Hardinge Medical College", "Safdarjung Hospital"],
                percentile: "98.5–99.5", rank: "3,000–15,000 (AIR)", tip: "Strong govt MBBS range. State counselling important." },
              { range: "500–550", label: "Moderate", color: "#f97316", emoji: "📈",
                colleges: ["Government MBBS (state quota)", "Top private medical colleges (management quota)", "ESIC Medical Colleges"],
                percentile: "95–98.5", rank: "15,000–50,000 (AIR)", tip: "Government MBBS in some states; explore private govt-aided" },
              { range: "450–500", label: "Borderline", color: "#ef4444", emoji: "⚠️",
                colleges: ["Private MBBS (high fees ~50L–1Cr)", "BDS (Dental) in government colleges", "AYUSH (BAMS/BHMS) govt colleges"],
                percentile: "85–95", rank: "50,000–1,20,000 (AIR)", tip: "Minimum NEET qualifying cutoff is 50th percentile (General)" },
              { range: "Below 450", label: "Limited", color: "#94a3b8", emoji: "📚",
                colleges: ["BDS / BAMS / BHMS private", "Veterinary (BVSC)", "Consider re-attempting NEET"],
                percentile: "Below 85", rank: "1,20,000+ (AIR)", tip: "Minimum qualifying percentile: 50th (General), 40th (SC/ST)" },
            ],
            categories: [
              { cat: "General", note: "Min: 50th percentile (~720×50% ≈ 360+ marks)." },
              { cat: "OBC/SC/ST", note: "Min: 40th percentile. Same seats, lower cutoff." },
              { cat: "PWD", note: "Min: 45th percentile for PH quota seats." },
            ],
            footer: "Source: MCC NEET-UG counselling 2021–2025 (Rounds 1–3). AIIMS has separate AIIMS MBBS counselling. Scores are approx and shift each year.",
          },
          cuet_ug: {
            title: "CUET UG → DU / BHU / JNU / Central University Admission",
            subtitle: "Score → Programme mapping (CUET 2022–2025, General category, Per-subject out of 200)",
            note: "CUET scores are per subject. Colleges set their own cutoffs based on subject combinations. Data is indicative.",
            scoreKey: "Score per subject (out of 200)",
            maxScore: 200,
            bands: [
              { range: "185–200", label: "Elite", color: "#22c55e", emoji: "🏆",
                colleges: ["Miranda House – English / Eco / Hist", "Lady Shri Ram – Eco/Psych", "Hindu College – B.Sc./B.A.", "SRCC – B.Com(H)"],
                percentile: "Top 1%", rank: "Open/Unreserved seats", tip: "DU's top colleges require near-perfect scores for popular courses" },
              { range: "165–185", label: "Top-Tier", color: "#3b82f6", emoji: "🎯",
                colleges: ["Hansraj College – Sciences", "Ramjas College – English/Eco", "Kirori Mal – Maths/Physics", "JMC (Journalism) DU"],
                percentile: "Top 5%", rank: "Good DU colleges", tip: "Most DU college/course combinations open at this range" },
              { range: "140–165", label: "Strong", color: "#f59e0b", emoji: "💪",
                colleges: ["BHU – BA/B.Sc./B.Com", "Jamia Millia Islamia – BA/B.Sc.", "Dyal Singh / Zakir Husain – DU", "Gargi College DU"],
                percentile: "Top 15%", rank: "Mid-range central universities", tip: "BHU and Jamia accessible; some DU evening colleges" },
              { range: "110–140", label: "Moderate", color: "#f97316", emoji: "📈",
                colleges: ["JNU – BA (Hons) some programmes", "Hyderabad Central University", "Pondicherry University", "EFLU Hyderabad"],
                percentile: "Top 30%", rank: "Good central universities outside DU", tip: "Many central universities have good programmes at this range" },
              { range: "80–110", label: "Qualifying", color: "#ef4444", emoji: "🔑",
                colleges: ["Various central universities", "Banaras Hindu University (some courses)", "North-East central universities"],
                percentile: "Top 50%", rank: "General qualifying range", tip: "Minimum qualifying score is typically 50–60 out of 200" },
              { range: "Below 80", label: "Limited", color: "#94a3b8", emoji: "📚",
                colleges: ["Private universities", "State universities", "Consider re-attempting CUET"],
                percentile: "Below 50%", rank: "Borderline", tip: "Most central universities set minimum at 40–60 marks per subject" },
            ],
            categories: [
              { cat: "General/Unreserved", note: "Highest cutoff. Scores shown above are for Open category." },
              { cat: "OBC-NCL", note: "~5–10% lower scores typically open OBC seats." },
              { cat: "SC/ST/EWS", note: "Significantly lower cutoffs. Apply to reserved seats." },
            ],
            footer: "Source: CUET-UG 2022–2025 (DU 1st–4th cutoffs, BHU, JNU admissions). Scores vary widely by subject and programme. Always check official cutoffs.",
          },
          sat: {
            title: "SAT (Digital SAT) → US / Global University Admissions",
            subtitle: "Score → University tier mapping (College Board 2022–2025, General applicants)",
            note: "SAT is accepted by 1,900+ US universities. Scores are scaled (not raw). No negative marking.",
            scoreKey: "SAT Score (400–1600)",
            maxScore: 1600,
            bands: [
              { range: "1500–1600", label: "Elite", color: "#22c55e", emoji: "🏆",
                colleges: ["MIT", "Harvard", "Stanford", "Princeton", "Yale", "Columbia", "University of Chicago"],
                percentile: "99th+", rank: "Top ~500 scorers globally", tip: "1600 is perfect score. These universities look beyond SAT — also need top GPA, essays, ECs." },
              { range: "1400–1499", label: "Top-Tier", color: "#3b82f6", emoji: "🎯",
                colleges: ["UC Berkeley", "UCLA", "University of Michigan", "NYU", "Boston University", "Purdue (CS/Engg)"],
                percentile: "96th–99th", rank: "Top 4%", tip: "Strong scores for top 50 US universities. Merit scholarships often require 1400+." },
              { range: "1300–1399", label: "Strong", color: "#f59e0b", emoji: "💪",
                colleges: ["Penn State", "University of Wisconsin", "Arizona State", "Florida International", "Singapore (NUS/NTU — international SAT accepted)"],
                percentile: "88th–96th", rank: "Top 12%", tip: "Good for admission to many well-ranked US public universities. Apply broadly." },
              { range: "1200–1299", label: "Moderate", color: "#f97316", emoji: "📈",
                colleges: ["Many US mid-range universities", "Community college transfer track", "UK/Australia universities (some use SAT)"],
                percentile: "74th–88th", rank: "Top 26%", tip: "Above average score. Accepted by many US universities. Strengthen GPA and extracurriculars." },
              { range: "1100–1199", label: "Qualifying", color: "#ef4444", emoji: "🔑",
                colleges: ["Regional US universities", "Test-optional universities (may not need SAT)", "State colleges"],
                percentile: "56th–74th", rank: "Above average", tip: "Many universities are test-optional (post-COVID). A strong application may outweigh a moderate SAT." },
              { range: "Below 1100", label: "Consider Retaking", color: "#94a3b8", emoji: "📚",
                colleges: ["Test-optional universities", "Community colleges", "Non-US alternatives (IELTS/TOEFL pathway)"],
                percentile: "Below 56th", rank: "Average", tip: "Digital SAT can be taken multiple times. Khan Academy free prep. Target 1200+ with focused study." },
            ],
            categories: [
              { cat: "Reading & Writing (200–800)", note: "Grammar, comprehension, vocabulary, reasoning — 54 questions, 64 min." },
              { cat: "Mathematics (200–800)", note: "Algebra (35%), Advanced Math (35%), Data Analysis (15%), Geometry/Trig (15%) — 44 questions, 70 min." },
              { cat: "Adaptive Scoring", note: "Module 2 difficulty adapts based on Module 1 performance. Higher performance in M1 → harder (higher-ceiling) M2." },
            ],
            footer: "Source: College Board SAT percentile data 2022–2025. University median SAT scores from Common Data Sets. Scores vary by programme and year.",
          },
          ielts: {
            title: "IELTS Academic → University Admissions Worldwide",
            subtitle: "Band score → University tier mapping (British Council / IDP 2022–2025, Academic IELTS)",
            note: "IELTS uses a 0–9 Band scale. Most universities require Band 6.0–7.0. No negative marking.",
            scoreKey: "Overall Band Score (0–9)",
            maxScore: 9,
            bands: [
              { range: "8.0–9.0", label: "Expert/Very Good", color: "#22c55e", emoji: "🏆",
                colleges: ["Oxford / Cambridge", "Imperial College London", "UCL", "LSE", "University of Toronto", "NUS Singapore"],
                percentile: "Top 5%", rank: "Expert user", tip: "Band 9 is very rare. Most top UK universities require Band 7.5–8.0 minimum for competitive programmes." },
              { range: "7.0–7.5", label: "Good", color: "#3b82f6", emoji: "🎯",
                colleges: ["Most UK Russell Group universities", "Australian Group of 8", "McGill / UBC Canada", "ETH Zurich", "TU Munich (English programmes)"],
                percentile: "Top 15%", rank: "Good user", tip: "Band 7.0 is the most common minimum for postgraduate programmes. Many UK master's require 7.0 overall, 6.5 in each component." },
              { range: "6.5", label: "Competent+", color: "#f59e0b", emoji: "💪",
                colleges: ["Many UK / Australian / Canadian universities", "Ireland universities", "Netherlands English-taught programmes"],
                percentile: "Top 25%", rank: "Competent user", tip: "The most widely accepted minimum overall. Often paired with a minimum of 6.0 per band." },
              { range: "6.0", label: "Competent", color: "#f97316", emoji: "📈",
                colleges: ["Entry-level UK / Australian / Canadian universities", "Many pathway programmes", "Foundation Year entry"],
                percentile: "Top 40%", rank: "Competent user", tip: "Minimum for most undergraduate international admissions. Some universities accept 6.0 with conditions." },
              { range: "5.5", label: "Modest", color: "#ef4444", emoji: "⚠️",
                colleges: ["Pre-sessional / Foundation entry", "Some universities with conditional offers", "English language courses"],
                percentile: "Top 55%", rank: "Modest user", tip: "Often only sufficient for pre-sessional English courses before university. Most universities require 6.0+." },
              { range: "Below 5.5", label: "Limited", color: "#94a3b8", emoji: "📚",
                colleges: ["English language schools", "IELTS preparation institutes", "Foundation programmes"],
                percentile: "Below 55%", rank: "Limited user", tip: "Retake recommended. Study for 2–4 months. Focus on Listening and Reading for quickest improvement." },
            ],
            categories: [
              { cat: "Listening (0–9)", note: "4 recordings, 40 questions, 30 min. Everyday and academic contexts. MCQ, gap-fill, matching." },
              { cat: "Reading (0–9)", note: "3 academic passages, 40 questions, 60 min. Matching headings, T/F/NG, sentence completion." },
              { cat: "Writing (0–9)", note: "Task 1: Describe a graph/chart (150 words). Task 2: Essay (250 words). 60 min total." },
              { cat: "Speaking (0–9)", note: "3-part interview with examiner. 11–14 min. Introduction, cue card, discussion." },
            ],
            footer: "Source: British Council / IDP IELTS band descriptors 2022–2025. University requirements from official admissions pages. Band requirements vary by programme.",
          },
          toefl_ibt: {
            title: "TOEFL iBT → University Admissions (US & Global)",
            subtitle: "Score → University tier mapping (ETS 2022–2025, iBT Internet-Based Test)",
            note: "TOEFL iBT scores 0–120. Each of 4 sections scored 0–30. No negative marking. Duration ~2 hours.",
            scoreKey: "TOEFL iBT Score (0–120)",
            maxScore: 120,
            bands: [
              { range: "110–120", label: "Elite", color: "#22c55e", emoji: "🏆",
                colleges: ["MIT", "Harvard", "Yale", "Stanford", "Princeton", "Top US research universities"],
                percentile: "Top 5%", rank: "Expert Level", tip: "Most Ivy League and T20 US universities require 100+ for admission. 110+ is competitive for top programmes." },
              { range: "100–109", label: "Top-Tier", color: "#3b82f6", emoji: "🎯",
                colleges: ["Top 50 US universities", "University of Toronto", "McGill", "Australian Group of 8 (many accept TOEFL)"],
                percentile: "Top 15%", rank: "Advanced", tip: "100+ is the most common minimum for competitive graduate programmes in the US." },
              { range: "90–99", label: "Strong", color: "#f59e0b", emoji: "💪",
                colleges: ["Most top 100 US universities", "University of Edinburgh", "Some UK universities", "European English-taught programmes"],
                percentile: "Top 30%", rank: "High Intermediate", tip: "90+ accepted by most US universities. Graduate programmes often require 90–100." },
              { range: "80–89", label: "Moderate", color: "#f97316", emoji: "📈",
                colleges: ["Many US state universities", "UK universities (some)", "Canada (conditional admission)"],
                percentile: "Top 45%", rank: "Intermediate", tip: "80+ is sufficient for many undergraduate US admissions. Graduate programmes may require higher." },
              { range: "60–79", label: "Qualifying", color: "#ef4444", emoji: "🔑",
                colleges: ["Community colleges and transfer pathways", "ESL bridge programmes", "Conditional university admissions"],
                percentile: "Top 60%", rank: "Low-Intermediate", tip: "Below minimum for most 4-year universities. Retake recommended or consider IELTS alternative." },
              { range: "Below 60", label: "Limited", color: "#94a3b8", emoji: "📚",
                colleges: ["Intensive English programmes", "Foundation courses", "TOEFL preparation institutes"],
                percentile: "Below 60%", rank: "Basic", tip: "Significant improvement needed. ETS official prep materials + daily academic reading in English recommended." },
            ],
            categories: [
              { cat: "Reading (0–30)", note: "2 academic passages, 20 questions, 35 min. Comprehension, inference, vocabulary, sentence insertion." },
              { cat: "Listening (0–30)", note: "3 lectures + 2 conversations, 28 questions, 36 min. Main ideas, detail, purpose, inference." },
              { cat: "Speaking (0–30)", note: "4 integrated tasks, 16 min. 3 integrated (read/listen/speak) + 1 independent." },
              { cat: "Writing (0–30)", note: "Integrated writing (20 min) + Academic Discussion Writing (10 min). Total 29 min." },
            ],
            footer: "Source: ETS TOEFL score data 2022–2025. University minimum requirements from official admissions pages. Scores and requirements vary by programme and year.",
          },
        };

        const data = ORACLE_DATA[selectedExam] || ORACLE_DATA.jee_main;
        const _examColor = examInfo.color; // reserved for future use (colour-coded bands)

        // ── Compute "Your Standing" from history ──────────────────────────────
        const latestEntry = simHistory.length > 0 ? simHistory[0] : null;
        const latestRawScore = latestEntry
          ? (latestEntry.score_raw != null ? latestEntry.score_raw : Math.round(latestEntry.score_normalized / 100 * data.maxScore))
          : null;
        // Find which band the latest score falls in
        const activeBandIdx = latestRawScore != null
          ? data.bands.findIndex(band => {
              const [lo, hi] = band.range.replace("Below ", "0–").replace("–", " ").split(" ").map(Number);
              return latestRawScore >= lo && (hi ? latestRawScore <= hi : true);
            })
          : -1;
        // Trend: compare latest 2 scores
        const trend = simHistory.length >= 2
          ? (simHistory[0].score_normalized > simHistory[1].score_normalized ? "up"
            : simHistory[0].score_normalized < simHistory[1].score_normalized ? "down" : "same")
          : "none";
        const trendIcon = trend === "up" ? "↗️" : trend === "down" ? "↘️" : trend === "same" ? "→" : "";
        const trendColor = trend === "up" ? "#22c55e" : trend === "down" ? "#ef4444" : "#94a3b8";

        return (
          <section className="premium-section" style={{ paddingTop: 0 }}>

            {/* ── Your Standing panel ── */}
            {simHistoryLoading && (
              <div style={{ background: "var(--panel,#1e293b)", border: "1px solid rgba(139,92,246,.25)", borderRadius: 12, padding: "14px 18px", marginBottom: 20, display: "flex", alignItems: "center", gap: 10, fontSize: ".78rem", color: "var(--muted,#64748b)" }}>
                <Loader size={13} style={{ animation: "spin 1s linear infinite" }} /> Loading your test performance…
              </div>
            )}

            {!simHistoryLoading && simHistory.length === 0 && (
              <div style={{ background: "rgba(139,92,246,.06)", border: "1px dashed rgba(139,92,246,.35)", borderRadius: 12, padding: "16px 20px", marginBottom: 20 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
                  <span style={{ fontSize: "1.4rem" }}>📊</span>
                  <div style={{ fontWeight: 800, fontSize: ".88rem", color: "#a78bfa" }}>Your Standing</div>
                </div>
                <div style={{ fontSize: ".75rem", color: "var(--muted,#64748b)", lineHeight: 1.6 }}>
                  No simulated tests taken yet for <strong>{examInfo.label}</strong>.<br />
                  Take the <button onClick={() => setActiveMode("test")} style={{ background: "none", border: "none", color: "#8b5cf6", fontWeight: 700, fontSize: ".75rem", cursor: "pointer", padding: 0, fontFamily: "inherit" }}>Simulated Test →</button> to see which college band you fall in.
                </div>
              </div>
            )}

            {!simHistoryLoading && simHistory.length > 0 && latestRawScore != null && (
              <div style={{ background: "linear-gradient(135deg,rgba(139,92,246,.1),rgba(99,102,241,.07))", border: "2px solid rgba(139,92,246,.35)", borderRadius: 14, padding: "18px 20px", marginBottom: 20 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14 }}>
                  <span style={{ fontSize: "1.6rem" }}>📊</span>
                  <div>
                    <div style={{ fontWeight: 800, fontSize: ".95rem", color: "#a78bfa" }}>Your Standing — {examInfo.label}</div>
                    <div style={{ fontSize: ".7rem", color: "var(--muted,#64748b)" }}>Based on your last {simHistory.length} simulated test{simHistory.length > 1 ? "s" : ""}</div>
                  </div>
                </div>

                {/* Stats row */}
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(110px,1fr))", gap: 10, marginBottom: 14 }}>
                  {/* Latest score */}
                  <div style={{ background: "rgba(139,92,246,.1)", border: "1px solid rgba(139,92,246,.25)", borderRadius: 10, padding: "10px 12px", textAlign: "center" }}>
                    <div style={{ fontSize: "1.4rem", fontWeight: 900, color: activeBandIdx >= 0 ? data.bands[activeBandIdx].color : "#a78bfa" }}>
                      {latestRawScore}
                    </div>
                    <div style={{ fontSize: ".6rem", color: "var(--muted,#64748b)", marginTop: 2 }}>Latest Score<br />{data.scoreKey.split("(")[1]?.replace(")", "") || ""}</div>
                  </div>
                  {/* Percentile/band */}
                  {activeBandIdx >= 0 && (
                    <div style={{ background: `${data.bands[activeBandIdx].color}14`, border: `1px solid ${data.bands[activeBandIdx].color}40`, borderRadius: 10, padding: "10px 12px", textAlign: "center" }}>
                      <div style={{ fontSize: "1.1rem", marginBottom: 2 }}>{data.bands[activeBandIdx].emoji}</div>
                      <div style={{ fontSize: ".75rem", fontWeight: 800, color: data.bands[activeBandIdx].color }}>{data.bands[activeBandIdx].label}</div>
                      <div style={{ fontSize: ".58rem", color: "var(--muted,#64748b)" }}>{data.bands[activeBandIdx].percentile}</div>
                    </div>
                  )}
                  {/* Tests taken */}
                  <div style={{ background: "rgba(99,102,241,.08)", border: "1px solid rgba(99,102,241,.2)", borderRadius: 10, padding: "10px 12px", textAlign: "center" }}>
                    <div style={{ fontSize: "1.4rem", fontWeight: 900, color: "#a5b4fc" }}>{simHistory.length}</div>
                    <div style={{ fontSize: ".6rem", color: "var(--muted,#64748b)", marginTop: 2 }}>Tests Taken</div>
                  </div>
                  {/* Trend */}
                  {trend !== "none" && (
                    <div style={{ background: `${trendColor}12`, border: `1px solid ${trendColor}35`, borderRadius: 10, padding: "10px 12px", textAlign: "center" }}>
                      <div style={{ fontSize: "1.4rem" }}>{trendIcon}</div>
                      <div style={{ fontSize: ".65rem", fontWeight: 700, color: trendColor, marginTop: 2 }}>
                        {trend === "up" ? "Improving" : trend === "down" ? "Declining" : "Stable"}
                      </div>
                      <div style={{ fontSize: ".55rem", color: "var(--muted,#64748b)" }}>vs prev test</div>
                    </div>
                  )}
                </div>

                {/* Sparkline — last up-to-8 tests as mini bars */}
                {simHistory.length >= 2 && (() => {
                  const bars = simHistory.slice(0, 8).reverse();
                  const maxNorm = Math.max(...bars.map(t => t.score_normalized), 1);
                  return (
                    <div style={{ marginBottom: 14 }}>
                      <div style={{ fontSize: ".62rem", fontWeight: 700, color: "var(--muted,#64748b)", textTransform: "uppercase", letterSpacing: ".05em", marginBottom: 6 }}>Score Trend</div>
                      <div style={{ display: "flex", alignItems: "flex-end", gap: 4, height: 40 }}>
                        {bars.map((t, i) => {
                          const h = Math.max(4, Math.round((t.score_normalized / maxNorm) * 36));
                          const isLatest = i === bars.length - 1;
                          const barColor = isLatest ? "#8b5cf6" : "#334155";
                          return (
                            <div key={t.id} title={`${new Date(t.submitted_at).toLocaleDateString()}: ${t.score_normalized.toFixed(1)}%`}
                              style={{ flex: 1, height: h, background: barColor, borderRadius: 3, transition: "height .3s", minWidth: 8 }} />
                          );
                        })}
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between", marginTop: 4 }}>
                        <span style={{ fontSize: ".58rem", color: "var(--muted,#475569)" }}>Oldest</span>
                        <span style={{ fontSize: ".58rem", color: "#8b5cf6", fontWeight: 700 }}>Latest</span>
                      </div>
                    </div>
                  );
                })()}

                {/* Best score & improvement needed */}
                {simHistory.length >= 2 && (() => {
                  const best = Math.max(...simHistory.map(t => t.score_normalized));
                  const bestRaw = Math.round(best / 100 * data.maxScore);
                  const nextBandIdx = activeBandIdx > 0 ? activeBandIdx - 1 : -1;
                  return (
                    <div style={{ display: "flex", gap: 10, flexWrap: "wrap", fontSize: ".7rem" }}>
                      <div style={{ background: "rgba(34,197,94,.08)", border: "1px solid rgba(34,197,94,.2)", borderRadius: 7, padding: "5px 10px", color: "#4ade80" }}>
                        🏅 Best: <strong>{bestRaw}</strong> / {data.maxScore}
                      </div>
                      {nextBandIdx >= 0 && (
                        <div style={{ background: "rgba(251,191,36,.08)", border: "1px solid rgba(251,191,36,.2)", borderRadius: 7, padding: "5px 10px", color: "#fbbf24" }}>
                          🎯 Next band: <strong>{data.bands[nextBandIdx].label}</strong> — aim for {data.bands[nextBandIdx].range}
                        </div>
                      )}
                    </div>
                  );
                })()}

                <button onClick={() => setActiveMode("test")}
                  style={{ marginTop: 14, padding: "8px 18px", background: "linear-gradient(135deg,#8b5cf6,#6366f1)", border: "none", borderRadius: 8, color: "#fff", fontWeight: 700, fontSize: ".78rem", cursor: "pointer", fontFamily: "inherit" }}>
                  📝 Take Another Test →
                </button>
              </div>
            )}

            {/* Header */}
            <div style={{ background: `linear-gradient(135deg,rgba(139,92,246,.1),rgba(99,102,241,.06))`, border: "1px solid rgba(139,92,246,.25)", borderRadius: 12, padding: "16px 20px", marginBottom: 20 }}>
              <div style={{ display: "flex", alignItems: "flex-start", gap: 14 }}>
                <span style={{ fontSize: "2rem" }}>🔮</span>
                <div>
                  <div style={{ fontWeight: 800, fontSize: ".95rem", marginBottom: 3 }}>{data.title}</div>
                  <div style={{ fontSize: ".78rem", color: "var(--muted,#94a3b8)", marginBottom: 4 }}>{data.subtitle}</div>
                  <div style={{ fontSize: ".72rem", color: "#fbbf24", background: "rgba(245,158,11,.08)", borderRadius: 6, padding: "4px 10px", display: "inline-block" }}>⚠️ {data.note}</div>
                </div>
              </div>
            </div>

            {/* Score bands */}
            <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 20 }}>
              {data.bands.map((band, i) => (
                <div key={i} style={{ background: "var(--panel,#1e293b)", border: `2px solid ${band.color}33`, borderRadius: 12, padding: "14px 16px", display: "grid", gridTemplateColumns: "120px 1fr auto", gap: 14, alignItems: "start" }}>
                  {/* Score range */}
                  <div style={{ textAlign: "center" }}>
                    <div style={{ fontSize: ".6rem", fontWeight: 700, color: "var(--muted,#64748b)", textTransform: "uppercase", letterSpacing: ".05em", marginBottom: 4 }}>{data.scoreKey.split("(")[0].trim()}</div>
                    <div style={{ fontSize: "1.1rem", fontWeight: 900, color: band.color }}>{band.range}</div>
                    <div style={{ fontSize: ".65rem", marginTop: 4 }}>{band.emoji} <span style={{ fontWeight: 700, color: band.color }}>{band.label}</span></div>
                    <div style={{ fontSize: ".58rem", color: "var(--muted,#64748b)", marginTop: 2 }}>{band.percentile}</div>
                    <div style={{ fontSize: ".55rem", color: "var(--muted,#475569)" }}>{band.rank}</div>
                  </div>
                  {/* Colleges */}
                  <div>
                    <div style={{ fontSize: ".65rem", fontWeight: 700, color: "var(--muted,#64748b)", marginBottom: 6 }}>Accessible with this score:</div>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 5 }}>
                      {band.colleges.map((c, ci) => (
                        <span key={ci} style={{ fontSize: ".65rem", background: `${band.color}12`, color: band.color, border: `1px solid ${band.color}30`, padding: "3px 8px", borderRadius: 6, fontWeight: 600 }}>{c}</span>
                      ))}
                    </div>
                  </div>
                  {/* Tip */}
                  <div style={{ fontSize: ".65rem", color: "var(--muted,#64748b)", fontStyle: "italic", maxWidth: 180, lineHeight: 1.4 }}>
                    💡 {band.tip}
                  </div>
                </div>
              ))}
            </div>

            {/* Category guide */}
            <div style={{ background: "var(--panel,#1e293b)", border: "1px solid rgba(139,92,246,.25)", borderRadius: 10, padding: "14px 16px", marginBottom: 16 }}>
              <div style={{ fontSize: ".7rem", fontWeight: 700, color: "#a78bfa", marginBottom: 10 }}>📊 Category-wise Cutoff Guide</div>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                {data.categories.map((cat, i) => (
                  <div key={i} style={{ background: "rgba(139,92,246,.06)", border: "1px solid rgba(139,92,246,.18)", borderRadius: 7, padding: "7px 12px", flex: "1 1 200px" }}>
                    <div style={{ fontSize: ".7rem", fontWeight: 700, color: "#c4b5fd", marginBottom: 2 }}>{cat.cat}</div>
                    <div style={{ fontSize: ".65rem", color: "var(--muted,#94a3b8)" }}>{cat.note}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Footer */}
            <div style={{ fontSize: ".65rem", color: "var(--muted,#475569)", fontStyle: "italic", textAlign: "center" }}>
              🔮 {data.footer}
            </div>
          </section>
        );
      })()}

      {/* ── Quick Reference mode ── */}
      {activeMode === "reference" && (() => {
        const examRef = QUICK_REFERENCE[selectedExam] || QUICK_REFERENCE.jee_main;
        const refSubjects = examRef.subjects || [];
        const activeRefSubj = refSubject || refSubjects[0] || "";
        const subjData = examRef[activeRefSubj] || {};
        const subjColor = SUBJECT_COLORS[activeRefSubj] || "#10b981";
        return (
          <section className="premium-section" style={{ paddingTop: 0 }}>
            <div style={{ fontSize: ".7rem", fontWeight: 700, color: "var(--muted,#64748b)", textTransform: "uppercase", letterSpacing: ".05em", marginBottom: 14 }}>
              📋 {examInfo.label} — Quick Reference · Formulas · Traps · Mnemonics
            </div>

            {/* Subject tabs */}
            <div style={{ display: "flex", gap: 6, marginBottom: 20, flexWrap: "wrap" }}>
              {refSubjects.map(s => {
                const sc = SUBJECT_COLORS[s] || "#10b981";
                const isActive = activeRefSubj === s;
                return (
                  <button key={s} onClick={() => setRefSubject(s)}
                    style={{ padding: "7px 16px", borderRadius: 8, border: `2px solid ${isActive ? sc : "var(--border,#334155)"}`, background: isActive ? `${sc}18` : "var(--panel,#1e293b)", color: isActive ? sc : "var(--muted,#94a3b8)", fontWeight: 700, fontSize: ".8rem", cursor: "pointer", fontFamily: "inherit", display: "flex", alignItems: "center", gap: 6 }}>
                    <span>{SUBJECT_ICONS[s] || "📚"}</span><span>{s}</span>
                  </button>
                );
              })}
            </div>

            {/* Content sections */}
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>

              {/* Key Formulas */}
              {subjData.formulas?.length > 0 && (
                <div style={{ background: "var(--panel,#1e293b)", border: `1px solid ${subjColor}33`, borderRadius: 12, overflow: "hidden" }}>
                  <div style={{ background: `${subjColor}10`, padding: "10px 16px", fontWeight: 700, fontSize: ".78rem", color: subjColor, borderBottom: `1px solid ${subjColor}22` }}>
                    📐 Key Formulas
                  </div>
                  <div style={{ padding: "12px 16px", display: "flex", flexDirection: "column", gap: 6 }}>
                    {subjData.formulas.map((f, i) => (
                      <div key={i} style={{ display: "flex", gap: 12, padding: "7px 10px", background: "rgba(99,102,241,.04)", border: "1px solid rgba(99,102,241,.12)", borderRadius: 7 }}>
                        <code style={{ fontSize: ".75rem", color: "#c7d2fe", fontFamily: "monospace", fontWeight: 700, flexShrink: 0, minWidth: 180 }}>{f.expr}</code>
                        <span style={{ fontSize: ".7rem", color: "var(--muted,#64748b)", lineHeight: 1.4 }}>{f.desc}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Constants */}
              {subjData.constants?.length > 0 && (
                <div style={{ background: "var(--panel,#1e293b)", border: "1px solid rgba(16,185,129,.25)", borderRadius: 12, overflow: "hidden" }}>
                  <div style={{ background: "rgba(16,185,129,.08)", padding: "10px 16px", fontWeight: 700, fontSize: ".78rem", color: "#34d399", borderBottom: "1px solid rgba(16,185,129,.18)" }}>
                    ⚡ Important Constants & Facts
                  </div>
                  <div style={{ padding: "12px 16px", display: "flex", flexDirection: "column", gap: 5 }}>
                    {subjData.constants.map((c, i) => (
                      <div key={i} style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
                        <span style={{ fontSize: ".72rem", fontWeight: 700, color: "#34d399", flexShrink: 0, minWidth: 160 }}>{c.name}</span>
                        <span style={{ fontSize: ".72rem", color: "var(--muted,#94a3b8)", lineHeight: 1.5 }}>{c.value}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Exam Traps */}
              {subjData.traps?.length > 0 && (
                <div style={{ background: "var(--panel,#1e293b)", border: "1px solid rgba(239,68,68,.25)", borderRadius: 12, overflow: "hidden" }}>
                  <div style={{ background: "rgba(239,68,68,.07)", padding: "10px 16px", fontWeight: 700, fontSize: ".78rem", color: "#f87171", borderBottom: "1px solid rgba(239,68,68,.18)" }}>
                    ⚠️ Common Exam Traps — Students Lose Marks Here
                  </div>
                  <div style={{ padding: "12px 16px", display: "flex", flexDirection: "column", gap: 5 }}>
                    {subjData.traps.map((t, i) => (
                      <div key={i} style={{ fontSize: ".72rem", color: "#fca5a5", padding: "5px 8px", background: "rgba(239,68,68,.05)", borderRadius: 5, borderLeft: "3px solid rgba(239,68,68,.4)" }}>
                        {t}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Mnemonics */}
              {subjData.mnemonics?.length > 0 && (
                <div style={{ background: "var(--panel,#1e293b)", border: "1px solid rgba(139,92,246,.25)", borderRadius: 12, overflow: "hidden" }}>
                  <div style={{ background: "rgba(139,92,246,.07)", padding: "10px 16px", fontWeight: 700, fontSize: ".78rem", color: "#a78bfa", borderBottom: "1px solid rgba(139,92,246,.18)" }}>
                    🧠 Memory Mnemonics
                  </div>
                  <div style={{ padding: "12px 16px", display: "flex", flexDirection: "column", gap: 5 }}>
                    {subjData.mnemonics.map((m, i) => (
                      <div key={i} style={{ fontSize: ".72rem", color: "#c4b5fd", padding: "5px 8px", background: "rgba(139,92,246,.05)", borderRadius: 5 }}>
                        {m}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Last-minute Revision */}
              {subjData.revision?.length > 0 && (
                <div style={{ background: "var(--panel,#1e293b)", border: "1px solid rgba(245,158,11,.25)", borderRadius: 12, overflow: "hidden" }}>
                  <div style={{ background: "rgba(245,158,11,.07)", padding: "10px 16px", fontWeight: 700, fontSize: ".78rem", color: "#fbbf24", borderBottom: "1px solid rgba(245,158,11,.18)" }}>
                    🎯 Last-minute Revision Bullets
                  </div>
                  <div style={{ padding: "12px 16px", display: "flex", flexDirection: "column", gap: 4 }}>
                    {subjData.revision.map((r, i) => (
                      <div key={i} style={{ fontSize: ".72rem", color: "#94a3b8", padding: "3px 0", paddingLeft: 12, position: "relative" }}>
                        <span style={{ position: "absolute", left: 0, color: "#fbbf24" }}>•</span>
                        {r}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div style={{ marginTop: 16, fontSize: ".7rem", color: "var(--muted,#475569)", textAlign: "center", fontStyle: "italic" }}>
              Content covers JEE · NEET · CUET — switch exam tab above to change subjects.
            </div>
          </section>
        );
      })()}

      {/* ── Structured Learning mode ── */}
      {activeMode === "learn" && (
        <section className="premium-section" style={{ paddingTop: 0 }}>
          <div style={{ fontSize: ".7rem", fontWeight: 700, color: "var(--muted,#64748b)", textTransform: "uppercase", letterSpacing: ".05em", marginBottom: 16 }}>
            📖 {examInfo.label} — Structured Chapter-wise Study Plan
          </div>
          {subjects.length === 0 ? (
            <div style={{ color: "var(--muted,#64748b)", fontSize: ".82rem" }}>Loading subjects…</div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
              {subjects.map((subj, _si) => {
                const color = SUBJECT_COLORS[subj.name] || "#6366f1";
                return (
                  <div key={subj.name} style={{ background: "var(--panel,#1e293b)", border: `1px solid ${color}44`, borderRadius: 14, overflow: "hidden" }}>
                    {/* Subject header */}
                    <div style={{ background: `${color}12`, padding: "14px 18px", display: "flex", alignItems: "center", gap: 12 }}>
                      <span style={{ fontSize: "1.6rem" }}>{SUBJECT_ICONS[subj.name] || "📚"}</span>
                      <div>
                        <div style={{ fontWeight: 800, fontSize: "1rem" }}>{subj.name}</div>
                        <div style={{ fontSize: ".72rem", color: "var(--muted,#64748b)" }}>
                          {subj.chapters} chapters · {subj.topic_count} topics · {subj.weightage_pct}% weightage
                        </div>
                      </div>
                      <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
                        <span style={{ fontSize: ".65rem", fontWeight: 700, background: `${color}22`, color, padding: "3px 10px", borderRadius: 20 }}>
                          {subj.question_count} questions
                        </span>
                      </div>
                    </div>

                    {/* Study phases */}
                    <div style={{ padding: "14px 18px" }}>
                      <div style={{ fontSize: ".68rem", fontWeight: 700, color: "var(--muted,#64748b)", textTransform: "uppercase", letterSpacing: ".06em", marginBottom: 12 }}>
                        Recommended Study Sequence
                      </div>
                      {(() => {
                        // Derive weak topics from feedbacks (questions answered incorrectly in Practice)
                        const weakTopics = Object.entries(feedbacks)
                          .filter(([, fb]) => !fb.is_correct && fb.topic)
                          .map(([, fb]) => fb.topic)
                          .filter((t, i, arr) => arr.indexOf(t) === i); // unique

                        const phases = [
                          {
                            phase: "Phase 1", icon: "📘", label: "Read NCERT",
                            desc: "Cover all theory, definitions, and solved examples from your textbook",
                            color: "#6366f1", actionLabel: "Open Lessons →",
                            onClick: () => setActivePage && setActivePage("lessons"),
                          },
                          {
                            phase: "Phase 2", icon: "📝", label: "Note Key Concepts",
                            desc: "Formulas, constants, mnemonics and exam traps — your personalised revision notebook",
                            color: "#8b5cf6", actionLabel: "Open Quick Reference →",
                            onClick: () => {
                              const examRef = QUICK_REFERENCE[selectedExam];
                              if (examRef) setRefSubject(examRef.subjects?.[0] || "");
                              setActiveMode("reference");
                            },
                          },
                          {
                            phase: "Phase 3", icon: "⚡", label: "Practice Questions",
                            desc: "Use the Practice tab — work chapter-wise from easy to hard",
                            color: "#10b981", actionLabel: "Go to Practice →",
                            onClick: () => { setSelectedSubject(subj.name); setActiveMode("practice"); handleSelectSubject(subj.name); },
                          },
                          {
                            phase: "Phase 4", icon: "🔁", label: "Revise Weak Topics",
                            desc: weakTopics.length > 0
                              ? `You have ${weakTopics.length} topic${weakTopics.length > 1 ? "s" : ""} to revise: ${weakTopics.slice(0, 3).join(", ")}${weakTopics.length > 3 ? "…" : ""}`
                              : "Your weak topics will appear here as you practise — review incorrect answers and re-read those NCERT sections.",
                            color: "#f59e0b",
                            actionLabel: weakTopics.length > 0 ? `Revise ${weakTopics.length} topic${weakTopics.length > 1 ? "s" : ""} →` : null,
                            onClick: weakTopics.length > 0
                              ? () => {
                                  setSelectedSubject(subj.name);
                                  setActiveMode("practice");
                                  // Load questions filtered to the first weak topic
                                  handleSelectSubject(subj.name).then?.(() => {
                                    setFilterTopic(weakTopics[0]);
                                    loadQuestions(subj.name, weakTopics[0]);
                                  });
                                  setFilterTopic(weakTopics[0]);
                                  loadQuestions(subj.name, weakTopics[0]);
                                }
                              : null,
                          },
                          {
                            phase: "Phase 5", icon: "📊", label: "Full Test Simulation",
                            desc: "Take the Simulated Test to gauge readiness under timed conditions",
                            color: "#ef4444", actionLabel: "Start Simulation →",
                            onClick: () => setActiveMode("test"),
                          },
                        ];

                        return (
                          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(220px,1fr))", gap: 10 }}>
                            {phases.map(p => (
                              <div key={p.phase}
                                onClick={p.onClick || undefined}
                                style={{ background: `${p.color}08`, border: `1px solid ${p.color}25`, borderRadius: 10, padding: "12px 14px", cursor: p.onClick ? "pointer" : "default", transition: "all .12s" }}
                                onMouseEnter={p.onClick ? e => { e.currentTarget.style.background = `${p.color}14`; e.currentTarget.style.borderColor = `${p.color}50`; } : undefined}
                                onMouseLeave={p.onClick ? e => { e.currentTarget.style.background = `${p.color}08`; e.currentTarget.style.borderColor = `${p.color}25`; } : undefined}
                              >
                                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                                  <span style={{ fontSize: "1.1rem" }}>{p.icon}</span>
                                  <div>
                                    <div style={{ fontSize: ".6rem", fontWeight: 700, color: p.color, textTransform: "uppercase", letterSpacing: ".05em" }}>{p.phase}</div>
                                    <div style={{ fontSize: ".78rem", fontWeight: 700 }}>{p.label}</div>
                                  </div>
                                </div>
                                <div style={{ fontSize: ".68rem", color: "var(--muted,#64748b)", lineHeight: 1.5, marginBottom: p.actionLabel ? 8 : 0 }}>{p.desc}</div>
                                {p.actionLabel && (
                                  <div style={{ fontSize: ".65rem", color: p.color, fontWeight: 700, marginTop: 4 }}>{p.actionLabel}</div>
                                )}
                                {p.phase === "Phase 4" && weakTopics.length === 0 && (
                                  <div style={{ fontSize: ".6rem", color: "var(--muted,#475569)", marginTop: 6, fontStyle: "italic" }}>
                                    🕐 Builds as you study
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        );
                      })()}

                      {/* Priority topics for this subject */}
                      <div style={{ marginTop: 16 }}>
                        <div style={{ fontSize: ".68rem", fontWeight: 700, color: "var(--muted,#64748b)", textTransform: "uppercase", letterSpacing: ".06em", marginBottom: 10 }}>
                          High-Priority Topics to Cover First
                        </div>
                        <button
                          onClick={() => { setSelectedSubject(subj.name); setActiveMode("practice"); handleSelectSubject(subj.name); }}
                          style={{ display: "flex", alignItems: "center", gap: 8, padding: "9px 16px", background: `linear-gradient(135deg,${color},${color}cc)`, border: "none", borderRadius: 8, color: "#fff", fontWeight: 700, fontSize: ".78rem", cursor: "pointer", fontFamily: "inherit" }}>
                          <span>⚡</span> Start Practising {subj.name} →
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Exam-level strategy box */}
          <div style={{ marginTop: 24, background: "rgba(99,102,241,.06)", border: "1px solid rgba(99,102,241,.2)", borderRadius: 12, padding: "18px 20px" }}>
            <div style={{ fontWeight: 800, fontSize: ".9rem", marginBottom: 10 }}>🎯 {examInfo.label} — Exam Strategy</div>
            {selectedExam === "jee_main" && (
              <ul style={{ fontSize: ".78rem", color: "var(--muted,#94a3b8)", lineHeight: 2, margin: 0, paddingLeft: 18 }}>
                <li><strong style={{color:"#a5b4fc"}}>75 questions · 3 hours · 300 marks · +4/−1 (MCQ & Numerical)</strong></li>
                <li>Each subject: 25 questions (20 MCQ + 5 Numerical Value) · Physics / Chemistry / Mathematics</li>
                <li>Numerical: correct = +4 · wrong = −1 (negative marking applies — attempt only when confident)</li>
                <li>Difficulty mix: ~20% easy · ~55% moderate · ~25% hard · Average time: 2.4 min/question</li>
                <li>Topic weightage: Calculus ~35% · Algebra ~30% · Coordinate Geometry ~20% · Vectors ~10%</li>
                <li>Chemistry is easiest · Physics is calculation-heavy · Maths is consistently toughest</li>
                <li>Target: 70%+ accuracy. Focus on Mechanics, Electrostatics, Organic, Calculus first.</li>
              </ul>
            )}
            {selectedExam === "neet_ug" && (
              <ul style={{ fontSize: ".78rem", color: "var(--muted,#94a3b8)", lineHeight: 2, margin: 0, paddingLeft: 18 }}>
                <li><strong style={{color:"#34d399"}}>180 questions · 3 hours · 720 marks · +4/−1 · Pen & Paper (OMR)</strong></li>
                <li>4 subjects: Physics (45 Qs) · Chemistry (45 Qs) · Botany (45 Qs) · Zoology (45 Qs)</li>
                <li>Biology (Botany + Zoology) = 90 questions = 360 marks — most weightage!</li>
                <li>Difficulty mix: ~30% easy · ~50% moderate · ~20% hard · Average time: 1.0 min/question</li>
                <li>90–95% of Biology questions come directly from NCERT text — read every line</li>
                <li>High-weight Biology chapters: Genetics · Human Physiology · Ecology · Biotechnology</li>
                <li>Target: 550+ score. Biology alone can carry you — Physics has most difficult questions.</li>
              </ul>
            )}
            {selectedExam === "cuet_ug" && (
              <ul style={{ fontSize: ".78rem", color: "var(--muted,#94a3b8)", lineHeight: 2, margin: 0, paddingLeft: 18 }}>
                <li>Section IA: English (mandatory) · Section II: 2–6 Domain subjects · Section III: General Test</li>
                <li>+5 / –1 marking · Questions are NCERT Class 12 level</li>
                <li>Focus on Class 12 NCERT thoroughly — most questions come directly from it</li>
                <li>General Test: current affairs, quantitative aptitude, logical reasoning</li>
                <li>Choose domain subjects matching your target university programme.</li>
              </ul>
            )}
            {selectedExam === "sat" && (
              <ul style={{ fontSize: ".78rem", color: "var(--muted,#94a3b8)", lineHeight: 2, margin: 0, paddingLeft: 18 }}>
                <li><strong style={{color:"#3b82f6"}}>98 questions · 134 min · Score 400–1600 · No negative marking · Digital Adaptive Test</strong></li>
                <li>Reading & Writing: 54 questions, 64 min · Mathematics: 44 questions, 70 min</li>
                <li>Adaptive: Module 1 performance determines Module 2 difficulty. Higher M1 → harder M2 → higher ceiling.</li>
                <li>No penalty for wrong answers — always guess if unsure. Blank = 0, guess = chance of +1.</li>
                <li>Desmos graphing calculator available throughout Math section — use it for graph/equation questions.</li>
                <li>Math focus: Algebra + Advanced Math = 70% of score. Master linear equations, quadratics, functions first.</li>
                <li>R&W focus: vocabulary in context, grammar (subject-verb agreement, parallel structure), evidence-based reading.</li>
                <li>Target: 1400+ for top 50 US universities. 1200+ opens most mid-tier universities.</li>
              </ul>
            )}
            {selectedExam === "ielts" && (
              <ul style={{ fontSize: ".78rem", color: "var(--muted,#94a3b8)", lineHeight: 2, margin: 0, paddingLeft: 18 }}>
                <li><strong style={{color:"#8b5cf6"}}>4 skills · ~2h45m total · Band Score 0–9 · No negative marking</strong></li>
                <li>Listening (30 min) · Reading (60 min) · Writing (60 min) · Speaking (11–14 min, separate appointment)</li>
                <li>Spelling counts in Listening and Writing — one wrong letter = wrong answer in gap-fill.</li>
                <li>True/False/Not Given: "Not Given" ≠ "False". If passage doesn't mention it → Not Given.</li>
                <li>Word limit: 'NO MORE THAN 2 WORDS' means 2 max — writing 3 words = wrong even if correct fact.</li>
                <li>Writing Task 2 (essay, 250+ words) carries the most weight in the Writing band score.</li>
                <li>Speaking: recorded. Focus on fluency over accuracy — don't stop to correct yourself mid-sentence.</li>
                <li>Target: Band 6.5 for most universities · Band 7.0 for UK postgraduate · Band 7.5+ for top programmes.</li>
              </ul>
            )}
            {selectedExam === "toefl_ibt" && (
              <ul style={{ fontSize: ".78rem", color: "var(--muted,#94a3b8)", lineHeight: 2, margin: 0, paddingLeft: 18 }}>
                <li><strong style={{color:"#06b6d4"}}>4 sections · ~2 hours total · Score 0–120 (30 per section) · No negative marking</strong></li>
                <li>Reading (35 min, 20 Qs) · Listening (36 min, 28 Qs) · Speaking (16 min) · Writing (29 min)</li>
                <li>Each audio plays ONCE — note-taking during Listening is essential. Never relying on memory alone.</li>
                <li>Integrated Writing: summarise how the LECTURE challenges the READING — do NOT give your own opinion.</li>
                <li>Academic Discussion Writing: add a NEW point or reason, don't just agree with classmates' posts.</li>
                <li>Reading: Prose Summary questions ask you to choose 3 of 6 — wrong answers are too specific (details, not main ideas).</li>
                <li>Official ETS materials are the gold standard for practice — other sources vary in difficulty calibration.</li>
                <li>Target: 100+ for top US grad programmes · 90+ for most US universities · 80+ for many undergrad programmes.</li>
              </ul>
            )}
          </div>
        </section>
      )}

      {/* ── Practice mode ── */}
      {activeMode === "practice" && (
        <>
          {/* Subject cards */}
          <section className="premium-section" style={{ paddingTop: 0 }}>
            <div style={{ fontSize: ".7rem", fontWeight: 700, color: "var(--muted,#64748b)", textTransform: "uppercase", letterSpacing: ".05em", marginBottom: 12 }}>
              {examInfo.icon} {examInfo.label} — Subjects
            </div>
            {subjects.length === 0 ? (
              <div style={{ color: "var(--muted,#64748b)", fontSize: ".82rem" }}>Loading subjects…</div>
            ) : (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(200px,1fr))", gap: 12, marginBottom: selectedSubject ? 20 : 0 }}>
                {subjects.map(s => (
                  <SubjectCard key={s.name} subject={s} selected={selectedSubject === s.name} onClick={() => handleSelectSubject(s.name)} />
                ))}
              </div>
            )}

            {/* Topic cards */}
            {selectedSubject && (
              <div style={{ marginTop: 16 }}>
                <div style={{ fontSize: ".7rem", fontWeight: 700, color: "var(--muted,#64748b)", textTransform: "uppercase", letterSpacing: ".05em", marginBottom: 12 }}>
                  {SUBJECT_ICONS[selectedSubject]} {selectedSubject} — Priority Topics
                </div>
                {loadingTopics ? (
                  <div style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--muted,#64748b)", fontSize: ".78rem" }}>
                    <Loader size={13} style={{ animation: "spin 1s linear infinite" }} /> Loading topics…
                  </div>
                ) : (
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(240px,1fr))", gap: 10 }}>
                    {topics.map(t => (
                      <TopicCard key={t.name} topic={t} onPractice={handlePracticeTopic} />
                    ))}
                  </div>
                )}
              </div>
            )}
          </section>

          {/* Question practice */}
          {selectedSubject && (
            <section className="premium-section" style={{ paddingTop: 0 }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
                <div>
                  <div style={{ fontSize: ".7rem", fontWeight: 700, color: "var(--muted,#64748b)", textTransform: "uppercase", letterSpacing: ".05em" }}>
                    Quick Practice {filterTopic ? `— ${filterTopic}` : `— ${selectedSubject}`}
                  </div>
                  {filterTopic && (
                    <button onClick={() => { setFilterTopic(null); loadQuestions(selectedSubject, null); }}
                      style={{ fontSize: ".65rem", color: "#6366f1", background: "none", border: "none", cursor: "pointer", padding: 0, marginTop: 2 }}>
                      ✕ Clear filter
                    </button>
                  )}
                </div>
                <div style={{ fontSize: ".72rem", color: "var(--muted,#64748b)" }}>{questions.length} questions</div>
              </div>

              {loadingQuestions ? (
                <div style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--muted,#64748b)", fontSize: ".8rem" }}>
                  <Loader size={14} style={{ animation: "spin 1s linear infinite" }} /> Loading questions…
                </div>
              ) : questions.length === 0 ? (
                <div style={{ background: "var(--panel,#1e293b)", border: "1px solid var(--border,#334155)", borderRadius: 10, padding: 24, textAlign: "center" }}>
                  <div style={{ fontSize: "2rem", marginBottom: 10 }}>📭</div>
                  <div style={{ fontSize: ".85rem", fontWeight: 700, marginBottom: 6 }}>No questions available yet</div>
                  <div style={{ fontSize: ".75rem", color: "var(--muted,#64748b)" }}>
                    {isAdmin ? "Use the Admin → Exam Prep Question Bank to generate questions." : "Check back soon — questions are being added!"}
                  </div>
                </div>
              ) : (
                <div style={{ display: "grid", gridTemplateColumns: "1fr 360px", gap: 14 }}>
                  {/* Question list */}
                  <div style={{ background: "var(--panel,#1e293b)", border: "1px solid var(--border,#334155)", borderRadius: 12, overflow: "hidden" }}>
                    <div style={{ maxHeight: 500, overflowY: "auto" }}>
                      {questions.map(q => (
                        <div key={q.id} onClick={() => setSelectedQuestion(q.id === selectedQuestion ? null : q)}
                          style={{ borderLeft: `3px solid ${q.id === selectedQuestion?.id ? "#6366f1" : "transparent"}`, cursor: "pointer", background: q.id === selectedQuestion?.id ? "rgba(99,102,241,.05)" : "transparent" }}>
                          <QuestionCard
                            question={q}
                            selectedOption={selectedOptions[q.id]}
                            onSelect={opt => handleSelectOption(q.id, opt)}
                            feedback={feedbacks[q.id]}
                            showFeedback={!!feedbacks[q.id]}
                            username={user?.username}
                          />
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* AI panel */}
                  <div style={{ background: "var(--panel,#1e293b)", border: "1px solid var(--border,#334155)", borderRadius: 12, overflow: "hidden", display: "flex", flexDirection: "column", maxHeight: 500 }}>
                    <div style={{ padding: "10px 14px", borderBottom: "1px solid var(--border,#334155)", background: "rgba(99,102,241,.06)", display: "flex", alignItems: "center", gap: 8 }}>
                      <div style={{ width: 22, height: 22, borderRadius: "50%", background: "linear-gradient(135deg,#6366f1,#10b981)", display: "grid", placeItems: "center", fontSize: ".7rem", flexShrink: 0 }}>🤖</div>
                      <div style={{ fontSize: ".8rem", fontWeight: 700, color: "#a5b4fc" }}>
                        {selectedQuestion ? `AI Explanation — ${selectedQuestion.topic || ""}` : "AI Explanation"}
                      </div>
                    </div>
                    <div style={{ flex: 1, overflowY: "auto" }}>
                      <AIPanel
                        question={selectedQuestion}
                        selectedOption={selectedOptions[selectedQuestion?.id]}
                        feedback={feedbacks[selectedQuestion?.id]}
                        user={user}
                      />
                    </div>
                  </div>
                </div>
              )}
            </section>
          )}
        </>
      )}

      {/* ── Simulated Test mode ── */}
      {activeMode === "test" && !testResult && (
        <section className="premium-section" style={{ paddingTop: 0 }}>
          {!testSession ? (
            selectedExam === "cuet_ug" ? (
              // CUET: show realistic subject combination selector
              <CUETTestSetup onStart={(subjects) => handleStartTest(subjects)} testLoading={testLoading} />
            ) : (
            <div style={{ maxWidth: 560, margin: "0 auto", textAlign: "center", padding: "40px 20px" }}>
              <div style={{ fontSize: "3rem", marginBottom: 16 }}>{examInfo.icon}</div>
              <h3 style={{ fontSize: "1.2rem", fontWeight: 800, marginBottom: 8 }}>Start {examInfo.label} Simulation</h3>
              {(() => {
                const cfg = EXAM_SIM_CONFIG[selectedExam] || EXAM_SIM_CONFIG.jee_main;
                return (
                  <>
                    <p style={{ color: "var(--muted,#64748b)", fontSize: ".85rem", marginBottom: 24, lineHeight: 1.6 }}>
                      {cfg.questions} questions across {cfg.subjects.length} subjects · {cfg.duration} min · {cfg.totalMarks ? `${cfg.totalMarks} marks · ` : ""}{cfg.marking}
                    </p>
                    <div style={{ display: "grid", gridTemplateColumns: `repeat(${cfg.subjects.length},1fr)`, gap: 10, marginBottom: 28 }}>
                      {cfg.subjects.map(s => (
                        <div key={s} style={{ background: "var(--panel,#1e293b)", border: "1px solid var(--border,#334155)", borderRadius: 10, padding: "12px 10px", textAlign: "center" }}>
                          <div style={{ fontSize: "1.3rem", marginBottom: 4 }}>{SUBJECT_ICONS[s] || "📚"}</div>
                          <div style={{ fontSize: ".75rem", fontWeight: 700 }}>{s}</div>
                          <div style={{ fontSize: ".62rem", color: "var(--muted,#64748b)" }}>{cfg.questionsPerSubject || Math.round(cfg.questions / cfg.subjects.length)} Qs</div>
                        </div>
                      ))}
                    </div>
                  </>
                );
              })()}
              <button onClick={handleStartTest} disabled={testLoading}
                style={{ padding: "13px 32px", background: `linear-gradient(135deg,${examInfo.color},${examInfo.color}cc)`, border: "none", borderRadius: 12, color: "#fff", fontWeight: 800, fontSize: ".95rem", cursor: "pointer", fontFamily: "inherit", opacity: testLoading ? .7 : 1, display: "flex", alignItems: "center", gap: 10, margin: "0 auto" }}>
                {testLoading ? <><Loader size={16} style={{ animation: "spin 1s linear infinite" }} /> Starting…</> : `🚀 Start ${examInfo.label} Simulation`}
              </button>
            </div>
            )
          ) : (
            <NTATestView
              questions={questions}
              testSession={testSession}
              testAnswers={testAnswers}
              setTestAnswers={setTestAnswers}
              onSubmit={handleSubmitTest}
              testLoading={testLoading}
              startTimestamp={testStartTimestamp}
              examLabel={examInfo.label}
              examColor={examInfo.color}
              cuetSubjects={selectedExam === "cuet_ug" ? cuetSelectedSubjects : null}
              username={user?.username}
            />
          )}
        </section>
      )}

      {/* ── Resource links ── */}
      <section className="premium-section">
        <div style={{ fontSize: ".7rem", fontWeight: 700, color: "var(--muted,#64748b)", textTransform: "uppercase", letterSpacing: ".05em", marginBottom: 14 }}>
          📚 Resources & Tools
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(160px,1fr))", gap: 10 }}>
          {RESOURCES.map(r => (
            <div key={r.label}
              onClick={() => r.onClick && setActivePage && setActivePage(r.onClick)}
              className="premium-card"
              style={{ border: `1px solid ${r.onClick ? r.color + "40" : "var(--border,#334155)"}`, borderRadius: 10, padding: "14px 14px", cursor: r.onClick ? "pointer" : "default", transition: "all .12s", marginBottom: 0 }}>
              <div style={{ fontSize: "1.4rem", marginBottom: 6 }}>{r.icon}</div>
              <div style={{ fontWeight: 700, fontSize: ".8rem", marginBottom: 3 }}>{r.label}</div>
              <div style={{ fontSize: ".65rem", color: "var(--muted,#64748b)" }}>{r.desc}</div>
              {r.onClick && <div style={{ fontSize: ".62rem", color: r.color, marginTop: 6, fontWeight: 600 }}>Open →</div>}
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
