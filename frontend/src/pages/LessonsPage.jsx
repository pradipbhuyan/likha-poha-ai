import { useCallback, useEffect, useState } from "react";
import { RotateCcw } from "lucide-react";

import { getSyllabus } from "../api/syllabus";
import { getChapterDoc } from "../api/lesson";
import ChapterJourneyView from "../components/journey/ChapterJourneyView";
import {
  getDefaultSelection,
  getUserBoard,
  getUserGrade,
  getVisibleGrades,
} from "../utils/syllabusDefaults";
import { filterAllowedSubjects } from "../utils/subjectAccess";
import { hasPaidAccess } from "../utils/resolveSubscription";
import { isAllAccessTestUser } from "../utils/testAccounts";

// ── Chapter Journey rollout ────────────────────────────────────────────────
// Grades listed here try the typed-block Chapter Journey experience: one GET,
// whole chapter, zero Generate clicks. Grades 5-8 render Journey mode (card
// feed, XP), Grades 9-12 render Study mode (outline, exam-style). When no
// chapter doc is available (nothing prewarmed/convertible), the page shows
// a simple "Not ready yet" message rather than any legacy per-step UI.
const CHAPTER_JOURNEY_PILOT_GRADES = new Set([
  "Grade 5", "Grade 6", "Grade 7", "Grade 8",
  "Grade 9", "Grade 10", "Grade 11", "Grade 12",
]);

const STEP_CONTROL_FONT_SIZE = "0.875rem";

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

