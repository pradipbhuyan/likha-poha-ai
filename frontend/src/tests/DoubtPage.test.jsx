import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import DoubtPage from "../pages/DoubtPage";
import { answerDoubt, getDoubtHistory } from "../api/doubt";

vi.mock("../api/syllabus", () => ({
  getSyllabus: vi.fn(async () => ({
    syllabus: {
      "Grade 9": {
        CBSE: {
          Science: ["Matter in Our Surroundings"],
        },
      },
    },
  })),
}));

vi.mock("../api/doubt", () => ({
  answerDoubt: vi.fn(),
  getDoubtHistory: vi.fn(),
}));

vi.mock("../components/MermaidBlock", () => ({
  default: ({ chart }) => <pre>{chart}</pre>,
}));

const studentUser = {
  role: "student",
  username: "student_one",
  accessCbse: true,
};

describe("DoubtPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    answerDoubt.mockResolvedValue({
      success: true,
      answer: "Matter has mass and occupies space.",
      source_type: "MOCK",
      sources: [],
      mentor_suggestions: [],
    });
    getDoubtHistory.mockResolvedValue({
      success: true,
      history: [],
    });
  });

  test("sends a CBSE doubt with the selected mode and subject", async () => {
    render(<DoubtPage user={studentUser} />);

    // Mode is auto-selected from grade access (no manual Mode selector in
    // the live top bar) — confirmed via the Grade select's accessible name.
    expect(await screen.findByLabelText(/^grade$/i)).toBeInTheDocument();

    fireEvent.change(screen.getByRole("textbox"), {
      target: { value: "What is matter?" },
    });
    fireEvent.click(screen.getByRole("button", { name: /ask ai tutor/i }));

    await waitFor(() => {
      expect(answerDoubt).toHaveBeenCalledWith(
        expect.objectContaining({
          mode: "CBSE",
          username: "student_one",
          question: expect.stringContaining("What is matter?"),
          display_question: "What is matter?",
          save_to_history: true,
        })
      );
    });
  });

  test("loads a saved doubt answer from history", async () => {
    getDoubtHistory.mockResolvedValue({
      success: true,
      history: [
        {
          id: "history-1",
          grade: "Grade 9",
          mode: "CBSE",
          subject: "Science",
          chapter: "Matter in Our Surroundings",
          question: "What is matter?",
          answer: "Saved answer from history.",
          source_type: "LLM",
          sources: [],
          mentor_suggestions: [],
          created_at: "2026-06-04T10:00:00Z",
        },
      ],
    });

    render(<DoubtPage user={studentUser} />);

    const savedDoubt = await screen.findByRole("button", {
      name: /what is matter/i,
    });

    fireEvent.click(savedDoubt);

    expect(await screen.findByText("Saved answer from history.")).toBeInTheDocument();
  });

  test("top-bar Grade/Subject selects each have exactly one accessible name (P1-11)", async () => {
    // Regression test for P1-11: a dead, fully-labelled duplicate of this
    // form used to sit in the DOM behind display:none. Confirms both that
    // the live selects are named, and that removing the dead markup left
    // no duplicate to collide with getByLabelText.
    render(<DoubtPage user={studentUser} />);

    expect(await screen.findByLabelText(/^grade$/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^subject$/i)).toBeInTheDocument();

    // The old dead duplicate form is gone entirely, not just re-hidden.
    expect(document.querySelector(".premium-doubt-context")).not.toBeInTheDocument();
  });
});
