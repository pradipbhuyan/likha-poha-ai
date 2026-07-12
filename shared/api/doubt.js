import { authFetch } from "./authClient";

export async function answerDoubt(payload) {
  /** Send an authenticated Ask Doubt request with optional subject/chapter context. */
  return authFetch("/api/doubt/answer", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getDoubtHistory(limit = 20) {
  /** Load recent full Ask Doubt answers for the authenticated student. */
  return authFetch(`/api/doubt/history?limit=${limit}`);
}

export function getDoubtSuggestions({ grade, mode = "CBSE", subject = "", chapter = "", limit = 6 }) {
  /** Fetch DKB-backed suggestion chips for the Ask Doubt page.
   *  When subject is empty (Open subject), returns the most popular pre-answered
   *  questions across all subjects for the grade so chips are always relevant.
   */
  const params = new URLSearchParams({ grade, mode, limit });
  if (subject) params.set("subject", subject);
  if (chapter) params.set("chapter", chapter);
  return authFetch(`/api/doubt/suggestions?${params.toString()}`);
}
