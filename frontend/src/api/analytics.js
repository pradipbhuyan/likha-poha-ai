const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  "http://localhost:8000";

export async function saveTestHistory(payload) {
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
  const response = await fetch(`${API_BASE_URL}/api/analytics/test-history/${username}`);

  if (!response.ok) {
    throw new Error("Failed to load user history");
  }

  return response.json();
}

export async function getLeaderboard() {
  const response = await fetch(`${API_BASE_URL}/api/analytics/leaderboard`);

  if (!response.ok) {
    throw new Error("Failed to load leaderboard");
  }

  return response.json();
}

export async function clearUserHistory(username) {
  const response = await fetch(`${API_BASE_URL}/api/analytics/test-history/user/${username}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    throw new Error("Failed to clear user history");
  }

  return response.json();
}

export async function clearAllHistory() {
  const response = await fetch(`${API_BASE_URL}/api/analytics/test-history`, {
    method: "DELETE",
  });

  if (!response.ok) {
    throw new Error("Failed to clear all history");
  }

  return response.json();
}

export async function getAnalytics(username) {
  const response = await fetch(
    `${API_BASE_URL}/api/analytics/test-history/${username}`
  );

  if (!response.ok) {
    throw new Error("Failed to load analytics");
  }

  return response.json();
}