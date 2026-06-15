import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";

import { getSyllabus } from "../api/syllabus";
import { answerDoubt, getDoubtHistory, getDoubtSuggestions } from "../api/doubt";
import StructuredVisualBlock from "../components/StructuredVisualBlock";
import {
  getDefaultSelection,
  getUserBoard,
  getUserGrade,
  getVisibleGrades,
} from "../utils/syllabusDefaults";
import { normalizeTutorMarkdown } from "../utils/markdownCleanup";
import { filterAllowedSubjects, isSchoolBoardMode } from "../utils/subjectAccess";
import { isAllAccessTestUser } from "../utils/testAccounts";

const ANSWER_STYLE_OPTIONS = [
  {
    key: "simple",
    label: "Explain simply",
    instruction: "Explain this in simple language first.",
  },
  {
    key: "example",
    label: "Give example",
    instruction: "Include one clear example.",
  },
  {
    key: "steps",
    label: "Step by step",
    instruction: "Show the answer step by step.",
  },
  {
    key: "practice",
    label: "Create practice question",
    instruction: "End with one similar practice question.",
  },
];

function DoubtPage({ user }) {
  /** Student doubt-solving page with syllabus context, RAG/LLM answers, images, and follow-ups. */
  const [loading, setLoading] = useState(true);
  const [syllabusData, setSyllabusData] = useState(null);
  const [error, setError] = useState("");

  const [grade, setGrade] = useState("Grade 9");
  const [mode, setMode] = useState("CBSE");
  const [subject, setSubject] = useState("");
  const [chapter, setChapter] = useState("");
  const [answerStyle, setAnswerStyle] = useState("simple");
  const [doubtSuggestions, setDoubtSuggestions] = useState([]);

  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [sourceInfo, setSourceInfo] = useState(null);
  const [asking, setAsking] = useState(false);
  const [mentorSuggestions, setMentorSuggestions] = useState([]);
  const [relatedDkbQuestions, setRelatedDkbQuestions] = useState([]);

  const answerRef = useRef(null);

  const [followUpQuestion, setFollowUpQuestion] = useState("");
  const [followUpAnswers, setFollowUpAnswers] = useState({});
  const [followUpLoading, setFollowUpLoading] = useState(false);
  const [activeSuggestion, setActiveSuggestion] = useState("");
  const [actionMessage, setActionMessage] = useState("");
  const [doubtHistory, setDoubtHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  useEffect(() => {
    async function loadSyllabus() {
      /** Load syllabus metadata before allowing the student to choose context for a doubt. */
      try {
        const data = await getSyllabus();
        setSyllabusData(data.syllabus);

        const {
          grade: defaultGrade,
          mode: defaultMode,
        } = getDefaultSelection(
          data.syllabus,
          getUserGrade(user),
          getUserBoard(user)
        );

        setGrade(defaultGrade);
        setMode(defaultMode);
      } catch {
        setError("Could not load syllabus. Please refresh and try again.");
      } finally {
        setLoading(false);
      }
    }

    loadSyllabus();
  }, []);

  useEffect(() => {
    async function loadSuggestions() {
      /** Load DKB-backed question chips whenever the learning context changes. */
      try {
        const result = await getDoubtSuggestions({ grade, mode, subject, chapter, limit: 6 });
        setDoubtSuggestions(Array.isArray(result?.doubt_suggestions) ? result.doubt_suggestions : []);
      } catch {
        setDoubtSuggestions([]);
      }
    }
    if (grade && mode) loadSuggestions();
  }, [grade, mode, subject, chapter]);

  useEffect(() => {
    async function loadHistory() {
      /** Load saved Ask Doubt answers for quick student review. */
      setHistoryLoading(true);

      try {
        const result = await getDoubtHistory(20);
        setDoubtHistory(result.history || []);
      } catch {
        setDoubtHistory([]);
      } finally {
        setHistoryLoading(false);
      }
    }

    loadHistory();
  }, []);

  if (loading) return <p>Loading doubt page...</p>;
  if (error && !answer) return <p className="error">{error}</p>;

  const grades = getVisibleGrades(syllabusData, user);
  const modes = Object.keys(syllabusData[grade]);

  function hasModeAccess(selectedMode) {
    /** Check whether the signed-in user may use CBSE or at least one SOF subject. */
    if (user.role === "admin" || isAllAccessTestUser(user)) return true;

    if (isSchoolBoardMode(selectedMode)) {
      return !!user.accessCbse;
    }

    if (selectedMode === "SOF") {
      return (
        !!user.accessSofScience ||
        !!user.accessSofMaths ||
        !!user.accessSofEnglish
      );
    }

    return false;
  }

  const allowedModes = modes.filter((m) => hasModeAccess(m));
  const allModeSubjects = mode ? Object.keys(syllabusData[grade][mode] || {}) : [];
  const allowedSubjects = filterAllowedSubjects(user, allModeSubjects, mode);
  const availableChapters = subject
    ? syllabusData[grade][mode]?.[subject] || []
    : [];
  const requestBoard = mode === "SOF" ? getUserBoard(user) : mode;

  function getAllowedSofSubjectsForGrade(selectedGrade) {
    /** Return only SOF subjects the user can access for the selected grade. */
    const sofSubjects = Object.keys(syllabusData[selectedGrade]?.SOF || {});
    return filterAllowedSubjects(user, sofSubjects, "SOF");
  }

  function getDoubtSubject() {
    /** Provide the selected subject to the backend for RAG filtering and access checks. */
    return subject;
  }

  function buildQuestionWithContext(questionText) {
    /** Combine the typed question, answer style, and OCR text into one backend prompt. */
    const selectedStyle = ANSWER_STYLE_OPTIONS.find(
      (option) => option.key === answerStyle
    );
    const contextParts = [questionText.trim()];

    if (selectedStyle?.instruction) {
      contextParts.push(`Preferred answer style: ${selectedStyle.instruction}`);
    }

    return contextParts.join("\n\n");
  }

  function buildDoubtPayload(questionText, options = {}) {
    /** Build the authenticated doubt payload with syllabus context and enriched question text. */
    return {
      username: user.username,
      grade,
      mode,
      board: requestBoard,
      subject: getDoubtSubject(),
      chapter,
      question: buildQuestionWithContext(questionText),
      display_question:
        options.displayQuestion ?? questionText.trim() ?? question.trim(),
      save_to_history: options.saveToHistory !== false,
    };
  }

  function clearAnswerState() {
    /** Reset generated answer, source, follow-up, and feedback state after context changes. */
    setAnswer("");
    setSourceInfo(null);
    setMentorSuggestions([]);
    setFollowUpQuestion("");
    setFollowUpAnswers({});
    setError("");
    setActionMessage("");
  }

  function handleGradeChange(value) {
    /** Change grade and choose the first accessible mode for that grade. */
    const gradeModes = Object.keys(syllabusData[value]);
    const firstAllowedMode = gradeModes.find((m) => hasModeAccess(m));

    setGrade(value);

    if (!firstAllowedMode) {
      setMode("");
      clearAnswerState();
      setError("You do not have access to any learning mode.");
      return;
    }

    setMode(firstAllowedMode);
    setSubject(
      firstAllowedMode === "SOF"
        ? getAllowedSofSubjectsForGrade(value)[0] || ""
        : filterAllowedSubjects(
            user,
            Object.keys(syllabusData[value][firstAllowedMode] || {}),
            firstAllowedMode
          )[0] || ""
    );
    setChapter("");
    clearAnswerState();
  }

  function handleModeChange(value) {
    /** Change CBSE/SOF mode only when the user has access to it. */
    if (!hasModeAccess(value)) {
      setError(`You do not have access to ${value}.`);
      return;
    }

    setMode(value);
    setSubject(
      value === "SOF"
        ? getAllowedSofSubjectsForGrade(grade)[0] || ""
        : filterAllowedSubjects(
            user,
            Object.keys(syllabusData[grade][value] || {}),
            value
          )[0] || ""
    );
    setChapter("");
    clearAnswerState();
  }

  function handleSubjectChange(value) {
    /** Change the SOF subject and clear stale answer state. */
    setSubject(value);
    setChapter("");
    clearAnswerState();
  }

  function handleChapterChange(value) {
    /** Change the chapter used for retrieval and clear stale answer state. */
    setChapter(value);
    clearAnswerState();
  }

  async function handleCopyAnswer() {
    /** Copy the latest answer to the clipboard when the browser allows it. */
    if (!answer) return;

    try {
      await navigator.clipboard.writeText(answer);
      setActionMessage("Answer copied.");
    } catch {
      setActionMessage("Copy is not available in this browser.");
    }
  }

  function handleStartManualFollowUp() {
    /** Open the manual follow-up prompt under the answer actions. */
    setActiveSuggestion("Ask a follow-up");
    setFollowUpQuestion("");
    setActionMessage("Follow-up box opened.");
  }

  function formatHistoryDate(value) {
    /** Format a saved doubt timestamp for compact display. */
    if (!value) return "";

    return new Date(value).toLocaleString([], {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function handleOpenHistoryItem(item) {
    /** Restore a saved doubt and answer into the main answer panel. */
    setGrade(item.grade || grade);
    setMode(item.mode || mode);
    setSubject(item.subject || "");
    setChapter(item.chapter || "");
    setQuestion(item.question || "");
    setAnswer(normalizeTutorMarkdown(item.answer || ""));
    setMentorSuggestions(item.mentor_suggestions || []);
    setSourceInfo({
      sourceType: item.source_type || "LLM",
      sources: item.sources || [],
    });
    setFollowUpQuestion("");
    setFollowUpAnswers({});
    setActiveSuggestion("");
    setActionMessage("Loaded saved doubt.");
    setError("");
  }

  async function handleAskDoubt() {
    /** Validate access and context, then request the main answer from the backend. */
    if (!hasModeAccess(mode)) {
      setError(`You do not have access to ${mode}.`);
      return;
    }

    if (!question.trim()) {
      setError("Please type your question.");
      return;
    }

    if (mode === "SOF" && !subject) {
      setError("Please select Science, Maths, or English Olympiad.");
      return;
    }

    if (isSchoolBoardMode(mode) && allowedSubjects.length === 0) {
      setError("You do not have access to this CBSE subject.");
      return;
    }

    setAsking(true);
    setError("");
    setAnswer("");
    setSourceInfo(null);
    setMentorSuggestions([]);
    setFollowUpQuestion("");
    setFollowUpAnswers({});

    try {
      const result = await answerDoubt(
        buildDoubtPayload(question, {
          displayQuestion: question.trim(),
          saveToHistory: true,
        })
      );

      if (!result.success) {
        setError(result.message || "Could not answer doubt");
        return;
      }

      const finalAnswer = normalizeTutorMarkdown(result.answer || "");

      setAnswer(finalAnswer);
      setMentorSuggestions(result.mentor_suggestions || []);

      // Scroll to the answer section so students see the response immediately
      setTimeout(() => {
        answerRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 100);

      // Fetch DKB-answerable related questions to show as instant-answer cards
      try {
        const dkbResult = await getDoubtSuggestions({ grade, mode, subject, chapter, limit: 6 });
        const dkbQ = (dkbResult?.doubt_suggestions || []).filter(
          (s) => s.question.toLowerCase() !== question.trim().toLowerCase()
        );
        setRelatedDkbQuestions(dkbQ.slice(0, 3));
      } catch {
        setRelatedDkbQuestions([]);
      }

      setSourceInfo({
        sourceType: result.source_type,
        sources: result.sources || [],
        textbookVisuals: result.textbook_visuals || [],
      });

      try {
        const historyResult = await getDoubtHistory(20);
        setDoubtHistory(historyResult.history || []);
      } catch {
        // History is a convenience feature; a refresh failure should not hide
        // the answer the student just received.
      }
    } catch (err) {
      setError(
        err.message ||
          "Could not answer right now. Please check your login and try again."
      );
    } finally {
      setAsking(false);
    }
  }

  async function handleOpenSuggestionCard(suggestion) {
    /** Generate a concise mentor follow-up for one suggested learning action. */
    if (!hasModeAccess(mode)) {
      setError(`You do not have access to ${mode}.`);
      return;
    }

    if (mode === "SOF" && !subject) {
      setError("Please select Science, Maths, or English Olympiad.");
      return;
    }

    if (isSchoolBoardMode(mode) && allowedSubjects.length === 0) {
      setError("You do not have access to this CBSE subject.");
      return;
    }

    if (followUpAnswers[suggestion]) {
      return;
    }

    setFollowUpLoading(true);

    try {
      const result = await answerDoubt(buildDoubtPayload(`Mentor follow-up mode.

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
- End with one short reflective question.`, {
        saveToHistory: false,
      }));

      if (!result.success) {
        setError(result.message || "Could not answer follow-up.");
        return;
      }

      setFollowUpAnswers((prev) => ({
        ...prev,
        [suggestion]: normalizeTutorMarkdown(result.answer || ""),
      }));
    } catch (err) {
      setError(
        err.message ||
          "Could not answer the follow-up right now. Please try again."
      );
    } finally {
      setFollowUpLoading(false);
    }
  }

  async function handleAskFollowUpCard(suggestion) {
    /** Ask a custom deeper follow-up while preserving the original doubt as context. */
    if (!hasModeAccess(mode)) {
      setError(`You do not have access to ${mode}.`);
      return;
    }

    if (mode === "SOF" && !subject) {
      setError("Please select Science, Maths, or English Olympiad.");
      return;
    }

    if (isSchoolBoardMode(mode) && allowedSubjects.length === 0) {
      setError("You do not have access to this CBSE subject.");
      return;
    }

    if (!followUpQuestion.trim()) {
      return;
    }

    setFollowUpLoading(true);

    try {
      const result = await answerDoubt(buildDoubtPayload(`${suggestion}

Deeper follow-up question:
${followUpQuestion}

Original student doubt:
${question}

Important:
- Answer the deeper follow-up directly.
- Use the original doubt as context.
- Keep the response concise unless detail is required.`, {
        saveToHistory: false,
      }));

      if (!result.success) {
        setError(result.message || "Could not answer follow-up.");
        return;
      }

      setFollowUpAnswers((prev) => ({
        ...prev,
        [suggestion]: normalizeTutorMarkdown(result.answer || ""),
      }));

      setFollowUpQuestion("");
    } catch (err) {
      setError(
        err.message ||
          "Could not answer the follow-up right now. Please try again."
      );
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
              Open mentor mode • {grade} • {mode || "No Access"}
              {mode === "SOF" && subject ? ` • ${subject}` : ""}
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
              Ask Doubt is open-topic, but access is restricted by your enabled
              learning modes.
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
                disabled={allowedModes.length === 0}
              >
                {allowedModes.length === 0 ? (
                  <option value="">No access available</option>
                ) : (
                  allowedModes.map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))
                )}
              </select>
            </label>

            {mode && (
              <label>
                {mode === "SOF" ? "Olympiad Subject" : "Subject"}
                <select
                  value={subject}
                  onChange={(e) => handleSubjectChange(e.target.value)}
                  disabled={allowedSubjects.length === 0}
                >
                  {allowedSubjects.length === 0 ? (
                    <option value="">No subject access</option>
                  ) : mode !== "SOF" ? (
                    <option value="">Open subject</option>
                  ) : null}

                  {allowedSubjects.length === 0 ? null : (
                    allowedSubjects.map((subjectName) => (
                      <option key={subjectName} value={subjectName}>
                        {subjectName}
                      </option>
                    ))
                  )}
                </select>
              </label>
            )}

            {subject && (
              <label>
                Chapter
                <select
                  value={chapter}
                  onChange={(e) => handleChapterChange(e.target.value)}
                >
                  <option value="">Open chapter</option>
                  {availableChapters.map((chapterName) => (
                    <option key={chapterName} value={chapterName}>
                      {chapterName}
                    </option>
                  ))}
                </select>
              </label>
            )}
          </div>

          <div className="premium-open-mentor-note">
            <strong>How this works</strong>
            <p>
              {mode === "SOF"
                ? "Select the Olympiad subject. Chapter is optional, but choosing it helps the AI search the matching SOF content before adding wider explanation."
                : "Subject and chapter are optional. Add them when you know the source topic, or leave them open for a broader textbook search."}
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
              disabled={!mode}
            />

            {/* DKB pre-answered question chips */}
            {doubtSuggestions.length > 0 && (
              <div style={{ marginBottom: 12 }}>
                <p style={{ fontSize: "0.78rem", color: "#6b7280", fontWeight: 600, marginBottom: 6 }}>
                  Suggested questions:
                </p>
                <div className="prompt-chip-row">
                  {doubtSuggestions.map((s) => (
                    <button
                      key={s.id}
                      type="button"
                      className="followup-chip"
                      disabled={!mode || asking}
                      onClick={() => {
                        setQuestion(s.question);
                        setTimeout(() => {
                          document.querySelector(".doubt-submit-btn")?.click();
                        }, 50);
                      }}
                    >
                      {s.question.length > 55 ? s.question.slice(0, 52) + "…" : s.question}
                    </button>
                  ))}
                </div>
              </div>
            )}

            <div className="prompt-chip-row answer-style-row">
              {ANSWER_STYLE_OPTIONS.map((option) => (
                <button
                  key={option.key}
                  type="button"
                  className={
                    answerStyle === option.key
                      ? "prompt-chip selected"
                      : "prompt-chip"
                  }
                  disabled={!mode}
                  onClick={() => setAnswerStyle(option.key)}
                >
                  {option.label}
                </button>
              ))}
            </div>

            <button
              className="primary-btn doubt-submit-btn"
              onClick={handleAskDoubt}
              disabled={asking || !mode}
            >
              {asking ? "Thinking..." : "✨ Ask AI Tutor"}
            </button>
          </section>

          <section className="premium-section premium-doubt-history">
            <div className="premium-header">
              <p className="eyebrow">Saved History</p>
              <h3>Recent Doubts</h3>
              <p>Reopen previous questions and answers whenever you revise.</p>
            </div>

            {historyLoading && <p>Loading saved doubts...</p>}

            {!historyLoading && doubtHistory.length === 0 && (
              <p className="muted-text">
                Your answered doubts will appear here after you ask the tutor.
              </p>
            )}

            {!historyLoading && doubtHistory.length > 0 && (
              <div className="doubt-history-list">
                {doubtHistory.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    className="doubt-history-item"
                    onClick={() => handleOpenHistoryItem(item)}
                  >
                    <strong>{item.question}</strong>
                    <span>
                      {item.grade} • {item.mode}
                      {item.subject ? ` • ${item.subject}` : ""}
                    </span>
                    <small>{formatHistoryDate(item.created_at)}</small>
                  </button>
                ))}
              </div>
            )}
          </section>

          {error && <div className="error-box">{error}</div>}
          {actionMessage && <div className="success-box">{actionMessage}</div>}

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
            <section ref={answerRef} className="premium-section lesson-output premium-doubt-answer">
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
                      const language = className || "";

                      if (/language-visual-json/.test(language)) {
                        return (
                          <StructuredVisualBlock
                            raw={String(children).replace(/\n$/, "")}
                          />
                        );
                      }

                      if (/language-mermaid/.test(language)) {
                        return null;
                      }

                      return <code className={className}>{children}</code>;
                    },
                  }}
                >
                  {answer}
                </ReactMarkdown>
              </div>

              {sourceInfo?.textbookVisuals?.length > 0 && (
                <div className="textbook-visual-strip">
                  {sourceInfo.textbookVisuals.map((visual) => (
                    <figure key={visual.id} className="textbook-visual-card">
                      <img
                        src={visual.asset_url}
                        alt={
                          visual.caption ||
                          `Textbook page ${visual.page_number}`
                        }
                      />
                      <figcaption>
                        <strong>Textbook visual</strong>
                        <span>
                          Page {visual.page_number} • {visual.chapter}
                        </span>
                      </figcaption>
                    </figure>
                  ))}
                </div>
              )}

              <div className="doubt-answer-actions">
                <button type="button" onClick={handleCopyAnswer} title="Copy answer to clipboard">
                  📋 Copy answer
                </button>
                <button type="button" onClick={handleStartManualFollowUp} title="Ask a deeper follow-up question about this answer">
                  💬 Ask follow-up
                </button>
              </div>

              {activeSuggestion === "Ask a follow-up" && (
                <div className="mentor-followup-panel mentor-common-followup-panel">
                  <h4>Ask a follow-up</h4>

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

                  {followUpAnswers[activeSuggestion] && (
                    <div className="mentor-followup-answer markdown-content">
                      <ReactMarkdown
                        remarkPlugins={[remarkGfm, remarkMath]}
                        rehypePlugins={[rehypeKatex]}
                        components={{
                          code({ className, children }) {
                            const language = className || "";

                            if (/language-visual-json/.test(language)) {
                              return (
                                <StructuredVisualBlock
                                  raw={String(children).replace(/\n$/, "")}
                                />
                              );
                            }

                            if (/language-mermaid/.test(language)) {
                              return null;
                            }

                            return <code className={className}>{children}</code>;
                          },
                        }}
                      >
                        {followUpAnswers[activeSuggestion]}
                      </ReactMarkdown>
                    </div>
                  )}
                </div>
              )}

              {/* DKB-backed related questions — answered instantly, no AI needed */}
              {relatedDkbQuestions.length > 0 && (
                <div className="mentor-suggestion-section">
                  <h4>🧠 Suggested Next Steps</h4>
                  <div className="mentor-suggestion-card-grid">
                    {relatedDkbQuestions.map((s) => (
                      <div key={s.id} className="mentor-suggestion-card">
                        <button
                          type="button"
                          className="mentor-suggestion-card-btn"
                          onClick={() => {
                            setQuestion(s.question);
                            setTimeout(() => {
                              document.querySelector(".doubt-submit-btn")?.click();
                            }, 50);
                          }}
                        >
                          <span>🧠</span>
                          <strong>{s.question.length > 60 ? s.question.slice(0, 57) + "…" : s.question}</strong>
                          <small>Ask this question</small>
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {mentorSuggestions.length > 0 && relatedDkbQuestions.length === 0 && (
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

                  {activeSuggestion && activeSuggestion !== "Ask a follow-up" && (
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
                                const language = className || "";

                                if (/language-visual-json/.test(language)) {
                                  return (
                                    <StructuredVisualBlock
                                      raw={String(children).replace(/\n$/, "")}
                                    />
                                  );
                                }

                                if (/language-mermaid/.test(language)) {
                                  return null;
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
