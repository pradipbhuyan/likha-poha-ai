import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { getSyllabus } from "../api/syllabus";
import { answerDoubt } from "../api/doubt";
import MermaidBlock from "../components/MermaidBlock";

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

      let finalAnswer = result.answer || "";

      if (
        finalAnswer.includes("graph TD") &&
        !finalAnswer.includes("```mermaid")
      ) {
        const lines = finalAnswer.split("\n");
        const output = [];
        let inMermaid = false;

        for (const line of lines) {
          const trimmed = line.trim();

          if (trimmed.startsWith("graph TD")) {
            output.push("```mermaid");
            output.push(line);
            inMermaid = true;
            continue;
          }

          if (inMermaid) {
            const isMermaidLine =
              trimmed === "" ||
              trimmed.includes("-->") ||
              trimmed.includes("-.->") ||
              /^[A-Za-z0-9_]+\[.*\]$/.test(trimmed);

            if (isMermaidLine) {
              output.push(line);
            } else {
              output.push("```");
              output.push(line);
              inMermaid = false;
            }

            continue;
          }

          output.push(line);
        }

        if (inMermaid) {
          output.push("```");
        }

        finalAnswer = output.join("\n");
      }

      setAnswer(finalAnswer);

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
    <div className="doubt-page">
      <h2>❓ Ask Doubt</h2>

      <div className="card">
        <h3>Select Context</h3>

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

        <div className="doubt-composer">
          <div className="composer-header">
            <div>
              <h3>💬 Ask your AI tutor</h3>
              <p>Type your doubt, or choose a quick prompt below.</p>
            </div>

            <span className="composer-badge">AI Guided</span>
          </div>

          <textarea
            rows="5"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Example: What is the difference between frequency and resonance?"
          />

          <div className="prompt-chip-row">
            {[
              "Explain simply",
              "Give real-life example",
              "Show step-by-step",
              "Olympiad style",
              "Add diagram if useful",
            ].map((chip) => (
              <button
                key={chip}
                type="button"
                className="prompt-chip"
                onClick={() =>
                  setQuestion((prev) => (prev ? `${prev}\n${chip}` : chip))
                }
              >
                {chip}
              </button>
            ))}
          </div>

          <button
            className="primary-btn doubt-submit-btn"
            onClick={handleAskDoubt}
            disabled={asking}
          >
            {asking ? "Thinking..." : "✨ Ask AI Tutor"}
          </button>
        </div>
      </div>

      {error && <div className="error-box">{error}</div>}

      {answer && (
        <div className="card lesson-output">
          <h3>Answer</h3>

          <div className="markdown-content">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                code({ className, children }) {
                  const match = /language-mermaid/.exec(className || "");

                  if (match) {
                    return (
                      <MermaidBlock
                        chart={String(children).replace(/\n$/, "")}
                      />
                    );
                  }

                  return <code className={className}>{children}</code>;
                },
              }}
            >
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
            sourceInfo.sources.length > 0 &&
            (() => {
              const uniqueDocs = [];
              const seen = new Set();

              sourceInfo.sources.forEach((s) => {
                const title = s.document?.title || "Unknown";

                if (!seen.has(title)) {
                  seen.add(title);

                  uniqueDocs.push({
                    title,
                    chapter: s.document?.chapter || chapter,
                  });
                }
              });

              return (
                <>
                  <h4>Matched Sources</h4>

                  {uniqueDocs.map((doc, index) => (
                    <div key={index} className="question-card">
                      <p>
                        <strong>Source:</strong> {doc.title}
                      </p>

                      <p>
                        <strong>Chapter:</strong> {doc.chapter}
                      </p>

                      <p>
                        <strong>Match:</strong> Textbook chapter match
                      </p>
                    </div>
                  ))}
                </>
              );
            })()}
        </div>
      )}
    </div>
  );
}

export default DoubtPage;
