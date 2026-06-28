/**
 * AdminQACenterPage.test.jsx
 * Frontend tests for the Admin Platform QA Center.
 */
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, expect, test, vi, beforeEach } from "vitest";

vi.mock("../api/authClient", () => ({
  authFetch: vi.fn(),
}));

import AdminQACenterPage from "../pages/AdminQACenterPage";
import { authFetch } from "../api/authClient";

const ADMIN = { id: "admin-uid-1", username: "admin", role: "admin" };

const EMPTY_REPORT = { success: true, available: false, message: "No lesson quality audit has been run yet." };

const SAMPLE_REPORT = {
  success: true, available: true,
  audited_at: "2026-06-28T10:00:00Z",
  lessons_audited: 5, overall_score: 82,
  critical_count: 1, high_count: 3, medium_count: 8, low_count: 2,
  grade_scores: { "Grade 9": 82, "Grade 10": 78 },
  subject_scores: { Mathematics: 85, Science: 79 },
  worst_lessons: [
    { grade: "Grade 9", subject: "Science", chapter: "Motion", step_count: 3, overall_score: 60, critical: 1, high: 2 },
  ],
  all_issues: [
    { grade: "Grade 9", subject: "Science", chapter: "Motion", severity: "critical",
      category: "structure", message: "Missing lesson content", detail: "" },
    { grade: "Grade 9", subject: "Mathematics", chapter: "Triangles", severity: "high",
      category: "formula", message: "Missing variable definitions", detail: "formula section" },
  ],
};

const RUN_RESPONSE = { success: true, job_id: "job-abc-123", message: "Audit started" };
const STATUS_QUEUED = { success: true, job: { id: "job-abc-123", status: "queued", mode: "sample" } };
const STATUS_COMPLETED = { success: true, job: { id: "job-abc-123", status: "completed", lessons_audited: 5, overall_score: 82, critical_count: 1 } };

