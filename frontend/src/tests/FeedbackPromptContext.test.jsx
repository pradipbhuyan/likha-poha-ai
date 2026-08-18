/**
 * FeedbackPromptContext.test.jsx
 * Tests for the contextual (not persistent) feedback prompt gating logic.
 */
import { describe, test, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { FeedbackPromptProvider } from "../context/FeedbackPromptContext";
import { useFeedbackPrompt } from "../context/useFeedbackPrompt";

vi.mock("../api/feedback", () => ({
  getFeedbackEligibility: vi.fn(),
  markFeedbackPromptShown: vi.fn(),
  submitFeedback: vi.fn(),
}));

import { getFeedbackEligibility, markFeedbackPromptShown } from "../api/feedback";

const MOCK_USER = { id: "user-1", role: "student", grade: "Grade 9" };

function Harness({ event = "lesson_completed" }) {
  const { triggerFeedbackPrompt } = useFeedbackPrompt();
  return (
    <button data-testid="fire-trigger" onClick={() => triggerFeedbackPrompt(event, { grade: "Grade 9" })}>
      complete action
    </button>
  );
}

function renderWithProvider(children = <Harness />) {
  return render(<FeedbackPromptProvider user={MOCK_USER}>{children}</FeedbackPromptProvider>);
}

describe("FeedbackPromptContext", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    markFeedbackPromptShown.mockResolvedValue({ success: true });
  });

  test("does not show the card before any trigger fires", () => {
    renderWithProvider();
    expect(screen.queryByTestId("feedback-prompt-card")).toBeNull();
  });

  test("shows the prompt card when eligible", async () => {
    getFeedbackEligibility.mockResolvedValueOnce({ success: true, eligible: true, activity_count: 5, threshold: 3 });
    renderWithProvider();
    fireEvent.click(screen.getByTestId("fire-trigger"));
    await waitFor(() => {
      expect(screen.getByTestId("feedback-prompt-card")).toBeInTheDocument();
    });
    expect(markFeedbackPromptShown).toHaveBeenCalled();
  });

  test("does not show the prompt card when not eligible", async () => {
    getFeedbackEligibility.mockResolvedValueOnce({ success: true, eligible: false, activity_count: 1, threshold: 3 });
    renderWithProvider();
    fireEvent.click(screen.getByTestId("fire-trigger"));
    await waitFor(() => {
      expect(getFeedbackEligibility).toHaveBeenCalled();
    });
    expect(screen.queryByTestId("feedback-prompt-card")).toBeNull();
    expect(markFeedbackPromptShown).not.toHaveBeenCalled();
  });

  test("only checks eligibility once per session across multiple triggers", async () => {
    getFeedbackEligibility.mockResolvedValueOnce({ success: true, eligible: false });
    renderWithProvider();
    fireEvent.click(screen.getByTestId("fire-trigger"));
    await waitFor(() => expect(getFeedbackEligibility).toHaveBeenCalledTimes(1));
    fireEvent.click(screen.getByTestId("fire-trigger"));
    fireEvent.click(screen.getByTestId("fire-trigger"));
    await waitFor(() => expect(getFeedbackEligibility).toHaveBeenCalledTimes(1));
  });

  test("dismissing the card hides it without opening the modal", async () => {
    getFeedbackEligibility.mockResolvedValueOnce({ success: true, eligible: true });
    renderWithProvider();
    fireEvent.click(screen.getByTestId("fire-trigger"));
    await waitFor(() => screen.getByTestId("feedback-prompt-card"));
    fireEvent.click(screen.getByTestId("feedback-prompt-not-now"));
    expect(screen.queryByTestId("feedback-prompt-card")).toBeNull();
    expect(screen.queryByTestId("feedback-modal")).toBeNull();
  });

  test("clicking Share feedback opens the full modal", async () => {
    getFeedbackEligibility.mockResolvedValueOnce({ success: true, eligible: true });
    renderWithProvider();
    fireEvent.click(screen.getByTestId("fire-trigger"));
    await waitFor(() => screen.getByTestId("feedback-prompt-card"));
    fireEvent.click(screen.getByTestId("feedback-prompt-share"));
    expect(screen.getByTestId("feedback-modal")).toBeInTheDocument();
    expect(screen.queryByTestId("feedback-prompt-card")).toBeNull();
  });

  test("does nothing without a signed-in user", () => {
    renderWithProvider();
    render(
      <FeedbackPromptProvider user={null}>
        <Harness />
      </FeedbackPromptProvider>
    );
    const buttons = screen.getAllByTestId("fire-trigger");
    fireEvent.click(buttons[buttons.length - 1]);
    expect(getFeedbackEligibility).not.toHaveBeenCalled();
  });

  test("useFeedbackPrompt outside provider degrades gracefully", () => {
    function Standalone() {
      const { triggerFeedbackPrompt } = useFeedbackPrompt();
      return <button data-testid="standalone-trigger" onClick={() => triggerFeedbackPrompt("x")}>go</button>;
    }
    render(<Standalone />);
    expect(() => fireEvent.click(screen.getByTestId("standalone-trigger"))).not.toThrow();
  });
});
