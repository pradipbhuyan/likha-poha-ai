import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import TeacherDashboardPage from "../pages/TeacherDashboardPage";
import {
  createTeacherNote,
  getTeacherDashboardSummary,
} from "../api/teacherDashboard";

vi.mock("../api/teacherDashboard", () => ({
  getTeacherDashboardSummary: vi.fn(),
  createTeacherNote: vi.fn(),
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

  test("renders assigned students and saves a teacher note", async () => {
    render(<TeacherDashboardPage user={teacherUser} />);

    expect(await screen.findAllByText("Akshita")).toHaveLength(2);
    expect(screen.getByText("Motion")).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText("Science"), {
      target: { value: "Science" },
    });
    fireEvent.change(screen.getByPlaceholderText("Motion"), {
      target: { value: "Motion" },
    });
    fireEvent.change(
      screen.getByPlaceholderText(
        "Add a follow-up, intervention, or parent update."
      ),
      {
        target: { value: "Revise speed and velocity." },
      }
    );

    fireEvent.click(screen.getByRole("button", { name: /save note/i }));

    await waitFor(() => {
      expect(createTeacherNote).toHaveBeenCalledWith({
        student_id: "student-1",
        subject: "Science",
        chapter: "Motion",
        note: "Revise speed and velocity.",
      });
    });
  });

  test("filters assigned students by subject", async () => {
    getTeacherDashboardSummary.mockResolvedValue({
      success: true,
      summary: {
        assigned_students: 2,
        active_grades: ["Grade 8", "Grade 9"],
        subjects: ["Maths", "Science"],
        total_assignments: 2,
      },
      students: [
        {
          profile: {
            id: "student-1",
            username: "Akshita",
            email: "akshita@example.com",
            grade: "Grade 9",
          },
          assignments: [{ grade: "Grade 9", subject: "Science" }],
          activity: {},
          progress_summary: {},
          recent_progress: [],
          notes: [],
        },
        {
          profile: {
            id: "student-2",
            username: "Rohan",
            email: "rohan@example.com",
            grade: "Grade 8",
          },
          assignments: [{ grade: "Grade 8", subject: "Maths" }],
          activity: {},
          progress_summary: {},
          recent_progress: [],
          notes: [],
        },
      ],
    });

    render(<TeacherDashboardPage user={teacherUser} />);

    expect(await screen.findByText("Rohan")).toBeInTheDocument();

    fireEvent.change(screen.getAllByLabelText(/subject/i)[0], {
      target: { value: "Science" },
    });

    expect(screen.getAllByText("Akshita").length).toBeGreaterThan(0);
    expect(screen.queryByText("Rohan")).not.toBeInTheDocument();
  });

  test("shows empty roster guidance when no students are assigned", async () => {
    getTeacherDashboardSummary.mockResolvedValue({
      success: true,
      summary: {
        assigned_students: 0,
        active_grades: [],
        subjects: [],
        total_assignments: 0,
      },
      students: [],
    });

    render(<TeacherDashboardPage user={teacherUser} />);

    expect(
      await screen.findByText(/ask an admin to assign students/i)
    ).toBeInTheDocument();
  });

  test("shows a helpful error if teacher dashboard loading fails", async () => {
    getTeacherDashboardSummary.mockRejectedValue(
      new Error("Teacher access required")
    );

    render(<TeacherDashboardPage user={teacherUser} />);

    expect(await screen.findByText(/teacher access required/i)).toBeInTheDocument();
  });
});
