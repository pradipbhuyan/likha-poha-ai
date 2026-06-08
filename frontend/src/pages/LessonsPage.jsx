import { useEffect, useState } from "react";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import ReactMarkdown from "react-markdown";
import StructuredVisualBlock from "../components/StructuredVisualBlock";

import { getSyllabus } from "../api/syllabus";
import { generateLesson, askLessonFollowUp } from "../api/lesson";
import { getDoubtHistory } from "../api/doubt";
import { generateSpeech } from "../api/tts";
import { getChapterProgress, saveChapterProgress } from "../api/progress";
import { generateEducationalImage } from "../api/images";
import LessonSections from "../components/LessonSections";
import { saveWeakAreaAlert } from "../api/weakAreaAlerts";

import {
  evaluateStudentAnswer,
  generatePracticeQuestions,
} from "../api/evaluation";
import {
  getDefaultSelection,
  getUserBoard,
  getUserGrade,
  getVisibleGrades,
} from "../utils/syllabusDefaults";
import { normalizeTutorMarkdown } from "../utils/markdownCleanup";
import { filterAllowedSubjects } from "../utils/subjectAccess";

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

const MATH_VISUAL_AID_SUGGESTIONS = [
  "Number line with examples marked",
  "Fraction bars or area model",
  "Coordinate plane sketch",
  "Geometry shape with key parts",
  "Graph of a simple relation",
  "Step diagram for solving",
];

const SCIENCE_VISUAL_AID_SUGGESTIONS = [
  "Process flow with arrows",
  "Cause and effect scene",
  "Experiment setup sketch",
  "Cycle or sequence diagram",
  "Classification tree",
  "Real-life example scene",
];

function isHindiSubjectName(subject) {
  /** Identify Hindi subjects so practice can stay objective and lightweight. */
  return subject === "Hindi" || subject === "Hindi Olympiad";
}

function buildPracticeFallbackQuestions(subject) {
  /** Keep practice usable if the backend cannot generate structured questions. */
  const isMath =
    subject === "Maths" ||
    subject === "Maths Olympiad" ||
    subject === "Mathematics";

  if (isMath || isHindiSubjectName(subject)) {
    return [
      {
        type: "mcq",
        question: isHindiSubjectName(subject)
          ? "पाठ पढ़ते समय सबसे अच्छा तरीका क्या है?"
          : "Which option best describes how to use this lesson idea?",
        options: [
          isHindiSubjectName(subject)
            ? "मुख्य विचार समझकर उदाहरण से जोड़ना।"
            : "Apply the rule step by step and check the answer.",
          isHindiSubjectName(subject)
            ? "केवल शीर्षक याद करना।"
            : "Memorise only the heading.",
          isHindiSubjectName(subject)
            ? "प्रश्न को बिना पढ़े उत्तर चुनना।"
            : "Ignore the working.",
          isHindiSubjectName(subject)
            ? "सबसे लंबा विकल्प चुनना।"
            : "Choose the longest option.",
        ],
        answer: isHindiSubjectName(subject)
          ? "मुख्य विचार समझकर उदाहरण से जोड़ना।"
          : "Apply the rule step by step and check the answer.",
        explanation: isHindiSubjectName(subject)
          ? "हिंदी में अच्छा उत्तर मुख्य विचार, पात्र या प्रसंग, और एक छोटा उदाहरण जोड़कर लिखा जाता है।"
          : "Maths practice is strongest when you identify the rule, apply it, and check each step.",
        expected_keywords: isHindiSubjectName(subject)
          ? ["मुख्य विचार", "उदाहरण", "पूरा वाक्य"]
          : ["rule", "step", "check"],
      },
      {
        type: "mcq",
        question: isHindiSubjectName(subject)
          ? "हिंदी उत्तर लिखते समय कौन-सी बात सबसे उपयोगी है?"
          : "What is the best habit before finalising a maths answer?",
        options: [
          isHindiSubjectName(subject)
            ? "स्पष्ट, पूरे वाक्यों में उत्तर लिखना।"
            : "Check signs, values, and the method used.",
          isHindiSubjectName(subject)
            ? "बहुत छोटे और अधूरे शब्द लिखना।"
            : "Skip the final check.",
          isHindiSubjectName(subject)
            ? "प्रश्न से अलग बात लिखना।"
            : "Write only the answer without thinking.",
          isHindiSubjectName(subject)
            ? "पाठ के संदर्भ को छोड़ देना।"
            : "Ignore the question condition.",
        ],
        answer: isHindiSubjectName(subject)
          ? "स्पष्ट, पूरे वाक्यों में उत्तर लिखना।"
          : "Check signs, values, and the method used.",
        explanation: isHindiSubjectName(subject)
          ? "उत्तर लिखते समय स्पष्ट वाक्य, पाठ से जुड़ा कारण, और सही शब्द चयन जरूरी होता है।"
          : "Checking signs, values, and method helps catch common mistakes before submission.",
        expected_keywords: isHindiSubjectName(subject)
          ? ["स्पष्ट वाक्य", "कारण", "पाठ"]
          : ["signs", "values", "method"],
      },
    ];
  }

  return [
    {
      type: "mcq",
      question: "Which option best captures the main idea from this lesson?",
      options: [
        "The concept explains an idea and how it is used.",
        "The concept is only a heading.",
        "The concept has no examples.",
        "The concept cannot be explained simply.",
      ],
      answer: "The concept explains an idea and how it is used.",
      explanation:
        "A strong answer connects the concept with a use, reason, or example.",
      expected_keywords: ["concept", "use", "example"],
    },
    {
      type: "descriptive",
      question:
        "Explain the main concept from this lesson in your own words. Add one example if possible.",
      expected_keywords: ["concept", "example", "reason"],
    },
  ];
}

