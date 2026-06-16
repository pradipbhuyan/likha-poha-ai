import { useEffect, useState } from "react";
import { redeemOfferCode } from "../api/adminControl";
import { getAnalytics } from "../api/analytics";
import { calculateAchievements } from "../utils/achievements";
import { getRecommendations } from "../api/recommendations";
import { getStudentProfile } from "../api/profile";

import {
  BarChart3,
  BookOpen,
  Bot,
  ClipboardList,
  Flame,
  Image,
  Sparkles,
  Target,
  Trophy,
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
  /** Student dashboard that summarizes progress, recommendations, and quick entry points. */
  const [achievements, setAchievements] = useState([]);
  const [profile, setProfile] = useState(null);
  const [offerCode, setOfferCode] = useState("");
  const [offerMsg, setOfferMsg] = useState("");
  const [offerErr, setOfferErr] = useState("");
  const [offerAccess, setOfferAccess] = useState(null); // { has_offer_access, valid_until }
  const [offerLoading, setOfferLoading] = useState(false);

  const [stats, setStats] = useState({
    testsTaken: 0,
    bestScore: 0,
    averageScore: 0,
    lastScore: 0,
  });

  const [scoreTrend, setScoreTrend] = useState([]);
  const [subjectPerformance, setSubjectPerformance] = useState([]);
  const [recommendations, setRecommendations] = useState([]);

  useEffect(() => {
    async function loadDashboard() {
      /** Load analytics, profile metrics, recommendations, and achievement badges together. */
      try {
        const result = await getAnalytics(user.username);

        const profileData = await getStudentProfile(user.username);
        setProfile(profileData.profile);

        const recData = await getRecommendations(user.username);
        setRecommendations(recData.recommendations || []);

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

  const profileStats = [
    {
      label: "Level",
      value: profile?.student_level || 1,
      suffix: profile?.rank_title || "Beginner",
      icon: Trophy,
      hint: "Learning rank",
      className: "purple",
    },
    {
      label: "XP",
      value: profile?.xp_points || 0,
      suffix: "points",
      icon: Sparkles,
      hint: "Keep earning",
      className: "cyan",
    },
    {
      label: "Study streak",
      value: profile?.study_streak_days || 0,
      suffix: "days",
      icon: Flame,
      hint: "Keep it up!",
      className: "orange",
    },
    {
      label: "Lessons",
      value: profile?.lessons_completed || 0,
      suffix: "completed",
      icon: BookOpen,
      hint: "Build your base",
      className: "green",
    },
    {
      label: "Quiz",
      value: profile?.quizzes_attempted || 0,
      suffix: "activities",
      icon: Target,
      hint: "Practice daily",
      className: "purple",
    },
    {
      label: "Visuals",
      value: profile?.visuals_generated || 0,
      suffix: "generated",
      icon: Image,
      hint: "Learn visually",
      className: "cyan",
    },
  ];

  return (
    <div className="dashboard-page premium-dashboard-page">
      <section className="dashboard-hero premium-dashboard-hero">
        <div className="premium-hero-copy">
          <p className="eyebrow">AI Learning Dashboard</p>

          <h2>
            <span>👋</span> Welcome back, {user.username}!
          </h2>

          <p>
            You have completed <strong>{profile?.lessons_completed || 0}</strong> lessons,
            attempted <strong>{stats.testsTaken}</strong> mock tests and currently hold a{" "}
            <strong>{stats.averageScore}%</strong> average score.
          </p>

          <div className="dashboard-actions premium-hero-actions">
            <button
              className="primary-btn dashboard-hero-btn"
              onClick={() => setActivePage("lessons")}
            >
              <BookOpen size={22} />
              Continue Learning
            </button>

            <button
              className="secondary-btn dashboard-hero-btn"
              onClick={() => setActivePage("mockTest")}
            >
              <ClipboardList size={22} />
              Take Mock Test
            </button>
          </div>
        </div>

        <div className="dashboard-ai-card premium-ai-card">
          <div className="premium-ai-content">
            <div className="premium-ai-icon">
              <Bot size={32} strokeWidth={2.4} />
            </div>

            <div>
              <h3>AI Tutor Suggestion</h3>

              {recommendations.length > 0 ? (
                <>
                  <p>
                    <strong>{recommendations[0].title}</strong>
                  </p>

                  <p>{recommendations[0].message}</p>

                  <button
                    className="mini-cta-btn"
                    onClick={() => setActivePage("lessons")}
                  >
                    📚 Continue Learning
                  </button>
                </>
              ) : (
                <>
                  <p>
                    Continue your learning journey by revising your latest
                    chapter and attempting a lesson.
                  </p>

                  <button
                    className="mini-cta-btn"
                    onClick={() => setActivePage("lessons")}
                  >
                    📚 Continue Learning
                  </button>
                </>
              )}
            </div>
          </div>

          <div className="premium-ai-mascot" aria-hidden="true">
            🤖
          </div>
        </div>
      </section>

      <section className="dashboard-grid premium-stat-grid">
        <div className="dashboard-stat-card premium-stat-card blue">
          <div className="dashboard-stat-icon blue">
            <ClipboardList size={28} strokeWidth={2.4} />
          </div>

          <div>
            <h3>{stats.testsTaken}</h3>
            <p>Mock tests completed</p>
          </div>

          <div className="mini-sparkline blue-line" />
        </div>

        <div className="dashboard-stat-card premium-stat-card purple">
          <div className="dashboard-stat-icon purple">
            <Target size={28} strokeWidth={2.4} />
          </div>

          <div>
            <h3>{stats.bestScore}%</h3>
            <p>Best mock test score</p>
          </div>

          <div className="mini-sparkline purple-line" />
        </div>

        <div className="dashboard-stat-card premium-stat-card green">
          <div className="dashboard-stat-icon green">
            <BarChart3 size={28} strokeWidth={2.4} />
          </div>

          <div>
            <h3>{stats.averageScore}%</h3>
            <p>Average performance</p>
          </div>

          <div className="mini-bars" />
        </div>

        <div className="dashboard-stat-card premium-stat-card red">
          <div className="dashboard-stat-icon red">
            <BookOpen size={28} strokeWidth={2.4} />
          </div>

          <div>
            <h3>{stats.lastScore}%</h3>
            <p>Latest test score</p>
          </div>

          <div className="mini-sparkline red-line" />
        </div>
      </section>

      <section className="profile-progress-strip">
        {profileStats.map((item) => {
          const Icon = item.icon;

          return (
            <div key={item.label} className="profile-progress-item">
              <div className={`profile-progress-icon ${item.className}`}>
                <Icon size={26} strokeWidth={2.4} />
              </div>

              <div>
                <h3>{item.value}</h3>
                <p>
                  {item.label} <span>{item.suffix}</span>
                </p>
                <small>{item.hint}</small>
              </div>
            </div>
          );
        })}

        <div className="profile-trophy">
          <Trophy size={76} strokeWidth={2.1} />
          <Sparkles size={22} className="sparkle-one" />
          <Sparkles size={18} className="sparkle-two" />
        </div>
      </section>

      <section className="recommendation-section">
        <div className="section-heading-row">
          <div>
            <h3>🧠 AI Study Recommendations</h3>
            <p>
              Personalized guidance based on performance and learning patterns.
            </p>
          </div>
        </div>

        <div className="recommendation-grid">
          {recommendations.map((rec, index) => (
            <div key={index} className={`recommendation-card ${rec.priority}`}>
              <h4>{rec.title}</h4>

              <p>{rec.message}</p>

              <span className="recommendation-priority">
                {rec.priority} priority
              </span>
            </div>
          ))}
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

        <div className="card" style={{ gridColumn: "1 / -1" }}>
          <h3>🎟️ Have an Offer Code?</h3>
          {offerAccess?.has_offer_access ? (
            <div className="info-box" style={{ margin: 0 }}>
              ✅ Offer access active until <strong>{offerAccess.valid_until?.slice(0, 10)}</strong>
            </div>
          ) : (
            <>
              <p style={{ fontSize: "0.9rem", color: "#94a3b8", marginBottom: 12 }}>
                Enter your 8-character offer code to unlock platform access for the code's validity period.
              </p>
              <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                <input
                  type="text"
                  maxLength={8}
                  value={offerCode}
                  onChange={e => setOfferCode(e.target.value.toUpperCase())}
                  placeholder="XXXXXXXX"
                  style={{ fontFamily: "monospace", letterSpacing: 3, textTransform: "uppercase", flex: 1, minWidth: 160, maxWidth: 220 }}
                />
                <button
                  className="primary-btn"
                  disabled={offerLoading || offerCode.length !== 8}
                  onClick={async () => {
                    setOfferLoading(true);
                    setOfferMsg("");
                    setOfferErr("");
                    try {
                      const res = await redeemOfferCode(offerCode, user.accessToken);
                      setOfferMsg(res.message || "✅ Offer code applied!");
                      setOfferAccess({ has_offer_access: true, valid_until: res.valid_until });
                      setOfferCode("");
                    } catch (err) {
                      setOfferErr(err.message || "Invalid or expired offer code.");
                    } finally {
                      setOfferLoading(false);
                    }
                  }}
                >
                  {offerLoading ? "Applying…" : "Apply Code"}
                </button>
              </div>
              {offerMsg && <div className="info-box" style={{ marginTop: 10 }}>{offerMsg}</div>}
              {offerErr && <div className="error-box" style={{ marginTop: 10 }}>{offerErr}</div>}
            </>
          )}
        </div>
      </section>
    </div>
  );
}

export default DashboardPage;
