/**
 * AdminSchoolOutreachPage.jsx — CBSE principal outreach campaign console.
 *
 * Browse/filter/select principals from the 28k+ school list (Supabase-backed
 * — see backend/app/services/school_outreach_service.py) and trigger sends:
 * the initial pitch, or the one-time 7-day reminder for non-responders.
 * Sending happens in a background thread server-side, so this page polls
 * the summary/list after a send rather than blocking on it.
 */
import { useEffect, useState, useCallback } from "react";
import { Send, RefreshCw, CheckCircle2, Mail } from "lucide-react";
import {
  getOutreachSummary,
  listOutreachPrincipals,
  sendOutreachEmails,
  markOutreachResponded,
  getOutreachStates,
} from "../api/schoolOutreach";

const PAGE_SIZE = 50;

const btnPrimary = {
  padding: "8px 16px", borderRadius: 8, border: "none", background: "#6366f1",
  color: "#fff", fontFamily: "inherit", fontSize: ".82rem", fontWeight: 700, cursor: "pointer",
};
const btnGhost = {
  padding: "7px 13px", borderRadius: 7, border: "1px solid var(--border,#e5e7eb)",
  background: "var(--panel,#fff)", fontFamily: "inherit", fontSize: ".78rem",
  cursor: "pointer", color: "var(--text,#374151)",
};
const inputStyle = {
  padding: "8px 12px", borderRadius: 8, border: "1px solid var(--border,#e5e7eb)",
  fontFamily: "inherit", fontSize: ".85rem", background: "var(--surface2,#f8fafc)",
  color: "var(--text,#1e293b)",
};
const thStyle = {
  textAlign: "left", fontSize: ".7rem", textTransform: "uppercase", letterSpacing: ".04em",
  color: "var(--text-muted,#8288a0)", fontWeight: 700, padding: "0 10px 8px", borderBottom: "1px solid var(--border,#e5e7eb)",
};
const tdStyle = { padding: "9px 10px", borderBottom: "1px solid var(--border-soft,#edeff4)", fontSize: ".82rem" };

function pill(bg, color, text) {
  return <span style={{ background: bg, color, borderRadius: 999, padding: "2px 9px", fontSize: ".7rem", fontWeight: 700 }}>{text}</span>;
}

function statusPill(status) {
  if (status === "sent") return pill("rgba(16,185,129,.12)", "#10b981", "Sent");
  if (status === "failed") return pill("rgba(220,38,38,.12)", "#dc2626", "Failed");
  return pill("var(--surface2,#f8fafc)", "var(--text-muted,#565b73)", "Pending");
}

