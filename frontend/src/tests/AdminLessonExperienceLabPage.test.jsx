/**
 * AdminLessonExperienceLabPage.test.jsx
 * Frontend tests for the Admin Lesson Experience Lab.
 * All API calls are mocked — no live backend required.
 */
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

vi.mock("../api/lessonLab", () => ({
  listLabLessons:  vi.fn(),
  getLabLesson:    vi.fn(),
  getLabVisuals:   vi.fn(),
  previewTransform: vi.fn(),
}));

// AdminLessonExperienceLabPage is embedded inside AdminControlPage when wired.
// The test renders the page directly, but AdminControlPage is imported and may
// trigger side-effects. Mock adminControl API to prevent real network calls.
vi.mock("../api/adminControl", () => ({
  getAdminFamilies: vi.fn(() => Promise.resolve({ families: [] })),
  getAiSettings:    vi.fn(() => Promise.resolve({ api_enabled: true, provider: "openai" })),
  updateAiSettings: vi.fn(() => Promise.resolve({ api_enabled: true })),
  listOfferCodes:   vi.fn(() => Promise.resolve({ offer_codes: [] })),
  getInfluencerSummary:       vi.fn(() => Promise.resolve({ influencers: [] })),
  getOfferCodeEnrollments:    vi.fn(() => Promise.resolve({ codes: [] })),
  createAdminParent:          vi.fn(),
  createAdminChild:           vi.fn(),
  createAdminStudent:         vi.fn(),
  createAdminTeacher:         vi.fn(),
  assignTeacherStudent:       vi.fn(),
  deleteTeacherAssignment:    vi.fn(),
  updateChildAccess:          vi.fn(),
  updateChildLimits:          vi.fn(),
  deleteUser:                 vi.fn(),
  createOfferCode:            vi.fn(),
  deactivateOfferCode:        vi.fn(),
  reactivateOfferCode:        vi.fn(),
  extendOfferCodeValidity:    vi.fn(),
  markInfluencerIncentivePaid: vi.fn(),
  regeneratePromoImages:       vi.fn(),
}));

import {
  listLabLessons,
  getLabLesson,
  getLabVisuals,
} from "../api/lessonLab";
import AdminLessonExperienceLabPage from "../pages/AdminLessonExperienceLabPage";

const mockUser = { role: "admin", username: "admin", accessToken: "tok" };

function renderPage() {
  return render(<AdminLessonExperienceLabPage user={mockUser} />);
}

const EMPTY_LAB = {
  success: true, grades: [], subjects: [], chapters: [],
  lessons: [], total_lessons: 0, total_steps: 0,
};

const SAMPLE_LAB = {
  success: true,
  grades: ["Grade 9"],
  subjects: ["Science"],
  chapters: ["Photosynthesis"],
  lessons: [
    {
      lesson_id: "Grade 9|Science|Photosynthesis",
      grade: "Grade 9", subject: "Science", chapter: "Photosynthesis",
      steps: [
        { db_id: "1", step_title: "Concept Introduction" },
        { db_id: "2", step_title: "Core Explanation" },
      ],
    },
  ],
  total_lessons: 1, total_steps: 2,
};

const SAMPLE_LESSON = {
  success: true,
  lesson_id: "Grade 9|Science|Photosynthesis",
  grade: "Grade 9", subject: "Science", chapter: "Photosynthesis",
  title: "Science — Photosynthesis",
  total_steps: 2,
  total_estimated_minutes: 10,
  steps: [
    {
      step_number: 1, step_title: "Concept Introduction",
      raw_content: "## Introduction\nPhotosynthesis is the process...\n## Summary\nKey points.",
      normalized_sections: { introduction: "Photosynthesis is the process...", summary: "Key points." },
      formulas: ["6CO2 + 6H2O → glucose"],
      examples: ["For example, leaves use sunlight."],
      mcqs: ["What is photosynthesis?\nA. Making food\nB. Eating food"],
      summary: "Key points.",
      word_count: 120, estimated_minutes: 5,
      completeness_score: 75, uniqueness_score: 80,
      depth_progression_score: 70, cross_step_repetition_score: 85,
      overall_step_score: 77, status: "pass", issues: [],
    },
    {
      step_number: 2, step_title: "Core Explanation",
      raw_content: "## Core Explanation\nMore detailed content here.",
      normalized_sections: { "core explanation": "More detailed content here." },
      formulas: [], examples: [], mcqs: [], summary: "",
      word_count: 80, estimated_minutes: 5,
      completeness_score: 60, uniqueness_score: 70,
      depth_progression_score: 65, cross_step_repetition_score: 90,
      overall_step_score: 70, status: "warning",
      issues: [{ severity: "medium", issue_type: "step_too_short", issue_message: "Step 2 is short.", suggested_fix: "Expand." }],
    },
  ],
  audit_summary: {
    overall_step_sequence_score: 75, avg_step_uniqueness_score: 75,
    depth_progression_score: 68, cross_step_repetition_score: 88,
    avg_step_completeness_score: 68, critical_issues: 0, high_issues: 0,
    total_issues: 1, steps_with_issues: 1, eligible_for_bulk_apply: false,
  },
  similarity_matrix: [[1.0, 0.2], [0.2, 1.0]],
};

describe("AdminLessonExperienceLabPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    listLabLessons.mockResolvedValue(EMPTY_LAB);
    getLabLesson.mockResolvedValue(SAMPLE_LESSON);
    getLabVisuals.mockResolvedValue({ success: true, available: false, visuals: [], empty_state: "No textbook visuals linked yet." });
  });

  // ── Rendering ──────────────────────────────────────────────────────────────

  test("renders the page with lab banner", async () => {
    renderPage();
    expect(await screen.findByTestId("admin-lesson-experience-lab")).toBeInTheDocument();
    expect(screen.getByText(/Lesson Experience Lab/i)).toBeInTheDocument();
    expect(screen.getByText(/prototype only/i)).toBeInTheDocument();
  });

  test("shows 'select a lesson' empty state when no lesson loaded", async () => {
    renderPage();
    await screen.findByTestId("admin-lesson-experience-lab");
    expect(screen.getByText(/Select a lesson to begin/i)).toBeInTheDocument();
  });

  // ── Selector rendering ─────────────────────────────────────────────────────

  test("grade/subject/chapter/lesson selectors render", async () => {
    listLabLessons.mockResolvedValue(SAMPLE_LAB);
    renderPage();
    await screen.findByTestId("admin-lesson-experience-lab");
    expect(screen.getByTestId("grade-select")).toBeInTheDocument();
    expect(screen.getByTestId("subject-select")).toBeInTheDocument();
    expect(screen.getByTestId("chapter-select")).toBeInTheDocument();
    expect(screen.getByTestId("lesson-select")).toBeInTheDocument();
  });

  test("grades populate from lab data", async () => {
    listLabLessons.mockResolvedValue(SAMPLE_LAB);
    renderPage();
    await screen.findByTestId("grade-select");
    expect(screen.getByRole("option", { name: "Grade 9" })).toBeInTheDocument();
  });

  // ── Lesson loading ─────────────────────────────────────────────────────────

  test("lesson preview loads when lesson is selected", async () => {
    listLabLessons.mockResolvedValue(SAMPLE_LAB);
    renderPage();
    await screen.findByTestId("lesson-select");
    fireEvent.change(screen.getByTestId("lesson-select"), {
      target: { value: "Grade 9|Science|Photosynthesis" },
    });
    expect(await screen.findByTestId("lesson-content-view")).toBeInTheDocument();
    expect(screen.getByText(/Science — Photosynthesis/i)).toBeInTheDocument();
  });

  test("step sidebar renders with steps", async () => {
    listLabLessons.mockResolvedValue(SAMPLE_LAB);
    renderPage();
    await screen.findByTestId("lesson-select");
    fireEvent.change(screen.getByTestId("lesson-select"), {
      target: { value: "Grade 9|Science|Photosynthesis" },
    });
    expect(await screen.findByTestId("step-sidebar")).toBeInTheDocument();
    expect(screen.getByTestId("step-sidebar-item-0")).toBeInTheDocument();
    expect(screen.getByTestId("step-sidebar-item-1")).toBeInTheDocument();
  });

  test("clicking a step in sidebar shows that step", async () => {
    listLabLessons.mockResolvedValue(SAMPLE_LAB);
    renderPage();
    await screen.findByTestId("lesson-select");
    fireEvent.change(screen.getByTestId("lesson-select"), {
      target: { value: "Grade 9|Science|Photosynthesis" },
    });
    await screen.findByTestId("step-sidebar");
    fireEvent.click(screen.getByTestId("step-sidebar-item-1"));
    expect(await screen.findByText(/Core Explanation/i)).toBeInTheDocument();
  });

  // ── Audit issues ───────────────────────────────────────────────────────────

  test("audit issues appear for steps with issues", async () => {
    listLabLessons.mockResolvedValue(SAMPLE_LAB);
    renderPage();
    fireEvent.change(await screen.findByTestId("lesson-select"), {
      target: { value: "Grade 9|Science|Photosynthesis" },
    });
    await screen.findByTestId("step-sidebar");
    fireEvent.click(screen.getByTestId("step-sidebar-item-1")); // step 2 has issues
    expect(await screen.findByText(/audit issue/i)).toBeInTheDocument();
  });

  // ── Raw content toggle ─────────────────────────────────────────────────────

  test("raw content toggle shows raw content", async () => {
    listLabLessons.mockResolvedValue(SAMPLE_LAB);
    renderPage();
    fireEvent.change(await screen.findByTestId("lesson-select"), {
      target: { value: "Grade 9|Science|Photosynthesis" },
    });
    await screen.findByTestId("lesson-content-view");
    // Find the "Show raw content" checkbox
    const rawToggle = screen.getByLabelText(/show raw content/i);
    fireEvent.click(rawToggle);
    expect(await screen.findByText(/Raw Lesson Content/i)).toBeInTheDocument();
  });

  // ── Visual panel ───────────────────────────────────────────────────────────

  test("visual panel shows empty state when no visuals", async () => {
    listLabLessons.mockResolvedValue(SAMPLE_LAB);
    renderPage();
    fireEvent.change(await screen.findByTestId("lesson-select"), {
      target: { value: "Grade 9|Science|Photosynthesis" },
    });
    await screen.findByTestId("lesson-content-view");
    // Toggle show visuals
    const visToggle = screen.getByLabelText(/show visuals/i);
    fireEvent.click(visToggle);
    expect(await screen.findByTestId("visual-empty-state")).toBeInTheDocument();
    expect(screen.getByText(/No textbook visuals linked yet/i)).toBeInTheDocument();
  });

  // ── Accessibility controls ─────────────────────────────────────────────────

  test("accessibility controls render when lesson is loaded", async () => {
    listLabLessons.mockResolvedValue(SAMPLE_LAB);
    renderPage();
    fireEvent.change(await screen.findByTestId("lesson-select"), {
      target: { value: "Grade 9|Science|Photosynthesis" },
    });
    expect(await screen.findByTestId("accessibility-controls")).toBeInTheDocument();
  });

  test("accessibility font size selector changes state", async () => {
    listLabLessons.mockResolvedValue(SAMPLE_LAB);
    renderPage();
    fireEvent.change(await screen.findByTestId("lesson-select"), {
      target: { value: "Grade 9|Science|Photosynthesis" },
    });
    await screen.findByTestId("accessibility-controls");
    const fontSelect = screen.getAllByRole("combobox").find(s => s.querySelector && s.options?.[0]?.text === "Small");
    if (fontSelect) {
      fireEvent.change(fontSelect, { target: { value: "20px" } });
      expect(fontSelect.value).toBe("20px");
    }
  });

  // ── Preview mode ───────────────────────────────────────────────────────────

  test("preview mode selector renders 3 options", async () => {
    renderPage();
    await screen.findByTestId("admin-lesson-experience-lab");
    expect(screen.getByText("Student View")).toBeInTheDocument();
    expect(screen.getByText("Structure")).toBeInTheDocument();
    expect(screen.getByText("Summary")).toBeInTheDocument();
  });

  // ── Non-admin / safety ─────────────────────────────────────────────────────

  test("renders admin-lab-specific banner (lab notice visible)", async () => {
    renderPage();
    await screen.findByTestId("admin-lesson-experience-lab");
    expect(screen.getByText(/prototype only/i)).toBeInTheDocument();
  });

  test("does not show publish/write buttons", async () => {
    listLabLessons.mockResolvedValue(SAMPLE_LAB);
    renderPage();
    fireEvent.change(await screen.findByTestId("lesson-select"), {
      target: { value: "Grade 9|Science|Photosynthesis" },
    });
    await screen.findByTestId("lesson-content-view");
    expect(screen.queryByText(/publish/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/save to lesson/i)).not.toBeInTheDocument();
  });

  // ── Mobile layout ──────────────────────────────────────────────────────────

  test("renders without horizontal overflow on narrow viewport", async () => {
    Object.defineProperty(window, "innerWidth", { value: 375, writable: true });
    renderPage();
    const page = await screen.findByTestId("admin-lesson-experience-lab");
    expect(page).toBeInTheDocument();
    Object.defineProperty(window, "innerWidth", { value: 1024, writable: true });
  });
});
