import { useEffect, useState } from "react";

import { getSyllabus } from "../api/syllabus";

import {
  uploadRagFilesBatch,
  getRagDocuments,
  deleteRagDocument,
  analyzeRagImage,
  analyzeSofImages,
  confirmSofUpload,
  searchRag,
} from "../api/rag";

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

        const defaultGrade = "Grade 9";
        const defaultMode = "CBSE";
        const defaultSubject = Object.keys(
          data.syllabus[defaultGrade][defaultMode]
        )[0];

        const defaultChapter =
          data.syllabus[defaultGrade][defaultMode][defaultSubject][0];

        setGrade(defaultGrade);
        setMode(defaultMode);
        setSubject(defaultSubject);
        setChapter(defaultChapter);
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
        setError(result.message || "SOF image analysis failed.");
        return;
      }

      setSofPages(result.pages || []);
      setSofGroups(result.groups || []);
      setSofRawResponse(result.raw_ai_response || "");
      setMessage("SOF files analyzed. Review extracted pages and groups before uploading.");
    } catch (err) {
      console.error(err);
      setError("SOF image analysis failed. Check backend.");
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
                <div key={index} className="premium-rag-result-row success">
                  <div>
                    <strong>{group.title || group.chapter}</strong>
                    <p>
                      {group.grade} • {group.subject}
                    </p>
                    <p>{group.chapter}</p>
                    <small>
                      Pages: {(group.page_numbers || []).join(", ") || "N/A"} •
                      Confidence: {group.confidence || "Unknown"}
                    </small>
                  </div>

                  <div>
                    <span>
                      {
                        (group.combined_text || "").split(/\s+/).filter(Boolean)
                          .length
                      }{" "}
                      words
                    </span>
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
            accept=".txt,.jpg,.jpeg,.png,.webp,.pdf,.docx,.pptx"
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
                  <p>{item.chapter || item.message}</p>
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
