import { useEffect, useRef, useState } from "react";
import { BookOpen, Sparkles, RotateCcw, ArrowLeft, ArrowRight } from "lucide-react";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import ReactMarkdown from "react-markdown";
import StructuredVisualBlock from "../components/StructuredVisualBlock";

import { getSyllabus } from "../api/syllabus";
import {
  generateLesson,
  askLessonFollowUp,
  getLessonTextbookVisuals,
  getLessonDoubtSuggestions,
  ensureLessonKbChips,
} from "../api/lesson";
import { getDoubtHistory } from "../api/doubt";
import { generateSpeech, getCachedAudioUrl } from "../api/tts";
import { getChapterProgress, saveChapterProgress } from "../api/progress";
import LessonSections from "../components/LessonSections";
import { saveWeakAreaAlert } from "../api/weakAreaAlerts";
import { getLessonCardPublicSettings } from "../api/platformSettings";

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
import { hasPaidAccess } from "../utils/resolveSubscription";

const TEACHER_PERSONAS = {
  "Friendly Teacher": "Explain warmly, patiently, and encouragingly.",
  "Strict Exam Coach":
    "Focus on exam preparation, accuracy, common mistakes, and scoring.",
  "Slow Step-by-Step Teacher":
    "Explain slowly, with very small steps and simple examples.",
  "HOTS Coach":
    "Focus on reasoning, HOTS, shortcuts, and tricky question patterns.",
  "Storytelling Teacher":
    "Explain concepts using stories, analogies, and real-life examples.",
};

// Default voice and speed — not exposed in UI, used for narration.
const DEFAULT_VOICE = "en-IN-NeerjaNeural";
const HINDI_VOICE   = "hi-IN-SwaraNeural";   // Microsoft Hindi neural voice
const DEFAULT_SPEECH_RATE = "+0%";

function getVoiceForSubject(subjectName) {
  /** Pick the right TTS voice based on the subject language. */
  const s = (subjectName || "").toLowerCase();
  if (s === "hindi" || s.includes("hindi")) return HINDI_VOICE;
  return DEFAULT_VOICE;
}

// ── Dynamic loading messages: subject × step ──────────────────────────────────
const LOADING_MESSAGES = {
  0: { // Step 1: Concept Introduction
    maths:   "Solving the equation of understanding — your foundation is loading 🔢",
    science: "Setting up the experiment — concept intro being prepared in the AI lab 🔬",
    hindi:   "पाठ की नींव रखी जा रही है… शब्दों का जादू अभी शुरू होता है ✍️",
    social:  "Turning the pages of history — your foundation lesson is loading 🌍",
    english: "Crafting your introduction with the finest words in the dictionary 📚",
    default: "Your AI tutor is reading the textbook so you don't have to… 📖",
  },
  1: { // Step 2: Core Explanation
    maths:   "Crunching the numbers — your core maths concepts are being assembled 🔢",
    science: "The AI lab is running the experiment — core concepts incoming 🧪",
    hindi:   "गहराई से समझाने की तैयारी है… आपका विशेष पाठ बन रहा है 🖊️",
    social:  "Connecting history, geography, and civics just for you 🗺️",
    english: "Every word chosen carefully — your core lesson is being written ✒️",
    default: "Digging deeper — your AI tutor is connecting the dots just for you 🧩",
  },
  2: { // Step 3: Worked Examples
    maths:   "Solving step by step — worked examples are being calculated ✏️",
    science: "Running the experiment with real worked examples — results loading 🔭",
    hindi:   "उदाहरणों से सीखें — आपके लिए खास उदाहरण तैयार हो रहे हैं 📝",
    social:  "Real events, real maps, real examples — loading just for you 🗺️",
    english: "Show, don't tell — worked examples are being crafted with care 📖",
    default: "Cooking up real-world examples — watch and learn mode: ON 🍳",
  },
  3: { // Step 4: Exam-style Problems
    maths:   "CBSE maths problems incoming — sharpen your pencil ✏️",
    science: "Exam-style science questions being calibrated — accuracy loading 🎯",
    hindi:   "परीक्षा की तैयारी हो रही है — CBSE स्तर के प्रश्न आ रहे हैं 🏆",
    social:  "Exam-level questions from history and civics — loading now 🎓",
    english: "Grammar, comprehension, and expression — exam mode ON 🏅",
    default: "Sharpening your exam skills ⚔️ CBSE-style practice questions being forged…",
  },
  4: { // Step 5: Revision & Recap
    maths:   "Recapping all formulas and methods — your maths revision is loading 📐",
    science: "Summarising the key science concepts — your revision is almost ready 🧬",
    hindi:   "पूरे पाठ का निचोड़ तैयार हो रहा है… एक आखिरी नज़र 🌟",
    social:  "History, geography, civics — all packed into your crisp revision 🗺️",
    english: "Key grammar, literary devices, and tips — revision loading 📚",
    default: "Pulling 4 steps of learning into a crisp revision — almost there 🚀",
  },
  5: { // Step 6: Exam Preparation (Grade 10+)
    maths:   "Final formula check — getting your maths fully exam-ready 🏆",
    science: "Last-minute science essentials — exam preparation loading 🎓",
    hindi:   "परीक्षा की अंतिम तैयारी — सब कुछ आपके लिए तैयार हो रहा है 🌟",
    social:  "Final revision of key events and concepts — exam prep loading 🎓",
    english: "Last-minute tips and tricks — English exam prep is ready 📝",
    default: "Final polish mode 🎓 Getting you fully exam-ready…",
  },
};

function getLoadingMessage(stepIndex, subject) {
  /** Return a subject-aware, step-specific loading message shown during generation. */
  const s = (subject || "").toLowerCase();
  const isMaths   = s.includes("math");
  const isScience = s === "science" || (s.includes("science") && !s.includes("social"));
  const isHindi   = s === "hindi" || s.includes("hindi");
  const isSocial  = s.includes("social");
  const isEnglish = s === "english" || s.includes("english");

  const pool = LOADING_MESSAGES[stepIndex] ?? LOADING_MESSAGES[4];

  if (isMaths)   return pool.maths;
  if (isScience) return pool.science;
  if (isHindi)   return pool.hindi;
  if (isSocial)  return pool.social;
  if (isEnglish) return pool.english;
  return pool.default;
}

// ── Layout feature flags ──────────────────────────────────────────────────────
// Set USE_TOP_BAR_LAYOUT=true to move Learning Path to a compact top bar so
// the lesson content takes the full width. Set false to roll back to left sidebar.
const USE_REFINED_LESSON_EXPERIENCE_LAYOUT = true;
const USE_TOP_BAR_LAYOUT = true;

// ── Shared sizing for the top bar + step-nav controls ─────────────────────────
// One scale for every chip/button/select across both rows so nothing reads
// taller or shorter than its neighbor (previously each row had its own
// font-size/padding, so the "% complete" pill was visibly shorter than the
// Previous/Next buttons next to it).
const STEP_CONTROL_FONT_SIZE = "0.875rem";
const stepChipStyle = (complete) => ({
  fontSize: STEP_CONTROL_FONT_SIZE,
  fontWeight: 700,
  color: "#fff",
  background: complete ? "#16a34a" : "#0891b2",
  borderRadius: 999,
  padding: "7px 14px",
  lineHeight: 1,
  whiteSpace: "nowrap",
});
const stepButtonStyle = {
  padding: "7px 16px",
  fontSize: STEP_CONTROL_FONT_SIZE,
  borderRadius: 8,
  lineHeight: 1,
  // .primary-btn in App.css sets margin-top:18px (for buttons stacked below a
  // form) — override it here since these buttons sit inline in a flex row.
  marginTop: 0,
};

const RAG_VISUAL_ENABLED_CONTEXTS = new Set(["CBSE|Grade 9", "CBSE|Grade 10"]);
// Grade 10 visuals restricted to Science and Maths only
const GRADE10_VISUAL_SUBJECTS = new Set([
  "Science", "Maths", "Mathematics",
  "Advanced Science", "Advanced Mathematics",
]);

function isHindiSubjectName(subject) {
  /** Identify Hindi subjects so practice can stay objective and lightweight. */
  return subject === "Hindi";
}

