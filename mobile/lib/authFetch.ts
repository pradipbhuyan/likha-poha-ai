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
  // Normalize detail to string — FastAPI can return detail as array (422), object, or string
  const rawDetail = body?.detail;
  const detail = typeof rawDetail === "string"
    ? rawDetail
    : Array.isArray(rawDetail)
      ? rawDetail.map((e: any) => e?.msg ?? String(e)).join("; ")
      : rawDetail != null ? String(rawDetail) : "";

  if (status === 401) return "Your session has expired. Please sign in again.";
  if (status === 403) {
    const d = detail.toLowerCase();
    if (d.includes("parent")) return "This account is not registered as a Parent.";
    if (d.includes("student")) return "This account is not registered as a Student.";
    if (d.includes("teacher")) return "This account is not registered as a Teacher.";
    if (d.includes("exemplar") || d.includes("feature") || d.includes("access")) return "Exemplar is available on Premium plans. Upgrade to unlock.";
    return "This account does not have access to this page.";
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
