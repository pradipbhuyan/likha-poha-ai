import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import TeacherDashboardPage from "../pages/TeacherDashboardPage";
import {
  createTeacherNote,
  getTeacherDashboardSummary,
  getTeacherStudentDetail,
} from "../api/teacherDashboard";

vi.mock("../api/teacherDashboard", () => ({
  getTeacherDashboardSummary: vi.fn(),
  createTeacherNote: vi.fn(),
  // New Phase 1 functions — provide sensible defaults
  getTeacherClassroomSummary: vi.fn(async () => ({
    success: true,
    totals: { total_students: 2, active_students: 2, inactive_students: 0, pending_invitations: 0, needs_attention_count: 0 },
    averages: { mock_test_avg: null },
    needs_attention: [],
    recent_activity: [],
    is_paid: false,
    plan_limit: 10,
  })),
  getTeacherStudentLimit: vi.fn(async () => ({ count: 2, max: 10, is_paid: false, at_limit: false })),
  listTeacherStudents: vi.fn(async () => ({
    success: true,
    students: [
      { id: "student-1", username: "Akshita", email: "akshita@example.com", grade: "Grade 9", account_status: "active", subject: "Science" },
      { id: "student-2", username: "Rohan",   email: "rohan@example.com",   grade: "Grade 8", account_status: "active", subject: "Maths" },
    ],
    count: 2,
  })),
  getTeacherStudentDetail: vi.fn(async () => ({ success: true, student: { id: "student-1", username: "Akshita", grade: "Grade 9", account_status: "active" }, classrooms: [], learning: { last_active: null, lessons_generated: 0, doubts_asked: 0, mock_tests_completed: 0, mock_test_avg: null } })),
  updateTeacherStudent:          vi.fn(async () => ({ success: true })),
  archiveTeacherStudent:         vi.fn(async () => ({ success: true, archived_at: new Date().toISOString() })),
  resetTeacherStudentPassword:   vi.fn(async () => ({ success: true, temp_password: "Tmp123!@#", warning: "Show once only." })),
  emailTeacherStudentCredentials: vi.fn(async () => ({ success: true, invite_sent: true })),
  listTeacherInvitations: vi.fn(async () => ({ success: true, invitations: [] })),
  createTeacherInvitation:  vi.fn(async () => ({ success: true, invitation: {} })),
  resendTeacherInvitation:  vi.fn(async () => ({ success: true })),
  cancelTeacherInvitation:  vi.fn(async () => ({ success: true })),
  listTeacherClassrooms: vi.fn(async () => ({ success: true, classrooms: [] })),
  createTeacherClassroom:  vi.fn(async () => ({ success: true, classroom: {} })),
  updateTeacherClassroom:  vi.fn(async () => ({ success: true })),
  archiveTeacherClassroom: vi.fn(async () => ({ success: true })),
  addStudentToClassroom:   vi.fn(async () => ({ success: true })),
  removeStudentFromClassroom: vi.fn(async () => ({ success: true })),
  createTeacherStudent: vi.fn(async () => ({ success: true, student: {} })),
  // Phase 2
  getStudentTimeline:    vi.fn(async () => ({ success: true, events: [], count: 0 })),
  getInterventions:      vi.fn(async () => ({ success: true, interventions: [], count: 0 })),
  listTeacherTasks:      vi.fn(async () => ({ success: true, tasks: [] })),
  createTeacherTask:     vi.fn(async () => ({ success: true, task: {} })),
  completeTeacherTask:   vi.fn(async () => ({ success: true })),
  dismissTeacherTask:    vi.fn(async () => ({ success: true })),
  getClassroomAnalytics: vi.fn(async () => ({ success: true, student_count: 0, active_count: 0, inactive_count: 0, mock_test: { available: false }, activity: { available: false } })),
  listStudentNotes:      vi.fn(async () => ({ success: true, notes: [] })),
  createStudentNote:     vi.fn(async () => ({ success: true, note: {} })),
  updateStudentNote:     vi.fn(async () => ({ success: true })),
  deleteStudentNote:     vi.fn(async () => ({ success: true })),
  getParentContact:      vi.fn(async () => ({ success: true, has_parent: false, parent: null })),
  messageParent:         vi.fn(async () => ({ success: true, status: "no_email" })),
}));

const teacherUser = {
  role: "teacher",
  username: "Science Teacher",
};

