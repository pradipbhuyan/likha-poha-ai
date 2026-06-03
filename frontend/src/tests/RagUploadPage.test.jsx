import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import RagUploadPage from "../pages/RagUploadPage";
import {
  analyzeBookSetFiles,
  uploadBookSet,
  uploadBulkBooks,
} from "../api/rag";

vi.mock("../api/syllabus", () => ({
  getSyllabus: vi.fn(async () => ({
    syllabus: {
      "Grade 1": {
        CBSE: {
          EVS: ["Uploaded Book Content"],
          Maths: ["Uploaded Book Content"],
        },
        SOF: {
          "Science Olympiad": ["Uploaded Book Content"],
        },
      },
      "Grade 5": {
        CBSE: {
          Maths: ["Uploaded Book Content"],
          Science: ["Uploaded Book Content"],
        },
        SOF: {
          "Maths Olympiad": ["Uploaded Book Content"],
        },
      },
    },
  })),
}));

vi.mock("../api/rag", () => ({
  uploadRagFilesBatch: vi.fn(),
  uploadBulkBooks: vi.fn(async () => ({
    success: true,
    message: "1 of 1 books uploaded successfully.",
    results: [
      {
        title: "Grade 5 Maths Full Book",
        subject: "Maths",
        chapter: "Uploaded Book Content",
        success: true,
        chunks_created: 2,
      },
    ],
  })),
  uploadBookSet: vi.fn(async () => ({
    success: true,
    message: "2 of 2 book files uploaded successfully.",
    results: [
      {
        title: "Grade 5 Science Textbook - Table of Contents",
        subject: "Science",
        chapter: "Table of Contents",
        success: true,
        chunks_created: 1,
      },
      {
        title: "Grade 5 Science Textbook - Chapter 1: Plants",
        subject: "Science",
        chapter: "Chapter 1: Plants",
        success: true,
        chunks_created: 2,
      },
    ],
  })),
  analyzeBookSetFiles: vi.fn(async () => ({
    success: true,
    message: "Book files analyzed. Review suggested labels before upload.",
    sections: [
      {
        filename: "toc.pdf",
        suggested_title: "Table of Contents",
        word_count: 12,
        preview: "Contents Chapter 1 Plants",
        warnings: [],
      },
      {
        filename: "chapter-1.pdf",
        suggested_title: "Chapter 1: Plants",
        word_count: 25,
        preview: "Chapter 1: Plants Roots and leaves",
        warnings: [],
      },
    ],
  })),
  getRagDocuments: vi.fn(async () => ({ documents: [] })),
  deleteRagDocument: vi.fn(),
  analyzeRagImage: vi.fn(),
  analyzeSofImages: vi.fn(),
  confirmSofUpload: vi.fn(),
  searchRag: vi.fn(),
}));

describe("RagUploadPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test("uploads a Class 1-10 bulk book with per-file metadata", async () => {
    /*
     * This validates the admin bulk-book upload path.
     *
     * Expected result:
     * - Admin can select Grade 5 and Maths for one uploaded book.
     * - The API receives the selected metadata and file together.
     */
    render(
      <RagUploadPage
        user={{
          role: "admin",
          username: "admin",
        }}
      />
    );

    expect(
      await screen.findByRole("heading", {
        name: /cbse class 1-10 bulk book upload/i,
      })
    ).toBeInTheDocument();

    const bulkBookSection = screen
      .getByRole("heading", {
        name: /cbse class 1-10 bulk book upload/i,
      })
      .closest("section");

    const bulkBookControls = within(bulkBookSection);

    const classSelect = bulkBookControls.getByLabelText("Class");
    fireEvent.change(classSelect, {
      target: {
        value: "Grade 5",
      },
    });

    const subjectSelect = bulkBookControls.getByLabelText("Subject");
    fireEvent.change(subjectSelect, {
      target: {
        value: "Maths",
      },
    });

    fireEvent.change(bulkBookControls.getByLabelText("Document Title"), {
      target: {
        value: "Grade 5 Maths Full Book",
      },
    });

    const file = new File(["fractions and decimals"], "grade-5-maths.pdf", {
      type: "application/pdf",
    });

    fireEvent.change(bulkBookControls.getByLabelText("Book File"), {
      target: {
        files: [file],
      },
    });

    fireEvent.click(
      bulkBookControls.getByRole("button", {
        name: /upload books to rag/i,
      })
    );

    await waitFor(() => {
      expect(uploadBulkBooks).toHaveBeenCalledWith({
        username: "admin",
        books: [
          {
            grade: "Grade 5",
            subject: "Maths",
            chapter: "Uploaded Book Content",
            title: "Grade 5 Maths Full Book",
            file,
          },
        ],
      });
    });
  });

  test("uploads one book split across TOC and chapter files", async () => {
    /*
     * This validates the multi-file book path.
     *
     * Expected result:
     * - Admin can choose one grade/subject/book title.
     * - TOC/chapter files and titles are submitted as a single book set.
     */
    render(
      <RagUploadPage
        user={{
          role: "admin",
          username: "admin",
        }}
      />
    );

    expect(
      await screen.findByRole("heading", {
        name: /one book, many files/i,
      })
    ).toBeInTheDocument();

    const bookSetSection = screen
      .getByRole("heading", {
        name: /one book, many files/i,
      })
      .closest("section");
    const bookSetControls = within(bookSetSection);

    fireEvent.change(bookSetControls.getByLabelText("Book Set Class"), {
      target: {
        value: "Grade 5",
      },
    });

    fireEvent.change(bookSetControls.getByLabelText("Book Set Subject"), {
      target: {
        value: "Science",
      },
    });

    fireEvent.change(bookSetControls.getByLabelText("Book Title"), {
      target: {
        value: "Grade 5 Science Textbook",
      },
    });

    const tocFile = new File(["contents"], "toc.pdf", {
      type: "application/pdf",
    });
    const chapterFile = new File(["plants"], "chapter-1.pdf", {
      type: "application/pdf",
    });

    fireEvent.change(bookSetControls.getByLabelText("Book Files"), {
      target: {
        files: [tocFile, chapterFile],
      },
    });

    fireEvent.click(
      bookSetControls.getByRole("button", {
        name: /analyze chapter labels/i,
      })
    );

    await waitFor(() => {
      expect(analyzeBookSetFiles).toHaveBeenCalledWith({
        files: [tocFile, chapterFile],
      });
    });

    expect(
      await bookSetControls.findByDisplayValue("Table of Contents")
    ).toBeInTheDocument();
    expect(
      await bookSetControls.findByDisplayValue("Chapter 1: Plants")
    ).toBeInTheDocument();

    fireEvent.click(
      bookSetControls.getByRole("button", {
        name: /upload book set to rag/i,
      })
    );

    await waitFor(() => {
      expect(uploadBookSet).toHaveBeenCalledWith({
        username: "admin",
        grade: "Grade 5",
        subject: "Science",
        bookTitle: "Grade 5 Science Textbook",
        sectionTitles: "Table of Contents\nChapter 1: Plants",
        files: [tocFile, chapterFile],
      });
    });
  });
});
