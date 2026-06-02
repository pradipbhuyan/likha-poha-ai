import { authFetch } from "./authClient";

export async function getFamily() {
  return authFetch("/api/parent-dashboard/family", {
    method: "GET",
  });
}

export async function getParentChildren() {
  return authFetch("/api/parent-dashboard/children", {
    method: "GET",
  });
}

export async function getParentChild(childId) {
  return authFetch(`/api/parent-dashboard/children/${childId}`, {
    method: "GET",
  });
}

export async function createStudent(payload) {
  return authFetch("/api/parent-dashboard/create-student", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function inviteParent(payload) {
  return authFetch("/api/parent-dashboard/invite-parent", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getWeakAreaAlerts(childId) {
  const response = await authFetch(
    `/api/parent-dashboard/children/${childId}/weak-area-alerts`
  );

  return response;
}