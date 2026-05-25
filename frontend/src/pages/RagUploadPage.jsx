import { useEffect, useState } from "react";

import { getSyllabus } from "../api/syllabus";
import { uploadRagFile, uploadRagFilesBatch } from "../api/rag";

function RagUploadPage({ user }) {
  const [loading, setLoading] = useState(true);
  const [syllabusData, setSyllabusData] = useState(null);

  const [grade, setGrade] = useState("Grade 9");
  const [mode, setMode] = useState("CBSE");
  const [subject, setSubject] = useState("");
  const [chapter, setChapter] = useState("");

  const [title, setTitle] = useState("");
  const [file, setFile] = useState(null);

  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const [files, setFiles] = useState([]);
  const [batchResults, setBatchResults] = useState([]);

  const allowedUsers = ["admin", "pradip"];

  useEffect(() => {
    async function loadSyllabus() {
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
  }, []);

  if (!allowedUsers.includes(user.username)) {
    return (
      <div className="premium-page">
        <section className="premium-section premium-rag-locked">
          <div className="premium-header">
            <p className="eyebrow">Restricted Access</p>
            <h2>🔒 RAG Upload</h2>
            <p>Only admin/pradip can upload textbook content.</p>
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
    const newMode = Object.keys(syllabusData[value])[0];
    const newSubject = Object.keys(syllabusData[value][newMode])[0];
    const newChapter = syllabusData[value][newMode][newSubject][0];

    setGrade(value);
    setMode(newMode);
    setSubject(newSubject);
    setChapter(newChapter);
  }

  function handleModeChange(value) {
    const newSubject = Object.keys(syllabusData[grade][value])[0];
    const newChapter = syllabusData[grade][value][newSubject][0];

    setMode(value);
    setSubject(newSubject);
    setChapter(newChapter);
  }

  function handleSubjectChange(value) {
    const newChapter = syllabusData[grade][mode][value][0];

    setSubject(value);
    setChapter(newChapter);
  }

  async function handleUpload() {
    setMessage("");
    setError("");

    if (!title.trim()) {
      setError("Please enter a document titles.");
      return;
    }

    if (!file) {
      setError("Please select a file.");
      return;
    }

    setUploading(true);

    try {
      const result = await uploadRagFile({
        username: user.username,
        grade,
        subject,
        chapter,
        title,
        file,
      });

      if (!result.success) {
        setError(result.message || "Upload failed.");
        return;
      }

      setMessage(
        `Upload successful. Document ID: ${result.document_id}. Chunks created: ${result.chunks_created}.`
      );

      setTitle("");
      setFile(null);
    } catch {
      setError("Upload failed. Check backend.");
    } finally {
      setUploading(false);
    }
  }

  async function handleBatchUpload() {
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

    if (files.length > 10) {
      setError("You can upload a maximum of 10 files.");
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

      setTitle("");
      setFiles([]);
    } catch {
      setError("Batch upload failed. Check backend.");
    } finally {
      setUploading(false);
    }
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
            <strong>Batch Upload Ready</strong>
            <p>Upload up to 10 documents in one batch with comma-separated titles.</p>
          </div>
        </div>
      </section>

      <section className="premium-section premium-rag-upload-panel">
        <div className="premium-header">
          <h3>Upload Textbook / Notes / Worksheet</h3>
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
            <h3>Batch Upload Results</h3>
            <p>Each document title is mapped to the selected file order.</p>
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
                  <p>File: {item.filename}</p>
                  <p>{item.message}</p>
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
    </div>
  );
}

export default RagUploadPage;
