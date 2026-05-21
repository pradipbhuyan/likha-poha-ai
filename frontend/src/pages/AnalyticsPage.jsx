import { useEffect, useState } from "react";
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
          (history.reduce((sum, item) => sum + Number(item.percentage || 0), 0) /
            totalTests) *
            100
        ) / 100
      : 0;

  const bestScore =
    totalTests > 0
      ? Math.max(...history.map((item) => Number(item.percentage || 0)))
      : 0;

  const latestScore =
    totalTests > 0
      ? Number(history[history.length - 1].percentage || 0)
      : 0;

  const subjectSummary = {};

  history.forEach((item) => {
    const subject = item.subject || "Unknown";

    if (!subjectSummary[subject]) {
      subjectSummary[subject] = {
        tests: 0,
        total: 0,
      };
    }

    subjectSummary[subject].tests += 1;
    subjectSummary[subject].total += Number(item.percentage || 0);
  });

  return (
    <div>
      <h2>📊 Analytics</h2>

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

          <div className="card">
            <h3>Subject-wise Performance</h3>

            {Object.entries(subjectSummary).map(([subject, data]) => {
              const avg =
                Math.round((data.total / data.tests) * 100) / 100;

              return (
                <p key={subject}>
                  <strong>{subject}</strong> — Tests: {data.tests} | Average: {avg}%
                </p>
              );
            })}
          </div>

          <div className="card">
            <h3>Recent Test History</h3>

            {[...history].reverse().slice(0, 10).map((item, index) => (
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