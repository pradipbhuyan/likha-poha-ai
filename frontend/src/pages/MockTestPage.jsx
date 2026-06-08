import { useEffect, useState } from "react";
import { getSyllabus } from "../api/syllabus";
import { generateMockTest } from "../api/mockTest";
import { saveTestHistory } from "../api/analytics";
import { logStudentActivity } from "../api/profile";
import {
  getDefaultSelection,
  getUserBoard,
  getUserGrade,
  getVisibleGrades,
} from "../utils/syllabusDefaults";
import { filterAllowedSubjects, isSchoolBoardMode } from "../utils/subjectAccess";
import { isAllAccessTestUser } from "../utils/testAccounts";

function MockTestPage({ user }) {
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
  const modes = Object.keys(syllabusData[grade]);
  
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
  }

  async function handleGenerateMockTest() {
    /** Validate access and request a fresh mock test for the selected topic and settings. */
    setLoading(true);

    if (
      isSchoolBoardMode(mode) &&
      !isAllAccessTestUser(user) &&
      !user.accessCbse
    ) {
      setError(
        `You do not have access to ${mode} mock tests.`
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
      });

      if (!response.success) {
        setError(response.message || "Could not generate mock test");
        return;
      }

      setQuestions(response.questions || []);

      if (timerEnabled) {
        setSecondsLeft(durationMinutes * 60);
      }
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
      submittedAt: new Date().toISOString(),
      review,
    };

    setResults(resultPayload);

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
            Subject / Olympiad
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
              <option>SOF Olympiad Mock Test</option>
            </select>
          </label>

          <label>
            Exam Type
            <select
              value={examType}
              onChange={(e) => setExamType(e.target.value)}
              disabled={mockType === "SOF Olympiad Mock Test"}
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
            Questions
            <input
              type="number"
              min="5"
              max="30"
              value={questionCount}
              onChange={(e) => setQuestionCount(e.target.value)}
            />
          </label>

          <label>
            Test Duration Minutes
            <input
              type="number"
              min="5"
              max="120"
              value={durationMinutes}
              onChange={(e) => setDurationMinutes(Number(e.target.value))}
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

        <button
          className="primary-btn premium-mock-generate-btn"
          onClick={handleGenerateMockTest}
          disabled={loading}
        >
          {loading ? "Generating..." : "✨ Generate Mock Test"}
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
                    Q{q.id}. {q.question}
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
                        <strong>{key}.</strong> {value}
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

                <p>{r.question}</p>

                <p>
                  Your Answer:{" "}
                  <strong>
                    {r.selected || "Not answered"}
                    {r.selected ? `. ${r.options?.[r.selected] || ""}` : ""}
                  </strong>
                </p>

                <p>
                  Correct Answer:{" "}
                  <strong>
                    {r.correct}. {r.options?.[r.correct]}
                  </strong>
                </p>

                <p>Explanation: {r.explanation}</p>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

export default MockTestPage;
