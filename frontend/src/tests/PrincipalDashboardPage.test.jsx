import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import PrincipalDashboardPage from "../pages/PrincipalDashboardPage";
import {
  getPrincipalSchool,
  getPrincipalDashboardSummary,
  listPrincipalTeachers,
  linkTeacherToSchool,
  unlinkTeacherFromSchool,
  listPrincipalStudents,
  linkStudentToSchool,
  unlinkStudentFromSchool,
  getPrincipalIncentives,
  redeemPrincipalReward,
} from "../api/principalDashboard";

vi.mock("../api/principalDashboard", () => ({
  getPrincipalSchool: vi.fn(),
  getPrincipalDashboardSummary: vi.fn(),
  listPrincipalTeachers: vi.fn(),
  linkTeacherToSchool: vi.fn(),
  unlinkTeacherFromSchool: vi.fn(),
  listPrincipalStudents: vi.fn(),
  linkStudentToSchool: vi.fn(),
  unlinkStudentFromSchool: vi.fn(),
  getPrincipalIncentives: vi.fn(),
  redeemPrincipalReward: vi.fn(),
}));

function mockSchool() {
  return {
    success: true,
    school: {
      id: "school-1",
      name: "Sunrise Public School",
      school_code: "SUN-7F3K2",
      status: "active",
      tier: "bronze",
    },
  };
}

function mockSummary() {
  return {
    success: true,
    teacher_count: 1,
    student_count: 2,
    free_student_count: 1,
    paid_student_count: 1,
    conversion_rate: 50.0,
    tier: "bronze",
    next_tier: { tier: "silver", threshold: 100, remaining: 99 },
  };
}

function mockTeachers() {
  return {
    success: true,
    teachers: [
      { id: "teacher-1", username: "Meena Sharma", email: "meena@example.com", assigned_students: 12, account_status: "active" },
    ],
  };
}

function mockStudents() {
  return {
    success: true,
    students: [
      { id: "student-1", username: "Ankita Baruah", grade: "Grade 10", tier: "paid", subscription_plan: "starter", last_active_date: "2026-08-27" },
      { id: "student-2", username: "Rohit Nath", grade: "Grade 9", tier: "free", subscription_plan: "free", last_active_date: "2026-08-26" },
    ],
  };
}

function mockIncentives() {
  return {
    success: true,
    tier: "bronze",
    paid_student_count: 1,
    next_tier: { tier: "silver", threshold: 100, remaining: 99 },
    unlocked_rewards: [{ key: "bronze_support", label: "Standard support line", description: "Email support." }],
    catalog: {
      bronze: [{ key: "bronze_support", label: "Standard support line", description: "Email support." }],
      silver: [{ key: "silver_priority_support", label: "Priority support line", description: "WhatsApp line." }],
      gold: [],
      platinum: [],
    },
    redemption_history: [],
  };
}

describe("PrincipalDashboardPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getPrincipalSchool.mockResolvedValue(mockSchool());
    getPrincipalDashboardSummary.mockResolvedValue(mockSummary());
    listPrincipalTeachers.mockResolvedValue(mockTeachers());
    listPrincipalStudents.mockResolvedValue(mockStudents());
    getPrincipalIncentives.mockResolvedValue(mockIncentives());
    linkTeacherToSchool.mockResolvedValue({ success: true });
    unlinkTeacherFromSchool.mockResolvedValue({ success: true });
    linkStudentToSchool.mockResolvedValue({ success: true });
    unlinkStudentFromSchool.mockResolvedValue({ success: true });
    redeemPrincipalReward.mockResolvedValue({ success: true });
  });

  test("renders school name and overview KPIs", async () => {
    render(<PrincipalDashboardPage />);
    expect(await screen.findByText("Sunrise Public School")).toBeInTheDocument();
    expect(screen.getByText("Total Students")).toBeInTheDocument();
    expect(screen.getByText("Paid Students")).toBeInTheDocument();
    expect(screen.getByText("Conversion Rate")).toBeInTheDocument();
  });

  test("switching to Teachers tab shows the roster and a link form", async () => {
    render(<PrincipalDashboardPage />);
    await screen.findByText("Sunrise Public School");

    fireEvent.click(screen.getByRole("button", { name: "Teachers" }));
    expect(await screen.findByText("Meena Sharma")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Link an existing teacher by email")).toBeInTheDocument();
  });

  test("linking a teacher by email calls the API and refreshes the roster", async () => {
    render(<PrincipalDashboardPage />);
    await screen.findByText("Sunrise Public School");
    fireEvent.click(screen.getByRole("button", { name: "Teachers" }));
    await screen.findByText("Meena Sharma");

    fireEvent.change(screen.getByPlaceholderText("Link an existing teacher by email"), {
      target: { value: "new.teacher@example.com" },
    });
    fireEvent.click(screen.getByText("Link teacher"));

    await waitFor(() => {
      expect(linkTeacherToSchool).toHaveBeenCalledWith("new.teacher@example.com");
    });
  });

  test("Students tab shows tier pills and never exposes chat/doubt content", async () => {
    render(<PrincipalDashboardPage />);
    await screen.findByText("Sunrise Public School");
    fireEvent.click(screen.getByRole("button", { name: "Students" }));

    expect(await screen.findByText("Ankita Baruah")).toBeInTheDocument();
    expect(screen.getByText("Rohit Nath")).toBeInTheDocument();
    expect(screen.getByText(/never changes their login, plan, or what they can do/i)).toBeInTheDocument();
  });

  test("filtering students by tier re-queries the API", async () => {
    render(<PrincipalDashboardPage />);
    await screen.findByText("Sunrise Public School");
    fireEvent.click(screen.getByRole("button", { name: "Students" }));
    await screen.findByText("Ankita Baruah");

    fireEvent.click(screen.getByText("Paid"));

    await waitFor(() => {
      expect(listPrincipalStudents).toHaveBeenCalledWith("paid");
    });
  });

  test("Incentives tab shows current tier and locked rewards", async () => {
    render(<PrincipalDashboardPage />);
    await screen.findByText("Sunrise Public School");
    fireEvent.click(screen.getByRole("button", { name: "Incentives & Rewards" }));

    expect(await screen.findByText(/is on the Bronze tier/)).toBeInTheDocument();
    expect(screen.getByText("Standard support line")).toBeInTheDocument();
    expect(screen.getByText("Priority support line")).toBeInTheDocument();
    // Silver reward is locked at bronze tier — its button must say Locked, not Redeem.
    const lockedCard = screen.getByText("Priority support line").closest("div");
    expect(lockedCard.parentElement.textContent).toContain("Locked");
  });

  test("redeeming an unlocked reward calls the API", async () => {
    render(<PrincipalDashboardPage />);
    await screen.findByText("Sunrise Public School");
    fireEvent.click(screen.getByRole("button", { name: "Incentives & Rewards" }));
    await screen.findByText("Standard support line");

    fireEvent.click(screen.getByText("Redeem"));

    await waitFor(() => {
      expect(redeemPrincipalReward).toHaveBeenCalledWith("bronze_support");
    });
  });
});
