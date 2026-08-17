import { authFetch } from "./authClient";

export async function saveTestHistory(payload) {
  /** Save one completed mock-test result for analytics and leaderboard views. */
  return authFetch("/api/analytics/test-history", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getUserHistory(username) {
  /** Load one student's historical mock-test results. */
  return authFetch(`/api/analytics/test-history/${username}`);
}

export async function getLeaderboard() {
  /** Load leaderboard data built from saved test history. Requires sign-in. */
  return authFetch("/api/analytics/leaderboard");
}

export async function clearUserHistory(username) {
  /** Delete one student's test-history records. */
  return authFetch(`/api/analytics/test-history/user/${username}`, {
    method: "DELETE",
  });
}

export async function clearAllHistory() {
  /** Delete all stored test-history records. */
  return authFetch("/api/analytics/test-history", {
    method: "DELETE",
  });
}

export async function getAnalytics(username) {
  /** Load test-history data for the analytics page. */
  return authFetch(`/api/analytics/test-history/${username}`);
}

export async function saveWrongAnswers({ username, grade, mode, subject, chapter, wrongAnswers }) {
  /**
   * Persist per-question wrong answers after a mock test is submitted.
   * wrongAnswers: array of { question_id, question, selected, correct, options, explanation, section, marks }
   */
  try {
    return await authFetch("/api/analytics/wrong-answers", {
      method: "POST",
      body: JSON.stringify({
        username,
        grade,
        mode,
        subject,
        chapter,
        wrong_answers: wrongAnswers,
      }),
    });
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
    return await authFetch(`/api/analytics/wrong-answers/${encodeURIComponent(username)}${qs}`);
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
    return await authFetch(`/api/analytics/weak-chapters/${encodeURIComponent(username)}`);
  } catch {
    return { success: false, weak_chapters: [] };
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Student Dashboard Summary — new canonical endpoint
// ─────────────────────────────────────────────────────────────────────────────


export async function getStudentDashboardSummary() {
  /** Fetch all student dashboard data in one call from /api/student/dashboard/summary */
  return authFetch("/api/student/dashboard/summary", { method: "GET" });
}

// ─────────────────────────────────────────────────────────────────────────────
// Student Exam Schedule API
// ─────────────────────────────────────────────────────────────────────────────

export async function getStudentExams() {
  return authFetch("/api/student/exams", { method: "GET" });
}
export async function addStudentExam(payload) {
  return authFetch("/api/student/exams", { method: "POST", body: JSON.stringify(payload) });
}
export async function updateStudentExam(examId, payload) {
  return authFetch(`/api/student/exams/${examId}`, { method: "PATCH", body: JSON.stringify(payload) });
}
export async function deleteStudentExam(examId) {
  return authFetch(`/api/student/exams/${examId}`, { method: "DELETE" });
}

// Parent: add exam for child
export async function addChildExam(childId, payload) {
  return authFetch(`/api/parent/children/${childId}/exams`, { method: "POST", body: JSON.stringify(payload) });
}
export async function getChildExams(childId) {
  return authFetch(`/api/parent/children/${childId}/exams`, { method: "GET" });
}
