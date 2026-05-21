import { useEffect, useState } from "react";

import { getSyllabus } from "../api/syllabus";
import { generateQuiz } from "../api/quiz";

function QuizPage() {
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
      try {
        const data = await getSyllabus();
        setSyllabusData(data.syllabus);

        const defaultGrade = "Grade 9";
        const defaultMode = "CBSE";
        const defaultSubject = Object.keys(
          data.syllabus[defaultGrade][defaultMode]
        )[0];

        const defaultChapter =
          data.syllabus[defaultGrade][defaultMode][defaultSubject][0];

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

  const grades = Object.keys(syllabusData);
  const modes = Object.keys(syllabusData[grade]);
  const subjects = Object.keys(syllabusData[grade][mode]);
  const chapters = syllabusData[grade][mode][subject] || [];

  function resetQuiz() {
    setQuestions([]);
    setSelectedAnswers({});
    setCheckedAnswers({});
  }

  function handleGradeChange(value) {
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
    const newSubject = Object.keys(syllabusData[grade][value])[0];
    const newChapter = syllabusData[grade][value][newSubject][0];

    setMode(value);
    setSubject(newSubject);
    setChapter(newChapter);
    resetQuiz();
  }

  function handleSubjectChange(value) {
    const newChapter = syllabusData[grade][mode][value][0];

    setSubject(value);
    setChapter(newChapter);
    resetQuiz();
  }

  async function handleGenerateQuiz() {
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
    setSelectedAnswers((prev) => ({
      ...prev,
      [questionId]: optionKey,
    }));
  }

  function handleCheckAnswer(questionId) {
    setCheckedAnswers((prev) => ({
      ...prev,
      [questionId]: true,
    }));
  }

  return (
    <div>
      <h2>📝 Quiz</h2>

      <div className="card">
        <h3>Quiz Setup</h3>

        <div className="form-grid">
          <label>
            Grade
            <select value={grade} onChange={(e) => handleGradeChange(e.target.value)}>
              {grades.map((g) => (
                <option key={g} value={g}>{g}</option>
              ))}
            </select>
          </label>

          <label>
            Mode
            <select value={mode} onChange={(e) => handleModeChange(e.target.value)}>
              {modes.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          </label>

          <label>
            Subject
            <select value={subject} onChange={(e) => handleSubjectChange(e.target.value)}>
              {subjects.map((s) => (
                <option key={s} value={s}>{s}</option>
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
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </label>

          <label>
            Difficulty
            <select value={difficulty} onChange={(e) => setDifficulty(e.target.value)}>
              <option>Easy</option>
              <option>Medium</option>
              <option>Hard</option>
              <option>Olympiad HOTS</option>
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
        <div className="card">
          <h3>Practice Questions</h3>

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
                  <div className={isCorrect ? "review-card correct" : "review-card wrong"}>
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

                    <p>
                      Explanation: {q.explanation}
                    </p>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default QuizPage;