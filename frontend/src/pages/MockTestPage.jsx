import { useEffect, useState } from "react";
import { getSyllabus } from "../api/syllabus";
import { generateMockTest } from "../api/mockTest";
import { saveTestHistory, saveWrongAnswers } from "../api/analytics";
import { logStudentActivity } from "../api/profile";
import {
  getDefaultSelection,
  getUserBoard,
  getUserGrade,
  getVisibleGrades,
} from "../utils/syllabusDefaults";
import { filterAllowedSubjects, isSchoolBoardMode } from "../utils/subjectAccess";
import { isAllAccessTestUser } from "../utils/testAccounts";
import { hasPaidAccess } from "../utils/resolveSubscription";

/**
 * Renders text that may contain caret-notation exponents (x^2, a^{n+1}).
 * Splits on exponent patterns and renders <sup> via React — no innerHTML needed.
 */
function MathText({ text }) {
  const str = String(text || "");
  // Split on ^{expr} or ^digits — keep delimiters so we know what was matched
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

// ── Daily mock test limit for free-tier students ─────────────────────────────
const FREE_DAILY_MOCK_LIMIT = 5;

function getDailyMockKey(username) {
  const today = new Date().toISOString().slice(0, 10); // YYYY-MM-DD
  return `mock_daily_${username}_${today}`;
}

function getDailyMockCount(username) {
  try { return parseInt(localStorage.getItem(getDailyMockKey(username)) || "0", 10); } catch { return 0; }
}

function incrementDailyMockCount(username) {
  try {
    const key = getDailyMockKey(username);
    const count = parseInt(localStorage.getItem(key) || "0", 10);
    localStorage.setItem(key, String(count + 1));
  } catch { /* non-critical */ }
}

function MockTestPage({ user, setActivePage }) {
  /** Builds, runs, scores, and stores CBSE/SOF mock tests for the signed-in student. */
  function getPerformanceSummary(percentage) {
    /** Choose summary text based on the submitted test percentage. */
    if (percentage >= 90) {
      return {
        title: "🌟 Olympiad Ready",
        message:
          "Outstanding performance! You have mastered this chapter extremely well.",
      };
    }

    if (percentage >= 75) {
      return {
        title: "👏 Strong Foundation",
        message:
          "Very good work! Your concepts are strong and improving steadily.",
      };
    }

    if (percentage >= 60) {
      return {
        title: "👍 Good Progress",
        message:
          "You are improving well. A little more practice can boost your score further.",
      };
    }

    return {
      title: "💪 Revision Needed",
      message:
        "Keep practicing. Revising core concepts and solving more questions will help.",
    };
  }

  const [syllabusData, setSyllabusData] = useState(null);

  const [grade, setGrade] = useState("Grade 9");
  const [mode, setMode] = useState("CBSE");
  const [subject, setSubject] = useState("");
  const [chapter, setChapter] = useState("");

  const [mockType, setMockType] = useState("CBSE Exam Mock Test");
  const [examType, setExamType] = useState("Class Test");
  const [difficulty, setDifficulty] = useState("Medium");
  const [questionCount, setQuestionCount] = useState(5);

  const [timerEnabled, setTimerEnabled] = useState(true);
  const [durationMinutes, setDurationMinutes] = useState(30);
  const [secondsLeft, setSecondsLeft] = useState(0);

  const [negativeMarking, setNegativeMarking] = useState(false);
  const [negativeMarks, setNegativeMarks] = useState(0.25);

  const [questions, setQuestions] = useState([]);
  const [answers, setAnswers] = useState({});
  const [results, setResults] = useState(null);
  // Track when the test starts so we can compute time taken on submit
  const [testStartedAt, setTestStartedAt] = useState(null);

  // Accumulate question bank IDs shown to this user across tests in this session.
  // Sent back to the backend as excluded_ids so the same question is never
  // repeated within the same test or the next 30 tests.
  const [excludedIds, setExcludedIds] = useState([]);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadSyllabus() {
      /** Load syllabus options and initialize the mock test topic. */
      try {
        const data = await getSyllabus();
        setSyllabusData(data.syllabus);

        const {
          grade: defaultGrade,
          mode: defaultMode,
          subject: defaultSubject,
          chapter: defaultChapter,
        } = getDefaultSelection(
          data.syllabus,
          getUserGrade(user),
          getUserBoard(user)
        );
        const defaultSubjects = Object.keys(
          data.syllabus[defaultGrade]?.[defaultMode] || {}
        );
        const allowedDefaultSubjects = filterAllowedSubjects(
          user,
          defaultSubjects,
          defaultMode
        );
        let selectedMode = defaultMode;
        let selectedSubject = allowedDefaultSubjects.includes(defaultSubject)
          ? defaultSubject
          : allowedDefaultSubjects[0] || "";

        if (!selectedSubject) {
          selectedMode =
            Object.keys(data.syllabus[defaultGrade] || {}).find((modeName) => {
              const modeSubjects = Object.keys(
                data.syllabus[defaultGrade]?.[modeName] || {}
              );
              return filterAllowedSubjects(user, modeSubjects, modeName).length > 0;
            }) || defaultMode;
          selectedSubject =
            filterAllowedSubjects(
              user,
              Object.keys(data.syllabus[defaultGrade]?.[selectedMode] || {}),
              selectedMode
            )[0] || "";
        }
        const selectedChapter =
          selectedSubject === defaultSubject
            ? defaultChapter
            : data.syllabus[defaultGrade]?.[selectedMode]?.[selectedSubject]?.[0] || "";

        setGrade(defaultGrade);
        setMode(selectedMode);
        setSubject(selectedSubject);
        setChapter(selectedChapter);
      } catch {
        setError("Could not load syllabus");
      }
    }

    loadSyllabus();
  }, []);

  useEffect(() => {
    if (!timerEnabled || secondsLeft <= 0 || results || questions.length === 0) {
      return;
    }

    const timer = setInterval(() => {
      setSecondsLeft((prev) => Math.max(0, prev - 1));
    }, 1000);

    return () => clearInterval(timer);
  }, [timerEnabled, secondsLeft, results, questions.length]);

  if (!syllabusData) {
    return <p>Loading mock test setup...</p>;
  }

  const grades = getVisibleGrades(syllabusData, user);
  // SOF/Olympiad mode is only available for Grade 9.
  // All other grades show CBSE only.
  // To enable SOF for additional grades, add them to this list.
  const SOF_ENABLED_GRADES = ["Grade 9"];
  const modes = Object.keys(syllabusData[grade]).filter(
    m => m !== "SOF" || SOF_ENABLED_GRADES.includes(grade)
  );
  
  function getAllowedSubjects(allSubjects, selectedMode) {
    /** Enforce subscription access when showing CBSE and SOF subjects. */
    return filterAllowedSubjects(user, allSubjects, selectedMode);
  }
  
  const allSubjects = Object.keys(syllabusData[grade][mode]);
  const subjects = getAllowedSubjects(allSubjects, mode);
  const chapters = subject
    ? syllabusData[grade][mode][subject] || []
    : [];
  const requestBoard = mode === "SOF" ? getUserBoard(user) : mode;

  const answeredCount = Object.keys(answers).length;
  const progressPercent = questions.length
    ? Math.round((answeredCount / questions.length) * 100)
    : 0;

  function resetSelections(newGrade, newMode) {
    /** Reset subject and chapter when grade or mode changes. */
    const modeSubjects = Object.keys(syllabusData[newGrade][newMode] || {});
    const allowedModeSubjects = getAllowedSubjects(modeSubjects, newMode);
    const firstSubject = allowedModeSubjects[0] || "";
    const firstChapter = firstSubject
      ? syllabusData[newGrade][newMode][firstSubject][0]
      : "";

    setSubject(firstSubject);
    setChapter(firstChapter);
  }

  function handleGradeChange(value) {
    /** Switch grade, reset dependent selections, and clear any generated test. */
    const gradeModes = Object.keys(syllabusData[value]);
    const newMode =
      gradeModes.find((modeName) => {
        const modeSubjects = Object.keys(syllabusData[value][modeName] || {});
        return getAllowedSubjects(modeSubjects, modeName).length > 0;
      }) || gradeModes[0];

    setGrade(value);
    setMode(newMode);
    resetSelections(value, newMode);
    setError("");
    clearTest();
  }

  function handleModeChange(value) {
    /** Switch mode only when at least one subject is available to the student. */
    const allModeSubjects = Object.keys(
      syllabusData[grade][value]
    );
  
    const allowedModeSubjects =
      getAllowedSubjects(
        allModeSubjects,
        value
      );
  
    if (allowedModeSubjects.length === 0) {
      setMode(value);
      setSubject("");
      setChapter("");
      setError(
        `You do not have access to ${value} mock tests.`
      );
      clearTest();
      return;
    }
  
    const firstSubject = allowedModeSubjects[0];
    const firstChapter =
      syllabusData[grade][value][firstSubject]?.[0] || "";
  
    setError("");
    setMode(value);
    setSubject(firstSubject);
    setChapter(firstChapter);
  
    clearTest();
  }

  function handleSubjectChange(value) {
    /** Change subject, default to its first chapter, and clear stale test state. */
    setSubject(value);
    setChapter(syllabusData[grade][mode][value][0]);
    clearTest();
  }

  function clearTest() {
    /** Remove generated questions, answers, results, and active timer. */
    setQuestions([]);
    setAnswers({});
    setResults(null);
    setSecondsLeft(0);
    setTestStartedAt(null);
  }

  // ── Compute free-tier daily limit state ──────────────────────────────────
  // SECURITY FIX: parentId alone does NOT indicate paid access.
  // A student created by a free-plan parent has parentId set but accessCbse=false.
  // Use hasPaidAccess() which correctly checks accessCbse + subscriptionExpiresAt.
  const isFreeUser = user?.role === "student" && !hasPaidAccess(user);
  const todayMockCount = isFreeUser ? getDailyMockCount(user?.username) : 0;
  const dailyLimitReached = isFreeUser && todayMockCount >= FREE_DAILY_MOCK_LIMIT;

  async function handleGenerateMockTest() {
    /** Validate access and request a fresh mock test for the selected topic and settings. */

    // Daily limit gate for free-tier students
    if (dailyLimitReached) return;

    setLoading(true);

    // SECURITY FIX: Free-tier users (including children of free-plan parents)
    // are allowed mock tests but subject to the daily limit (enforced above).
    // Do NOT block them here — the daily limit check at the top of this function
    // handles free users. What we block here is paid users with the wrong plan
    // (e.g. a SOF-only paid user trying CBSE mock tests).
    // The old check `!user.accessCbse && !user.offerAccess && hasPaidPlan` was
    // wrong: hasPaidPlan=false for free users → the entire condition was false
    // → free users were never blocked even if logic intended to gate them.
    if (
      isSchoolBoardMode(mode) &&
      user?.role !== "admin" &&
      !isAllAccessTestUser(user) &&
      !isFreeUser &&      // free users are handled by daily limit, not this gate
      !user.accessCbse &&
      !user.offerAccess
    ) {
      setError(
        `You do not have access to ${mode} mock tests. Please check your subscription.`
      );
      setLoading(false);
      return;
    }

    if (isSchoolBoardMode(mode) && subjects.length === 0) {
      setError(`You do not have access to this ${mode} subject.`);
      setLoading(false);
      return;
    }
    
    if (
      mode === "SOF" &&
      user?.role !== "admin" &&
      !isAllAccessTestUser(user) &&
      !(
        user.accessSofScience ||
        user.accessSofMaths ||
        user.accessSofEnglish
      )
    ) {
      setError(
        "You do not have access to SOF mock tests."
      );
      setLoading(false);
      return;
    }

    setError("");
    setResults(null);
    setAnswers({});

    try {
      const response = await generateMockTest({
        grade,
        mode,
        board: requestBoard,
        subject,
        chapter,
        mock_type: mockType,
        difficulty,
        question_count: Number(questionCount),
        exam_type: examType,
        excluded_ids: excludedIds,   // prevent repeating recently shown questions
      });

      if (!response.success) {
        setError(response.message || "Could not generate mock test");
        return;
      }

      const newQuestions = response.questions || [];
      setQuestions(newQuestions);
      setTestStartedAt(Date.now()); // record start time

      // Accumulate db_ids for exclusion in future tests (persistent across tests in session)
      const newIds = newQuestions.map(q => q.db_id).filter(Boolean);
      if (newIds.length > 0) {
        setExcludedIds(prev => {
          const merged = [...new Set([...prev, ...newIds])];
          // Keep at most 30 tests × 100 questions = 3000 IDs to avoid huge payloads
          return merged.slice(-3000);
        });
      }

      if (timerEnabled) {
        setSecondsLeft(durationMinutes * 60);
      }

      // Increment free-tier daily counter after successful generation
      if (isFreeUser) incrementDailyMockCount(user?.username);
    } catch {
      setError("Could not generate mock test. Check backend.");
    } finally {
      setLoading(false);
    }
  }

  function handleAnswerChange(questionId, optionKey) {
    /** Store the selected answer for one mock-test question. */
    setAnswers((prev) => ({
      ...prev,
      [questionId]: optionKey,
    }));
  }

  function handleSubmitTest() {
    /** Score the test, apply optional negative marking, and persist history/activity. */
    let rawScore = 0;
    let maxScore = 0;
    let wrongCount = 0;

    const review = questions.map((q) => {
      const selected = answers[q.id];
      const correct = q.answer;
      const marks = Number(q.marks || 1);
      const isCorrect = selected === correct;

      maxScore += marks;

      if (isCorrect) {
        rawScore += marks;
      } else {
        wrongCount += 1;
      }

      return {
        id: q.id,
        section: q.section,
        question: q.question,
        options: q.options,
        selected,
        correct,
        isCorrect,
        marks,
        explanation: q.explanation,
      };
    });

    const penalty = negativeMarking ? wrongCount * Number(negativeMarks) : 0;
    const finalScore = Math.max(0, rawScore - penalty);
    const percentage = maxScore
      ? Math.round((finalScore / maxScore) * 10000) / 100
      : 0;

    // Calculate time taken (seconds) — null if start was never recorded
    const timeTakenSeconds = testStartedAt
      ? Math.round((Date.now() - testStartedAt) / 1000)
      : null;

    const resultPayload = {
      username: user?.username,
      grade,
      mode,
      subject,
      chapter,
      mockType,
      examType,
      difficulty,
      rawScore,
      finalScore,
      maxScore,
      wrongCount,
      penalty,
      percentage,
      timeTakenSeconds,
      submittedAt: new Date().toISOString(),
      review,
    };

    setResults(resultPayload);

    // Persist wrong answers for weak-chapter tracking (best-effort, non-blocking)
    const wrongItems = review
      .filter((r) => !r.isCorrect)
      .map((r) => ({
        question_id: r.id,
        question: r.question,
        selected: r.selected || null,
        correct: r.correct,
        options: r.options || null,
        explanation: r.explanation || "",
        section: r.section || "",
        marks: r.marks,
      }));

    saveTestHistory(resultPayload)
      .then(() =>
        logStudentActivity({
          username: user.username,
          activity_type: "mock_test_taken",
        })
      )
      .catch(() => {
        setError("Test submitted, but history/activity could not be saved.");
      });

    if (wrongItems.length > 0) {
      saveWrongAnswers({
        username: user?.username,
        grade,
        mode,
        subject,
        chapter,
        wrongAnswers: wrongItems,
      }).catch(() => {}); // silent — wrong-answer tracking is best-effort
    }

    setSecondsLeft(0);
  }

  function formatTime(totalSeconds) {
    /** Format the countdown timer as mm:ss. */
    const mins = Math.floor(totalSeconds / 60);
    const secs = totalSeconds % 60;
    return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
  }

  function getRecommendation(percentage) {
    /** Suggest the next difficulty level based on submitted performance. */
    if (percentage >= 85) return "Recommended next difficulty: Hard / Olympiad HOTS";
    if (percentage >= 60) return "Recommended next difficulty: Medium";
    return "Recommended next difficulty: Easy with revision";
  }

  return (
    <div className="mock-test-page premium-page premium-mock-page">
      <section className="premium-section premium-mock-hero">
        <div className="premium-header">
          <p className="eyebrow">Exam Practice</p>
          <h2>🧪 Mock Test Studio</h2>
          <p>
            Generate exam-style practice tests, track your answers, review
            mistakes, and build confidence for CBSE and SOF preparation.
          </p>
        </div>

        <div className="premium-mock-hero-card">
          <span>🎯</span>
          <div>
            <strong>{difficulty}</strong>
            <p>
              {mockType} • {questionCount} questions • {durationMinutes} minutes
            </p>
          </div>
        </div>
      </section>

      <section className="premium-section premium-mock-setup">
        <div className="premium-header">
          <h3>Test Setup</h3>
          <p>Customize the paper before generating your mock test.</p>
        </div>

        <div className="form-grid premium-mock-form-grid">
          <label>
            Grade
            <select
              value={grade}
              onChange={(e) => handleGradeChange(e.target.value)}
            >
              {grades.map((g) => (
                <option key={g}>{g}</option>
              ))}
            </select>
          </label>

          <label>
            Mode
            <select
              value={mode}
              onChange={(e) => handleModeChange(e.target.value)}
            >
              {modes.map((m) => (
                <option key={m}>{m}</option>
              ))}
            </select>
          </label>

          <label>
            Subject
            <select
              value={subject}
              onChange={(e) => handleSubjectChange(e.target.value)}
              disabled={subjects.length === 0}
            >
              {subjects.length === 0 ? (
                <option value="">No access available</option>
              ) : (
                subjects.map((s) => <option key={s}>{s}</option>)
              )}
            </select>
          </label>

          <label>
            Chapter / Section
            <select
              value={chapter}
              onChange={(e) => setChapter(e.target.value)}
            >
              {chapters.map((c) => (
                <option key={c}>{c}</option>
              ))}
            </select>
          </label>

          <label>
            Test Type
            <select
              value={mockType}
              onChange={(e) => setMockType(e.target.value)}
            >
              <option>CBSE Exam Mock Test</option>
              <option>CBSE Chapter Test</option>
            </select>
          </label>

          <label>
            Exam Type
            <select
              value={examType}
              onChange={(e) => setExamType(e.target.value)}
              disabled={false}
            >
              <option>Class Test</option>
              <option>Mid Term</option>
              <option>Annual Exam</option>
            </select>
          </label>

          <label>
            Difficulty
            <select
              value={difficulty}
              onChange={(e) => setDifficulty(e.target.value)}
            >
              <option>Easy</option>
              <option>Medium</option>
              <option>Hard</option>
              <option>Olympiad HOTS</option>
            </select>
          </label>

          <label>
            Questions <small style={{color:"var(--muted)"}}>(max 100)</small>
            <input
              type="number"
              min="5"
              max="100"
              value={questionCount}
              onChange={(e) => setQuestionCount(Math.min(100, Math.max(1, Number(e.target.value))))}
            />
          </label>

          <label>
            Test Duration Minutes <small style={{color:"var(--muted)"}}>(max 180 = 3 hrs)</small>
            <input
              type="number"
              min="5"
              max="180"
              step="5"
              value={durationMinutes}
              onChange={(e) => setDurationMinutes(Math.min(180, Math.max(5, Number(e.target.value))))}
            />
          </label>

          <label>
            Negative Marks
            <select
              value={negativeMarks}
              onChange={(e) => setNegativeMarks(Number(e.target.value))}
            >
              <option value="0">0</option>
              <option value="0.25">0.25</option>
              <option value="0.5">0.5</option>
              <option value="1">1</option>
            </select>
          </label>
        </div>

        <div className="checkbox-row premium-test-options">
          <label>
            <input
              type="checkbox"
              checked={timerEnabled}
              onChange={(e) => setTimerEnabled(e.target.checked)}
            />
            Enable Timer
          </label>

          <label>
            <input
              type="checkbox"
              checked={negativeMarking}
              onChange={(e) => setNegativeMarking(e.target.checked)}
            />
            Enable Negative Marking
          </label>
        </div>

        {/* Daily limit banner for free-tier students */}
        {isFreeUser && (
          <div style={{ marginBottom: 10, padding: "8px 12px", borderRadius: 8,
            background: dailyLimitReached ? "rgba(239,68,68,.08)" : "rgba(99,102,241,.07)",
            border: `1px solid ${dailyLimitReached ? "rgba(239,68,68,.3)" : "rgba(167,139,250,.25)"}`,
            display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
            <span style={{ fontSize: ".82rem", color: dailyLimitReached ? "#f87171" : "#a78bfa", fontWeight: 600 }}>
              {dailyLimitReached
                ? `🚫 Daily limit reached (${FREE_DAILY_MOCK_LIMIT}/${FREE_DAILY_MOCK_LIMIT} tests used today)`
                : `📊 ${todayMockCount}/${FREE_DAILY_MOCK_LIMIT} free mock tests used today`}
            </span>
            {dailyLimitReached && (
              <div style={{ display: "flex", gap: 8 }}>
                <button type="button" onClick={() => setActivePage?.("subscriptionPlans")}
                  style={{ padding: "4px 12px", borderRadius: 7, border: "none", background: "linear-gradient(135deg,#6366f1,#8b5cf6)", color: "#fff", fontWeight: 700, fontSize: ".76rem", cursor: "pointer", fontFamily: "inherit" }}>
                  🚀 Upgrade for unlimited
                </button>
                <span style={{ fontSize: ".72rem", color: "var(--muted)", alignSelf: "center" }}>or come back tomorrow</span>
              </div>
            )}
          </div>
        )}

        <button
          className="primary-btn premium-mock-generate-btn"
          onClick={handleGenerateMockTest}
          disabled={loading || dailyLimitReached}
        >
          {dailyLimitReached
            ? "🚫 Daily Limit Reached — Come Back Tomorrow"
            : loading ? "Generating..." : "✨ Generate Mock Test"}
        </button>

        {error && <div className="error-box">{error}</div>}
      </section>

      {questions.length > 0 && !results && (
        <section className="premium-section premium-test-area">
          <div className="premium-test-sticky-header">
            <div>
              <p className="eyebrow">Live Test</p>
              <h3>Answer the questions</h3>
            </div>

            {timerEnabled && (
              <div className={secondsLeft === 0 ? "timer warning" : "timer"}>
                ⏱️ {formatTime(secondsLeft)}
              </div>
            )}
          </div>

          <div className="mock-progress-box premium-mock-progress">
            <div>
              <strong>
                {answeredCount} / {questions.length}
              </strong>{" "}
              questions answered
            </div>

            <span>{progressPercent}% complete</span>

            <progress value={answeredCount} max={questions.length} />
          </div>

          {timerEnabled && secondsLeft === 0 && (
            <div className="error-box">
              Time is over. Please submit your test.
            </div>
          )}

          <div className="premium-question-list">
            {questions.map((q) => (
              <div key={q.id} className="question-card premium-question-card">
                <div className="premium-question-header">
                  <h4>
                    Q{q.id}. <MathText text={q.question} />
                  </h4>

                  <span>
                    {q.marks} mark{Number(q.marks || 1) > 1 ? "s" : ""}
                  </span>
                </div>

                <p className="muted">Section: {q.section}</p>

                <div className="premium-option-list">
                  {Object.entries(q.options || {}).map(([key, value]) => (
                    <label
                      key={key}
                      className={
                        answers[q.id] === key
                          ? "option-row premium-option-row selected"
                          : "option-row premium-option-row"
                      }
                    >
                      <input
                        type="radio"
                        name={`question-${q.id}`}
                        checked={answers[q.id] === key}
                        onChange={() => handleAnswerChange(q.id, key)}
                      />
                      <span>
                        <strong>{key}.</strong> <MathText text={value} />
                      </span>
                    </label>
                  ))}
                </div>
              </div>
            ))}
          </div>

          <button
            className="primary-btn premium-submit-test-btn"
            onClick={handleSubmitTest}
          >
            Submit Test
          </button>
        </section>
      )}

      {results && (
        <section className="premium-section premium-results-section">
          <div className="premium-results-hero">
            <div>
              <p className="eyebrow">Results</p>
              <h2>{getPerformanceSummary(results.percentage).title}</h2>
              <p>{getPerformanceSummary(results.percentage).message}</p>
            </div>

            <div className="premium-score-orb">
              <strong>{results.percentage}%</strong>
              <span>Score</span>
            </div>
          </div>

          <div className="result-grid premium-result-grid">
            <div className="premium-card premium-glow-card glow-blue">
              <strong>Score</strong>
              <p>
                {results.finalScore} / {results.maxScore}
              </p>
            </div>

            <div className="premium-card premium-glow-card glow-green">
              <strong>Percentage</strong>
              <p>{results.percentage}%</p>
            </div>

            <div className="premium-card premium-glow-card glow-red">
              <strong>Wrong Answers</strong>
              <p>{results.wrongCount}</p>
            </div>

            <div className="premium-card premium-glow-card glow-purple">
              <strong>Penalty</strong>
              <p>-{results.penalty}</p>
            </div>

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

          <div className="info-box premium-next-step-box">
            {getRecommendation(results.percentage)}
          </div>

          <div className="premium-header">
            <h3>📘 Answer Review</h3>
            <p>
              Review each question to understand mistakes and strengthen
              concepts.
            </p>
          </div>

          {/* Retest reminder for wrong answers */}
          {results.wrongCount > 0 && (
            <div
              className="info-box premium-retest-reminder"
              style={{
                background: "linear-gradient(135deg,#fff7ed 0%,#ffedd5 100%)",
                border: "1px solid #fdba74",
                borderRadius: 12,
                padding: "16px 20px",
                marginBottom: 24,
                display: "flex",
                alignItems: "center",
                gap: 16,
                flexWrap: "wrap",
              }}
            >
              <span style={{ fontSize: "1.5rem" }}>🔁</span>
              <div style={{ flex: 1, minWidth: 200 }}>
                <strong style={{ color: "#c2410c" }}>
                  {results.wrongCount} question{results.wrongCount > 1 ? "s" : ""} need revision
                </strong>
                <p style={{ margin: "4px 0 0", fontSize: "0.85rem", color: "#78350f" }}>
                  Study the detailed explanations below carefully, then take a fresh retest on <strong>{chapter}</strong> to improve.
                </p>
              </div>
              <button
                className="primary-btn"
                style={{ background: "#ea580c", border: "none", whiteSpace: "nowrap" }}
                onClick={() => {
                  // Pre-fill the test form with the same chapter and start a retest
                  clearTest();
                  window.scrollTo({ top: 0, behavior: "smooth" });
                }}
              >
                🔁 Take Retest
              </button>
            </div>
          )}

          <div className="premium-review-list">
            {results.review.map((r) => (
              <div
                key={r.id}
                className={
                  r.isCorrect
                    ? "review-card correct premium-review-card"
                    : "review-card wrong premium-review-card"
                }
              >
                <h4>
                  Q{r.id}. {r.isCorrect ? "✅ Correct" : "❌ Incorrect"}
                </h4>

                <p><MathText text={r.question} /></p>

                {/* Show all options with highlighting */}
                {r.options && (
                  <div style={{ margin: "10px 0", display: "flex", flexDirection: "column", gap: 6 }}>
                    {Object.entries(r.options).map(([key, val]) => {
                      const isCorrect = key === r.correct;
                      const isSelected = key === r.selected;
                      let bg = "transparent";
                      let border = "1px solid #d1d5db";
                      let color = "inherit";
                      if (isCorrect) { bg = "#dcfce7"; border = "1px solid #86efac"; color = "#166534"; }
                      else if (isSelected && !isCorrect) { bg = "#fee2e2"; border = "1px solid #fca5a5"; color = "#991b1b"; }
                      return (
                        <div key={key} style={{ padding: "6px 10px", borderRadius: 6, background: bg, border, color, fontSize: "0.88rem" }}>
                          <strong>{key}.</strong> <MathText text={val} />
                          {isCorrect && <span style={{ marginLeft: 8, fontWeight: 700 }}>✓ Correct</span>}
                          {isSelected && !isCorrect && <span style={{ marginLeft: 8, fontWeight: 700 }}>✗ Your answer</span>}
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* Detailed explanation — more prominent for wrong answers */}
                {!r.isCorrect && r.explanation && (
                  <div style={{
                    background: "#eff6ff",
                    border: "1px solid #bfdbfe",
                    borderRadius: 8,
                    padding: "12px 14px",
                    marginTop: 8,
                  }}>
                    <strong style={{ color: "#1d4ed8", fontSize: "0.85rem", display: "block", marginBottom: 4 }}>
                      📖 Detailed Explanation
                    </strong>
                    <p style={{ margin: 0, fontSize: "0.88rem", lineHeight: 1.6, color: "#1e3a5f" }}>
                      <MathText text={r.explanation} />
                    </p>
                  </div>
                )}

                {r.isCorrect && r.explanation && (
                  <p style={{ fontSize: "0.85rem", color: "#6b7280", marginTop: 6 }}>
                    <em>Explanation: <MathText text={r.explanation} /></em>
                  </p>
                )}
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

export default MockTestPage;
