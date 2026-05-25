import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { getSyllabus } from "../api/syllabus";
import { answerDoubt } from "../api/doubt";
import MermaidBlock from "../components/MermaidBlock";

function DoubtPage({ user }) {
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
  if (error && !answer) return <p className="error">{error}</p>;

  const grades = Object.keys(syllabusData);
  const modes = Object.keys(syllabusData[grade]);
  const subjects = Object.keys(syllabusData[grade][mode]);
  const chapters = syllabusData[grade][mode][subject] || [];

  function clearAnswerState() {
    setAnswer("");
    setSourceInfo(null);
    setError("");
  }

  function handleGradeChange(value) {
    const newMode = Object.keys(syllabusData[value])[0];
    const newSubject = Object.keys(syllabusData[value][newMode])[0];
    const newChapter = syllabusData[value][newMode][newSubject][0];

    setGrade(value);
    setMode(newMode);
    setSubject(newSubject);
    setChapter(newChapter);
    clearAnswerState();
  }

  function handleModeChange(value) {
    const newSubject = Object.keys(syllabusData[grade][value])[0];
    const newChapter = syllabusData[grade][value][newSubject][0];

    setMode(value);
    setSubject(newSubject);
    setChapter(newChapter);
    clearAnswerState();
  }

  function handleSubjectChange(value) {
    const newChapter = syllabusData[grade][mode][value][0];

    setSubject(value);
    setChapter(newChapter);
    clearAnswerState();
  }

  async function handleAskDoubt() {
    if (!question.trim()) {
      setError("Please type your question.");
      return;
    }

    setAsking(true);
    setError("");
    setAnswer("");
    setSourceInfo(null);

    try {
      const result = await answerDoubt({
        username: user.username,
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
    <div className="doubt-page premium-page premium-doubt-page">
      <section className="premium-section premium-doubt-hero">
        <div className="premium-header">
          <p className="eyebrow">AI Mentor Workspace</p>
          <h2>❓ Ask Doubt</h2>
          <p>
            Ask your AI tutor anything. Get textbook-aware explanations,
            examples, diagrams, and step-by-step help.
          </p>
        </div>

        <div className="premium-doubt-mentor-card">
          <span>🤖</span>
          <div>
            <strong>AI Study Companion</strong>
            <p>
              Context: {grade} • {subject} • {chapter}
            </p>
          </div>
        </div>
      </section>

      <section className="premium-doubt-layout">
        <aside className="premium-section premium-doubt-context">
          <div className="premium-header">
            <p className="eyebrow">Context</p>
            <h3>📚 Select Topic</h3>
            <p>Choose the syllabus context so answers stay focused.</p>
          </div>

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
                  clearAnswerState();
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
        </aside>

        <main className="premium-doubt-main">
          <section className="premium-section premium-doubt-composer">
            <div className="composer-header">
              <div>
                <p className="eyebrow">Ask AI Tutor</p>
                <h3>💬 What are you stuck on?</h3>
                <p>Type your doubt, or choose a quick prompt below.</p>
              </div>

              <span className="composer-badge">AI Guided</span>
            </div>

            <textarea
              rows="6"
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
          </section>

          {error && <div className="error-box">{error}</div>}

          {!answer && !asking && (
            <section className="premium-section premium-doubt-empty">
              <div className="premium-header">
                <p className="eyebrow">Ready to help</p>
                <h3>Ask any doubt from this chapter</h3>
                <p>
                  Your AI mentor can simplify concepts, give examples, solve
                  problems, and explain diagrams using your selected context.
                </p>
              </div>

              <div className="premium-grid premium-grid-3">
                <div className="premium-card premium-glow-card glow-blue">
                  <h3>🧩 Concept Help</h3>
                  <p>Break difficult topics into simple steps.</p>
                </div>

                <div className="premium-card premium-glow-card glow-purple">
                  <h3>📘 Textbook Aware</h3>
                  <p>Uses uploaded RAG content when relevant.</p>
                </div>

                <div className="premium-card premium-glow-card glow-green">
                  <h3>🧠 Exam Focused</h3>
                  <p>Get clear answers with scoring tips.</p>
                </div>
              </div>
            </section>
          )}

          {answer && (
            <section className="premium-section lesson-output premium-doubt-answer">
              <div className="premium-header">
                <p className="eyebrow">
                  {sourceInfo?.sourceType === "RAG"
                    ? "Textbook aligned"
                    : "AI generated"}
                </p>
                <h3>Answer</h3>
                <p>Your AI tutor response for the selected chapter.</p>
              </div>

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
            </section>
          )}

          {sourceInfo && (
            <section className="premium-section premium-doubt-source">
              <div className="premium-header">
                <h3>📚 Source Information</h3>

                <p>
                  <strong>Answer Source:</strong>{" "}
                  {sourceInfo.sourceType === "RAG"
                    ? "Uploaded Textbook / RAG Content"
                    : "General LLM Knowledge"}
                </p>
              </div>

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
            </section>
          )}
        </main>
      </section>
    </div>
  );
}

export default DoubtPage;
