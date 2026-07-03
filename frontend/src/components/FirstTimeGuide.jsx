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
  auto_open: false, // Always start minimised — user opens manually
  message:
    "Click any step to jump to it. Click Finish when you're ready to explore on your own.",
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
      title: "Dashboard — Your Home Base",
      text: "Your Dashboard shows today's focus areas, weak topics flagged by the AI, and your overall progress. Check it every day before starting a lesson.",
      icon: Compass,
    },
    {
      title: "Lessons — 5-Step Learning",
      text: "Go to Lessons → pick Grade, Subject, and Chapter. Each chapter has 5 steps: Concept Introduction → Core Explanation → Worked Examples → Exam-Style Problems → Revision & Recap. Grade 10 has a bonus Exam Preparation step.",
      icon: BookOpen,
    },
    {
      title: "Generate & Read Your Lesson",
      text: "Click Generate Lesson. The AI creates a personalised, NCERT-grounded lesson just for you. Read each step carefully. Click Listen to hear it aloud while you follow along.",
      icon: Sparkles,
    },
    {
      title: "Ask Doubts Inside Lessons",
      text: "See chips (quick questions) at the bottom of each lesson — click any chip for an instant pre-answered answer at zero AI cost. Or type your own question in the Ask a follow-up box.",
      icon: HelpCircle,
    },
    {
      title: "Practice Questions",
      text: "After reading, click Generate 2 Practice Questions. For MCQs, click Check Answer for instant feedback. For descriptive, click Get AI Feedback. This builds exam memory.",
      icon: ClipboardList,
    },
    {
      title: "Move to the Next Step",
      text: "Use the Previous / Next buttons at the top and bottom of the lesson to move between the 5 steps. All steps are freely navigable — no lock.",
      icon: Compass,
    },
    {
      title: "Mock Tests",
      text: "Go to Mock Test → pick Subject and Chapter → Generate 10 Questions. After submitting, review the detailed explanation for each answer. Wrong answers are saved to your weak areas.",
      icon: ClipboardList,
    },
    {
      title: "Ask Doubt (Standalone)",
      text: "Use the Ask Doubt page for any question not tied to a specific lesson step. The AI answers instantly using NCERT-grounded knowledge.",
      icon: HelpCircle,
    },
    {
      title: "Formula Sheet",
      text: "Go to Formula Sheet → pick your Grade and Subject → see all key formulas chapter-wise. Free preview included. Full access with paid plan.",
      icon: ClipboardList,
    },
    {
      title: "Exemplar Research",
      text: "Go to Exemplar Research → pick a hard NCERT Exemplar topic → get an instant AI explanation + practice link. Great for Olympiad prep and HOTS questions.",
      icon: Sparkles,
    },
    {
      title: "Analytics — Track Progress",
      text: "Analytics shows your lesson completion, mock test scores by chapter, weak areas, and AI usage. Review it weekly to see where you're improving.",
      icon: BarChart3,
    },
  ],
  parent: [
    {
      title: "Parent Dashboard — Overview",
      text: "Your Parent Dashboard shows all linked children, their subscription status, and recent learning activity. Switch between children using the selector at the top.",
      icon: Users,
    },
    {
      title: "Child Progress & Activity",
      text: "See each child's lesson completion rate, mock test scores, weak subjects, and daily AI usage. The progress section shows which chapters they've finished and which need attention.",
      icon: LineChart,
    },
    {
      title: "Notifications",
      text: "Get notified when your child completes a chapter, scores below average on a mock test, or has not logged in for several days. Notifications appear in your dashboard.",
      icon: Compass,
    },
    {
      title: "Subscription Plans",
      text: "Go to Subscription → compare Standard and Premium plans. Click Choose Plan to start checkout via Razorpay (UPI supported). Plans auto-renew monthly unless cancelled.",
      icon: ClipboardList,
    },
    {
      title: "Contact Support",
      text: "Need help activating a plan or linking a child? Use the contact details shown on the Subscription page — email, WhatsApp, and phone. Support replies within 24 hours.",
      icon: HelpCircle,
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
      text: "Browse NCERT step-wise lessons for any grade (5-10) and answer student doubts using the AI tutor.",
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
                <StepIcon size={20} strokeWidth={2.4} />
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
