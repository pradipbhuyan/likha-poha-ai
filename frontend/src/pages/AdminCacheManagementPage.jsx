import { useEffect, useRef, useState } from "react";
import {
  getCacheStatus,
  startLessonPrewarm,
  startQuestionBankBuild,
  clearLessonCache,
  clearQuestionBank,
  getChaptersForGrade,
  startChapterPrewarm,
  startChapterQuestionBankBuild,
  startDoubtKbPrewarm,
  getDoubtKbStats,
  restoreLessonCache,
  startLkbBuild,
  getLkbOverview,
  getAudioOverview,
  startAudioPrewarm,
  clearChapterCache,
} from "../api/cacheManagement";
import { adminGetQBStatus, adminPrewarm, runExamPrepMigration, adminImportBulk } from "../api/examPrep";

function gradeToSlug(grade) {
  /** Convert "Grade 9" to "grade-9" for URL slugs. */
  return grade.toLowerCase().replace(" ", "-");
}

function ProgressBar({ value, max, color = "blue" }) {
  /** Compact progress bar for lesson/question counts. */
  const pct = max > 0 ? Math.min(100, Math.round((value / max) * 100)) : 0;
  return (
    <div style={{ background: "#e5e7eb", borderRadius: 6, height: 8, overflow: "hidden" }}>
      <div
        style={{
          width: `${pct}%`,
          height: "100%",
          background: pct === 100 ? "#22c55e" : color === "purple" ? "#a855f7" : "#3b82f6",
          transition: "width 0.4s",
        }}
      />
    </div>
  );
}

function StatusBadge({ complete, running }) {
  /** Show a compact status badge for a grade/action. */
  if (running) return <span className="status-pill" style={{ background: "#f59e0b", color: "#fff" }}>⏳ Running…</span>;
  if (complete) return <span className="status-pill" style={{ background: "#22c55e", color: "#fff" }}>✅ Complete</span>;
  return <span className="status-pill" style={{ background: "#6b7280", color: "#fff" }}>⬜ Ready</span>;
}

const ALL_GRADE_OPTIONS = Array.from({ length: 12 }, (_, i) => `Grade ${i + 1}`);

// Models available for pre-warming (admin choice, default nano)
const PREWARM_MODEL_OPTIONS = [
  { value: "gpt-4.1-nano", label: "gpt-4.1-nano (cheapest — default)" },
  { value: "gpt-4.1-mini", label: "gpt-4.1-mini (better quality)" },
  { value: "gpt-4.1",      label: "gpt-4.1 (highest quality)" },
];

// Fixed embedding model for all RAG / vector indexing
const EMBEDDING_MODEL = "text-embedding-3-small";

/**
 * Approximate per-grade-9 prewarm costs.
 * Lessons: ~750 steps × (1 000 input + 1 500 output tokens each)
 * Questions: ~13 500 questions × (500 input + 800 output tokens each)
 * Time figures are wall-clock estimates at typical concurrency.
 */
const PREWARM_COST = {
  "gpt-4.1-nano": {
    lessons:       0.53,   lessonMin: 12,
    questions:     5.00,   questionMin: 40,
    inputPer1K:    0.0001, outputPer1K: 0.0004,
  },
  "gpt-4.1-mini": {
    lessons:       2.10,   lessonMin: 20,
    questions:    20.00,   questionMin: 65,
    inputPer1K:   0.0004,  outputPer1K: 0.0016,
  },
  "gpt-4.1": {
    lessons:      10.50,   lessonMin: 30,
    questions:   100.00,   questionMin: 100,
    inputPer1K:   0.002,   outputPer1K: 0.008,
  },
};

