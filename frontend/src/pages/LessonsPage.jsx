import { useEffect, useState } from "react";
import remarkGfm from "remark-gfm";
import ReactMarkdown from "react-markdown";

import { getSyllabus } from "../api/syllabus";

import { generateLesson, askLessonFollowUp } from "../api/lesson";

import { generateSpeech } from "../api/tts";
import MermaidBlock from "../components/MermaidBlock";
import LessonSections from "../components/LessonSections";

import { getChapterProgress, saveChapterProgress } from "../api/progress";

const TEACHER_PERSONAS = {
  "Friendly Teacher": "Explain warmly, patiently, and encouragingly.",

  "Strict Exam Coach":
    "Focus on exam preparation, accuracy, common mistakes, and scoring.",

  "Slow Step-by-Step Teacher":
    "Explain slowly, with very small steps and simple examples.",

  "Olympiad Coach":
    "Focus on reasoning, HOTS, shortcuts, and tricky question patterns.",

  "Storytelling Teacher":
    "Explain concepts using stories, analogies, and real-life examples.",
};

const VOICE_OPTIONS = {
  "English India Female (Neerja)": "en-IN-NeerjaNeural",
  "English India Male (Prabhat)": "en-IN-PrabhatNeural",
  "Hindi Female (Swara)": "hi-IN-SwaraNeural",
  "Hindi Male (Madhur)": "hi-IN-MadhurNeural",
  "US Female (Aria)": "en-US-AriaNeural",
  "US Male (Guy)": "en-US-GuyNeural",
  "UK Female (Sonia)": "en-GB-SoniaNeural",
  "UK Male (Ryan)": "en-GB-RyanNeural",
};

