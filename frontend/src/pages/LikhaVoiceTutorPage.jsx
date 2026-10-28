import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import { BookOpen, Mic, Sparkles } from "lucide-react";

import idleNeutral from "../assets/avatar/likha/idle-neutral.png";
import { getSyllabus } from "../api/syllabus";
import { answerDoubt, getDoubtSuggestions } from "../api/doubt";
import LikhaVoicePlayer from "../components/likha/LikhaVoicePlayer";
import LikhaVoiceTutorComposer from "../components/likha/LikhaVoiceTutorComposer";
import StructuredVisualBlock from "../components/StructuredVisualBlock";
import {
  getDefaultSelection,
  getUserBoard,
  getUserGrade,
  getVisibleGrades,
} from "../utils/syllabusDefaults";
import { filterAllowedSubjects } from "../utils/subjectAccess";
import { normalizeTutorMarkdown } from "../utils/markdownCleanup";

const HINDI_SCRIPT_PATTERN = /[\u0900-\u097F]/;

const SOURCE_LABELS = {
  DOUBT_KB: "Knowledge-base answer",
  TEXTBOOK_EXCERPT: "Textbook-grounded answer",
  TEXTBOOK_EXCERPT_WEAK: "Textbook-related answer",
  TEXTBOOK_CONTENT_UNAVAILABLE: "Selected lesson content unavailable",
  WIDER_LLM_KNOWLEDGE: "Wider AI knowledge",
  NO_MATCH_FALLBACK: "No exact match found",
  PLATFORM_RAG: "Platform information",
};

