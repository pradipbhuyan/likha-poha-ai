/**
 * StudyPlannerPage.jsx — AI Study Planner
 * =========================================
 * Phase 1: Live exam countdown + today's recommendation
 * Phase 2: LLM-generated week-by-week plan (accordion timeline)
 * Phase 3: Daily task checklist with done/skipped tracking
 */

import { useEffect, useState, useCallback } from "react";
import { Loader } from "lucide-react";
import {
  getStudyPlan,
  generateStudyPlan,
  updateTaskStatus,
  migrateStudyPlanner,
} from "../api/studyPlanner";

// ── Exam options ──────────────────────────────────────────────────────────────
const EXAMS = [
  { value: "jee_main",  label: "JEE Main",   icon: "📐", color: "#6366f1" },
  { value: "neet_ug",   label: "NEET UG",    icon: "🔬", color: "#10b981" },
  { value: "cuet_ug",   label: "CUET UG",    icon: "🏛️", color: "#f59e0b" },
  { value: "sat",       label: "SAT",        icon: "🎓", color: "#3b82f6" },
  { value: "ielts",     label: "IELTS",      icon: "🌐", color: "#8b5cf6" },
  { value: "toefl_ibt", label: "TOEFL iBT",  icon: "📡", color: "#06b6d4" },
];

// ── Task type styles ──────────────────────────────────────────────────────────
const TASK_TYPE_CONFIG = {
  revise:         { icon: "📖", color: "#6366f1", label: "Revise" },
  practice:       { icon: "⚡", color: "#f59e0b", label: "Practice" },
  formula_review: { icon: "📐", color: "#10b981", label: "Formula Review" },
  mock_test:      { icon: "📝", color: "#ef4444", label: "Mock Test" },
  light_revision: { icon: "🌅", color: "#22c55e", label: "Light Revision" },
};

// ── Helpers ───────────────────────────────────────────────────────────────────
function pad2(n) { return String(n).padStart(2, "0"); }

