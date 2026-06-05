import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import LoginPage from "../pages/LoginPage";
import { supabase } from "../api/supabaseClient";

vi.mock("../api/supabaseClient", () => ({
  supabase: {
    auth: {
      resetPasswordForEmail: vi.fn(),
    },
  },
}));

describe("LoginPage password reset", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.unstubAllEnvs();
  });

  test("sends a reset email for an entered email address", async () => {
    /** Forgot password should call Supabase Auth with the reset redirect URL. */
    supabase.auth.resetPasswordForEmail.mockResolvedValue({
      data: {},
      error: null,
    });

    render(<LoginPage onLogin={vi.fn()} />);

    fireEvent.change(screen.getByPlaceholderText(/enter username or email/i), {
      target: { value: "parent@example.com" },
    });
    fireEvent.click(screen.getByRole("button", { name: /forgot password/i }));

    await waitFor(() => {
      expect(supabase.auth.resetPasswordForEmail).toHaveBeenCalledWith(
        "parent@example.com",
        expect.objectContaining({
          redirectTo: `${window.location.origin}/reset-password`,
        })
      );
    });

    expect(
      await screen.findByText(/if this account exists/i)
    ).toBeInTheDocument();
  });
});
