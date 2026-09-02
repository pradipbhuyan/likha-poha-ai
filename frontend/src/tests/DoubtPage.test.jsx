import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import DoubtPage from "../pages/DoubtPage";
import { answerDoubt, getDoubtHistory, getDoubtSuggestions } from "../api/doubt";

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
  getDoubtSuggestions: vi.fn(),
}));

vi.mock("../components/MermaidBlock", () => ({
  default: ({ chart }) => <pre>{chart}</pre>,
}));

const studentUser = {
  role: "student",
  username: "student_one",
  accessCbse: true,
};

const freeTierUser = {
  role: "student",
  username: "free_student",
  accessCbse: false,
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
    getDoubtSuggestions.mockResolvedValue({
      success: true,
      doubt_suggestions: [],
    });
  });

  test("sends a CBSE doubt with the selected mode and subject", async () => {
    render(<DoubtPage user={studentUser} />);

    expect(await screen.findByLabelText(/mode/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/mode/i)).toHaveValue("CBSE");

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

  test("disables free-text asking for a free-tier user", async () => {
    render(<DoubtPage user={freeTierUser} />);

    expect(await screen.findByLabelText(/mode/i)).toBeInTheDocument();

    expect(screen.getByRole("textbox")).toBeDisabled();
    expect(screen.getByRole("button", { name: /ask ai tutor/i })).toBeDisabled();
    expect(screen.getByText(/suggested-question library/i)).toBeInTheDocument();
  });

  test("leaves the composer enabled for a paid-access user", async () => {
    render(<DoubtPage user={studentUser} />);

    expect(await screen.findByLabelText(/mode/i)).toBeInTheDocument();

    expect(screen.getByRole("textbox")).not.toBeDisabled();
    expect(screen.getByRole("button", { name: /ask ai tutor/i })).not.toBeDisabled();
  });

  test("suggested-question chips stay clickable for a free-tier user", async () => {
    getDoubtSuggestions.mockResolvedValue({
      success: true,
      doubt_suggestions: [{ id: "dkb-1", question: "What is matter made of?" }],
    });

    render(<DoubtPage user={freeTierUser} />);

    const chip = await screen.findByRole("button", { name: /what is matter made of/i });
    expect(chip).not.toBeDisabled();

    fireEvent.click(chip);

    await waitFor(() => {
      expect(answerDoubt).toHaveBeenCalled();
    });
  });
});
