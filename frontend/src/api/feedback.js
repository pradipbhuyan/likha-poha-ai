import { authFetch } from "./authClient";

// ── Student/user ──────────────────────────────────────────────────────────

export function getFeedbackEligibility() {
  return authFetch("/api/feedback/eligibility");
}

export function markFeedbackPromptShown() {
  return authFetch("/api/feedback/prompt-shown", { method: "POST" });
}

export function submitFeedback(body) {
  return authFetch("/api/feedback/report", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function getMyFeedback() {
  return authFetch("/api/feedback/mine");
}

// ── Admin: feedback triage ───────────────────────────────────────────────

export function adminListFeedback(filters = {}) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => { if (v) params.append(k, v); });
  return authFetch(`/api/admin/feedback?${params.toString()}`);
}

export function adminFeedbackSummary() {
  return authFetch("/api/admin/feedback/summary");
}

export function adminUpdateFeedback(id, body) {
  return authFetch(`/api/admin/feedback/${id}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

// ── Admin: tech debt backlog ─────────────────────────────────────────────

export function adminCreateTechDebt(body) {
  return authFetch("/api/admin/tech-debt", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function adminListTechDebt(filters = {}) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => { if (v) params.append(k, v); });
  return authFetch(`/api/admin/tech-debt?${params.toString()}`);
}

export function adminTechDebtSummary() {
  return authFetch("/api/admin/tech-debt/summary");
}

export function adminReviewTechDebt(id, body) {
  return authFetch(`/api/admin/tech-debt/${id}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}
