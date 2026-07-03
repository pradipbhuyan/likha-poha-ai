import { useEffect, useMemo, useState } from "react";
import {
  BarChart3,
  BookOpen,
  ClipboardList,
  Compass,
  HelpCircle,
  LineChart,
  Sparkles,
  Users,
  X,
} from "lucide-react";

import { getOnboardingGuideSettings } from "../api/onboardingGuide";

const DEFAULT_SETTINGS = {
  enabled: true,
  active_theme: "quest",
  rotation_enabled: false,
  rotation_days: 14,
  student_theme: "quest",
  parent_theme: "clean",
  teacher_theme: "forest",
  show_once_per_theme: true,
  auto_open: true,
  message:
    "A friendly first-time guide helps new users understand the main pages without feeling lost.",
};

const THEME_ORDER = ["clean", "quest", "space", "forest"];

const THEME_META = {
  clean: {
    label: "Clean Coach",
    badge: "Quick tour",
    mascot: "🧭",
    line: "A calm, simple guide for families who like a neat path.",
  },
  quest: {
    label: "Quest Mode",
    badge: "Level 1",
    mascot: "🏅",
    line: "A mission-style guide that makes the first visit feel like a learning quest.",
  },
  space: {
    label: "Space Mission",
    badge: "Launch pad",
    mascot: "🚀",
    line: "A playful launch sequence for exploring lessons, practice, and progress.",
  },
  forest: {
    label: "Forest Trail",
    badge: "Trail map",
    mascot: "🌿",
    line: "A softer guided trail for teachers and parents who want a steady walkthrough.",
  },
};

const ROLE_STEPS = {
  student: [
    {
      title: "Start at Dashboard",
      text: "See your learning streak, weak areas, and what to study next. The dashboard shows you exactly where to begin today.",
      icon: Compass,
    },
    {
      title: "Pick a Chapter in Lessons",
      text: "Go to Lessons → choose your Grade, Subject, and Chapter. Always start from Step 1 of the chapter. Each chapter has 5 lesson steps.",
      icon: BookOpen,
    },
    {
      title: "Generate & Read the Lesson",
      text: "Click ✨ Generate Lesson. Read carefully — each step teaches one focused concept. Use 🔊 Listen to hear it aloud.",
      icon: Sparkles,
    },
    {
      title: "Practice & Mark Complete",
      text: "After reading, click 🎲 Generate 2 Practice Questions. Answer them, then click ✅ Mark Step Complete to unlock the next step.",
      icon: ClipboardList,
    },
    {
      title: "Ask Doubts Anytime",
      text: "Stuck on something? Use Ask Doubt or the 💬 Ask a follow-up box inside the lesson. Pre-answered questions are shown as chips.",
      icon: HelpCircle,
    },
    {
      title: "Take a Mock Test",
      text: "Once you finish all steps of a chapter, go to Mock Test to test yourself with MCQs. Review explanations to learn from mistakes.",
      icon: ClipboardList,
    },
    {
      title: "Track Your Progress",
      text: "Check Analytics to see which subjects are improving. The Dashboard shows weak areas to revisit before your exam.",
      icon: BarChart3,
    },
  ],
  parent: [
    {
      title: "Family Dashboard",
      text: "Review your children, subscriptions, and linked parent accounts in one place.",
      icon: Users,
    },
    {
      title: "Progress Snapshot",
      text: "See lesson progress, mock-test results, and AI usage patterns.",
      icon: LineChart,
    },
    {
      title: "Subscription Help",
      text: "Compare available plans and contact support if you need activation help.",
      icon: ClipboardList,
    },
  ],
  teacher: [
    {
      title: "Teacher Dashboard",
      text: "View assigned students, subjects, class progress, and add teacher notes from your workspace.",
      icon: Users,
    },
    {
      title: "AI Lessons & Ask Doubt",
      text: "Browse NCERT step-wise lessons for any grade (5–10) and answer student doubts using the AI tutor.",
      icon: BookOpen,
    },
    {
      title: "Create Test Paper",
      text: "Generate MCQ and subjective test papers for any grade and chapter in seconds. Download the question paper and answer key for printing.",
      icon: ClipboardList,
    },
    {
      title: "Student Analytics",
      text: "See each student's score trend, subject performance (best/average/latest bars), and recent test activity. Sort by weakest first to spot students who need help.",
      icon: BarChart3,
    },
    {
      title: "Learn More Resources",
      text: "Access NCERT reference videos, exemplar materials, and grammar guides for any subject you teach.",
      icon: Sparkles,
    },
    {
      title: "Spot Weak Areas",
      text: "The class overview chart shows the average score per subject across all your students — identify which topic needs the most revision.",
      icon: LineChart,
    },
  ],
};

