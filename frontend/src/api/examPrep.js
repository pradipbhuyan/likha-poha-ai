/**
 * examPrep.js — Exam Prep Center API client
 * ==========================================
 * Wraps all /api/exam-prep/* and /api/admin/exam-prep/* endpoints.
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

function authHeaders(accessToken) {
  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${accessToken}`,
  };
}

async function handleResponse(res) {
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg = data?.detail || data?.message || `HTTP ${res.status}`;
    throw new Error(msg);
  }
  return data;
}

// ── Status & Dashboard ─────────────────────────────────────────────────────────

export async function getExamPrepStatus(accessToken) {
  const res = await fetch(`${API_BASE}/api/exam-prep/status`, {
    headers: authHeaders(accessToken),
  });
  return handleResponse(res);
}

export async function getExamPrepDashboard(accessToken, exam = "jee_main") {
  const res = await fetch(`${API_BASE}/api/exam-prep/dashboard?exam=${exam}`, {
    headers: authHeaders(accessToken),
  });
  return handleResponse(res);
}

// ── Subjects & Topics ──────────────────────────────────────────────────────────

export async function getExamPrepSubjects(accessToken, exam = "jee_main") {
  const res = await fetch(`${API_BASE}/api/exam-prep/subjects?exam=${exam}`, {
    headers: authHeaders(accessToken),
  });
  return handleResponse(res);
}

export async function getExamPrepTopics(accessToken, exam = "jee_main", subject = "Physics") {
  const res = await fetch(
    `${API_BASE}/api/exam-prep/topics?exam=${exam}&subject=${encodeURIComponent(subject)}`,
    { headers: authHeaders(accessToken) }
  );
  return handleResponse(res);
}

// ── Questions ──────────────────────────────────────────────────────────────────

export async function getExamPrepQuestions(accessToken, { exam = "jee_main", subject, topic, limit = 20 } = {}) {
  const params = new URLSearchParams({ exam, limit });
  if (subject) params.set("subject", subject);
  if (topic) params.set("topic", topic);
  const res = await fetch(`${API_BASE}/api/exam-prep/questions?${params}`, {
    headers: authHeaders(accessToken),
  });
  return handleResponse(res);
}

export async function getExamPrepQuestion(accessToken, questionId) {
  const res = await fetch(`${API_BASE}/api/exam-prep/questions/${questionId}`, {
    headers: authHeaders(accessToken),
  });
  return handleResponse(res);
}

export async function submitQuestionAnswer(accessToken, questionId, { selectedOption, timeTakenSeconds = 0 }) {
  const res = await fetch(`${API_BASE}/api/exam-prep/questions/${questionId}/answer`, {
    method: "POST",
    headers: authHeaders(accessToken),
    body: JSON.stringify({
      selected_option: selectedOption,
      time_taken_seconds: timeTakenSeconds,
    }),
  });
  return handleResponse(res);
}

// ── AI Explanation & Follow-up ─────────────────────────────────────────────────

export async function explainQuestion(accessToken, { questionText, subject = "Physics", exam = "JEE Main", userAnswer, followUp }) {
  const res = await fetch(`${API_BASE}/api/exam-prep/explain`, {
    method: "POST",
    headers: authHeaders(accessToken),
    body: JSON.stringify({
      question_text: questionText,
      subject,
      exam,
      user_answer: userAnswer,
      follow_up: followUp,
    }),
  });
  return handleResponse(res);
}

export async function askFollowUp(accessToken, { questionText, subject, exam, followUp, userAnswer }) {
  const res = await fetch(`${API_BASE}/api/exam-prep/ask-followup`, {
    method: "POST",
    headers: authHeaders(accessToken),
    body: JSON.stringify({
      question_text: questionText,
      subject: subject || "Physics",
      exam: exam || "JEE Main",
      follow_up: followUp,
      user_answer: userAnswer,
    }),
  });
  return handleResponse(res);
}

// ── Simulated Tests ────────────────────────────────────────────────────────────

export async function startSimulatedTest(accessToken, exam = "jee_main") {
  const res = await fetch(`${API_BASE}/api/exam-prep/simulated-tests/start`, {
    method: "POST",
    headers: authHeaders(accessToken),
    body: JSON.stringify({ exam }),
  });
  return handleResponse(res);
}

export async function getSimulatedTest(accessToken, testId) {
  const res = await fetch(`${API_BASE}/api/exam-prep/simulated-tests/${testId}`, {
    headers: authHeaders(accessToken),
  });
  return handleResponse(res);
}

export async function submitSimulatedTest(accessToken, testId, { answers = [], timeSpentSeconds = 0 }) {
  const res = await fetch(`${API_BASE}/api/exam-prep/simulated-tests/${testId}/submit`, {
    method: "POST",
    headers: authHeaders(accessToken),
    body: JSON.stringify({
      answers,
      time_spent_seconds: timeSpentSeconds,
    }),
  });
  return handleResponse(res);
}

export async function getTestResult(accessToken, testId) {
  const res = await fetch(`${API_BASE}/api/exam-prep/results/${testId}`, {
    headers: authHeaders(accessToken),
  });
  return handleResponse(res);
}

// ── Legacy PYQ ─────────────────────────────────────────────────────────────────

export async function getPYQPapers(accessToken, exam = "jee") {
  const res = await fetch(`${API_BASE}/api/exam-prep/papers?exam=${exam}`, {
    headers: authHeaders(accessToken),
  });
  return handleResponse(res);
}

export async function getPYQChunks(accessToken, docId, limit = 50) {
  const res = await fetch(`${API_BASE}/api/exam-prep/paper/${docId}/chunks?limit=${limit}`, {
    headers: authHeaders(accessToken),
  });
  return handleResponse(res);
}

// ── Admin endpoints ────────────────────────────────────────────────────────────

export async function runExamPrepMigration(accessToken) {
  const res = await fetch(`${API_BASE}/api/admin/exam-prep/migrate`, {
    method: "POST",
    headers: authHeaders(accessToken),
  });
  return handleResponse(res);
}

export async function adminGetQBStatus(accessToken, examType) {
  const params = examType ? `?exam_type=${examType}` : "";
  const res = await fetch(`${API_BASE}/api/admin/exam-prep/question-bank/status${params}`, {
    headers: authHeaders(accessToken),
  });
  return handleResponse(res);
}

export async function adminPrewarm(accessToken, options) {
  const res = await fetch(`${API_BASE}/api/admin/exam-prep/question-bank/prewarm`, {
    method: "POST",
    headers: authHeaders(accessToken),
    body: JSON.stringify(options),
  });
  return handleResponse(res);
}

export async function adminGetJob(accessToken, jobId) {
  const res = await fetch(`${API_BASE}/api/admin/exam-prep/question-bank/jobs/${jobId}`, {
    headers: authHeaders(accessToken),
  });
  return handleResponse(res);
}

export async function adminGetQuestions(accessToken, { examType, subject, status, limit = 50 } = {}) {
  const params = new URLSearchParams({ limit });
  if (examType) params.set("exam_type", examType);
  if (subject) params.set("subject", subject);
  if (status) params.set("status", status);
  const res = await fetch(`${API_BASE}/api/admin/exam-prep/questions?${params}`, {
    headers: authHeaders(accessToken),
  });
  return handleResponse(res);
}

export async function adminPublishQuestion(accessToken, questionId) {
  const res = await fetch(`${API_BASE}/api/admin/exam-prep/questions/${questionId}/publish`, {
    method: "POST",
    headers: authHeaders(accessToken),
  });
  return handleResponse(res);
}

export async function adminArchiveQuestion(accessToken, questionId) {
  const res = await fetch(`${API_BASE}/api/admin/exam-prep/questions/${questionId}/archive`, {
    method: "POST",
    headers: authHeaders(accessToken),
  });
  return handleResponse(res);
}

export async function adminUpdateQuestion(accessToken, questionId, updates) {
  const res = await fetch(`${API_BASE}/api/admin/exam-prep/questions/${questionId}`, {
    method: "PATCH",
    headers: authHeaders(accessToken),
    body: JSON.stringify(updates),
  });
  return handleResponse(res);
}
