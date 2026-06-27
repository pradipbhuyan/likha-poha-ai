/**
 * TeacherDashboardPage.jsx — Teacher Success Platform
 * ─────────────────────────────────────────────────────────────────────────────
 * 5-tab classroom management system:
 *   Overview | Students | Invitations | Classrooms | Insights
 *
 * Safety:
 *  - Teacher only sees their own assigned students (backend enforced)
 *  - Password actions use one-time display, never stored
 *  - Plan limits enforced by backend; UI shows warnings
 *  - Free tier teacher sees disabled Email Login Details with tooltip
 *  - All destructive actions require confirmation
 */
import { useCallback, useEffect, useState } from "react";
import {
  getTeacherClassroomSummary,
  listTeacherStudents,
  getTeacherStudentDetail,
  updateTeacherStudent,
  archiveTeacherStudent,
  resetTeacherStudentPassword,
  emailTeacherStudentCredentials,
  listTeacherInvitations,
  createTeacherInvitation,
  resendTeacherInvitation,
  cancelTeacherInvitation,
  listTeacherClassrooms,
  createTeacherClassroom,
  updateTeacherClassroom,
  archiveTeacherClassroom,
  addStudentToClassroom,
  removeStudentFromClassroom,
  createTeacherStudent,
} from "../api/teacherDashboard";

// ── Style helpers ─────────────────────────────────────────────────────────────
const card = {
  background: "var(--panel,#fff)",
  border: "1px solid var(--border,#e5e7eb)",
  borderRadius: 10,
  padding: "14px 16px",
  marginBottom: 12,
};

const inputStyle = {
  padding: "8px 10px",
  borderRadius: 7,
  border: "1px solid var(--border,#e5e7eb)",
  fontFamily: "inherit",
  fontSize: ".85rem",
  background: "var(--surface2,#f8fafc)",
  color: "var(--text,#1e293b)",
  width: "100%",
};

const STATUS_COLOR = {
  active:    { bg: "rgba(34,197,94,.1)",  color: "#166534" },
  inactive:  { bg: "rgba(148,163,184,.1)", color: "#64748b" },
  suspended: { bg: "rgba(239,68,68,.1)",  color: "#dc2626" },
  pending:   { bg: "rgba(245,158,11,.1)",  color: "#92400e" },
  accepted:  { bg: "rgba(34,197,94,.1)",  color: "#166534" },
  expired:   { bg: "rgba(239,68,68,.1)",  color: "#dc2626" },
  cancelled: { bg: "rgba(148,163,184,.1)", color: "#64748b" },
};

function Badge({ status }) {
  const sc = STATUS_COLOR[status] || STATUS_COLOR.inactive;
  return (
    <span style={{ ...sc, display: "inline-block", fontSize: ".72rem", padding: "2px 7px", borderRadius: 5, fontWeight: 600 }}>
      {status}
    </span>
  );
}

function KpiCard({ label, value, sub, color = "#6366f1" }) {
  return (
    <div style={{ ...card, flex: "1 1 130px", minWidth: 120, textAlign: "center" }}>
      <div style={{ fontSize: "1.6rem", fontWeight: 800, color }}>{value ?? "—"}</div>
      <div style={{ fontSize: ".78rem", fontWeight: 600, marginTop: 2 }}>{label}</div>
      {sub && <div style={{ fontSize: ".7rem", color: "#94a3b8", marginTop: 2 }}>{sub}</div>}
    </div>
  );
}

// ── Grade options ─────────────────────────────────────────────────────────────
const GRADE_OPTIONS = Array.from({ length: 12 }, (_, i) => `Grade ${i + 1}`);

