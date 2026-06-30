/**
 * AdminLessonExperiencePage.jsx — Admin-only Lesson Experience Preview
 * ─────────────────────────────────────────────────────────────────────────────
 * Polished student-style lesson UI using real published content.
 * Admin-only, read-only, no audit/repair/QA controls shown.
 * Safe to later promote as Student Lesson v2.
 * ─────────────────────────────────────────────────────────────────────────────
 */
import { useEffect, useState, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import {
  getLessonCatalog,
  getLessonDetail,
  getLessonVisuals,
} from "../api/lessonExperience";

// ── Design tokens ─────────────────────────────────────────────────────────────

const ACCENT = {
  blue:   "#3b82f6",
  green:  "#22c55e",
  purple: "#8b5cf6",
  orange: "#f59e0b",
  indigo: "#6366f1",
};

const card = (extra = {}) => ({
  background: "var(--panel,#fff)",
  border: "1px solid var(--border,#e5e7eb)",
  borderRadius: 16,
  padding: "18px 20px",
  boxShadow: "0 1px 6px rgba(0,0,0,.06)",
  ...extra,
});

const inp = {
  background: "var(--surface2,#f8fafc)",
  border: "1px solid var(--border,#e5e7eb)",
  borderRadius: 10,
  padding: "8px 12px",
  fontFamily: "inherit",
  fontSize: ".85rem",
  color: "var(--text,#374151)",
  width: "100%",
};

// ── localStorage helpers ──────────────────────────────────────────────────────

const LS_NS = "admin_lesson_experience_notes";

function loadNotes() {
  try { return JSON.parse(localStorage.getItem(LS_NS) || "{}"); } catch { return {}; }
}
function saveNotes(notes) {
  try { localStorage.setItem(LS_NS, JSON.stringify(notes)); } catch { /* ok */ }
}

// ── Small components ──────────────────────────────────────────────────────────

function AdminBadge() {
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 5,
      padding: "3px 10px", borderRadius: 99,
      background: "rgba(99,102,241,.1)", color: "#6366f1",
      fontSize: ".72rem", fontWeight: 800, letterSpacing: ".04em",
    }}>
      ✦ ADMIN PREVIEW
    </span>
  );
}

function StepNav({ steps, selectedIdx, onSelect }) {
  return (
    <div data-testid="step-nav" style={{ display: "flex", flexDirection: "column", gap: 5 }}>
      {steps.map((step, i) => {
        const isActive = i === selectedIdx;
        return (
          <button key={i}
            data-testid={`step-nav-item-${i}`}
            onClick={() => onSelect(i)}
            style={{
              display: "flex", alignItems: "flex-start", gap: 10, textAlign: "left",
              padding: "10px 12px", borderRadius: 10,
              border: `1.5px solid ${isActive ? ACCENT.indigo : "var(--border,#e5e7eb)"}`,
              background: isActive ? "rgba(99,102,241,.08)" : "var(--panel,#fff)",
              fontFamily: "inherit", cursor: "pointer",
            }}
          >
            <span style={{
              minWidth: 24, height: 24, borderRadius: "50%", flexShrink: 0,
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: ".72rem", fontWeight: 800,
              background: isActive ? ACCENT.indigo : "var(--surface2,#f1f5f9)",
              color: isActive ? "#fff" : "#94a3b8",
            }}>
              {i + 1}
            </span>
            <div>
              <div style={{ fontSize: ".8rem", fontWeight: isActive ? 700 : 500, color: isActive ? ACCENT.indigo : "var(--text,#374151)", lineHeight: 1.3 }}>
                {step.step_title}
              </div>
              <div style={{ fontSize: ".68rem", color: "#94a3b8", marginTop: 2 }}>
                ~{step.estimated_minutes || 3}m
              </div>
            </div>
          </button>
        );
      })}
    </div>
  );
}

function ProgressBar({ current, total }) {
  const pct = total > 0 ? Math.round(((current + 1) / total) * 100) : 0;
  return (
    <div style={{ marginBottom: 4 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: ".72rem", color: "#94a3b8", marginBottom: 4 }}>
        <span>Step {current + 1} of {total}</span>
        <span>{pct}% previewed</span>
      </div>
      <div style={{ height: 6, background: "var(--border,#e5e7eb)", borderRadius: 99, overflow: "hidden" }}>
        <div style={{ width: `${pct}%`, height: "100%", background: `linear-gradient(90deg,${ACCENT.indigo},${ACCENT.purple})`, borderRadius: 99, transition: "width .4s ease" }} />
      </div>
    </div>
  );
}

