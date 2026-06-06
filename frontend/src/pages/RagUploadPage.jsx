import { useEffect, useState } from "react";

import { getSyllabus } from "../api/syllabus";

import {
  uploadRagFilesBatch,
  uploadBulkBooks,
  uploadBookSet,
  analyzeBookSetFiles,
  startFullBookAnalysisJob,
  startFullBookUploadJob,
  getRagUploadJob,
  getRagUploadJobs,
  getRagDocuments,
  deleteRagDocument,
  previewRagDocument,
  updateRagDocumentMetadata,
  analyzeRagImage,
  analyzeSofImages,
  confirmSofUpload,
  searchRag,
} from "../api/rag";
import { getDefaultSelection } from "../utils/syllabusDefaults";

const BOOK_CHAPTER_LABEL = "Uploaded Book Content";
const BULK_BOOK_FILE_ACCEPT = ".txt,.jpg,.jpeg,.png,.webp,.pdf,.docx,.pptx";
const SCHOOL_BOARD_OPTIONS = ["CBSE", "ICSE", "State Board"];
const RAG_JOB_RUNNING_STATUSES = new Set(["queued", "running"]);
const RAG_WORKSPACE_TABS = [
  {
    id: "bookUploads",
    label: "Book Uploads",
    description: "Full books, chapter PDFs, and class books",
  },
  {
    id: "sof",
    label: "SOF Upload",
    description: "Olympiad worksheets and prep books",
  },
  {
    id: "manual",
    label: "Manual / Scan",
    description: "Quick uploads, photos, and single-page OCR",
  },
  {
    id: "library",
    label: "Library / Test",
    description: "Search, preview, repair, and delete RAG content",
  },
];