function LessonsPage({ user }) {
  const [loading, setLoading] = useState(true);
  const [syllabusData, setSyllabusData] = useState(null);
  const [error, setError] = useState("");

  const [grade, setGrade] = useState("Grade 9");
  const [mode, setMode] = useState("CBSE");
  const [subject, setSubject] = useState("");
  const [chapter, setChapter] = useState("");

  const lessonSteps = [
    "Concept introduction",
    "Core explanation",
    "Worked examples",
    "Practice questions",
    "Revision and recap",
  ];

  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [completed, setCompleted] = useState(false);

  const stepTitle = lessonSteps[currentStepIndex];

  const [teacherPersona, setTeacherPersona] = useState("Friendly Teacher");

  const [lesson, setLesson] = useState("");
  const [sourceInfo, setSourceInfo] = useState(null);
  const [generating, setGenerating] = useState(false);

  const [followUpQuestion, setFollowUpQuestion] = useState("");
  const [followUpMessages, setFollowUpMessages] = useState([]);
  const [followUpLoading, setFollowUpLoading] = useState(false);

  // -----------------------------
  // TTS STATES
  // -----------------------------
  const [voiceName, setVoiceName] = useState("English India Female (Neerja)");

  const [speechRate, setSpeechRate] = useState("+0%");
  const [audioUrl, setAudioUrl] = useState("");
  const [ttsLoading, setTtsLoading] = useState(false);

  // -----------------------------
  // LOAD SYLLABUS
  // -----------------------------
  useEffect(() => {
    async function loadSyllabus() {
      try {
        const data = await getSyllabus();

        setSyllabusData(data.syllabus);

        const defaultGrade = "Grade 9";
        const defaultMode = "CBSE";

        const defaultSubjects = Object.keys(
          data.syllabus[defaultGrade][defaultMode]
        );

        const defaultSubject = defaultSubjects[0];

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

  useEffect(() => {
    async function loadProgress() {
      if (!grade || !mode || !subject || !chapter) {
        return;
      }

      try {
        const result = await getChapterProgress({
          username: user.username,
          grade,
          mode,
          subject,
          chapter,
        });

        const progress = result.progress;

        setCurrentStepIndex(progress.current_step_index || 0);

        setCompleted(progress.completed || false);

        if (progress.last_lesson) {
          setLesson(progress.last_lesson);
        } else {
          setLesson("");
        }
      } catch {
        console.error("Could not load progress");
      }
    }

    loadProgress();
  }, [grade, mode, subject, chapter, user.username]);

  if (loading) {
    return <p>Loading syllabus...</p>;
  }

  if (error) {
    return <p className="error">{error}</p>;
  }

  const grades = Object.keys(syllabusData);

  const modes = Object.keys(syllabusData[grade]);

  const subjects = Object.keys(syllabusData[grade][mode]);

  const chapters = syllabusData[grade][mode][subject] || [];

  // -----------------------------
  // DROPDOWN HANDLERS
  // -----------------------------
  function handleGradeChange(value) {
    const newMode = Object.keys(syllabusData[value])[0];

    const newSubject = Object.keys(syllabusData[value][newMode])[0];

    const newChapter = syllabusData[value][newMode][newSubject][0];

    setGrade(value);
    setMode(newMode);
    setSubject(newSubject);
    setChapter(newChapter);

    setLesson("");
  }

  function handleModeChange(value) {
    const newSubject = Object.keys(syllabusData[grade][value])[0];

    const newChapter = syllabusData[grade][value][newSubject][0];

    setMode(value);
    setSubject(newSubject);
    setChapter(newChapter);

    setLesson("");
  }

  function handleSubjectChange(value) {
    const newChapter = syllabusData[grade][mode][value][0];

    setSubject(value);
    setChapter(newChapter);

    setLesson("");
  }

  // -----------------------------
  // GENERATE LESSON
  // -----------------------------
  async function handleGenerateLesson() {
    setGenerating(true);
    setLesson("");
    setAudioUrl("");
    setSourceInfo(null);
    setError("");
    setFollowUpQuestion("");
    setFollowUpMessages([]);

    try {
      const result = await generateLesson({
        grade,
        mode,
        subject,
        chapter,
        step_title: stepTitle,
        teacher_persona: TEACHER_PERSONAS[teacherPersona],
      });

      if (!result.success) {
        setError(result.message || "Lesson generation failed");

        return;
      }

      setLesson(result.lesson);

      setSourceInfo({
        sourceType: result.source_type || "LLM",
        sources: result.sources || [],
      });

      await saveChapterProgress({
        username: user.username,
        grade,
        mode,
        subject,
        chapter,
        current_step_index: currentStepIndex,
        completed: false,
        last_lesson: result.lesson,
      });
    } catch {
      setError("Could not generate lesson. Check backend.");
    } finally {
      setGenerating(false);
    }
  }

  async function handleAskFollowUp() {
    if (!followUpQuestion.trim()) {
      return;
    }

    setFollowUpLoading(true);

    const userMessage = {
      role: "user",
      content: followUpQuestion,
    };

    setFollowUpMessages((prev) => [...prev, userMessage]);

    const questionToAsk = followUpQuestion;

    setFollowUpQuestion("");

    try {
      const result = await askLessonFollowUp({
        grade,
        mode,
        subject,
        chapter,
        step_title: stepTitle,
        lesson,
        question: questionToAsk,
      });

      if (!result.success) {
        setFollowUpMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: result.message || "Could not answer follow-up question.",
          },
        ]);

        return;
      }

      setFollowUpMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: result.answer,
          sourceType: result.source_type,
        },
      ]);
    } catch {
      setFollowUpMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Follow-up failed. Check backend.",
        },
      ]);
    } finally {
      setFollowUpLoading(false);
    }
  }
  // -----------------------------
  // READ ALOUD
  // -----------------------------
  async function handleReadAloud() {
    if (!lesson) return;

    setTtsLoading(true);
    setAudioUrl("");

    try {
      const url = await generateSpeech({
        text: lesson,
        voice: VOICE_OPTIONS[voiceName],
        rate: speechRate,
      });

      setAudioUrl(url);
    } catch {
      setError("Could not generate audio.");
    } finally {
      setTtsLoading(false);
    }
  }

  return (
    <div className="lesson-workspace">
      <div className="lesson-layout">
        <aside className="lesson-control-panel">
          <div className="card lesson-controls-card">
            <h3>Select Learning Path</h3>

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
                    setLesson("");
                    setAudioUrl("");
                    setSourceInfo(null);
                    setFollowUpQuestion("");
                    setFollowUpMessages([]);
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
                Lesson Step
                <select
                  value={currentStepIndex}
                  onChange={(e) => {
                    setCurrentStepIndex(Number(e.target.value));
                    setLesson("");
                    setAudioUrl("");
                    setFollowUpQuestion("");
                    setFollowUpMessages([]);
                  }}
                >
                  {lessonSteps.map((step, index) => (
                    <option key={step} value={index}>
                      Step {index + 1}: {step}
                    </option>
                  ))}
                </select>
              </label>

              <label>
                Teacher Persona
                <select
                  value={teacherPersona}
                  onChange={(e) => setTeacherPersona(e.target.value)}
                >
                  {Object.keys(TEACHER_PERSONAS).map((p) => (
                    <option key={p} value={p}>
                      {p}
                    </option>
                  ))}
                </select>
              </label>

              <label>
                Narration Voice
                <select
                  value={voiceName}
                  onChange={(e) => setVoiceName(e.target.value)}
                >
                  {Object.keys(VOICE_OPTIONS).map((v) => (
                    <option key={v} value={v}>
                      {v}
                    </option>
                  ))}
                </select>
              </label>

              <label>
                Narration Speed
                <select
                  value={speechRate}
                  onChange={(e) => setSpeechRate(e.target.value)}
                >
                  <option>-25%</option>
                  <option>-10%</option>
                  <option>+0%</option>
                  <option>+10%</option>
                  <option>+20%</option>
                </select>
              </label>
            </div>

            <div className="progress-box">
              <p>
                Step {currentStepIndex + 1} of {lessonSteps.length}:{" "}
                <strong>{stepTitle}</strong>
              </p>

              <progress value={currentStepIndex + 1} max={lessonSteps.length} />

              {completed && (
                <p className="success-text">🎉 This chapter is completed.</p>
              )}
            </div>

            <button
              className="primary-btn"
              onClick={handleGenerateLesson}
              disabled={generating}
            >
              {generating ? "Generating..." : "Generate Lesson"}
            </button>

            <div className="button-row">
              <button
                className="secondary-btn"
                disabled={currentStepIndex === 0}
                onClick={async () => {
                  const newIndex = currentStepIndex - 1;

                  setCurrentStepIndex(newIndex);
                  setLesson("");
                  setAudioUrl("");
                  setCompleted(false);

                  await saveChapterProgress({
                    username: user.username,
                    grade,
                    mode,
                    subject,
                    chapter,
                    current_step_index: newIndex,
                    completed: false,
                    last_lesson: "",
                  });
                }}
              >
                ⬅ Previous Step
              </button>

              <button
                className="secondary-btn"
                onClick={async () => {
                  const isLastStep = currentStepIndex >= lessonSteps.length - 1;

                  if (isLastStep) {
                    setCompleted(true);

                    await saveChapterProgress({
                      username: user.username,
                      grade,
                      mode,
                      subject,
                      chapter,
                      current_step_index: currentStepIndex,
                      completed: true,
                      last_lesson: lesson,
                    });
                  } else {
                    const newIndex = currentStepIndex + 1;

                    setCurrentStepIndex(newIndex);

                    setLesson("");
                    setAudioUrl("");

                    await saveChapterProgress({
                      username: user.username,
                      grade,
                      mode,
                      subject,
                      chapter,
                      current_step_index: newIndex,
                      completed: false,
                      last_lesson: "",
                    });
                  }
                }}
              >
                ✅ Mark Step Complete
              </button>

              <button
                className="secondary-btn"
                onClick={async () => {
                  setCurrentStepIndex(0);

                  setLesson("");
                  setAudioUrl("");

                  setCompleted(false);

                  await saveChapterProgress({
                    username: user.username,
                    grade,
                    mode,
                    subject,
                    chapter,
                    current_step_index: 0,
                    completed: false,
                    last_lesson: "",
                  });
                }}
              >
                🔄 Restart Chapter
              </button>
            </div>
          </div>
        </aside>

        <section className="lesson-content-panel">
          {error && <div className="error-box">{error}</div>}

          {lesson && (
            <>
              <div className="card lesson-output">
                <h3>Generated Lesson</h3>

                <div className="markdown-content">
                  <LessonSections lesson={lesson} />
                </div>

                <div className="lesson-action-footer">
                  <div className="lesson-source-badge">
                    {sourceInfo?.sourceType === "RAG"
                      ? "📚 RAG Powered"
                      : "🤖 LLM Generated"}
                  </div>

                  <button
                    className="primary-btn lesson-audio-btn"
                    onClick={handleReadAloud}
                    disabled={ttsLoading}
                  >
                    {ttsLoading ? "Generating Audio..." : "🔊 Listen to Lesson"}
                  </button>

                  {audioUrl && (
                    <div className="lesson-audio-player">
                      <audio controls src={audioUrl} />
                    </div>
                  )}
                </div>

                <div className="lesson-followup-box">
                  <div className="lesson-followup-header">
                    <h3>💬 Ask a follow-up</h3>
                    <p>Ask anything about this lesson step.</p>
                  </div>

                  {followUpMessages.length > 0 && (
                    <div className="lesson-chat-thread">
                      {followUpMessages.map((msg, index) => (
                        <div
                          key={index}
                          className={
                            msg.role === "user"
                              ? "chat-message user-message"
                              : "chat-message ai-message"
                          }
                        >
                          <strong>
                            {msg.role === "user" ? "You" : "AI Tutor"}
                          </strong>

                          <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {msg.content}
                          </ReactMarkdown>

                          {msg.sourceType && (
                            <span className="chat-source-chip">
                              {msg.sourceType === "RAG" ? "📚 RAG" : "🤖 LLM"}
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="lesson-followup-input">
                    <textarea
                      rows="4"
                      placeholder="Ask a follow-up question..."
                      value={followUpQuestion}
                      onChange={(e) => setFollowUpQuestion(e.target.value)}
                    />

                    <div className="followup-chip-row">
                      {[
                        "Explain in simpler words",
                        "Give an example",
                        "Why is this important?",
                        "Show a diagram",
                        "Ask more questions",
                      ].map((chip) => (
                        <button
                          key={chip}
                          type="button"
                          className="followup-chip"
                          onClick={() =>
                            setFollowUpQuestion((prev) =>
                              prev ? `${prev}\n${chip}` : chip
                            )
                          }
                        >
                          {chip}
                        </button>
                      ))}
                    </div>

                    <button
                      className="primary-btn followup-submit-btn"
                      onClick={handleAskFollowUp}
                      disabled={followUpLoading || !followUpQuestion.trim()}
                    >
                      {followUpLoading ? "Thinking..." : "✨ Ask AI Tutor"}
                    </button>
                  </div>
                </div>
              </div>

              {sourceInfo && (
                <div className="card">
                  <h3>📚 Source Information</h3>

                  <p>
                    <strong>Lesson Source:</strong>{" "}
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
            </>
          )}
        </section>
      </div>
    </div>
  );
}
export default LessonsPage;
