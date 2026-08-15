import { authFetch } from "./authClient";

/**
 * Lesson progress reads and writes.
 *
 * These endpoints identify the student from the bearer token, not from a
 * username in the payload — the backend ignores any username sent here.
 */

export async function getChapterProgress(payload) {
  /** Load saved lesson progress for one chapter selection. */
  return authFetch("/api/progress/chapter", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function saveChapterProgress(payload) {
  /** Save current step, unlock state, completion flag, and cached lesson text. */
  return authFetch("/api/progress/save", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getUserProgress(username) {
  /** Load all saved chapter progress for one student (self, or any as admin/teacher). */
  return authFetch(`/api/progress/user/${encodeURIComponent(username)}`);
}
