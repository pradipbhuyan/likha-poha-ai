import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";

import LessonsPage from "../pages/LessonsPage";

vi.mock("../api/syllabus", () => ({
  getSyllabus: vi.fn(async () => ({
    syllabus: {
      "Grade 9": {
        CBSE: {
          Science: ["Tissues in Action"],
        },
      },
    },
  })),
}));

vi.mock("../api/progress", () => ({
  getChapterProgress: vi.fn(async () => ({
    progress: {
      current_step_index: 0,
      completed: false,
      last_lesson: "This is a generated lesson about tissues.",
      step_lessons: {
        0: "This is a generated lesson about tissues.",
      },
    },
  })),
  saveChapterProgress: vi.fn(async () => ({ success: true })),
}));

vi.mock("../api/evaluation", () => ({
  evaluateStudentAnswer: vi.fn(async () => ({
    success: true,
    evaluation: "## Score\n8/10\n\n## Verdict\nPASS",
    score: 8,
    passed: true,
  })),
  generatePracticeQuestions: vi.fn(async () => ({
    success: true,
    questions: [
      "Explain tissues in your own words.",
      "Why is division of labour important in multicellular organisms?",
    ],
  })),
}));

vi.mock("../api/lesson", () => ({
  generateLesson: vi.fn(),
  askLessonFollowUp: vi.fn(),
}));

vi.mock("../api/tts", () => ({
  generateSpeech: vi.fn(),
}));

vi.mock("../api/images", () => ({
  generateEducationalImage: vi.fn(),
}));

vi.mock("../components/LessonSections", () => ({
  default: ({ lesson }) => <div>{lesson}</div>,
}));

vi.mock("../components/MermaidBlock", () => ({
  default: () => <div>Mermaid diagram</div>,
}));

describe("LessonsPage", () => {
  test("practice mode disables Ask AI follow-up", async () => {
    render(
      <LessonsPage
        user={{
          username: "test_user",
        }}
      />
    );

    expect(
        await screen.findByRole("heading", {
          name: /generated lesson/i,
        })
      ).toBeInTheDocument();

    const practiceButton = screen.getByRole("button", {
      name: /generate 2 practice questions/i,
    });

    fireEvent.click(practiceButton);

    expect(
      await screen.findByText(/practice mode active/i)
    ).toBeInTheDocument();

    await waitFor(() => {
      expect(
        screen.getByPlaceholderText(
          /practice mode active. complete written practice first/i
        )
      ).toBeDisabled();
    });

    expect(
      screen.getByRole("button", {
        name: /ask ai tutor/i,
      })
    ).toBeDisabled();
  });
});