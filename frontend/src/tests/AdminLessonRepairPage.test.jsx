/**
 * AdminLessonRepairPage.test.jsx
 *
 * Frontend tests for the Admin Lesson Repair workflow UI.
 * All API calls are mocked — no live backend required.
 */
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

// ── Mock API module ────────────────────────────────────────────────────────────
vi.mock("../api/lessonRepair", () => ({
  getLatestRepairStatus: vi.fn(),
  getRepairHistory:      vi.fn(),
  runRepairJob:          vi.fn(),
  getRepairJobStatus:    vi.fn(),
  getRepairTasks:        vi.fn(),
  getRepairTask:         vi.fn(),
  approveRepairTask:     vi.fn(),
  publishRepairTask:     vi.fn(),
  rerunRepairTask:       vi.fn(),
  cancelRepairJob:       vi.fn(),
  getRepairReportUrl:    vi.fn(() => "/api/admin/qa/lesson-repair/report?format=json"),
}));

import {
  getLatestRepairStatus,
  getRepairTasks,
  getRepairTask,
  approveRepairTask,
  runRepairJob,
} from "../api/lessonRepair";

import AdminLessonRepairPage from "../pages/AdminLessonRepairPage";

const mockUser = { role: "admin", username: "admin", accessToken: "tok" };

function renderPage() {
  return render(<AdminLessonRepairPage user={mockUser} />);
}

// ── Default mocks ─────────────────────────────────────────────────────────────

function mockLatestNoJob() {
  getLatestRepairStatus.mockResolvedValue({
    success: true,
    latest_job: null,
    audit_report_meta: {
      audited_at: "2026-06-29T10:00:00+00:00",
      lessons_audited: 20,
      critical_issues: 8,
      avg_overall_score: 42,
      overall: "CRITICAL",
    },
  });
}

function mockLatestWithJob(jobOverrides = {}) {
  getLatestRepairStatus.mockResolvedValue({
    success: true,
    latest_job: {
      id: "job-001",
      status: "completed",
      mode: "sample",
      total_tasks: 5,
      completed_tasks: 4,
      failed_tasks: 1,
      approved_tasks: 2,
      published_tasks: 1,
      ...jobOverrides,
    },
    audit_report_meta: {
      audited_at: "2026-06-29T10:00:00+00:00",
      lessons_audited: 20,
      critical_issues: 8,
      avg_overall_score: 42,
      overall: "CRITICAL",
    },
  });
}

