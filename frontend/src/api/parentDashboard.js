import { authFetch } from "./authClient";

export async function getFamily() {
  /** Load all family members visible to the signed-in parent. */
  return authFetch("/api/parent-dashboard/family", {
    method: "GET",
  });
}

export async function getParentChildren() {
  /** Load child profiles for the signed-in parent. */
  return authFetch("/api/parent-dashboard/children", {
    method: "GET",
  });
}

export async function getParentChild(childId) {
  /** Load one child profile after backend parent/family validation. */
  return authFetch(`/api/parent-dashboard/children/${childId}`, {
    method: "GET",
  });
}

export async function createStudent(payload) {
  /** Create a child account/profile inside the signed-in parent's family. */
  return authFetch("/api/parent-dashboard/create-student", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function inviteParent(payload) {
  /** Invite another parent into the same family. */
  return authFetch("/api/parent-dashboard/invite-parent", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getWeakAreaAlerts(childId) {
  /** Load weak-area alerts for one parent-owned child profile. */
  const response = await authFetch(
    `/api/parent-dashboard/children/${childId}/weak-area-alerts`
  );

  return response;
}

export async function getParentSubscriptionPlans() {
  /** Load public subscription plans for parent purchase/upgrade UI. */
  return authFetch("/api/parent-dashboard/subscription-plans", {
    method: "GET",
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// Parent Experience Phase 1 — /api/parent/*
// ─────────────────────────────────────────────────────────────────────────────

export async function getParentDashboardSummary() {
  /** Canonical parent dashboard summary — children with subscription, features, activity, recommendations. */
  return authFetch("/api/parent/dashboard/summary", { method: "GET" });
}

export async function getChildDetail(childId) {
  /** Enriched child detail: subscription, features, progress, mock tests, recommendations. */
  return authFetch(`/api/parent/children/${childId}/detail`, { method: "GET" });
}

// ─────────────────────────────────────────────────────────────────────────────
// Parent Experience Phase 2 — /api/parent/*
// ─────────────────────────────────────────────────────────────────────────────

export async function getChildAnalytics(childId) {
  return authFetch(`/api/parent/children/${childId}/analytics`, { method: "GET" });
}
export async function getChildAcademicInsights(childId) {
  return authFetch(`/api/parent/children/${childId}/academic-insights`, { method: "GET" });
}
export async function getChildProgressReport(childId) {
  return authFetch(`/api/parent/children/${childId}/progress-report`, { method: "GET" });
}
export async function getParentNotifications(status = "all", type = "all") {
  const qs = new URLSearchParams();
  if (status !== "all") qs.set("status", status);
  if (type !== "all") qs.set("notif_type", type);
  const q = qs.toString() ? "?" + qs.toString() : "";
  return authFetch(`/api/parent/notifications${q}`, { method: "GET" });
}
export async function markNotificationRead(notificationId) {
  return authFetch(`/api/parent/notifications/${notificationId}/read`, { method: "POST" });
}
export async function markAllNotificationsRead() {
  return authFetch("/api/parent/notifications/read-all", { method: "POST" });
}
