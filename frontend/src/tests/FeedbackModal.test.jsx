/**
 * FeedbackModal.test.jsx
 * Tests for the general (non-bug-report) feedback modal.
 */
import { describe, test, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import FeedbackModal from "../components/FeedbackModal";

vi.mock("../api/feedback", () => ({
  submitFeedback: vi.fn(),
}));

import { submitFeedback } from "../api/feedback";

const MOCK_USER = { id: "user-1", role: "student", grade: "Grade 9" };
const MOCK_CONTEXT = { route: "/lessons", grade: "Grade 9", subject: "Science", chapter: "Motion", triggerEvent: "lesson_completed" };

describe("FeedbackModal", () => {
  beforeEach(() => { vi.clearAllMocks(); });

  test("does not render when open=false", () => {
    render(<FeedbackModal open={false} onClose={vi.fn()} user={MOCK_USER} />);
    expect(screen.queryByTestId("feedback-modal")).toBeNull();
  });

  test("renders modal when open=true", () => {
    render(<FeedbackModal open={true} onClose={vi.fn()} user={MOCK_USER} />);
    expect(screen.getByTestId("feedback-modal")).toBeInTheDocument();
  });

  test("shows all feedback type chips", () => {
    render(<FeedbackModal open={true} onClose={vi.fn()} user={MOCK_USER} />);
    expect(screen.getByTestId("feedback-type-bug")).toBeInTheDocument();
    expect(screen.getByTestId("feedback-type-feature_request")).toBeInTheDocument();
    expect(screen.getByTestId("feedback-type-content_suggestion")).toBeInTheDocument();
    expect(screen.getByTestId("feedback-type-praise")).toBeInTheDocument();
    expect(screen.getByTestId("feedback-type-other")).toBeInTheDocument();
  });

  test("shows star rating control", () => {
    render(<FeedbackModal open={true} onClose={vi.fn()} user={MOCK_USER} />);
    expect(screen.getByTestId("feedback-rating")).toBeInTheDocument();
  });

  test("shows context chip when context is provided", () => {
    render(<FeedbackModal open={true} onClose={vi.fn()} context={MOCK_CONTEXT} user={MOCK_USER} />);
    expect(screen.getByText(/Grade 9/)).toBeInTheDocument();
    expect(screen.getByText(/Science/)).toBeInTheDocument();
  });

  test("shows error when message is empty on submit", async () => {
    render(<FeedbackModal open={true} onClose={vi.fn()} user={MOCK_USER} />);
    fireEvent.click(screen.getByTestId("feedback-submit-btn"));
    await waitFor(() => {
      expect(submitFeedback).not.toHaveBeenCalled();
    });
    expect(screen.getByText(/share a few words/i)).toBeInTheDocument();
  });

  test("submits successfully and shows success state", async () => {
    submitFeedback.mockResolvedValueOnce({ success: true, id: "fb-1" });
    render(<FeedbackModal open={true} onClose={vi.fn()} context={MOCK_CONTEXT} user={MOCK_USER} />);
    fireEvent.change(screen.getByTestId("feedback-message-input"), {
      target: { value: "It would be great to bookmark favourite lessons." },
    });
    fireEvent.click(screen.getByTestId("feedback-submit-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("feedback-success")).toBeInTheDocument();
    });
  });

  test("includes selected type, rating and trigger_event in submitted payload", async () => {
    submitFeedback.mockResolvedValueOnce({ success: true, id: "fb-2" });
    render(<FeedbackModal open={true} onClose={vi.fn()} context={MOCK_CONTEXT} user={MOCK_USER} />);
    fireEvent.click(screen.getByTestId("feedback-type-praise"));
    fireEvent.click(screen.getByLabelText("4 stars"));
    fireEvent.change(screen.getByTestId("feedback-message-input"), {
      target: { value: "Loving the new voice tutor!" },
    });
    fireEvent.click(screen.getByTestId("feedback-submit-btn"));
    await waitFor(() => expect(submitFeedback).toHaveBeenCalled());
    const payload = submitFeedback.mock.calls[0][0];
    expect(payload.feedback_type).toBe("praise");
    expect(payload.rating).toBe(4);
    expect(payload.trigger_event).toBe("lesson_completed");
    expect(payload.grade).toBe("Grade 9");
    expect(payload.subject).toBe("Science");
  });

  test("clicking close calls onClose", () => {
    const onClose = vi.fn();
    render(<FeedbackModal open={true} onClose={onClose} user={MOCK_USER} />);
    fireEvent.click(screen.getByLabelText("Close"));
    expect(onClose).toHaveBeenCalled();
  });
});
