import { useEffect, useMemo, useState } from "react";
import { BookOpen, ClipboardList, GraduationCap, Users, UserPlus, Mail } from "lucide-react";

import {
  createTeacherNote,
  createTeacherStudent,
  emailStudentCredentials,
  getTeacherDashboardSummary,
} from "../api/teacherDashboard";

const GRADES = [
  "Grade 5","Grade 6","Grade 7","Grade 8","Grade 9","Grade 10",
];

const DEFAULT_STUDENT_FORM = {
  username: "",
  grade: "Grade 9",
  password: "",
  email: "",
  subject: "",
};

function TeacherDashboardPage({ user }) {
  /** Teacher workspace — assigned students, progress, notes, and student creation. */
  const [summary, setSummary] = useState(null);
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [savingNote, setSavingNote] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [selectedGrade, setSelectedGrade] = useState("all");
  const [selectedSubject, setSelectedSubject] = useState("all");
  const [selectedStudentId, setSelectedStudentId] = useState("");
  const [noteForm, setNoteForm] = useState({ subject: "", chapter: "", note: "" });

  // ── Add Student modal state ──────────────────────────────────────────────
  const [showAddStudent, setShowAddStudent] = useState(false);
  const [studentForm, setStudentForm] = useState(DEFAULT_STUDENT_FORM);
  const [addingStudent, setAddingStudent] = useState(false);
  const [addStudentError, setAddStudentError] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  // ── Email credentials state ──────────────────────────────────────────────
  const [emailingId, setEmailingId] = useState("");
  const [emailMsg, setEmailMsg] = useState("");

  async function loadDashboard() {
    setLoading(true);
    setError("");
    try {
      const data = await getTeacherDashboardSummary();
      setSummary(data.summary || {});
      setStudents(data.students || []);
      setSelectedStudentId((current) => {
        if (current && (data.students || []).some((s) => s.profile.id === current)) return current;
        return data.students?.[0]?.profile?.id || "";
      });
    } catch (err) {
      setError(err.message || "Unable to load teacher dashboard.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadDashboard(); }, []);

  const gradeOptions = summary?.active_grades || [];
  const subjectOptions = summary?.subjects || [];
  const studentLimit = summary?.student_limit || { count: 0, max: 10, is_paid: false, at_limit: false };

  const filteredStudents = useMemo(() => students.filter((student) => {
    const assignments = student.assignments || [];
    const gradeMatch = selectedGrade === "all" || assignments.some((a) => a.grade === selectedGrade);
    const subjectMatch = selectedSubject === "all" || assignments.some((a) => a.subject === selectedSubject);
    return gradeMatch && subjectMatch;
  }), [students, selectedGrade, selectedSubject]);

  const selectedStudent =
    students.find((s) => s.profile.id === selectedStudentId) ||
    filteredStudents[0] ||
    null;

  // ── Save note ────────────────────────────────────────────────────────────
  async function handleSaveNote(e) {
    e.preventDefault();
    setMessage("");
    setError("");
    if (!selectedStudent) { setError("Select a student before saving a note."); return; }
    setSavingNote(true);
    try {
      await createTeacherNote({
        student_id: selectedStudent.profile.id,
        subject: noteForm.subject,
        chapter: noteForm.chapter,
        note: noteForm.note,
      });
      setNoteForm({ subject: "", chapter: "", note: "" });
      await loadDashboard();
      setMessage("Teacher note saved.");
    } catch (err) {
      setError(err.message || "Unable to save note.");
    } finally { setSavingNote(false); }
  }

  // ── Add student ──────────────────────────────────────────────────────────
  async function handleAddStudent(e) {
    e.preventDefault();
    setAddStudentError("");
    if (!studentForm.username.trim()) { setAddStudentError("Student name is required."); return; }
    if (!studentForm.grade) { setAddStudentError("Grade is required."); return; }
    if (!studentForm.password || studentForm.password.length < 6) {
      setAddStudentError("Temporary password must be at least 6 characters.");
      return;
    }
    setAddingStudent(true);
    try {
      const result = await createTeacherStudent({
        username: studentForm.username.trim(),
        grade: studentForm.grade,
        password: studentForm.password,
        email: studentForm.email.trim() || undefined,
        subject: studentForm.subject.trim() || undefined,
      });
      setShowAddStudent(false);
      setStudentForm(DEFAULT_STUDENT_FORM);
      setMessage(
        `✅ Student "${result.student?.username}" added! ` +
        `(${result.student_count} / ${result.max_students} students)`
      );
      await loadDashboard();
    } catch (err) {
      setAddStudentError(err.message || "Could not add student. Please try again.");
    } finally { setAddingStudent(false); }
  }

  // ── Email credentials ────────────────────────────────────────────────────
  async function handleEmailCredentials(studentId) {
    setEmailMsg("");
    setEmailingId(studentId);
    try {
      const result = await emailStudentCredentials(studentId);
      setEmailMsg(result.message || "Password reset link sent.");
    } catch (err) {
      setEmailMsg(`❌ ${err.message || "Failed to send email."}`);
    } finally { setEmailingId(""); }
  }

  if (loading) return <p>Loading teacher dashboard...</p>;

  const completedChapters = students.reduce((s, st) => s + Number(st.progress_summary?.completed_chapters || 0), 0);
  const totalMockTests = students.reduce((s, st) => s + Number(st.test_summary?.total_tests || 0), 0);
  const atLimit = studentLimit.at_limit;

  return (
    <div className="premium-page teacher-dashboard-page">
      <section className="premium-section">
        <div className="premium-header">
          <p className="eyebrow">Teacher Workspace</p>
          <h2>{user?.username || "Teacher"} Dashboard</h2>
          <p>Track assigned students across school classrooms or independent tutoring groups.</p>
        </div>
      </section>

      {message && <div className="info-box">{message}</div>}
      {error && <div className="error-box">{error}</div>}
      {emailMsg && (
        <div className={emailMsg.startsWith("❌") ? "error-box" : "info-box"} style={{ marginBottom: 12 }}>
          {emailMsg}
        </div>
      )}

      {/* Stats */}
      <section className="premium-grid premium-grid-4 premium-parent-stats">
        <div className="premium-card">
          <div className="dashboard-stat-icon blue"><Users size={22} /></div>
          <h3>{summary?.assigned_students || 0}</h3>
          <p>Assigned Students</p>
        </div>
        <div className="premium-card">
          <div className="dashboard-stat-icon green"><GraduationCap size={22} /></div>
          <h3>{gradeOptions.length}</h3>
          <p>Active Grades</p>
        </div>
        <div className="premium-card">
          <div className="dashboard-stat-icon purple"><BookOpen size={22} /></div>
          <h3>{completedChapters}</h3>
          <p>Completed Chapters</p>
        </div>
        <div className="premium-card">
          <div className="dashboard-stat-icon red"><ClipboardList size={22} /></div>
          <h3>{totalMockTests}</h3>
          <p>Mock Tests Taken</p>
        </div>
      </section>

      {/* Assigned Roster */}
      <section className="premium-section">
        <div className="premium-header" style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
          <div>
            <h3>Assigned Roster</h3>
            <p>Filter by grade or subject to focus on one class group.</p>
          </div>

          {/* Student limit badge + Add button */}
          <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
            <div style={{
              padding: "6px 14px", borderRadius: 20, fontSize: ".82rem", fontWeight: 600,
              background: atLimit ? "rgba(239,68,68,.12)" : "rgba(99,102,241,.12)",
              color: atLimit ? "#f87171" : "#a5b4fc",
              border: `1px solid ${atLimit ? "rgba(239,68,68,.3)" : "rgba(99,102,241,.3)"}`,
            }}>
              {studentLimit.count} / {studentLimit.max} students
              {studentLimit.is_paid ? " · Paid" : " · Free Tier"}
            </div>

            {atLimit ? (
              <div style={{
                padding: "8px 14px", borderRadius: 9, fontSize: ".8rem", fontWeight: 500,
                background: "rgba(239,68,68,.1)", color: "#f87171",
                border: "1px solid rgba(239,68,68,.25)", maxWidth: 320,
              }}>
                Student limit reached. Contact admin to add more students.
              </div>
            ) : (
              <button
                className="primary-btn"
                style={{ display: "flex", alignItems: "center", gap: 7, padding: "9px 18px", fontSize: ".88rem" }}
                onClick={() => { setShowAddStudent(true); setAddStudentError(""); setStudentForm(DEFAULT_STUDENT_FORM); }}
              >
                <UserPlus size={16} strokeWidth={2.5} />
                Add Student
              </button>
            )}
          </div>
        </div>

        {/* Grade / Subject filters */}
        <div className="form-grid premium-rag-form-grid">
          <label>
            Grade
            <select value={selectedGrade} onChange={(e) => setSelectedGrade(e.target.value)}>
              <option value="all">All grades</option>
              {gradeOptions.map((g) => <option key={g} value={g}>{g}</option>)}
            </select>
          </label>
          <label>
            Subject
            <select value={selectedSubject} onChange={(e) => setSelectedSubject(e.target.value)}>
              <option value="all">All subjects</option>
              {subjectOptions.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </label>
        </div>

        {filteredStudents.length === 0 ? (
          <div className="info-box">
            No students assigned yet.{" "}
            {!atLimit && (
              <span
                style={{ color: "var(--accent-blue, #6366f1)", cursor: "pointer", fontWeight: 600 }}
                onClick={() => setShowAddStudent(true)}
              >
                Add your first student →
              </span>
            )}
          </div>
        ) : (
          <div className="teacher-roster-grid">
            {filteredStudents.map((student) => {
              const profile = student.profile;
              const assignments = student.assignments || [];
              const activity = student.activity || {};
              const progressSummary = student.progress_summary || {};
              const hasRealEmail = profile.has_real_email;

              return (
                <button
                  key={profile.id}
                  className={selectedStudent?.profile?.id === profile.id ? "teacher-student-card active" : "teacher-student-card"}
                  onClick={() => setSelectedStudentId(profile.id)}
                  style={{ position: "relative" }}
                >
                  <strong>{profile.username}</strong>
                  <span>{profile.grade || assignments[0]?.grade || "Grade 9"}</span>
                  <small>
                    {assignments.map((a) => a.subject).filter(Boolean).join(", ") || "General"}
                  </small>
                  <div>
                    <span>{progressSummary.completed_chapters || 0} complete</span>
                    <span>{activity.requests_total || 0} AI requests</span>
                  </div>

                  {/* Email credentials button */}
                  {studentLimit.is_paid ? (
                    <div
                      style={{ marginTop: 8 }}
                      onClick={(e) => {
                        e.stopPropagation();
                        if (hasRealEmail && emailingId !== profile.id) {
                          handleEmailCredentials(profile.id);
                        }
                      }}
                    >
                      {hasRealEmail ? (
                        <span
                          title="Send password reset link to student's email"
                          style={{
                            display: "inline-flex", alignItems: "center", gap: 4,
                            fontSize: ".72rem", fontWeight: 600, cursor: "pointer",
                            color: emailingId === profile.id ? "#64748b" : "#6366f1",
                            padding: "3px 8px", borderRadius: 6,
                            background: "rgba(99,102,241,.1)",
                          }}
                        >
                          <Mail size={12} />
                          {emailingId === profile.id ? "Sending…" : "Email Login"}
                        </span>
                      ) : (
                        <span
                          title="No email available for this student"
                          style={{
                            display: "inline-flex", alignItems: "center", gap: 4,
                            fontSize: ".72rem", color: "#475569",
                            padding: "3px 8px", borderRadius: 6,
                            background: "rgba(71,85,105,.1)",
                            cursor: "not-allowed",
                          }}
                        >
                          <Mail size={12} />
                          No email
                        </span>
                      )}
                    </div>
                  ) : (
                    <div style={{ marginTop: 8 }}>
                      <span
                        title="Upgrade to a paid plan to email login details"
                        style={{
                          display: "inline-flex", alignItems: "center", gap: 4,
                          fontSize: ".72rem", color: "#475569", cursor: "not-allowed",
                          padding: "3px 8px", borderRadius: 6,
                          background: "rgba(71,85,105,.08)",
                        }}
                      >
                        <Mail size={12} />
                        Paid plan needed
                      </span>
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        )}
      </section>

      {/* Student detail + notes */}
      {selectedStudent && (
        <section className="premium-section teacher-detail-grid">
          <div>
            <div className="premium-header">
              <h3>{selectedStudent.profile.username}</h3>
              <p>{selectedStudent.profile.has_real_email ? selectedStudent.profile.email : "(no real email)"}</p>
            </div>
            <div className="premium-card" style={{ marginBottom: 18 }}>
              <h4>Assignments</h4>
              {(selectedStudent.assignments || []).map((a) => (
                <p key={a.id || `${a.subject}-${a.grade}`}>
                  {a.grade || "Grade 9"} • {a.subject || "General"}
                  {a.section ? ` • ${a.section}` : ""}
                </p>
              ))}
            </div>
            <div className="premium-card">
              <h4>Recent Progress</h4>
              {(selectedStudent.recent_progress || []).length === 0 ? (
                <p>No chapter progress recorded yet.</p>
              ) : (
                selectedStudent.recent_progress.map((progress) => (
                  <div key={`${progress.subject}-${progress.chapter}-${progress.updated_at}`} className="teacher-progress-row">
                    <strong>{progress.chapter}</strong>
                    <span>{progress.subject} • Step {Number(progress.current_step_index || 0) + 1}
                      {progress.completed ? " • Completed" : ""}</span>
                  </div>
                ))
              )}
            </div>

            {/* Mock Test Results */}
            <div className="premium-card" style={{ marginTop: 16 }}>
              <h4>🧪 Mock Test Results</h4>
              {selectedStudent.test_summary?.total_tests > 0 && (
                <div style={{
                  display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 10,
                  marginBottom: 14, padding: "10px 14px",
                  background: "rgba(99,102,241,.07)", borderRadius: 9,
                }}>
                  <div style={{ textAlign: "center" }}>
                    <div style={{ fontSize: "1.3rem", fontWeight: 800 }}>{selectedStudent.test_summary.total_tests}</div>
                    <div style={{ fontSize: ".75rem", color: "var(--muted)" }}>Tests taken</div>
                  </div>
                  <div style={{ textAlign: "center" }}>
                    <div style={{ fontSize: "1.3rem", fontWeight: 800, color: "#10b981" }}>{selectedStudent.test_summary.best_score}%</div>
                    <div style={{ fontSize: ".75rem", color: "var(--muted)" }}>Best score</div>
                  </div>
                  <div style={{ textAlign: "center" }}>
                    <div style={{ fontSize: "1.3rem", fontWeight: 800, color: "#6366f1" }}>{selectedStudent.test_summary.average_score}%</div>
                    <div style={{ fontSize: ".75rem", color: "var(--muted)" }}>Average</div>
                  </div>
                </div>
              )}
              {(selectedStudent.recent_tests || []).length === 0 ? (
                <p>No mock tests taken yet.</p>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {selectedStudent.recent_tests.map((test, i) => {
                    const pct = Number(test.percentage || 0);
                    const color = pct >= 80 ? "#10b981" : pct >= 50 ? "#f59e0b" : "#ef4444";
                    return (
                      <div key={i} style={{
                        display: "flex", alignItems: "center", justifyContent: "space-between",
                        padding: "8px 12px", background: "var(--surface2, #f8f9fa)",
                        borderRadius: 8, flexWrap: "wrap", gap: 6,
                      }}>
                        <div style={{ flex: 1 }}>
                          <strong style={{ fontSize: ".88rem" }}>{test.subject}</strong>
                          {test.chapter && <span style={{ color: "var(--muted)", fontSize: ".78rem", marginLeft: 6 }}>• {test.chapter}</span>}
                          <div style={{ fontSize: ".75rem", color: "var(--muted)", marginTop: 2 }}>
                            {test.exam_type || "Class Test"} · {test.difficulty || "Medium"}
                            {test.submitted_at && ` · ${String(test.submitted_at).slice(0, 10)}`}
                          </div>
                        </div>
                        <div style={{ textAlign: "right", fontWeight: 800, fontSize: "1rem", color }}>
                          {pct.toFixed(1)}%
                          <div style={{ fontSize: ".72rem", fontWeight: 400, color: "var(--muted)" }}>
                            {test.final_score ?? "—"}/{test.max_score ?? "—"}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          <div>
            <div className="premium-card" style={{ marginBottom: 18 }}>
              <h4>Add Teacher Note</h4>
              <form onSubmit={handleSaveNote} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                  <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: ".85rem", fontWeight: 600 }}>
                    Subject
                    <input value={noteForm.subject} onChange={(e) => setNoteForm((p) => ({ ...p, subject: e.target.value }))} placeholder="Science" style={{ marginTop: 0 }} />
                  </label>
                  <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: ".85rem", fontWeight: 600 }}>
                    Chapter
                    <input value={noteForm.chapter} onChange={(e) => setNoteForm((p) => ({ ...p, chapter: e.target.value }))} placeholder="Motion" style={{ marginTop: 0 }} />
                  </label>
                </div>
                <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: ".85rem", fontWeight: 600 }}>
                  Note
                  <textarea
                    value={noteForm.note}
                    onChange={(e) => setNoteForm((p) => ({ ...p, note: e.target.value }))}
                    placeholder="Add a follow-up, intervention, or parent update."
                    required
                    rows={4}
                    style={{ width: "100%", boxSizing: "border-box", resize: "vertical", fontFamily: "inherit", fontSize: ".88rem" }}
                  />
                </label>
                <button type="submit" className="primary-btn" disabled={savingNote} style={{ width: "100%", boxSizing: "border-box" }}>
                  {savingNote ? "Saving..." : "Save Note"}
                </button>
              </form>
            </div>
            <div className="premium-card">
              <h4>Recent Notes</h4>
              {(selectedStudent.notes || []).length === 0 ? <p>No notes yet.</p> : (
                selectedStudent.notes.map((note) => (
                  <div key={note.id || note.created_at} className="teacher-note-row">
                    <strong>{note.subject || "General"}{note.chapter ? ` • ${note.chapter}` : ""}</strong>
                    <p>{note.note}</p>
                    <small>{String(note.created_at || "").slice(0, 19)}</small>
                  </div>
                ))
              )}
            </div>
          </div>
        </section>
      )}

      {/* ── Add Student Modal ─────────────────────────────────────────────── */}
      {showAddStudent && (
        <div style={{
          position: "fixed", inset: 0, zIndex: 999,
          background: "rgba(0,0,0,.65)", display: "flex",
          alignItems: "center", justifyContent: "center", padding: 20,
        }}
          onClick={(e) => { if (e.target === e.currentTarget) setShowAddStudent(false); }}
        >
          <div style={{
            width: "100%", maxWidth: 480, background: "#1e293b",
            borderRadius: 16, padding: "32px 28px", color: "#f8fafc",
            boxShadow: "0 24px 80px rgba(0,0,0,.6)",
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
              <h3 style={{ margin: 0, fontSize: "1.15rem", fontWeight: 800 }}>
                <UserPlus size={18} style={{ marginRight: 8 }} />
                Add New Student
              </h3>
              <button onClick={() => setShowAddStudent(false)}
                style={{ background: "none", border: "none", color: "#94a3b8", fontSize: "1.4rem", cursor: "pointer" }}>
                ×
              </button>
            </div>

            <p style={{ fontSize: ".82rem", color: "#94a3b8", marginBottom: 18 }}>
              Plan: {studentLimit.count} / {studentLimit.max} students used
              {studentLimit.is_paid ? " (Paid)" : " (Free Tier — upgrade for 30 students)"}
            </p>

            {addStudentError && (
              <div style={{
                background: "rgba(239,68,68,.1)", border: "1px solid rgba(239,68,68,.3)",
                color: "#fca5a5", borderRadius: 9, padding: "10px 14px", fontSize: ".85rem", marginBottom: 14,
              }}>{addStudentError}</div>
            )}

            <form onSubmit={handleAddStudent} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              <label style={{ display: "block", fontSize: ".85rem", fontWeight: 600, color: "#cbd5e1", marginBottom: 4 }}>
                Student Name *
                <input
                  style={{ width: "100%", background: "#111827", border: "2px solid #1e293b", borderRadius: 10, padding: "11px 13px", color: "#f8fafc", fontFamily: "inherit", fontSize: ".92rem", outline: "none", marginTop: 5 }}
                  type="text" placeholder="Full name" required
                  value={studentForm.username}
                  onChange={(e) => setStudentForm((p) => ({ ...p, username: e.target.value }))}
                />
              </label>

              <label style={{ display: "block", fontSize: ".85rem", fontWeight: 600, color: "#cbd5e1", marginBottom: 4 }}>
                Grade *
                <select
                  style={{ width: "100%", background: "#111827", border: "2px solid #1e293b", borderRadius: 10, padding: "11px 13px", color: "#f8fafc", fontFamily: "inherit", fontSize: ".92rem", outline: "none", marginTop: 5 }}
                  required value={studentForm.grade}
                  onChange={(e) => setStudentForm((p) => ({ ...p, grade: e.target.value }))}
                >
                  {GRADES.map((g) => <option key={g} value={g}>{g}</option>)}
                </select>
              </label>

              <label style={{ display: "block", fontSize: ".85rem", fontWeight: 600, color: "#cbd5e1", marginBottom: 4 }}>
                Email <span style={{ color: "#64748b", fontWeight: 400 }}>(optional)</span>
                <input
                  style={{ width: "100%", background: "#111827", border: "2px solid #1e293b", borderRadius: 10, padding: "11px 13px", color: "#f8fafc", fontFamily: "inherit", fontSize: ".92rem", outline: "none", marginTop: 5 }}
                  type="email" placeholder="student@example.com"
                  value={studentForm.email}
                  onChange={(e) => setStudentForm((p) => ({ ...p, email: e.target.value }))}
                />
                <small style={{ color: "#64748b", fontSize: ".75rem" }}>
                  Required for "Email Login" feature. If skipped, student logs in with username + password.
                </small>
              </label>

              <label style={{ display: "block", fontSize: ".85rem", fontWeight: 600, color: "#cbd5e1", marginBottom: 4 }}>
                Temporary Password *
                <div style={{ position: "relative", marginTop: 5 }}>
                  <input
                    style={{ width: "100%", background: "#111827", border: "2px solid #1e293b", borderRadius: 10, padding: "11px 40px 11px 13px", color: "#f8fafc", fontFamily: "inherit", fontSize: ".92rem", outline: "none" }}
                    type={showPassword ? "text" : "password"}
                    placeholder="Min 6 characters" required minLength={6}
                    value={studentForm.password}
                    onChange={(e) => setStudentForm((p) => ({ ...p, password: e.target.value }))}
                  />
                  <button type="button"
                    onClick={() => setShowPassword((p) => !p)}
                    style={{ position: "absolute", right: 10, top: "50%", transform: "translateY(-50%)", background: "none", border: "none", cursor: "pointer", color: "#64748b", fontSize: "1.1rem", padding: 0 }}>
                    {showPassword ? "🙈" : "👁️"}
                  </button>
                </div>
                <small style={{ color: "#64748b", fontSize: ".75rem" }}>
                  Share this with the student. Password is hashed immediately — never stored in plain text.
                </small>
              </label>

              <label style={{ display: "block", fontSize: ".85rem", fontWeight: 600, color: "#cbd5e1", marginBottom: 4 }}>
                Subject <span style={{ color: "#64748b", fontWeight: 400 }}>(optional)</span>
                <input
                  style={{ width: "100%", background: "#111827", border: "2px solid #1e293b", borderRadius: 10, padding: "11px 13px", color: "#f8fafc", fontFamily: "inherit", fontSize: ".92rem", outline: "none", marginTop: 5 }}
                  type="text" placeholder="Science"
                  value={studentForm.subject}
                  onChange={(e) => setStudentForm((p) => ({ ...p, subject: e.target.value }))}
                />
              </label>

              <button
                type="submit"
                style={{
                  width: "100%", padding: "13px", borderRadius: 10, border: "none",
                  background: "linear-gradient(135deg,#2563eb,#7c3aed)", color: "#fff",
                  fontSize: ".95rem", fontWeight: 700, cursor: "pointer", fontFamily: "inherit",
                  opacity: addingStudent ? 0.7 : 1,
                }}
                disabled={addingStudent}
              >
                {addingStudent ? "Creating student…" : "Create Student & Assign"}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default TeacherDashboardPage;
