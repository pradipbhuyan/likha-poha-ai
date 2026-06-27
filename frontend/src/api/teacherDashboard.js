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

// ─────────────────────────────────────────────────────────────────────────────
// Teacher Success Platform — Phase 1  (/api/teacher/*)
// ─────────────────────────────────────────────────────────────────────────────

export async function getTeacherClassroomSummary() {
  /** Classroom KPI dashboard cards — counts, averages, attention list. */
  return authFetch("/api/teacher/dashboard/summary", { method: "GET" });
}

// ── Students ──────────────────────────────────────────────────────────────────

export async function listTeacherStudents({ q, grade, status, sort } = {}) {
  /** Roster with optional search/filter/sort. */
  const params = new URLSearchParams();
  if (q)      params.set("q", q);
  if (grade)  params.set("grade", grade);
  if (status) params.set("status", status);
  if (sort)   params.set("sort", sort);
  const qs = params.toString() ? `?${params}` : "";
  return authFetch(`/api/teacher/students${qs}`, { method: "GET" });
}

export async function getTeacherStudentDetail(studentId) {
  /** Full student profile + learning signals. */
  return authFetch(`/api/teacher/students/${studentId}`, { method: "GET" });
}

export async function updateTeacherStudent(studentId, payload) {
  /** PATCH name/grade/email for an assigned student. */
  return authFetch(`/api/teacher/students/${studentId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function archiveTeacherStudent(studentId) {
  /** Soft-archive a student from the teacher's roster. */
  return authFetch(`/api/teacher/students/${studentId}/archive`, { method: "POST" });
}

export async function resetTeacherStudentPassword(studentId) {
  /**
   * Generate and return a new temp password (shown once only).
   * Never stored or logged.
   */
  return authFetch(`/api/teacher/students/${studentId}/reset-password`, { method: "POST" });
}

export async function emailTeacherStudentCredentials(studentId) {
  /** Email login credentials — paid teachers only (backend enforces). */
  return authFetch(`/api/teacher/students/${studentId}/email-credentials`, { method: "POST" });
}

// ── Invitations ───────────────────────────────────────────────────────────────

export async function listTeacherInvitations(status = null) {
  /** List invitations, optionally filtered by status. */
  const qs = status ? `?status=${encodeURIComponent(status)}` : "";
  return authFetch(`/api/teacher/invitations${qs}`, { method: "GET" });
}

export async function createTeacherInvitation(payload) {
  /** Create a new student invitation. payload: { student_name, grade, email } */
  return authFetch("/api/teacher/invitations", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function resendTeacherInvitation(invitationId) {
  /** Resend and extend expiry of a pending/expired invitation. */
  return authFetch(`/api/teacher/invitations/${invitationId}/resend`, { method: "POST" });
}

export async function cancelTeacherInvitation(invitationId) {
  /** Cancel a pending invitation. */
  return authFetch(`/api/teacher/invitations/${invitationId}/cancel`, { method: "POST" });
}

// ── Classrooms ────────────────────────────────────────────────────────────────

export async function listTeacherClassrooms(status = "active") {
  /** List classrooms with student counts. */
  return authFetch(`/api/teacher/classrooms?status=${encodeURIComponent(status)}`, { method: "GET" });
}

export async function createTeacherClassroom(payload) {
  /** Create a new classroom. payload: { name, description? } */
  return authFetch("/api/teacher/classrooms", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateTeacherClassroom(classroomId, payload) {
  /** Rename or update description. payload: { name?, description? } */
  return authFetch(`/api/teacher/classrooms/${classroomId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function archiveTeacherClassroom(classroomId) {
  /** Archive a classroom. */
  return authFetch(`/api/teacher/classrooms/${classroomId}/archive`, { method: "POST" });
}

export async function addStudentToClassroom(classroomId, studentId) {
  /** Add an assigned student to a classroom. */
  return authFetch(`/api/teacher/classrooms/${classroomId}/students`, {
    method: "POST",
    body: JSON.stringify({ student_id: studentId }),
  });
}

export async function removeStudentFromClassroom(classroomId, studentId) {
  /** Remove a student from a classroom. */
  return authFetch(`/api/teacher/classrooms/${classroomId}/students/${studentId}`, {
    method: "DELETE",
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
