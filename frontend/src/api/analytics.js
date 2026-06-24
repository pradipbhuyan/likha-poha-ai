const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  "http://localhost:8000";

export async function saveTestHistory(payload) {
  /** Save one completed mock-test result for analytics and leaderboard views. */
  const response = await fetch(`${API_BASE_URL}/api/analytics/test-history`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error("Failed to save test history");
  }

  return response.json();
}

export async function getUserHistory(username) {
  /** Load one student's historical mock-test results. */
  const response = await fetch(`${API_BASE_URL}/api/analytics/test-history/${username}`);

  if (!response.ok) {
    throw new Error("Failed to load user history");
  }

  return response.json();
}

export async function getLeaderboard() {
  /** Load leaderboard data built from saved test history. */
  const response = await fetch(`${API_BASE_URL}/api/analytics/leaderboard`);

  if (!response.ok) {
    throw new Error("Failed to load leaderboard");
  }

  return response.json();
}

export async function clearUserHistory(username) {
  /** Delete one student's test-history records. */
  const response = await fetch(`${API_BASE_URL}/api/analytics/test-history/user/${username}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    throw new Error("Failed to clear user history");
  }

  return response.json();
}

export async function clearAllHistory() {
  /** Delete all stored test-history records. */
  const response = await fetch(`${API_BASE_URL}/api/analytics/test-history`, {
    method: "DELETE",
  });

  if (!response.ok) {
    throw new Error("Failed to clear all history");
  }

  return response.json();
}

export async function getAnalytics(username) {
  /** Load test-history data for the analytics page. */
  const response = await fetch(
    `${API_BASE_URL}/api/analytics/test-history/${username}`
  );

  if (!response.ok) {
    throw new Error("Failed to load analytics");
  }

  return response.json();
}

export async function saveWrongAnswers({ username, grade, mode, subject, chapter, wrongAnswers }) {
  /**
   * Persist per-question wrong answers after a mock test is submitted.
   * wrongAnswers: array of { question_id, question, selected, correct, options, explanation, section, marks }
   */
  try {
    const response = await fetch(`${API_BASE_URL}/api/analytics/wrong-answers`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username,
        grade,
        mode,
        subject,
        chapter,
        wrong_answers: wrongAnswers,
      }),
    });
    if (!response.ok) return { success: false };
    return response.json();
  } catch {
    return { success: false };
  }
}

export async function getWrongAnswersForChapter(username, { subject, chapter } = {}) {
  /**
   * Fetch stored wrong-answer rows for a student, optionally filtered by subject+chapter.
   * Returns: { success, wrong_answers: [{ question, correct_answer, selected_answer, options, explanation, created_at }] }
   */
  try {
    const params = new URLSearchParams();
    if (subject) params.set("subject", subject);
    if (chapter) params.set("chapter", chapter);
    const qs = params.toString() ? `?${params.toString()}` : "";
    const response = await fetch(
      `${API_BASE_URL}/api/analytics/wrong-answers/${encodeURIComponent(username)}${qs}`
    );
    if (!response.ok) return { success: false, wrong_answers: [] };
    return response.json();
  } catch {
    return { success: false, wrong_answers: [] };
  }
}

export async function getWeakChapters(username) {
  /**
   * Fetch the student's weak chapters (chapters with the most wrong answers),
   * ordered by error count descending.
   * Returns: { success, weak_chapters: [{ grade, mode, subject, chapter, wrong_count }] }
   */
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/analytics/weak-chapters/${encodeURIComponent(username)}`
    );
    if (!response.ok) return { success: false, weak_chapters: [] };
    return response.json();
  } catch {
    return { success: false, weak_chapters: [] };
  }
}
