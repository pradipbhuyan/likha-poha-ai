/**
 * AdminLessonExperiencePage.jsx — Admin Preview: Student Guided Lesson Experience
 * ─────────────────────────────────────────────────────────────────────────────
 * Replaces the old Admin Lesson Experience page with a guided learning journey
 * preview. Shows admins how the future student-facing lesson path will look.
 *
 * IMPORTANT:
 *  - Admin-only. The live student lesson experience is NOT modified here.
 *  - No write operations. Read-only preview of published lesson content.
 *  - Mock/fallback preview state is local to this component only.
 *  - To edit lesson content, use Lesson Lab or Lesson Repair.
 * ─────────────────────────────────────────────────────────────────────────────
 */
import { useCallback, useEffect, useState } from "react";
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

const C = {
  indigo:  "#6366f1",
  purple:  "#8b5cf6",
  green:   "#22c55e",
  blue:    "#3b82f6",
  orange:  "#f59e0b",
  red:     "#ef4444",
  muted:   "#94a3b8",
  text:    "var(--text,#374151)",
  border:  "var(--border,#e5e7eb)",
  panel:   "var(--panel,#fff)",
  surface: "var(--surface2,#f8fafc)",
};

const inp = {
  background: C.surface, border: `1px solid ${C.border}`, borderRadius: 10,
  padding: "8px 12px", fontFamily: "inherit", fontSize: ".85rem",
  color: C.text, width: "100%",
};

const card = (extra = {}) => ({
  background: C.panel, border: `1px solid ${C.border}`,
  borderRadius: 16, padding: "18px 20px",
  boxShadow: "0 1px 6px rgba(0,0,0,.06)", ...extra,
});

// ── localStorage helpers ──────────────────────────────────────────────────────

const LS_NS = "admin_lesson_experience_notes";
function loadNotes() {
  try { return JSON.parse(localStorage.getItem(LS_NS) || "{}"); } catch { return {}; }
}
function saveNotes(notes) {
  try { localStorage.setItem(LS_NS, JSON.stringify(notes)); } catch { /* ok */ }
}

// ── Motivational copy helpers ─────────────────────────────────────────────────

function progressCopy(stepIdx, total) {
  const pct = total > 0 ? Math.round(((stepIdx + 1) / total) * 100) : 0;
  if (stepIdx === 0)            return "You're off to a great start!";
  if (pct >= 100)               return "Chapter complete! Outstanding work.";
  if (pct >= 80)                return "Almost there — keep going!";
  if (pct >= 50)                return "Halfway through — you're doing great!";
  return "Keep building on what you've learned!";
}

function ctaLabel(state) {
  if (state === "completed") return "Continue to Next Step →";
  if (state === "in_progress") return "Continue Learning";
  return "Start Learning";
}

// ── Step status helpers ───────────────────────────────────────────────────────

function stepStatus(stepIdx, currentIdx, previewStates) {
  const state = previewStates[stepIdx] || "not_started";
  if (state === "completed") return "completed";
  if (stepIdx === currentIdx) return "current";
  if (stepIdx === currentIdx + 1) return "next";
  if (stepIdx < currentIdx) return "completed";
  return "locked";
}

const STEP_STATUS_STYLE = {
  completed:  { bg: "rgba(34,197,94,.12)",  color: "#166534",   icon: "✓",  label: "Done" },
  current:    { bg: "rgba(99,102,241,.12)",  color: C.indigo,    icon: "▶",  label: "Current" },
  next:       { bg: "rgba(245,158,11,.08)",  color: "#92400e",   icon: "→",  label: "Next" },
  locked:     { bg: "rgba(148,163,184,.1)",  color: "#94a3b8",   icon: "○",  label: "" },
  not_started:{ bg: "rgba(148,163,184,.1)",  color: "#94a3b8",   icon: "○",  label: "" },
};

// ── Small components ──────────────────────────────────────────────────────────