function AdminCacheManagementPage({ user }) {
  /** Admin page for grade-by-grade lesson pre-warming, question bank building, and cache clearing. */
  const [grades, setGrades] = useState([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const pollRef = useRef(null);

  // ---- Prewarm model selection ----
  const [prewarmModel, setPrewarmModel] = useState("gpt-4.1-nano");

  // ---- Doubt KB state ----
  const [dkbStats, setDkbStats] = useState(null);
  const [dkbRunningGrades, setDkbRunningGrades] = useState({});

  // ---- LKB (Lesson Knowledge Base) state ----
  const [lkbOverviews, setLkbOverviews] = useState({});
  const [lkbRunningGrades, setLkbRunningGrades] = useState({});

  // ---- Audio cache state ----
  const [audioOverviews, setAudioOverviews] = useState({});
  const [audioRunningGrades, setAudioRunningGrades] = useState({});

  // ---- Chapter-by-chapter prewarm state ----
  const [chapterGrade, setChapterGrade] = useState("Grade 9");
  const [chapterList, setChapterList] = useState([]);
  const [chapterListLoading, setChapterListLoading] = useState(false);
  const [selectedSubject, setSelectedSubject] = useState("");
  const [selectedChapter, setSelectedChapter] = useState("");
  const [chapterRunning, setChapterRunning] = useState(false);
  const [chapterQBankRunning, setChapterQBankRunning] = useState(false);
  const [chapterMessage, setChapterMessage] = useState("");
  const [chapterError, setChapterError] = useState("");

  async function loadStatus() {
    /** Fetch latest cache/bank status for all grades. */
    try {
      const result = await getCacheStatus(user.accessToken);
      if (result.success) {
        setGrades(result.grades || []);
      }
    } catch (err) {
      setError(err.message || "Could not load cache status.");
    } finally {
      setLoading(false);
    }
  }

  async function loadDkbStats() {
    try {
      const result = await getDoubtKbStats(user.accessToken);
      if (result.success) setDkbStats(result);
    } catch {
      // DKB stats are optional — fail silently
    }
  }

  async function loadAudioOverview(grade) {
    try {
      const result = await getAudioOverview(gradeToSlug(grade), user.accessToken);
      if (result.success) {
        setAudioOverviews(prev => ({ ...prev, [grade]: result }));
      }
    } catch {
      // Audio overview is optional — fail silently
    }
  }

  async function loadLkbOverview(grade) {
    try {
      const result = await getLkbOverview(gradeToSlug(grade), user.accessToken);
      if (result.success) {
        setLkbOverviews(prev => ({ ...prev, [grade]: result }));
      }
    } catch {
      // LKB overview is optional — fail silently
    }
  }

  useEffect(() => {
    // Initial load + poll every 15 seconds for background job progress
    let cancelled = false;

    async function fetchStatus() {
      try {
        const result = await getCacheStatus(user.accessToken);
        if (!cancelled && result.success) {
          setGrades(result.grades || []);
        }
      } catch (err) {
        if (!cancelled) setError(err.message || "Could not load cache status.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchStatus();
    loadDkbStats();

    // Pre-load LKB + audio overviews for supported grades only (Grade 5–12)
    // Grades 1–4 are not supported by the backend and return 400.
    const supportedGrades = Array.from({ length: 8 }, (_, i) => `Grade ${i + 5}`);
    supportedGrades.forEach((g) => { loadLkbOverview(g); loadAudioOverview(g); });

    // Poll every 15 seconds — refresh cache status, LKB, and audio counts
    pollRef.current = setInterval(() => {
      fetchStatus();
      supportedGrades.forEach((g) => { loadLkbOverview(g); loadAudioOverview(g); });
    }, 15000);

    return () => {
      cancelled = true;
      clearInterval(pollRef.current);
    };
  }, [user.accessToken]);

  async function handleStartLessons(grade) {
    /** Start lesson pre-warming for a grade in the background. */
    setMessage("");
    setError("");
    try {
      const result = await startLessonPrewarm(gradeToSlug(grade), user.accessToken);
      setMessage(result.message || `Lesson pre-warming started for ${grade}.`);
      setTimeout(loadStatus, 2000);
    } catch (err) {
      setError(err.message || "Failed to start lesson pre-warming.");
    }
  }

  async function handleStartQuestions(grade) {
    /** Start question bank building for a grade in the background. */
    setMessage("");
    setError("");
    try {
      const result = await startQuestionBankBuild(gradeToSlug(grade), user.accessToken);
      setMessage(result.message || `Question bank building started for ${grade}.`);
      setTimeout(loadStatus, 2000);
    } catch (err) {
      setError(err.message || "Failed to start question bank building.");
    }
  }

  async function handleBuildDoubtKb(grade) {
    /** Start background Doubt KB pre-warming for a grade. */
    setMessage("");
    setError("");
    setDkbRunningGrades((prev) => ({ ...prev, [grade]: true }));
    try {
      const result = await startDoubtKbPrewarm(gradeToSlug(grade), user.accessToken);
      setMessage(result.message || `Doubt KB pre-warming started for ${grade}.`);
      // Reload stats after a delay
      setTimeout(loadDkbStats, 30000);
    } catch (err) {
      setError(err.message || "Failed to start Doubt KB pre-warming.");
    } finally {
      setTimeout(() => setDkbRunningGrades((prev) => ({ ...prev, [grade]: false })), 60000);
    }
  }

  async function handleBuildAudio(grade) {
    /** Start background TTS audio pre-warm for a grade. */
    setMessage("");
    setError("");
    setAudioRunningGrades((prev) => ({ ...prev, [grade]: true }));
    try {
      const result = await startAudioPrewarm(gradeToSlug(grade), user.accessToken);
      setMessage(result.message || `Audio prewarm started for ${grade}.`);
      // Refresh audio overview after a delay
      setTimeout(() => loadAudioOverview(grade), 30000);
    } catch (err) {
      setError(err.message || "Failed to start audio prewarm.");
    } finally {
      // Audio takes ~18s per step × many steps — reset after 10 min
      setTimeout(() => setAudioRunningGrades((prev) => ({ ...prev, [grade]: false })), 600000);
    }
  }

  async function handleBuildLkb(grade) {
    /** Start background LKB chip generation for a grade. */
    setMessage("");
    setError("");
    setLkbRunningGrades((prev) => ({ ...prev, [grade]: true }));
    try {
      const result = await startLkbBuild(gradeToSlug(grade), user.accessToken);
      setMessage(result.message || `LKB build started for ${grade}.`);
      setTimeout(() => loadLkbOverview(grade), 30000);
    } catch (err) {
      setError(err.message || "Failed to start LKB build.");
    } finally {
      setTimeout(() => setLkbRunningGrades((prev) => ({ ...prev, [grade]: false })), 90000);
    }
  }

  async function handleRestoreLessons(grade) {
    /** Restore archived lessons for a grade. */
    setMessage("");
    setError("");
    try {
      const result = await restoreLessonCache(gradeToSlug(grade), user.accessToken);
      setMessage(result.message || `Lessons restored for ${grade}.`);
      loadStatus();
    } catch (err) {
      setError(err.message || "Failed to restore lessons.");
    }
  }

  async function handleClearLessons(grade) {
    /** Archive (soft-delete) cached lessons for a grade. Lessons can be restored. */
    if (!window.confirm(
      `Archive cached lessons for ${grade}?\n\nThey will be hidden from students but NOT permanently deleted.\nYou can restore them with the Restore button.`
    )) return;
    setMessage("");
    setError("");
    try {
      const result = await clearLessonCache(gradeToSlug(grade), user.accessToken);
      setMessage(result.message || `Lesson cache cleared for ${grade}.`);
      loadStatus();
    } catch (err) {
      setError(err.message || "Failed to clear lesson cache.");
    }
  }

  async function loadChaptersForGrade(grade) {
    /** Fetch available chapters for the selected grade. */
    setChapterListLoading(true);
    setChapterList([]);
    setSelectedSubject("");
    setSelectedChapter("");
    setChapterMessage("");
    setChapterError("");
    try {
      const result = await getChaptersForGrade(gradeToSlug(grade), user.accessToken);
      const chapters = result.chapters || [];
      setChapterList(chapters);
      if (chapters.length > 0) {
        setSelectedSubject(chapters[0].subject);
        setSelectedChapter(chapters[0].chapter);
      }
    } catch (err) {
      setChapterError(err.message || "Could not load chapters.");
    } finally {
      setChapterListLoading(false);
    }
  }

  useEffect(() => {
    if (user?.accessToken && chapterGrade) {
      loadChaptersForGrade(chapterGrade);
    }
  }, [chapterGrade, user?.accessToken]);

  async function handleChapterPrewarm() {
    /** Start a background prewarm for the selected single chapter. */
    if (!selectedSubject || !selectedChapter) return;
    const entry = chapterList.find(
      (c) => c.subject === selectedSubject && c.chapter === selectedChapter
    );
    if (!entry) return;

    setChapterRunning(true);
    setChapterMessage("");
    setChapterError("");
    try {
      const result = await startChapterPrewarm(
        { grade: chapterGrade, mode: entry.mode, subject: selectedSubject, chapter: selectedChapter },
        user.accessToken
      );
      setChapterMessage(result.message || "Chapter prewarm started.");
      [20000, 45000, 75000, 110000].forEach((delay) =>
        setTimeout(loadStatus, delay)
      );
    } catch (err) {
      setChapterError(err.message || "Failed to start chapter prewarm.");
    } finally {
      setChapterRunning(false);
    }
  }

  async function handleChapterQuestionBankBuild() {
    /** Start background RAG-grounded question bank building for the selected chapter. */
    if (!selectedSubject || !selectedChapter) return;
    const entry = chapterList.find(
      (c) => c.subject === selectedSubject && c.chapter === selectedChapter
    );
    if (!entry) return;

    setChapterQBankRunning(true);
    setChapterMessage("");
    setChapterError("");
    try {
      const result = await startChapterQuestionBankBuild(
        { grade: chapterGrade, mode: entry.mode, subject: selectedSubject, chapter: selectedChapter },
        user.accessToken
      );
      setChapterMessage(result.message || "Question bank build started.");
      // 9 batches × ~4 s each ≈ 36 s; poll at 20 s, 40 s, 60 s
      [20000, 40000, 60000].forEach((delay) =>
        setTimeout(loadStatus, delay)
      );
    } catch (err) {
      setChapterError(err.message || "Failed to start question bank build.");
    } finally {
      setChapterQBankRunning(false);
    }
  }

  async function handleClearQuestions(grade) {
    /** Clear all question bank entries for a grade after confirmation. */
    if (!window.confirm(`Clear ALL question bank entries for ${grade}? This cannot be undone.`)) return;
    setMessage("");
    setError("");
    try {
      const result = await clearQuestionBank(gradeToSlug(grade), user.accessToken);
      setMessage(result.message || `Question bank cleared for ${grade}.`);
      loadStatus();
    } catch (err) {
      setError(err.message || "Failed to clear question bank.");
    }
  }

  if (loading) return <p>Loading cache status…</p>;

  const anyRunning = grades.some((g) => g.lessons_running || g.questions_running);

  return (
    <div className="premium-page">
      <section className="premium-section">
        <div className="premium-header">
          <p className="eyebrow">Phase 2 — Content Pre-Generation</p>
          <h2>🗄️ Cache & Question Bank Management</h2>
          <p>
            Generate lessons and mock test questions once per grade and serve them
            instantly to all students at zero token cost. Run grade by grade and
            test before moving to the next grade.
          </p>
        </div>

        {anyRunning && (
          <div className="info-box">
            ⏳ A background job is running. This page auto-refreshes every 15 seconds.
          </div>
        )}

        {message && <div className="info-box">{message}</div>}
        {error && <div className="error-box">{error}</div>}

        <div className="info-box" style={{ fontSize: "0.85rem", marginBottom: 24 }}>
          <strong>How it works:</strong> Click <em>Generate Lessons</em> to start background
          pre-warming for a grade. The button disables once the grade is complete. Use
          <em> Clear Cache</em> to reset a grade if RAG content changes. All students continue
          getting lessons normally — the cache just makes it instant and free.
        </div>
      </section>

      <section className="premium-section">
        {grades.map((gradeData) => {
          const {
            grade,
            cached_lessons, expected_lessons, lessons_complete, lessons_running,
            banked_questions, expected_questions, questions_complete, questions_running,
            dkb_cached = 0, dkb_expected = 0, dkb_complete = false, dkb_running = false,
          } = gradeData;

          const lessonPct = expected_lessons > 0
            ? Math.round((cached_lessons / expected_lessons) * 100)
            : 0;
          const questionPct = expected_questions > 0
            ? Math.round((banked_questions / expected_questions) * 100)
            : 0;
          const dkbPct = dkb_expected > 0
            ? Math.min(100, Math.round((dkb_cached / dkb_expected) * 100))
            : 0;
          const hasContent = expected_lessons > 0 || expected_questions > 0;

          return (
            <div key={grade} className="premium-card" style={{ marginBottom: 20 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                <h3 style={{ margin: 0 }}>{grade}</h3>
                <div style={{ display: "flex", gap: 8 }}>
                  <StatusBadge complete={lessons_complete} running={lessons_running} />
                  {expected_questions > 0 && (
                    <StatusBadge complete={questions_complete} running={questions_running} />
                  )}
                </div>
              </div>

              {!hasContent && (
                <p className="muted-text" style={{ fontSize: "0.85rem" }}>
                  No RAG content uploaded for this grade yet. Upload textbook chapters first.
                </p>
              )}

              {hasContent && (
                <>
                  {/* Lesson cache progress */}
                  <div style={{ marginBottom: 12 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem", marginBottom: 4 }}>
                      <span>📚 Lessons cached</span>
                      <strong>{cached_lessons} / {expected_lessons} ({lessonPct}%)</strong>
                    </div>
                    <ProgressBar value={cached_lessons} max={expected_lessons} color="blue" />
                  </div>

                  {/* Question bank progress */}
                  {expected_questions > 0 && (
                    <div style={{ marginBottom: 12 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem", marginBottom: 4 }}>
                        <span>🎯 Questions in bank</span>
                        <strong>{banked_questions} / {expected_questions} ({questionPct}%)</strong>
                      </div>
                      <ProgressBar value={banked_questions} max={expected_questions} color="purple" />
                    </div>
                  )}

                  {/* DKB (Doubt Knowledge Base) progress */}
                  {dkb_expected > 0 && (
                    <div style={{ marginBottom: 12 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem", marginBottom: 4 }}>
                        <span>🧠 Doubt KB Q&A pairs</span>
                        <strong style={{ color: dkb_complete ? "#22c55e" : dkbPct > 0 ? "#7c3aed" : "#6b7280" }}>
                          {dkb_cached.toLocaleString()} / {dkb_expected.toLocaleString()} ({dkbPct}%)
                          {dkb_running && " ⏳"}
                          {!dkb_running && dkb_cached < dkb_expected && dkb_cached > 0 && (
                            <span style={{ fontWeight: 400, color: "#9ca3af" }}>
                              {" "}— {(dkb_expected - dkb_cached).toLocaleString()} more needed
                            </span>
                          )}
                        </strong>
                      </div>
                      <div style={{ background: "#e5e7eb", borderRadius: 6, height: 8, overflow: "hidden" }}>
                        <div style={{
                          width: `${dkbPct}%`, height: "100%", transition: "width 0.4s",
                          background: dkb_complete ? "#22c55e" : dkbPct > 0 ? "#7c3aed" : "#d1d5db",
                        }} />
                      </div>
                    </div>
                  )}

                  {/* Audio cache progress row */}
                  {(() => {
                    const audio = audioOverviews[grade];
                    const audio_cached = audio?.audio_cached ?? 0;
                    const audio_expected = audio?.audio_expected ?? 0;
                    const audio_pct = audio_expected > 0 ? Math.min(100, Math.round(audio_cached / audio_expected * 100)) : 0;
                    const audio_complete = audio_expected > 0 && audio_cached >= audio_expected;
                    const audio_running = audioRunningGrades[grade];
                    if (!audio && !audio_running) return null;
                    return (
                      <div style={{ marginBottom: 16 }}>
                        <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem", marginBottom: 4 }}>
                          <span>🔊 Audio cached</span>
                          <strong style={{ color: audio_complete ? "#22c55e" : audio_pct > 0 ? "#db2777" : "#6b7280" }}>
                            {audio_cached.toLocaleString()} / {audio_expected.toLocaleString()} ({audio_pct}%)
                            {audio_running && " ⏳"}
                            {!audio_running && audio_cached < audio_expected && audio_cached > 0 && (
                              <span style={{ fontWeight: 400, color: "#9ca3af" }}>
                                {" "}— {(audio_expected - audio_cached).toLocaleString()} more needed
                              </span>
                            )}
                            {audio?.total_mb > 0 && (
                              <span style={{ fontWeight: 400, color: "#9ca3af" }}>
                                {" "}· {audio.total_mb} MB
                              </span>
                            )}
                          </strong>
                        </div>
                        <div style={{ background: "#e5e7eb", borderRadius: 6, height: 8, overflow: "hidden" }}>
                          <div style={{
                            width: `${audio_pct}%`, height: "100%", transition: "width 0.4s",
                            background: audio_complete ? "#22c55e" : audio_pct > 0 ? "#db2777" : "#d1d5db",
                          }} />
                        </div>
                      </div>
                    );
                  })()}

                  {/* LKB (Lesson Knowledge Base) progress — inline with above rows */}
                  {(() => {
                    const lkb = lkbOverviews[grade];
                    const lkb_built = lkb?.chips_built ?? 0;
                    const lkb_expected = lkb?.chips_expected ?? 0;
                    const lkb_pct = lkb_expected > 0 ? Math.min(100, Math.round(lkb_built / lkb_expected * 100)) : 0;
                    const lkb_complete = lkb_expected > 0 && lkb_built >= lkb_expected;
                    const lkb_running = lkbRunningGrades[grade];
                    if (!lkb && !lkb_running) return null;
                    return (
                      <div style={{ marginBottom: 16 }}>
                        <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem", marginBottom: 4 }}>
                          <span>📚 LKB chips</span>
                          <strong style={{ color: lkb_complete ? "#22c55e" : lkb_pct > 0 ? "#0891b2" : "#6b7280" }}>
                            {lkb_built.toLocaleString()} / {lkb_expected.toLocaleString()} ({lkb_pct}%)
                            {lkb_running && " ⏳"}
                            {!lkb_running && lkb_built < lkb_expected && lkb_built > 0 && (
                              <span style={{ fontWeight: 400, color: "#9ca3af" }}>
                                {" "}— {(lkb_expected - lkb_built).toLocaleString()} more needed
                              </span>
                            )}
                          </strong>
                        </div>
                        <div style={{ background: "#e5e7eb", borderRadius: 6, height: 8, overflow: "hidden" }}>
                          <div style={{
                            width: `${lkb_pct}%`, height: "100%", transition: "width 0.4s",
                            background: lkb_complete ? "#22c55e" : lkb_pct > 0 ? "#0891b2" : "#d1d5db",
                          }} />
                        </div>
                      </div>
                    );
                  })()}

                  {/* Action buttons */}
                  <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                    <button
                      className="primary-btn"
                      disabled={lessons_complete || lessons_running}
                      onClick={() => handleStartLessons(grade)}
                      title={lessons_complete ? "Already complete for this grade" : ""}
                    >
                      {lessons_running ? "⏳ Generating…" : lessons_complete ? "✅ Lessons Done" : "⚡ Generate Lessons"}
                    </button>

                    {expected_questions > 0 && (
                      <button
                        className="primary-btn"
                        disabled={questions_complete || questions_running}
                        onClick={() => handleStartQuestions(grade)}
                        title={questions_complete ? "Already complete for this grade" : ""}
                        style={{ background: questions_complete ? "#22c55e" : undefined }}
                      >
                        {questions_running ? "⏳ Building…" : questions_complete ? "✅ Bank Done" : "🎯 Build Question Bank"}
                      </button>
                    )}

                    <button
                      className="secondary-btn"
                      disabled={cached_lessons === 0 || lessons_running}
                      onClick={() => handleClearLessons(grade)}
                      title="Archives lessons (not deleted — can be restored)"
                    >
                      🗑️ Clear Lessons
                    </button>

                    <button
                      className="secondary-btn"
                      onClick={() => handleRestoreLessons(grade)}
                      title="Restore archived lessons back to active"
                      style={{ background: "#f0fdf4", color: "#166534", border: "1px solid #bbf7d0" }}
                    >
                      ↩️ Restore
                    </button>

                    {expected_questions > 0 && (
                      <button
                        className="secondary-btn"
                        disabled={banked_questions === 0 || questions_running}
                        onClick={() => handleClearQuestions(grade)}
                        title="Clear question bank to force re-generation"
                      >
                        🗑️ Clear Bank
                      </button>
                    )}

                    <button
                      className="primary-btn"
                      disabled={dkbRunningGrades[grade] || dkb_running}
                      onClick={() => handleBuildDoubtKb(grade)}
                      title={dkb_complete ? "Doubt KB complete for this grade" : `Pre-generate ${dkb_expected - dkb_cached} more Q&A pairs`}
                      style={{ background: dkb_complete ? "#22c55e" : (dkbRunningGrades[grade] || dkb_running) ? "#6b7280" : "#7c3aed" }}
                    >
                      {(dkbRunningGrades[grade] || dkb_running)
                        ? "⏳ Building Doubt KB…"
                        : dkb_complete
                        ? "✅ Doubt KB Done"
                        : `🧠 Build Doubt KB${dkb_cached > 0 ? " (Resume)" : ""}`}
                    </button>

                    {/* Audio build button */}
                    {(() => {
                      const audio = audioOverviews[grade];
                      const audio_cached = audio?.audio_cached ?? 0;
                      const audio_expected = audio?.audio_expected ?? 0;
                      const audio_pct = audio_expected > 0 ? Math.round(audio_cached / audio_expected * 100) : 0;
                      const audio_complete = audio_expected > 0 && audio_cached >= audio_expected;
                      const audio_running = audioRunningGrades[grade];
                      return (
                        <button
                          className="primary-btn"
                          disabled={audio_running}
                          onClick={() => {
                            if (!audioOverviews[grade]) loadAudioOverview(grade);
                            handleBuildAudio(grade);
                          }}
                          style={{ background: audio_complete ? "#22c55e" : audio_running ? "#6b7280" : "#db2777" }}
                          title="Pre-generate TTS audio for all lesson steps — instant playback for students (Edge TTS, free)"
                        >
                          {audio_running
                            ? "⏳ Building Audio…"
                            : audio_complete
                            ? "✅ Audio Done"
                            : audio_cached > 0
                            ? `🔊 Build Audio (Resume · ${audio_pct}%)`
                            : "🔊 Build Audio Cache"}
                        </button>
                      );
                    })()}

                    {/* LKB build button — inline with other action buttons */}
                    {(() => {
                      const lkb = lkbOverviews[grade];
                      const lkb_built = lkb?.chips_built ?? 0;
                      const lkb_expected_val = lkb?.chips_expected ?? 0;
                      const lkb_pct = lkb_expected_val > 0 ? Math.round(lkb_built / lkb_expected_val * 100) : 0;
                      const lkb_complete = lkb_expected_val > 0 && lkb_built >= lkb_expected_val;
                      const lkb_running = lkbRunningGrades[grade];
                      return (
                        <button
                          className="primary-btn"
                          disabled={lkb_running}
                          onClick={() => {
                            if (!lkbOverviews[grade]) loadLkbOverview(grade);
                            handleBuildLkb(grade);
                          }}
                          style={{ background: lkb_complete ? "#22c55e" : lkb_running ? "#6b7280" : "#0891b2" }}
                          title="Generate 5 NCERT-grounded chip Q&As per step per chapter"
                        >
                          {lkb_running
                            ? "⏳ Building LKB…"
                            : lkb_complete
                            ? "✅ LKB Done"
                            : lkb_built > 0
                            ? `📚 Build LKB (Resume · ${lkb_pct}%)`
                            : "📚 Build LKB Chips"}
                        </button>
                      );
                    })()}
                  </div>

                  {(lessons_complete && (expected_questions === 0 || questions_complete)) && (
                    <div style={{ marginTop: 10, fontSize: "0.8rem", color: "#22c55e" }}>
                      ✅ {grade} is fully pre-generated. All lessons and tests serve from cache at zero token cost.
                    </div>
                  )}
                </>
              )}
            </div>
          );
        })}
      </section>

      {/* Doubt KB stats panel */}
      {dkbStats && dkbStats.total_entries > 0 && (
        <section className="premium-section">
          <div className="premium-header">
            <p className="eyebrow">Internal Performance Metric</p>
            <h3>🧠 Doubt Knowledge Base Stats</h3>
          </div>
          <div className="premium-grid premium-grid-3">
            <div className="premium-card">
              <strong>Total Q&A Pairs</strong>
              <h4>{dkbStats.total_entries?.toLocaleString()}</h4>
              <small>
                {dkbStats.prewarmed?.toLocaleString()} prewarmed
                &nbsp;+&nbsp;
                {dkbStats.llm_generated?.toLocaleString()} auto-generated
              </small>
            </div>
            <div className="premium-card">
              <strong>Total DB Hits</strong>
              <h4>{dkbStats.total_hits?.toLocaleString()}</h4>
              <small>Doubts served from DB at zero token cost</small>
            </div>
            <div className="premium-card">
              <strong>Estimated Savings</strong>
              <h4>${dkbStats.estimated_savings_usd?.toFixed(3)}</h4>
              <small>vs. always calling LLM for every doubt</small>
            </div>
          </div>
          <div className="info-box" style={{ marginTop: 12, fontSize: "0.82rem" }}>
            💡 Click <strong>🧠 Build Doubt KB</strong> on any grade to pre-generate 25 Q&A
            pairs per chapter. New student doubts that don't match are automatically added
            to the KB so it grows with use.
          </div>
        </section>
      )}

      {/* Chapter-by-chapter prewarm panel */}
      <section className="premium-section">
        <div className="premium-header">
          <p className="eyebrow">Token-Efficient Testing</p>
          <h3>🔬 Chapter-by-Chapter Prewarm</h3>
          <p>
            Test one chapter at a time (5 steps × gpt-4.1-nano ≈ $0.002) before
            committing to a full grade. Use this after uploading a new textbook chapter.
          </p>
        </div>

        <div className="premium-card" style={{ maxWidth: 580 }}>
          <div className="form-grid premium-rag-form-grid">
            <label>
              Grade
              <select
                value={chapterGrade}
                onChange={(e) => setChapterGrade(e.target.value)}
              >
                {ALL_GRADE_OPTIONS.map((g) => (
                  <option key={g} value={g}>{g}</option>
                ))}
              </select>
            </label>

            <label>
              Subject
              <select
                value={selectedSubject}
                onChange={(e) => {
                  setSelectedSubject(e.target.value);
                  const first = chapterList.find((c) => c.subject === e.target.value);
                  setSelectedChapter(first ? first.chapter : "");
                }}
                disabled={chapterListLoading || chapterList.length === 0}
              >
                {[...new Set(chapterList.map((c) => c.subject))].map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </label>
          </div>

          <label style={{ display: "block", marginTop: 12 }}>
            Chapter
            <select
              value={selectedChapter}
              onChange={(e) => setSelectedChapter(e.target.value)}
              disabled={chapterListLoading || !selectedSubject}
              style={{ width: "100%", marginTop: 4 }}
            >
              {chapterList
                .filter((c) => c.subject === selectedSubject)
                .map((c) => (
                  <option key={c.chapter} value={c.chapter}>{c.chapter}</option>
                ))}
            </select>
          </label>

          {chapterListLoading && <p style={{ fontSize: "0.85rem", color: "#888" }}>Loading chapters…</p>}

          {chapterList.length === 0 && !chapterListLoading && (
            <p style={{ fontSize: "0.85rem", color: "#888" }}>
              No RAG content uploaded for {chapterGrade} yet.
            </p>
          )}

          <div style={{ display: "flex", gap: 10, marginTop: 16, flexWrap: "wrap" }}>
            <button
              className="primary-btn"
              onClick={handleChapterPrewarm}
              disabled={chapterRunning || chapterQBankRunning || !selectedChapter || chapterListLoading}
            >
              {chapterRunning ? "⏳ Prewarm running…" : "🎯 Prewarm Lessons (4-6 steps)"}
            </button>

            <button
              className="secondary-btn"
              onClick={handleChapterQuestionBankBuild}
              disabled={chapterQBankRunning || chapterRunning || !selectedChapter || chapterListLoading}
              title="Generates 60 RAG-grounded questions (20 Easy + 20 Medium + 20 Hard)"
            >
              {chapterQBankRunning ? "⏳ Building questions…" : "🎯 Build 60 Questions"}
            </button>
          </div>

          {chapterMessage && (
            <div className="info-box" style={{ marginTop: 12 }}>{chapterMessage}</div>
          )}
          {chapterError && (
            <div className="error-box" style={{ marginTop: 12 }}>{chapterError}</div>
          )}
        </div>
      </section>

      {/* ── Clear Chapter Cache ─────────────────────────────────────────── */}
      <ClearChapterCacheSection user={user} chapterList={chapterList} chapterListLoading={chapterListLoading} />

      <section className="premium-section">
        <div className="premium-header">
          <h3>📋 Pre-Generation Cost Estimates</h3>
          <p>Estimated one-time cost to pre-warm lessons and question bank for all grades.</p>
        </div>

        {/* Model + embedding selectors */}
        <div className="form-grid premium-rag-form-grid" style={{ maxWidth: 620, marginBottom: 20 }}>
          <label>
            Prewarm Model
            <select
              value={prewarmModel}
              onChange={(e) => setPrewarmModel(e.target.value)}
            >
              {PREWARM_MODEL_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </label>
          <label>
            Embedding Model
            <input
              type="text"
              value={EMBEDDING_MODEL}
              readOnly
              style={{ background: "var(--surface2, #f5f5f5)", cursor: "not-allowed", color: "#888" }}
            />
            <small style={{ display: "block", marginTop: 4, color: "#888" }}>
              Fixed — used for all RAG / vector indexing. Changing requires re-uploading all documents.
            </small>
          </label>
        </div>

        {/* Dynamic cost cards */}
        {(() => {
          const c = PREWARM_COST[prewarmModel] || PREWARM_COST["gpt-4.1-nano"];
          const allGradesLessons  = (c.lessons  * 10).toFixed(0);
          const allGradesQuestions= (c.questions * 10).toFixed(0);
          return (
            <div className="premium-grid premium-grid-3">
              <div className="premium-card">
                <strong>Grade 9 — Lessons</strong>
                <p>~750 steps × ({c.inputPer1K}/1K in + {c.outputPer1K}/1K out)</p>
                <h4>~${c.lessons.toFixed(2)}</h4>
                <small>~{c.lessonMin} min to generate</small>
              </div>
              <div className="premium-card">
                <strong>Grade 9 — Question Bank</strong>
                <p>~13,500 questions × ({c.inputPer1K}/1K in + {c.outputPer1K}/1K out)</p>
                <h4>~${c.questions.toFixed(2)}</h4>
                <small>~{c.questionMin} min to generate</small>
              </div>
              <div className="premium-card">
                <strong>All 10 Grades (estimate)</strong>
                <p>Lessons ~${allGradesLessons} + Q-Bank ~${allGradesQuestions}</p>
                <h4>~${(Number(allGradesLessons) + Number(allGradesQuestions)).toFixed(0)} total</h4>
                <small>$0 / request after — only Ask Doubt uses tokens</small>
              </div>
            </div>
          );
        })()}

        <div className="info-box" style={{ marginTop: 16, fontSize: "0.85rem" }}>
          💡 <strong>Tip:</strong> Use <strong>gpt-4.1-nano</strong> for the lowest cost prewarm.
          Switch to <strong>gpt-4.1-mini</strong> or <strong>gpt-4.1</strong> only if you need
          richer lesson content or HOTS-quality questions in the pre-generated cache.
        </div>
      </section>

      {/* ── Exam Prep Question Bank ── */}
      <ExamPrepQBSection user={user} />
    </div>
  );
}

// ── Clear Chapter Cache Section ───────────────────────────────────────────────

function ClearChapterCacheSection({ user }) {
  const [clearGrade, setClearGrade] = useState("Grade 5");
  const [clearChapters, setClearChapters] = useState([]);
  const [clearLoading, setClearLoading] = useState(false);
  const [clearSubject, setClearSubject] = useState("");
  const [clearChapter, setClearChapter] = useState("");
  const [clearing, setClearing] = useState(false);
  const [clearMsg, setClearMsg] = useState("");
  const [clearErr, setClearErr] = useState("");

  async function loadClearChapters(grade) {
    setClearLoading(true);
    setClearChapters([]);
    setClearSubject("");
    setClearChapter("");
    setClearMsg("");
    setClearErr("");
    try {
      const result = await getChaptersForGrade(gradeToSlug(grade), user.accessToken);
      const chapters = result.chapters || [];
      setClearChapters(chapters);
      if (chapters.length > 0) {
        setClearSubject(chapters[0].subject);
        setClearChapter(chapters[0].chapter);
      }
    } catch {
      // fail silently — section is optional
    } finally {
      setClearLoading(false);
    }
  }

  useEffect(() => {
    if (user?.accessToken && clearGrade) {
      loadClearChapters(clearGrade);
    }
  }, [clearGrade, user?.accessToken]); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleClearChapterCache() {
    if (!clearSubject || !clearChapter) return;
    if (!window.confirm(
      `Mark lesson cache stale for:\n\nGrade: ${clearGrade}\nSubject: ${clearSubject}\nChapter: ${clearChapter}\n\nThe next lesson request will regenerate fresh from the uploaded RAG content.\nThis does NOT delete — rows are marked stale and can be re-generated.`
    )) return;

    setClearing(true);
    setClearMsg("");
    setClearErr("");
    try {
      const result = await clearChapterCache(
        { grade: clearGrade, subject: clearSubject, chapter: clearChapter },
        user.accessToken
      );
      setClearMsg(result.message || `Cache cleared for ${clearChapter}.`);
    } catch (err) {
      setClearErr(err.message || "Failed to clear chapter cache.");
    } finally {
      setClearing(false);
    }
  }

  return (
    <section className="premium-section">
      <div className="premium-header">
        <p className="eyebrow">Fix Stale or Incorrect Lessons</p>
        <h3>🧹 Clear Lesson Cache — Selected Chapter</h3>
        <p>
          Use this after renaming a chapter, updating its RAG content, or when a
          lesson shows wrong or outdated content. Marks the cached lesson steps
          as stale so the next request regenerates fresh from the uploaded textbook.
          Works across all grades and subjects. Does not affect other chapters.
        </p>
      </div>

      <div className="premium-card" style={{ maxWidth: 580 }}>
        <div className="form-grid premium-rag-form-grid">
          <label>
            Grade
            <select
              value={clearGrade}
              onChange={(e) => setClearGrade(e.target.value)}
            >
              {ALL_GRADE_OPTIONS.map((g) => (
                <option key={g} value={g}>{g}</option>
              ))}
            </select>
          </label>

          <label>
            Subject
            <select
              value={clearSubject}
              onChange={(e) => {
                setClearSubject(e.target.value);
                const first = clearChapters.find((c) => c.subject === e.target.value);
                setClearChapter(first ? first.chapter : "");
              }}
              disabled={clearLoading || clearChapters.length === 0}
            >
              {[...new Set(clearChapters.map((c) => c.subject))].map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </label>
        </div>

        <label style={{ display: "block", marginTop: 12 }}>
          Chapter
          <select
            value={clearChapter}
            onChange={(e) => setClearChapter(e.target.value)}
            disabled={clearLoading || !clearSubject}
            style={{ width: "100%", marginTop: 4 }}
          >
            {clearChapters
              .filter((c) => c.subject === clearSubject)
              .map((c) => (
                <option key={c.chapter} value={c.chapter}>{c.chapter}</option>
              ))}
          </select>
        </label>

        {clearLoading && (
          <p style={{ fontSize: "0.85rem", color: "#888", marginTop: 8 }}>Loading chapters…</p>
        )}
        {clearChapters.length === 0 && !clearLoading && (
          <p style={{ fontSize: "0.85rem", color: "#888", marginTop: 8 }}>
            No RAG content uploaded for {clearGrade} yet.
          </p>
        )}

        <div style={{ marginTop: 16 }}>
          <button
            className="secondary-btn"
            onClick={handleClearChapterCache}
            disabled={clearing || clearLoading || !clearChapter}
            style={{ background: "#fef2f2", color: "#991b1b", border: "1px solid #fecaca" }}
          >
            {clearing ? "⏳ Clearing cache…" : "🧹 Clear Cache for This Chapter"}
          </button>
        </div>

        {clearMsg && (
          <div className="info-box" style={{ marginTop: 12 }}>{clearMsg}</div>
        )}
        {clearErr && (
          <div className="error-box" style={{ marginTop: 12 }}>{clearErr}</div>
        )}

        <div style={{ marginTop: 12, fontSize: "0.8rem", color: "#888", lineHeight: 1.5 }}>
          💡 After clearing, go to the lesson page and click <strong>Generate Lesson</strong> to
          regenerate with the latest uploaded content. The old cached content is kept as
          stale (not deleted) and can be recovered if needed.
        </div>
      </div>
    </section>
  );
}

// ── Exam Prep Question Bank Section ───────────────────────────────────────────

const EXAM_OPTIONS = [
  { value: "jee_main",  label: "JEE Main",   icon: "📐", color: "#6366f1" },
  { value: "neet_ug",   label: "NEET UG",    icon: "🔬", color: "#10b981" },
  { value: "cuet_ug",   label: "CUET UG",    icon: "🏛️", color: "#f59e0b" },
  { value: "sat",       label: "SAT",        icon: "🎓", color: "#3b82f6" },
  { value: "ielts",     label: "IELTS",      icon: "🌐", color: "#8b5cf6" },
  { value: "toefl_ibt", label: "TOEFL iBT",  icon: "📡", color: "#06b6d4" },
];

const EXAM_SUBJECTS = {
  jee_main: ["Physics", "Chemistry", "Mathematics"],
  neet_ug:  ["Physics", "Chemistry", "Biology"],
  cuet_ug:  [
    // Language & General
    "English", "General Test",
    // Science Domain
    "Physics (Domain)", "Chemistry (Domain)", "Mathematics (Domain)", "Biology (Domain)",
    // Humanities Domain
    "History", "Geography", "Political Science", "Economics",
    "Accountancy", "Business Studies", "Sociology", "Psychology", "Legal Studies",
  ],
  sat:       ["Reading & Writing", "Mathematics"],
  ielts:     ["Listening", "Reading", "Vocabulary & Grammar"],
  toefl_ibt: ["Reading", "Listening", "Integrated Skills"],
};

const EXAM_GRADE_OPTIONS = ["Grade 11", "Grade 12", "Both"];

function ExamPrepQBSection({ user }) {
  const [qbStatus, setQbStatus] = useState(null);
  const [qbLoading, setQbLoading] = useState(true);
  const [qbMsg, setQbMsg] = useState("");
  const [qbErr, setQbErr] = useState("");
  const [prewarmRunning, setPrewarmRunning] = useState(false);
  const [migrationRunning, setMigrationRunning] = useState(false);
  const [migrationResult, setMigrationResult] = useState(null);
  // Incremented after a successful paste-import to auto-refresh the review panel
  const [reviewRefreshKey, setReviewRefreshKey] = useState(0);

  // Form state
  const [selExam, setSelExam] = useState("jee_main");
  const [selGrade, setSelGrade] = useState("Grade 12");
  const [selSubject, setSelSubject] = useState("Physics");
  const [selTopic, setSelTopic] = useState("");
  const [questionCount, setQuestionCount] = useState(10);
  const [publishMode, setPublishMode] = useState("draft");
  const [diffEasy, setDiffEasy] = useState(30);
  const [diffMed, setDiffMed] = useState(50);
  const [diffHard, setDiffHard] = useState(20);
  const [lastJob, setLastJob] = useState(null);

  // Reset subject when exam changes
  useEffect(() => {
    setSelSubject(EXAM_SUBJECTS[selExam]?.[0] || "Physics");
  }, [selExam]);

  async function loadQBStatus() {
    setQbLoading(true);
    try {
      const data = await adminGetQBStatus(user.accessToken, null);
      setQbStatus(data);
    } catch { /* non-critical */ }
    finally { setQbLoading(false); }
  }

  useEffect(() => { loadQBStatus(); }, [user.accessToken]); // eslint-disable-line

  async function handlePrewarm() {
    if (!window.confirm(
      `Generate ${questionCount} ${selExam.toUpperCase().replace("_", " ")} questions for ${selGrade} — ${selSubject}${selTopic ? ` / ${selTopic}` : ""}?\n\nQuestions will be saved as "${publishMode}" and can be reviewed before publishing.`
    )) return;

    setPrewarmRunning(true);
    setQbMsg("");
    setQbErr("");
    try {
      const gradeParam = selGrade === "Both" ? "Grade 12" : selGrade;
      const result = await adminPrewarm(user.accessToken, {
        exam_type: selExam,
        grade: gradeParam,
        subject: selSubject || null,
        topic: selTopic || null,
        question_count: questionCount,
        publish_mode: publishMode,
        difficulty_mix: {
          easy: diffEasy / 100,
          medium: diffMed / 100,
          hard: diffHard / 100,
        },
        run_now: true,
      });
      setLastJob(result.result || result.job || {});
      setQbMsg(
        `✅ Generated ${result.result?.questions_generated || 0} questions ` +
        `(${result.result?.questions_validated || 0} valid, ` +
        `${result.result?.questions_published || 0} published). ` +
        `Saved as ${publishMode}.`
      );
      loadQBStatus();
    } catch (e) {
      setQbErr(e.message || "Prewarm failed.");
    } finally {
      setPrewarmRunning(false);
    }
  }

  // Difficulty mix normalizer
  function normalizeDiff(easy, med, hard) {
    const total = easy + med + hard;
    return total === 100;
  }
  const diffValid = normalizeDiff(diffEasy, diffMed, diffHard);

  return (
    <section className="premium-section">
      <div className="premium-header">
        <p className="eyebrow">Grade 11 & 12 — Competitive Exams</p>
        <h3>🎯 Exam Prep Question Bank (JEE / NEET / CUET / SAT / IELTS / TOEFL)</h3>
        <p>
          Generate AI-powered MCQ questions for JEE Main, NEET UG, CUET UG, SAT, IELTS, and TOEFL iBT.
          Questions are saved as <em>draft</em> by default — review and publish them
          from the Exam Prep Center page.
        </p>
      </div>

      {/* DB Migration setup */}
      <div style={{ background: "rgba(245,158,11,.06)", border: "1px solid rgba(245,158,11,.25)", borderRadius: 10, padding: "12px 16px", marginBottom: 16, display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 10 }}>
        <div>
          <div style={{ fontSize: ".82rem", fontWeight: 700, color: "#fbbf24", marginBottom: 2 }}>
            ⚙️ First-time Setup — Run Migration
          </div>
          <div style={{ fontSize: ".72rem", color: "var(--muted,#94a3b8)" }}>
            Creates the exam prep DB tables. Run once before generating questions. Safe to re-run.
          </div>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexShrink: 0 }}>
          {migrationResult && (
            <span style={{ fontSize: ".72rem", color: migrationResult.success ? "#22c55e" : "#f87171", fontWeight: 600 }}>
              {migrationResult.success ? "✅ Tables ready" : "⚠️ Run SQL manually"}
            </span>
          )}
          <button
            onClick={async () => {
              setMigrationRunning(true);
              setMigrationResult(null);
              try {
                const result = await runExamPrepMigration(user.accessToken);
                setMigrationResult(result);
                if (result.success) loadQBStatus();
              } catch (e) {
                setMigrationResult({ success: false, message: e.message });
              } finally { setMigrationRunning(false); }
            }}
            disabled={migrationRunning}
            style={{ padding: "7px 16px", background: migrationRunning ? "#6b7280" : "#f59e0b", border: "none", borderRadius: 7, color: "#fff", fontWeight: 700, fontSize: ".78rem", cursor: "pointer", fontFamily: "inherit" }}
          >
            {migrationRunning ? "⏳ Checking…" : "🗄️ Run Migration"}
          </button>
        </div>
      </div>
      {migrationResult && !migrationResult.success && migrationResult.missing_tables?.length > 0 && (
        <div className="error-box" style={{ fontSize: ".78rem", marginBottom: 12 }}>
          Missing tables: <strong>{migrationResult.missing_tables?.join(", ")}</strong><br />
          Run the SQL manually in your Supabase dashboard:<br />
          <code style={{ fontSize: ".7rem", background: "rgba(0,0,0,.2)", padding: "2px 6px", borderRadius: 4 }}>
            backend/migrations/20260707_exam_prep_center.sql
          </code>
        </div>
      )}

      {/* Status overview */}
      {!qbLoading && qbStatus?.stats && (
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 20 }}>
          {EXAM_OPTIONS.map(exam => {
            const examStats = qbStatus.stats[exam.value] || {};
            const total = Object.values(examStats).reduce((s, v) => s + (v.total || 0), 0);
            const published = Object.values(examStats).reduce((s, v) => s + (v.published || 0), 0);
            const draft = total - published;
            return (
              <div key={exam.value} style={{ background: "var(--panel,#1e293b)", border: `1px solid ${exam.color}33`, borderRadius: 10, padding: "12px 16px", minWidth: 200 }}>
                <div style={{ fontSize: ".8rem", fontWeight: 700, marginBottom: 6, display: "flex", alignItems: "center", gap: 6 }}>
                  <span>{exam.icon}</span>
                  <span style={{ color: exam.color }}>{exam.label}</span>
                </div>
                <div style={{ display: "flex", gap: 12 }}>
                  <div>
                    <div style={{ fontSize: "1.3rem", fontWeight: 800 }}>{total}</div>
                    <div style={{ fontSize: ".62rem", color: "var(--muted,#64748b)" }}>Total Qs</div>
                  </div>
                  <div>
                    <div style={{ fontSize: "1.3rem", fontWeight: 800, color: "#22c55e" }}>{published}</div>
                    <div style={{ fontSize: ".62rem", color: "var(--muted,#64748b)" }}>Published</div>
                  </div>
                  <div>
                    <div style={{ fontSize: "1.3rem", fontWeight: 800, color: "#f59e0b" }}>{draft}</div>
                    <div style={{ fontSize: ".62rem", color: "var(--muted,#64748b)" }}>Draft</div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Prewarm form */}
      <div className="premium-card" style={{ maxWidth: 680 }}>
        <div style={{ fontWeight: 700, fontSize: ".9rem", marginBottom: 16 }}>Generate Questions</div>

        {/* Exam / Grade / Subject row */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12, marginBottom: 12 }}>
          <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: ".82rem" }}>
            Exam
            <select value={selExam} onChange={e => setSelExam(e.target.value)}
              style={{ padding: "7px 10px", borderRadius: 7, border: "1px solid var(--border,#e2e8f0)", background: "var(--surface,#f8fafc)", color: "var(--text,#1e293b)", fontFamily: "inherit" }}>
              {EXAM_OPTIONS.map(e => <option key={e.value} value={e.value}>{e.icon} {e.label}</option>)}
            </select>
          </label>
          <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: ".82rem" }}>
            Grade
            <select value={selGrade} onChange={e => setSelGrade(e.target.value)}
              style={{ padding: "7px 10px", borderRadius: 7, border: "1px solid var(--border,#e2e8f0)", background: "var(--surface,#f8fafc)", color: "var(--text,#1e293b)", fontFamily: "inherit" }}>
              {EXAM_GRADE_OPTIONS.map(g => <option key={g} value={g}>{g}</option>)}
            </select>
          </label>
          <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: ".82rem" }}>
            Subject
            <select value={selSubject} onChange={e => setSelSubject(e.target.value)}
              style={{ padding: "7px 10px", borderRadius: 7, border: "1px solid var(--border,#e2e8f0)", background: "var(--surface,#f8fafc)", color: "var(--text,#1e293b)", fontFamily: "inherit" }}>
              {(EXAM_SUBJECTS[selExam] || []).map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </label>
        </div>

        {/* Topic (optional) */}
        <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: ".82rem", marginBottom: 12 }}>
          Topic <span style={{ color: "var(--muted,#64748b)", fontWeight: 400 }}>(optional — leave blank for full subject)</span>
          <input value={selTopic} onChange={e => setSelTopic(e.target.value)}
            placeholder="e.g. Kinematics, Electrochemistry, Integration…"
            style={{ padding: "7px 10px", borderRadius: 7, border: "1px solid var(--border,#e2e8f0)", background: "var(--surface,#f8fafc)", color: "var(--text,#1e293b)", fontFamily: "inherit" }} />
        </label>

        {/* Question count + publish mode */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 12 }}>
          <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: ".82rem" }}>
            Question Count (1–50)
            <input type="number" min={1} max={50} value={questionCount} onChange={e => setQuestionCount(Number(e.target.value))}
              style={{ padding: "7px 10px", borderRadius: 7, border: "1px solid var(--border,#e2e8f0)", background: "var(--surface,#f8fafc)", color: "var(--text,#1e293b)", fontFamily: "inherit" }} />
          </label>
          <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: ".82rem" }}>
            Publish Mode
            <select value={publishMode} onChange={e => setPublishMode(e.target.value)}
              style={{ padding: "7px 10px", borderRadius: 7, border: "1px solid var(--border,#e2e8f0)", background: "var(--surface,#f8fafc)", color: "var(--text,#1e293b)", fontFamily: "inherit" }}>
              <option value="draft">Draft only (review before publishing)</option>
              <option value="auto_publish">Auto-publish if validation passes</option>
            </select>
          </label>
        </div>

        {/* Difficulty mix */}
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: ".82rem", fontWeight: 600, marginBottom: 8 }}>
            Difficulty Mix
            {!diffValid && <span style={{ color: "#f87171", marginLeft: 8, fontSize: ".75rem", fontWeight: 400 }}>⚠️ Must total 100%</span>}
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
            {[
              { label: "Easy %", val: diffEasy, set: setDiffEasy, color: "#22c55e" },
              { label: "Medium %", val: diffMed, set: setDiffMed, color: "#f59e0b" },
              { label: "Hard %", val: diffHard, set: setDiffHard, color: "#ef4444" },
            ].map(d => (
              <label key={d.label} style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: ".78rem" }}>
                <span style={{ color: d.color, fontWeight: 700 }}>{d.label}</span>
                <input type="number" min={0} max={100} value={d.val}
                  onChange={e => d.set(Number(e.target.value))}
                  style={{ padding: "6px 10px", borderRadius: 7, border: `1px solid ${d.color}44`, background: "var(--surface,#f8fafc)", color: "var(--text,#1e293b)", fontFamily: "inherit" }} />
              </label>
            ))}
          </div>
          <div style={{ fontSize: ".72rem", color: "var(--muted,#64748b)", marginTop: 4 }}>
            Total: {diffEasy + diffMed + diffHard}% (must equal 100%)
          </div>
        </div>

        {/* Generate button */}
        <button
          onClick={handlePrewarm}
          disabled={prewarmRunning || !diffValid || questionCount < 1 || questionCount > 50}
          style={{
            width: "100%", padding: "11px 20px",
            background: prewarmRunning ? "#6b7280" : "linear-gradient(135deg,#6366f1,#8b5cf6)",
            border: "none", borderRadius: 8, color: "#fff",
            fontWeight: 700, fontSize: ".88rem", cursor: "pointer",
            fontFamily: "inherit", opacity: (!diffValid || questionCount < 1) ? .5 : 1,
          }}
        >
          {prewarmRunning
            ? "⏳ Generating… (this may take 30–60 seconds)"
            : `🚀 Generate ${questionCount} Questions — ${EXAM_OPTIONS.find(e => e.value === selExam)?.label}`}
        </button>

        {qbMsg && <div className="info-box" style={{ marginTop: 12, fontSize: ".82rem" }}>{qbMsg}</div>}
        {qbErr && <div className="error-box" style={{ marginTop: 12, fontSize: ".82rem" }}>{qbErr}</div>}

        {/* Last job result */}
        {lastJob?.questions_generated > 0 && (
          <div style={{ marginTop: 12, padding: "10px 14px", background: "rgba(99,102,241,.08)", border: "1px solid rgba(99,102,241,.2)", borderRadius: 8, fontSize: ".78rem" }}>
            <div style={{ fontWeight: 700, color: "#a5b4fc", marginBottom: 4 }}>Last Job Result</div>
            <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
              <span>📥 Generated: <strong>{lastJob.questions_generated}</strong></span>
              <span>✅ Valid: <strong style={{ color: "#22c55e" }}>{lastJob.questions_validated}</strong></span>
              <span>📤 Published: <strong style={{ color: "#6366f1" }}>{lastJob.questions_published}</strong></span>
              {lastJob.errors?.length > 0 && (
                <span style={{ color: "#f87171" }}>⚠️ Errors: {lastJob.errors.length}</span>
              )}
            </div>
          </div>
        )}
      </div>

      <div className="info-box" style={{ marginTop: 16, fontSize: ".82rem" }}>
        💡 <strong>Tip:</strong> Start with 10 questions per subject/topic in <em>draft</em> mode.
        Review them below, then publish individually or use <em>Publish All Valid</em>.
        Each 10-question batch costs ~$0.001–0.01 depending on the AI provider.
      </div>

      {/* Paste & Import from ChatGPT */}
      <PasteImportSection user={user} onImportSuccess={() => setReviewRefreshKey(k => k + 1)} />

      {/* Question Review Panel — refreshKey increments after successful import */}
      <QuestionReviewPanel user={user} refreshKey={reviewRefreshKey} />
    </section>
  );
}

