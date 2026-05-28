import { authFetch } from "./authClient";

export async function generateLesson(payload) {
  return authFetch("/api/lesson/generate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function askLessonFollowUp(payload) {
  return authFetch("/api/lesson/follow-up", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}