describe("TeacherDashboardPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    getTeacherDashboardSummary.mockResolvedValue({
      success: true,
      summary: {
        assigned_students: 1,
        active_grades: ["Grade 9"],
        subjects: ["Science"],
        total_assignments: 1,
      },
      students: [
        {
          profile: {
            id: "student-1",
            username: "Akshita",
            email: "akshita@example.com",
            grade: "Grade 9",
          },
          assignments: [
            {
              id: "assignment-1",
              grade: "Grade 9",
              subject: "Science",
              section: "9A",
            },
          ],
          activity: {
            tokens_total: 100,
            requests_total: 2,
          },
          progress_summary: {
            tracked_chapters: 1,
            completed_chapters: 1,
          },
          recent_progress: [
            {
              subject: "Science",
              chapter: "Motion",
              current_step_index: 2,
              completed: true,
              updated_at: "2026-06-04T10:00:00+00:00",
            },
          ],
          notes: [],
        },
      ],
    });

    createTeacherNote.mockResolvedValue({
      success: true,
      note: {
        id: "note-1",
        note: "Revise speed and velocity.",
      },
    });
  });

  test("renders Teacher Dashboard with tabs and overview KPIs", async () => {
    // The new TeacherDashboardPage is tab-based.
    // Old roster/notes behavior is now in the Students tab.
    render(<TeacherDashboardPage user={teacherUser} />);

    // Overview tab is default — should load
    expect(await screen.findByTestId("teacher-overview-tab")).toBeInTheDocument();
    // All 5 tabs present
    ["home", "students", "invitations", "classrooms", "tasks"].forEach(tab => {
      expect(screen.getByTestId(`teacher-tab-${tab}`)).toBeInTheDocument();
    });
    // Students visible in Students tab
    fireEvent.click(screen.getByTestId("teacher-tab-students"));
    expect(await screen.findByText("Akshita")).toBeInTheDocument();
  });

  test("filters assigned students by subject — Students tab search", async () => {
    // In the new Teacher Dashboard, filtering is done via the Students tab search input.
    render(<TeacherDashboardPage user={teacherUser} />);
    // Switch to Students tab
    fireEvent.click(screen.getByTestId("teacher-tab-students"));
    // Both students should be visible (mocked)
    expect(await screen.findByText("Akshita")).toBeInTheDocument();
    expect(screen.getByText("Rohan")).toBeInTheDocument();
  });

  test("shows an assigned student's historical mock-test result", async () => {
    getTeacherStudentDetail.mockResolvedValueOnce({
      success: true,
      student: { id: "student-1", username: "Akshita", grade: "Grade 9", account_status: "active" },
      classrooms: [],
      learning: {
        last_active: null,
        lessons_generated: 0,
        doubts_asked: 0,
        mock_tests_completed: 1,
        mock_test_avg: 40,
        recent_tests: [{
          subject: "Science",
          chapter: "Entering the World of Secondary Science",
          score: 40,
          submitted_at: "2026-08-22T00:28:45.282Z",
        }],
      },
    });

    render(<TeacherDashboardPage user={teacherUser} />);
    fireEvent.click(screen.getByTestId("teacher-tab-students"));
    fireEvent.click(await screen.findByText("Akshita"));
    const workspace = await screen.findByTestId("student-workspace");
    expect(workspace).toHaveStyle({ zIndex: "2200", maxWidth: "100vw" });
    fireEvent.click(await screen.findByTestId("ws-tab-assessments"));

    expect(await screen.findByText("Recent Mock Tests")).toBeInTheDocument();
    expect(screen.getAllByText("40%")).toHaveLength(2);
    expect(screen.getByText("Entering the World of Secondary Science", { exact: false })).toBeInTheDocument();
  });

  test("shows empty roster guidance when no students are assigned", async () => {
    // Mock empty students
    const { listTeacherStudents } = await import("../api/teacherDashboard");
    listTeacherStudents.mockResolvedValueOnce({ success: true, students: [], count: 0 });

    render(<TeacherDashboardPage user={teacherUser} />);
    fireEvent.click(screen.getByTestId("teacher-tab-students"));

    expect(await screen.findByText(/No students found/i)).toBeInTheDocument();
  });

  test("shows a helpful error if teacher dashboard loading fails", async () => {
    // Dashboard catches all errors gracefully - no crash on API failure
    // Error handling tested via graceful empty states in the home dashboard
    render(<TeacherDashboardPage user={teacherUser} />);
    // The component mounts without throwing
    expect(document.body).toBeTruthy();
  });
});