// ── Verbose generation progress panel ────────────────────────────────────────
// Shows cycling status messages + animated progress bar while the LLM generates.
// Entirely client-side — no backend streaming needed.
function GeneratingProgress({ examLabel, weakTopics, weeksRemaining, dailyHours, color }) {
  const [stepIdx, setStepIdx] = useState(0);
  const [elapsed, setElapsed] = useState(0);
  const [progPct, setProgPct] = useState(2);

  // Build exam/context-specific steps
  const weakStr = weakTopics?.length > 0
    ? weakTopics.slice(0, 3).join(", ") + (weakTopics.length > 3 ? `… +${weakTopics.length - 3} more` : "")
    : "none yet (will scan test history)";

  const steps = [
    { icon: "🔍", text: `Reading your test history and identifying weak topics…`, detail: `Weak topics found: ${weakStr}` },
    { icon: "📅", text: `Calculating ${weeksRemaining} weeks until your ${examLabel} exam…`, detail: "Mapping study phases: Learning → Revision → Mock Tests → Light Revision" },
    { icon: "🧠", text: `Asking AI to design your personalised ${examLabel} schedule…`, detail: `${dailyHours}h/day × ${weeksRemaining} weeks = ${dailyHours * weeksRemaining * 7} total study hours` },
    { icon: "📝", text: `Writing Week 1–${Math.min(6, weeksRemaining)} study plan (weak topics first)…`, detail: weakTopics?.length > 0 ? `Prioritising: ${weakStr}` : "Balanced topic coverage across subjects" },
    { icon: "📚", text: `Mapping all ${examLabel} chapters across subjects…`, detail: "Assigning chapters to days — no overlaps, no gaps" },
    { icon: "🗓️", text: `Building Week ${Math.min(7, weeksRemaining)}–${Math.min(Math.ceil(weeksRemaining * 0.7), weeksRemaining)} full revision cycle…`, detail: "Each chapter revisited once before the final 4 weeks" },
    { icon: "🧪", text: `Adding mock test weeks and formula review sessions…`, detail: "Final 2 weeks: daily mock tests + light revision only" },
    { icon: "📖", text: `Assigning daily tasks with durations (${dailyHours}h/day)…`, detail: "Each task has a description, topic, and estimated time" },
    { icon: "💾", text: `Saving ${weeksRemaining * 7} daily tasks to your study calendar…`, detail: "Tasks stored with exact dates — starting from today" },
    { icon: "✅", text: `Finalising your personalised ${examLabel} study plan…`, detail: "Almost there! Verifying schedule completeness" },
  ];

  // Advance step every 8 seconds, progress bar grows smoothly
  useEffect(() => {
    const stepTimer = setInterval(() => {
      setStepIdx(i => Math.min(i + 1, steps.length - 1));
    }, 8000);
    return () => clearInterval(stepTimer);
  }, [steps.length]);

  // Elapsed second counter
  useEffect(() => {
    const tick = setInterval(() => setElapsed(e => e + 1), 1000);
    return () => clearInterval(tick);
  }, []);

  // Progress bar: fills to 88% over ~80s, then stalls waiting for response
  useEffect(() => {
    const rate = setInterval(() => {
      setProgPct(p => {
        if (p >= 88) return p; // stall at 88% until done
        return Math.min(88, p + (88 / 80)); // ~80s to reach 88%
      });
    }, 1000);
    return () => clearInterval(rate);
  }, []);

  const currentStep = steps[stepIdx];
  const mins = Math.floor(elapsed / 60);
  const secs = elapsed % 60;

  return (
    <div style={{ background: `linear-gradient(135deg,${color}12,${color}06)`, border: `2px solid ${color}40`, borderRadius: 16, padding: "24px 28px", maxWidth: 560, margin: "0 auto" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 20 }}>
        <div style={{ width: 40, height: 40, borderRadius: "50%", background: `${color}20`, border: `2px solid ${color}50`, display: "flex", alignItems: "center", justifyContent: "center", animation: "spin 2s linear infinite", flexShrink: 0 }}>
          <span style={{ fontSize: "1.1rem", animation: "none" }}>🤖</span>
        </div>
        <div>
          <div style={{ fontWeight: 800, fontSize: ".9rem" }}>AI is building your {examLabel} plan…</div>
          <div style={{ fontSize: ".68rem", color: "var(--muted,#64748b)", marginTop: 2 }}>
            ⏱ {mins > 0 ? `${mins}m ` : ""}{pad2(secs)}s elapsed · typically 30–90 seconds
          </div>
        </div>
      </div>

      {/* Progress bar */}
      <div style={{ marginBottom: 18 }}>
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: ".62rem", color: "var(--muted,#64748b)", marginBottom: 5 }}>
          <span>Plan generation progress</span>
          <span style={{ color, fontWeight: 700 }}>{Math.round(progPct)}%</span>
        </div>
        <div style={{ background: "var(--border,#334155)", borderRadius: 8, height: 8, overflow: "hidden" }}>
          <div style={{ width: `${progPct}%`, height: "100%", background: `linear-gradient(90deg,${color},${color}cc)`, borderRadius: 8, transition: "width 1s linear" }} />
        </div>
      </div>

      {/* Current step */}
      <div style={{ background: "var(--panel,#1e293b)", border: `1px solid ${color}30`, borderRadius: 10, padding: "14px 16px", marginBottom: 14 }}>
        <div style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
          <span style={{ fontSize: "1.2rem", flexShrink: 0, marginTop: 1 }}>{currentStep.icon}</span>
          <div>
            <div style={{ fontWeight: 700, fontSize: ".82rem", marginBottom: 4 }}>{currentStep.text}</div>
            <div style={{ fontSize: ".7rem", color: "var(--muted,#64748b)", lineHeight: 1.5 }}>{currentStep.detail}</div>
          </div>
        </div>
      </div>

      {/* Step dots */}
      <div style={{ display: "flex", gap: 5, justifyContent: "center", marginBottom: 14 }}>
        {steps.map((_, i) => (
          <div key={i} style={{
            width: i === stepIdx ? 18 : 6,
            height: 6,
            borderRadius: 3,
            background: i < stepIdx ? "#22c55e" : i === stepIdx ? color : "var(--border,#334155)",
            transition: "all .4s",
          }} />
        ))}
      </div>

      {/* Completed steps */}
      {stepIdx > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 4, maxHeight: 120, overflowY: "auto" }}>
          {steps.slice(0, stepIdx).map((s, i) => (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 7, fontSize: ".68rem", color: "#22c55e" }}>
              <span style={{ fontSize: ".7rem" }}>✓</span>
              <span style={{ color: "#4ade80" }}>{s.text}</span>
            </div>
          ))}
        </div>
      )}

      <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
    </div>
  );
}

