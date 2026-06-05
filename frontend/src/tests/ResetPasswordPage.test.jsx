import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import ResetPasswordPage from "../pages/ResetPasswordPage";
import { supabase } from "../api/supabaseClient";

vi.mock("../api/supabaseClient", () => ({
  supabase: {
    auth: {
      exchangeCodeForSession: vi.fn(),
      getSession: vi.fn(),
      onAuthStateChange: vi.fn(),
      signOut: vi.fn(),
      updateUser: vi.fn(),
    },
  },
}));

describe("ResetPasswordPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    supabase.auth.getSession.mockResolvedValue({
      data: {
        session: {
          access_token: "reset-token",
        },
      },
    });
    supabase.auth.onAuthStateChange.mockReturnValue({
      data: {
        subscription: {
          unsubscribe: vi.fn(),
        },
      },
    });
    supabase.auth.updateUser.mockResolvedValue({
      data: {},
      error: null,
    });
    supabase.auth.signOut.mockResolvedValue({
      error: null,
    });
  });

  test("updates the password when recovery session is ready", async () => {
    /** A valid recovery session should allow the student/parent to set a password. */
    render(<ResetPasswordPage onBackToLogin={vi.fn()} />);

    expect(
      await screen.findByRole("button", { name: /update password/i })
    ).not.toBeDisabled();

    fireEvent.change(screen.getByPlaceholderText(/^new password$/i), {
      target: { value: "newpassword123" },
    });
    fireEvent.change(screen.getByPlaceholderText(/confirm new password/i), {
      target: { value: "newpassword123" },
    });
    fireEvent.click(screen.getByRole("button", { name: /update password/i }));

    await waitFor(() => {
      expect(supabase.auth.updateUser).toHaveBeenCalledWith({
        password: "newpassword123",
      });
    });

    expect(await screen.findByText(/password updated/i)).toBeInTheDocument();
  });
});
