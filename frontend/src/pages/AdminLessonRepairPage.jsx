/**
 * AdminLessonRepairPage.jsx — Admin Lesson Repair Workflow
 *
 * Provides the full repair pipeline UI:
 *  1. Mode selector (sample / filtered / all)
 *  2. LLM toggle with cost warning
 *  3. Run Repair button + Cancel Job
 *  4. Progress bar + step timeline + live counters
 *  5. Task table with filters
 *  6. Task detail drawer with Before / After view
 *  7. Approve / Publish / Reject / Re-run per task
 *
 * Uses existing CSS variables for light/dark mode compatibility.
 * Admin-only — backend enforces require_admin on all endpoints.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import {
  approveRepairTask,
  cancelRepairJob,
  getLatestRepairStatus,
  getRepairJobStatus,
  getRepairLlmInfo,
  getRepairReportUrl,
  getRepairTask,
  getRepairTasks,
  publishRepairTask,
  rerunRepairTask,
  runRepairJob,
} from "../api/lessonRepair";

// ── Status colours ────────────────────────────────────────────────────────────
const STATUS_COLORS = {
  queued:           { bg: "rgba(99,102,241,.1)",  color: "#6366f1" },
  running:          { bg: "rgba(245,158,11,.1)",  color: "#b45309" },
  completed:        { bg: "rgba(34,197,94,.1)",   color: "#166534" },
  failed:           { bg: "rgba(239,68,68,.1)",   color: "#dc2626" },
  cancelled:        { bg: "rgba(148,163,184,.1)", color: "#64748b" },
  ready_for_review: { bg: "rgba(99,102,241,.1)",  color: "#6366f1" },
  validation_failed:{ bg: "rgba(245,158,11,.1)",  color: "#b45309" },
  approved:         { bg: "rgba(34,197,94,.1)",   color: "#166534" },
  published:        { bg: "rgba(16,185,129,.1)",  color: "#065f46" },
  rejected:         { bg: "rgba(239,68,68,.1)",   color: "#dc2626" },
};

const STEP_LABELS = [
  "Reading audit report",
  "Creating repair tasks",
  "Generating drafts",
  "Validating drafts",
  "Re-auditing",
  "Ready for admin review",
];

function StatusPill({ status }) {
  const style = STATUS_COLORS[status] || STATUS_COLORS.queued;
  return (
    <span style={{
      display: "inline-block", padding: "2px 8px", borderRadius: 12,
      fontSize: ".72rem", fontWeight: 700,
      background: style.bg, color: style.color,
    }}>
      {status?.replace(/_/g, " ") || "unknown"}
    </span>
  );
}

function Counter({ label, value, color }) {
  return (
    <div style={{
      background: "var(--panel,#fff)", border: "1px solid var(--border,#e5e7eb)",
      borderRadius: 10, padding: "10px 14px", textAlign: "center", minWidth: 80,
    }}>
      <div style={{ fontSize: "1.4rem", fontWeight: 800, color: color || "var(--text,#1e293b)" }}>
        {value ?? 0}
      </div>
      <div style={{ fontSize: ".72rem", color: "#64748b", marginTop: 2 }}>{label}</div>
    </div>
  );
}

// ── Task Detail Drawer ────────────────────────────────────────────────────────

function TaskDrawer({ taskId, onClose, onApprove, onPublish, onRerun }) {
  const [task, setTask] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionMsg, setActionMsg] = useState(null);
  const [actionError, setActionError] = useState(null);
  const [activeTab, setActiveTab] = useState("issues"); // issues | before | after | validation

  useEffect(() => {
    if (!taskId) return;
    setLoading(true);
    getRepairTask(taskId)
      .then(d => setTask(d?.task || null))
      .catch(() => setTask(null))
      .finally(() => setLoading(false));
  }, [taskId]);

  if (!taskId) return null;

  const handleAction = async (fn, label) => {
    setActionMsg(null); setActionError(null);
    try {
      const r = await fn(taskId);
      setActionMsg(r?.message || `${label} successful.`);
      // Refresh task
      const updated = await getRepairTask(taskId);
      setTask(updated?.task || task);
      if (label === "Approve") onApprove?.();
      if (label === "Publish") onPublish?.();
      if (label === "Re-run") onRerun?.();
    } catch (e) {
      setActionError(e.message || `${label} failed.`);
    }
  };

  const drawerStyle = {
    position: "fixed", top: 0, right: 0, bottom: 0, width: "min(700px,95vw)",
    background: "var(--panel,#fff)", borderLeft: "1px solid var(--border,#e5e7eb)",
    zIndex: 500, overflowY: "auto", padding: "24px",
    boxShadow: "-4px 0 24px rgba(0,0,0,.12)",
  };
  const tabStyle = (active) => ({
    padding: "6px 14px", borderRadius: 8, border: "none",
    background: active ? "#6366f1" : "var(--surface2,#f8fafc)",
    color: active ? "#fff" : "var(--text,#374151)",
    cursor: "pointer", fontFamily: "inherit", fontWeight: 600, fontSize: ".8rem",
  });

  return (
    <div style={drawerStyle} data-testid="task-drawer">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
        <div>
          <h3 style={{ margin: 0, fontSize: ".95rem", fontWeight: 800 }}>Task Detail</h3>
          {task && (
            <p style={{ margin: "4px 0 0", fontSize: ".78rem", color: "#64748b" }}>
              {task.grade} · {task.subject} · {task.chapter}
            </p>
          )}
        </div>
        <button onClick={onClose} style={{
          background: "none", border: "none", cursor: "pointer", fontSize: "1.2rem",
          color: "#64748b", padding: "4px 8px",
        }}>✕</button>
      </div>

      {loading && <p style={{ color: "#94a3b8" }}>Loading task…</p>}
      {!loading && !task && <p style={{ color: "#dc2626" }}>Task not found.</p>}

      {task && (
        <>
          <div style={{ display: "flex", gap: 8, marginBottom: 12, alignItems: "center" }}>
            <StatusPill status={task.status} />
            <span style={{ fontSize: ".78rem", color: "#64748b" }}>
              Before: <strong>{task.audit_before_score ?? "N/A"}</strong>/100
              {task.audit_after_score != null && (
                <> → After: <strong style={{ color: "#166534" }}>{task.audit_after_score}/100</strong></>
              )}
            </span>
          </div>

          <p style={{ fontSize: ".82rem", fontWeight: 700, color: "#475569", marginBottom: 6 }}>
            {task.step_title}
          </p>

          {/* Action buttons */}
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 12 }}>
            {task.status === "ready_for_review" && (
              <button
                data-testid="btn-approve"
                onClick={() => handleAction(approveRepairTask, "Approve")}
                style={{
                  padding: "7px 16px", borderRadius: 8, border: "none",
                  background: "#22c55e", color: "#fff", cursor: "pointer",
                  fontFamily: "inherit", fontWeight: 700, fontSize: ".8rem",
                }}
              >
                ✓ Approve Draft
              </button>
            )}
            {task.status === "approved" && (
              <button
                data-testid="btn-publish"
                onClick={() => handleAction(publishRepairTask, "Publish")}
                style={{
                  padding: "7px 16px", borderRadius: 8, border: "none",
                  background: "#6366f1", color: "#fff", cursor: "pointer",
                  fontFamily: "inherit", fontWeight: 700, fontSize: ".8rem",
                }}
              >
                🚀 Publish Approved
              </button>
            )}
            {["failed", "validation_failed"].includes(task.status) && (
              <button
                data-testid="btn-rerun"
                onClick={() => handleAction(rerunRepairTask, "Re-run")}
                style={{
                  padding: "7px 16px", borderRadius: 8, border: "none",
                  background: "#f59e0b", color: "#fff", cursor: "pointer",
                  fontFamily: "inherit", fontWeight: 700, fontSize: ".8rem",
                }}
              >
                ↺ Re-run Repair
              </button>
            )}
          </div>

          {actionMsg && (
            <div style={{
              padding: "8px 12px", borderRadius: 8, marginBottom: 10,
              background: "rgba(34,197,94,.1)", border: "1px solid rgba(34,197,94,.3)",
              fontSize: ".8rem", color: "#166534",
            }}>{actionMsg}</div>
          )}
          {actionError && (
            <div style={{
              padding: "8px 12px", borderRadius: 8, marginBottom: 10,
              background: "rgba(239,68,68,.1)", border: "1px solid rgba(239,68,68,.3)",
              fontSize: ".8rem", color: "#dc2626",
            }}>{actionError}</div>
          )}

          {/* Tabs */}
          <div style={{ display: "flex", gap: 6, marginBottom: 12, flexWrap: "wrap" }}>
            {["issues", "before", "after", "validation"].map(tab => (
              <button key={tab} onClick={() => setActiveTab(tab)} style={tabStyle(activeTab === tab)}>
                {tab === "issues" ? "Issues" : tab === "before" ? "Original" : tab === "after" ? "Repaired" : "Validation"}
              </button>
            ))}
          </div>

          {/* Tab content */}
          <div style={{
            background: "var(--surface2,#f8fafc)", borderRadius: 8,
            padding: "12px 14px", fontSize: ".8rem", overflowX: "auto",
            maxHeight: 480, overflowY: "auto",
          }}>
            {activeTab === "issues" && (
              <div data-testid="tab-issues">
                {(task.issues_json || []).length === 0
                  ? <p style={{ color: "#94a3b8" }}>No issues recorded.</p>
                  : (task.issues_json || []).map((issue, i) => (
                    <div key={i} style={{
                      marginBottom: 8, padding: "6px 10px", borderRadius: 6,
                      background: issue.severity === "critical"
                        ? "rgba(239,68,68,.08)" : "rgba(245,158,11,.08)",
                      borderLeft: `3px solid ${issue.severity === "critical" ? "#dc2626" : "#b45309"}`,
                    }}>
                      <strong style={{ fontSize: ".72rem", textTransform: "uppercase", color: issue.severity === "critical" ? "#dc2626" : "#b45309" }}>
                        [{issue.severity}]
                      </strong>{" "}
                      <strong>{issue.section}</strong>: {issue.issue}
                    </div>
                  ))
                }
              </div>
            )}
            {activeTab === "before" && (
              <pre data-testid="tab-before" style={{ whiteSpace: "pre-wrap", wordBreak: "break-word", margin: 0, fontSize: ".75rem" }}>
                {task.original_content_json?.lesson_content
                  ? task.original_content_json.lesson_content
                  : "(No original content stored)"}
              </pre>
            )}
            {activeTab === "after" && (
              <div data-testid="tab-after">
                {task.repaired_content_json
                  ? <pre style={{ whiteSpace: "pre-wrap", wordBreak: "break-word", margin: 0, fontSize: ".75rem" }}>
                      {JSON.stringify(task.repaired_content_json.sections || task.repaired_content_json, null, 2)}
                    </pre>
                  : <p style={{ color: "#94a3b8" }}>No repaired content yet. Run LLM repair first.</p>
                }
              </div>
            )}
            {activeTab === "validation" && (
              <div data-testid="tab-validation">
                {task.validation_result_json
                  ? <>
                      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 10 }}>
                        <span>Overall: <strong>{task.validation_result_json.overall_score ?? "N/A"}/100</strong></span>
                        <span>Depth: <strong>{task.validation_result_json.depth_score ?? "N/A"}/100</strong></span>
                        <span>Compliance: <strong>{task.validation_result_json.section_compliance ?? "N/A"}%</strong></span>
                        <span>Valid: <strong style={{ color: task.validation_result_json.valid ? "#166534" : "#dc2626" }}>
                          {task.validation_result_json.valid ? "YES ✓" : "NO ✗"}
                        </strong></span>
                      </div>
                      {(task.validation_result_json.issues || []).map((issue, i) => (
                        <div key={i} style={{ fontSize: ".75rem", marginBottom: 4 }}>
                          [{issue.severity}] <strong>{issue.section}</strong>: {issue.issue}
                        </div>
                      ))}
                    </>
                  : <p style={{ color: "#94a3b8" }}>No validation result yet.</p>
                }
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function AdminLessonRepairPage({ user }) { // eslint-disable-line no-unused-vars
  const [auditMeta, setAuditMeta] = useState(null);
  const [currentJob, setCurrentJob] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [runError, setRunError] = useState(null);
  const [runLoading, setRunLoading] = useState(false);
  const [selectedTaskId, setSelectedTaskId] = useState(null);

  // LLM info state
  const [llmInfo, setLlmInfo] = useState(null);
  const [llmInfoLoading, setLlmInfoLoading] = useState(false);
  const [showApiKeyInput, setShowApiKeyInput] = useState(false);
  const [overrideApiKey, setOverrideApiKey] = useState("");
  const [showApiKey, setShowApiKey] = useState(false);

  // Form state
  const [mode, setMode] = useState("sample");
  const [grade, setGrade] = useState("");
  const [subject, setSubject] = useState("");
  const [chapter, setChapter] = useState("");
  const [useLlm, setUseLlm] = useState(false);

  // Task table filters
  const [filterStatus, setFilterStatus] = useState("");
  const [filterGrade, setFilterGrade] = useState("");

  const pollRef = useRef(null);

  const loadLatest = useCallback(async () => {
    try {
      const d = await getLatestRepairStatus();
      setAuditMeta(d?.audit_report_meta || null);
      if (d?.latest_job) setCurrentJob(d.latest_job);
    } catch { /* non-critical */ }
    finally { setLoading(false); }
  }, []);

  const loadLlmInfo = useCallback(async () => {
    setLlmInfoLoading(true);
    try {
      const d = await getRepairLlmInfo();
      setLlmInfo(d || null);
    } catch { /* non-critical */ }
    finally { setLlmInfoLoading(false); }
  }, []);

  const loadTasks = useCallback(async (jobId) => {
    if (!jobId) return;
    try {
      const d = await getRepairTasks(jobId, {
        status: filterStatus || undefined,
        grade: filterGrade || undefined,
        limit: 200,
      });
      setTasks(d?.tasks || []);
    } catch { /* non-critical */ }
  }, [filterStatus, filterGrade]);

  useEffect(() => { loadLatest(); loadLlmInfo(); }, [loadLatest, loadLlmInfo]); // eslint-disable-line react-hooks/exhaustive-deps

  // Poll while job is running
  useEffect(() => {
    const jobId = currentJob?.id;
    const jobStatus = currentJob?.status;
    if (!jobId || !["queued", "running"].includes(jobStatus)) {
      clearInterval(pollRef.current);
      if (jobId) loadTasks(jobId);
      return;
    }
    clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const d = await getRepairJobStatus(jobId);
        if (d?.job) {
          setCurrentJob(d.job);
          if (!["queued", "running"].includes(d.job.status)) {
            clearInterval(pollRef.current);
            loadTasks(jobId);
          }
        }
      } catch { /* ignore */ }
    }, 2500);
    return () => clearInterval(pollRef.current);
  }, [currentJob?.id, currentJob?.status, loadTasks]);

  useEffect(() => {
    if (currentJob?.id) loadTasks(currentJob.id);
  }, [currentJob?.id, loadTasks]);

  async function handleRun() {
    setRunError(null);
    setRunLoading(true);
    try {
      const d = await runRepairJob({
        mode,
        grade: grade || null,
        subject: subject || null,
        chapter: chapter || null,
        use_llm: useLlm,
        override_api_key: (useLlm && overrideApiKey.trim()) ? overrideApiKey.trim() : null,
      });
      if (d?.job_id) {
        setCurrentJob({ id: d.job_id, status: "queued", mode, total_tasks: 0, completed_tasks: 0, failed_tasks: 0, approved_tasks: 0, published_tasks: 0 });
        setTasks([]);
      }
    } catch (e) {
      setRunError(e.message || "Failed to start repair job.");
    } finally {
      setRunLoading(false);
    }
  }

  async function handleCancel() {
    if (!currentJob?.id) return;
    try { await cancelRepairJob(currentJob.id); loadLatest(); }
    catch (e) { setRunError(e.message || "Failed to cancel job."); }
  }

  const isRunning = ["queued", "running"].includes(currentJob?.status);
  const pct = currentJob?.total_tasks > 0
    ? Math.round((currentJob.completed_tasks + currentJob.failed_tasks) / currentJob.total_tasks * 100)
    : 0;

  // Step timeline heuristic
  const step = currentJob
    ? currentJob.status === "queued" ? 0
    : currentJob.status === "running" && currentJob.total_tasks === 0 ? 1
    : currentJob.status === "running" && currentJob.total_tasks > 0 && currentJob.completed_tasks === 0 ? 2
    : currentJob.status === "running" ? 3
    : currentJob.status === "completed" ? 5 : 4
    : -1;

  const btn = {
    padding: "9px 20px", borderRadius: 8, border: "none", fontFamily: "inherit",
    fontWeight: 700, fontSize: ".85rem", cursor: "pointer",
  };
  const inp = {
    background: "var(--surface2,#f8fafc)", border: "1px solid var(--border,#e5e7eb)",
    borderRadius: 8, padding: "7px 10px", fontFamily: "inherit", fontSize: ".82rem",
    color: "var(--text,#374151)", width: "100%",
  };

  return (
    <div data-testid="admin-lesson-repair-page" style={{ maxWidth: 1100, margin: "0 auto", padding: "0 14px 60px", fontFamily: "inherit" }}>

      {/* Header */}
      <div style={{ marginBottom: 20 }}>
        <h2 style={{ margin: "0 0 4px", fontSize: "1.05rem", fontWeight: 800 }}>🔧 Lesson Repair</h2>
        <p style={{ margin: 0, fontSize: ".82rem", color: "#64748b" }}>
          Repair lessons that failed the 8-section audit. LLM repair is opt-in only.
        </p>
        {auditMeta && (
          <div style={{ marginTop: 8, fontSize: ".78rem", color: "#64748b" }}>
            Last audit: {auditMeta.audited_at?.slice(0, 10)} ·{" "}
            {auditMeta.lessons_audited} lessons ·{" "}
            <span style={{ color: auditMeta.critical_issues > 0 ? "#dc2626" : "#166534", fontWeight: 700 }}>
              {auditMeta.critical_issues} critical issues
            </span> ·
            Avg score: {auditMeta.avg_overall_score}/100 ·{" "}
            <span style={{ fontWeight: 700, color: auditMeta.overall === "CRITICAL" ? "#dc2626" : "#166534" }}>
              {auditMeta.overall}
            </span>
          </div>
        )}
      </div>

      {/* Config panel */}
      <div style={{
        background: "var(--panel,#fff)", border: "1px solid var(--border,#e5e7eb)",
        borderRadius: 14, padding: "16px 18px", marginBottom: 20,
      }}>
        <h4 style={{ margin: "0 0 12px", fontSize: ".88rem", fontWeight: 700 }}>Repair Configuration</h4>

        {/* Mode selector */}
        <div style={{ marginBottom: 12 }}>
          <label style={{ fontSize: ".78rem", fontWeight: 600, display: "block", marginBottom: 6 }}>Mode</label>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {[["sample", "Sample (10 failures)"], ["filtered", "Filtered"], ["all", "All failures"]].map(([v, label]) => (
              <button key={v} data-testid={`mode-${v}`}
                onClick={() => setMode(v)}
                style={{
                  ...btn, padding: "7px 14px",
                  background: mode === v ? "#6366f1" : "var(--surface2,#f8fafc)",
                  color: mode === v ? "#fff" : "var(--text,#374151)",
                  border: `1px solid ${mode === v ? "#6366f1" : "var(--border,#e5e7eb)"}`,
                }}
              >{label}</button>
            ))}
          </div>
        </div>

        {/* Filters (only when mode=filtered) */}
        {mode === "filtered" && (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(160px,1fr))", gap: 10, marginBottom: 12 }}>
            <div>
              <label style={{ fontSize: ".75rem", fontWeight: 600, display: "block", marginBottom: 4 }}>Grade</label>
              <select value={grade} onChange={e => setGrade(e.target.value)} style={inp}>
                <option value="">Any</option>
                {["Grade 5","Grade 6","Grade 7","Grade 8","Grade 9","Grade 10"].map(g => <option key={g}>{g}</option>)}
              </select>
            </div>
            <div>
              <label style={{ fontSize: ".75rem", fontWeight: 600, display: "block", marginBottom: 4 }}>Subject</label>
              <input value={subject} onChange={e => setSubject(e.target.value)} placeholder="e.g. Science" style={inp} />
            </div>
            <div>
              <label style={{ fontSize: ".75rem", fontWeight: 600, display: "block", marginBottom: 4 }}>Chapter</label>
              <input value={chapter} onChange={e => setChapter(e.target.value)} placeholder="Chapter name" style={inp} />
            </div>
          </div>
        )}

        {/* LLM Info Panel */}
        <div style={{
          marginBottom: 14, padding: "12px 14px", borderRadius: 10,
          background: "var(--surface2,#f8fafc)", border: "1px solid var(--border,#e5e7eb)",
        }} data-testid="llm-info-panel">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
            <span style={{ fontSize: ".8rem", fontWeight: 700, color: "var(--text,#374151)" }}>🤖 AI Provider</span>
            <button onClick={loadLlmInfo} disabled={llmInfoLoading}
              style={{ fontSize: ".72rem", background: "none", border: "none", color: "#6366f1", cursor: "pointer", fontFamily: "inherit", fontWeight: 600 }}>
              {llmInfoLoading ? "…" : "↺ Refresh"}
            </button>
          </div>
          {llmInfo ? (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, fontSize: ".78rem" }}>
              <div>
                <div style={{ color: "#64748b", marginBottom: 2 }}>Provider</div>
                <div style={{ fontWeight: 700, color: "var(--text,#1e293b)" }}>{llmInfo.provider_name}</div>
              </div>
              <div>
                <div style={{ color: "#64748b", marginBottom: 2 }}>Model</div>
                <div style={{ fontWeight: 700, color: "var(--text,#1e293b)" }}>{llmInfo.model_label}</div>
              </div>
              <div>
                <div style={{ color: "#64748b", marginBottom: 2 }}>API Key</div>
                <div style={{
                  fontWeight: 700,
                  color: llmInfo.api_key_configured ? "#166534" : "#dc2626",
                }}>
                  {llmInfo.api_key_configured ? "✓ Configured" : "✗ Not set"}
                </div>
              </div>
              <div>
                <div style={{ color: "#64748b", marginBottom: 2 }}>Free Tier</div>
                <div style={{ fontWeight: 700, color: llmInfo.free_tier_available ? "#166534" : "#64748b" }}>
                  {llmInfo.free_tier_available ? "✓ Available" : "Paid only"}
                </div>
              </div>
            </div>
          ) : (
            <div style={{ fontSize: ".78rem", color: "#94a3b8" }}>
              {llmInfoLoading ? "Loading provider info…" : "Could not load provider info."}
            </div>
          )}
        </div>

        {/* LLM toggle + cost estimate */}
        <div style={{ marginBottom: 14 }}>
          <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
            <input type="checkbox" checked={useLlm} onChange={e => setUseLlm(e.target.checked)} data-testid="llm-toggle" />
            <span style={{ fontSize: ".82rem", fontWeight: 600 }}>Enable LLM Repair</span>
          </label>
          {useLlm && (
            <div data-testid="llm-warning" style={{
              marginTop: 8, borderRadius: 8,
              background: "rgba(245,158,11,.07)", border: "1px solid rgba(245,158,11,.3)",
              fontSize: ".78rem", color: "#78350f", overflow: "hidden",
            }}>
              {/* Cost estimate */}
              {llmInfo && (
                <div style={{ padding: "10px 12px", borderBottom: "1px solid rgba(245,158,11,.2)" }}>
                  <div style={{ fontWeight: 700, marginBottom: 6 }}>
                    ⚠️ Indicative Cost — {llmInfo.provider_name} / {llmInfo.model_label}
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(120px,1fr))", gap: 6 }}>
                    {[
                      { label: "Per lesson", value: llmInfo.cost_per_lesson_usd },
                      { label: "10 lessons", value: llmInfo.cost_10_lessons_usd },
                      { label: "50 lessons", value: llmInfo.cost_50_lessons_usd },
                      { label: "100 lessons", value: llmInfo.cost_100_lessons_usd },
                    ].map(({ label, value }) => (
                      <div key={label} style={{
                        background: "rgba(245,158,11,.12)", borderRadius: 6, padding: "5px 8px", textAlign: "center",
                      }}>
                        <div style={{ fontSize: ".65rem", color: "#92400e", marginBottom: 2 }}>{label}</div>
                        <div style={{ fontWeight: 800, fontSize: ".85rem", color: "#78350f" }}>
                          {value === 0 ? "$0" : value < 0.001 ? `$${(value * 1000).toFixed(2)}m` : `$${value.toFixed(4)}`}
                        </div>
                      </div>
                    ))}
                  </div>
                  {llmInfo.free_tier_available && (
                    <div style={{ marginTop: 6, fontSize: ".72rem", color: "#166534", background: "rgba(34,197,94,.08)", borderRadius: 4, padding: "3px 8px", display: "inline-block" }}>
                      ✓ Free tier available — may be $0 within quota
                    </div>
                  )}
                  <div style={{ marginTop: 4, fontSize: ".68rem", color: "#92400e" }}>
                    Estimates based on ~{llmInfo.token_estimates?.input_tokens_per_lesson || 1600} input + ~{llmInfo.token_estimates?.output_tokens_per_lesson || 2500} output tokens per lesson.
                  </div>
                </div>
              )}

              {/* API key override */}
              <div style={{ padding: "10px 12px" }}>
                <div style={{ marginBottom: 6, fontWeight: 600 }}>
                  Admin approval required before publishing.
                </div>
                <button
                  onClick={() => setShowApiKeyInput(p => !p)}
                  style={{
                    fontSize: ".72rem", background: "none", border: "1px solid rgba(245,158,11,.4)",
                    borderRadius: 6, padding: "3px 10px", cursor: "pointer",
                    fontFamily: "inherit", color: "#78350f", fontWeight: 600,
                  }}
                >
                  {showApiKeyInput ? "▲ Hide API Key Override" : "🔑 Use a different API key for this session"}
                </button>
                {showApiKeyInput && (
                  <div style={{ marginTop: 8 }}>
                    <div style={{ fontSize: ".72rem", color: "#92400e", marginBottom: 4 }}>
                      Optional: Enter a session-only API key. It is used for this repair job only and is never stored or logged.
                    </div>
                    <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                      <input
                        type={showApiKey ? "text" : "password"}
                        value={overrideApiKey}
                        onChange={e => setOverrideApiKey(e.target.value)}
                        placeholder={`${llmInfo?.provider_name || "Provider"} API key (e.g. sk-... / gsk_...)`}
                        data-testid="override-api-key-input"
                        style={{
                          flex: 1, background: "rgba(255,255,255,.6)", border: "1px solid rgba(245,158,11,.4)",
                          borderRadius: 6, padding: "6px 10px", fontFamily: "inherit", fontSize: ".78rem",
                          color: "#1e293b",
                        }}
                      />
                      <button
                        type="button"
                        onClick={() => setShowApiKey(p => !p)}
                        style={{
                          background: "none", border: "none", cursor: "pointer",
                          fontSize: ".82rem", color: "#78350f", padding: "4px",
                        }}
                      >
                        {showApiKey ? "🙈" : "👁️"}
                      </button>
                    </div>
                    {overrideApiKey && (
                      <div style={{ marginTop: 4, fontSize: ".68rem", color: "#166534" }}>
                        ✓ Session key entered — will be used for this repair job only.
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Run / Cancel buttons */}
        <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
          <button
            data-testid="btn-run-repair"
            onClick={handleRun}
            disabled={isRunning || runLoading}
            style={{ ...btn, background: isRunning || runLoading ? "#94a3b8" : "#6366f1", color: "#fff" }}
          >
            {runLoading ? "Starting…" : isRunning ? "Running…" : "▶ Run Repair"}
          </button>
          {isRunning && (
            <button
              data-testid="btn-cancel"
              onClick={handleCancel}
              style={{ ...btn, background: "rgba(239,68,68,.1)", color: "#dc2626", border: "1px solid rgba(239,68,68,.3)" }}
            >
              ✕ Cancel Job
            </button>
          )}
          {currentJob?.id && (
            <a
              href={getRepairReportUrl(currentJob.id, "csv")}
              target="_blank" rel="noreferrer"
              style={{ fontSize: ".78rem", color: "#6366f1", textDecoration: "none" }}
            >
              ↓ Download CSV
            </a>
          )}
        </div>
        {runError && <p style={{ fontSize: ".8rem", color: "#dc2626", marginTop: 8 }}>{runError}</p>}
      </div>

      {/* Progress section */}
      {currentJob && (
        <div style={{
          background: "var(--panel,#fff)", border: "1px solid var(--border,#e5e7eb)",
          borderRadius: 14, padding: "16px 18px", marginBottom: 20,
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <h4 style={{ margin: 0, fontSize: ".88rem", fontWeight: 700 }}>Job Progress</h4>
            <StatusPill status={currentJob.status} />
          </div>

          {/* Progress bar */}
          <div style={{ background: "var(--border,#e5e7eb)", borderRadius: 8, height: 10, marginBottom: 14, overflow: "hidden" }}
               data-testid="progress-bar">
            <div style={{
              width: `${pct}%`, height: "100%",
              background: "linear-gradient(90deg,#6366f1,#8b5cf6)",
              transition: "width .5s ease",
              borderRadius: 8,
            }} />
          </div>

          {/* Step timeline */}
          <div data-testid="step-timeline" style={{ display: "flex", gap: 4, marginBottom: 16, overflowX: "auto" }}>
            {STEP_LABELS.map((label, i) => (
              <div key={i} style={{
                flex: 1, minWidth: 70, padding: "6px 8px", borderRadius: 6, textAlign: "center",
                background: i <= step ? "rgba(99,102,241,.12)" : "var(--surface2,#f8fafc)",
                border: `1px solid ${i <= step ? "#6366f1" : "var(--border,#e5e7eb)"}`,
                fontSize: ".68rem", color: i <= step ? "#6366f1" : "#94a3b8",
                fontWeight: i === step ? 800 : 400,
              }}>
                {i < step ? "✓ " : i === step ? "⟳ " : ""}{label}
              </div>
            ))}
          </div>

          {/* Counters */}
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            <Counter label="Total" value={currentJob.total_tasks} />
            <Counter label="Completed" value={currentJob.completed_tasks} color="#166534" />
            <Counter label="Failed" value={currentJob.failed_tasks} color="#dc2626" />
            <Counter label="Ready" value={tasks.filter(t => t.status === "ready_for_review").length} color="#6366f1" />
            <Counter label="Approved" value={currentJob.approved_tasks} color="#059669" />
            <Counter label="Published" value={currentJob.published_tasks} color="#0891b2" />
            <Counter label="Val. Failed" value={tasks.filter(t => t.status === "validation_failed").length} color="#b45309" />
          </div>
        </div>
      )}

      {/* Task table */}
      {tasks.length > 0 && (
        <div style={{
          background: "var(--panel,#fff)", border: "1px solid var(--border,#e5e7eb)",
          borderRadius: 14, padding: "16px 18px", marginBottom: 20,
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12, flexWrap: "wrap", gap: 8 }}>
            <h4 style={{ margin: 0, fontSize: ".88rem", fontWeight: 700 }}>Repair Tasks ({tasks.length})</h4>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)} style={{ ...inp, width: "auto" }}>
                <option value="">All statuses</option>
                {["queued","running","ready_for_review","validation_failed","approved","published","failed","rejected"].map(s => (
                  <option key={s} value={s}>{s.replace(/_/g," ")}</option>
                ))}
              </select>
              <select value={filterGrade} onChange={e => setFilterGrade(e.target.value)} style={{ ...inp, width: "auto" }}>
                <option value="">All grades</option>
                {["Grade 5","Grade 6","Grade 7","Grade 8","Grade 9","Grade 10"].map(g => <option key={g}>{g}</option>)}
              </select>
            </div>
          </div>

          <div data-testid="task-table" style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: ".78rem" }}>
              <thead>
                <tr style={{ color: "#64748b", borderBottom: "1px solid var(--border,#e5e7eb)" }}>
                  <th style={{ textAlign: "left", padding: "6px 8px" }}>Grade</th>
                  <th style={{ textAlign: "left", padding: "6px 8px" }}>Subject</th>
                  <th style={{ textAlign: "left", padding: "6px 8px" }}>Chapter / Step</th>
                  <th style={{ textAlign: "center", padding: "6px 8px" }}>Before</th>
                  <th style={{ textAlign: "center", padding: "6px 8px" }}>After</th>
                  <th style={{ textAlign: "left", padding: "6px 8px" }}>Status</th>
                  <th style={{ textAlign: "center", padding: "6px 8px" }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {tasks
                  .filter(t => !filterStatus || t.status === filterStatus)
                  .filter(t => !filterGrade || t.grade === filterGrade)
                  .map(t => (
                  <tr key={t.id} style={{ borderBottom: "1px solid var(--border,#f1f5f9)" }}>
                    <td style={{ padding: "6px 8px" }}>{t.grade}</td>
                    <td style={{ padding: "6px 8px" }}>{t.subject}</td>
                    <td style={{ padding: "6px 8px" }}>
                      <div style={{ fontWeight: 600 }}>{t.step_title}</div>
                      <div style={{ fontSize: ".7rem", color: "#94a3b8" }}>{t.chapter}</div>
                    </td>
                    <td style={{ padding: "6px 8px", textAlign: "center" }}>{t.audit_before_score ?? "—"}</td>
                    <td style={{ padding: "6px 8px", textAlign: "center", color: t.audit_after_score != null ? "#166534" : "#94a3b8" }}>
                      {t.audit_after_score ?? "—"}
                    </td>
                    <td style={{ padding: "6px 8px" }}><StatusPill status={t.status} /></td>
                    <td style={{ padding: "6px 8px", textAlign: "center" }}>
                      <button
                        onClick={() => setSelectedTaskId(t.id)}
                        style={{
                          padding: "3px 10px", borderRadius: 6, border: "1px solid var(--border,#e5e7eb)",
                          background: "var(--surface2,#f8fafc)", cursor: "pointer",
                          fontSize: ".72rem", fontWeight: 600, fontFamily: "inherit",
                          color: "var(--text,#374151)",
                        }}
                      >
                        View
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {!loading && !currentJob && (
        <div style={{
          padding: "32px 24px", textAlign: "center", color: "#94a3b8", fontSize: ".88rem",
          background: "var(--panel,#fff)", border: "1px solid var(--border,#e5e7eb)", borderRadius: 14,
        }}>
          No repair jobs yet. Run the lesson sections audit first, then click <strong>Run Repair</strong>.
        </div>
      )}

      {/* Task detail drawer */}
      {selectedTaskId && (
        <TaskDrawer
          taskId={selectedTaskId}
          onClose={() => setSelectedTaskId(null)}
          onApprove={() => currentJob?.id && loadTasks(currentJob.id)}
          onPublish={() => currentJob?.id && loadTasks(currentJob.id)}
          onRerun={() => currentJob?.id && loadTasks(currentJob.id)}
        />
      )}
    </div>
  );
}