function AdminPreviewBanner() {
  return (
    <div data-testid="admin-preview-banner" style={{
      display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap",
      padding: "10px 16px", borderRadius: 10, marginBottom: 16,
      background: "rgba(99,102,241,.07)", border: "1px solid rgba(99,102,241,.2)",
      fontSize: ".8rem",
    }}>
      <span style={{
        padding: "2px 10px", borderRadius: 99, background: "rgba(99,102,241,.15)",
        color: C.indigo, fontSize: ".72rem", fontWeight: 800, letterSpacing: ".04em",
      }}>
        ✦ ADMIN PREVIEW
      </span>
      <span style={{ color: C.text, fontWeight: 600 }}>Student Guided Lesson Experience</span>
      <span style={{ color: "#64748b" }}>·</span>
      <span data-testid="not-live-notice" style={{ color: "#64748b", fontSize: ".78rem" }}>
        This preview is not live for students.
        Read-only — to edit content, use <strong>Lesson Lab or Lesson Repair</strong>.
      </span>
    </div>
  );
}

function HeroCard({ lesson, stepIdx, total }) {
  const pct = total > 0 ? Math.round(((stepIdx + 1) / total) * 100) : 0;
  return (
    <div data-testid="lesson-hero" style={{
      ...card({ background: "linear-gradient(135deg,rgba(99,102,241,.07),rgba(139,92,246,.04))" }),
      marginBottom: 18,
    }}>
      <div style={{ fontSize: ".74rem", color: "#94a3b8", marginBottom: 6, fontWeight: 600, letterSpacing: ".04em" }}>
        {lesson.subject} • {lesson.grade} • CBSE
      </div>
      <h2 style={{ margin: "0 0 8px", fontSize: "1.15rem", fontWeight: 800, color: C.text }}>
        {lesson.title || `${lesson.subject} — ${lesson.chapter}`}
      </h2>
      <p style={{ margin: "0 0 14px", fontSize: ".85rem", color: "#64748b", lineHeight: 1.6 }}>
        You're on a {total}-step journey to understand{" "}
        {lesson.chapter || "this chapter"} — through explanation, examples, and practice.
      </p>

      {/* Progress bar */}
      <div>
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: ".72rem", color: "#94a3b8", marginBottom: 5 }}>
          <span>Step {stepIdx + 1} of {total}</span>
          <span style={{ color: C.indigo, fontWeight: 700 }}>{pct}% complete</span>
        </div>
        <div style={{ height: 7, background: C.border, borderRadius: 99, overflow: "hidden" }}>
          <div style={{
            width: `${pct}%`, height: "100%",
            background: `linear-gradient(90deg,${C.indigo},${C.purple})`,
            borderRadius: 99, transition: "width .5s ease",
          }} />
        </div>
        <p style={{ margin: "6px 0 0", fontSize: ".75rem", color: "#64748b", fontStyle: "italic" }}>
          {progressCopy(stepIdx, total)}
        </p>
      </div>
    </div>
  );
}

function JourneyStepper({ steps, currentIdx, previewStates, onSelect }) {
  return (
    <div data-testid="step-nav" style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <h4 style={{ margin: "0 0 10px", fontSize: ".82rem", fontWeight: 800, color: "#64748b", letterSpacing: ".05em" }}>
        LEARNING JOURNEY
      </h4>
      {steps.map((step, i) => {
        const status = stepStatus(i, currentIdx, previewStates);
        const s = STEP_STATUS_STYLE[status] || STEP_STATUS_STYLE.locked;
        const isActive = i === currentIdx;
        return (
          <button
            key={i}
            data-testid={`step-nav-item-${i}`}
            onClick={() => onSelect(i)}
            style={{
              display: "flex", alignItems: "center", gap: 10,
              textAlign: "left", padding: "10px 12px", borderRadius: 12,
              border: `1.5px solid ${isActive ? C.indigo : C.border}`,
              background: isActive ? "rgba(99,102,241,.07)" : C.panel,
              fontFamily: "inherit", cursor: "pointer",
              transition: "border-color .15s",
            }}
          >
            {/* Step number / status indicator */}
            <div style={{
              width: 28, height: 28, borderRadius: "50%", flexShrink: 0,
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: ".72rem", fontWeight: 800,
              background: isActive ? C.indigo : s.bg,
              color: isActive ? "#fff" : s.color,
              border: isActive ? `2px solid ${C.indigo}` : "2px solid transparent",
            }}>
              {s.icon || (i + 1)}
            </div>

            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{
                fontSize: ".8rem", fontWeight: isActive ? 700 : 500,
                color: isActive ? C.indigo : C.text, lineHeight: 1.3,
              }}>
                Step {i + 1}: {step.step_title}
              </div>
              <div style={{ fontSize: ".68rem", color: C.muted, marginTop: 2 }}>
                ~{step.estimated_minutes || 3}m
                {s.label && <span style={{ marginLeft: 6, fontWeight: 600, color: s.color }}>· {s.label}</span>}
              </div>
            </div>
          </button>
        );
      })}
    </div>
  );
}

