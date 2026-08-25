/**
 * Lessons tab — syllabus selector + structured lesson rendering.
 *
 * Phase 2 (2026-07-13):
 *   - Lesson markdown is parsed into named sections (same parseSections logic
 *     as the web's LessonSections.jsx).
 *   - Each section is rendered as a color-coded card matching the web's
 *     Card Feed layout: intro (blue), concept (amber), example (green),
 *     warning (orange), check (red), summary (purple).
 *   - Section content uses react-native-markdown-display with rich styles.
 *   - "Step N / N" progress bar shown during exam.
 *   - Step navigation (Prev / Next) replaces the chip row for cleaner UX.
 */
import { useEffect, useRef, useState } from "react";
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity,
  ActivityIndicator, Alert, Image, Animated, Platform,
} from "react-native";
import Markdown from "react-native-markdown-display";
import { Feather } from "@expo/vector-icons";
import { authFetch } from "../../lib/authFetch";
import { useUserProfile } from "../../lib/UserProfileContext";
import { BRAND_COLOR } from "../../constants";
import { STREAM_SUBJECTS } from "@likhapoha/shared/utils/subjectAccess";
import { normalizeTutorMarkdown } from "@likhapoha/shared/utils/markdownCleanup";
import { extractChapterSummaries } from "@likhapoha/shared/utils/chapterSummary";
import { extractChapterInfographics } from "@likhapoha/shared/utils/chapterInfographic";
import ChapterJourney, { ChapterDocData } from "../../components/ChapterJourney";
import ChapterSummaryCard, { ChapterSummary } from "../../components/ChapterSummaryCard";
import ChapterInfographicCard, { ChapterInfographic } from "../../components/ChapterInfographicCard";

// ── Dynamic loading messages — mirrors web LessonsPage.jsx getLoadingMessage ──
const LOADING_MESSAGES: Record<number, Record<string, string>> = {
  0: {
    maths:   "Solving the equation of understanding — your foundation is loading 🔢",
    science: "Setting up the experiment — concept intro being prepared in the AI lab 🔬",
    hindi:   "पाठ की नींव रखी जा रही है… शब्दों का जादू अभी शुरू होता है ✍️",
    social:  "Turning the pages of history — your foundation lesson is loading 🌍",
    english: "Crafting your introduction with the finest words in the dictionary 📚",
    default: "Your AI tutor is reading the textbook so you don't have to… 📖",
  },
  1: {
    maths:   "Crunching the numbers — your core maths concepts are being assembled 🔢",
    science: "The AI lab is running the experiment — core concepts incoming 🧪",
    hindi:   "गहराई से समझाने की तैयारी है… आपका विशेष पाठ बन रहा है 🖊️",
    social:  "Connecting history, geography, and civics just for you 🗺️",
    english: "Every word chosen carefully — your core lesson is being written ✒️",
    default: "Digging deeper — your AI tutor is connecting the dots just for you 🧩",
  },
  2: {
    maths:   "Solving step by step — worked examples are being calculated ✏️",
    science: "Running the experiment with real worked examples — results loading 🔭",
    hindi:   "उदाहरणों से सीखें — आपके लिए खास उदाहरण तैयार हो रहे हैं 📝",
    social:  "Real events, real maps, real examples — loading just for you 🗺️",
    english: "Show, don't tell — worked examples are being crafted with care 📖",
    default: "Cooking up real-world examples — watch and learn mode: ON 🍳",
  },
  3: {
    maths:   "CBSE maths problems incoming — sharpen your pencil ✏️",
    science: "Exam-style science questions being calibrated — accuracy loading 🎯",
    hindi:   "परीक्षा की तैयारी हो रही है — CBSE स्तर के प्रश्न आ रहे हैं 🏆",
    social:  "Exam-level questions from history and civics — loading now 🎓",
    english: "Grammar, comprehension, and expression — exam mode ON 🏅",
    default: "Sharpening your exam skills ⚔️ CBSE-style practice questions being forged…",
  },
  4: {
    maths:   "Recapping all formulas and methods — your maths revision is loading 📐",
    science: "Summarising the key science concepts — your revision is almost ready 🧬",
    hindi:   "पूरे पाठ का निचोड़ तैयार हो रहा है… एक आखिरी नज़र 🌟",
    social:  "History, geography, civics — all packed into your crisp revision 🗺️",
    english: "Key grammar, literary devices, and tips — revision loading 📚",
    default: "Pulling all steps of learning into a crisp revision — almost there 🚀",
  },
  5: {
    maths:   "Final formula check — getting your maths fully exam-ready 🏆",
    science: "Last-minute science essentials — exam preparation loading 🎓",
    hindi:   "परीक्षा की अंतिम तैयारी — सब कुछ आपके लिए तैयार हो रहा है 🌟",
    social:  "Final revision of key events and concepts — exam prep loading 🎓",
    english: "Last-minute tips and tricks — English exam prep is ready 📝",
    default: "Final polish mode 🎓 Getting you fully exam-ready…",
  },
};

