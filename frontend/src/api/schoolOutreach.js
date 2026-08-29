import { authFetch } from "./authClient";

export async function getOutreachSummary() {
  /** Campaign-wide counts: pending, sent, failed, sent_today, reminders_sent, responded. */
  return authFetch("/api/admin/outreach/summary", { method: "GET" });
}

export async function listOutreachPrincipals({ status = "", needsReminder = false, q = "", state = "", limit = 50, offset = 0 } = {}) {
  /** Paginated, filterable roster for the selection table. */
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  if (needsReminder) params.set("needs_reminder", "true");
  if (q) params.set("q", q);
  if (state) params.set("state", state);
  params.set("limit", String(limit));
  params.set("offset", String(offset));
  return authFetch(`/api/admin/outreach/principals?${params.toString()}`, { method: "GET" });
}

export async function getOutreachStates() {
  /** The fixed list of distinct states/UTs in the imported master list, for the state filter dropdown. */
  return authFetch("/api/admin/outreach/states", { method: "GET" });
}

export async function sendOutreachEmails(emails, type = "initial") {
  /** Queues sending to the given emails in the background (~2s apart). type: "initial" | "reminder". */
  return authFetch("/api/admin/outreach/send", {
    method: "POST",
    body: JSON.stringify({ emails, type }),
  });
}

export async function markOutreachResponded(emails) {
  /** Manually flag principals as having replied, so they're skipped for reminders. */
  return authFetch("/api/admin/outreach/mark-responded", {
    method: "POST",
    body: JSON.stringify({ emails }),
  });
}