function normalizePracticeQuestion(question, subject) {
  /** Accept both legacy string questions and the newer structured question format. */
  if (typeof question === "string") {
    return {
      type: "descriptive",
      question,
      options: [],
      answer: "",
      explanation: "",
      expected_keywords: [],
    };
  }

  if (!question || typeof question !== "object") {
    return buildPracticeFallbackQuestions(subject)[0];
  }

  const options = Array.isArray(question.options)
    ? question.options.slice(0, 4)
    : [];
  const type = question.type === "mcq" && options.length >= 2
    ? "mcq"
    : "descriptive";

  return {
    type,
    question: question.question || "Answer this practice question.",
    options,
    answer: question.answer || question.correct_answer || "",
    explanation: question.explanation || "",
    expected_keywords: Array.isArray(question.expected_keywords)
      ? question.expected_keywords
      : [],
  };
}

function LessonsPage({ user }) {
  /** Student lesson workspace with AI lessons, progress, audio, visuals, follow-ups, and coaching practice. */
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
  const [practiceAttemptCount, setPracticeAttemptCount] = useState(0);
  const [practiceBestScore, setPracticeBestScore] = useState(0);
  const [allowContinueAnyway, setAllowContinueAnyway] = useState(false);

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
  const [lessonDoubtHistory, setLessonDoubtHistory] = useState([]);
  const [followUpLoading, setFollowUpLoading] = useState(false);

  const [voiceName, setVoiceName] = useState("English India Female (Neerja)");
  const [speechRate, setSpeechRate] = useState("+0%");
  const [audioUrl, setAudioUrl] = useState("");
  const [ttsLoading, setTtsLoading] = useState(false);

  const [practiceModeActive, setPracticeModeActive] = useState(false);
  const [practiceFocusWarnings, setPracticeFocusWarnings] = useState(0);

  useEffect(() => {
    async function loadSyllabus() {
      /** Load syllabus data and initialize the lesson selectors to the default topic. */
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
        const defaultSubjects = Object.keys(
          data.syllabus[defaultGrade]?.[defaultMode] || {}
        );
        const allowedDefaultSubjects = filterAllowedSubjects(
          user,
          defaultSubjects,
          defaultMode
        );
        let selectedMode = defaultMode;
        let selectedSubject = allowedDefaultSubjects.includes(defaultSubject)
          ? defaultSubject
          : allowedDefaultSubjects[0] || "";

        if (!selectedSubject) {
          selectedMode =
            Object.keys(data.syllabus[defaultGrade] || {}).find((modeName) => {
              const modeSubjects = Object.keys(
                data.syllabus[defaultGrade]?.[modeName] || {}
              );
              return filterAllowedSubjects(user, modeSubjects, modeName).length > 0;
            }) || defaultMode;
          selectedSubject =
            filterAllowedSubjects(
              user,
              Object.keys(data.syllabus[defaultGrade]?.[selectedMode] || {}),
              selectedMode
            )[0] || "";
        }
        const selectedChapter =
          selectedSubject === defaultSubject
            ? defaultChapter
            : data.syllabus[defaultGrade]?.[selectedMode]?.[selectedSubject]?.[0] || "";

        setGrade(defaultGrade);
        setMode(selectedMode);
        setSubject(selectedSubject);
        setChapter(selectedChapter);
      } catch {
        setError("Could not load syllabus");
      } finally {
        setLoading(false);
      }
    }

    loadSyllabus();
  }, []);

  useEffect(() => {
    loadLessonDoubtHistory();
  }, [user?.username]);

  async function loadLessonDoubtHistory() {
    /** Load recent saved follow-up doubts asked from the Lessons page. */
    try {
      const result = await getDoubtHistory(30);
      const lessonHistory = (result.history || []).filter((item) =>
        ["LESSON_FOLLOW_UP", "LESSON_PLATFORM_RAG"].includes(item.source_type)
      );

      setLessonDoubtHistory(lessonHistory);
    } catch {
      // Lesson history is a convenience feature and should never block lessons.
    }
  }

  useEffect(() => {
    if (!practiceModeActive) {
      return;
    }

    let warningCooldown = false;

    function registerFocusWarning() {
      /** Count focus loss during practice mode to discourage switching away mid-answer. */
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
      /** Treat hidden browser tabs as practice focus warnings. */
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
      /** Restore saved lesson step, generated content, and completion state for the selected chapter. */
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

  const grades = getVisibleGrades(syllabusData, user);
  const modes = Object.keys(syllabusData[grade]);

  function getAllowedSubjects(allSubjects, selectedMode) {
    /** Filter subjects by the student's subscription access for CBSE and SOF modes. */
    return filterAllowedSubjects(user, allSubjects, selectedMode);
  }

  const allSubjects = Object.keys(syllabusData[grade][mode]);
  const subjects = getAllowedSubjects(allSubjects, mode);
  const chapters = subject ? syllabusData[grade][mode][subject] || [] : [];
  const requestBoard = mode === "SOF" ? getUserBoard(user) : mode;

  function resetLessonState() {
    /** Clear generated lesson artifacts when the selected topic changes. */
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
    /** Reset mode, subject, chapter, and generated content after changing grade. */
    const gradeModes = Object.keys(syllabusData[value]);
    const newMode =
      gradeModes.find((modeName) => {
        const modeSubjects = Object.keys(syllabusData[value][modeName] || {});
        return getAllowedSubjects(modeSubjects, modeName).length > 0;
      }) || gradeModes[0];
    const allowedModeSubjects = getAllowedSubjects(
      Object.keys(syllabusData[value][newMode] || {}),
      newMode
    );
    const newSubject = allowedModeSubjects[0] || "";
    const newChapter = newSubject
      ? syllabusData[value][newMode][newSubject][0]
      : "";

    setGrade(value);
    setMode(newMode);
    setSubject(newSubject);
    setChapter(newChapter);
    setError(newSubject ? "" : `You do not have access to ${newMode} lessons.`);
    resetLessonState();
  }

  function handleModeChange(value) {
    /** Switch learning mode while enforcing subject-level access. */
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
    /** Select a new subject and reset the chapter to its first available lesson. */
    const newChapter = syllabusData[grade][mode][value][0];

    setSubject(value);
    setChapter(newChapter);
    resetLessonState();
  }

  function shouldSkipPracticeRequirement() {
    /** Practice is available for every subject and no longer gates progression. */
    return false;
  }
  
  function isMathSubject() {
    /** Identify math subjects so numeric answers are not forced into long prose. */
    return subject === "Maths" || subject === "Maths Olympiad";
  }

  function isHindiSubject() {
    /** Hindi lessons use objective checks and skip lesson chat follow-ups. */
    return isHindiSubjectName(subject);
  }

  function isScienceSubject() {
    /** Identify science subjects for useful visual-aid suggestions. */
    return subject === "Science" || subject === "Science Olympiad";
  }

  function isVisualSubject() {
    /** Restrict image generation to subjects where conceptual visuals add real value. */
    return (
      subject === "Science" ||
      subject === "Maths" ||
      subject === "Science Olympiad" ||
      subject === "Maths Olympiad"
    );
  }

  function getVisualPlaceholder() {
    /** Give subject-specific prompt examples so students ask for useful visuals. */
    if (isMathSubject()) {
      return "Example: show rational numbers on a number line";
    }

    if (isScienceSubject()) {
      return "Example: show osmosis as water movement through a membrane";
    }

    return "Example: how friction affects motion in daily life";
  }

  function getVisualAidSuggestions() {
    /** Choose useful visual prompt starters by subject type. */
    if (isMathSubject()) return MATH_VISUAL_AID_SUGGESTIONS;
    if (isScienceSubject()) return SCIENCE_VISUAL_AID_SUGGESTIONS;
    return [];
  }

  function getVisualAidHeading() {
    /** Label the visual suggestions in a subject-specific way. */
    return isMathSubject()
      ? "Best Maths visual aids to ask for"
      : "Best Science visual aids to ask for";
  }

  function getVisualAidWarning() {
    /** Explain how to spend image tokens on visuals that improve learning. */
    return isMathSubject()
      ? "Avoid asking for formula posters. Ask for a model that shows the idea visually."
      : "Avoid asking for decorative pictures. Ask for a process, setup, cycle, or cause-effect visual.";
  }

  function getMinimumPracticeWords() {
    /** Practice has no word limit; any thoughtful answer can be evaluated. */
    return 1;
  }

  function resetPracticeState() {
    /** Clear all practice questions, evaluations, scores, and focus warnings. */
    setPracticeQuestions([]);
    setPracticeAnswers({});
    setPracticeEvaluations({});
    setPracticeScores({});
    setPracticePassedMap({});
    setPracticeLoadingMap({});
    setPracticePassed(false);
    setPracticeAttemptCount(0);
    setPracticeBestScore(0);
    setAllowContinueAnyway(false);
    setPracticeModeActive(false);
    setPracticeFocusWarnings(0);
  }

  async function handleGenerateLesson() {
    /** Generate one lesson step, save it to progress, and store RAG source metadata. */
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
        board: requestBoard,
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
        board: requestBoard,
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
    /** Ask a follow-up about the current lesson unless practice mode is active. */
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

      loadLessonDoubtHistory();
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

  function handleOpenLessonHistory(item) {
    /** Restore a saved lesson follow-up into the current lesson chat thread. */
    setFollowUpMessages([
      {
        role: "user",
        content: item.question || "",
      },
      {
        role: "assistant",
        content: item.answer || "",
        sourceType:
          item.source_type === "LESSON_PLATFORM_RAG"
            ? "PLATFORM_RAG"
            : item.source_type,
      },
    ]);
  }

  async function handleReadAloud() {
    /** Convert the current lesson into speech using the selected voice and rate. */
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
    /** Generate an educational image for a custom topic or the current lesson step. */
    const topic = visualTopic.trim();

    if (!isVisualSubject()) {
      setVisualError(
        "Visual generation is available only for Science and Maths."
      );
      return;
    }

    if (!lesson && !topic) return;

    setVisualLoading(true);
    setVisualImage("");
    setVisualError("");

    try {
      const imagePrompt = topic
        ? `${grade} ${subject} - ${chapter}. Create a clear educational visual specifically about: ${topic}`
        : `${grade} ${subject} - ${chapter} - ${stepTitle}. Create a visual explanation for this lesson: ${lesson.slice(
            0,
            1200
          )}`;

      const result = await generateEducationalImage(imagePrompt, user.username, {
        grade,
        mode,
        subject,
        chapter,
      });

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
    /** Create practice questions from the lesson, with local fallback prompts if AI fails. */
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
      const fallbackQuestions = buildPracticeFallbackQuestions(subject);
      const result = await generatePracticeQuestions({
        grade,
        mode,
        subject,
        chapter,
        step_title: stepTitle,
        username: user.username,
        question: chapter,
        student_answer: "",
        ideal_context: lesson,
      });

      if (!result.success) {
        setPracticeQuestions(fallbackQuestions);
        setPracticeModeActive(true);
        return;
      }

      let normalizedQuestions = (result.questions || [])
        .map((item) => normalizePracticeQuestion(item, subject))
        .slice(0, 2);

      if (isHindiSubject()) {
        normalizedQuestions = [
          ...normalizedQuestions.filter((item) => item.type === "mcq"),
          ...fallbackQuestions,
        ].slice(0, 2);
      }

      setPracticeQuestions(
        normalizedQuestions.length
          ? normalizedQuestions
          : fallbackQuestions
      );
      setPracticeModeActive(true);
    } catch {
      setPracticeQuestions(buildPracticeFallbackQuestions(subject));
      setPracticeModeActive(true);
    } finally {
      setPracticeQuestionsLoading(false);
    }
  }

  async function handleEvaluatePracticeAnswer(question, index) {
    /** Evaluate one practice answer and record revision signals without blocking progress. */
    const practiceQuestion = normalizePracticeQuestion(question, subject);
    const answer = practiceAnswers[index] || "";

    if (!answer.trim()) {
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
      if (isHindiSubject() && practiceQuestion.type === "mcq") {
        const isCorrect = answer === practiceQuestion.answer;
        const nextAttemptCount = practiceAttemptCount + 1;
        const nextBestScore = Math.max(practiceBestScore, isCorrect ? 10 : 0);
        const writingNote =
          practiceQuestion.explanation ||
          "When writing Hindi answers, start with the direct answer, add one reason from the lesson, and write in complete sentences.";

        setPracticeEvaluations((prev) => ({
          ...prev,
          [index]: [
            `## ${isCorrect ? "Correct" : "Incorrect"}`,
            isCorrect
              ? "You selected the right answer."
              : `Correct answer: ${practiceQuestion.answer}`,
            "## Note for writing answers",
            `- ${writingNote}`,
            "- While writing, use complete Hindi sentences, mention the main idea, and support it with one short example from the lesson.",
          ].join("\n\n"),
        }));

        setPracticeScores((prev) => ({
          ...prev,
          [index]: isCorrect ? 10 : 0,
        }));

        setPracticePassedMap((prev) => ({
          ...prev,
          [index]: isCorrect,
        }));

        setPracticeAttemptCount(nextAttemptCount);
        setPracticeBestScore(nextBestScore);
        setPracticePassed(true);
        setPracticeModeActive(false);

        if (!isCorrect) {
          try {
            await saveWeakAreaAlert({
              username: user.username,
              grade,
              mode,
              subject,
              chapter,
              step_title: stepTitle,
              step_index: currentStepIndex,
              attempts: nextAttemptCount,
              best_score: nextBestScore,
            });
          } catch (err) {
            console.error("Unable to save weak area alert", err);
          }
        }

        return;
      }

      const result = await evaluateStudentAnswer({
        grade,
        mode,
        subject,
        chapter,
        step_title: stepTitle,
        username: user.username,
        question: practiceQuestion.question,
        student_answer: answer,
        ideal_context: lesson,
        question_type: practiceQuestion.type,
        expected_keywords: practiceQuestion.expected_keywords || [],
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
        [index]: true,
      }));
      
      const nextAttemptCount = practiceAttemptCount + 1;
      const nextBestScore = Math.max(practiceBestScore, result.score || 0);
      
      setPracticeAttemptCount(nextAttemptCount);
      setPracticeBestScore(nextBestScore);

      setPracticePassed(true);
      setPracticeModeActive(false);

      if ((result.score || 0) < 7) {
        try {
          await saveWeakAreaAlert({
            username: user.username,
            grade,
            mode,
            subject,
            chapter,
            step_title: stepTitle,
            step_index: currentStepIndex,
            attempts: nextAttemptCount,
            best_score: nextBestScore,
          });
        } catch (err) {
          console.error("Unable to save weak area alert", err);
        }
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

  async function handleEvaluateInlineLessonQuestion({ question, answer }) {
    /** Evaluate optional lesson-section answers without making the prompt mandatory. */
    if (!question?.trim() || !answer?.trim()) {
      return {
        success: false,
        message: "Write an answer before asking for evaluation.",
      };
    }

    return evaluateStudentAnswer({
      grade,
      mode,
      subject,
      chapter,
      step_title: stepTitle,
      username: user.username,
      question,
      student_answer: answer,
      ideal_context: lesson,
      question_type: "short_answer",
      expected_keywords: [],
    });
  }
  
  function countWords(text) {
    /** Count non-empty words for minimum practice answer validation. */
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
                title="You can complete this step. Practice feedback is for revision, not pass/fail."
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
                  <LessonSections
                    lesson={lesson}
                    onEvaluateQuestion={handleEvaluateInlineLessonQuestion}
                  />
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

                    {allowContinueAnyway && !practicePassed && (
                      <div className="practice-warning-banner">
                        ⚠️ This topic has been marked for revision. You can
                        still continue and revisit it later.
                      </div>
                    )}

                    {practiceModeActive && (
                      <div className="practice-focus-banner">
                        ✍️ Practice Mode Active — try the questions from memory
                        first. Your result will guide revision, not block the
                        next step.
                      </div>
                    )}

                    <div className="lesson-followup-header">
                      <h3>✍️ Self Check Practice</h3>
                      <p>
                        {isHindiSubject()
                          ? "Hindi gets two MCQs with instant correct or incorrect feedback plus writing pointers."
                          : "Maths gets two MCQs. Science, English, and Social Science get one MCQ plus one open answer with AI feedback."}
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
                          const practiceQuestion = normalizePracticeQuestion(
                            q,
                            subject
                          );
                          const currentAnswer = practiceAnswers[index] || "";
                          const currentWordCount = countWords(currentAnswer);
                          const currentEvaluation =
                            practiceEvaluations[index] || "";
                          const currentScore = practiceScores[index] || 0;
                          const currentCorrect =
                            practicePassedMap[index] || false;
                          const currentLoading =
                            practiceLoadingMap[index] || false;
                          const isMcq = practiceQuestion.type === "mcq";
                          const isHindiPractice = isHindiSubject();

                          return (
                            <div
                              key={index}
                              className="practice-question-card workbook-card"
                            >
                              <strong>Question {index + 1}</strong>
                              <span>{practiceQuestion.question}</span>

                              {isMcq ? (
                                <div className="practice-option-list">
                                  {practiceQuestion.options.map((option) => (
                                    <button
                                      key={option}
                                      type="button"
                                      className={
                                        currentAnswer === option
                                          ? "practice-option-btn selected"
                                          : "practice-option-btn"
                                      }
                                      onClick={() =>
                                        setPracticeAnswers((prev) => ({
                                          ...prev,
                                          [index]: option,
                                        }))
                                      }
                                    >
                                      {option}
                                    </button>
                                  ))}
                                </div>
                              ) : (
                                <textarea
                                  rows="7"
                                  value={currentAnswer}
                                  placeholder="Write freely here. There is no word limit."
                                  onChange={(e) =>
                                    setPracticeAnswers((prev) => ({
                                      ...prev,
                                      [index]: e.target.value,
                                    }))
                                  }
                                />
                              )}

                              <p className="practice-word-count">
                                {isMcq
                                  ? currentAnswer
                                    ? "Option selected. Check it for instant feedback."
                                    : "Choose one option."
                                  : `Words written: ${currentWordCount}. No word limit.`}
                              </p>

                              <button
                                className="primary-btn"
                                disabled={currentLoading || !currentAnswer}
                                onClick={() =>
                                  handleEvaluatePracticeAnswer(q, index)
                                }
                              >
                                {currentLoading
                                  ? "Evaluating..."
                                  : isMcq
                                  ? "Check Answer"
                                  : "Get AI Feedback"}
                              </button>

                              {currentEvaluation && (
                                <div className="mentor-followup-answer markdown-content">
                                  <ReactMarkdown
                                    remarkPlugins={[remarkGfm, remarkMath]}
                                    rehypePlugins={[rehypeKatex]}
                                  >
                                    {normalizeTutorMarkdown(currentEvaluation)}
                                  </ReactMarkdown>
                                </div>
                              )}

                              {currentEvaluation && (
                                <div
                                  className="practice-status-box coaching"
                                >
                                  <strong>🧠 Practice feedback saved</strong>

                                  <p>
                                    {isHindiPractice
                                      ? `Result: ${
                                          currentCorrect
                                            ? "Correct"
                                            : "Incorrect"
                                        }. Read the note above before writing your own answer.`
                                      : `Score signal: ${currentScore}/10. You can continue to the next step anytime; this feedback will help future revision.`}
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

                {isVisualSubject() && (
                  <div className="visual-generator-card premium-card premium-glow-card glow-purple">
                    <div className="visual-generator-header">
                      <h3>🖼 Visual Generator</h3>

                      <p>
                        {isMathSubject()
                          ? "Ask for a visual aid like a number line, fraction model, graph, or geometry sketch."
                          : "Ask for a visual aid like a process flow, experiment setup, cycle, or cause-effect scene."}
                      </p>
                    </div>

                    <div className="visual-aid-helper">
                      <strong>{getVisualAidHeading()}</strong>

                      <div className="visual-aid-chip-grid">
                        {getVisualAidSuggestions().map((suggestion) => (
                          <button
                            key={suggestion}
                            type="button"
                            className="visual-aid-chip"
                            onClick={() => setVisualTopic(suggestion)}
                          >
                            {suggestion}
                          </button>
                        ))}
                      </div>

                      <p>{getVisualAidWarning()}</p>
                    </div>

                    <div className="visual-generator-controls">
                      <input
                        className="visual-topic-input"
                        type="text"
                        placeholder={getVisualPlaceholder()}
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
                )}

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

                {!isHindiSubject() && (
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
                              {normalizeTutorMarkdown(msg.content)}
                            </ReactMarkdown>

                            {msg.sourceType && (
                              <span className="chat-source-chip">
                                {msg.sourceType === "PLATFORM_RAG"
                                  ? "🏷 Platform"
                                  : msg.sourceType === "RAG"
                                  ? "📚 RAG"
                                  : "🤖 LLM"}
                              </span>
                            )}
                          </div>
                        ))}
                      </div>
                    )}

                    {lessonDoubtHistory.length > 0 && (
                      <details className="lesson-history-panel">
                        <summary>
                          Recent Lesson Doubts
                          <span>{lessonDoubtHistory.length}</span>
                        </summary>

                        <div className="lesson-history-list">
                          {lessonDoubtHistory.slice(0, 5).map((item) => (
                            <button
                              key={item.id}
                              type="button"
                              className="lesson-history-item"
                              onClick={() => handleOpenLessonHistory(item)}
                            >
                              <strong>{item.question}</strong>
                              <small>
                                {item.chapter ||
                                  item.subject ||
                                  "Lesson follow-up"}
                              </small>
                            </button>
                          ))}
                        </div>
                      </details>
                    )}

                    <div className="lesson-followup-input">
                      <textarea
                        rows="4"
                        disabled={practiceModeActive}
                        placeholder={
                          practiceModeActive
                            ? "Practice mode active. Complete self-check practice first."
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
                )}
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
