/**
 * studyPlanner.js — Study Planner API client
 * Calls /api/exam-prep/study-planner/* endpoints.
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

function authHeaders(token) {
  return { "Content-Type": "application/json", Authorization: `Bearer ${token}` };
}

async function handleResponse(res) {
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg = data?.detail || data?.message || `HTTP ${res.status}`;
    throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
  }
  return data;
}

/** Get the full study plan (countdown + today's tasks + weekly timeline) */
export async function getStudyPlan(token, examType = "jee_main") {
  const res = await fetch(
    `${API_BASE}/api/exam-prep/study-planner?exam_type=${examType}`,
    { headers: authHeaders(token) }
  );
  return handleResponse(res);
}

/** Generate (or regenerate) a new AI study plan */
export async function generateStudyPlan(token, { examType, dailyHours = 4 }) {
  const res = await fetch(`${API_BASE}/api/exam-prep/study-planner/generate`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify({ exam_type: examType, daily_hours: dailyHours }),
  });
  return handleResponse(res);
}

/** Mark a task as done, skipped, or pending */
export async function updateTaskStatus(token, taskId, status) {
  const res = await fetch(`${API_BASE}/api/exam-prep/study-planner/tasks/${taskId}`, {
    method: "PATCH",
    headers: authHeaders(token),
    body: JSON.stringify({ status }),
  });
  return handleResponse(res);
}

/** Create DB tables (first-time setup — safe to re-run) */
export async function migrateStudyPlanner(token) {
  const res = await fetch(`${API_BASE}/api/exam-prep/study-planner/migrate`, {
    method: "POST",
    headers: authHeaders(token),
  });
  return handleResponse(res);
}

/** Get exam countdown only (fast, no DB) */
export async function getCountdown(token, examType = "jee_main") {
  const res = await fetch(
    `${API_BASE}/api/exam-prep/study-planner/countdown?exam_type=${examType}`,
    { headers: authHeaders(token) }
  );
  return handleResponse(res);
}
