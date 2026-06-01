import { useEffect, useState } from "react";
import remarkGfm from "remark-gfm";
import ReactMarkdown from "react-markdown";
import MermaidBlock from "../components/MermaidBlock";

import { getSyllabus } from "../api/syllabus";
import { generateLesson, askLessonFollowUp } from "../api/lesson";
import { generateSpeech } from "../api/tts";
import { getChapterProgress, saveChapterProgress } from "../api/progress";
import { generateEducationalImage } from "../api/images";
import LessonSections from "../components/LessonSections";

import {
  evaluateStudentAnswer,
  generatePracticeQuestions,
} from "../api/evaluation";

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

  const [visualImage, setVisualImage] = useState("");
  const [visualLoading, setVisualLoading] = useState(false);
  const [visualTopic, setVisualTopic] = useState("");
  const [visualError, setVisualError] = useState("");

  const [practiceAnswers, setPracticeAnswers] = useState({});
  const [practiceEvaluations, setPracticeEvaluations] = useState({});
  const [practiceScores, setPracticeScores] = useState({});
  const [practicePassedMap, setPracticePassedMap] = useState({});
  const [practiceLoadingMap, setPracticeLoadingMap] = useState({});
  const [practicePassed, setPracticePassed] = useState(false);

  const [practiceQuestions, setPracticeQuestions] = useState([]);
  const [practiceQuestionsLoading, setPracticeQuestionsLoading] =
    useState(false);

  const lessonSteps = [
    "Concept introduction",
    "Core explanation",
    "Worked examples",
    "Practice questions",
    "Revision and recap",
  ];

  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [highestUnlockedStep, setHighestUnlockedStep] = useState(0);
  const [completed, setCompleted] = useState(false);

  const stepTitle = lessonSteps[currentStepIndex];

  const [teacherPersona, setTeacherPersona] = useState("Friendly Teacher");

  const [lesson, setLesson] = useState("");
  const [stepLessons, setStepLessons] = useState({});
  const [sourceInfo, setSourceInfo] = useState(null);
  const [generating, setGenerating] = useState(false);

  const [followUpQuestion, setFollowUpQuestion] = useState("");
  const [followUpMessages, setFollowUpMessages] = useState([]);
  const [followUpLoading, setFollowUpLoading] = useState(false);

  const [voiceName, setVoiceName] = useState("English India Female (Neerja)");
  const [speechRate, setSpeechRate] = useState("+0%");
  const [audioUrl, setAudioUrl] = useState("");
  const [ttsLoading, setTtsLoading] = useState(false);

  const [practiceModeActive, setPracticeModeActive] = useState(false);
  const [practiceFocusWarnings, setPracticeFocusWarnings] = useState(0);

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
    if (!practiceModeActive) {
      return;
    }

    let warningCooldown = false;

    function registerFocusWarning() {
      if (warningCooldown) {
        return;
      }

      warningCooldown = true;

      setPracticeFocusWarnings((prev) => prev + 1);

      setTimeout(() => {
        warningCooldown = false;
      }, 1500);
    }

    function handleVisibilityChange() {
      if (document.hidden) {
        registerFocusWarning();
      }
    }

    window.addEventListener("blur", registerFocusWarning);
    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      window.removeEventListener("blur", registerFocusWarning);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [practiceModeActive]);

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

        const progress = result.progress || {};

        const savedStepIndex = progress.current_step_index || 0;
        const savedHighestUnlockedStep =
          progress.highest_unlocked_step ?? savedStepIndex;
        const savedStepLessons = progress.step_lessons || {};

        setCurrentStepIndex(savedStepIndex);
        setHighestUnlockedStep(savedHighestUnlockedStep);
        setCompleted(progress.completed || false);
        setStepLessons(savedStepLessons);

        setLesson(
          savedStepLessons[String(savedStepIndex)] || progress.last_lesson || ""
        );

        setAudioUrl("");
        setVisualImage("");
        setVisualError("");
        setSourceInfo(null);
        setFollowUpQuestion("");
        setFollowUpMessages([]);
        resetPracticeState();
      } catch {
        console.error("Could not load progress");
      }
    }

    loadProgress();
  }, [grade, mode, subject, chapter, user.username]);

  if (loading) {
    return <p>Loading syllabus...</p>;
  }

  if (error && !lesson) {
    return <p className="error">{error}</p>;
  }

  const grades = Object.keys(syllabusData);
  const modes = Object.keys(syllabusData[grade]);

  function getAllowedSubjects(allSubjects, selectedMode) {
    if (user.role === "admin") return allSubjects;

    if (selectedMode === "CBSE") {
      return user.accessCbse ? allSubjects : [];
    }

    if (selectedMode === "SOF") {
      return allSubjects.filter((subjectName) => {
        if (subjectName === "Science Olympiad") return user.accessSofScience;
        if (subjectName === "Maths Olympiad") return user.accessSofMaths;
        if (subjectName === "English Olympiad") return user.accessSofEnglish;
        return false;
      });
    }

    return [];
  }

  const allSubjects = Object.keys(syllabusData[grade][mode]);
  const subjects = getAllowedSubjects(allSubjects, mode);
  const chapters = subject ? syllabusData[grade][mode][subject] || [] : [];

  function resetLessonState() {
    setLesson("");
    setAudioUrl("");
    setVisualImage("");
    setVisualError("");
    setSourceInfo(null);
    setFollowUpQuestion("");
    setFollowUpMessages([]);
    resetPracticeState();
  }

  function handleGradeChange(value) {
    const newMode = Object.keys(syllabusData[value])[0];
    const newSubject = Object.keys(syllabusData[value][newMode])[0];
    const newChapter = syllabusData[value][newMode][newSubject][0];

    setGrade(value);
    setMode(newMode);
    setSubject(newSubject);
    setChapter(newChapter);
    resetLessonState();
  }

  function handleModeChange(value) {
    const allModeSubjects = Object.keys(syllabusData[grade][value]);
    const allowedModeSubjects = getAllowedSubjects(allModeSubjects, value);

    if (allowedModeSubjects.length === 0) {
      setMode(value);
      setSubject("");
      setChapter("");
      setError(`You do not have access to ${value} lessons.`);
      resetLessonState();
      return;
    }

    const newSubject = allowedModeSubjects[0];
    const newChapter = syllabusData[grade][value][newSubject][0];

    setError("");
    setMode(value);
    setSubject(newSubject);
    setChapter(newChapter);
    resetLessonState();
  }

  function handleSubjectChange(value) {
    const newChapter = syllabusData[grade][mode][value][0];

    setSubject(value);
    setChapter(newChapter);
    resetLessonState();
  }

  function shouldSkipPracticeRequirement() {
    return subject === "Hindi" || subject === "Sanskrit";
  }
  
  function isMathSubject() {
    return subject === "Maths" || subject === "Maths Olympiad";
  }
  
  function getMinimumPracticeWords() {
    return isMathSubject() ? 1 : 100;
  }

  function resetPracticeState() {
    setPracticeQuestions([]);
    setPracticeAnswers({});
    setPracticeEvaluations({});
    setPracticeScores({});
    setPracticePassedMap({});
    setPracticeLoadingMap({});
    setPracticePassed(false);
    setPracticeModeActive(false);
    setPracticeFocusWarnings(0);
  }

  async function handleGenerateLesson() {
    setGenerating(true);
    setLesson("");
    setAudioUrl("");
    setVisualImage("");
    setVisualError("");
    setSourceInfo(null);
    setError("");
    setFollowUpQuestion("");
    setFollowUpMessages([]);
    resetPracticeState();
  
    try {
      const result = await generateLesson({
        username: user.username,
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
  
      const updatedStepLessons = {
        ...stepLessons,
        [String(currentStepIndex)]: result.lesson,
      };
  
      setStepLessons(updatedStepLessons);
  
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
        highest_unlocked_step: highestUnlockedStep,
        completed: false,
        last_lesson: result.lesson,
        step_lessons: updatedStepLessons,
      });
    } catch (err) {
      setError(err.message || "Could not generate lesson. Check backend.");
    } finally {
      setGenerating(false);
    }
  }


  async function handleAskFollowUp() {
    if (!followUpQuestion.trim() || practiceModeActive) {
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
        username: user.username,
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
    } catch (error) {
      setFollowUpMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: error.message || "Follow-up failed. Check backend.",
        },
      ]);
    } finally {
      setFollowUpLoading(false);
    }
  }

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

  async function handleGenerateVisual() {
    const topic = visualTopic.trim();

    if (!lesson && !topic) return;

    setVisualLoading(true);
    setVisualImage("");
    setVisualError("");

    try {
      const imagePrompt = topic
        ? `${subject} - ${chapter}. Create a clear educational visual specifically about: ${topic}`
        : `${subject} - ${chapter} - ${stepTitle}. Create a visual explanation for this lesson: ${lesson.slice(
            0,
            1200
          )}`;

      const result = await generateEducationalImage(imagePrompt, user.username);

      if (!result.success) {
        setVisualError(result.message || "Visual generation failed.");
        return;
      }

      setVisualImage(`data:image/png;base64,${result.image_base64}`);
    } catch {
      setVisualError("Could not generate visual explanation.");
    } finally {
      setVisualLoading(false);
    }
  }

  const hasSavedLesson = Boolean(stepLessons[String(currentStepIndex)]);

  async function handleGeneratePracticeQuestions() {
    if (!lesson) {
      return;
    }

    setPracticeQuestionsLoading(true);
    setPracticeQuestions([]);
    setPracticeAnswers({});
    setPracticeEvaluations({});
    setPracticeScores({});
    setPracticePassedMap({});
    setPracticeLoadingMap({});
    setPracticePassed(false);
    setPracticeFocusWarnings(0);

    try {
      const result = await generatePracticeQuestions({
        username: user.username,
        question: chapter,
        student_answer: "",
        ideal_context: lesson,
      });

      if (!result.success) {
        setPracticeQuestions([
          "Explain the main concept from this lesson in your own words.",
          "Give one real-life example or application of this concept.",
        ]);
        setPracticeModeActive(true);
        return;
      }

      setPracticeQuestions(result.questions || []);
      setPracticeModeActive(true);
    } catch {
      setPracticeQuestions([
        "Explain the main concept from this lesson in your own words.",
        "Give one real-life example or application of this concept.",
      ]);
      setPracticeModeActive(true);
    } finally {
      setPracticeQuestionsLoading(false);
    }
  }

  async function handleEvaluatePracticeAnswer(question, index) {
    const answer = practiceAnswers[index] || "";

    const minimumWords = getMinimumPracticeWords();

    if (!answer.trim() || countWords(answer) < minimumWords) {
      return;
    }

    setPracticeLoadingMap((prev) => ({
      ...prev,
      [index]: true,
    }));

    setPracticeEvaluations((prev) => ({
      ...prev,
      [index]: "",
    }));

    setPracticeScores((prev) => ({
      ...prev,
      [index]: 0,
    }));

    setPracticePassedMap((prev) => ({
      ...prev,
      [index]: false,
    }));

    try {
      const result = await evaluateStudentAnswer({
        username: user.username,
        question,
        student_answer: answer,
        ideal_context: lesson,
      });

      if (!result.success) {
        setPracticeEvaluations((prev) => ({
          ...prev,
          [index]: result.message || "Could not evaluate answer.",
        }));
        return;
      }

      setPracticeEvaluations((prev) => ({
        ...prev,
        [index]: result.evaluation || "",
      }));

      setPracticeScores((prev) => ({
        ...prev,
        [index]: result.score || 0,
      }));

      setPracticePassedMap((prev) => ({
        ...prev,
        [index]: result.passed || false,
      }));

      if (result.passed) {
        setPracticePassed(true);
        setPracticeModeActive(false);
      }
    } catch {
      setPracticeEvaluations((prev) => ({
        ...prev,
        [index]: "Could not evaluate answer. Check backend.",
      }));
    } finally {
      setPracticeLoadingMap((prev) => ({
        ...prev,
        [index]: false,
      }));
    }
  }
  
  function countWords(text) {
    return text.trim().split(/\s+/).filter(Boolean).length;
  }

  return (
    <div className="lesson-workspace premium-page premium-lessons-page">
      <div className="lesson-layout premium-lesson-layout">
        <aside className="lesson-control-panel">
          <div className="premium-section premium-lesson-controls">
            <div className="premium-header">
              <p className="eyebrow">Learning Path</p>
              <h3>📚 Select Lesson Setup</h3>
              <p>Choose grade, subject, step, persona, and narration style.</p>
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
                  disabled={subjects.length === 0}
                >
                  {subjects.length === 0 ? (
                    <option value="">No access available</option>
                  ) : (
                    subjects.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))
                  )}
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
                    setVisualImage("");
                    setSourceInfo(null);
                    setFollowUpQuestion("");
                    setFollowUpMessages([]);
                    resetPracticeState();
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
                    const newIndex = Number(e.target.value);
                    setCurrentStepIndex(newIndex);
                    setLesson(stepLessons[String(newIndex)] || "");
                    setAudioUrl("");
                    setVisualImage("");
                    setVisualError("");
                    setFollowUpQuestion("");
                    setFollowUpMessages([]);
                    resetPracticeState();
                  }}
                >
                  {lessonSteps.map((step, index) => (
                    <option
                      key={step}
                      value={index}
                      disabled={index > highestUnlockedStep}
                    >
                      {index > highestUnlockedStep ? "🔒 " : ""}
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

            <div className="progress-box premium-progress-box">
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
              className="primary-btn premium-generate-btn"
              onClick={handleGenerateLesson}
              disabled={generating || hasSavedLesson}
            >
              {hasSavedLesson
                ? "Lesson Already Generated"
                : generating
                ? "Generating..."
                : "✨ Generate Lesson"}
            </button>

            <div className="button-row premium-lesson-button-row">
              <button
                className="secondary-btn"
                disabled={currentStepIndex === 0}
                onClick={async () => {
                  const newIndex = currentStepIndex - 1;

                  setCurrentStepIndex(newIndex);
                  setLesson(stepLessons[String(newIndex)] || "");
                  setAudioUrl("");
                  setVisualImage("");
                  setVisualError("");
                  setCompleted(false);
                  resetPracticeState();

                  await saveChapterProgress({
                    username: user.username,
                    grade,
                    mode,
                    subject,
                    chapter,
                    current_step_index: newIndex,
                    highest_unlocked_step: highestUnlockedStep,
                    completed: false,
                    last_lesson: "",
                    step_lessons: stepLessons,
                  });
                }}
              >
                ⬅ Previous Step
              </button>

              <button
                className="secondary-btn"
                disabled={!practicePassed && !shouldSkipPracticeRequirement()}
                title={
                  practicePassed || shouldSkipPracticeRequirement()
                    ? "You can complete this step."
                    : "Write and pass practice answer first."
                }
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
                      highest_unlocked_step: highestUnlockedStep,
                      completed: true,
                      last_lesson: lesson,
                      step_lessons: stepLessons,
                    });
                  } else {
                    const newIndex = currentStepIndex + 1;

                    const newHighestUnlockedStep = Math.max(
                      highestUnlockedStep,
                      newIndex
                    );

                    setHighestUnlockedStep(newHighestUnlockedStep);
                    setCurrentStepIndex(newIndex);
                    setLesson(stepLessons[String(newIndex)] || "");
                    setAudioUrl("");
                    setVisualImage("");
                    setVisualError("");
                    resetPracticeState();

                    await saveChapterProgress({
                      username: user.username,
                      grade,
                      mode,
                      subject,
                      chapter,
                      current_step_index: newIndex,
                      highest_unlocked_step: newHighestUnlockedStep,
                      completed: false,
                      last_lesson: "",
                      step_lessons: stepLessons,
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
                  setHighestUnlockedStep(0);
                  setLesson("");
                  setAudioUrl("");
                  setVisualImage("");
                  setCompleted(false);
                  resetPracticeState();

                  await saveChapterProgress({
                    username: user.username,
                    grade,
                    mode,
                    subject,
                    chapter,
                    current_step_index: 0,
                    highest_unlocked_step: 0,
                    completed: false,
                    last_lesson: "",
                    step_lessons: {},
                  });
                }}
              >
                🔄 Restart Chapter
              </button>
            </div>
          </div>
        </aside>

        <section className="lesson-content-panel premium-lesson-content">
          {error && <div className="error-box">{error}</div>}

          {!lesson && !generating && (
            <div className="premium-section premium-empty-lesson">
              <div className="premium-header">
                <p className="eyebrow">Ready when you are</p>
                <h2>Start your next AI-guided lesson</h2>
                <p>
                  Pick a lesson step from the left panel and generate a focused,
                  step-wise explanation with narration, visuals, and follow-up
                  support.
                </p>
              </div>

              <div className="premium-grid premium-grid-3">
                <div className="premium-card premium-glow-card glow-blue">
                  <h3>📘 Focused Lessons</h3>
                  <p>Learn one sub-topic at a time without chapter overload.</p>
                </div>

                <div className="premium-card premium-glow-card glow-purple">
                  <h3>🔊 Narration</h3>
                  <p>Listen to lessons aloud using your selected voice.</p>
                </div>

                <div className="premium-card premium-glow-card glow-green">
                  <h3>🖼 AI Visuals</h3>
                  <p>Create custom educational visuals for any topic.</p>
                </div>
              </div>
            </div>
          )}

          {lesson && (
            <>
              <div className="premium-section lesson-output premium-lesson-output">
                <div className="premium-header lesson-output-header">
                  <p className="eyebrow">
                    {sourceInfo?.sourceType === "RAG"
                      ? "Textbook aligned"
                      : "AI generated"}
                  </p>
                  <h3>Generated Lesson</h3>
                  <p>
                    Step {currentStepIndex + 1}: {stepTitle}
                  </p>
                </div>

                <div className="markdown-content">
                  <LessonSections lesson={lesson} />
                </div>

                <div className="lesson-audio-section premium-card">
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

                {!shouldSkipPracticeRequirement() && (
                  <div className="lesson-practice-card">
                    {practiceFocusWarnings > 0 && (
                      <div className="practice-warning-banner">
                        ⚠️ Focus warning {practiceFocusWarnings}: Please stay on
                        this page while answering. Practice works best when you
                        recall from memory.
                      </div>
                    )}

                    {practiceModeActive && (
                      <div className="practice-focus-banner">
                        ✍️ Practice Mode Active — AI follow-up help is
                        temporarily disabled. Try answering from memory like a
                        real exam.
                      </div>
                    )}

                    <div className="lesson-followup-header">
                      <h3>✍️ Write & Practice</h3>
                      <p>
                        Write your own answer first. AI will evaluate it like an
                        examiner.
                      </p>
                    </div>

                    <button
                      className="secondary-btn"
                      onClick={handleGeneratePracticeQuestions}
                      disabled={practiceQuestionsLoading}
                    >
                      {practiceQuestionsLoading
                        ? "Creating practice questions..."
                        : "🎲 Generate 2 Practice Questions"}
                    </button>

                    {practiceQuestions.length > 0 && (
                      <div className="practice-question-list">
                        {practiceQuestions.map((q, index) => {
                          const currentAnswer = practiceAnswers[index] || "";
                          const currentWordCount = countWords(currentAnswer);
                          const minimumWords = getMinimumPracticeWords();
                          const currentEvaluation =
                            practiceEvaluations[index] || "";
                          const currentScore = practiceScores[index] || 0;
                          const currentPassed =
                            practicePassedMap[index] || false;
                          const currentLoading =
                            practiceLoadingMap[index] || false;

                          return (
                            <div
                              key={index}
                              className="practice-question-card workbook-card"
                            >
                              <strong>Question {index + 1}</strong>
                              <span>{q}</span>

                              <textarea
                                rows="6"
                                value={currentAnswer}
                                placeholder={
                                  isMathSubject()
                                    ? "Write your final answer and short working here..."
                                    : "Write your answer here in at least 100 words..."
                                }
                                onChange={(e) =>
                                  setPracticeAnswers((prev) => ({
                                    ...prev,
                                    [index]: e.target.value,
                                  }))
                                }
                              />

                              <p className="practice-word-count">
                                {isMathSubject()
                                  ? `Answer length: ${currentWordCount} word(s)`
                                  : `Words: ${currentWordCount} / ${minimumWords}`}
                              </p>

                              <button
                                className="primary-btn"
                                disabled={
                                  currentLoading ||
                                  currentWordCount < minimumWords
                                }
                                onClick={() =>
                                  handleEvaluatePracticeAnswer(q, index)
                                }
                              >
                                {currentLoading
                                  ? "Evaluating..."
                                  : currentWordCount < minimumWords
                                  ? isMathSubject()
                                    ? "Write your answer"
                                    : `Write at least ${minimumWords} words`
                                  : "Evaluate This Answer"}
                              </button>

                              {currentEvaluation && (
                                <div className="mentor-followup-answer markdown-content">
                                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                    {currentEvaluation}
                                  </ReactMarkdown>
                                </div>
                              )}

                              {currentEvaluation && (
                                <div
                                  className={
                                    currentPassed
                                      ? "practice-status-box passed"
                                      : "practice-status-box retry"
                                  }
                                >
                                  <strong>
                                    {currentPassed
                                      ? "✅ Practice Passed"
                                      : "🔁 Retry Needed"}
                                  </strong>

                                  <p>
                                    Score: {currentScore}/10.{" "}
                                    {currentPassed
                                      ? "You can now mark this step complete."
                                      : "Improve your answer and try again. You need 8/10 to continue."}
                                  </p>
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                )}

                <div className="visual-generator-card premium-card premium-glow-card glow-purple">
                  <div className="visual-generator-header">
                    <h3>🖼 Visual Generator</h3>

                    <p>
                      Generate a custom educational visual for this lesson or
                      topic.
                    </p>
                  </div>

                  <div className="visual-generator-controls">
                    <input
                      className="visual-topic-input"
                      type="text"
                      placeholder="Example: how friction affects motion in daily life"
                      value={visualTopic}
                      onChange={(e) => setVisualTopic(e.target.value)}
                    />

                    <button
                      className="secondary-btn visual-generate-btn"
                      onClick={handleGenerateVisual}
                      disabled={visualLoading}
                    >
                      {visualLoading ? "Generating..." : "🖼 Generate Visual"}
                    </button>
                  </div>

                  {visualError && (
                    <div className="visual-error-box">{visualError}</div>
                  )}
                </div>

                {visualImage && (
                  <div className="visual-image-card premium-card">
                    <div className="visual-image-header">
                      <h3>🖼 Visual Explanation</h3>
                    </div>

                    <img
                      src={visualImage}
                      alt="AI generated educational visual"
                    />
                  </div>
                )}

                <div
                  className={
                    practiceModeActive
                      ? "lesson-followup-box disabled-practice-mode"
                      : "lesson-followup-box"
                  }
                >
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

                          <ReactMarkdown
                            remarkPlugins={[remarkGfm]}
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
                      disabled={practiceModeActive}
                      placeholder={
                        practiceModeActive
                          ? "Practice mode active. Complete written practice first."
                          : "Ask a follow-up question..."
                      }
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
                          disabled={practiceModeActive}
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
                      disabled={
                        practiceModeActive ||
                        followUpLoading ||
                        !followUpQuestion.trim()
                      }
                    >
                      {followUpLoading ? "Thinking..." : "✨ Ask AI Tutor"}
                    </button>
                  </div>
                </div>
              </div>

              {sourceInfo && (
                <div className="premium-section">
                  <div className="premium-header">
                    <h3>📚 Source Information</h3>

                    <p>
                      <strong>Lesson Source:</strong>{" "}
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