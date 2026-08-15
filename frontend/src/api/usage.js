import { authFetch } from "./authClient";

export async function getUsageSummary(username = "") {
  /** Load AI token/cost/image usage, optionally filtered by username. Admin-only. */
  const query = username ? `?username=${encodeURIComponent(username)}` : "";

  return authFetch(`/api/usage/summary${query}`);
}
