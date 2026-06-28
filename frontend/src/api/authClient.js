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
    const refreshed = await supabase.auth.refreshSession();
    token = refreshed.data.session?.access_token;
  }

  if (!token) {
    console.error("[auth] No access token available after refresh attempt");
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
    let rawDetail = "";

    try {
      const errorData = await response.json();
      rawDetail = errorData.detail || errorData.message || "";

      if (response.status === 401 || response.status === 403) {
        // Auth errors: never show raw token/JWT details to user
        message = "Your session has expired. Please sign in again.";
        console.error("[auth] Unauthorized:", rawDetail);
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

    throw new Error(message);
  }

  return response.json();
}
