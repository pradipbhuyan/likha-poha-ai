import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import {
  Settings, Sparkles, History, Printer, Ban, BarChart3,
  Lightbulb, Target, ClipboardList, Bell, FlaskConical, BookOpen,
  Pin, CheckCircle2, Loader2, ListChecks, Wrench, NotebookPen,
  Users, AlertTriangle, Link2, Presentation, ArrowLeft, Download,
  Pencil, Save, RotateCcw, UserCheck,
} from "lucide-react";
import { generateLessonPlanPdf } from "../utils/lessonPlanPdf";
import { normalizeTutorMarkdown } from "../utils/markdownCleanup";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const GRADES = ["Grade 5","Grade 6","Grade 7","Grade 8","Grade 9","Grade 10","Grade 11","Grade 12"];

// Maps the plain-text section headings authored in lesson_plan_bank markdown
// to a matching Lucide icon, so the rendered plan uses icons instead of emoji.
const H2_ICONS = {
  "Lesson Overview": BookOpen,
  "Learning Objectives": Target,
  "Prerequisites": ListChecks,
  "Materials & Resources": Wrench,
  "Lesson Plan (Step-by-Step)": ClipboardList,
  "Homework Assignment": NotebookPen,
  "Differentiation Strategies": Users,
  "Common Misconceptions to Address": AlertTriangle,
  "NCERT Alignment": Link2,
};
const H3_ICONS = {
  "Introduction & Hook": Bell,
  "Direct Instruction": Presentation,
  "Guided Practice": FlaskConical,
  "Student Activity": Users,
  "Assessment & Closure": CheckCircle2,
};

// The fixed section order every lesson_plan_bank handout is authored with —
// used to drive the stepwise "creating your lesson plan" reveal animation.
const SECTION_STEPS = Object.keys(H2_ICONS);

function HeadingWithIcon({ level: Tag, iconMap, children, ...props }) {
  const text = Array.isArray(children) ? children.join("") : String(children ?? "");
  // H3 headings carry a trailing "(N minutes)" that isn't part of the icon lookup key.
  const key = text.replace(/\s*\(\d+[^)]*\)\s*$/, "").trim();
  const Icon = iconMap[key];
  return (
    <Tag {...props} style={{ display: "flex", alignItems: "center", gap: 8 }}>
      {Icon && <Icon size={Tag === "h2" ? 19 : 16} strokeWidth={2.2} style={{ flexShrink: 0 }} />}
      {children}
    </Tag>
  );
}

const MARKDOWN_COMPONENTS = {
  h2: (props) => <HeadingWithIcon level="h2" iconMap={H2_ICONS} {...props} />,
  h3: (props) => <HeadingWithIcon level="h3" iconMap={H3_ICONS} {...props} />,
};

const PRINT_STYLES = `
  body { font-family: Arial, sans-serif; margin: 36px; color: #000; font-size: 12pt; line-height: 1.6; }
  h1 { font-size: 18pt; margin-bottom: 4px; }
  h2 { font-size: 14pt; margin-top: 20px; margin-bottom: 6px; border-bottom: 1px solid #aaa; padding-bottom: 4px; }
  h3 { font-size: 12pt; margin-top: 14px; margin-bottom: 4px; }
  ul, ol { margin-left: 18px; }
  li { margin-bottom: 3px; }
  p { margin: 4px 0; }
  .header { text-align: center; border-bottom: 2px solid #000; padding-bottom: 10px; margin-bottom: 16px; }
  .footer { text-align: center; font-size: 9pt; color: #666; margin-top: 30px; border-top: 1px solid #ccc; padding-top: 8px; }
  @media print { .no-print { display: none; } }
`;

