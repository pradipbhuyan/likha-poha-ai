const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  "http://localhost:8000";

export async function saveTestHistory(payload) {
  /** Save one completed mock-test result for analytics and leaderboard views. */
  const response = await fetch(`${API_BASE_URL}/api/analytics/test-history`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error("Failed to save test history");
  }

  return response.json();
}

export async function getUserHistory(username) {
  /** Load one student's historical mock-test results. */
  const response = await fetch(`${API_BASE_URL}/api/analytics/test-history/${username}`);

  if (!response.ok) {
    throw new Error("Failed to load user history");
  }

  return response.json();
}

export async function getLeaderboard() {
  /** Load leaderboard data built from saved test history. */
  const response = await fetch(`${API_BASE_URL}/api/analytics/leaderboard`);

  if (!response.ok) {
    throw new Error("Failed to load leaderboard");
  }

  return response.json();
}

export async function clearUserHistory(username) {
  /** Delete one student's test-history records. */
  const response = await fetch(`${API_BASE_URL}/api/analytics/test-history/user/${username}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    throw new Error("Failed to clear user history");
  }

  return response.json();
}

export async function clearAllHistory() {
  /** Delete all stored test-history records. */
  const response = await fetch(`${API_BASE_URL}/api/analytics/test-history`, {
    method: "DELETE",
  });

  if (!response.ok) {
    throw new Error("Failed to clear all history");
  }

  return response.json();
}

export async function getAnalytics(username) {
  /** Load test-history data for the analytics page. */
  const response = await fetch(
    `${API_BASE_URL}/api/analytics/test-history/${username}`
  );

  if (!response.ok) {
    throw new Error("Failed to load analytics");
  }

  return response.json();
}