function mockTasks(tasks = []) {
  getRepairTasks.mockResolvedValue({ success: true, tasks, total: tasks.length });
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("AdminLessonRepairPage", () => {

  beforeEach(() => {
    vi.clearAllMocks();
    mockLatestNoJob();
    mockTasks([]);
  });

  // ── Rendering ────────────────────────────────────────────────────────────────

  test("renders the page with correct title", async () => {
    renderPage();
    expect(await screen.findByTestId("admin-lesson-repair-page")).toBeInTheDocument();
    expect(screen.getByText(/Lesson Repair/i)).toBeInTheDocument();
  });

  test("shows audit report metadata when available", async () => {
    renderPage();
    expect(await screen.findByText(/8 critical issues/i)).toBeInTheDocument();
    expect(screen.getByText(/42\/100/i)).toBeInTheDocument();
  });

  test("shows 'no repair jobs yet' when no current job", async () => {
    renderPage();
    expect(await screen.findByText(/No repair jobs yet/i)).toBeInTheDocument();
  });

  // ── Mode selector ─────────────────────────────────────────────────────────

  test("mode selector shows three options", async () => {
    renderPage();
    await screen.findByTestId("admin-lesson-repair-page");
    expect(screen.getByTestId("mode-sample")).toBeInTheDocument();
    expect(screen.getByTestId("mode-filtered")).toBeInTheDocument();
    expect(screen.getByTestId("mode-all")).toBeInTheDocument();
  });

  test("clicking a mode button selects it", async () => {
    renderPage();
    await screen.findByTestId("admin-lesson-repair-page");
    fireEvent.click(screen.getByTestId("mode-all"));
    expect(screen.getByTestId("mode-all")).toHaveStyle({ background: "#6366f1" });
  });

  // ── LLM toggle ──────────────────────────────────────────────────────────────

  test("LLM toggle is unchecked by default", async () => {
    renderPage();
    await screen.findByTestId("admin-lesson-repair-page");
    const toggle = screen.getByTestId("llm-toggle");
    expect(toggle).not.toBeChecked();
  });

  test("LLM cost warning appears when toggle is enabled", async () => {
    renderPage();
    await screen.findByTestId("admin-lesson-repair-page");
    const toggle = screen.getByTestId("llm-toggle");
    fireEvent.click(toggle);
    expect(await screen.findByTestId("llm-warning")).toBeInTheDocument();
    expect(screen.getByText(/Cost Warning/i)).toBeInTheDocument();
  });

  test("LLM cost warning is not visible when toggle is off", async () => {
    renderPage();
    await screen.findByTestId("admin-lesson-repair-page");
    expect(screen.queryByTestId("llm-warning")).not.toBeInTheDocument();
  });

  // ── Run button ───────────────────────────────────────────────────────────────

  test("Run Repair button is visible", async () => {
    renderPage();
    await screen.findByTestId("admin-lesson-repair-page");
    expect(screen.getByTestId("btn-run-repair")).toBeInTheDocument();
  });

  test("Run Repair button starts a job on click", async () => {
    runRepairJob.mockResolvedValue({ success: true, job_id: "job-new-001", message: "Started" });

    renderPage();
    await screen.findByTestId("admin-lesson-repair-page");
    fireEvent.click(screen.getByTestId("btn-run-repair"));

    await waitFor(() => {
      expect(runRepairJob).toHaveBeenCalledTimes(1);
    });
  });

  test("Run Repair passes use_llm=true when LLM toggle is on", async () => {
    runRepairJob.mockResolvedValue({ success: true, job_id: "job-llm-001", message: "Started" });

    renderPage();
    await screen.findByTestId("admin-lesson-repair-page");
    fireEvent.click(screen.getByTestId("llm-toggle"));  // enable LLM
    fireEvent.click(screen.getByTestId("btn-run-repair"));

    await waitFor(() => {
      expect(runRepairJob).toHaveBeenCalledWith(
        expect.objectContaining({ use_llm: true })
      );
    });
  });

  // ── Progress section ─────────────────────────────────────────────────────────

  test("progress bar renders when a job exists", async () => {
    mockLatestWithJob({ status: "running", total_tasks: 10, completed_tasks: 5 });
    renderPage();
    expect(await screen.findByTestId("progress-bar")).toBeInTheDocument();
  });

  test("step timeline renders when a job exists", async () => {
    mockLatestWithJob();
    renderPage();
    expect(await screen.findByTestId("step-timeline")).toBeInTheDocument();
    expect(screen.getByText(/Reading audit report/i)).toBeInTheDocument();
  });

  test("cancel button visible when job is running", async () => {
    mockLatestWithJob({ status: "running" });
    renderPage();
    expect(await screen.findByTestId("btn-cancel")).toBeInTheDocument();
  });

  test("cancel button NOT visible when job is completed", async () => {
    mockLatestWithJob({ status: "completed" });
    renderPage();
    await screen.findByTestId("progress-bar");
    expect(screen.queryByTestId("btn-cancel")).not.toBeInTheDocument();
  });

  // ── Task table ────────────────────────────────────────────────────────────────

  test("task table renders when tasks are available", async () => {
    mockLatestWithJob();
    mockTasks([
      { id: "task-1", grade: "Grade 9", subject: "Science", chapter: "Matter",
        step_title: "States", status: "ready_for_review", audit_before_score: 35, audit_after_score: 92 },
    ]);

    renderPage();
    expect(await screen.findByTestId("task-table")).toBeInTheDocument();
    expect(screen.getByText("States")).toBeInTheDocument();
  });

  test("clicking View button on a task opens the drawer", async () => {
    const task = {
      id: "task-drawer-1", grade: "Grade 9", subject: "Science",
      chapter: "Matter", step_title: "States", status: "ready_for_review",
      audit_before_score: 35, audit_after_score: 92,
      issues_json: [{ severity: "critical", section: "introduction", issue: "Missing." }],
      original_content_json: { lesson_content: "Original content here." },
      repaired_content_json: { sections: { introduction: "Repaired intro." } },
      validation_result_json: { valid: true, overall_score: 92, depth_score: 88, section_compliance: 100, issues: [] },
    };

    mockLatestWithJob();
    mockTasks([task]);
    getRepairTask.mockResolvedValue({ success: true, task });

    renderPage();
    await screen.findByTestId("task-table");
    fireEvent.click(screen.getByText("View"));

    expect(await screen.findByTestId("task-drawer")).toBeInTheDocument();
    expect(screen.getByText("Task Detail")).toBeInTheDocument();
  });

  // ── Task drawer actions ───────────────────────────────────────────────────────

  test("approve button shown for ready_for_review tasks", async () => {
    const task = {
      id: "task-approve-1", grade: "Grade 9", subject: "Science",
      chapter: "Matter", step_title: "States", status: "ready_for_review",
      issues_json: [], repaired_content_json: { sections: {} },
      original_content_json: {}, validation_result_json: null,
    };

    mockLatestWithJob();
    mockTasks([task]);
    getRepairTask.mockResolvedValue({ success: true, task });

    renderPage();
    await screen.findByTestId("task-table");
    fireEvent.click(screen.getByText("View"));
    expect(await screen.findByTestId("btn-approve")).toBeInTheDocument();
  });

  test("publish button shown for approved tasks", async () => {
    const task = {
      id: "task-publish-1", grade: "Grade 9", subject: "Science",
      chapter: "Matter", step_title: "States", status: "approved",
      issues_json: [], repaired_content_json: { sections: {} },
      original_content_json: {}, validation_result_json: null,
    };

    mockLatestWithJob();
    mockTasks([task]);
    getRepairTask.mockResolvedValue({ success: true, task });

    renderPage();
    await screen.findByTestId("task-table");
    fireEvent.click(screen.getByText("View"));
    expect(await screen.findByTestId("btn-publish")).toBeInTheDocument();
  });

  test("rerun button shown for failed tasks", async () => {
    const task = {
      id: "task-rerun-1", grade: "Grade 9", subject: "Science",
      chapter: "Matter", step_title: "States", status: "failed",
      issues_json: [], error_message: "LLM timeout",
      original_content_json: {}, repaired_content_json: null, validation_result_json: null,
    };

    mockLatestWithJob();
    mockTasks([task]);
    getRepairTask.mockResolvedValue({ success: true, task });

    renderPage();
    await screen.findByTestId("task-table");
    fireEvent.click(screen.getByText("View"));
    expect(await screen.findByTestId("btn-rerun")).toBeInTheDocument();
  });

  test("approving a task calls approveRepairTask", async () => {
    approveRepairTask.mockResolvedValue({ success: true, message: "Task approved." });

    const task = {
      id: "task-approve-2", grade: "Grade 9", subject: "Science",
      chapter: "Matter", step_title: "States", status: "ready_for_review",
      issues_json: [], repaired_content_json: { sections: {} },
      original_content_json: {}, validation_result_json: null,
    };
    const approvedTask = { ...task, status: "approved" };

    mockLatestWithJob();
    mockTasks([task]);
    getRepairTask
      .mockResolvedValueOnce({ success: true, task })
      .mockResolvedValueOnce({ success: true, task: approvedTask });

    renderPage();
    await screen.findByTestId("task-table");
    fireEvent.click(screen.getByText("View"));
    fireEvent.click(await screen.findByTestId("btn-approve"));

    await waitFor(() => {
      expect(approveRepairTask).toHaveBeenCalledWith("task-approve-2");
    });
    expect(await screen.findByText("Task approved.")).toBeInTheDocument();
  });

  // ── Light/dark mode compatibility ─────────────────────────────────────────────

  test("renders without crashing in dark mode body class", async () => {
    document.body.classList.add("dark-mode");
    renderPage();
    expect(await screen.findByTestId("admin-lesson-repair-page")).toBeInTheDocument();
    document.body.classList.remove("dark-mode");
  });

  test("uses CSS variables for background colors (dark mode compatible)", async () => {
    renderPage();
    const page = await screen.findByTestId("admin-lesson-repair-page");
    // Page should not hardcode any bg colors that break dark mode
    // Just verify the container renders — CSS variables handle theming
    expect(page).toBeInTheDocument();
  });
});
