/**
 * oauthDiagnostics.js — OAuth Stage Tracking & Correlation ID
 *
 * Provides:
 *  - Correlation ID generation/persistence in sessionStorage
 *  - Stage recording with timestamps (never records tokens/codes)
 *  - Safe diagnostic display for the error panel
 *
 * SECURITY CONTRACT:
 *  - NEVER record: access_token, refresh_token, authorization code, provider secrets
 *  - Safe to record: stage name, status, user-friendly message, error_code, correlation_id
 */

// ── OAuth stage names ─────────────────────────────────────────────────────────
export const STAGES = {
  CALLBACK_RECEIVED:          "callback_received",
  CALLBACK_PARAMS_DETECTED:   "callback_params_detected",
  SESSION_EXCHANGE_STARTED:   "session_exchange_started",
  SESSION_EXCHANGE_COMPLETED: "session_exchange_completed",
  SESSION_DETECTED:           "session_detected",
  ACCESS_TOKEN_DETECTED:      "access_token_detected",
  AUTH_ME_STARTED:            "auth_me_started",
  AUTH_ME_COMPLETED:          "auth_me_completed",
  PROFILE_COMPLETE_CHECKED:   "profile_complete_checked",
  ROUTE_RESOLVED:             "route_resolved",
  NAVIGATION_STARTED:         "navigation_started",
  NAVIGATION_COMPLETED:       "navigation_completed",
  FAILED:                     "failed",
};

// ── Status values ─────────────────────────────────────────────────────────────
export const STATUS = {
  PENDING: "pending",
  SUCCESS: "success",
  FAILED:  "failed",
  SKIPPED: "skipped",
};

// ── In-memory stage log (not persisted — cleared on page reload) ──────────────
let _stages = [];
let _correlationId = null;

// ── Correlation ID ────────────────────────────────────────────────────────────

/**
 * Generate a short, URL-safe correlation ID.
 * Format: oauth-{timestamp}-{random6}
 * Never contains any auth tokens or codes.
 */
function _generateCorrelationId() {
  const ts = Date.now().toString(36);
  const rnd = Math.random().toString(36).slice(2, 8);
  return `oauth-${ts}-${rnd}`;
}

/**
 * Get or create the correlation ID for the current OAuth flow.
 * On a fresh callback: reads from sessionStorage (set before redirect) or creates new.
 * Stores the ID in sessionStorage for the duration of this browser session.
 */
export function getOrCreateCorrelationId() {
  if (_correlationId) return _correlationId;

  // Try to restore from sessionStorage (set by initiateOAuth before redirect)
  try {
    const stored = sessionStorage.getItem("oauth_correlation_id");
    if (stored && stored.startsWith("oauth-")) {
      _correlationId = stored;
      return _correlationId;
    }
  } catch { /* sessionStorage not available — likely private browsing */ }

  // Generate a new one
  _correlationId = _generateCorrelationId();
  try {
    sessionStorage.setItem("oauth_correlation_id", _correlationId);
  } catch { /* ignore */ }
  return _correlationId;
}

/**
 * Store correlation ID before triggering OAuth redirect.
 * Call this from your signInWithOAuth() wrapper.
 */
export function storeCorrelationIdBeforeRedirect(opts = {}) {
  const id = _generateCorrelationId();
  _correlationId = id;
  try {
    sessionStorage.setItem("oauth_correlation_id", id);
    sessionStorage.setItem("oauth_started_at", new Date().toISOString());
    if (opts.returnTo) {
      sessionStorage.setItem("oauth_return_to", opts.returnTo);
    }
  } catch { /* ignore */ }
  return id;
}

/**
 * Clear correlation ID and all OAuth session storage keys.
 * Call after successful login or after error dismiss.
 */
export function clearOAuthSession() {
  _correlationId = null;
  _stages = [];
  try {
    sessionStorage.removeItem("oauth_correlation_id");
    sessionStorage.removeItem("oauth_started_at");
    sessionStorage.removeItem("oauth_return_to");
  } catch { /* ignore */ }
}

// ── Stage recording ───────────────────────────────────────────────────────────

/**
 * Record an OAuth processing stage.
 *
 * @param {string} stage       - One of STAGES.*
 * @param {string} status      - One of STATUS.*
 * @param {string} message     - User-safe description (no tokens)
 * @param {string} [errorCode] - Machine-readable error code (no tokens)
 */
