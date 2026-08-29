/**
 * AuthSessionReliability.test.jsx
 * Regression tests for auth error messages and session reliability.
 *
 * Covers:
 * - Technical "No Supabase access token" message never shown to user
 * - Session expired shows friendly message
 * - Missing token → friendly "sign in again" message
 * - 401/403 from API → friendly session-expired message
 * - 500 from API → friendly "try again" message
 * - Raw Supabase internals never shown in user-facing errors
 * - authFetch hides token/JWT details from users
 */
import { describe, expect, test, vi, beforeEach } from "vitest";

// Mock supabase client
vi.mock("../api/supabaseClient", () => ({
  supabase: {
    auth: {
      getSession: vi.fn(),
      refreshSession: vi.fn(),
    },
  },
}));

// Mock fetch globally using vitest's stubGlobal
const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

import { supabase } from "../api/supabaseClient";

// Dynamic import to get fresh module after mocks
async function getAuthFetch() {
  const mod = await import("../api/authClient");
  return mod.authFetch;
}

describe("authFetch — user-facing error messages", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetch.mockReset();
  });

  test("session read error shows friendly message, not technical detail", async () => {
    supabase.auth.getSession.mockResolvedValue({
      data: { session: null },
      error: { message: "JWT expired" },
    });
    supabase.auth.refreshSession.mockResolvedValue({ data: { session: null } });

    const authFetch = await getAuthFetch();
    await expect(authFetch("/api/test")).rejects.toThrow(/sign in again|session/i);
    // Must NOT expose JWT details to user
    await expect(authFetch("/api/test")).rejects.not.toThrow(/JWT|Supabase/i);
  });

  test("missing token shows 'session expired' not 'No Supabase access token found'", async () => {
    supabase.auth.getSession.mockResolvedValue({ data: { session: null }, error: null });
    supabase.auth.refreshSession.mockResolvedValue({ data: { session: null } });

    const authFetch = await getAuthFetch();
    let caught = null;
    try { await authFetch("/api/test"); } catch(e) { caught = e.message; }
    expect(caught).toBeTruthy();
    expect(caught).not.toContain("No Supabase access token found");
    expect(caught).not.toContain("Please logout and login again");
    expect(caught).toMatch(/session has expired|sign in again/i);
  });

  test("401 response shows friendly session-expired message", async () => {
    supabase.auth.getSession.mockResolvedValue({
      data: { session: { access_token: "fake-token" } }, error: null
    });
    supabase.auth.refreshSession.mockResolvedValue({ data: { session: null } });
    mockFetch.mockResolvedValue({
      ok: false,
      status: 401,
      json: async () => ({ detail: "JWT token is expired" }),
      text: async () => "JWT token is expired",
    });

    const authFetch = await getAuthFetch();
    let caught = null;
    try { await authFetch("/api/test"); } catch(e) { caught = e.message; }
    expect(caught).toMatch(/session has expired|sign in again/i);
    expect(caught).not.toContain("JWT");
    expect(caught).not.toContain("token is expired");
  });

  test("500 response shows 'try again' not raw server error", async () => {
    supabase.auth.getSession.mockResolvedValue({
      data: { session: { access_token: "fake-token" } }, error: null
    });
    supabase.auth.refreshSession.mockResolvedValue({ data: { session: null } });
    mockFetch.mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => ({ detail: "Internal server error: supabase_key_missing" }),
      text: async () => "",
    });

    const authFetch = await getAuthFetch();
    let caught = null;
    try { await authFetch("/api/test"); } catch(e) { caught = e.message; }
    expect(caught).toMatch(/try again|trouble/i);
    expect(caught).not.toContain("supabase_key_missing");
  });

  test("403 response shows friendly access-denied message without Supabase internals", async () => {
    // 403 = authenticated but wrong role/access — must NOT say "session expired".
    // The new authClient.js correctly distinguishes 401 (session) from 403 (access).
    supabase.auth.getSession.mockResolvedValue({
      data: { session: { access_token: "fake-token" } }, error: null
    });
    supabase.auth.refreshSession.mockResolvedValue({ data: { session: null } });
    mockFetch.mockResolvedValue({
      ok: false,
      status: 403,
      json: async () => ({ detail: "Supabase RLS policy denied" }),
      text: async () => "",
    });

    const authFetch = await getAuthFetch();
    let caught = null;
    try { await authFetch("/api/test"); } catch(e) { caught = e.message; }
    // 403 must show an access-denied message, NOT "session expired"
    expect(caught).toMatch(/does not have access|not registered/i);
    // Must NOT show "session expired" — that is only for 401
    expect(caught).not.toMatch(/session has expired|sign in again/i);
    // Must NOT expose Supabase internals
    expect(caught).not.toContain("RLS");
    expect(caught).not.toContain("Supabase");
  });

  test("403 'School account pending verification' shows a principal-specific message, not the teacher one", async () => {
    // Regression: require_principal() raises "School account pending verification",
    // which contains the substring "pending verification" — the same substring
    // require_teacher() uses. Both must map to their own role-correct message.
    supabase.auth.getSession.mockResolvedValue({
      data: { session: { access_token: "fake-token" } }, error: null
    });
    supabase.auth.refreshSession.mockResolvedValue({ data: { session: null } });
    mockFetch.mockResolvedValue({
      ok: false,
      status: 403,
      json: async () => ({ detail: "School account pending verification" }),
      text: async () => "",
    });

    const authFetch = await getAuthFetch();
    let caught = null;
    try { await authFetch("/api/test"); } catch(e) { caught = e.message; }
    expect(caught).toMatch(/principal account.*pending verification/i);
    expect(caught).not.toMatch(/teacher account/i);
  });

  test("403 'Teacher account pending verification' still shows the teacher-specific message", async () => {
    supabase.auth.getSession.mockResolvedValue({
      data: { session: { access_token: "fake-token" } }, error: null
    });
    supabase.auth.refreshSession.mockResolvedValue({ data: { session: null } });
    mockFetch.mockResolvedValue({
      ok: false,
      status: 403,
      json: async () => ({ detail: "Teacher account pending verification" }),
      text: async () => "",
    });

    const authFetch = await getAuthFetch();
    let caught = null;
    try { await authFetch("/api/test"); } catch(e) { caught = e.message; }
    expect(caught).toMatch(/teacher account.*pending verification/i);
  });

  test("403 'Parent access required' shows role-specific message not session expired", async () => {
    supabase.auth.getSession.mockResolvedValue({
      data: { session: { access_token: "fake-token" } }, error: null
    });
    supabase.auth.refreshSession.mockResolvedValue({ data: { session: null } });
    mockFetch.mockResolvedValue({
      ok: false,
      status: 403,
      json: async () => ({ detail: "Parent access required" }),
      text: async () => "",
    });

    const authFetch = await getAuthFetch();
    let caught = null;
    try { await authFetch("/api/test"); } catch(e) { caught = e.message; }
    expect(caught).toContain("Parent");
    expect(caught).not.toMatch(/session has expired|sign in again/i);
  });

  test("safe business error (non-auth 400) is shown to user", async () => {
    supabase.auth.getSession.mockResolvedValue({
      data: { session: { access_token: "fake-token" } }, error: null
    });
    supabase.auth.refreshSession.mockResolvedValue({ data: { session: null } });
    mockFetch.mockResolvedValue({
      ok: false,
      status: 400,
      json: async () => ({ detail: "Child limit reached for Free Tier." }),
      text: async () => "",
    });

    const authFetch = await getAuthFetch();
    let caught = null;
    try { await authFetch("/api/test"); } catch(e) { caught = e.message; }
    // Safe business error — should be shown as-is
    expect(caught).toContain("Child limit reached");
  });

  test("successful request returns data without modification", async () => {
    supabase.auth.getSession.mockResolvedValue({
      data: { session: { access_token: "fake-token" } }, error: null
    });
    supabase.auth.refreshSession.mockResolvedValue({ data: { session: null } });
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, data: "hello" }),
    });

    const authFetch = await getAuthFetch();
    const result = await authFetch("/api/test");
    expect(result.success).toBe(true);
    expect(result.data).toBe("hello");
  });

  test("error message never contains raw JWT or Bearer token", async () => {
    supabase.auth.getSession.mockResolvedValue({ data: { session: null }, error: null });
    supabase.auth.refreshSession.mockResolvedValue({ data: { session: null } });

    const authFetch = await getAuthFetch();
    let caught = null;
    try { await authFetch("/api/test"); } catch(e) { caught = e.message; }
    expect(caught).not.toMatch(/eyJ[A-Za-z0-9]/); // JWT format
    expect(caught).not.toContain("Bearer");
    expect(caught).not.toContain("access_token");
  });
});
