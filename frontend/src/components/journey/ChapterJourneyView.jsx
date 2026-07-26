import { useEffect, useMemo, useRef, useState } from "react";
import { MessageCircle, Send } from "lucide-react";

import { askLessonFollowUp } from "../../api/lesson";
import { saveChapterProgress } from "../../api/progress";
import { logStudentActivity } from "../../api/profile";
import JourneyRenderer from "./JourneyRenderer";
import StudyRenderer from "./StudyRenderer";
import LessonMarkdown from "./LessonMarkdown";

/**
 * ChapterJourneyView — container for the Chapter Journey pilot (Phase 2).
 *
 * Receives a validated chapter doc (typed blocks) and renders it with the
 * grade-band renderer: Journey (Grades 5-8) or Study (Grades 9-12).
 *
 * Progress (quick-check answers + XP) persists in localStorage — a few bytes,
 * no lesson content is copied per student. Zero LLM calls while scrolling;
 * only the optional follow-up box hits the AI.
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
    return raw ? JSON.parse(raw) : { quizAnswers: {}, xp: 0 };
  } catch {
    return { quizAnswers: {}, xp: 0 };
  }
}

function milestoneContextText(doc, milestoneIndex) {
  /** Plain-text context of one milestone for follow-up questions. */
  const milestone = doc.milestones[milestoneIndex] || doc.milestones[0];
  if (!milestone) return "";
  const parts = [milestone.title];
  milestone.blocks.forEach((block) => {
    if (block.body_md) parts.push(block.body_md);
    if (block.text) parts.push(block.text);
    if (block.question) parts.push(block.question);
  });
  return parts.join("\n\n").slice(0, 6000);
}

function ChapterJourneyView({ doc, user, grade, mode, subject, chapter }) {
  const storageKey = progressKey({ grade, subject, chapter });
  const [progress, setProgress] = useState(() => loadProgress(storageKey));
  const [activeMilestone, setActiveMilestone] = useState(0);
  const hasSavedCompletionRef = useRef(false);

  const [followUpQuestion, setFollowUpQuestion] = useState("");
  const [followUpMessages, setFollowUpMessages] = useState([]);
  const [followUpLoading, setFollowUpLoading] = useState(false);
  const threadEndRef = useRef(null);

  const isJunior = JUNIOR_GRADES.has(grade);
  // Wide screens get a sticky milestone rail (Journey) / outline (Study), so
  // the compact progress strip is only needed on narrow viewports.
  const isWide = useMediaQuery("(min-width: 1024px)");

  // Reload saved progress when the chapter changes
  useEffect(() => {
    setProgress(loadProgress(storageKey));
    setActiveMilestone(0);
    setFollowUpMessages([]);
    setFollowUpQuestion("");
    hasSavedCompletionRef.current = false;
  }, [storageKey]);

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
          }
        });
      },
      { threshold: 0.4 }
    );
    observer.observe(card);
    return () => observer.disconnect();
  }, [doc, isJunior, user.username, grade, mode, subject, chapter]);

  function handleQuickCheckAnswer(blockKey, answerIndex, isCorrect) {
    setProgress((prev) => {
      const next = {
        ...prev,
        quizAnswers: { ...prev.quizAnswers, [blockKey]: answerIndex },
        xp: prev.xp + (isCorrect ? 10 : 0),
      };
      try {
        window.localStorage.setItem(storageKey, JSON.stringify(next));
      } catch {
        // Progress persistence is best-effort
      }
      return next;
    });
  }

  async function handleAskFollowUp() {
    const question = followUpQuestion.trim();
    if (!question || followUpLoading) return;

    setFollowUpMessages((prev) => [...prev, { role: "user", content: question }]);
    setFollowUpQuestion("");
    setFollowUpLoading(true);

    try {
      const milestone = doc.milestones[activeMilestone] || doc.milestones[0];
      const result = await askLessonFollowUp({
        username: user.username,
        grade,
        mode,
        subject,
        chapter,
        step_title: milestone?.title || "Chapter",
        lesson: milestoneContextText(doc, activeMilestone),
        question,
      });
      setFollowUpMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: result.success
            ? result.answer
            : result.message || "Could not answer that right now.",
        },
      ]);
    } catch (error) {
      setFollowUpMessages((prev) => [
        ...prev,
        { role: "assistant", content: error.message || "Follow-up failed. Check backend." },
      ]);
    } finally {
      setFollowUpLoading(false);
      setTimeout(() => threadEndRef.current?.scrollIntoView({ behavior: "smooth" }), 80);
    }
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
          xp={progress.xp || 0}
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

      {/* Follow-up — the only AI touchpoint in the Journey view */}
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
            (answers use the milestone you are reading)
          </span>
        </div>

        {followUpMessages.length > 0 && (
          <div className="lesson-chat-thread" style={{ marginBottom: 12 }}>
            {followUpMessages.map((message, index) => (
              <div
                key={index}
                className={message.role === "user" ? "chat-message user-message" : "chat-message ai-message"}
              >
                <strong>{message.role === "user" ? "You" : "AI Tutor"}</strong>
                <LessonMarkdown>{message.content}</LessonMarkdown>
              </div>
            ))}
            <div ref={threadEndRef} />
          </div>
        )}

        <div style={{ display: "flex", gap: 8, alignItems: "flex-end" }}>
          <textarea
            rows={2}
            value={followUpQuestion}
            placeholder="Ask a question about what you just read..."
            onChange={(event) => setFollowUpQuestion(event.target.value)}
            style={{ flex: 1, resize: "vertical" }}
          />
          <button
            type="button"
            className="primary-btn"
            onClick={handleAskFollowUp}
            disabled={followUpLoading || !followUpQuestion.trim()}
            style={{ marginTop: 0, display: "inline-flex", alignItems: "center", gap: 6 }}
          >
            {followUpLoading ? "Thinking..." : <><Send size={14} strokeWidth={2.4} aria-hidden="true" /> Ask</>}
          </button>
        </div>
      </div>
    </div>
  );
}

export default ChapterJourneyView;
