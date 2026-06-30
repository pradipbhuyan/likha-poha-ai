/**
 * AdminLessonExperienceLabPage.jsx — Admin Lesson Experience Lab
 * ─────────────────────────────────────────────────────────────────────────────
 * Prototype for the improved student lesson UX.
 * Admin-only — never modifies live lesson data.
 * ─────────────────────────────────────────────────────────────────────────────
 */
import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import remarkGfm from "remark-gfm";
import {
  listLabLessons,
  getLabLesson,
  getLabVisuals,
} from "../api/lessonLab";

// ── Status colours ────────────────────────────────────────────────────────────
const STATUS_BADGE = {
  pass:     { bg: "rgba(34,197,94,.12)",  color: "#166534", label: "✓ Pass" },
  warning:  { bg: "rgba(245,158,11,.12)", color: "#92400e", label: "⚠ Warning" },
  critical: { bg: "rgba(239,68,68,.12)",  color: "#dc2626", label: "✗ Critical" },
};

const PREVIEW_MODES = [
  { key: "sectioned",      label: "Student View" },
  { key: "structure_only", label: "Structure" },
  { key: "summary_only",   label: "Summary" },
];

const inp = {
  background: "var(--surface2,#f8fafc)", border: "1px solid var(--border,#e5e7eb)",
  borderRadius: 8, padding: "7px 10px", fontFamily: "inherit",
  fontSize: ".82rem", color: "var(--text,#374151)", width: "100%",
};
const card = (extra = {}) => ({
  background: "var(--panel,#fff)", border: "1px solid var(--border,#e5e7eb)",
  borderRadius: 12, padding: "14px 16px", ...extra,
});

// ── Small helper components ───────────────────────────────────────────────────

function ScoreChip({ value, label, color = "#6366f1" }) {
  return (
    <div style={{ textAlign: "center", minWidth: 60 }}>
      <div style={{ fontSize: "1.1rem", fontWeight: 800, color }}>{value ?? "—"}</div>
      <div style={{ fontSize: ".65rem", color: "#94a3b8" }}>{label}</div>
    </div>
  );
}

function IssueBadge({ severity, message }) {
  const s = STATUS_BADGE[severity] || STATUS_BADGE.warning;
  return (
    <div style={{
      padding: "5px 10px", borderRadius: 7, marginBottom: 5,
      background: s.bg, color: s.color, fontSize: ".75rem",
      borderLeft: `3px solid ${s.color}`,
    }}>
      <strong style={{ fontSize: ".7rem", textTransform: "uppercase" }}>[{severity}]</strong>{" "}
      {message}
    </div>
  );
}

function ExpandableSection({ title, children, defaultOpen = false, issueCount = 0 }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div style={{ ...card(), marginBottom: 10 }}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          width: "100%", display: "flex", alignItems: "center", justifyContent: "space-between",
          background: "none", border: "none", cursor: "pointer", fontFamily: "inherit",
          padding: 0, textAlign: "left",
        }}
      >
        <span style={{ fontWeight: 700, fontSize: ".85rem", color: "var(--text,#1e293b)" }}>
          {title}
        </span>
        <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
          {issueCount > 0 && (
            <span style={{ background: "#ef4444", color: "#fff", borderRadius: 99, fontSize: ".65rem", padding: "1px 6px", fontWeight: 800 }}>
              {issueCount}
            </span>
          )}
          <span style={{ color: "#94a3b8", fontSize: ".9rem" }}>{open ? "▲" : "▼"}</span>
        </span>
      </button>
      {open && <div style={{ marginTop: 12 }}>{children}</div>}
    </div>
  );
}

