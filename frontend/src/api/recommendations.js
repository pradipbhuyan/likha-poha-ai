import { authFetch } from "./authClient";

export async function getRecommendations(username) {
  /** Load study recommendations generated from the student's test history. */
  return authFetch(`/api/recommendations/${encodeURIComponent(username)}`);
}
