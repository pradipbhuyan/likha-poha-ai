import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Settings, Sparkles, History, Printer, RefreshCw, Ban, BarChart3,
  Lightbulb, Target, ClipboardList, Bell, FlaskConical, BookOpen,
  Pin, CheckCircle2, Loader2, ListChecks, Wrench, NotebookPen,
  Users, AlertTriangle, Link2, Presentation, ArrowLeft,
} from "lucide-react";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const GRADES = ["Grade 5","Grade 6","Grade 7","Grade 8","Grade 9","Grade 10"];

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
      setPlan(data.lesson_plan);
      const meta = { grade, subject, chapter, ts: new Date().toLocaleTimeString() };
      setPlanMeta(meta);
      setHistory(prev => [{ ...meta, plan: data.lesson_plan }, ...prev.slice(0, 9)]);
      if (freeTeacher) incrementPlanCount();
    } catch (err) {
      setError(err.message || "Failed to generate lesson plan. Please try again.");
    } finally {
      setGenerating(false);
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

        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <button className="primary-btn" onClick={handleGenerate} disabled={generating || syllabusLoading || planLimitReached} style={{ maxWidth: 260, display: "inline-flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
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

      {/* Plan preview */}
      {plan && planMeta && (
        <div>
          {/* Action bar */}
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 18 }}>
            <button className="primary-btn" onClick={handlePrint} style={{ maxWidth: 240, display: "inline-flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
              <Printer size={16} /> Download / Print PDF
            </button>
            <button onClick={() => { setPlan(""); setPlanMeta(null); }}
              style={{ padding: "10px 18px", borderRadius: 10, border: "1.5px solid var(--border)", background: "transparent", color: "var(--muted)", fontFamily: "inherit", fontSize: ".85rem", cursor: "pointer", display: "inline-flex", alignItems: "center", gap: 6 }}>
              <ArrowLeft size={14} /> New Plan
            </button>
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
          </div>

          {/* Rendered markdown */}
          <div className="premium-card" style={{ padding: "28px 32px" }}>
            <div className="markdown-content" style={{ fontSize: ".9rem", lineHeight: 1.7 }}>
              <ReactMarkdown remarkPlugins={[remarkGfm]} components={MARKDOWN_COMPONENTS}>{plan}</ReactMarkdown>
            </div>

            {/* Print button at bottom too */}
            <div style={{ marginTop: 24, paddingTop: 16, borderTop: "1px solid var(--border)", display: "flex", gap: 10 }}>
              <button className="primary-btn" onClick={handlePrint} style={{ maxWidth: 240, display: "inline-flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
                <Printer size={16} /> Download as PDF
              </button>
              <button onClick={handleGenerate} disabled={generating}
                style={{ padding: "10px 18px", borderRadius: 10, border: "1.5px solid var(--border)", background: "transparent", color: "var(--muted)", fontFamily: "inherit", fontSize: ".85rem", cursor: "pointer", display: "inline-flex", alignItems: "center", gap: 7 }}>
                <RefreshCw size={14} /> Regenerate
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Empty state tip */}
      {!plan && !generating && (
        <div style={{ padding: "20px 22px", borderRadius: 12, background: "rgba(99,102,241,.06)", border: "1px solid rgba(99,102,241,.2)", display: "flex", gap: 14, alignItems: "flex-start" }}>
          <Lightbulb size={26} strokeWidth={2} style={{ flexShrink: 0, color: "#7c6fe0" }} />
          <div>
            <div style={{ fontWeight: 700, fontSize: ".88rem", marginBottom: 6 }}>What the lesson plan includes</div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "4px 16px", fontSize: ".8rem", color: "var(--muted)", lineHeight: 1.7 }}>
              {[
                { Icon: Target, label: "3 Learning objectives (Bloom's taxonomy)" },
                { Icon: ClipboardList, label: "Step-by-step lesson activities with timings" },
                { Icon: Bell, label: "Introduction hook to grab attention" },
                { Icon: FlaskConical, label: "Guided practice + student activities" },
                { Icon: BookOpen, label: "NCERT-aligned homework assignment" },
                { Icon: Target, label: "Differentiation for slow/fast learners" },
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
