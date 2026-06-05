import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import AdminSyllabusReviewPage from "../pages/AdminSyllabusReviewPage";
import {
  getAdminSyllabusReview,
  saveAdminSubjectOverride,
  saveAdminSyllabusOverride,
} from "../api/syllabus";

vi.mock("../api/syllabus", () => ({
  getAdminSyllabusReview: vi.fn(),
  saveAdminSubjectOverride: vi.fn(),
  saveAdminSyllabusOverride: vi.fn(),
}));

const adminUser = {
  role: "admin",
  username: "Pradip Admin",
  accessToken: "admin-token",
};

describe("AdminSyllabusReviewPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    getAdminSyllabusReview.mockResolvedValue({
      success: true,
      syllabus: {
        "Grade 8": {
          CBSE: {
            Maths: [
              "Front Matter",
              "Chapter 1: Percentages",
              "Chapter 2: Doubling a Square",
            ],
            Science: ["Chapter 1: Crop Production"],
            "Computer Science": ["Uploaded Book Content"],
          },
        },
      },
      content_status: [
        {
          grade: "Grade 8",
          mode: "CBSE",
          subject: "Maths",
          chapter: "Front Matter",
          document_count: 0,
          has_content: false,
        },
        {
          grade: "Grade 8",
          mode: "CBSE",
          subject: "Maths",
          chapter: "Chapter 1: Percentages",
          document_count: 1,
          has_content: true,
        },
        {
          grade: "Grade 8",
          mode: "CBSE",
          subject: "Maths",
          chapter: "Chapter 2: Doubling a Square",
          document_count: 0,
          has_content: false,
        },
      ],
      overrides: [],
      subject_overrides: [],
    });

    saveAdminSubjectOverride.mockResolvedValue({
      success: true,
      message: "Subject list saved.",
    });

    saveAdminSyllabusOverride.mockResolvedValue({
      success: true,
      message: "Syllabus dropdown saved.",
      renamed: [
        {
          from: "Chapter 1: Percentages",
          to: "Chapter 1: Percentages and Ratios",
        },
      ],
    });
  });

  test("previews and saves an approved subject dropdown", async () => {
    render(<AdminSyllabusReviewPage user={adminUser} />);

    expect(await screen.findByText(/student dropdown preview/i)).toBeInTheDocument();

    const mathsPanel = screen
      .getByLabelText(/maths chapter preview/i)
      .closest(".admin-syllabus-preview-panel");
    const mathsControls = within(mathsPanel);

    expect(
      mathsControls.getByLabelText(/maths chapter preview/i)
    ).toHaveDisplayValue("Front Matter");

    fireEvent.click(mathsControls.getByRole("button", { name: /review \/ fix/i }));

    fireEvent.change(screen.getByDisplayValue("Chapter 1: Percentages"), {
      target: {
        value: "Chapter 1: Percentages and Ratios",
      },
    });

    fireEvent.click(
      screen.getByRole("button", {
        name: /save reviewed dropdown/i,
      })
    );

    await waitFor(() => {
      expect(saveAdminSyllabusOverride).toHaveBeenCalledWith(
        {
          grade: "Grade 8",
          mode: "CBSE",
          subject: "Maths",
          items: [
            {
              original_chapter: "Front Matter",
              chapter: "Front Matter",
            },
            {
              original_chapter: "Chapter 1: Percentages",
              chapter: "Chapter 1: Percentages and Ratios",
            },
            {
              original_chapter: "Chapter 2: Doubling a Square",
              chapter: "Chapter 2: Doubling a Square",
            },
          ],
        },
        "admin-token"
      );
    });

    expect(
      await screen.findByText(/1 RAG label\(s\) renamed/i)
    ).toBeInTheDocument();
  });

  test("shows reviewed dropdown options that no longer have RAG content", async () => {
    getAdminSyllabusReview.mockResolvedValueOnce({
      success: true,
      syllabus: {
        "Grade 8": {
          CBSE: {
            Science: [
              "Chapter 6: Pressure, Winds, Storms, and Cyclones",
              "Chapter 7: Particulate Nature of Matter",
            ],
          },
        },
      },
      content_status: [
        {
          grade: "Grade 8",
          mode: "CBSE",
          subject: "Science",
          chapter: "Chapter 6: Pressure, Winds, Storms, and Cyclones",
          document_count: 1,
          has_content: true,
        },
        {
          grade: "Grade 8",
          mode: "CBSE",
          subject: "Science",
          chapter: "Chapter 7: Particulate Nature of Matter",
          document_count: 0,
          has_content: false,
        },
      ],
      overrides: [
        {
          grade: "Grade 8",
          mode: "CBSE",
          subject: "Science",
          chapters: [
            "Chapter 6: Pressure, Winds, Storms, and Cyclones",
            "Chapter 7: Particulate Nature of Matter",
          ],
        },
      ],
      subject_overrides: [],
    });

    render(<AdminSyllabusReviewPage user={adminUser} />);

    expect(await screen.findByText("1 missing RAG")).toBeInTheDocument();

    const sciencePanel = screen
      .getByLabelText(/science chapter preview/i)
      .closest(".admin-syllabus-preview-panel");
    fireEvent.click(
      within(sciencePanel).getByRole("button", {
        name: /review \/ fix/i,
      })
    );

    expect(
      await screen.findByText("1 RAG document(s) linked")
    ).toBeInTheDocument();
    expect(
      screen.getByText("No matching RAG document right now")
    ).toBeInTheDocument();
  });

  test("lets admins hide subjects and add new visible subjects", async () => {
    render(<AdminSyllabusReviewPage user={adminUser} />);

    expect(
      await screen.findByRole("heading", { name: /visible subjects/i })
    ).toBeInTheDocument();
    expect(screen.getAllByText("Computer Science").length).toBeGreaterThan(0);

    fireEvent.click(
      screen.getByTitle("Remove Computer Science")
    );
    fireEvent.change(screen.getByPlaceholderText(/add subject/i), {
      target: {
        value: "Marathi",
      },
    });
    fireEvent.click(screen.getByRole("button", { name: /add subject/i }));

    expect(screen.getByText("Marathi")).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", {
        name: /save visible subjects/i,
      })
    );

    await waitFor(() => {
      expect(saveAdminSubjectOverride).toHaveBeenCalledWith(
        {
          grade: "Grade 8",
          mode: "CBSE",
          subjects: ["Maths", "Science", "Marathi"],
        },
        "admin-token"
      );
    });

    expect(await screen.findByText("Subject list saved.")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.queryByText("Computer Science")).not.toBeInTheDocument();
    });
  });
});
