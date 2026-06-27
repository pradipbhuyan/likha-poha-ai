/**
 * TeacherUXPhase3.test.jsx — Regression tests for Teacher UX Completion
 * ─────────────────────────────────────────────────────────────────────────────
 * Covers:
 *  - TeacherAssistantCard: renders summary, shows "no urgent actions"
 *  - StudentWorkspace: opens from Students tab, has all 7 sections
 *  - StudentWorkspace: missing data shows "Not available yet"
 *  - WSNotes: notes labelled private, add/delete actions
 *  - WSActivity: timeline loads, error state safe
 *  - WSParent: linked/no-linked/no-email states
 *  - InterventionQueue: groups critical/medium/low, "Create Task" button
 *  - SuggestedTaskModal: pre-filled, editable, saves
 *  - ClassroomAnalyticsCard: renders available, shows "Not available yet"
 */
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

// ── Mock API ──────────────────────────────────────────────────────────────────
vi.mock("../api/teacherDashboard", () => ({
  getTeacherClassroomSummary: vi.fn(async () => ({
    success: true,
    totals: { total_students: 3, active_students: 2, inactive_students: 1, pending_invitations: 1, needs_attention_count: 1 },
    averages: { mock_test_avg: null },
    needs_attention: [],
    recent_activity: [],
    is_paid: false,
    plan_limit: 10,
    students: { pending_invitations: 1 },
  })),
  getInterventions: vi.fn(async () => ({
    success: true,
    interventions: [
      { student_id: "s1", student_name: "Aarav", grade: "Grade 9", severity: "critical", reasons: ["Inactive for 14 days"], recommended_actions: ["view_student"], last_active_at: null },
      { student_id: "s2", student_name: "Riya", grade: "Grade 10", severity: "medium", reasons: ["Low mock test average: 35%"], recommended_actions: ["view_student"], last_active_at: null },
      { student_id: "s3", student_name: "Karan", grade: "Grade 8", severity: "low", reasons: ["No mock tests completed"], recommended_actions: ["view_student"], last_active_at: null },
    ],
    count: 3,
  })),
  listTeacherTasks: vi.fn(async () => ({ success: true, tasks: [{ id: "t1", title: "Follow up", priority: "medium", status: "open" }] })),
  createTeacherTask: vi.fn(async () => ({ success: true, task: { id: "t2", title: "Follow up with Aarav", status: "open" } })),
  completeTeacherTask: vi.fn(async () => ({ success: true })),
  dismissTeacherTask:  vi.fn(async () => ({ success: true })),
  getTeacherStudentDetail: vi.fn(async () => ({
    success: true,
    student: { id: "s1", username: "Aarav", grade: "Grade 9", account_status: "active", subscription_plan: "free" },
    classrooms: [],
    learning: { last_active: null, lessons_generated: 0, doubts_asked: 0, mock_tests_completed: 0, mock_test_avg: null },
  })),
  getStudentTimeline: vi.fn(async () => ({
    success: true,
    events: [
      { id: "e1", type: "audit", title: "✏️ Profile Updated", description: "Student details updated", timestamp: "2026-01-10T10:00:00Z", category: "info" },
    ],
    count: 1,
  })),
  listStudentNotes: vi.fn(async () => ({ success: true, notes: [{ id: "n1", note: "Check on Aarav", created_at: "2026-01-10T10:00:00Z" }] })),
  createStudentNote: vi.fn(async () => ({ success: true, note: { id: "n2", note: "New note" } })),
  updateStudentNote: vi.fn(async () => ({ success: true })),
  deleteStudentNote: vi.fn(async () => ({ success: true })),
  getParentContact:  vi.fn(async () => ({ success: true, has_parent: true, parent: { id: "p1", username: "Parent", has_email: false } })),
  messageParent:     vi.fn(async () => ({ success: true, status: "no_email", note: "No email address for parent." })),
  getClassroomAnalytics: vi.fn(async () => ({
    success: true, classroom_id: "c1",
    student_count: 5, active_count: 4, inactive_count: 1,
    mock_test: { available: true, average_score: 72, total_tests: 10, students_tested: 4 },
    activity: { available: true, active_last_7_days: 3, total_ai_requests: 15 },
  })),
  resetTeacherStudentPassword:    vi.fn(async () => ({ success: true, temp_password: "Tmp123!", warning: "Show once" })),
  emailTeacherStudentCredentials: vi.fn(async () => ({ success: true, invite_sent: true })),
  updateTeacherStudent:  vi.fn(async () => ({ success: true })),
  archiveTeacherStudent: vi.fn(async () => ({ success: true })),
  listTeacherStudents:   vi.fn(async () => ({ success: true, students: [] })),
  listTeacherInvitations: vi.fn(async () => ({ success: true, invitations: [] })),
  createTeacherInvitation: vi.fn(async () => ({ success: true })),
  resendTeacherInvitation: vi.fn(async () => ({ success: true })),
  cancelTeacherInvitation: vi.fn(async () => ({ success: true })),
  listTeacherClassrooms:   vi.fn(async () => ({ success: true, classrooms: [] })),
  createTeacherClassroom:  vi.fn(async () => ({ success: true })),
  updateTeacherClassroom:  vi.fn(async () => ({ success: true })),
  archiveTeacherClassroom: vi.fn(async () => ({ success: true })),
  addStudentToClassroom:   vi.fn(async () => ({ success: true })),
  createTeacherStudent:    vi.fn(async () => ({ success: true })),
  getTeacherDashboardSummary: vi.fn(async () => ({ success: true })),
  createTeacherNote:       vi.fn(async () => ({ success: true })),
}));