function MCQCard({ mcq }) {
  const [selected, setSelected] = useState(null);
  const [revealed, setRevealed] = useState(false);
  // Try to detect options: lines like "A. ..." or "A) ..."
  const lines = (mcq || "").split(/\n/).map(l => l.trim()).filter(Boolean);
  const question = lines[0] || mcq;
  const options = lines.slice(1).filter(l => /^[A-D][).:]./.test(l));

  if (options.length === 0) {
    return (
      <div style={{ ...card({ background: "var(--surface2,#f8fafc)" }), fontSize: ".82rem" }}>
        <strong>Practice Question</strong>
        <p style={{ margin: "6px 0 0" }}>{question}</p>
      </div>
    );
  }

  return (
    <div style={{ ...card({ background: "var(--surface2,#f8fafc)" }) }}>
      <strong style={{ fontSize: ".85rem" }}>Practice Question</strong>
      <p style={{ margin: "8px 0", fontSize: ".85rem" }}>{question}</p>
      <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
        {options.map((opt, i) => (
          <button key={i}
            onClick={() => setSelected(opt)}
            style={{
              textAlign: "left", padding: "7px 12px", borderRadius: 8,
              border: `1.5px solid ${selected === opt ? "#6366f1" : "var(--border,#e5e7eb)"}`,
              background: selected === opt ? "rgba(99,102,241,.1)" : "var(--panel,#fff)",
              fontFamily: "inherit", fontSize: ".82rem", cursor: "pointer",
            }}
          >{opt}</button>
        ))}
      </div>
      {selected && !revealed && (
        <button onClick={() => setRevealed(true)} style={{ marginTop: 10, padding: "5px 12px", borderRadius: 7, border: "none", background: "#6366f1", color: "#fff", fontFamily: "inherit", fontSize: ".78rem", cursor: "pointer" }}>
          Check Answer
        </button>
      )}
      {revealed && (
        <div style={{ marginTop: 8, padding: "8px 12px", borderRadius: 8, background: "rgba(34,197,94,.08)", border: "1px solid rgba(34,197,94,.3)", fontSize: ".78rem", color: "#166534" }}>
          Answer selected: {selected}<br/>
          <span style={{ fontSize: ".72rem", color: "#64748b" }}>This is a prototype — scoring not persisted.</span>
        </div>
      )}
    </div>
  );
}

// ── Step Sidebar ──────────────────────────────────────────────────────────────