function CountdownTimer({ daysRemaining, weeksRemaining, examDate, examLabel, color }) {
  const [tick, setTick] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setTick(t => t + 1), 1000);
    return () => clearInterval(id);
  }, []);

  const urgency = daysRemaining <= 14 ? "#ef4444" : daysRemaining <= 42 ? "#f59e0b" : color;
  const pct = Math.min(100, Math.max(0, 100 - (daysRemaining / (weeksRemaining * 7 + daysRemaining)) * 100));

  return (
    <div style={{ background: `linear-gradient(135deg,${urgency}18,${urgency}08)`, border: `2px solid ${urgency}55`, borderRadius: 16, padding: "20px 24px" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14, flexWrap: "wrap", gap: 10 }}>
        <div>
          <div style={{ fontSize: ".7rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: ".06em", color: urgency, marginBottom: 4 }}>
            {examLabel} Exam Countdown
          </div>
          <div style={{ fontSize: ".78rem", color: "var(--muted,#64748b)" }}>{examDate}</div>
        </div>
        <div style={{ display: "flex", gap: 12 }}>
          {[
            { label: "Weeks", value: weeksRemaining },
            { label: "Days", value: daysRemaining },
          ].map(({ label, value }) => (
            <div key={label} style={{ textAlign: "center", background: `${urgency}15`, border: `1px solid ${urgency}35`, borderRadius: 10, padding: "10px 14px", minWidth: 70 }}>
              <div style={{ fontSize: "1.8rem", fontWeight: 900, color: urgency, lineHeight: 1 }}>{value}</div>
              <div style={{ fontSize: ".6rem", color: "var(--muted,#64748b)", marginTop: 3 }}>{label}</div>
            </div>
          ))}
        </div>
      </div>
      {/* Progress bar — time elapsed */}
      <div>
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: ".62rem", color: "var(--muted,#64748b)", marginBottom: 4 }}>
          <span>Time elapsed</span>
          <span>{pct.toFixed(0)}%</span>
        </div>
        <div style={{ background: "var(--border,#334155)", borderRadius: 6, height: 6, overflow: "hidden" }}>
          <div style={{ width: `${pct}%`, height: "100%", background: urgency, borderRadius: 6, transition: "width .5s" }} />
        </div>
      </div>
    </div>
  );
}

function TaskCard({ task, onToggle, updating }) {
  const isDone = task.status === "done";
  const isSkipped = task.status === "skipped";
  const cfg = TASK_TYPE_CONFIG[task.task_type] || TASK_TYPE_CONFIG.revise;

  return (
    <div style={{
      display: "flex", alignItems: "flex-start", gap: 12, padding: "12px 14px",
      borderRadius: 10,
      background: isDone ? "rgba(34,197,94,.06)" : isSkipped ? "rgba(100,116,139,.05)" : "var(--panel,#1e293b)",
      border: `1px solid ${isDone ? "rgba(34,197,94,.25)" : isSkipped ? "rgba(100,116,139,.2)" : "var(--border,#334155)"}`,
      opacity: isSkipped ? 0.6 : 1,
      transition: "all .15s",
    }}>
      {/* Done checkbox */}
      <button
        onClick={() => onToggle(task.id, isDone ? "pending" : "done")}
        disabled={updating}
        style={{
          width: 22, height: 22, borderRadius: 6, flexShrink: 0, marginTop: 1,
          border: `2px solid ${isDone ? "#22c55e" : "var(--border,#475569)"}`,
          background: isDone ? "#22c55e" : "transparent",
          cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center",
        }}
      >
        {isDone && <span style={{ color: "#fff", fontSize: ".7rem", fontWeight: 900 }}>✓</span>}
      </button>

      {/* Content */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 7, marginBottom: 3, flexWrap: "wrap" }}>
          <span style={{ fontSize: ".6rem", fontWeight: 700, background: `${cfg.color}18`, color: cfg.color, padding: "1px 7px", borderRadius: 20 }}>
            {cfg.icon} {cfg.label}
          </span>
          <span style={{ fontSize: ".6rem", background: "rgba(99,102,241,.1)", color: "#a5b4fc", padding: "1px 7px", borderRadius: 20 }}>{task.subject}</span>
          <span style={{ fontSize: ".62rem", color: "var(--muted,#64748b)" }}>⏱ {task.duration_minutes} min</span>
        </div>
        <div style={{ fontWeight: 700, fontSize: ".82rem", marginBottom: 2, textDecoration: isSkipped ? "line-through" : "none" }}>
          {task.topic}
        </div>
        {task.description && (
          <div style={{ fontSize: ".72rem", color: "var(--muted,#94a3b8)", lineHeight: 1.5 }}>{task.description}</div>
        )}
      </div>

      {/* Skip button */}
      {!isDone && (
        <button
          onClick={() => onToggle(task.id, isSkipped ? "pending" : "skipped")}
          disabled={updating}
          style={{ fontSize: ".6rem", color: isSkipped ? "#22c55e" : "var(--muted,#64748b)", background: "none", border: "none", cursor: "pointer", fontFamily: "inherit", flexShrink: 0, marginTop: 2 }}
          title={isSkipped ? "Undo skip" : "Skip for today"}
        >
          {isSkipped ? "↩ Undo" : "Skip"}
        </button>
      )}
    </div>
  );
}

