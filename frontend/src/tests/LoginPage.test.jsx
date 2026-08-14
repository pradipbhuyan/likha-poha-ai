import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import LoginPage from "../pages/LoginPage";

vi.mock("../api/supabaseClient", () => ({
  supabase: {
    auth: {
      signOut: vi.fn().mockResolvedValue({}),
      signInWithPassword: vi.fn(),
      resetPasswordForEmail: vi.fn(),
    },
    from: vi.fn().mockReturnThis(),
  },
}));

// Mock global fetch — the forgot-password flow now calls the backend endpoint
// POST /api/auth/forgot-password, which handles sending the email server-side
// (including forwarding to the parent's email for student accounts).
const mockFetch = vi.fn();

describe("LoginPage password reset", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.unstubAllEnvs();
    globalThis.fetch = mockFetch;
  });

  test("sends a reset request to the backend forgot-password endpoint", async () => {
    /**
     * Forgot password now POSTs to /api/auth/forgot-password instead of
     * calling Supabase directly.  The backend handles sending to the student
     * email and forwarding to the parent's email.
     */
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true, message: "If this account exists, a reset link was sent." }),
    });

    render(<LoginPage onLogin={vi.fn()} />);

    fireEvent.change(screen.getByPlaceholderText(/username or email/i), {
      target: { value: "likha1" },
    });
    fireEvent.click(screen.getByRole("button", { name: /forgot password/i }));

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/auth/forgot-password"),
        expect.objectContaining({
          method: "POST",
          body: expect.stringContaining("likha1"),
        })
      );
    });

    expect(
      await screen.findByText(/if this account exists/i)
    ).toBeInTheDocument();
  });

  test("shows reset message even when backend fetch fails", async () => {
    /** If the backend is unreachable, the UI still shows the safe success message. */
    mockFetch.mockRejectedValueOnce(new Error("network error"));

    render(<LoginPage onLogin={vi.fn()} />);

    fireEvent.change(screen.getByPlaceholderText(/username or email/i), {
      target: { value: "parent@example.com" },
    });
    fireEvent.click(screen.getByRole("button", { name: /forgot password/i }));

    expect(
      await screen.findByText(/if this account exists/i)
    ).toBeInTheDocument();
  });
});

describe("LoginPage account creation", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('"Create an account" always hands off to onShowSignup, never opens an in-page signup form', () => {
    /**
     * Regression test: LoginPage used to have a dormant in-page signup path
     * (handleSignup/isSignupMode) that directly inserted an unrestricted-
     * access profile via the anon-key client, unreachable only because
     * onShowSignup is always passed by App.jsx. That path has been removed
     * entirely — clicking "Create an account" must always defer to the real
     * signup flow via onShowSignup, and no full-name/signup form can appear.
     */
    const onShowSignup = vi.fn();
    render(<LoginPage onLogin={vi.fn()} onShowSignup={onShowSignup} />);

    fireEvent.click(screen.getByText(/create an account/i));

    expect(onShowSignup).toHaveBeenCalledTimes(1);
    expect(screen.queryByPlaceholderText(/full name/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/create parent account/i)).not.toBeInTheDocument();
  });

  test('clicking "Create an account" without onShowSignup does not crash or open a signup form', () => {
    render(<LoginPage onLogin={vi.fn()} />);

    fireEvent.click(screen.getByText(/create an account/i));

    expect(screen.queryByPlaceholderText(/full name/i)).not.toBeInTheDocument();
    expect(screen.getByText(/welcome back/i)).toBeInTheDocument();
  });
});