function getLoadingMessage(stepIndex: number, subject: string): string {
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

// ── Animated loading dots ─────────────────────────────────────────────────────
function AnimatedDots() {
  const dots = [useRef(new Animated.Value(0)).current, useRef(new Animated.Value(0)).current, useRef(new Animated.Value(0)).current];
  useEffect(() => {
    const animations = dots.map((dot, i) =>
      Animated.loop(
        Animated.sequence([
          Animated.delay(i * 200),
          Animated.timing(dot, { toValue: 1, duration: 400, useNativeDriver: true }),
          Animated.timing(dot, { toValue: 0, duration: 400, useNativeDriver: true }),
          Animated.delay((2 - i) * 200),
        ])
      )
    );
    animations.forEach(a => a.start());
    return () => animations.forEach(a => a.stop());
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <View style={{ flexDirection: "row", gap: 6, marginTop: 14 }}>
      {dots.map((dot, i) => (
        <Animated.View key={i} style={{
          width: 8, height: 8, borderRadius: 4,
          backgroundColor: BRAND_COLOR,
          opacity: dot,
          transform: [{ translateY: dot.interpolate({ inputRange: [0, 1], outputRange: [0, -6] }) }],
        }} />
      ))}
    </View>
  );
}

type SyllabusData = Record<string, Record<string, Record<string, string[]>>>;

const LESSON_STEPS_BY_GRADE: Record<string, string[]> = {
  default: ["Concept introduction", "Core explanation", "Worked examples", "Exam-style problems", "Revision and recap"],
  "Grade 6": ["Concept introduction", "Core explanation", "Worked examples", "Revision and recap"],
  "Grade 7": ["Concept introduction", "Core explanation", "Worked examples", "Revision and recap"],
  "Grade 8": ["Concept introduction", "Core explanation", "Worked examples", "Revision and recap"],
  "Grade 10": ["Concept introduction", "Core explanation", "Worked examples", "Exam-style problems", "Revision and recap", "Exam preparation"],
  "Grade 11": ["Concept introduction", "Core explanation", "Worked examples", "Exam-style problems", "Revision and recap", "Exam preparation"],
  "Grade 12": ["Concept introduction", "Core explanation", "Worked examples", "Exam-style problems", "Revision and recap", "Exam preparation"],
};

// ── Section type detection (mirrors web getSectionType) ──────────────────────
type SectionType = "intro" | "concept" | "example" | "warning" | "check" | "summary" | "default";

const SECTION_CARDS: Record<SectionType, {
  bg: string; border: string; accent: string; icon: string; label: string; labelColor: string;
}> = {
  intro:   { bg: "rgba(59,130,246,.07)",  border: "rgba(59,130,246,.3)",  accent: "#3b82f6", icon: "🎯", label: "Introduction",  labelColor: "#1d4ed8" },
  concept: { bg: "rgba(245,158,11,.07)",  border: "rgba(245,158,11,.3)",  accent: "#f59e0b", icon: "📘", label: "Concept",       labelColor: "#b45309" },
  example: { bg: "rgba(34,197,94,.07)",   border: "rgba(34,197,94,.3)",   accent: "#22c55e", icon: "🧪", label: "Examples",      labelColor: "#15803d" },
  warning: { bg: "rgba(249,115,22,.07)",  border: "rgba(249,115,22,.3)",  accent: "#f97316", icon: "⚠️", label: "Watch Out",     labelColor: "#c2410c" },
  check:   { bg: "rgba(239,68,68,.07)",   border: "rgba(239,68,68,.3)",   accent: "#ef4444", icon: "✅", label: "Quick Check",   labelColor: "#dc2626" },
  summary: { bg: "rgba(139,92,246,.07)",  border: "rgba(139,92,246,.3)",  accent: "#8b5cf6", icon: "📌", label: "Summary",       labelColor: "#7c3aed" },
  default: { bg: "rgba(107,114,128,.05)", border: "rgba(107,114,128,.2)", accent: "#6b7280", icon: "📚", label: "Lesson",        labelColor: "#374151" },
};

function getSectionType(title: string): SectionType {
  const t = (title || "").toLowerCase();
  if (t.includes("what you will learn") || t.includes("introduction") || t.includes("overview") || t.includes("context"))
    return "intro";
  if (t.includes("simple explanation") || t.includes("core explanation") || t.includes("concept") || t.includes("explanation") || t.includes("breakdown"))
    return "concept";
  if (t.includes("worked example") || t.includes("example") || t.includes("step-by-step") || t.includes("step by step"))
    return "example";
  if (t.includes("common mistake") || t.includes("warning") || t.includes("avoid") || t.includes("do not"))
    return "warning";
  if (t.includes("quick check") || t.includes("check question") || t.includes("practice") || t.includes("self check"))
    return "check";
  if (t.includes("summary") || t.includes("recap") || t.includes("revision") || t.includes("review") || t.includes("key points"))
    return "summary";
  return "default";
}

// ── Section parser (mirrors web parseSections) ────────────────────────────────
interface Section { title: string; content: string; }

function cleanTitle(title: string): string {
  return title.replace(/\*\*/g, "").replace(/#/g, "").trim();
}

function detectHeading(line: string): string | null {
  // Pattern 1 & 2: numbered heading with optional # or ** wrapper
  let m = line.match(/^#{0,3}\s*\**\s*(\d+\.\s+.+?)\**\s*$/);
  if (m) {
    const captured = m[1].replace(/^\d+\.\s*/, "").trim();
    if (captured.length <= 65 && !/[.?!]$/.test(captured)) return captured;
  }
  // Pattern 3: markdown heading ## or ###
  m = line.match(/^#{1,3}\s+(.+)$/);
  if (m) {
    const title = m[1].replace(/\*\*/g, "").trim();
    if (title.length >= 3) return title;
  }
  // Pattern 4: Step N: Title / named section keywords
  m = line.match(/^(Step\s+\d+|Question|Summary|Introduction|Conclusion|Common\s+Mistake|Quick\s+Check|What\s+You\s+Will\s+Learn|Worked\s+Example|Overview)\s*:\s*(.*)$/i);
  if (m) {
    const label = m[1].trim();
    const rest = (m[2] || "").trim();
    const combined = rest ? `${label}: ${rest}` : label;
    if (combined.length >= 3 && combined.length <= 70 && !/[.?!]$/.test(combined)) return combined;
  }
  // Pattern 5: standalone bold line
  m = line.match(/^\*\*(.+?)\*\*:?\s*$/);
  if (m) {
    const title = m[1].trim();
    if (title.length >= 4 && title.length <= 80 && !/^[a-z]/.test(title)) return title;
  }
  return null;
}

function parseSections(markdown: string): Section[] {
  const lines = markdown.split("\n");
  const sections: Section[] = [];
  let currentTitle: string | null = null;
  let currentContent: string[] = [];

  for (const line of lines) {
    const title = detectHeading(line);
    if (title) {
      if (currentContent.join("\n").trim()) {
        sections.push({ title: cleanTitle(currentTitle || "Introduction"), content: currentContent.join("\n") });
      }
      currentTitle = title;
      currentContent = [];
    } else {
      currentContent.push(line);
    }
  }
  if (currentContent.join("\n").trim()) {
    sections.push({ title: cleanTitle(currentTitle || "Introduction"), content: currentContent.join("\n") });
  }
  return sections;
}

// ── LaTeX → Unicode converter ─────────────────────────────────────────────────
// Converts common LaTeX expressions to readable Unicode text so formulas
// display correctly in react-native-markdown-display (no KaTeX support).
// Fixes screenshot bug: $$(formula)$$ rendered as raw LaTeX text.
function mathToUnicode(latex: string): string {
  return latex
    .replace(/\\text\{([^}]+)\}/g, "$1")
    .replace(/\\frac\{([^}]+)\}\{([^}]+)\}/g, "($1)/($2)")
    .replace(/\\sqrt\{([^}]+)\}/g, "√($1)")
    .replace(/\\sqrt\s*([a-zA-Z0-9])/g, "√$1")
    // Superscripts
    .replace(/\^\{2\}/g, "²").replace(/\^2(?![0-9{])/g, "²")
    .replace(/\^\{3\}/g, "³").replace(/\^3(?![0-9{])/g, "³")
    .replace(/\^\{n\}/g, "ⁿ")
    .replace(/\^\{([^}]+)\}/g, "^($1)")
    // Subscripts
    .replace(/\_\{1\}/g, "₁").replace(/_1(?![0-9])/g, "₁")
    .replace(/\_\{2\}/g, "₂").replace(/_2(?![0-9])/g, "₂")
    .replace(/\_\{3\}/g, "₃").replace(/_3(?![0-9])/g, "₃")
    .replace(/\_\{0\}/g, "₀").replace(/_0(?![0-9])/g, "₀")
    .replace(/\_\{([^}]+)\}/g, "_($1)")
    // Operators and symbols
    .replace(/\\times/g, "×").replace(/\\cdot/g, "·")
    .replace(/\\div/g, "÷").replace(/\\pm/g, "±").replace(/\\mp/g, "∓")
    .replace(/\\leq/g, "≤").replace(/\\geq/g, "≥").replace(/\\neq/g, "≠")
    .replace(/\\approx/g, "≈").replace(/\\sim/g, "~").replace(/\\cong/g, "≅")
    .replace(/\\infty/g, "∞").replace(/\\partial/g, "∂").replace(/\\nabla/g, "∇")
    .replace(/\\therefore/g, "∴").replace(/\\because/g, "∵")
    .replace(/\\rightarrow/g, "→").replace(/\\leftarrow/g, "←").replace(/\\Rightarrow/g, "⇒")
    .replace(/\\in/g, "∈").replace(/\\notin/g, "∉").replace(/\\subset/g, "⊂")
    .replace(/\\cup/g, "∪").replace(/\\cap/g, "∩").replace(/\\emptyset/g, "∅")
    .replace(/\\forall/g, "∀").replace(/\\exists/g, "∃")
    // Greek letters
    .replace(/\\pi/g, "π").replace(/\\Pi/g, "Π")
    .replace(/\\alpha/g, "α").replace(/\\beta/g, "β").replace(/\\gamma/g, "γ")
    .replace(/\\delta/g, "δ").replace(/\\Delta/g, "Δ").replace(/\\epsilon/g, "ε")
    .replace(/\\theta/g, "θ").replace(/\\Theta/g, "Θ").replace(/\\lambda/g, "λ")
    .replace(/\\Lambda/g, "Λ").replace(/\\mu/g, "μ").replace(/\\nu/g, "ν")
    .replace(/\\xi/g, "ξ").replace(/\\rho/g, "ρ").replace(/\\sigma/g, "σ")
    .replace(/\\Sigma/g, "Σ").replace(/\\tau/g, "τ").replace(/\\phi/g, "φ")
    .replace(/\\Phi/g, "Φ").replace(/\\psi/g, "ψ").replace(/\\Psi/g, "Ψ")
    .replace(/\\omega/g, "ω").replace(/\\Omega/g, "Ω")
    // Trig / log
    .replace(/\\sin/g, "sin").replace(/\\cos/g, "cos").replace(/\\tan/g, "tan")
    .replace(/\\log/g, "log").replace(/\\ln/g, "ln").replace(/\\exp/g, "exp")
    .replace(/\\lim/g, "lim").replace(/\\sum/g, "Σ").replace(/\\prod/g, "Π")
    .replace(/\\int/g, "∫")
    // Remove remaining LaTeX wrappers — expose inner content
    .replace(/\\[a-zA-Z]+\{([^}]+)\}/g, "$1")
    .replace(/\\[a-zA-Z]+/g, "")
    // Clean up spacing and braces
    .replace(/\{([^}]*)\}/g, "$1")
    .replace(/\s+/g, " ")
    .trim();
}