function ObjectivesCard({ step }) {
  // Derive objectives from "what you will learn" section or first 3 sentences of content
  const sections = step?.normalized_sections || {};
  const objText = sections["what you will learn"] || sections["learning objectives"] || "";
  const objectives = objText
    ? objText.split(/\n/).map(l => l.replace(/^[-•*]\s*/, "").trim()).filter(l => l.length > 10).slice(0, 4)
    : [];

  return (
    <div data-testid="objectives-card" style={{ ...card({ background: "rgba(59,130,246,.04)", borderColor: "rgba(59,130,246,.2)" }), marginBottom: 14 }}>
      <h4 style={{ margin: "0 0 10px", fontSize: ".88rem", fontWeight: 800, color: ACCENT.blue }}>
        🎯 What You Will Learn
      </h4>
      {objectives.length > 0 ? (
        <ul style={{ margin: 0, paddingLeft: 18 }}>
          {objectives.map((obj, i) => (
            <li key={i} style={{ fontSize: ".85rem", lineHeight: 1.6, color: "var(--text,#374151)", marginBottom: 4 }}>
              {obj}
            </li>
          ))}
        </ul>
      ) : (
        <p style={{ fontSize: ".82rem", color: "#94a3b8", margin: 0 }}>
          Objectives are not available for this step yet.
        </p>
      )}
    </div>
  );
}

function CollapsibleSection({ title, icon, children, defaultOpen = false, accentColor = ACCENT.indigo }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div style={{ ...card(), marginBottom: 10 }}>
      <button onClick={() => setOpen(o => !o)} style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        width: "100%", background: "none", border: "none", cursor: "pointer",
        padding: 0, fontFamily: "inherit",
      }}>
        <span style={{ fontSize: ".88rem", fontWeight: 700, color: accentColor, display: "flex", alignItems: "center", gap: 8 }}>
          <span>{icon}</span> {title}
        </span>
        <span style={{ color: "#94a3b8", fontSize: ".85rem" }}>{open ? "▲" : "▼"}</span>
      </button>
      {open && (
        <div data-testid={`section-${title.toLowerCase().replace(/\s+/g, "-")}`}
          style={{ marginTop: 12, fontSize: ".88rem", lineHeight: 1.8, color: "var(--text,#374151)" }}>
          {children}
        </div>
      )}
    </div>
  );
}

function FormulaCard({ formulas }) {
  if (!formulas?.length) return null;
  return (
    <div data-testid="formula-card" style={{ ...card({ background: "rgba(245,158,11,.04)", borderColor: "rgba(245,158,11,.25)" }), marginBottom: 14 }}>
      <h4 style={{ margin: "0 0 10px", fontSize: ".85rem", fontWeight: 800, color: ACCENT.orange }}>📐 Key Formulas</h4>
      {formulas.map((f, i) => (
        <div key={i} style={{ marginBottom: 8, padding: "8px 12px", borderRadius: 8, background: "var(--surface2,#f8fafc)", fontFamily: "monospace", fontSize: ".85rem" }}>
          <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>{String(f)}</ReactMarkdown>
        </div>
      ))}
    </div>
  );
}