function buildPracticeFallbackQuestions(subject) {
  /** Keep practice usable if the backend cannot generate structured questions. */
  const isMath =
    subject === "Maths" ||
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

function LessonsPage({ user, setActivePage }) {
  /** Student lesson workspace with AI lessons, progress, audio, visuals, follow-ups, and coaching practice. */

  // ── Effective user: syncs stream/cbseSubjects from backend for Grade 11/12 ──
  // When a user's session was cached before stream/cbseSubjects were propagated,
  // fetch the profile once on mount to get the correct subject list.
  const [effectiveUser, setEffectiveUser] = useState(user);
  useEffect(() => {
    const g = (user?.grade || "").toLowerCase();
    const isUpperSecondary = g === "grade 11" || g === "grade 12";
    const needsSync = isUpperSecondary && (
      !user?.stream || !user?.cbseSubjects?.length
    );
    if (!needsSync || !user?.accessToken) return;
    const apiBase = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
    fetch(`${apiBase}/api/auth/profile`, {
      headers: { Authorization: `Bearer ${user.accessToken}` },
    })
      .then(r => r.json())
      .then(p => {
        if (p.stream || (p.cbse_subjects && p.cbse_subjects.length)) {
          setEffectiveUser({
            ...user,
            stream: p.stream || user.stream || null,
            cbseSubjects: Array.isArray(p.cbse_subjects) && p.cbse_subjects.length
              ? p.cbse_subjects
              : user.cbseSubjects || [],
            grade: p.grade || user.grade,
          });
        }
      })
      .catch(() => {/* non-critical — use user as-is */});
  }, [user?.accessToken, user?.grade]);

  const [loading, setLoading] = useState(true);
  const [syllabusData, setSyllabusData] = useState(null);
  const [error, setError] = useState("");

  const [grade, setGrade] = useState("Grade 9");
  const [mode, setMode] = useState("CBSE");
  const [subject, setSubject] = useState("");
  const [chapter, setChapter] = useState("");

  const [textbookVisuals, setTextbookVisuals] = useState([]);
  const [textbookVisualsLoading, setTextbookVisualsLoading] = useState(false);
  const [selectedTextbookVisual, setSelectedTextbookVisual] = useState(null);
  const [textbookVisualQuery, setTextbookVisualQuery] = useState("");
  const [textbookVisualSearchResults, setTextbookVisualSearchResults] = useState([]);
  const [textbookVisualSearching, setTextbookVisualSearching] = useState(false);
  const [textbookVisualError, setTextbookVisualError] = useState("");

  const [practiceAnswers, setPracticeAnswers] = useState({});
  const [practiceEvaluations, setPracticeEvaluations] = useState({});
  const [practicePassedMap, setPracticePassedMap] = useState({});
  const [practiceLoadingMap, setPracticeLoadingMap] = useState({});
  const [practicePassed, setPracticePassed] = useState(false);
  const [practiceAttemptCount, setPracticeAttemptCount] = useState(0);
  const [practiceBestScore, setPracticeBestScore] = useState(0);
  const [allowContinueAnyway, setAllowContinueAnyway] = useState(false);

  const [practiceQuestions, setPracticeQuestions] = useState([]);
  const [practiceQuestionsLoading, setPracticeQuestionsLoading] =
    useState(false);

  const lessonSteps = (() => {
    /** Return grade-appropriate lesson steps matching the backend prewarm step definitions. */
    const g = (grade || "").toLowerCase();
    if (g === "grade 1" || g === "grade 2" || g === "grade 3") {
      return ["Introduction", "Let's Practice", "Quick Review"];
    }
    if (g === "grade 4" || g === "grade 5") {
      return ["What We Learn", "Worked Examples", "Recap"];
    }
    if (g === "grade 6" || g === "grade 7" || g === "grade 8") {
      return ["Concept introduction", "Core explanation", "Worked examples", "Revision and recap"];
    }
    if (g === "grade 10" || g === "grade 11" || g === "grade 12") {
      return ["Concept introduction", "Core explanation", "Worked examples", "Exam-style problems", "Revision and recap", "Exam preparation"];
    }
    // Grade 9 + fallback
    return ["Concept introduction", "Core explanation", "Worked examples", "Exam-style problems", "Revision and recap"];
  })();

  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [highestUnlockedStep, setHighestUnlockedStep] = useState(0);
  const [completed, setCompleted] = useState(false);

  const stepTitle = lessonSteps[currentStepIndex];

  // Write lesson context for Report Issue modal
  if (typeof window !== "undefined") {
    window.__LIKHAPOHA_CONTEXT__ = {
      page: "lessons",
      grade: grade || null,
      subject: subject || null,
      chapter: chapter || null,
      lessonStep: stepTitle || null,
      lessonStepIndex: currentStepIndex,
      totalSteps: lessonSteps.length,
      lessonId: chapter ? (grade+"-"+subject+"-"+chapter).toLowerCase().replace(/[^a-z0-9]+/g,"-") : null,
    };
  }

  // Teacher persona, voice, and speed are fixed defaults — not user-selectable.
  // Using "" persona ensures pre-warmed cached lessons are served instantly.
  const teacherPersona = "";

  const [lesson, setLesson] = useState("");
  const [stepLessons, setStepLessons] = useState({});
  const [sourceInfo, setSourceInfo] = useState(null);
  const [generating, setGenerating] = useState(false);

  const [followUpQuestion, setFollowUpQuestion] = useState("");
  const [followUpMessages, setFollowUpMessages] = useState([]);
  const [lessonDoubtHistory, setLessonDoubtHistory] = useState([]);
  const [followUpLoading, setFollowUpLoading] = useState(false);
  const [doubtSuggestions, setDoubtSuggestions] = useState([]);

  // ── Session-level answer cache ─────────────────────────────────────────────
  // Common questions (chip suggestions, repeated questions) are answered instantly
  // from cache — no network call, no loading spinner.
  // Key: grade|subject|chapter|stepTitle|question (lowercased, trimmed)
  const followUpCache = useRef({});

  // ── Chip cache readiness ───────────────────────────────────────────────────
  // Only chips whose answers are already in followUpCache are shown.
  // Chips are pre-fetched in background when suggestions or lesson loads.
  const [cachedChipQuestions, setCachedChipQuestions] = useState(new Set());
  const [activeChip, setActiveChip] = useState(null); // tracks which chip is loading
  const chatBottomRef = useRef(null); // scroll target after AI response
  // Set to true by Next/Previous nav handlers when the destination step has no
  // saved lesson. A useEffect picks this up AFTER state commits and auto-calls
  // handleGenerateLesson(true) to serve the prewarmed lesson without a button click.
  const autoGenerateRef = useRef(false);

  const [audioUrl, setAudioUrl] = useState("");
  const [ttsLoading, setTtsLoading] = useState(false);

  const [practiceModeActive, setPracticeModeActive] = useState(false);
  const [practiceFocusWarnings, setPracticeFocusWarnings] = useState(0);
  const [gifFading, setGifFading] = useState(false);
  const [cardStyle, setCardStyle] = useState("default");
  const [cardTheme, setCardTheme] = useState("brand");

  useEffect(() => {
    getLessonCardPublicSettings().then(s => {
      setCardStyle(s.card_style || "default");
      setCardTheme(s.card_theme || "brand");
    });
  }, []);

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
        setSourceInfo(null);
        setFollowUpQuestion("");
        setFollowUpMessages([]);
        setDoubtSuggestions([]);
        resetPracticeState();

        // ── LKB chips: ensure endpoint — always returns chips ─────────────────
        // 1. If pre-warmed: returns from DB instantly.
        // 2. If not pre-warmed: generates via LLM on-demand (~5-8s), stores in DB,
        //    returns chips — every subsequent request is instant from DB.
        // Called in background so static chips show immediately while LKB generates.
        const lkbStepTitle = lessonSteps[savedStepIndex];
        ensureLessonKbChips({ grade, subject, chapter, step_title: lkbStepTitle })
          .then(lkbResult => {
            const lkbChips = Array.isArray(lkbResult?.lkb_chips) ? lkbResult.lkb_chips : [];
            if (lkbChips.length > 0) {
              const newReady = new Set();
              lkbChips.forEach(({ question, answer }) => {
                const key = `${grade}|${subject}|${chapter}|${lkbStepTitle}|${question.trim().toLowerCase()}`;
                followUpCache.current[key] = {
                  role: "assistant",
                  content: answer,
                  sourceType: "PLATFORM_RAG",
                  textbookVisuals: [],
                  offerGate: false,
                };
                newReady.add(question);
              });
              setCachedChipQuestions(prev => {
                const merged = new Set(prev);
                newReady.forEach(q => merged.add(q));
                return merged;
              });
              // LKB chips take priority — replace whatever was shown before
              setDoubtSuggestions(lkbChips.map(c => ({ question: c.question, answer: c.answer })));
            }
          })
          .catch(() => {
            // LKB generation failed — static chips remain visible
          });

        // DKB suggestion cards (best-effort, shown while LKB generates)
        try {
          const suggestionsResult = await getLessonDoubtSuggestions({
            grade, mode, subject, chapter,
            board: mode,
          });
          const dkbChips = Array.isArray(suggestionsResult?.doubt_suggestions)
            ? suggestionsResult.doubt_suggestions.slice(0, 6)
            : [];
          if (dkbChips.length > 0) {
            // Only show DKB chips if LKB hasn't loaded yet
            setDoubtSuggestions(prev => prev.length > 0 ? prev : dkbChips);
            preFetchChipAnswers(dkbChips, grade, mode, subject, chapter, lessonSteps[savedStepIndex]);
          }
        } catch {
          // DKB suggestions are a convenience — never block lesson loading
        }
      } catch {
        console.error("Could not load progress");
      }
    }

    loadProgress();
  }, [grade, mode, subject, chapter, user.username]);

  // ── LKB chips: reload whenever step changes (navigation or initial load) ──
  // loadProgress only runs when chapter/grade changes. When user navigates
  // between steps (Previous/Next), currentStepIndex changes but loadProgress
  // does NOT re-run. This effect ensures LKB chips are always correct for the
  // CURRENT step — cache keys always match what the user sees.
  useEffect(() => {
    if (!grade || !subject || !chapter || !stepTitle) return;

    // Clear stale chips from previous step
    setDoubtSuggestions([]);

    // Fetch LKB chips for current step in background
    ensureLessonKbChips({ grade, subject, chapter, step_title: stepTitle })
      .then(lkbResult => {
        const lkbChips = Array.isArray(lkbResult?.lkb_chips) ? lkbResult.lkb_chips : [];
        if (lkbChips.length > 0) {
          const newReady = new Set();
          lkbChips.forEach(({ question, answer }) => {
            const key = `${grade}|${subject}|${chapter}|${stepTitle}|${question.trim().toLowerCase()}`;
            followUpCache.current[key] = {
              role: "assistant",
              content: answer,
              sourceType: "PLATFORM_RAG",
              textbookVisuals: [],
              offerGate: false,
            };
            newReady.add(question);
          });
          setCachedChipQuestions(prev => {
            const merged = new Set(prev);
            newReady.forEach(q => merged.add(q));
            return merged;
          });
          setDoubtSuggestions(lkbChips.map(c => ({ question: c.question, answer: c.answer })));
        }
      })
      .catch(() => {
        // LKB unavailable — static chips already loaded above
      });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [grade, subject, chapter, currentStepIndex]);

  // ── Auto-load prewarmed lesson on step navigation ─────────────────────────
  // When the user clicks Next/Previous and the target step has no saved lesson,
  // autoGenerateRef.current is set to true inside the nav handler. This effect
  // fires AFTER React has committed the new currentStepIndex/stepTitle, so
  // handleGenerateLesson sees the correct step. Prewarmed cache hits return in
  // < 1 s with no LLM cost; non-cached steps generate normally.
  useEffect(() => {
    if (!autoGenerateRef.current) return;
    if (!grade || !subject || !chapter || !stepTitle) return;
    if (generating) return;
    if (isExemplarLocked) { autoGenerateRef.current = false; return; }
    autoGenerateRef.current = false;
    handleGenerateLesson(true); // skipGifDelay=true — instant for cache hits
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentStepIndex, grade, subject, chapter]);

  // ── Scroll to top on step navigation (Previous / Next) ───────────────────
  // Fires after every step change so the user always starts reading from the
  // top of the new step, not from wherever they were in the previous one.
  // Skip the initial mount (isFirstStepRender) to avoid jarring scroll on load.
  const isFirstStepRender = useRef(true);
  useEffect(() => {
    if (isFirstStepRender.current) {
      isFirstStepRender.current = false;
      return;
    }
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, [currentStepIndex]);

  useEffect(() => {
    loadTextbookVisuals();
  }, [grade, mode, subject, chapter, user.username]);

  async function loadTextbookVisuals() {
    /** Load approved textbook-only visuals for this exact lesson context. */
    if (!grade || !mode || !subject || !chapter || !isTextbookVisualSubject()) {
      setTextbookVisuals([]);
      setSelectedTextbookVisual(null);
      setTextbookVisualError("");
      return;
    }

    setTextbookVisualsLoading(true);
    setTextbookVisualError("");

    try {
      const result = await getLessonTextbookVisuals({
        grade,
        mode,
        board: mode,
        subject,
        chapter,
      });

      const visuals = result.visuals || [];
      setTextbookVisuals(visuals);
      setTextbookVisualSearchResults([]);
      setSelectedTextbookVisual(visuals[0] || null);
      setTextbookVisualError("");
    } catch (err) {
      setTextbookVisualError(
        err.message || "Could not load textbook visuals for this lesson."
      );
    } finally {
      setTextbookVisualsLoading(false);
    }
  }

  if (loading) {
    return <p>Loading syllabus...</p>;
  }

  if (error && !lesson) {
    return <p className="error">{error}</p>;
  }

  const grades = getVisibleGrades(syllabusData, user);
  const modes = Object.keys(syllabusData[grade]);

  function getAllowedSubjects(allSubjects, selectedMode) {
    /** Filter subjects by the student's subscription access for CBSE mode.
     *  Uses effectiveUser (which has up-to-date stream/cbseSubjects) rather than user. */
    return filterAllowedSubjects(effectiveUser, allSubjects, selectedMode);
  }

  const allSubjects = Object.keys(syllabusData[grade][mode]);
  const subjects = getAllowedSubjects(allSubjects, mode);
  const chapters = subject ? syllabusData[grade][mode][subject] || [] : [];
  const requestBoard = mode;

  function resetTextbookVisualBrowser() {
    /** Clear textbook visual browser state when the lesson context changes. */
    setTextbookVisuals([]);
    setSelectedTextbookVisual(null);
    setTextbookVisualQuery("");
    setTextbookVisualSearchResults([]);
    setTextbookVisualError("");
  }

  function resetLessonState() {
    /** Clear generated lesson artifacts when the selected topic changes. */
    autoGenerateRef.current = false; // cancel any pending auto-generation
    setLesson("");
    setAudioUrl("");
    resetTextbookVisualBrowser();
    setSourceInfo(null);
    setFollowUpQuestion("");
    setFollowUpMessages([]);
    setDoubtSuggestions([]);
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
  
  function isHindiSubject() {
    /** Hindi lessons use objective checks and skip lesson chat follow-ups. */
    return isHindiSubjectName(subject);
  }

  function isTextbookVisualSubject() {
    /** Keep RAG visuals limited while storage quota is tight.
     * Grade 9: all subjects.
     * Grade 10: Science and Maths only.
     */
    if (!RAG_VISUAL_ENABLED_CONTEXTS.has(`${requestBoard}|${grade}`)) return false;
    if (!subject) return false;
    if (grade === "Grade 10") {
      return GRADE10_VISUAL_SUBJECTS.has(subject);
    }
    return true; // Grade 9: all subjects
  }

  function shouldShowTextbookVisualTools() {
    /** Textbook visual browser removed from student-facing lesson page.
     * Feature is available in the Admin Lesson Experience Lab only.
     */
    return false;
  }

  function getTextbookVisualSearchTerms(query = "") {
    /** Support English and Indian-language searches without regex escaping risk. */
    return query
      .toLowerCase()
      .split(/[^\p{L}\p{N}]+/u)
      .filter((term) => term.length > 1);
  }

  function getTextbookVisualCallout(visual, query = "") {
    /** Build a short, grounded callout from stored visual metadata. */
    const sourceText = [
      visual.caption,
      visual.nearby_text,
      visual.title,
      visual.chapter,
    ]
      .filter(Boolean)
      .join(" ");

    const cleanText = sourceText.replace(/\s+/g, " ").trim();
    if (!cleanText) {
      return `Page ${visual.page_number} is an approved textbook visual for this lesson.`;
    }

    const terms = getTextbookVisualSearchTerms(query);
    const lowerText = cleanText.toLowerCase();
    const firstMatchIndex = terms
      .map((term) => lowerText.indexOf(term))
      .filter((index) => index >= 0)
      .sort((a, b) => a - b)[0];
    const startIndex =
      firstMatchIndex > 60 ? cleanText.lastIndexOf(" ", firstMatchIndex - 45) : 0;
    const words = cleanText.slice(Math.max(0, startIndex)).split(/\s+/).slice(0, 20);

    return words.join(" ");
  }

  function renderHighlightedText(text, query = "") {
    /** Highlight the matching search word in the metadata callout, not on the image itself. */
    const terms = getTextbookVisualSearchTerms(query);
    const term = terms.find((item) => text.toLowerCase().includes(item));

    if (!term) {
      return text;
    }

    const matchIndex = text.toLowerCase().indexOf(term);
    const before = text.slice(0, matchIndex);
    const match = text.slice(matchIndex, matchIndex + term.length);
    const after = text.slice(matchIndex + term.length);

    return (
      <>
        {before}
        <mark>{match}</mark>
        {after}
      </>
    );
  }

  async function handleFindTextbookVisual() {
    /** Search active textbook visuals only inside the selected lesson context. */
    const query = textbookVisualQuery.trim();

    if (!query) {
      setTextbookVisualSearchResults([]);
      setTextbookVisualError("Type what you want to find in this lesson's textbook visuals.");
      return;
    }

    if (!isTextbookVisualSubject()) {
      setTextbookVisualSearchResults([]);
      setTextbookVisualError(
        "Textbook visual search is currently enabled only where reviewed visual assets exist."
      );
      return;
    }

    setTextbookVisualSearching(true);
    setTextbookVisualError("");

    try {
      const result = await getLessonTextbookVisuals({
        grade,
        mode,
        board: mode,
        subject,
        chapter,
        query,
      });
      const visuals = result.visuals || [];

      setTextbookVisualSearchResults(visuals);
      if (visuals.length) {
        setSelectedTextbookVisual(visuals[0]);
        setTextbookVisualError("");
      } else {
        setTextbookVisualError(
          result.message ||
            "No approved textbook visual matched that text in this lesson."
        );
      }
    } catch (err) {
      setTextbookVisualError(
        err.message || "Could not search textbook visuals for this lesson."
      );
    } finally {
      setTextbookVisualSearching(false);
    }
  }

  function resetPracticeState() {
    /** Clear all practice questions, evaluations, scores, and focus warnings. */
    setPracticeQuestions([]);
    setPracticeAnswers({});
    setPracticeEvaluations({});
    setPracticePassedMap({});
    setPracticeLoadingMap({});
    setPracticePassed(false);
    setPracticeAttemptCount(0);
    setPracticeBestScore(0);
    setAllowContinueAnyway(false);
    setPracticeModeActive(false);
    setPracticeFocusWarnings(0);
  }

  async function handleGenerateLesson(skipGifDelay = false, forceRefresh = false) {
    /** Generate one lesson step, save it to progress, and store RAG source metadata.
     *  Normal: GIF plays for 5 s, fades out over 1 s, lesson appears at 6 s.
     *  skipGifDelay=true (auto-load from prewarm cache): no forced wait — lesson
     *  appears as soon as the backend responds (cache hit ≈ 500 ms).
     *  forceRefresh=true: bypasses backend cache — regenerates fresh and overwrites
     *  stale prewarmed content (used by the "Refresh lesson" button).
     */
    const GIF_FADE_AT_MS = skipGifDelay ? 100 : 5000;
    const MIN_GIF_MS = skipGifDelay ? 0 : 6000;
    const gifStart = Date.now();

    setGenerating(true);
    setGifFading(false);
    setLesson("");
    setAudioUrl("");
    setSourceInfo(null);
    setError("");
    setFollowUpQuestion("");
    setFollowUpMessages([]);
    resetPracticeState();

    // Schedule the fade-out regardless of how fast the lesson loads
    const fadeTimer = setTimeout(() => setGifFading(true), GIF_FADE_AT_MS);
  
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
        force_refresh: forceRefresh,
      });
  
      if (!result.success) {
        clearTimeout(fadeTimer);
        setError(result.message || "Lesson generation failed");
        return;
      }

      // Wait until 6 s total so the fade-out (1 s) has time to finish
      const elapsed = Date.now() - gifStart;
      if (elapsed < MIN_GIF_MS) {
        await new Promise((resolve) => setTimeout(resolve, MIN_GIF_MS - elapsed));
      }
      clearTimeout(fadeTimer);

      setLesson(result.lesson);
      if ((result.textbook_visuals || []).length > 0) {
        setSelectedTextbookVisual(result.textbook_visuals[0]);
      }
      // ── Load LKB chips immediately after lesson is generated ─────────────
      // LKB chips don't come from the lesson API — they live in lesson_kb.
      // ensureLessonKbChips must be called explicitly after lesson generation;
      // the useEffect on currentStepIndex doesn't re-fire because the step
      // index hasn't changed, and loadProgress ran before the lesson existed.
      ensureLessonKbChips({ grade, subject, chapter, step_title: stepTitle })
        .then(lkbResult => {
          const lkbChips = Array.isArray(lkbResult?.lkb_chips) ? lkbResult.lkb_chips : [];
          if (lkbChips.length > 0) {
            const newReady = new Set();
            lkbChips.forEach(({ question, answer }) => {
              const key = `${grade}|${subject}|${chapter}|${stepTitle}|${question.trim().toLowerCase()}`;
              followUpCache.current[key] = {
                role: "assistant",
                content: answer,
                sourceType: "PLATFORM_RAG",
                textbookVisuals: [],
                offerGate: false,
              };
              newReady.add(question);
            });
            setCachedChipQuestions(prev => {
              const merged = new Set(prev);
              newReady.forEach(q => merged.add(q));
              return merged;
            });
            // LKB chips take priority over DKB suggestions
            setDoubtSuggestions(lkbChips.map(c => ({ question: c.question, answer: c.answer })));
            return; // LKB loaded — skip DKB fallback below
          }
          // LKB returned no chips — fall back to DKB suggestions from lesson API
          const newChips = Array.isArray(result.doubt_suggestions)
            ? result.doubt_suggestions.slice(0, 6)
            : [];
          setDoubtSuggestions(newChips);
          if (newChips.length > 0) {
            preFetchChipAnswers(newChips, grade, mode, subject, chapter, stepTitle);
          }
        })
        .catch(() => {
          // LKB unavailable — fall back to DKB suggestions from lesson API
          const newChips = Array.isArray(result.doubt_suggestions)
            ? result.doubt_suggestions.slice(0, 6)
            : [];
          setDoubtSuggestions(newChips);
          if (newChips.length > 0) {
            preFetchChipAnswers(newChips, grade, mode, subject, chapter, stepTitle);
          }
        });
  
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
      clearTimeout(fadeTimer);
      setError(err.message || "Could not generate lesson. Check backend.");
    } finally {
      setGenerating(false);
      setGifFading(false);
    }
  }


  async function handleAskFollowUp(overrideQuestion = null) {
    /** Ask a follow-up about the current lesson unless practice mode is active.
     *  Accepts an optional overrideQuestion so chip clicks can submit directly
     *  without a separate state-set-then-submit cycle.
     *
     *  Performance: questions already answered in this session are served instantly
     *  from followUpCache — no network call and no loading spinner.
     */
    const questionToAsk =
      overrideQuestion !== null ? String(overrideQuestion) : followUpQuestion;

    if (!questionToAsk.trim() || practiceModeActive) {
      return;
    }

    // Show the user's message immediately and clear the text area
    setFollowUpMessages((prev) => [...prev, { role: "user", content: questionToAsk }]);
    setFollowUpQuestion("");

    // ── Cache hit: serve from LKB/DKB cache with a brief thinking delay ──────
    // The 2s pause makes the response feel considered rather than instantaneous,
    // without any actual LLM cost — the answer is already pre-warmed in cache.
    const cacheKey = `${grade}|${subject}|${chapter}|${stepTitle}|${questionToAsk.trim().toLowerCase()}`;
    if (followUpCache.current[cacheKey]) {
      setFollowUpLoading(true);
      await new Promise((resolve) => setTimeout(resolve, 2000));
      setFollowUpLoading(false);
      setFollowUpMessages((prev) => {
        const updated = [...prev, followUpCache.current[cacheKey]];
        setTimeout(() => chatBottomRef.current?.scrollIntoView({ behavior: "smooth" }), 80);
        return updated;
      });
      setActiveChip(null);
      return;
    }

    setFollowUpLoading(true);

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

      const assistantMessage = {
        role: "assistant",
        content: result.answer,
        sourceType: result.source_type,
        textbookVisuals: result.textbook_visuals || [],
        offerGate: result.source_type === "OFFER_GATE",
      };

      // Cache non-gated answers for instant re-use in this session
      if (result.source_type !== "OFFER_GATE") {
        followUpCache.current[cacheKey] = assistantMessage;
      }

      setFollowUpMessages((prev) => {
        const updated = [...prev, assistantMessage];
        setTimeout(() => chatBottomRef.current?.scrollIntoView({ behavior: "smooth" }), 80);
        return updated;
      });
      setActiveChip(null);
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
      setActiveChip(null);
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
    /**
     * Play lesson audio.
     * Fast path: check for pre-warmed audio in Supabase Storage (instant, $0).
     * Fallback: generate via Edge TTS (~15-20s for a full lesson step).
     */
    if (!lesson) return;

    setTtsLoading(true);
    setAudioUrl("");

    try {
      // ── Fast path: pre-warmed audio cache ────────────────────────────────
      const cached = await getCachedAudioUrl({
        grade,
        subject,
        chapter,
        stepTitle,
      });
      if (cached?.cached && cached.url) {
        setAudioUrl(cached.url);
        return;
      }

      // ── Fallback: generate via Edge TTS ──────────────────────────────────
      const url = await generateSpeech({
        text: lesson,
        voice: getVoiceForSubject(subject),
        rate: DEFAULT_SPEECH_RATE,
      });

      setAudioUrl(url);
    } catch {
      setError("Could not generate audio.");
    } finally {
      setTtsLoading(false);
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

      const normalizedQuestions = (result.questions || [])
        .map((item) => normalizePracticeQuestion(item, subject))
        .slice(0, 2);

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

    setPracticePassedMap((prev) => ({
      ...prev,
      [index]: false,
    }));

    try {
      // ── MCQ: fully local evaluation — no LLM, no API call ─────────────────
      if (practiceQuestion.type === "mcq") {
        const isCorrect = answer === practiceQuestion.answer;
        const nextAttemptCount = practiceAttemptCount + 1;
        const nextBestScore = Math.max(practiceBestScore, isCorrect ? 10 : 0);
        const expl = practiceQuestion.explanation || "";

        const feedback = isCorrect
          ? ["**✓ Correct!**", expl].filter(Boolean).join("\n\n")
          : [`**✗ Incorrect** — the right answer is: **${practiceQuestion.answer}**`, expl].filter(Boolean).join("\n\n");

        setPracticeEvaluations((prev) => ({ ...prev, [index]: feedback }));
        setPracticePassedMap((prev) => ({ ...prev, [index]: isCorrect }));
        setPracticeAttemptCount(nextAttemptCount);
        setPracticeBestScore(nextBestScore);
        setPracticePassed(true);
        setPracticeModeActive(false);

        if (!isCorrect) {
          try {
            await saveWeakAreaAlert({
              username: user.username, grade, mode, subject, chapter,
              step_title: stepTitle, step_index: currentStepIndex,
              attempts: nextAttemptCount, best_score: nextBestScore,
            });
          } catch (err) {
            console.error("Unable to save weak area alert", err);
          }
        }
        return;
      }
      // ──────────────────────────────────────────────────────────────────────

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
        correct_answer: practiceQuestion.answer || "",
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


  async function preFetchChipAnswers(chips, chipGrade, chipMode, chipSubject, chipChapter, chipStepTitle) {
    /** Pre-populate followUpCache for every chip question so chips are instant.
     *  1. If the chip item already has an .answer field (DKB), store directly — zero API cost.
     *  2. Otherwise call askLessonFollowUp in background for each chip.
     *  Only chips with cached answers are shown (cachedChipQuestions state).
     */
    if (!chips || chips.length === 0) return;

    const newReady = new Set();

    await Promise.allSettled(chips.map(async (chip) => {
      const question = typeof chip === "string" ? chip : chip.question;
      if (!question) return;

      const key = `${chipGrade}|${chipSubject}|${chipChapter}|${chipStepTitle}|${question.trim().toLowerCase()}`;

      // ── Fast path: DKB chip already has answer in response ────────────────
      const existingAnswer = typeof chip === "object" ? (chip.answer || chip.pre_answer || "") : "";
      if (existingAnswer) {
        followUpCache.current[key] = {
          role: "assistant",
          content: existingAnswer,
          sourceType: "PLATFORM_RAG",
          textbookVisuals: [],
          offerGate: false,
        };
        newReady.add(question);
        return;
      }

      // ── Slow path: already in cache from previous session interaction ──────
      if (followUpCache.current[key]) {
        newReady.add(question);
        return;
      }

      // ── Background fetch: call API without blocking UI ─────────────────────
      // Skip if lesson is not yet loaded — backend requires a non-empty lesson.
      // The chip will become available once the lesson is generated.
      if (!lesson || !lesson.trim()) return;
      try {
        const result = await askLessonFollowUp({
          username: user.username,
          grade: chipGrade,
          mode: chipMode,
          subject: chipSubject,
          chapter: chipChapter,
          step_title: chipStepTitle,
          lesson,
          question,
        });
        if (result.success && result.source_type !== "OFFER_GATE") {
          followUpCache.current[key] = {
            role: "assistant",
            content: result.answer,
            sourceType: result.source_type,
            textbookVisuals: result.textbook_visuals || [],
            offerGate: false,
          };
          newReady.add(question);
        }
      } catch {
        // Background pre-fetch failure — chip simply won't appear
      }
    }));

    setCachedChipQuestions((prev) => {
      const merged = new Set(prev);
      newReady.forEach((q) => merged.add(q));
      return merged;
    });
  }

  // ── Exemplar chapter gate ──────────────────────────────────────────────────
  const isExemplarChapter = chapter?.includes("Exemplar:");
  // SECURITY FIX: parentId alone does NOT grant paid access.
  // A child added by a free-plan parent has parentId but no accessCbse.
  // Use hasPaidAccess() which checks accessCbse + subscriptionExpiresAt correctly.
  // Also: subscriptionPlan !== "free" is ambiguous — "free" is the Nano DB key too.
  const hasPaidAccessForLessons = hasPaidAccess(user);
  const isExemplarLocked = isExemplarChapter && !hasPaidAccessForLessons;

  // ── Top-bar layout: compact horizontal selector strip ─────────────────────
  // Inline style helpers shared by all top-bar selects — adaptive to light/dark.
  // CSS variables alone aren't enough because the dark defaults (rgba white) are
  // invisible against a light background; we use explicit light-mode-safe values.
  const _selectStyle = {
    fontSize: STEP_CONTROL_FONT_SIZE,
    padding: "7px 10px",
    borderRadius: 8,
    border: "1px solid var(--border, #d1d5db)",
    background: "var(--panel, #ffffff)",
    color: "var(--text, #111827)",
    cursor: "pointer",
    fontFamily: "inherit",
  };

  const topBarControls = USE_TOP_BAR_LAYOUT ? (
    <div style={{
      display: "flex",
      alignItems: "center",
      gap: 8,
      padding: "10px 16px",
      background: "var(--panel, #ffffff)",
      border: "1px solid var(--border, #e5e7eb)",
      borderRadius: 12,
      marginBottom: 16,
      flexWrap: "wrap",
      boxShadow: "0 1px 4px rgba(0,0,0,.06)",
    }}>
      {/* Compact selectors */}
      <BookOpen size={16} strokeWidth={2.4} color="var(--muted, #6b7280)" style={{ marginRight: 2, flexShrink: 0 }} />
      <select
        value={grade}
        onChange={(e) => handleGradeChange(e.target.value)}
        style={{ ..._selectStyle, maxWidth: 105 }}
      >
        {grades.map(g => <option key={g} value={g}>{g}</option>)}
      </select>
      <select
        value={subject}
        onChange={(e) => handleSubjectChange(e.target.value)}
        disabled={subjects.length === 0}
        style={{ ..._selectStyle, maxWidth: 115 }}
      >
        {subjects.map(s => <option key={s} value={s}>{s}</option>)}
      </select>
      <select
        value={chapter}
        onChange={(e) => {
          setChapter(e.target.value);
          setLesson(""); setAudioUrl(""); resetTextbookVisualBrowser();
          setSourceInfo(""); setFollowUpQuestion(""); setFollowUpMessages([]);
          resetPracticeState();
        }}
        style={{ ..._selectStyle, maxWidth: 220, flex: 1 }}
      >
        {chapters.map(c => {
          const locked = c.includes("Exemplar:") && !hasPaidAccessForLessons;
          return <option key={c} value={c}>{locked ? `🔒 ${c}` : c}</option>;
        })}
      </select>
      {/* Step progress pill */}
      <span style={{ ...stepChipStyle(Object.keys(stepLessons).length === lessonSteps.length), whiteSpace: "nowrap" }}>
        Step {currentStepIndex + 1}/{lessonSteps.length} · {stepTitle}
      </span>
      {/* Generate / Refresh */}
      {!hasSavedLesson && !isExemplarLocked ? (
        <button
          className="primary-btn"
          onClick={handleGenerateLesson}
          disabled={generating}
          style={{ ...stepButtonStyle, display: "inline-flex", alignItems: "center", gap: 6, whiteSpace: "nowrap" }}
        >
          {generating ? "…" : <><Sparkles size={16} strokeWidth={2.4} /> Generate</>}
        </button>
      ) : hasSavedLesson && !isExemplarLocked ? (
        <button
          onClick={async () => {
            const upd = { ...stepLessons };
            delete upd[String(currentStepIndex)];
            setStepLessons(upd); setLesson(""); setAudioUrl("");
            try { await saveChapterProgress({ username: user.username, grade, mode, board: requestBoard, subject, chapter, current_step_index: currentStepIndex, highest_unlocked_step: highestUnlockedStep, completed: false, last_lesson: "", step_lessons: upd }); } catch (e) { /* non-critical */ }
          }}
          style={{
            ...stepButtonStyle,
            display: "inline-flex", alignItems: "center", gap: 6,
            background: "none", border: "none", color: "var(--muted, #888)", cursor: "pointer", textDecoration: "underline",
          }}
        >
          <RotateCcw size={16} strokeWidth={2.4} /> Refresh
        </button>
      ) : null}
    </div>
  ) : null;

  return (
    <div
      className="lesson-workspace premium-page premium-lessons-page"
      style={USE_TOP_BAR_LAYOUT ? { display: "block" } : undefined}
    >
      {/* Top bar replaces sidebar when USE_TOP_BAR_LAYOUT is true */}
      {USE_TOP_BAR_LAYOUT && topBarControls}

      <div
        className="lesson-layout premium-lesson-layout"
        style={USE_TOP_BAR_LAYOUT ? { display: "block" } : undefined}
      >
        {/* Sidebar hidden in top-bar mode */}
        <aside
          className="lesson-control-panel"
          style={USE_TOP_BAR_LAYOUT ? { display: "none" } : undefined}
        >
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

              {/* Grade 9 Social Science — NCERT book not yet released */}
              {grade === "Grade 9" && subject?.toLowerCase().includes("social") && (
                <div style={{
                  background: "rgba(245,158,11,.1)",
                  border: "1px solid rgba(245,158,11,.35)",
                  borderRadius: "10px",
                  padding: "12px 16px",
                  fontSize: ".88rem",
                  color: "var(--text)",
                  lineHeight: 1.55,
                  gridColumn: "1 / -1",
                }}>
                  📚 <strong>Social Science — Grade 9 content coming soon</strong>
                  <br />
                  NCERT has not yet released the updated Class 9 Social Science textbook. Lessons and content for this subject will be added as soon as the official book is published.
                </div>
              )}

              <label>
                Chapter / Section
                <select
                  value={chapter}
                  onChange={(e) => {
                    setChapter(e.target.value);
                    setLesson("");
                    setAudioUrl("");
                    resetTextbookVisualBrowser();
                    setSourceInfo(null);
                    setFollowUpQuestion("");
                    setFollowUpMessages([]);
                    resetPracticeState();
                  }}
                >
                  {chapters.map((c) => {
                    const isLockedOption = c.includes("Exemplar:") && !hasPaidAccessForLessons;
                    return (
                      <option key={c} value={c}>
                        {isLockedOption ? `🔒 ${c}` : c}
                      </option>
                    );
                  })}
                </select>
              </label>

              {/* Lesson Step dropdown hidden when refined layout is active.
                  Step state (currentStepIndex, highestUnlockedStep) is preserved. */}
              {!USE_REFINED_LESSON_EXPERIENCE_LAYOUT && (
                <label>
                  Lesson Step
                  <select
                    value={currentStepIndex}
                    onChange={(e) => {
                      const newIndex = Number(e.target.value);
                      setCurrentStepIndex(newIndex);
                      setLesson(stepLessons[String(newIndex)] || "");
                      setAudioUrl("");
                      resetTextbookVisualBrowser();
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
              )}

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

            {/* Exemplar locked notice for free/promo students */}
            {isExemplarLocked && (
              <div style={{ padding: "12px 14px", borderRadius: 10, background: "rgba(99,102,241,.1)", border: "1px solid rgba(167,139,250,.3)", marginBottom: 8 }}>
                <div style={{ fontSize: ".8rem", fontWeight: 700, color: "#a78bfa", marginBottom: 4 }}>🔐 Exemplar Lesson — Paid Only</div>
                <div style={{ fontSize: ".74rem", color: "var(--muted)", lineHeight: 1.5, marginBottom: 8 }}>Lessons for NCERT Exemplar chapters are available to paid subscribers.</div>
                <button
                  type="button"
                  onClick={() => setActivePage?.("subscriptionPlans")}
                  style={{ padding: "6px 14px", borderRadius: 8, border: "none", background: "linear-gradient(135deg,#6366f1,#8b5cf6)", color: "#fff", fontWeight: 700, fontSize: ".78rem", cursor: "pointer", fontFamily: "inherit" }}>
                  🚀 Upgrade to Unlock
                </button>
              </div>
            )}

            <button
              className="primary-btn premium-generate-btn"
              onClick={handleGenerateLesson}
              disabled={generating || hasSavedLesson || isExemplarLocked}
            >
              {isExemplarLocked
                ? "🔒 Upgrade to Generate Lesson"
                : hasSavedLesson
                ? "Lesson Already Generated"
                : generating
                ? "Generating..."
                : "✨ Generate Lesson"}
            </button>

            {/* Allow re-fetch if admin has updated the pre-warmed lesson */}
            {hasSavedLesson && !isExemplarLocked && !generating && (
              <button
                style={{
                  background: "none",
                  border: "none",
                  color: "#888",
                  fontSize: "0.75rem",
                  cursor: "pointer",
                  marginTop: "0.3rem",
                  textDecoration: "underline",
                  padding: "0",
                }}
                onClick={async () => {
                  // Clear this step from BOTH local state AND the DB progress
                  // so that loadProgress() on the next page load doesn't restore
                  // the stale lesson from the saved step_lessons record.
                  // Then immediately force-refresh from the LLM (bypassing the
                  // Supabase lesson_cache) so the student gets regenerated content
                  // and doesn't get the same stale cache entry back.
                  const updatedStepLessons = { ...stepLessons };
                  delete updatedStepLessons[String(currentStepIndex)];
                  setStepLessons(updatedStepLessons);
                  setLesson("");
                  setAudioUrl("");
                  // Persist the removal so the DB progress doesn't restore old content
                  try {
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
                      last_lesson: "",
                      step_lessons: updatedStepLessons,
                    });
                  } catch {
                    // Non-critical — local state is already cleared
                  }
                  // Force-regenerate from LLM — bypass the Supabase cache entirely
                  // so the student always receives fresh content, not the stale
                  // cache entry that caused the reported issue.
                  handleGenerateLesson(true, true);
                }}
              >
                🔄 Refresh lesson
              </button>
            )}

            {/* Mark Step Complete and Restart Chapter hidden in refined layout.
                Their state logic (highestUnlockedStep, completed) is preserved. */}
            {!USE_REFINED_LESSON_EXPERIENCE_LAYOUT && (
              <div className="button-row premium-lesson-button-row">
                <button
                  className="secondary-btn"
                  disabled={currentStepIndex === 0}
                  onClick={async () => {
                    const newIndex = currentStepIndex - 1;
                    setCurrentStepIndex(newIndex);
                    setLesson(stepLessons[String(newIndex)] || "");
                    setAudioUrl("");
                    resetTextbookVisualBrowser();
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
                      const newHighestUnlockedStep = Math.max(highestUnlockedStep, newIndex);
                      setHighestUnlockedStep(newHighestUnlockedStep);
                      setCurrentStepIndex(newIndex);
                      setLesson(stepLessons[String(newIndex)] || "");
                      setAudioUrl("");
                      resetTextbookVisualBrowser();
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
                    setStepLessons({});
                    setAudioUrl("");
                    resetTextbookVisualBrowser();
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
            )}
          </div>
        </aside>

        <section className="lesson-content-panel premium-lesson-content">
          {/* ── Refined layout: Previous / Next navigation at top of right pane ── */}
          {USE_REFINED_LESSON_EXPERIENCE_LAYOUT && (
            <div
              className="lesson-step-nav-bar"
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "10px 0 14px",
                marginBottom: 4,
                borderBottom: "1px solid var(--border, #e5e7eb)",
              }}
            >
              {/* Left: step label */}
              <span style={{ fontSize: STEP_CONTROL_FONT_SIZE, color: "var(--text-muted, #6b7280)", fontWeight: 500 }}>
                Step {currentStepIndex + 1} of {lessonSteps.length}:&nbsp;
                <strong style={{ color: "var(--text, #111827)" }}>{stepTitle}</strong>
              </span>

              {/* Right: progress % + nav buttons */}
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                {/* Progress badge — solid colors work in both light and dark mode */}
                <span style={stepChipStyle(Object.keys(stepLessons).length === lessonSteps.length)}>
                  {Math.round(Object.keys(stepLessons).length / lessonSteps.length * 100)}% complete
                </span>

                <button
                  className="secondary-btn"
                  disabled={currentStepIndex === 0}
                  style={{ ...stepButtonStyle, display: "inline-flex", alignItems: "center", gap: 6 }}
                  onClick={async () => {
                    const newIndex = currentStepIndex - 1;
                    const savedLesson = stepLessons[String(newIndex)] || "";
                    if (!savedLesson) autoGenerateRef.current = true;
                    setCurrentStepIndex(newIndex);
                    setLesson(savedLesson);
                    setAudioUrl("");
                    resetTextbookVisualBrowser();
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
                  <ArrowLeft size={16} strokeWidth={2.4} /> Previous
                </button>
                <button
                  className="secondary-btn"
                  disabled={currentStepIndex >= lessonSteps.length - 1}
                  title={
                    currentStepIndex >= lessonSteps.length - 1
                      ? "You are on the last step"
                      : `Go to Step ${currentStepIndex + 2}: ${lessonSteps[currentStepIndex + 1] || ""}`
                  }
                  style={{ ...stepButtonStyle, display: "inline-flex", alignItems: "center", gap: 6 }}
                  onClick={async () => {
                    const newIndex = currentStepIndex + 1;
                    if (newIndex >= lessonSteps.length) return;
                    // All steps freely navigable — no unlock gate
                    const newHighest = Math.max(highestUnlockedStep, newIndex);
                    const savedLesson = stepLessons[String(newIndex)] || "";
                    if (!savedLesson) autoGenerateRef.current = true;
                    setHighestUnlockedStep(newHighest);
                    setCurrentStepIndex(newIndex);
                    setLesson(savedLesson);
                    setAudioUrl("");
                    resetTextbookVisualBrowser();
                    resetPracticeState();
                    await saveChapterProgress({
                      username: user.username,
                      grade,
                      mode,
                      subject,
                      chapter,
                      current_step_index: newIndex,
                      highest_unlocked_step: newHighest,
                      completed: false,
                      last_lesson: "",
                      step_lessons: stepLessons,
                    });
                  }}
                >
                  Next <ArrowRight size={16} strokeWidth={2.4} />
                </button>
              </div>
            </div>
          )}

          {error && <div className="error-box">{error}</div>}

          {generating && (
            <div className={`lesson-generating-overlay${gifFading ? " lesson-gif-fading" : ""}`}>
              <img
                src="/likhapohaai.gif"
                alt="Likha Poha AI is preparing your lesson…"
                className="lesson-loading-gif"
              />
              <p className="lesson-loading-label">
                {getLoadingMessage(currentStepIndex, subject)}
              </p>
            </div>
          )}

          {!lesson && !generating && (
            <div className="premium-section premium-empty-lesson">
              <div className="premium-header">
                <p className="eyebrow">Ready when you are</p>
                <h2>Start your next AI-guided lesson</h2>
              </div>

              {/* Step-by-step how-to guide */}
              <div className="premium-card" style={{ background: "linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%)", border: "1px solid #bae6fd", marginBottom: 24 }}>
                <h3 style={{ margin: "0 0 16px", fontSize: "1rem", color: "#0369a1" }}>📖 How to use Lessons — 5 simple steps</h3>
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  {[
                    { n: "1", icon: "⬅️", text: "Select your Grade, Subject, and Chapter from the left panel" },
                    { n: "2", icon: "✨", text: 'Click "Generate Lesson" — each chapter has 5 steps, always start from Step 1' },
                    { n: "3", icon: "📚", text: "Read the lesson carefully. Use 🔊 Listen to hear it aloud" },
                    { n: "4", icon: "🎲", text: 'Click "Generate 2 Practice Questions", answer them to test your understanding' },
                    { n: "5", icon: "✅", text: 'Click "Mark Step Complete" to unlock the next step and move forward' },
                  ].map(({ n, icon, text }) => (
                    <div key={n} style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
                      <span style={{
                        minWidth: 24, height: 24, borderRadius: "50%",
                        background: "#0ea5e9", color: "#fff",
                        display: "flex", alignItems: "center", justifyContent: "center",
                        fontSize: "0.75rem", fontWeight: 700, flexShrink: 0, marginTop: 1,
                      }}>{n}</span>
                      <span style={{ fontSize: "0.88rem", color: "#374151", lineHeight: 1.5 }}>
                        {icon} {text}
                      </span>
                    </div>
                  ))}
                </div>
                <p style={{ fontSize: "0.78rem", color: "#6b7280", marginTop: 12, marginBottom: 0 }}>
                  💡 Complete all 5 steps of a chapter to unlock the full chapter. Then try a Mock Test!
                </p>
              </div>

              <div className="premium-grid premium-grid-3">
                <div className="premium-card premium-glow-card glow-blue">
                  <h3>📘 5-Step Learning</h3>
                  <p>Each chapter has 5 steps: Intro → Core → Examples → Exam Problems → Revision.</p>
                </div>

                <div className="premium-card premium-glow-card glow-purple">
                  <h3>🔊 Listen & Learn</h3>
                  <p>Every lesson can be read aloud so you can learn while relaxing.</p>
                </div>

                <div className="premium-card premium-glow-card glow-green">
                  <h3>� Ask Doubts</h3>
                  <p>Ask follow-up questions inside the lesson. Pre-answered questions shown as chips.</p>
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
                    subject={subject}
                    grade={grade}
                    cardStyle={cardStyle}
                    cardTheme={cardTheme}
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
                        {"Quick practice to help you remember and apply what you've learned."}
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
                                <div className="practice-status-box coaching">
                                  <strong>🧠 Practice feedback saved</strong>
                                  <p>
                                    {isHindiPractice
                                      ? `Result: ${currentCorrect ? "Correct" : "Incorrect"}. Read the note above before writing your own answer.`
                                      : "Review the feedback above and try to improve your answer. You can continue to the next step anytime."}
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

                {shouldShowTextbookVisualTools() && (
                  <div className="textbook-visual-browser-card premium-card premium-glow-card glow-blue">
                    <div className="visual-generator-header">
                      <h3>📖 Textbook visuals only</h3>

                      <p>
                        Choose from approved visuals extracted from this exact
                        lesson. AI-generated images are not used here.
                      </p>
                    </div>

                    {textbookVisualsLoading && (
                      <div className="textbook-visual-note">
                        Loading approved textbook visuals...
                      </div>
                    )}

                    {!textbookVisualsLoading && textbookVisuals.length > 0 && (
                      <div className="textbook-visual-picker">
                        {textbookVisuals.map((visual) => (
                          <button
                            key={visual.id}
                            type="button"
                            className={
                              selectedTextbookVisual?.id === visual.id
                                ? "textbook-visual-option selected"
                                : "textbook-visual-option"
                            }
                            onClick={() => {
                              setSelectedTextbookVisual(visual);
                              setTextbookVisualError("");
                            }}
                          >
                            <img
                              src={visual.asset_url}
                              alt={
                                visual.caption ||
                                `${visual.chapter} textbook page ${visual.page_number}`
                              }
                            />

                            <span>
                              Page {visual.page_number}
                              <small>
                                {visual.caption ||
                                  visual.title ||
                                  "Approved textbook visual"}
                              </small>
                            </span>
                          </button>
                        ))}
                      </div>
                    )}

                    <div className="textbook-visual-search">
                      <input
                        className="textbook-visual-input"
                        type="text"
                        placeholder="Search text in approved visuals, e.g. cell wall or grandmother"
                        value={textbookVisualQuery}
                        onChange={(e) => setTextbookVisualQuery(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") {
                            e.preventDefault();
                            handleFindTextbookVisual();
                          }
                        }}
                      />

                      <button
                        className="secondary-btn textbook-visual-search-btn"
                        onClick={handleFindTextbookVisual}
                        disabled={textbookVisualSearching}
                      >
                        {textbookVisualSearching ? "Searching..." : "Search visuals"}
                      </button>
                    </div>

                    {textbookVisualSearchResults.length > 0 && (
                      <div className="textbook-visual-results">
                        <strong>Matching textbook visual(s)</strong>

                        <div className="textbook-visual-picker">
                          {textbookVisualSearchResults.map((visual) => {
                            const callout = getTextbookVisualCallout(
                              visual,
                              textbookVisualQuery
                            );

                            return (
                              <button
                                key={visual.id}
                                type="button"
                                className={
                                  selectedTextbookVisual?.id === visual.id
                                    ? "textbook-visual-option selected"
                                    : "textbook-visual-option"
                                }
                                onClick={() => {
                                  setSelectedTextbookVisual(visual);
                                  setTextbookVisualError("");
                                }}
                              >
                                <img
                                  src={visual.asset_url}
                                  alt={
                                    visual.caption ||
                                    `${visual.chapter} textbook page ${visual.page_number}`
                                  }
                                />

                                <span>
                                  Page {visual.page_number}
                                  <small>
                                    {visual.caption ||
                                      visual.title ||
                                      "Approved textbook visual"}
                                  </small>
                                </span>

                                <small className="textbook-visual-callout">
                                  {renderHighlightedText(
                                    callout,
                                    textbookVisualQuery
                                  )}
                                </small>
                              </button>
                            );
                          })}
                        </div>
                      </div>
                    )}

                    {!textbookVisualsLoading &&
                      !textbookVisuals.length &&
                      !textbookVisualSearchResults.length && (
                      <div className="textbook-visual-note">
                        No approved textbook visuals are available for this
                        lesson yet.
                      </div>
                    )}

                    {textbookVisualError && (
                      <div className="visual-error-box">
                        {textbookVisualError}
                      </div>
                    )}
                  </div>
                )}

                {selectedTextbookVisual && shouldShowTextbookVisualTools() && (
                  <div className="visual-image-card premium-card textbook-selected-visual-card">
                    <div className="visual-image-header">
                      <h3>📖 Textbook Visual</h3>
                    </div>

                    <img
                      src={selectedTextbookVisual.asset_url}
                      alt={
                        selectedTextbookVisual.caption ||
                        `${selectedTextbookVisual.chapter} textbook page ${selectedTextbookVisual.page_number}`
                      }
                    />

                    <p className="textbook-selected-caption">
                      {selectedTextbookVisual.caption ||
                        `${selectedTextbookVisual.chapter} - page ${selectedTextbookVisual.page_number}`}
                    </p>
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
                      <div className="lesson-chat-thread" ref={chatBottomRef}>
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

                            {msg.offerGate ? (
                              <div style={{
                                background: "rgba(99,102,241,.07)",
                                border: "1.5px solid rgba(99,102,241,.3)",
                                borderRadius: "12px",
                                padding: "18px 20px",
                                textAlign: "center",
                                marginTop: 8,
                              }}>
                                <p style={{ fontSize: "1.3rem", marginBottom: 6 }}>🔒</p>
                                <p style={{ fontWeight: 600, marginBottom: 8, fontSize: "0.95rem" }}>
                                  This doubt is outside your current access
                                </p>
                                <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginBottom: 16, lineHeight: 1.6 }}>
                                  Your offer gives you a taste of Likha Poha AI across select topics.
                                  To ask the AI anything — any subject, any chapter, any question —
                                  a paid subscription unlocks it all.
                                </p>
                                <button
                                  type="button"
                                  onClick={() => setActivePage?.("subscriptionPlans")}
                                  style={{
                                    display: "inline-block",
                                    background: "var(--accent, #6366f1)",
                                    color: "#fff",
                                    borderRadius: "8px",
                                    padding: "8px 20px",
                                    fontWeight: 600,
                                    fontSize: "0.85rem",
                                    border: "none",
                                    cursor: "pointer",
                                  }}
                                >
                                  See plans →
                                </button>
                              </div>
                            ) : (
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
                            )}

                            {msg.sourceType && !msg.offerGate && (
                              <span className="chat-source-chip">
                                {msg.sourceType === "PLATFORM_RAG"
                                  ? "🏷 Platform"
                                  : msg.sourceType === "RAG"
                                  ? "📚 RAG"
                                  : "🤖 LLM"}
                              </span>
                            )}

                            {msg.textbookVisuals?.length > 0 && (
                              <div className="textbook-visual-strip">
                                {msg.textbookVisuals.map((visual) => (
                                  <figure
                                    key={visual.id}
                                    className="textbook-visual-card"
                                  >
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
                                        Page {visual.page_number} •{" "}
                                        {visual.chapter}
                                      </span>
                                    </figcaption>
                                  </figure>
                                ))}
                              </div>
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
                        {((() => {
                          // Show only LKB chips that are in the cache.
                          // No static fallback — chips come from LKB only.
                          return doubtSuggestions
                            .map((s) => s.question)
                            .filter((chip) => cachedChipQuestions.has(chip));
                        })()).map((chip) => (
                          <button
                            key={chip}
                            type="button"
                            className={`followup-chip${activeChip === chip ? " followup-chip--active" : ""}`}
                            disabled={practiceModeActive || followUpLoading}
                            onClick={() => {
                              setActiveChip(chip);
                              handleAskFollowUp(chip);
                            }}
                          >
                            {chip}
                          </button>
                        ))}
                      </div>

                      <button
                        className="primary-btn followup-submit-btn"
                        onClick={() => handleAskFollowUp()}
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

            </>
          )}

          {/* ── Bottom navigation bar — mirrors top nav + "What's next" preview ── */}
          {USE_REFINED_LESSON_EXPERIENCE_LAYOUT && lesson && (
            <div style={{
              marginTop: 32,
              borderTop: "1px solid var(--border, #e5e7eb)",
              paddingTop: 20,
            }}>
              {/* Bottom prev/next buttons */}
              <div style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                flexWrap: "wrap",
                gap: 10,
              }}>
                <span style={{ fontSize: STEP_CONTROL_FONT_SIZE, color: "var(--text-muted, #6b7280)", fontWeight: 500 }}>
                  Step {currentStepIndex + 1} of {lessonSteps.length}:&nbsp;
                  <strong style={{ color: "var(--text, #111827)" }}>{stepTitle}</strong>
                </span>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <span style={stepChipStyle(Object.keys(stepLessons).length === lessonSteps.length)}>
                    {Math.round(Object.keys(stepLessons).length / lessonSteps.length * 100)}% complete
                  </span>
                  <button
                    className="secondary-btn"
                    disabled={currentStepIndex === 0}
                    style={{ ...stepButtonStyle, display: "inline-flex", alignItems: "center", gap: 6 }}
                    onClick={async () => {
                      const newIndex = currentStepIndex - 1;
                      const savedLesson = stepLessons[String(newIndex)] || "";
                      if (!savedLesson) autoGenerateRef.current = true;
                      setCurrentStepIndex(newIndex);
                      setLesson(savedLesson);
                      setAudioUrl("");
                      resetTextbookVisualBrowser();
                      setCompleted(false);
                      resetPracticeState();
                      await saveChapterProgress({
                        username: user.username, grade, mode, subject, chapter,
                        current_step_index: newIndex,
                        highest_unlocked_step: highestUnlockedStep,
                        completed: false, last_lesson: "", step_lessons: stepLessons,
                      });
                    }}
                  >
                    <ArrowLeft size={16} strokeWidth={2.4} /> Previous
                  </button>
                  <button
                    className="secondary-btn"
                    disabled={currentStepIndex >= lessonSteps.length - 1}
                    style={{ ...stepButtonStyle, display: "inline-flex", alignItems: "center", gap: 6 }}
                    onClick={async () => {
                      const newIndex = currentStepIndex + 1;
                      if (newIndex >= lessonSteps.length) return;
                      const newHighest = Math.max(highestUnlockedStep, newIndex);
                      const savedLesson = stepLessons[String(newIndex)] || "";
                      if (!savedLesson) autoGenerateRef.current = true;
                      setHighestUnlockedStep(newHighest);
                      setCurrentStepIndex(newIndex);
                      setLesson(savedLesson);
                      setAudioUrl("");
                      resetTextbookVisualBrowser();
                      resetPracticeState();
                      await saveChapterProgress({
                        username: user.username, grade, mode, subject, chapter,
                        current_step_index: newIndex,
                        highest_unlocked_step: newHighest,
                        completed: false, last_lesson: "", step_lessons: stepLessons,
                      });
                    }}
                  >
                    Next <ArrowRight size={16} strokeWidth={2.4} />
                  </button>
                </div>
              </div>

              {/* "What you'll learn next" preview */}
              {currentStepIndex < lessonSteps.length - 1 && (
                <div style={{
                  marginTop: 16,
                  background: "linear-gradient(135deg, rgba(99,102,241,0.06), rgba(139,92,246,0.04))",
                  border: "1px solid rgba(99,102,241,0.18)",
                  borderRadius: 12,
                  padding: "14px 18px",
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                }}>
                  <span style={{ fontSize: "1.4rem", flexShrink: 0 }}>🔭</span>
                  <div>
                    <div style={{ fontSize: "0.72rem", fontWeight: 700, color: "#6366f1", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 2 }}>
                      Up next — Step {currentStepIndex + 2} of {lessonSteps.length}
                    </div>
                    <div style={{ fontSize: "0.88rem", fontWeight: 700, color: "var(--text, #111827)" }}>
                      {lessonSteps[currentStepIndex + 1]}
                    </div>
                    <div style={{ fontSize: "0.75rem", color: "var(--text-muted, #6b7280)", marginTop: 2 }}>
                      {stepLessons[String(currentStepIndex + 1)]
                        ? "Ready to continue — click Next ➡ to load it."
                        : "Click Next ➡ — will auto-load from pre-warmed cache ⚡"}
                    </div>
                  </div>
                </div>
              )}

              {/* Last step completion message */}
              {currentStepIndex === lessonSteps.length - 1 && (
                <div style={{
                  marginTop: 16,
                  background: "linear-gradient(135deg, rgba(34,197,94,0.08), rgba(16,185,129,0.05))",
                  border: "1px solid rgba(34,197,94,0.25)",
                  borderRadius: 12,
                  padding: "14px 18px",
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                }}>
                  <span style={{ fontSize: "1.4rem", flexShrink: 0 }}>🎉</span>
                  <div>
                    <div style={{ fontSize: "0.88rem", fontWeight: 700, color: "#15803d" }}>
                      You've reached the last step of this chapter!
                    </div>
                    <div style={{ fontSize: "0.75rem", color: "var(--text-muted, #6b7280)", marginTop: 2 }}>
                      Take a mock test or try another chapter to keep progressing.
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

        </section>
      </div>
    </div>
  );
}

export default LessonsPage;
