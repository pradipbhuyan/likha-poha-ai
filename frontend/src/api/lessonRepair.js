import { authFetch } from "./authClient";

const BASE = "/api/admin/qa/lesson-repair";

/** Get currently configured LLM provider, model, and cost estimates */
export async function getRepairLlmInfo() {
  return authFetch(`${BASE}/llm-info`);
}

/** Get latest repair job + audit report metadata */
export async function getLatestRepairStatus() {
  return authFetch(`${BASE}/latest`);
}

/** Get repair job history */
export async function getRepairHistory(limit = 20) {
  return authFetch(`${BASE}/history?limit=${limit}`);
}

/**
 * Start a repair job.
 * @param {object} opts - { mode, grade, subject, chapter, use_llm, override_api_key }
 */
export async function runRepairJob(opts = {}) {
  return authFetch(`${BASE}/run`, {
    method: "POST",
    body: JSON.stringify({
      mode: opts.mode || "sample",
      grade: opts.grade || null,
      subject: opts.subject || null,
      chapter: opts.chapter || null,
      use_llm: !!opts.use_llm,
      // Session-only key override — not stored, used for this job only
      override_api_key: opts.override_api_key || null,
    }),
  });
}

/** Poll status of a repair job */
export async function getRepairJobStatus(jobId) {
  return authFetch(`${BASE}/status/${jobId}`);
}

/**
 * Get all tasks for a job.
 * @param {string} jobId
 * @param {object} filters - { status, grade, subject, limit }
 */
export async function getRepairTasks(jobId, filters = {}) {
  const params = new URLSearchParams();
  if (filters.status) params.set("status", filters.status);
  if (filters.grade) params.set("grade", filters.grade);
  if (filters.subject) params.set("subject", filters.subject);
  if (filters.limit) params.set("limit", String(filters.limit));
  const qs = params.toString() ? `?${params.toString()}` : "";
  return authFetch(`${BASE}/tasks/${jobId}${qs}`);
}

/** Get single task detail */
export async function getRepairTask(taskId) {
  return authFetch(`${BASE}/task/${taskId}`);
}

/** Approve a task draft */
export async function approveRepairTask(taskId) {
  return authFetch(`${BASE}/task/${taskId}/approve`, { method: "POST" });
}

/** Publish an approved task to lesson_cache */
export async function publishRepairTask(taskId) {
  return authFetch(`${BASE}/task/${taskId}/publish`, { method: "POST" });
}

/** Re-run LLM repair for a failed/validation-failed task */
export async function rerunRepairTask(taskId) {
  return authFetch(`${BASE}/task/${taskId}/rerun`, { method: "POST" });
}

/** Cancel a running or queued job */
export async function cancelRepairJob(jobId) {
  return authFetch(`${BASE}/job/${jobId}/cancel`, { method: "POST" });
}

/** Download repair report */
export function getRepairReportUrl(jobId, format = "json") {
  const qs = new URLSearchParams({ format });
  if (jobId) qs.set("job_id", jobId);
  return `${BASE}/report?${qs.toString()}`;
}

// ── Step Sequence Analysis ────────────────────────────────────────────────────

/**
 * Run step-sequence audit by providing step content directly.
 * @param {{ grade, subject, chapter, lesson_id, steps }} opts
 */
export async function postStepAnalysis({ grade, subject, chapter, lesson_id, steps }) {
  return authFetch(`${BASE}/step-analysis`, {
    method: "POST",
    body: JSON.stringify({
      grade: grade || "",
      subject: subject || "",
      chapter: chapter || "",
      lesson_id: lesson_id || "",
      steps: steps || [],
    }),
  });
}

/**
 * Run step-sequence audit for a lesson already in DB.
 * @param {string} lessonId
 * @param {{ grade, subject, chapter }} opts
 */
export async function getStepAnalysis(lessonId, { grade, subject, chapter } = {}) {
  const params = new URLSearchParams();
  if (grade)   params.set("grade",   grade);
  if (subject) params.set("subject", subject);
  if (chapter) params.set("chapter", chapter);
  const qs = params.toString() ? `?${params.toString()}` : "";
  return authFetch(`${BASE}/step-analysis/${lessonId}${qs}`);
}

// ── Bulk Apply ────────────────────────────────────────────────────────────────

/**
 * Dry-run: analyse eligibility without publishing.
 * @param {{ scope, task_ids, grade, subject, chapter, min_score, min_depth_score }} opts
 */
export async function bulkDryRun(opts = {}) {
  return authFetch(`${BASE}/bulk-dry-run`, {
    method: "POST",
    body: JSON.stringify({
      scope: opts.scope || "selected",
      task_ids: opts.task_ids || [],
      grade: opts.grade || null,
      subject: opts.subject || null,
      chapter: opts.chapter || null,
      min_score: opts.min_score ?? 90,
      min_depth_score: opts.min_depth_score ?? 85,
      dry_run: true,
    }),
  });
}

/**
 * Apply all eligible repair tasks.
 * @param {{ scope, task_ids, grade, subject, chapter, min_score, min_depth_score }} opts
 */
export async function bulkApply(opts = {}) {
  return authFetch(`${BASE}/bulk-apply`, {
    method: "POST",
    body: JSON.stringify({
      scope: opts.scope || "selected",
      task_ids: opts.task_ids || [],
      grade: opts.grade || null,
      subject: opts.subject || null,
      chapter: opts.chapter || null,
      min_score: opts.min_score ?? 90,
      min_depth_score: opts.min_depth_score ?? 85,
      dry_run: false,
    }),
  });
}
