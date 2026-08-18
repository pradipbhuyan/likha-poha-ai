/**
 * AdminFeedbackPage.jsx -- User Feedback Triage
 * Lists feedback sorted by criticality. Admins select one or more related
 * items and bundle them into a tech debt backlog entry for approval.
 */
import { useCallback, useEffect, useState } from "react";
import {
  adminListFeedback, adminFeedbackSummary, adminUpdateFeedback, adminCreateTechDebt,
} from "../api/feedback";

const TC = { critical: "#ef4444", high: "#f97316", medium: "#f59e0b", low: "#94a3b8" };
const TYPE_LABELS = { bug: "🐛 Bug", feature_request: "💡 Feature", content_suggestion: "📚 Content", praise: "🌟 Praise", other: "💬 Other" };
const CLOSED = new Set(["converted", "dismissed"]);

function Badge({ label, color }) {
  return <span style={{ fontSize: ".68rem", fontWeight: 700, padding: "2px 8px", borderRadius: 8, background: color + "20", color }}>{label}</span>;
}

function SCard({ label, value, color, testid }) {
  return (
    <div data-testid={testid} style={{ background: "var(--panel,#fff)", border: "1px solid var(--border,#e5e7eb)", borderRadius: 10, padding: "14px 18px", flex: "1 1 150px", minWidth: 140 }}>
      <div style={{ fontWeight: 800, fontSize: "1.5rem", color: color || "#6366f1" }}>{value ?? 0}</div>
      <div style={{ fontSize: ".75rem", color: "#64748b", marginTop: 3 }}>{label}</div>
    </div>
  );
}

function ConvertPanel({ count, onCancel, onConfirm, busy }) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const inp = { width: "100%", padding: "8px 10px", borderRadius: 7, border: "1px solid var(--border,#e5e7eb)", fontFamily: "inherit", fontSize: ".82rem", boxSizing: "border-box" };
  return (
    <div data-testid="convert-panel" style={{ background: "#f0f0ff", border: "1px solid rgba(99,102,241,.25)", borderRadius: 10, padding: 14, marginBottom: 12 }}>
      <div style={{ fontWeight: 700, fontSize: ".85rem", marginBottom: 8 }}>⚡ Convert {count} feedback item{count > 1 ? "s" : ""} to Tech Debt</div>
      <label style={{ fontSize: ".76rem", fontWeight: 600, display: "block", marginBottom: 4 }}>Title</label>
      <input data-testid="convert-title-input" value={title} onChange={e => setTitle(e.target.value)} placeholder="Short summary for the backlog item" style={{ ...inp, marginBottom: 8 }} />
      <label style={{ fontSize: ".76rem", fontWeight: 600, display: "block", marginBottom: 4 }}>Description (optional)</label>
      <textarea data-testid="convert-description-input" value={description} onChange={e => setDescription(e.target.value)} rows={3} style={{ ...inp, marginBottom: 10, resize: "vertical" }} />
      <div style={{ display: "flex", gap: 8 }}>
        <button data-testid="convert-confirm-btn" disabled={busy || !title.trim()} onClick={() => onConfirm(title.trim(), description.trim())}
          style={{ padding: "7px 16px", borderRadius: 7, border: "none", background: busy || !title.trim() ? "#94a3b8" : "#4f46e5", color: "#fff", fontWeight: 700, fontSize: ".78rem", cursor: busy || !title.trim() ? "not-allowed" : "pointer", fontFamily: "inherit" }}>
          {busy ? "Creating…" : "Create Tech Debt Item"}
        </button>
        <button onClick={onCancel} style={{ padding: "7px 14px", borderRadius: 7, border: "none", background: "none", color: "#64748b", fontSize: ".78rem", cursor: "pointer", fontFamily: "inherit" }}>Cancel</button>
      </div>
    </div>
  );
}

