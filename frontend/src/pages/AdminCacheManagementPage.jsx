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
} from "../api/cacheManagement";

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
    pollRef.current = setInterval(fetchStatus, 15000);

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
                    <div style={{ marginBottom: 16 }}>
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
    </div>
  );
}

export default AdminCacheManagementPage;