function StepSidebar({ steps, selectedIdx, onSelect }) {
  return (
    <div data-testid="step-sidebar" style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      {steps.map((step, i) => {
        const s = STATUS_BADGE[step.status] || STATUS_BADGE.pass;
        const isActive = i === selectedIdx;
        return (
          <button key={i}
            data-testid={`step-sidebar-item-${i}`}
            onClick={() => onSelect(i)}
            style={{
              textAlign: "left", padding: "8px 12px", borderRadius: 9,
              border: `1.5px solid ${isActive ? "#6366f1" : "var(--border,#e5e7eb)"}`,
              background: isActive ? "rgba(99,102,241,.1)" : "var(--panel,#fff)",
              fontFamily: "inherit", cursor: "pointer",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
              <span style={{ width: 7, height: 7, borderRadius: "50%", background: s.color, flexShrink: 0 }} />
              <span style={{ fontSize: ".78rem", fontWeight: isActive ? 700 : 500, color: "var(--text,#374151)", flex: 1, lineHeight: 1.3 }}>
                Step {step.step_number}: {step.step_title}
              </span>
            </div>
            <div style={{ display: "flex", gap: 8, marginTop: 5, flexWrap: "wrap" }}>
              <span style={{ fontSize: ".65rem", color: "#94a3b8" }}>{step.word_count} w</span>
              <span style={{ fontSize: ".65rem", color: "#94a3b8" }}>~{step.estimated_minutes}m</span>
              <span style={{ fontSize: ".65rem", color: "#6366f1" }}>U:{step.uniqueness_score}</span>
              <span style={{ fontSize: ".65rem", color: "#10b981" }}>D:{step.depth_progression_score}</span>
              {(step.issues || []).length > 0 && (
                <span style={{ fontSize: ".65rem", background: "#ef4444", color: "#fff", borderRadius: 99, padding: "0 5px", fontWeight: 800 }}>
                  {step.issues.length}
                </span>
              )}
            </div>
          </button>
        );
      })}
    </div>
  );
}

// ── Lesson Content View ───────────────────────────────────────────────────────

function LessonContentView({ step, showRaw, showAudit }) {
  if (!step) return <p style={{ color: "#94a3b8" }}>Select a step to preview.</p>;

  const sections = step.normalized_sections || {};
  const sectionKeys = Object.keys(sections);
  const hasIssues = (step.issues || []).length > 0;

  const SECTION_ICONS = {
    introduction: "📖",
    "what you will learn": "🎯",
    "simple explanation": "💡",
    "step-by-step breakdown": "🔢",
    "worked example": "✏️",
    "common mistake": "⚠️",
    "quick check question": "❓",
    summary: "📋",
  };

  return (
    <div data-testid="lesson-content-view">
      {/* Step header */}
      <div style={{ ...card(), marginBottom: 14 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <h3 style={{ margin: 0, fontSize: ".95rem", fontWeight: 800 }}>
            Step {step.step_number}: {step.step_title}
          </h3>
          <span style={{
            padding: "2px 8px", borderRadius: 99, fontSize: ".72rem", fontWeight: 700,
            background: STATUS_BADGE[step.status]?.bg || "#f1f5f9",
            color: STATUS_BADGE[step.status]?.color || "#64748b",
          }}>
            {STATUS_BADGE[step.status]?.label || step.status}
          </span>
        </div>
        <div style={{ display: "flex", gap: 16, marginTop: 10, flexWrap: "wrap" }}>
          <ScoreChip value={step.overall_step_score} label="Overall" color="#6366f1" />
          <ScoreChip value={step.uniqueness_score} label="Unique" color="#8b5cf6" />
          <ScoreChip value={step.depth_progression_score} label="Depth" color="#10b981" />
          <ScoreChip value={step.completeness_score} label="Complete" color="#0ea5e9" />
          <ScoreChip value={step.estimated_minutes} label="Min" color="#f59e0b" />
        </div>
      </div>

      {/* Audit issues */}
      {showAudit && hasIssues && (
        <div style={{ ...card({ background: "rgba(239,68,68,.04)" }), marginBottom: 14 }}>
          <strong style={{ fontSize: ".82rem", color: "#dc2626" }}>
            ⚠ {step.issues.length} audit issue{step.issues.length > 1 ? "s" : ""}
          </strong>
          <div style={{ marginTop: 8 }}>
            {step.issues.map((issue, i) => (
              <IssueBadge key={i} severity={issue.severity} message={issue.issue_message} />
            ))}
          </div>
        </div>
      )}

      {/* Raw content toggle */}
      {showRaw ? (
        <ExpandableSection title="Raw Lesson Content" defaultOpen>
          <pre style={{ whiteSpace: "pre-wrap", wordBreak: "break-word", fontSize: ".75rem", color: "var(--text,#374151)", margin: 0 }}>
            {step.raw_content}
          </pre>
        </ExpandableSection>
      ) : (
        <>
          {/* Sectioned content */}
          {sectionKeys.length > 0 ? (
            sectionKeys.map(key => (
              <ExpandableSection
                key={key}
                title={`${SECTION_ICONS[key] || "📄"} ${key.replace(/\b\w/g, c => c.toUpperCase())}`}
                defaultOpen={key === "introduction" || key === "simple explanation"}
                issueCount={0}
              >
                <div className="markdown-content" style={{ fontSize: ".85rem", lineHeight: 1.7 }}>
                  <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]}>
                    {sections[key]}
                  </ReactMarkdown>
                </div>
              </ExpandableSection>
            ))
          ) : (
            <div style={{ ...card(), marginBottom: 14 }}>
              <div className="markdown-content" style={{ fontSize: ".85rem", lineHeight: 1.7 }}>
                <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]}>
                  {step.raw_content}
                </ReactMarkdown>
              </div>
            </div>
          )}

          {/* Formulas */}
          {(step.formulas || []).length > 0 && (
            <ExpandableSection title="📐 Formulas">
              {step.formulas.map((f, i) => (
                <div key={i} style={{ padding: "4px 10px", borderRadius: 6, background: "var(--surface2,#f8fafc)", marginBottom: 5, fontFamily: "monospace", fontSize: ".82rem" }}>
                  {f}
                </div>
              ))}
            </ExpandableSection>
          )}

          {/* MCQs */}
          {(step.mcqs || []).length > 0 && (
            <ExpandableSection title="❓ Practice Questions">
              {step.mcqs.map((mcq, i) => <MCQCard key={i} mcq={mcq} />)}
            </ExpandableSection>
          )}

          {/* Summary */}
          {step.summary && (
            <ExpandableSection title="📋 Summary">
              <div style={{ fontSize: ".85rem", lineHeight: 1.7 }}>
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{step.summary}</ReactMarkdown>
              </div>
            </ExpandableSection>
          )}
        </>
      )}
    </div>
  );
}

// ── Visual Panel ──────────────────────────────────────────────────────────────

