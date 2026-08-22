/**
 * StudentWorkspace.jsx — Multi-section student detail workspace
 * ─────────────────────────────────────────────────────────────────────────────
 * Replaces the inline student detail drawer with a full-featured workspace.
 * Sections: Overview | Progress | Assessments | Notes | Activity | Parent | Settings
 *
 * Props: student (basic), onClose, isPaid
 * Safety: notes are private, parent email not exposed, no secrets displayed
 */
import { useCallback, useEffect, useState } from "react";
import {
  User, TrendingUp, ClipboardList, NotebookPen, Clock, Users, Settings,
  X, BarChart3, Zap, KeyRound, Mail, CheckCircle2, AlertTriangle, Lock,
  MessageCircle, Save, Trash2,
} from "lucide-react";
import {
  getTeacherStudentDetail,
  getStudentTimeline,
  listStudentNotes,
  createStudentNote,
  updateStudentNote,
  deleteStudentNote,
  getParentContact,
  messageParent,
  resetTeacherStudentPassword,
  emailTeacherStudentCredentials,
  updateTeacherStudent,
  archiveTeacherStudent,
} from "../../api/teacherDashboard";

const SECTIONS = [
  { key: "overview",     label: "Overview",     Icon: User },
  { key: "progress",     label: "Progress",     Icon: TrendingUp },
  { key: "assessments",  label: "Assessments",  Icon: ClipboardList },
  { key: "notes",        label: "Notes",        Icon: NotebookPen },
  { key: "activity",     label: "Activity",     Icon: Clock },
  { key: "parent",       label: "Parent",       Icon: Users },
  { key: "settings",     label: "Settings",     Icon: Settings },
];

const card = { background: "var(--panel,#fff)", border: "1px solid var(--border,#e5e7eb)", borderRadius: 10, padding: "14px 16px", marginBottom: 12 };
const inp  = { padding: "8px 10px", borderRadius: 7, border: "1px solid var(--border,#e5e7eb)", fontFamily: "inherit", fontSize: ".85rem", background: "var(--surface2,#f8fafc)", color: "var(--text,#1e293b)", width: "100%" };
const NA   = () => <div style={{ color: "#94a3b8", fontSize: ".78rem", padding: "8px 0" }}>Not available yet.</div>;

