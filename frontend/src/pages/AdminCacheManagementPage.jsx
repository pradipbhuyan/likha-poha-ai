import { useEffect, useRef, useState } from "react";
import {
  getCacheStatus,
  startLessonPrewarm,
  startQuestionBankBuild,
  clearLessonCache,
  clearQuestionBank,
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

function AdminCacheManagementPage({ user }) {
  /** Admin page for grade-by-grade lesson pre-warming, question bank building, and cache clearing. */
  const [grades, setGrades] = useState([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const pollRef = useRef(null);

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

  async function handleClearLessons(grade) {
    /** Clear all cached lessons for a grade after confirmation. */
    if (!window.confirm(`Clear ALL cached lessons for ${grade}? This cannot be undone.`)) return;
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
          } = gradeData;

          const lessonPct = expected_lessons > 0
            ? Math.round((cached_lessons / expected_lessons) * 100)
            : 0;
          const questionPct = expected_questions > 0
            ? Math.round((banked_questions / expected_questions) * 100)
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
                    <div style={{ marginBottom: 16 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem", marginBottom: 4 }}>
                        <span>🎯 Questions in bank</span>
                        <strong>{banked_questions} / {expected_questions} ({questionPct}%)</strong>
                      </div>
                      <ProgressBar value={banked_questions} max={expected_questions} color="purple" />
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
                      title="Clear lesson cache to force re-generation (e.g. after RAG update)"
                    >
                      🗑️ Clear Lessons
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

      <section className="premium-section">
        <div className="premium-header">
          <h3>📋 Pre-Generation Cost Estimates</h3>
          <p>One-time cost to populate lessons and question bank for all grades.</p>
        </div>
        <div className="premium-grid premium-grid-3">
          <div className="premium-card">
            <strong>Grade 9 Lessons</strong>
            <p>~750 lesson steps × $0.003</p>
            <h4>~$2.50</h4>
            <small>~25 min to generate</small>
          </div>
          <div className="premium-card">
            <strong>Grade 9 Question Bank</strong>
            <p>~13,500 questions × $0.0006</p>
            <h4>~$8.73</h4>
            <small>~60 min to generate</small>
          </div>
          <div className="premium-card">
            <strong>After pre-generation</strong>
            <p>Zero LLM cost for lessons + tests</p>
            <h4>$0 / request</h4>
            <small>Only Ask Doubt uses tokens</small>
          </div>
        </div>
      </section>
    </div>
  );
}

export default AdminCacheManagementPage;
