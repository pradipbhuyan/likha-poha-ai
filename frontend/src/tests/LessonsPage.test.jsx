import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";

import LessonsPage from "../pages/LessonsPage";
import { getDoubtHistory } from "../api/doubt";
import { generateEducationalImage } from "../api/images";

vi.mock("../api/syllabus", () => ({
  getSyllabus: vi.fn(async () => ({
    syllabus: {
      "Grade 5": {
        CBSE: {
          Maths: ["Fractions"],
        },
      },
      "Grade 6": {
        CBSE: {
          English: ["Nouns"],
        },
      },
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
      {
        type: "mcq",
        question: "Which tissue transports water in plants?",
        options: ["Xylem", "Phloem", "Epidermis", "Cork"],
        answer: "Xylem",
        explanation: "Xylem transports water and minerals.",
        expected_keywords: ["xylem", "water", "minerals"],
      },
      {
        type: "descriptive",
        question: "Explain tissues in your own words.",
        options: [],
        answer: "A tissue is a group of similar cells doing one job.",
        explanation: "Good answers mention cells, structure, and function.",
        expected_keywords: ["cells", "function", "similar"],
      },
    ],
  })),
}));

vi.mock("../api/lesson", () => ({
  generateLesson: vi.fn(),
  askLessonFollowUp: vi.fn(),
}));

vi.mock("../api/doubt", () => ({
  getDoubtHistory: vi.fn(),
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
  beforeEach(() => {
    vi.clearAllMocks();
    generateEducationalImage.mockResolvedValue({
      success: true,
      image_base64: "fake-image",
    });
    getDoubtHistory.mockResolvedValue({
      success: true,
      history: [],
    });
  });

  test("loads and displays saved lesson progress", async () => {
    /*
     * This test checks the initial LessonsPage load.
     *
     * The mocked progress API returns a saved lesson:
     * "This is a generated lesson about tissues."
     *
     * Expected result:
     * - The page should show the Generated Lesson heading.
     * - The saved lesson text should appear on screen.
     */

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

    expect(
      await screen.findByText(/this is a generated lesson about tissues/i)
    ).toBeInTheDocument();
  });

  test("shows practice questions after clicking generate practice questions", async () => {
    /*
     * This test checks that practice questions are displayed.
     *
     * The mocked evaluation API returns two practice questions.
     *
     * Expected result:
     * - User clicks Generate 2 Practice Questions.
     * - The two mocked questions should appear on screen.
     */

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
      await screen.findByText(
        /which tissue transports water in plants/i
      )
    ).toBeInTheDocument();

    expect(
      await screen.findByText(/explain tissues in your own words/i)
    ).toBeInTheDocument();
  });

  test("practice mode disables Ask AI follow-up", async () => {
    /*
     * This test checks that practice mode blocks AI follow-up questions.
     *
     * Once practice mode is active, the student should complete the written
     * practice first instead of immediately asking the AI tutor for help.
     *
     * Expected result:
     * - Practice mode active message should appear.
     * - Ask AI input should be disabled.
     * - Ask AI Tutor button should be disabled.
     */

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
          /practice mode active. complete self-check practice first/i
        )
      ).toBeDisabled();
    });

    expect(
      screen.getByRole("button", {
        name: /ask ai tutor/i,
      })
    ).toBeDisabled();
  });

  test("student only sees their onboarded grade in the grade dropdown", async () => {
    /*
     * This test protects grade-scoped onboarding behavior.
     *
     * A Grade 5 student should not see Grade 9 content in the lesson selector.
     */

    render(
      <LessonsPage
        user={{
          role: "student",
          username: "grade_five_student",
          grade: "Grade 5",
        }}
      />
    );

    const gradeSelect = await screen.findByLabelText(/grade/i);

    expect(gradeSelect).toHaveValue("Grade 5");
    expect(
      Array.from(gradeSelect.options).map((option) => option.value)
    ).toEqual(["Grade 5"]);
  });

  test("shows visual generator for Science and sends lesson context", async () => {
    render(
      <LessonsPage
        user={{
          role: "student",
          username: "science_student",
          grade: "Grade 9",
          accessCbse: true,
        }}
      />
    );

    expect(
      await screen.findByRole("heading", {
        name: /visual generator/i,
      })
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /generate visual/i }));

    await waitFor(() => {
      expect(generateEducationalImage).toHaveBeenCalledWith(
        expect.any(String),
        "science_student",
        expect.objectContaining({
          grade: "Grade 9",
          mode: "CBSE",
          subject: "Science",
          chapter: "Tissues in Action",
        })
      );
    });
  });

  test("hides visual generator for English lessons", async () => {
    render(
      <LessonsPage
        user={{
          role: "student",
          username: "english_student",
          grade: "Grade 6",
          accessCbse: true,
        }}
      />
    );

    expect(
      await screen.findByRole("heading", {
        name: /generated lesson/i,
      })
    ).toBeInTheDocument();

    expect(
      screen.queryByRole("heading", {
        name: /visual generator/i,
      })
    ).not.toBeInTheDocument();
  });

  test("shows Maths visual aid suggestions and fills the visual prompt", async () => {
    render(
      <LessonsPage
        user={{
          role: "student",
          username: "maths_student",
          grade: "Grade 5",
          accessCbse: true,
        }}
      />
    );

    expect(
      await screen.findByText(/best maths visual aids to ask for/i)
    ).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", {
        name: /number line with examples marked/i,
      })
    );

    expect(
      screen.getByPlaceholderText(/show rational numbers on a number line/i)
    ).toHaveValue("Number line with examples marked");
  });

  test("shows Science visual aid suggestions and fills the visual prompt", async () => {
    render(
      <LessonsPage
        user={{
          role: "student",
          username: "science_student",
          grade: "Grade 9",
          accessCbse: true,
        }}
      />
    );

    expect(
      await screen.findByText(/best science visual aids to ask for/i)
    ).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", {
        name: /process flow with arrows/i,
      })
    );

    expect(
      screen.getByPlaceholderText(/show osmosis as water movement/i)
    ).toHaveValue("Process flow with arrows");
  });

  test("shows saved lesson follow-up history and restores a selected doubt", async () => {
    getDoubtHistory.mockResolvedValue({
      success: true,
      history: [
        {
          id: "lesson-history-1",
          source_type: "LESSON_PLATFORM_RAG",
          question: "What is Likha Poha AI?",
          answer:
            "Likha Poha AI was initially developed to help Akshita with her studies.",
          subject: "Maths Olympiad",
          chapter: "Number Systems",
        },
      ],
    });

    render(
      <LessonsPage
        user={{
          role: "student",
          username: "history_student",
          grade: "Grade 9",
          accessCbse: true,
        }}
      />
    );

    expect(
      await screen.findByText(/recent lesson doubts/i)
    ).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", {
        name: /what is likha poha ai/i,
      })
    );

    expect(
      await screen.findByText(/initially developed to help Akshita/i)
    ).toBeInTheDocument();
    expect(await screen.findByText(/platform/i)).toBeInTheDocument();
  });
});
