import { authFetch } from "./authClient";

export async function getCacheStatus(accessToken) {
  /** Load grade-by-grade lesson cache and question bank status. */
  return authFetch("/api/cache-management/status", {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
}

export async function startLessonPrewarm(gradeSlug, accessToken) {
  /** Start background lesson pre-warming for a grade. */
  return authFetch(`/api/cache-management/prewarm/lessons/${gradeSlug}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${accessToken}` },
  });
}

export async function startQuestionBankBuild(gradeSlug, accessToken) {
  /** Start background question bank building for a grade. */
  return authFetch(`/api/cache-management/prewarm/questions/${gradeSlug}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${accessToken}` },
  });
}

export async function clearLessonCache(gradeSlug, accessToken) {
  /** Delete all cached lessons for a grade. */
  return authFetch(`/api/cache-management/cache/lessons/${gradeSlug}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${accessToken}` },
  });
}

export async function clearQuestionBank(gradeSlug, accessToken) {
  /** Delete all question bank entries for a grade. */
  return authFetch(`/api/cache-management/cache/questions/${gradeSlug}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${accessToken}` },
  });
}
