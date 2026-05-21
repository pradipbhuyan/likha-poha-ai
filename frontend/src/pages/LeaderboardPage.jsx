import { useEffect, useState } from "react";
import { getLeaderboard } from "../api/analytics";

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

  return (
    <div>
      <h2>🏆 Leaderboard</h2>

      {leaderboard.length === 0 ? (
        <div className="card">
          <p>No leaderboard data yet.</p>
        </div>
      ) : (
        <div className="card">
          {leaderboard.map((item, index) => (
            <div key={item.username} className="question-card">
              <h3>
                #{index + 1} {item.username}
              </h3>

              <p>Average Score: {item.average_score}%</p>
              <p>Best Score: {item.best_score}%</p>
              <p>Tests Taken: {item.tests}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default LeaderboardPage;