// ── JSON sanitizer for ChatGPT / Custom GPT output ───────────────────────────
// ChatGPT commonly produces JSON with:
//   1. Unicode "smart quotes"  "  "  (U+201C / U+201D) instead of  "
//   2. Unicode smart apostrophes  '  '  (U+2018 / U+2019)
//   3. Trailing commas before } or ]  (invalid JSON)
//   4. Markdown code fences  ```json  ...  ```
//   5. Non-breaking spaces (U+00A0) and zero-width characters
//   6. Byte-order mark (U+FEFF) at start
//   7. Escaped Unicode sequences that need normalisation

function sanitizeJsonFromChatGPT(raw) {
  let s = raw;

  // 1. Strip BOM
  s = s.replace(/^\uFEFF/, "");

  // 2. Strip markdown code fences (```json ... ``` or ``` ... ```)
  s = s.replace(/^```(?:json)?\s*/i, "").replace(/\s*```\s*$/, "");

  // 3. Replace Unicode "smart" double quotes with escaped ASCII double quotes.
  //    These appear INSIDE JSON string values (e.g. quoting passage text in SAT options:
  //    "A": ""the expansion..."" where inner "" are U+201C/U+201D smart quotes).
  //    Replacing with \" (escaped quote) produces valid JSON: "A": "\"the expansion...\""
  //    U+201C  "  (left double quotation mark)
  //    U+201D  "  (right double quotation mark)
  //    U+201E  „  (double low-9 quotation mark — German style)
  //    U+00AB  «  and  U+00BB  »  (guillemets)
  s = s.replace(/[\u201C\u201D\u201E\u00AB\u00BB]/g, '\\"');

  // 4. Replace Unicode smart single quotes / apostrophes with straight ASCII
  //    U+2018  '  (left single quotation mark)
  //    U+2019  '  (right single quotation mark — also used as apostrophe)
  //    U+201A  ‚  (single low-9 quotation mark)
  //    U+2039  ‹  and  U+203A  ›  (single angle quotation marks)
  s = s.replace(/[\u2018\u2019\u201A\u2039\u203A]/g, "'");

  // 5. Replace non-breaking space (U+00A0) and en/em dashes used as hyphens
  s = s.replace(/\u00A0/g, " ");
  s = s.replace(/[\u2013\u2014]/g, "-"); // en-dash / em-dash → hyphen

  // 6. Remove zero-width characters individually (splitting avoids ESLint no-misleading-character-class
  //    warning — \u200D (ZWJ) in a character class is flagged as a "joined character sequence")
  s = s.replace(/\u200B/g, ""); // zero-width space
  s = s.replace(/\u200C/g, ""); // zero-width non-joiner
  s = s.replace(/\u200D/g, ""); // zero-width joiner (ZWJ)
  s = s.replace(/\uFEFF/g, ""); // BOM / zero-width no-break space

  // 6b. Fix ASCII double quotes used as inner content quotes inside JSON string values.
  //     This handles the ChatGPT SAT pattern where passage excerpts are wrapped in
  //     ASCII double quotes: "A":""the expansion..."" (all quotes are ASCII)
  //     The JSON parser sees: empty string "" + unexpected text → parse error.
  //     Fix: convert to "A":"\"the expansion...\"" (escaped inner quotes).
  //     The regex is deliberately narrow: only matches when content between inner
  //     quotes contains NO JSON structural characters (no " { } [ ] ,) to avoid
  //     corrupting legitimate empty strings "" or valid JSON constructs.
  s = s.replace(/:\s*""([^"{}[\],\r\n]+)""/g, ': "\\"$1\\""');

  // 7. Fix unescaped literal newlines / carriage returns / tabs inside JSON string values.
  //    ChatGPT sometimes writes multi-line strings with actual newlines instead of \n.
  //    Strategy: find each "..." string token and escape any bare control characters inside it.
  //    The regex matches a JSON string: opening " then any mix of escaped chars or non-quote chars.
  s = s.replace(/"(?:[^"\\]|\\.)*"/g, (match) => {
    // Inside a matched string token, replace bare control characters with their JSON escapes.
    // We skip already-escaped sequences (the regex already consumed them as \\X).
    return match
      .replace(/\r\n/g, "\\n")  // CRLF → \n
      .replace(/\r/g,   "\\r")  // bare CR → \r
      .replace(/\n/g,   "\\n")  // bare LF → \n
      .replace(/\t/g,   "\\t"); // bare TAB → \t (sometimes causes issues)
  });

  // 8. Remove trailing commas before } or ] (common ChatGPT error)
  //    Handles: { "key": "val", }  and  [1, 2, 3,]
  s = s.replace(/,\s*([}\]])/g, "$1");

  // 9. Extract JSON array/object if surrounded by extra text
  //    Find first [ or { and last ] or }
  const firstBracket = s.search(/[{[]/);
  const lastBracket = Math.max(s.lastIndexOf("}"), s.lastIndexOf("]"));
  if (firstBracket !== -1 && lastBracket > firstBracket) {
    s = s.slice(firstBracket, lastBracket + 1);
  }

  return s.trim();
}

// ── Paste & Import from Custom GPT / ChatGPT ───────────────────────────────────

function PasteImportSection({ user, onImportSuccess }) {
  const [jsonText, setJsonText] = useState("");
  const [importing, setImporting] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [showReport, setShowReport] = useState(false);

  async function handleImport() {
    setError("");
    setResult(null);
    setShowReport(false);

    // Sanitize and parse JSON — auto-fix common ChatGPT formatting issues
    let questions;
    let sanitized = sanitizeJsonFromChatGPT(jsonText);
    try {
      const parsed = JSON.parse(sanitized);
      questions = Array.isArray(parsed) ? parsed : [parsed];
    } catch (firstErr) {
      // Second attempt: try the raw trimmed text in case sanitizer over-stripped
      try {
        const parsed = JSON.parse(jsonText.trim());
        questions = Array.isArray(parsed) ? parsed : [parsed];
      } catch {
        setError(
          `❌ Invalid JSON — could not auto-fix. Common causes:\n` +
          `• Smart/curly quotes inside values (auto-fixed normally)\n` +
          `• Trailing comma after last item in array or object\n` +
          `• Missing comma between items\n` +
          `• Unescaped newline inside a string value\n\n` +
          `Error detail: ${firstErr.message}`
        );
        return;
      }
    }

    if (questions.length === 0) {
      setError("❌ No questions found in the JSON.");
      return;
    }
    if (questions.length > 100) {
      setError(`❌ Too many questions (${questions.length}). Maximum is 100 per import.`);
      return;
    }

    setImporting(true);
    try {
      const data = await adminImportBulk(user.accessToken, questions);
      setResult(data);
      if (data.imported > 0) {
        setJsonText(""); // clear on success
        if (onImportSuccess) onImportSuccess(); // trigger review panel refresh
      }
    } catch (e) {
      setError("❌ Import failed: " + (e.message || "unknown error"));
    } finally {
      setImporting(false);
    }
  }

  const statusIcon = (status) => {
    if (status === "imported") return "✅";
    if (status === "imported_with_warning") return "⚠️";
    if (status === "skipped_duplicate") return "🔁";
    if (status === "skipped_invalid") return "❌";
    if (status === "error") return "💥";
    return "❓";
  };
  const statusColor = (status) => {
    if (status === "imported") return "#22c55e";
    if (status === "imported_with_warning") return "#f59e0b";
    if (status === "skipped_duplicate") return "#64748b";
    if (status === "skipped_invalid") return "#ef4444";
    return "#f87171";
  };

  return (
    <div style={{ marginTop: 24, padding: "20px", background: "rgba(99,102,241,.04)", border: "1px solid rgba(99,102,241,.2)", borderRadius: 12 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
        <span style={{ fontSize: "1.3rem" }}>📥</span>
        <div>
          <div style={{ fontWeight: 800, fontSize: ".95rem" }}>Paste & Import from ChatGPT / Custom GPT</div>
          <div style={{ fontSize: ".75rem", color: "var(--muted,#64748b)" }}>
            Generate questions using your Custom GPT, copy the JSON output, paste below, and import directly into the question bank.
          </div>
        </div>
      </div>

      <textarea
        value={jsonText}
        onChange={e => { setJsonText(e.target.value); setError(""); setResult(null); }}
        placeholder={`Paste JSON array from ChatGPT here…\n\nExample:\n[\n  {\n    "exam_type": "jee_main",\n    "grade": "Grade 12",\n    "subject": "Physics",\n    "chapter": "Current Electricity",\n    "topic": "Kirchhoff's Laws",\n    "question_text": "At a junction...",\n    "options": {"A": "2 A", "B": "4 A", "C": "8 A", "D": "12 A"},\n    "correct_option": "B",\n    "detailed_explanation": "Step 1: ...",\n    "difficulty": "easy",\n    "marks": 4,\n    "negative_marks": 1,\n    "ncert_reference": "NCERT Class 12 Physics, Chapter 3",\n    "formula_used": "KCL",\n    "source_type": "llm_generated",\n    "status": "draft"\n  }\n]`}
        rows={12}
        style={{
          width: "100%", boxSizing: "border-box",
          padding: "12px 14px", borderRadius: 8,
          border: "1.5px solid rgba(99,102,241,.3)",
          background: "var(--surface,#f8fafc)", color: "var(--text,#1e293b)",
          fontFamily: "monospace", fontSize: ".78rem", lineHeight: 1.5,
          resize: "vertical",
        }}
      />

      {/* Character count + question count preview */}
      {jsonText.trim() && (
        <div style={{ fontSize: ".7rem", color: "var(--muted,#64748b)", marginTop: 4, display: "flex", gap: 12 }}>
          <span>{jsonText.length.toLocaleString()} chars</span>
          {(() => {
            try {
              const sanitized = sanitizeJsonFromChatGPT(jsonText);
              const p = JSON.parse(sanitized);
              const count = Array.isArray(p) ? p.length : 1;
              return (
                <>
                  <span style={{ color: count > 100 ? "#f87171" : "#22c55e" }}>{count} question{count !== 1 ? "s" : ""} detected</span>
                  {sanitized !== jsonText.trim() && (
                    <span style={{ color: "#f59e0b", fontSize: ".65rem" }}>⚡ Auto-fix applied (smart quotes/trailing commas removed)</span>
                  )}
                </>
              );
            } catch {
              return <span style={{ color: "#f87171" }}>⚠️ Invalid JSON — auto-fix could not repair (check for missing commas)</span>;
            }
          })()}
        </div>
      )}

      <div style={{ marginTop: 12, display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
        <button
          onClick={handleImport}
          disabled={importing || !jsonText.trim()}
          style={{
            padding: "10px 24px",
            background: importing ? "#6b7280" : "linear-gradient(135deg,#6366f1,#8b5cf6)",
            border: "none", borderRadius: 8, color: "#fff",
            fontWeight: 700, fontSize: ".88rem", cursor: "pointer",
            fontFamily: "inherit", opacity: !jsonText.trim() ? .5 : 1,
          }}
        >
          {importing ? "⏳ Validating & Importing…" : "📥 Validate & Import Questions"}
        </button>
        {jsonText.trim() && (
          <button
            onClick={() => { setJsonText(""); setError(""); setResult(null); }}
            style={{ padding: "10px 16px", background: "transparent", border: "1px solid rgba(239,68,68,.3)", borderRadius: 8, color: "#f87171", fontWeight: 600, fontSize: ".8rem", cursor: "pointer", fontFamily: "inherit" }}
          >
            🗑 Clear
          </button>
        )}
      </div>

      {error && (
        <div className="error-box" style={{ marginTop: 10, fontSize: ".82rem" }}>{error}</div>
      )}

      {/* Import result summary */}
      {result && (
        <div style={{ marginTop: 14, padding: "14px 16px", background: "var(--panel,rgba(0,0,0,.06))", border: "1px solid rgba(99,102,241,.2)", borderRadius: 10 }}>
          <div style={{ fontWeight: 700, fontSize: ".9rem", marginBottom: 10, color: "#a5b4fc" }}>
            Import Complete — {result.total_submitted} submitted
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(130px,1fr))", gap: 10, marginBottom: 12 }}>
            {[
              { label: "Imported", value: result.imported, color: "#22c55e", icon: "✅" },
              { label: "With Warnings", value: result.warnings || 0, color: "#f59e0b", icon: "⚠️" },
              { label: "Duplicates Skipped", value: result.skipped_duplicate, color: "#64748b", icon: "🔁" },
              { label: "Invalid Skipped", value: result.skipped_invalid, color: "#ef4444", icon: "❌" },
            ].map(s => (
              <div key={s.label} style={{ background: "var(--panel,#1e293b)", borderRadius: 8, padding: "10px 12px", textAlign: "center" }}>
                <div style={{ fontSize: "1.5rem", fontWeight: 800, color: s.color }}>{s.value}</div>
                <div style={{ fontSize: ".65rem", color: "var(--muted,#64748b)", marginTop: 2 }}>{s.icon} {s.label}</div>
              </div>
            ))}
          </div>

          {result.imported > 0 && (
            <div className="info-box" style={{ fontSize: ".78rem", marginBottom: 10 }}>
              ✅ {result.imported} question{result.imported !== 1 ? "s" : ""} saved as <strong>draft</strong>.
              Review them in the panel below and publish the ones that look correct.
            </div>
          )}

          {/* Per-question report */}
          {result.report?.length > 0 && (
            <div>
              <button
                onClick={() => setShowReport(v => !v)}
                style={{ padding: "5px 12px", background: "transparent", border: "1px solid rgba(99,102,241,.3)", borderRadius: 6, color: "#a5b4fc", fontWeight: 600, fontSize: ".75rem", cursor: "pointer", fontFamily: "inherit", marginBottom: 8 }}
              >
                {showReport ? "▲ Hide" : "▼ Show"} Detailed Report ({result.report.length} questions)
              </button>

              {showReport && (
                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  {result.report.map((item, i) => (
                    <div key={i} style={{
                      padding: "8px 12px", borderRadius: 7,
                      background: item.status === "imported" ? "rgba(34,197,94,.06)"
                        : item.status === "imported_with_warning" ? "rgba(245,158,11,.06)"
                        : "rgba(239,68,68,.06)",
                      border: `1px solid ${item.status === "imported" ? "rgba(34,197,94,.2)"
                        : item.status === "imported_with_warning" ? "rgba(245,158,11,.2)"
                        : "rgba(239,68,68,.2)"}`,
                    }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: item.issues?.length || item.warnings?.length ? 4 : 0 }}>
                        <span style={{ fontSize: ".75rem", fontWeight: 700, color: statusColor(item.status) }}>
                          {statusIcon(item.status)} Q{item.question_num}
                        </span>
                        <span style={{ fontSize: ".72rem", color: "#e2e8f0", flex: 1 }}>
                          {item.question_text}…
                        </span>
                      </div>
                      {item.issues?.map((issue, j) => (
                        <div key={j} style={{ fontSize: ".7rem", color: "#fca5a5", marginLeft: 20 }}>• {issue}</div>
                      ))}
                      {item.warnings?.map((w, j) => (
                        <div key={j} style={{ fontSize: ".7rem", color: "#fcd34d", marginLeft: 20 }}>• {w}</div>
                      ))}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Question Review & Publish Panel ───────────────────────────────────────────

const REVIEW_EXAM_OPTIONS = [
  { value: "jee_main",  label: "JEE Main",   color: "#6366f1" },
  { value: "neet_ug",   label: "NEET UG",    color: "#10b981" },
  { value: "cuet_ug",   label: "CUET UG",    color: "#f59e0b" },
  { value: "sat",       label: "SAT",        color: "#3b82f6" },
  { value: "ielts",     label: "IELTS",      color: "#8b5cf6" },
  { value: "toefl_ibt", label: "TOEFL iBT",  color: "#06b6d4" },
];
const REVIEW_STATUS_OPTIONS = ["draft", "published", "archived"];

function QuestionReviewPanel({ user, refreshKey }) {
  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filterExam, setFilterExam] = useState("jee_main");
  const [filterStatus, setFilterStatus] = useState("draft");
  const [filterSubject, setFilterSubject] = useState("");
  const [publishing, setPublishing] = useState({});
  const [msg, setMsg] = useState("");
  const [expanded, setExpanded] = useState(null);

  async function loadQuestions() {
    setLoading(true);
    setMsg("");
    try {
      const params = new URLSearchParams({ exam_type: filterExam, status: filterStatus, limit: 100 });
      if (filterSubject) params.set("subject", filterSubject);
      const res = await fetch(
        `${import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"}/api/admin/exam-prep/questions?${params}`,
        { headers: { "Content-Type": "application/json", Authorization: `Bearer ${user.accessToken}` } }
      );
      const data = await res.json().catch(() => ({}));
      setQuestions(data.questions || []);
    } catch (e) {
      setMsg("Failed to load questions: " + e.message);
    } finally { setLoading(false); }
  }

  // Re-load when filters change OR when refreshKey increments (after paste-import)
  useEffect(() => { loadQuestions(); }, [filterExam, filterStatus, filterSubject, refreshKey]); // eslint-disable-line

  async function handleAction(questionId, action) {
    setPublishing(prev => ({ ...prev, [questionId]: action }));
    try {
      const url = `${import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"}/api/admin/exam-prep/questions/${questionId}/${action}`;
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${user.accessToken}` },
      });
      const data = await res.json().catch(() => ({}));
      if (data.success) {
        setQuestions(prev => prev.filter(q => q.id !== questionId));
        setMsg(`✅ Question ${action === "publish" ? "published" : "archived"}.`);
      } else {
        setMsg(`❌ Failed: ${data.detail || "unknown error"}`);
      }
    } catch (e) {
      setMsg("❌ " + e.message);
    } finally {
      setPublishing(prev => ({ ...prev, [questionId]: null }));
    }
  }

  async function handlePublishAll() {
    if (!window.confirm(`Publish all ${questions.length} draft questions?`)) return;
    setMsg("Publishing…");
    let done = 0;
    for (const q of questions) {
      await handleAction(q.id, "publish");
      done++;
    }
    setMsg(`✅ Published ${done} questions.`);
    loadQuestions();
  }

  async function handleArchiveAll() {
    if (!window.confirm(`Archive all ${questions.length} ${filterStatus} questions? They will be hidden from students.`)) return;
    setMsg("Archiving…");
    let done = 0;
    for (const q of questions) {
      if (q.status !== "archived") {
        await handleAction(q.id, "archive");
        done++;
      }
    }
    setMsg(`🗑 Archived ${done} questions.`);
    loadQuestions();
  }

  const [copied, setCopied] = useState(false);

  function copyForReview() {
    if (!questions.length) return;
    const lines = [
      `You are an expert exam question reviewer. Please review the following ${questions.length} MCQ questions for a ${filterExam.toUpperCase().replace("_"," ")} exam.`,
      `For each question, evaluate:`,
      `1. Is the question text clear and unambiguous?`,
      `2. Are all 4 options distinct and plausible?`,
      `3. Is the correct answer definitely correct?`,
      `4. Is the explanation accurate and sufficient?`,
      `5. Is the difficulty level appropriate?`,
      `6. Any factual errors or NCERT inaccuracies?`,
      ``,
      `Rate each question: ✅ Approve | ⚠️ Minor fix needed | ❌ Reject`,
      ``,
      `---`,
      ``,
    ];

    questions.forEach((q, i) => {
      const opts = Array.isArray(q.options_json) ? q.options_json : [];
      lines.push(`**Q${i + 1}.** [${q.subject} | ${q.difficulty} | ${q.topic || ""}]`);
      lines.push(q.question_text || "");
      lines.push("");
      opts.forEach(opt => {
        const marker = opt.key === q.correct_option ? `✓` : " ";
        lines.push(`  ${opt.key}${marker} ${opt.text}`);
      });
      lines.push("");
      lines.push(`**Correct Answer:** ${q.correct_option}`);
      if (q.detailed_explanation) {
        lines.push(`**Explanation:** ${q.detailed_explanation}`);
      }
      if (q.formula_used) {
        lines.push(`**Formula:** ${q.formula_used}`);
      }
      if (q.ncert_reference) {
        lines.push(`**NCERT:** ${q.ncert_reference}`);
      }
      lines.push("");
      lines.push(`---`);
      lines.push("");
    });

    lines.push(`Please provide your review for each question in the format above, and at the end give a summary of overall quality (X/Y approved, common issues).`);

    const text = lines.join("\n");
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 3000);
    }).catch(() => {
      // Fallback: open in textarea
      const ta = document.createElement("textarea");
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
      setCopied(true);
      setTimeout(() => setCopied(false), 3000);
    });
  }

  // When filterStatus is "draft", ALL loaded questions are drafts — the API already filters by status.
  // Avoid relying on q.status which may be absent in the API response shape.
  const draftCount = filterStatus === "draft" ? questions.length : questions.filter(q => q.status === "draft").length;

  return (
    <div style={{ marginTop: 20 }}>
      <div style={{ fontWeight: 700, fontSize: ".9rem", marginBottom: 14, display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 10 }}>
        <span>📋 Review & Publish Questions</span>
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          {/* Exam filter */}
          <select value={filterExam} onChange={e => setFilterExam(e.target.value)}
            style={{ padding: "5px 10px", borderRadius: 7, border: "1px solid var(--border,#e2e8f0)", background: "var(--surface,#f8fafc)", color: "var(--text,#1e293b)", fontSize: ".78rem", fontFamily: "inherit" }}>
            {REVIEW_EXAM_OPTIONS.map(e => <option key={e.value} value={e.value}>{e.label}</option>)}
          </select>
          {/* Status filter */}
          <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)}
            style={{ padding: "5px 10px", borderRadius: 7, border: "1px solid var(--border,#e2e8f0)", background: "var(--surface,#f8fafc)", color: "var(--text,#1e293b)", fontSize: ".78rem", fontFamily: "inherit" }}>
            {REVIEW_STATUS_OPTIONS.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
          {/* Subject filter */}
          <input value={filterSubject} onChange={e => setFilterSubject(e.target.value)}
            placeholder="Filter by subject…"
            style={{ padding: "5px 10px", borderRadius: 7, border: "1px solid var(--border,#e2e8f0)", background: "var(--surface,#f8fafc)", color: "var(--text,#1e293b)", fontSize: ".78rem", fontFamily: "inherit", width: 140 }} />
          <button onClick={loadQuestions} style={{ padding: "5px 12px", background: "rgba(99,102,241,.15)", border: "1px solid rgba(99,102,241,.3)", borderRadius: 7, color: "#a5b4fc", fontWeight: 700, fontSize: ".78rem", cursor: "pointer", fontFamily: "inherit" }}>
            🔄 Refresh
          </button>
          {questions.length > 0 && (
            <button
              onClick={copyForReview}
              title="Copy all questions as a structured prompt to paste into ChatGPT / Claude / Gemini for review"
              style={{ padding: "5px 14px", background: copied ? "#22c55e" : "rgba(139,92,246,.15)", border: `1px solid ${copied ? "#22c55e" : "rgba(139,92,246,.4)"}`, borderRadius: 7, color: copied ? "#fff" : "#a78bfa", fontWeight: 700, fontSize: ".78rem", cursor: "pointer", fontFamily: "inherit", transition: "all .2s" }}
            >
              {copied ? "✅ Copied!" : `📋 Copy for AI Review (${questions.length})`}
            </button>
          )}
          {filterStatus === "draft" && draftCount > 0 && (
            <button onClick={handlePublishAll} style={{ padding: "5px 14px", background: "#22c55e", border: "none", borderRadius: 7, color: "#fff", fontWeight: 700, fontSize: ".78rem", cursor: "pointer", fontFamily: "inherit" }}>
              ✅ Publish All ({draftCount})
            </button>
          )}
          {questions.length > 0 && filterStatus !== "archived" && (
            <button onClick={handleArchiveAll} style={{ padding: "5px 14px", background: "rgba(107,114,128,.15)", border: "1px solid rgba(107,114,128,.4)", borderRadius: 7, color: "#9ca3af", fontWeight: 700, fontSize: ".78rem", cursor: "pointer", fontFamily: "inherit" }}>
              🗑 Archive All ({questions.length})
            </button>
          )}
        </div>
      </div>

      {msg && <div className={msg.startsWith("❌") ? "error-box" : "info-box"} style={{ marginBottom: 10, fontSize: ".78rem" }}>{msg}</div>}

      {loading && <div style={{ color: "var(--muted,#64748b)", fontSize: ".82rem", padding: 12 }}>⏳ Loading questions…</div>}

      {!loading && questions.length === 0 && (
        <div style={{ background: "var(--panel,#1e293b)", border: "1px solid var(--border,#334155)", borderRadius: 10, padding: 20, textAlign: "center", color: "var(--muted,#64748b)", fontSize: ".82rem" }}>
          No {filterStatus} questions found for {REVIEW_EXAM_OPTIONS.find(e => e.value === filterExam)?.label}.
          {filterStatus === "draft" && " Generate some questions above."}
        </div>
      )}

      {!loading && questions.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {questions.map(q => {
            const isExpanded = expanded === q.id;
            const opts = Array.isArray(q.options_json) ? q.options_json : [];
            const validErrs = q.validation_errors;
            const hasErrors = Array.isArray(validErrs) && validErrs.length > 0;
            const statusColor = q.status === "published" ? "#22c55e" : q.status === "archived" ? "#6b7280" : "#f59e0b";
            return (
              <div key={q.id} style={{ background: "var(--panel,#1e293b)", border: `1px solid ${hasErrors ? "rgba(239,68,68,.3)" : "var(--border,#334155)"}`, borderRadius: 10, overflow: "hidden" }}>
                {/* Header row */}
                <div onClick={() => setExpanded(isExpanded ? null : q.id)}
                  style={{ display: "flex", alignItems: "center", gap: 10, padding: "10px 14px", cursor: "pointer", flexWrap: "wrap" }}>
                  <span style={{ fontSize: ".6rem", fontWeight: 800, background: `${statusColor}22`, color: statusColor, padding: "2px 8px", borderRadius: 20, flexShrink: 0 }}>
                    {q.status}
                  </span>
                  <span style={{ fontSize: ".6rem", background: "rgba(99,102,241,.1)", color: "#a5b4fc", padding: "2px 8px", borderRadius: 20, flexShrink: 0 }}>
                    {q.subject}
                  </span>
                  <span style={{ fontSize: ".6rem", background: "rgba(255,255,255,.05)", color: "var(--muted,#64748b)", padding: "2px 8px", borderRadius: 20, flexShrink: 0 }}>
                    {q.difficulty}
                  </span>
                  {hasErrors && <span style={{ fontSize: ".6rem", color: "#f87171", flexShrink: 0 }}>⚠️ {validErrs.length} issue{validErrs.length > 1 ? "s" : ""}</span>}
                  <span style={{ fontSize: ".78rem", color: "var(--text,#1e293b)", flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {q.question_text?.slice(0, 100)}{q.question_text?.length > 100 ? "…" : ""}
                  </span>
                  <span style={{ fontSize: ".7rem", color: "var(--muted,#64748b)", flexShrink: 0 }}>{isExpanded ? "▲" : "▼"}</span>
                </div>

                {/* Expanded content */}
                {isExpanded && (
                  <div style={{ borderTop: "1px solid var(--border,#334155)", padding: "12px 14px" }}>
                    {/* Full question */}
                    <div style={{ fontSize: ".82rem", color: "var(--text,#1e293b)", marginBottom: 12, lineHeight: 1.6 }}>{q.question_text}</div>

                    {/* Options */}
                    <div style={{ display: "flex", flexDirection: "column", gap: 5, marginBottom: 12 }}>
                      {opts.map(opt => (
                        <div key={opt.key} style={{ display: "flex", gap: 8, padding: "6px 10px", borderRadius: 6, background: opt.key === q.correct_option ? "rgba(34,197,94,.1)" : "rgba(255,255,255,.03)", border: `1px solid ${opt.key === q.correct_option ? "#22c55e" : "var(--border,#334155)"}`, fontSize: ".78rem" }}>
                          <strong style={{ color: opt.key === q.correct_option ? "#22c55e" : "var(--muted,#64748b)", width: 16 }}>{opt.key}</strong>
                          <span style={{ color: "var(--text,#1e293b)" }}>{opt.text}</span>
                          {opt.key === q.correct_option && <span style={{ color: "#22c55e", marginLeft: "auto" }}>✓ Correct</span>}
                        </div>
                      ))}
                    </div>

                    {/* Explanation */}
                    {q.detailed_explanation && (
                      <div style={{ background: "rgba(99,102,241,.07)", border: "1px solid rgba(99,102,241,.2)", borderRadius: 7, padding: 10, fontSize: ".75rem", color: "var(--text,#1e293b)", marginBottom: 10 }}>
                        <strong style={{ color: "#6366f1", display: "block", marginBottom: 4 }}>Explanation:</strong>
                        {q.detailed_explanation}
                      </div>
                    )}

                    {/* Validation errors */}
                    {hasErrors && (
                      <div style={{ background: "rgba(239,68,68,.06)", border: "1px solid rgba(239,68,68,.2)", borderRadius: 7, padding: 8, marginBottom: 10 }}>
                        <div style={{ fontSize: ".7rem", fontWeight: 700, color: "#f87171", marginBottom: 4 }}>⚠️ Validation Issues:</div>
                        {validErrs.map((e, i) => <div key={i} style={{ fontSize: ".7rem", color: "#fca5a5" }}>• {e}</div>)}
                      </div>
                    )}

                    {/* Metadata row */}
                    <div style={{ display: "flex", gap: 12, marginBottom: 12, flexWrap: "wrap" }}>
                      {q.topic && <span style={{ fontSize: ".65rem", color: "var(--muted,#64748b)" }}>📌 {q.topic}</span>}
                      {q.ncert_reference && <span style={{ fontSize: ".65rem", color: "var(--muted,#64748b)" }}>📖 {q.ncert_reference}</span>}
                      {q.source_type && <span style={{ fontSize: ".65rem", color: "var(--muted,#64748b)" }}>🤖 {q.source_type}</span>}
                      {q.validation_score != null && (
                        <span style={{ fontSize: ".65rem", color: q.validation_score >= 0.8 ? "#22c55e" : q.validation_score >= 0.5 ? "#f59e0b" : "#f87171" }}>
                          Score: {(q.validation_score * 100).toFixed(0)}%
                        </span>
                      )}
                    </div>

                    {/* Action buttons */}
                    <div style={{ display: "flex", gap: 8 }}>
                      {q.status !== "published" && (
                        <button
                          onClick={e => { e.stopPropagation(); handleAction(q.id, "publish"); }}
                          disabled={!!publishing[q.id]}
                          style={{ padding: "7px 16px", background: "#22c55e", border: "none", borderRadius: 7, color: "#fff", fontWeight: 700, fontSize: ".78rem", cursor: "pointer", fontFamily: "inherit", opacity: publishing[q.id] ? .6 : 1 }}
                        >
                          {publishing[q.id] === "publish" ? "⏳ Publishing…" : "✅ Publish"}
                        </button>
                      )}
                      {q.status !== "archived" && (
                        <button
                          onClick={e => { e.stopPropagation(); handleAction(q.id, "archive"); }}
                          disabled={!!publishing[q.id]}
                          style={{ padding: "7px 14px", background: "rgba(107,114,128,.15)", border: "1px solid rgba(107,114,128,.3)", borderRadius: 7, color: "#9ca3af", fontWeight: 700, fontSize: ".78rem", cursor: "pointer", fontFamily: "inherit" }}
                        >
                          {publishing[q.id] === "archive" ? "⏳…" : "🗑 Archive"}
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default AdminCacheManagementPage;
