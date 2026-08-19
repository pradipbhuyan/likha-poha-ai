import { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";

import {
  getUserHistory,
  clearUserHistory,
  clearAllHistory,
  getWeakChapters,
} from "../api/analytics";

/** Consistent color palette for subjects across charts */
const SUBJECT_COLORS = [
  "#3b82f6", "#10b981", "#f59e0b", "#ef4444",
  "#8b5cf6", "#06b6d4", "#ec4899", "#f97316",
];

/**
 * Build per-subject score sequences for the multi-line trend chart.
 * Returns { trendData: [{name, Subject1: score, ...}], subjects: [str] }
 */
function buildSubjectTrend(history) {
  const subjectScores = {};
  history.forEach((item) => {
    const subj = item.subject || "Unknown";
    if (!subjectScores[subj]) subjectScores[subj] = [];
    subjectScores[subj].push(Number(item.percentage || 0));
  });

  const subjects = Object.keys(subjectScores);
  if (subjects.length === 0) return { trendData: [], subjects: [] };

  const maxLen = Math.max(...subjects.map((s) => subjectScores[s].length));
  const trendData = Array.from({ length: maxLen }, (_, i) => {
    const point = { name: `Test ${i + 1}` };
    subjects.forEach((subj) => {
      if (i < subjectScores[subj].length) point[subj] = subjectScores[subj][i];
    });
    return point;
  });

  return { trendData, subjects };
}

/**
 * Build grouped bar data: best / average / latest score per subject.
 */
function buildSubjectPerformance(history) {
  const subjectData = {};
  history.forEach((item) => {
    const subj = item.subject || "Unknown";
    const score = Number(item.percentage || 0);
    if (!subjectData[subj]) subjectData[subj] = { scores: [], latest: score };
    subjectData[subj].scores.push(score);
    subjectData[subj].latest = score; // last occurrence wins
  });

  return Object.entries(subjectData).map(([subject, d]) => ({
    subject,
    Best: Math.max(...d.scores),
    Average: Math.round(d.scores.reduce((a, b) => a + b, 0) / d.scores.length),
    Latest: d.latest,
  }));
}

function AnalyticsPage({ user, setActivePage }) {
  /** Shows a student's test history trends and provides admin cleanup actions. */
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [weakChapters, setWeakChapters] = useState([]);

  async function loadHistory() {
    setLoading(true);
    try {
      const data = await getUserHistory(user.username);
      setHistory(data.history || []);
    } catch {
      setMessage("Could not load analytics.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadHistory(); }, [user.username]);

  useEffect(() => {
    // Same weak-chapters source the Dashboard already uses — one definition
    // of "weak" across the app, not a new Analytics-only calculation.
    getWeakChapters(user.username)
      .then((data) => setWeakChapters(data?.weak_chapters || []))
      .catch(() => setWeakChapters([]));
  }, [user.username]);

  async function handleClearMyHistory() {
    if (!confirm("Clear your test history?")) return;
    await clearUserHistory(user.username);
    setMessage("Your history cleared.");
    loadHistory();
  }

  async function handleClearAkshitaHistory() {
    if (!confirm("Clear Akshita's test history?")) return;
    await clearUserHistory("akshita");
    setMessage("Akshita's history cleared.");
    loadHistory();
  }

  async function handleClearAllHistory() {
    if (!confirm("Clear ALL test history?")) return;
    await clearAllHistory();
    setMessage("All history cleared.");
    loadHistory();
  }

  if (loading) return <p>Loading analytics...</p>;

  const totalTests = history.length;
  const averageScore = totalTests > 0
    ? Math.round(history.reduce((sum, i) => sum + Number(i.percentage || 0), 0) / totalTests)
    : 0;
  const bestScore = totalTests > 0
    ? Math.max(...history.map((i) => Number(i.percentage || 0)))
    : 0;
  const latestScore = totalTests > 0
    ? Number(history[history.length - 1].percentage || 0)
    : 0;

  const { trendData, subjects } = buildSubjectTrend(history);
  const subjectPerformance = buildSubjectPerformance(history);

  const tooltipStyle = {
    contentStyle: {
      background: "#0f172a",
      border: "1px solid #334155",
      borderRadius: "14px",
      color: "#f8fafc",
    },
    labelStyle: { color: "#f8fafc" },
    itemStyle: { color: "#93c5fd" },
  };

  return (
    <div className="analytics-page premium-page premium-analytics-page">
      {message && <div className="info-box">{message}</div>}

      {totalTests === 0 ? (
        <section className="premium-section premium-empty-analytics">
          <div className="premium-header">
            <p className="eyebrow">No data yet</p>
            <h2>Submit a mock test to unlock analytics</h2>
            <p>
              Once you complete mock tests, this page will show score trends,
              subject performance, recent history, and AI learning insights.
            </p>
          </div>
          <div className="premium-grid premium-grid-3">
            <div className="premium-card premium-glow-card glow-blue">
              <h3>📈 Score Trends</h3>
              <p>See whether performance is improving over time.</p>
            </div>
            <div className="premium-card premium-glow-card glow-purple">
              <h3>📚 Subject Strength</h3>
              <p>Identify strong and weak subjects from test history.</p>
            </div>
            <div className="premium-card premium-glow-card glow-green">
              <h3>🧠 Smart Insights</h3>
              <p>Use analytics to guide revision and practice.</p>
            </div>
          </div>
        </section>
      ) : (
        <>
          <section className="premium-grid premium-grid-4 premium-analytics-stats">
            <div className="premium-card premium-glow-card glow-blue">
              <strong>Tests Taken</strong>
              <p>{totalTests}</p>
            </div>
            <div className="premium-card premium-glow-card glow-green">
              <strong>Average Score</strong>
              <p>{averageScore}%</p>
            </div>
            <div className="premium-card premium-glow-card glow-purple">
              <strong>Best Score</strong>
              <p>{bestScore}%</p>
            </div>
            <div className="premium-card premium-glow-card glow-red">
              <strong>Latest Score</strong>
              <p>{latestScore}%</p>
            </div>
          </section>

          {/* ── Weak chapters — act on it, don't just look at it ── */}
          <section className="premium-section premium-weak-chapters-section">
            <div className="premium-header">
              <h3>🎯 Weak Chapters</h3>
              <p>Chapters with the most wrong answers — same list the Dashboard uses.</p>
            </div>
            {weakChapters.length === 0 ? (
              <div style={{ color: "var(--text-muted, #94a3b8)", fontSize: "0.85rem" }}>
                No weak chapters yet — keep practising!
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {weakChapters.slice(0, 5).map((w, i) => (
                  <div
                    key={`${w.subject}-${w.chapter}-${i}`}
                    style={{
                      display: "flex", alignItems: "center", justifyContent: "space-between",
                      gap: 12, padding: "10px 14px", borderRadius: 10,
                      background: "var(--panel-soft, rgba(148,163,184,.08))",
                      border: "1px solid var(--border, rgba(148,163,184,.18))",
                    }}
                  >
                    <div style={{ minWidth: 0 }}>
                      <strong style={{ fontSize: "0.85rem" }}>{w.subject}</strong>
                      <span style={{ color: "var(--text-muted, #94a3b8)", fontSize: "0.82rem" }}> — {w.chapter}</span>
                    </div>
                    <button
                      type="button"
                      onClick={() => setActivePage && setActivePage("mockTest")}
                      style={{
                        flexShrink: 0, background: "#4f46e5", color: "#fff", border: "none",
                        borderRadius: 8, padding: "6px 12px", fontSize: "0.78rem", fontWeight: 700,
                        cursor: "pointer", fontFamily: "inherit",
                      }}
                    >
                      Practice →
                    </button>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* ── Charts row ── */}
          <section className="analytics-chart-grid premium-analytics-chart-grid">

            {/* Score Trend — one line per subject */}
            <div className="dashboard-chart-card premium-card premium-chart-card">
              <div className="section-heading-row">
                <div>
                  <h3>📈 Score Trend</h3>
                  <p>Performance per subject over successive tests.</p>
                </div>
              </div>
              <div className="chart-container">
                <ResponsiveContainer width="100%" height={280}>
                  <LineChart data={trendData}>
                    <CartesianGrid stroke="#334155" strokeDasharray="3 3" />
                    <XAxis dataKey="name" stroke="#94a3b8" />
                    <YAxis domain={[0, 100]} stroke="#94a3b8" />
                    <Tooltip {...tooltipStyle} />
                    <Legend wrapperStyle={{ color: "#94a3b8", fontSize: "12px" }} />
                    {subjects.map((subj, i) => (
                      <Line
                        key={subj}
                        type="monotone"
                        dataKey={subj}
                        stroke={SUBJECT_COLORS[i % SUBJECT_COLORS.length]}
                        strokeWidth={2.5}
                        dot={{ r: 3 }}
                        activeDot={{ r: 5 }}
                        connectNulls
                      />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Subject Performance — grouped bars: Best / Average / Latest */}
            <div className="dashboard-chart-card premium-card premium-chart-card">
              <div className="section-heading-row">
                <div>
                  <h3>📚 Subject Performance</h3>
                  <p>Best, average and latest score per subject.</p>
                </div>
              </div>
              <div className="chart-container">
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={subjectPerformance} barCategoryGap="30%" barGap={3}>
                    <CartesianGrid stroke="#334155" strokeDasharray="3 3" />
                    <XAxis dataKey="subject" stroke="#94a3b8" tick={{ fontSize: 11 }} />
                    <YAxis domain={[0, 100]} stroke="#94a3b8" />
                    <Tooltip
                      cursor={{ fill: "rgba(59,130,246,0.06)" }}
                      {...tooltipStyle}
                    />
                    <Legend wrapperStyle={{ color: "#94a3b8", fontSize: "12px" }} />
                    <Bar dataKey="Best"    fill="#10b981" radius={[6,6,0,0]} />
                    <Bar dataKey="Average" fill="#3b82f6" radius={[6,6,0,0]} />
                    <Bar dataKey="Latest"  fill="#f59e0b" radius={[6,6,0,0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

          </section>

          <section className="premium-section premium-history-section">
            <div className="premium-header">
              <h3>🕘 Recent Test History</h3>
              <p>Your latest mock test attempts and performance snapshots.</p>
            </div>
            <div className="premium-history-list">
              {[...history].reverse().slice(0, 10).map((item, index) => (
                <div key={index} className="premium-history-row">
                  <div>
                    <strong>{item.subject} - {item.chapter || item.mockType}</strong>
                    <p>{item.difficulty} | {(item.submittedAt || item.saved_at || "").slice(0, 10)}</p>
                  </div>
                  <span>{item.percentage}%</span>
                </div>
              ))}
            </div>
          </section>
        </>
      )}

      {user.role === "admin" && (
        <section className="premium-section premium-admin-danger-section">
          <div className="premium-header">
            <h3>🧹 Admin: Clear Test History</h3>
            <p>Use carefully. These actions remove analytics history.</p>
          </div>
          <div className="premium-danger-actions">
            <button className="danger-btn" onClick={handleClearMyHistory}>Clear My History</button>
            <button className="danger-btn" onClick={handleClearAkshitaHistory}>Clear Akshita History</button>
            <button className="danger-btn" onClick={handleClearAllHistory}>Clear All History</button>
          </div>
        </section>
      )}
    </div>
  );
}

export default AnalyticsPage;
