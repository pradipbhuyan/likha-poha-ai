import { useEffect, useState } from "react";
import { getLeadClaims, getAdminCommissionSummary, batchPayCommissions, manualConfirmClaim } from "../api/sales";
import SalesLeadForm from "../components/SalesLeadForm";

const SC = {
  claimed:   { c:"#ef4444", bg:"rgba(239,68,68,.10)",   b:"rgba(239,68,68,.30)",   i:"🔴", l:"Awaiting Payment" },
  confirmed: { c:"#22c55e", bg:"rgba(34,197,94,.10)",   b:"rgba(34,197,94,.30)",   i:"🟢", l:"Payment Confirmed" },
  paid:      { c:"#3b82f6", bg:"rgba(59,130,246,.10)",  b:"rgba(59,130,246,.30)",  i:"🔵", l:"Commission Paid" },
  expired:   { c:"#6b7280", bg:"rgba(107,114,128,.10)", b:"rgba(107,114,128,.25)", i:"⛔", l:"Expired" },
};
const fmt = v => new Intl.NumberFormat("en-IN",{style:"currency",currency:"INR",maximumFractionDigits:0}).format(Number(v||0));
const ago = d => { if(!d) return ""; const n=Math.floor((Date.now()-new Date(d).getTime())/86400000); return n===0?"today":n===1?"1 day ago":`${n} days ago`; };
const left = ms => Math.max(0,Math.ceil((ms-Date.now())/86400000));

function Banner({ bg, bd, color, children }) {
  return <div style={{background:bg,border:`1px solid ${bd}`,borderRadius:10,padding:"10px 14px",marginBottom:10,fontSize:".87rem",color}}>{children}</div>;
}

