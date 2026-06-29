/**
 * OAuthReliability.test.jsx
 *
 * Tests for the OAuth cross-device reliability layer.
 * Covers: oauthDiagnostics utilities, URL inspection, error mapping.
 * App.jsx OAuth callback logic is covered via OAuthErrorMapping.test.jsx.
 */
import { beforeEach, describe, expect, test, vi } from "vitest";

// ── Mock sessionStorage ───────────────────────────────────────────────────────
const _sessionStore = {};
const mockSessionStorage = {
  getItem: vi.fn((k) => _sessionStore[k] ?? null),
  setItem: vi.fn((k, v) => { _sessionStore[k] = v; }),
  removeItem: vi.fn((k) => { delete _sessionStore[k]; }),
};
Object.defineProperty(globalThis, "sessionStorage", { value: mockSessionStorage, writable: true });

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("oauthDiagnostics — correlation ID", () => {

  beforeEach(() => {
    vi.resetModules();
    Object.keys(_sessionStore).forEach(k => delete _sessionStore[k]);
    vi.clearAllMocks();
  });

  test("getOrCreateCorrelationId generates a new ID when none stored", async () => {
    const { getOrCreateCorrelationId } = await import("../api/oauthDiagnostics");
    const id = getOrCreateCorrelationId();
    expect(id).toMatch(/^oauth-/);
    expect(id.length).toBeGreaterThan(10);
  });

  test("getOrCreateCorrelationId returns stored ID from sessionStorage", async () => {
    _sessionStore["oauth_correlation_id"] = "oauth-abc123-xyz";
    const { getOrCreateCorrelationId } = await import("../api/oauthDiagnostics");
    const id = getOrCreateCorrelationId();
    expect(id).toBe("oauth-abc123-xyz");
  });

  test("storeCorrelationIdBeforeRedirect stores ID in sessionStorage", async () => {
    const { storeCorrelationIdBeforeRedirect } = await import("../api/oauthDiagnostics");
    const id = storeCorrelationIdBeforeRedirect();
    expect(id).toMatch(/^oauth-/);
    expect(mockSessionStorage.setItem).toHaveBeenCalledWith("oauth_correlation_id", id);
    expect(mockSessionStorage.setItem).toHaveBeenCalledWith(
      "oauth_started_at", expect.any(String));
  });

  test("clearOAuthSession removes correlation ID from sessionStorage", async () => {
    _sessionStore["oauth_correlation_id"] = "oauth-test-1";
    const { clearOAuthSession } = await import("../api/oauthDiagnostics");
    clearOAuthSession();
    expect(mockSessionStorage.removeItem).toHaveBeenCalledWith("oauth_correlation_id");
  });
});

describe("oauthDiagnostics — stage recording", () => {

  beforeEach(() => {
    vi.resetModules();
    Object.keys(_sessionStore).forEach(k => delete _sessionStore[k]);
  });

  test("recordStage adds a stage entry", async () => {
    const { recordStage, getStages, STAGES, STATUS } = await import("../api/oauthDiagnostics");
    recordStage(STAGES.CALLBACK_RECEIVED, STATUS.SUCCESS, "callback received");
    const stages = getStages();
    expect(stages).toHaveLength(1);
    expect(stages[0].stage).toBe(STAGES.CALLBACK_RECEIVED);
    expect(stages[0].status).toBe(STATUS.SUCCESS);
    expect(stages[0].message).toBe("callback received");
  });

  test("recordStage does not include tokens in entry", async () => {
    const { recordStage, getStages, STAGES, STATUS } = await import("../api/oauthDiagnostics");
    recordStage(STAGES.SESSION_DETECTED, STATUS.SUCCESS, "session ok");
    const stages = getStages();
    const entry = stages[0];
    // Entry must never contain token-like data
    expect(JSON.stringify(entry)).not.toMatch(/eyJ/); // JWT prefix
    expect(JSON.stringify(entry)).not.toMatch(/Bearer/);
    expect(JSON.stringify(entry)).not.toMatch(/refresh_token/);
  });

  test("resetStages clears all stages", async () => {
    const { recordStage, getStages, resetStages, STAGES, STATUS } = await import("../api/oauthDiagnostics");
    recordStage(STAGES.CALLBACK_RECEIVED, STATUS.SUCCESS, "cb");
    recordStage(STAGES.SESSION_DETECTED, STATUS.SUCCESS, "sess");
    expect(getStages()).toHaveLength(2);
    resetStages();
    expect(getStages()).toHaveLength(0);
  });

  test("failed stage is recorded with error_code", async () => {
    const { recordStage, getLastFailure, STAGES, STATUS } = await import("../api/oauthDiagnostics");
    recordStage(STAGES.AUTH_ME_COMPLETED, STATUS.FAILED, "auth/me failed", "auth_me_network");
    const failure = getLastFailure();
    expect(failure).not.toBeNull();
    expect(failure.error_code).toBe("auth_me_network");
    expect(failure.status).toBe(STATUS.FAILED);
  });

  test("getStages returns a copy (mutations do not affect internal state)", async () => {
    const { recordStage, getStages, STAGES, STATUS } = await import("../api/oauthDiagnostics");
    recordStage(STAGES.CALLBACK_RECEIVED, STATUS.SUCCESS, "cb");
    const stages = getStages();
    stages.push({ fake: true });
    expect(getStages()).toHaveLength(1); // internal state unchanged
  });
});

