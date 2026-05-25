import { useEffect, useState } from "react";
import { getUserHistory } from "../api/analytics";
import { getUsageSummary } from "../api/usage";

import { BarChart3, ClipboardList, Target, Trophy } from "lucide-react";

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

function ParentDashboardPage() {
  const studentUsername = "akshita";

  const [history, setHistory] = useState([]);
  const [usage, setUsage] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadParentDashboard() {
      try {
        const historyData = await getUserHistory(studentUsername);
        const usageData = await getUsageSummary(studentUsername);

        setHistory(historyData.history || []);
        setUsage(usageData);
      } finally {
        setLoading(false);
      }
    }

    loadParentDashboard();
  }, []);

  if (loading) return <p>Loading parent dashboard...</p>;

  const totalTests = history.length;
  const scores = history.map((item) => Number(item.percentage || 0));

  const averageScore = scores.length
    ? Math.round(scores.reduce((sum, score) => sum + score, 0) / scores.length)
    : 0;

  const bestScore = scores.length ? Math.max(...scores) : 0;
  const latestScore = scores.length ? scores[scores.length - 1] : 0;

  const scoreTrend = history.map((item, index) => ({
    name: `Test ${index + 1}`,
    score: Number(item.percentage || 0),
  }));

  const subjectMap = {};

  history.forEach((item) => {
    const subject = item.subject || "Unknown";
    const score = Number(item.percentage || 0);

    if (!subjectMap[subject]) {
      subjectMap[subject] = { total: 0, count: 0 };
    }

    subjectMap[subject].total += score;
    subjectMap[subject].count += 1;
  });

  const subjectPerformance = Object.entries(subjectMap).map(
    ([subject, value]) => ({
      subject,
      average: Math.round(value.total / value.count),
    })
  );

  const parentInsight =
    latestScore >= 85
      ? "Akshita is performing strongly. Encourage harder practice and Olympiad-style questions."
      : latestScore >= 60
      ? "Akshita is progressing well. Weekly revision and mistake review will help improve consistency."
      : "Akshita may need guided revision. Start with weak chapters, then use short tests to rebuild confidence.";

  return (
    <div className="parent-dashboard-page premium-page premium-parent-page">
      <section className="premium-section premium-parent-hero">
        <div className="premium-header">
          <p className="eyebrow">Parent Insights Center</p>
          <h2>Akshita&apos;s Learning Overview</h2>
          <p>
            Track learning progress, test performance, AI usage, and suggested
            next steps in one parent-friendly view.
          </p>
        </div>

        <div className="premium-parent-insight-card">
          <span>👨‍👩‍👧</span>
          <div>
            <strong>Parent Suggestion</strong>
            <p>{parentInsight}</p>
          </div>
        </div>
      </section>

      <section className="premium-grid premium-grid-4 premium-parent-stats">
        <div className="premium-card premium-glow-card glow-blue">
          <div className="dashboard-stat-icon blue">
            <ClipboardList size={28} strokeWidth={2.4} />
          </div>
          <h3>{totalTests}</h3>
          <p>Mock tests completed</p>
        </div>

        <div className="premium-card premium-glow-card glow-green">
          <div className="dashboard-stat-icon green">
            <BarChart3 size={28} strokeWidth={2.4} />
          </div>
          <h3>{averageScore}%</h3>
          <p>Average score</p>
        </div>

        <div className="premium-card premium-glow-card glow-purple">
          <div className="dashboard-stat-icon purple">
            <Trophy size={28} strokeWidth={2.4} />
          </div>
          <h3>{bestScore}%</h3>
          <p>Best score</p>
        </div>

        <div className="premium-card premium-glow-card glow-red">
          <div className="dashboard-stat-icon red">
            <Target size={28} strokeWidth={2.4} />
          </div>
          <h3>{latestScore}%</h3>
          <p>Latest score</p>
        </div>
      </section>

      <section className="analytics-chart-grid premium-parent-chart-grid">
        <div className="dashboard-chart-card premium-card premium-chart-card">
          <div className="section-heading-row">
            <div>
              <h3>📈 Score Trend</h3>
              <p>Akshita&apos;s mock test score over time.</p>
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

      <section className="dashboard-bottom-grid premium-parent-bottom-grid">
        <div className="premium-section premium-parent-activity">
          <div className="premium-header">
            <h3>🕘 Recent Test Activity</h3>
            <p>Latest mock tests completed by Akshita.</p>
          </div>

          {history.length === 0 ? (
            <div className="premium-parent-empty">
              <h3>No test history yet</h3>
              <p>Ask Akshita to complete a mock test to unlock insights.</p>
            </div>
          ) : (
            <div className="premium-parent-activity-list">
              {[...history]
                .reverse()
                .slice(0, 5)
                .map((item, index) => (
                  <div key={index} className="premium-parent-activity-row">
                    <div>
                      <strong>{item.subject}</strong>
                      <p>{item.chapter || item.mockType}</p>
                    </div>

                    <span>{item.percentage}%</span>
                  </div>
                ))}
            </div>
          )}
        </div>

        <div className="premium-section premium-parent-usage">
          <div className="premium-header">
            <h3>🤖 AI Usage</h3>
            <p>Estimated AI usage and cost visibility for this student.</p>
          </div>

          <div className="premium-parent-usage-grid">
            <div>
              <strong>
                ${Number(usage?.totals?.total_cost || 0).toFixed(6)}
              </strong>
              <span>Estimated cost</span>
            </div>

            <div>
              <strong>{usage?.totals?.total_tokens || 0}</strong>
              <span>Total tokens</span>
            </div>

            <div>
              <strong>{usage?.totals?.requests || 0}</strong>
              <span>Requests</span>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

export default ParentDashboardPage;
