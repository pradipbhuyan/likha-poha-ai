/**
 * TeacherAssistantCard.jsx — Rule-based Teacher Assistant summary card
 * Shows: attention count, expiring invitations, open tasks, top 3 actions.
 * No external AI required — derived from dashboard summary + interventions + tasks.
 */
import { useEffect, useState } from "react";
import { getTeacherClassroomSummary, getInterventions, listTeacherTasks } from "../../api/teacherDashboard";

export default function TeacherAssistantCard({ onNavigate }) {
  const [, setSummary]             = useState(null);
  const [critical, setCritical]   = useState(0);
  const [openTasks, setOpenTasks] = useState(0);
  const [expiring, setExpiring]   = useState(0);
  const [loading, setLoading]     = useState(true);

  useEffect(() => {
    Promise.all([
      getTeacherClassroomSummary().catch(() => null),
      getInterventions().catch(() => null),
      listTeacherTasks("open").catch(() => null),
    ]).then(([s, inv, tasks]) => {
      setSummary(s);
      const criticalCount = (inv?.interventions || []).filter(i => i.severity === "critical").length;
      setCritical(criticalCount);
      setOpenTasks((tasks?.tasks || []).length);
      // Count pending invitations that are near expiry (within 3 days)
      // expiry calculation placeholder
      const expiringCount = (s?.students?.pending_invitations || 0);
      setExpiring(expiringCount);
      setLoading(false);
    });
  }, []);

  if (loading) return null;

  const allClear = critical === 0 && openTasks === 0 && expiring === 0;
  const actions = [];
  if (critical > 0) actions.push({ label: "Review inactive students", tab: "insights" });
  if (expiring > 0) actions.push({ label: "Check pending invitations", tab: "invitations" });
  if (openTasks > 0) actions.push({ label: "Complete open tasks", tab: "tasks" });
  if (actions.length === 0) actions.push({ label: "Add a student", tab: "students" });

  return (
    <div data-testid="teacher-assistant-card" style={{ background: allClear ? "linear-gradient(135deg,#f0fdf4,#dcfce7)" : "linear-gradient(135deg,#eff6ff,#dbeafe)", border: `1px solid ${allClear ? "#bbf7d0" : "#bfdbfe"}`, borderRadius: 12, padding: "14px 16px", marginBottom: 14 }}>
      <div style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
        <span style={{ fontSize: "1.4rem" }}>{allClear ? "✅" : "🧑‍🏫"}</span>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 700, fontSize: ".9rem", marginBottom: 4 }}>
            {allClear
              ? "Everything looks good. No urgent classroom actions today."
              : `${[critical > 0 && `${critical} student${critical > 1 ? "s" : ""} need${critical > 1 ? "" : "s"} attention`, openTasks > 0 && `${openTasks} task${openTasks > 1 ? "s" : ""} open`, expiring > 0 && `${expiring} pending invitation${expiring > 1 ? "s" : ""}`].filter(Boolean).join(" · ")}.`
            }
          </div>
          {!allClear && (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 6 }}>
              {actions.slice(0, 3).map(a => (
                <button key={a.label} onClick={() => onNavigate && onNavigate(a.tab)}
                  style={{ padding: "4px 10px", borderRadius: 6, border: "1px solid #3b82f6", background: "rgba(59,130,246,.08)", color: "#1d4ed8", fontSize: ".75rem", cursor: "pointer", fontFamily: "inherit", fontWeight: 600 }}>
                  {a.label}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
