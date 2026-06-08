import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import FirstTimeGuide from "../components/FirstTimeGuide";
import { getOnboardingGuideSettings } from "../api/onboardingGuide";

vi.mock("../api/onboardingGuide", () => ({
  getOnboardingGuideSettings: vi.fn(),
}));

describe("FirstTimeGuide", () => {
  beforeEach(() => {
    localStorage.clear();
    getOnboardingGuideSettings.mockResolvedValue({
      success: true,
      settings: {
        enabled: true,
        active_theme: "quest",
        rotation_enabled: false,
        rotation_days: 14,
        student_theme: "quest",
        parent_theme: "clean",
        teacher_theme: "forest",
        show_once_per_theme: false,
        auto_open: true,
        message: "Welcome to your first learning quest.",
      },
    });
  });

  test("shows a role-aware guide for student users", async () => {
    render(
      <FirstTimeGuide
        activePage="dashboard"
        user={{ role: "student", username: "akshita.teststudent" }}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/quest mode/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/start at dashboard/i)).toBeInTheDocument();
    expect(screen.getByText(/welcome to your first learning quest/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /next/i }));
    expect(screen.getByText(/open lessons/i)).toBeInTheDocument();
  });

  test("does not render for admin users", async () => {
    render(
      <FirstTimeGuide
        activePage="adminControl"
        user={{ role: "admin", username: "pradip" }}
      />
    );

    await waitFor(() => {
      expect(getOnboardingGuideSettings).toHaveBeenCalled();
    });

    expect(screen.queryByText(/guide/i)).not.toBeInTheDocument();
  });
});