describe("AdminQACenterPage", () => {
  beforeEach(() => { vi.clearAllMocks(); });

  test("Authorization Audit card is clickable and renders Feature Auth content", async () => {
    authFetch.mockResolvedValueOnce(EMPTY_REPORT);
    const { authFetch: fa } = await import("../api/authClient");
    fa.mockResolvedValue(EMPTY_REPORT);
    render(<AdminQACenterPage setActivePage={vi.fn()} />);
    await screen.findByTestId("admin-qa-center");
    const authCard = screen.getByTestId("module-feature-auth");
    fireEvent.click(authCard);
    expect(await screen.findByTestId("module-content-feature-auth")).toBeInTheDocument();
    expect(document.body.textContent).toContain("Authorization Audit");
  });

  test("Lesson Quality card click stays on lesson quality module", async () => {
    authFetch.mockResolvedValue(EMPTY_REPORT);
    render(<AdminQACenterPage setActivePage={vi.fn()} />);
    await screen.findByTestId("admin-qa-center");
    const lqCard = screen.getByTestId("module-lesson-quality");
    fireEvent.click(lqCard);
    expect(await screen.findByTestId("module-content-lesson-quality")).toBeInTheDocument();
    expect(document.body.textContent).toContain("Lesson Quality");
  });

  test("Back to Lesson Quality button returns to lesson quality", async () => {
    authFetch.mockResolvedValue(EMPTY_REPORT);
    render(<AdminQACenterPage setActivePage={vi.fn()} />);
    await screen.findByTestId("admin-qa-center");
    fireEvent.click(screen.getByTestId("module-feature-auth"));
    await screen.findByTestId("back-to-lesson-quality");
    fireEvent.click(screen.getByTestId("back-to-lesson-quality"));
    expect(await screen.findByTestId("module-content-lesson-quality")).toBeInTheDocument();
  });

  test("Coming soon modules are not clickable", async () => {
    authFetch.mockResolvedValueOnce(EMPTY_REPORT);
    render(<AdminQACenterPage setActivePage={vi.fn()} />);
    await screen.findByTestId("admin-qa-center");
    expect(document.body.textContent).toContain("Coming soon");
    expect(document.body.textContent).toContain("Formula Sheet Audit");
  });
});

  test("renders Platform QA Center", async () => {
    authFetch.mockResolvedValueOnce(EMPTY_REPORT);
    render(<AdminQACenterPage user={ADMIN} />);
    expect(await screen.findByTestId("admin-qa-center")).toBeInTheDocument();
    expect(document.body.textContent).toContain("Platform QA Center");
  });

  test("shows empty state when no report exists", async () => {
    authFetch.mockResolvedValueOnce(EMPTY_REPORT);
    render(<AdminQACenterPage user={ADMIN} />);
    expect(await screen.findByTestId("no-report-state")).toBeInTheDocument();
    expect(document.body.textContent).toContain("No lesson quality audit has been run yet");
  });

  test("shows summary cards when report exists", async () => {
    authFetch.mockResolvedValueOnce(SAMPLE_REPORT);
    render(<AdminQACenterPage user={ADMIN} />);
    expect(await screen.findByTestId("summary-cards")).toBeInTheDocument();
    expect(screen.getByTestId("stat-overall")).toBeInTheDocument();
    expect(screen.getByTestId("stat-critical")).toBeInTheDocument();
    expect(document.body.textContent).toContain("82%");
    expect(document.body.textContent).toContain("5"); // lessons audited
  });

  test("run audit button calls backend", async () => {
    authFetch.mockResolvedValueOnce(EMPTY_REPORT);
    authFetch.mockResolvedValueOnce(RUN_RESPONSE);
    authFetch.mockResolvedValue(STATUS_COMPLETED);
    render(<AdminQACenterPage user={ADMIN} />);
    await screen.findByTestId("run-audit-btn");
    fireEvent.click(screen.getByTestId("run-audit-btn"));
    await waitFor(() => expect(authFetch).toHaveBeenCalledWith(
      "/api/admin/qa/lesson-quality/run",
      expect.objectContaining({ method: "POST" })
    ));
  });

  test("grade selector works when grade mode selected", async () => {
    authFetch.mockResolvedValueOnce(EMPTY_REPORT);
    render(<AdminQACenterPage user={ADMIN} />);
    await screen.findByTestId("run-audit-panel");
    fireEvent.click(screen.getByTestId("mode-grade"));
    expect(await screen.findByTestId("grade-selector")).toBeInTheDocument();
    fireEvent.change(screen.getByTestId("grade-selector"), { target: { value: "Grade 9" } });
    expect(screen.getByTestId("grade-selector").value).toBe("Grade 9");
  });

  test("subject selector works when subject mode selected", async () => {
    authFetch.mockResolvedValueOnce(EMPTY_REPORT);
    render(<AdminQACenterPage user={ADMIN} />);
    await screen.findByTestId("run-audit-panel");
    fireEvent.click(screen.getByTestId("mode-subject"));
    expect(await screen.findByTestId("subject-selector")).toBeInTheDocument();
  });

  test("LLM warning renders when LLM checkbox enabled", async () => {
    authFetch.mockResolvedValueOnce(EMPTY_REPORT);
    render(<AdminQACenterPage user={ADMIN} />);
    await screen.findByTestId("run-audit-panel");
    fireEvent.click(document.querySelector("#use_llm"));
    expect(await screen.findByTestId("llm-warning")).toBeInTheDocument();
    expect(document.body.textContent).toContain("tokens and incur cost");
  });

  test("E2E not-configured state renders", async () => {
    authFetch.mockResolvedValueOnce(EMPTY_REPORT);
    render(<AdminQACenterPage user={ADMIN} />);
    await screen.findByTestId("run-audit-panel");
    expect(screen.getByTestId("e2e-not-configured")).toBeInTheDocument();
    expect(document.body.textContent).toContain("Not configured yet");
  });

  test("status panel shows polling status", async () => {
    authFetch.mockResolvedValueOnce(EMPTY_REPORT);
    authFetch.mockResolvedValueOnce(RUN_RESPONSE);
    authFetch.mockResolvedValue(STATUS_QUEUED);
    render(<AdminQACenterPage user={ADMIN} />);
    await screen.findByTestId("run-audit-btn");
    fireEvent.click(screen.getByTestId("run-audit-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("job-status-panel")).toBeInTheDocument();
    });
  });

  test("report viewer shows issues panel", async () => {
    authFetch.mockResolvedValueOnce(SAMPLE_REPORT);
    render(<AdminQACenterPage user={ADMIN} />);
    expect(await screen.findByTestId("issues-panel")).toBeInTheDocument();
    expect(document.body.textContent).toContain("Missing lesson content");
  });

  test("severity filter changes visible issues", async () => {
    authFetch.mockResolvedValueOnce(SAMPLE_REPORT);
    render(<AdminQACenterPage user={ADMIN} />);
    await screen.findByTestId("sev-filter");
    fireEvent.change(screen.getByTestId("sev-filter"), { target: { value: "critical" } });
    await waitFor(() => {
      expect(document.body.textContent).toContain("Missing lesson content");
      expect(document.body.textContent).not.toContain("Missing variable definitions");
    });
  });

  test("category filter works", async () => {
    authFetch.mockResolvedValueOnce(SAMPLE_REPORT);
    render(<AdminQACenterPage user={ADMIN} />);
    await screen.findByTestId("cat-filter");
    fireEvent.change(screen.getByTestId("cat-filter"), { target: { value: "formula" } });
    await waitFor(() => {
      expect(document.body.textContent).toContain("Missing variable definitions");
    });
  });

  test("quality gates card renders", async () => {
    authFetch.mockResolvedValueOnce(SAMPLE_REPORT);
    render(<AdminQACenterPage user={ADMIN} />);
    expect(await screen.findByTestId("quality-gates")).toBeInTheDocument();
    expect(document.body.textContent).toContain("Critical Issues");
    expect(document.body.textContent).toContain("= 0");
  });

  test("download buttons render when report exists", async () => {
    authFetch.mockResolvedValueOnce(SAMPLE_REPORT);
    render(<AdminQACenterPage user={ADMIN} />);
    await screen.findByTestId("summary-cards");
    expect(screen.getByTestId("download-json")).toBeInTheDocument();
    expect(screen.getByTestId("download-md")).toBeInTheDocument();
    expect(screen.getByTestId("download-csv")).toBeInTheDocument();
  });

  test("future modules show coming soon", async () => {
    authFetch.mockResolvedValueOnce(EMPTY_REPORT);
    render(<AdminQACenterPage user={ADMIN} />);
    await screen.findByTestId("admin-qa-center");
    expect(document.body.textContent).toContain("Formula Sheet Audit");
    expect(document.body.textContent).toContain("Coming soon");
  });
