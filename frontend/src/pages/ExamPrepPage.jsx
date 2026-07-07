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

import { useEffect, useState, useRef } from "react";
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
} from "../api/examPrep";

// ── Constants ──────────────────────────────────────────────────────────────────

// NOTE: Frontend does NOT infer Exam Prep access from plan strings.
// All access decisions come from GET /api/exam-prep/access-check (canonical backend).
const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const TEST_ACCESS_USERS = new Set(["akshita.teststudent"]);

const EXAMS = {
  jee_main: { label: "JEE Main", icon: "📐", color: "#6366f1", active: true },
  neet_ug: { label: "NEET UG", icon: "🔬", color: "#10b981", active: true },
  cuet_ug: { label: "CUET UG", icon: "🏛️", color: "#f59e0b", active: true },
};

// Exam-specific simulation config
const EXAM_SIM_CONFIG = {
  jee_main: { subjects: ["Physics", "Chemistry", "Mathematics"], duration: 180, questions: 90, marking: "+4 / -1" },
  neet_ug: { subjects: ["Physics", "Chemistry", "Biology"], duration: 200, questions: 200, marking: "+4 / -1" },
  cuet_ug: { subjects: ["English", "General Test", "Domain Subject"], duration: 195, questions: 150, marking: "+5 / -1" },
};

const SUBJECT_ICONS = { Physics: "⚛️", Chemistry: "🧪", Mathematics: "📐", Biology: "🌿" };
const SUBJECT_COLORS = { Physics: "#6366f1", Chemistry: "#10b981", Mathematics: "#f59e0b", Biology: "#22c55e" };
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

