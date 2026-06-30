/**
 * AdminLessonExperiencePage.test.jsx
 * Admin-only lesson experience preview page tests.
 * All API calls are mocked — no live backend required.
 */
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

vi.mock("../api/lessonExperience", () => ({
  getLessonCatalog:  vi.fn(),
  getLessonDetail:   vi.fn(),
  getLessonVisuals:  vi.fn(() => Promise.resolve({ available: false, visuals: [], empty_state: "No visuals." })),
}));

import { getLessonCatalog, getLessonDetail } from "../api/lessonExperience";
import AdminLessonExperiencePage from "../pages/AdminLessonExperiencePage";

const adminUser = { role: "admin", username: "admin", accessToken: "tok" };

function renderPage() {
  return render(<AdminLessonExperiencePage user={adminUser} />);
}

const EMPTY_CATALOG = {
  success: true, grades: [], subjects: [], chapters: [],
  lessons: [], total_lessons: 0,
};

const SAMPLE_CATALOG = {
  success: true,
  grades: ["Grade 9"],
  subjects: ["Science"],
  chapters: ["Motion"],
  lessons: [
    {
      lesson_id: "Grade 9|Science|Motion",
      grade: "Grade 9", subject: "Science", chapter: "Motion",
      step_count: 2, estimated_minutes: 10,
    },
  ],
};

const SAMPLE_LESSON = {
  success: true,
  lesson_id: "Grade 9|Science|Motion",
  grade: "Grade 9", subject: "Science", chapter: "Motion",
  title: "Science — Motion",
  total_steps: 2, total_estimated_minutes: 10,
  steps: [
    {
      step_number: 1, step_title: "Concept Introduction",
      raw_content: "Motion is the change in position over time.",
      normalized_sections: {
        introduction: "Motion is the change in position over time.",
        "what you will learn": "- Understand what motion is\n- Learn about displacement",
        summary: "Motion = change in position.",
      },
      formulas: ["v = s/t"],
      examples: ["A car moving at 60 km/h"],
      mcqs: [
        {
          question: "What is the SI unit of velocity?\nA. m/s\nB. km/h\nC. m/s²\nD. N",
          type: "mcq", answer: "A. m/s", explanation: "SI unit of velocity is m/s.",
        },
      ],
      summary: "Motion = change in position.",
      word_count: 40, estimated_minutes: 5,
      overall_step_score: 78, uniqueness_score: 80,
    },
    {
      step_number: 2, step_title: "Core Explanation",
      raw_content: "Velocity is speed with direction.",
      normalized_sections: { "simple explanation": "Velocity is speed with direction." },
      formulas: [], examples: [], mcqs: [], summary: "",
      word_count: 30, estimated_minutes: 5,
      overall_step_score: 70,
    },
  ],
};

