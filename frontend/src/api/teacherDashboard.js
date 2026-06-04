import { authFetch } from "./authClient";

export async function getTeacherDashboardSummary() {
  /** Load assigned students, progress, usage, and notes for the signed-in teacher. */
  return authFetch("/api/teacher-dashboard/summary", {
    method: "GET",
  });
}

export async function createTeacherNote(payload) {
  /** Create a teacher note for an assigned student. */
  return authFetch("/api/teacher-dashboard/notes", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