function LikhaVoiceTutorPage({ user }) {
  const [loading, setLoading] = useState(true);
  const [syllabus, setSyllabus] = useState(null);
  const [pageError, setPageError] = useState("");
  const [grade, setGrade] = useState("Grade 9");
  const [mode, setMode] = useState("CBSE");
  const [subject, setSubject] = useState("");
  const [chapter, setChapter] = useState("");
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [answerData, setAnswerData] = useState(null);
  const [suggestions, setSuggestions] = useState([]);
  const [language, setLanguage] = useState("en-IN");
  const [recognitionState, setRecognitionState] = useState("idle");
  const [recognitionMessage, setRecognitionMessage] = useState("");
  const [followUpReady, setFollowUpReady] = useState(false);
  const [conversationHistory, setConversationHistory] = useState([]);
  const recognitionRef = useRef(null);
  const voiceTranscriptRef = useRef("");
  const answerRef = useRef(null);
  const hasReceivedFirstAnswerRef = useRef(false);

  useEffect(() => {
    async function loadSyllabus() {
      try {
        const result = await getSyllabus();
        setSyllabus(result.syllabus);
        const defaults = getDefaultSelection(result.syllabus, getUserGrade(user), getUserBoard(user));
        setGrade(defaults.grade);
        setMode(defaults.mode);
      } catch {
        setPageError("Could not load your learning context. Please refresh and try again.");
      } finally {
        setLoading(false);
      }
    }
    loadSyllabus();
  }, [user]);

  useEffect(() => {
    async function loadSuggestions() {
      if (!grade || !mode) return;
      try {
        const result = await getDoubtSuggestions({ grade, mode, subject, chapter, limit: 6 });
        setSuggestions(Array.isArray(result?.doubt_suggestions) ? result.doubt_suggestions : []);
      } catch {
        setSuggestions([]);
      }
    }
    loadSuggestions();
  }, [grade, mode, subject, chapter]);

  useEffect(() => {
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Recognition) {
      setRecognitionState("unsupported");
      setRecognitionMessage("Voice input is not available in this browser. You can always type your question.");
    }
    return () => recognitionRef.current?.abort?.();
  }, []);

  const grades = syllabus ? getVisibleGrades(syllabus, user) : [];
  const subjects = syllabus ? filterAllowedSubjects(user, Object.keys(syllabus[grade]?.[mode] || {}), mode) : [];
  const chapters = subject ? (syllabus?.[grade]?.[mode]?.[subject] || []) : [];

  function resetAnswer() {
    setAnswerData(null);
    setPageError("");
  }

  function changeGrade(nextGrade) {
    setGrade(nextGrade);
    setSubject("");
    setChapter("");
    setConversationHistory([]);
    resetAnswer();
  }

  function handleVoiceInput() {
    if (recognitionState === "recording") {
      recognitionRef.current?.stop?.();
      return;
    }

    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Recognition) return;

    const recognition = new Recognition();
    const isFollowUp = followUpReady;
    recognitionRef.current = recognition;
    voiceTranscriptRef.current = "";
    setFollowUpReady(false);
    recognition.lang = language;
    recognition.interimResults = true;
    recognition.continuous = false;
    recognition.onstart = () => {
      setRecognitionState("recording");
      setRecognitionMessage("Listening… speak your question. You can edit the transcript before asking.");
    };
    recognition.onresult = (event) => {
      const transcript = Array.from(event.results).map((result) => result[0].transcript).join("").trim();
      voiceTranscriptRef.current = transcript;
      setQuestion(transcript);
      setRecognitionMessage(event.results[event.results.length - 1].isFinal
        ? "Question heard. Likha will start preparing your answer now."
        : "Listening…");
    };
    recognition.onerror = (event) => {
      setRecognitionState("error");
      setRecognitionMessage(event.error === "not-allowed"
        ? "Microphone access was not allowed. You can type your question instead."
        : "Voice input could not start. You can type your question instead.");
    };
    recognition.onend = () => {
      recognitionRef.current = null;
      setRecognitionState((current) => current === "error" ? current : "idle");

      const transcript = voiceTranscriptRef.current.trim();
      voiceTranscriptRef.current = "";
      if (!transcript) return;

      // English recognition can produce an unreliable transcript when a
      // learner speaks Hindi. Do not send that ambiguous text to the academic
      // answer pipeline: ask them to select Hindi and repeat instead.
      if (language === "en-IN" && HINDI_SCRIPT_PATTERN.test(transcript)) {
        setRecognitionState("error");
        setRecognitionMessage(
          "It sounds like you asked that in Hindi. Choose Hindi under Voice language, then tap Speak follow-up and repeat your question."
        );
        return;
      }

      setRecognitionMessage("Likha is preparing your answer…");
      askLikha(transcript, { followUp: isFollowUp });
    };
    recognition.start();
  }

  async function askLikha(questionOverride, { followUp = false } = {}) {
    const askedQuestion = (questionOverride ?? question).trim();
    if (!askedQuestion) {
      setPageError("Please type or speak an academic question first.");
      return;
    }
    if (!subject || !chapter) {
      setPageError("Choose both a subject and chapter so Likha can answer only from that selected lesson.");
      return;
    }

    recognitionRef.current?.stop?.();
    setAsking(true);
    setFollowUpReady(false);
    resetAnswer();

    const sessionHistory = followUp ? conversationHistory : [];

    try {
      const result = await answerDoubt({
        username: user.username,
        grade,
        mode,
        board: mode,
        subject,
        chapter,
        question: askedQuestion,
        display_question: askedQuestion,
        save_to_history: true,
        require_textbook_grounding: true,
        conversation_history: sessionHistory,
        is_follow_up: followUp,
      });

      if (!result?.success) {
        setPageError(result?.message || "Likha could not answer right now. Please try again.");
        return;
      }

      const includeFirstAnswerGreeting = !hasReceivedFirstAnswerRef.current;
      hasReceivedFirstAnswerRef.current = true;
      setQuestion(askedQuestion);
      setConversationHistory((current) => [
        ...current.slice(-2),
        { question: askedQuestion, answer: result.answer || "" },
      ]);
      setAnswerData({
        question: askedQuestion,
        includeFirstAnswerGreeting,
        firstAnswerGreeting: `Great question, ${user.username || "there"}.`,
        answer: normalizeTutorMarkdown(result.answer || ""),
        sourceType: result.source_type,
        sources: result.sources || [],
        visuals: result.textbook_visuals || [],
        suggestions: result.mentor_suggestions || [],
        historyId: result.history_id,
      });
      setTimeout(() => {
        answerRef.current?.scrollIntoView?.({ behavior: "smooth", block: "start" });
      }, 80);
    } catch (error) {
      setPageError(error?.status === 429
        ? "You have reached today’s doubt limit. Please try again tomorrow or review your plan."
        : error?.message || "Likha could not answer right now. Please try again.");
    } finally {
      setAsking(false);
    }
  }

  if (loading) return <p>Loading Likha Voice Tutor…</p>;
  if (pageError && !syllabus) return <p className="error">{pageError}</p>;

  return (
    <div className="doubt-page premium-page premium-doubt-page">
      <section className="premium-section likha-voice-hero" style={{ display: "grid", gridTemplateColumns: "minmax(110px, 145px) minmax(0, 1fr)", gap: 16, alignItems: "center", marginBottom: 14 }}>
        <img src={idleNeutral} alt="Likha, your voice tutor" style={{ width: "100%", maxHeight: 150, objectFit: "contain" }} />
        <div>
          <p className="eyebrow">Your AI learning companion</p>
          <h2 style={{ margin: "0 0 8px" }}>Learn through every doubt</h2>
          <p style={{ margin: 0, color: "var(--text-muted,#64748b)", lineHeight: 1.55, maxWidth: 760 }}>
            Ask by typing or speaking and get a clear answer grounded in your learning
            materials whenever available. Voice questions are sent as soon as you finish
            speaking, and Likha explains the answer aloud in English or Hindi.
          </p>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 14 }}>
            {["Type or speak", "Instant voice response", "Read and listen"].map((feature) => (
              <span key={feature} style={{
                padding: "6px 10px", borderRadius: 999, fontSize: ".78rem", fontWeight: 700,
                color: "#4338ca", background: "rgba(99,102,241,.1)", border: "1px solid rgba(99,102,241,.2)",
              }}>
                {feature}
              </span>
            ))}
          </div>
        </div>
      </section>

      <section className="premium-section" aria-labelledby="likha-context-heading" style={{ marginBottom: 14 }}>
        <p className="eyebrow">Learning context</p>
        <h3 id="likha-context-heading">Choose the topic you are studying</h3>
        <div className="form-grid">
          <label>Grade
            <select value={grade} onChange={(event) => changeGrade(event.target.value)}>
              {grades.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
          </label>
          <label>Subject
            <select value={subject} onChange={(event) => { setSubject(event.target.value); setChapter(""); setConversationHistory([]); resetAnswer(); }}>
              <option value="">Choose a subject</option>
              {subjects.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
          </label>
          <label>Chapter
            <select value={chapter} onChange={(event) => { setChapter(event.target.value); setConversationHistory([]); resetAnswer(); }} disabled={!subject}>
              <option value="">Choose a chapter</option>
              {chapters.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
          </label>
        </div>
      </section>

      {pageError && <div className="error-box" role="alert" style={{ marginBottom: 14 }}>{pageError}</div>}

      <LikhaVoiceTutorComposer
        question={question}
        onQuestionChange={setQuestion}
        onSubmit={() => askLikha()}
        asking={asking}
        suggestions={suggestions}
        onSuggestionSelect={(suggestion) => { setQuestion(suggestion.question); askLikha(suggestion.question); }}
        language={language}
        onLanguageChange={setLanguage}
        recognitionState={recognitionState}
        recognitionMessage={recognitionMessage}
        onVoiceInput={handleVoiceInput}
      />

      {asking && (
        <section className="premium-section" role="status" aria-live="polite" style={{ marginTop: 14 }}>
          <p className="eyebrow">Checking your learning materials</p>
          <h3><Sparkles size={18} /> Likha is preparing an explanation…</h3>
        </section>
      )}

      {answerData && (
        <section ref={answerRef} className="premium-section lesson-output premium-doubt-answer" style={{ marginTop: 14 }}>
          <div className="premium-header">
            <p className="eyebrow">{SOURCE_LABELS[answerData.sourceType] || "Answer"}</p>
            <h3>Likha’s explanation</h3>
            <p>{answerData.sourceType === "TEXTBOOK_CONTENT_UNAVAILABLE"
              ? "Likha could not verify enough material from the selected lesson, so she did not create an answer."
              : "Read the written explanation at your own pace, then choose Listen when you want audio."}</p>
          </div>

          <div className="markdown-content">
            <ReactMarkdown
              remarkPlugins={[remarkGfm, remarkMath]}
              rehypePlugins={[rehypeKatex]}
              components={{
                code({ className, children }) {
                  if (/language-visual-json/.test(className || "")) return <StructuredVisualBlock raw={String(children).replace(/\n$/, "")} />;
                  return <code className={className}>{children}</code>;
                },
              }}
            >
              {answerData.answer}
            </ReactMarkdown>
          </div>

          {answerData.visuals.length > 0 && (
            <div className="textbook-visual-strip">
              {answerData.visuals.map((visual) => (
                <figure key={visual.id} className="textbook-visual-card">
                  <img src={visual.asset_url} alt={visual.caption || `Textbook page ${visual.page_number}`} />
                  <figcaption><strong>Textbook visual</strong><span>Page {visual.page_number} • {visual.chapter}</span></figcaption>
                </figure>
              ))}
            </div>
          )}

          <LikhaVoicePlayer
            historyId={answerData.historyId}
            answer={answerData.answer}
            language={language}
            autoPlay
            includeFirstAnswerGreeting={answerData.includeFirstAnswerGreeting}
            firstAnswerGreeting={answerData.firstAnswerGreeting}
            onFollowUpReady={() => setFollowUpReady(true)}
          />

          {followUpReady && (
            <section className="likha-voice-followup" aria-live="polite" style={{
              display: "flex", alignItems: "center", justifyContent: "space-between",
              gap: 14, flexWrap: "wrap", marginTop: 16, padding: "14px 16px",
              borderRadius: 12, background: "rgba(99,102,241,.08)",
              border: "1px solid rgba(99,102,241,.22)",
            }}>
              <div>
                <strong>Do you have a follow-up question?</strong>
                <p style={{ margin: "3px 0 0", color: "var(--text-muted,#64748b)", fontSize: ".84rem" }}>
                  Tap once, speak naturally, and Likha will continue the explanation.
                </p>
              </div>
              <button type="button" onClick={handleVoiceInput} className="primary-btn" style={{
                height: 48, margin: 0, display: "inline-flex", alignItems: "center",
                justifyContent: "center", gap: 8, padding: "0 16px", whiteSpace: "nowrap",
              }}>
                <Mic size={17} /> Speak follow-up
              </button>
            </section>
          )}

          {answerData.sourceType === "TEXTBOOK_EXCERPT" && (
            <p style={{ marginTop: 14, fontSize: ".82rem", color: "#059669", fontWeight: 700 }}>
              <BookOpen size={15} /> This explanation is based on your selected textbook context.
            </p>
          )}

        </section>
      )}
    </div>
  );
}

export default LikhaVoiceTutorPage;
