import { useEffect, useState } from "react";
import {
  getProductCatalogue,
  setGradeVisibility,
  setProgramVisibility,
} from "../api/productCatalogue";

/** Inline toggle switch component */
function Toggle({ enabled, onChange, disabled = false }) {
  return (
    <div
      onClick={() => !disabled && onChange(!enabled)}
      style={{
        width: 48,
        height: 26,
        borderRadius: 13,
        background: enabled ? "var(--accent, #2563eb)" : "#4b5563",
        position: "relative",
        cursor: disabled ? "not-allowed" : "pointer",
        transition: "background 0.2s",
        flexShrink: 0,
        opacity: disabled ? 0.5 : 1,
      }}
    >
      <div
        style={{
          position: "absolute",
          top: 3,
          left: enabled ? 25 : 3,
          width: 20,
          height: 20,
          borderRadius: "50%",
          background: "#fff",
          transition: "left 0.2s",
          boxShadow: "0 1px 4px rgba(0,0,0,0.25)",
        }}
      />
    </div>
  );
}

/** Status pill */
function Pill({ visible }) {
  return (
    <span
      className="status-pill"
      style={{
        background: visible ? "#22c55e" : "#4b5563",
        color: "#fff",
        fontSize: "0.75rem",
        padding: "2px 10px",
      }}
    >
      {visible ? "LIVE" : "HIDDEN"}
    </span>
  );
}

