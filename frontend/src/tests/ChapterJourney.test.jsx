import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import ChapterJourneyView from "../components/journey/ChapterJourneyView";
import JourneyRenderer from "../components/journey/JourneyRenderer";
import StudyRenderer from "../components/journey/StudyRenderer";

vi.mock("../api/lesson", () => ({
  askLessonFollowUp: vi.fn(async () => ({
    success: true,
    answer: "Because gas particles move freely.",
    source_type: "MOCK",
  })),
}));

vi.mock("../api/progress", () => ({
  saveChapterProgress: vi.fn(async () => ({ success: true })),
}));

// Minimal IntersectionObserver stub — jsdom doesn't implement it. Each
// instance records the element it was asked to observe so a test can find
// "its" observer and manually fire the intersecting callback.
class MockIntersectionObserver {
  constructor(callback) {
    this.callback = callback;
    MockIntersectionObserver.instances.push(this);
  }
  observe(el) { this.target = el; }
  disconnect() {}
}
MockIntersectionObserver.instances = [];

function fireIntersection(elementId, isIntersecting = true) {
  const observer = MockIntersectionObserver.instances.find((o) => o.target?.id === elementId);
  if (!observer) throw new Error(`No observer found for #${elementId}`);
  observer.callback([{ isIntersecting, target: observer.target }]);
}

const SAMPLE_DOC = {
  board: "CBSE",
  grade: "Grade 6",
  subject: "Science",
  chapter: "Chapter 3: Matter Around Us",
  mode: "CBSE",
  version: 1,
  source: "converted",
  milestones: [
    {
      title: "Concept introduction",
      blocks: [
        { type: "hook", text: "Ice, water and steam are the same substance." },
        { type: "concept", title: "States of matter", body_md: "Solids keep their shape.", key_terms: [] },
        {
          type: "quickcheck",
          format: "mcq",
          question: "Which state fills its container fully?",
          options: ["Solid", "Liquid", "Gas", "None"],
          answer_index: 2,
          explanation: "Gases expand to fill available space.",
        },
        { type: "students_ask", question: "Why does ice float?", answer_md: "Ice is less dense than water." },
      ],
    },
    {
      title: "Worked examples",
      blocks: [
        {
          type: "example",
          question: "A car travels 120 km in 2 hours. Find the speed.",
          body_md: "Step 1: speed = distance/time\nAnswer: 60 km/h",
        },
        { type: "watchout", body_md: "Do not confuse speed with velocity." },
      ],
    },
  ],
  recap: { type: "recap", body_md: "Matter has three states." },
  exam: [
    {
      type: "exam_qa",
      marks: 3,
      year: "CBSE 2023",
      question: "Define matter with two examples.",
      model_answer_md: "Matter occupies space and has mass. Examples: air, water.",
    },
  ],
};

const USER = { username: "test_user" };

describe("JourneyRenderer (Grades 5-8)", () => {
  test("renders hook, concept, milestone titles, and recap", () => {
    render(
      <JourneyRenderer doc={SAMPLE_DOC} xp={0} quizAnswers={{}} onQuickCheckAnswer={() => {}} />
    );
    expect(screen.getByText(/same substance/i)).toBeInTheDocument();
    expect(screen.getByText(/solids keep their shape/i)).toBeInTheDocument();
    expect(screen.getByText("Concept introduction")).toBeInTheDocument();
    expect(screen.getByText(/matter has three states/i)).toBeInTheDocument();
    expect(screen.getByText(/chapter complete/i)).toBeInTheDocument();
  });

  test("quick check gives instant local feedback on correct answer", () => {
    const onAnswer = vi.fn();
    render(
      <JourneyRenderer doc={SAMPLE_DOC} xp={0} quizAnswers={{}} onQuickCheckAnswer={onAnswer} />
    );
    fireEvent.click(screen.getByRole("button", { name: "Gas" }));
    expect(screen.getByText(/correct! \+10 xp/i)).toBeInTheDocument();
    expect(onAnswer).toHaveBeenCalledWith("0:2", 2, true);
  });

  test("students_ask answer is hidden until revealed", () => {
    render(
      <JourneyRenderer doc={SAMPLE_DOC} xp={0} quizAnswers={{}} onQuickCheckAnswer={() => {}} />
    );
    expect(screen.queryByText(/less dense than water/i)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /why does ice float/i }));
    expect(screen.getByText(/less dense than water/i)).toBeInTheDocument();
  });
});

