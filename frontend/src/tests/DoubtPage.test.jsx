import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import DoubtPage from "../pages/DoubtPage";
import { answerDoubt } from "../api/doubt";

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
          question: "What is matter?",
        })
      );
    });
  });
});
