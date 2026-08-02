import { supabase } from "./supabaseClient";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export async function authFetch(path, options = {}) {
  /**
   * Call a protected backend endpoint with the current Supabase bearer token.
   *
   * Error messages are always user-friendly.
   * Technical details (JWT, Supabase internals) are only logged to console.
   * FormData requests intentionally omit Content-Type so the browser can attach
   * the multipart boundary.
   */
  const { data, error } = await supabase.auth.getSession();

  if (error) {
    console.error("[auth] Session read error:", error.message);
    throw new Error("Your session could not be read. Please sign in again.");
  }

  let token = data.session?.access_token;

  if (!token) {
    // First attempt: try a refresh
    const refreshed = await supabase.auth.refreshSession();
    token = refreshed.data.session?.access_token;
  }

  if (!token) {
    // Second attempt: wait and retry — handles post-OAuth window for new parent/student
    // Role/grade selection + handleLogin may take time before session is stored
    await new Promise(r => setTimeout(r, 800));
    const { data: retryData } = await supabase.auth.getSession();
    token = retryData.session?.access_token;
    if (!token) {
      const retryRefreshed = await supabase.auth.refreshSession();
      token = retryRefreshed.data.session?.access_token;
    }
  }

  if (!token) {
    // Third attempt: additional 1200ms — for parent flow where subscriptionPlans
    // page makes authFetch calls very soon after handleLogin completes
    await new Promise(r => setTimeout(r, 1200));
    const { data: retryData3 } = await supabase.auth.getSession();
    token = retryData3.session?.access_token;
    if (!token) {
      const retryRefreshed3 = await supabase.auth.refreshSession();
      token = retryRefreshed3.data.session?.access_token;
    }
  }

  if (!token) {
    console.error("[auth] No access token available after all retry attempts");
    throw new Error("Your session has expired. Please sign in again.");
  }

  const isFormData = options.body instanceof FormData;

  const headers = {
    ...(!isFormData ? { "Content-Type": "application/json" } : {}),
    ...(options.headers || {}),
    Authorization: `Bearer ${token}`,
  };

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let message = "Something went wrong. Please try again.";

    try {
      const errorData = await response.json();
      const rawDetail = errorData.detail || errorData.message || "";

      if (response.status === 401) {
        // 401 = genuinely expired / invalid session token
        message = "Your session has expired. Please sign in again.";
        console.error("[auth] Session expired/invalid token:", rawDetail);

      } else if (response.status === 403) {
        // 403 = authenticated but wrong role — NOT a session expiry.
        // Map to a role-specific friendly message so the user understands
        // the problem and doesn't wrongly think they need to log in again.
        const detail = (rawDetail || "").toLowerCase();
        if (detail.includes("parent")) {
          message = "This account is not registered as a Parent. Please sign in with a Parent account.";
        } else if (detail.includes("student")) {
          message = "Student access is required for this feature. Please sign in with a student account.";
        } else if (detail.includes("teacher")) {
          message = "This account is not registered as a Teacher. Please sign in with a Teacher account.";
        } else if (detail.includes("admin")) {
          message = "This account does not have admin access.";
        } else {
          message = "This account does not have access to this page.";
        }
        console.error("[auth] Access denied (role mismatch):", rawDetail);

      } else if (response.status === 409) {
        // 409 = conflict (e.g. role conflict for OAuth users) — safe to show
        if (
          rawDetail &&
          !rawDetail.toLowerCase().includes("supabase") &&
          !rawDetail.toLowerCase().includes("token") &&
          !rawDetail.toLowerCase().includes("jwt")
        ) {
          message = rawDetail;
        } else {
          message = "Account conflict. Please contact support.";
        }
        console.error("[auth] Conflict:", rawDetail);

      } else if (response.status === 404) {
        message = rawDetail || "The requested resource was not found.";

      } else if (response.status >= 500) {
        message = "We're having trouble right now. Please try again in a moment.";
        console.error("[api] Server error:", rawDetail);

      } else if (
        rawDetail &&
        !rawDetail.toLowerCase().includes("supabase") &&
        !rawDetail.toLowerCase().includes("token") &&
        !rawDetail.toLowerCase().includes("jwt") &&
        !rawDetail.toLowerCase().includes("bearer")
      ) {
        // Safe to show: does not contain auth internals
        message = rawDetail;
      } else if (rawDetail) {
        // Contains auth internals — log but don't expose to user
        console.error("[api] API error (sanitized for user):", rawDetail);
      }
    } catch {
      try {
        const errorText = await response.text();
        if (
          errorText &&
          !errorText.includes("token") &&
          !errorText.includes("JWT") &&
          !errorText.includes("Supabase")
        ) {
          message = errorText;
        }
        console.error("[api] Non-JSON error:", errorText);
      } catch { /* ignore */ }
    }

    const err = new Error(message);
    err.status = response.status;
    throw err;
  }

  return response.json();
}
