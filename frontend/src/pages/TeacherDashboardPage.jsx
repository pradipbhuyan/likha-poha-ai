import { useEffect, useMemo, useState } from "react";
import { BookOpen, ClipboardEdit, GraduationCap, Users } from "lucide-react";

import {
  createTeacherNote,
  getTeacherDashboardSummary,
} from "../api/teacherDashboard";

function TeacherDashboardPage({ user }) {
  /** Teacher workspace for assigned students, learning progress, usage, and notes. */
  const [summary, setSummary] = useState(null);
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [savingNote, setSavingNote] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [selectedGrade, setSelectedGrade] = useState("all");
  const [selectedSubject, setSelectedSubject] = useState("all");
  const [selectedStudentId, setSelectedStudentId] = useState("");
  const [noteForm, setNoteForm] = useState({
    subject: "",
    chapter: "",
    note: "",
  });

  async function loadDashboard() {
    /** Refresh teacher-scoped dashboard data from the backend. */
    setLoading(true);
    setError("");

    try {
      const data = await getTeacherDashboardSummary();
      setSummary(data.summary || {});
      setStudents(data.students || []);

      setSelectedStudentId((current) => {
        if (current && (data.students || []).some((item) => item.profile.id === current)) {
          return current;
        }

        return data.students?.[0]?.profile?.id || "";
      });
    } catch (err) {
      console.error(err);
      setError(err.message || "Unable to load teacher dashboard.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadDashboard();
  }, []);

  const gradeOptions = summary?.active_grades || [];
  const subjectOptions = summary?.subjects || [];

  const filteredStudents = useMemo(() => {
    /** Apply grade and subject filters without mutating the loaded roster. */
    return students.filter((student) => {
      const assignments = student.assignments || [];

      const gradeMatch =
        selectedGrade === "all" ||
        assignments.some((assignment) => assignment.grade === selectedGrade);
      const subjectMatch =
        selectedSubject === "all" ||
        assignments.some((assignment) => assignment.subject === selectedSubject);

      return gradeMatch && subjectMatch;
    });
  }, [students, selectedGrade, selectedSubject]);

  const selectedStudent =
    students.find((student) => student.profile.id === selectedStudentId) ||
    filteredStudents[0] ||
    null;

  async function handleSaveNote(e) {
    /** Persist a note against the selected assigned student. */
    e.preventDefault();
    setMessage("");
    setError("");

    if (!selectedStudent) {
      setError("Select a student before saving a note.");
      return;
    }

    setSavingNote(true);

    try {
      await createTeacherNote({
        student_id: selectedStudent.profile.id,
        subject: noteForm.subject,
        chapter: noteForm.chapter,
        note: noteForm.note,
      });

      setNoteForm({
        subject: "",
        chapter: "",
        note: "",
      });
      await loadDashboard();
      setMessage("Teacher note saved.");
    } catch (err) {
      console.error(err);
      setError(err.message || "Unable to save note.");
    } finally {
      setSavingNote(false);
    }
  }

  if (loading) {
    return <p>Loading teacher dashboard...</p>;
  }

  const totalTokens = students.reduce(
    (sum, student) => sum + Number(student.activity?.tokens_total || 0),
    0
  );
  const completedChapters = students.reduce(
    (sum, student) =>
      sum + Number(student.progress_summary?.completed_chapters || 0),
    0
  );

  return (
    <div className="premium-page teacher-dashboard-page">
      <section className="premium-section">
        <div className="premium-header">
          <p className="eyebrow">Teacher Workspace</p>
          <h2>{user?.username || "Teacher"} Dashboard</h2>
          <p>
            Track assigned students across school classrooms or independent
            tutoring groups from one focused view.
          </p>
        </div>
      </section>

      {message && <div className="info-box">{message}</div>}
      {error && <div className="error-box">{error}</div>}

      <section className="premium-grid premium-grid-4 premium-parent-stats">
        <div className="premium-card">
          <div className="dashboard-stat-icon blue">
            <Users size={22} />
          </div>
          <h3>{summary?.assigned_students || 0}</h3>
          <p>Assigned Students</p>
        </div>

        <div className="premium-card">
          <div className="dashboard-stat-icon green">
            <GraduationCap size={22} />
          </div>
          <h3>{gradeOptions.length}</h3>
          <p>Active Grades</p>
        </div>

        <div className="premium-card">
          <div className="dashboard-stat-icon purple">
            <BookOpen size={22} />
          </div>
          <h3>{completedChapters}</h3>
          <p>Completed Chapters</p>
        </div>

        <div className="premium-card">
          <div className="dashboard-stat-icon red">
            <ClipboardEdit size={22} />
          </div>
          <h3>{totalTokens}</h3>
          <p>Total AI Tokens</p>
        </div>
      </section>

      <section className="premium-section">
        <div className="premium-header">
          <h3>Assigned Roster</h3>
          <p>Filter by grade or subject to focus on one class group.</p>
        </div>

        <div className="form-grid premium-rag-form-grid">
          <label>
            Grade
            <select
              value={selectedGrade}
              onChange={(e) => setSelectedGrade(e.target.value)}
            >
              <option value="all">All grades</option>
              {gradeOptions.map((grade) => (
                <option key={grade} value={grade}>
                  {grade}
                </option>
              ))}
            </select>
          </label>

          <label>
            Subject
            <select
              value={selectedSubject}
              onChange={(e) => setSelectedSubject(e.target.value)}
            >
              <option value="all">All subjects</option>
              {subjectOptions.map((subject) => (
                <option key={subject} value={subject}>
                  {subject}
                </option>
              ))}
            </select>
          </label>
        </div>

        {filteredStudents.length === 0 ? (
          <div className="info-box">
            No students match this filter. Ask an admin to assign students to
            this teacher account.
          </div>
        ) : (
          <div className="teacher-roster-grid">
            {filteredStudents.map((student) => {
              const profile = student.profile;
              const assignments = student.assignments || [];
              const activity = student.activity || {};
              const progressSummary = student.progress_summary || {};

              return (
                <button
                  key={profile.id}
                  className={
                    selectedStudent?.profile?.id === profile.id
                      ? "teacher-student-card active"
                      : "teacher-student-card"
                  }
                  onClick={() => setSelectedStudentId(profile.id)}
                >
                  <strong>{profile.username}</strong>
                  <span>{profile.grade || assignments[0]?.grade || "Grade 9"}</span>
                  <small>
                    {assignments
                      .map((assignment) => assignment.subject)
                      .filter(Boolean)
                      .join(", ") || "General"}
                  </small>
                  <div>
                    <span>{progressSummary.completed_chapters || 0} complete</span>
                    <span>{activity.requests_total || 0} AI requests</span>
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </section>

      {selectedStudent && (
        <section className="premium-section teacher-detail-grid">
          <div>
            <div className="premium-header">
              <h3>{selectedStudent.profile.username}</h3>
              <p>{selectedStudent.profile.email}</p>
            </div>

            <div className="premium-card" style={{ marginBottom: 18 }}>
              <h4>Assignments</h4>
              {(selectedStudent.assignments || []).map((assignment) => (
                <p key={assignment.id || `${assignment.subject}-${assignment.grade}`}>
                  {assignment.grade || "Grade 9"} •{" "}
                  {assignment.subject || "General"}
                  {assignment.section ? ` • ${assignment.section}` : ""}
                </p>
              ))}
            </div>

            <div className="premium-card">
              <h4>Recent Progress</h4>
              {(selectedStudent.recent_progress || []).length === 0 ? (
                <p>No chapter progress recorded yet.</p>
              ) : (
                selectedStudent.recent_progress.map((progress) => (
                  <div
                    key={`${progress.subject}-${progress.chapter}-${progress.updated_at}`}
                    className="teacher-progress-row"
                  >
                    <strong>{progress.chapter}</strong>
                    <span>
                      {progress.subject} • Step{" "}
                      {Number(progress.current_step_index || 0) + 1}
                      {progress.completed ? " • Completed" : ""}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>

          <div>
            <div className="premium-card" style={{ marginBottom: 18 }}>
              <h4>Add Teacher Note</h4>
              <form onSubmit={handleSaveNote} className="form-grid">
                <label>
                  Subject
                  <input
                    value={noteForm.subject}
                    onChange={(e) =>
                      setNoteForm((prev) => ({
                        ...prev,
                        subject: e.target.value,
                      }))
                    }
                    placeholder="Science"
                  />
                </label>

                <label>
                  Chapter
                  <input
                    value={noteForm.chapter}
                    onChange={(e) =>
                      setNoteForm((prev) => ({
                        ...prev,
                        chapter: e.target.value,
                      }))
                    }
                    placeholder="Motion"
                  />
                </label>

                <label>
                  Note
                  <textarea
                    value={noteForm.note}
                    onChange={(e) =>
                      setNoteForm((prev) => ({
                        ...prev,
                        note: e.target.value,
                      }))
                    }
                    placeholder="Add a follow-up, intervention, or parent update."
                    required
                  />
                </label>

                <button
                  type="submit"
                  className="primary-btn"
                  disabled={savingNote}
                >
                  {savingNote ? "Saving..." : "Save Note"}
                </button>
              </form>
            </div>

            <div className="premium-card">
              <h4>Recent Notes</h4>
              {(selectedStudent.notes || []).length === 0 ? (
                <p>No notes yet.</p>
              ) : (
                selectedStudent.notes.map((note) => (
                  <div key={note.id || note.created_at} className="teacher-note-row">
                    <strong>
                      {note.subject || "General"}
                      {note.chapter ? ` • ${note.chapter}` : ""}
                    </strong>
                    <p>{note.note}</p>
                    <small>{String(note.created_at || "").slice(0, 19)}</small>
                  </div>
                ))
              )}
            </div>
          </div>
        </section>
      )}
    </div>
  );
}

export default TeacherDashboardPage;