export default function SalesLeadPage({ user }) {
  const isAdmin = user?.role === "admin";
  const [claims, setClaims] = useState([]);
  const [summary, setSummary] = useState(null);
  const [adminSummary, setAdminSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");
  const [paying, setPaying] = useState(false);
  const [confirmingId, setConfirmingId] = useState(null); // claim being manually confirmed
  const [confirmForm, setConfirmForm] = useState({ package_amount: "", package_key: "starter", admin_notes: "" });
  const [confirmErr, setConfirmErr] = useState("");

  async function load() {
    setLoading(true); setError("");
    try {
      const d = await getLeadClaims();
      setClaims(d.claims || []);
      if (d.summary) setSummary(d.summary);
      if (isAdmin) {
        const a = await getAdminCommissionSummary();
        setAdminSummary(a);
      }
    } catch (e) { setError(e.message || "Failed to load."); }
    finally { setLoading(false); }
  }

  useEffect(() => { load(); }, []);

  async function manualConfirm(claim) {
    const amt = parseInt(confirmForm.package_amount);
    if (!amt || amt <= 0) { setConfirmErr("Enter a valid payment amount (₹)."); return; }
    try {
      await manualConfirmClaim(claim.id, {
        package_amount: amt,
        package_key: confirmForm.package_key || claim.package_key || "starter",
        admin_notes: confirmForm.admin_notes,
      });
      setConfirmingId(null);
      setConfirmForm({ package_amount: "", package_key: "starter", admin_notes: "" });
      setConfirmErr("");
      setMsg("✅ Claim manually confirmed. Commission calculated.");
      await load();
    } catch (e) { setConfirmErr(e.message || "Failed."); }
  }

  async function pay(ids) {
    if (!ids.length || !window.confirm(`Mark ${ids.length} commission(s) as paid?`)) return;
    setPaying(true);
    try {
      const r = await batchPayCommissions(ids);
      setMsg(r.message || "Done.");
      await load();
    } catch (e) { setError(e.message || "Failed."); }
    finally { setPaying(false); }
  }

  const confirmed = claims.filter(c => c.status === "confirmed");
  const pending   = claims.filter(c => c.status === "claimed");

  function exportToCSV() {
    const headers = [
      "Salesperson","Student Name","Student Email","Phone","Grade","Package",
      "Amount (₹)","Incentive %","Commission (₹)","Status",
      "Claimed Date","Confirmed Date","Paid Date","Admin Notes",
    ];
    const rows = claims.map(c => [
      isAdmin ? (c.salesperson?.username || c.sales_person_id || "") : (user?.username || ""),
      c.student_name || "",
      c.student_email || "",
      c.student_phone || "",
      c.grade || "",
      c.package_key || "",
      c.package_amount || 0,
      c.incentive_percent || 5,
      c.commission_amount || 0,
      c.status || "",
      c.claimed_at   ? c.claimed_at.slice(0, 10)   : "",
      c.confirmed_at ? c.confirmed_at.slice(0, 10) : "",
      c.paid_at      ? c.paid_at.slice(0, 10)      : "",
      (c.admin_notes || "").replace(/,/g, ";"),
    ]);

    const csv = [headers, ...rows]
      .map(row => row.map(v => `"${String(v).replace(/"/g, '""')}"`).join(","))
      .join("\r\n");

    const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `lead_claims_${new Date().toISOString().slice(0,10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div style={{ color: "#f8fafc", minHeight: "100vh" }}>
      <div style={{ maxWidth: 1100, margin: "0 auto", padding: "32px 20px" }}>

        {/* Header */}
        <div style={{ marginBottom: 24 }}>
          <p style={{ color: "#6366f1", fontWeight: 700, fontSize: ".78rem", letterSpacing: ".1em", textTransform: "uppercase", marginBottom: 6 }}>Sales Dashboard</p>
          <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", flexWrap: "wrap", gap: 10 }}>
            <div>
              <h2 style={{ fontSize: "1.8rem", fontWeight: 900, margin: 0 }}>
                {isAdmin ? "💰 Commission Overview" : "🤝 My Lead Claims"}
              </h2>
              <p style={{ color: "#64748b", marginTop: 5 }}>
                {isAdmin ? "All salespeople leads, conversions, and monthly payouts." : "Submit student leads and track commissions in real time."}
              </p>
            </div>
            {claims.length > 0 && (
              <button onClick={exportToCSV}
                style={{ background: "rgba(34,197,94,.12)", color: "#86efac", border: "1px solid rgba(34,197,94,.3)", borderRadius: 8, padding: "8px 16px", fontSize: ".85rem", fontWeight: 700, cursor: "pointer", fontFamily: "inherit", whiteSpace: "nowrap", alignSelf: "flex-start" }}>
                📥 Export to Excel
              </button>
            )}
          </div>
        </div>

        {/* Notifications */}
        {pending.length > 0 && <Banner bg="rgba(251,191,36,.08)" bd="rgba(251,191,36,.3)" color="#fbbf24">⚠️ {pending.length} lead{pending.length > 1 ? "s are" : " is"} awaiting payment</Banner>}
        {!isAdmin && summary?.commission_pending > 0 && <Banner bg="rgba(251,191,36,.08)" bd="rgba(251,191,36,.3)" color="#fbbf24">💰 {fmt(summary.commission_pending)} commission pending payout</Banner>}
        {msg   && <Banner bg="rgba(34,197,94,.1)"  bd="rgba(34,197,94,.3)"  color="#86efac">{msg}</Banner>}
        {error && <Banner bg="rgba(239,68,68,.1)"  bd="rgba(239,68,68,.3)"  color="#fca5a5">{error}</Banner>}

        {/* Stats strip — sales person */}
        {!isAdmin && summary && (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(140px,1fr))", gap: 12, marginBottom: 26 }}>
            {[
              { l: "Total Leads",      v: summary.total,                            c: "#94a3b8" },
              { l: "Awaiting Payment", v: summary.claimed,                          c: "#ef4444" },
              { l: "Confirmed",        v: summary.confirmed,                        c: "#22c55e" },
              { l: "Commission Paid",  v: fmt(summary.total_commission_paid),       c: "#3b82f6" },
              { l: "Pending Payout",   v: fmt(summary.commission_pending),          c: "#f59e0b" },
            ].map(s => (
              <div key={s.l} style={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 12, padding: "13px 15px" }}>
                <div style={{ fontSize: "1.25rem", fontWeight: 900, color: s.c }}>{s.v}</div>
                <div style={{ fontSize: ".74rem", color: "#64748b", marginTop: 3 }}>{s.l}</div>
              </div>
            ))}
          </div>
        )}

        {/* Admin: per-salesperson payout summary */}
        {isAdmin && adminSummary && (
          <div style={{ marginBottom: 26 }}>
            <div style={{ background: "rgba(34,197,94,.08)", border: "1px solid rgba(34,197,94,.25)", borderRadius: 12, padding: "13px 18px", marginBottom: 14, display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 10 }}>
              <span style={{ color: "#86efac", fontWeight: 700 }}>Total pending payout: {fmt(adminSummary.total_confirmed_payable)}</span>
              {confirmed.length > 0 && (
                <button onClick={() => pay(confirmed.map(c => c.id))} disabled={paying}
                  style={{ background: "linear-gradient(135deg,#059669,#0d9488)", color: "#fff", border: "none", borderRadius: 8, padding: "7px 18px", fontWeight: 700, cursor: "pointer", fontFamily: "inherit", fontSize: ".87rem" }}>
                  {paying ? "…" : `✅ Pay All ${confirmed.length} Commission${confirmed.length > 1 ? "s" : ""}`}
                </button>
              )}
            </div>
            {(adminSummary.salespeople || []).map(sp => (
              <div key={sp.sales_person_id} style={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 11, padding: "12px 18px", marginBottom: 9, display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 10 }}>
                <div>
                  <strong>{sp.username}</strong>
                  <span style={{ color: "#64748b", fontSize: ".8rem", marginLeft: 8 }}>{sp.email}</span>
                </div>
                <div style={{ display: "flex", gap: 18, fontSize: ".84rem" }}>
                  <span>🟢 <strong style={{ color: "#22c55e" }}>{fmt(sp.confirmed_amount)}</strong></span>
                  <span>🔵 <strong style={{ color: "#3b82f6" }}>{fmt(sp.paid_amount)}</strong></span>
                  {sp.confirmed_count > 0 && (
                    <button onClick={() => pay(sp.confirmed_claim_ids)} disabled={paying}
                      style={{ background: "rgba(34,197,94,.15)", color: "#86efac", border: "1px solid rgba(34,197,94,.3)", borderRadius: 6, padding: "3px 10px", cursor: "pointer", fontFamily: "inherit", fontSize: ".78rem", fontWeight: 700 }}>
                      Pay {sp.confirmed_count}
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Claims list + submit form */}
        <div style={{ display: "grid", gridTemplateColumns: isAdmin ? "1fr" : "1fr 330px", gap: 22, alignItems: "start" }}>

          {/* Claims */}
          <div>
            <h3 style={{ fontSize: "1rem", fontWeight: 700, marginBottom: 12, color: "#94a3b8" }}>
              {isAdmin ? `All Lead Claims (${claims.length})` : `My Claims (${claims.length})`}
            </h3>

            {loading ? (
              <p style={{ color: "#64748b" }}>Loading…</p>
            ) : claims.length === 0 ? (
              <div style={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 13, padding: 28, textAlign: "center", color: "#475569" }}>
                No leads yet.{!isAdmin && " Use the form → to submit your first lead."}
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {claims.map(claim => {
                  const s = SC[claim.status] || SC.claimed;
                  const exp = claim.status === "claimed"
                    ? left(new Date(claim.claimed_at).getTime() + 30 * 86400000)
                    : 0;
                  return (
                    <div key={claim.id} style={{ background: s.bg, border: `1px solid ${s.b}`, borderRadius: 11, padding: "13px 16px", opacity: claim.status === "expired" ? 0.5 : 1 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", gap: 10, flexWrap: "wrap" }}>
                        <div style={{ flex: 1, minWidth: 160 }}>
                          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 3 }}>
                            <span>{s.i}</span>
                            <strong style={{ color: "#f1f5f9" }}>{claim.student_name || claim.student_email}</strong>
                            <span style={{ fontSize: ".68rem", fontWeight: 700, padding: "2px 6px", borderRadius: 99, background: s.bg, border: `1px solid ${s.b}`, color: s.c }}>{s.l}</span>
                          </div>
                          <div style={{ fontSize: ".79rem", color: "#94a3b8" }}>
                            {claim.student_email}{claim.grade ? ` · ${claim.grade}` : ""}{claim.student_phone ? ` · ${claim.student_phone}` : ""}
                          </div>
                          {isAdmin && claim.salesperson?.username && (
                            <div style={{ fontSize: ".73rem", color: "#64748b", marginTop: 3 }}>Sales: {claim.salesperson.username}</div>
                          )}
                          {/* Admin manual confirm for offline payments */}
                          {isAdmin && claim.status === "claimed" && (
                            <div style={{ marginTop: 8 }}>
                              {confirmingId === claim.id ? (
                                <div style={{ background: "rgba(251,191,36,.06)", border: "1px solid rgba(251,191,36,.2)", borderRadius: 8, padding: "10px 12px", display: "flex", flexDirection: "column", gap: 7 }}>
                                  <div style={{ fontSize: ".75rem", color: "#fbbf24", fontWeight: 700 }}>💵 Manual Confirmation (Offline Payment)</div>
                                  <input type="number" min="1" placeholder="Amount collected ₹" value={confirmForm.package_amount}
                                    onChange={e => setConfirmForm(p => ({ ...p, package_amount: e.target.value }))}
                                    style={{ background: "#111827", border: "1px solid #334155", borderRadius: 6, padding: "6px 10px", color: "#f8fafc", fontSize: ".82rem", fontFamily: "inherit" }} />
                                  <input type="text" placeholder="Notes: cash/UPI ref/bank transfer" value={confirmForm.admin_notes}
                                    onChange={e => setConfirmForm(p => ({ ...p, admin_notes: e.target.value }))}
                                    style={{ background: "#111827", border: "1px solid #334155", borderRadius: 6, padding: "6px 10px", color: "#f8fafc", fontSize: ".82rem", fontFamily: "inherit" }} />
                                  {confirmErr && <div style={{ fontSize: ".75rem", color: "#fca5a5" }}>{confirmErr}</div>}
                                  <div style={{ display: "flex", gap: 7 }}>
                                    <button onClick={() => manualConfirm(claim)} style={{ background: "#059669", color: "#fff", border: "none", borderRadius: 6, padding: "5px 12px", fontSize: ".78rem", fontWeight: 700, cursor: "pointer", fontFamily: "inherit" }}>Confirm</button>
                                    <button onClick={() => { setConfirmingId(null); setConfirmErr(""); }} style={{ background: "transparent", color: "#64748b", border: "1px solid #334155", borderRadius: 6, padding: "5px 10px", fontSize: ".78rem", cursor: "pointer", fontFamily: "inherit" }}>Cancel</button>
                                  </div>
                                </div>
                              ) : (
                                <button onClick={() => { setConfirmingId(claim.id); setConfirmErr(""); setConfirmForm({ package_amount: "", package_key: claim.package_key || "starter", admin_notes: "" }); }}
                                  style={{ background: "rgba(251,191,36,.12)", color: "#fbbf24", border: "1px solid rgba(251,191,36,.3)", borderRadius: 6, padding: "4px 10px", fontSize: ".75rem", fontWeight: 700, cursor: "pointer", fontFamily: "inherit" }}>
                                  💵 Manually Confirm (Offline Payment)
                                </button>
                              )}
                            </div>
                          )}
                          {claim.status === "confirmed" && claim.confirmed_at && (
                            <div style={{ fontSize: ".73rem", color: "#86efac", marginTop: 3 }}>✅ Confirmed {ago(claim.confirmed_at)}</div>
                          )}
                          {claim.status === "paid" && claim.paid_at && (
                            <div style={{ fontSize: ".73rem", color: "#93c5fd", marginTop: 3 }}>🔵 Commission paid {ago(claim.paid_at)}</div>
                          )}
                          {claim.status === "claimed" && exp > 0 && (
                            <div style={{ fontSize: ".71rem", color: "#f59e0b", marginTop: 3 }}>⏳ {exp} day{exp !== 1 ? "s" : ""} left</div>
                          )}
                        </div>
                        <div style={{ textAlign: "right", flexShrink: 0 }}>
                          {claim.commission_amount > 0 && (
                            <div style={{ fontSize: "1.05rem", fontWeight: 800, color: s.c }}>{fmt(claim.commission_amount)}</div>
                          )}
                          {claim.package_amount > 0 && (
                            <div style={{ fontSize: ".74rem", color: "#64748b" }}>₹{claim.package_amount} × {claim.incentive_percent}%</div>
                          )}
                          <div style={{ fontSize: ".72rem", color: "#475569", marginTop: 3 }}>Claimed {ago(claim.claimed_at)}</div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Submit form (sales person only) */}
          {!isAdmin && <SalesLeadForm onSuccess={load} />}

        </div>
      </div>
    </div>
  );
}