function MCQCard({ mcq }) {
  const [selected, setSelected] = useState(null);
  const [revealed, setRevealed] = useState(false);

  if (!mcq) return null;

  const lines = (typeof mcq === "string" ? mcq : (mcq.question || "")).split(/\n/).map(l => l.trim()).filter(Boolean);
  const question = lines[0] || "";
  const options = lines.slice(1).filter(l => /^[A-D][).:]./.test(l));
  const explanation = typeof mcq === "object" ? mcq.explanation : "";

  return (
    <div data-testid="mcq-card" style={{ ...card({ background: "rgba(34,197,94,.03)", borderColor: "rgba(34,197,94,.2)" }), marginBottom: 10 }}>
      <div style={{ fontSize: ".78rem", fontWeight: 700, color: ACCENT.green, marginBottom: 8 }}>✍️ Practice Question</div>
      <p style={{ margin: "0 0 10px", fontSize: ".88rem", lineHeight: 1.6, fontWeight: 600 }}>{question}</p>
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        {options.map((opt, i) => (
          <button key={i} onClick={() => setSelected(opt)} style={{
            textAlign: "left", padding: "8px 12px", borderRadius: 9,
            border: `1.5px solid ${selected === opt ? ACCENT.green : "var(--border,#e5e7eb)"}`,
            background: selected === opt ? "rgba(34,197,94,.08)" : "var(--panel,#fff)",
            fontFamily: "inherit", fontSize: ".85rem", cursor: "pointer",
          }}>{opt}</button>
        ))}
      </div>
      {options.length === 0 && <p style={{ color: "#94a3b8", fontSize: ".82rem" }}>No answer options detected.</p>}
      {selected && !revealed && (
        <button onClick={() => setRevealed(true)} style={{
          marginTop: 10, padding: "7px 16px", borderRadius: 8, border: "none",
          background: ACCENT.green, color: "#fff", fontFamily: "inherit", fontWeight: 700, fontSize: ".8rem", cursor: "pointer",
        }}>
          Check Answer
        </button>
      )}
      {revealed && (
        <div style={{ marginTop: 10, padding: "10px 14px", borderRadius: 10, background: "rgba(34,197,94,.08)", border: "1px solid rgba(34,197,94,.3)", fontSize: ".82rem" }}>
          <strong style={{ color: ACCENT.green }}>You selected:</strong> {selected}
          {explanation && <p style={{ margin: "6px 0 0", color: "#374151" }}>{explanation}</p>}
          <p style={{ margin: "4px 0 0", fontSize: ".72rem", color: "#94a3b8" }}>Admin preview only — not persisted.</p>
        </div>
      )}
    </div>
  );
}

function ConceptMap({ step }) {
  // Deterministic visual map: lesson title → section headings → formulas/examples
  const sections = Object.keys(step?.normalized_sections || {}).filter(k => !["what you will learn", "learning objectives"].includes(k));
  const formulas = (step?.formulas || []).slice(0, 3);

  return (
    <div data-testid="concept-map" style={{ ...card({ background: "var(--surface2,#f8fafc)" }), marginBottom: 14 }}>
      <h4 style={{ margin: "0 0 12px", fontSize: ".85rem", fontWeight: 800, color: ACCENT.purple }}>🗺️ Concept Map</h4>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center" }}>
        <div style={{ padding: "6px 14px", borderRadius: 99, background: ACCENT.purple, color: "#fff", fontSize: ".78rem", fontWeight: 700 }}>
          {step?.step_title || "Step"}
        </div>
        {sections.slice(0, 5).map((s, i) => (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <span style={{ color: "#94a3b8", fontSize: ".72rem" }}>→</span>
            <div style={{ padding: "4px 12px", borderRadius: 99, background: "rgba(139,92,246,.1)", color: ACCENT.purple, fontSize: ".75rem", fontWeight: 600 }}>
              {s.replace(/\b\w/g, c => c.toUpperCase())}
            </div>
          </div>
        ))}
        {formulas.length > 0 && formulas.map((f, i) => (
          <div key={`f${i}`} style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <span style={{ color: "#94a3b8", fontSize: ".72rem" }}>📐</span>
            <div style={{ padding: "3px 10px", borderRadius: 99, background: "rgba(245,158,11,.1)", color: ACCENT.orange, fontSize: ".72rem", fontFamily: "monospace" }}>
              {String(f).slice(0, 30)}{String(f).length > 30 ? "…" : ""}
            </div>
          </div>
        ))}
        {sections.length === 0 && (
          <p style={{ color: "#94a3b8", fontSize: ".78rem", margin: 0 }}>Select a step to see the concept map.</p>
        )}
      </div>
    </div>
  );
}

