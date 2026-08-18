/**
 * AdminTechDebtPage.jsx -- Tech Debt Backlog
 * Cards sorted by criticality (server-sorted). Admin approves or rejects
 * each proposed item; rejecting requires a short reason.
 */
import { useCallback, useEffect, useState } from "react";
import { adminListTechDebt, adminTechDebtSummary, adminReviewTechDebt } from "../api/feedback";

const TIER_COLOR = { critical: "#ef4444", high: "#f97316", medium: "#f59e0b", low: "#94a3b8" };
const STATUS_COLOR = { proposed: "#6366f1", approved: "#22c55e", rejected: "#94a3b8", in_progress: "#0ea5e9", done: "#16a34a" };
const STATUS_LABEL = { proposed: "PROPOSED", approved: "APPROVED", rejected: "REJECTED", in_progress: "IN PROGRESS", done: "DONE" };

function Badge({ label, color }) {
  return <span style={{ fontSize: ".68rem", fontWeight: 800, padding: "3px 10px", borderRadius: 8, background: color + "20", color, letterSpacing: ".03em", whiteSpace: "nowrap" }}>{label}</span>;
}

function SCard({ label, value, color }) {
  return (
    <div style={{ background: "var(--panel,#fff)", border: "1px solid var(--border,#e5e7eb)", borderRadius: 10, padding: "14px 18px", flex: "1 1 150px", minWidth: 140 }}>
      <div style={{ fontWeight: 800, fontSize: "1.5rem", color }}>{value ?? 0}</div>
      <div style={{ fontSize: ".75rem", color: "#64748b", marginTop: 3 }}>{label}</div>
    </div>
  );
}