// ── MathAwareMarkdown — renders $$ display blocks + converts $inline$ ─────────
// react-native-markdown-display has no LaTeX support. This component:
//  1. Splits content by $$...$$ display math blocks
//  2. Renders each display block as a styled formula card (📐)
//  3. Converts $...$$ inline math → Unicode text in markdown passages
function MathAwareMarkdown({ content, accent }: { content: string; accent: string }) {
  // Pull out ```chapter-summary fences BEFORE anything else. React Native's
  // markdown renderer has no per-fence component hook (unlike react-markdown
  // on the web), so a fence left in the text renders as a wall of raw JSON.
  // Extracting here covers every mobile caller at once: this lessons tab and
  // ChapterJourney, which receives this component via its renderMarkdown prop.
  const { text: withoutSummaries, summaries } = extractChapterSummaries(content) as {
    text: string;
    summaries: ChapterSummary[];
  };
  const { text: withoutBlocks, infographics } = extractChapterInfographics(withoutSummaries) as {
    text: string;
    infographics: ChapterInfographic[];
  };
  // Run the same shared cleanup pass the web LessonMarkdown uses first —
  // model output often writes display math as "[ \frac{a}{b} ]" (plain
  // square brackets) rather than "$$...$$". Without this, that content
  // never matches DISPLAY_MATH_RE below and renders as raw LaTeX text.
  const normalized: string = normalizeTutorMarkdown(withoutBlocks);
  // Split on $$...$$ (multiline)
  const DISPLAY_MATH_RE = /(\$\$[\s\S]+?\$\$)/g;
  const parts = normalized.split(DISPLAY_MATH_RE);

  return (
    <View>
      {parts.map((part, i) => {
        // Display math block
        if (part.startsWith("$$") && part.endsWith("$$")) {
          const latex = part.slice(2, -2).trim();
          const rendered = mathToUnicode(latex);
          return (
            <View key={i} style={[mathStyles.displayBlock, { borderLeftColor: accent, backgroundColor: accent + "0C" }]}>
              <Text style={mathStyles.displayIcon}>📐</Text>
              <Text style={[mathStyles.displayText, { color: "#111827" }]}>{rendered}</Text>
            </View>
          );
        }
        // Regular markdown — convert inline $...$ to unicode first
        const processed = part.replace(/\$([^$\n]+)\$/g, (_m, latex) => mathToUnicode(latex));
        if (!processed.trim()) return null;
        return (
          <Markdown key={i} style={buildMarkdownStyles(accent)}>{processed}</Markdown>
        );
      })}
      {summaries.map((summary, i) => (
        <ChapterSummaryCard key={`chapter-summary-${i}`} summary={summary} />
      ))}
      {infographics.map((infographic, i) => (
        <ChapterInfographicCard key={`chapter-infographic-${i}`} infographic={infographic} />
      ))}
    </View>
  );
}

const mathStyles = StyleSheet.create({
  displayBlock: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 8,
    borderLeftWidth: 3,
    borderRadius: 8,
    padding: 12,
    marginVertical: 8,
  },
  displayIcon: { fontSize: 16, flexShrink: 0, marginTop: 1 },
  displayText: {
    flex: 1,
    fontSize: 15,
    fontFamily: "monospace",
    lineHeight: 22,
    fontWeight: "600",
  },
});

// ── MCQ parser for Quick Check sections ──────────────────────────────────────
interface MCQParsed {
  question: string;
  options: { key: string; text: string }[];
  answer: string;   // "A" | "B" | "C" | "D"
  explanation: string;
}