describe("StudyRenderer (Grades 9-12)", () => {
  test("renders outline, skips hook, and gates the worked example solution", () => {
    render(
      <StudyRenderer
        doc={SAMPLE_DOC}
        quizAnswers={{}}
        onQuickCheckAnswer={() => {}}
        activeMilestone={0}
        onNavigate={() => {}}
      />
    );
    // Hook is a Journey-only block
    expect(screen.queryByText(/same substance/i)).not.toBeInTheDocument();
    // Outline lists milestones
    expect(screen.getAllByText("Worked examples").length).toBeGreaterThan(0);
    // Solution hidden behind attempt-first reveal
    expect(screen.queryByText(/60 km\/h/i)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /show the solution/i }));
    expect(screen.getByText(/60 km\/h/i)).toBeInTheDocument();
  });
});

describe("StudyRenderer board questions", () => {
  test("renders exam_qa with marks tag and gated model answer; Journey ignores it", () => {
    const { unmount } = render(
      <StudyRenderer
        doc={SAMPLE_DOC}
        quizAnswers={{}}
        onQuickCheckAnswer={() => {}}
        activeMilestone={0}
        onNavigate={() => {}}
      />
    );
    // Appears twice: outline link + section heading
    expect(screen.getAllByText(/board questions/i)).toHaveLength(2);
    expect(screen.getByText("3 marks")).toBeInTheDocument();
    expect(screen.getByText("CBSE 2023")).toBeInTheDocument();
    expect(screen.queryByText(/occupies space and has mass/i)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /show model answer/i }));
    expect(screen.getByText(/occupies space and has mass/i)).toBeInTheDocument();
    unmount();

    render(
      <JourneyRenderer doc={SAMPLE_DOC} xp={0} quizAnswers={{}} onQuickCheckAnswer={() => {}} />
    );
    expect(screen.queryByText(/board questions/i)).not.toBeInTheDocument();
  });
});

describe("ChapterJourneyView", () => {
  test("renders Journey renderer for Grade 6 with progress strip", () => {
    render(
      <ChapterJourneyView
        doc={SAMPLE_DOC}
        user={USER}
        grade="Grade 6"
        mode="CBSE"
        subject="Science"
        chapter="Chapter 3: Matter Around Us"
      />
    );
    expect(screen.getByTestId("chapter-journey")).toBeInTheDocument();
    expect(screen.getByText(/milestone 1 of 2/i)).toBeInTheDocument();
    expect(screen.getByText(/0\/1 checks done/i)).toBeInTheDocument();
  });

  test("renders Study renderer for Grade 10", () => {
    render(
      <ChapterJourneyView
        doc={{ ...SAMPLE_DOC, grade: "Grade 10" }}
        user={USER}
        grade="Grade 10"
        mode="CBSE"
        subject="Science"
        chapter="Chapter 3: Matter Around Us"
      />
    );
    // Study mode shows the outline header, not the XP chip
    expect(screen.getByText(/on this chapter/i)).toBeInTheDocument();
    expect(screen.queryByText(/xp/i)).not.toBeInTheDocument();
  });

  test("quick check answer updates progress and persists to localStorage", () => {
    window.localStorage.clear();
    render(
      <ChapterJourneyView
        doc={SAMPLE_DOC}
        user={USER}
        grade="Grade 6"
        mode="CBSE"
        subject="Science"
        chapter="Chapter 3: Matter Around Us"
      />
    );
    fireEvent.click(screen.getByRole("button", { name: "Gas" }));
    expect(screen.getByText(/1\/1 checks done/i)).toBeInTheDocument();
    const saved = JSON.parse(
      window.localStorage.getItem("lp_journey:Grade 6|Science|Chapter 3: Matter Around Us")
    );
    expect(saved.quizAnswers["0:2"]).toBe(2);
    expect(saved.xp).toBe(10);
  });

  test("follow-up box sends question with milestone context", async () => {
    const { askLessonFollowUp } = await import("../api/lesson");
    render(
      <ChapterJourneyView
        doc={SAMPLE_DOC}
        user={USER}
        grade="Grade 6"
        mode="CBSE"
        subject="Science"
        chapter="Chapter 3: Matter Around Us"
      />
    );
    fireEvent.change(
      screen.getByPlaceholderText(/ask a question about what you just read/i),
      { target: { value: "Why do gases spread?" } }
    );
    fireEvent.click(screen.getByRole("button", { name: /ask/i }));
    expect(
      await screen.findByText(/because gas particles move freely/i)
    ).toBeInTheDocument();
    expect(askLessonFollowUp).toHaveBeenCalledWith(
      expect.objectContaining({
        username: "test_user",
        grade: "Grade 6",
        step_title: "Concept introduction",
      })
    );
  });
});

