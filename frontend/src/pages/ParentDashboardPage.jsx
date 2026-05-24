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

  return (
    <div className="parent-dashboard-page">
      <section className="dashboard-hero">
        <div>
          <p className="eyebrow">Parent Dashboard</p>
          <h2>Akshita&apos;s Learning Overview</h2>
          <p>
            Track learning progress, test performance, AI usage, and suggested
            next steps.
          </p>
        </div>

        <div className="dashboard-ai-card">
          <h3>Parent Suggestion</h3>
          <p>
            Review weak chapters weekly and encourage one short quiz after every
            lesson.
          </p>
        </div>
      </section>

      <section className="dashboard-grid">
        <div className="dashboard-stat-card">
          <div className="dashboard-stat-icon blue">
            <ClipboardList size={28} strokeWidth={2.4} />
          </div>
          <h3>{totalTests}</h3>
          <p>Mock tests completed</p>
        </div>

        <div className="dashboard-stat-card">
          <div className="dashboard-stat-icon green">
            <BarChart3 size={28} strokeWidth={2.4} />
          </div>
          <h3>{averageScore}%</h3>
          <p>Average score</p>
        </div>

        <div className="dashboard-stat-card">
          <div className="dashboard-stat-icon purple">
            <Trophy size={28} strokeWidth={2.4} />
          </div>
          <h3>{bestScore}%</h3>
          <p>Best score</p>
        </div>

        <div className="dashboard-stat-card">
          <div className="dashboard-stat-icon red">
            <Target size={28} strokeWidth={2.4} />
          </div>
          <h3>{latestScore}%</h3>
          <p>Latest score</p>
        </div>
      </section>

      <section className="analytics-chart-grid">
        <div className="dashboard-chart-card">
          <div className="section-heading-row">
            <div>
              <h3>📈 Score Trend</h3>
              <p>Akshita&apos;s mock test score over time.</p>
            </div>
          </div>

          <div className="chart-container">
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={scoreTrend}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis domain={[0, 100]} />
                <Tooltip />
                <Line type="monotone" dataKey="score" strokeWidth={3} />
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

      <section className="dashboard-bottom-grid">
        <div className="card">
          <h3>Recent Test Activity</h3>

          {history.length === 0 ? (
            <p>No test history yet.</p>
          ) : (
            [...history]
              .reverse()
              .slice(0, 5)
              .map((item, index) => (
                <div key={index} className="question-card">
                  <strong>{item.subject}</strong>
                  <p>{item.chapter || item.mockType}</p>
                  <p>{item.percentage}%</p>
                </div>
              ))
          )}
        </div>

        <div className="card">
          <h3>AI Usage</h3>
          <p>
            Estimated cost: ${Number(usage?.totals?.total_cost || 0).toFixed(6)}
          </p>
          <p>Total tokens: {usage?.totals?.total_tokens || 0}</p>
          <p>Requests: {usage?.totals?.requests || 0}</p>
        </div>
      </section>
    </div>
  );
}

export default ParentDashboardPage;
