/**
 * SuggestedTaskModal.jsx — Pre-filled task creation from intervention data.
 * Teacher can edit before saving. Manual task creation unchanged.
 */
import { useState } from "react";
import { createTeacherTask } from "../../api/teacherDashboard";

const inp = { padding: "8px 10px", borderRadius: 7, border: "1px solid var(--border,#e5e7eb)", fontFamily: "inherit", fontSize: ".85rem", background: "var(--surface2,#f8fafc)", color: "var(--text,#1e293b)", width: "100%" };

function buildSuggestedTitle(intervention) {
  const name = intervention.student_name || "Student";
  const reasons = intervention.reasons || [];
  if (reasons.some(r => r.toLowerCase().includes("inactive"))) {
    const days = (reasons[0] || "").match(/\d+/)?.[0];
    return `Follow up with ${name}${days ? `: inactive for ${days} days` : ""}`;
  }
  if (reasons.some(r => r.toLowerCase().includes("mock test") || r.toLowerCase().includes("score"))) {
    return `Review ${name}'s mock test performance`;
  }
  if (reasons.some(r => r.toLowerCase().includes("invitation"))) {
    return `Contact parent for pending invitation (${name})`;
  }
  return `Follow up with ${name}`;
}

function buildSuggestedPriority(intervention) {
  return intervention.severity === "critical" ? "critical" : intervention.severity === "medium" ? "medium" : "low";
}

export default function SuggestedTaskModal({ intervention, onClose, onCreated }) {
  const [title, setTitle]           = useState(buildSuggestedTitle(intervention));
  const [description, setDescription] = useState((intervention.reasons || []).join(". "));
  const [priority, setPriority]     = useState(buildSuggestedPriority(intervention));
  const [loading, setLoading]       = useState(false);
  const [error, setError]           = useState(null);

  async function doSave(e) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    const d = await createTeacherTask({
      title: title.trim(),
      description: description.trim(),
      priority,
      student_id: intervention.student_id || null,
      source: "intervention",
    }).catch(e => ({ success: false, error: e.message }));
    setLoading(false);
    if (d.success) {
      onCreated && onCreated(d.task);
      onClose();
    } else {
      setError(d.error || "Failed to create task.");
    }
  }

  return (
    <div
      data-testid="suggested-task-modal"
      style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.4)", zIndex: 400, display: "flex", alignItems: "center", justifyContent: "center", padding: 16 }}>
      <div style={{ background: "var(--panel,#fff)", borderRadius: 12, padding: 20, width: "100%", maxWidth: 480, maxHeight: "90vh", overflowY: "auto", boxShadow: "0 8px 32px rgba(0,0,0,.2)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
          <h4 style={{ margin: 0 }}>✅ Create Task</h4>
          <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", fontSize: "1.1rem" }}>✕</button>
        </div>

        {intervention.student_name && (
          <div style={{ fontSize: ".78rem", background: "rgba(99,102,241,.08)", color: "#6366f1", padding: "4px 8px", borderRadius: 5, marginBottom: 12, display: "inline-block" }}>
            For: {intervention.student_name}
          </div>
        )}

        <form onSubmit={doSave} style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <label>
            <span style={{ fontSize: ".78rem", fontWeight: 600 }}>Title *</span>
            <input value={title} onChange={e => setTitle(e.target.value)} required style={{ ...inp, marginTop: 3 }} data-testid="suggested-task-title" />
          </label>
          <label>
            <span style={{ fontSize: ".78rem", fontWeight: 600 }}>Notes</span>
            <textarea value={description} onChange={e => setDescription(e.target.value)} rows={3} style={{ ...inp, marginTop: 3, resize: "vertical" }} />
          </label>
          <label>
            <span style={{ fontSize: ".78rem", fontWeight: 600 }}>Priority</span>
            <select value={priority} onChange={e => setPriority(e.target.value)} style={{ ...inp, marginTop: 3 }}>
              <option value="critical">🔴 Critical</option>
              <option value="medium">🟡 Medium</option>
              <option value="low">⚪ Low</option>
            </select>
          </label>
          {error && <div style={{ fontSize: ".82rem", color: "#dc2626" }}>⚠ {error}</div>}
          <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
            <button type="submit" disabled={loading} className="primary-btn">{loading ? "Saving…" : "Create Task"}</button>
            <button type="button" onClick={onClose} className="secondary-btn">Cancel</button>
          </div>
        </form>
      </div>
    </div>
  );
}
