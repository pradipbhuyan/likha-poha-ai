import { useEffect, useState } from "react";
import { getSyllabus } from "../api/syllabus";
import { generateMockTest } from "../api/mockTest";
import { saveTestHistory } from "../api/analytics";
import { logStudentActivity } from "../api/profile";

function MockTestPage({ user }) {
  function getPerformanceSummary(percentage) {

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
      try {
        const data = await getSyllabus();
        setSyllabusData(data.syllabus);

        const defaultSubject = Object.keys(data.syllabus["Grade 9"]["CBSE"])[0];
        const defaultChapter = data.syllabus["Grade 9"]["CBSE"][defaultSubject][0];

        setSubject(defaultSubject);
        setChapter(defaultChapter);
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

  const grades = Object.keys(syllabusData);
  const modes = Object.keys(syllabusData[grade]);
  const subjects = Object.keys(syllabusData[grade][mode]);
  const chapters = syllabusData[grade][mode][subject] || [];

  function resetSelections(newGrade, newMode) {
    const firstSubject = Object.keys(syllabusData[newGrade][newMode])[0];
    const firstChapter = syllabusData[newGrade][newMode][firstSubject][0];

    setSubject(firstSubject);
    setChapter(firstChapter);
  }

  function handleGradeChange(value) {
    const newMode = Object.keys(syllabusData[value])[0];

    setGrade(value);
    setMode(newMode);
    resetSelections(value, newMode);
    clearTest();
  }

  function handleModeChange(value) {
    setMode(value);
    resetSelections(grade, value);
    clearTest();
  }

  function handleSubjectChange(value) {
    setSubject(value);
    setChapter(syllabusData[grade][mode][value][0]);
    clearTest();
  }

  function clearTest() {
    setQuestions([]);
    setAnswers({});
    setResults(null);
    setSecondsLeft(0);
  }

  async function handleGenerateMockTest() {
    setLoading(true);
    setError("");
    setResults(null);
    setAnswers({});

    try {
      const response = await generateMockTest({
        grade,
        mode,
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
    setAnswers((prev) => ({
      ...prev,
      [questionId]: optionKey,
    }));
  }

  function handleSubmitTest() {
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
    const percentage = maxScore ? Math.round((finalScore / maxScore) * 10000) / 100 : 0;

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
    const mins = Math.floor(totalSeconds / 60);
    const secs = totalSeconds % 60;
    return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
  }

  function getRecommendation(percentage) {
    if (percentage >= 85) return "Recommended next difficulty: Hard / Olympiad HOTS";
    if (percentage >= 60) return "Recommended next difficulty: Medium";
    return "Recommended next difficulty: Easy with revision";
  }

  return (
    <div className="mock-test-page">
      <h2>🧪 Mock Test</h2>

      <div className="card">
        <h3>Test Setup</h3>

        <div className="form-grid">
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
            >
              {subjects.map((s) => (
                <option key={s}>{s}</option>
              ))}
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

        <div className="checkbox-row">
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
          className="primary-btn"
          onClick={handleGenerateMockTest}
          disabled={loading}
        >
          {loading ? "Generating..." : "Generate Mock Test"}
        </button>

        {error && <div className="error-box">{error}</div>}
      </div>

      {questions.length > 0 && !results && (
        <div className="card">
          <h3>Test</h3>

          <div className="mock-progress-box">
            <div>
              <strong>
                {Object.keys(answers).length} / {questions.length}
              </strong>{" "}
              questions answered
            </div>

            <progress
              value={Object.keys(answers).length}
              max={questions.length}
            />
          </div>

          {timerEnabled && (
            <div className={secondsLeft === 0 ? "timer warning" : "timer"}>
              ⏱️ Time Remaining: {formatTime(secondsLeft)}
            </div>
          )}

          {timerEnabled && secondsLeft === 0 && (
            <div className="error-box">
              Time is over. Please submit your test.
            </div>
          )}

          {questions.map((q) => (
            <div key={q.id} className="question-card">
              <h4>
                Q{q.id}. {q.question}
              </h4>

              <p className="muted">
                Section: {q.section} | Marks: {q.marks}
              </p>

              {Object.entries(q.options || {}).map(([key, value]) => (
                <label key={key} className="option-row">
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
          ))}

          <button className="primary-btn" onClick={handleSubmitTest}>
            Submit Test
          </button>
        </div>
      )}

      {results && (
        <div className="card">
          <h3>📊 Results</h3>

          <div className="result-grid">
            <div>
              <strong>Score</strong>
              <p>
                {results.finalScore} / {results.maxScore}
              </p>
            </div>

            <div>
              <strong>Percentage</strong>
              <p>{results.percentage}%</p>
            </div>

            <div>
              <strong>Wrong Answers</strong>
              <p>{results.wrongCount}</p>
            </div>

            <div>
              <strong>Penalty</strong>
              <p>-{results.penalty}</p>
            </div>
          </div>

          <div className="info-box">
            {getRecommendation(results.percentage)}
          </div>

          <div className="info-box">
            <strong>{getPerformanceSummary(results.percentage).title}</strong>

            <p>{getPerformanceSummary(results.percentage).message}</p>
          </div>

          <h3>📘 Answer Review</h3>

          {results.review.map((r) => (
            <div
              key={r.id}
              className={
                r.isCorrect ? "review-card correct" : "review-card wrong"
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
      )}
    </div>
  );
}

export default MockTestPage;