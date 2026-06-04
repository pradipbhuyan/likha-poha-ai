import { useEffect, useState } from "react";

import { getSyllabus } from "../api/syllabus";

import {
  uploadRagFilesBatch,
  uploadBulkBooks,
  uploadBookSet,
  analyzeBookSetFiles,
  getRagDocuments,
  deleteRagDocument,
  analyzeRagImage,
  analyzeSofImages,
  confirmSofUpload,
  searchRag,
} from "../api/rag";
import { getDefaultSelection } from "../utils/syllabusDefaults";

const BOOK_CHAPTER_LABEL = "Uploaded Book Content";
const BULK_BOOK_FILE_ACCEPT = ".txt,.jpg,.jpeg,.png,.webp,.pdf,.docx,.pptx";

function createBulkBookRow(index = 0) {
  /** Create one editable row for a Class 1-10 full-book RAG upload. */
  return {
    id: `${Date.now()}-${index}`,
    grade: "Grade 1",
    subject: "",
    title: "",
    file: null,
  };
}

function RagUploadPage({ user }) {
  /** Admin-only workspace for uploading, analyzing, searching, and deleting RAG documents. */
  const [loading, setLoading] = useState(true);
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
  const [bookSetSubject, setBookSetSubject] = useState("");
  const [bookSetTitle, setBookSetTitle] = useState("");
  const [bookSetSectionTitles, setBookSetSectionTitles] = useState("");
  const [bookSetFiles, setBookSetFiles] = useState([]);
  const [bookSetAnalysis, setBookSetAnalysis] = useState([]);
  const [bookSetAnalyzing, setBookSetAnalyzing] = useState(false);
  const [bookSetUploading, setBookSetUploading] = useState(false);

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
      } finally {
        setLoading(false);
      }
    }

    loadSyllabus();
    loadDocuments();
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

  function appendFiles(currentFiles, selectedFiles, maxFiles = 20) {
    /** Add selected files while enforcing the 20-file upload limit. */
    return [...currentFiles, ...selectedFiles].slice(0, maxFiles);
  }

  function getCbseSubjectsForGrade(rowGrade) {
    /** Return the CBSE subject options available for one bulk book row. */
    return Object.keys(syllabusData?.[rowGrade]?.CBSE || {});
  }

  function resolveBulkBookRow(row) {
    /** Fill safe defaults for one bulk book row before validation/upload. */
    const subjectsForGrade = getCbseSubjectsForGrade(row.grade);
    const resolvedSubject = row.subject || subjectsForGrade[0] || "";

    return {
      ...row,
      subject: resolvedSubject,
      title:
        row.title.trim() ||
        `${row.grade} ${resolvedSubject || "CBSE"} Full Book`,
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

        if (updates.grade) {
          nextRow.subject = getCbseSubjectsForGrade(updates.grade)[0] || "";
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
    nextRow.subject = getCbseSubjectsForGrade(nextRow.grade)[0] || "";
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
    setBookSetSubject(getCbseSubjectsForGrade(value)[0] || "");
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

    const sectionTitleCount = bookSetSectionTitles
      .replace(/,/g, "\n")
      .split("\n")
      .map((item) => item.trim())
      .filter(Boolean).length;

    if (sectionTitleCount > 0 && sectionTitleCount !== bookSetFiles.length) {
      setError("Section title count must match selected file count.");
      return;
    }

    setBookSetUploading(true);

    try {
      const result = await uploadBookSet({
        username: user.username,
        grade: bookSetGrade,
        subject: bookSetSubject,
        bookTitle: bookSetTitle.trim(),
        sectionTitles: bookSetSectionTitles,
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
  const bookSetSubjects = getCbseSubjectsForGrade(bookSetGrade);

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

      <section className="premium-section premium-rag-upload-panel">
        <div className="premium-header">
          <h3>📦 CBSE Class 1-10 Bulk Book Upload</h3>
          <p>
            Upload full subject books for any class from 1 to 10. Each file is
            tagged with its own class and subject, then indexed under Uploaded
            Book Content for lessons, doubts, and mock-test retrieval.
          </p>
        </div>

        <div className="premium-rag-bulk-book-list">
          {bulkBookRows.map((row, index) => {
            const resolvedRow = resolveBulkBookRow(row);
            const rowSubjects = getCbseSubjectsForGrade(resolvedRow.grade);

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
                    Subject
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
            Book Set Subject
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
                    <input
                      type="text"
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
                <div>
                  <strong>{doc.title}</strong>
                  <p>
                    {doc.grade} • {doc.subject}
                  </p>
                  <p>{doc.chapter}</p>
                  <small>Uploaded by {doc.uploaded_by}</small>
                </div>

                <div>
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
    </div>
  );
}

export default RagUploadPage;
