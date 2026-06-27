/**
 * ClassroomAnalyticsCard.jsx — Per-classroom analytics summary.
 * Loads from /api/teacher/classrooms/{id}/analytics.
 * Shows "Not available yet" when source data is missing.
 */
import { useEffect, useState } from "react";
import { getClassroomAnalytics } from "../../api/teacherDashboard";

export default function ClassroomAnalyticsCard({ classroomId, classroomName: _cn }) {
  const [data, setData]     = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!classroomId) return;
    getClassroomAnalytics(classroomId)
      .then(d => { setData(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, [classroomId]);

  if (loading) return <div style={{ color: "#94a3b8", fontSize: ".75rem" }}>Loading analytics…</div>;
  if (!data)   return null;

  const mock  = data.mock_test || {};
  const act   = data.activity  || {};

  return (
    <div data-testid={`classroom-analytics-${classroomId}`} style={{ marginTop: 10 }}>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
        <div style={{ background: "var(--surface2,#f8fafc)", border: "1px solid var(--border,#e5e7eb)", borderRadius: 7, padding: "6px 10px", minWidth: 60, textAlign: "center" }}>
          <div style={{ fontWeight: 700, fontSize: ".88rem" }}>{data.student_count || 0}</div>
          <div style={{ fontSize: ".65rem", color: "#64748b" }}>Students</div>
        </div>
        <div style={{ background: "var(--surface2,#f8fafc)", border: "1px solid var(--border,#e5e7eb)", borderRadius: 7, padding: "6px 10px", minWidth: 60, textAlign: "center" }}>
          <div style={{ fontWeight: 700, fontSize: ".88rem", color: "#22c55e" }}>{data.active_count || 0}</div>
          <div style={{ fontSize: ".65rem", color: "#64748b" }}>Active</div>
        </div>
        <div style={{ background: "var(--surface2,#f8fafc)", border: "1px solid var(--border,#e5e7eb)", borderRadius: 7, padding: "6px 10px", minWidth: 80, textAlign: "center" }}>
          <div style={{ fontWeight: 700, fontSize: ".88rem", color: "#0ea5e9" }}>
            {mock.available ? mock.average_score + "%" : <span style={{ fontSize: ".7rem", color: "#94a3b8" }}>Not available yet</span>}
          </div>
          <div style={{ fontSize: ".65rem", color: "#64748b" }}>Avg Score</div>
        </div>
        <div style={{ background: "var(--surface2,#f8fafc)", border: "1px solid var(--border,#e5e7eb)", borderRadius: 7, padding: "6px 10px", minWidth: 80, textAlign: "center" }}>
          <div style={{ fontWeight: 700, fontSize: ".88rem", color: "#8b5cf6" }}>
            {act.available ? act.active_last_7_days : <span style={{ fontSize: ".7rem", color: "#94a3b8" }}>Not available yet</span>}
          </div>
          <div style={{ fontSize: ".65rem", color: "#64748b" }}>Active 7d</div>
        </div>
      </div>
    </div>
  );
}
