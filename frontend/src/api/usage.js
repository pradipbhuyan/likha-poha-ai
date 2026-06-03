import API_BASE_URL from "./client";

export async function getUsageSummary(username = "") {
  /** Load AI token/cost/image usage, optionally filtered by username. */
  const query = username ? `?username=${encodeURIComponent(username)}` : "";

  const response = await fetch(`${API_BASE_URL}/api/usage/summary${query}`);

  if (!response.ok) {
    throw new Error("Failed to load usage summary");
  }

  return response.json();
}
