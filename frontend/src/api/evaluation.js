import { authFetch } from "./authClient";

export async function evaluateStudentAnswer(payload) {
  /**
   * Send a practice response for coaching feedback, score signal, and
   * revision memory. Uses authFetch so the backend can identify the
   * requesting user's tier (free vs paid) for AI-feedback gating: free
   * tier only gets instant keyword-scored feedback, paid tier gets a
   * 10/day cap on live AI feedback (see offer_access_service.py).
   */
  return authFetch("/api/evaluation/evaluate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function generatePracticeQuestions(payload) {
  /** Generate structured self-check questions for the current lesson step. */
  return authFetch("/api/evaluation/practice-questions", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
