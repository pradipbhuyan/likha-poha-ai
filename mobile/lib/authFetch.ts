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
  if (status === 401) return "Your session has expired. Please sign in again.";
  if (status === 403) {
    const detail = body?.detail ?? "";
    if (detail.toLowerCase().includes("parent")) return "This account is not registered as a Parent.";
    if (detail.toLowerCase().includes("student")) return "This account is not registered as a Student.";
    if (detail.toLowerCase().includes("teacher")) return "This account is not registered as a Teacher.";
    return "This account does not have access to this page.";
  }
  if (status === 409) return body?.detail ?? "Conflict error.";
  if (status >= 500) return "We're having trouble right now. Please try again in a moment.";
  return body?.detail ?? body?.message ?? `Request failed (${status})`;
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
