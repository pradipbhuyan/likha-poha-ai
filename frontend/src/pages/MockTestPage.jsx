import { useEffect, useRef, useState } from "react";
import { getSyllabus } from "../api/syllabus";
import { generateMockTest } from "../api/mockTest";
import { saveTestHistory, saveWrongAnswers } from "../api/analytics";
import { logStudentActivity } from "../api/profile";
import { evaluateStudentAnswer } from "../api/evaluation";
import { getDefaultSelection, getUserBoard, getUserGrade, getVisibleGrades } from "../utils/syllabusDefaults";
import { filterAllowedSubjects, isSchoolBoardMode } from "../utils/subjectAccess";
import { isAllAccessTestUser } from "../utils/testAccounts";
import { hasPaidAccess } from "../utils/resolveSubscription";

function MathText({ text }) {
  const str = String(text || "");
  const parts = str.split(/(\^\{[^}]+\}|\^[0-9]+)/g);
  return (
    <span>
      {parts.map((part, i) => {
        if (part.startsWith("^")) {
          const exp = part.replace(/^\^[{]?/, "").replace(/[}]$/, "");
          return <sup key={i}>{exp}</sup>;
        }
        return part;
      })}
    </span>
  );
}

const FREE_DAILY_MOCK_LIMIT = 5;
function getDailyMockKey(u) { return `mock_daily_${u}_${new Date().toISOString().slice(0, 10)}`; }
function getDailyMockCount(u) { try { return parseInt(localStorage.getItem(getDailyMockKey(u)) || "0", 10); } catch { return 0; } }
function incrementDailyMockCount(u) { try { const k = getDailyMockKey(u); localStorage.setItem(k, String(parseInt(localStorage.getItem(k) || "0", 10) + 1)); } catch { /* */ } }

const PHASE_SETUP = "setup";
const PHASE_EXAM  = "exam";
const PHASE_RESULT = "result";
const FORMAT_MCQ     = "mcq";
const FORMAT_WRITTEN = "written";
const FORMAT_MIXED   = "mixed";