function CurrentMissionCard({ step, stepIdx, total, previewState, onAdvanceState, onNextStep }) {
  const isLast = stepIdx >= total - 1;
  const cta = ctaLabel(previewState);

  return (
    <div data-testid="current-mission-card" style={{
      ...card({ background: "rgba(99,102,241,.03)", borderColor: "rgba(99,102,241,.25)" }),
      marginBottom: 16,
    }}>
      <div style={{ fontSize: ".72rem", color: C.indigo, fontWeight: 800, marginBottom: 6, letterSpacing: ".05em" }}>
        ▶ CURRENT MISSION
      </div>
      <h3 style={{ margin: "0 0 6px", fontSize: "1rem", fontWeight: 800, color: C.text }}>
        {step.step_title}
      </h3>
      <p style={{ margin: "0 0 12px", fontSize: ".85rem", color: "#64748b", lineHeight: 1.6 }}>
        {step.normalized_sections?.introduction
          ? step.normalized_sections.introduction.split(".")[0] + "."
          : `In this step, you'll work through ${step.step_title.toLowerCase()} and build your understanding.`}
      </p>
      <div style={{ fontSize: ".74rem", color: C.muted, marginBottom: 14 }}>
        ⏱ Estimated time: ~{step.estimated_minutes || 3} min
        &nbsp;·&nbsp; Step {stepIdx + 1} of {total}
      </div>

      {/* Primary CTA */}
      <button
        data-testid="primary-cta-btn"
        onClick={() => {
          if (previewState === "not_started")    onAdvanceState("in_progress");
          else if (previewState === "in_progress") onAdvanceState("completed");
          else if (!isLast) onNextStep();
        }}
        style={{
          width: "100%", padding: "12px 20px", borderRadius: 12, border: "none",
          background: `linear-gradient(90deg,${C.indigo},${C.purple})`, color: "#fff",
          fontFamily: "inherit", fontSize: ".92rem", fontWeight: 800, cursor: "pointer",
          boxShadow: "0 4px 14px rgba(99,102,241,.3)", marginBottom: 8,
        }}
      >
        {cta}
      </button>

      {previewState === "completed" && isLast && (
        <div style={{ textAlign: "center", fontSize: ".78rem", color: "#64748b", fontStyle: "italic" }}>
          🎉 Chapter complete in preview
        </div>
      )}
    </div>
  );
}

function NextUpCard({ nextStep, stepIdx, total }) {
  if (!nextStep || stepIdx >= total - 1) return null;
  return (
    <div data-testid="next-up-card" style={{
      ...card({ background: "rgba(245,158,11,.03)", borderColor: "rgba(245,158,11,.2)" }),
      marginBottom: 16,
    }}>
      <div style={{ fontSize: ".72rem", color: "#92400e", fontWeight: 800, marginBottom: 6, letterSpacing: ".05em" }}>
        → NEXT UP
      </div>
      <div style={{ fontWeight: 700, fontSize: ".88rem", color: C.text, marginBottom: 4 }}>
        {nextStep.step_title}
      </div>
      <p style={{ margin: 0, fontSize: ".8rem", color: "#64748b", lineHeight: 1.5 }}>
        {nextStep.normalized_sections?.introduction
          ? nextStep.normalized_sections.introduction.split(".")[0] + "."
          : `You'll continue building on what you've learned.`}
      </p>
    </div>
  );
}

function ObjectivesCard({ step }) {
  const sections = step?.normalized_sections || {};
  const objText = sections["what you will learn"] || sections["learning objectives"] || "";
  const objectives = objText
    ? objText.split(/\n/).map(l => l.replace(/^[-•*]\s*/, "").trim()).filter(l => l.length > 10).slice(0, 4)
    : [];

  return (
    <div data-testid="objectives-card" style={{
      ...card({ background: "rgba(59,130,246,.04)", borderColor: "rgba(59,130,246,.2)" }),
      marginBottom: 14,
    }}>
      <h4 style={{ margin: "0 0 10px", fontSize: ".88rem", fontWeight: 800, color: C.blue }}>
        🎯 What You Will Learn
      </h4>
      {objectives.length > 0 ? (
        <ul style={{ margin: 0, paddingLeft: 18 }}>
          {objectives.map((obj, i) => (
            <li key={i} style={{ fontSize: ".85rem", lineHeight: 1.6, color: C.text, marginBottom: 4 }}>
              {obj}
            </li>
          ))}
        </ul>
      ) : (
        <p style={{ fontSize: ".82rem", color: C.muted, margin: 0 }}>
          Objectives will appear here when content is available.
        </p>
      )}
    </div>
  );
}

