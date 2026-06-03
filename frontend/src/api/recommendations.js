import API_BASE_URL from "./client";

export async function getRecommendations(username) {
  /** Load study recommendations generated from the student's test history. */
  const response = await fetch(
    `${API_BASE_URL}/api/recommendations/${username}`
  );

  if (!response.ok) {
    throw new Error("Failed to load recommendations");
  }

  return response.json();
}