function VisualPanel({ visuals }) {
  if (!visuals || !visuals.available || !visuals.visuals?.length) {
    return (
      <div data-testid="visual-empty-state" style={{ padding: "20px 16px", textAlign: "center", background: "var(--surface2,#f8fafc)", borderRadius: 12, color: "#94a3b8", fontSize: ".85rem" }}>
        <div style={{ fontSize: "1.8rem", marginBottom: 6 }}>🖼️</div>
        <div style={{ fontWeight: 600, marginBottom: 4 }}>No linked visual yet.</div>
        <div style={{ fontSize: ".75rem" }}>Textbook visuals can be uploaded in the RAG Upload section.</div>
      </div>
    );
  }
  return (
    <div data-testid="visual-panel">
      {visuals.visuals.slice(0, 3).map(v => (
        <div key={v.id} style={{ ...card(), marginBottom: 10 }}>
          {v.asset_url && (
            <img src={v.asset_url} alt={v.caption || v.title || "Visual"} style={{ width: "100%", borderRadius: 10, marginBottom: 8, objectFit: "contain", maxHeight: 180 }} />
          )}
          <div style={{ fontSize: ".82rem", fontWeight: 700 }}>{v.title || "Textbook Visual"}</div>
          {v.caption && <div style={{ fontSize: ".75rem", color: "#64748b", marginTop: 3 }}>{v.caption}</div>}
          {v.matched_topic && <div style={{ fontSize: ".7rem", color: ACCENT.indigo, marginTop: 4 }}>📍 {v.matched_topic}</div>}
        </div>
      ))}
    </div>
  );
}

