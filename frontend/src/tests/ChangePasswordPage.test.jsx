import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import ChangePasswordPage from "../pages/ChangePasswordPage";
import { supabase } from "../api/supabaseClient";

vi.mock("../api/supabaseClient", () => ({
  supabase: {
    auth: {
      signInWithPassword: vi.fn(),
      updateUser: vi.fn(),
    },
  },
}));

const user = {
  email: "student@example.com",
};

describe("ChangePasswordPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    supabase.auth.signInWithPassword.mockResolvedValue({
      data: {},
      error: null,
    });
    supabase.auth.updateUser.mockResolvedValue({
      data: {},
      error: null,
    });
  });

  test("reauthenticates before updating the password", async () => {
    /** Change password should verify the current password first. */
    render(<ChangePasswordPage user={user} />);

    fireEvent.change(screen.getByLabelText(/current password/i), {
      target: { value: "oldpassword123" },
    });
    fireEvent.change(screen.getByLabelText(/^new password$/i), {
      target: { value: "newpassword123" },
    });
    fireEvent.change(screen.getByLabelText(/confirm new password/i), {
      target: { value: "newpassword123" },
    });
    fireEvent.click(screen.getByRole("button", { name: /change password/i }));

    await waitFor(() => {
      expect(supabase.auth.signInWithPassword).toHaveBeenCalledWith({
        email: "student@example.com",
        password: "oldpassword123",
      });
      expect(supabase.auth.updateUser).toHaveBeenCalledWith({
        password: "newpassword123",
      });
    });

    expect(
      await screen.findByText(/password changed successfully/i)
    ).toBeInTheDocument();
  });

  test("blocks mismatched new passwords", async () => {
    /** Client validation should catch mismatched confirmation before Supabase. */
    render(<ChangePasswordPage user={user} />);

    fireEvent.change(screen.getByLabelText(/current password/i), {
      target: { value: "oldpassword123" },
    });
    fireEvent.change(screen.getByLabelText(/^new password$/i), {
      target: { value: "newpassword123" },
    });
    fireEvent.change(screen.getByLabelText(/confirm new password/i), {
      target: { value: "different123" },
    });
    fireEvent.click(screen.getByRole("button", { name: /change password/i }));

    expect(await screen.findByText(/passwords do not match/i)).toBeInTheDocument();
    expect(supabase.auth.updateUser).not.toHaveBeenCalled();
  });
});