export default function AdminProductCataloguePage({ user }) {
  /** Admin page — manage which grades and coaching programs are visible to students. */
  const [catalogue, setCatalogue] = useState(null);
  const [loading, setLoading]     = useState(true);
  const [saving, setSaving]       = useState(null); // key being saved
  const [message, setMessage]     = useState("");
  const [error, setError]         = useState("");

  async function load() {
    setLoading(true);
    try {
      const data = await getProductCatalogue();
      setCatalogue(data.catalogue);
    } catch (err) {
      setError(err.message || "Could not load product catalogue.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (user?.accessToken) load();
  }, [user?.accessToken]);

  async function handleGradeToggle(grade, visible) {
    setSaving(grade);
    setMessage(""); setError("");
    try {
      const data = await setGradeVisibility(grade, visible);
      setCatalogue(data.catalogue);
      setMessage(data.message);
    } catch (err) {
      setError(err.message || "Failed to update grade.");
    } finally {
      setSaving(null);
    }
  }

  async function handleProgramToggle(program, visible) {
    setSaving(program);
    setMessage(""); setError("");
    try {
      const data = await setProgramVisibility(program, visible);
      setCatalogue(data.catalogue);
      setMessage(data.message);
    } catch (err) {
      setError(err.message || "Failed to update program.");
    } finally {
      setSaving(null);
    }
  }

  if (loading) return <p>Loading product catalogue…</p>;

  const grades   = Object.entries(catalogue?.grades || {});
  const programs = Object.entries(catalogue?.coaching_programs || {});

  const liveGrades   = grades.filter(([, v]) => v.visible).length;
  const hiddenGrades = grades.filter(([, v]) => !v.visible).length;

  return (
    <div className="premium-page">

      {/* ── Header ──────────────────────────────────────────────────────── */}
      <section className="premium-section">
        <div className="premium-header">
          <p className="eyebrow">Admin — Product Management</p>
          <h2>📦 Product Catalogue</h2>
          <p>
            Control which grades, boards, and coaching programs are visible to
            students and parents. Hidden items exist fully in the codebase but
            are not shown anywhere in the student or parent UI until you toggle
            them on here.
          </p>
        </div>

        {/* Overview pills */}
        <div className="admin-overview-grid">
          <div className="admin-overview-card">
            <span>Live Grades</span>
            <strong style={{ color: "#22c55e" }}>{liveGrades}</strong>
          </div>
          <div className="admin-overview-card">
            <span>Hidden Grades</span>
            <strong style={{ color: "#f59e0b" }}>{hiddenGrades}</strong>
          </div>
          <div className="admin-overview-card">
            <span>Coaching Programs</span>
            <strong>{programs.length}</strong>
            <small>{programs.filter(([, v]) => v.visible).length} live</small>
          </div>
        </div>

        {message && <div className="info-box" style={{ marginTop: 16 }}>{message}</div>}
        {error   && <div className="error-box" style={{ marginTop: 16 }}>{error}</div>}
      </section>

      {/* ── Grades & Boards ──────────────────────────────────────────────── */}
      <section className="premium-section">
        <div className="premium-header">
          <p className="eyebrow">Section A</p>
          <h3>🎓 Grades & Boards</h3>
          <p>
            Grade 1–10 are live. Grade 11 and Grade 12 are ready in the codebase
            but hidden until NCERT content is uploaded and prewarmed.
          </p>
        </div>

        <div className="premium-card" style={{ padding: 0, overflow: "hidden" }}>
          {/* Table header */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1.5fr 1.5fr 1fr 1fr 80px",
              gap: 0,
              background: "var(--accent, #2563eb)",
              padding: "10px 20px",
            }}
          >
            {["Grade", "Board", "Streams", "Status", "Visible"].map((h) => (
              <span key={h} style={{ fontSize: "0.8rem", fontWeight: 700, color: "#fff" }}>{h}</span>
            ))}
          </div>

          {grades.map(([grade, info], idx) => {
            const isHigherGrade = grade === "Grade 11" || grade === "Grade 12";
            const rowBg = idx % 2 === 0 ? "var(--surface, #1e293b)" : "var(--surface2, #162136)";
            return (
              <div
                key={grade}
                style={{
                  display: "grid",
                  gridTemplateColumns: "1.5fr 1.5fr 1fr 1fr 80px",
                  gap: 0,
                  background: rowBg,
                  padding: "12px 20px",
                  alignItems: "center",
                  borderTop: "1px solid rgba(255,255,255,0.05)",
                }}
              >
                <span style={{ fontWeight: isHigherGrade ? 700 : 400, color: isHigherGrade ? "#fbbf24" : "#fff" }}>
                  {grade}
                  {isHigherGrade && (
                    <span style={{ marginLeft: 8, fontSize: "0.7rem", color: "#fbbf24", background: "rgba(251,191,36,0.15)", padding: "1px 6px", borderRadius: 4 }}>
                      NEW
                    </span>
                  )}
                </span>
                <span style={{ color: "#cbd5e1", fontSize: "0.85rem" }}>
                  {(info.boards || ["CBSE"]).join(", ")}
                </span>
                <span style={{ color: "#64748b", fontSize: "0.82rem" }}>
                  {(info.streams || []).length > 0
                    ? info.streams.join(" · ")
                    : "—"}
                </span>
                <Pill visible={info.visible} />
                <Toggle
                  enabled={info.visible}
                  disabled={saving === grade}
                  onChange={(val) => handleGradeToggle(grade, val)}
                />
              </div>
            );
          })}
        </div>

        <div className="info-box" style={{ marginTop: 12, fontSize: "0.83rem" }}>
          ⚠️ <strong>Before making Grade 11 or 12 visible:</strong> upload NCERT textbooks
          for all subjects via the RAG Upload page, then prewarm lessons and the question
          bank via Cache Management. Only then toggle visible.
        </div>
      </section>

      {/* ── Coaching Programs ────────────────────────────────────────────── */}
      <section className="premium-section">
        <div className="premium-header">
          <p className="eyebrow">Section B</p>
          <h3>🏆 Coaching Programs (Entrance Exam Prep)</h3>
          <p>
            JEE, NEET, and CUET preparation modules. All hidden until dedicated
            subject content is uploaded and the coaching-mode UI is built.
          </p>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))", gap: 20 }}>
          {programs.map(([key, info]) => (
            <div key={key} className="premium-card">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
                <div>
                  <h3 style={{ margin: 0, marginBottom: 4 }}>{info.full_name || key}</h3>
                  <p style={{ margin: 0, color: "#64748b", fontSize: "0.85rem" }}>{info.description}</p>
                </div>
                <Pill visible={info.visible} />
              </div>

              <div style={{ marginBottom: 12 }}>
                <p style={{ fontSize: "0.8rem", color: "#64748b", margin: "0 0 4px" }}>Subjects</p>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {(info.subjects || []).map((subj) => (
                    <span
                      key={subj}
                      style={{
                        background: "rgba(37,99,235,0.15)",
                        color: "#93c5fd",
                        borderRadius: 4,
                        padding: "2px 8px",
                        fontSize: "0.78rem",
                      }}
                    >
                      {subj}
                    </span>
                  ))}
                </div>
              </div>

              <div style={{ marginBottom: 16 }}>
                <p style={{ fontSize: "0.8rem", color: "#64748b", margin: "0 0 4px" }}>Target Grades</p>
                <span style={{ fontSize: "0.85rem", color: "#cbd5e1" }}>
                  {(info.target_grades || []).join(", ")}
                </span>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <Toggle
                  enabled={info.visible}
                  disabled={saving === key}
                  onChange={(val) => handleProgramToggle(key, val)}
                />
                <span style={{ fontSize: "0.85rem", color: info.visible ? "#22c55e" : "#6b7280" }}>
                  {saving === key
                    ? "Saving…"
                    : info.visible
                    ? "Visible to students"
                    : "Hidden from students"}
                </span>
              </div>
            </div>
          ))}
        </div>

        <div className="info-box" style={{ marginTop: 16, fontSize: "0.83rem" }}>
          🚧 <strong>Content roadmap for coaching programs:</strong>
          Upload topic-wise Physics / Chemistry / Maths / Biology PDFs →
          Prewarm via Cache Management → Build JEE/NEET mock format (180Q with
          negative marking) → Toggle visible here when ready.
        </div>
      </section>

      {/* ── Roadmap ──────────────────────────────────────────────────────── */}
      <section className="premium-section">
        <div className="premium-header">
          <p className="eyebrow">Section C</p>
          <h3>🗺️ Feature Readiness Roadmap</h3>
        </div>

        <div className="premium-card">
          {[
            { phase: "Now — Live",       color: "#22c55e", items: ["Grade 1–10 CBSE", "SOF Olympiad (NSO/IMO/IEO)", "Ask Doubt (RAG)", "42,000+ Question Bank", "Parent Dashboard", "Teacher Module"] },
            { phase: "Phase 2 (Ready to unlock)", color: "#f59e0b", items: ["Grade 11 CBSE — Science, Commerce, Arts", "Grade 12 CBSE — Science, Commerce, Arts", "Stream selection at signup"] },
            { phase: "Phase 3 (Content + UI needed)", color: "#a78bfa", items: ["JEE Mains + Advanced prep", "NEET UG prep", "CUET prep", "Negative marking mock tests", "Topic-wise progress tracking"] },
            { phase: "Phase 4 (Future)",  color: "#64748b", items: ["ICSE + State Board content", "Vernacular (Hindi/Marathi/Tamil) UI", "School white-labelling", "Mobile app (native)"] },
          ].map(({ phase, color, items }) => (
            <div key={phase} style={{ marginBottom: 20 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
                <div style={{ width: 10, height: 10, borderRadius: "50%", background: color, flexShrink: 0 }} />
                <strong style={{ color }}>{phase}</strong>
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8, paddingLeft: 20 }}>
                {items.map((item) => (
                  <span
                    key={item}
                    style={{
                      background: "rgba(255,255,255,0.06)",
                      color: "#cbd5e1",
                      borderRadius: 4,
                      padding: "3px 10px",
                      fontSize: "0.82rem",
                    }}
                  >
                    {item}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

    </div>
  );
}