function TechDebtCard({ item, onReview }) {
  const [rejecting, setRejecting] = useState(false);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);

  async function approve() {
    setBusy(true);
    try { await onReview(item.id, { status: "approved" }); } finally { setBusy(false); }
  }
  async function confirmReject() {
    if (!reason.trim()) return;
    setBusy(true);
    try { await onReview(item.id, { status: "rejected", rejection_reason: reason.trim() }); setRejecting(false); setReason(""); } finally { setBusy(false); }
  }

  const sourceCount = (item.source_feedback_ids || []).length;

  return (
    <div data-testid="tech-debt-card" style={{ background: "#fff", border: "1px solid var(--border,#dde2f0)", borderRadius: 12, padding: "16px 20px", marginBottom: 12 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 10 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <Badge label={(item.criticality_tier || "low").toUpperCase()} color={TIER_COLOR[item.criticality_tier] || "#94a3b8"} />
          <span style={{ fontWeight: 700, fontSize: ".94rem", color: "#0f172a" }}>{item.title}</span>
        </div>
        <Badge label={STATUS_LABEL[item.status] || item.status} color={STATUS_COLOR[item.status] || "#94a3b8"} />
      </div>

      <div style={{ fontSize: ".78rem", color: "#94a3b8", margin: "10px 0 14px" }}>
        🔗 {sourceCount} source{sourceCount === 1 ? "" : "s"}
        {item.description ? ` · ${item.description}` : ""}
        {" · "}Reported {item.created_at ? new Date(item.created_at).toLocaleDateString() : "—"}
      </div>

      {item.status === "proposed" && !rejecting && (
        <div style={{ display: "flex", gap: 8 }}>
          <button onClick={approve} disabled={busy} data-testid={"approve-" + item.id}
            style={{ border: "none", borderRadius: 7, padding: "8px 16px", fontSize: ".8rem", fontWeight: 700, background: busy ? "#94a3b8" : "#22c55e", color: "#fff", cursor: busy ? "not-allowed" : "pointer", fontFamily: "inherit" }}>
            ✓ Approve
          </button>
          <button onClick={() => setRejecting(true)} disabled={busy} data-testid={"reject-" + item.id}
            style={{ background: "transparent", border: "1px solid #dc2626", color: "#dc2626", borderRadius: 7, padding: "8px 16px", fontSize: ".8rem", fontWeight: 700, cursor: "pointer", fontFamily: "inherit" }}>
            ✕ Reject
          </button>
        </div>
      )}

      {item.status === "proposed" && rejecting && (
        <div>
          <div style={{ fontSize: ".74rem", fontWeight: 600, color: "#0f172a", marginBottom: 6 }}>
            Why are you rejecting this? <span style={{ color: "#94a3b8", fontWeight: 400 }}>(visible to the reporting admin)</span>
          </div>
          <textarea data-testid={"reject-reason-" + item.id} value={reason} onChange={e => setReason(e.target.value)} rows={2}
            placeholder="Type a reason…"
            style={{ width: "100%", border: "1px solid #dde2f0", borderRadius: 8, padding: "9px 11px", fontSize: ".8rem", background: "#f8fafc", marginBottom: 10, fontFamily: "inherit", boxSizing: "border-box", resize: "vertical" }} />
          <div style={{ display: "flex", gap: 8 }}>
            <button onClick={confirmReject} disabled={busy || !reason.trim()} data-testid={"confirm-reject-" + item.id}
              style={{ background: busy || !reason.trim() ? "#94a3b8" : "#dc2626", color: "#fff", border: "none", borderRadius: 7, padding: "8px 16px", fontSize: ".8rem", fontWeight: 700, cursor: busy || !reason.trim() ? "not-allowed" : "pointer", fontFamily: "inherit" }}>
              Confirm Reject
            </button>
            <button onClick={() => { setRejecting(false); setReason(""); }} style={{ background: "transparent", border: "1px solid #dde2f0", color: "#475569", borderRadius: 7, padding: "8px 16px", fontSize: ".8rem", fontWeight: 700, cursor: "pointer", fontFamily: "inherit" }}>
              Cancel
            </button>
          </div>
        </div>
      )}

      {item.status === "approved" && (
        <div style={{ background: "rgba(34,197,94,.08)", border: "1px solid rgba(34,197,94,.25)", color: "#16a34a", borderRadius: 8, padding: "8px 12px", fontSize: ".78rem", fontWeight: 600, display: "inline-block" }}>
          ✓ Approved{item.reviewed_at ? ` · ${new Date(item.reviewed_at).toLocaleDateString()}` : ""}
        </div>
      )}
      {item.status === "rejected" && (
        <div style={{ background: "rgba(148,163,184,.12)", border: "1px solid #dde2f0", color: "#64748b", borderRadius: 8, padding: "8px 12px", fontSize: ".78rem", display: "inline-block" }}>
          ✕ Rejected — <span style={{ fontStyle: "italic" }}>"{item.rejection_reason}"</span>
        </div>
      )}
      {item.status === "in_progress" && (
        <div style={{ background: "rgba(14,165,233,.08)", border: "1px solid rgba(14,165,233,.25)", color: "#0284c7", borderRadius: 8, padding: "8px 12px", fontSize: ".78rem", fontWeight: 600, display: "inline-block" }}>
          🔧 In progress — assigned to engineering
        </div>
      )}
    </div>
  );
}

export default function AdminTechDebtPage({ user: _user }) {
  const [summary, setSummary] = useState(null);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState("");
  const [msg, setMsg] = useState(null);

  const loadSummary = useCallback(async () => { try { const r = await adminTechDebtSummary(); if (r.success) setSummary(r); } catch { setSummary(null); } }, []);
  const loadItems = useCallback(async () => {
    setLoading(true);
    try { const r = await adminListTechDebt(status ? { status } : {}); if (r.success) setItems(r.tech_debt || []); } catch { setItems([]); } finally { setLoading(false); }
  }, [status]);
  useEffect(() => { loadSummary(); }, [loadSummary]);
  useEffect(() => { loadItems(); }, [loadItems]);

  async function handleReview(id, body) {
    setMsg(null);
    try {
      const r = await adminReviewTechDebt(id, body);
      if (r.success) {
        setItems(prev => prev.map(it => it.id === id ? r.tech_debt : it));
        loadSummary();
      }
    } catch (e) { setMsg("Error: " + e.message); }
  }

  const sel = { background: "var(--panel,#fff)", padding: "7px 10px", borderRadius: 7, border: "1px solid var(--border,#e5e7eb)", fontFamily: "inherit", fontSize: ".8rem" };

  return (
    <div data-testid="admin-tech-debt-page" style={{ maxWidth: 1100, margin: "0 auto", padding: "0 0 60px" }}>
      <div style={{ marginBottom: 20 }}>
        <h2 style={{ fontWeight: 800, fontSize: "1.2rem", margin: "0 0 3px" }}>🛠️ Tech Debt Backlog</h2>
        <div style={{ fontSize: ".85rem", color: "#64748b" }}>Assimilated from user feedback and bug reports. Sorted by criticality — approve to add to the engineering backlog.</div>
      </div>

      {summary && (
        <div data-testid="tech-debt-summary-cards" style={{ display: "flex", flexWrap: "wrap", gap: 10, marginBottom: 24 }}>
          <SCard label="Proposed" value={summary.proposed} color="#6366f1" />
          <SCard label="Approved" value={summary.approved} color="#22c55e" />
          <SCard label="In Progress" value={summary.in_progress} color="#0ea5e9" />
          <SCard label="Rejected" value={summary.rejected} color="#94a3b8" />
        </div>
      )}

      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        <select value={status} style={sel} data-testid="filter-status" onChange={e => setStatus(e.target.value)}>
          <option value="">All statuses</option>
          {["proposed", "approved", "rejected", "in_progress", "done"].map(s => <option key={s} value={s}>{STATUS_LABEL[s]}</option>)}
        </select>
      </div>

      {msg && <div style={{ marginBottom: 10, fontSize: ".8rem", color: "#dc2626" }}>{msg}</div>}

      {loading ? (
        <div style={{ textAlign: "center", padding: 40, color: "#94a3b8" }}>Loading…</div>
      ) : items.length === 0 ? (
        <div data-testid="no-tech-debt" style={{ textAlign: "center", padding: 40 }}>
          <div style={{ fontSize: "2rem" }}>✅</div>
          <p style={{ fontWeight: 600 }}>No tech debt items yet.</p>
        </div>
      ) : (
        items.map(item => <TechDebtCard key={item.id} item={item} onReview={handleReview} />)
      )}
    </div>
  );
}
