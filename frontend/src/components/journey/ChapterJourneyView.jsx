import { useEffect, useMemo, useRef, useState } from "react";
import { MessageCircle } from "lucide-react";

import { ensureLessonKbChips } from "../../api/lesson";
import { saveChapterProgress } from "../../api/progress";
import { logStudentActivity } from "../../api/profile";
import { useFeedbackPrompt } from "../../context/FeedbackPromptContext";
import JourneyRenderer from "./JourneyRenderer";
import StudyRenderer from "./StudyRenderer";
import LessonMarkdown from "./LessonMarkdown";

const MAX_DOUBT_CHIPS = 6;

function DoubtChip({ chip, isOpen, onToggle }) {
  /** Pre-warmed LKB question chip — click to reveal the stored answer. No AI call. */
  return (
    <div style={{
      border: "1.5px solid rgba(124,92,214,.35)",
      background: "rgba(124,92,214,.08)",
      borderRadius: 12,
      padding: "10px 14px",
      marginBottom: 8,
    }}>
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={isOpen}
        style={{
          display: "flex", width: "100%", justifyContent: "space-between",
          alignItems: "center", gap: 10, font: "inherit", fontSize: ".88rem",
          fontWeight: 700, color: "var(--text, #111827)",
          background: "none", border: "none", padding: 0, cursor: "pointer",
          textAlign: "left",
        }}
      >
        <span>{chip.question}</span>
        <span style={{ fontSize: ".7rem", fontWeight: 800, color: "#7c5cd6", flexShrink: 0 }}>
          {isOpen ? "HIDE" : "REVEAL"}
        </span>
      </button>
      {isOpen && (
        <div style={{ marginTop: 8, fontSize: ".86rem", lineHeight: 1.6 }}>
          <LessonMarkdown>{chip.answer}</LessonMarkdown>
        </div>
      )}
    </div>
  );
}

/**
 * ChapterJourneyView — container for the Chapter Journey pilot (Phase 2).
 *
 * Receives a validated chapter doc (typed blocks) and renders it with the
 * grade-band renderer: Journey (Grades 5-8) or Study (Grades 9-12).
 *
 * Progress (quick-check answers + XP) persists in localStorage — a few bytes,
 * no lesson content is copied per student. The "Ask about this chapter" panel
 * serves pre-warmed LKB question/answer chips (click to reveal) — no free-text
 * AI call from this view; the LKB endpoint only hits an LLM on a rare first-ever
 * cache miss for a given lesson step, and every subsequent view is instant.
 */

const JUNIOR_GRADES = new Set(["Grade 5", "Grade 6", "Grade 7", "Grade 8"]);

function useMediaQuery(query) {
  /** Safe matchMedia hook — returns false where matchMedia is unavailable (jsdom). */
  const [matches, setMatches] = useState(
    () => typeof window !== "undefined"
      && typeof window.matchMedia === "function"
      && window.matchMedia(query).matches
  );
  useEffect(() => {
    if (typeof window.matchMedia !== "function") return undefined;
    const mql = window.matchMedia(query);
    const onChange = (event) => setMatches(event.matches);
    setMatches(mql.matches);
    mql.addEventListener?.("change", onChange);
    return () => mql.removeEventListener?.("change", onChange);
  }, [query]);
  return matches;
}

function progressKey({ grade, subject, chapter }) {
  return `lp_journey:${grade}|${subject}|${chapter}`;
}

function loadProgress(key) {
  try {
    const raw = window.localStorage.getItem(key);
    return raw ? JSON.parse(raw) : { quizAnswers: {} };
  } catch {
    return { quizAnswers: {} };
  }
}