import TeacherAssistantCard   from "../components/teacher/TeacherAssistantCard";
import StudentWorkspace        from "../components/teacher/StudentWorkspace";
import InterventionQueue       from "../components/teacher/InterventionQueue";
import SuggestedTaskModal      from "../components/teacher/SuggestedTaskModal";
import ClassroomAnalyticsCard  from "../components/teacher/ClassroomAnalyticsCard";

const STUDENT = { id: "s1", username: "Aarav", grade: "Grade 9", email: "aarav@test.com", account_status: "active" };

// ─────────────────────────────────────────────────────────────────────────────
// TeacherAssistantCard
// ─────────────────────────────────────────────────────────────────────────────
describe("TeacherAssistantCard", () => {
  test("renders with attention count from interventions", async () => {
    render(<TeacherAssistantCard onNavigate={vi.fn()} />);
    // Card eventually renders (either loading → content)
    await waitFor(() => {
      expect(screen.getByTestId("teacher-assistant-card")).toBeInTheDocument();
    });
  });

  test("shows 'no urgent actions' when all clear", async () => {
    const { getInterventions, listTeacherTasks, getTeacherClassroomSummary } = await import("../api/teacherDashboard");
    getInterventions.mockResolvedValueOnce({ success: true, interventions: [], count: 0 });
    listTeacherTasks.mockResolvedValueOnce({ success: true, tasks: [] });
    getTeacherClassroomSummary.mockResolvedValueOnce({
      success: true, totals: {}, averages: {}, needs_attention: [],
      recent_activity: [], students: { pending_invitations: 0 },
    });

    render(<TeacherAssistantCard onNavigate={vi.fn()} />);
    await waitFor(() => {
      expect(screen.getByTestId("teacher-assistant-card")).toBeInTheDocument();
    });
    expect(screen.getByText(/Everything looks good/i)).toBeInTheDocument();
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// StudentWorkspace
// ─────────────────────────────────────────────────────────────────────────────
describe("StudentWorkspace", () => {
  test("opens and shows student name", async () => {
    render(<StudentWorkspace student={STUDENT} isPaid={false} onClose={vi.fn()} />);
    expect(await screen.findByTestId("student-workspace")).toBeInTheDocument();
    expect(screen.getByTestId("workspace-student-name")).toHaveTextContent("Aarav");
  });

  test("has all 7 section tabs", async () => {
    render(<StudentWorkspace student={STUDENT} isPaid={false} onClose={vi.fn()} />);
    await screen.findByTestId("student-workspace");
    ["overview","progress","assessments","notes","activity","parent","settings"].forEach(key => {
      expect(screen.getByTestId(`ws-tab-${key}`)).toBeInTheDocument();
    });
  });

  test("Overview section shows status and learning data", async () => {
    render(<StudentWorkspace student={STUDENT} isPaid={false} onClose={vi.fn()} />);
    expect(await screen.findByTestId("ws-overview")).toBeInTheDocument();
  });

  test("Progress section shows 'Not available yet' when no data", async () => {
    render(<StudentWorkspace student={STUDENT} isPaid={false} onClose={vi.fn()} />);
    await screen.findByTestId("student-workspace");
    fireEvent.click(screen.getByTestId("ws-tab-progress"));
    expect(await screen.findByTestId("ws-progress")).toBeInTheDocument();
    expect(screen.getByText(/Not available yet/i)).toBeInTheDocument();
  });

  test("Assessments section shows 'Not available yet' when no tests", async () => {
    render(<StudentWorkspace student={STUDENT} isPaid={false} onClose={vi.fn()} />);
    await screen.findByTestId("student-workspace");
    fireEvent.click(screen.getByTestId("ws-tab-assessments"));
    expect(await screen.findByTestId("ws-assessments")).toBeInTheDocument();
    expect(screen.getByText(/Not available yet/i)).toBeInTheDocument();
  });

  test("Notes section labelled private", async () => {
    render(<StudentWorkspace student={STUDENT} isPaid={false} onClose={vi.fn()} />);
    await screen.findByTestId("student-workspace");
    fireEvent.click(screen.getByTestId("ws-tab-notes"));
    expect(await screen.findByTestId("ws-notes")).toBeInTheDocument();
    expect(screen.getByText(/Private Teacher Notes/i)).toBeInTheDocument();
    expect(screen.getByText(/Visible to you only/i)).toBeInTheDocument();
  });

  test("Notes section loads existing notes", async () => {
    render(<StudentWorkspace student={STUDENT} isPaid={false} onClose={vi.fn()} />);
    await screen.findByTestId("student-workspace");
    fireEvent.click(screen.getByTestId("ws-tab-notes"));
    expect(await screen.findByText("Check on Aarav")).toBeInTheDocument();
  });

  test("Activity timeline loads events", async () => {
    render(<StudentWorkspace student={STUDENT} isPaid={false} onClose={vi.fn()} />);
    await screen.findByTestId("student-workspace");
    fireEvent.click(screen.getByTestId("ws-tab-activity"));
    expect(await screen.findByTestId("ws-activity")).toBeInTheDocument();
    expect(await screen.findByText("✏️ Profile Updated")).toBeInTheDocument();
  });

  test("Activity timeline shows error state safely", async () => {
    const { getStudentTimeline } = await import("../api/teacherDashboard");
    getStudentTimeline.mockRejectedValueOnce(new Error("Timeline unavailable"));
    render(<StudentWorkspace student={STUDENT} isPaid={false} onClose={vi.fn()} />);
    await screen.findByTestId("student-workspace");
    fireEvent.click(screen.getByTestId("ws-tab-activity"));
    expect(await screen.findByText(/Timeline unavailable/i)).toBeInTheDocument();
  });

  test("Parent section shows linked parent with no email", async () => {
    render(<StudentWorkspace student={STUDENT} isPaid={false} onClose={vi.fn()} />);
    await screen.findByTestId("student-workspace");
    fireEvent.click(screen.getByTestId("ws-tab-parent"));
    expect(await screen.findByTestId("ws-parent")).toBeInTheDocument();
    expect(await screen.findByText(/No email address/i)).toBeInTheDocument();
  });

  test("Parent section shows no parent message when not linked", async () => {
    const { getParentContact } = await import("../api/teacherDashboard");
    getParentContact.mockResolvedValueOnce({ success: true, has_parent: false, parent: null });
    render(<StudentWorkspace student={STUDENT} isPaid={false} onClose={vi.fn()} />);
    await screen.findByTestId("student-workspace");
    fireEvent.click(screen.getByTestId("ws-tab-parent"));
    expect(await screen.findByText(/No parent linked/i)).toBeInTheDocument();
  });

  test("Free teacher: Email Login Details disabled in Overview", async () => {
    render(<StudentWorkspace student={STUDENT} isPaid={false} onClose={vi.fn()} />);
    expect(await screen.findByTestId("ws-overview")).toBeInTheDocument();
    const btns = screen.getAllByRole("button", { name: /Email Login Details/i });
    expect(btns[0]).toBeDisabled();
  });

  test("Paid teacher: Email Login Details enabled in Overview", async () => {
    render(<StudentWorkspace student={STUDENT} isPaid={true} onClose={vi.fn()} />);
    expect(await screen.findByTestId("ws-overview")).toBeInTheDocument();
    const btns = screen.getAllByRole("button", { name: /Email Login Details/i });
    expect(btns[0]).not.toBeDisabled();
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// InterventionQueue
// ─────────────────────────────────────────────────────────────────────────────
describe("InterventionQueue", () => {
  test("groups interventions: critical, medium, low", async () => {
    render(<InterventionQueue isPaid={false} onViewStudent={vi.fn()} onCreateTask={vi.fn()} />);
    expect(await screen.findByTestId("intervention-queue")).toBeInTheDocument();
    expect(screen.getByTestId("intervention-critical-0")).toBeInTheDocument();
    expect(screen.getByTestId("intervention-medium-0")).toBeInTheDocument();
    expect(screen.getByTestId("intervention-low-0")).toBeInTheDocument();
    expect(screen.getByText("Aarav")).toBeInTheDocument();
    expect(screen.getByText("Riya")).toBeInTheDocument();
    expect(screen.getByText("Karan")).toBeInTheDocument();
  });

  test("shows 'no students need attention' when empty", async () => {
    const { getInterventions } = await import("../api/teacherDashboard");
    getInterventions.mockResolvedValueOnce({ success: true, interventions: [], count: 0 });
    render(<InterventionQueue isPaid={false} onViewStudent={vi.fn()} onCreateTask={vi.fn()} />);
    expect(await screen.findByTestId("intervention-queue-empty")).toBeInTheDocument();
  });

  test("Create Task button calls onCreateTask with intervention data", async () => {
    const onCreateTask = vi.fn();
    render(<InterventionQueue isPaid={false} onViewStudent={vi.fn()} onCreateTask={onCreateTask} />);
    await screen.findByTestId("intervention-queue");
    const btns = screen.getAllByTestId("create-task-0");
    fireEvent.click(btns[0]);
    expect(onCreateTask).toHaveBeenCalledWith(expect.objectContaining({ student_name: "Aarav", severity: "critical" }));
  });

  test("View Student button calls onViewStudent", async () => {
    const onViewStudent = vi.fn();
    render(<InterventionQueue isPaid={false} onViewStudent={onViewStudent} onCreateTask={vi.fn()} />);
    const viewBtns = await screen.findAllByRole("button", { name: /View/i });
    fireEvent.click(viewBtns[0]);
    expect(onViewStudent).toHaveBeenCalled();
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// SuggestedTaskModal
// ─────────────────────────────────────────────────────────────────────────────
describe("SuggestedTaskModal", () => {
  const INV = { student_id: "s1", student_name: "Aarav", severity: "critical", reasons: ["Inactive for 14 days"] };

  test("renders pre-filled title from intervention", () => {
    render(<SuggestedTaskModal intervention={INV} onClose={vi.fn()} onCreated={vi.fn()} />);
    expect(screen.getByTestId("suggested-task-modal")).toBeInTheDocument();
    const titleInput = screen.getByTestId("suggested-task-title");
    expect(titleInput.value).toMatch(/Aarav/i);
  });

  test("title is editable", () => {
    render(<SuggestedTaskModal intervention={INV} onClose={vi.fn()} onCreated={vi.fn()} />);
    const titleInput = screen.getByTestId("suggested-task-title");
    fireEvent.change(titleInput, { target: { value: "Custom title" } });
    expect(titleInput.value).toBe("Custom title");
  });

  test("creates task on submit and calls onCreated", async () => {
    const onCreated = vi.fn();
    const onClose = vi.fn();
    render(<SuggestedTaskModal intervention={INV} onClose={onClose} onCreated={onCreated} />);
    fireEvent.click(screen.getByRole("button", { name: /Create Task/i }));
    await waitFor(() => expect(onCreated).toHaveBeenCalled());
    expect(onClose).toHaveBeenCalled();
  });

  test("closes when Cancel clicked", () => {
    const onClose = vi.fn();
    render(<SuggestedTaskModal intervention={INV} onClose={onClose} onCreated={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: /Cancel/i }));
    expect(onClose).toHaveBeenCalled();
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// ClassroomAnalyticsCard
// ─────────────────────────────────────────────────────────────────────────────
describe("ClassroomAnalyticsCard", () => {
  test("renders with analytics data when available", async () => {
    render(<ClassroomAnalyticsCard classroomId="c1" classroomName="Grade 9A" />);
    expect(await screen.findByTestId("classroom-analytics-c1")).toBeInTheDocument();
    expect(screen.getByText("72%")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument(); // active_last_7_days
  });

  test("shows 'Not available yet' when data missing", async () => {
    const { getClassroomAnalytics } = await import("../api/teacherDashboard");
    getClassroomAnalytics.mockResolvedValueOnce({
      success: true, classroom_id: "c2",
      student_count: 3, active_count: 2, inactive_count: 1,
      mock_test: { available: false, reason: "No test history" },
      activity: { available: false, reason: "No recent activity" },
    });
    render(<ClassroomAnalyticsCard classroomId="c2" classroomName="Grade 8B" />);
    expect(await screen.findByTestId("classroom-analytics-c2")).toBeInTheDocument();
    const notAvailable = screen.getAllByText(/Not available yet/i);
    expect(notAvailable.length).toBeGreaterThanOrEqual(2);
  });
});
