/**
 * LeaderboardPage.test.jsx
 *
 * Covers the pinned "Your Rank" summary — previously the only way to find
 * your own standing was to scroll the full ranking list until the
 * highlighted `is_you` row appeared. The pinned summary shows it
 * unconditionally, near the top, regardless of where the viewer ranks.
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, test, vi, beforeEach } from "vitest";

vi.mock("../api/analytics", () => ({
  getLeaderboard: vi.fn(),
}));

import LeaderboardPage from "../pages/LeaderboardPage";
import { getLeaderboard } from "../api/analytics";

describe("LeaderboardPage — pinned Your Rank summary", () => {
  beforeEach(() => { vi.clearAllMocks(); });

  test("shows nothing extra when the leaderboard is empty", async () => {
    getLeaderboard.mockResolvedValue({ leaderboard: [] });
    render(<LeaderboardPage />);

    expect(await screen.findByText("Submit a mock test to enter the leaderboard")).toBeInTheDocument();
    expect(screen.queryByTestId("your-rank-pinned")).not.toBeInTheDocument();
  });

  test("shows nothing extra when the viewer has no is_you row (not yet ranked)", async () => {
    getLeaderboard.mockResolvedValue({
      leaderboard: [
        { rank: 1, display_name: "R.B.", is_you: false, tests: 3, best_score: 92, average_score: 88 },
      ],
    });
    render(<LeaderboardPage />);

    await screen.findAllByText("R.B.");
    expect(screen.queryByTestId("your-rank-pinned")).not.toBeInTheDocument();
  });

  test("pins the viewer's rank even when they are far down the list", async () => {
    const leaderboard = [
      { rank: 1, display_name: "A.A.", is_you: false, tests: 10, best_score: 99, average_score: 95 },
      { rank: 2, display_name: "B.B.", is_you: false, tests: 10, best_score: 90, average_score: 88 },
      { rank: 3, display_name: "C.C.", is_you: false, tests: 10, best_score: 85, average_score: 80 },
      { rank: 47, display_name: "Y.O.", is_you: true, tests: 4, best_score: 70, average_score: 55 },
    ];
    getLeaderboard.mockResolvedValue({ leaderboard });
    render(<LeaderboardPage />);

    const pinned = await screen.findByTestId("your-rank-pinned");
    expect(pinned.textContent).toContain("Your rank: #47");
    expect(pinned.textContent).toContain("55% average");
    expect(pinned.textContent).toContain("Best 70%");
    expect(pinned.textContent).toContain("4 tests taken");
  });

  test("still pins the summary when the viewer is already visible in the podium", async () => {
    const leaderboard = [
      { rank: 1, display_name: "Y.O.", is_you: true, tests: 12, best_score: 100, average_score: 91 },
      { rank: 2, display_name: "B.B.", is_you: false, tests: 10, best_score: 90, average_score: 88 },
    ];
    getLeaderboard.mockResolvedValue({ leaderboard });
    render(<LeaderboardPage />);

    const pinned = await screen.findByTestId("your-rank-pinned");
    expect(pinned.textContent).toContain("Your rank: #1");
  });
});
