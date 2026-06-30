/**
 * lessonExperience.js — Admin Lesson Experience API client
 * Admin-only. Read-only. Uses latest published lesson content.
 */
import { authFetch } from "./authClient";

const BASE = "/api/admin/lesson-experience";

/** Get the full lesson hierarchy (grades → subjects → chapters → lessons) */
export async function getLessonCatalog({ grade, subject, chapter } = {}) {
  const params = new URLSearchParams();
  if (grade)   params.set("grade",   grade);
  if (subject) params.set("subject", subject);
  if (chapter) params.set("chapter", chapter);
  const qs = params.toString() ? `?${params}` : "";
  return authFetch(`${BASE}/catalog${qs}`);
}

/** Get full lesson detail including normalized steps */
export async function getLessonDetail(lessonId, { grade, subject, chapter } = {}) {
  const params = new URLSearchParams();
  if (grade)   params.set("grade",   grade);
  if (subject) params.set("subject", subject);
  if (chapter) params.set("chapter", chapter);
  const qs = params.toString() ? `?${params}` : "";
  return authFetch(`${BASE}/lesson/${encodeURIComponent(lessonId)}${qs}`);
}

/** Get linked textbook visuals for the current lesson context */
export async function getLessonVisuals({ grade, subject, chapter, lesson_id } = {}) {
  const params = new URLSearchParams();
  if (grade)     params.set("grade",     grade);
  if (subject)   params.set("subject",   subject);
  if (chapter)   params.set("chapter",   chapter);
  if (lesson_id) params.set("lesson_id", lesson_id);
  const qs = params.toString() ? `?${params}` : "";
  return authFetch(`${BASE}/visuals${qs}`);
}
