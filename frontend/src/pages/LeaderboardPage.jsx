import { useEffect, useState } from "react";
import { getLeaderboard } from "../api/analytics";

function getMedal(index) {
  if (index === 0) return "🥇";
  if (index === 1) return "🥈";
  if (index === 2) return "🥉";
  return `#${index + 1}`;
}

function LeaderboardPage() {
  const [leaderboard, setLeaderboard] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadLeaderboard() {
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
  const rest = leaderboard.slice(3);

  return (
    <div className="leaderboard-page">
      {leaderboard.length === 0 ? (
        <div className="card">
          <p>No leaderboard data yet.</p>
        </div>
      ) : (
        <>
          <section className="leaderboard-podium">
            {topThree.map((item, index) => (
              <div key={item.username} className={`podium-card rank-${index + 1}`}>
                <div className="podium-medal">{getMedal(index)}</div>

                <div className="leader-avatar">
                  {item.username?.[0]?.toUpperCase() || "U"}
                </div>

                <h3>{item.username}</h3>

                <p className="leader-score">{item.average_score}%</p>
                <span>Average Score</span>
              </div>
            ))}
          </section>

          <section className="card leaderboard-list">
            <h3>🏁 Full Rankings</h3>

            {leaderboard.map((item, index) => (
              <div key={item.username} className="leaderboard-row">
                <div className="leader-rank">{getMedal(index)}</div>

                <div className="leader-avatar small">
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
              </div>
            ))}
          </section>
        </>
      )}
    </div>
  );
}

export default LeaderboardPage;