/**
 * StepSequencePanel.jsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Renders a 6-step timeline for a lesson's step-sequence audit result.
 *
 * Props:
 *   analysis  — audit result from POST /api/admin/qa/lesson-repair/step-analysis
 *   onSelectStep(stepResult) — called when a step card is clicked
 *   selectedStepIndex — currently selected step index (for highlight)
 */

const STATUS_COLOR = {
  pass:     { bg: "rgba(34,197,94,.1)",   border: "#22c55e", text: "#166534", dot: "#22c55e"  },
  warning:  { bg: "rgba(245,158,11,.1)",  border: "#f59e0b", text: "#92400e", dot: "#f59e0b"  },
  critical: { bg: "rgba(239,68,68,.1)",   border: "#ef4444", text: "#dc2626", dot: "#ef4444"  },
};

function ScoreBar({ value, color = "#6366f1", label }) {
  return (
    <div style={{ marginBottom: 4 }}>
      {label && <div style={{ fontSize: ".68rem", color: "#94a3b8", marginBottom: 2 }}>{label}</div>}
      <div style={{ height: 5, borderRadius: 99, background: "var(--border,#e5e7eb)", overflow: "hidden" }}>
        <div style={{ height: "100%", width: `${Math.max(0, Math.min(100, value || 0))}%`, background: color, borderRadius: 99, transition: "width .3s" }} />
      </div>
      <div style={{ fontSize: ".68rem", color, fontWeight: 700, marginTop: 1 }}>{value ?? "—"}</div>
    </div>
  );
}

function StepCard({ stepResult, isSelected, onClick }) {
  const s = stepResult;
  const col = STATUS_COLOR[s.status] || STATUS_COLOR.warning;
  const severityCount = (s.issues || []).length;

  return (
    <div
      data-testid={`step-card-${s.step_number}`}
      onClick={onClick}
      style={{
        flex: "1 1 140px",
        minWidth: 130,
        maxWidth: 200,
        padding: "10px 12px",
        borderRadius: 10,
        border: `2px solid ${isSelected ? "#6366f1" : col.border}`,
        background: isSelected ? "rgba(99,102,241,.1)" : col.bg,
        cursor: "pointer",
        transition: "all .15s",
      }}
    >
      {/* Step header */}
      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 6 }}>
        <span style={{ width: 8, height: 8, borderRadius: "50%", background: col.dot, flexShrink: 0 }} />
        <strong style={{ fontSize: ".75rem", color: col.text }}>Step {s.step_number}</strong>
        {severityCount > 0 && (
          <span style={{
            marginLeft: "auto", fontSize: ".62rem", fontWeight: 700,
            background: col.dot, color: "#fff",
            padding: "1px 5px", borderRadius: 99,
          }}>
            {severityCount}
          </span>
        )}
      </div>

      {/* Step title */}
      <div style={{ fontSize: ".7rem", color: "var(--text,#374151)", fontWeight: 600, marginBottom: 8, lineHeight: 1.3 }}>
        {s.step_title || s.step_role}
      </div>

      {/* Scores */}
      <ScoreBar value={s.step_uniqueness_score}       label="Unique %"  color="#6366f1" />
      <ScoreBar value={s.depth_progression_score}     label="Depth"     color="#10b981" />
      <ScoreBar value={s.cross_step_repetition_score} label="No repeat" color="#f59e0b" />

      {/* Word count */}
      <div style={{ fontSize: ".65rem", color: "#94a3b8", marginTop: 4 }}>
        {s.word_count} words · {s.unique_content_pct}% unique
      </div>
    </div>
  );
}

