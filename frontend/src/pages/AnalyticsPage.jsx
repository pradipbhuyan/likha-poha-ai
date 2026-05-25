import { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";

import {
  getUserHistory,
  clearUserHistory,
  clearAllHistory,
} from "../api/analytics";

function AnalyticsPage({ user }) {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

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

  useEffect(() => {
    loadHistory();
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

  if (loading) {
    return <p>Loading analytics...</p>;
  }

  const totalTests = history.length;

  const averageScore =
    totalTests > 0
      ? Math.round(
          history.reduce(
            (sum, item) => sum + Number(item.percentage || 0),
            0
          ) / totalTests
        )
      : 0;

  const bestScore =
    totalTests > 0
      ? Math.max(...history.map((item) => Number(item.percentage || 0)))
      : 0;

  const latestScore =
    totalTests > 0
      ? Number(history[history.length - 1].percentage || 0)
      : 0;

  const scoreTrend = history.map((item, index) => ({
    name: `Test ${index + 1}`,
    score: Number(item.percentage || 0),
  }));

  const subjectMap = {};

  history.forEach((item) => {
    const subject = item.subject || "Unknown";
    const percentage = Number(item.percentage || 0);

    if (!subjectMap[subject]) {
      subjectMap[subject] = {
        total: 0,
        tests: 0,
      };
    }

    subjectMap[subject].total += percentage;
    subjectMap[subject].tests += 1;
  });

  const subjectPerformance = Object.entries(subjectMap).map(
    ([subject, data]) => ({
      subject,
      average: Math.round(data.total / data.tests),
      tests: data.tests,
    })
  );

  const insightText =
    averageScore >= 85
      ? "Excellent consistency. You are ready for harder questions and Olympiad-level practice."
      : averageScore >= 65
      ? "Good progress. Focus on weaker subjects and review mistakes after every mock test."
      : "Revision needed. Start with concept review, then attempt short quizzes before mock tests.";

  return (
    <div className="analytics-page premium-page premium-analytics-page">
      {message && <div className="info-box">{message}</div>}

      <section className="premium-section premium-analytics-hero">
        <div className="premium-header">
          <p className="eyebrow">Learning Intelligence</p>
          <h2>📊 Analytics Dashboard</h2>
          <p>
            Track mock test performance, subject strength, score trends, and
            learning patterns over time.
          </p>
        </div>

        <div className="premium-analytics-insight-card">
          <span>🧠</span>
          <div>
            <strong>AI Insight</strong>
            <p>{insightText}</p>
          </div>
        </div>
      </section>

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

          <section className="analytics-chart-grid premium-analytics-chart-grid">
            <div className="dashboard-chart-card premium-card premium-chart-card">
              <div className="section-heading-row">
                <div>
                  <h3>📈 Score Trend</h3>
                  <p>Your mock test performance over time.</p>
                </div>
              </div>

              <div className="chart-container">
                <ResponsiveContainer width="100%" height={280}>
                  <LineChart data={scoreTrend}>
                    <CartesianGrid stroke="#334155" strokeDasharray="3 3" />
                    <XAxis dataKey="name" stroke="#94a3b8" />
                    <YAxis domain={[0, 100]} stroke="#94a3b8" />
                    <Tooltip
                      contentStyle={{
                        background: "#0f172a",
                        border: "1px solid #334155",
                        borderRadius: "14px",
                        color: "#f8fafc",
                      }}
                      labelStyle={{ color: "#f8fafc" }}
                      itemStyle={{ color: "#93c5fd" }}
                    />
                    <Line
                      type="monotone"
                      dataKey="score"
                      stroke="#3b82f6"
                      strokeWidth={3}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="dashboard-chart-card premium-card premium-chart-card">
              <div className="section-heading-row">
                <div>
                  <h3>📚 Subject Performance</h3>
                  <p>Average score by subject.</p>
                </div>
              </div>

              <div className="chart-container">
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={subjectPerformance}>
                    <CartesianGrid stroke="#334155" strokeDasharray="3 3" />
                    <XAxis dataKey="subject" stroke="#94a3b8" />
                    <YAxis domain={[0, 100]} stroke="#94a3b8" />
                    <Tooltip
                      cursor={{ fill: "rgba(59, 130, 246, 0.08)" }}
                      contentStyle={{
                        background: "#0f172a",
                        border: "1px solid #334155",
                        borderRadius: "14px",
                        color: "#f8fafc",
                      }}
                      labelStyle={{ color: "#f8fafc" }}
                      itemStyle={{ color: "#93c5fd" }}
                    />
                    <Bar
                      dataKey="average"
                      fill="#3b82f6"
                      radius={[10, 10, 0, 0]}
                      activeBar={{ fill: "#60a5fa" }}
                    />
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
              {[...history]
                .reverse()
                .slice(0, 10)
                .map((item, index) => (
                  <div key={index} className="premium-history-row">
                    <div>
                      <strong>
                        {item.subject} - {item.chapter || item.mockType}
                      </strong>

                      <p>
                        {item.difficulty} |{" "}
                        {(item.submittedAt || item.saved_at || "").slice(0, 10)}
                      </p>
                    </div>

                    <span>{item.percentage}%</span>
                  </div>
                ))}
            </div>
          </section>
        </>
      )}

      {(user.username === "pradip" || user.username === "admin") && (
        <section className="premium-section premium-admin-danger-section">
          <div className="premium-header">
            <h3>🧹 Admin: Clear Test History</h3>
            <p>Use carefully. These actions remove analytics history.</p>
          </div>

          <div className="premium-danger-actions">
            <button className="danger-btn" onClick={handleClearMyHistory}>
              Clear My History
            </button>

            <button className="danger-btn" onClick={handleClearAkshitaHistory}>
              Clear Akshita History
            </button>

            <button className="danger-btn" onClick={handleClearAllHistory}>
              Clear All History
            </button>
          </div>
        </section>
      )}
    </div>
  );
}

export default AnalyticsPage;
