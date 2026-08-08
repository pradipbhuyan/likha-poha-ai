import { useEffect, useState } from "react";
import {
  BarChart, Bar, LineChart, Line,
  XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, CartesianGrid,
} from "recharts";
import { getUserHistory } from "../api/analytics";
import { getTeacherDashboardSummary } from "../api/teacherDashboard";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const SUBJECT_COLORS = [
  "#3b82f6","#10b981","#f59e0b","#ef4444",
  "#8b5cf6","#06b6d4","#ec4899","#f97316",
];

function ScoreBadge({ score }) {
  const color = score >= 75 ? "#10b981" : score >= 50 ? "#f59e0b" : "#ef4444";
  const label = score >= 75 ? "Good" : score >= 50 ? "Average" : "Needs Help";
  return (
    <span style={{ fontSize: ".72rem", fontWeight: 700, padding: "2px 8px", borderRadius: 12,
      background: `${color}22`, color, border: `1px solid ${color}44` }}>
      {score}% · {label}
    </span>
  );
}

export default function TeacherStudentAnalyticsPage({ user }) {
  const [students, setStudents] = useState([]);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState("");
  const [selected, setSelected] = useState(null);
  const [history, setHistory]   = useState([]);
  const [histLoading, setHistLoading] = useState(false);
  const [gradeFilter, setGradeFilter] = useState("all");
  const [sortBy, setSortBy]     = useState("name");

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError("");
      try {
        const res = await fetch(`${API_BASE}/api/teacher/student-analytics`, {
          headers: { Authorization: `Bearer ${user?.accessToken}` },
        });
        const data = await res.json();
        if (!res.ok || !data.success) throw new Error(data.detail || "Could not load analytics");
        setStudents(data.students || []);
        if (data.students?.length > 0) setSelected(data.students[0]);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [user?.accessToken]);

  useEffect(() => {
    if (!selected) return;
    async function loadHist() {
      setHistLoading(true);
      try {
        const data = await getUserHistory(selected.username);
        setHistory(data.history || []);
      } catch { setHistory([]); }
      setHistLoading(false);
    }
    loadHist();
  }, [selected]);

  if (loading) return <p>Loading student analytics…</p>;

  const grades = ["all", ...new Set(students.map(s => s.grade).filter(Boolean))].sort();
  let filtered = gradeFilter === "all" ? students : students.filter(s => s.grade === gradeFilter);
  filtered = [...filtered].sort((a, b) => {
    if (sortBy === "score_desc") return b.average_score - a.average_score;
    if (sortBy === "score_asc")  return a.average_score - b.average_score;
    if (sortBy === "tests_desc") return b.total_tests - a.total_tests;
    return a.username.localeCompare(b.username);
  });

  // Score trend for selected student
  const trendData = history.map((h, i) => ({ name: `T${i+1}`, score: Number(h.percentage || 0) }));

  // Subject performance grouped bars
  const subjectPerf = (selected?.subject_performance || []).map(sp => ({
    subject: sp.subject,
    Best: sp.best,
    Average: sp.average,
    Latest: sp.latest,
  }));

  // Class overview — average per subject across all students
  const classSubjectMap = {};
  students.forEach(s => {
    (s.subject_performance || []).forEach(sp => {
      if (!classSubjectMap[sp.subject]) classSubjectMap[sp.subject] = [];
      classSubjectMap[sp.subject].push(sp.average);
    });
  });
  const classOverview = Object.entries(classSubjectMap).map(([subject, scores]) => ({
    subject,
    "Class Avg": Math.round(scores.reduce((a, b) => a + b, 0) / scores.length),
  }));

  return (
    <div className="premium-page">
      {error && <div className="error-box">{error}</div>}

      {students.length === 0 && !error && (
        <div className="premium-card" style={{ textAlign: "center", padding: 40 }}>
          <div style={{ fontSize: "3rem", marginBottom: 12 }}>🎓</div>
          <h3>No assigned students yet</h3>
          <p style={{ color: "var(--muted)" }}>Ask your admin to assign students to your account.</p>
        </div>
      )}

      {students.length > 0 && (
        <>
          {/* Class overview cards */}
          <section className="premium-grid premium-grid-4" style={{ marginBottom: 24 }}>
            <div className="premium-card premium-glow-card glow-blue">
              <strong>Students</strong>
              <p style={{ fontSize: "1.8rem", fontWeight: 800 }}>{students.length}</p>
            </div>
            <div className="premium-card premium-glow-card glow-green">
              <strong>Class Average</strong>
              <p style={{ fontSize: "1.8rem", fontWeight: 800 }}>
                {students.length ? Math.round(students.reduce((s, st) => s + st.average_score, 0) / students.length) : 0}%
              </p>
            </div>
            <div className="premium-card premium-glow-card glow-purple">
              <strong>Total Tests Taken</strong>
              <p style={{ fontSize: "1.8rem", fontWeight: 800 }}>
                {students.reduce((s, st) => s + st.total_tests, 0)}
              </p>
            </div>
            <div className="premium-card premium-glow-card glow-red">
              <strong>Needs Attention</strong>
              <p style={{ fontSize: "1.8rem", fontWeight: 800 }}>
                {students.filter(s => s.average_score < 50).length}
              </p>
            </div>
          </section>

          {/* Class subject overview chart */}
          {classOverview.length > 0 && (
            <div className="premium-card" style={{ marginBottom: 24 }}>
              <h3 style={{ marginBottom: 4 }}>📈 Class Subject Performance</h3>
              <p style={{ color: "var(--muted)", fontSize: ".82rem", marginBottom: 14 }}>
                Average score per subject across all your students.
              </p>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={classOverview} barCategoryGap="30%">
                  <CartesianGrid stroke="#334155" strokeDasharray="3 3" />
                  <XAxis dataKey="subject" stroke="#94a3b8" tick={{ fontSize: 11 }} />
                  <YAxis domain={[0, 100]} stroke="#94a3b8" />
                  <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155", borderRadius: 12, color: "#f8fafc" }} />
                  <Bar dataKey="Class Avg" fill="#3b82f6" radius={[6,6,0,0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Student roster + detail split */}
          <div style={{ display: "grid", gridTemplateColumns: "300px 1fr", gap: 20, alignItems: "flex-start" }}>

            {/* Left: student roster */}
            <div>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 10 }}>
                <select value={gradeFilter} onChange={e => setGradeFilter(e.target.value)}
                  style={{ flex: 1, fontSize: ".8rem", padding: "6px 10px" }}>
                  {grades.map(g => <option key={g} value={g}>{g === "all" ? "All Grades" : g}</option>)}
                </select>
                <select value={sortBy} onChange={e => setSortBy(e.target.value)}
                  style={{ flex: 1, fontSize: ".8rem", padding: "6px 10px" }}>
                  <option value="name">Name A–Z</option>
                  <option value="score_desc">Best Score ↓</option>
                  <option value="score_asc">Weakest First</option>
                  <option value="tests_desc">Most Active</option>
                </select>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: 6, maxHeight: 520, overflowY: "auto" }}>
                {filtered.map(st => {
                  const isSelected = selected?.id === st.id;
                  const scoreColor = st.average_score >= 75 ? "#10b981" : st.average_score >= 50 ? "#f59e0b" : "#ef4444";
                  return (
                    <button key={st.id}
                      onClick={() => setSelected(st)}
                      style={{
                        display: "flex", alignItems: "center", gap: 10, padding: "10px 12px",
                        borderRadius: 10, border: `2px solid ${isSelected ? "#6366f1" : "var(--border)"}`,
                        background: isSelected ? "rgba(99,102,241,.1)" : "var(--card-bg)",
                        cursor: "pointer", textAlign: "left", fontFamily: "inherit",
                      }}>
                      <div style={{
                        width: 34, height: 34, borderRadius: "50%", flexShrink: 0,
                        background: scoreColor + "22", border: `2px solid ${scoreColor}`,
                        display: "flex", alignItems: "center", justifyContent: "center",
                        fontSize: "1rem", fontWeight: 800, color: scoreColor,
                      }}>
                        {st.username[0]?.toUpperCase()}
                      </div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontWeight: 700, fontSize: ".88rem", truncate: true, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                          {st.username}
                        </div>
                        <div style={{ fontSize: ".72rem", color: "var(--muted)" }}>
                          {st.grade} · {st.total_tests} tests
                        </div>
                      </div>
                      <div style={{ fontSize: ".8rem", fontWeight: 800, color: scoreColor, flexShrink: 0 }}>
                        {st.average_score}%
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Right: selected student detail */}
            {selected && (
              <div>
                {/* Student header */}
                <div className="premium-card" style={{ marginBottom: 16 }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
                    <div>
                      <h3 style={{ marginBottom: 4 }}>{selected.username}</h3>
                      <p style={{ color: "var(--muted)", fontSize: ".82rem" }}>
                        {selected.grade} · {selected.email}
                      </p>
                    </div>
                    <ScoreBadge score={selected.average_score} />
                  </div>

                  <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginTop: 16 }}>
                    {[
                      { label: "Tests", value: selected.total_tests },
                      { label: "Average", value: `${selected.average_score}%` },
                      { label: "Best", value: `${selected.best_score}%` },
                      { label: "Latest", value: `${selected.latest_score}%` },
                    ].map(s => (
                      <div key={s.label} style={{ textAlign: "center", padding: "8px 0", background: "rgba(99,102,241,.05)", borderRadius: 8 }}>
                        <div style={{ fontSize: "1.2rem", fontWeight: 800 }}>{s.value}</div>
                        <div style={{ fontSize: ".72rem", color: "var(--muted)" }}>{s.label}</div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Score trend */}
                {!histLoading && trendData.length > 0 && (
                  <div className="premium-card" style={{ marginBottom: 16 }}>
                    <h4 style={{ marginBottom: 12 }}>📈 Score Trend</h4>
                    <ResponsiveContainer width="100%" height={200}>
                      <LineChart data={trendData}>
                        <CartesianGrid stroke="#334155" strokeDasharray="3 3" />
                        <XAxis dataKey="name" stroke="#94a3b8" />
                        <YAxis domain={[0, 100]} stroke="#94a3b8" />
                        <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155", borderRadius: 10, color: "#f8fafc" }} />
                        <Line type="monotone" dataKey="score" stroke="#6366f1" strokeWidth={2.5} dot={{ r: 3 }} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                )}

                {/* Subject performance */}
                {subjectPerf.length > 0 && (
                  <div className="premium-card" style={{ marginBottom: 16 }}>
                    <h4 style={{ marginBottom: 12 }}>📚 Subject Performance</h4>
                    <ResponsiveContainer width="100%" height={200}>
                      <BarChart data={subjectPerf} barCategoryGap="30%" barGap={3}>
                        <CartesianGrid stroke="#334155" strokeDasharray="3 3" />
                        <XAxis dataKey="subject" stroke="#94a3b8" tick={{ fontSize: 10 }} />
                        <YAxis domain={[0, 100]} stroke="#94a3b8" />
                        <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155", borderRadius: 10, color: "#f8fafc" }} />
                        <Legend wrapperStyle={{ color: "#94a3b8", fontSize: "11px" }} />
                        <Bar dataKey="Best"    fill="#10b981" radius={[5,5,0,0]} />
                        <Bar dataKey="Average" fill="#3b82f6" radius={[5,5,0,0]} />
                        <Bar dataKey="Latest"  fill="#f59e0b" radius={[5,5,0,0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}

                {/* Recent test activity */}
                <div className="premium-card">
                  <h4 style={{ marginBottom: 12 }}>🕘 Recent Tests</h4>
                  {(selected.recent_history || []).length === 0 ? (
                    <p style={{ color: "var(--muted)", fontSize: ".85rem" }}>No tests taken yet.</p>
                  ) : (
                    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                      {(selected.recent_history || []).slice(0, 8).map((h, i) => {
                        const pct = Number(h.percentage || 0);
                        const pctColor = pct >= 75 ? "#10b981" : pct >= 50 ? "#f59e0b" : "#ef4444";
                        return (
                          <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center",
                            padding: "8px 10px", borderRadius: 8, background: "rgba(99,102,241,.04)", border: "1px solid var(--border)" }}>
                            <div>
                              <div style={{ fontWeight: 600, fontSize: ".85rem" }}>{h.subject}</div>
                              <div style={{ fontSize: ".72rem", color: "var(--muted)" }}>
                                {h.chapter} · {(h.created_at || "").slice(0, 10)}
                              </div>
                            </div>
                            <span style={{ fontWeight: 800, fontSize: ".9rem", color: pctColor }}>{pct}%</span>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