function parseMCQ(content: string): MCQParsed | null {
  // Normalise: strip markdown bold/italic, clean up whitespace
  const text = content.replace(/\*\*/g, "").replace(/\*/g, "").trim();
  const lines = text.split("\n").map(l => l.trim()).filter(Boolean);

  // Detect option lines: "A) ...", "A. ...", "(A) ...", "a) ...", "a. ..."
  const OPTION_RE = /^([A-Da-d])[.)]\s*(.+)$/;
  const optionIndices: number[] = [];
  lines.forEach((line, i) => { if (OPTION_RE.test(line)) optionIndices.push(i); });

  // Need at least 2 options (ideally 4) to be a valid MCQ
  if (optionIndices.length < 2) return null;

  // Question = everything before the first option
  const firstOptionIdx = optionIndices[0];
  const questionLines = lines.slice(0, firstOptionIdx);
  const question = questionLines
    .filter(l => !/^quick check|^question\s*:/i.test(l))
    .join(" ")
    .trim();

  if (!question || question.length < 5) return null;

  // Options
  const options: { key: string; text: string }[] = [];
  for (const idx of optionIndices) {
    const m = lines[idx].match(OPTION_RE);
    if (m) options.push({ key: m[1].toUpperCase(), text: m[2].trim() });
  }

  // Answer: look for "Answer: B", "Correct answer: C", "Ans: A" after options
  let answer = "";
  const ANSWER_RE = /(?:correct\s+)?ans(?:wer)?\s*:\s*([A-Da-d])/i;
  const afterOptions = lines.slice(optionIndices[optionIndices.length - 1] + 1);
  for (const line of afterOptions) {
    const m = line.match(ANSWER_RE);
    if (m) { answer = m[1].toUpperCase(); break; }
  }
  // If answer not explicitly labelled, try to find it inline in last few lines
  if (!answer) {
    for (const line of lines.slice(-4)) {
      const m = line.match(ANSWER_RE);
      if (m) { answer = m[1].toUpperCase(); break; }
    }
  }
  // Validate answer key exists in options
  if (answer && !options.find(o => o.key === answer)) answer = "";

  // Explanation: everything after the answer line (or after options if no answer marker)
  let explanation = "";
  const EXPL_RE = /^explanation\s*:/i;
  const explIdx = afterOptions.findIndex(l => EXPL_RE.test(l) || l.toLowerCase().startsWith("because") || l.toLowerCase().startsWith("this is correct"));
  if (explIdx >= 0) {
    explanation = afterOptions
      .slice(explIdx)
      .join(" ")
      .replace(/^explanation\s*:\s*/i, "")
      .trim();
  } else if (afterOptions.length > 0 && answer) {
    // Everything after the answer line is the explanation
    const ansLineIdx = afterOptions.findIndex(l => ANSWER_RE.test(l));
    if (ansLineIdx >= 0) {
      explanation = afterOptions.slice(ansLineIdx + 1).join(" ").trim();
    }
  }

  return { question, options, answer, explanation };
}

// ── Interactive MCQ widget for Quick Check cards ──────────────────────────────
function MCQWidget({ mcq, accent }: { mcq: MCQParsed; accent: string }) {
  const [selected, setSelected] = useState<string | null>(null);
  const submitted = selected !== null;
  const isCorrect = submitted && selected === mcq.answer;

  return (
    <View style={{ marginTop: 8 }}>
      {/* Question */}
      <Text style={mcqStyles.question}>{mcq.question}</Text>

      {/* Option buttons */}
      {mcq.options.map(({ key, text }) => {
        const isSelected = selected === key;
        const isAnswerKey = key === mcq.answer;
        let bg = "#fff";
        let borderColor = "#d1d5db";
        let textColor = "#374151";
        let icon = "";

        if (submitted) {
          if (isAnswerKey) {
            bg = "#dcfce7"; borderColor = "#16a34a"; textColor = "#15803d"; icon = "✓";
          } else if (isSelected && !isAnswerKey) {
            bg = "#fef2f2"; borderColor = "#ef4444"; textColor = "#dc2626"; icon = "✗";
          } else {
            bg = "#f9fafb"; borderColor = "#e5e7eb"; textColor = "#9ca3af";
          }
        } else if (isSelected) {
          bg = accent + "15"; borderColor = accent; textColor = "#111827";
        }

        return (
          <TouchableOpacity
            key={key}
            style={[mcqStyles.optionBtn, { backgroundColor: bg, borderColor }]}
            onPress={() => { if (!submitted) setSelected(key); }}
            disabled={submitted}
            activeOpacity={submitted ? 1 : 0.7}
          >
            <View style={[mcqStyles.optionKeyBox, { backgroundColor: submitted && isAnswerKey ? "#16a34a" : submitted && isSelected ? "#ef4444" : accent + "20" }]}>
              <Text style={[mcqStyles.optionKey, { color: submitted && (isAnswerKey || isSelected) ? "#fff" : accent }]}>{key}</Text>
            </View>
            <Text style={[mcqStyles.optionText, { color: textColor, flex: 1 }]}>{text}</Text>
            {icon ? <Text style={{ fontSize: 16, marginLeft: 6, color: isAnswerKey ? "#16a34a" : "#ef4444" }}>{icon}</Text> : null}
          </TouchableOpacity>
        );
      })}

      {/* Validation feedback */}
      {submitted && (
        <View style={[mcqStyles.feedback, { backgroundColor: isCorrect ? "rgba(34,197,94,.08)" : "rgba(239,68,68,.08)", borderColor: isCorrect ? "rgba(34,197,94,.3)" : "rgba(239,68,68,.3)" }]}>
          <Text style={[mcqStyles.feedbackTitle, { color: isCorrect ? "#15803d" : "#dc2626" }]}>
            {isCorrect ? "✅ Correct! Well done." : `❌ Not quite — the correct answer is ${mcq.answer}.`}
          </Text>
          {mcq.explanation ? (
            <Text style={mcqStyles.feedbackExplanation}>{mcq.explanation}</Text>
          ) : null}
          {!isCorrect && mcq.answer && mcq.options.find(o => o.key === mcq.answer) && (
            <Text style={mcqStyles.feedbackCorrectText}>
              <Text style={{ fontWeight: "700" }}>{mcq.answer}. </Text>
              {mcq.options.find(o => o.key === mcq.answer)?.text}
            </Text>
          )}
        </View>
      )}

      {/* Try again */}
      {submitted && !isCorrect && (
        <TouchableOpacity style={mcqStyles.retryBtn} onPress={() => setSelected(null)}>
          <Text style={mcqStyles.retryText}>🔄 Try Again</Text>
        </TouchableOpacity>
      )}
    </View>
  );
}

const mcqStyles = StyleSheet.create({
  question: { fontSize: 15, fontWeight: "600", color: "#111827", lineHeight: 22, marginBottom: 12 },
  optionBtn: { flexDirection: "row", alignItems: "center", borderWidth: 1.5, borderRadius: 10, padding: 11, marginBottom: 8, gap: 10 },
  optionKeyBox: { width: 28, height: 28, borderRadius: 7, alignItems: "center", justifyContent: "center", flexShrink: 0 },
  optionKey: { fontSize: 13, fontWeight: "800" },
  optionText: { fontSize: 14, fontWeight: "500", lineHeight: 20 },
  feedback: { borderWidth: 1, borderRadius: 10, padding: 12, marginTop: 4 },
  feedbackTitle: { fontSize: 14, fontWeight: "700", marginBottom: 4 },
  feedbackExplanation: { fontSize: 13, color: "#374151", lineHeight: 19, marginTop: 4 },
  feedbackCorrectText: { fontSize: 13, color: "#15803d", lineHeight: 19, marginTop: 6, fontStyle: "italic" },
  retryBtn: { alignSelf: "flex-start", marginTop: 8, paddingHorizontal: 14, paddingVertical: 7, borderRadius: 8, backgroundColor: "rgba(99,102,241,.1)" },
  retryText: { fontSize: 13, fontWeight: "700", color: "#6366f1" },
});