function QuestionCard({ question, selectedOption, onSelect, feedback, showFeedback }) {
  const opts = question.options_json || [];
  const isCorrect = (key) => showFeedback && feedback?.correct_option === key;
  const isWrong = (key) => showFeedback && selectedOption === key && !feedback?.is_correct;

  return (
    <div style={{ padding: "16px", borderBottom: "1px solid var(--border,#334155)" }}>
      <div style={{ display: "flex", gap: 8, marginBottom: 10, flexWrap: "wrap" }}>
        <span style={{ fontSize: ".6rem", fontWeight: 700, background: `${DIFFICULTY_COLORS[question.difficulty] || "#94a3b8"}22`, color: DIFFICULTY_COLORS[question.difficulty] || "#94a3b8", padding: "2px 8px", borderRadius: 20 }}>{question.difficulty}</span>
        <span style={{ fontSize: ".6rem", color: "var(--muted,#64748b)", background: "rgba(255,255,255,.05)", padding: "2px 8px", borderRadius: 20 }}>{question.topic}</span>
        {question.marks && <span style={{ fontSize: ".6rem", color: "#fbbf24", background: "rgba(251,191,36,.08)", padding: "2px 8px", borderRadius: 20 }}>+{question.marks} / -{question.negative_marks}</span>}
      </div>
      <div style={{ fontSize: ".85rem", color: "var(--text,#1e293b)", lineHeight: 1.6, marginBottom: 14 }}>{question.question_text}</div>
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
              <span style={{ fontSize: ".8rem", color: "var(--text,#1e293b)", lineHeight: 1.5, flex: 1 }}>{opt.text}</span>
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
              style={{ flex: 1, background: "var(--surface,#0f172a)", border: "1px solid var(--border,#334155)", borderRadius: 6, padding: "6px 9px", color: "#f1f5f9", fontSize: ".72rem", fontFamily: "inherit" }} />
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
                <div style={{ background: "rgba(255,255,255,.06)", borderRadius: 6, height: 6 }}>
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
              <li key={i} style={{ fontSize: ".75rem", color: "#cbd5e1", marginBottom: 4, lineHeight: 1.5 }}>{r}</li>
            ))}
          </ul>
        </div>
      )}

      <div style={{ display: "flex", gap: 10, justifyContent: "center" }}>
        <button onClick={onRetake} style={{ padding: "11px 24px", background: "linear-gradient(135deg,#6366f1,#8b5cf6)", border: "none", borderRadius: 10, color: "#fff", fontWeight: 700, fontSize: ".88rem", cursor: "pointer", fontFamily: "inherit" }}>
          Try Again
        </button>
        <button onClick={onClose} style={{ padding: "11px 24px", background: "rgba(255,255,255,.06)", border: "1px solid var(--border,#334155)", borderRadius: 10, color: "#f1f5f9", fontWeight: 700, fontSize: ".88rem", cursor: "pointer", fontFamily: "inherit" }}>
          Back to Dashboard
        </button>
      </div>
    </div>
  );
}

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
  const [activeMode, setActiveMode] = useState("practice"); // practice | test | result
  const [testSession, setTestSession] = useState(null);
  const [testAnswers, setTestAnswers] = useState({});
  const [testResult, setTestResult] = useState(null);
  const [testLoading, setTestLoading] = useState(false);
  const [filterTopic, setFilterTopic] = useState(null);
  const testStartRef = useRef(null);

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
  async function handleStartTest() {
    setTestLoading(true);
    try {
      const data = await startSimulatedTest(user.accessToken, selectedExam);
      setTestSession(data);
      testStartRef.current = Date.now();
      setTestAnswers({});
      setActiveMode("test");
      // Load questions for test
      if (data.question_ids?.length > 0) {
        const qData = await getExamPrepQuestions(user.accessToken, { exam: selectedExam, limit: 90 });
        setQuestions(qData.questions || []);
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
            <StatCard value={`${dashboard.weeks_to_exam}w`} label="Weeks to JEE" icon="📅" color="#6366f1" />
            <StatCard value={dashboard.total_questions} label="Questions Available" icon="❓" color="#10b981" />
            <StatCard value={dashboard.questions_attempted} label="Practiced" icon="✅" color="#f59e0b" />
            <StatCard value={`${dashboard.accuracy_pct}%`} label="Accuracy" icon="🎯" color={dashboard.accuracy_pct >= 60 ? "#22c55e" : "#ef4444"} />
            <StatCard value={dashboard.total_topics} label="Topics" icon="📚" color="#8b5cf6" />
          </div>
        )}

        {/* Mode tabs */}
        <div style={{ display: "flex", gap: 8, marginBottom: 20 }}>
          {[
            { key: "practice", label: "Quick Practice", icon: "⚡" },
            { key: "test", label: "Simulated Test", icon: "📝" },
          ].map(m => (
            <button key={m.key} onClick={() => setActiveMode(m.key)}
              style={{ padding: "8px 16px", borderRadius: 8, border: `1px solid ${activeMode === m.key ? "#6366f1" : "var(--border,#334155)"}`, background: activeMode === m.key ? "rgba(99,102,241,.12)" : "var(--panel,#1e293b)", color: activeMode === m.key ? "#a5b4fc" : "var(--muted,#94a3b8)", fontWeight: 700, fontSize: ".8rem", cursor: "pointer", fontFamily: "inherit" }}>
              {m.icon} {m.label}
            </button>
          ))}
        </div>
      </section>

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
            <div style={{ maxWidth: 560, margin: "0 auto", textAlign: "center", padding: "40px 20px" }}>
              <div style={{ fontSize: "3rem", marginBottom: 16 }}>{examInfo.icon}</div>
              <h3 style={{ fontSize: "1.2rem", fontWeight: 800, marginBottom: 8 }}>Start {examInfo.label} Simulation</h3>
              {(() => {
                const cfg = EXAM_SIM_CONFIG[selectedExam] || EXAM_SIM_CONFIG.jee_main;
                return (
                  <>
                    <p style={{ color: "var(--muted,#64748b)", fontSize: ".85rem", marginBottom: 24, lineHeight: 1.6 }}>
                      A full {examInfo.label} simulation with ~{cfg.questions} questions across {cfg.subjects.join(", ")}.
                      {cfg.duration} minutes · Marking: {cfg.marking}
                    </p>
                    <div style={{ display: "grid", gridTemplateColumns: `repeat(${cfg.subjects.length},1fr)`, gap: 10, marginBottom: 28 }}>
                      {cfg.subjects.map(s => (
                        <div key={s} style={{ background: "var(--panel,#1e293b)", border: "1px solid var(--border,#334155)", borderRadius: 10, padding: "12px 10px", textAlign: "center" }}>
                          <div style={{ fontSize: "1.3rem", marginBottom: 4 }}>{SUBJECT_ICONS[s] || "📚"}</div>
                          <div style={{ fontSize: ".75rem", fontWeight: 700 }}>{s}</div>
                          <div style={{ fontSize: ".62rem", color: "var(--muted,#64748b)" }}>~{Math.round(cfg.questions / cfg.subjects.length)} Qs</div>
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
          ) : (
            <div>
              {/* Test header */}
              <div style={{ background: "var(--panel,#1e293b)", border: "1px solid var(--border,#334155)", borderRadius: 10, padding: "12px 16px", marginBottom: 16, display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 10 }}>
                <div>
                  <div style={{ fontWeight: 800, fontSize: ".9rem" }}>🎯 {examInfo.label} Simulation</div>
                  <div style={{ fontSize: ".7rem", color: "var(--muted,#64748b)" }}>
                    {Object.keys(testAnswers).length} / {testSession.total_questions || questions.length} answered
                  </div>
                </div>
                <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                  <div style={{ fontSize: ".75rem", color: "var(--muted,#64748b)" }}>⏱️ {testSession.duration_minutes} min</div>
                  <button onClick={handleSubmitTest} disabled={testLoading}
                    style={{ padding: "9px 20px", background: "#22c55e", border: "none", borderRadius: 8, color: "#fff", fontWeight: 700, fontSize: ".82rem", cursor: "pointer", fontFamily: "inherit" }}>
                    {testLoading ? "Submitting…" : "Submit Test →"}
                  </button>
                </div>
              </div>

              {questions.length === 0 ? (
                <div style={{ textAlign: "center", padding: 40, color: "var(--muted,#64748b)" }}>
                  <div style={{ fontSize: "2rem", marginBottom: 12 }}>📭</div>
                  <div style={{ fontSize: ".85rem", fontWeight: 700, marginBottom: 6 }}>No questions in bank yet</div>
                  <div style={{ fontSize: ".75rem" }}>Admin needs to prewarm the question bank first.</div>
                  <button onClick={handleSubmitTest} style={{ marginTop: 16, padding: "9px 20px", background: "#6366f1", border: "none", borderRadius: 8, color: "#fff", fontWeight: 700, fontSize: ".82rem", cursor: "pointer", fontFamily: "inherit" }}>
                    Submit Empty Test (see result)
                  </button>
                </div>
              ) : (
                <div style={{ maxHeight: 520, overflowY: "auto", background: "var(--panel,#1e293b)", border: "1px solid var(--border,#334155)", borderRadius: 12 }}>
                  {questions.map((q, idx) => (
                    <div key={q.id} style={{ borderLeft: `3px solid ${testAnswers[q.id] ? "#22c55e" : "transparent"}` }}>
                      <div style={{ padding: "8px 16px 0", fontSize: ".68rem", color: "var(--muted,#64748b)", fontWeight: 700 }}>Q{idx + 1}</div>
                      <QuestionCard
                        question={q}
                        selectedOption={testAnswers[q.id]}
                        onSelect={opt => setTestAnswers(prev => ({ ...prev, [q.id]: opt }))}
                        feedback={null}
                        showFeedback={false}
                      />
                    </div>
                  ))}
                </div>
              )}
            </div>
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
