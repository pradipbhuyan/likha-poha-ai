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

  return (
    <div className="analytics-page">
      {message && <div className="info-box">{message}</div>}

      {totalTests === 0 ? (
        <div className="card">
          <p>No test history yet. Submit a mock test to see analytics.</p>
        </div>
      ) : (
        <>
          <div className="result-grid">
            <div>
              <strong>Tests Taken</strong>
              <p>{totalTests}</p>
            </div>

            <div>
              <strong>Average Score</strong>
              <p>{averageScore}%</p>
            </div>

            <div>
              <strong>Best Score</strong>
              <p>{bestScore}%</p>
            </div>

            <div>
              <strong>Latest Score</strong>
              <p>{latestScore}%</p>
            </div>
          </div>

          <div className="analytics-chart-grid">
            <div className="dashboard-chart-card">
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
                    <XAxis dataKey="name" />
                    <YAxis domain={[0, 100]} stroke="#94a3b8" />
                    <Tooltip
                      contentStyle={{
                        background: "#0f172a",
                        border: "1px solid #334155",
                        borderRadius: "14px",
                        color: "#f8fafc",
                      }}
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

            <div className="dashboard-chart-card">
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
                    <YAxis domain={[0, 100]} />
                    <Tooltip />
                    <Bar
                      dataKey="average"
                      fill="#3b82f6"
                      radius={[8, 8, 0, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          <div className="card">
            <h3>Recent Test History</h3>

            {[...history]
              .reverse()
              .slice(0, 10)
              .map((item, index) => (
                <div key={index} className="question-card">
                  <strong>
                    {item.subject} - {item.chapter || item.mockType}
                  </strong>

                  <p>
                    {item.difficulty} | {item.percentage}% |{" "}
                    {(item.submittedAt || item.saved_at || "").slice(0, 10)}
                  </p>
                </div>
              ))}
          </div>
        </>
      )}

      {(user.username === "pradip" || user.username === "admin") && (
        <div className="card">
          <h3>🧹 Admin: Clear Test History</h3>

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
      )}
    </div>
  );
}

export default AnalyticsPage;