export default function StudentWorkspace({ student, onClose, isPaid }) {
  const [activeSection, setSection] = useState("overview");
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!student?.id) return;
    setLoading(true);
    getTeacherStudentDetail(student.id)
      .then(d => { setDetail(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, [student?.id]);

  if (!student) return null;

  const width = Math.min(680, window.innerWidth);

  return (
    <>
    <div
      aria-hidden="true"
      onClick={onClose}
      style={{ position: "fixed", inset: 0, background: "rgba(15,23,42,.36)", zIndex: 2199 }}
    />
    <div
      data-testid="student-workspace"
      role="dialog"
      aria-modal="true"
      aria-label={`${student.username || "Student"} workspace`}
      style={{ position: "fixed", top: 0, right: 0, width, maxWidth: "100vw", height: "100dvh", boxSizing: "border-box", background: "var(--panel,#fff)", boxShadow: "-4px 0 32px rgba(0,0,0,.22)", zIndex: 2200, display: "flex", flexDirection: "column", overflow: "hidden" }}>

      {/* ── Header ─────────────────────────────────────────────────────── */}
      <div style={{ padding: "14px 16px 0", borderBottom: "1px solid var(--border,#e5e7eb)", background: "var(--panel,#fff)", flexShrink: 0 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
          <div>
            <h3 style={{ margin: 0, fontSize: "1rem" }} data-testid="workspace-student-name">{student.username}</h3>
            <span style={{ fontSize: ".75rem", color: "#64748b" }}>{student.grade || "—"} · {student.email || "No email"}</span>
          </div>
          <button aria-label="Close student workspace" onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", padding: "4px 8px", display: "flex", alignItems: "center" }}><X size={19}/></button>
        </div>
        {/* Section tabs */}
        <div style={{ display: "flex", gap: 2, overflowX: "auto", paddingBottom: 0, WebkitOverflowScrolling: "touch" }}>
          {SECTIONS.map(s => (
            <button key={s.key}
              onClick={() => setSection(s.key)}
              data-testid={`ws-tab-${s.key}`}
              style={{
                padding: "6px 10px", border: "none", background: "none", cursor: "pointer",
                fontFamily: "inherit", fontSize: ".78rem", fontWeight: activeSection === s.key ? 700 : 400,
                color: activeSection === s.key ? "#6366f1" : "#64748b",
                borderBottom: activeSection === s.key ? "2px solid #6366f1" : "2px solid transparent",
                whiteSpace: "nowrap", marginBottom: -1,
              }}>
              <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}><s.Icon size={13}/>{s.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* ── Body ───────────────────────────────────────────────────────── */}
      <div style={{ flex: 1, overflowY: "auto", padding: 16 }}>
        {loading && <div style={{ color: "#94a3b8", padding: 20 }}>Loading student details…</div>}
        {!loading && (
          <>
            {activeSection === "overview"    && <WSOverview    student={student} detail={detail} isPaid={isPaid} />}
            {activeSection === "progress"    && <WSProgress    detail={detail} />}
            {activeSection === "assessments" && <WSAssessments detail={detail} />}
            {activeSection === "notes"       && <WSNotes       studentId={student.id} />}
            {activeSection === "activity"    && <WSActivity    studentId={student.id} />}
            {activeSection === "parent"      && <WSParent      studentId={student.id} isPaid={isPaid} />}
            {activeSection === "settings"    && <WSSettings    student={student} detail={detail} isPaid={isPaid} onClose={onClose} />}
          </>
        )}
      </div>
    </div>
    </>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Section: Overview
// ─────────────────────────────────────────────────────────────────────────────
function WSOverview({ student, detail, isPaid }) {
  const [pwResult, setPwResult] = useState(null);
  const [msg, setMsg] = useState(null);

  const learning = detail?.learning || {};
  const classrooms = detail?.classrooms || [];

  async function doReset() {
    if (!window.confirm("Reset temp password? Shown once only.")) return;
    const d = await resetTeacherStudentPassword(student.id).catch(e => ({ success: false, error: e.message }));
    setPwResult(d);
  }

  async function doEmail() {
    const d = await emailTeacherStudentCredentials(student.id).catch(e => ({ success: false, error: e.message }));
    setMsg(d.invite_sent ? { ok: true, text: "Credentials emailed." } : { ok: false, text: d.error || "Could not send." });
  }

  return (
    <div data-testid="ws-overview">
      {/* Info cards */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 12 }}>
        {[
          ["Status", student.account_status || "active"],
          ["Grade", student.grade || "—"],
          ["Plan", detail?.student?.subscription_plan || "free"],
          ["Last Active", learning.last_active ? new Date(learning.last_active).toLocaleDateString() : "Unknown"],
        ].map(([k, v]) => (
          <div key={k} style={{ background: "var(--surface2,#f8fafc)", border: "1px solid var(--border,#e5e7eb)", borderRadius: 8, padding: "8px 12px", minWidth: 80 }}>
            <div style={{ fontSize: ".68rem", color: "#64748b" }}>{k}</div>
            <div style={{ fontSize: ".82rem", fontWeight: 700 }}>{v}</div>
          </div>
        ))}
      </div>

      {/* Learning stats */}
      <div style={card}>
        <div style={{ fontWeight: 700, marginBottom: 8, display: "flex", alignItems: "center", gap: 6 }}><BarChart3 size={15}/>Learning</div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          {[["Lessons", learning.lessons_generated ?? 0], ["Doubts", learning.doubts_asked ?? 0], ["Mock Tests", learning.mock_tests_completed ?? 0], ["Avg Score", learning.mock_test_avg != null ? learning.mock_test_avg + "%" : "—"]].map(([k, v]) => (
            <div key={k} style={{ background: "var(--surface2,#f8fafc)", border: "1px solid var(--border,#e5e7eb)", borderRadius: 7, padding: "6px 10px", textAlign: "center", minWidth: 64 }}>
              <div style={{ fontWeight: 700 }}>{v}</div>
              <div style={{ fontSize: ".65rem", color: "#64748b" }}>{k}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Classrooms */}
      {classrooms.length > 0 && (
        <div style={{ marginBottom: 12 }}>
          <span style={{ fontSize: ".8rem", fontWeight: 600 }}>Classrooms: </span>
          {classrooms.map(c => <span key={c.id} style={{ marginRight: 6, fontSize: ".78rem", background: "rgba(99,102,241,.1)", color: "#6366f1", padding: "2px 7px", borderRadius: 5 }}>{c.name}</span>)}
        </div>
      )}

      {/* Quick actions */}
      <div style={card}>
        <div style={{ fontWeight: 700, marginBottom: 8, display: "flex", alignItems: "center", gap: 6 }}><Zap size={15}/>Quick Actions</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <button onClick={doReset} className="secondary-btn" style={{ display: "inline-flex", alignItems: "center", gap: 6 }}><KeyRound size={14}/>Reset Password</button>
          {isPaid
            ? <button onClick={doEmail} className="secondary-btn" style={{ display: "inline-flex", alignItems: "center", gap: 6 }}><Mail size={14}/>Email Login Details</button>
            : <button disabled title="Upgrade to paid plan" style={{ opacity: .5, cursor: "not-allowed", display: "inline-flex", alignItems: "center", gap: 6 }} className="secondary-btn"><Mail size={14}/>Email Login Details (Paid only)</button>
          }
        </div>
        {msg && <div style={{ marginTop: 6, fontSize: ".82rem", color: msg.ok ? "#166534" : "#dc2626", display: "flex", alignItems: "center", gap: 5 }}>{msg.ok ? <CheckCircle2 size={14}/> : <AlertTriangle size={14}/>}{msg.text}</div>}
        {pwResult?.success && (
          <div style={{ marginTop: 8, padding: "8px 12px", background: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: 7, fontSize: ".82rem", display: "flex", alignItems: "center", gap: 5, flexWrap: "wrap" }}>
            <KeyRound size={14}/>Temp password: <code style={{ color: "#f59e0b", fontWeight: 700 }}>{pwResult.temp_password}</code>
            <small style={{ display: "block", color: "#64748b", width: "100%" }}>{pwResult.warning}</small>
          </div>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Section: Progress
// ─────────────────────────────────────────────────────────────────────────────
function WSProgress({ detail }) {
  const learning = detail?.learning || {};
  const hasData = learning.lessons_generated > 0 || learning.doubts_asked > 0;
  return (
    <div data-testid="ws-progress">
      <h4 style={{ margin: "0 0 10px", display: "flex", alignItems: "center", gap: 6 }}><TrendingUp size={16}/>Learning Progress</h4>
      {!hasData ? <NA /> : (
        <>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 12 }}>
            {[["Lessons", learning.lessons_generated], ["Doubts", learning.doubts_asked]].map(([k, v]) => (
              <div key={k} style={{ background: "var(--surface2,#f8fafc)", border: "1px solid var(--border,#e5e7eb)", borderRadius: 8, padding: "10px 14px", textAlign: "center", flex: "1 1 80px" }}>
                <div style={{ fontSize: "1.4rem", fontWeight: 800, color: "#6366f1" }}>{v ?? 0}</div>
                <div style={{ fontSize: ".72rem", color: "#64748b" }}>{k}</div>
              </div>
            ))}
          </div>
          <div style={card}>
            <div style={{ fontWeight: 700, marginBottom: 6 }}>Recent Activity</div>
            {(learning.recent_activity || []).length === 0
              ? <NA />
              : (learning.recent_activity || []).slice(0, 5).map((a, i) => (
                  <div key={i} style={{ display: "flex", gap: 8, padding: "4px 0", borderBottom: "1px solid var(--border,#f1f5f9)", fontSize: ".78rem" }}>
                    <span style={{ color: "#94a3b8", minWidth: 70 }}>{(a.created_at || "").slice(0, 10)}</span>
                    <span>{a.feature || "activity"}</span>
                  </div>
                ))
            }
          </div>
        </>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Section: Assessments
// ─────────────────────────────────────────────────────────────────────────────
function WSAssessments({ detail }) {
  const learning = detail?.learning || {};
  const hasTests = learning.mock_tests_completed > 0;
  return (
    <div data-testid="ws-assessments">
      <h4 style={{ margin: "0 0 10px", display: "flex", alignItems: "center", gap: 6 }}><ClipboardList size={16}/>Assessments</h4>
      {!hasTests ? <NA /> : (
        <>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 12 }}>
            {[
              ["Tests Done", learning.mock_tests_completed],
              ["Avg Score", learning.mock_test_avg != null ? learning.mock_test_avg + "%" : "—"],
            ].map(([k, v]) => (
              <div key={k} style={{ background: "var(--surface2,#f8fafc)", border: "1px solid var(--border,#e5e7eb)", borderRadius: 8, padding: "10px 14px", textAlign: "center", flex: "1 1 80px" }}>
                <div style={{ fontSize: "1.4rem", fontWeight: 800, color: "#0ea5e9" }}>{v ?? 0}</div>
                <div style={{ fontSize: ".72rem", color: "#64748b" }}>{k}</div>
              </div>
            ))}
          </div>
          <div style={card}>
            <div style={{ fontWeight: 700, marginBottom: 6 }}>Recent Mock Tests</div>
            {(learning.recent_tests || []).map((test, index) => (
              <div key={`${test.submitted_at || "test"}-${index}`} style={{ display: "flex", justifyContent: "space-between", gap: 10, padding: "7px 0", borderBottom: "1px solid var(--border,#f1f5f9)", fontSize: ".78rem" }}>
                <div>
                  <div style={{ fontWeight: 600 }}>{test.subject || "Mock Test"}</div>
                  <div style={{ color: "#94a3b8" }}>{test.chapter || ""}{test.submitted_at ? ` · ${test.submitted_at.slice(0, 10)}` : ""}</div>
                </div>
                <strong style={{ color: "#0ea5e9" }}>{test.score != null ? `${test.score}%` : "—"}</strong>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Section: Notes (private teacher notes)
// ─────────────────────────────────────────────────────────────────────────────
function WSNotes({ studentId }) {
  const [notes, setNotes]     = useState([]);
  const [loading, setLoading] = useState(true);
  const [text, setText]       = useState("");
  const [editId, setEditId]   = useState(null);
  const [editText, setEditText] = useState("");
  const [msg, setMsg]         = useState(null);

  const loadNotes = useCallback(async () => {
    setLoading(true);
    const d = await listStudentNotes(studentId).catch(() => null);
    setNotes(d?.notes || []);
    setLoading(false);
  }, [studentId]);

  useEffect(() => { loadNotes(); }, [loadNotes]);

  async function doAdd(e) {
    e.preventDefault();
    if (!text.trim()) return;
    await createStudentNote(studentId, text.trim());
    setText(""); setMsg({ ok: true, text: "Note added." }); loadNotes();
  }

  async function doEdit(noteId) {
    await updateStudentNote(studentId, noteId, editText.trim());
    setEditId(null); setMsg({ ok: true, text: "Note updated." }); loadNotes();
  }

  async function doDelete(noteId) {
    if (!window.confirm("Delete this note?")) return;
    await deleteStudentNote(studentId, noteId);
    setMsg({ ok: false, text: "Note deleted." }); loadNotes();
  }

  return (
    <div data-testid="ws-notes">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
        <h4 style={{ margin: 0, display: "flex", alignItems: "center", gap: 6 }}><NotebookPen size={16}/>Private Teacher Notes</h4>
        <span style={{ fontSize: ".7rem", background: "rgba(99,102,241,.08)", color: "#6366f1", padding: "2px 7px", borderRadius: 4, fontWeight: 600, display: "inline-flex", alignItems: "center", gap: 3 }}><Lock size={11}/>Visible to you only</span>
      </div>
      <form onSubmit={doAdd} style={{ display: "flex", gap: 6, marginBottom: 12 }}>
        <input value={text} onChange={e => setText(e.target.value)} placeholder="Add a private note…" style={{ ...inp, flex: 1 }} data-testid="note-input" />
        <button type="submit" className="primary-btn" style={{ whiteSpace: "nowrap" }}>Add</button>
      </form>
      {msg && <div style={{ marginBottom: 8, fontSize: ".82rem", color: msg.ok ? "#166534" : "#64748b" }}>{msg.text}</div>}
      {loading && <div style={{ color: "#94a3b8" }}>Loading notes…</div>}
      {!loading && notes.length === 0 && <div style={{ color: "#94a3b8", fontSize: ".85rem" }}>No notes yet. Add your first note above.</div>}
      {notes.map(n => (
        <div key={n.id} style={{ ...card, marginBottom: 8 }}>
          {editId === n.id ? (
            <div style={{ display: "flex", gap: 6 }}>
              <input value={editText} onChange={e => setEditText(e.target.value)} style={{ ...inp, flex: 1 }} />
              <button onClick={() => doEdit(n.id)} className="primary-btn">Save</button>
              <button onClick={() => setEditId(null)} className="secondary-btn">Cancel</button>
            </div>
          ) : (
            <div style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "flex-start" }}>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: ".85rem" }}>{n.note}</div>
                <div style={{ fontSize: ".7rem", color: "#94a3b8", marginTop: 3 }}>{new Date(n.created_at).toLocaleString()}</div>
              </div>
              <div style={{ display: "flex", gap: 4 }}>
                <button onClick={() => { setEditId(n.id); setEditText(n.note); }} style={{ background: "none", border: "none", cursor: "pointer", fontSize: ".78rem", color: "#6366f1" }}>Edit</button>
                <button onClick={() => doDelete(n.id)} style={{ background: "none", border: "none", cursor: "pointer", fontSize: ".78rem", color: "#dc2626" }}>Delete</button>
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Section: Activity (Timeline)
// ─────────────────────────────────────────────────────────────────────────────
function WSActivity({ studentId }) {
  const [events, setEvents]   = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);

  useEffect(() => {
    getStudentTimeline(studentId)
      .then(d => { setEvents(d?.events || []); setLoading(false); })
      .catch(e => { setError(e.message || "Failed to load timeline."); setLoading(false); });
  }, [studentId]);

  const CAT_COLOR = { success: "#166534", warning: "#92400e", alert: "#dc2626", info: "#64748b" };

  return (
    <div data-testid="ws-activity">
      <h4 style={{ margin: "0 0 10px", display: "flex", alignItems: "center", gap: 6 }}><Clock size={16}/>Activity Timeline</h4>
      {loading && <div style={{ color: "#94a3b8" }}>Loading timeline…</div>}
      {error && <div style={{ color: "#dc2626", fontSize: ".82rem", display: "flex", alignItems: "center", gap: 5 }}><AlertTriangle size={14}/>{error}</div>}
      {!loading && !error && events.length === 0 && <div style={{ color: "#94a3b8", fontSize: ".85rem" }}>No activity recorded yet.</div>}
      <div style={{ position: "relative" }}>
        {events.map((ev, i) => (
          <div key={ev.id || i} style={{ display: "flex", gap: 10, marginBottom: 10 }}>
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
              <div style={{ width: 10, height: 10, borderRadius: "50%", background: CAT_COLOR[ev.category] || "#94a3b8", flexShrink: 0, marginTop: 4 }} />
              {i < events.length - 1 && <div style={{ width: 2, flex: 1, background: "var(--border,#e5e7eb)", marginTop: 3 }} />}
            </div>
            <div style={{ flex: 1, paddingBottom: 6 }}>
              <div style={{ fontSize: ".82rem", fontWeight: 600 }}>{ev.title}</div>
              <div style={{ fontSize: ".75rem", color: "#64748b" }}>{ev.description}</div>
              <div style={{ fontSize: ".7rem", color: "#94a3b8", marginTop: 2 }}>{ev.timestamp ? new Date(ev.timestamp).toLocaleString() : "—"}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Section: Parent
// ─────────────────────────────────────────────────────────────────────────────
function WSParent({ studentId, isPaid: _isPaid }) {
  const [parentData, setParentData] = useState(null);
  const [loading, setLoading]       = useState(true);
  const [showModal, setShowModal]   = useState(false);
  const [subject, setSubject]       = useState("");
  const [msgBody, setMsgBody]       = useState("");
  const [sendResult, setSendResult] = useState(null);

  useEffect(() => {
    getParentContact(studentId)
      .then(d => { setParentData(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, [studentId]);

  async function doSend(e) {
    e.preventDefault();
    const d = await messageParent(studentId, { subject, message: msgBody }).catch(e => ({ success: false, error: e.message }));
    setSendResult(d);
    if (d.success) { setSubject(""); setMsgBody(""); }
  }

  if (loading) return <div style={{ color: "#94a3b8" }}>Loading parent info…</div>;

  return (
    <div data-testid="ws-parent">
      <h4 style={{ margin: "0 0 10px", display: "flex", alignItems: "center", gap: 6 }}><Users size={16}/>Parent Contact</h4>
      {!parentData?.has_parent ? (
        <div style={{ ...card, color: "#64748b", fontSize: ".85rem" }}>
          No parent linked to this student.
        </div>
      ) : (
        <div style={card}>
          <div style={{ fontSize: ".85rem", marginBottom: 8 }}>
            <strong>{parentData.parent?.username || "Parent"}</strong>
            <span style={{ marginLeft: 8, fontSize: ".75rem", color: "#64748b", display: "inline-flex", alignItems: "center", gap: 3 }}>
              {parentData.parent?.has_email ? <><CheckCircle2 size={12}/>Can be messaged</> : <><X size={12}/>No email address</>}
            </span>
          </div>
          {parentData.parent?.has_email && (
            <button onClick={() => setShowModal(true)} className="secondary-btn" style={{ display: "inline-flex", alignItems: "center", gap: 6 }}><MessageCircle size={14}/>Message Parent</button>
          )}
        </div>
      )}

      {/* Message modal */}
      {showModal && (
        <div style={{ ...card, borderColor: "#6366f1" }}>
          <h5 style={{ margin: "0 0 8px", display: "flex", alignItems: "center", gap: 6 }}><MessageCircle size={14}/>Send Message to Parent</h5>
          <form onSubmit={doSend} style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <input value={subject} onChange={e => setSubject(e.target.value)} placeholder="Subject" required style={{ ...inp }} />
            <textarea value={msgBody} onChange={e => setMsgBody(e.target.value)} placeholder="Message…" required rows={4} style={{ ...inp, resize: "vertical" }} />
            <div style={{ display: "flex", gap: 8 }}>
              <button type="submit" className="primary-btn">Send</button>
              <button type="button" onClick={() => setShowModal(false)} className="secondary-btn">Cancel</button>
            </div>
          </form>
          {sendResult && (
            <div style={{ marginTop: 8, fontSize: ".82rem", color: sendResult.status === "sent" ? "#166534" : "#dc2626", display: "flex", alignItems: "center", gap: 5 }}>
              {sendResult.note || (sendResult.success ? <><CheckCircle2 size={14}/>Sent</> : <><AlertTriangle size={14}/>Failed</>)}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Section: Settings
// ─────────────────────────────────────────────────────────────────────────────
const GRADE_OPTIONS = Array.from({ length: 12 }, (_, i) => `Grade ${i + 1}`);

function WSSettings({ student, detail: _detail, isPaid, onClose }) {
  const [form, setForm] = useState({ username: student.username || "", grade: student.grade || "Grade 9", email: student.email || "" });
  const [pwResult, setPwResult] = useState(null);
  const [msg, setMsg] = useState(null);

  async function doSave(e) {
    e.preventDefault();
    const d = await updateTeacherStudent(student.id, form).catch(e => ({ success: false, error: e.message }));
    setMsg(d.success ? { ok: true, text: "Saved." } : { ok: false, text: d.error });
  }

  async function doReset() {
    if (!window.confirm("Reset temp password? Shown once only.")) return;
    const d = await resetTeacherStudentPassword(student.id).catch(e => ({ success: false, error: e.message }));
    setPwResult(d);
  }

  async function doArchive() {
    if (!window.confirm("Archive " + student.username + "? They will be removed from your roster.")) return;
    await archiveTeacherStudent(student.id);
    onClose();
  }

  return (
    <div data-testid="ws-settings">
      <h4 style={{ margin: "0 0 10px", display: "flex", alignItems: "center", gap: 6 }}><Settings size={16}/>Settings</h4>
      <form onSubmit={doSave} style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 16 }}>
        <label>
          <span style={{ fontSize: ".78rem", fontWeight: 600 }}>Name</span>
          <input value={form.username} onChange={e => setForm(p => ({ ...p, username: e.target.value }))} style={{ ...inp, marginTop: 2 }} />
        </label>
        <label>
          <span style={{ fontSize: ".78rem", fontWeight: 600 }}>Grade</span>
          <select value={form.grade} onChange={e => setForm(p => ({ ...p, grade: e.target.value }))} style={{ ...inp, marginTop: 2 }}>
            {GRADE_OPTIONS.map(g => <option key={g} value={g}>{g}</option>)}
          </select>
        </label>
        <label>
          <span style={{ fontSize: ".78rem", fontWeight: 600 }}>Email</span>
          <input type="email" value={form.email} onChange={e => setForm(p => ({ ...p, email: e.target.value }))} style={{ ...inp, marginTop: 2 }} />
        </label>
        {msg && <div style={{ fontSize: ".82rem", color: msg.ok ? "#166534" : "#dc2626", display: "flex", alignItems: "center", gap: 5 }}>{msg.ok ? <CheckCircle2 size={14}/> : <AlertTriangle size={14}/>}{msg.text}</div>}
        <button type="submit" className="primary-btn" style={{ display: "inline-flex", alignItems: "center", gap: 6 }}><Save size={14}/>Save Changes</button>
      </form>

      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        <button onClick={doReset} className="secondary-btn" style={{ display: "inline-flex", alignItems: "center", gap: 6 }}><KeyRound size={14}/>Reset Temporary Password</button>
        {isPaid
          ? <button onClick={async () => { const d = await emailTeacherStudentCredentials(student.id).catch(() => ({ success: false })); setMsg(d.invite_sent ? { ok: true, text: "Emailed." } : { ok: false, text: "Failed." }); }} className="secondary-btn" style={{ display: "inline-flex", alignItems: "center", gap: 6 }}><Mail size={14}/>Email Login Details</button>
          : <button disabled title="Upgrade to paid plan" style={{ opacity: .5, cursor: "not-allowed", display: "inline-flex", alignItems: "center", gap: 6 }} className="secondary-btn"><Mail size={14}/>Email Login Details (Paid only)</button>
        }
        <button onClick={doArchive} className="danger-btn" style={{ display: "inline-flex", alignItems: "center", gap: 6 }}><Trash2 size={14}/>Archive / Remove from Roster</button>
      </div>

      {pwResult?.success && (
        <div style={{ marginTop: 10, padding: "8px 12px", background: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: 7, fontSize: ".82rem", display: "flex", alignItems: "center", gap: 5, flexWrap: "wrap" }}>
          <KeyRound size={14}/>Temp password: <code style={{ color: "#f59e0b", fontWeight: 700 }}>{pwResult.temp_password}</code>
          <small style={{ display: "block", color: "#64748b", width: "100%" }}>{pwResult.warning}</small>
        </div>
      )}
    </div>
  );
}
