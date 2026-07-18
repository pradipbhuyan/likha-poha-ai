import { useEffect, useState } from "react";

import { getSyllabus } from "../api/syllabus";
import { generateQuiz } from "../api/quiz";
import { logStudentActivity } from "../api/profile";
import {
  getDefaultSelection,
  getUserBoard,
  getUserGrade,
  getVisibleGrades,
} from "../utils/syllabusDefaults";

function QuizPage({ user }) {
  /** Legacy quiz page for generating and checking short practice quizzes. */
  function getQuizEncouragement(scorePercent) {
    /** Choose feedback copy based on the student's quiz score percentage. */
    if (scorePercent >= 90) {
      return "🌟 Outstanding work! You have mastered this concept very well.";
    }

    if (scorePercent >= 75) {
      return "👏 Great job! Your understanding is strong.";
    }

    if (scorePercent >= 60) {
      return "👍 Good progress! A little more practice will make you even stronger.";
    }

    return "💪 Keep practicing. Every mistake is a learning opportunity.";
  }

  const [loading, setLoading] = useState(true);
  const [syllabusData, setSyllabusData] = useState(null);
  const [error, setError] = useState("");

  const [grade, setGrade] = useState("Grade 9");
  const [mode, setMode] = useState("CBSE");
  const [subject, setSubject] = useState("");
  const [chapter, setChapter] = useState("");

  const [difficulty, setDifficulty] = useState("Medium");
  const [questionCount, setQuestionCount] = useState(5);

  const [questions, setQuestions] = useState([]);
  const [selectedAnswers, setSelectedAnswers] = useState({});
  const [checkedAnswers, setCheckedAnswers] = useState({});
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    async function loadSyllabus() {
      /** Load syllabus data and initialize quiz filters to the first valid topic. */
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

        setGrade(defaultGrade);
        setMode(defaultMode);
        setSubject(defaultSubject);
        setChapter(defaultChapter);
      } catch {
        setError("Could not load syllabus");
      } finally {
        setLoading(false);
      }
    }

    loadSyllabus();
  }, []);

  if (loading) return <p>Loading quiz page...</p>;
  if (error) return <p className="error">{error}</p>;

  const grades = getVisibleGrades(syllabusData, user);
  const modes = Object.keys(syllabusData[grade]);
  const requestBoard = mode;
  const subjects = Object.keys(syllabusData[grade][mode]);
  const chapters = syllabusData[grade][mode][subject] || [];

  function resetQuiz() {
    /** Clear generated questions and all answer state when quiz context changes. */
    setQuestions([]);
    setSelectedAnswers({});
    setCheckedAnswers({});
  }

  function handleGradeChange(value) {
    /** Change grade and reset all dependent quiz selections. */
    const newMode = Object.keys(syllabusData[value])[0];
    const newSubject = Object.keys(syllabusData[value][newMode])[0];
    const newChapter = syllabusData[value][newMode][newSubject][0];

    setGrade(value);
    setMode(newMode);
    setSubject(newSubject);
    setChapter(newChapter);
    resetQuiz();
  }

  function handleModeChange(value) {
    /** Change mode and reset subject and chapter selections. */
    const newSubject = Object.keys(syllabusData[grade][value])[0];
    const newChapter = syllabusData[grade][value][newSubject][0];

    setMode(value);
    setSubject(newSubject);
    setChapter(newChapter);
    resetQuiz();
  }

  function handleSubjectChange(value) {
    /** Change subject and reset the chapter to the first available option. */
    const newChapter = syllabusData[grade][mode][value][0];

    setSubject(value);
    setChapter(newChapter);
    resetQuiz();
  }

  async function handleGenerateQuiz() {
    /** Request AI-generated quiz questions for the selected topic and difficulty. */
    console.log("Generate quiz clicked");
    console.log("Payload:", {
      grade,
      mode,
      subject,
      chapter,
      difficulty,
      question_count: Number(questionCount),
    });
    setGenerating(true);
    setError("");
    resetQuiz();

    try {
      const result = await generateQuiz({
        grade,
        mode,
        board: requestBoard,
        subject,
        chapter,
        difficulty,
        question_count: Number(questionCount),
      });

      if (!result.success) {
        setError(result.message || "Could not generate quiz");
        return;
      }

      setQuestions(result.questions || []);
    } catch (err) {
      console.error("Quiz error:", err);
      setError("Could not generate quiz. Check backend.");
    } finally {
      setGenerating(false);
    }
  }

  function handleSelectAnswer(questionId, optionKey) {
    /** Store the selected option for one generated quiz question. */
    setSelectedAnswers((prev) => ({
      ...prev,
      [questionId]: optionKey,
    }));
  }

  async function handleCheckAnswer(questionId) {
    /** Reveal one answer and attempt to log the quiz activity. */
    setCheckedAnswers((prev) => ({
      ...prev,
      [questionId]: true,
    }));
  
    try {
      await logStudentActivity({
        username: user.username,
        activity_type: "quiz_attempted",
      });
    } catch {
      console.error("Could not log quiz activity");
    }
  }

  return (
    <div>
      <h2>📝 Quiz</h2>

      <div className="card">
        <h3>Quiz Setup</h3>

        <div className="form-grid">
          <label>
            Grade
            <select
              value={grade}
              onChange={(e) => handleGradeChange(e.target.value)}
            >
              {grades.map((g) => (
                <option key={g} value={g}>
                  {g}
                </option>
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
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </label>

          <label>
            Subject
            <select
              value={subject}
              onChange={(e) => handleSubjectChange(e.target.value)}
            >
              {subjects.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </label>

          <label>
            Chapter / Section
            <select
              value={chapter}
              onChange={(e) => {
                setChapter(e.target.value);
                resetQuiz();
              }}
            >
              {chapters.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
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
            </select>
          </label>

          <label>
            Number of Questions
            <input
              type="number"
              min="3"
              max="15"
              value={questionCount}
              onChange={(e) => setQuestionCount(e.target.value)}
            />
          </label>
        </div>

        <button
          className="primary-btn"
          onClick={handleGenerateQuiz}
          disabled={generating}
        >
          {generating ? "Generating..." : "Generate Quiz"}
        </button>
      </div>

      {error && <div className="error-box">{error}</div>}

      {questions.length > 0 && (
        <div className="card quiz-workspace">
          <div className="quiz-header">
            <div>
              <h3>Practice Questions</h3>
              <p>Answer each question and check instantly.</p>
            </div>

            <div className="quiz-progress-pill">
              {Object.keys(checkedAnswers).length} / {questions.length} checked
            </div>
          </div>
          {questions.map((q) => {
            const selected = selectedAnswers[q.id];
            const checked = checkedAnswers[q.id];
            const isCorrect = selected === q.answer;

            return (
              <div key={q.id} className="question-card">
                <h4>
                  Q{q.id}. {q.question}
                </h4>

                {Object.entries(q.options || {}).map(([key, value]) => (
                  <label key={key} className="option-row">
                    <input
                      type="radio"
                      name={`quiz-question-${q.id}`}
                      checked={selected === key}
                      disabled={checked}
                      onChange={() => handleSelectAnswer(q.id, key)}
                    />

                    <span>
                      <strong>{key}.</strong> {value}
                    </span>
                  </label>
                ))}

                <button
                  className="secondary-btn"
                  disabled={!selected || checked}
                  onClick={() => handleCheckAnswer(q.id)}
                >
                  Check Answer
                </button>

                {checked && (
                  <div
                    className={
                      isCorrect ? "review-card correct" : "review-card wrong"
                    }
                  >
                    <h4>{isCorrect ? "✅ Correct" : "❌ Incorrect"}</h4>

                    <p>
                      Your Answer:{" "}
                      <strong>
                        {selected}. {q.options?.[selected]}
                      </strong>
                    </p>

                    <p>
                      Correct Answer:{" "}
                      <strong>
                        {q.answer}. {q.options?.[q.answer]}
                      </strong>
                    </p>

                    <p>Explanation: {q.explanation}</p>

                    <div className="info-box">
                      {getQuizEncouragement(isCorrect ? 100 : 40)}
                    </div>
                  </div>
                )}
              </div>
            );
          })}{" "}
        </div>
      )}
    </div>
  );
}

export default QuizPage;
