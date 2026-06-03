import { authFetch } from "./authClient";

export async function generateLesson(payload) {
  /** Generate one authenticated lesson step for the selected chapter/subtopic. */
  return authFetch("/api/lesson/generate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function askLessonFollowUp(payload) {
  /** Ask an authenticated follow-up question about the current lesson step. */
  return authFetch("/api/lesson/follow-up", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