function storageKey(user, theme) {
  /** Keep guide completion scoped to user, role, and theme. */
  return `likha_poha_guide_seen_${user?.role || "guest"}_${
    user?.username || "unknown"
  }_${theme}`;
}

function getRotatedTheme(settings) {
  /** Rotate available themes in stable two-week windows when admin enables it. */
  if (!settings.rotation_enabled) return settings.active_theme || "quest";

  const rotationDays = Number(settings.rotation_days || 14);
  const windowMs = Math.max(7, rotationDays) * 24 * 60 * 60 * 1000;
  const index = Math.floor(Date.now() / windowMs) % THEME_ORDER.length;

  return THEME_ORDER[index];
}

function pickTheme(settings, role) {
  /** Prefer role-specific themes, then active or rotated global theme. */
  const roleTheme = settings[`${role}_theme`];
  return roleTheme || getRotatedTheme(settings);
}

function FirstTimeGuide({ user, activePage }) {
  /** Role-aware first-time guide with admin-configurable visual themes. */
  const role = user?.role;
  const [settings, setSettings] = useState(DEFAULT_SETTINGS);
  const [open, setOpen] = useState(false);
  const [stepIndex, setStepIndex] = useState(0);
  const steps = ROLE_STEPS[role] || [];

  useEffect(() => {
    let cancelled = false;

    async function loadSettings() {
      try {
        const response = await getOnboardingGuideSettings();
        if (!cancelled) {
          setSettings({
            ...DEFAULT_SETTINGS,
            ...(response.settings || {}),
          });
        }
      } catch {
        if (!cancelled) {
          setSettings(DEFAULT_SETTINGS);
        }
      }
    }

    loadSettings();

    return () => {
      cancelled = true;
    };
  }, []);

  const theme = useMemo(() => pickTheme(settings, role), [settings, role]);
  const themeMeta = THEME_META[theme] || THEME_META.quest;
  const currentStep = steps[stepIndex] || steps[0];
  const seenKey = storageKey(user, theme);

  useEffect(() => {
    if (!settings.enabled || !settings.auto_open || !steps.length) return;
    if (settings.show_once_per_theme && localStorage.getItem(seenKey) === "true") {
      return;
    }

    setOpen(true);
  }, [
    activePage,
    seenKey,
    settings.auto_open,
    settings.enabled,
    settings.show_once_per_theme,
    steps.length,
  ]);

  if (!settings.enabled || !steps.length) {
    return null;
  }

  function closeGuide(markSeen = true) {
    /** Close the guide and optionally mark the current theme as seen. */
    if (markSeen) {
      localStorage.setItem(seenKey, "true");
    }
    setOpen(false);
    setStepIndex(0);
  }

  function goNext() {
    /** Advance the walkthrough or finish when the last guide card is reached. */
    if (stepIndex >= steps.length - 1) {
      closeGuide(true);
      return;
    }
    setStepIndex((prev) => prev + 1);
  }

  const StepIcon = currentStep?.icon || Sparkles;

  return (
    <>
      <button
        className={`first-guide-launcher first-guide-launcher-${theme}`}
        onClick={() => setOpen(true)}
      >
        <Sparkles size={17} strokeWidth={2.5} />
        Likha Poha AI Guide
      </button>

      {open && (
        <div className="first-guide-layer" role="dialog" aria-modal="false">
          <section className={`first-guide-panel first-guide-${theme}`}>
            <button
              className="first-guide-close"
              onClick={() => closeGuide(false)}
              aria-label="Close guide"
            >
              <X size={18} strokeWidth={2.5} />
            </button>

            <div className="first-guide-hero">
              <span className="first-guide-mascot">{themeMeta.mascot}</span>
              <div>
                <p>{themeMeta.badge}</p>
                <h3>{themeMeta.label}</h3>
                <small>{themeMeta.line}</small>
              </div>
            </div>

            <div className="first-guide-progress">
              {steps.map((step, index) => (
                <button
                  key={step.title}
                  className={index === stepIndex ? "active" : ""}
                  onClick={() => setStepIndex(index)}
                  aria-label={`Guide step ${index + 1}`}
                />
              ))}
            </div>

            <article className="first-guide-step-card">
              <span className="first-guide-step-icon">
                <StepIcon size={23} strokeWidth={2.4} />
              </span>
              <div>
                <p>Step {stepIndex + 1} of {steps.length}</p>
                <h4>{currentStep.title}</h4>
                <span>{currentStep.text}</span>
              </div>
            </article>

            <p className="first-guide-message">{settings.message}</p>

            <div className="first-guide-actions">
              <button onClick={() => closeGuide(true)}>Skip</button>
              <button className="primary-btn" onClick={goNext}>
                {stepIndex >= steps.length - 1 ? "Finish" : "Next"}
              </button>
            </div>
          </section>
        </div>
      )}
    </>
  );
}

export default FirstTimeGuide;