function GamificationPreview() {
  return (
    <div data-testid="gamification-preview" style={{ ...card({ background: "linear-gradient(135deg,rgba(99,102,241,.06),rgba(139,92,246,.04))" }), marginBottom: 14 }}>
      <div style={{ fontSize: ".72rem", fontWeight: 700, color: "#94a3b8", marginBottom: 10, textTransform: "uppercase", letterSpacing: ".04em" }}>
        Gamification Preview
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
        {[
          { icon: "⭐", label: "XP Earned", value: "—", color: ACCENT.orange },
          { icon: "🔥", label: "Streak", value: "—", color: "#ef4444" },
          { icon: "📈", label: "Progress", value: "0%", color: ACCENT.green },
          { icon: "🏅", label: "Badge", value: "—", color: ACCENT.purple },
        ].map(({ icon, label, value, color }) => (
          <div key={label} style={{ textAlign: "center", padding: "10px 6px", borderRadius: 10, background: "var(--panel,#fff)", border: "1px solid var(--border,#e5e7eb)" }}>
            <div style={{ fontSize: "1.2rem", marginBottom: 3 }}>{icon}</div>
            <div style={{ fontSize: "1rem", fontWeight: 800, color }}>{value}</div>
            <div style={{ fontSize: ".65rem", color: "#94a3b8" }}>{label}</div>
          </div>
        ))}
      </div>
      <div style={{ marginTop: 10, fontSize: ".7rem", color: "#94a3b8", textAlign: "center" }}>
        Gamification preview only — not connected to student data.
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function AdminLessonExperiencePage({ user }) { // eslint-disable-line no-unused-vars
  const [catalog, setCatalog]   = useState(null);
  const [catLoading, setCatLoading] = useState(true);
  const [catError, setCatError] = useState("");

  // Selectors
  const [selGrade,   setSelGrade]   = useState("");
  const [selSubject, setSelSubject] = useState("");
  const [selChapter, setSelChapter] = useState("");
  const [selLesson,  setSelLesson]  = useState("");

  // Lesson
  const [lesson,       setLesson]       = useState(null);
  const [lessonLoading, setLessonLoading] = useState(false);
  const [lessonError,  setLessonError]  = useState("");
  const [stepIdx,      setStepIdx]      = useState(0);

  // Visuals
  const [visuals,    setVisuals]    = useState(null);

  // Notes (local)
  const [notes, setNotes] = useState(loadNotes);
  const [noteText, setNoteText] = useState("");
  const [bookmarked, setBookmarked] = useState(false);

  // Accessibility
  const [a11y, setA11y] = useState({ fontSize: "16px", lineHeight: "1.8", focusMode: false, darkMode: false });

  // Load catalog
  useEffect(() => {
    setCatLoading(true);
    getLessonCatalog()
      .then(d => setCatalog(d))
      .catch(() => setCatError("Could not load lesson catalog."))
      .finally(() => setCatLoading(false));
  }, []);

  // Load lesson when selected
  const loadLesson = useCallback(async (lessonId) => {
    if (!lessonId) return;
    setLessonLoading(true);
    setLesson(null);
    setLessonError("");
    setStepIdx(0);
    setVisuals(null);
    try {
      const d = await getLessonDetail(lessonId);
      setLesson(d);
    } catch (err) {
      setLessonError(err.message || "Could not load lesson.");
    } finally {
      setLessonLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selLesson) loadLesson(selLesson);
  }, [selLesson, loadLesson]);

  // Load visuals when lesson is loaded
  useEffect(() => {
    if (!lesson) return;
    getLessonVisuals({ grade: selGrade, subject: selSubject, chapter: selChapter, lesson_id: selLesson })
      .then(v => setVisuals(v))
      .catch(() => setVisuals({ available: false, visuals: [], empty_state: "No visuals available." }));
  }, [lesson, selGrade, selSubject, selChapter, selLesson]);

  // Note for current step
  const noteKey = `${selLesson}-step-${stepIdx}`;
  useEffect(() => {
    setNoteText(notes[noteKey] || "");
    setBookmarked(!!(notes[`${noteKey}-bm`]));
  }, [noteKey, notes]);

  function saveNote(text) {
    const updated = { ...notes, [noteKey]: text };
    setNotes(updated);
    saveNotes(updated);
    setNoteText(text);
  }
  function toggleBookmark() {
    const bmKey = `${noteKey}-bm`;
    const updated = { ...notes, [bmKey]: !bookmarked ? "1" : "" };
    setNotes(updated);
    saveNotes(updated);
    setBookmarked(b => !b);
  }

  // Derived catalog selectors
  const lessons = catalog?.lessons || [];
  const grades   = [...new Set(lessons.map(l => l.grade))].sort();
  const subjects = [...new Set(lessons.filter(l => !selGrade || l.grade === selGrade).map(l => l.subject))].sort();
  const chapters = [...new Set(lessons.filter(l => (!selGrade || l.grade === selGrade) && (!selSubject || l.subject === selSubject)).map(l => l.chapter))].sort();
  const filteredLessons = lessons.filter(l =>
    (!selGrade   || l.grade   === selGrade) &&
    (!selSubject || l.subject === selSubject) &&
    (!selChapter || l.chapter === selChapter)
  );

  const steps       = lesson?.steps || [];
  const currentStep = steps[stepIdx] || null;
  const sections    = currentStep?.normalized_sections || {};
  const totalTime   = lesson?.total_estimated_minutes || steps.reduce((s, t) => s + (t.estimated_minutes || 3), 0);

  const sectionIcons = {
    introduction: "📖",
    "what you will learn": "🎯",
    "simple explanation": "💡",
    "step-by-step breakdown": "🔢",
    "worked example": "✏️",
    "common mistake": "⚠️",
    "quick check question": "❓",
    summary: "📋",
  };

  const contentStyle = {
    fontSize: a11y.fontSize,
    lineHeight: a11y.lineHeight,
    maxWidth: a11y.focusMode ? 680 : "100%",
  };

  return (
    <div data-testid="admin-lesson-experience-page"
      style={{ maxWidth: 1400, margin: "0 auto", padding: "0 16px 60px", fontFamily: "inherit" }}>

      {/* Page header */}
      <div data-testid="page-header" style={{ marginBottom: 20, paddingTop: 8 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap", marginBottom: 6 }}>
          <h2 style={{ margin: 0, fontSize: "1.1rem", fontWeight: 800 }}>✨ Lesson Experience</h2>
          <AdminBadge />
        </div>
        <p style={{ margin: "0 0 6px", fontSize: ".85rem", color: "#64748b" }}>
          Future student lesson page preview — reads latest published lesson content.
        </p>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", fontSize: ".75rem" }}>
          <span style={{ padding: "3px 10px", borderRadius: 99, background: "rgba(34,197,94,.1)", color: "#166534" }}>
            ✓ Read-only · No edits made here
          </span>
          <span style={{ padding: "3px 10px", borderRadius: 99, background: "rgba(245,158,11,.1)", color: "#92400e" }}>
            ⚡ To edit content: use Lesson Lab or Lesson Repair
          </span>
        </div>
      </div>

      {catError && (
        <div style={{ padding: "10px 14px", borderRadius: 10, background: "rgba(239,68,68,.08)", color: "#dc2626", fontSize: ".85rem", marginBottom: 14 }}>
          {catError}
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "270px 1fr", gap: 18, alignItems: "start" }}>

        {/* ── Left: Selector Panel ── */}
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div style={card()}>
            <h4 style={{ margin: "0 0 12px", fontSize: ".88rem", fontWeight: 800 }}>Select Lesson</h4>
            {catLoading ? (
              <p style={{ color: "#94a3b8", fontSize: ".82rem" }}>Loading catalog…</p>
            ) : (
              <>
                <label style={{ fontSize: ".75rem", fontWeight: 600, display: "block", marginBottom: 3 }}>Grade</label>
                <select value={selGrade} onChange={e => { setSelGrade(e.target.value); setSelSubject(""); setSelChapter(""); setSelLesson(""); }}
                  style={{ ...inp, marginBottom: 10 }} data-testid="grade-select">
                  <option value="">All grades</option>
                  {grades.map(g => <option key={g}>{g}</option>)}
                </select>

                <label style={{ fontSize: ".75rem", fontWeight: 600, display: "block", marginBottom: 3 }}>Subject</label>
                <select value={selSubject} onChange={e => { setSelSubject(e.target.value); setSelChapter(""); setSelLesson(""); }}
                  style={{ ...inp, marginBottom: 10 }} data-testid="subject-select">
                  <option value="">All subjects</option>
                  {subjects.map(s => <option key={s}>{s}</option>)}
                </select>

                <label style={{ fontSize: ".75rem", fontWeight: 600, display: "block", marginBottom: 3 }}>Chapter</label>
                <select value={selChapter} onChange={e => { setSelChapter(e.target.value); setSelLesson(""); }}
                  style={{ ...inp, marginBottom: 10 }} data-testid="chapter-select">
                  <option value="">All chapters</option>
                  {chapters.map(c => <option key={c}>{c}</option>)}
                </select>

                <label style={{ fontSize: ".75rem", fontWeight: 600, display: "block", marginBottom: 3 }}>Lesson</label>
                <select value={selLesson} onChange={e => setSelLesson(e.target.value)}
                  style={{ ...inp, marginBottom: 0 }} data-testid="lesson-select">
                  <option value="">Select a lesson…</option>
                  {filteredLessons.map(l => (
                    <option key={l.lesson_id} value={l.lesson_id}>
                      {l.grade} | {l.subject} | {l.chapter}
                    </option>
                  ))}
                </select>
              </>
            )}
          </div>

          {/* Accessibility controls */}
          <div style={card()} data-testid="accessibility-controls">
            <h4 style={{ margin: "0 0 10px", fontSize: ".85rem", fontWeight: 800 }}>Accessibility</h4>
            <label style={{ fontSize: ".75rem", display: "flex", alignItems: "center", gap: 6, marginBottom: 8, cursor: "pointer" }}>
              Font
              <select value={a11y.fontSize} onChange={e => setA11y(p => ({ ...p, fontSize: e.target.value }))}
                style={{ fontSize: ".72rem", borderRadius: 6, border: "1px solid var(--border,#e5e7eb)", padding: "2px 6px", fontFamily: "inherit" }}>
                <option value="14px">Small</option>
                <option value="16px">Normal</option>
                <option value="18px">Large</option>
                <option value="20px">X-Large</option>
              </select>
            </label>
            <label style={{ fontSize: ".75rem", display: "flex", alignItems: "center", gap: 6, marginBottom: 8, cursor: "pointer" }}>
              <input type="checkbox" checked={a11y.focusMode} onChange={e => setA11y(p => ({ ...p, focusMode: e.target.checked }))} />
              Focus Mode
            </label>
          </div>

          {/* Step nav (shown when lesson loaded) */}
          {steps.length > 0 && (
            <div style={card()}>
              <h4 style={{ margin: "0 0 10px", fontSize: ".85rem", fontWeight: 800 }}>Steps</h4>
              <ProgressBar current={stepIdx} total={steps.length} />
              <div style={{ marginTop: 10 }}>
                <StepNav steps={steps} selectedIdx={stepIdx} onSelect={setStepIdx} />
              </div>
            </div>
          )}

          {/* Gamification preview */}
          <GamificationPreview />
        </div>

        {/* ── Right: Main Lesson Area ── */}
        <div>
          {lessonLoading && (
            <div style={{ padding: 40, textAlign: "center", color: "#94a3b8" }}>Loading lesson…</div>
          )}

          {lessonError && (
            <div style={{ padding: "10px 14px", borderRadius: 10, background: "rgba(239,68,68,.08)", color: "#dc2626", fontSize: ".85rem" }}>
              {lessonError}
            </div>
          )}

          {!lessonLoading && !lesson && !selLesson && (
            <div style={{ ...card({ textAlign: "center", padding: "50px 24px" }), color: "#94a3b8" }}>
              <div style={{ fontSize: "2.5rem", marginBottom: 12 }}>✨</div>
              <div style={{ fontWeight: 700, fontSize: "1rem", marginBottom: 8, color: "var(--text,#374151)" }}>
                Select a lesson to begin
              </div>
              <div style={{ fontSize: ".85rem" }}>
                Choose a grade, subject, chapter, and lesson from the left panel.
              </div>
            </div>
          )}

          {!lessonLoading && lesson && currentStep && (
            <div style={contentStyle}>
              {/* Hero card */}
              <div data-testid="lesson-hero" style={{ ...card({ background: "linear-gradient(135deg,rgba(99,102,241,.07),rgba(139,92,246,.04))" }), marginBottom: 18 }}>
                <div style={{ fontSize: ".75rem", color: "#94a3b8", marginBottom: 6 }}>
                  {lesson.grade} → {lesson.subject} → {lesson.chapter}
                </div>
                <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", flexWrap: "wrap", gap: 10 }}>
                  <div>
                    <h2 style={{ margin: "0 0 6px", fontSize: "1.1rem", fontWeight: 800 }}>{lesson.title || currentStep.step_title}</h2>
                    <div style={{ display: "flex", gap: 12, flexWrap: "wrap", fontSize: ".78rem", color: "#64748b" }}>
                      <span>⏱ ~{totalTime}m total</span>
                      <span>📚 {steps.length} steps</span>
                      <span>Step {stepIdx + 1}: <strong>{currentStep.step_title}</strong></span>
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
                    <AdminBadge />
                    <button onClick={toggleBookmark}
                      data-testid="bookmark-btn"
                      style={{ padding: "4px 12px", borderRadius: 99, border: "1.5px solid var(--border,#e5e7eb)", background: bookmarked ? "rgba(245,158,11,.1)" : "var(--panel,#fff)", cursor: "pointer", fontSize: ".75rem", fontWeight: 600, color: bookmarked ? ACCENT.orange : "#94a3b8", fontFamily: "inherit" }}>
                      {bookmarked ? "🔖 Bookmarked" : "🔖 Bookmark"}
                    </button>
                  </div>
                </div>
                <div style={{ marginTop: 14 }}>
                  <ProgressBar current={stepIdx} total={steps.length} />
                </div>
              </div>

              {/* Learning objectives */}
              <ObjectivesCard step={currentStep} />

              {/* Main content sections */}
              {Object.keys(sections).filter(k => k !== "what you will learn" && k !== "learning objectives").map(key => (
                <CollapsibleSection
                  key={key}
                  title={key.replace(/\b\w/g, c => c.toUpperCase())}
                  icon={sectionIcons[key] || "📄"}
                  defaultOpen={key === "introduction" || key === "simple explanation"}
                  accentColor={key === "worked example" ? ACCENT.green : key === "common mistake" ? "#ef4444" : ACCENT.indigo}
                >
                  <div className="markdown-content">
                    <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]}>
                      {sections[key]}
                    </ReactMarkdown>
                  </div>
                </CollapsibleSection>
              ))}

              {/* Fallback: raw content if no sections */}
              {Object.keys(sections).length === 0 && currentStep.raw_content && (
                <div data-testid="raw-content" style={{ ...card(), marginBottom: 14 }}>
                  <div className="markdown-content" style={{ lineHeight: 1.8 }}>
                    <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]}>
                      {currentStep.raw_content}
                    </ReactMarkdown>
                  </div>
                </div>
              )}

              {/* Formulas */}
              <FormulaCard formulas={currentStep.formulas} />

              {/* Practice MCQ */}
              {(currentStep.mcqs || []).length > 0 ? (
                <div data-testid="practice-section">
                  <h4 style={{ fontSize: ".88rem", fontWeight: 800, marginBottom: 10, color: ACCENT.green }}>✍️ Practice as You Learn</h4>
                  {currentStep.mcqs.slice(0, 2).map((mcq, i) => <MCQCard key={i} mcq={mcq} />)}
                </div>
              ) : (
                <div data-testid="practice-empty" style={{ padding: "14px 16px", borderRadius: 12, background: "var(--surface2,#f8fafc)", color: "#94a3b8", fontSize: ".82rem", marginBottom: 14, textAlign: "center" }}>
                  No practice question is available for this step yet.
                </div>
              )}

              {/* Concept map */}
              <ConceptMap step={currentStep} />

              {/* Visual panel */}
              <div style={{ marginBottom: 14 }}>
                <h4 style={{ fontSize: ".88rem", fontWeight: 800, marginBottom: 10, color: ACCENT.blue }}>🖼️ Visual Learning</h4>
                <VisualPanel visuals={visuals} />
              </div>

              {/* Quick Summary */}
              {currentStep.summary && (
                <CollapsibleSection title="Quick Summary" icon="📋" accentColor={ACCENT.purple} defaultOpen>
                  <div className="markdown-content">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{typeof currentStep.summary === "string" ? currentStep.summary : JSON.stringify(currentStep.summary)}</ReactMarkdown>
                  </div>
                </CollapsibleSection>
              )}

              {/* Placeholder disabled features */}
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16 }}>
                {[
                  { label: "💬 Ask Doubt about this step", title: "Ask Doubt" },
                  { label: "🎤 Voice Read-out", title: "Voice" },
                  { label: "🖨️ Print", title: "Print" },
                ].map(({ label, title }) => (
                  <button key={title} disabled title="Coming soon"
                    style={{ padding: "7px 14px", borderRadius: 99, border: "1px dashed var(--border,#e5e7eb)", background: "var(--surface2,#f8fafc)", color: "#94a3b8", fontSize: ".78rem", cursor: "not-allowed", fontFamily: "inherit" }}>
                    {label} <span style={{ fontSize: ".68rem" }}>(Coming soon)</span>
                  </button>
                ))}
              </div>

              {/* Admin notes */}
              <div data-testid="notes-panel" style={{ ...card(), marginBottom: 14 }}>
                <h4 style={{ margin: "0 0 8px", fontSize: ".85rem", fontWeight: 800 }}>
                  🗒️ Admin Notes <span style={{ fontSize: ".72rem", color: "#94a3b8", fontWeight: 400 }}>(local only — not saved to backend)</span>
                </h4>
                <textarea
                  rows={3}
                  value={noteText}
                  onChange={e => saveNote(e.target.value)}
                  placeholder="Add observations about this step's content quality, UX, gaps…"
                  data-testid="note-input"
                  style={{ ...inp, resize: "vertical" }}
                />
              </div>

              {/* Step navigation buttons */}
              <div style={{ display: "flex", gap: 10, justifyContent: "space-between", flexWrap: "wrap" }}>
                <button
                  data-testid="prev-step-btn"
                  disabled={stepIdx === 0}
                  onClick={() => setStepIdx(i => Math.max(0, i - 1))}
                  style={{ padding: "9px 20px", borderRadius: 10, border: "1px solid var(--border,#e5e7eb)", background: "var(--panel,#fff)", cursor: stepIdx === 0 ? "not-allowed" : "pointer", fontFamily: "inherit", fontWeight: 600, fontSize: ".85rem", color: stepIdx === 0 ? "#94a3b8" : "var(--text,#374151)" }}>
                  ← Previous Step
                </button>
                <button
                  data-testid="next-step-btn"
                  disabled={stepIdx >= steps.length - 1}
                  onClick={() => setStepIdx(i => Math.min(steps.length - 1, i + 1))}
                  style={{ padding: "9px 20px", borderRadius: 10, border: "none", background: stepIdx >= steps.length - 1 ? "#94a3b8" : ACCENT.indigo, color: "#fff", cursor: stepIdx >= steps.length - 1 ? "not-allowed" : "pointer", fontFamily: "inherit", fontWeight: 700, fontSize: ".85rem" }}>
                  Next Step →
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
