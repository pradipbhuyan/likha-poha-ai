import { useEffect, useState } from "react";
import { getAnalytics } from "../api/analytics";
import { calculateAchievements } from "../utils/achievements";

import {
  BarChart3,
  BookOpen,
  Bot,
  ClipboardList,
  Target,
} from "lucide-react";

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

function DashboardPage({ user, setActivePage }) {
  const [achievements, setAchievements] = useState([]);

  const [stats, setStats] = useState({
    testsTaken: 0,
    bestScore: 0,
    averageScore: 0,
    lastScore: 0,
  });

  const [scoreTrend, setScoreTrend] = useState([]);
  const [subjectPerformance, setSubjectPerformance] = useState([]);

  useEffect(() => {
    async function loadDashboard() {
      try {
        const result = await getAnalytics(user.username);

        const history =
          result.history ||
          result.test_history ||
          result.results ||
          result.data ||
          [];

        const trendData = history.map((item, index) => ({
          name: `Test ${index + 1}`,
          score: Number(item.percentage || 0),
        }));

        setScoreTrend(trendData);

        const subjectMap = {};

        history.forEach((item) => {
          const subjectName = item.subject || "Unknown";
          const percentage = Number(item.percentage || 0);

          if (!subjectMap[subjectName]) {
            subjectMap[subjectName] = {
              total: 0,
              count: 0,
            };
          }

          subjectMap[subjectName].total += percentage;
          subjectMap[subjectName].count += 1;
        });

        const subjectData = Object.entries(subjectMap).map(
          ([subjectName, value]) => ({
            subject: subjectName,
            average: Math.round(value.total / value.count),
          })
        );

        setSubjectPerformance(subjectData);

        const percentages = history.map((item) => Number(item.percentage || 0));

        const testsTaken = history.length;
        const bestScore = percentages.length ? Math.max(...percentages) : 0;

        const averageScore = percentages.length
          ? Math.round(
              percentages.reduce((sum, score) => sum + score, 0) /
                percentages.length
            )
          : 0;

        const lastScore = percentages.length
          ? percentages[percentages.length - 1]
          : 0;

        setStats({
          testsTaken,
          bestScore,
          averageScore,
          lastScore,
        });

        setAchievements(
          calculateAchievements({
            testHistory: history,
          })
        );
      } catch (err) {
        console.error("Dashboard load failed", err);

        setAchievements(
          calculateAchievements({
            testHistory: [],
          })
        );
      }
    }

    loadDashboard();
  }, [user.username]);

  return (
    <div className="dashboard-page">
      <section className="dashboard-hero">
        <div>
          <p className="eyebrow">AI Learning Dashboard</p>

          <h2>Welcome back, {user.username} 👋</h2>

          <p>
            Continue your CBSE + SOF learning journey with lessons, doubts,
            quizzes, mock tests, and textbook-powered AI support.
          </p>

          <div className="dashboard-actions">
            <button
              className="primary-btn"
              onClick={() => setActivePage("lessons")}
            >
              Continue Learning
            </button>

            <button
              className="secondary-btn"
              onClick={() => setActivePage("mockTest")}
            >
              Take Mock Test
            </button>
          </div>
        </div>

        <div className="dashboard-ai-card">
          <div className="dashboard-stat-icon purple">
            <Bot size={28} strokeWidth={2.4} />
          </div>

          <h3>AI Tutor Suggestion</h3>

          <p>
            Start with your latest chapter, then attempt a quick quiz to check
            understanding.
          </p>
        </div>
      </section>

      <section className="dashboard-grid">
        <div className="dashboard-stat-card">
          <div className="dashboard-stat-icon blue">
            <ClipboardList size={28} strokeWidth={2.4} />
          </div>

          <h3>{stats.testsTaken}</h3>

          <p>Mock tests completed</p>
        </div>

        <div className="dashboard-stat-card">
          <div className="dashboard-stat-icon purple">
            <Target size={28} strokeWidth={2.4} />
          </div>

          <h3>{stats.bestScore}%</h3>

          <p>Best mock test score</p>
        </div>

        <div className="dashboard-stat-card">
          <div className="dashboard-stat-icon green">
            <BarChart3 size={28} strokeWidth={2.4} />
          </div>

          <h3>{stats.averageScore}%</h3>

          <p>Average performance</p>
        </div>

        <div className="dashboard-stat-card">
          <div className="dashboard-stat-icon red">
            <BookOpen size={28} strokeWidth={2.4} />
          </div>

          <h3>{stats.lastScore}%</h3>

          <p>Latest test score</p>
        </div>
      </section>

      <section className="achievement-section">
        <div className="section-heading-row">
          <div>
            <h3>🏅 Student Achievements</h3>
            <p>Motivation badges based on your learning activity.</p>
          </div>
        </div>

        <div className="achievement-grid">
          {achievements.map((achievement) => (
            <div
              key={achievement.id}
              className={
                achievement.unlocked
                  ? "achievement-card unlocked"
                  : "achievement-card"
              }
            >
              <span>{achievement.icon}</span>

              <h4>{achievement.title}</h4>

              <p>{achievement.description}</p>

              <small>{achievement.unlocked ? "Unlocked" : "Locked"}</small>
            </div>
          ))}
        </div>
      </section>

      <section className="dashboard-chart-card">
        <div className="section-heading-row">
          <div>
            <h3>📈 Score Trend</h3>
            <p>Your mock test performance over time.</p>
          </div>
        </div>

        {scoreTrend.length > 0 ? (
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
        ) : (
          <p className="muted">
            Take a mock test to see your score trend here.
          </p>
        )}
      </section>

      <section className="dashboard-chart-card">
        <div className="section-heading-row">
          <div>
            <h3>📚 Subject Performance</h3>
            <p>Your average mock test score by subject.</p>
          </div>
        </div>

        {subjectPerformance.length > 0 ? (
          <div className="chart-container">
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={subjectPerformance}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="subject" />
                <YAxis domain={[0, 100]} />
                <Tooltip />
                <Bar dataKey="average" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <p className="muted">
            Take mock tests in different subjects to see subject-wise analytics.
          </p>
        )}
      </section>

      <section className="dashboard-bottom-grid">
        <div className="card">
          <h3>🏆 Learning Goals</h3>

          <ul>
            <li>Complete one lesson step daily.</li>
            <li>Attempt at least one quiz after every lesson.</li>
            <li>Review weak topics from mock test results.</li>
          </ul>
        </div>

        <div className="card">
          <h3>📚 RAG Textbook Support</h3>

          <p>
            When uploaded textbook content matches your topic, answers and
            lessons use your textbook as the source.
          </p>
        </div>
      </section>
    </div>
  );
}

export default DashboardPage;