function CollapsibleSection({ title, icon, children, defaultOpen = false, accentColor }) {
  const [open, setOpen] = useState(defaultOpen);
  const color = accentColor || C.indigo;
  return (
    <div style={{ ...card(), marginBottom: 10 }}>
      <button onClick={() => setOpen(o => !o)} style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        width: "100%", background: "none", border: "none", cursor: "pointer",
        padding: 0, fontFamily: "inherit",
      }}>
        <span style={{ fontSize: ".88rem", fontWeight: 700, color, display: "flex", alignItems: "center", gap: 8 }}>
          <span>{icon}</span> {title}
        </span>
        <span style={{ color: C.muted, fontSize: ".85rem" }}>{open ? "▲" : "▼"}</span>
      </button>
      {open && (
        <div data-testid={`section-${title.toLowerCase().replace(/\s+/g,"-")}`}
          style={{ marginTop: 12, fontSize: ".88rem", lineHeight: 1.8, color: C.text }}>
          {children}
        </div>
      )}
    </div>
  );
}

function FormulaCard({ formulas }) {
  if (!formulas?.length) return null;
  return (
    <div data-testid="formula-card" style={{
      ...card({ background: "rgba(245,158,11,.04)", borderColor: "rgba(245,158,11,.25)" }),
      marginBottom: 14,
    }}>
      <h4 style={{ margin: "0 0 10px", fontSize: ".85rem", fontWeight: 800, color: C.orange }}>📐 Key Formulas</h4>
      {formulas.map((f, i) => (
        <div key={i} style={{ marginBottom: 8, padding: "8px 12px", borderRadius: 8, background: C.surface, fontFamily: "monospace", fontSize: ".85rem" }}>
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
    <div data-testid="mcq-card" style={{
      ...card({ background: "rgba(34,197,94,.03)", borderColor: "rgba(34,197,94,.2)" }),
      marginBottom: 10,
    }}>
      <div style={{ fontSize: ".78rem", fontWeight: 700, color: C.green, marginBottom: 8 }}>✍️ Practice Question</div>
      <p style={{ margin: "0 0 10px", fontSize: ".88rem", lineHeight: 1.6, fontWeight: 600 }}>{question}</p>
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        {options.map((opt, i) => (
          <button key={i} onClick={() => setSelected(opt)} style={{
            textAlign: "left", padding: "8px 12px", borderRadius: 9,
            border: `1.5px solid ${selected === opt ? C.green : C.border}`,
            background: selected === opt ? "rgba(34,197,94,.08)" : C.panel,
            fontFamily: "inherit", fontSize: ".85rem", cursor: "pointer",
          }}>{opt}</button>
        ))}
      </div>
      {options.length === 0 && <p style={{ color: C.muted, fontSize: ".82rem" }}>No answer options detected.</p>}
      {selected && !revealed && (
        <button onClick={() => setRevealed(true)} style={{
          marginTop: 10, padding: "7px 16px", borderRadius: 8, border: "none",
          background: C.green, color: "#fff", fontFamily: "inherit", fontWeight: 700, fontSize: ".8rem", cursor: "pointer",
        }}>Check Answer</button>
      )}
      {revealed && (
        <div style={{ marginTop: 10, padding: "10px 14px", borderRadius: 10, background: "rgba(34,197,94,.08)", border: "1px solid rgba(34,197,94,.3)", fontSize: ".82rem" }}>
          <strong style={{ color: C.green }}>You selected:</strong> {selected}
          {explanation && <p style={{ margin: "6px 0 0", color: C.text }}>{explanation}</p>}
          <p style={{ margin: "4px 0 0", fontSize: ".72rem", color: C.muted }}>Admin preview only — not persisted.</p>
        </div>
      )}
    </div>
  );
}

function ConceptMap({ step }) {
  const sections = Object.keys(step?.normalized_sections || {}).filter(k => !["what you will learn","learning objectives"].includes(k));
  const formulas = (step?.formulas || []).slice(0, 3);
  return (
    <div data-testid="concept-map" style={{ ...card({ background: "rgba(139,92,246,.03)", borderColor: "rgba(139,92,246,.2)" }), marginBottom: 14 }}>
      <h4 style={{ margin: "0 0 12px", fontSize: ".85rem", fontWeight: 800, color: C.purple }}>🗺️ Concept Map</h4>
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        <div style={{ padding: "8px 12px", borderRadius: 8, background: "rgba(99,102,241,.08)", fontSize: ".82rem", fontWeight: 700, textAlign: "center", color: C.indigo }}>
          {step?.step_title || "This Step"}
        </div>
        {sections.slice(0, 3).map(k => (
          <div key={k} style={{ padding: "6px 12px", borderRadius: 8, background: "rgba(139,92,246,.06)", fontSize: ".78rem", color: C.purple, marginLeft: 16, borderLeft: `3px solid ${C.purple}` }}>
            {k.replace(/\b\w/g, c => c.toUpperCase())}
          </div>
        ))}
        {formulas.slice(0, 2).map((f, i) => (
          <div key={i} style={{ padding: "6px 12px", borderRadius: 8, background: "rgba(245,158,11,.06)", fontSize: ".78rem", color: "#92400e", marginLeft: 32, fontFamily: "monospace" }}>
            {String(f).slice(0, 40)}
          </div>
        ))}
      </div>
    </div>
  );
}

function VisualPanel({ visuals }) {
  if (!visuals) return (
    <div data-testid="visual-empty-state" style={{ padding: "20px 16px", textAlign: "center", color: C.muted, fontSize: ".82rem", background: C.surface, borderRadius: 12 }}>
      <div style={{ fontSize: "2rem", marginBottom: 8 }}>🖼️</div>
      <div style={{ fontWeight: 600 }}>No textbook visuals linked yet.</div>
      <div style={{ fontSize: ".72rem", marginTop: 6 }}>Upload assets in RAG Upload to see them here.</div>
    </div>
  );
  if (visuals.available && visuals.visuals.length > 0) {
    return (
      <div>
        {visuals.visuals.map(v => (
          <div key={v.id} style={card()}>
            {v.image_url_or_asset_ref && <img src={v.image_url_or_asset_ref} alt={v.caption || v.title} style={{ width: "100%", borderRadius: 8, marginBottom: 8, objectFit: "contain", maxHeight: 200 }} />}
            <strong style={{ fontSize: ".82rem" }}>{v.title}</strong>
            {v.caption && <p style={{ fontSize: ".75rem", color: "#64748b", margin: "4px 0 0" }}>{v.caption}</p>}
          </div>
        ))}
      </div>
    );
  }
  return (
    <div data-testid="visual-empty-state" style={{ padding: "20px 16px", textAlign: "center", color: C.muted, fontSize: ".82rem", background: C.surface, borderRadius: 12 }}>
      <div style={{ fontSize: "2rem", marginBottom: 8 }}>🖼️</div>
      <div style={{ fontWeight: 600 }}>{visuals.empty_state || "No textbook visuals linked yet."}</div>
    </div>
  );
}

function GamificationPreview() {
  return (
    <div data-testid="gamification-preview" style={{ ...card({ background: "rgba(245,158,11,.04)", borderColor: "rgba(245,158,11,.2)" }) }}>
      <h4 style={{ margin: "0 0 6px", fontSize: ".82rem", fontWeight: 800, color: C.orange }}>🏆 XP & Streaks</h4>
      <p style={{ margin: 0, fontSize: ".74rem", color: "#64748b" }}>Gamification preview only — not connected to real student data.</p>
      <div style={{ display: "flex", gap: 10, marginTop: 10, flexWrap: "wrap" }}>
        {[{ icon: "⚡", label: "XP", value: "—" }, { icon: "🔥", label: "Streak", value: "—" }, { icon: "🎯", label: "Goals", value: "—" }].map(({ icon, label, value }) => (
          <div key={label} style={{ textAlign: "center", flex: 1, minWidth: 48 }}>
            <div style={{ fontSize: "1.2rem" }}>{icon}</div>
            <div style={{ fontSize: ".65rem", color: C.muted }}>{label}</div>
            <div style={{ fontSize: ".78rem", fontWeight: 700, color: C.orange }}>{value}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Restart confirmation ──────────────────────────────────────────────────────

function RestartConfirmDialog({ onConfirm, onCancel }) {
  return (
    <div data-testid="restart-confirm-dialog" style={{
      position: "fixed", inset: 0, background: "rgba(0,0,0,.45)", zIndex: 999,
      display: "flex", alignItems: "center", justifyContent: "center", padding: 16,
    }}>
      <div style={{ ...card({ maxWidth: 380, width: "100%" }), padding: "24px 28px" }}>
        <h3 style={{ margin: "0 0 8px", fontSize: ".95rem", fontWeight: 800 }}>Restart Chapter?</h3>
        <p style={{ margin: "0 0 18px", fontSize: ".85rem", color: "#64748b" }}>
          This will reset all preview progress for this chapter. Local notes are kept.
        </p>
        <div style={{ display: "flex", gap: 10 }}>
          <button onClick={onConfirm} data-testid="restart-confirm-btn" style={{
            flex: 1, padding: "9px 16px", borderRadius: 10, border: "none",
            background: C.red, color: "#fff", fontFamily: "inherit", fontWeight: 700, fontSize: ".85rem", cursor: "pointer",
          }}>Yes, Restart</button>
          <button onClick={onCancel} data-testid="restart-cancel-btn" style={{
            flex: 1, padding: "9px 16px", borderRadius: 10, border: `1px solid ${C.border}`,
            background: C.panel, color: C.text, fontFamily: "inherit", fontWeight: 600, fontSize: ".85rem", cursor: "pointer",
          }}>Cancel</button>
        </div>
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

const SECTION_ICONS = {
  introduction: "📖", "what you will learn": "🎯", "simple explanation": "💡",
  "step-by-step breakdown": "🔢", "worked example": "✏️", "common mistake": "⚠️",
  "quick check question": "❓", summary: "📋",
};

export default function AdminLessonExperiencePage({ user }) { // eslint-disable-line no-unused-vars
  // Catalog & selection
  const [catalog, setCatalog]       = useState(null);
  const [catLoading, setCatLoading] = useState(true);
  const [selGrade, setSelGrade]     = useState("");
  const [selSubject, setSelSubject] = useState("");
  const [selChapter, setSelChapter] = useState("");
  const [selLesson, setSelLesson]   = useState("");

  // Lesson data
  const [lesson, setLesson]           = useState(null);
  const [lessonLoading, setLessonLoading] = useState(false);
  const [lessonError, setLessonError]   = useState("");
  const [stepIdx, setStepIdx]           = useState(0);
  const [visuals, setVisuals]           = useState(null);

  // Per-step preview state (local only — admin-side simulation)
  const [previewStates, setPreviewStates] = useState({});

  // UI state
  const [showRestart, setShowRestart] = useState(false);

  // Notes (local only)
  const [notes, setNotes] = useState(loadNotes);

  // Load catalog
  useEffect(() => {
    setCatLoading(true);
    getLessonCatalog()
      .then(d => setCatalog(d))
      .catch(() => setCatalog({ success: true, grades: [], subjects: [], chapters: [], lessons: [], total_lessons: 0 }))
      .finally(() => setCatLoading(false));
  }, []);

  // Load lesson detail
  const loadLesson = useCallback(async (lessonId) => {
    if (!lessonId) return;
    setLessonLoading(true);
    setLesson(null);
    setVisuals(null);
    setStepIdx(0);
    setPreviewStates({});
    setLessonError("");
    try {
      const d = await getLessonDetail(lessonId);
      setLesson(d);
      // Load visuals in background
      getLessonVisuals({ lesson_id: lessonId })
        .then(v => setVisuals(v))
        .catch(() => setVisuals({ available: false, visuals: [], empty_state: "Could not load visuals." }));
    } catch (err) {
      setLessonError(err.message || "Could not load lesson.");
    } finally {
      setLessonLoading(false);
    }
  }, []);

  useEffect(() => { loadLesson(selLesson); }, [selLesson, loadLesson]);

  function saveNote(key, value) {
    const updated = { ...notes, [key]: value };
    setNotes(updated);
    saveNotes(updated);
  }

  function handleRestart() {
    setPreviewStates({});
    setStepIdx(0);
    setShowRestart(false);
  }

  const steps = lesson?.steps || [];
  const currentStep = steps[stepIdx] || null;
  const nextStep = steps[stepIdx + 1] || null;
  const totalTime = steps.reduce((a, s) => a + (s.estimated_minutes || 3), 0);
  const currentPreviewState = previewStates[stepIdx] || "not_started";

  // Catalog-derived selectors
  const allLessons = catalog?.lessons || [];
  const grades     = [...new Set(allLessons.map(l => l.grade))].sort();
  const subjects   = [...new Set(allLessons.filter(l => !selGrade || l.grade === selGrade).map(l => l.subject))].sort();
  const chapters   = [...new Set(allLessons.filter(l => (!selGrade || l.grade === selGrade) && (!selSubject || l.subject === selSubject)).map(l => l.chapter))].sort();
  const filteredLessons = allLessons.filter(l =>
    (!selGrade || l.grade === selGrade) &&
    (!selSubject || l.subject === selSubject) &&
    (!selChapter || l.chapter === selChapter)
  );

  const noteKey = `${selLesson}-step-${stepIdx}`;
  const contentStyle = {};

  return (
    <div data-testid="admin-lesson-experience-page" style={{ maxWidth: 1280, margin: "0 auto", padding: "0 14px 60px", fontFamily: "inherit" }}>

      {/* Admin Preview Banner */}
      <div data-testid="page-header">
        <AdminPreviewBanner />
        <div style={{ marginBottom: 18 }}>
          <h2 style={{ margin: "0 0 4px", fontSize: "1.05rem", fontWeight: 800 }}>Lesson Experience</h2>
          <p style={{ margin: 0, fontSize: ".82rem", color: "#64748b" }}>
            Preview the proposed student guided lesson UX. No changes affect live student content.
          </p>
        </div>
      </div>

      {showRestart && <RestartConfirmDialog onConfirm={handleRestart} onCancel={() => setShowRestart(false)} />}

      <div style={{ display: "grid", gridTemplateColumns: "260px 1fr", gap: 18, alignItems: "start" }}>

        {/* ── Left column ── */}
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>

          {/* Lesson selector */}
          <div style={card()}>
            <h4 style={{ margin: "0 0 12px", fontSize: ".85rem", fontWeight: 800 }}>Select Lesson</h4>
            {catLoading ? <p style={{ color: C.muted, fontSize: ".82rem" }}>Loading catalog…</p> : (
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
                  style={inp} data-testid="lesson-select">
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

          {/* Journey stepper (shown when lesson loaded) */}
          {steps.length > 0 && (
            <div style={card()}>
              <JourneyStepper
                steps={steps}
                currentIdx={stepIdx}
                previewStates={previewStates}
                onSelect={setStepIdx}
              />
            </div>
          )}
        </div>

        {/* ── Right column ── */}
        <div>
          {lessonLoading && <div style={{ padding: 40, textAlign: "center", color: C.muted }}>Loading lesson…</div>}
          {lessonError && <div style={{ padding: "10px 14px", borderRadius: 10, background: "rgba(239,68,68,.08)", color: C.red, fontSize: ".85rem" }}>{lessonError}</div>}

          {!lessonLoading && !lesson && !selLesson && (
            <div style={{ ...card({ textAlign: "center", padding: "50px 24px" }), color: C.muted }}>
              <div style={{ fontSize: "2.5rem", marginBottom: 12 }}>✨</div>
              <div style={{ fontWeight: 700, fontSize: "1rem", marginBottom: 8, color: C.text }}>Select a lesson to preview</div>
              <div style={{ fontSize: ".85rem" }}>
                Choose a grade, subject, chapter, and lesson from the left panel to see the guided student journey.
              </div>
            </div>
          )}

          {!lessonLoading && lesson && currentStep && (
            <div style={contentStyle}>
              {/* Hero card */}
              <HeroCard lesson={lesson} stepIdx={stepIdx} total={steps.length} />

              {/* Current mission */}
              <CurrentMissionCard
                step={currentStep}
                stepIdx={stepIdx}
                total={steps.length}
                previewState={currentPreviewState}
                onAdvanceState={(state) => setPreviewStates(p => ({ ...p, [stepIdx]: state }))}
                onNextStep={() => setStepIdx(i => Math.min(steps.length - 1, i + 1))}
              />

              {/* Learning objectives */}
              <ObjectivesCard step={currentStep} />

              {/* Main content sections */}
              {Object.keys(currentStep.normalized_sections || {})
                .filter(k => !["what you will learn","learning objectives"].includes(k))
                .map(key => (
                  <CollapsibleSection
                    key={key}
                    title={key.replace(/\b\w/g, c => c.toUpperCase())}
                    icon={SECTION_ICONS[key] || "📄"}
                    defaultOpen={key === "introduction" || key === "simple explanation"}
                    accentColor={key === "worked example" ? C.green : key === "common mistake" ? C.red : C.indigo}
                  >
                    <div className="markdown-content">
                      <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]}>
                        {currentStep.normalized_sections[key]}
                      </ReactMarkdown>
                    </div>
                  </CollapsibleSection>
                ))}

              {/* Fallback: raw content if no sections */}
              {Object.keys(currentStep.normalized_sections || {}).length === 0 && currentStep.raw_content && (
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
                  <h4 style={{ fontSize: ".88rem", fontWeight: 800, marginBottom: 10, color: C.green }}>✍️ Practice as You Learn</h4>
                  {currentStep.mcqs.slice(0, 2).map((mcq, i) => <MCQCard key={i} mcq={mcq} />)}
                </div>
              ) : (
                <div data-testid="practice-empty" style={{ padding: "14px 16px", borderRadius: 12, background: C.surface, color: C.muted, fontSize: ".82rem", marginBottom: 14, textAlign: "center" }}>
                  No practice question is available for this step yet.
                </div>
              )}

              {/* Concept map */}
              <ConceptMap step={currentStep} />

              {/* Visual panel */}
              <div style={{ marginBottom: 14 }}>
                <h4 style={{ fontSize: ".88rem", fontWeight: 800, marginBottom: 10, color: C.blue }}>🖼️ Visual Learning</h4>
                <VisualPanel visuals={visuals} />
              </div>

              {/* Next up */}
              <NextUpCard nextStep={nextStep} stepIdx={stepIdx} total={steps.length} />

              {/* Admin notes */}
              <div data-testid="notes-panel" style={{ ...card(), marginBottom: 14 }}>
                <h4 style={{ margin: "0 0 8px", fontSize: ".85rem", fontWeight: 800 }}>
                  🗒️ Admin Notes <span style={{ fontSize: ".72rem", color: C.muted, fontWeight: 400 }}>(local only — not saved to backend)</span>
                </h4>
                <textarea
                  rows={3}
                  value={notes[noteKey] || ""}
                  onChange={e => saveNote(noteKey, e.target.value)}
                  placeholder="Add UX observations about this step's guided journey…"
                  data-testid="note-input"
                  style={{ ...inp, resize: "vertical" }}
                />
              </div>

              {/* Navigation buttons */}
              <div style={{ display: "flex", gap: 10, justifyContent: "space-between", flexWrap: "wrap", marginBottom: 8 }}>
                <button
                  data-testid="prev-step-btn"
                  disabled={stepIdx === 0}
                  onClick={() => setStepIdx(i => Math.max(0, i - 1))}
                  style={{
                    padding: "9px 20px", borderRadius: 10, border: `1px solid ${C.border}`,
                    background: C.panel, cursor: stepIdx === 0 ? "not-allowed" : "pointer",
                    fontFamily: "inherit", fontWeight: 600, fontSize: ".85rem",
                    color: stepIdx === 0 ? C.muted : C.text,
                  }}>
                  ← Previous Step
                </button>
                <button
                  data-testid="next-step-btn"
                  disabled={stepIdx >= steps.length - 1}
                  onClick={() => setStepIdx(i => Math.min(steps.length - 1, i + 1))}
                  style={{
                    padding: "9px 20px", borderRadius: 10, border: "none",
                    background: stepIdx >= steps.length - 1 ? C.muted : C.indigo,
                    color: "#fff", cursor: stepIdx >= steps.length - 1 ? "not-allowed" : "pointer",
                    fontFamily: "inherit", fontWeight: 700, fontSize: ".85rem",
                  }}>
                  Next Step →
                </button>
              </div>

              {/* Restart — low emphasis, hidden behind confirm */}
              <div style={{ textAlign: "center", marginTop: 8 }}>
                <button
                  data-testid="restart-chapter-link"
                  onClick={() => setShowRestart(true)}
                  style={{ background: "none", border: "none", color: C.muted, fontSize: ".78rem", cursor: "pointer", fontFamily: "inherit", textDecoration: "underline" }}>
                  ↺ Restart Chapter (preview)
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
