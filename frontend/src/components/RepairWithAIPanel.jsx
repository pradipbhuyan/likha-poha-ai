/**
 * RepairWithAIPanel.jsx — Repair with AI workflow for Lesson Lab
 * ─────────────────────────────────────────────────────────────────────────────
 * Provides single-step AI repair with before/after comparison, validation
 * checklist, impact scores, and safe approve/publish workflow.
 *
 * Safety guarantees:
 * - LLM never runs automatically (user must click Generate Repair)
 * - Publish requires explicit admin confirmation modal
 * - Validation failure disables Approve & Publish
 * - Original content preserved in DB for rollback
 * ─────────────────────────────────────────────────────────────────────────────
 */
import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { repairStepApprove, repairStepPreview, repairStepPublish } from "../api/lessonLab";

// ── Helpers ───────────────────────────────────────────────────────────────────

const card = (extra = {}) => ({
  background: "var(--panel,#fff)", border: "1px solid var(--border,#e5e7eb)",
  borderRadius: 12, padding: "14px 16px", ...extra,
});

function ScoreDelta({ label, before, after, color = "#6366f1" }) {
  const delta = (after ?? 0) - (before ?? 0);
  const deltaColor = delta > 0 ? "#22c55e" : delta < 0 ? "#ef4444" : "#94a3b8";
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6, fontSize: ".82rem" }}>
      <span style={{ color: "#64748b" }}>{label}</span>
      <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <span style={{ color: "#94a3b8" }}>{before ?? "—"}</span>
        <span style={{ color: "#94a3b8", fontSize: ".7rem" }}>→</span>
        <span style={{ fontWeight: 700, color }}>{after ?? "—"}</span>
        {delta !== 0 && (
          <span style={{ fontSize: ".68rem", fontWeight: 800, color: deltaColor }}>
            {delta > 0 ? "+" : ""}{delta}
          </span>
        )}
      </span>
    </div>
  );
}

function ValidationCheck({ label, pass }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6, fontSize: ".82rem" }}>
      <span style={{
        width: 18, height: 18, borderRadius: "50%", flexShrink: 0,
        display: "flex", alignItems: "center", justifyContent: "center",
        background: pass ? "rgba(34,197,94,.15)" : "rgba(239,68,68,.15)",
        color: pass ? "#22c55e" : "#ef4444", fontSize: ".7rem", fontWeight: 800,
      }}>
        {pass ? "✓" : "✗"}
      </span>
      <span style={{ color: pass ? "var(--text,#374151)" : "#ef4444" }}>{label}</span>
    </div>
  );
}