describe("ChapterJourneyView — real completion save", () => {
  beforeEach(async () => {
    MockIntersectionObserver.instances = [];
    vi.stubGlobal("IntersectionObserver", MockIntersectionObserver);
    const { saveChapterProgress } = await import("../api/progress");
    saveChapterProgress.mockClear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  test("saves completed:true once the Journey finish card scrolls into view", async () => {
    const { saveChapterProgress } = await import("../api/progress");
    render(
      <ChapterJourneyView
        doc={SAMPLE_DOC}
        user={USER}
        grade="Grade 6"
        mode="CBSE"
        subject="Science"
        chapter="Chapter 3: Matter Around Us"
      />
    );

    expect(saveChapterProgress).not.toHaveBeenCalled();

    fireIntersection("journey-finish-card");

    await waitFor(() => {
      expect(saveChapterProgress).toHaveBeenCalledWith(
        expect.objectContaining({
          username: "test_user",
          grade: "Grade 6",
          subject: "Science",
          chapter: "Chapter 3: Matter Around Us",
          completed: true,
        })
      );
    });
  });

  test("does not save again if the finish card intersects a second time", async () => {
    const { saveChapterProgress } = await import("../api/progress");
    render(
      <ChapterJourneyView
        doc={SAMPLE_DOC}
        user={USER}
        grade="Grade 6"
        mode="CBSE"
        subject="Science"
        chapter="Chapter 3: Matter Around Us"
      />
    );

    fireIntersection("journey-finish-card");
    await waitFor(() => expect(saveChapterProgress).toHaveBeenCalledTimes(1));

    fireIntersection("journey-finish-card");
    fireIntersection("journey-finish-card");
    expect(saveChapterProgress).toHaveBeenCalledTimes(1);
  });

  test("does not save when the finish card is observed but not yet intersecting", async () => {
    const { saveChapterProgress } = await import("../api/progress");
    render(
      <ChapterJourneyView
        doc={SAMPLE_DOC}
        user={USER}
        grade="Grade 6"
        mode="CBSE"
        subject="Science"
        chapter="Chapter 3: Matter Around Us"
      />
    );

    fireIntersection("journey-finish-card", false);
    expect(saveChapterProgress).not.toHaveBeenCalled();
  });

  test("saves completed:true once the Study finish card scrolls into view", async () => {
    const { saveChapterProgress } = await import("../api/progress");
    render(
      <ChapterJourneyView
        doc={{ ...SAMPLE_DOC, grade: "Grade 10" }}
        user={USER}
        grade="Grade 10"
        mode="CBSE"
        subject="Science"
        chapter="Chapter 3: Matter Around Us"
      />
    );

    fireIntersection("study-finish-card");

    await waitFor(() => {
      expect(saveChapterProgress).toHaveBeenCalledWith(
        expect.objectContaining({ grade: "Grade 10", completed: true })
      );
    });
  });

  test("Study renderer shows the same finish card as Journey", () => {
    render(
      <StudyRenderer
        doc={SAMPLE_DOC}
        quizAnswers={{}}
        onQuickCheckAnswer={() => {}}
        activeMilestone={0}
        onNavigate={() => {}}
      />
    );
    expect(screen.getByText(/chapter complete — great work/i)).toBeInTheDocument();
  });
});