export default function AdminSchoolOutreachPage() {
  const [summary, setSummary] = useState(null);
  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [statusFilter, setStatusFilter] = useState("");
  const [needsReminder, setNeedsReminder] = useState(false);
  const [query, setQuery] = useState("");
  const [stateFilter, setStateFilter] = useState("");
  const [states, setStates] = useState([]);
  const [selected, setSelected] = useState(() => new Set());
  const [sendType, setSendType] = useState("initial");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const loadSummary = useCallback(async () => {
    try {
      const res = await getOutreachSummary();
      setSummary(res.summary);
    } catch (err) {
      setError(err.message || "Couldn't load campaign summary.");
    }
  }, []);

  const loadPrincipals = useCallback(async () => {
    setLoading(true);
    try {
      const res = await listOutreachPrincipals({
        status: needsReminder ? "" : statusFilter,
        needsReminder,
        q: query,
        state: stateFilter,
        limit: PAGE_SIZE,
        offset,
      });
      setRows(res.principals || []);
      setTotal(res.total || 0);
    } catch (err) {
      setError(err.message || "Couldn't load the principal list.");
    } finally {
      setLoading(false);
    }
  }, [statusFilter, needsReminder, query, stateFilter, offset]);

  useEffect(() => { loadSummary(); }, [loadSummary]);
  useEffect(() => { loadPrincipals(); }, [loadPrincipals]);
  useEffect(() => {
    getOutreachStates()
      .then((res) => setStates(res.states || []))
      .catch(() => {});
  }, []);

  // Reminder view only makes sense for the reminder send type, and vice versa —
  // keep them in sync so a stray click can't queue the wrong template.
  useEffect(() => {
    setSendType(needsReminder ? "reminder" : "initial");
  }, [needsReminder]);

  function toggleRow(email) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(email)) next.delete(email); else next.add(email);
      return next;
    });
  }

  function clearSelection() {
    setSelected(new Set());
  }

  const pageAllSelected = rows.length > 0 && rows.every((r) => selected.has(r.email));

  function toggleSelectAllOnPage() {
    setSelected((prev) => {
      const next = new Set(prev);
      if (pageAllSelected) {
        rows.forEach((r) => next.delete(r.email));
      } else {
        rows.forEach((r) => next.add(r.email));
      }
      return next;
    });
  }

  async function handleSend() {
    if (selected.size === 0) return;
    const label = sendType === "reminder" ? "reminder" : "initial";
    if (!window.confirm(`Send the ${label} email to ${selected.size} principal(s)? This goes out to real inboxes.`)) return;

    setBusy(true);
    setMessage("");
    setError("");
    try {
      const res = await sendOutreachEmails([...selected], sendType);
      setMessage(res.message || `Queued ${res.queued} email(s).`);
      clearSelection();
      setTimeout(() => { loadSummary(); loadPrincipals(); }, 1500);
    } catch (err) {
      setError(err.message || "Couldn't queue the send.");
    } finally {
      setBusy(false);
    }
  }

  async function handleMarkResponded() {
    if (selected.size === 0) return;
    setBusy(true);
    setMessage("");
    setError("");
    try {
      const res = await markOutreachResponded([...selected]);
      setMessage(`Marked ${res.updated} principal(s) as responded — they'll be skipped for reminders.`);
      clearSelection();
      loadSummary();
      loadPrincipals();
    } catch (err) {
      setError(err.message || "Couldn't update response status.");
    } finally {
      setBusy(false);
    }
  }

  function refreshAll() {
    loadSummary();
    loadPrincipals();
  }

  const pageStart = total === 0 ? 0 : offset + 1;
  const pageEnd = Math.min(offset + PAGE_SIZE, total);

  return (
    <div className="premium-page" data-testid="admin-school-outreach-page">
      <section className="premium-section">
        <div className="premium-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 10 }}>
          <div>
            <p className="eyebrow">School Outreach</p>
            <h2>📧 CBSE Principal Campaign</h2>
            <p>Browse the list, select principals, and send the pitch or the 7-day reminder.</p>
          </div>
          <button type="button" style={btnGhost} onClick={refreshAll}>
            <RefreshCw size={14} style={{ verticalAlign: "middle", marginRight: 6 }} />Refresh
          </button>
        </div>
      </section>

      {message && <div className="info-box">{message}</div>}
      {error && <div className="error-box">{error}</div>}

      {summary && (
        <section className="premium-grid premium-grid-4 premium-parent-stats">
          <div className="premium-card">
            <div className="dashboard-stat-icon blue"><Mail size={20} /></div>
            <h3>{summary.total}</h3>
            <p>Total Principals</p>
          </div>
          <div className="premium-card">
            <div className="dashboard-stat-icon purple"><Send size={20} /></div>
            <h3>{summary.sent}</h3>
            <p>Emailed ({summary.sent_today} today)</p>
          </div>
          <div className="premium-card">
            <div className="dashboard-stat-icon green"><CheckCircle2 size={20} /></div>
            <h3>{summary.responded}</h3>
            <p>Responded</p>
          </div>
          <div className="premium-card">
            <div className="dashboard-stat-icon red"><RefreshCw size={20} /></div>
            <h3>{summary.reminders_sent}</h3>
            <p>Reminders Sent</p>
          </div>
        </section>
      )}

      <div className="premium-card">
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 14, alignItems: "center" }}>
          <select
            value={statusFilter}
            disabled={needsReminder}
            onChange={(e) => { setStatusFilter(e.target.value); setOffset(0); }}
            style={inputStyle}
          >
            <option value="">All statuses</option>
            <option value="pending">Pending</option>
            <option value="sent">Sent</option>
            <option value="failed">Failed</option>
          </select>

          <select
            value={stateFilter}
            onChange={(e) => { setStateFilter(e.target.value); setOffset(0); }}
            style={inputStyle}
          >
            <option value="">All states</option>
            {states.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>

          <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: ".82rem", cursor: "pointer" }}>
            <input
              type="checkbox"
              checked={needsReminder}
              onChange={(e) => { setNeedsReminder(e.target.checked); setOffset(0); }}
            />
            Needs reminder (sent 7+ days ago, no reply)
          </label>

          <input
            type="text"
            placeholder="Search name, school, or email"
            value={query}
            onChange={(e) => { setQuery(e.target.value); setOffset(0); }}
            style={{ ...inputStyle, flex: 1, minWidth: 200 }}
          />
        </div>

        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10, flexWrap: "wrap", gap: 10 }}>
          <div style={{ fontSize: ".8rem", color: "var(--text-muted,#8288a0)" }}>
            {selected.size} selected &middot; showing {pageStart}-{pageEnd} of {total}
          </div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button type="button" style={btnGhost} onClick={clearSelection} disabled={selected.size === 0}>Clear</button>
            <select value={sendType} onChange={(e) => setSendType(e.target.value)} style={{ ...inputStyle, padding: "7px 10px" }}>
              <option value="initial">Initial email</option>
              <option value="reminder">Reminder</option>
            </select>
            <button type="button" style={btnGhost} onClick={handleMarkResponded} disabled={busy || selected.size === 0}>
              Mark as Responded
            </button>
            <button type="button" style={btnPrimary} onClick={handleSend} disabled={busy || selected.size === 0}>
              <Send size={13} style={{ verticalAlign: "middle", marginRight: 6 }} />
              Send to Selected ({selected.size})
            </button>
          </div>
        </div>

        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th style={thStyle}>
                  <input
                    type="checkbox"
                    data-testid="select-all-page"
                    aria-label="Select all on page"
                    checked={pageAllSelected}
                    onChange={toggleSelectAllOnPage}
                  />
                </th>
                <th style={thStyle}>Principal</th>
                <th style={thStyle}>School</th>
                <th style={thStyle}>Email</th>
                <th style={thStyle}>Status</th>
                <th style={thStyle}>Sent</th>
                <th style={thStyle}>Reminder</th>
                <th style={thStyle}>Responded</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((p) => (
                <tr key={p.email}>
                  <td style={tdStyle}>
                    <input
                      type="checkbox"
                      aria-label={`Select ${p.email}`}
                      checked={selected.has(p.email)}
                      onChange={() => toggleRow(p.email)}
                    />
                  </td>
                  <td style={{ ...tdStyle, fontWeight: 700 }}>{p.principal_name || "—"}</td>
                  <td style={tdStyle}>{p.school_name}</td>
                  <td style={tdStyle}>{p.email}</td>
                  <td style={tdStyle}>{statusPill(p.status)}</td>
                  <td style={tdStyle}>{p.sent_at ? new Date(p.sent_at).toLocaleDateString() : "—"}</td>
                  <td style={tdStyle}>{p.reminder_sent_at ? new Date(p.reminder_sent_at).toLocaleDateString() : "—"}</td>
                  <td style={tdStyle}>{p.responded ? pill("rgba(16,185,129,.12)", "#10b981", "Yes") : "—"}</td>
                </tr>
              ))}
              {!loading && rows.length === 0 && (
                <tr><td style={tdStyle} colSpan={8}>No principals match these filters.</td></tr>
              )}
            </tbody>
          </table>
        </div>

        <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 12 }}>
          <button type="button" style={btnGhost} disabled={offset === 0} onClick={() => setOffset((o) => Math.max(0, o - PAGE_SIZE))}>
            Previous
          </button>
          <button type="button" style={btnGhost} disabled={pageEnd >= total} onClick={() => setOffset((o) => o + PAGE_SIZE)}>
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