// ── Main Component ────────────────────────────────────────────────────────────
export default function TeacherDashboardPage({ user }) {
  const [activeTab, setActiveTab] = useState("overview");

  const TABS = [
    { key: "overview",     label: "Overview",     icon: "🏠" },
    { key: "students",     label: "Students",     icon: "🎓" },
    { key: "invitations",  label: "Invitations",  icon: "✉️" },
    { key: "classrooms",   label: "Classrooms",   icon: "🏫" },
    { key: "insights",     label: "Insights",     icon: "📊" },
  ];

  const isPaid = user?.isPaid ?? false;

  return (
    <div style={{ fontFamily: "inherit", maxWidth: 960, margin: "0 auto", padding: "0 12px 40px" }}>
      <h2 style={{ margin: "16px 0 4px", fontSize: "1.15rem", fontWeight: 800 }}>
        🏫 Teacher Dashboard
      </h2>
      <p style={{ margin: "0 0 16px", fontSize: ".82rem", color: "#64748b" }}>
        Classroom management · Students · Invitations · Insights
      </p>

      {/* ── Tab nav ─────────────────────────────────────────────────────── */}
      <div style={{ display: "flex", gap: 4, flexWrap: "wrap", marginBottom: 20, borderBottom: "2px solid var(--border,#e5e7eb)", paddingBottom: 0 }}>
        {TABS.map(t => (
          <button key={t.key}
            onClick={() => setActiveTab(t.key)}
            data-testid={`teacher-tab-${t.key}`}
            style={{
              padding: "8px 16px", border: "none", background: "none", cursor: "pointer",
              fontFamily: "inherit", fontSize: ".85rem", fontWeight: activeTab === t.key ? 700 : 500,
              color: activeTab === t.key ? "#6366f1" : "var(--text,#374151)",
              borderBottom: activeTab === t.key ? "2px solid #6366f1" : "2px solid transparent",
              marginBottom: -2,
            }}>
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      {/* ── Panels ──────────────────────────────────────────────────────── */}
      {activeTab === "overview"    && <OverviewTab    user={user} isPaid={isPaid} onNavigate={setActiveTab} />}
      {activeTab === "students"    && <StudentsTab    user={user} isPaid={isPaid} />}
      {activeTab === "invitations" && <InvitationsTab user={user} isPaid={isPaid} />}
      {activeTab === "classrooms"  && <ClassroomsTab  user={user} />}
      {activeTab === "insights"    && <InsightsTab    user={user} />}
      {/* InsightsTab uses summary cached in OverviewTab — see shared cache below */}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Overview Tab
// ─────────────────────────────────────────────────────────────────────────────
function OverviewTab({ user, isPaid, onNavigate }) {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState(null);

  useEffect(() => {
    // Single canonical fetch — no secondary student-limit call
    getTeacherClassroomSummary()
      .then(s => { setSummary(s); setLoading(false); })
      .catch(e => { setFetchError(e.message || "Failed to load dashboard."); setLoading(false); });
  }, []);

  // ── Loading skeleton ───────────────────────────────────────────────────────
  if (loading) return (
    <div data-testid="teacher-overview-tab">
      <div style={{ ...card, opacity: .5 }}>
        <div style={{ height: 12, background: "var(--border,#e5e7eb)", borderRadius: 4, marginBottom: 8, width: "40%" }} />
        <div style={{ display: "flex", gap: 8 }}>
          {[1,2,3,4].map(i => <div key={i} style={{ flex: 1, height: 60, background: "var(--border,#e5e7eb)", borderRadius: 8 }} />)}
        </div>
      </div>
    </div>
  );

  // ── Error state ────────────────────────────────────────────────────────────
  if (fetchError || summary?.error) return (
    <div data-testid="teacher-overview-tab">
      <div style={{ ...card, color: "#dc2626", background: "#fef2f2", border: "1px solid #fecaca" }}>
        ⚠ {fetchError || summary?.error}
      </div>
    </div>
  );

  // ── Derive all counts from the single canonical summary ────────────────────
  // Use new structured DTO when available, fall back to legacy flat fields
  const sub = summary?.subscription || {
    students_used: summary?.totals?.total_students ?? 0,
    student_limit: summary?.plan_limit ?? 10,
    is_paid: summary?.is_paid ?? false,
  };
  const stu = summary?.students || summary?.totals || {};
  const cls = summary?.classrooms || {};
  const lrn = summary?.learning || {
    average_mock_score: summary?.averages?.mock_test_avg ?? null,
    recent_activity: summary?.recent_activity || [],
    attention_students: summary?.needs_attention || [],
  };

  const studentsUsed  = sub.students_used ?? stu.total_students ?? 0;
  const studentLimit  = sub.student_limit ?? 10;
  const atLimit       = studentsUsed >= studentLimit;
  const totalStudents = studentsUsed;
  const activeCount   = stu.active_students ?? 0;
  const inactiveCount = stu.inactive_students ?? 0;
  const pendingInv    = stu.pending_invitations ?? 0;
  const needsCount    = stu.needs_attention_count ?? 0;
  const classCount    = cls.classroom_count ?? 0;
  const mockAvg       = lrn.average_mock_score ?? null;
  const recentAct     = lrn.recent_activity || [];
  const attentionList = lrn.attention_students || [];

  return (
    <div data-testid="teacher-overview-tab">
      {/* Plan usage bar — single source of truth */}
      <div style={{ ...card, display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 700, fontSize: ".88rem" }}>
            Students: {studentsUsed} / {studentLimit}
            {atLimit && <span style={{ marginLeft: 8, color: "#dc2626", fontSize: ".78rem" }}>Limit reached</span>}
          </div>
          <div style={{ marginTop: 6, background: "var(--border,#e5e7eb)", borderRadius: 4, height: 6 }}>
            <div style={{ height: 6, borderRadius: 4, background: atLimit ? "#dc2626" : "#6366f1", width: `${Math.min(100, (studentsUsed / studentLimit) * 100)}%`, transition: "width .3s" }} />
          </div>
        </div>
        {!isPaid && (
          <span style={{ fontSize: ".75rem", color: "#64748b" }}>
            {studentsUsed}/{studentLimit} · Upgrade to paid plan for {studentLimit === 10 ? "30" : "more"} students
          </span>
        )}
      </div>

      {/* KPI row — all from one fetch */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 10, marginBottom: 16 }}>
        <KpiCard label="Total Students"   value={totalStudents} color="#6366f1" />
        <KpiCard label="Active"           value={activeCount}   color="#22c55e" />
        <KpiCard label="Inactive"         value={inactiveCount} color="#94a3b8" />
        <KpiCard label="Pending Invites"  value={pendingInv}    color="#f59e0b" />
        <KpiCard label="Needs Attention"  value={needsCount}    color="#ef4444" />
        {classCount > 0 && <KpiCard label="Classrooms"    value={classCount}    color="#8b5cf6" />}
        {mockAvg != null && <KpiCard label="Class Avg Score" value={`${mockAvg}%`} color="#0ea5e9" />}
      </div>

      {/* Needs attention */}
      {attentionList.length > 0 && (
        <div style={{ ...card, borderLeft: "3px solid #f59e0b" }}>
          <div style={{ fontWeight: 700, marginBottom: 6 }}>⚠ Students needing attention (no activity 7+ days)</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {attentionList.map(n => (
              <span key={n} style={{ fontSize: ".78rem", background: "rgba(245,158,11,.1)", color: "#92400e", padding: "3px 8px", borderRadius: 5, fontWeight: 600 }}>{n}</span>
            ))}
          </div>
        </div>
      )}

      {/* Recent activity */}
      {recentAct.length > 0 && (
        <div style={card}>
          <div style={{ fontWeight: 700, marginBottom: 8 }}>🕐 Recent Activity</div>
          {recentAct.map((a, i) => (
            <div key={i} style={{ display: "flex", gap: 10, padding: "4px 0", borderBottom: "1px solid var(--border,#f1f5f9)", fontSize: ".78rem" }}>
              <span style={{ color: "#94a3b8", minWidth: 80 }}>{(a.at || "").slice(0, 16)}</span>
              <span style={{ fontWeight: 600 }}>{a.username}</span>
              <span style={{ color: "#64748b" }}>{a.feature}</span>
            </div>
          ))}
        </div>
      )}

      {/* Quick actions */}
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <button onClick={() => onNavigate("students")}    className="primary-btn">🎓 Manage Students</button>
        <button onClick={() => onNavigate("invitations")} className="secondary-btn">✉️ Invite Student</button>
        <button onClick={() => onNavigate("classrooms")}  className="secondary-btn">🏫 Classrooms</button>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Students Tab
// ─────────────────────────────────────────────────────────────────────────────
function StudentsTab({ user, isPaid }) {
  const [students, setStudents] = useState([]);
  const [loading, setLoading]   = useState(true);
  const [q, setQ]               = useState("");
  const [filterGrade, setGrade] = useState("");
  const [filterStatus, setStatus] = useState("");
  const [sort, setSort]         = useState("name");
  const [selected, setSelected] = useState(null);   // student detail drawer
  const [detail, setDetail]     = useState(null);
  const [detailLoading, setDL]  = useState(false);
  const [msg, setMsg]           = useState(null);
  const [pwResult, setPwResult] = useState(null);
  const [editMode, setEditMode] = useState(false);
  const [editData, setEditData] = useState({});
  const [showAddForm, setShowAdd] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    const d = await listTeacherStudents({ q, grade: filterGrade, status: filterStatus, sort }).catch(() => null);
    setStudents(d?.students || []);
    setLoading(false);
  }, [q, filterGrade, filterStatus, sort]);

  useEffect(() => { load(); }, [load]);

  async function openDetail(s) {
    setSelected(s);
    setDL(true);
    setDetail(null);
    setPwResult(null);
    setMsg(null);
    setEditMode(false);
    const d = await getTeacherStudentDetail(s.id).catch(() => null);
    setDetail(d);
    setDL(false);
  }

  async function doArchive(s) {
    if (!window.confirm(`Archive ${s.username}? They will be removed from your roster.`)) return;
    const d = await archiveTeacherStudent(s.id).catch(e => ({ success: false, error: e.message }));
    if (d.success) { setMsg("✅ Student archived."); load(); setSelected(null); }
    else setMsg(`⚠ ${d.error}`);
  }

  async function doResetPassword(s) {
    if (!window.confirm("Reset temporary password for " + s.username + "? Shown once only.")) return;
    const d = await resetTeacherStudentPassword(s.id).catch(e => ({ success: false, error: e.message }));
    setPwResult(d);
  }

  async function doEmailCredentials(s) {
    const d = await emailTeacherStudentCredentials(s.id).catch(e => ({ success: false, error: e.message }));
    if (d.invite_sent) setMsg("✅ Login credentials emailed.");
    else setMsg("⚠ " + (d.error || d.note || "Could not send."));
  }

  async function doSaveEdit() {
    const d = await updateTeacherStudent(selected.id, editData).catch(e => ({ success: false, error: e.message }));
    if (d.success) { setMsg("✅ Saved."); setEditMode(false); load(); openDetail(selected); }
    else setMsg("⚠ " + d.error);
  }

  return (
    <div data-testid="teacher-students-tab">
      {/* ── Add student form ── */}
      <div style={{ marginBottom: 12, display: "flex", gap: 8, flexWrap: "wrap" }}>
        <button onClick={() => setShowAdd(v => !v)} className="primary-btn">
          {showAddForm ? "✕ Close" : "➕ Add Student"}
        </button>
      </div>
      {showAddForm && <AddStudentForm onAdded={() => { setShowAdd(false); load(); }} />}

      {/* ── Search / filter bar ── */}
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
        <input value={q} onChange={e => setQ(e.target.value)} placeholder="Search by name or email…"
          data-testid="student-search-input"
          style={{ ...inputStyle, flex: 1, minWidth: 160 }} />
        <select value={filterGrade} onChange={e => setGrade(e.target.value)} style={{ ...inputStyle, width: "auto" }}>
          <option value="">All Grades</option>
          {GRADE_OPTIONS.map(g => <option key={g} value={g}>{g}</option>)}
        </select>
        <select value={filterStatus} onChange={e => setStatus(e.target.value)} style={{ ...inputStyle, width: "auto" }}>
          <option value="">All Statuses</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
          <option value="archived">Archived</option>
        </select>
        <select value={sort} onChange={e => setSort(e.target.value)} style={{ ...inputStyle, width: "auto" }}>
          <option value="name">Sort: Name</option>
          <option value="grade">Sort: Grade</option>
        </select>
      </div>

      {msg && <div style={{ marginBottom: 8, color: msg.startsWith("✅") ? "#166534" : "#dc2626", fontSize: ".82rem" }}>{msg}</div>}

      {/* ── Roster ── */}
      {loading && <div style={{ color: "#94a3b8" }}>Loading students…</div>}
      {!loading && students.length === 0 && (
        <div style={{ padding: 20, textAlign: "center", color: "#94a3b8", fontSize: ".85rem" }}>
          No students found. Add a student or send an invitation.
        </div>
      )}
      {students.map(s => (
        <div key={s.id} style={{ ...card, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8, flexWrap: "wrap" }}>
          <div style={{ flex: 1, minWidth: 140 }}>
            <strong style={{ fontSize: ".88rem" }}>{s.username}</strong>
            <span style={{ marginLeft: 8 }}><Badge status={s.account_status || "active"} /></span>
            <div style={{ fontSize: ".72rem", color: "#94a3b8", marginTop: 2 }}>
              {s.email || "—"} · {s.grade || "—"}
            </div>
          </div>
          <button onClick={() => openDetail(s)} style={{ padding: "4px 10px", borderRadius: 6, border: "1px solid #6366f1", background: "rgba(99,102,241,.08)", color: "#6366f1", fontWeight: 600, fontSize: ".78rem", cursor: "pointer", fontFamily: "inherit" }}>
            View
          </button>
        </div>
      ))}

      {/* ── Student detail drawer ── */}
      {selected && (
        <div style={{ position: "fixed", top: 0, right: 0, width: Math.min(420, window.innerWidth), height: "100vh", background: "var(--panel,#fff)", boxShadow: "-4px 0 24px rgba(0,0,0,.12)", overflowY: "auto", zIndex: 200, padding: 20 }}>
          <button onClick={() => setSelected(null)} style={{ float: "right", background: "none", border: "none", fontSize: "1.2rem", cursor: "pointer" }}>✕</button>
          <h3 style={{ margin: "0 0 4px" }}>{selected.username}</h3>
          {detailLoading && <div style={{ color: "#94a3b8" }}>Loading…</div>}

          {detail && !detailLoading && (
            <>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 12 }}>
                {[["Grade", detail.student?.grade], ["Plan", detail.student?.subscription_plan], ["Status", detail.student?.account_status]].map(([k, v]) => (
                  <div key={k} style={{ background: "var(--surface2,#f8fafc)", border: "1px solid var(--border,#e5e7eb)", borderRadius: 7, padding: "6px 10px" }}>
                    <div style={{ fontSize: ".68rem", color: "#64748b" }}>{k}</div>
                    <div style={{ fontSize: ".82rem", fontWeight: 700 }}>{v || "—"}</div>
                  </div>
                ))}
              </div>

              {/* Learning signals */}
              {detail.learning && (
                <div style={{ ...card }}>
                  <div style={{ fontWeight: 700, marginBottom: 6 }}>📊 Learning Signals</div>
                  {detail.learning.last_active
                    ? <div style={{ fontSize: ".78rem" }}>Last active: {new Date(detail.learning.last_active).toLocaleString()}</div>
                    : <div style={{ fontSize: ".78rem", color: "#94a3b8" }}>No recent activity recorded.</div>}
                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 8 }}>
                    {[["Lessons", detail.learning.lessons_generated], ["Doubts", detail.learning.doubts_asked], ["Mock Tests", detail.learning.mock_tests_completed], ["Avg Score", detail.learning.mock_test_avg != null ? detail.learning.mock_test_avg + "%" : "—"]].map(([k, v]) => (
                      <div key={k} style={{ background: "var(--surface2,#f8fafc)", border: "1px solid var(--border,#e5e7eb)", borderRadius: 7, padding: "6px 10px", textAlign: "center" }}>
                        <div style={{ fontWeight: 700 }}>{v ?? 0}</div>
                        <div style={{ fontSize: ".68rem", color: "#64748b" }}>{k}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Classrooms */}
              {detail.classrooms?.length > 0 && (
                <div style={{ marginBottom: 10 }}>
                  <strong style={{ fontSize: ".8rem" }}>Classrooms: </strong>
                  {detail.classrooms.map(c => <span key={c.id} style={{ marginRight: 6, fontSize: ".78rem", background: "rgba(99,102,241,.1)", color: "#6366f1", padding: "2px 7px", borderRadius: 5 }}>{c.name}</span>)}
                </div>
              )}

              {/* Edit form */}
              {editMode ? (
                <div style={{ marginBottom: 10 }}>
                  {["username", "grade", "email"].map(f => (
                    <label key={f} style={{ display: "block", marginBottom: 6 }}>
                      <span style={{ fontSize: ".78rem", fontWeight: 600 }}>{f}</span>
                      <input value={editData[f] ?? (detail.student?.[f] || "")} onChange={e => setEditData(p => ({ ...p, [f]: e.target.value }))}
                        style={{ ...inputStyle, marginTop: 2 }} />
                    </label>
                  ))}
                  <div style={{ display: "flex", gap: 8 }}>
                    <button onClick={doSaveEdit} className="primary-btn">💾 Save</button>
                    <button onClick={() => setEditMode(false)} className="secondary-btn">Cancel</button>
                  </div>
                </div>
              ) : null}

              {/* Actions */}
              <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 8 }}>
                {!editMode && <button onClick={() => { setEditMode(true); setEditData({}); }} className="secondary-btn">✏️ Edit Details</button>}
                <button onClick={() => doResetPassword(selected)} className="secondary-btn">🔑 Reset Password</button>

                {/* Email credentials — paid only */}
                {isPaid ? (
                  <button onClick={() => doEmailCredentials(selected)} className="secondary-btn">📧 Email Login Details</button>
                ) : (
                  <button disabled title="Upgrade to a paid plan to email login details." style={{ opacity: .5, cursor: "not-allowed" }} className="secondary-btn">
                    📧 Email Login Details (Paid only)
                  </button>
                )}

                <button onClick={() => doArchive(selected)} className="danger-btn">🗑 Archive Student</button>
              </div>

              {/* Password result */}
              {pwResult?.success && (
                <div style={{ marginTop: 10, padding: "8px 12px", background: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: 7, fontSize: ".82rem" }}>
                  🔑 New temp password: <code style={{ color: "#f59e0b", fontWeight: 700 }}>{pwResult.temp_password}</code><br />
                  <small style={{ color: "#64748b" }}>{pwResult.warning}</small>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}

// ── Add Student form ──────────────────────────────────────────────────────────
function AddStudentForm({ onAdded }) {
  const [form, setForm] = useState({ username: "", grade: "Grade 9", password: "", email: "" });
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState(null);

  async function submit(e) {
    e.preventDefault();
    if (!form.username || !form.grade || !form.password) {
      setMsg("Name, grade and password are required."); return;
    }
    setLoading(true);
    const d = await createTeacherStudent({ username: form.username, grade: form.grade, password: form.password, email: form.email || undefined })
      .catch(e => ({ success: false, error: e.message }));
    setLoading(false);
    if (d.success !== false) { setMsg("✅ Student created!"); onAdded(); }
    else setMsg("⚠ " + d.error);
  }

  return (
    <div style={{ ...card }}>
      <h4 style={{ margin: "0 0 10px" }}>➕ Add Student</h4>
      <form onSubmit={submit} style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
        <label style={{ gridColumn: "1 / -1" }}>
          <span style={{ fontSize: ".78rem", fontWeight: 600 }}>Name *</span>
          <input value={form.username} onChange={e => setForm(p => ({ ...p, username: e.target.value }))} required style={{ ...inputStyle, marginTop: 2 }} />
        </label>
        <label>
          <span style={{ fontSize: ".78rem", fontWeight: 600 }}>Grade *</span>
          <select value={form.grade} onChange={e => setForm(p => ({ ...p, grade: e.target.value }))} style={{ ...inputStyle, marginTop: 2 }}>
            {GRADE_OPTIONS.map(g => <option key={g} value={g}>{g}</option>)}
          </select>
        </label>
        <label>
          <span style={{ fontSize: ".78rem", fontWeight: 600 }}>Temp Password *</span>
          <input type="text" value={form.password} onChange={e => setForm(p => ({ ...p, password: e.target.value }))} required placeholder="Share with student" style={{ ...inputStyle, marginTop: 2 }} />
        </label>
        <label style={{ gridColumn: "1 / -1" }}>
          <span style={{ fontSize: ".78rem", fontWeight: 600 }}>Email (optional)</span>
          <input type="email" value={form.email} onChange={e => setForm(p => ({ ...p, email: e.target.value }))} style={{ ...inputStyle, marginTop: 2 }} />
        </label>
        {msg && <div style={{ gridColumn: "1 / -1", fontSize: ".82rem", color: msg.startsWith("✅") ? "#166534" : "#dc2626" }}>{msg}</div>}
        <button type="submit" disabled={loading} className="primary-btn">{loading ? "Creating…" : "Create Student"}</button>
      </form>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Invitations Tab
// ─────────────────────────────────────────────────────────────────────────────
function InvitationsTab({ user, isPaid }) {
  const [invitations, setInvitations] = useState([]);
  const [loading, setLoading]   = useState(true);
  const [form, setForm]         = useState({ student_name: "", grade: "Grade 9", email: "" });
  const [msg, setMsg]           = useState(null);
  const [filterStatus, setStatus] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    const d = await listTeacherInvitations(filterStatus || null).catch(() => null);
    setInvitations(d?.invitations || []);
    setLoading(false);
  }, [filterStatus]);

  useEffect(() => { load(); }, [load]);

  async function doCreate(e) {
    e.preventDefault();
    if (!form.student_name || !form.email) { setMsg("Name and email are required."); return; }
    const d = await createTeacherInvitation(form).catch(e => ({ success: false, error: e.message }));
    if (d.success) { setMsg("✅ Invitation sent to " + form.email); setForm({ student_name: "", grade: "Grade 9", email: "" }); load(); }
    else setMsg("⚠ " + d.error);
  }

  return (
    <div data-testid="teacher-invitations-tab">
      {/* Create invitation form */}
      <div style={card}>
        <h4 style={{ margin: "0 0 10px" }}>✉️ Invite a Student</h4>
        <form onSubmit={doCreate} style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
          <label style={{ gridColumn: "1 / -1" }}>
            <span style={{ fontSize: ".78rem", fontWeight: 600 }}>Student Name *</span>
            <input value={form.student_name} onChange={e => setForm(p => ({ ...p, student_name: e.target.value }))} required style={{ ...inputStyle, marginTop: 2 }} />
          </label>
          <label>
            <span style={{ fontSize: ".78rem", fontWeight: 600 }}>Grade</span>
            <select value={form.grade} onChange={e => setForm(p => ({ ...p, grade: e.target.value }))} style={{ ...inputStyle, marginTop: 2 }}>
              {GRADE_OPTIONS.map(g => <option key={g} value={g}>{g}</option>)}
            </select>
          </label>
          <label>
            <span style={{ fontSize: ".78rem", fontWeight: 600 }}>Email *</span>
            <input type="email" value={form.email} onChange={e => setForm(p => ({ ...p, email: e.target.value }))} required style={{ ...inputStyle, marginTop: 2 }} />
          </label>
          {msg && <div style={{ gridColumn: "1 / -1", fontSize: ".82rem", color: msg.startsWith("✅") ? "#166534" : "#dc2626" }}>{msg}</div>}
          <button type="submit" className="primary-btn">Send Invitation</button>
        </form>
      </div>

      {/* Filter */}
      <div style={{ display: "flex", gap: 8, marginBottom: 10 }}>
        {["", "pending", "accepted", "expired", "cancelled"].map(s => (
          <button key={s} onClick={() => setStatus(s)}
            style={{ padding: "4px 10px", borderRadius: 6, border: "1px solid var(--border,#e5e7eb)", background: filterStatus === s ? "#6366f1" : "var(--panel,#fff)", color: filterStatus === s ? "#fff" : "var(--text,#374151)", fontSize: ".78rem", cursor: "pointer", fontFamily: "inherit", fontWeight: 600 }}>
            {s || "All"}
          </button>
        ))}
      </div>

      {loading && <div style={{ color: "#94a3b8" }}>Loading…</div>}
      {!loading && invitations.length === 0 && (
        <div style={{ padding: 20, textAlign: "center", color: "#94a3b8", fontSize: ".85rem" }}>No invitations yet.</div>
      )}
      {invitations.map(inv => (
        <div key={inv.id} style={{ ...card, display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
          <div>
            <strong>{inv.student_name}</strong>
            <span style={{ marginLeft: 8 }}><Badge status={inv.status} /></span>
            <div style={{ fontSize: ".72rem", color: "#94a3b8", marginTop: 2 }}>
              {inv.email} · {inv.grade} · Expires {(inv.expires_at || "").slice(0, 10)}
            </div>
          </div>
          <div style={{ display: "flex", gap: 6 }}>
            {(inv.status === "pending" || inv.status === "expired") && (
              <button onClick={async () => { await resendTeacherInvitation(inv.id); setMsg("✅ Resent."); load(); }}
                style={{ padding: "3px 9px", borderRadius: 6, border: "1px solid #6366f1", background: "rgba(99,102,241,.08)", color: "#6366f1", fontSize: ".75rem", cursor: "pointer", fontFamily: "inherit" }}>
                Resend
              </button>
            )}
            {inv.status === "pending" && (
              <button onClick={async () => { if (!window.confirm("Cancel this invitation?")) return; await cancelTeacherInvitation(inv.id); setMsg("Cancelled."); load(); }}
                style={{ padding: "3px 9px", borderRadius: 6, border: "1px solid #ef4444", background: "rgba(239,68,68,.07)", color: "#dc2626", fontSize: ".75rem", cursor: "pointer", fontFamily: "inherit" }}>
                Cancel
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Classrooms Tab
// ─────────────────────────────────────────────────────────────────────────────
function ClassroomsTab({ user }) {
  const [classrooms, setClassrooms] = useState([]);
  const [loading, setLoading]   = useState(true);
  const [form, setForm]         = useState({ name: "", description: "" });
  const [msg, setMsg]           = useState(null);
  const [renaming, setRenaming] = useState(null);
  const [renameVal, setRenameVal] = useState("");
  const [students, setStudents] = useState([]);

  const load = useCallback(async () => {
    setLoading(true);
    const [cls, stu] = await Promise.all([
      listTeacherClassrooms("active").catch(() => null),
      listTeacherStudents().catch(() => null),
    ]);
    setClassrooms(cls?.classrooms || []);
    setStudents(stu?.students || []);
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  async function doCreate(e) {
    e.preventDefault();
    if (!form.name.trim()) { setMsg("Name is required."); return; }
    const d = await createTeacherClassroom(form).catch(e => ({ success: false, error: e.message }));
    if (d.success) { setMsg("✅ Classroom created."); setForm({ name: "", description: "" }); load(); }
    else setMsg("⚠ " + d.error);
  }

  return (
    <div data-testid="teacher-classrooms-tab">
      {/* Create form */}
      <div style={card}>
        <h4 style={{ margin: "0 0 10px" }}>🏫 Create Classroom</h4>
        <form onSubmit={doCreate} style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <input value={form.name} onChange={e => setForm(p => ({ ...p, name: e.target.value }))} placeholder="Classroom name *" required
            data-testid="classroom-name-input"
            style={{ ...inputStyle, flex: 1, minWidth: 160 }} />
          <input value={form.description} onChange={e => setForm(p => ({ ...p, description: e.target.value }))} placeholder="Description (optional)"
            style={{ ...inputStyle, flex: 1, minWidth: 160 }} />
          <button type="submit" className="primary-btn">Create</button>
        </form>
        {msg && <div style={{ marginTop: 6, fontSize: ".82rem", color: msg.startsWith("✅") ? "#166534" : "#dc2626" }}>{msg}</div>}
      </div>

      {loading && <div style={{ color: "#94a3b8" }}>Loading classrooms…</div>}
      {!loading && classrooms.length === 0 && (
        <div style={{ padding: 20, textAlign: "center", color: "#94a3b8", fontSize: ".85rem" }}>No classrooms yet. Create one above.</div>
      )}

      {classrooms.map(cls => (
        <div key={cls.id} style={card}>
          {renaming === cls.id ? (
            <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
              <input value={renameVal} onChange={e => setRenameVal(e.target.value)} style={{ ...inputStyle, flex: 1 }} />
              <button onClick={async () => { await updateTeacherClassroom(cls.id, { name: renameVal }); setRenaming(null); load(); }} className="primary-btn">Save</button>
              <button onClick={() => setRenaming(null)} className="secondary-btn">Cancel</button>
            </div>
          ) : (
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8, marginBottom: 8 }}>
              <div>
                <strong>{cls.name}</strong>
                <span style={{ marginLeft: 8, fontSize: ".72rem", color: "#94a3b8" }}>{cls.student_count || 0} students</span>
              </div>
              <div style={{ display: "flex", gap: 6 }}>
                <button onClick={() => { setRenaming(cls.id); setRenameVal(cls.name); }}
                  style={{ padding: "3px 9px", borderRadius: 6, border: "1px solid var(--border,#e5e7eb)", background: "var(--panel,#fff)", fontSize: ".75rem", cursor: "pointer", fontFamily: "inherit" }}>
                  Rename
                </button>
                <button onClick={async () => { if (!window.confirm("Archive " + cls.name + "?")) return; await archiveTeacherClassroom(cls.id); load(); }}
                  style={{ padding: "3px 9px", borderRadius: 6, border: "1px solid #ef4444", background: "rgba(239,68,68,.07)", color: "#dc2626", fontSize: ".75rem", cursor: "pointer", fontFamily: "inherit" }}>
                  Archive
                </button>
              </div>
            </div>
          )}

          {/* Add student to classroom */}
          <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
            <select onChange={async e => {
              if (!e.target.value) return;
              await addStudentToClassroom(cls.id, e.target.value);
              e.target.value = "";
              load();
            }} style={{ ...inputStyle, width: "auto", flex: 1 }}>
              <option value="">+ Add student…</option>
              {students.map(s => <option key={s.id} value={s.id}>{s.username} ({s.grade || "—"})</option>)}
            </select>
          </div>
        </div>
      ))}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Insights Tab
// ─────────────────────────────────────────────────────────────────────────────
function InsightsTab({ user }) {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getTeacherClassroomSummary().then(s => { setSummary(s); setLoading(false); }).catch(() => setLoading(false));
  }, []);

  if (loading) return <div style={{ color: "#94a3b8", padding: 16 }}>Loading insights…</div>;

  const attention = summary?.needs_attention || [];
  const t = summary?.totals || {};
  const avg = summary?.averages || {};

  return (
    <div data-testid="teacher-insights-tab">
      <div style={{ display: "flex", flexWrap: "wrap", gap: 10, marginBottom: 16 }}>
        <KpiCard label="Class Avg Score" value={avg.mock_test_avg != null ? avg.mock_test_avg + "%" : "Not available yet"} color="#0ea5e9" />
        <KpiCard label="Inactive Students" value={t.inactive_students ?? 0} color="#94a3b8" />
        <KpiCard label="Need Attention" value={t.needs_attention_count ?? 0} color="#ef4444" />
      </div>

      {attention.length > 0 && (
        <div style={{ ...card, borderLeft: "3px solid #ef4444" }}>
          <div style={{ fontWeight: 700, marginBottom: 6 }}>🚨 Students inactive 7+ days</div>
          {attention.map(n => (
            <div key={n} style={{ fontSize: ".82rem", padding: "4px 0", borderBottom: "1px solid var(--border,#f1f5f9)" }}>{n}</div>
          ))}
        </div>
      )}

      {attention.length === 0 && (
        <div style={{ ...card, color: "#166534", background: "#f0fdf4", border: "1px solid #bbf7d0" }}>
          ✅ All students have been active recently.
        </div>
      )}

      <div style={{ ...card }}>
        <div style={{ fontWeight: 700, marginBottom: 6 }}>📊 Data availability</div>
        <div style={{ fontSize: ".78rem", color: "#64748b" }}>
          Mock test scores, lesson completion, and weak topics are shown when available.<br />
          If a data source is not yet set up, "Not available yet" is displayed instead of an error.
        </div>
      </div>
    </div>
  );
}