export function recordStage(stage, status, message = "", errorCode = null) {
  const entry = {
    stage,
    status,
    message,
    error_code: errorCode || null,
    timestamp: new Date().toISOString(),
    correlation_id: getOrCreateCorrelationId(),
  };
  _stages.push(entry);

  // Console log for developer visibility (safe — no tokens)
  if (status === STATUS.FAILED) {
    console.error(`[oauth:${stage}] FAILED — ${errorCode || "unknown"}: ${message}`);
  } else {
    console.info(`[oauth:${stage}] ${status}: ${message}`);
  }

  return entry;
}

/**
 * Get all recorded stages for display in the error panel.
 * Safe to show to users — never includes tokens.
 */
export function getStages() {
  return [..._stages];
}

/**
 * Reset stage log (call at the start of each fresh callback).
 */
export function resetStages() {
  _stages = [];
}

/**
 * Get the last failed stage if any.
 */
export function getLastFailure() {
  return [..._stages].reverse().find(s => s.status === STATUS.FAILED) || null;
}

// ── Callback URL inspection ───────────────────────────────────────────────────

/**
 * Inspect the current URL for OAuth callback parameters.
 * Returns a safe summary — NEVER returns the raw code/token values.
 *
 * @returns {{
 *   hasCode: boolean,
 *   hasError: boolean,
 *   hasAccessToken: boolean,
 *   hasState: boolean,
 *   errorParam: string | null,
 *   errorDescription: string | null,
 *   isOAuthCallback: boolean,
 * }}
 */
export function inspectCallbackUrl(url = window.location.href) {
  let search;
  let hash;

  try {
    const parsed = new URL(url);
    search = parsed.search || "";
    hash = parsed.hash || "";
  } catch {
    search = window.location.search || "";
    hash = window.location.hash || "";
  }

  // Parse both query string and hash fragment
  const parseParams = (str) => {
    if (!str) return new URLSearchParams();
    return new URLSearchParams(str.startsWith("?") || str.startsWith("#") ? str.slice(1) : str);
  };

  const qp = parseParams(search);
  const hp = parseParams(hash);

  const get = (key) => qp.get(key) || hp.get(key);

  const errorParam = get("error");
  const errorDescription = get("error_description");

  return {
    hasCode: !!get("code"),
    hasError: !!errorParam,
    hasAccessToken: !!get("access_token"),
    hasState: !!get("state"),
    errorParam,                                    // safe — not a secret
    errorDescription,                              // safe — not a secret
    isOAuthCallback: !!(get("code") || get("error") || get("access_token")),
  };
}

// ── Human-readable error mapping ──────────────────────────────────────────────

const ERROR_CODE_MESSAGES = {
  // Provider errors
  oauth_cancelled:              "Google sign-in was cancelled. Please try again.",
  oauth_access_denied:          "Google sign-in was denied. Please allow access and try again.",
  oauth_error:                  "Google sign-in encountered an error. Please try again.",

  // Session errors
  oauth_session_missing:        "A secure session could not be established. Please try signing in again.",
  oauth_access_token_missing:   "We could not retrieve your session credentials. Please try again.",
  oauth_exchange_failed:        "Secure login handshake failed. Please try again.",

  // Profile errors
  oauth_profile_missing:        "We could not load your profile. Please try again.",
  oauth_role_conflict:          "This Google account is already registered with a different role.",
  oauth_needs_role_selection:   "Please select your role to complete sign-in.",

  // Backend errors
  auth_me_failed:               "We could not verify your account. Please try again.",
  auth_me_unauthorized:         "Your session could not be verified. Please sign in again.",
  auth_me_network:              "Connection issue. Please check your network and try again.",

  // Generic
  unknown:                      "An unexpected error occurred. Please try again.",
};

/**
 * Get a user-friendly error message from an error code.
 */
export function getErrorMessage(errorCode) {
  if (!errorCode) return ERROR_CODE_MESSAGES.unknown;

  // Check for OAuth provider error param (e.g. "access_denied")
  if (errorCode.includes("access_denied") || errorCode.includes("denied")) {
    return ERROR_CODE_MESSAGES.oauth_access_denied;
  }
  if (errorCode.includes("cancelled") || errorCode.includes("canceled")) {
    return ERROR_CODE_MESSAGES.oauth_cancelled;
  }

  return ERROR_CODE_MESSAGES[errorCode] || ERROR_CODE_MESSAGES.unknown;
}

/**
 * Map a provider error param to an internal error code.
 */
export function mapProviderError(errorParam, errorDescription = "") {
  if (!errorParam) return null;
  const e = errorParam.toLowerCase();
  const d = (errorDescription || "").toLowerCase();

  if (e === "access_denied" || d.includes("denied")) return "oauth_access_denied";
  if (e === "cancelled" || e === "canceled") return "oauth_cancelled";
  return "oauth_error";
}