export default function TeacherLessonPlanPage({ user }) {
  const [syllabus, setSyllabus] = useState({});
  const [syllabusLoading, setSyllabusLoading] = useState(true);

  const [grade, setGrade] = useState("Grade 9");
  const [subject, setSubject] = useState("");
  const [chapter, setChapter] = useState("");

  const [generating, setGenerating] = useState(false);
  const [plan, setPlan] = useState("");
  const [planMeta, setPlanMeta] = useState(null);
  const [error, setError] = useState("");

  // Whether the currently displayed plan is this teacher's own saved edit
  // (private to them) vs the shared system-generated version. Editing/
  // saving here never touches the system-generated lesson_plan_bank file —
  // it only ever creates/updates this teacher's own private copy.
  const [isTeacherEdited, setIsTeacherEdited] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [draftPlan, setDraftPlan] = useState("");
  const [saving, setSaving] = useState(false);
  const [reverting, setReverting] = useState(false);
  const [saveError, setSaveError] = useState("");
  const [saveNotice, setSaveNotice] = useState("");

  // Lesson plans are served instantly from a pre-authored bank (no live LLM
  // call), so the fetch itself has nothing to visibly wait for. This holds
  // the fetched result back and reveals it section-by-section against the
  // Likha Poha AI gif so "Generate" still feels like it's building the plan.
  const [pendingResult, setPendingResult] = useState(null);
  const [stepIndex, setStepIndex] = useState(0);

  // History of generated plans (session only)
  const [history, setHistory] = useState([]);
  const [historyOpen, setHistoryOpen] = useState(false);

  useEffect(() => {
    async function loadSyllabus() {
      setSyllabusLoading(true);
      try {
        const res = await fetch(`${API_BASE}/api/syllabus`);
        const data = await res.json();
        setSyllabus(data.syllabus || {});
      } catch { /* ignore */ }
      setSyllabusLoading(false);
    }
    loadSyllabus();
  }, []);

  const subjects = Object.keys(syllabus?.[grade]?.CBSE || {});
  const chapters = (syllabus?.[grade]?.CBSE?.[subject] || []).filter(c => c !== "Uploaded Book Content");

  useEffect(() => { setSubject(subjects[0] || ""); setChapter(""); }, [grade]);
  useEffect(() => { setChapter(chapters[0] || ""); }, [subject, grade]);

  // Advances one section at a time through SECTION_STEPS, then reveals the
  // already-fetched plan once every step has had its moment on screen.
  useEffect(() => {
    if (!pendingResult) return;
    if (stepIndex >= SECTION_STEPS.length) {
      const t = setTimeout(() => {
        setPlan(pendingResult.plan);
        setPlanMeta(pendingResult.meta);
        setIsTeacherEdited(!!pendingResult.isTeacherEdited);
        setIsEditing(false);
        setDraftPlan("");
        setSaveError("");
        setSaveNotice("");
        setHistory(prev => [{ ...pendingResult.meta, plan: pendingResult.plan }, ...prev.slice(0, 9)]);
        setGenerating(false);
        setPendingResult(null);
        setStepIndex(0);
      }, 350);
      return () => clearTimeout(t);
    }
    const t = setTimeout(() => setStepIndex(i => i + 1), 260);
    return () => clearTimeout(t);
  }, [pendingResult, stepIndex]);

  // ── Free-tier daily limit ──────────────────────────────────────────────────
  const freeTeacher = user?.role === "teacher" &&
    (!user?.subscriptionPlan || user.subscriptionPlan === "free") &&
    !user?.accessCbse;
  const todayPlanCount = freeTeacher
    ? (() => { try { return parseInt(localStorage.getItem(`teacher_lessonplan_${user?.username}_${new Date().toISOString().slice(0,10)}`)||"0",10); } catch(e) { return 0; } })()
    : 0;
  const planLimitReached = freeTeacher && todayPlanCount >= 2;
  function incrementPlanCount() {
    try { const k=`teacher_lessonplan_${user?.username}_${new Date().toISOString().slice(0,10)}`; localStorage.setItem(k,String(parseInt(localStorage.getItem(k)||"0",10)+1)); } catch(e) { /* non-critical */ }
  }

  async function handleGenerate() {
    if (planLimitReached) return;
    if (!grade || !subject || !chapter) {
      setError("Please select Grade, Subject and Chapter.");
      return;
    }
    setError("");
    setGenerating(true);
    setPlan("");
    setPlanMeta(null);
    setPendingResult(null);
    setStepIndex(0);
    try {
      const res = await fetch(`${API_BASE}/api/teacher/lesson-plan/generate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${user?.accessToken}`,
        },
        body: JSON.stringify({ grade, subject, chapter }),
      });
      const data = await res.json();
      if (!res.ok || !data.success) throw new Error(data.detail || data.message || "Generation failed");
      const meta = { grade, subject, chapter, ts: new Date().toLocaleTimeString() };
      // Hand off to the stepwise-reveal effect above instead of showing the
      // plan immediately — see the pendingResult/stepIndex effect.
      setPendingResult({ plan: data.lesson_plan, meta, isTeacherEdited: !!data.is_teacher_edited });
      if (freeTeacher) incrementPlanCount();
    } catch (err) {
      setError(err.message || "Failed to generate lesson plan. Please try again.");
      setGenerating(false);
    }
  }

  function handleDownloadPdf() {
    if (!plan) return;
    generateLessonPlanPdf(plan, planMeta);
  }

  function handleStartEdit() {
    setDraftPlan(plan);
    setSaveError("");
    setSaveNotice("");
    setIsEditing(true);
  }

  function handleCancelEdit() {
    setIsEditing(false);
    setDraftPlan("");
    setSaveError("");
  }

  async function handleSaveEdit() {
    if (!planMeta) return;
    setSaving(true);
    setSaveError("");
    setSaveNotice("");
    try {
      const res = await fetch(`${API_BASE}/api/teacher/lesson-plan/save`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${user?.accessToken}`,
        },
        body: JSON.stringify({
          grade: planMeta.grade,
          subject: planMeta.subject,
          chapter: planMeta.chapter,
          lesson_plan_markdown: draftPlan,
        }),
      });
      const data = await res.json();
      if (!res.ok || !data.success) throw new Error(data.detail || "Failed to save your edits.");
      setPlan(draftPlan);
      setIsTeacherEdited(true);
      setIsEditing(false);
      setDraftPlan("");
      setSaveNotice("Saved — only visible to you. The original plan is unchanged for other teachers.");
    } catch (err) {
      setSaveError(err.message || "Failed to save your edits. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  async function handleRevert() {
    if (!planMeta) return;
    setReverting(true);
    setSaveError("");
    setSaveNotice("");
    try {
      const res = await fetch(`${API_BASE}/api/teacher/lesson-plan/revert`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${user?.accessToken}`,
        },
        body: JSON.stringify({ grade: planMeta.grade, subject: planMeta.subject, chapter: planMeta.chapter }),
      });
      const data = await res.json();
      if (!res.ok || !data.success) throw new Error(data.detail || "Failed to revert.");
      setPlan(data.lesson_plan || "");
      setIsTeacherEdited(false);
      setIsEditing(false);
      setDraftPlan("");
      setSaveNotice("Reverted to the original system-generated plan.");
    } catch (err) {
      setSaveError(err.message || "Failed to revert. Please try again.");
    } finally {
      setReverting(false);
    }
  }

  function handlePrint() {
    if (!plan) return;
    const content = `<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Lesson Plan</title>
      <style>${PRINT_STYLES}</style></head><body>
      <div class="header">
        <h1>CBSE Lesson Plan</h1>
        <p>${planMeta?.grade} · ${planMeta?.subject} · ${planMeta?.chapter}</p>
        <p>Date: ${new Date().toLocaleDateString("en-IN")}</p>
        <p style="font-size:10pt;color:#555">Generated by Likha Poha AI for Teacher</p>
      </div>
      <div id="content"></div>
      <div class="footer">— Likha Poha AI Lesson Plan — For classroom use only —</div>
      </body></html>`;
    const w = window.open("", "_blank");
    w.document.write(content);
    // Render markdown as plain paragraphs using a simple converter
    const mdToHtml = plan
      .replace(/^#{1,6}\s+(.+)$/gm, (_, t) => `<h2>${t}</h2>`)
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/^- (.+)$/gm, "<li>$1</li>")
      .replace(/(<li>.*<\/li>\n?)+/g, s => `<ul>${s}</ul>`)
      .replace(/^(\d+)\. (.+)$/gm, "<li>$2</li>")
      .replace(/\n\n/g, "</p><p>")
      .replace(/\n/g, "<br/>");
    w.document.getElementById("content").innerHTML = `<p>${mdToHtml}</p>`;
    w.document.close();
    w.focus();
    setTimeout(() => w.print(), 600);
  }

  return (
    <div className="premium-page" style={{ maxWidth: 960 }}>
      {/* Settings card */}
      <div className="premium-card" style={{ marginBottom: 24 }}>
        <h3 style={{ marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
          <Settings size={17} strokeWidth={2.2} /> Plan Settings
        </h3>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 14, marginBottom: 14 }}>
          <label style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <span style={{ fontSize: ".82rem", fontWeight: 600, color: "var(--muted)" }}>Grade</span>
            <select value={grade} onChange={e => setGrade(e.target.value)}>
              {GRADES.map(g => <option key={g}>{g}</option>)}
            </select>
          </label>
          <label style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <span style={{ fontSize: ".82rem", fontWeight: 600, color: "var(--muted)" }}>Subject</span>
            <select value={subject} onChange={e => setSubject(e.target.value)}>
              {syllabusLoading ? <option>Loading…</option> : subjects.map(s => <option key={s}>{s}</option>)}
            </select>
          </label>
          <label style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <span style={{ fontSize: ".82rem", fontWeight: 600, color: "var(--muted)" }}>Chapter / Topic</span>
            <select value={chapter} onChange={e => setChapter(e.target.value)}>
              {chapters.length === 0 ? <option>Select subject first</option> : chapters.map(c => <option key={c}>{c}</option>)}
            </select>
          </label>
        </div>

        {error && <div className="error-box" style={{ marginBottom: 12 }}>{error}</div>}

        {/* Daily limit banner for free-tier teachers */}
        {freeTeacher && (
          <div style={{ marginBottom: 10, padding: "8px 12px", borderRadius: 8, fontSize: ".82rem", fontWeight: 600,
            display: "flex", alignItems: "center", gap: 7,
            background: planLimitReached ? "rgba(239,68,68,.08)" : "rgba(99,102,241,.07)",
            border: `1px solid ${planLimitReached ? "rgba(239,68,68,.3)" : "rgba(167,139,250,.25)"}`,
            color: planLimitReached ? "#f87171" : "#a78bfa" }}>
            {planLimitReached
              ? <><Ban size={15} /> Daily limit reached (2/2 lesson plans today). Upgrade for unlimited or come back tomorrow.</>
              : <><BarChart3 size={15} /> {todayPlanCount}/2 free lesson plans used today</>}
          </div>
        )}

        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
          <button className="primary-btn" onClick={handleGenerate} disabled={generating || syllabusLoading || planLimitReached} style={{ maxWidth: 260, marginTop: 0, display: "inline-flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
            {planLimitReached
              ? <><Ban size={16} /> Daily Limit Reached</>
              : generating
                ? <><Loader2 size={16} className="spin" /> Generating Lesson Plan…</>
                : <><Sparkles size={16} /> Generate Lesson Plan</>}
          </button>
          {history.length > 0 && (
            <button onClick={() => setHistoryOpen(h => !h)}
              style={{ padding: "11px 18px", borderRadius: 10, border: "1.5px solid var(--border)", background: "transparent", color: "var(--muted)", fontFamily: "inherit", fontSize: ".85rem", cursor: "pointer", display: "inline-flex", alignItems: "center", gap: 7 }}>
              <History size={15} /> History ({history.length})
            </button>
          )}
        </div>
      </div>

      {/* History panel */}
      {historyOpen && history.length > 0 && (
        <div className="premium-card" style={{ marginBottom: 20 }}>
          <h4 style={{ marginBottom: 12, display: "flex", alignItems: "center", gap: 7 }}>
            <History size={16} /> Recently Generated Plans
          </h4>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {history.map((h, i) => (
              <button key={i} onClick={() => { setPlan(h.plan); setPlanMeta(h); setHistoryOpen(false); }}
                style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "8px 12px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--card-bg)", cursor: "pointer", fontFamily: "inherit", textAlign: "left" }}>
                <div>
                  <span style={{ fontWeight: 600, fontSize: ".85rem" }}>{h.grade} — {h.subject}</span>
                  <span style={{ fontSize: ".75rem", color: "var(--muted)", marginLeft: 8 }}>{h.chapter.length > 40 ? h.chapter.slice(0, 38) + "…" : h.chapter}</span>
                </div>
                <span style={{ fontSize: ".72rem", color: "var(--muted)" }}>{h.ts}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Stepwise "creating your lesson plan" reveal — the plan itself is a
          near-instant bank lookup, so this holds it back and walks through
          SECTION_STEPS to give Generate a sense of building something. */}
      {generating && (
        <div className="premium-card" style={{ padding: "36px 28px", textAlign: "center" }}>
          <img
            src="/likhapohaai.gif"
            alt="Likha Poha AI is creating your lesson plan…"
            style={{ width: 150, height: "auto", margin: "0 auto 10px", display: "block" }}
          />
          <div style={{ fontWeight: 700, fontSize: "1rem", marginBottom: 20 }}>Creating your lesson plan…</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 6, maxWidth: 380, margin: "0 auto", textAlign: "left" }}>
            {SECTION_STEPS.map((label, i) => {
              const Icon = H2_ICONS[label];
              const done = i < stepIndex;
              const active = i === stepIndex;
              return (
                <div key={label} style={{
                  display: "flex", alignItems: "center", gap: 10, padding: "7px 10px", borderRadius: 8,
                  background: active ? "rgba(99,102,241,.08)" : "transparent",
                  opacity: done || active ? 1 : 0.4,
                  transition: "opacity .25s ease, background .25s ease",
                }}>
                  {done
                    ? <CheckCircle2 size={16} style={{ color: "var(--success)", flexShrink: 0 }} />
                    : active
                      ? <Loader2 size={16} className="spin" style={{ color: "var(--primary)", flexShrink: 0 }} />
                      : <Icon size={16} style={{ opacity: .6, flexShrink: 0 }} />}
                  <span style={{ fontSize: ".85rem", fontWeight: active ? 700 : 500 }}>{label}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Plan preview */}
      {plan && planMeta && (
        <div>
          {/* Action bar */}
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center", marginBottom: 18 }}>
            {!isEditing && (
              <button className="primary-btn" onClick={handleDownloadPdf} style={{ maxWidth: 220, marginTop: 0, display: "inline-flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
                <Download size={16} /> Download as PDF
              </button>
            )}
            {!isEditing && (
              <button onClick={handlePrint}
                style={{ padding: "12px 18px", borderRadius: 12, border: "1.5px solid var(--border)", background: "var(--panel-soft)", color: "var(--text)", fontWeight: 600, fontFamily: "inherit", fontSize: ".85rem", cursor: "pointer", display: "inline-flex", alignItems: "center", gap: 6 }}>
                <Printer size={14} /> Print
              </button>
            )}
            {!isEditing && (
              <button onClick={handleStartEdit}
                style={{ padding: "12px 18px", borderRadius: 12, border: "1.5px solid var(--border)", background: "var(--panel-soft)", color: "var(--text)", fontWeight: 600, fontFamily: "inherit", fontSize: ".85rem", cursor: "pointer", display: "inline-flex", alignItems: "center", gap: 6 }}>
                <Pencil size={14} /> Edit Plan
              </button>
            )}
            {!isEditing && isTeacherEdited && (
              <button onClick={handleRevert} disabled={reverting}
                style={{ padding: "12px 18px", borderRadius: 12, border: "1.5px solid rgba(239,68,68,.35)", background: "rgba(239,68,68,.06)", color: "#dc2626", fontWeight: 600, fontFamily: "inherit", fontSize: ".85rem", cursor: "pointer", display: "inline-flex", alignItems: "center", gap: 6 }}>
                {reverting ? <Loader2 size={14} className="spin" /> : <RotateCcw size={14} />} Revert to Original
              </button>
            )}
            {!isEditing && (
              <button onClick={() => { setPlan(""); setPlanMeta(null); setIsEditing(false); setIsTeacherEdited(false); }}
                style={{ padding: "12px 18px", borderRadius: 12, border: "1.5px solid var(--border)", background: "var(--panel-soft)", color: "var(--text)", fontWeight: 600, fontFamily: "inherit", fontSize: ".85rem", cursor: "pointer", display: "inline-flex", alignItems: "center", gap: 6 }}>
                <ArrowLeft size={14} /> New Plan
              </button>
            )}
          </div>

          {/* Meta badges */}
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16 }}>
            {[
              { label: `${planMeta.grade}`, color: "#2563eb" },
              { label: planMeta.subject, color: "#7c3aed" },
              { label: planMeta.chapter.length > 42 ? planMeta.chapter.slice(0, 40) + "…" : planMeta.chapter, color: "#059669" },
            ].map(b => (
              <span key={b.label} style={{ fontSize: ".78rem", fontWeight: 700, padding: "4px 10px", borderRadius: 20, background: `${b.color}22`, color: b.color, border: `1px solid ${b.color}44` }}>
                {b.label}
              </span>
            ))}
            {isTeacherEdited && (
              <span style={{ fontSize: ".78rem", fontWeight: 700, padding: "4px 10px", borderRadius: 20, background: "rgba(217,119,6,.14)", color: "#d97706", border: "1px solid rgba(217,119,6,.35)", display: "inline-flex", alignItems: "center", gap: 5 }}>
                <UserCheck size={13} /> Your saved version — visible only to you
              </span>
            )}
          </div>

          {saveNotice && !isEditing && (
            <div style={{ marginBottom: 14, padding: "8px 12px", borderRadius: 8, fontSize: ".82rem", fontWeight: 600, background: "rgba(16,185,129,.08)", border: "1px solid rgba(16,185,129,.3)", color: "#059669" }}>
              {saveNotice}
            </div>
          )}
          {saveError && (
            <div className="error-box" style={{ marginBottom: 14 }}>{saveError}</div>
          )}

          {isEditing ? (
            /* Edit mode: a plain markdown textarea. Saving writes ONLY to
               this teacher's own private teacher_lesson_plan_edits row —
               the shared system-generated bank file is never touched, and
               no other teacher will ever see this content. */
            <div className="premium-card" style={{ padding: "24px 28px" }}>
              <div style={{ marginBottom: 12, padding: "8px 12px", borderRadius: 8, fontSize: ".8rem", fontWeight: 600,
                background: "rgba(99,102,241,.06)", border: "1px solid rgba(99,102,241,.2)", color: "var(--muted)",
                display: "flex", alignItems: "center", gap: 7 }}>
                <Pencil size={14} /> Editing markdown — only you will see this saved version. The original plan stays the same for every other teacher.
              </div>
              <textarea
                value={draftPlan}
                onChange={e => setDraftPlan(e.target.value)}
                rows={26}
                style={{
                  width: "100%", fontFamily: "monospace", fontSize: ".82rem", lineHeight: 1.6,
                  padding: "14px 16px", borderRadius: 10, border: "1.5px solid var(--border)",
                  background: "var(--panel-soft)", color: "var(--text)", resize: "vertical",
                }}
              />
              <div style={{ marginTop: 16, display: "flex", gap: 10, alignItems: "center" }}>
                <button className="primary-btn" onClick={handleSaveEdit} disabled={saving || !draftPlan.trim()}
                  style={{ maxWidth: 200, marginTop: 0, display: "inline-flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
                  {saving ? <><Loader2 size={16} className="spin" /> Saving…</> : <><Save size={16} /> Save My Version</>}
                </button>
                <button onClick={handleCancelEdit} disabled={saving}
                  style={{ padding: "12px 18px", borderRadius: 12, border: "1.5px solid var(--border)", background: "var(--panel-soft)", color: "var(--text)", fontWeight: 600, fontFamily: "inherit", fontSize: ".85rem", cursor: "pointer" }}>
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            /* Rendered markdown */
            <div className="premium-card" style={{ padding: "28px 32px" }}>
              <div className="markdown-content" style={{ fontSize: ".9rem", lineHeight: 1.7 }}>
                <ReactMarkdown
                  remarkPlugins={[remarkGfm, remarkMath]}
                  rehypePlugins={[rehypeKatex]}
                  components={MARKDOWN_COMPONENTS}
                >
                  {normalizeTutorMarkdown(plan)}
                </ReactMarkdown>
              </div>

              {/* Download/Print buttons at bottom too. No "Regenerate" here —
                  plans are served from a fixed pre-authored bank, so
                  regenerating the same grade/subject/chapter always returns
                  byte-identical content; "New Plan" above is the only way to
                  get something different. */}
              <div style={{ marginTop: 24, paddingTop: 16, borderTop: "1px solid var(--border)", display: "flex", alignItems: "center", gap: 10 }}>
                <button className="primary-btn" onClick={handleDownloadPdf} style={{ maxWidth: 220, marginTop: 0, display: "inline-flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
                  <Download size={16} /> Download as PDF
                </button>
                <button onClick={handlePrint}
                  style={{ padding: "10px 18px", borderRadius: 10, border: "1.5px solid var(--border)", background: "transparent", color: "var(--muted)", fontFamily: "inherit", fontSize: ".85rem", cursor: "pointer", display: "inline-flex", alignItems: "center", gap: 7 }}>
                  <Printer size={14} /> Print
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Empty state tip — uses the same premium-card container as every
          other panel on this page so all cards share one consistent
          background, border-radius, and shadow instead of a mismatched
          tinted box. */}
      {!plan && !generating && (
        <div className="premium-card" style={{ display: "flex", gap: 14, alignItems: "flex-start" }}>
          <div style={{
            flexShrink: 0, width: 40, height: 40, borderRadius: 12,
            background: "rgba(99,102,241,.12)", display: "flex",
            alignItems: "center", justifyContent: "center",
          }}>
            <Lightbulb size={22} strokeWidth={2} style={{ color: "#7c6fe0" }} />
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: ".88rem", marginBottom: 6 }}>What the lesson plan includes</div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "4px 16px", fontSize: ".8rem", color: "var(--muted)", lineHeight: 1.7 }}>
              {[
                { Icon: Target, label: "3 Learning objectives (Bloom's taxonomy)" },
                { Icon: ClipboardList, label: "Step-by-step lesson activities with timings" },
                { Icon: Bell, label: "Introduction hook to grab attention" },
                { Icon: FlaskConical, label: "Guided practice + student activities" },
                { Icon: BookOpen, label: "NCERT-aligned homework assignment" },
                { Icon: Target, label: "Differentiation for support & extension" },
                { Icon: Pin, label: "Common misconceptions to address" },
                { Icon: CheckCircle2, label: "Assessment & exit ticket strategy" },
              ].map(({ Icon, label }) => (
                <div key={label} style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <Icon size={14} strokeWidth={2} style={{ flexShrink: 0 }} /> {label}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