function sleep(ms) {
  /** Wait between background job polling attempts. */
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function isRagJobRunning(job) {
  /** Detect whether a background RAG job still needs polling. */
  return job && RAG_JOB_RUNNING_STATUSES.has(job.status);
}

function RagJobProgress({ job, title }) {
  /** Show live RAG analysis/upload progress with page, chapter, and chunk counters. */
  if (!job) {
    return null;
  }

  const percent = Math.max(0, Math.min(100, Number(job.percent || 0)));

  return (
    <div className={`premium-rag-job-progress ${job.status || ""}`}>
      <div className="premium-rag-job-progress-header">
        <div>
          <strong>{title}</strong>
          <p>{job.message || job.phase || "Working..."}</p>
        </div>
        <span>{percent}%</span>
      </div>

      <div className="premium-rag-job-progress-bar">
        <div style={{ width: `${percent}%` }} />
      </div>

      <div className="premium-rag-job-progress-meta">
        <span>
          Pages {job.processed_pages || 0}/{job.page_count || 0}
        </span>
        <span>
          Chapters {job.processed_chapters || 0}/{job.total_chapters || 0}
        </span>
        <span>
          Chunks {job.processed_chunks || 0}/{job.total_chunks || 0}
        </span>
        <span>{job.status || "queued"}</span>
      </div>

      {job.error_message && (
        <p className="premium-rag-job-progress-error">{job.error_message}</p>
      )}
    </div>
  );
}

function createBulkBookRow(index = 0) {
  /** Create one editable row for a Class 1-10 full-book RAG upload. */
  return {
    id: `${Date.now()}-${index}`,
    board: "CBSE",
    grade: "Grade 1",
    subject: "",
    title: "",
    file: null,
  };
}

function getReadableSectionTitleFromFile(file, index) {
  /** Build a readable fallback chapter label when admin labels are incomplete. */
  const fallbackName = file?.name || `Section ${index + 1}`;
  const nameWithoutExtension = fallbackName.replace(/\.[^/.]+$/, "");

  return (
    nameWithoutExtension
      .replace(/[_-]+/g, " ")
      .replace(/\s+/g, " ")
      .trim() || `Section ${index + 1}`
  );
}

function RagUploadPage({ user }) {
  /** Admin-only workspace for uploading, analyzing, searching, and deleting RAG documents. */
  const [loading, setLoading] = useState(true);
  const [activeRagWorkspace, setActiveRagWorkspace] = useState("bookUploads");
  const [syllabusData, setSyllabusData] = useState(null);

  const [grade, setGrade] = useState("Grade 9");
  const [mode, setMode] = useState("CBSE");
  const [subject, setSubject] = useState("");
  const [chapter, setChapter] = useState("");

  const [title, setTitle] = useState("");

  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const [files, setFiles] = useState([]);
  const [batchResults, setBatchResults] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [bulkBookRows, setBulkBookRows] = useState([createBulkBookRow()]);
  const [bulkUploading, setBulkUploading] = useState(false);
  const [bookSetGrade, setBookSetGrade] = useState("Grade 1");
  const [bookSetBoard, setBookSetBoard] = useState("CBSE");
  const [bookSetSubject, setBookSetSubject] = useState("");
  const [bookSetTitle, setBookSetTitle] = useState("");
  const [bookSetSectionTitles, setBookSetSectionTitles] = useState("");
  const [bookSetFiles, setBookSetFiles] = useState([]);
  const [bookSetAnalysis, setBookSetAnalysis] = useState([]);
  const [bookSetAnalyzing, setBookSetAnalyzing] = useState(false);
  const [bookSetUploading, setBookSetUploading] = useState(false);
  const [fullBookGrade, setFullBookGrade] = useState("Grade 1");
  const [fullBookBoard, setFullBookBoard] = useState("State Board");
  const [fullBookSubject, setFullBookSubject] = useState("");
  const [fullBookTitle, setFullBookTitle] = useState("");
  const [fullBookFile, setFullBookFile] = useState(null);
  const [fullBookOcrScanned, setFullBookOcrScanned] = useState(false);
  const [fullBookAnalysis, setFullBookAnalysis] = useState(null);
  const [fullBookAnalyzing, setFullBookAnalyzing] = useState(false);
  const [fullBookUploading, setFullBookUploading] = useState(false);
  const [fullBookAnalysisJob, setFullBookAnalysisJob] = useState(null);
  const [fullBookUploadJob, setFullBookUploadJob] = useState(null);
  const [recentRagJobs, setRecentRagJobs] = useState([]);

  const [analysisImage, setAnalysisImage] = useState(null);
  const [analyzingImage, setAnalyzingImage] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);

  const [sofFiles, setSofFiles] = useState([]);
  const [sofAnalyzing, setSofAnalyzing] = useState(false);
  const [sofUploading, setSofUploading] = useState(false);
  const [sofPages, setSofPages] = useState([]);
  const [sofGroups, setSofGroups] = useState([]);
  const [sofRawResponse, setSofRawResponse] = useState("");
  const [ragQuery, setRagQuery] = useState("");
  const [ragResults, setRagResults] = useState([]);
  const [searchingRag, setSearchingRag] = useState(false);
  const [activeMetadataDocId, setActiveMetadataDocId] = useState("");
  const [metadataDraft, setMetadataDraft] = useState({
    title: "",
    chapter: "",
  });
  const [previewByDocument, setPreviewByDocument] = useState({});
  const [previewLoadingId, setPreviewLoadingId] = useState("");
  const [savingMetadataId, setSavingMetadataId] = useState("");

  const [searchGrade, setSearchGrade] = useState("Grade 9");
  const [searchMode, setSearchMode] = useState("SOF");
  const [searchSubject, setSearchSubject] = useState("English Olympiad");
  const [searchChapter, setSearchChapter] = useState("Nouns");

  useEffect(() => {
    async function loadSyllabus() {
      /** Load syllabus metadata so uploads can be tagged with grade, subject, and chapter. */
      try {
        const data = await getSyllabus();
        setSyllabusData(data.syllabus);

        const {
          grade: defaultGrade,
          mode: defaultMode,
          subject: defaultSubject,
          chapter: defaultChapter,
        } = getDefaultSelection(data.syllabus);

        setGrade(defaultGrade);
        setMode(defaultMode);
        setSubject(defaultSubject);
        setChapter(defaultChapter);
        setSearchGrade(defaultGrade);
        setSearchMode(defaultMode);
        setSearchSubject(defaultSubject);
        setSearchChapter(defaultChapter);
        setBulkBookRows([createBulkBookRow()]);
        setBookSetGrade(defaultGrade);
        setBookSetSubject(
          Object.keys(data.syllabus?.[defaultGrade]?.CBSE || {})[0] ||
            defaultSubject
        );
        setFullBookGrade(defaultGrade);
        setFullBookSubject(
          Object.keys(data.syllabus?.[defaultGrade]?.["State Board"] || {})[0] ||
            Object.keys(data.syllabus?.[defaultGrade]?.CBSE || {})[0] ||
            defaultSubject
        );
      } finally {
        setLoading(false);
      }
    }

    loadSyllabus();
    loadDocuments();
    loadRagJobs();
  }, []);

  async function loadDocuments() {
    /** Refresh the list of documents already indexed in the RAG database. */
    try {
      const result = await getRagDocuments();
      setDocuments(result.documents || []);
    } catch (err) {
      console.error(err);
    }
  }

  async function loadRagJobs() {
    /** Refresh recent background RAG jobs for parallel batch monitoring. */
    if (!user?.accessToken) {
      return;
    }

    try {
      const result = await getRagUploadJobs(user.accessToken);
      setRecentRagJobs(result.jobs || []);
    } catch (err) {
      console.error(err);
    }
  }

  async function pollRagJob(jobId, onUpdate) {
    /** Poll one background job until it reaches a terminal state. */
    let latestJob = null;

    for (let attempt = 0; attempt < 720; attempt += 1) {
      const result = await getRagUploadJob(jobId, user.accessToken);
      latestJob = result.job;
      onUpdate(latestJob);
      await loadRagJobs();

      if (!isRagJobRunning(latestJob)) {
        return latestJob;
      }

      await sleep(1500);
    }

    throw new Error("RAG job is still running after the polling window.");
  }

  function appendFiles(currentFiles, selectedFiles, maxFiles = 20) {
    /** Add selected files while enforcing the 20-file upload limit. */
    return [...currentFiles, ...selectedFiles].slice(0, maxFiles);
  }

  function getSubjectsForGradeAndBoard(rowGrade, rowBoard = "CBSE") {
    /** Return subject options available for one grade/board combination. */
    return Object.keys(syllabusData?.[rowGrade]?.[rowBoard] || {});
  }

  function resolveBulkBookRow(row) {
    /** Fill safe defaults for one bulk book row before validation/upload. */
    const subjectsForGrade = getSubjectsForGradeAndBoard(row.grade, row.board);
    const resolvedSubject = row.subject || subjectsForGrade[0] || "";

    return {
      ...row,
      subject: resolvedSubject,
      title:
        row.title.trim() ||
        `${row.grade} ${row.board || "CBSE"} ${resolvedSubject || "Book"} Full Book`,
    };
  }

  function updateBulkBookRow(rowId, updates) {
    /** Update one editable bulk book row, resetting subject if grade changes. */
    setBulkBookRows((currentRows) =>
      currentRows.map((row) => {
        if (row.id !== rowId) {
          return row;
        }

        const nextRow = {
          ...row,
          ...updates,
        };

        if (updates.grade || updates.board) {
          nextRow.subject =
            getSubjectsForGradeAndBoard(nextRow.grade, nextRow.board)[0] ||
            nextRow.subject ||
            "";
        }

        return nextRow;
      })
    );
  }

  function addBulkBookRow() {
    /** Add another Class 1-10 book row while keeping the backend 20-file limit. */
    if (bulkBookRows.length >= 20) {
      setError("You can upload a maximum of 20 books at once.");
      return;
    }

    const nextRow = createBulkBookRow(bulkBookRows.length);
    nextRow.subject =
      getSubjectsForGradeAndBoard(nextRow.grade, nextRow.board)[0] || "";
    setBulkBookRows((currentRows) => [...currentRows, nextRow]);
  }

  function removeBulkBookRow(rowId) {
    /** Remove one bulk book row, keeping at least one editable row on screen. */
    setBulkBookRows((currentRows) => {
      const nextRows = currentRows.filter((row) => row.id !== rowId);

      return nextRows.length > 0 ? nextRows : [createBulkBookRow()];
    });
  }

  function handleBookSetGradeChange(value) {
    /** Keep the book-set subject valid when the selected grade changes. */
    setBookSetGrade(value);
    setBookSetSubject(getSubjectsForGradeAndBoard(value, bookSetBoard)[0] || bookSetSubject);
  }

  function handleBookSetBoardChange(value) {
    /** Keep the book-set subject valid when the selected board changes. */
    setBookSetBoard(value);
    setBookSetSubject(getSubjectsForGradeAndBoard(bookSetGrade, value)[0] || bookSetSubject);
  }

  function handleFullBookGradeChange(value) {
    /** Keep the full-book splitter subject valid when class changes. */
    setFullBookGrade(value);
    setFullBookSubject(
      getSubjectsForGradeAndBoard(value, fullBookBoard)[0] || fullBookSubject
    );
  }

  function handleFullBookBoardChange(value) {
    /** Keep the full-book splitter subject valid when board changes. */
    setFullBookBoard(value);
    setFullBookSubject(
      getSubjectsForGradeAndBoard(fullBookGrade, value)[0] || fullBookSubject
    );
  }

  function updateSofGroup(index, updates) {
    /** Let admins correct SOF metadata and OCR context before RAG upload. */
    setSofGroups((currentGroups) =>
      currentGroups.map((group, groupIndex) =>
        groupIndex === index
          ? {
              ...group,
              ...updates,
            }
          : group
      )
    );
  }

  async function handleAnalyzeImage() {
    /** Run single-image OCR/analysis as a quick quality check before upload. */
    if (!analysisImage) {
      alert("Please select an image.");
      return;
    }

    setAnalyzingImage(true);
    setAnalysisResult(null);

    try {
      const result = await analyzeRagImage(analysisImage);
      setAnalysisResult(result);
    } catch (err) {
      console.error(err);
      alert("Image analysis failed.");
    } finally {
      setAnalyzingImage(false);
    }
  }

  async function handleAnalyzeSofImages() {
    /** Analyze up to 20 SOF PDFs/photos and group pages by subject/chapter before indexing. */
    setMessage("");
    setError("");
    setSofPages([]);
    setSofGroups([]);
    setSofRawResponse("");

    if (sofFiles.length === 0) {
      setError("Please select SOF PDFs or page photos.");
      return;
    }

    if (sofFiles.length > 20) {
      setError("You can analyze a maximum of 20 SOF files.");
      return;
    }

    setSofAnalyzing(true);

    try {
      const result = await analyzeSofImages({
        grade,
        files: sofFiles,
      });

      if (!result.success) {
        setSofPages(result.pages || []);
        setSofGroups(result.groups || []);
        setSofRawResponse(
          result.raw_ai_response ||
            (result.file_warnings || [])
              .map((warning) => `${warning.filename}: ${warning.message}`)
              .join("\n")
        );
        setError(result.message || "SOF image analysis failed.");
        return;
      }

      setSofPages(result.pages || []);
      setSofGroups(result.groups || []);
      setSofRawResponse(result.raw_ai_response || "");
      setMessage(result.message || "SOF files analyzed. Review extracted pages and groups before uploading.");
    } catch (err) {
      console.error(err);
      setError(err.message || "SOF image analysis failed. Check backend.");
    } finally {
      setSofAnalyzing(false);
    }
  }

  async function handleConfirmSofUpload() {
    /** Persist reviewed SOF page groups into the RAG database. */
    setMessage("");
    setError("");

    if (sofGroups.length === 0) {
      setError("No SOF groups found to upload.");
      return;
    }

    setSofUploading(true);

    try {
      const result = await confirmSofUpload({
        username: "admin",
        groups: sofGroups,
      });

      console.log("SOF upload result:", result);

      if (!result.success) {
        setError(result.message || "SOF upload failed.");
        setBatchResults(result.results || []);
        return;
      }

      setMessage(result.message || "SOF upload completed.");
      setBatchResults(result.results || []);

      setSofFiles([]);
      setSofPages([]);
      setSofGroups([]);
      setSofRawResponse("");

      await loadDocuments();
    } catch (err) {
      console.error("SOF upload failed:", err);
      setError(err.message || "SOF upload failed. Check backend.");
    } finally {
      setSofUploading(false);
    }
  }

  async function handleBulkBookUpload() {
    /** Upload full subject books for Class 1-10 with explicit metadata per file. */
    setMessage("");
    setError("");
    setBatchResults([]);

    const rowsToUpload = bulkBookRows
      .map(resolveBulkBookRow)
      .filter((row) => row.file);

    if (rowsToUpload.length === 0) {
      setError("Please select at least one book file.");
      return;
    }

    if (rowsToUpload.length > 20) {
      setError("You can upload a maximum of 20 books at once.");
      return;
    }

    const missingMetadataRow = rowsToUpload.find(
      (row) => !row.grade || !row.subject || !row.title.trim()
    );

    if (missingMetadataRow) {
      setError("Every selected book needs a grade, subject, and title.");
      return;
    }

    setBulkUploading(true);

    try {
      const result = await uploadBulkBooks({
        username: user.username,
        books: rowsToUpload.map((row) => ({
          grade: row.grade,
          board: row.board || "CBSE",
          subject: row.subject,
          chapter: BOOK_CHAPTER_LABEL,
          title: row.title.trim(),
          file: row.file,
        })),
      });

      if (!result.success) {
        setError(result.message || "Bulk book upload failed.");
        setBatchResults(result.results || []);
        return;
      }

      setMessage(result.message || "Bulk books uploaded successfully.");
      setBatchResults(result.results || []);
      setBulkBookRows([createBulkBookRow()]);

      await loadDocuments();
    } catch (err) {
      console.error(err);
      setError("Bulk book upload failed. Check backend.");
    } finally {
      setBulkUploading(false);
    }
  }

  async function handleBookSetUpload() {
    /** Upload one book that is represented by multiple TOC/chapter files. */
    setMessage("");
    setError("");
    setBatchResults([]);

    if (!bookSetTitle.trim()) {
      setError("Please enter a book title.");
      return;
    }

    if (bookSetFiles.length === 0) {
      setError("Please select TOC/chapter files for the book.");
      return;
    }

    if (bookSetFiles.length > 20) {
      setError("You can upload a maximum of 20 book files at once.");
      return;
    }

    const manualSectionTitles = bookSetSectionTitles
      .split("\n")
      .map((item) => item.trim())
      .filter(Boolean);

    const resolvedSectionTitles = bookSetFiles.map((file, index) => {
      const analyzedTitle = bookSetAnalysis[index]?.suggested_title?.trim();
      const manualTitle = manualSectionTitles[index];

      return (
        analyzedTitle ||
        manualTitle ||
        getReadableSectionTitleFromFile(file, index)
      );
    });

    setBookSetUploading(true);

    try {
      const result = await uploadBookSet({
        username: user.username,
        grade: bookSetGrade,
        board: bookSetBoard,
        subject: bookSetSubject,
        bookTitle: bookSetTitle.trim(),
        sectionTitles: resolvedSectionTitles.join("\n"),
        files: bookSetFiles,
      });

      if (!result.success) {
        setError(result.message || "Book set upload failed.");
        setBatchResults(result.results || []);
        return;
      }

      setMessage(result.message || "Book files uploaded successfully.");
      setBatchResults(result.results || []);
      setBookSetTitle("");
      setBookSetSectionTitles("");
      setBookSetFiles([]);
      setBookSetAnalysis([]);

      await loadDocuments();
    } catch (err) {
      console.error(err);
      setError("Book set upload failed. Check backend.");
    } finally {
      setBookSetUploading(false);
    }
  }

  async function handleAnalyzeFullBook() {
    /** Analyze one full textbook PDF and suggest chapter page ranges. */
    setMessage("");
    setError("");
    setBatchResults([]);
    setFullBookAnalysis(null);
    setFullBookAnalysisJob(null);

    if (!fullBookFile) {
      setError("Please select one full textbook PDF.");
      return;
    }

    if (!fullBookFile.name.toLowerCase().endsWith(".pdf")) {
      setError("Full book splitter currently supports PDF files only.");
      return;
    }

    setFullBookAnalyzing(true);

    try {
      const started = await startFullBookAnalysisJob({
        file: fullBookFile,
        ocrScanned: fullBookOcrScanned,
        accessToken: user.accessToken,
      });
      setFullBookAnalysisJob(started.job || null);
      setMessage(started.message || "Full-book analysis started.");

      const completedJob = await pollRagJob(started.job_id, setFullBookAnalysisJob);
      const result = completedJob.result || {};

      if (completedJob.status === "failed" || !result.success) {
        setError(
          completedJob.error_message ||
            result.message ||
            "Full book analysis failed."
        );
        setFullBookAnalysis(result);
        return;
      }

      setFullBookAnalysis(result);
      setMessage(result.message || "Full book analyzed. Review chapters before upload.");
    } catch (err) {
      console.error(err);
      setError("Full book analysis failed. Check backend.");
    } finally {
      setFullBookAnalyzing(false);
    }
  }

  function updateFullBookChapter(index, updates) {
    /** Let admins correct detected chapter ranges before upload. */
    setFullBookAnalysis((currentAnalysis) => {
      if (!currentAnalysis) {
        return currentAnalysis;
      }

      return {
        ...currentAnalysis,
        chapters: (currentAnalysis.chapters || []).map((chapter, chapterIndex) =>
          chapterIndex === index
            ? {
                ...chapter,
                ...updates,
              }
            : chapter
        ),
      };
    });
  }

  async function handleUploadFullBookSections() {
    /** Upload reviewed full-book page ranges as separate RAG chapter documents. */
    setMessage("");
    setError("");
    setBatchResults([]);
    setFullBookUploadJob(null);

    if (!fullBookFile) {
      setError("Please select one full textbook PDF.");
      return;
    }

    if (!fullBookTitle.trim()) {
      setError("Please enter a book title.");
      return;
    }

    const chapters = fullBookAnalysis?.chapters || [];
    const selectedChapters = chapters.filter((chapter) => chapter.include !== false);

    if (selectedChapters.length === 0) {
      setError("Select at least one chapter to upload.");
      return;
    }

    setFullBookUploading(true);

    try {
      const started = await startFullBookUploadJob({
        username: user.username,
        grade: fullBookGrade,
        board: fullBookBoard,
        subject: fullBookSubject,
        bookTitle: fullBookTitle.trim(),
        chapters,
        ocrScanned: fullBookOcrScanned,
        file: fullBookFile,
        accessToken: user.accessToken,
      });
      setFullBookUploadJob(started.job || null);
      setMessage(started.message || "Full-book RAG upload started.");

      const completedJob = await pollRagJob(started.job_id, setFullBookUploadJob);
      const result = completedJob.result || {};

      if (completedJob.status === "failed" || !result.success) {
        setError(
          completedJob.error_message ||
            result.message ||
            "Full book chapter upload failed."
        );
        setBatchResults(result.results || []);
        return;
      }

      setMessage(result.message || "Full book chapters uploaded successfully.");
      setBatchResults(result.results || []);
      setFullBookFile(null);
      setFullBookAnalysis(null);

      await loadDocuments();
    } catch (err) {
      console.error(err);
      setError("Full book chapter upload failed. Check backend.");
    } finally {
      setFullBookUploading(false);
    }
  }

  async function handleAnalyzeBookSet() {
    /** Suggest editable labels for each TOC/chapter file before uploading. */
    setMessage("");
    setError("");
    setBookSetAnalysis([]);

    if (bookSetFiles.length === 0) {
      setError("Please select TOC/chapter files to analyze.");
      return;
    }

    if (bookSetFiles.length > 20) {
      setError("You can analyze a maximum of 20 book files at once.");
      return;
    }

    setBookSetAnalyzing(true);

    try {
      const result = await analyzeBookSetFiles({
        files: bookSetFiles,
      });

      if (!result.success) {
        setError(result.message || "Book set analysis failed.");
        return;
      }

      const sections = result.sections || [];
      setBookSetAnalysis(sections);
      setBookSetSectionTitles(
        sections.map((section) => section.suggested_title || "").join("\n")
      );
      setMessage(result.message || "Book labels suggested. Review before upload.");
    } catch (err) {
      console.error(err);
      setError("Book set analysis failed. Check backend.");
    } finally {
      setBookSetAnalyzing(false);
    }
  }

  function updateBookSetAnalysisTitle(index, value) {
    /** Keep editable section cards and the upload title textarea in sync. */
    setBookSetAnalysis((currentSections) => {
      const nextSections = currentSections.map((section, sectionIndex) =>
        sectionIndex === index
          ? {
              ...section,
              suggested_title: value,
            }
          : section
      );

      setBookSetSectionTitles(
        nextSections.map((section) => section.suggested_title || "").join("\n")
      );

      return nextSections;
    });
  }

  async function handleBatchUpload() {
    /** Upload one or more regular RAG documents with the selected syllabus metadata. */
    setMessage("");
    setError("");
    setBatchResults([]);

    if (!title.trim()) {
      setError("Please enter comma-separated document titles.");
      return;
    }

    if (files.length === 0) {
      setError("Please select files.");
      return;
    }

    if (files.length > 20) {
      setError("You can upload a maximum of 20 files.");
      return;
    }

    setUploading(true);

    try {
      const result = await uploadRagFilesBatch({
        username: user.username,
        grade,
        board: mode === "SOF" ? "CBSE" : mode,
        subject,
        chapter,
        titles: title,
        files,
      });

      if (!result.success) {
        setError(result.message || "Batch upload failed.");
        return;
      }

      setMessage(result.message);
      setBatchResults(result.results || []);

      await loadDocuments();

      setTitle("");
      setFiles([]);
    } catch {
      setError("Batch upload failed. Check backend.");
    } finally {
      setUploading(false);
    }
  }

  async function handleSearchRag() {
    /** Query the RAG index to verify that uploaded content is retrievable. */
    if (!ragQuery.trim()) {
      alert("Please enter a search query.");
      return;
    }

    setSearchingRag(true);

    try {
      const result = await searchRag({
        grade: searchGrade,
        board: searchMode === "SOF" ? "CBSE" : searchMode,
        subject: searchSubject,
        chapter: searchChapter,
        query: ragQuery,
        matchCount: 5,
      });

      setRagResults(result.results || []);
    } catch (err) {
      console.error(err);
      alert("RAG search failed.");
    } finally {
      setSearchingRag(false);
    }
  }

  async function handleDeleteDocument(documentId) {
    /** Delete an indexed RAG document after admin confirmation. */
    if (!window.confirm("Delete this document?")) {
      return;
    }

    try {
      await deleteRagDocument(documentId);
      await loadDocuments();
    } catch (err) {
      alert("Unable to delete document.");
    }
  }

  function startEditRagDocument(doc) {
    /** Open metadata editing for one uploaded RAG document. */
    setActiveMetadataDocId(doc.id);
    setMetadataDraft({
      title: doc.title || "",
      chapter: doc.chapter || "",
    });
    setMessage("");
    setError("");
  }

  async function handleSaveRagMetadata(doc) {
    /** Save corrected document title/chapter metadata without changing chunks. */
    setSavingMetadataId(doc.id);
    setMessage("");
    setError("");

    try {
      await updateRagDocumentMetadata(
        doc.id,
        {
          title: metadataDraft.title,
          chapter: metadataDraft.chapter,
        },
        user.accessToken
      );

      setMessage(
        "RAG metadata updated. Content chunks are unchanged; retrieval now uses the corrected chapter label."
      );
      setActiveMetadataDocId("");
      await loadDocuments();
    } catch (err) {
      console.error(err);
      setError(err.message || "Unable to update RAG metadata.");
    } finally {
      setSavingMetadataId("");
    }
  }

  async function handlePreviewRagDocument(doc) {
    /** Load stored chunks so admin can compare content against the chapter label. */
    setPreviewLoadingId(doc.id);
    setError("");

    try {
      const result = await previewRagDocument(doc.id, user.accessToken);

      setPreviewByDocument((currentPreviews) => ({
        ...currentPreviews,
        [doc.id]: result.preview || "No chunk text found for this document.",
      }));
    } catch (err) {
      console.error(err);
      setError(err.message || "Unable to preview RAG document.");
    } finally {
      setPreviewLoadingId("");
    }
  }

  if (user.role !== "admin") {
    return (
      <div className="premium-page">
        <section className="premium-section premium-rag-locked">
          <div className="premium-header">
            <p className="eyebrow">Restricted Access</p>
            <h2>🔒 RAG Upload</h2>
            <p>Only administrators can upload textbook content.</p>
          </div>
        </section>
      </div>
    );
  }

  if (loading) {
    return <p>Loading RAG upload page...</p>;
  }

  const grades = Object.keys(syllabusData);
  const modes = Object.keys(syllabusData[grade]);
  const subjects = Object.keys(syllabusData[grade][mode]);
  const chapters = syllabusData[grade][mode][subject] || [];
  const bookSetSubjects = getSubjectsForGradeAndBoard(bookSetGrade, bookSetBoard);
  const fullBookSubjects = getSubjectsForGradeAndBoard(fullBookGrade, fullBookBoard);

  function handleGradeChange(value) {
    /** Reset upload selectors to valid mode, subject, and chapter defaults for the grade. */
    const newMode = Object.keys(syllabusData[value])[0];
    const newSubject = Object.keys(syllabusData[value][newMode])[0];
    const newChapter = syllabusData[value][newMode][newSubject][0];

    setGrade(value);
    setMode(newMode);
    setSubject(newSubject);
    setChapter(newChapter);
  }

  function handleModeChange(value) {
    /** Reset subject and chapter when the upload mode changes. */
    const newSubject = Object.keys(syllabusData[grade][value])[0];
    const newChapter = syllabusData[grade][value][newSubject][0];

    setMode(value);
    setSubject(newSubject);
    setChapter(newChapter);
  }

  function handleSubjectChange(value) {
    /** Reset chapter to the first available option for the selected upload subject. */
    const newChapter = syllabusData[grade][mode][value][0];

    setSubject(value);
    setChapter(newChapter);
  }

  return (
    <div className="rag-upload-page premium-page premium-rag-page">
      <section className="premium-section premium-rag-hero">
        <div className="premium-header">
          <p className="eyebrow">Admin Knowledge Base</p>
          <h2>📤 RAG Upload</h2>
          <p>
            Upload textbook chapters, notes, worksheets, PDFs, DOCX, PPTX, and
            image-based content into the AI tutor knowledge base.
          </p>
        </div>

        <div className="premium-rag-info-card">
          <span>📚</span>
          <div>
            <strong>SOF Bulk Upload Ready</strong>
            <p>
              Upload up to 20 SOF book photos. AI will organize them by Olympiad
              subject and chapter before RAG upload.
            </p>
          </div>
        </div>
      </section>

      <section className="premium-rag-workspace-tabs" aria-label="RAG workspace sections">
        {RAG_WORKSPACE_TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            className={
              activeRagWorkspace === tab.id
                ? "premium-rag-workspace-tab active"
                : "premium-rag-workspace-tab"
            }
            aria-pressed={activeRagWorkspace === tab.id}
            onClick={() => setActiveRagWorkspace(tab.id)}
          >
            <strong>{tab.label}</strong>
            <span>{tab.description}</span>
          </button>
        ))}
      </section>

      {activeRagWorkspace === "library" && (
      <section className="premium-section">
        <div className="premium-header">
          <h3>🧪 RAG Search Test Console</h3>

          <p>
            Test whether uploaded RAG content can be found correctly before
            using it in lessons, doubts, or mock tests.
          </p>
        </div>

        <div className="form-grid premium-rag-form-grid">
          <label>
            Search Grade
            <select
              value={searchGrade}
              onChange={(e) => {
                const newGrade = e.target.value;
                const newMode = Object.keys(syllabusData[newGrade])[0];
                const newSubject = Object.keys(
                  syllabusData[newGrade][newMode]
                )[0];
                const newChapter =
                  syllabusData[newGrade][newMode][newSubject][0];

                setSearchGrade(newGrade);
                setSearchMode(newMode);
                setSearchSubject(newSubject);
                setSearchChapter(newChapter);
              }}
            >
              {grades.map((g) => (
                <option key={g} value={g}>
                  {g}
                </option>
              ))}
            </select>
          </label>

          <label>
            Search Mode
            <select
              value={searchMode}
              onChange={(e) => {
                const newMode = e.target.value;
                const newSubject = Object.keys(
                  syllabusData[searchGrade][newMode]
                )[0];
                const newChapter =
                  syllabusData[searchGrade][newMode][newSubject][0];

                setSearchMode(newMode);
                setSearchSubject(newSubject);
                setSearchChapter(newChapter);
              }}
            >
              {Object.keys(syllabusData[searchGrade]).map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </label>

          <label>
            Search Subject
            <select
              value={searchSubject}
              onChange={(e) => {
                const newSubject = e.target.value;
                const newChapter =
                  syllabusData[searchGrade][searchMode][newSubject][0];

                setSearchSubject(newSubject);
                setSearchChapter(newChapter);
              }}
            >
              {Object.keys(syllabusData[searchGrade][searchMode]).map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </label>

          <label>
            Search Chapter
            <select
              value={searchChapter}
              onChange={(e) => setSearchChapter(e.target.value)}
            >
              {(syllabusData[searchGrade][searchMode][searchSubject] || []).map(
                (c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                )
              )}
            </select>
          </label>
        </div>

        <input
          type="text"
          placeholder="Example: What are nouns?"
          value={ragQuery}
          onChange={(e) => setRagQuery(e.target.value)}
          style={{
            width: "100%",
            padding: 12,
            marginBottom: 16,
          }}
        />

        <button
          className="primary-btn"
          onClick={handleSearchRag}
          disabled={searchingRag}
        >
          {searchingRag ? "Searching..." : "🔍 Search RAG"}
        </button>

        {ragResults.length > 0 && (
          <div
            style={{
              marginTop: 24,
            }}
          >
            {ragResults.map((item, index) => (
              <div key={index} className="premium-rag-result-row success">
                <div>
                  <strong>{item.document?.title || "Unknown Source"}</strong>

                  <p>
                    {item.document?.subject} • {item.document?.chapter}
                  </p>

                  <pre
                    style={{
                      whiteSpace: "pre-wrap",
                      marginTop: 12,
                    }}
                  >
                    {item.chunk_text}
                  </pre>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
      )}

      {activeRagWorkspace === "bookUploads" && (
      <>
      <section className="premium-section premium-rag-upload-panel">
        <div className="premium-header">
          <h3>📖 Full Book PDF Splitter</h3>
          <p>
            Upload one complete textbook PDF, detect chapter page ranges, review
            them, then create one RAG document per chapter. Best for State Board
            books that come as a single PDF.
          </p>
        </div>

        <div className="form-grid premium-rag-form-grid">
          <label>
            Class
            <select
              value={fullBookGrade}
              onChange={(e) => handleFullBookGradeChange(e.target.value)}
            >
              {grades.map((g) => (
                <option key={g} value={g}>
                  {g}
                </option>
              ))}
            </select>
          </label>

          <label>
            Board
            <select
              value={fullBookBoard}
              onChange={(e) => handleFullBookBoardChange(e.target.value)}
            >
              {SCHOOL_BOARD_OPTIONS.map((boardOption) => (
                <option key={boardOption} value={boardOption}>
                  {boardOption}
                </option>
              ))}
            </select>
          </label>

          <label>
            Subject
            {fullBookSubjects.length > 0 ? (
              <select
                value={fullBookSubject}
                onChange={(e) => setFullBookSubject(e.target.value)}
              >
                {fullBookSubjects.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            ) : (
              <input
                type="text"
                value={fullBookSubject}
                placeholder="Example: English"
                onChange={(e) => setFullBookSubject(e.target.value)}
              />
            )}
          </label>

          <label>
            Book Title
            <input
              type="text"
              value={fullBookTitle}
              placeholder="Example: Assam State Board - English Beehive"
              onChange={(e) => setFullBookTitle(e.target.value)}
            />
          </label>

          <label>
            Full Book PDF
            <input
              type="file"
              accept=".pdf"
              onChange={(e) => {
                setFullBookFile(e.target.files?.[0] || null);
                setFullBookAnalysis(null);
              }}
            />
          </label>

          <label className="premium-toggle-row">
            <input
              type="checkbox"
              checked={fullBookOcrScanned}
              onChange={(e) => setFullBookOcrScanned(e.target.checked)}
            />
            OCR scanned/image PDF
          </label>
        </div>

        {fullBookFile && (
          <small className="premium-rag-bulk-book-file">
            Selected: {fullBookFile.name}
          </small>
        )}

        <div className="premium-rag-bulk-book-actions">
          <button
            type="button"
            className="secondary-btn"
            onClick={handleAnalyzeFullBook}
            disabled={fullBookAnalyzing || isRagJobRunning(fullBookAnalysisJob) || !fullBookFile}
          >
            {fullBookAnalyzing ? "Analyzing Book..." : "Analyze Full Book"}
          </button>

          <button
            type="button"
            className="primary-btn premium-rag-upload-btn"
            onClick={handleUploadFullBookSections}
            disabled={
              fullBookUploading ||
              isRagJobRunning(fullBookUploadJob) ||
              !fullBookAnalysis?.chapters?.length
            }
          >
            {fullBookUploading ? "Uploading Chapters..." : "Upload Reviewed Chapters"}
          </button>
        </div>

        <RagJobProgress
          job={fullBookAnalysisJob}
          title="Full-book analysis"
        />

        <RagJobProgress
          job={fullBookUploadJob}
          title="Reviewed chapter upload"
        />

        {recentRagJobs.length > 0 && (
          <div className="premium-rag-job-list">
            <div className="premium-rag-job-list-header">
              <strong>Recent RAG jobs</strong>
              <small>Parallel book batches continue in the background.</small>
            </div>

            {recentRagJobs.slice(0, 5).map((job) => (
              <div key={job.id} className="premium-rag-job-list-row">
                <span>{job.filename || job.job_type}</span>
                <span>{job.phase || job.status}</span>
                <span>{job.percent || 0}%</span>
              </div>
            ))}
          </div>
        )}

        {fullBookAnalysis && (
          <div className="premium-rag-extracted-pages">
            <h4>Review Detected Chapters</h4>
            <p>
              {fullBookAnalysis.page_count || 0} pages •{" "}
              {fullBookAnalysis.word_count || 0} extracted words •{" "}
              {(fullBookAnalysis.extraction_methods || []).join(", ") || "No extraction method"}
            </p>

            {(fullBookAnalysis.warnings || []).map((warning, index) => (
              <div key={index} className="premium-rag-result-row failed">
                {warning}
              </div>
            ))}

            <div className="premium-rag-result-list">
              {(fullBookAnalysis.chapters || []).map((chapter, index) => (
                <div
                  key={`${chapter.title}-${index}`}
                  className="premium-rag-result-row premium-rag-chapter-review-row success"
                >
                  <div className="premium-rag-chapter-review-fields">
                    <label className="premium-toggle-row">
                      <input
                        type="checkbox"
                        checked={chapter.include !== false}
                        onChange={(e) =>
                          updateFullBookChapter(index, {
                            include: e.target.checked,
                          })
                        }
                      />
                      Include
                    </label>

                    <label className="premium-rag-inline-label">
                      Chapter Title
                      <input
                        type="text"
                        value={chapter.title || ""}
                        onChange={(e) =>
                          updateFullBookChapter(index, {
                            title: e.target.value,
                          })
                        }
                      />
                    </label>

                    <label className="premium-rag-inline-label">
                      Start Page
                      <input
                        type="number"
                        min="1"
                        value={chapter.start_page || 1}
                        onChange={(e) =>
                          updateFullBookChapter(index, {
                            start_page: Number(e.target.value),
                          })
                        }
                      />
                    </label>

                    <label className="premium-rag-inline-label">
                      End Page
                      <input
                        type="number"
                        min="1"
                        value={chapter.end_page || chapter.start_page || 1}
                        onChange={(e) =>
                          updateFullBookChapter(index, {
                            end_page: Number(e.target.value),
                          })
                        }
                      />
                    </label>
                  </div>

                  <div className="premium-rag-chapter-preview">
                    <strong>Confidence: {chapter.confidence || "Low"}</strong>
                    {chapter.preview && (
                      <small>{chapter.preview.slice(0, 220)}</small>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </section>

      <section className="premium-section premium-rag-upload-panel">
        <div className="premium-header">
          <h3>📦 Class 1-10 School-board Bulk Book Upload</h3>
          <p>
            Upload full subject books for CBSE, ICSE, or State Board classes 1
            to 10. Each file is tagged with its own board, class, and subject, then indexed under Uploaded
            Book Content for lessons, doubts, and mock-test retrieval.
          </p>
        </div>

        <div className="premium-rag-bulk-book-list">
          {bulkBookRows.map((row, index) => {
            const resolvedRow = resolveBulkBookRow(row);
            const rowSubjects = getSubjectsForGradeAndBoard(
              resolvedRow.grade,
              resolvedRow.board
            );

            return (
              <div key={row.id} className="premium-rag-bulk-book-row">
                <div className="premium-rag-bulk-book-heading">
                  <strong>Book {index + 1}</strong>
                  <button
                    type="button"
                    className="secondary-btn"
                    onClick={() => removeBulkBookRow(row.id)}
                    disabled={bulkBookRows.length === 1}
                  >
                    Remove
                  </button>
                </div>

                <div className="form-grid premium-rag-form-grid">
                  <label>
                    Class
                    <select
                      value={resolvedRow.grade}
                      onChange={(e) =>
                        updateBulkBookRow(row.id, {
                          grade: e.target.value,
                        })
                      }
                    >
                      {grades.map((g) => (
                        <option key={g} value={g}>
                          {g}
                        </option>
                      ))}
                    </select>
                  </label>

                  <label>
                    Board
                    <select
                      value={resolvedRow.board || "CBSE"}
                      onChange={(e) =>
                        updateBulkBookRow(row.id, {
                          board: e.target.value,
                        })
                      }
                    >
                      {SCHOOL_BOARD_OPTIONS.map((boardOption) => (
                        <option key={boardOption} value={boardOption}>
                          {boardOption}
                        </option>
                      ))}
                    </select>
                  </label>

                  <label>
                    Subject
                    {rowSubjects.length > 0 ? (
                      <select
                        value={resolvedRow.subject}
                        onChange={(e) =>
                          updateBulkBookRow(row.id, {
                            subject: e.target.value,
                          })
                        }
                      >
                        {rowSubjects.map((s) => (
                          <option key={s} value={s}>
                            {s}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <input
                        type="text"
                        value={resolvedRow.subject}
                        placeholder="Example: Science"
                        onChange={(e) =>
                          updateBulkBookRow(row.id, {
                            subject: e.target.value,
                          })
                        }
                      />
                    )}
                  </label>

                  <label>
                    Document Title
                    <input
                      type="text"
                      value={row.title}
                      placeholder={`${resolvedRow.grade} ${resolvedRow.subject} Full Book`}
                      onChange={(e) =>
                        updateBulkBookRow(row.id, {
                          title: e.target.value,
                        })
                      }
                    />
                  </label>

                  <label>
                    Book File
                    <input
                      type="file"
                      accept={BULK_BOOK_FILE_ACCEPT}
                      onChange={(e) =>
                        updateBulkBookRow(row.id, {
                          file: e.target.files?.[0] || null,
                        })
                      }
                    />
                  </label>
                </div>

                {row.file && (
                  <small className="premium-rag-bulk-book-file">
                    Selected: {row.file.name} • Stored as {BOOK_CHAPTER_LABEL}
                  </small>
                )}
              </div>
            );
          })}
        </div>

        <div className="premium-rag-bulk-book-actions">
          <button
            type="button"
            className="secondary-btn"
            onClick={addBulkBookRow}
            disabled={bulkBookRows.length >= 20}
          >
            + Add Another Book
          </button>

          <button
            className="primary-btn premium-rag-upload-btn"
            onClick={handleBulkBookUpload}
            disabled={bulkUploading}
          >
            {bulkUploading ? "Uploading Books..." : "Upload Books to RAG"}
          </button>
        </div>
      </section>

      <section className="premium-section premium-rag-upload-panel">
        <div className="premium-header">
          <h3>🗂️ One Book, Many Files</h3>
          <p>
            Upload a TOC PDF and chapter PDFs that together make one book. Each
            file is indexed as a separate searchable section under the same book.
          </p>
        </div>

        <div className="form-grid premium-rag-form-grid">
          <label>
            Book Set Class
            <select
              value={bookSetGrade}
              onChange={(e) => handleBookSetGradeChange(e.target.value)}
            >
              {grades.map((g) => (
                <option key={g} value={g}>
                  {g}
                </option>
              ))}
            </select>
          </label>

          <label>
            Book Set Board
            <select
              value={bookSetBoard}
              onChange={(e) => handleBookSetBoardChange(e.target.value)}
            >
              {SCHOOL_BOARD_OPTIONS.map((boardOption) => (
                <option key={boardOption} value={boardOption}>
                  {boardOption}
                </option>
              ))}
            </select>
          </label>

          <label>
            Book Set Subject
            {bookSetSubjects.length > 0 ? (
              <select
                value={bookSetSubject}
                onChange={(e) => setBookSetSubject(e.target.value)}
              >
                {bookSetSubjects.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            ) : (
              <input
                type="text"
                value={bookSetSubject}
                placeholder="Example: Science"
                onChange={(e) => setBookSetSubject(e.target.value)}
              />
            )}
          </label>

          <label>
            Book Title
            <input
              type="text"
              value={bookSetTitle}
              placeholder="Example: Grade 5 Science Textbook"
              onChange={(e) => setBookSetTitle(e.target.value)}
            />
          </label>

          <label>
            Book Files
            <input
              type="file"
              multiple
              accept={BULK_BOOK_FILE_ACCEPT}
              onChange={(e) => setBookSetFiles(Array.from(e.target.files || []))}
            />
          </label>
        </div>

        <label className="full-width-label premium-rag-title-input">
          TOC / Chapter Titles
          <textarea
            value={bookSetSectionTitles}
            rows={5}
            placeholder={"Table of Contents\nChapter 1: Plants\nChapter 2: Animals"}
            onChange={(e) => setBookSetSectionTitles(e.target.value)}
          />
        </label>

        {bookSetFiles.length > 0 && (
          <div className="selected-files-box premium-selected-files-box">
            <strong>Selected book files:</strong>
            {bookSetFiles.map((selectedFile, index) => (
              <div key={index}>
                {index + 1}. {selectedFile.name}
              </div>
            ))}
          </div>
        )}

        <div className="premium-rag-bulk-book-actions">
          <button
            type="button"
            className="secondary-btn"
            onClick={handleAnalyzeBookSet}
            disabled={bookSetAnalyzing || bookSetFiles.length === 0}
          >
            {bookSetAnalyzing ? "Analyzing Labels..." : "Analyze Chapter Labels"}
          </button>
        </div>

        {bookSetAnalysis.length > 0 && (
          <div className="premium-rag-extracted-pages">
            <h4>Review Suggested Labels</h4>
            <div className="premium-rag-result-list">
              {bookSetAnalysis.map((section, index) => (
                <div
                  key={`${section.filename}-${index}`}
                  className={
                    section.warnings?.length
                      ? "premium-rag-result-row failed"
                      : "premium-rag-result-row success"
                  }
                >
                  <div>
                    <strong>{section.filename}</strong>
                    <p>{section.word_count || 0} extracted words</p>
                    {section.warnings?.length > 0 && (
                      <small>{section.warnings.join(" ")}</small>
                    )}
                    {section.preview && (
                      <small>{section.preview.slice(0, 180)}</small>
                    )}
                  </div>

                  <label className="premium-rag-inline-label">
                    Confirm Label
                    <textarea
                      className="premium-rag-label-input"
                      rows={2}
                      value={section.suggested_title || ""}
                      onChange={(e) =>
                        updateBookSetAnalysisTitle(index, e.target.value)
                      }
                    />
                  </label>
                </div>
              ))}
            </div>
          </div>
        )}

        <button
          className="primary-btn premium-rag-upload-btn"
          onClick={handleBookSetUpload}
          disabled={bookSetUploading}
        >
          {bookSetUploading ? "Uploading Book Files..." : "Upload Book Set to RAG"}
        </button>
      </section>
      </>
      )}

      {activeRagWorkspace === "sof" && (
      <section className="premium-section">
        <div className="premium-header">
          <h3>📚 SOF Bulk Book Upload</h3>
          <p>
            Upload up to 20 SOF PDFs or page photos. AI will group them as Science
            Olympiad, Maths Olympiad, or English Olympiad and prepare them for
            RAG upload.
          </p>
        </div>

        <label className="full-width-label premium-rag-file-input">
          SOF PDFs or Page Photos
          <input
            type="file"
            multiple
            accept=".pdf,image/*"
            onChange={(e) => setSofFiles(Array.from(e.target.files || []))}
          />
        </label>

        <label className="full-width-label premium-rag-file-input premium-rag-camera-input">
          <span>Scan SOF Page With Phone Camera</span>
          <span className="premium-rag-camera-button">Open Camera</span>
          <input
            className="premium-rag-hidden-file-input"
            type="file"
            accept="image/*"
            capture="environment"
            onChange={(e) => {
              const selectedFiles = Array.from(e.target.files || []);

              setSofFiles((prev) => appendFiles(prev, selectedFiles));
              e.target.value = "";
            }}
          />
        </label>

        {sofFiles.length > 0 && (
          <div className="selected-files-box premium-selected-files-box">
            <strong>Selected SOF files:</strong>
            {sofFiles.map((selectedFile, index) => (
              <div key={index}>
                {index + 1}. {selectedFile.name}
              </div>
            ))}
          </div>
        )}

        <button
          className="primary-btn"
          onClick={handleAnalyzeSofImages}
          disabled={sofAnalyzing}
          style={{ marginTop: 16 }}
        >
          {sofAnalyzing
            ? "Analyzing SOF Files..."
            : "🧠 Analyze & Organize SOF Files"}
        </button>

        {sofPages.length > 0 && (
          <div className="premium-rag-extracted-pages">
            <h4>Extracted Pages Review</h4>
            <div className="premium-rag-result-list">
              {sofPages.map((page) => (
                <div
                  key={`${page.filename}-${page.page_number}`}
                  className={
                    page.warnings?.length
                      ? "premium-rag-result-row failed"
                      : "premium-rag-result-row success"
                  }
                >
                  <div>
                    <strong>
                      Page {page.page_number}: {page.filename}
                    </strong>
                    <p>
                      Source page {page.source_page_number || page.page_number} •{" "}
                      {page.extraction_method || "extracted text"} •{" "}
                      {page.word_count || 0} words
                    </p>
                    {page.warnings?.length > 0 && (
                      <small>{page.warnings.join(" ")}</small>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {sofGroups.length > 0 && (
          <div
            style={{
              marginTop: 24,
              padding: 20,
              borderRadius: 16,
              border: "1px solid #334155",
            }}
          >
            <h4>Detected SOF Groups</h4>

            <div className="premium-rag-result-list">
              {sofGroups.map((group, index) => (
                <div key={index} className="premium-rag-result-row success premium-rag-editable-group">
                  <div className="premium-rag-editable-group-main">
                    <strong>{group.title || group.chapter}</strong>
                    <small>
                      Pages: {(group.page_numbers || []).join(", ") || "N/A"} •
                      Confidence: {group.confidence || "Unknown"} •{" "}
                      {(group.combined_text || "").split(/\s+/).filter(Boolean).length} words
                    </small>

                    <div className="form-grid premium-rag-form-grid">
                      <label>
                        Grade
                        <input
                          type="text"
                          value={group.grade || ""}
                          onChange={(e) =>
                            updateSofGroup(index, {
                              grade: e.target.value,
                            })
                          }
                        />
                      </label>

                      <label>
                        Subject
                        <select
                          value={group.subject || ""}
                          onChange={(e) =>
                            updateSofGroup(index, {
                              subject: e.target.value,
                            })
                          }
                        >
                          {[
                            "Science Olympiad",
                            "Maths Olympiad",
                            "English Olympiad",
                          ].map((option) => (
                            <option key={option} value={option}>
                              {option}
                            </option>
                          ))}
                        </select>
                      </label>

                      <label>
                        Chapter / Section
                        <input
                          type="text"
                          value={group.chapter || ""}
                          onChange={(e) =>
                            updateSofGroup(index, {
                              chapter: e.target.value,
                            })
                          }
                        />
                      </label>

                      <label>
                        Document Title
                        <input
                          type="text"
                          value={group.title || ""}
                          onChange={(e) =>
                            updateSofGroup(index, {
                              title: e.target.value,
                            })
                          }
                        />
                      </label>
                    </div>

                    <label className="full-width-label premium-rag-title-input">
                      RAG Context Text
                      <textarea
                        value={group.combined_text || ""}
                        rows={8}
                        onChange={(e) =>
                          updateSofGroup(index, {
                            combined_text: e.target.value,
                          })
                        }
                      />
                    </label>
                  </div>
                </div>
              ))}
            </div>

            <button
              className="primary-btn"
              onClick={handleConfirmSofUpload}
              disabled={sofUploading}
              style={{ marginTop: 16 }}
            >
              {sofUploading
                ? "Uploading to RAG..."
                : "✅ Confirm SOF Upload to RAG"}
            </button>
          </div>
        )}

        {sofRawResponse && sofGroups.length === 0 && (
          <div
            style={{
              marginTop: 24,
              padding: 20,
              borderRadius: 16,
              border: "1px solid #334155",
            }}
          >
            <h4>Raw AI Response</h4>
            <pre style={{ whiteSpace: "pre-wrap" }}>{sofRawResponse}</pre>
          </div>
        )}
      </section>
      )}

      {activeRagWorkspace === "manual" && (
      <>
      <section className="premium-section">
        <div className="premium-header">
          <h3>📸 Analyze Single Book Page</h3>
          <p>
            Upload one textbook page photo. AI will extract text and suggest
            title, chapter, subject, and grade.
          </p>
        </div>

        <div className="premium-rag-scan-grid">
          <label className="full-width-label premium-rag-file-input">
            Upload Page Photo
            <input
              type="file"
              accept="image/*"
              onChange={(e) => setAnalysisImage(e.target.files?.[0] || null)}
            />
          </label>

          <label className="full-width-label premium-rag-file-input premium-rag-camera-input">
            <span>Scan Page With Phone Camera</span>
            <span className="premium-rag-camera-button">Open Camera</span>
            <input
              className="premium-rag-hidden-file-input"
              type="file"
              accept="image/*"
              capture="environment"
              onChange={(e) => {
                setAnalysisImage(e.target.files?.[0] || null);
                e.target.value = "";
              }}
            />
          </label>
        </div>

        {analysisImage && (
          <div className="selected-files-box premium-selected-files-box">
            <strong>Selected page:</strong>
            <div>{analysisImage.name}</div>
          </div>
        )}

        <button
          className="primary-btn"
          onClick={handleAnalyzeImage}
          disabled={analyzingImage}
          style={{ marginTop: 16 }}
        >
          {analyzingImage ? "Analyzing..." : "🔍 Analyze Page"}
        </button>

        {analysisResult && (
          <div
            style={{
              marginTop: 24,
              padding: 20,
              borderRadius: 16,
              border: "1px solid #334155",
            }}
          >
            <h4>Detected Metadata</h4>

            <pre style={{ whiteSpace: "pre-wrap" }}>
              {analysisResult.suggestion}
            </pre>
          </div>
        )}
      </section>

      <section className="premium-section premium-rag-upload-panel">
        <div className="premium-header">
          <h3>Manual Upload Textbook / Notes / Worksheet</h3>
          <p>Supported files: txt, jpg, jpeg, png, webp, pdf, docx, pptx.</p>
        </div>

        <div className="form-grid premium-rag-form-grid">
          <label>
            Grade
            <select
              value={grade}
              onChange={(e) => handleGradeChange(e.target.value)}
            >
              {grades.map((g) => (
                <option key={g} value={g}>
                  {g}
                </option>
              ))}
            </select>
          </label>

          <label>
            Mode
            <select
              value={mode}
              onChange={(e) => handleModeChange(e.target.value)}
            >
              {modes.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </label>

          <label>
            Subject
            <select
              value={subject}
              onChange={(e) => handleSubjectChange(e.target.value)}
            >
              {subjects.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </label>

          <label>
            Chapter / Section
            <select
              value={chapter}
              onChange={(e) => setChapter(e.target.value)}
            >
              {chapters.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </label>
        </div>

        <label className="full-width-label premium-rag-title-input">
          Document Titles
          <input
            type="text"
            value={title}
            placeholder="Example: Chapter 1, Chapter 2, Chapter 3"
            onChange={(e) => setTitle(e.target.value)}
          />
        </label>

        <label className="full-width-label premium-rag-file-input">
          Upload Files
          <input
            type="file"
            multiple
            accept={BULK_BOOK_FILE_ACCEPT}
            onChange={(e) => setFiles(Array.from(e.target.files || []))}
          />
        </label>

        <label className="full-width-label premium-rag-file-input premium-rag-camera-input">
          <span>Scan Page With Phone Camera</span>
          <span className="premium-rag-camera-button">Open Camera</span>
          <input
            className="premium-rag-hidden-file-input"
            type="file"
            accept="image/*"
            capture="environment"
            onChange={(e) => {
              const selectedFiles = Array.from(e.target.files || []);

              setFiles((prev) => appendFiles(prev, selectedFiles));
              e.target.value = "";
            }}
          />
        </label>

        {files.length > 0 && (
          <div className="selected-files-box premium-selected-files-box">
            <strong>Selected files:</strong>
            {files.map((selectedFile, index) => (
              <div key={index}>
                {index + 1}. {selectedFile.name}
              </div>
            ))}
          </div>
        )}

        <button
          className="primary-btn premium-rag-upload-btn"
          onClick={handleBatchUpload}
          disabled={uploading}
        >
          {uploading ? "Uploading..." : "✨ Upload Batch to RAG"}
        </button>
      </section>
      </>
      )}

      {message && <div className="info-box">{message}</div>}
      {error && <div className="error-box">{error}</div>}

      {batchResults.length > 0 && (
        <section className="premium-section premium-rag-results">
          <div className="premium-header">
            <h3>Upload Results</h3>
            <p>Uploaded documents and chunk creation status.</p>
          </div>

          <div className="premium-rag-result-list">
            {batchResults.map((item, index) => (
              <div
                key={index}
                className={
                  item.success
                    ? "premium-rag-result-row success"
                    : "premium-rag-result-row failed"
                }
              >
                <div>
                  <strong>{item.title}</strong>
                  <p>{item.subject || item.filename}</p>
                  <p>{item.chapter || "No chapter metadata"}</p>
                  {!item.success && item.message && (
                    <small>{item.message}</small>
                  )}
                </div>

                <div>
                  <span>{item.success ? "Success" : "Failed"}</span>
                  <small>{item.chunks_created} chunks</small>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {activeRagWorkspace === "library" && (
      <section className="premium-section">
        <div className="premium-header">
          <h3>📚 RAG Document Library</h3>
          <p>Uploaded documents currently available to the AI tutor.</p>
        </div>

        {documents.length === 0 ? (
          <div className="premium-parent-empty">
            <h3>No documents uploaded yet</h3>
          </div>
        ) : (
          <div className="premium-rag-result-list">
            {documents.map((doc) => (
              <div key={doc.id} className="premium-rag-result-row success">
                <div className="premium-rag-library-main">
                  {activeMetadataDocId === doc.id ? (
                    <div className="premium-rag-metadata-editor">
                      <label>
                        Document title
                        <input
                          value={metadataDraft.title}
                          onChange={(e) =>
                            setMetadataDraft((currentDraft) => ({
                              ...currentDraft,
                              title: e.target.value,
                            }))
                          }
                        />
                      </label>

                      <label>
                        Retrieval chapter
                        <input
                          value={metadataDraft.chapter}
                          onChange={(e) =>
                            setMetadataDraft((currentDraft) => ({
                              ...currentDraft,
                              chapter: e.target.value,
                            }))
                          }
                        />
                      </label>
                    </div>
                  ) : (
                    <>
                      <strong>{doc.title}</strong>
                      <p>
                        {doc.board || "CBSE"} • {doc.grade} • {doc.subject}
                      </p>
                      <p>{doc.chapter}</p>
                      <small>Uploaded by {doc.uploaded_by}</small>
                    </>
                  )}

                  {previewByDocument[doc.id] && (
                    <div className="premium-rag-preview-box">
                      <strong>Stored content preview</strong>
                      <p>{previewByDocument[doc.id]}</p>
                    </div>
                  )}
                </div>

                <div className="premium-rag-library-actions">
                  {activeMetadataDocId === doc.id ? (
                    <>
                      <button
                        className="primary-btn compact-btn"
                        onClick={() => handleSaveRagMetadata(doc)}
                        disabled={savingMetadataId === doc.id}
                      >
                        {savingMetadataId === doc.id ? "Saving..." : "Save Metadata"}
                      </button>
                      <button
                        className="secondary-btn compact-btn"
                        onClick={() => setActiveMetadataDocId("")}
                      >
                        Cancel
                      </button>
                    </>
                  ) : (
                    <>
                      <button
                        className="secondary-btn compact-btn"
                        onClick={() => handlePreviewRagDocument(doc)}
                        disabled={previewLoadingId === doc.id}
                      >
                        {previewLoadingId === doc.id ? "Loading..." : "Preview Content"}
                      </button>
                      <button
                        className="secondary-btn compact-btn"
                        onClick={() => startEditRagDocument(doc)}
                      >
                        Edit Metadata
                      </button>
                    </>
                  )}
                  <button
                    className="danger-btn"
                    onClick={() => handleDeleteDocument(doc.id)}
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
      )}
    </div>
  );
}

export default RagUploadPage;
