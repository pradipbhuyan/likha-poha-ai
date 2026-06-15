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

export async function getLessonTextbookVisuals({
  grade,
  mode,
  board,
  subject,
  chapter,
  query = "",
}) {
  /** Load approved textbook visuals for the selected lesson context. */
  const params = new URLSearchParams({
    grade,
    mode,
    board,
    subject,
    chapter,
  });

  if (query.trim()) {
    params.set("query", query.trim());
  }

  return authFetch(`/api/lesson/textbook-visuals?${params.toString()}`);
}

export function getLessonDoubtSuggestions({ grade, mode, subject, chapter, board = "CBSE" }) {
  /** Fetch DKB-backed suggestion cards for a saved lesson (progress restore).
   *  Returns the same doubt_suggestions format as generateLesson so chips
   *  show pre-answered questions regardless of whether the lesson was freshly
   *  generated or loaded from saved progress.
   */
  const params = new URLSearchParams({ grade, mode, subject, chapter, board });
  return authFetch(`/api/lesson/doubt-suggestions?${params.toString()}`);
}
