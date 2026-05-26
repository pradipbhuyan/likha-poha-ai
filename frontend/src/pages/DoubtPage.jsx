import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";

import { getSyllabus } from "../api/syllabus";
import { answerDoubt } from "../api/doubt";
import MermaidBlock from "../components/MermaidBlock";

function DoubtPage({ user }) {
  const [loading, setLoading] = useState(true);
  const [syllabusData, setSyllabusData] = useState(null);
  const [error, setError] = useState("");

  const [grade, setGrade] = useState("Grade 9");
  const [mode, setMode] = useState("CBSE");

  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [sourceInfo, setSourceInfo] = useState(null);
  const [asking, setAsking] = useState(false);
  const [mentorSuggestions, setMentorSuggestions] = useState([]);

  const [activeFollowUpCard, setActiveFollowUpCard] = useState(null);
  const [followUpQuestion, setFollowUpQuestion] = useState("");
  const [followUpAnswers, setFollowUpAnswers] = useState({});
  const [followUpLoading, setFollowUpLoading] = useState(false);
  const [activeSuggestion, setActiveSuggestion] = useState("");

  useEffect(() => {
    async function loadSyllabus() {
      try {
        const data = await getSyllabus();
        setSyllabusData(data.syllabus);

        const defaultGrade = "Grade 9";
        const defaultMode = "CBSE";

        setGrade(defaultGrade);
        setMode(defaultMode);
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

  function clearAnswerState() {
    setAnswer("");
    setSourceInfo(null);
    setMentorSuggestions([]);
    setActiveFollowUpCard(null);
    setFollowUpQuestion("");
    setFollowUpAnswers({});
    setError("");
  }

  function handleGradeChange(value) {
    const newMode = Object.keys(syllabusData[value])[0];

    setGrade(value);
    setMode(newMode);
    clearAnswerState();
  }

  function handleModeChange(value) {
    setMode(value);
    clearAnswerState();
  }

  function normalizeMermaidBlocks(text) {
    if (!text) return "";

    if (text.includes("graph TD") && !text.includes("```mermaid")) {
      const lines = text.split("\n");
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

      return output.join("\n");
    }

    return text;
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
    setMentorSuggestions([]);
    setActiveFollowUpCard(null);
    setFollowUpQuestion("");
    setFollowUpAnswers({});

    try {
      const result = await answerDoubt({
        username: user.username,
        grade,
        mode,
        subject: "",
        chapter: "",
        question,
      });

      if (!result.success) {
        setError(result.message || "Could not answer doubt");
        return;
      }

      const finalAnswer = normalizeMermaidBlocks(result.answer || "");

      setAnswer(finalAnswer);
      setMentorSuggestions(result.mentor_suggestions || []);

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

  async function handleOpenSuggestionCard(suggestion) {
    setActiveFollowUpCard(suggestion);

    if (followUpAnswers[suggestion]) {
      return;
    }

    setFollowUpLoading(true);

    try {
const result = await answerDoubt({
  username: user.username,
  grade,
  mode,
  subject: "",
  chapter: "",
  question: `Mentor follow-up mode.

Student's original doubt:
${question}

Requested follow-up:
${suggestion}

Rules:
- Keep response under 150 words.
- No Mermaid diagrams.
- No long lesson structure.
- No markdown tables.
- Be concise and conversational.
- Focus only on the requested follow-up.
- End with one short reflective question.`,
});

      if (!result.success) {
        setError(result.message || "Could not answer follow-up.");
        return;
      }

      setFollowUpAnswers((prev) => ({
        ...prev,
        [suggestion]: normalizeMermaidBlocks(result.answer || ""),
      }));
    } catch {
      setError("Could not answer follow-up. Check backend.");
    } finally {
      setFollowUpLoading(false);
    }
  }

  async function handleAskFollowUpCard(suggestion) {
    if (!followUpQuestion.trim()) {
      return;
    }

    setFollowUpLoading(true);

    try {
      const result = await answerDoubt({
        username: user.username,
        grade,
        mode,
        subject: "",
        chapter: "",
        question: `${suggestion}

Deeper follow-up question:
${followUpQuestion}

Original student doubt:
${question}

Important:
- Answer the deeper follow-up directly.
- Use the original doubt as context.
- Keep the response concise unless detail is required.`,
      });

      if (!result.success) {
        setError(result.message || "Could not answer follow-up.");
        return;
      }

      setFollowUpAnswers((prev) => ({
        ...prev,
        [suggestion]: normalizeMermaidBlocks(result.answer || ""),
      }));

      setFollowUpQuestion("");
    } catch {
      setError("Could not answer follow-up. Check backend.");
    } finally {
      setFollowUpLoading(false);
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
              Open mentor mode • {grade} • {mode}
            </p>
          </div>
        </div>
      </section>

      <section className="premium-doubt-layout premium-doubt-open-layout">
        <aside className="premium-section premium-doubt-context">
          <div className="premium-header">
            <p className="eyebrow">Mentor Context</p>
            <h3>🎯 Choose Learning Level</h3>
            <p>
              Ask Doubt is now open-topic. The AI will use your question, mentor
              memory, textbook RAG, and general LLM knowledge together.
            </p>
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
          </div>

          <div className="premium-open-mentor-note">
            <strong>How this works</strong>
            <p>
              You do not need to select a subject or chapter here. Type your
              doubt naturally, and the AI will search broadly across uploaded
              textbook content and combine it with mentor memory.
            </p>
          </div>
        </aside>

        <main className="premium-doubt-main">
          <section className="premium-section premium-doubt-composer">
            <div className="composer-header">
              <div>
                <p className="eyebrow">Ask AI Tutor</p>
                <h3>💬 What are you stuck on?</h3>
                <p>Ask any concept, homework, textbook, or Olympiad doubt.</p>
              </div>

              <span className="composer-badge">Open Mentor</span>
            </div>

            <textarea
              rows="6"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Example: Explain Newton's laws of force with real-life examples."
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
                <h3>Ask any doubt in open mentor mode</h3>
                <p>
                  Your AI mentor can simplify concepts, solve problems, explain
                  diagrams, and connect your question to textbook content when
                  available.
                </p>
              </div>

              <div className="premium-grid premium-grid-3">
                <div className="premium-card premium-glow-card glow-blue">
                  <h3>🧩 Concept Help</h3>
                  <p>Break difficult topics into simple steps.</p>
                </div>

                <div className="premium-card premium-glow-card glow-purple">
                  <h3>📘 RAG + LLM</h3>
                  <p>
                    Uses textbook context and general AI knowledge together.
                  </p>
                </div>

                <div className="premium-card premium-glow-card glow-green">
                  <h3>🧠 Mentor Memory</h3>
                  <p>
                    Adapts to previous doubts and preferred explanation style.
                  </p>
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
                <p>
                  Your AI tutor response using your question as the main
                  context.
                </p>
              </div>

              <div className="markdown-content">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm, remarkMath]}
                  rehypePlugins={[rehypeKatex]}
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

              {mentorSuggestions.length > 0 && (
                <div className="mentor-suggestion-section">
                  <h4>🧠 Suggested Next Steps</h4>

                  <div className="mentor-suggestion-card-grid">
                    {mentorSuggestions.map((suggestion, index) => (
                      <div key={index} className="mentor-suggestion-card">
                        <button
                          type="button"
                          className="mentor-suggestion-card-btn"
                          onClick={() => {
                            setActiveSuggestion(suggestion);
                            handleOpenSuggestionCard(suggestion);
                            setFollowUpQuestion("");
                          }}
                        >
                          <span>🧠</span>
                          <strong>{suggestion}</strong>
                          <small>Open guided follow-up</small>
                        </button>
                      </div>
                    ))}
                  </div>

                  {activeSuggestion && (
                    <div className="mentor-followup-panel mentor-common-followup-panel">
                      <h4>🧠 {activeSuggestion}</h4>

                      {followUpLoading &&
                        !followUpAnswers[activeSuggestion] && (
                          <p>Thinking...</p>
                        )}

                      {followUpAnswers[activeSuggestion] && (
                        <div className="mentor-followup-answer markdown-content">
                          <ReactMarkdown
                            remarkPlugins={[remarkGfm, remarkMath]}
                            rehypePlugins={[rehypeKatex]}
                            components={{
                              code({ className, children }) {
                                const match = /language-mermaid/.exec(
                                  className || ""
                                );

                                if (match) {
                                  return (
                                    <MermaidBlock
                                      chart={String(children).replace(
                                        /\n$/,
                                        ""
                                      )}
                                    />
                                  );
                                }

                                return (
                                  <code className={className}>{children}</code>
                                );
                              },
                            }}
                          >
                            {followUpAnswers[activeSuggestion]}
                          </ReactMarkdown>
                        </div>
                      )}

                      <textarea
                        rows="3"
                        value={followUpQuestion}
                        placeholder="Ask a deeper follow-up..."
                        onChange={(e) => setFollowUpQuestion(e.target.value)}
                      />

                      <button
                        className="primary-btn"
                        disabled={followUpLoading || !followUpQuestion.trim()}
                        onClick={() => handleAskFollowUpCard(activeSuggestion)}
                      >
                        {followUpLoading ? "Thinking..." : "Ask Follow-up"}
                      </button>
                    </div>
                  )}
                </div>
              )}
            </section>
          )}

          {sourceInfo && (
            <section className="premium-section premium-doubt-source">
              <div className="premium-header">
                <h3>📚 Source Information</h3>

                <p>
                  <strong>Answer Source:</strong>{" "}
                  {sourceInfo.sourceType === "RAG"
                    ? "Uploaded Textbook / RAG Content + LLM"
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
                        chapter: s.document?.chapter || "Matched topic",
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
                            <strong>Match:</strong> Broad textbook match
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