function ChapterJourneyView({ doc, user, grade, mode, subject, chapter }) {
  const storageKey = progressKey({ grade, subject, chapter });
  const [progress, setProgress] = useState(() => loadProgress(storageKey));
  const [activeMilestone, setActiveMilestone] = useState(0);
  const hasSavedCompletionRef = useRef(false);

  const [lkbChipsByStep, setLkbChipsByStep] = useState({});
  const [lkbLoadingStep, setLkbLoadingStep] = useState(null);
  const [openChipIds, setOpenChipIds] = useState(() => new Set());
  const requestedStepsRef = useRef(new Set());

  const { triggerFeedbackPrompt } = useFeedbackPrompt();
  const isJunior = JUNIOR_GRADES.has(grade);
  // Wide screens get a sticky milestone rail (Journey) / outline (Study), so
  // the compact progress strip is only needed on narrow viewports.
  const isWide = useMediaQuery("(min-width: 1024px)");

  // Reload saved progress when the chapter changes
  useEffect(() => {
    setProgress(loadProgress(storageKey));
    setActiveMilestone(0);
    setLkbChipsByStep({});
    setOpenChipIds(new Set());
    requestedStepsRef.current = new Set();
    hasSavedCompletionRef.current = false;
  }, [storageKey]);

  // Fetch pre-warmed LKB question chips for the milestone currently being
  // read (zero LLM cost after the first pre-warm) — one request per step
  // title, cached for the lifetime of this chapter view.
  useEffect(() => {
    const milestone = doc.milestones[activeMilestone] || doc.milestones[0];
    const stepTitle = milestone?.title || "Chapter";
    if (requestedStepsRef.current.has(stepTitle)) return;
    requestedStepsRef.current.add(stepTitle);
    setLkbLoadingStep(stepTitle);
    ensureLessonKbChips({ grade, subject, chapter, step_title: stepTitle })
      .then((result) => {
        setLkbChipsByStep((prev) => ({ ...prev, [stepTitle]: result?.lkb_chips || [] }));
      })
      .catch(() => {
        setLkbChipsByStep((prev) => ({ ...prev, [stepTitle]: [] }));
      })
      .finally(() => {
        setLkbLoadingStep((prev) => (prev === stepTitle ? null : prev));
      });
  }, [activeMilestone, doc, grade, subject, chapter]);

  // Scroll-spy: highlight the milestone currently in view (Study outline)
  useEffect(() => {
    const prefix = isJunior ? "journey-milestone-" : "study-milestone-";
    const sections = doc.milestones
      .map((_, mi) => document.getElementById(`${prefix}${mi}`))
      .filter(Boolean);
    if (sections.length === 0 || typeof IntersectionObserver === "undefined") return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const index = Number(entry.target.id.replace(prefix, ""));
            if (!Number.isNaN(index)) setActiveMilestone(index);
          }
        });
      },
      { rootMargin: "-15% 0px -70% 0px" }
    );
    sections.forEach((section) => observer.observe(section));
    return () => observer.disconnect();
  }, [doc, isJunior]);

  // Real completion: this view has no step-by-step gating — the student
  // reads one continuous scroll. Reaching the finish card at the bottom
  // (same card already shown to every student) is the honest signal that
  // they've been through the whole chapter, so that's what saves progress.
  // No click required, no visual change to the card itself.
  useEffect(() => {
    const cardId = isJunior ? "journey-finish-card" : "study-finish-card";
    const card = document.getElementById(cardId);
    if (!card || typeof IntersectionObserver === "undefined") return undefined;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting && !hasSavedCompletionRef.current) {
            hasSavedCompletionRef.current = true;
            const lastIndex = Math.max(0, doc.milestones.length - 1);
            saveChapterProgress({
              username: user.username,
              grade,
              mode,
              subject,
              chapter,
              current_step_index: lastIndex,
              highest_unlocked_step: lastIndex,
              completed: true,
              last_lesson: "",
              step_lessons: {},
            }).catch(() => {
              // Non-critical — the student already sees the finish card;
              // allow a retry on next scroll-into-view if this failed.
              hasSavedCompletionRef.current = false;
            });
            // Same gamified-profile activity log Mock Test and Quiz already
            // use — this is what actually drives the real study streak,
            // lessons_completed count, and XP in student_profiles. Lesson
            // completion never called this before, so the streak could only
            // move from taking a mock test or quiz, never from studying.
            logStudentActivity({
              username: user.username,
              activity_type: "lesson_completed",
            }).catch(() => { /* non-critical */ });
            triggerFeedbackPrompt("lesson_completed", { grade, subject, chapter });
          }
        });
      },
      { threshold: 0.4 }
    );
    observer.observe(card);
    return () => observer.disconnect();
  }, [doc, isJunior, user.username, grade, mode, subject, chapter, triggerFeedbackPrompt]);

  function handleQuickCheckAnswer(blockKey, answerIndex, _isCorrect) {
    setProgress((prev) => {
      const next = {
        ...prev,
        quizAnswers: { ...prev.quizAnswers, [blockKey]: answerIndex },
      };
      try {
        window.localStorage.setItem(storageKey, JSON.stringify(next));
      } catch {
        // Progress persistence is best-effort
      }
      return next;
    });
  }

  function toggleDoubtChip(chipKey) {
    setOpenChipIds((prev) => {
      const next = new Set(prev);
      if (next.has(chipKey)) next.delete(chipKey);
      else next.add(chipKey);
      return next;
    });
  }

  const totalQuickChecks = useMemo(
    () =>
      doc.milestones.reduce(
        (count, milestone) =>
          count + milestone.blocks.filter((b) => b.type === "quickcheck").length,
        0
      ),
    [doc]
  );
  const answeredQuickChecks = Object.keys(progress.quizAnswers || {}).length;

  const currentStepTitle = doc.milestones[activeMilestone]?.title || doc.milestones[0]?.title || "Chapter";
  const currentStepChips = (lkbChipsByStep[currentStepTitle] || []).slice(0, MAX_DOUBT_CHIPS);
  const isChipsLoading = lkbLoadingStep === currentStepTitle;

  return (
    <div className="chapter-journey" data-testid="chapter-journey">
      {/* Progress strip — narrow viewports only; sticky so it stays useful
          while scrolling. Wide screens use the milestone rail/outline instead. */}
      {!isWide && (
      <div style={{
        display: "flex", alignItems: "center", gap: 12,
        padding: "8px 14px", flexWrap: "wrap", marginBottom: 14,
        position: "sticky", top: 8, zIndex: 40,
        background: "var(--panel, #fff)",
        border: "1px solid var(--border, #e5e7eb)",
        borderRadius: 10,
        boxShadow: "0 2px 10px rgba(0,0,0,.06)",
      }}>
        <span style={{ fontSize: ".82rem", fontWeight: 600, color: "var(--muted, #6b7280)" }}>
          Milestone {Math.min(activeMilestone + 1, doc.milestones.length)} of {doc.milestones.length}
          {" · "}
          <strong style={{ color: "var(--text, #111827)" }}>
            {doc.milestones[activeMilestone]?.title || doc.milestones[0].title}
          </strong>
        </span>
        <div style={{ flex: 1, minWidth: 120, height: 6, background: "var(--border, #e5e7eb)", borderRadius: 99, overflow: "hidden" }}>
          <div style={{
            height: "100%", borderRadius: 99,
            width: `${doc.milestones.length ? ((activeMilestone + 1) / doc.milestones.length) * 100 : 0}%`,
            background: isJunior ? "#0e9488" : "var(--accent, #2d4a8a)",
            transition: "width .3s",
          }} />
        </div>
        {totalQuickChecks > 0 && (
          <span style={{ fontSize: ".78rem", color: "var(--muted, #6b7280)", fontVariantNumeric: "tabular-nums" }}>
            {answeredQuickChecks}/{totalQuickChecks} checks done
          </span>
        )}
      </div>
      )}

      {isJunior ? (
        <JourneyRenderer
          doc={doc}
          quizAnswers={progress.quizAnswers}
          onQuickCheckAnswer={handleQuickCheckAnswer}
          activeMilestone={activeMilestone}
          isWide={isWide}
        />
      ) : (
        <StudyRenderer
          doc={doc}
          quizAnswers={progress.quizAnswers}
          onQuickCheckAnswer={handleQuickCheckAnswer}
          activeMilestone={activeMilestone}
          onNavigate={setActiveMilestone}
        />
      )}

      {/* Ask about this chapter — pre-warmed LKB question chips, zero LLM
          cost per click. Replaces free-text asking with click-to-reveal
          questions already answered for this milestone. */}
      <div style={{
        marginTop: 28, background: "var(--panel, #fff)",
        border: "1px solid var(--border, #e5e7eb)", borderRadius: 14,
        padding: "16px 18px",
        maxWidth: isJunior && !isWide ? 640 : "none",
        marginLeft: isJunior && !isWide ? "auto" : 0,
        marginRight: isJunior && !isWide ? "auto" : 0,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
          <MessageCircle size={16} strokeWidth={2.4} color="var(--accent, #6366f1)" aria-hidden="true" />
          <strong style={{ fontSize: ".95rem" }}>Ask about this chapter</strong>
          <span style={{ fontSize: ".76rem", color: "var(--muted, #6b7280)" }}>
            (tap a question to reveal the answer)
          </span>
        </div>

        {currentStepChips.length === 0 && isChipsLoading && (
          <div style={{ fontSize: ".85rem", color: "var(--muted, #6b7280)" }}>
            Loading questions…
          </div>
        )}

        {currentStepChips.length === 0 && !isChipsLoading && (
          <div style={{ fontSize: ".85rem", color: "var(--muted, #6b7280)" }}>
            No suggested questions yet for this section.
          </div>
        )}

        {currentStepChips.map((chip) => {
          const chipKey = chip.id || chip.question;
          return (
            <DoubtChip
              key={chipKey}
              chip={chip}
              isOpen={openChipIds.has(chipKey)}
              onToggle={() => toggleDoubtChip(chipKey)}
            />
          );
        })}
      </div>
    </div>
  );
}

export default ChapterJourneyView;
