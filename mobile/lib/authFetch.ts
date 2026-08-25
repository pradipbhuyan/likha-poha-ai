/**
 * Authenticated fetch for the Likha Poha AI mobile app.
 *
 * Mobile equivalent of frontend/src/api/authClient.js:
 * - Gets the current Supabase session token
 * - Adds Authorization: Bearer <token> header
 * - Maps HTTP status codes to user-friendly error messages
 *   (same mapping as the web: 401 = expired, 403 = role mismatch)
 *
 * Usage:
 *   const data = await authFetch("/api/student/dashboard/summary");
 */
import { supabase } from "./supabase";
import { API_BASE_URL } from "../constants";

function friendlyError(status: number, body: any): string {
  // Normalize detail to string — FastAPI can return detail as array (422), a
  // structured object (403s from require_feature()/entitlement gates use
  // {feature, message, upgrade_message, ...}), or a plain string (403s from
  // require_parent()/require_student()-style role dependencies).
  const rawDetail = body?.detail;
  const isStructured = rawDetail !== null && typeof rawDetail === "object" && !Array.isArray(rawDetail);
  const detail = typeof rawDetail === "string"
    ? rawDetail
    : Array.isArray(rawDetail)
      ? rawDetail.map((e: any) => e?.msg ?? String(e)).join("; ")
      : isStructured
        ? String(rawDetail.message || rawDetail.upgrade_message || "")
        : rawDetail != null ? String(rawDetail) : "";

  if (status === 401) return "Your session has expired. Please sign in again.";
  if (status === 403) {
    // Structured 403s (feature/entitlement gates, e.g. Exemplar Research)
    // already carry a specific, correct message from the backend — trust it
    // rather than re-guessing from a keyword match. A previous version of
    // this function stringified the whole object (producing "[object
    // Object]"), then guessed wrong from that string, showing an unrelated
    // paid-plan message ("Exemplar is available on Premium plans") sourced
    // from a different feature than the one that actually denied the request.
    if (isStructured && detail) return detail;
    const d = detail.toLowerCase();
    if (d.includes("parent")) return "This account is not registered as a Parent.";
    if (d.includes("student")) return "This account is not registered as a Student.";
    if (d.includes("teacher")) return "This account is not registered as a Teacher.";
    return detail || "This account does not have access to this page.";
  }
  if (status === 402) return "This feature requires a Premium subscription.";
  if (status === 409) return detail || "Conflict error.";
  if (status >= 500) return "We're having trouble right now. Please try again in a moment.";
  return detail || body?.message || `Request failed (${status})`;
}

export async function authFetch(
  path: string,
  options: RequestInit = {}
): Promise<any> {
  const { data: { session } } = await supabase.auth.getSession();
  const token = session?.access_token;
  if (!token) throw new Error("Your session has expired. Please sign in again.");

  const url = path.startsWith("http") ? path : `${API_BASE_URL}${path}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...(options.headers ?? {}),
    },
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(friendlyError(res.status, body));
  }

  return res.json();
}