export default function AdminFeedbackPage({ user: _user }) {
  const [summary, setSummary] = useState(null);
  const [feedback, setFeedback] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({ status: "", feedback_type: "", criticality_tier: "" });
  const [hideClosed, setHideClosed] = useState(true);
  const [selected, setSelected] = useState(new Set());
  const [showConvert, setShowConvert] = useState(false);
  const [converting, setConverting] = useState(false);
  const [msg, setMsg] = useState(null);

  const loadSummary = useCallback(async () => { try { const r = await adminFeedbackSummary(); if (r.success) setSummary(r); } catch { setSummary(null); } }, []);
  const loadFeedback = useCallback(async () => {
    setLoading(true);
    try { const r = await adminListFeedback(filters); if (r.success) setFeedback(r.feedback || []); } catch { setFeedback([]); } finally { setLoading(false); }
  }, [filters]);
  useEffect(() => { loadSummary(); }, [loadSummary]);
  useEffect(() => { loadFeedback(); }, [loadFeedback]);

  const visible = hideClosed ? feedback.filter(f => !CLOSED.has(f.status)) : feedback;

  function toggleSelect(id) { setSelected(prev => { const n = new Set(prev); if (n.has(id)) n.delete(id); else n.add(id); return n; }); }
  function clearSelect() { setSelected(new Set()); setShowConvert(false); }

  async function dismiss(id) {
    try {
      const r = await adminUpdateFeedback(id, { status: "dismissed" });
      if (r.success) { setFeedback(prev => prev.map(f => f.id === id ? r.feedback : f)); loadSummary(); }
    } catch (e) { setMsg("Error: " + e.message); }
  }

  async function convertToTechDebt(title, description) {
    setConverting(true); setMsg(null);
    try {
      const r = await adminCreateTechDebt({ title, description, source_feedback_ids: [...selected] });
      if (r.success) {
        setMsg("✅ Tech debt item created — pending approval.");
        clearSelect();
        loadFeedback(); loadSummary();
      }
    } catch (e) { setMsg("Error: " + e.message); }
    finally { setConverting(false); }
  }

  const sel = { background: "var(--panel,#fff)", padding: "7px 10px", borderRadius: 7, border: "1px solid var(--border,#e5e7eb)", fontFamily: "inherit", fontSize: ".8rem" };

  return (
    <div data-testid="admin-feedback-page" style={{ maxWidth: 1100, margin: "0 auto", padding: "0 0 60px" }}>
      <div style={{ marginBottom: 20 }}>
        <h2 style={{ fontWeight: 800, fontSize: "1.2rem", margin: "0 0 3px" }}>💬 User Feedback</h2>
        <div style={{ fontSize: ".85rem", color: "#64748b" }}>Feedback and suggestions submitted by students, parents and teachers.</div>
      </div>

      {summary && (
        <div data-testid="feedback-summary-cards" style={{ display: "flex", flexWrap: "wrap", gap: 10, marginBottom: 24 }}>
          <SCard label="Open" value={summary.open} color="#6366f1" testid="stat-open" />
          <SCard label="Critical" value={summary.critical} color="#ef4444" testid="stat-critical" />
          <SCard label="This Week" value={summary.this_week} color="#0ea5e9" testid="stat-week" />
          <SCard label="Converted to Tech Debt" value={summary.converted} color="#7c3aed" testid="stat-converted" />
        </div>
      )}

      <div data-testid="feedback-filters" style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 12, alignItems: "center" }}>
        <select value={filters.feedback_type} style={sel} data-testid="filter-type" onChange={e => setFilters(p => ({ ...p, feedback_type: e.target.value }))}>
          <option value="">Type</option>
          {Object.entries(TYPE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <select value={filters.criticality_tier} style={sel} data-testid="filter-tier" onChange={e => setFilters(p => ({ ...p, criticality_tier: e.target.value }))}>
          <option value="">Criticality</option>
          {["critical", "high", "medium", "low"].map(t => <option key={t} value={t}>{t}</option>)}
        </select>
        <button onClick={() => setFilters({ status: "", feedback_type: "", criticality_tier: "" })} style={{ ...sel, cursor: "pointer", color: "#6366f1", fontWeight: 600 }}>Clear</button>
        <button data-testid="hide-closed-toggle" onClick={() => setHideClosed(p => !p)}
          style={{ ...sel, cursor: "pointer", fontWeight: 700, color: hideClosed ? "#22c55e" : "#94a3b8", borderColor: hideClosed ? "#22c55e" : "#e5e7eb" }}>
          {hideClosed ? "✓ Hiding Closed" : "Show All"}
        </button>
      </div>

      {selected.size > 0 && !showConvert && (
        <div data-testid="bulk-toolbar" style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center", marginBottom: 12, padding: "10px 14px", background: "#f0f0ff", borderRadius: 10, border: "1px solid rgba(99,102,241,.2)" }}>
          <span style={{ fontWeight: 700, fontSize: ".82rem", color: "#6366f1" }}>{selected.size} selected</span>
          <button onClick={() => setShowConvert(true)} data-testid="open-convert-btn"
            style={{ padding: "6px 14px", borderRadius: 7, border: "none", background: "#4f46e5", color: "#fff", fontWeight: 700, fontSize: ".78rem", cursor: "pointer", fontFamily: "inherit" }}>
            ⚡ Convert to Tech Debt
          </button>
          <button onClick={clearSelect} style={{ padding: "6px 10px", borderRadius: 7, border: "none", background: "none", color: "#94a3b8", fontSize: ".78rem", cursor: "pointer" }}>Deselect All</button>
        </div>
      )}
      {showConvert && <ConvertPanel count={selected.size} busy={converting} onCancel={() => setShowConvert(false)} onConfirm={convertToTechDebt} />}
      {msg && <div style={{ marginBottom: 10, fontSize: ".8rem", color: msg.startsWith("Error") ? "#dc2626" : "#22c55e" }}>{msg}</div>}

      {loading ? (
        <div style={{ textAlign: "center", padding: 40, color: "#94a3b8" }}>Loading…</div>
      ) : visible.length === 0 ? (
        <div data-testid="no-feedback" style={{ textAlign: "center", padding: 40 }}>
          <div style={{ fontSize: "2rem" }}>✅</div>
          <p style={{ fontWeight: 600 }}>No feedback found matching filters.</p>
        </div>
      ) : (
        <div style={{ border: "1px solid var(--border,#e5e7eb)", borderRadius: 10, overflow: "hidden" }}>
          <div style={{ display: "grid", gridTemplateColumns: "36px 100px 1fr 100px 130px 90px 100px", background: "var(--surface2,#f8fafc)", padding: "8px 14px", fontSize: ".72rem", fontWeight: 700, color: "#64748b", textTransform: "uppercase", letterSpacing: ".04em", alignItems: "center" }}>
            <input type="checkbox" checked={selected.size === visible.length && visible.length > 0}
              onChange={e => setSelected(e.target.checked ? new Set(visible.map(f => f.id)) : new Set())} style={{ cursor: "pointer" }} />
            <span>Type</span><span>Message</span><span>Criticality</span><span>Reporter</span><span>Date</span><span>Action</span>
          </div>
          {visible.map(f => (
            <div key={f.id} data-testid="feedback-row" style={{ display: "grid", gridTemplateColumns: "36px 100px 1fr 100px 130px 90px 100px", padding: "10px 14px", borderTop: "1px solid var(--border,#f1f5f9)", alignItems: "center" }}>
              <input type="checkbox" checked={selected.has(f.id)} onChange={() => toggleSelect(f.id)} style={{ cursor: "pointer" }} />
              <span style={{ fontSize: ".78rem" }}>{TYPE_LABELS[f.feedback_type] || f.feedback_type}</span>
              <span style={{ fontSize: ".78rem", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", paddingRight: 10 }}>{f.message}</span>
              <span><Badge label={(f.criticality_tier || "low").toUpperCase()} color={TC[f.criticality_tier] || "#94a3b8"} /></span>
              <span style={{ fontSize: ".78rem", color: "#475569" }}>{f.username || "—"} <span style={{ color: "#94a3b8" }}>· {f.user_role || "user"}</span></span>
              <span style={{ fontSize: ".72rem", color: "#94a3b8" }}>{f.created_at ? new Date(f.created_at).toLocaleDateString() : "—"}</span>
              {CLOSED.has(f.status) ? (
                <span style={{ fontSize: ".72rem", color: "#94a3b8" }}>{f.status}</span>
              ) : (
                <button onClick={() => dismiss(f.id)} data-testid={"dismiss-" + f.id}
                  style={{ padding: "4px 10px", borderRadius: 6, border: "1px solid var(--border,#e5e7eb)", background: "transparent", color: "#64748b", fontWeight: 600, fontSize: ".7rem", cursor: "pointer", fontFamily: "inherit" }}>
                  Dismiss
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