// ── Section Card ──────────────────────────────────────────────────────────────
function SectionCard({ section, index }: { section: Section; index: number }) {
  const type = getSectionType(section.title);
  const card = SECTION_CARDS[type];

  // For Quick Check sections, try to extract and render an interactive MCQ
  const isCheckSection = type === "check";
  const mcq = isCheckSection ? parseMCQ(section.content) : null;

  return (
    <View style={[
      sectionStyles.card,
      { backgroundColor: card.bg, borderColor: card.border, borderLeftColor: card.accent },
    ]}>
      {/* Header row */}
      <View style={sectionStyles.header}>
        <View style={[sectionStyles.iconBox, { backgroundColor: card.accent + "22" }]}>
          <Text style={sectionStyles.iconText}>{card.icon}</Text>
        </View>
        <View style={sectionStyles.headerTextCol}>
          <Text style={[sectionStyles.typeLabel, { color: card.labelColor }]}>{card.label}</Text>
          <Text style={sectionStyles.sectionTitle}>{cleanTitle(section.title)}</Text>
        </View>
      </View>

      {/* Content */}
      <View style={sectionStyles.body}>
        {isCheckSection && mcq ? (
          // Interactive MCQ widget — replaces plain markdown for Quick Check
          <MCQWidget mcq={mcq} accent={card.accent} />
        ) : (
          // MathAwareMarkdown handles $$...$$ display blocks + $...$ inline math
          // converting LaTeX to Unicode (√, ², ₁, π, etc.) before rendering.
          // Fixes: raw LaTeX text showing on mobile (no KaTeX in react-native-markdown-display)
          <MathAwareMarkdown content={section.content.trim()} accent={card.accent} />
        )}
      </View>
    </View>
  );
}

// ── Markdown styles per section accent colour ─────────────────────────────────
function buildMarkdownStyles(accent: string) {
  return {
    body: { color: "#1f2937", fontSize: 15, lineHeight: 24 },
    heading1: { color: "#111827", fontWeight: "800" as const, fontSize: 18, marginTop: 12, marginBottom: 6 },
    heading2: { color: "#111827", fontWeight: "700" as const, fontSize: 16, marginTop: 10, marginBottom: 4 },
    heading3: { color: "#111827", fontWeight: "700" as const, fontSize: 15, marginTop: 8, marginBottom: 4 },
    strong: { fontWeight: "700" as const, color: "#111827" },
    em: { fontStyle: "italic" as const, color: "#374151" },
    bullet_list: { marginVertical: 6 },
    ordered_list: { marginVertical: 6 },
    list_item: { marginBottom: 4 },
    bullet_list_icon: { color: accent, fontWeight: "700" as const, marginRight: 6 },
    ordered_list_icon: { color: accent, fontWeight: "700" as const, marginRight: 6 },
    code_inline: { backgroundColor: "#f3f4f6", color: "#1e40af", borderRadius: 4, fontSize: 13, fontFamily: "monospace" },
    fence: { backgroundColor: "#f8fafc", borderRadius: 8, padding: 12, fontSize: 13, color: "#1e293b", fontFamily: "monospace", marginVertical: 8 },
    code_block: { backgroundColor: "#f8fafc", borderRadius: 8, padding: 12, fontSize: 13, color: "#1e293b", fontFamily: "monospace", marginVertical: 8 },
    blockquote: { backgroundColor: accent + "12", borderLeftWidth: 3, borderLeftColor: accent, paddingLeft: 12, paddingVertical: 4, marginVertical: 6, borderRadius: 4 },
    hr: { backgroundColor: "#e5e7eb", height: 1, marginVertical: 12 },
    table: { borderWidth: 1, borderColor: "#e5e7eb", borderRadius: 6, marginVertical: 8 },
    th: { backgroundColor: accent + "18", fontWeight: "700" as const, padding: 8, fontSize: 13, color: "#111827" },
    td: { padding: 8, fontSize: 13, color: "#374151", borderTopWidth: 1, borderTopColor: "#e5e7eb" },
    paragraph: { marginBottom: 8, lineHeight: 24 },
  };
}

const sectionStyles = StyleSheet.create({
  card: {
    borderRadius: 14,
    borderWidth: 1,
    borderLeftWidth: 4,
    padding: 14,
    marginBottom: 14,
  },
  header: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 10,
    marginBottom: 10,
  },
  iconBox: {
    width: 32,
    height: 32,
    borderRadius: 8,
    alignItems: "center",
    justifyContent: "center",
    flexShrink: 0,
    marginTop: 2,
  },
  iconText: { fontSize: 16 },
  headerTextCol: { flex: 1 },
  typeLabel: {
    fontSize: 10,
    fontWeight: "800",
    textTransform: "uppercase",
    letterSpacing: 0.8,
    marginBottom: 2,
  },
  sectionTitle: {
    fontSize: 15,
    fontWeight: "700",
    color: "#111827",
    lineHeight: 20,
  },
  body: { marginTop: 4 },
});

