import { authFetch } from "./authClient";

export async function getTeacherDashboardSummary() {
  /** Load assigned students, progress, usage, notes, and student limit. */
  return authFetch("/api/teacher-dashboard/summary", { method: "GET" });
}

export async function getTeacherStudentLimit() {
  /** Return { count, max, is_paid, at_limit } for the signed-in teacher. */
  return authFetch("/api/teacher-dashboard/student-limit", { method: "GET" });
}

export async function createTeacherStudent(payload) {
  /**
   * Create a new student and auto-assign them to this teacher.
   * payload: { username, grade, password, email?, subject?, section? }
   * The password is sent over HTTPS and hashed by Supabase — never returned.
   */
  return authFetch("/api/teacher-dashboard/create-student", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function emailStudentCredentials(studentId) {
  /**
   * Send a Supabase password-reset link to a student's real email.
   * Paid teachers only — backend enforces this.
   */
  return authFetch(`/api/teacher-dashboard/email-credentials/${studentId}`, {
    method: "POST",
  });
}

export async function createTeacherNote(payload) {
  /** Create a teacher note for an assigned student. */
  return authFetch("/api/teacher-dashboard/notes", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// ── Admin: parent-child association ──────────────────────────────────────────

export async function searchUsers(q, role = "") {
  /** Search users by username/email. role: "parent" | "student" | "" (all) */
  const params = new URLSearchParams({ q: q || "", role });
  return authFetch(`/api/admin-control/search-users?${params}`, { method: "GET" });
}

export async function listParentChildAssociations(q = "") {
  /** Return all parent-child links (admin only). */
  const params = new URLSearchParams({ q });
  return authFetch(`/api/admin-control/parent-child-associations?${params}`, { method: "GET" });
}

export async function linkParentToChild(parentId, childId) {
  /** Associate a parent with a student (admin only). */
  return authFetch("/api/admin-control/link-parent-child", {
    method: "POST",
    body: JSON.stringify({ parent_id: parentId, child_id: childId }),
  });
}

export async function unlinkParentFromChild(childId) {
  /** Remove a parent-child association (admin only). */
  return authFetch(`/api/admin-control/link-parent-child/${childId}`, {
    method: "DELETE",
  });
}
