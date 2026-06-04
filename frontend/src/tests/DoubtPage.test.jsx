import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import DoubtPage from "../pages/DoubtPage";
import { answerDoubt, extractDoubtImage, getDoubtHistory } from "../api/doubt";

vi.mock("../api/syllabus", () => ({
  getSyllabus: vi.fn(async () => ({
    syllabus: {
      "Grade 9": {
        CBSE: {
          Science: ["Matter in Our Surroundings"],
        },
        SOF: {
          "Science Olympiad": ["Matter in Our Surroundings"],
          "Maths Olympiad": ["Number Systems"],
          "English Olympiad": ["Nouns"],
        },
      },
    },
  })),
}));

vi.mock("../api/doubt", () => ({
  answerDoubt: vi.fn(),
  extractDoubtImage: vi.fn(),
  getDoubtHistory: vi.fn(),
}));

vi.mock("../components/MermaidBlock", () => ({
  default: ({ chart }) => <pre>{chart}</pre>,
}));

const studentUser = {
  role: "student",
  username: "student_one",
  accessCbse: true,
  accessSofScience: true,
  accessSofMaths: false,
  accessSofEnglish: false,
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
    extractDoubtImage.mockResolvedValue({
      success: true,
      text: "What is matter?",
    });
    getDoubtHistory.mockResolvedValue({
      success: true,
      history: [],
    });
  });

  test("requires an allowed SOF subject and sends it with the doubt", async () => {
    render(<DoubtPage user={studentUser} />);

    expect(await screen.findByLabelText(/mode/i)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/mode/i), {
      target: { value: "SOF" },
    });

    const subjectSelect = screen.getByLabelText(/olympiad subject/i);
    expect(subjectSelect).toHaveValue("Science Olympiad");
    expect(
      screen.queryByRole("option", { name: "Maths Olympiad" })
    ).not.toBeInTheDocument();

    fireEvent.change(screen.getByRole("textbox"), {
      target: { value: "What is matter?" },
    });
    fireEvent.click(screen.getByRole("button", { name: /ask ai tutor/i }));

    await waitFor(() => {
      expect(answerDoubt).toHaveBeenCalledWith(
        expect.objectContaining({
          mode: "SOF",
          subject: "Science Olympiad",
          username: "student_one",
          question: expect.stringContaining("What is matter?"),
          display_question: "What is matter?",
          save_to_history: true,
        })
      );
    });
  });

  test("adds extracted image text to the submitted doubt", async () => {
    render(<DoubtPage user={studentUser} />);

    expect(await screen.findByLabelText(/mode/i)).toBeInTheDocument();

    const file = new File(["fake"], "question.png", { type: "image/png" });

    fireEvent.change(screen.getByLabelText(/upload image/i), {
      target: { files: [file] },
    });

    expect(
      await screen.findByText(/image text added to this doubt/i)
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /ask ai tutor/i }));

    await waitFor(() => {
      expect(answerDoubt).toHaveBeenCalledWith(
        expect.objectContaining({
          question: expect.stringContaining("Text extracted from attached image"),
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
});