function MockTestPage({ user, setActivePage }) {
  const [syllabusData,    setSyllabusData]    = useState(null);
  const [grade,           setGrade]           = useState("Grade 9");
  const [mode,            setMode]            = useState("CBSE");
  const [subject,         setSubject]         = useState("");
  const [chapter,         setChapter]         = useState("");
  const [mockType,        setMockType]        = useState("CBSE Exam Mock Test");
  const [examType,        setExamType]        = useState("Class Test");
  const [difficulty,      setDifficulty]      = useState("Medium");
  const [questionCount,   setQuestionCount]   = useState(5);
  const [questionFormat,  setQuestionFormat]  = useState(FORMAT_MCQ);
  const [timerEnabled,    setTimerEnabled]    = useState(true);
  const [durationMinutes, setDurationMinutes] = useState(30);
  const [negativeMarking, setNegativeMarking] = useState(false);
  const [negativeMarks,   setNegativeMarks]   = useState(0.25);
  const [phase,           setPhase]           = useState(PHASE_SETUP);
  const [questions,       setQuestions]       = useState([]);
  const [answers,         setAnswers]         = useState({});
  const [writtenAnswers,  setWrittenAnswers]  = useState({});
  const [writtenEvals,    setWrittenEvals]    = useState({});
  const [writtenLoading,  setWrittenLoading]  = useState({});
  const [activeQuestion,  setActiveQuestion]  = useState(0);
  const [results,         setResults]         = useState(null);
  const [testStartedAt,   setTestStartedAt]   = useState(null);
  const [secondsLeft,     setSecondsLeft]     = useState(0);
  const [excludedIds,     setExcludedIds]     = useState([]);
  const [loading,         setLoading]         = useState(false);
  const [error,           setError]           = useState("");

  const examTopRef    = useRef(null);
  const questionRefs  = useRef({});

  const isPaid            = hasPaidAccess(user);
  const isFreeUser        = user?.role === "student" && !isPaid;
  const todayMockCount    = isFreeUser ? getDailyMockCount(user?.username) : 0;
  const dailyLimitReached = isFreeUser && todayMockCount >= FREE_DAILY_MOCK_LIMIT;

  // ── Load syllabus ────────────────────────────────────────────────────────────
  useEffect(() => {
    async function load() {
      try {
        const data = await getSyllabus();
        setSyllabusData(data.syllabus);
        const { grade: dg, mode: dm, subject: ds, chapter: dc } = getDefaultSelection(data.syllabus, getUserGrade(user), getUserBoard(user));
        const allowed = filterAllowedSubjects(user, Object.keys(data.syllabus[dg]?.[dm] || {}), dm);
        let sm = dm, ss = allowed.includes(ds) ? ds : allowed[0] || "";
        if (!ss) {
          sm = Object.keys(data.syllabus[dg] || {}).find(mn => filterAllowedSubjects(user, Object.keys(data.syllabus[dg]?.[mn] || {}), mn).length > 0) || dm;
          ss = filterAllowedSubjects(user, Object.keys(data.syllabus[dg]?.[sm] || {}), sm)[0] || "";
        }
        setGrade(dg); setMode(sm); setSubject(ss);
        setChapter(ss === ds ? dc : data.syllabus[dg]?.[sm]?.[ss]?.[0] || "");
      } catch { setError("Could not load syllabus"); }
    }
    load();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Timer ────────────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!timerEnabled || secondsLeft <= 0 || phase !== PHASE_EXAM) return;
    const t = setInterval(() => setSecondsLeft(p => Math.max(0, p - 1)), 1000);
    return () => clearInterval(t);
  }, [timerEnabled, secondsLeft, phase]);

  if (!syllabusData) return <p>Loading mock test setup...</p>;

  // ── Derived ──────────────────────────────────────────────────────────────────
  const grades = getVisibleGrades(syllabusData, user);
  const modes  = Object.keys(syllabusData[grade]).filter(m => m !== "SOF" || grade === "Grade 9");
  function getAllowed(all, sm) { return filterAllowedSubjects(user, all, sm); }
  const subjects     = getAllowed(Object.keys(syllabusData[grade][mode]), mode);
  const chapters     = subject ? syllabusData[grade][mode][subject] || [] : [];
  const requestBoard = mode === "SOF" ? getUserBoard(user) : mode;

  const isMCQ     = q => !q.question_type || q.question_type === "mcq";
  const isWritten = q => q.question_type === "written_short" || q.question_type === "written_long";

  const mcqDone     = questions.filter(isMCQ).filter(q => answers[q.id]).length;
  const writtenDone = questions.filter(isWritten).filter(q => (writtenAnswers[q.id] || "").trim()).length;
  const answeredCount   = mcqDone + writtenDone;
  const progressPercent = questions.length ? Math.round(answeredCount / questions.length * 100) : 0;

  function formatTime(s) { return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`; }

  function perf(pct) {
    if (pct >= 90) return { title: "🌟 Olympiad Ready",      msg: "Outstanding! You have mastered this chapter." };
    if (pct >= 75) return { title: "👏 Strong Foundation",   msg: "Very good! Concepts are strong and improving." };
    if (pct >= 60) return { title: "👍 Good Progress",       msg: "Improving well. More practice will boost you further." };
    return           { title: "💪 Revision Needed",          msg: "Keep practicing — revising core concepts will help." };
  }

  function rec(pct) {
    if (pct >= 85) return "Recommended next: Hard / Olympiad HOTS";
    if (pct >= 60) return "Recommended next: Medium difficulty";
    return "Recommended: Easy with thorough revision";
  }

  // ── Handlers ─────────────────────────────────────────────────────────────────
  function clearTest() {
    setPhase(PHASE_SETUP); setQuestions([]); setAnswers({}); setWrittenAnswers({});
    setWrittenEvals({}); setWrittenLoading({}); setResults(null); setSecondsLeft(0);
    setTestStartedAt(null); setActiveQuestion(0);
  }

  function resetSelections(ng, nm) {
    const a = getAllowed(Object.keys(syllabusData[ng][nm] || {}), nm);
    setSubject(a[0] || ""); setChapter(a[0] ? syllabusData[ng][nm][a[0]][0] : "");
  }

  function handleGradeChange(v) {
    const gradeModes = Object.keys(syllabusData[v]);
    const nm = gradeModes.find(mn => getAllowed(Object.keys(syllabusData[v][mn] || {}), mn).length > 0) || gradeModes[0];
    setGrade(v); setMode(nm); resetSelections(v, nm); setError(""); clearTest();
  }

  function handleModeChange(v) {
    const a = getAllowed(Object.keys(syllabusData[grade][v]), v);
    if (!a.length) { setMode(v); setSubject(""); setChapter(""); setError(`No access to ${v} tests`); clearTest(); return; }
    setError(""); setMode(v); setSubject(a[0]); setChapter(syllabusData[grade][v][a[0]]?.[0] || ""); clearTest();
  }

  function handleSubjectChange(v) { setSubject(v); setChapter(syllabusData[grade][mode][v][0]); clearTest(); }

  function handleAnswerChange(qId, optKey) { setAnswers(p => ({ ...p, [qId]: optKey })); }

  async function handleEvaluateWritten(q) {
    const ans = (writtenAnswers[q.id] || "").trim();
    if (!ans) return;
    setWrittenLoading(p => ({ ...p, [q.id]: true }));
    setWrittenEvals(p => ({ ...p, [q.id]: null }));
    try {
      const r = await evaluateStudentAnswer({
        grade, mode, subject, chapter, step_title: examType, username: user?.username,
        question: q.question, student_answer: ans,
        ideal_context: q.explanation || q.model_answer || "",
        question_type: "short_answer", expected_keywords: q.expected_keywords || [],
      });
      setWrittenEvals(p => ({ ...p, [q.id]: r }));
    } catch {
      setWrittenEvals(p => ({ ...p, [q.id]: { success: false, evaluation: "Could not evaluate. Try again." } }));
    } finally {
      setWrittenLoading(p => ({ ...p, [q.id]: false }));
    }
  }

  async function handleGenerateMockTest() {
    if (dailyLimitReached) return;
    if (questionFormat !== FORMAT_MCQ && !isPaid && user?.role !== "admin" && !isAllAccessTestUser(user)) {
      setError("✍️ Written and Mixed modes require a paid subscription. MCQ is free for all.");
      return;
    }
    if (isSchoolBoardMode(mode) && user?.role !== "admin" && !isAllAccessTestUser(user) &&
        !isFreeUser && !user.accessCbse && !user.offerAccess) {
      setError(`No access to ${mode} mock tests.`); return;
    }
    if (mode === "SOF" && user?.role !== "admin" && !isAllAccessTestUser(user) &&
        !(user.accessSofScience || user.accessSofMaths || user.accessSofEnglish)) {
      setError("No access to SOF mock tests."); return;
    }

    setLoading(true); setError(""); setResults(null);
    setAnswers({}); setWrittenAnswers({}); setWrittenEvals({}); setWrittenLoading({});

    try {
      const res = await generateMockTest({
        grade, mode, board: requestBoard, subject, chapter,
        mock_type: mockType, difficulty, question_count: Number(questionCount),
        exam_type: examType, excluded_ids: excludedIds, question_format: questionFormat,
      });
      if (!res.success) { setError(res.message || "Could not generate mock test"); return; }

      const newQs = res.questions || [];
      setQuestions(newQs); setActiveQuestion(0); setTestStartedAt(Date.now());
      const newIds = newQs.map(q => q.db_id).filter(Boolean);
      if (newIds.length) setExcludedIds(p => [...new Set([...p, ...newIds])].slice(-3000));
      if (timerEnabled) setSecondsLeft(durationMinutes * 60);
      if (isFreeUser) incrementDailyMockCount(user?.username);
      setPhase(PHASE_EXAM);
      setTimeout(() => examTopRef.current?.scrollIntoView({ behavior: "smooth" }), 100);
    } catch { setError("Could not generate mock test. Check backend."); }
    finally { setLoading(false); }
  }

  function handleSubmitTest() {
    let rawScore = 0, maxScore = 0, wrongCount = 0;
    const review = questions.map(q => {
      const marks = Number(q.marks || 1);
      maxScore += marks;
      if (isMCQ(q)) {
        const selected = answers[q.id];
        const isCorrect = selected === q.answer;
        if (isCorrect) rawScore += marks; else wrongCount += 1;
        return { id: q.id, question_type: "mcq", section: q.section, question: q.question,
          options: q.options, selected, correct: q.answer, isCorrect, marks, explanation: q.explanation };
      } else {
        const wrAns = writtenAnswers[q.id] || "";
        const ev    = writtenEvals[q.id];
        const aiScore = ev?.score != null ? Math.min(Number(ev.score), 10) : (wrAns.trim() ? 5 : 0);
        const earnedMarks = Math.round(aiScore / 10 * marks * 10) / 10;
        rawScore += earnedMarks;
        return { id: q.id, question_type: q.question_type, section: q.section, question: q.question,
          wrAns, earnedMarks, marks, aiScore, evaluation: ev?.evaluation || "",
          modelAnswer: q.explanation || q.model_answer || "", isCorrect: aiScore >= 6 };
      }
    });

    const penalty = negativeMarking ? wrongCount * Number(negativeMarks) : 0;
    const finalScore = Math.max(0, rawScore - penalty);
    const percentage = maxScore ? Math.round(finalScore / maxScore * 10000) / 100 : 0;
    const timeTakenSeconds = testStartedAt ? Math.round((Date.now() - testStartedAt) / 1000) : null;

    const payload = {
      username: user?.username, grade, mode, subject, chapter, mockType, examType,
      difficulty, rawScore, finalScore, maxScore, wrongCount, penalty, percentage,
      timeTakenSeconds, submittedAt: new Date().toISOString(), review,
    };

    setResults(payload);
    setPhase(PHASE_RESULT);
    setSecondsLeft(0);

    saveTestHistory(payload)
      .then(() => logStudentActivity({ username: user.username, activity_type: "mock_test_taken" }))
      .catch(() => setError("Test submitted, but history could not be saved."));

    const wrongItems = review.filter(r => !r.isCorrect && isMCQ(r))
      .map(r => ({ question_id: r.id, question: r.question, selected: r.selected || null,
        correct: r.correct, options: r.options || null, explanation: r.explanation || "", section: r.section || "", marks: r.marks }));
    if (wrongItems.length) saveWrongAnswers({ username: user?.username, grade, mode, subject, chapter, wrongAnswers: wrongItems }).catch(() => {});

    setTimeout(() => window.scrollTo({ top: 0, behavior: "smooth" }), 100);
  }

  // ── Navigator helper ──────────────────────────────────────────────────────────
  function navigateTo(idx) {
    setActiveQuestion(idx);
    const ref = questionRefs.current[idx];
    if (ref) ref.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function isAnswered(q, _idx) {
    if (isMCQ(q)) return !!answers[q.id];
    return !!(writtenAnswers[q.id] || "").trim();
  }

  // ── Render ────────────────────────────────────────────────────────────────────
  return (
    <div className="mock-test-page premium-page premium-mock-page">

      {/* ── PHASE: SETUP ── */}
      {phase === PHASE_SETUP && (
        <>
          <section className="premium-section premium-mock-hero">
            <div className="premium-header">
              <p className="eyebrow">Exam Practice</p>
              <h2>🧪 Mock Test Studio</h2>
              <p>Generate exam-style practice tests, track your answers, review mistakes, and build confidence.</p>
            </div>

            {/* Exam format selector — shown prominently at the top */}
            <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginTop: 16 }}>
              {[
                { fmt: FORMAT_MCQ,     icon: "🅰️", label: "MCQ Practice",     sub: "Multiple choice — Free for all",        free: true  },
                { fmt: FORMAT_WRITTEN, icon: "✍️", label: "Written Practice",  sub: "Short & long answers — AI step-marking", free: false },
                { fmt: FORMAT_MIXED,   icon: "📋", label: "Mixed (CBSE style)", sub: "MCQ + Written like real CBSE paper",     free: false },
              ].map(({ fmt, icon, label, sub, free }) => {
                const locked = !free && !isPaid && user?.role !== "admin" && !isAllAccessTestUser(user);
                const selected = questionFormat === fmt;
                return (
                  <button
                    key={fmt}
                    type="button"
                    onClick={() => { if (!locked) { setQuestionFormat(fmt); setError(""); } else { setError("✍️ Written and Mixed modes require a paid subscription."); } }}
                    style={{
                      flex: "1 1 180px", padding: "14px 16px", borderRadius: 12, cursor: "pointer",
                      border: selected ? "2px solid #6366f1" : "1.5px solid #e5e7eb",
                      background: selected ? "rgba(99,102,241,0.07)" : "#fff",
                      textAlign: "left", fontFamily: "inherit", opacity: locked ? 0.75 : 1,
                      transition: "all 0.15s",
                    }}
                  >
                    <div style={{ fontSize: "1.3rem" }}>{icon} {locked && "🔒"}</div>
                    <div style={{ fontWeight: 700, marginTop: 4, color: selected ? "#4f46e5" : "#111" }}>{label}</div>
                    <div style={{ fontSize: "0.75rem", color: "#6b7280", marginTop: 2 }}>{sub}</div>
                    {!free && !locked && <div style={{ fontSize: "0.7rem", color: "#16a34a", marginTop: 2, fontWeight: 600 }}>✓ Premium unlocked</div>}
                    {locked && <div style={{ fontSize: "0.7rem", color: "#9333ea", marginTop: 2, fontWeight: 600 }}>Upgrade to unlock →</div>}
                  </button>
                );
              })}
            </div>
          </section>

          <section className="premium-section premium-mock-setup">
            <div className="premium-header">
              <h3>Test Setup</h3>
              <p>Customize the paper before generating your mock test.</p>
            </div>

            <div className="form-grid premium-mock-form-grid">
              <label>Grade
                <select value={grade} onChange={e => handleGradeChange(e.target.value)}>
                  {grades.map(g => <option key={g}>{g}</option>)}
                </select>
              </label>
              <label>Mode
                <select value={mode} onChange={e => handleModeChange(e.target.value)}>
                  {modes.map(m => <option key={m}>{m}</option>)}
                </select>
              </label>
              <label>Subject
                <select value={subject} onChange={e => handleSubjectChange(e.target.value)} disabled={!subjects.length}>
                  {!subjects.length ? <option value="">No access</option> : subjects.map(s => <option key={s}>{s}</option>)}
                </select>
              </label>
              <label>Chapter / Section
                <select value={chapter} onChange={e => setChapter(e.target.value)}>
                  {chapters.map(c => <option key={c}>{c}</option>)}
                </select>
              </label>
              <label>Test Type
                <select value={mockType} onChange={e => setMockType(e.target.value)}>
                  <option>CBSE Exam Mock Test</option>
                  <option>CBSE Chapter Test</option>
                </select>
              </label>
              <label>Exam Type
                <select value={examType} onChange={e => setExamType(e.target.value)}>
                  <option>Class Test</option>
                  <option>Mid Term</option>
                  <option>Annual Exam</option>
                </select>
              </label>
              <label>Difficulty
                <select value={difficulty} onChange={e => setDifficulty(e.target.value)}>
                  <option>Easy</option><option>Medium</option><option>Hard</option><option>Olympiad HOTS</option>
                </select>
              </label>
              <label>Questions <small style={{ color: "var(--muted)" }}>(max 100)</small>
                <input type="number" min="5" max="100" value={questionCount}
                  onChange={e => setQuestionCount(Math.min(100, Math.max(1, Number(e.target.value))))} />
              </label>
              <label>Duration (minutes) <small style={{ color: "var(--muted)" }}>(max 180)</small>
                <input type="number" min="5" max="180" step="5" value={durationMinutes}
                  onChange={e => setDurationMinutes(Math.min(180, Math.max(5, Number(e.target.value))))} />
              </label>
              <label>Negative Marks
                <select value={negativeMarks} onChange={e => setNegativeMarks(Number(e.target.value))}>
                  <option value="0">0</option><option value="0.25">0.25</option>
                  <option value="0.5">0.5</option><option value="1">1</option>
                </select>
              </label>
            </div>

            <div className="checkbox-row premium-test-options">
              <label><input type="checkbox" checked={timerEnabled} onChange={e => setTimerEnabled(e.target.checked)} /> Enable Timer</label>
              <label><input type="checkbox" checked={negativeMarking} onChange={e => setNegativeMarking(e.target.checked)} /> Enable Negative Marking</label>
            </div>

            {isFreeUser && (
              <div style={{ marginBottom: 10, padding: "8px 12px", borderRadius: 8,
                background: dailyLimitReached ? "rgba(239,68,68,.08)" : "rgba(99,102,241,.07)",
                border: `1px solid ${dailyLimitReached ? "rgba(239,68,68,.3)" : "rgba(167,139,250,.25)"}`,
                display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                <span style={{ fontSize: ".82rem", color: dailyLimitReached ? "#f87171" : "#a78bfa", fontWeight: 600 }}>
                  {dailyLimitReached ? `🚫 Daily limit reached (${FREE_DAILY_MOCK_LIMIT}/${FREE_DAILY_MOCK_LIMIT} today)`
                    : `📊 ${todayMockCount}/${FREE_DAILY_MOCK_LIMIT} free mock tests used today`}
                </span>
                {dailyLimitReached && (
                  <div style={{ display: "flex", gap: 8 }}>
                    <button type="button" onClick={() => setActivePage?.("subscriptionPlans")}
                      style={{ padding: "4px 12px", borderRadius: 7, border: "none", background: "linear-gradient(135deg,#6366f1,#8b5cf6)", color: "#fff", fontWeight: 700, fontSize: ".76rem", cursor: "pointer", fontFamily: "inherit" }}>
                      🚀 Upgrade for unlimited
                    </button>
                  </div>
                )}
              </div>
            )}

            <button className="primary-btn premium-mock-generate-btn"
              onClick={handleGenerateMockTest} disabled={loading || dailyLimitReached}>
              {dailyLimitReached ? "🚫 Daily Limit Reached" : loading ? "Generating..." : "✨ Generate Mock Test"}
            </button>
            {error && <div className="error-box">{error}</div>}
          </section>
        </>
      )}

      {/* ── PHASE: EXAM ── */}
      {phase === PHASE_EXAM && questions.length > 0 && (
        <div ref={examTopRef}>
          {/* Sticky exam header */}
          <div style={{
            position: "sticky", top: 0, zIndex: 100,
            background: "var(--bg, #fff)", borderBottom: "1px solid var(--border, #e5e7eb)",
            padding: "10px 20px", display: "flex", alignItems: "center",
            justifyContent: "space-between", flexWrap: "wrap", gap: 10,
          }}>
            <div>
              <strong style={{ fontSize: "0.9rem" }}>{subject} — {chapter.slice(0, 50)}</strong>
              <span style={{ marginLeft: 12, fontSize: "0.8rem", color: "var(--muted)" }}>
                {answeredCount}/{questions.length} answered • {progressPercent}%
              </span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              {timerEnabled && (
                <div style={{
                  fontWeight: 700, fontSize: "1rem", padding: "4px 14px", borderRadius: 8,
                  background: secondsLeft < 120 ? "#fee2e2" : "rgba(99,102,241,.1)",
                  color: secondsLeft < 120 ? "#dc2626" : "#4f46e5",
                }}>
                  ⏱ {formatTime(secondsLeft)}
                </div>
              )}
              <button className="primary-btn" style={{ padding: "6px 18px" }} onClick={handleSubmitTest}>
                Submit Test
              </button>
            </div>
          </div>

          {timerEnabled && secondsLeft === 0 && (
            <div className="error-box" style={{ margin: "12px 0" }}>⏰ Time is over. Please submit your test.</div>
          )}

          {/* Question Navigator */}
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, padding: "14px 0 8px" }}>
            {questions.map((q, idx) => {
              const done = isAnswered(q, idx);
              return (
                <button key={q.id} type="button" onClick={() => navigateTo(idx)}
                  style={{
                    width: 36, height: 36, borderRadius: 8, border: "none", cursor: "pointer",
                    fontWeight: 700, fontSize: "0.8rem", fontFamily: "inherit",
                    background: activeQuestion === idx ? "#6366f1" : done ? "#16a34a" : "#e5e7eb",
                    color: activeQuestion === idx || done ? "#fff" : "#374151",
                  }}>
                  {idx + 1}
                </button>
              );
            })}
          </div>
          <div style={{ fontSize: "0.72rem", color: "var(--muted)", marginBottom: 12 }}>
            <span style={{ display: "inline-block", width: 12, height: 12, borderRadius: 3, background: "#16a34a", marginRight: 4, verticalAlign: "middle" }} />Answered
            <span style={{ display: "inline-block", width: 12, height: 12, borderRadius: 3, background: "#e5e7eb", marginLeft: 10, marginRight: 4, verticalAlign: "middle" }} />Unanswered
            <span style={{ display: "inline-block", width: 12, height: 12, borderRadius: 3, background: "#6366f1", marginLeft: 10, marginRight: 4, verticalAlign: "middle" }} />Current
          </div>

          {/* Questions */}
          <div className="premium-question-list">
            {questions.map((q, idx) => (
              <div key={q.id} ref={el => { questionRefs.current[idx] = el; }}
                className="question-card premium-question-card"
                style={{ scrollMarginTop: 80 }}>
                <div className="premium-question-header">
                  <h4>Q{idx + 1}. <MathText text={q.question} /></h4>
                  <span>{q.marks} mark{Number(q.marks || 1) > 1 ? "s" : ""}</span>
                </div>
                {q.section && <p className="muted">Section: {q.section}</p>}

                {/* MCQ options */}
                {isMCQ(q) && (
                  <div className="premium-option-list">
                    {Object.entries(q.options || {}).map(([key, val]) => (
                      <label key={key} className={answers[q.id] === key ? "option-row premium-option-row selected" : "option-row premium-option-row"}>
                        <input type="radio" name={`q-${q.id}`} checked={answers[q.id] === key}
                          onChange={() => handleAnswerChange(q.id, key)} />
                        <span><strong>{key}.</strong> <MathText text={val} /></span>
                      </label>
                    ))}
                  </div>
                )}

                {/* Written answer */}
                {isWritten(q) && (
                  <div style={{ marginTop: 12 }}>
                    {q.marks && <div style={{ fontSize: "0.78rem", color: "#6b7280", marginBottom: 6 }}>
                      {q.question_type === "written_long" ? "Long answer" : "Short answer"} • {q.marks} marks
                    </div>}
                    <textarea rows={q.question_type === "written_long" ? 8 : 4}
                      value={writtenAnswers[q.id] || ""}
                      placeholder="Write your answer here..."
                      onChange={e => setWrittenAnswers(p => ({ ...p, [q.id]: e.target.value }))}
                      style={{ width: "100%", borderRadius: 8, border: "1px solid #d1d5db", padding: "10px 12px", fontFamily: "inherit", fontSize: "0.9rem", resize: "vertical" }}
                    />
                    <button type="button" className="secondary-btn" style={{ marginTop: 6, fontSize: "0.82rem" }}
                      disabled={!(writtenAnswers[q.id] || "").trim() || writtenLoading[q.id]}
                      onClick={() => handleEvaluateWritten(q)}>
                      {writtenLoading[q.id] ? "Evaluating..." : "✨ Get AI Feedback"}
                    </button>
                    {writtenEvals[q.id] && (
                      <div style={{ marginTop: 8, padding: "10px 12px", borderRadius: 8, background: "#f0fdf4", border: "1px solid #86efac" }}>
                        <strong style={{ fontSize: "0.8rem", color: "#15803d" }}>AI Feedback</strong>
                        <p style={{ margin: "4px 0 0", fontSize: "0.85rem", color: "#166534", lineHeight: 1.6 }}>
                          {writtenEvals[q.id]?.evaluation || "Evaluation received."}
                        </p>
                        {writtenEvals[q.id]?.score != null && (
                          <div style={{ marginTop: 4, fontSize: "0.78rem", fontWeight: 700, color: "#16a34a" }}>
                            Score: {writtenEvals[q.id].score}/10
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>

          <button className="primary-btn premium-submit-test-btn" onClick={handleSubmitTest}>
            ✅ Submit Test
          </button>
        </div>
      )}

      {/* ── PHASE: RESULT ── */}
      {phase === PHASE_RESULT && results && (
        <section className="premium-section premium-results-section">
          <div className="premium-results-hero">
            <div>
              <p className="eyebrow">Results</p>
              <h2>{perf(results.percentage).title}</h2>
              <p>{perf(results.percentage).msg}</p>
            </div>
            <div className="premium-score-orb">
              <strong>{results.percentage}%</strong>
              <span>Score</span>
            </div>
          </div>

          <div className="result-grid premium-result-grid">
            <div className="premium-card premium-glow-card glow-blue"><strong>Score</strong><p>{results.finalScore} / {results.maxScore}</p></div>
            <div className="premium-card premium-glow-card glow-green"><strong>Percentage</strong><p>{results.percentage}%</p></div>
            <div className="premium-card premium-glow-card glow-red"><strong>Wrong (MCQ)</strong><p>{results.wrongCount}</p></div>
            <div className="premium-card premium-glow-card glow-purple"><strong>Penalty</strong><p>-{results.penalty}</p></div>
            {results.timeTakenSeconds != null && (
              <div className="premium-card" style={{ borderTop: "3px solid #0891b2" }}>
                <strong style={{ color: "var(--muted)" }}>⏱️ Time Taken</strong>
                <p style={{ color: "#0891b2" }}>
                  {results.timeTakenSeconds >= 60
                    ? `${Math.floor(results.timeTakenSeconds / 60)}m ${results.timeTakenSeconds % 60}s`
                    : `${results.timeTakenSeconds}s`}
                </p>
              </div>
            )}
          </div>

          <div className="info-box premium-next-step-box">{rec(results.percentage)}</div>

          {results.wrongCount > 0 && (
            <div style={{ background: "rgba(239,120,50,0.1)", border: "1px solid rgba(239,120,50,0.35)",
              borderRadius: 12, padding: "16px 20px", marginBottom: 24, display: "flex", alignItems: "center", gap: 16, flexWrap: "wrap" }}>
              <span style={{ fontSize: "1.5rem" }}>🔁</span>
              <div style={{ flex: 1, minWidth: 200 }}>
                <strong style={{ color: "#fb923c" }}>{results.wrongCount} question{results.wrongCount > 1 ? "s" : ""} need revision</strong>
                <p style={{ margin: "4px 0 0", fontSize: "0.85rem", color: "var(--text, #e5e7eb)" }}>
                  Study the explanations below, then take a fresh retest on <strong style={{ color: "#fb923c" }}>{chapter}</strong>.
                </p>
              </div>
              <button className="primary-btn" style={{ background: "#ea580c", border: "none" }}
                onClick={() => { clearTest(); window.scrollTo({ top: 0, behavior: "smooth" }); }}>
                🔁 Take Retest
              </button>
            </div>
          )}

          <div className="premium-header"><h3>📘 Answer Review</h3></div>

          <div className="premium-review-list">
            {results.review.map((r, idx) => (
              <div key={r.id} className={r.isCorrect ? "review-card correct premium-review-card" : "review-card wrong premium-review-card"}>
                <h4>Q{idx + 1}. {r.isCorrect ? "✅ Correct" : "❌ Incorrect"}</h4>
                <p><MathText text={r.question} /></p>

                {/* MCQ review */}
                {r.question_type === "mcq" && r.options && (
                  <div style={{ margin: "10px 0", display: "flex", flexDirection: "column", gap: 6 }}>
                    {Object.entries(r.options).map(([key, val]) => {
                      const isCor = key === r.correct, isSel = key === r.selected;
                      const bg    = isCor ? "rgba(34,197,94,0.15)" : isSel ? "rgba(239,68,68,0.12)" : "transparent";
                      const border = isCor ? "1.5px solid #16a34a" : isSel ? "1.5px solid #ef4444" : "1px solid #d1d5db";
                      const color  = isCor ? "#16a34a" : isSel ? "#ef4444" : "var(--text, #e5e7eb)";
                      return (
                        <div key={key} style={{ padding: "6px 10px", borderRadius: 6, background: bg, border, color, fontSize: "0.88rem" }}>
                          <strong>{key}.</strong> <MathText text={val} />
                          {isCor && <span style={{ marginLeft: 8, fontWeight: 700 }}>✓ Correct</span>}
                          {isSel && !isCor && <span style={{ marginLeft: 8, fontWeight: 700 }}>✗ Your answer</span>}
                        </div>
                      );
                    })}
                  </div>
                )}
                {r.question_type === "mcq" && !r.isCorrect && r.explanation && (
                  <div style={{ background: "rgba(99,102,241,0.1)", border: "1px solid rgba(99,102,241,0.3)", borderRadius: 8, padding: "12px 14px", marginTop: 8 }}>
                    <strong style={{ color: "#818cf8", fontSize: "0.85rem", display: "block", marginBottom: 4 }}>📖 Explanation</strong>
                    <p style={{ margin: 0, fontSize: "0.88rem", lineHeight: 1.6, color: "var(--text, #e5e7eb)" }}><MathText text={r.explanation} /></p>
                  </div>
                )}

                {/* Written review */}
                {r.question_type !== "mcq" && (
                  <div style={{ marginTop: 8 }}>
                    <div style={{ background: "rgba(255,255,255,0.05)", border: "1px solid var(--border,#374151)", borderRadius: 8, padding: "10px 12px", marginBottom: 8 }}>
                      <strong style={{ fontSize: "0.8rem", color: "var(--muted,#9ca3af)" }}>Your answer:</strong>
                      <p style={{ margin: "4px 0 0", fontSize: "0.88rem", color: "var(--text,#e5e7eb)", whiteSpace: "pre-wrap" }}>{r.wrAns || "(no answer)"}</p>
                    </div>
                    {r.evaluation && (
                      <div style={{ background: "#f0fdf4", border: "1px solid #86efac", borderRadius: 8, padding: "10px 12px", marginBottom: 8 }}>
                        <strong style={{ fontSize: "0.8rem", color: "#15803d" }}>AI Feedback:</strong>
                        <p style={{ margin: "4px 0 0", fontSize: "0.85rem", color: "#166534", lineHeight: 1.6 }}>{r.evaluation}</p>
                        {r.aiScore != null && <div style={{ marginTop: 4, fontSize: "0.78rem", fontWeight: 700, color: "#16a34a" }}>Score: {r.aiScore}/10 → {r.earnedMarks}/{r.marks} marks</div>}
                      </div>
                    )}
                    {r.modelAnswer && (
                      <div style={{ background: "rgba(99,102,241,0.08)", border: "1px solid rgba(99,102,241,0.25)", borderRadius: 8, padding: "10px 12px" }}>
                        <strong style={{ fontSize: "0.8rem", color: "#818cf8" }}>Model answer:</strong>
                        <p style={{ margin: "4px 0 0", fontSize: "0.85rem", color: "var(--text,#e5e7eb)", lineHeight: 1.6 }}>{r.modelAnswer}</p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>

          <button className="secondary-btn" style={{ marginTop: 20 }}
            onClick={() => { clearTest(); window.scrollTo({ top: 0, behavior: "smooth" }); }}>
            🔄 Take Another Test
          </button>
        </section>
      )}

    </div>
  );
}

export default MockTestPage;