function ConfirmPublishModal({ open, stepTitle, onConfirm, onCancel, publishing }) {
  if (!open) return null;
  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.5)", zIndex: 1000, display: "flex", alignItems: "center", justifyContent: "center", padding: 16 }}>
      <div style={{ ...card(), maxWidth: 440, width: "100%", boxShadow: "0 8px 32px rgba(0,0,0,.2)" }}>
        <h3 style={{ margin: "0 0 8px", fontSize: ".95rem", fontWeight: 800 }}>Confirm Publish</h3>
        <p style={{ margin: "0 0 14px", fontSize: ".85rem", color: "#64748b", lineHeight: 1.6 }}>
          This will publish the repaired <strong>{stepTitle}</strong> to lesson_cache.
          Original content will be preserved for rollback.
        </p>
        <div style={{ padding: "10px 14px", background: "rgba(34,197,94,.07)", border: "1px solid rgba(34,197,94,.2)", borderRadius: 8, marginBottom: 16, fontSize: ".78rem", color: "#166534" }}>
          ✓ Validation passed · Original preserved · Audit log written
        </div>
        <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
          <button onClick={onCancel} disabled={publishing}
            style={{ padding: "7px 16px", borderRadius: 8, border: "1px solid var(--border,#e5e7eb)", background: "var(--surface2,#f8fafc)", cursor: "pointer", fontFamily: "inherit", fontWeight: 600 }}>
            Cancel
          </button>
          <button data-testid="confirm-publish-btn" onClick={onConfirm} disabled={publishing}
            style={{ padding: "7px 16px", borderRadius: 8, border: "none", background: "#6366f1", color: "#fff", cursor: "pointer", fontFamily: "inherit", fontWeight: 700 }}>
            {publishing ? "Publishing…" : "Publish Repaired Step"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────

export default function RepairWithAIPanel({
  step,                 // current step object from lesson detail
  lessonDetail,         // full lesson detail (for context)
  onPublishSuccess,     // callback after successful publish
}) {
  const [repairResult, setRepairResult]     = useState(null);
  const [generating, setGenerating]         = useState(false);
  const [approving, setApproving]           = useState(false);
  const [publishing, setPublishing]         = useState(false);
  const [confirmOpen, setConfirmOpen]       = useState(false);
  const [viewMode, setViewMode]             = useState("side-by-side"); // side-by-side | diff | raw
  const [useLlm, setUseLlm]                 = useState(true);
  const [overrideKey, setOverrideKey]       = useState("");
  const [showKeyInput, setShowKeyInput]     = useState(false);
  const [taskId, setTaskId]                 = useState(null);
  const [taskStatus, setTaskStatus]         = useState(null); // ready_for_review | approved | published | validation_failed
  const [error, setError]                   = useState("");
  const [successMsg, setSuccessMsg]         = useState("");

  if (!step) {
    return (
      <div style={{ padding: 32, textAlign: "center", color: "#94a3b8" }}>
        Select a step from the sidebar to repair it.
      </div>
    );
  }

  const allStepContents = (lessonDetail?.steps || []).map(s => s.raw_content || "");
  const stepIdx = step.step_number - 1;
  const prevContent = stepIdx > 0 ? (allStepContents[stepIdx - 1] || "") : "";
  const nextContent = stepIdx < allStepContents.length - 1 ? (allStepContents[stepIdx + 1] || "") : "";

  async function handleGenerate() {
    setGenerating(true);
    setError("");
    setSuccessMsg("");
    setRepairResult(null);
    setTaskId(null);
    setTaskStatus(null);
    try {
      const result = await repairStepPreview({
        lesson_id: lessonDetail?.lesson_id || "",
        grade: lessonDetail?.grade || "",
        subject: lessonDetail?.subject || "",
        chapter: lessonDetail?.chapter || "",
        step_number: step.step_number,
        step_title: step.step_title,
        step_content: step.raw_content || "",
        all_step_contents: allStepContents,
        audit_issues: step.issues || [],
        previous_step_content: prevContent,
        next_step_content: nextContent,
        use_llm: useLlm,
        override_api_key: overrideKey.trim() || null,
      });
      setRepairResult(result);
      if (result.task_id) {
        setTaskId(result.task_id);
        setTaskStatus(result.task_status);
      }
      if (!result.success) {
        setError(result.message || "Repair generation failed.");
      }
    } catch (err) {
      setError(err.message || "Repair generation failed.");
    } finally {
      setGenerating(false);
    }
  }

  async function handleApprove() {
    if (!taskId) return;
    setApproving(true);
    setError("");
    try {
      const r = await repairStepApprove(taskId);
      if (r.success) {
        setTaskStatus("approved");
        setSuccessMsg("Draft approved. Click Publish to write to lesson_cache.");
      } else {
        setError(r.message || "Approval failed.");
      }
    } catch (err) {
      setError(err.message || "Approval failed.");
    } finally {
      setApproving(false);
    }
  }

  async function handlePublish() {
    if (!taskId) return;
    setPublishing(true);
    setError("");
    try {
      const r = await repairStepPublish(taskId);
      if (r.success) {
        setTaskStatus("published");
        setSuccessMsg(`✅ Step published successfully. Original preserved for rollback.`);
        setConfirmOpen(false);
        onPublishSuccess?.();
      } else {
        setError(r.message || "Publish failed.");
        setConfirmOpen(false);
      }
    } catch (err) {
      setError(err.message || "Publish failed.");
      setConfirmOpen(false);
    } finally {
      setPublishing(false);
    }
  }

  const checks = repairResult?.validation_checks || {};
  const allChecksPass = Object.values(checks).every(Boolean);
  const validationFailed = !repairResult?.validation_result?.valid;
  const canApprove = taskStatus === "ready_for_review" && !validationFailed;
  const canPublish = taskStatus === "approved";
  const canApproveAndPublish = canApprove;

  const btnStyle = (color, disabled) => ({
    padding: "8px 16px", borderRadius: 8, border: "none", fontFamily: "inherit",
    fontWeight: 700, fontSize: ".82rem", cursor: disabled ? "not-allowed" : "pointer",
    background: disabled ? "#94a3b8" : color, color: "#fff",
  });

  return (
    <div data-testid="repair-with-ai-panel" style={{ fontFamily: "inherit" }}>

      {/* Workflow progress bar */}
      <div style={{ display: "flex", alignItems: "center", gap: 0, marginBottom: 18, overflowX: "auto" }}>
        {[
          { label: "Select Step", done: true },
          { label: "Generate Repair", done: !!repairResult },
          { label: "Validate", done: !!repairResult && !validationFailed },
          { label: "Approve", done: taskStatus === "approved" || taskStatus === "published" },
          { label: "Publish", done: taskStatus === "published" },
        ].map((s, i, arr) => (
          <div key={i} style={{ display: "flex", alignItems: "center" }}>
            <div style={{
              display: "flex", flexDirection: "column", alignItems: "center", minWidth: 80,
            }}>
              <div style={{
                width: 24, height: 24, borderRadius: "50%", display: "flex",
                alignItems: "center", justifyContent: "center", fontSize: ".7rem",
                fontWeight: 800, flexShrink: 0,
                background: s.done ? "#6366f1" : "var(--border,#e5e7eb)",
                color: s.done ? "#fff" : "#94a3b8",
              }}>
                {s.done ? "✓" : i + 1}
              </div>
              <span style={{ fontSize: ".65rem", color: s.done ? "#6366f1" : "#94a3b8", marginTop: 3, textAlign: "center" }}>
                {s.label}
              </span>
            </div>
            {i < arr.length - 1 && (
              <div style={{ height: 2, width: 24, background: s.done ? "#6366f1" : "var(--border,#e5e7eb)", flexShrink: 0, marginBottom: 14 }} />
            )}
          </div>
        ))}
      </div>

      {/* Step being repaired */}
      <div style={{ ...card({ background: "var(--surface2,#f8fafc)" }), marginBottom: 14 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <strong style={{ fontSize: ".88rem" }}>Step {step.step_number}: {step.step_title}</strong>
          {step.issues?.length > 0 && (
            <span style={{ background: "#ef4444", color: "#fff", borderRadius: 99, fontSize: ".65rem", padding: "1px 6px", fontWeight: 800 }}>
              {step.issues.length} issue{step.issues.length > 1 ? "s" : ""}
            </span>
          )}
          {taskStatus && (
            <span style={{
              padding: "2px 8px", borderRadius: 99, fontSize: ".72rem", fontWeight: 700,
              background: taskStatus === "published" ? "rgba(16,185,129,.15)" :
                         taskStatus === "approved"  ? "rgba(34,197,94,.15)"  :
                         taskStatus === "validation_failed" ? "rgba(239,68,68,.15)" :
                         "rgba(99,102,241,.15)",
              color: taskStatus === "published" ? "#065f46" :
                     taskStatus === "approved"  ? "#166534" :
                     taskStatus === "validation_failed" ? "#dc2626" : "#6366f1",
            }}>
              {taskStatus.replace(/_/g, " ")}
            </span>
          )}
        </div>
        {/* Issue list */}
        {step.issues?.length > 0 && (
          <div style={{ marginTop: 10 }}>
            {step.issues.slice(0, 3).map((issue, i) => (
              <div key={i} style={{ fontSize: ".75rem", color: issue.severity === "critical" ? "#dc2626" : issue.severity === "high" ? "#d97706" : "#64748b", marginBottom: 3 }}>
                <strong style={{ textTransform: "capitalize" }}>[{issue.severity}]</strong> {issue.issue_message}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* LLM config + generate button */}
      <div style={{ ...card(), marginBottom: 14 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12, flexWrap: "wrap", gap: 8 }}>
          <h4 style={{ margin: 0, fontSize: ".88rem", fontWeight: 800 }}>AI Repair Mode</h4>
          <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer", fontSize: ".8rem" }}>
            <input type="checkbox" checked={useLlm} onChange={e => setUseLlm(e.target.checked)} />
            Enable LLM Repair
          </label>
        </div>

        {useLlm && (
          <div style={{ marginBottom: 10 }}>
            <button onClick={() => setShowKeyInput(v => !v)}
              style={{ fontSize: ".72rem", background: "none", border: "1px solid var(--border,#e5e7eb)", borderRadius: 6, padding: "3px 10px", cursor: "pointer", fontFamily: "inherit", color: "#64748b" }}>
              {showKeyInput ? "▲ Hide" : "🔑 Override API key (optional)"}
            </button>
            {showKeyInput && (
              <input type="password" value={overrideKey} onChange={e => setOverrideKey(e.target.value)}
                placeholder="Leave blank to use Admin Settings key"
                style={{ display: "block", marginTop: 6, width: "100%", padding: "6px 10px", borderRadius: 7, border: "1px solid var(--border,#e5e7eb)", fontFamily: "monospace", fontSize: ".78rem" }} />
            )}
          </div>
        )}

        <div style={{ display: "flex", gap: 8 }}>
          <button data-testid="generate-repair-btn" onClick={handleGenerate} disabled={generating || !useLlm}
            style={btnStyle("#6366f1", generating || !useLlm)}>
            {generating ? "Generating…" : repairResult ? "Regenerate Repair" : "Generate Repair"}
          </button>
          {!useLlm && <span style={{ fontSize: ".78rem", color: "#94a3b8", alignSelf: "center" }}>Enable LLM to generate repair</span>}
        </div>
      </div>

      {/* Error / success */}
      {error && <div style={{ padding: "8px 12px", borderRadius: 8, background: "rgba(239,68,68,.08)", color: "#dc2626", fontSize: ".82rem", marginBottom: 12 }}>{error}</div>}
      {successMsg && <div data-testid="repair-success" style={{ padding: "8px 12px", borderRadius: 8, background: "rgba(34,197,94,.08)", color: "#166534", fontSize: ".82rem", marginBottom: 12 }}>{successMsg}</div>}

      {/* ── Results section (only shown after generation) ── */}
      {repairResult?.success && (
        <>
          {/* View mode toggle */}
          <div style={{ display: "flex", gap: 6, marginBottom: 14 }}>
            {["side-by-side", "raw"].map(mode => (
              <button key={mode} onClick={() => setViewMode(mode)}
                style={{
                  padding: "5px 12px", borderRadius: 7, border: `1.5px solid ${viewMode === mode ? "#6366f1" : "var(--border,#e5e7eb)"}`,
                  background: viewMode === mode ? "rgba(99,102,241,.1)" : "var(--panel,#fff)",
                  fontFamily: "inherit", fontSize: ".78rem", fontWeight: viewMode === mode ? 700 : 400, cursor: "pointer",
                }}>
                {mode === "side-by-side" ? "Before / After" : "Raw JSON"}
              </button>
            ))}
          </div>

          {/* Before / After panels */}
          {viewMode === "side-by-side" && (
            <div data-testid="before-after-panels" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 14 }}>
              <div style={{ ...card({ background: "rgba(239,68,68,.03)", border: "1px solid rgba(239,68,68,.2)" }) }}>
                <div style={{ fontSize: ".72rem", fontWeight: 700, color: "#dc2626", marginBottom: 8, textTransform: "uppercase" }}>Before</div>
                <div style={{ fontSize: ".8rem", lineHeight: 1.7, maxHeight: 320, overflowY: "auto" }}>
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{repairResult.before_content || ""}</ReactMarkdown>
                </div>
              </div>
              <div style={{ ...card({ background: "rgba(34,197,94,.03)", border: "1px solid rgba(34,197,94,.2)" }) }}>
                <div style={{ fontSize: ".72rem", fontWeight: 700, color: "#166534", marginBottom: 8, textTransform: "uppercase" }}>After (Repaired)</div>
                <div style={{ fontSize: ".8rem", lineHeight: 1.7, maxHeight: 320, overflowY: "auto" }}>
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{repairResult.after_content || ""}</ReactMarkdown>
                </div>
              </div>
            </div>
          )}

          {viewMode === "raw" && (
            <div style={{ ...card(), marginBottom: 14 }}>
              <pre style={{ whiteSpace: "pre-wrap", wordBreak: "break-word", fontSize: ".72rem", margin: 0, maxHeight: 300, overflowY: "auto" }}>
                {JSON.stringify(repairResult.after_sections || {}, null, 2)}
              </pre>
            </div>
          )}

          {/* Impact + Validation side by side */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 14 }}>
            {/* Impact */}
            <div style={card()} data-testid="impact-panel">
              <h4 style={{ margin: "0 0 10px", fontSize: ".85rem", fontWeight: 800 }}>Impact After Repair</h4>
              <ScoreDelta label="Overall" before={repairResult.before_scores?.overall} after={repairResult.after_scores?.overall} color="#6366f1" />
              <ScoreDelta label="Uniqueness" before={repairResult.before_scores?.uniqueness} after={repairResult.after_scores?.uniqueness} color="#8b5cf6" />
              <ScoreDelta label="Depth" before={repairResult.before_scores?.depth} after={repairResult.after_scores?.depth} color="#10b981" />
              <ScoreDelta label="No Repeat" before={repairResult.before_scores?.repetition} after={repairResult.after_scores?.repetition} color="#f59e0b" />
              <ScoreDelta label="Completeness" before={repairResult.before_scores?.completeness} after={repairResult.after_scores?.completeness} color="#0ea5e9" />
            </div>

            {/* Validation checklist */}
            <div style={card()} data-testid="validation-checklist">
              <h4 style={{ margin: "0 0 10px", fontSize: ".85rem", fontWeight: 800 }}>Validation Checks</h4>
              <ValidationCheck label="No critical issues remaining" pass={checks.no_critical_issues} />
              <ValidationCheck label="Validation passed" pass={checks.validation_passed} />
              <ValidationCheck label="Overall score ≥ 85" pass={checks.overall_above_threshold} />
              <ValidationCheck label="Uniqueness improved" pass={checks.uniqueness_improved} />
              <ValidationCheck label="Depth maintained/improved" pass={checks.depth_improved} />
              <ValidationCheck label="Sections complete (≥75%)" pass={checks.sections_complete} />
              {validationFailed && (
                <div style={{ marginTop: 8, padding: "6px 10px", borderRadius: 7, background: "rgba(239,68,68,.08)", color: "#dc2626", fontSize: ".75rem", fontWeight: 700 }}>
                  Validation failed — regenerate or fix issues before approving.
                </div>
              )}
              {allChecksPass && (
                <div style={{ marginTop: 8, padding: "6px 10px", borderRadius: 7, background: "rgba(34,197,94,.08)", color: "#166534", fontSize: ".75rem", fontWeight: 700 }}>
                  ✓ All checks passed — ready to approve.
                </div>
              )}
            </div>
          </div>

          {/* Repair notes */}
          {(repairResult.repair_rationale || repairResult.new_value_added) && (
            <div style={{ ...card({ background: "var(--surface2,#f8fafc)" }), marginBottom: 14, fontSize: ".82rem" }}>
              {repairResult.repair_rationale && (
                <p style={{ margin: "0 0 6px" }}><strong>Repair rationale:</strong> {repairResult.repair_rationale}</p>
              )}
              {repairResult.new_value_added && (
                <p style={{ margin: 0 }}><strong>New value added:</strong> {repairResult.new_value_added}</p>
              )}
            </div>
          )}

          {/* Actions */}
          <div data-testid="repair-actions" style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 8 }}>
            <button onClick={handleGenerate} disabled={generating}
              style={btnStyle("#64748b", generating)}>
              ↺ Regenerate
            </button>
            {canApprove && (
              <button data-testid="approve-btn" onClick={handleApprove} disabled={approving}
                style={btnStyle("#22c55e", approving)}>
                {approving ? "Approving…" : "✓ Approve Draft"}
              </button>
            )}
            {canPublish && (
              <button data-testid="publish-btn" onClick={() => setConfirmOpen(true)}
                style={btnStyle("#6366f1", false)}>
                🚀 Publish Approved
              </button>
            )}
            {canApproveAndPublish && (
              <button data-testid="approve-publish-btn"
                onClick={async () => { await handleApprove(); setConfirmOpen(true); }}
                disabled={approving}
                style={btnStyle("#6366f1", approving)}>
                {approving ? "…" : "✓ Approve & Publish"}
              </button>
            )}
          </div>

          {/* Lesson Repair link */}
          <div style={{ fontSize: ".75rem", color: "#94a3b8", marginTop: 8 }}>
            💡 Use{" "}
            <a href="/?admin=true#tab=operations" style={{ color: "#6366f1", textDecoration: "none" }}>
              Lesson Repair
            </a>{" "}
            for bulk jobs, queue management, and bulk apply.
          </div>
        </>
      )}

      <ConfirmPublishModal
        open={confirmOpen}
        stepTitle={`Step ${step.step_number}: ${step.step_title}`}
        onConfirm={handlePublish}
        onCancel={() => setConfirmOpen(false)}
        publishing={publishing}
      />
    </div>
  );
}