function WeekAccordion({ week, tasks, defaultOpen }) {
  const [open, setOpen] = useState(defaultOpen || false);
  const total = tasks.length;
  const done = tasks.filter(t => t.status === "done").length;
  const pct = total > 0 ? Math.round(done / total * 100) : 0;
  const color = pct === 100 ? "#22c55e" : pct > 50 ? "#f59e0b" : "#6366f1";

  return (
    <div style={{ background: "var(--panel,#1e293b)", border: "1px solid var(--border,#334155)", borderRadius: 12, overflow: "hidden", marginBottom: 8 }}>
      {/* Header */}
      <div onClick={() => setOpen(o => !o)} style={{ display: "flex", alignItems: "center", gap: 12, padding: "12px 16px", cursor: "pointer", userSelect: "none" }}>
        <div style={{ width: 36, height: 36, borderRadius: 9, background: `${color}18`, border: `2px solid ${color}44`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
          <span style={{ fontSize: ".75rem", fontWeight: 800, color }}>{week}</span>
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: 700, fontSize: ".85rem", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            Week {week}
            {tasks[0]?.task_date && (
              <span style={{ fontWeight: 400, color: "var(--muted,#64748b)", marginLeft: 8, fontSize: ".72rem" }}>
                From {new Date(tasks[0].task_date + "T00:00:00").toLocaleDateString("en-IN", { month: "short", day: "numeric" })}
              </span>
            )}
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 4 }}>
            <div style={{ flex: 1, background: "var(--border,#334155)", borderRadius: 4, height: 4, overflow: "hidden" }}>
              <div style={{ width: `${pct}%`, height: "100%", background: color, borderRadius: 4, transition: "width .4s" }} />
            </div>
            <span style={{ fontSize: ".6rem", color, fontWeight: 700, flexShrink: 0 }}>{done}/{total}</span>
          </div>
        </div>
        <span style={{ fontSize: ".7rem", color: "var(--muted,#64748b)" }}>{open ? "▲" : "▼"}</span>
      </div>

      {/* Tasks */}
      {open && (
        <div style={{ padding: "0 14px 14px", display: "flex", flexDirection: "column", gap: 6 }}>
          {tasks.length === 0 ? (
            <div style={{ fontSize: ".78rem", color: "var(--muted,#64748b)", padding: "8px 0", textAlign: "center" }}>No tasks for this week yet.</div>
          ) : (
            tasks.map(task => (
              <div key={task.id} style={{ padding: "10px 12px", borderRadius: 8, background: "rgba(99,102,241,.04)", border: "1px solid var(--border,#334155)" }}>
                <div style={{ display: "flex", gap: 7, flexWrap: "wrap", marginBottom: 3 }}>
                  <span style={{ fontSize: ".6rem", fontWeight: 700, background: `${(TASK_TYPE_CONFIG[task.task_type] || TASK_TYPE_CONFIG.revise).color}18`, color: (TASK_TYPE_CONFIG[task.task_type] || TASK_TYPE_CONFIG.revise).color, padding: "1px 6px", borderRadius: 20 }}>
                    {(TASK_TYPE_CONFIG[task.task_type] || TASK_TYPE_CONFIG.revise).icon} {(TASK_TYPE_CONFIG[task.task_type] || TASK_TYPE_CONFIG.revise).label}
                  </span>
                  <span style={{ fontSize: ".6rem", background: "rgba(99,102,241,.1)", color: "#a5b4fc", padding: "1px 6px", borderRadius: 20 }}>{task.subject}</span>
                  {task.task_date && (
                    <span style={{ fontSize: ".6rem", color: "var(--muted,#64748b)" }}>
                      {new Date(task.task_date + "T00:00:00").toLocaleDateString("en-IN", { weekday: "short", month: "short", day: "numeric" })}
                    </span>
                  )}
                  <span style={{ fontSize: ".6rem", color: task.status === "done" ? "#22c55e" : task.status === "skipped" ? "#f59e0b" : "var(--muted,#64748b)" }}>
                    {task.status === "done" ? "✅ Done" : task.status === "skipped" ? "⏭ Skipped" : "⏳ Pending"}
                  </span>
                </div>
                <div style={{ fontWeight: 700, fontSize: ".78rem" }}>{task.topic}</div>
                {task.description && <div style={{ fontSize: ".68rem", color: "var(--muted,#94a3b8)", marginTop: 2, lineHeight: 1.4 }}>{task.description}</div>}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function StudyPlannerPage({ user, setActivePage }) {
  const [selectedExam, setSelectedExam] = useState("jee_main");
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [dailyHours, setDailyHours] = useState(4);
  const [updatingTask, setUpdatingTask] = useState(null);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");
  const [migrating, setMigrating] = useState(false);
  const [migrationDone, setMigrationDone] = useState(false);
  const [activeTab, setActiveTab] = useState("today"); // today | weekly
  const [expandedWeeks, setExpandedWeeks] = useState(new Set([1]));

  const examInfo = EXAMS.find(e => e.value === selectedExam) || EXAMS[0];

  const loadPlan = useCallback(async () => {
    setLoading(true);
    setErr("");
    try {
      const data = await getStudyPlan(user.accessToken, selectedExam);
      setPlan(data);
      if (data.daily_hours) setDailyHours(data.daily_hours);
    } catch (e) {
      setErr(e.message || "Failed to load plan.");
    } finally {
      setLoading(false);
    }
  }, [user.accessToken, selectedExam]);

  useEffect(() => { loadPlan(); }, [loadPlan]);

  async function handleGenerate() {
    if (!window.confirm(
      `Generate a new AI study plan for ${examInfo.label}?\n\n` +
      `This will create a ${plan?.countdown?.weeks_remaining || "30"}-week plan with ${dailyHours}h/day study schedule.\n\n` +
      `⚠️ Any existing plan will be replaced. This may take 30–120 seconds.`
    )) return;
    setGenerating(true);
    setErr("");
    setMsg("");
    try {
      const data = await generateStudyPlan(user.accessToken, { examType: selectedExam, dailyHours });
      setPlan(data);
      setMsg("✅ Study plan generated! Your personalised schedule is ready.");
      setActiveTab("today");
      setExpandedWeeks(new Set([1]));
    } catch (e) {
      setErr(e.message || "Failed to generate plan.");
    } finally {
      setGenerating(false);
    }
  }

  async function handleToggleTask(taskId, status) {
    setUpdatingTask(taskId);
    try {
      await updateTaskStatus(user.accessToken, taskId, status);
      // Optimistic update
      setPlan(prev => {
        if (!prev) return prev;
        const updateTasks = (tasks) =>
          tasks.map(t => t.id === taskId ? { ...t, status } : t);
        return {
          ...prev,
          today_tasks: updateTasks(prev.today_tasks || []),
          today_done: (prev.today_tasks || []).filter(t =>
            t.id === taskId ? status === "done" : t.status === "done"
          ).length,
          weeks: (prev.weeks || []).map(w => ({
            ...w,
            tasks: updateTasks(w.tasks || []),
          })),
        };
      });
    } catch (e) {
      setErr(e.message || "Failed to update task.");
    } finally {
      setUpdatingTask(null);
    }
  }

  async function handleMigrate() {
    setMigrating(true);
    try {
      const result = await migrateStudyPlanner(user.accessToken);
      setMigrationDone(true);
      setMsg(result.message || "Tables ready.");
      await loadPlan();
    } catch (e) {
      setErr(e.message || "Migration failed. Run the SQL manually in Supabase.");
    } finally {
      setMigrating(false);
    }
  }

  const todayTasks = plan?.today_tasks || [];
  const todayDone = todayTasks.filter(t => t.status === "done").length;
  const todayTotal = todayTasks.length;
  const todayPct = todayTotal > 0 ? Math.round(todayDone / todayTotal * 100) : 0;

  return (
    <div className="premium-page">
      {/* ── Header ── */}
      <section className="premium-section" style={{ paddingBottom: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
          <button
            onClick={() => setActivePage && setActivePage("examPrep")}
            style={{ background: "none", border: "1px solid var(--border,#334155)", borderRadius: 7, padding: "5px 12px", cursor: "pointer", fontSize: ".76rem", color: "var(--muted,#64748b)", fontFamily: "inherit" }}
          >
            ← Exam Prep
          </button>
          <span style={{ fontSize: ".82rem", color: "var(--muted,#64748b)" }}>📅 AI Study Planner</span>
        </div>

        <div className="premium-header" style={{ marginBottom: 16 }}>
          <p className="eyebrow">AI-Powered · Adaptive · Phase 1 + 2 + 3</p>
          <h2>📅 Study Planner</h2>
          <p>Personalised day-by-day study schedule based on your exam date, weak topics, and daily hours. Adapts after each practice test.</p>
        </div>

        {/* Exam selector */}
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16 }}>
          {EXAMS.map(exam => (
            <button key={exam.value}
              onClick={() => { setSelectedExam(exam.value); setMsg(""); setErr(""); }}
              style={{
                padding: "7px 14px", borderRadius: 9,
                border: `2px solid ${selectedExam === exam.value ? exam.color : "var(--border,#334155)"}`,
                background: selectedExam === exam.value ? `${exam.color}18` : "var(--panel,#1e293b)",
                color: selectedExam === exam.value ? exam.color : "var(--muted,#94a3b8)",
                fontWeight: 700, fontSize: ".8rem", cursor: "pointer", fontFamily: "inherit",
                display: "flex", alignItems: "center", gap: 6,
              }}>
              <span>{exam.icon}</span><span>{exam.label}</span>
            </button>
          ))}
        </div>
      </section>

      {/* ── First-time Setup Banner ── */}
      {!migrationDone && !plan?.has_plan && !loading && (
        <section className="premium-section" style={{ paddingTop: 0 }}>
          <div style={{ background: "rgba(245,158,11,.06)", border: "1px solid rgba(245,158,11,.25)", borderRadius: 10, padding: "12px 16px", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 10 }}>
            <div>
              <div style={{ fontSize: ".82rem", fontWeight: 700, color: "#fbbf24", marginBottom: 2 }}>⚙️ First-time Setup</div>
              <div style={{ fontSize: ".72rem", color: "var(--muted,#94a3b8)" }}>Run migration to create Study Planner tables, then generate your plan.</div>
            </div>
            <button onClick={handleMigrate} disabled={migrating}
              style={{ padding: "7px 16px", background: migrating ? "#6b7280" : "#f59e0b", border: "none", borderRadius: 7, color: "#fff", fontWeight: 700, fontSize: ".78rem", cursor: "pointer", fontFamily: "inherit" }}>
              {migrating ? "⏳ Setting up…" : "🗄️ Run Setup"}
            </button>
          </div>
        </section>
      )}

      {msg && <section className="premium-section" style={{ paddingTop: 0 }}><div className="info-box">{msg}</div></section>}
      {err && <section className="premium-section" style={{ paddingTop: 0 }}><div className="error-box">{err}</div></section>}

      {loading ? (
        <section className="premium-section" style={{ textAlign: "center", paddingTop: 40 }}>
          <Loader size={20} style={{ animation: "spin 1s linear infinite", color: "var(--muted,#64748b)" }} />
          <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
          <div style={{ marginTop: 10, fontSize: ".8rem", color: "var(--muted,#64748b)" }}>Loading your plan…</div>
        </section>
      ) : (
        <>
          {/* ── Phase 1: Countdown ── */}
          {plan?.countdown && (
            <section className="premium-section" style={{ paddingTop: 0 }}>
              <CountdownTimer
                daysRemaining={plan.countdown.days_remaining}
                weeksRemaining={plan.countdown.weeks_remaining}
                examDate={plan.countdown.exam_date}
                examLabel={plan.countdown.exam_label}
                color={examInfo.color}
              />
            </section>
          )}

          {/* ── No Plan State ── */}
          {!plan?.has_plan && (
            <section className="premium-section" style={{ paddingTop: 0 }}>
              <div style={{ background: "var(--panel,#1e293b)", border: `2px dashed ${examInfo.color}55`, borderRadius: 16, padding: "40px 32px", textAlign: "center", maxWidth: 560, margin: "0 auto" }}>
                <div style={{ fontSize: "3rem", marginBottom: 16 }}>🗓️</div>
                <h3 style={{ fontSize: "1.1rem", fontWeight: 800, marginBottom: 8 }}>No study plan yet</h3>
                <p style={{ color: "var(--muted,#64748b)", fontSize: ".82rem", lineHeight: 1.6, marginBottom: 20 }}>
                  Generate an AI-powered study plan covering all {examInfo.label} chapters.
                  The plan adapts to your weak topics after each practice test.
                </p>

                {/* Weak topics from tests */}
                {plan?.weak_topics?.length > 0 && (
                  <div style={{ marginBottom: 18 }}>
                    <div style={{ fontSize: ".7rem", fontWeight: 700, color: "#f87171", marginBottom: 6 }}>⚠️ Weak topics detected from your tests:</div>
                    <div style={{ display: "flex", gap: 5, flexWrap: "wrap", justifyContent: "center" }}>
                      {plan.weak_topics.map(t => (
                        <span key={t} style={{ fontSize: ".65rem", background: "rgba(239,68,68,.1)", color: "#f87171", padding: "2px 8px", borderRadius: 20 }}>{t}</span>
                      ))}
                    </div>
                    <div style={{ fontSize: ".65rem", color: "var(--muted,#64748b)", marginTop: 6 }}>These will be prioritised in the first few weeks of your plan.</div>
                  </div>
                )}

                {/* Daily hours input */}
                <div style={{ marginBottom: 20 }}>
                  <label style={{ fontSize: ".78rem", fontWeight: 700, color: "var(--muted,#64748b)", display: "block", marginBottom: 6 }}>
                    Daily study hours: <strong style={{ color: examInfo.color }}>{dailyHours}h</strong>
                  </label>
                  <input type="range" min={1} max={10} value={dailyHours} onChange={e => setDailyHours(Number(e.target.value))}
                    style={{ width: "100%", accentColor: examInfo.color }} />
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: ".6rem", color: "var(--muted,#64748b)", marginTop: 2 }}>
                    <span>1h</span><span>5h</span><span>10h</span>
                  </div>
                </div>

                {generating ? (
                  <GeneratingProgress
                    examLabel={examInfo.label}
                    weakTopics={plan?.weak_topics || []}
                    weeksRemaining={plan?.countdown?.weeks_remaining || 30}
                    dailyHours={dailyHours}
                    color={examInfo.color}
                  />
                ) : (
                  <button onClick={handleGenerate}
                    style={{ padding: "13px 32px", background: `linear-gradient(135deg,${examInfo.color},${examInfo.color}cc)`, border: "none", borderRadius: 12, color: "#fff", fontWeight: 800, fontSize: ".9rem", cursor: "pointer", fontFamily: "inherit", display: "flex", alignItems: "center", gap: 10, margin: "0 auto" }}>
                    🚀 Generate My {examInfo.label} Study Plan
                  </button>
                )}
              </div>
            </section>
          )}

          {/* ── Has Plan: Phase 2 + 3 ── */}
          {plan?.has_plan && (
            <>
              {/* Summary bar */}
              <section className="premium-section" style={{ paddingTop: 0 }}>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(130px,1fr))", gap: 10, marginBottom: 16 }}>
                  {[
                    { label: "Overall Progress", value: `${plan.completion_pct ?? 0}%`, color: "#6366f1" },
                    { label: "Tasks Done", value: `${plan.done_tasks ?? 0}/${plan.total_tasks ?? 0}`, color: "#22c55e" },
                    { label: "Today Done", value: `${plan.today_done ?? 0}/${plan.today_total ?? 0}`, color: "#f59e0b" },
                    { label: "Weeks Left", value: plan.countdown?.weeks_remaining ?? "—", color: examInfo.color },
                  ].map(s => (
                    <div key={s.label} style={{ background: "var(--panel,#1e293b)", border: "1px solid var(--border,#334155)", borderRadius: 10, padding: "12px 14px" }}>
                      <div style={{ fontSize: "1.4rem", fontWeight: 900, color: s.color }}>{s.value}</div>
                      <div style={{ fontSize: ".62rem", color: "var(--muted,#64748b)", marginTop: 3 }}>{s.label}</div>
                    </div>
                  ))}
                </div>

                {/* Weak topics */}
                {plan.weak_topics?.length > 0 && (
                  <div style={{ background: "rgba(239,68,68,.05)", border: "1px solid rgba(239,68,68,.2)", borderRadius: 9, padding: "10px 14px", marginBottom: 14 }}>
                    <div style={{ fontSize: ".7rem", fontWeight: 700, color: "#f87171", marginBottom: 6 }}>⚠️ Weak topics (prioritised in plan)</div>
                    <div style={{ display: "flex", gap: 5, flexWrap: "wrap" }}>
                      {plan.weak_topics.map(t => (
                        <span key={t} style={{ fontSize: ".65rem", background: "rgba(239,68,68,.1)", color: "#f87171", padding: "2px 8px", borderRadius: 20 }}>{t}</span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Tabs */}
                <div style={{ display: "flex", gap: 8, marginBottom: 14 }}>
                  {[{ key: "today", label: `📋 Today (${todayTotal})` }, { key: "weekly", label: "📅 Weekly Timeline" }].map(tab => (
                    <button key={tab.key} onClick={() => setActiveTab(tab.key)}
                      style={{ padding: "7px 16px", borderRadius: 8, border: `1px solid ${activeTab === tab.key ? examInfo.color : "var(--border,#334155)"}`, background: activeTab === tab.key ? `${examInfo.color}18` : "var(--panel,#1e293b)", color: activeTab === tab.key ? examInfo.color : "var(--muted,#94a3b8)", fontWeight: 700, fontSize: ".8rem", cursor: "pointer", fontFamily: "inherit" }}>
                      {tab.label}
                    </button>
                  ))}
                  <div style={{ marginLeft: "auto", display: "flex", gap: 8, alignItems: "center" }}>
                    <label style={{ fontSize: ".72rem", color: "var(--muted,#64748b)" }}>
                      Hours/day:
                      <select value={dailyHours} onChange={e => setDailyHours(Number(e.target.value))}
                        style={{ marginLeft: 6, padding: "3px 7px", borderRadius: 6, border: "1px solid var(--border,#334155)", background: "var(--panel,#1e293b)", color: "var(--text,#1e293b)", fontSize: ".75rem", fontFamily: "inherit" }}>
                        {[1,2,3,4,5,6,7,8,9,10].map(h => <option key={h} value={h}>{h}h</option>)}
                      </select>
                    </label>
                    <button onClick={handleGenerate} disabled={generating}
                      style={{ padding: "7px 14px", background: generating ? "var(--border,#334155)" : `linear-gradient(135deg,${examInfo.color},${examInfo.color}cc)`, border: "none", borderRadius: 8, color: "#fff", fontWeight: 700, fontSize: ".75rem", cursor: generating ? "not-allowed" : "pointer", fontFamily: "inherit", display: "flex", alignItems: "center", gap: 6, opacity: generating ? .5 : 1 }}>
                      🔄 Regenerate
                    </button>
                  </div>
                </div>

                {/* ── Regenerating overlay ── */}
                {generating && (
                  <div style={{ marginBottom: 16 }}>
                    <GeneratingProgress
                      examLabel={examInfo.label}
                      weakTopics={plan?.weak_topics || []}
                      weeksRemaining={plan?.countdown?.weeks_remaining || 30}
                      dailyHours={dailyHours}
                      color={examInfo.color}
                    />
                  </div>
                )}

                {/* ── Phase 3: Today's tasks ── */}
                {!generating && activeTab === "today" && (
                  <div>
                    {todayTotal === 0 ? (
                      <div style={{ background: "var(--panel,#1e293b)", border: "1px solid var(--border,#334155)", borderRadius: 10, padding: "32px 20px", textAlign: "center" }}>
                        <div style={{ fontSize: "2rem", marginBottom: 8 }}>🎉</div>
                        <div style={{ fontWeight: 700, marginBottom: 4 }}>No tasks scheduled for today</div>
                        <div style={{ fontSize: ".75rem", color: "var(--muted,#64748b)" }}>
                          Check the Weekly Timeline tab to see what's coming up.
                        </div>
                      </div>
                    ) : (
                      <div>
                        {/* Today progress */}
                        <div style={{ marginBottom: 12 }}>
                          <div style={{ display: "flex", justifyContent: "space-between", fontSize: ".72rem", color: "var(--muted,#64748b)", marginBottom: 4 }}>
                            <span>Today's progress</span>
                            <span style={{ color: todayPct === 100 ? "#22c55e" : "var(--muted,#64748b)", fontWeight: 700 }}>{todayDone}/{todayTotal} tasks ({todayPct}%)</span>
                          </div>
                          <div style={{ background: "var(--border,#334155)", borderRadius: 6, height: 6, overflow: "hidden" }}>
                            <div style={{ width: `${todayPct}%`, height: "100%", background: todayPct === 100 ? "#22c55e" : examInfo.color, borderRadius: 6, transition: "width .4s" }} />
                          </div>
                        </div>
                        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                          {todayTasks.map(task => (
                            <TaskCard
                              key={task.id}
                              task={task}
                              onToggle={handleToggleTask}
                              updating={updatingTask === task.id}
                            />
                          ))}
                        </div>
                        {todayPct === 100 && (
                          <div style={{ marginTop: 14, background: "rgba(34,197,94,.08)", border: "1px solid rgba(34,197,94,.25)", borderRadius: 10, padding: "12px 16px", textAlign: "center" }}>
                            <div style={{ fontSize: "1.5rem", marginBottom: 4 }}>🏆</div>
                            <div style={{ fontWeight: 700, color: "#22c55e", fontSize: ".85rem" }}>All done for today!</div>
                            <div style={{ fontSize: ".72rem", color: "var(--muted,#64748b)", marginTop: 4 }}>Great work. See you tomorrow!</div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}

                {/* ── Phase 2: Weekly timeline ── */}
                {!generating && activeTab === "weekly" && (
                  <div>
                    {(plan.weeks || []).length === 0 ? (
                      <div style={{ textAlign: "center", color: "var(--muted,#64748b)", fontSize: ".8rem", padding: 24 }}>No weekly plan data available.</div>
                    ) : (
                      (plan.weeks || []).map(w => (
                        <WeekAccordion
                          key={w.week}
                          week={w.week}
                          tasks={w.tasks || []}
                          defaultOpen={w.week === 1}
                        />
                      ))
                    )}
                  </div>
                )}

                {/* Plan info */}
                {plan.generated_at && (
                  <div style={{ marginTop: 16, fontSize: ".62rem", color: "var(--muted,#475569)", textAlign: "center" }}>
                    Plan generated {new Date(plan.generated_at).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" })}
                    {" · "}{plan.countdown?.weeks_remaining} weeks remaining
                  </div>
                )}
              </section>
            </>
          )}
        </>
      )}
    </div>
  );
}
