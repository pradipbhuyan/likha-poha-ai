import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { getSyllabus } from "../api/syllabus";
import { answerDoubt } from "../api/doubt";


function DoubtPage() {
  const [loading, setLoading] = useState(true);
  const [syllabusData, setSyllabusData] = useState(null);
  const [error, setError] = useState("");

  const [grade, setGrade] = useState("Grade 9");
  const [mode, setMode] = useState("CBSE");
  const [subject, setSubject] = useState("");
  const [chapter, setChapter] = useState("");

  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");

  const [sourceInfo, setSourceInfo] = useState(null);
  
  const [asking, setAsking] = useState(false);

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

  if (loading) return <p>Loading doubt page...</p>;
  if (error) return <p className="error">{error}</p>;

  const grades = Object.keys(syllabusData);
  const modes = Object.keys(syllabusData[grade]);
  const subjects = Object.keys(syllabusData[grade][mode]);
  const chapters = syllabusData[grade][mode][subject] || [];

  function handleGradeChange(value) {
    const newMode = Object.keys(syllabusData[value])[0];
    const newSubject = Object.keys(syllabusData[value][newMode])[0];
    const newChapter = syllabusData[value][newMode][newSubject][0];

    setGrade(value);
    setMode(newMode);
    setSubject(newSubject);
    setChapter(newChapter);
    setAnswer("");
  }

  function handleModeChange(value) {
    const newSubject = Object.keys(syllabusData[grade][value])[0];
    const newChapter = syllabusData[grade][value][newSubject][0];

    setMode(value);
    setSubject(newSubject);
    setChapter(newChapter);
    setAnswer("");
  }

  function handleSubjectChange(value) {
    const newChapter = syllabusData[grade][mode][value][0];

    setSubject(value);
    setChapter(newChapter);
    setAnswer("");
  }

  async function handleAskDoubt() {
    if (!question.trim()) {
      setError("Please type your question.");
      return;
    }

    setAsking(true);
    setError("");
    setAnswer("");

    try {
      const result = await answerDoubt({
        grade,
        mode,
        subject,
        chapter,
        question,
      });

      if (!result.success) {
        setError(result.message || "Could not answer doubt");
        return;
      }

      setAnswer(result.answer);

      setSourceInfo({
        sourceType: result.source_type,
        sources: result.sources || [],
      });

    } catch {
      setError("Could not answer doubt. Check backend.");
    } finally {
      setAsking(false);
    }
  }

  return (
    <div>
      <h2>❓ Ask Doubt</h2>

      <div className="card">
        <h3>Select Context</h3>

        <div className="form-grid">
          <label>
            Grade
            <select value={grade} onChange={(e) => handleGradeChange(e.target.value)}>
              {grades.map((g) => (
                <option key={g} value={g}>
                  {g}
                </option>
              ))}
            </select>
          </label>

          <label>
            Mode
            <select value={mode} onChange={(e) => handleModeChange(e.target.value)}>
              {modes.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </label>

          <label>
            Subject
            <select value={subject} onChange={(e) => handleSubjectChange(e.target.value)}>
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
                setAnswer("");
              }}
            >
              {chapters.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </label>
        </div>

        <label className="full-width-label">
          Type your doubt
          <textarea
            rows="5"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Example: What is the difference between speed and velocity?"
          />
        </label>

        <button
          className="primary-btn"
          onClick={handleAskDoubt}
          disabled={asking}
        >
          {asking ? "Thinking..." : "Explain Doubt"}
        </button>
      </div>

      {error && <div className="error-box">{error}</div>}

      {answer && (
        <div className="card lesson-output">
          <h3>Answer</h3>

          <div className="markdown-content">
     
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {answer}
            </ReactMarkdown>
          </div>
        </div>
      )}

      {sourceInfo && (
        <div className="card">
          <h3>📚 Source Information</h3>

          <p>
            <strong>Answer Source:</strong>{" "}
            {sourceInfo.sourceType === "RAG"
              ? "Uploaded Textbook / RAG Content"
              : "General LLM Knowledge"}
          </p>

          {sourceInfo.sourceType === "RAG" &&
            sourceInfo.sources.length > 0 && (
              <>
                <h4>Matched Documents</h4>

                {sourceInfo.sources.map((s, index) => (
                  <div key={index} className="question-card">
                    <p>
                      <strong>Document:</strong>{" "}
                      {s.document?.title || "Unknown"}
                    </p>

                    <p>
                      <strong>Similarity:</strong>{" "}
                      {(s.similarity * 100).toFixed(1)}%
                    </p>

                    <p>
                      <strong>Chapter:</strong>{" "}
                      {s.document?.chapter}
                    </p>
                  </div>
                ))}
              </>
            )}
        </div>
      )}


    </div>
  );
}

export default DoubtPage;