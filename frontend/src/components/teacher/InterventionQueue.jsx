/**
 * InterventionQueue.jsx — Prioritized intervention list with actionable buttons.
 * Loads from /api/teacher/interventions.
 * Groups: Needs Immediate Attention (critical) | Needs Review (medium) | Low Priority (low)
 * Actions: View Student, Create Task, Reset Password, Email Login Details (paid), Message Parent
 */
import { useEffect, useState } from "react";
import { getInterventions } from "../../api/teacherDashboard";

const SEV_LABELS = {
  critical: { label: "Needs Immediate Attention", color: "#dc2626", bg: "rgba(239,68,68,.07)", border: "rgba(239,68,68,.2)" },
  medium:   { label: "Needs Review",               color: "#f59e0b", bg: "rgba(245,158,11,.07)", border: "rgba(245,158,11,.2)" },
  low:      { label: "Low Priority",               color: "#64748b", bg: "rgba(148,163,184,.07)", border: "rgba(148,163,184,.2)" },
};

export default function InterventionQueue({ isPaid: _isPaid, onViewStudent, onCreateTask }) {
  const [interventions, setInterventions] = useState([]);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState(null);

  useEffect(() => {
    getInterventions()
      .then(d => { setInterventions(d?.interventions || []); setLoading(false); })
      .catch(e => { setError(e.message); setLoading(false); });
  }, []);

  if (loading) return <div style={{ color: "#94a3b8", fontSize: ".82rem" }}>Loading interventions…</div>;
  if (error)   return <div style={{ color: "#dc2626", fontSize: ".82rem" }}>⚠ {error}</div>;
  if (interventions.length === 0) return (
    <div data-testid="intervention-queue-empty" style={{ padding: "12px 0", color: "#94a3b8", fontSize: ".85rem" }}>
      ✅ No students need attention right now.
    </div>
  );

  const grouped = { critical: [], medium: [], low: [] };
  for (const inv of interventions) {
    (grouped[inv.severity] || grouped.low).push(inv);
  }

  return (
    <div data-testid="intervention-queue">
      {(["critical", "medium", "low"]).map(sev => {
        const group = grouped[sev];
        if (group.length === 0) return null;
        const style = SEV_LABELS[sev];
        return (
          <div key={sev} style={{ marginBottom: 16 }}>
            <div style={{ fontSize: ".75rem", fontWeight: 700, color: style.color, textTransform: "uppercase", letterSpacing: ".04em", marginBottom: 6 }}>
              {style.label} ({group.length})
            </div>
            {group.map((inv, i) => (
              <div key={inv.student_id || i} data-testid={`intervention-${sev}-${i}`}
                style={{ background: style.bg, border: `1px solid ${style.border}`, borderRadius: 9, padding: "10px 12px", marginBottom: 8 }}>
                <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 6 }}>
                  <div>
                    <strong style={{ fontSize: ".85rem" }}>{inv.student_name}</strong>
                    <span style={{ marginLeft: 6, fontSize: ".72rem", color: "#64748b" }}>{inv.grade}</span>
                    <div style={{ marginTop: 4, display: "flex", flexWrap: "wrap", gap: 4 }}>
                      {(inv.reasons || []).map((r, ri) => (
                        <span key={ri} style={{ fontSize: ".7rem", background: "rgba(0,0,0,.05)", padding: "1px 6px", borderRadius: 4, color: "#64748b" }}>{r}</span>
                      ))}
                    </div>
                  </div>
                  {/* Actions */}
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 5, alignSelf: "center" }}>
                    {inv.student_id && onViewStudent && (
                      <button onClick={() => onViewStudent(inv)}
                        style={{ padding: "4px 9px", borderRadius: 6, border: "1px solid #6366f1", background: "rgba(99,102,241,.08)", color: "#6366f1", fontSize: ".72rem", cursor: "pointer", fontFamily: "inherit", fontWeight: 600 }}>
                        View
                      </button>
                    )}
                    {inv.student_id && onCreateTask && (
                      <button onClick={() => onCreateTask(inv)}
                        data-testid={`create-task-${i}`}
                        style={{ padding: "4px 9px", borderRadius: 6, border: "1px solid #8b5cf6", background: "rgba(139,92,246,.08)", color: "#7c3aed", fontSize: ".72rem", cursor: "pointer", fontFamily: "inherit", fontWeight: 600 }}>
                        + Task
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        );
      })}
    </div>
  );
}
