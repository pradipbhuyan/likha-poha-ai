import { useEffect, useState } from "react";
import { getLeaderboard } from "../api/analytics";

function getMedal(index) {
  /** Return podium medals for the first three ranks and numeric labels after that. */
  if (index === 0) return "🥇";
  if (index === 1) return "🥈";
  if (index === 2) return "🥉";
  return `#${index + 1}`;
}

function getRankName(index) {
  /** Provide a friendly rank title for leaderboard cards. */
  if (index === 0) return "Champion";
  if (index === 1) return "Runner Up";
  if (index === 2) return "Rising Star";
  return "Learner";
}

function LeaderboardPage() {
  /** Shows ranked student mock-test performance with podium and full ranking views. */
  const [leaderboard, setLeaderboard] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadLeaderboard() {
      /** Load the leaderboard summary used by both podium and ranking rows. */
      try {
        const data = await getLeaderboard();
        setLeaderboard(data.leaderboard || []);
      } finally {
        setLoading(false);
      }
    }

    loadLeaderboard();
  }, []);

  if (loading) {
    return <p>Loading leaderboard...</p>;
  }

  const topThree = leaderboard.slice(0, 3);

  return (
    <div className="leaderboard-page premium-page premium-leaderboard-page">
      {/* Compact context bar: active learners count + tagline */}
      <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "12px 0 4px", flexWrap: "wrap" }}>
        <div style={{
          display: "inline-flex", alignItems: "center", gap: 8, padding: "6px 16px",
          borderRadius: 999, border: "2px solid rgba(99,102,241,0.4)",
          background: "rgba(99,102,241,0.1)",
        }}>
          <span style={{ fontSize: "1.1rem" }}>🏆</span>
          <span style={{ fontWeight: 800, fontSize: "1.2rem", color: "#818cf8" }}>{leaderboard.length}</span>
          <span style={{ fontWeight: 600, fontSize: "0.85rem", color: "var(--text, #e5e7eb)" }}>active learners ranked</span>
        </div>
        <span style={{ marginLeft: "auto", fontSize: "0.75rem", color: "var(--muted)", fontStyle: "italic" }}>
          Keep improving your mock test scores to climb the rankings
        </span>
      </div>

      {leaderboard.length === 0 ? (
        <section className="premium-section premium-empty-leaderboard">
          <div className="premium-header">
            <p className="eyebrow">No rankings yet</p>
            <h2>Submit a mock test to enter the leaderboard</h2>
            <p>
              Once students complete mock tests, their average and best scores
              will appear here.
            </p>
          </div>
        </section>
      ) : (
        <>
          <section className="leaderboard-podium premium-leaderboard-podium">
            {topThree.map((item, index) => (
              <div
                key={item.username}
                className={`podium-card premium-podium-card rank-${index + 1}`}
              >
                <div className="podium-medal">{getMedal(index)}</div>

                <div className="leader-avatar premium-leader-avatar">
                  {item.username?.[0]?.toUpperCase() || "U"}
                </div>

                <p className="premium-rank-name">{getRankName(index)}</p>

                <h3>{item.username}</h3>

                <p className="leader-score">{item.average_score}%</p>
                <span>Average Score</span>

                <div className="premium-podium-meta">
                  <small>{item.tests} tests</small>
                  <small>Best {item.best_score}%</small>
                </div>
              </div>
            ))}
          </section>

          <section className="premium-section leaderboard-list premium-leaderboard-list">
            <div className="premium-header">
              <h3>🏁 Full Rankings</h3>
              <p>Ranked by average score across completed mock tests.</p>
            </div>

            <div className="premium-leaderboard-rows">
              {leaderboard.map((item, index) => (
                <div key={item.username} className="leaderboard-row premium-leaderboard-row">
                  <div className="leader-rank">{getMedal(index)}</div>

                  <div className="leader-avatar small premium-leader-avatar small">
                    {item.username?.[0]?.toUpperCase() || "U"}
                  </div>

                  <div className="leader-main">
                    <strong>{item.username}</strong>
                    <span>{item.tests} tests taken</span>
                  </div>

                  <div className="leader-metric">
                    <strong>{item.average_score}%</strong>
                    <span>Average</span>
                  </div>

                  <div className="leader-metric">
                    <strong>{item.best_score}%</strong>
                    <span>Best</span>
                  </div>

                  <div className="premium-rank-chip">
                    {index < 3 ? "Top Performer" : "Climber"}
                  </div>
                </div>
              ))}
            </div>
          </section>
        </>
      )}
    </div>
  );
}

export default LeaderboardPage;