describe("AdminLessonExperiencePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getLessonCatalog.mockResolvedValue(EMPTY_CATALOG);
    getLessonDetail.mockResolvedValue(SAMPLE_LESSON);
  });

  // ── Core rendering ─────────────────────────────────────────────────────────

  test("renders page with header and admin preview badge", async () => {
    renderPage();
    expect(await screen.findByTestId("admin-lesson-experience-page")).toBeInTheDocument();
    expect(screen.getByTestId("page-header")).toBeInTheDocument();
    expect(screen.getByText(/ADMIN PREVIEW/i)).toBeInTheDocument();
    expect(screen.getByText(/Lesson Experience/i)).toBeInTheDocument();
  });

  test("shows read-only note and edit redirect in header", async () => {
    renderPage();
    await screen.findByTestId("page-header");
    expect(screen.getByText(/Read-only/i)).toBeInTheDocument();
    expect(screen.getByText(/Lesson Lab or Lesson Repair/i)).toBeInTheDocument();
  });

  test("renders selector dropdowns when catalog loaded", async () => {
    getLessonCatalog.mockResolvedValue(SAMPLE_CATALOG);
    renderPage();
    expect(await screen.findByTestId("grade-select")).toBeInTheDocument();
    expect(screen.getByTestId("subject-select")).toBeInTheDocument();
    expect(screen.getByTestId("chapter-select")).toBeInTheDocument();
    expect(screen.getByTestId("lesson-select")).toBeInTheDocument();
  });

  test("grade options populate from catalog", async () => {
    getLessonCatalog.mockResolvedValue(SAMPLE_CATALOG);
    renderPage();
    await screen.findByTestId("grade-select");
    expect(screen.getByRole("option", { name: "Grade 9" })).toBeInTheDocument();
  });

  // ── Non-admin access ───────────────────────────────────────────────────────

  test("non-admin sees nothing (returns null)", () => {
    render(<AdminLessonExperiencePage user={{ role: "student", username: "s" }} />);
    // App.jsx guards this — page returns null for non-admin
    expect(screen.queryByTestId("admin-lesson-experience-page")).not.toBeInTheDocument();
  });

  // ── Lesson loading ─────────────────────────────────────────────────────────

  test("loading lesson shows step nav and hero", async () => {
    getLessonCatalog.mockResolvedValue(SAMPLE_CATALOG);
    renderPage();
    fireEvent.change(await screen.findByTestId("lesson-select"), {
      target: { value: "Grade 9|Science|Motion" },
    });
    expect(await screen.findByTestId("lesson-hero")).toBeInTheDocument();
    expect(screen.getByTestId("step-nav")).toBeInTheDocument();
    expect(screen.getByTestId("step-nav-item-0")).toBeInTheDocument();
  });

  test("selecting lesson shows step progress bar", async () => {
    getLessonCatalog.mockResolvedValue(SAMPLE_CATALOG);
    renderPage();
    fireEvent.change(await screen.findByTestId("lesson-select"), {
      target: { value: "Grade 9|Science|Motion" },
    });
    await screen.findByTestId("lesson-hero");
    expect(screen.getByText(/Step 1 of 2/i)).toBeInTheDocument();
  });

  test("selecting a step changes displayed content", async () => {
    getLessonCatalog.mockResolvedValue(SAMPLE_CATALOG);
    renderPage();
    fireEvent.change(await screen.findByTestId("lesson-select"), {
      target: { value: "Grade 9|Science|Motion" },
    });
    await screen.findByTestId("step-nav");
    fireEvent.click(screen.getByTestId("step-nav-item-1"));
    await waitFor(() => {
      expect(screen.getByText(/Core Explanation/i)).toBeInTheDocument();
    });
  });

  // ── Content panels ─────────────────────────────────────────────────────────

  test("learning objectives card renders", async () => {
    getLessonCatalog.mockResolvedValue(SAMPLE_CATALOG);
    renderPage();
    fireEvent.change(await screen.findByTestId("lesson-select"), {
      target: { value: "Grade 9|Science|Motion" },
    });
    expect(await screen.findByTestId("objectives-card")).toBeInTheDocument();
  });

  test("formula card renders when formulas exist", async () => {
    getLessonCatalog.mockResolvedValue(SAMPLE_CATALOG);
    renderPage();
    fireEvent.change(await screen.findByTestId("lesson-select"), {
      target: { value: "Grade 9|Science|Motion" },
    });
    expect(await screen.findByTestId("formula-card")).toBeInTheDocument();
  });

  test("practice MCQ card renders when MCQs exist", async () => {
    getLessonCatalog.mockResolvedValue(SAMPLE_CATALOG);
    renderPage();
    fireEvent.change(await screen.findByTestId("lesson-select"), {
      target: { value: "Grade 9|Science|Motion" },
    });
    expect(await screen.findByTestId("mcq-card")).toBeInTheDocument();
    expect(screen.getByText(/Practice Question/i)).toBeInTheDocument();
  });

  test("practice empty state when no MCQs", async () => {
    getLessonCatalog.mockResolvedValue(SAMPLE_CATALOG);
    getLessonDetail.mockResolvedValue({
      ...SAMPLE_LESSON,
      steps: [{ ...SAMPLE_LESSON.steps[0], mcqs: [] }],
    });
    renderPage();
    fireEvent.change(await screen.findByTestId("lesson-select"), {
      target: { value: "Grade 9|Science|Motion" },
    });
    expect(await screen.findByTestId("practice-empty")).toBeInTheDocument();
  });

  test("concept map renders", async () => {
    getLessonCatalog.mockResolvedValue(SAMPLE_CATALOG);
    renderPage();
    fireEvent.change(await screen.findByTestId("lesson-select"), {
      target: { value: "Grade 9|Science|Motion" },
    });
    expect(await screen.findByTestId("concept-map")).toBeInTheDocument();
  });

  test("visual panel empty state renders when no visuals", async () => {
    getLessonCatalog.mockResolvedValue(SAMPLE_CATALOG);
    renderPage();
    fireEvent.change(await screen.findByTestId("lesson-select"), {
      target: { value: "Grade 9|Science|Motion" },
    });
    expect(await screen.findByTestId("visual-empty-state")).toBeInTheDocument();
  });

  test("gamification preview renders", async () => {
    renderPage();
    expect(await screen.findByTestId("gamification-preview")).toBeInTheDocument();
    expect(screen.getByText(/Gamification preview only/i)).toBeInTheDocument();
  });

  // ── Accessibility controls ─────────────────────────────────────────────────

  test("accessibility controls render", async () => {
    renderPage();
    expect(await screen.findByTestId("accessibility-controls")).toBeInTheDocument();
  });

  // ── Notes panel ────────────────────────────────────────────────────────────

  test("notes panel renders after lesson is loaded", async () => {
    getLessonCatalog.mockResolvedValue(SAMPLE_CATALOG);
    renderPage();
    fireEvent.change(await screen.findByTestId("lesson-select"), {
      target: { value: "Grade 9|Science|Motion" },
    });
    expect(await screen.findByTestId("notes-panel")).toBeInTheDocument();
    expect(screen.getByTestId("note-input")).toBeInTheDocument();
  });

  // ── No audit/repair controls ───────────────────────────────────────────────

  test("does NOT show audit scores or repair controls", async () => {
    getLessonCatalog.mockResolvedValue(SAMPLE_CATALOG);
    renderPage();
    fireEvent.change(await screen.findByTestId("lesson-select"), {
      target: { value: "Grade 9|Science|Motion" },
    });
    await screen.findByTestId("lesson-hero");
    expect(screen.queryByText(/audit score/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Repair with AI/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Publish/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/validation/i)).not.toBeInTheDocument();
  });

  // ── Navigation ─────────────────────────────────────────────────────────────

  test("next/prev step buttons render after lesson load", async () => {
    getLessonCatalog.mockResolvedValue(SAMPLE_CATALOG);
    renderPage();
    fireEvent.change(await screen.findByTestId("lesson-select"), {
      target: { value: "Grade 9|Science|Motion" },
    });
    expect(await screen.findByTestId("prev-step-btn")).toBeInTheDocument();
    expect(screen.getByTestId("next-step-btn")).toBeInTheDocument();
  });

  test("next step button advances step", async () => {
    getLessonCatalog.mockResolvedValue(SAMPLE_CATALOG);
    renderPage();
    fireEvent.change(await screen.findByTestId("lesson-select"), {
      target: { value: "Grade 9|Science|Motion" },
    });
    await screen.findByTestId("next-step-btn");
    fireEvent.click(screen.getByTestId("next-step-btn"));
    await waitFor(() => expect(screen.getByText(/Step 2 of 2/i)).toBeInTheDocument());
  });
});
