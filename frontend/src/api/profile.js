import { authFetch } from "./authClient";

/**
 * Gamified student profile reads and activity writes.
 *
 * Activity is logged against the signed-in user — the backend ignores any
 * username sent in the body.
 */

export async function logStudentActivity({ username, activity_type }) {
  /** Record one gamified student activity such as lesson completion or test. */
  return authFetch("/api/profile/activity", {
    method: "POST",
    body: JSON.stringify({ username, activity_type }),
  });
}

export async function getStudentProfile(username) {
  /** Load gamified profile counters, XP, level, rank, and streak details. */
  return authFetch(`/api/profile/${encodeURIComponent(username)}`);
}