function LessonsPage({ user, setActivePage, initialTarget, onInitialTargetConsumed }) {
  /** Student lesson workspace — Chapter Journey view with grade/subject/chapter selector. */

  // ── Effective user: syncs stream/cbseSubjects from backend for Grade 11/12 ──
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

  // ── Chapter Journey doc ────────────────────────────────────────────────────
  const [chapterDoc, setChapterDoc] = useState(null);
  const [chapterDocLoading, setChapterDocLoading] = useState(false);
  // True only while a manual "Refresh lesson" click is in flight — kept
  // separate from chapterDocLoading so the button can show its own
  // "Refreshing..." state without hiding the currently-visible lesson.
  const [chapterDocRefreshing, setChapterDocRefreshing] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setChapterDoc(null);
    if (!CHAPTER_JOURNEY_PILOT_GRADES.has(grade) || !subject || !chapter) {
      return undefined;
    }
    setChapterDocLoading(true);
    getChapterDoc({ grade, mode, subject, chapter, board: mode })
      .then((result) => {
        if (cancelled) return;
        setChapterDoc(result?.available && result?.doc ? result.doc : null);
      })
      .catch(() => {
        if (!cancelled) setChapterDoc(null);
      })
      .finally(() => {
        if (!cancelled) setChapterDocLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [grade, mode, subject, chapter]);

  // Manually re-fetch the Chapter Journey doc with refresh=true, forcing the
  // backend to discard any stored/stale converted document and rebuild it
  // fresh from the current lesson_cache content. This is the reliable fix
  // for "I updated the content but the lesson still shows old text" — that
  // staleness lives in a server-side cache table (lesson_chapter_doc),
  // which a browser hard-refresh cannot touch. See
  // docs/LESSON_CONTENT_QUALITY_REVIEW_PLAN.md §4o.
  const handleRefreshLesson = useCallback(() => {
    if (!CHAPTER_JOURNEY_PILOT_GRADES.has(grade) || !subject || !chapter) {
      return;
    }
    setChapterDocRefreshing(true);
    getChapterDoc({ grade, mode, subject, chapter, board: mode, refresh: true })
      .then((result) => {
        setChapterDoc(result?.available && result?.doc ? result.doc : null);
      })
      .catch(() => {
        // Keep whatever was showing before — a failed refresh should not
        // blank out a lesson that was already displaying correctly.
      })
      .finally(() => {
        setChapterDocRefreshing(false);
      });
  }, [grade, mode, subject, chapter]);

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
        let selectedChapter =
          selectedSubject === defaultSubject
            ? defaultChapter
            : data.syllabus[defaultGrade]?.[selectedMode]?.[selectedSubject]?.[0] || "";

        // A weak-topic/practice link from another page (e.g. the Dashboard's
        // Weak Topics card) can request a specific subject+chapter. Only
        // honor it if that combination is genuinely reachable for this
        // student — an allowed subject with a real chapter in the syllabus —
        // otherwise silently keep the computed default rather than risk
        // landing on a blank or inaccessible selection.
        if (initialTarget?.subject && initialTarget?.chapter) {
          const allowedSubjectsForSelectedMode = filterAllowedSubjects(
            user,
            Object.keys(data.syllabus[defaultGrade]?.[selectedMode] || {}),
            selectedMode
          );
          const targetChapters =
            data.syllabus[defaultGrade]?.[selectedMode]?.[initialTarget.subject] || [];

          if (
            allowedSubjectsForSelectedMode.includes(initialTarget.subject) &&
            targetChapters.includes(initialTarget.chapter)
          ) {
            selectedSubject = initialTarget.subject;
            selectedChapter = initialTarget.chapter;
          }
          onInitialTargetConsumed?.();
        }

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

  if (loading) {
    return <p>Loading syllabus...</p>;
  }

  if (error) {
    return <p className="error">{error}</p>;
  }

  const grades = getVisibleGrades(syllabusData, user);

  function getAllowedSubjects(allSubjects, selectedMode) {
    /** Filter subjects by the student's subscription access for CBSE mode.
     *  Uses effectiveUser (which has up-to-date stream/cbseSubjects) rather than user. */
    return filterAllowedSubjects(effectiveUser, allSubjects, selectedMode);
  }

  const allSubjects = Object.keys(syllabusData[grade][mode]);
  const subjects = getAllowedSubjects(allSubjects, mode);
  const chapters = subject ? syllabusData[grade][mode][subject] || [] : [];

  function handleGradeChange(value) {
    /** Reset mode, subject, and chapter after changing grade. */
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
  }

  function handleSubjectChange(value) {
    /** Select a new subject and reset the chapter to its first available lesson. */
    const newChapter = syllabusData[grade][mode][value][0];
    setSubject(value);
    setChapter(newChapter);
  }

  // ── Exemplar chapter gate ──────────────────────────────────────────────────
  const isExemplarChapter = chapter?.includes("Exemplar:");
  // SECURITY FIX: parentId alone does NOT grant paid access.
  // Use hasPaidAccess() which checks accessCbse + subscriptionExpiresAt correctly.
  const hasPaidAccessForLessons = hasPaidAccess(user);
  const isExemplarLocked = isExemplarChapter && !hasPaidAccessForLessons;

  const topBarControls = (
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
      <select
        value={grade}
        onChange={(e) => handleGradeChange(e.target.value)}
        style={{ ..._selectStyle, flex: 1, minWidth: 0 }}
      >
        {grades.map(g => <option key={g} value={g}>{g}</option>)}
      </select>
      <select
        value={subject}
        onChange={(e) => handleSubjectChange(e.target.value)}
        disabled={subjects.length === 0}
        style={{ ..._selectStyle, flex: 1, minWidth: 0 }}
      >
        {subjects.map(s => <option key={s} value={s}>{s}</option>)}
      </select>
      <select
        value={chapter}
        onChange={(e) => setChapter(e.target.value)}
        style={{ ..._selectStyle, flex: 2, minWidth: 0 }}
      >
        {chapters.map(c => {
          const locked = c.includes("Exemplar:") && !hasPaidAccessForLessons;
          return <option key={c} value={c}>{locked ? `🔒 ${c}` : c}</option>;
        })}
      </select>
    </div>
  );

  return (
    <div className="lesson-workspace premium-page premium-lessons-page">
      {/* Top bar hidden while a chapter is loading so switching chapters shows
          only the Likha Poha AI loading animation, not a half-relevant
          control bar sitting above a blank/loading area. */}
      {!chapterDocLoading && topBarControls}

      {chapterDocLoading ? (
        <div className="lesson-generating-overlay">
          <img
            src="/likhapohaai.gif"
            alt="Likha Poha AI is loading your chapter…"
            className="lesson-loading-gif"
          />
          <p className="lesson-loading-label">Loading your chapter…</p>
        </div>
      ) : chapterDoc && !isExemplarLocked ? (
        <>
          {/* Refresh lesson — reliably clears the server-side chapter-doc
              cache and rebuilds from the latest lesson_cache content. Use
              this instead of a browser hard-refresh, which cannot touch
              this server-side cache table. See §4o of the plan doc.
              Sticky-positioned so it stays reachable while scrolling
              through a long chapter, instead of only being visible at the
              very top of the page.
              Restricted to the internal QA test account only (2026-08-03) —
              this is a content-debugging tool, not a student-facing
              feature, so it must not appear for any real student/teacher
              account. */}
          {isAllAccessTestUser(user) && (
            <div
              style={{
                position: "sticky",
                top: 8,
                zIndex: 40,
                display: "flex",
                justifyContent: "flex-end",
                marginBottom: 8,
                pointerEvents: "none",
              }}
            >
              <button
                type="button"
                onClick={handleRefreshLesson}
                disabled={chapterDocRefreshing}
                title="Reload this chapter's content from the latest source — fixes 'I updated the lesson but it still shows old text'"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 6,
                  padding: "6px 14px",
                  fontSize: "0.8rem",
                  fontWeight: 600,
                  borderRadius: 8,
                  border: "1px solid var(--border, #d1d5db)",
                  background: "var(--panel, #ffffff)",
                  color: "var(--text, #374151)",
                  cursor: chapterDocRefreshing ? "default" : "pointer",
                  opacity: chapterDocRefreshing ? 0.6 : 1,
                  boxShadow: "0 2px 8px rgba(0,0,0,.12)",
                  pointerEvents: "auto",
                }}
              >
                <RotateCcw size={14} strokeWidth={2.4} />
                {chapterDocRefreshing ? "Refreshing…" : "Refresh lesson"}
              </button>
            </div>
          )}
          <ChapterJourneyView
            doc={chapterDoc}
            user={user}
            grade={grade}
            mode={mode}
            subject={subject}
            chapter={chapter}
          />
        </>
      ) : isExemplarLocked ? (
        <div className="premium-section premium-empty-lesson" style={{ textAlign: "center", padding: "48px 24px" }}>
          <p className="eyebrow">🔒 Exemplar Lesson — Paid Only</p>
          <h2 style={{ marginBottom: 12 }}>Upgrade to unlock this chapter</h2>
          <p style={{ color: "var(--text-muted, #6b7280)", maxWidth: 480, margin: "0 auto 20px" }}>
            Lessons for NCERT Exemplar chapters are available to paid subscribers.
          </p>
          <button
            type="button"
            onClick={() => setActivePage?.("subscriptionPlans")}
            style={{ padding: "10px 22px", borderRadius: 8, border: "none", background: "linear-gradient(135deg,#6366f1,#8b5cf6)", color: "#fff", fontWeight: 700, fontSize: ".9rem", cursor: "pointer", fontFamily: "inherit" }}>
            🚀 Upgrade to Unlock
          </button>
        </div>
      ) : (
        <div className="premium-section premium-empty-lesson" style={{ textAlign: "center", padding: "48px 24px" }}>
          <p className="eyebrow">Not ready yet</p>
          <h2 style={{ marginBottom: 12 }}>This chapter isn't available yet</h2>
          <p style={{ color: "var(--text-muted, #6b7280)", maxWidth: 480, margin: "0 auto" }}>
            Content for <strong>{chapter}</strong> hasn't been prepared for this grade/subject yet.
            Please choose a different chapter, or check back soon.
          </p>
        </div>
      )}
    </div>
  );
}

export default LessonsPage;