describe("oauthDiagnostics — URL inspection", () => {

  test("detects code= in query string", async () => {
    const { inspectCallbackUrl } = await import("../api/oauthDiagnostics");
    const result = inspectCallbackUrl("https://app.example.com/?code=abc123&state=xyz");
    expect(result.hasCode).toBe(true);
    expect(result.isOAuthCallback).toBe(true);
    expect(result.hasError).toBe(false);
    // Must NOT return the actual code value — only boolean
    expect(result.code).toBeUndefined();
  });

  test("detects error= in query string", async () => {
    const { inspectCallbackUrl } = await import("../api/oauthDiagnostics");
    const result = inspectCallbackUrl(
      "https://app.example.com/?error=access_denied&error_description=User+denied+access"
    );
    expect(result.hasError).toBe(true);
    expect(result.errorParam).toBe("access_denied");
    expect(result.errorDescription).toBe("User denied access");
    expect(result.isOAuthCallback).toBe(true);
  });

  test("detects access_token in hash fragment", async () => {
    const { inspectCallbackUrl } = await import("../api/oauthDiagnostics");
    const result = inspectCallbackUrl("https://app.example.com/#access_token=tok&type=bearer");
    expect(result.hasAccessToken).toBe(true);
    expect(result.isOAuthCallback).toBe(true);
    // Must NOT return the actual token value
    expect(result.access_token).toBeUndefined();
  });

  test("returns false for non-OAuth URL", async () => {
    const { inspectCallbackUrl } = await import("../api/oauthDiagnostics");
    const result = inspectCallbackUrl("https://app.example.com/dashboard");
    expect(result.isOAuthCallback).toBe(false);
    expect(result.hasCode).toBe(false);
    expect(result.hasError).toBe(false);
  });

  test("plain URL with no params returns all false", async () => {
    const { inspectCallbackUrl } = await import("../api/oauthDiagnostics");
    const result = inspectCallbackUrl("https://app.example.com/");
    expect(result.hasCode).toBe(false);
    expect(result.hasError).toBe(false);
    expect(result.hasAccessToken).toBe(false);
    expect(result.isOAuthCallback).toBe(false);
  });
});

describe("oauthDiagnostics — error mapping", () => {

  test("maps access_denied provider error to friendly message", async () => {
    const { mapProviderError, getErrorMessage } = await import("../api/oauthDiagnostics");
    const code = mapProviderError("access_denied", "User denied access");
    expect(code).toBe("oauth_access_denied");
    const msg = getErrorMessage(code);
    expect(msg).toContain("denied");
    expect(msg).not.toMatch(/access_denied/); // raw code not shown
  });

  test("maps oauth_session_missing to friendly message", async () => {
    const { getErrorMessage } = await import("../api/oauthDiagnostics");
    const msg = getErrorMessage("oauth_session_missing");
    expect(msg).toBeTruthy();
    expect(msg).not.toMatch(/oauth_session_missing/); // raw code not shown
    expect(msg.length).toBeGreaterThan(10);
  });

  test("maps oauth_access_token_missing to friendly message", async () => {
    const { getErrorMessage } = await import("../api/oauthDiagnostics");
    const msg = getErrorMessage("oauth_access_token_missing");
    expect(msg).toBeTruthy();
    expect(msg.length).toBeGreaterThan(10);
  });

  test("unknown error code returns generic message", async () => {
    const { getErrorMessage } = await import("../api/oauthDiagnostics");
    const msg = getErrorMessage("xyzzy_unknown_code");
    expect(msg).toBeTruthy();
    expect(msg.length).toBeGreaterThan(5);
  });

  test("null error code returns generic message without throwing", async () => {
    const { getErrorMessage } = await import("../api/oauthDiagnostics");
    expect(() => getErrorMessage(null)).not.toThrow();
    const msg = getErrorMessage(null);
    expect(msg).toBeTruthy();
  });

  test("error message never contains raw JWT or Bearer token", async () => {
    const { getErrorMessage } = await import("../api/oauthDiagnostics");
    const codes = [
      "oauth_session_missing", "oauth_access_token_missing",
      "auth_me_failed", "auth_me_unauthorized", "auth_me_network",
      "oauth_cancelled", "oauth_access_denied", "oauth_error",
    ];
    for (const code of codes) {
      const msg = getErrorMessage(code);
      expect(msg).not.toMatch(/eyJ/);    // JWT prefix
      expect(msg).not.toMatch(/Bearer/);
      expect(msg).not.toMatch(/sk-/);
    }
  });
});

describe("oauthDiagnostics — localStorage safety", () => {

  test("clearOAuthSession only removes oauth_ keys, not sb-* keys", async () => {
    const { clearOAuthSession } = await import("../api/oauthDiagnostics");

    // Simulate Supabase auth keys in sessionStorage
    _sessionStore["sb-xxxx-auth-token"] = "fake-session";
    _sessionStore["oauth_correlation_id"] = "oauth-test";
    _sessionStore["oauth_started_at"] = "2026-01-01T00:00:00Z";

    clearOAuthSession();

    // OAuth keys should be removed
    expect(mockSessionStorage.removeItem).toHaveBeenCalledWith("oauth_correlation_id");
    expect(mockSessionStorage.removeItem).toHaveBeenCalledWith("oauth_started_at");

    // Supabase auth key must NOT be removed
    const sbRemovals = mockSessionStorage.removeItem.mock.calls
      .filter(call => call[0].startsWith("sb-"));
    expect(sbRemovals).toHaveLength(0);
  });
});
