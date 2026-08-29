import { authFetch } from "./authClient";

export async function getPrincipalSchool() {
  /** School profile: name, join code, verification status, tier. */
  return authFetch("/api/principal/school", { method: "GET" });
}

export async function getPrincipalDashboardSummary() {
  /** Overview-tab KPIs: teacher/student counts, free-vs-paid split, tier. */
  return authFetch("/api/principal/dashboard-summary", { method: "GET" });
}

export async function listPrincipalTeachers() {
  /** Teacher roster with assigned-student counts. */
  return authFetch("/api/principal/teachers", { method: "GET" });
}

export async function linkTeacherToSchool(email) {
  /** Link an existing teacher account by email — never creates a login. */
  return authFetch("/api/principal/teachers/link", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export async function unlinkTeacherFromSchool(teacherId) {
  /** Remove a teacher from the roster — only clears their school link. */
  return authFetch(`/api/principal/teachers/${teacherId}`, { method: "DELETE" });
}

export async function listPrincipalStudents(tier = "") {
  /** Student roster, optionally filtered by tier: "free" | "paid" | "". */
  const params = tier ? `?tier=${encodeURIComponent(tier)}` : "";
  return authFetch(`/api/principal/students${params}`, { method: "GET" });
}

export async function linkStudentToSchool(email) {
  /** Link an existing student account by email — never creates a login. */
  return authFetch("/api/principal/students/link", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export async function unlinkStudentFromSchool(studentId) {
  /** Remove a student from the roster — only clears their school link. */
  return authFetch(`/api/principal/students/${studentId}`, { method: "DELETE" });
}

export async function getPrincipalIncentives() {
  /** Tier, progress to next tier, unlocked rewards, redemption history. */
  return authFetch("/api/principal/incentives", { method: "GET" });
}

export async function redeemPrincipalReward(rewardKey) {
  /** Request a reward unlocked at the school's current tier. */
  return authFetch("/api/principal/incentives/redeem", {
    method: "POST",
    body: JSON.stringify({ reward_key: rewardKey }),
  });
}
