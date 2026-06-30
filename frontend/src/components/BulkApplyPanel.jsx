/**
 * BulkApplyPanel.jsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Admin bulk-apply panel for Lesson Repair.
 *
 * Features:
 * - Dry-run: shows eligible/skipped summary before applying
 * - Confidence mode toggle (bulk apply disabled by default)
 * - Confirmation modal with dry-run summary
 * - Apply selected / all-approved scopes
 *
 * Props:
 *   selectedTaskIds  — array of task IDs selected in the task list
 *   jobGrade/jobSubject/jobChapter — optional filter context
 *   onApplied(result) — callback after successful bulk apply
 *   bulkDryRunFn(opts) — API function
 *   bulkApplyFn(opts)  — API function
 */

import { useState } from "react";

const SCOPE_LABELS = {
  selected:     "Selected Tasks",
  all_approved: "All Approved Tasks",
  current_filter: "Current Filter",
};

function DryRunSummary({ dryRun }) {
  if (!dryRun) return null;
  return (
    <div data-testid="dry-run-summary" style={{
      padding: "14px 16px",
      borderRadius: 10,
      background: dryRun.eligible > 0 ? "rgba(34,197,94,.07)" : "rgba(245,158,11,.07)",
      border: `1px solid ${dryRun.eligible > 0 ? "rgba(34,197,94,.3)" : "rgba(245,158,11,.3)"}`,
      marginBottom: 14,
    }}>
      <div style={{ display: "flex", gap: 20, flexWrap: "wrap", marginBottom: 8 }}>
        <div>
          <div style={{ fontSize: "1.4rem", fontWeight: 800, color: "#22c55e" }}>{dryRun.eligible}</div>
          <div style={{ fontSize: ".72rem", color: "#94a3b8" }}>Eligible</div>
        </div>
        <div>
          <div style={{ fontSize: "1.4rem", fontWeight: 800, color: "#f59e0b" }}>{dryRun.skipped}</div>
          <div style={{ fontSize: ".72rem", color: "#94a3b8" }}>Skipped</div>
        </div>
        <div>
          <div style={{ fontSize: "1.4rem", fontWeight: 800, color: "#64748b" }}>{dryRun.total}</div>
          <div style={{ fontSize: ".72rem", color: "#94a3b8" }}>Total</div>
        </div>
      </div>
      {dryRun.skipped_details?.length > 0 && (
        <details>
          <summary style={{ fontSize: ".75rem", color: "#64748b", cursor: "pointer" }}>
            {dryRun.skipped_details.length} skipped — see reasons
          </summary>
          <ul style={{ margin: "6px 0 0", paddingLeft: 16, fontSize: ".72rem", color: "#94a3b8" }}>
            {dryRun.skipped_details.slice(0, 10).map((s, i) => (
              <li key={i}>{s.task_id?.slice(0, 8)}… — {s.reason}</li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}

function ConfirmModal({ open, dryRun, scope, onConfirm, onCancel, applying }) {
  if (!open) return null;
  return (
    <div style={{
      position: "fixed", inset: 0, background: "rgba(0,0,0,.5)",
      zIndex: 1000, display: "flex", alignItems: "center", justifyContent: "center", padding: 16,
    }}>
      <div style={{
        background: "var(--panel,#fff)", borderRadius: 14, padding: "24px 28px",
        maxWidth: 480, width: "100%", boxShadow: "0 8px 32px rgba(0,0,0,.2)",
      }}>
        <h3 style={{ margin: "0 0 8px", fontSize: "1rem", fontWeight: 800 }}>
          Confirm Bulk Apply
        </h3>
        <p style={{ fontSize: ".85rem", color: "#64748b", margin: "0 0 16px", lineHeight: 1.6 }}>
          You are about to publish <strong>{dryRun?.eligible || 0} repaired lesson steps</strong> ({SCOPE_LABELS[scope] || scope}).
          Original content will be preserved for rollback.
        </p>
        <DryRunSummary dryRun={dryRun} />
        <div style={{ padding: "10px 14px", background: "rgba(245,158,11,.08)", border: "1px solid rgba(245,158,11,.3)", borderRadius: 8, fontSize: ".78rem", color: "#92400e", marginBottom: 16 }}>
          ⚠ Only tasks that passed validation and meet score thresholds will be published.
          Failed and unapproved tasks are automatically skipped.
        </div>
        <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
          <button
            onClick={onCancel}
            disabled={applying}
            style={{
              padding: "8px 18px", borderRadius: 8, border: "1px solid var(--border,#e5e7eb)",
              background: "var(--surface2,#f8f9fa)", fontFamily: "inherit", cursor: "pointer",
              fontSize: ".85rem", fontWeight: 600,
            }}
          >
            Cancel
          </button>
          <button
            data-testid="confirm-bulk-apply-btn"
            onClick={onConfirm}
            disabled={applying || !dryRun?.eligible}
            style={{
              padding: "8px 18px", borderRadius: 8, border: "none",
              background: dryRun?.eligible ? "#6366f1" : "#94a3b8",
              color: "#fff", fontFamily: "inherit", cursor: dryRun?.eligible ? "pointer" : "not-allowed",
              fontSize: ".85rem", fontWeight: 700,
            }}
          >
            {applying ? "Applying…" : `Publish ${dryRun?.eligible || 0} Steps`}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function BulkApplyPanel({
  selectedTaskIds = [],
  jobGrade,
  jobSubject,
  jobChapter,
  onApplied,
  bulkDryRunFn,
  bulkApplyFn,
}) {
  const [confidenceMode, setConfidenceMode] = useState(false);
  const [scope, setScope] = useState("selected");
  const [minScore, setMinScore] = useState(90);
  const [dryRunResult, setDryRunResult] = useState(null);
  const [dryRunLoading, setDryRunLoading] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [applying, setApplying] = useState(false);
  const [applyResult, setApplyResult] = useState(null);
  const [error, setError] = useState("");

  const opts = {
    scope,
    task_ids: scope === "selected" ? selectedTaskIds : [],
    grade:    jobGrade   || null,
    subject:  jobSubject || null,
    chapter:  jobChapter || null,
    min_score: minScore,
    min_depth_score: 85,
  };

  async function handleDryRun() {
    setDryRunLoading(true);
    setError("");
    setDryRunResult(null);
    setApplyResult(null);
    try {
      const result = await bulkDryRunFn(opts);
      setDryRunResult(result);
    } catch (err) {
      setError(err.message || "Dry-run failed.");
    } finally {
      setDryRunLoading(false);
    }
  }

  async function handleApply() {
    setApplying(true);
    setError("");
    try {
      const result = await bulkApplyFn(opts);
      setApplyResult(result);
      setConfirmOpen(false);
      setDryRunResult(null);
      onApplied && onApplied(result);
    } catch (err) {
      setError(err.message || "Bulk apply failed.");
      setConfirmOpen(false);
    } finally {
      setApplying(false);
    }
  }

  const canDryRun = scope !== "selected" || selectedTaskIds.length > 0;

  return (
    <div data-testid="bulk-apply-panel" style={{
      padding: "16px 18px",
      borderRadius: 12,
      border: "1px solid var(--border,#e5e7eb)",
      background: "var(--panel,#fff)",
      marginTop: 16,
    }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14, flexWrap: "wrap", gap: 8 }}>
        <h4 style={{ margin: 0, fontSize: ".9rem", fontWeight: 800 }}>Bulk Apply Fixes</h4>

        {/* Confidence mode toggle */}
        <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
          <div
            data-testid="confidence-mode-toggle"
            onClick={() => setConfidenceMode(v => !v)}
            style={{
              width: 42, height: 22, borderRadius: 11,
              background: confidenceMode ? "#6366f1" : "#cbd5e1",
              position: "relative", cursor: "pointer", flexShrink: 0,
            }}
          >
            <div style={{
              position: "absolute", top: 3,
              left: confidenceMode ? 23 : 3,
              width: 16, height: 16, borderRadius: "50%",
              background: "#fff", transition: "left .15s",
            }} />
          </div>
          <span style={{ fontSize: ".78rem", fontWeight: 600, color: confidenceMode ? "#6366f1" : "#94a3b8" }}>
            Bulk apply mode {confidenceMode ? "ON" : "OFF"}
          </span>
        </label>
      </div>

      {!confidenceMode && (
        <div style={{ padding: "10px 14px", background: "rgba(99,102,241,.06)", borderRadius: 8, fontSize: ".78rem", color: "#6366f1", marginBottom: 14 }}>
          Enable bulk apply mode to apply fixes in one click. When OFF you must approve tasks one by one.
        </div>
      )}

      {/* Scope selector */}
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
        {[
          { key: "selected",     label: `Selected (${selectedTaskIds.length})` },
          { key: "all_approved", label: "All Approved" },
        ].map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setScope(key)}
            style={{
              padding: "5px 12px", borderRadius: 7, fontFamily: "inherit",
              fontSize: ".78rem", fontWeight: 600, cursor: "pointer",
              background: scope === key ? "#6366f1" : "var(--surface2,#f8f9fa)",
              color: scope === key ? "#fff" : "var(--text,#374151)",
              border: `1px solid ${scope === key ? "#6366f1" : "var(--border,#e5e7eb)"}`,
            }}
          >
            {label}
          </button>
        ))}

        <label style={{ display: "flex", alignItems: "center", gap: 6, marginLeft: "auto", fontSize: ".78rem" }}>
          Min score
          <input
            type="number" min={50} max={100}
            value={minScore}
            onChange={e => setMinScore(Number(e.target.value))}
            style={{ width: 56, padding: "4px 6px", borderRadius: 6, border: "1px solid var(--border,#e5e7eb)", fontFamily: "inherit", fontSize: ".78rem" }}
          />
        </label>
      </div>

      {/* Action buttons */}
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <button
          data-testid="dry-run-btn"
          onClick={handleDryRun}
          disabled={dryRunLoading || !canDryRun}
          style={{
            padding: "7px 16px", borderRadius: 8, border: "1px solid #6366f1",
            background: "transparent", color: "#6366f1",
            fontFamily: "inherit", fontSize: ".82rem", fontWeight: 700, cursor: "pointer",
          }}
        >
          {dryRunLoading ? "Checking…" : "Dry Run — Check Eligibility"}
        </button>

        {confidenceMode && (
          <button
            data-testid="bulk-apply-btn"
            onClick={() => {
              if (!dryRunResult) { handleDryRun().then(() => setConfirmOpen(true)); return; }
              setConfirmOpen(true);
            }}
            disabled={applying || !canDryRun}
            style={{
              padding: "7px 16px", borderRadius: 8, border: "none",
              background: "#6366f1", color: "#fff",
              fontFamily: "inherit", fontSize: ".82rem", fontWeight: 700, cursor: "pointer",
            }}
          >
            {applying ? "Applying…" : "Apply Fixes →"}
          </button>
        )}
      </div>

      {/* Dry-run result */}
      {dryRunResult && !confirmOpen && (
        <div style={{ marginTop: 12 }}>
          <DryRunSummary dryRun={dryRunResult} />
          {confidenceMode && dryRunResult.eligible > 0 && (
            <button
              data-testid="confirm-open-btn"
              onClick={() => setConfirmOpen(true)}
              style={{
                padding: "7px 16px", borderRadius: 8, border: "none",
                background: "#6366f1", color: "#fff",
                fontFamily: "inherit", fontSize: ".82rem", fontWeight: 700, cursor: "pointer",
              }}
            >
              Apply {dryRunResult.eligible} Eligible Fixes →
            </button>
          )}
        </div>
      )}

      {/* Apply result */}
      {applyResult && (
        <div data-testid="apply-result" style={{
          marginTop: 12, padding: "12px 14px", borderRadius: 8,
          background: "rgba(34,197,94,.08)", border: "1px solid rgba(34,197,94,.3)",
          fontSize: ".82rem",
        }}>
          ✅ {applyResult.message || `Published ${applyResult.published} fixes.`}
          {applyResult.failed > 0 && (
            <span style={{ color: "#ef4444", marginLeft: 8 }}>({applyResult.failed} failed)</span>
          )}
        </div>
      )}

      {error && (
        <div style={{ marginTop: 12, padding: "10px 14px", borderRadius: 8, background: "rgba(239,68,68,.08)", border: "1px solid rgba(239,68,68,.25)", fontSize: ".82rem", color: "#dc2626" }}>
          {error}
        </div>
      )}

      <ConfirmModal
        open={confirmOpen}
        dryRun={dryRunResult}
        scope={scope}
        onConfirm={handleApply}
        onCancel={() => setConfirmOpen(false)}
        applying={applying}
      />
    </div>
  );
}
