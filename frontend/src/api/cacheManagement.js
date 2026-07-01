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

export async function getChaptersForGrade(gradeSlug, accessToken) {
  /** Load available {mode, subject, chapter} options for a grade from RAG documents. */
  return authFetch(`/api/cache-management/chapters/${gradeSlug}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
}

export async function startChapterQuestionBankBuild(payload, accessToken) {
  /**
   * Start background question bank building for one specific chapter.
   * payload: { grade, mode, subject, chapter }
   * Generates 60 RAG-grounded questions (20 Easy + 20 Medium + 20 Hard).
   */
  return authFetch("/api/cache-management/build-questions/chapter", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function startChapterPrewarm(payload, accessToken) {
  /**
   * Start background lesson pre-warming for one specific chapter.
   * payload: { grade, mode, subject, chapter }
   */
  return authFetch("/api/cache-management/prewarm/chapter", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function startDoubtKbPrewarm(gradeSlug, accessToken) {
  /** Start background Doubt Knowledge Base pre-warming for a grade.
   *  Generates 25 pre-answered Q&A pairs per chapter using gpt-4.1-nano.
   *  Already-covered chapters are skipped — safe to re-run. */
  return authFetch(`/api/cache-management/prewarm/doubt-kb/${gradeSlug}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${accessToken}` },
  });
}

export async function getDoubtKbStats(accessToken) {
  /** Load aggregate Doubt Knowledge Base stats (total entries, hit rate, savings). */
  return authFetch("/api/cache-management/doubt-kb/stats", {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
}

export async function restoreLessonCache(gradeSlug, accessToken) {
  /** Restore archived (soft-deleted) lessons for a grade back to active status. */
  return authFetch(`/api/cache-management/cache/lessons/${gradeSlug}/restore`, {
    method: "POST",
    headers: { Authorization: `Bearer ${accessToken}` },
  });
}

// ── LKB (Lesson Knowledge Base) ───────────────────────────────────────────────

export async function startLkbBuild(gradeSlug, accessToken) {
  /** Trigger LKB chip generation for an entire grade (background thread). */
  return authFetch(`/api/cache-management/prewarm/lkb/${gradeSlug}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${accessToken}` },
  });
}

export async function startLkbChapterBuild({ grade, subject, chapter }, accessToken) {
  /** Trigger LKB chip generation for a single chapter. */
  return authFetch("/api/cache-management/prewarm/lkb/chapter", {
    method: "POST",
    headers: { Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify({ grade, subject, chapter }),
  });
}

export async function getLkbOverview(gradeSlug, accessToken) {
  /** Return LKB chip counts and chapter completion status for a grade. */
  return authFetch(`/api/cache-management/lkb/overview/${gradeSlug}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
}
