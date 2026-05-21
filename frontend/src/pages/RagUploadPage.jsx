import { useEffect, useState } from "react";

import { getSyllabus } from "../api/syllabus";
import { uploadRagFile } from "../api/rag";

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
      <div className="card">
        <h2>🔒 RAG Upload</h2>
        <p>Only admin/pradip can upload textbook content.</p>
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
      setError("Please enter a document title.");
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

  return (
    <div>
      <h2>📤 RAG Upload</h2>

      <div className="card">
        <h3>Upload Textbook / Notes / Worksheet</h3>

        <p>
          Supported files: txt, jpg, jpeg, png, webp, pdf, docx, pptx.
        </p>

        <div className="form-grid">
          <label>
            Grade
            <select value={grade} onChange={(e) => handleGradeChange(e.target.value)}>
              {grades.map((g) => (
                <option key={g} value={g}>{g}</option>
              ))}
            </select>
          </label>

          <label>
            Mode
            <select value={mode} onChange={(e) => handleModeChange(e.target.value)}>
              {modes.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          </label>

          <label>
            Subject
            <select value={subject} onChange={(e) => handleSubjectChange(e.target.value)}>
              {subjects.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </label>

          <label>
            Chapter / Section
            <select value={chapter} onChange={(e) => setChapter(e.target.value)}>
              {chapters.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </label>
        </div>

        <label className="full-width-label">
          Document Title
          <input
            type="text"
            value={title}
            placeholder="Example: NCERT Polynomials Chapter"
            onChange={(e) => setTitle(e.target.value)}
          />
        </label>

        <label className="full-width-label">
          Upload File
          <input
            type="file"
            accept=".txt,.jpg,.jpeg,.png,.webp,.pdf,.docx,.pptx"
            onChange={(e) => setFile(e.target.files[0])}
          />
        </label>

        <button
          className="primary-btn"
          onClick={handleUpload}
          disabled={uploading}
        >
          {uploading ? "Uploading..." : "Upload to RAG"}
        </button>
      </div>

      {message && <div className="info-box">{message}</div>}
      {error && <div className="error-box">{error}</div>}
    </div>
  );
}

export default RagUploadPage;