// ── Main Screen ───────────────────────────────────────────────────────────────
export default function LessonsScreen() {
  const [syllabus, setSyllabus] = useState<SyllabusData | null>(null);
  const [grade, setGrade] = useState("Grade 9");
  const [subject, setSubject] = useState("");
  const [chapter, setChapter] = useState("");
  const [stepIndex, setStepIndex] = useState(0);
  const [lesson, setLesson] = useState("");
  const [generating, setGenerating] = useState(false);
  // Chapter Journey doc — non-null when the whole chapter is available as a
  // typed-block document (zero Generate clicks). Null → classic per-step flow.
  const [chapterDoc, setChapterDoc] = useState<ChapterDocData | null>(null);
  const [chapterDocLoading, setChapterDocLoading] = useState(false);
  const [loadingSyllabus, setLoadingSyllabus] = useState(true);
  const highestStepReached = useRef(0);

  // Enrolled grade/subjects/stream/username + feature access all come from
  // the shared profile context (fetched once at the tabs layout). This is
  // the one consumer that needs the raw `features` map (not just a single
  // derived boolean) since it reads Feature.EXEMPLAR specifically.
  const { profile, features, hasFullAccess } = useUserProfile();
  const studentGrade = profile ? (profile.grade ?? "Grade 9") : null;
  const studentCbseSubjects = profile?.cbseSubjects ?? [];
  const studentStream = profile?.stream ?? "";
  const studentUsername = profile?.username ?? "";

  const steps = LESSON_STEPS_BY_GRADE[grade] ?? LESSON_STEPS_BY_GRADE.default;
  const stepTitle = steps[stepIndex];
  const sections = lesson ? parseSections(lesson) : [];

  // Derived feature access
  const isExemplarChapter = chapter?.includes("Exemplar:");
  const hasExemplarAccess = features?.EXEMPLAR?.allowed ?? false;
  const isExemplarLocked = isExemplarChapter && !hasExemplarAccess;

  // Grade lock: only apply for free/limited users — premium/admin users can select any grade
  const isGradeLocked = studentGrade !== null && !hasFullAccess;

  useEffect(() => {
    // Wait for the shared profile context to resolve (grade/subjects/stream/
    // features), then fetch the syllabus — the syllabus lookup itself is
    // page-local (only this screen needs it), so it isn't part of the
    // shared context, but it depends on knowing the enrolled grade first.
    if (!profile) return;
    const enrolledGrade = studentGrade ?? "Grade 9";
    setGrade(enrolledGrade);

    authFetch("/api/syllabus").catch(() => null).then((syllabusData: any) => {
      if (syllabusData?.syllabus) {
        setSyllabus(syllabusData.syllabus);
        const allSubjects = Object.keys(syllabusData.syllabus?.[enrolledGrade]?.["CBSE"] ?? {});
        // For Grade 11/12: only show enrolled stream subjects
        const isG1112 = enrolledGrade === "Grade 11" || enrolledGrade === "Grade 12";
        const filteredSubjects = isG1112 && studentCbseSubjects.length > 0
          ? allSubjects.filter(s => studentCbseSubjects.some(es => s.toLowerCase().includes(es.toLowerCase()) || es.toLowerCase().includes(s.toLowerCase())))
          : allSubjects;
        const firstSubject = filteredSubjects[0] ?? allSubjects[0] ?? "";
        const firstChapter = syllabusData.syllabus?.[enrolledGrade]?.["CBSE"]?.[firstSubject]?.[0] ?? "";
        setSubject(firstSubject);
        setChapter(firstChapter);
      }
      setLoadingSyllabus(false);
    }).catch(() => {
      Alert.alert("Error", "Could not load lessons data.");
      setLoadingSyllabus(false);
    });
  }, [profile]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Chapter Journey: try the typed-block doc first; fall back silently ─────
  useEffect(() => {
    let cancelled = false;
    setChapterDoc(null);
    if (!grade || !subject || !chapter || isExemplarLocked) return undefined;
    setChapterDocLoading(true);
    const params = new URLSearchParams({ grade, mode: "CBSE", subject, chapter, board: "CBSE" });
    authFetch(`/api/lesson/chapter-doc?${params.toString()}`)
      .then((result: any) => {
        if (cancelled) return;
        setChapterDoc(result?.available && result?.doc ? result.doc : null);
      })
      .catch(() => { if (!cancelled) setChapterDoc(null); })
      .finally(() => { if (!cancelled) setChapterDocLoading(false); });
    return () => { cancelled = true; };
  }, [grade, subject, chapter, isExemplarLocked]);

  // Filter subjects for Grade 11/12 by enrolled cbse_subjects or stream
  const allSyllabusSubjects = Object.keys(syllabus?.[grade]?.["CBSE"] ?? {});
  const isGrade1112 = grade === "Grade 11" || grade === "Grade 12";
  // Build the effective subject list: use cbse_subjects if available, else derive from stream
  const effectiveSubjects = studentCbseSubjects.length > 0
    ? studentCbseSubjects
    : (studentStream && STREAM_SUBJECTS[studentStream] ? STREAM_SUBJECTS[studentStream] : []);
  const subjects = isGrade1112 && effectiveSubjects.length > 0
    ? allSyllabusSubjects.filter(s =>
        effectiveSubjects.some(es =>
          s.toLowerCase() === es.toLowerCase() ||
          s.toLowerCase().includes(es.toLowerCase()) ||
          es.toLowerCase().includes(s.toLowerCase())
        )
      )
    : allSyllabusSubjects;
  const chapters = syllabus?.[grade]?.["CBSE"]?.[subject] ?? [];

  function handleGradeChange(g: string) {
    setGrade(g);
    const firstSubject = Object.keys(syllabus?.[g]?.["CBSE"] ?? {})[0] ?? "";
    setSubject(firstSubject);
    setChapter(syllabus?.[g]?.["CBSE"]?.[firstSubject]?.[0] ?? "");
    setLesson("");
    setStepIndex(0);
    highestStepReached.current = 0;
  }

  function handleSubjectChange(s: string) {
    setSubject(s);
    setChapter(syllabus?.[grade]?.["CBSE"]?.[s]?.[0] ?? "");
    setLesson("");
    setStepIndex(0);
    highestStepReached.current = 0;
  }

  async function generateLesson() {
    if (!grade || !subject || !chapter) return;
    setGenerating(true);
    setLesson("");
    try {
      const result = await authFetch("/api/lesson/generate", {
        method: "POST",
        body: JSON.stringify({
          grade, mode: "CBSE", board: "CBSE",
          subject, chapter, step_title: stepTitle,
          teacher_persona: "",
        }),
      });
      if (result.success) {
        setLesson(result.lesson ?? "");
        highestStepReached.current = Math.max(highestStepReached.current, stepIndex);
        // Non-blocking — a failed save never blocks lesson viewing
        authFetch("/api/progress/save", {
          method: "POST",
          body: JSON.stringify({
            username: studentUsername, grade, mode: "CBSE", subject, chapter,
            current_step_index: stepIndex,
            highest_unlocked_step: highestStepReached.current,
            completed: stepIndex === steps.length - 1,
          }),
        }).catch(() => {});
      } else {
        Alert.alert("Error", result.message ?? "Lesson generation failed.");
      }
    } catch (err: any) {
      Alert.alert("Error", err.message ?? "Could not generate lesson.");
    } finally {
      setGenerating(false);
    }
  }

  if (loadingSyllabus) {
    return <View style={styles.center}><ActivityIndicator color={BRAND_COLOR} size="large" /></View>;
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>

      {/* ── Grade selector — locked to enrolled grade for free tier; all grades for premium ── */}
      <View style={styles.labelRow}>
        <Text style={styles.label}>Grade</Text>
        {isGradeLocked && studentGrade && (
          <Text style={styles.labelLock}>🔒 Locked to {studentGrade}</Text>
        )}
      </View>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.chipRow}>
        {Object.keys(syllabus ?? {})
          .filter(g => {
            const num = parseInt(g.replace("Grade ", ""), 10);
            return !isNaN(num) && num >= 5;
          })
          .map((g) => {
            const locked = isGradeLocked && g !== studentGrade;
            const isActive = grade === g;
            return (
              <TouchableOpacity
                key={g}
                style={[styles.chip, isActive && styles.chipActive, locked && styles.chipLocked]}
                onPress={() => !locked && handleGradeChange(g)}
                disabled={locked}
                activeOpacity={locked ? 1 : 0.7}
              >
                <Text style={[styles.chipText, isActive && styles.chipTextActive, locked && styles.chipTextLocked]}>
                  {g.replace("Grade ", "")}
                </Text>
              </TouchableOpacity>
            );
          })}
      </ScrollView>

      {/* ── Subject selector ── */}
      <Text style={styles.label}>Subject</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.chipRow}>
        {subjects.map((s) => (
          <TouchableOpacity key={s} style={[styles.chip, subject === s && styles.chipActive]} onPress={() => handleSubjectChange(s)}>
            <Text style={[styles.chipText, subject === s && styles.chipTextActive]}>{s}</Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      {/* ── Chapter selector — Exemplar chapters locked for free tier ── */}
      <Text style={styles.label}>Chapter</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.chipRow}>
        {chapters.map((c) => {
          const isExemplar = c.includes("Exemplar:");
          const locked = isExemplar && !hasExemplarAccess;
          const isActive = chapter === c;
          return (
            <TouchableOpacity
              key={c}
              style={[styles.chip, isActive && styles.chipActive, locked && styles.chipLocked]}
              onPress={() => { setChapter(c); setLesson(""); setStepIndex(0); highestStepReached.current = 0; }}
            >
              <Text style={[styles.chipText, isActive && styles.chipTextActive, locked && styles.chipTextLocked]} numberOfLines={1}>
                {locked ? "🔒 " : ""}{c.length > 28 ? c.slice(0, 26) + "…" : c}
              </Text>
            </TouchableOpacity>
          );
        })}
      </ScrollView>

      {/* ── Step navigation — hidden in Chapter Journey mode (no steps) ── */}
      {!chapterDoc && (
      <>
      <View style={styles.stepBar}>
        <TouchableOpacity
          style={[styles.stepNavBtn, stepIndex === 0 && styles.stepNavBtnDisabled]}
          disabled={stepIndex === 0}
          onPress={() => { setStepIndex(i => i - 1); setLesson(""); }}
        >
          <Text style={[styles.stepNavText, stepIndex === 0 && styles.stepNavTextDisabled]}>◀ Prev</Text>
        </TouchableOpacity>

        <View style={styles.stepCenter}>
          <Text style={styles.stepProgress}>{stepIndex + 1} / {steps.length}</Text>
          <Text style={styles.stepName} numberOfLines={1}>{stepTitle}</Text>
        </View>

        <TouchableOpacity
          style={[styles.stepNavBtn, stepIndex === steps.length - 1 && styles.stepNavBtnDisabled]}
          disabled={stepIndex === steps.length - 1}
          onPress={() => { setStepIndex(i => i + 1); setLesson(""); }}
        >
          <Text style={[styles.stepNavText, stepIndex === steps.length - 1 && styles.stepNavTextDisabled]}>Next ▶</Text>
        </TouchableOpacity>
      </View>

      {/* Step progress dots */}
      <View style={styles.stepDots}>
        {steps.map((_, i) => (
          <TouchableOpacity key={i} onPress={() => { setStepIndex(i); setLesson(""); }}>
            <View style={[styles.dot, i === stepIndex && styles.dotActive, i < stepIndex && styles.dotDone]} />
          </TouchableOpacity>
        ))}
      </View>
      </>
      )}

      {/* ── Exemplar upgrade banner (free tier) ── */}
      {isExemplarLocked && (
        <View style={styles.upgradeBanner}>
          <Text style={styles.upgradeBannerIcon}>🔒</Text>
          <View style={{ flex: 1 }}>
            <Text style={styles.upgradeBannerTitle}>Premium Feature</Text>
            <Text style={styles.upgradeBannerText}>Exemplar chapters are available on Premium plans. Upgrade to unlock all Exemplar content.</Text>
          </View>
        </View>
      )}

      {/* ── Chapter Journey: whole chapter, zero Generate clicks ── */}
      {chapterDocLoading && !chapterDoc && (
        <View style={{ marginTop: 28, alignItems: "center" }}>
          <ActivityIndicator color={BRAND_COLOR} size="large" />
          <Text style={{ marginTop: 10, fontSize: 13, color: "#6b7280" }}>Loading chapter…</Text>
        </View>
      )}
      {chapterDoc && (
        <ChapterJourney
          doc={chapterDoc}
          grade={grade}
          renderMarkdown={(content, accent) => (
            <MathAwareMarkdown content={content} accent={accent} />
          )}
        />
      )}

      {/* ── Generate button (classic flow only; disabled for locked Exemplar) ── */}
      {!chapterDoc && !chapterDocLoading && (
      <TouchableOpacity
        style={[styles.generateBtn, (generating || isExemplarLocked) && styles.generateBtnDisabled]}
        onPress={isExemplarLocked ? undefined : generateLesson}
        disabled={generating || isExemplarLocked}
      >
        {generating
          ? <ActivityIndicator color="#fff" />
          : <Text style={styles.generateBtnText}>{isExemplarLocked ? "🔒 Upgrade to Unlock" : "✨ Generate Lesson"}</Text>}
      </TouchableOpacity>
      )}

      {/* ── Lesson generating: Likha Poha AI GIF + dynamic message ── */}
      {generating && (
        <View style={styles.loadingCard}>
          {/* GIF — animates on Android; shows static first frame on iOS */}
          <Image
            source={require("../../assets/likhapohaai.gif")}
            style={styles.loadingGif}
            resizeMode="contain"
          />
          {/* iOS: overlay spinner since GIF doesn't animate in RN managed workflow */}
          {Platform.OS === "ios" && (
            <ActivityIndicator
              color={BRAND_COLOR}
              size="large"
              style={{ position: "absolute", top: 60, alignSelf: "center" }}
            />
          )}
          {/* Dynamic subject + step message */}
          <Text style={styles.loadingMessage}>
            {getLoadingMessage(stepIndex, subject)}
          </Text>
          {/* Lesson info below message */}
          <View style={styles.loadingInfoRow}>
            <View style={styles.loadingBadge}>
              <Text style={styles.loadingBadgeText}>{subject}</Text>
            </View>
            <View style={[styles.loadingBadge, { backgroundColor: "rgba(99,102,241,.12)" }]}>
              <Text style={[styles.loadingBadgeText, { color: BRAND_COLOR }]}>
                Step {stepIndex + 1}/{steps.length}: {stepTitle}
              </Text>
            </View>
          </View>
          <Text style={styles.loadingChapter} numberOfLines={2}>{chapter}</Text>
          <AnimatedDots />
        </View>
      )}

      {!chapterDoc && !generating && sections.length > 0 && (
        <View style={{ marginTop: 20 }}>
          {/* Lesson header */}
          <View style={styles.lessonHeader}>
            <Text style={styles.lessonHeaderSubject}>{subject}</Text>
            <Text style={styles.lessonHeaderChapter} numberOfLines={2}>{chapter}</Text>
            <View style={styles.lessonHeaderBadge}>
              <Text style={styles.lessonHeaderBadgeText}>{stepTitle}</Text>
            </View>
          </View>

          {/* Section cards */}
          {sections.map((section, i) => (
            <SectionCard key={i} section={section} index={i} />
          ))}

          {/* Step navigation footer */}
          <View style={[styles.stepBar, { marginTop: 8, marginBottom: 4 }]}>
            <TouchableOpacity
              style={[styles.stepNavBtn, stepIndex === 0 && styles.stepNavBtnDisabled]}
              disabled={stepIndex === 0}
              onPress={() => { setStepIndex(i => i - 1); setLesson(""); }}
            >
              <Text style={[styles.stepNavText, stepIndex === 0 && styles.stepNavTextDisabled]}>◀ Previous</Text>
            </TouchableOpacity>
            {stepIndex < steps.length - 1 ? (
              <TouchableOpacity
                style={[styles.stepNavBtn, styles.stepNavBtnNext]}
                onPress={() => { setStepIndex(i => i + 1); setLesson(""); }}
              >
                <Text style={styles.stepNavTextNext}>Next Step ▶</Text>
              </TouchableOpacity>
            ) : (
              <View style={[styles.stepNavBtn, { backgroundColor: "rgba(34,197,94,.1)" }]}>
                <Text style={{ color: "#15803d", fontWeight: "700", fontSize: 13 }}>✅ Complete</Text>
              </View>
            )}
          </View>
        </View>
      )}

      {!chapterDoc && !chapterDocLoading && !generating && !lesson && (
        <View style={styles.emptyState}>
          <View style={styles.emptyIconBox}>
            <Feather name="book-open" size={40} color={BRAND_COLOR} />
          </View>
          <Text style={styles.emptyTitle}>Ready to learn?</Text>
          <Text style={styles.emptySubtitle}>Select a grade, subject, and chapter, then tap Generate Lesson.</Text>
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f8fafc" },
  content: { padding: 16, paddingBottom: 80 },
  center: { flex: 1, justifyContent: "center", alignItems: "center" },
  labelRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginTop: 16, marginBottom: 8 },
  label: { fontSize: 11, fontWeight: "700", color: "#6b7280", textTransform: "uppercase", letterSpacing: 0.6 },
  labelLock: { fontSize: 10, fontWeight: "600", color: "#6366f1" },
  chipRow: { flexDirection: "row", marginBottom: 4 },
  chip: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 99, borderWidth: 1.5, borderColor: "#d1d5db", backgroundColor: "#fff", marginRight: 8 },
  chipActive: { borderColor: BRAND_COLOR, backgroundColor: BRAND_COLOR },
  chipLocked: { borderColor: "#e5e7eb", backgroundColor: "#f9fafb", opacity: 0.55 },
  chipText: { fontSize: 13, fontWeight: "600", color: "#374151" },
  chipTextActive: { color: "#fff" },
  chipTextLocked: { color: "#9ca3af" },
  // Upgrade banner
  upgradeBanner: { flexDirection: "row", alignItems: "flex-start", gap: 10, backgroundColor: "rgba(99,102,241,.07)", borderRadius: 12, padding: 14, marginTop: 16, borderWidth: 1, borderColor: "rgba(99,102,241,.2)" },
  upgradeBannerIcon: { fontSize: 20, marginTop: 1 },
  upgradeBannerTitle: { fontSize: 13, fontWeight: "800", color: "#6366f1", marginBottom: 3 },
  upgradeBannerText: { fontSize: 12, color: "#374151", lineHeight: 18 },
  // Step bar
  stepBar: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginTop: 18, backgroundColor: "#fff", borderRadius: 14, padding: 12, borderWidth: 1, borderColor: "#e5e7eb" },
  stepNavBtn: { paddingHorizontal: 12, paddingVertical: 8, borderRadius: 8, backgroundColor: "rgba(99,102,241,.08)" },
  stepNavBtnDisabled: { backgroundColor: "#f3f4f6" },
  stepNavBtnNext: { backgroundColor: BRAND_COLOR },
  stepNavText: { fontSize: 13, fontWeight: "700", color: BRAND_COLOR },
  stepNavTextDisabled: { color: "#9ca3af" },
  stepNavTextNext: { fontSize: 13, fontWeight: "700", color: "#fff" },
  stepCenter: { flex: 1, alignItems: "center", paddingHorizontal: 8 },
  stepProgress: { fontSize: 10, fontWeight: "700", color: "#9ca3af", textTransform: "uppercase", letterSpacing: 0.5 },
  stepName: { fontSize: 13, fontWeight: "700", color: "#111827", textAlign: "center", marginTop: 2 },
  // Step dots
  stepDots: { flexDirection: "row", justifyContent: "center", gap: 6, marginTop: 10, marginBottom: 4 },
  dot: { width: 8, height: 8, borderRadius: 4, backgroundColor: "#d1d5db" },
  dotActive: { backgroundColor: BRAND_COLOR, width: 20 },
  dotDone: { backgroundColor: "#22c55e" },
  // Generate button
  generateBtn: { backgroundColor: BRAND_COLOR, borderRadius: 12, padding: 15, alignItems: "center", marginTop: 18 },
  generateBtnDisabled: { opacity: 0.6 },
  generateBtnText: { color: "#fff", fontWeight: "700", fontSize: 16 },
  // Loading GIF card
  loadingCard: {
    marginTop: 28,
    alignItems: "center",
    backgroundColor: "#fff",
    borderRadius: 20,
    borderWidth: 1,
    borderColor: "#e5e7eb",
    padding: 24,
    paddingTop: 20,
    shadowColor: "#6366f1",
    shadowOpacity: 0.08,
    shadowRadius: 20,
    shadowOffset: { width: 0, height: 4 },
    elevation: 4,
    overflow: "visible",
  },
  loadingGif: {
    width: 160,
    height: 160,
    marginBottom: 16,
  },
  loadingMessage: {
    fontSize: 14,
    fontWeight: "600",
    color: "#374151",
    textAlign: "center",
    lineHeight: 21,
    paddingHorizontal: 8,
    marginBottom: 14,
  },
  loadingInfoRow: {
    flexDirection: "row",
    gap: 8,
    flexWrap: "wrap",
    justifyContent: "center",
    marginBottom: 8,
  },
  loadingBadge: {
    backgroundColor: "rgba(34,197,94,.1)",
    borderRadius: 99,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  loadingBadgeText: {
    fontSize: 11,
    fontWeight: "700",
    color: "#15803d",
    textTransform: "uppercase",
    letterSpacing: 0.4,
  },
  loadingChapter: {
    fontSize: 12,
    color: "#9ca3af",
    textAlign: "center",
    paddingHorizontal: 20,
  },
  // Lesson header
  lessonHeader: { backgroundColor: "#fff", borderRadius: 14, padding: 14, marginBottom: 16, borderWidth: 1, borderColor: "#e5e7eb" },
  lessonHeaderSubject: { fontSize: 11, fontWeight: "700", color: BRAND_COLOR, textTransform: "uppercase", letterSpacing: 0.6, marginBottom: 4 },
  lessonHeaderChapter: { fontSize: 17, fontWeight: "800", color: "#111827", lineHeight: 23, marginBottom: 10 },
  lessonHeaderBadge: { alignSelf: "flex-start", backgroundColor: "rgba(99,102,241,.1)", borderRadius: 99, paddingHorizontal: 10, paddingVertical: 4 },
  lessonHeaderBadgeText: { fontSize: 12, fontWeight: "700", color: BRAND_COLOR },
  // Empty state
  emptyState: { alignItems: "center", paddingTop: 48, paddingBottom: 32 },
  emptyIconBox: { width: 80, height: 80, borderRadius: 20, backgroundColor: "rgba(99,102,241,.08)", alignItems: "center", justifyContent: "center", marginBottom: 16 },
  emptyTitle: { fontSize: 18, fontWeight: "800", color: "#111827", marginBottom: 8 },
  emptySubtitle: { fontSize: 14, color: "#6b7280", textAlign: "center", lineHeight: 21, paddingHorizontal: 20 },
});
