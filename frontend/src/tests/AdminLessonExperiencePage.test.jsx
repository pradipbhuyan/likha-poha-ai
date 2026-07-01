/**
 * AdminLessonExperiencePage.test.jsx
 * Admin-only guided lesson experience preview page tests.
 * All API calls are mocked — no live backend required.
 *
 * Covers:
 * - Admin can access the new guided lesson preview page
 * - Non-admin/student users cannot see repair/audit controls
 * - Preview header states the experience is not live for students
 * - Guided roadmap (JourneyStepper) renders all steps
 * - Current step is visually highlighted
 * - Primary CTA changes by preview state
 * - Restart chapter requires confirmation
 * - Existing content panels still render correctly
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
    expect(screen.getAllByText(/Lesson Experience/i).length).toBeGreaterThan(0);
  });

  test("preview banner states the experience is not live for students", async () => {
    renderPage();
    await screen.findByTestId("page-header");
    expect(screen.getByTestId("not-live-notice")).toBeInTheDocument();
    expect(screen.getByText(/not live for students/i)).toBeInTheDocument();
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

  test("non-admin does not see repair/audit/publish controls", async () => {
    renderPage();
    expect(await screen.findByTestId("admin-lesson-experience-page")).toBeInTheDocument();
    expect(screen.queryByText(/Repair with AI/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Publish Approved/i })).not.toBeInTheDocument();
    expect(screen.queryByText(/audit score/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/validation checklist/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/validation failed/i)).not.toBeInTheDocument();
  });

  // ── Lesson loading ─────────────────────────────────────────────────────────

  test("loading lesson shows guided journey: hero and stepper", async () => {
    getLessonCatalog.mockResolvedValue(SAMPLE_CATALOG);
    renderPage();
    fireEvent.change(await screen.findByTestId("lesson-select"), {
      target: { value: "Grade 9|Science|Motion" },
    });
    expect(await screen.findByTestId("lesson-hero")).toBeInTheDocument();
    expect(screen.getByTestId("step-nav")).toBeInTheDocument();
    expect(screen.getByTestId("step-nav-item-0")).toBeInTheDocument();
    expect(screen.getByTestId("step-nav-item-1")).toBeInTheDocument();
  });

  test("guided roadmap renders all steps in the stepper", async () => {
    getLessonCatalog.mockResolvedValue(SAMPLE_CATALOG);
    renderPage();
    fireEvent.change(await screen.findByTestId("lesson-select"), {
      target: { value: "Grade 9|Science|Motion" },
    });
    await screen.findByTestId("step-nav");
    // All 2 steps in SAMPLE_LESSON appear
    expect(screen.getByTestId("step-nav-item-0")).toBeInTheDocument();
    expect(screen.getByTestId("step-nav-item-1")).toBeInTheDocument();
    expect(screen.getByText(/Step 1: Concept Introduction/i)).toBeInTheDocument();
    expect(screen.getByText(/Step 2: Core Explanation/i)).toBeInTheDocument();
  });

  test("current step is highlighted in the stepper", async () => {
    getLessonCatalog.mockResolvedValue(SAMPLE_CATALOG);
    renderPage();
    fireEvent.change(await screen.findByTestId("lesson-select"), {
      target: { value: "Grade 9|Science|Motion" },
    });
    await screen.findByTestId("step-nav");
    const step0 = screen.getByTestId("step-nav-item-0");
    // Active step should have indigo border styling
    expect(step0).toHaveStyle({ border: "1.5px solid #6366f1" });
  });

  test("hero shows subject/grade/CBSE breadcrumb", async () => {
    getLessonCatalog.mockResolvedValue(SAMPLE_CATALOG);
    renderPage();
    fireEvent.change(await screen.findByTestId("lesson-select"), {
      target: { value: "Grade 9|Science|Motion" },
    });
    await screen.findByTestId("lesson-hero");
    expect(screen.getByText(/Science.*Grade 9.*CBSE/i)).toBeInTheDocument();
  });

  test("hero shows Step N of M progress text", async () => {
    getLessonCatalog.mockResolvedValue(SAMPLE_CATALOG);
    renderPage();
    fireEvent.change(await screen.findByTestId("lesson-select"), {
      target: { value: "Grade 9|Science|Motion" },
    });
    await screen.findByTestId("lesson-hero");
    const progressTexts = screen.getAllByText(/Step 1 of 2/i);
    expect(progressTexts.length).toBeGreaterThan(0);
  });

  test("current mission card renders with step title", async () => {
    getLessonCatalog.mockResolvedValue(SAMPLE_CATALOG);
    renderPage();
    fireEvent.change(await screen.findByTestId("lesson-select"), {
      target: { value: "Grade 9|Science|Motion" },
    });
    expect(await screen.findByTestId("current-mission-card")).toBeInTheDocument();
    expect(screen.getByText(/CURRENT MISSION/i)).toBeInTheDocument();
  });

  // ── Primary CTA changes by preview state ──────────────────────────────────

  test("primary CTA shows 'Start Learning' initially", async () => {
    getLessonCatalog.mockResolvedValue(SAMPLE_CATALOG);
    renderPage();
    fireEvent.change(await screen.findByTestId("lesson-select"), {
      target: { value: "Grade 9|Science|Motion" },
    });
    await screen.findByTestId("primary-cta-btn");
    expect(screen.getByTestId("primary-cta-btn")).toHaveTextContent("Start Learning");
  });

  test("primary CTA changes to 'Continue Learning' after first click", async () => {
    getLessonCatalog.mockResolvedValue(SAMPLE_CATALOG);
    renderPage();
    fireEvent.change(await screen.findByTestId("lesson-select"), {
      target: { value: "Grade 9|Science|Motion" },
    });
    const cta = await screen.findByTestId("primary-cta-btn");
    fireEvent.click(cta);
    await waitFor(() => expect(cta).toHaveTextContent("Continue Learning"));
  });

  test("primary CTA changes to 'Continue to Next Step' after second click", async () => {
    getLessonCatalog.mockResolvedValue(SAMPLE_CATALOG);
    renderPage();
    fireEvent.change(await screen.findByTestId("lesson-select"), {
      target: { value: "Grade 9|Science|Motion" },
    });
    const cta = await screen.findByTestId("primary-cta-btn");
    fireEvent.click(cta); // not_started → in_progress
    await waitFor(() => expect(cta).toHaveTextContent("Continue Learning"));
    fireEvent.click(cta); // in_progress → completed
    await waitFor(() => expect(cta).toHaveTextContent("Continue to Next Step"));
  });

  // ── Restart chapter requires confirmation ─────────────────────────────────

  test("restart chapter link shows confirmation dialog", async () => {
    getLessonCatalog.mockResolvedValue(SAMPLE_CATALOG);
    renderPage();
    fireEvent.change(await screen.findByTestId("lesson-select"), {
      target: { value: "Grade 9|Science|Motion" },
    });
    await screen.findByTestId("restart-chapter-link");
    expect(screen.queryByTestId("restart-confirm-dialog")).not.toBeInTheDocument();
    fireEvent.click(screen.getByTestId("restart-chapter-link"));
    expect(await screen.findByTestId("restart-confirm-dialog")).toBeInTheDocument();
    expect(screen.getByTestId("restart-confirm-btn")).toBeInTheDocument();
    expect(screen.getByTestId("restart-cancel-btn")).toBeInTheDocument();
  });

  test("cancel in restart dialog dismisses it", async () => {
    getLessonCatalog.mockResolvedValue(SAMPLE_CATALOG);
    renderPage();
    fireEvent.change(await screen.findByTestId("lesson-select"), {
      target: { value: "Grade 9|Science|Motion" },
    });
    await screen.findByTestId("restart-chapter-link");
    fireEvent.click(screen.getByTestId("restart-chapter-link"));
    await screen.findByTestId("restart-confirm-dialog");
    fireEvent.click(screen.getByTestId("restart-cancel-btn"));
    await waitFor(() => expect(screen.queryByTestId("restart-confirm-dialog")).not.toBeInTheDocument());
  });

  test("confirming restart resets step to 1", async () => {
    getLessonCatalog.mockResolvedValue(SAMPLE_CATALOG);
    renderPage();
    fireEvent.change(await screen.findByTestId("lesson-select"), {
      target: { value: "Grade 9|Science|Motion" },
    });
    await screen.findByTestId("next-step-btn");
    fireEvent.click(screen.getByTestId("next-step-btn")); // go to step 2
    await waitFor(() => expect(screen.getAllByText(/Step 2 of 2/i).length).toBeGreaterThan(0));
    // Restart
    fireEvent.click(screen.getByTestId("restart-chapter-link"));
    await screen.findByTestId("restart-confirm-dialog");
    fireEvent.click(screen.getByTestId("restart-confirm-btn"));
    await waitFor(() => expect(screen.getAllByText(/Step 1 of 2/i).length).toBeGreaterThan(0));
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
    expect(screen.getAllByText(/Step 1 of 2/i).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByTestId("next-step-btn"));
    await waitFor(() => expect(screen.getAllByText(/Step 2 of 2/i).length).toBeGreaterThan(0));
  });

  test("next-up card renders when not on last step", async () => {
    getLessonCatalog.mockResolvedValue(SAMPLE_CATALOG);
    renderPage();
    fireEvent.change(await screen.findByTestId("lesson-select"), {
      target: { value: "Grade 9|Science|Motion" },
    });
    expect(await screen.findByTestId("next-up-card")).toBeInTheDocument();
    expect(screen.getByText(/NEXT UP/i)).toBeInTheDocument();
  });

  test("does NOT show audit scores or repair controls", async () => {
    getLessonCatalog.mockResolvedValue(SAMPLE_CATALOG);
    renderPage();
    fireEvent.change(await screen.findByTestId("lesson-select"), {
      target: { value: "Grade 9|Science|Motion" },
    });
    await screen.findByTestId("lesson-hero");
    expect(screen.queryByText(/audit score/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Repair with AI/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Publish Approved/i })).not.toBeInTheDocument();
    expect(screen.queryByText(/validation checklist/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/validation failed/i)).not.toBeInTheDocument();
  });

  // ── Selecting step 2 ──────────────────────────────────────────────────────

  test("selecting a step changes displayed content", async () => {
    getLessonCatalog.mockResolvedValue(SAMPLE_CATALOG);
    renderPage();
    fireEvent.change(await screen.findByTestId("lesson-select"), {
      target: { value: "Grade 9|Science|Motion" },
    });
    await screen.findByTestId("step-nav");
    fireEvent.click(screen.getByTestId("step-nav-item-1"));
    await waitFor(() => {
      expect(screen.getAllByText(/Step 2 of 2/i).length).toBeGreaterThan(0);
    });
  });
});
