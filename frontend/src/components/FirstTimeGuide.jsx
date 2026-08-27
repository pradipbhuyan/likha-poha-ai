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
      title: "Lessons — Chapter Journey",
      text: "Go to Lessons → pick Grade, Subject, and Chapter. Grade 11 and 12 students see subjects from their chosen stream — Science (PCM), Science (PCB), Science (PCMB), Commerce, or Humanities. Grade 5-8 gets a card-by-card feed with XP; Grade 9-12 gets an exam-style outline with worked examples.",
      icon: BookOpen,
    },
    {
      title: "Read & Answer Quick Checks",
      text: "Scroll through the chapter at your own pace — jump to any section using the milestone list. Answer the inline Quick Check questions and worked examples as you go; your progress saves automatically.",
      icon: Sparkles,
    },
    {
      title: "Ask About This Chapter",
      text: "Click Ask about this chapter to reveal ready-made answers to common questions for what you're reading — instant. For anything else, use the Ask Doubt page.",
      icon: HelpCircle,
    },
    {
      title: "Mock Tests",
      text: "Go to Mock Test → pick Subject and Chapter → Generate 10 Questions. After submitting, review the detailed explanation for each answer. Wrong answers are saved to your weak areas.",
      icon: ClipboardList,
    },
    {
      title: "Ask Doubt",
      text: "Use the Ask Doubt page for any question not tied to a specific lesson step. The AI answers instantly using NCERT-grounded knowledge.",
      icon: HelpCircle,
    },
    {
      title: "Formulas & Concepts",
      text: "Go to Formulas & Concepts → pick your Grade and Subject → see all key formulas, definitions, and concepts chapter-wise. Free preview included. Full access with paid plan.",
      icon: ClipboardList,
    },
    {
      title: "Exemplar Research",
      text: "Go to Exemplar Research → pick a hard NCERT Exemplar topic → get an instant AI explanation + practice link. Great for advanced prep and HOTS questions.",
      icon: Sparkles,
    },
    {
      title: "Exam Prep Center (Grade 11 & 12)",
      text: "Preparing for a competitive exam? Go to Exam Prep Center → choose JEE Main, NEET UG, CUET UG, SAT, IELTS, or TOEFL iBT → practice questions, simulated tests, and AI explanations tailored to that exam.",
      icon: Compass,
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
      title: "Add a Child",
      text: "Click Add Child → enter their name, pick their Grade (5-12), and set a password. Grade 11 and 12 also need a stream — Science (PCM), Science (PCB), Science (PCMB), Commerce, or Arts/Humanities. New children start on Free Tier with limited access until you upgrade.",
      icon: Compass,
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
      text: "Go to Subscription → compare Premium and Family Premium (up to 2 children). Grade 11 & 12 students can also choose the Exam Prep Center annual plan, which includes full Premium-equivalent access plus JEE, NEET, CUET, SAT, IELTS & TOEFL prep. Click Choose Plan to check out via Razorpay (UPI supported). Plans run for a fixed term and must be renewed manually before they expire — they do not auto-renew.",
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
      title: "Add or Invite a Student",
      text: "Click Add Student to create an account directly, or send an email invitation from the Invitations tab. Grade 5-12 only.",
      icon: ClipboardList,
    },
    {
      title: "Lessons",
      text: "Browse the same Chapter Journey lessons your students see for Grade 5-12 (Grade 11 & 12 by stream) — useful for lesson planning and checking content before teaching.",
      icon: BookOpen,
    },
    {
      title: "Create Test Paper",
      text: "Generate MCQ and subjective test papers for Grade 5-10 and any chapter in seconds. Download the question paper and answer key for printing.",
      icon: ClipboardList,
    },
    {
      title: "Create Lesson Plans",
      text: "Generate a detailed, CBSE-aligned lesson plan for any grade (5-12), subject, and chapter — download it as a PDF before class.",
      icon: ClipboardList,
    },
    {
      title: "Listen to Lecture",
      text: "Hear a model spoken run-through of any chapter's lesson plan, in a teacher's voice, to rehearse your delivery before class.",
      icon: Sparkles,
    },
    {
      title: "Student Analytics",
      text: "See each student's score trend, subject performance (best/average/latest bars), and recent test activity. Sort by weakest first to spot students who need help.",
      icon: BarChart3,
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

function FirstTimeGuide({ user }) {
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

  // Guide is always minimised by default — opens only on user click.
  // auto_open admin setting is intentionally ignored here.

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
              <button
                disabled={stepIndex === 0}
                onClick={() => setStepIndex((prev) => prev - 1)}
                className="primary-btn"
                style={{
                  background: "#475569",
                  opacity: stepIndex === 0 ? 0.35 : 1,
                }}
              >
                Back
              </button>
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
