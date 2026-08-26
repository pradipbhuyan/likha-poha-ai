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
  getRagDocuments,
  previewRagDocument,
  updateRagDocumentMetadata,
  uploadBookSet,
  uploadBulkBooks,
} from "../api/rag";

vi.mock("../api/syllabus", () => ({
  getSyllabus: vi.fn(async () => ({
    syllabus: {
      "Grade 5": {
        CBSE: {
          Maths: ["Uploaded Book Content"],
          Science: ["Uploaded Book Content"],
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
  previewRagDocument: vi.fn(async () => ({
    success: true,
    preview: "Pressure, winds, storms, and cyclones content from stored chunks.",
  })),
  updateRagDocumentMetadata: vi.fn(async () => ({
    success: true,
    message: "RAG document metadata updated.",
  })),
  startFullBookAnalysisJob: vi.fn(async () => ({
    success: true,
    job_id: "analysis-job",
    job: {
      id: "analysis-job",
      status: "completed",
      percent: 100,
      result: {
        success: true,
        chapters: [],
      },
    },
  })),
  startFullBookUploadJob: vi.fn(async () => ({
    success: true,
    job_id: "upload-job",
    job: {
      id: "upload-job",
      status: "completed",
      percent: 100,
      result: {
        success: true,
        results: [],
      },
    },
  })),
  getRagUploadJob: vi.fn(async () => ({
    success: true,
    job: {
      id: "upload-job",
      status: "completed",
      percent: 100,
      result: {
        success: true,
        chapters: [],
        results: [],
      },
    },
  })),
  getRagUploadJobs: vi.fn(async () => ({
    success: true,
    jobs: [],
  })),
  deleteRagDocument: vi.fn(),
  analyzeRagImage: vi.fn(),
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
        name: /school-board bulk book upload/i,
      })
    ).toBeInTheDocument();

    const bulkBookSection = screen
      .getByRole("heading", {
        name: /school-board bulk book upload/i,
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
            board: "CBSE",
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

    await waitFor(() => {
      expect(
        bookSetControls.getAllByDisplayValue("Table of Contents").length
      ).toBeGreaterThan(0);
    });
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
        board: "CBSE",
        grade: "Grade 5",
        subject: "Science",
        bookTitle: "Grade 5 Science Textbook",
        sectionTitles: "Table of Contents\nChapter 1: Plants",
        files: [tocFile, chapterFile],
      });
    });
  });

  test("uses analyzed and file-name fallback labels when section titles are incomplete", async () => {
    /*
     * This protects mobile/book-set uploads from failing with a brittle
     * "section title count" error when one label is blank or missing.
     */
    analyzeBookSetFiles.mockResolvedValueOnce({
      success: true,
      message: "Book files analyzed. Review suggested labels before upload.",
      sections: [
        {
          filename: "toc.pdf",
          suggested_title: "Table of Contents",
          word_count: 12,
          preview: "Contents",
          warnings: [],
        },
        {
          filename: "chapter-1.pdf",
          suggested_title: "",
          word_count: 25,
          preview: "Chapter text",
          warnings: [],
        },
      ],
    });

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

    fireEvent.change(bookSetControls.getByLabelText("TOC / Chapter Titles"), {
      target: {
        value: "Only One Manual Title",
      },
    });

    fireEvent.click(
      bookSetControls.getByRole("button", {
        name: /analyze chapter labels/i,
      })
    );

    await waitFor(() => {
      expect(
        bookSetControls.getAllByDisplayValue("Table of Contents").length
      ).toBeGreaterThan(0);
    });

    fireEvent.click(
      bookSetControls.getByRole("button", {
        name: /upload book set to rag/i,
      })
    );

    await waitFor(() => {
      expect(uploadBookSet).toHaveBeenCalledWith({
        username: "admin",
        board: "CBSE",
        grade: "Grade 5",
        subject: "Science",
        bookTitle: "Grade 5 Science Textbook",
        sectionTitles: "Table of Contents\nchapter 1",
        files: [tocFile, chapterFile],
      });
    });

    expect(
      screen.queryByText(/section title count must match selected file count/i)
    ).not.toBeInTheDocument();
  });

  test("keeps commas inside book-set chapter titles during upload", async () => {
    /*
     * Chapter labels are one per line. Commas are part of many real titles and
     * must not split one chapter into multiple RAG documents.
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
        value: "Science Text Book",
      },
    });

    const chapterSixFile = new File(["pressure"], "hecu106.pdf", {
      type: "application/pdf",
    });
    const chapterSevenFile = new File(["matter"], "hecu107.pdf", {
      type: "application/pdf",
    });

    fireEvent.change(bookSetControls.getByLabelText("Book Files"), {
      target: {
        files: [chapterSixFile, chapterSevenFile],
      },
    });
    fireEvent.change(bookSetControls.getByLabelText("TOC / Chapter Titles"), {
      target: {
        value:
          "Chapter 6: Pressure, Winds, Storms, and Cyclones\nChapter 7: Particulate Nature of Matter",
      },
    });

    fireEvent.click(
      bookSetControls.getByRole("button", {
        name: /upload book set to rag/i,
      })
    );

    await waitFor(() => {
      expect(uploadBookSet).toHaveBeenCalledWith({
        username: "admin",
        board: "CBSE",
        grade: "Grade 5",
        subject: "Science",
        bookTitle: "Science Text Book",
        sectionTitles:
          "Chapter 6: Pressure, Winds, Storms, and Cyclones\nChapter 7: Particulate Nature of Matter",
        files: [chapterSixFile, chapterSevenFile],
      });
    });
  });

  test("previews stored RAG content and edits document metadata", async () => {
    /*
     * This validates the metadata repair loop for mismatched RAG labels.
     *
     * Expected result:
     * - Admin can preview the stored chunks behind a document.
     * - Admin can fix both the visible document title and retrieval chapter.
     */
    getRagDocuments.mockResolvedValueOnce({
      documents: [
        {
          id: "doc-1",
          title: "Science Text Book - and Cyclones",
          grade: "Grade 8",
          subject: "Science",
          chapter: "Chapter 9: The Amazing World of Solutes, Solvents, and Solutions",
          uploaded_by: "Pradip Admin",
        },
      ],
    });

    render(
      <RagUploadPage
        user={{
          role: "admin",
          username: "admin",
          accessToken: "admin-token",
        }}
      />
    );

    fireEvent.click(
      await screen.findByRole("button", {
        name: /library \/ test/i,
      })
    );

    expect(
      await screen.findByText("Science Text Book - and Cyclones")
    ).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", {
        name: /preview content/i,
      })
    );

    expect(
      await screen.findByText(/pressure, winds, storms, and cyclones content/i)
    ).toBeInTheDocument();
    expect(previewRagDocument).toHaveBeenCalledWith("doc-1", "admin-token");

    fireEvent.click(
      screen.getByRole("button", {
        name: /edit metadata/i,
      })
    );

    fireEvent.change(
      screen.getByDisplayValue("Science Text Book - and Cyclones"),
      {
        target: {
          value:
            "Science Text Book - Chapter 6: Pressure, Winds, Storms, and Cyclones",
        },
      }
    );
    fireEvent.change(screen.getByDisplayValue(/Chapter 9:/), {
      target: {
        value: "Chapter 6: Pressure, Winds, Storms, and Cyclones",
      },
    });

    fireEvent.click(
      screen.getByRole("button", {
        name: /save metadata/i,
      })
    );

    await waitFor(() => {
      expect(updateRagDocumentMetadata).toHaveBeenCalledWith(
        "doc-1",
        {
          title:
            "Science Text Book - Chapter 6: Pressure, Winds, Storms, and Cyclones",
          chapter: "Chapter 6: Pressure, Winds, Storms, and Cyclones",
        },
        "admin-token"
      );
    });
  });
});