export default function StepSequencePanel({ analysis, onSelectStep, selectedStepIndex }) {
  if (!analysis) return null;
  const { step_results = [], summary = {}, similarity_matrix = [] } = analysis;

  const overallScore = summary.overall_step_sequence_score ?? 0;
  const overallColor = overallScore >= 80 ? "#22c55e" : overallScore >= 60 ? "#f59e0b" : "#ef4444";

  return (
    <div data-testid="step-sequence-panel">
      {/* Summary bar */}
      <div style={{
        display: "flex", alignItems: "center", gap: 16, flexWrap: "wrap",
        padding: "10px 16px", background: "var(--surface2,#f8f9fa)",
        borderRadius: 10, marginBottom: 14,
        border: "1px solid var(--border,#e5e7eb)",
      }}>
        <div style={{ textAlign: "center", minWidth: 60 }}>
          <div style={{ fontSize: "1.4rem", fontWeight: 800, color: overallColor }}>{overallScore}</div>
          <div style={{ fontSize: ".65rem", color: "#94a3b8" }}>Overall</div>
        </div>
        {[
          { label: "Uniqueness",  value: summary.avg_step_uniqueness_score,   color: "#6366f1" },
          { label: "Depth",       value: summary.depth_progression_score,     color: "#10b981" },
          { label: "No Repeat",   value: summary.cross_step_repetition_score, color: "#f59e0b" },
          { label: "Completeness",value: summary.avg_step_completeness_score, color: "#0ea5e9" },
        ].map(({ label, value, color }) => (
          <div key={label} style={{ minWidth: 70 }}>
            <ScoreBar value={value} color={color} label={label} />
          </div>
        ))}
        <div style={{ marginLeft: "auto", fontSize: ".78rem", display: "flex", gap: 10 }}>
          {summary.critical_issues > 0 && (
            <span style={{ color: "#ef4444", fontWeight: 700 }}>
              ⚠ {summary.critical_issues} critical
            </span>
          )}
          {summary.high_issues > 0 && (
            <span style={{ color: "#f59e0b", fontWeight: 700 }}>
              {summary.high_issues} high
            </span>
          )}
          {summary.critical_issues === 0 && summary.high_issues === 0 && (
            <span style={{ color: "#22c55e", fontWeight: 700 }}>✓ No critical issues</span>
          )}
        </div>
      </div>

      {/* Step timeline */}
      <div
        data-testid="step-timeline"
        style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 14 }}
      >
        {step_results.map((sr) => (
          <StepCard
            key={sr.step_index}
            stepResult={sr}
            isSelected={selectedStepIndex === sr.step_index}
            onClick={() => onSelectStep && onSelectStep(sr)}
          />
        ))}
      </div>

      {/* Similarity matrix (compact) */}
      {similarity_matrix.length > 0 && (
        <details style={{ marginTop: 8 }}>
          <summary style={{ fontSize: ".78rem", color: "#64748b", cursor: "pointer", userSelect: "none", marginBottom: 6 }}>
            Step similarity matrix
          </summary>
          <div style={{ overflowX: "auto" }}>
            <table style={{ borderCollapse: "collapse", fontSize: ".72rem" }}>
              <thead>
                <tr>
                  <th style={{ padding: "3px 6px", color: "#94a3b8" }}>vs</th>
                  {step_results.map((sr) => (
                    <th key={sr.step_index} style={{ padding: "3px 6px", color: "#94a3b8", minWidth: 36 }}>
                      S{sr.step_number}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {similarity_matrix.map((row, i) => (
                  <tr key={i}>
                    <td style={{ padding: "3px 6px", color: "#94a3b8", fontWeight: 600 }}>S{i + 1}</td>
                    {row.map((sim, j) => {
                      const bg = i === j ? "var(--border,#e5e7eb)" :
                        sim >= 0.90 ? "rgba(239,68,68,.25)" :
                        sim >= 0.75 ? "rgba(245,158,11,.2)" :
                        sim >= 0.50 ? "rgba(245,158,11,.08)" : "transparent";
                      return (
                        <td key={j} style={{ padding: "3px 6px", textAlign: "center", background: bg, borderRadius: 4 }}>
                          {i === j ? "—" : Math.round(sim * 100) + "%"}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      )}
    </div>
  );
}