function VisualPanel({ visuals }) {
  if (!visuals) return null;
  return (
    <div data-testid="visual-panel">
      {visuals.available && visuals.visuals.length > 0 ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {visuals.visuals.map(v => (
            <div key={v.id} style={{ ...card() }}>
              {v.image_url_or_asset_ref && (
                <img src={v.image_url_or_asset_ref} alt={v.caption || v.title}
                  style={{ width: "100%", borderRadius: 8, marginBottom: 8, objectFit: "contain", maxHeight: 200 }} />
              )}
              <strong style={{ fontSize: ".82rem" }}>{v.title}</strong>
              {v.caption && <p style={{ fontSize: ".75rem", color: "#64748b", margin: "4px 0 0" }}>{v.caption}</p>}
              {v.matched_topic && (
                <div style={{ fontSize: ".7rem", color: "#6366f1", marginTop: 4 }}>
                  Matched topic: {v.matched_topic}
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div data-testid="visual-empty-state" style={{ padding: "24px 16px", textAlign: "center", color: "#94a3b8", fontSize: ".82rem", background: "var(--surface2,#f8fafc)", borderRadius: 10 }}>
          <div style={{ fontSize: "2rem", marginBottom: 8 }}>🖼️</div>
          <div style={{ fontWeight: 600 }}>
            {visuals.empty_state || "No textbook visuals linked yet."}
          </div>
          <div style={{ fontSize: ".72rem", marginTop: 6 }}>
            Upload textbook visual assets in RAG Upload to see them here.
          </div>
        </div>
      )}
    </div>
  );
}

// ── Accessibility Controls ────────────────────────────────────────────────────

function AccessibilityBar({ a11y, setA11y }) {
  return (
    <div data-testid="accessibility-controls" style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center", padding: "8px 12px", background: "var(--surface2,#f8fafc)", borderRadius: 8, marginBottom: 14 }}>
      <span style={{ fontSize: ".72rem", color: "#94a3b8", fontWeight: 600 }}>ACCESSIBILITY</span>
      <label style={{ fontSize: ".72rem", display: "flex", alignItems: "center", gap: 5, cursor: "pointer" }}>
        Font
        <select value={a11y.fontSize} onChange={e => setA11y(p => ({ ...p, fontSize: e.target.value }))}
          style={{ fontSize: ".72rem", borderRadius: 5, border: "1px solid var(--border)", padding: "2px 6px", fontFamily: "inherit" }}>
          <option value="14px">Small</option>
          <option value="16px">Normal</option>
          <option value="18px">Large</option>
          <option value="20px">X-Large</option>
        </select>
      </label>
      <label style={{ fontSize: ".72rem", display: "flex", alignItems: "center", gap: 5, cursor: "pointer" }}>
        Spacing
        <select value={a11y.lineHeight} onChange={e => setA11y(p => ({ ...p, lineHeight: e.target.value }))}
          style={{ fontSize: ".72rem", borderRadius: 5, border: "1px solid var(--border)", padding: "2px 6px", fontFamily: "inherit" }}>
          <option value="1.5">Normal</option>
          <option value="1.8">Relaxed</option>
          <option value="2.2">Wide</option>
        </select>
      </label>
      <label style={{ fontSize: ".72rem", display: "flex", alignItems: "center", gap: 5, cursor: "pointer" }}>
        <input type="checkbox" checked={a11y.focusMode}
          onChange={e => setA11y(p => ({ ...p, focusMode: e.target.checked }))} />
        Focus Mode
      </label>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function AdminLessonExperienceLabPage({ user }) { // eslint-disable-line no-unused-vars
  const [labData, setLabData]     = useState(null);
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState("");

  // Selectors
  const [selGrade,   setSelGrade]   = useState("");
  const [selSubject, setSelSubject] = useState("");
  const [selChapter, setSelChapter] = useState("");
  const [selLesson,  setSelLesson]  = useState("");

  // Lesson detail
  const [lessonDetail, setLessonDetail] = useState(null);
  const [lessonLoading, setLessonLoading] = useState(false);
  const [selectedStepIdx, setSelectedStepIdx] = useState(0);

  // Visuals
  const [visuals, setVisuals] = useState(null);

  // Toggles
  const [previewMode, setPreviewMode] = useState("sectioned");
  const [showRaw,     setShowRaw]     = useState(false);
  const [showAudit,   setShowAudit]   = useState(true);
  const [showVisuals, setShowVisuals] = useState(false);

  // Accessibility
  const [a11y, setA11y] = useState({ fontSize: "16px", lineHeight: "1.7", focusMode: false });

  // Notes (local only, not persisted to backend)
  const [notes, setNotes] = useState(() => {
    try { return JSON.parse(localStorage.getItem("lessonLabNotes") || "{}"); } catch { return {}; }
  });

  useEffect(() => {
    setLoading(true);
    listLabLessons()
      .then(d => setLabData(d))
      .catch(() => setError("Could not load lesson list — check backend."))
      .finally(() => setLoading(false));
  }, []);

  async function loadLesson(lessonId) {
    if (!lessonId) return;
    setLessonLoading(true);
    setLessonDetail(null);
    setVisuals(null);
    setSelectedStepIdx(0);
    try {
      const d = await getLabLesson(lessonId);
      setLessonDetail(d);
    } catch (err) {
      setError(err.message || "Could not load lesson.");
    } finally {
      setLessonLoading(false);
    }
  }

  async function loadVisuals() {
    if (!selGrade && !selSubject && !selChapter && !selLesson) return;
    try {
      const v = await getLabVisuals({ grade: selGrade, subject: selSubject, chapter: selChapter, lesson_id: selLesson });
      setVisuals(v);
    } catch {
      setVisuals({ available: false, visuals: [], empty_state: "Could not load visuals." });
    }
  }

  useEffect(() => {
    if (selLesson) loadLesson(selLesson);
  }, [selLesson]); // eslint-disable-line -- loadLesson is stable

  useEffect(() => {
    if (showVisuals && selLesson) loadVisuals();
  }, [showVisuals, selLesson]); // eslint-disable-line -- loadVisuals is stable

  function saveNote(key, value) {
    const updated = { ...notes, [key]: value };
    setNotes(updated);
    try { localStorage.setItem("lessonLabNotes", JSON.stringify(updated)); } catch { /* ok */ }
  }

  const grades   = labData?.grades   || [];
  const subjects = (labData?.lessons || []).filter(l => !selGrade || l.grade === selGrade)
    .map(l => l.subject).filter((v, i, a) => a.indexOf(v) === i).sort();
  const chapters = (labData?.lessons || []).filter(l => (!selGrade || l.grade === selGrade) && (!selSubject || l.subject === selSubject))
    .map(l => l.chapter).filter((v, i, a) => a.indexOf(v) === i).sort();
  const lessons  = (labData?.lessons || []).filter(l =>
    (!selGrade   || l.grade   === selGrade) &&
    (!selSubject || l.subject === selSubject) &&
    (!selChapter || l.chapter === selChapter)
  );

  const steps = lessonDetail?.steps || [];
  const currentStep = steps[selectedStepIdx] || null;
  const auditSummary = lessonDetail?.audit_summary || null;

  const labBannerStyle = {
    display: "flex", alignItems: "center", gap: 10,
    padding: "8px 14px", borderRadius: 8, marginBottom: 12,
    background: "rgba(99,102,241,.08)", border: "1px solid rgba(99,102,241,.25)",
    fontSize: ".78rem", color: "#6366f1",
  };

  return (
    <div data-testid="admin-lesson-experience-lab" style={{ maxWidth: 1280, margin: "0 auto", padding: "0 14px 60px", fontFamily: "inherit" }}>

      {/* Lab banner */}
      <div style={labBannerStyle}>
        🧪 <strong>Admin Lesson Experience Lab</strong> — prototype only. No changes are made to live lesson content.
      </div>

      {/* Page header */}
      <div style={{ marginBottom: 16 }}>
        <h2 style={{ margin: "0 0 4px", fontSize: "1.05rem", fontWeight: 800 }}>Lesson Experience Lab</h2>
        <p style={{ margin: 0, fontSize: ".82rem", color: "#64748b" }}>
          Preview existing lesson content in the improved student UX. Select a lesson, choose a view mode, and inspect step quality.
        </p>
      </div>

      {error && <div style={{ padding: "8px 12px", borderRadius: 8, background: "rgba(239,68,68,.08)", color: "#dc2626", fontSize: ".82rem", marginBottom: 12 }}>{error}</div>}

      <div style={{ display: "grid", gridTemplateColumns: "280px 1fr", gap: 16, alignItems: "start" }}>

        {/* ── Left selector panel ── */}
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <div style={card()}>
            <h4 style={{ margin: "0 0 12px", fontSize: ".85rem", fontWeight: 800 }}>Select Lesson</h4>

            {loading ? <p style={{ color: "#94a3b8", fontSize: ".8rem" }}>Loading lessons…</p> : (
              <>
                <label style={{ fontSize: ".75rem", fontWeight: 600, display: "block", marginBottom: 3 }}>Grade</label>
                <select value={selGrade} onChange={e => { setSelGrade(e.target.value); setSelSubject(""); setSelChapter(""); setSelLesson(""); }} style={{ ...inp, marginBottom: 8 }} data-testid="grade-select">
                  <option value="">All grades</option>
                  {grades.map(g => <option key={g}>{g}</option>)}
                </select>

                <label style={{ fontSize: ".75rem", fontWeight: 600, display: "block", marginBottom: 3 }}>Subject</label>
                <select value={selSubject} onChange={e => { setSelSubject(e.target.value); setSelChapter(""); setSelLesson(""); }} style={{ ...inp, marginBottom: 8 }} data-testid="subject-select">
                  <option value="">All subjects</option>
                  {subjects.map(s => <option key={s}>{s}</option>)}
                </select>

                <label style={{ fontSize: ".75rem", fontWeight: 600, display: "block", marginBottom: 3 }}>Chapter</label>
                <select value={selChapter} onChange={e => { setSelChapter(e.target.value); setSelLesson(""); }} style={{ ...inp, marginBottom: 8 }} data-testid="chapter-select">
                  <option value="">All chapters</option>
                  {chapters.map(c => <option key={c}>{c}</option>)}
                </select>

                <label style={{ fontSize: ".75rem", fontWeight: 600, display: "block", marginBottom: 3 }}>Lesson</label>
                <select value={selLesson} onChange={e => setSelLesson(e.target.value)} style={{ ...inp, marginBottom: 0 }} data-testid="lesson-select">
                  <option value="">Select a lesson…</option>
                  {lessons.map(l => (
                    <option key={l.lesson_id} value={l.lesson_id}>
                      {l.grade} | {l.subject} | {l.chapter}
                    </option>
                  ))}
                </select>
              </>
            )}
          </div>

          {/* Preview mode */}
          <div style={card()}>
            <h4 style={{ margin: "0 0 10px", fontSize: ".85rem", fontWeight: 800 }}>Preview Mode</h4>
            {PREVIEW_MODES.map(m => (
              <button key={m.key} onClick={() => setPreviewMode(m.key)}
                style={{
                  display: "block", width: "100%", textAlign: "left",
                  padding: "6px 10px", borderRadius: 7, marginBottom: 4,
                  border: `1.5px solid ${previewMode === m.key ? "#6366f1" : "var(--border,#e5e7eb)"}`,
                  background: previewMode === m.key ? "rgba(99,102,241,.1)" : "var(--panel,#fff)",
                  fontFamily: "inherit", fontSize: ".8rem", fontWeight: previewMode === m.key ? 700 : 400,
                  cursor: "pointer",
                }}
              >{m.label}</button>
            ))}
          </div>

          {/* Toggles */}
          <div style={card()}>
            <h4 style={{ margin: "0 0 10px", fontSize: ".85rem", fontWeight: 800 }}>View Options</h4>
            {[
              { key: "showRaw",    label: "Show raw content",  val: showRaw,    set: setShowRaw },
              { key: "showAudit", label: "Show audit issues", val: showAudit,  set: setShowAudit },
              { key: "showVis",   label: "Show visuals",      val: showVisuals, set: setShowVisuals },
            ].map(({ key, label, val, set }) => (
              <label key={key} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8, cursor: "pointer", fontSize: ".8rem" }}>
                <input type="checkbox" checked={val} onChange={e => set(e.target.checked)} />
                {label}
              </label>
            ))}
          </div>

          {/* Audit summary */}
          {auditSummary && (
            <div style={card()}>
              <h4 style={{ margin: "0 0 10px", fontSize: ".85rem", fontWeight: 800 }}>Audit Summary</h4>
              {[
                { label: "Overall", value: auditSummary.overall_step_sequence_score, color: "#6366f1" },
                { label: "Uniqueness", value: auditSummary.avg_step_uniqueness_score, color: "#8b5cf6" },
                { label: "Depth", value: auditSummary.depth_progression_score, color: "#10b981" },
              ].map(({ label, value, color }) => (
                <div key={label} style={{ display: "flex", justifyContent: "space-between", marginBottom: 5, fontSize: ".78rem" }}>
                  <span style={{ color: "#64748b" }}>{label}</span>
                  <span style={{ fontWeight: 700, color }}>{value ?? "—"}/100</span>
                </div>
              ))}
              {auditSummary.critical_issues > 0 && (
                <div style={{ marginTop: 6, padding: "4px 8px", borderRadius: 6, background: "rgba(239,68,68,.08)", color: "#dc2626", fontSize: ".72rem", fontWeight: 700 }}>
                  {auditSummary.critical_issues} critical · {auditSummary.high_issues} high
                </div>
              )}
            </div>
          )}
        </div>

        {/* ── Main preview area ── */}
        <div>
          {lessonLoading && (
            <div style={{ padding: 32, textAlign: "center", color: "#94a3b8" }}>Loading lesson…</div>
          )}

          {!lessonLoading && !lessonDetail && !selLesson && (
            <div style={{ ...card(), textAlign: "center", padding: "40px 20px", color: "#94a3b8" }}>
              <div style={{ fontSize: "2rem", marginBottom: 8 }}>🧪</div>
              <div style={{ fontWeight: 600, marginBottom: 6 }}>Select a lesson to begin</div>
              <div style={{ fontSize: ".82rem" }}>Choose a grade, subject, chapter, and lesson from the left panel.</div>
            </div>
          )}

          {!lessonLoading && lessonDetail && (
            <>
              {/* Lesson header */}
              <div style={{ ...card({ background: "linear-gradient(135deg,rgba(99,102,241,.06),rgba(139,92,246,.04))" }), marginBottom: 14 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 10 }}>
                  <div>
                    <h2 style={{ margin: 0, fontSize: "1rem", fontWeight: 800 }}>{lessonDetail.title}</h2>
                    <p style={{ margin: "4px 0 0", fontSize: ".78rem", color: "#64748b" }}>
                      {lessonDetail.grade} · {lessonDetail.subject} · {lessonDetail.total_steps} steps · ~{lessonDetail.total_estimated_minutes} min
                    </p>
                  </div>
                  {auditSummary && (
                    <div style={{ textAlign: "center" }}>
                      <div style={{ fontSize: "1.4rem", fontWeight: 800, color: auditSummary.overall_step_sequence_score >= 80 ? "#22c55e" : auditSummary.overall_step_sequence_score >= 60 ? "#f59e0b" : "#ef4444" }}>
                        {auditSummary.overall_step_sequence_score}
                      </div>
                      <div style={{ fontSize: ".65rem", color: "#94a3b8" }}>audit score</div>
                    </div>
                  )}
                </div>
              </div>

              <AccessibilityBar a11y={a11y} setA11y={setA11y} />

              {/* Two-column: step sidebar + content */}
              <div style={{ display: "grid", gridTemplateColumns: "200px 1fr", gap: 14, alignItems: "start" }}>
                <StepSidebar steps={steps} selectedIdx={selectedStepIdx} onSelect={setSelectedStepIdx} />

                <div style={{ fontSize: a11y.fontSize, lineHeight: a11y.lineHeight, maxWidth: a11y.focusMode ? 680 : "100%" }}>
                  <LessonContentView step={currentStep} showRaw={showRaw} showAudit={showAudit} />

                  {/* Visual panel */}
                  {showVisuals && (
                    <div style={{ marginTop: 14 }}>
                      <h4 style={{ margin: "0 0 10px", fontSize: ".88rem", fontWeight: 700 }}>Textbook Visuals</h4>
                      <VisualPanel visuals={visuals} />
                    </div>
                  )}

                  {/* Notes panel */}
                  <div style={{ ...card(), marginTop: 14 }}>
                    <h4 style={{ margin: "0 0 8px", fontSize: ".85rem", fontWeight: 700 }}>
                      Admin Notes <span style={{ fontSize: ".7rem", color: "#94a3b8", fontWeight: 400 }}>(local only, not saved to backend)</span>
                    </h4>
                    <textarea
                      rows={3}
                      value={notes[`${selLesson}-step-${selectedStepIdx}`] || ""}
                      onChange={e => saveNote(`${selLesson}-step-${selectedStepIdx}`, e.target.value)}
                      placeholder="Add notes about this step's lesson quality, UX observations…"
                      style={{ ...inp, resize: "vertical" }}
                    />
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
