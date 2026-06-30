import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";

import LessonsPage from "../pages/LessonsPage";
import { getDoubtHistory } from "../api/doubt";

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
          Hindi: ["दो बैलों की कथा"],
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
  getLessonTextbookVisuals: vi.fn(async () => ({
    success: true,
    visuals: [],
  })),
}));

vi.mock("../api/doubt", () => ({
  getDoubtHistory: vi.fn(),
}));

vi.mock("../api/tts", () => ({
  generateSpeech: vi.fn(),
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

  test("textbook visuals card is removed from the student lesson page", async () => {
    // The 'Textbook visuals only' card has been removed from LessonsPage
    // (shouldShowTextbookVisualTools returns false). Verify it does not appear.
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

    // Wait for lesson to render
    expect(
      await screen.findByRole("heading", { name: /generated lesson/i })
    ).toBeInTheDocument();

    // Card must NOT appear
    expect(
      screen.queryByRole("heading", { name: /textbook visuals only/i })
    ).not.toBeInTheDocument();
    expect(
      screen.queryByPlaceholderText(/search text in approved visuals/i)
    ).not.toBeInTheDocument();
  });

  test("does not show visual tools for unsupported grades (Grade 6 English)", async () => {
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

    // Textbook visual section must NOT appear for Grade 6 (only Grade 9 all + Grade 10 Sci/Maths)
    expect(
      screen.queryByRole("heading", {
        name: /textbook visuals only/i,
      })
    ).not.toBeInTheDocument();
  });

  test("textbook visual search UI is not shown on lesson page (card removed)", async () => {
    // The textbook visual card was removed from LessonsPage.
    // Verify the search input and search button do not appear.
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
      await screen.findByRole("heading", { name: /generated lesson/i })
    ).toBeInTheDocument();

    expect(
      screen.queryByPlaceholderText(/search text in approved visuals/i)
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /search visuals/i })
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: /textbook visuals only/i })
    ).not.toBeInTheDocument();
  });

  test("uses Hindi MCQ-only practice and hides lesson follow-up chat", async () => {
    render(
      <LessonsPage
        user={{
          role: "student",
          username: "hindi_student",
          grade: "Grade 9",
          accessCbse: true,
        }}
      />
    );

    expect(
      await screen.findByRole("heading", {
        name: /generated lesson/i,
      })
    ).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/subject/i), {
      target: { value: "Hindi" },
    });

    await waitFor(() => {
      expect(screen.queryByText(/ask a follow-up/i)).not.toBeInTheDocument();
    });

    expect(await screen.findByText(/Hindi gets two MCQs/i)).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", {
        name: /generate 2 practice questions/i,
      })
    );

    expect(
      await screen.findByText(/Which tissue transports water in plants/i)
    ).toBeInTheDocument();
    expect(screen.queryByText(/Explain tissues/i)).not.toBeInTheDocument();
    expect(
      screen.queryByPlaceholderText(/write freely here/i)
    ).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Xylem" }));
    fireEvent.click(screen.getAllByRole("button", { name: /check answer/i })[0]);

    expect(await screen.findByRole("heading", { name: "Correct" })).toBeInTheDocument();
    expect(screen.getByText(/Result: Correct/i)).toBeInTheDocument();
    expect(screen.queryByText(/Score signal/i)).not.toBeInTheDocument();
  });

  test("does not show visual section for Grade 5 Maths (only Grade 9/10 supported)", async () => {
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
      await screen.findByRole("heading", { name: /generated lesson/i })
    ).toBeInTheDocument();

    // Textbook visual section must NOT appear for Grade 5
    expect(
      screen.queryByRole("heading", { name: /textbook visuals only/i })
    ).not.toBeInTheDocument();
  });

  test("textbook visual tools are hidden for all subjects including Science (card removed)", async () => {
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
      await screen.findByRole("heading", { name: /generated lesson/i })
    ).toBeInTheDocument();

    expect(
      screen.queryByRole("heading", { name: /textbook visuals only/i })
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText(/visuals to look for in this lesson/i)
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /tissues in action textbook page/i })
    ).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /find visual/i })).not.toBeInTheDocument();
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
