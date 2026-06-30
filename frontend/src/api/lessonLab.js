/**
 * lessonLab.js — Admin Lesson Experience Lab API client
 * All endpoints are admin-only. Non-admins receive 403.
 * No writes — read-only preview operations.
 */
import { authFetch } from "./authClient";

const BASE = "/api/admin/lesson-lab";

/** List lessons with optional grade/subject/chapter filters */
export async function listLabLessons({ grade, subject, chapter } = {}) {
  const params = new URLSearchParams();
  if (grade)   params.set("grade",   grade);
  if (subject) params.set("subject", subject);
  if (chapter) params.set("chapter", chapter);
  const qs = params.toString() ? `?${params}` : "";
  return authFetch(`${BASE}/lessons${qs}`);
}

/** Get full normalized lesson detail */
export async function getLabLesson(lessonId, { grade, subject, chapter } = {}) {
  const params = new URLSearchParams();
  if (grade)   params.set("grade",   grade);
  if (subject) params.set("subject", subject);
  if (chapter) params.set("chapter", chapter);
  const qs = params.toString() ? `?${params}` : "";
  return authFetch(`${BASE}/lesson/${encodeURIComponent(lessonId)}${qs}`);
}

/**
 * Preview-only transform — never saves content.
 * @param {{ lesson_id, mode, use_llm, grade, subject, chapter }} opts
 */
export async function previewTransform(opts = {}) {
  return authFetch(`${BASE}/preview-transform`, {
    method: "POST",
    body: JSON.stringify({
      lesson_id:  opts.lesson_id || "",
      mode:       opts.mode || "structure_only",
      use_llm:    !!opts.use_llm,
      grade:      opts.grade   || null,
      subject:    opts.subject || null,
      chapter:    opts.chapter || null,
    }),
  });
}

// ── Repair-with-AI ────────────────────────────────────────────────────────────

/**
 * Generate an AI repair draft for a single step (preview only — never publishes).
 */
export async function repairStepPreview({
  lesson_id, grade, subject, chapter,
  step_number, step_title, step_content,
  all_step_contents, audit_issues,
  previous_step_content, next_step_content,
  use_llm = true, override_api_key,
} = {}) {
  return authFetch(`${BASE}/repair-step-preview`, {
    method: "POST",
    body: JSON.stringify({
      lesson_id: lesson_id || "",
      grade: grade || "", subject: subject || "", chapter: chapter || "",
      step_number: step_number || 1,
      step_title: step_title || "",
      step_content: step_content || "",
      all_step_contents: all_step_contents || [],
      audit_issues: audit_issues || [],
      previous_step_content: previous_step_content || "",
      next_step_content: next_step_content || "",
      use_llm: !!use_llm,
      override_api_key: override_api_key || null,
    }),
  });
}

/** Approve a repair task generated from Lesson Lab */
export async function repairStepApprove(taskId) {
  return authFetch(`${BASE}/repair-step-approve`, {
    method: "POST",
    body: JSON.stringify({ task_id: taskId }),
  });
}

/** Publish an approved repair task to lesson_cache */
export async function repairStepPublish(taskId) {
  return authFetch(`${BASE}/repair-step-publish`, {
    method: "POST",
    body: JSON.stringify({ task_id: taskId }),
  });
}

/** Get available textbook visuals for a lesson context */
export async function getLabVisuals({ grade, subject, chapter, lesson_id } = {}) {
  const params = new URLSearchParams();
  if (grade)     params.set("grade",     grade);
  if (subject)   params.set("subject",   subject);
  if (chapter)   params.set("chapter",   chapter);
  if (lesson_id) params.set("lesson_id", lesson_id);
  const qs = params.toString() ? `?${params}` : "";
  return authFetch(`${BASE}/visuals${qs}`);
}
