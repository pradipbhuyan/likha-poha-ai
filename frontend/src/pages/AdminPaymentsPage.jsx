import { useEffect, useState } from "react";
import { getAdminPaymentLogs } from "../api/adminControl";

const PLAN_LABELS = {
  free: "Premium Nano ₹99",
  starter: "Premium ₹299",
  family_premium: "Family Premium ₹499",
  test_1rupee: "₹1 Test",
};

function planLabel(key) {
  return PLAN_LABELS[key] || key || "—";
}

function statusColor(status) {
  if (status === "paid") return "#22c55e";
  if (status === "failed") return "#ef4444";
  return "#f59e0b";
}

// ── Tiny bar chart component (no external library needed) ─────────────────
function BarChart({ data, valueKey, labelKey, color = "#6c63ff", height = 80 }) {
  if (!data?.length) return <p style={{fontSize:".8rem",color:"var(--muted)"}}>No data yet</p>;
  const max = Math.max(...data.map(d => d[valueKey]), 1);
  return (
    <div style={{display:"flex",alignItems:"flex-end",gap:3,height}}>
      {data.map((d, i) => (
        <div key={i} style={{flex:1,display:"flex",flexDirection:"column",alignItems:"center",gap:2}}>
          <div
            title={`${d[labelKey]}: ${d[valueKey]}`}
            style={{
              width:"100%", borderRadius:"3px 3px 0 0",
              background: color,
              height: `${Math.max(2, (d[valueKey] / max) * (height - 16))}px`,
              minHeight: d[valueKey] > 0 ? 4 : 0,
              opacity: 0.8,
              transition:"height 0.3s",
            }}
          />
          <span style={{fontSize:".55rem",color:"var(--muted)",textAlign:"center",lineHeight:1}}>{d[labelKey]}</span>
        </div>
      ))}
    </div>
  );
}

export default function AdminPaymentsPage({ user }) {
  /** Admin payment logs with revenue summary, trend charts and Excel export. */
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  useEffect(() => {
    if (user?.accessToken) load();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.accessToken]);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const result = await getAdminPaymentLogs(user.accessToken);
      setData(result);
    } catch (err) {
      setError(err.message || "Failed to load payment logs.");
    } finally {
      setLoading(false);
    }
  }

  function exportCSV() {
    if (!data?.payments?.length) return;
    const headers = ["Order ID","Payment ID","Status","Name","Email","Grade","Plan","Amount (₹)","Date","Failure Reason"];
    const rows = filteredPayments.map(p => [
      p.order_id, p.payment_id, p.status, p.username, p.email,
      p.grade, planLabel(p.plan_key), p.amount,
      p.created_at, p.failure_reason || "",
    ]);
    const csv = [headers, ...rows]
      .map(r => r.map(v => `"${String(v || "").replace(/"/g, '""')}"`).join(","))
      .join("\r\n");
    const blob = new Blob(["\uFEFF" + csv], {type:"text/csv;charset=utf-8;"});
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `payment-logs-${new Date().toISOString().slice(0,10)}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  const summary = data?.summary || {};
  const trends = data?.trends || [];
  const planDist = summary.plan_distribution || {};

  const filteredPayments = (data?.payments || []).filter(p => {
    const matchStatus = statusFilter === "all" || p.status === statusFilter;
    const q = search.toLowerCase();
    const matchSearch = !q || [p.username, p.email, p.order_id, p.payment_id, p.plan_key]
      .some(v => (v || "").toLowerCase().includes(q));
    return matchStatus && matchSearch;
  });

  if (loading) return <div className="premium-page"><p>Loading payment logs…</p></div>;
  if (error) return <div className="premium-page"><div className="error-box">{error}</div></div>;

  return (
    <div className="premium-page">
      {/* ── Header summary cards ── */}
      <section className="premium-section">
        <div className="premium-header">
          <p className="eyebrow">Revenue & Payments</p>
          <h2>💳 Payment Logs</h2>
          <p>All Razorpay transactions — successful and failed — with revenue analytics.</p>
        </div>

        <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(160px,1fr))",gap:16,marginBottom:8}}>
          {[
            {label:"This Month Revenue", value:`₹${(summary.monthly_revenue||0).toLocaleString("en-IN")}`, color:"#6c63ff"},
            {label:"Total Revenue", value:`₹${(summary.total_revenue||0).toLocaleString("en-IN")}`, color:"#22c55e"},
            {label:"Paid Users", value:summary.active_paid_users||0, color:"#3b82f6"},
            {label:"Total Transactions", value:summary.total_transactions||0, color:"#f59e0b"},
            {label:"Failed", value:summary.failed_transactions||0, color:"#ef4444"},
          ].map(c => (
            <div key={c.label} className="premium-card" style={{textAlign:"center",padding:"18px 12px"}}>
              <div style={{fontSize:"1.6rem",fontWeight:800,color:c.color}}>{c.value}</div>
              <div style={{fontSize:".78rem",color:"var(--muted)",marginTop:4}}>{c.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Trend charts ── */}
      <section className="premium-section">
        <div style={{display:"grid",gridTemplateColumns:"1fr 1fr 1fr",gap:20,flexWrap:"wrap"}}>
          {/* Revenue trend */}
          <div className="premium-card" style={{padding:16}}>
            <h4 style={{margin:"0 0 12px",fontSize:".9rem"}}>📈 Monthly Revenue (₹)</h4>
            <BarChart data={trends} valueKey="revenue" labelKey="label" color="#6c63ff" height={100} />
          </div>
          {/* User trend */}
          <div className="premium-card" style={{padding:16}}>
            <h4 style={{margin:"0 0 12px",fontSize:".9rem"}}>👥 New Paid Users / Month</h4>
            <BarChart data={trends} valueKey="users" labelKey="label" color="#22c55e" height={100} />
          </div>
          {/* Plan distribution */}
          <div className="premium-card" style={{padding:16}}>
            <h4 style={{margin:"0 0 12px",fontSize:".9rem"}}>📦 Plan Distribution</h4>
            {Object.keys(planDist).length === 0 ? (
              <p style={{fontSize:".8rem",color:"var(--muted)"}}>No paid transactions yet</p>
            ) : (
              <div style={{display:"flex",flexDirection:"column",gap:8}}>
                {Object.entries(planDist).sort((a,b) => b[1]-a[1]).map(([key, count]) => {
                  const total = Object.values(planDist).reduce((s,v) => s+v, 0);
                  const pct = Math.round((count/total)*100);
                  return (
                    <div key={key}>
                      <div style={{display:"flex",justifyContent:"space-between",fontSize:".78rem",marginBottom:3}}>
                        <span>{planLabel(key)}</span>
                        <span style={{fontWeight:700}}>{count} ({pct}%)</span>
                      </div>
                      <div style={{height:8,borderRadius:4,background:"var(--border)",overflow:"hidden"}}>
                        <div style={{height:"100%",width:`${pct}%`,background:"#6c63ff",borderRadius:4}} />
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </section>

      {/* ── Payment logs table ── */}
      <section className="premium-section">
        <div style={{display:"flex",gap:12,alignItems:"center",flexWrap:"wrap",marginBottom:16}}>
          <input
            type="text"
            placeholder="Search by name, email, order ID…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{flex:1,minWidth:200,padding:"8px 12px",borderRadius:8,border:"1px solid var(--border)",fontFamily:"inherit"}}
          />
          <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
            style={{padding:"8px 12px",borderRadius:8,border:"1px solid var(--border)",fontFamily:"inherit"}}>
            <option value="all">All Status</option>
            <option value="paid">Paid</option>
            <option value="failed">Failed</option>
            <option value="created">Pending</option>
          </select>
          <button
            className="secondary-btn"
            onClick={load}
            style={{whiteSpace:"nowrap"}}>
            🔄 Refresh
          </button>
          <button
            className="primary-btn"
            onClick={exportCSV}
            disabled={!filteredPayments.length}
            style={{whiteSpace:"nowrap"}}>
            📥 Export Excel
          </button>
        </div>

        <div style={{overflowX:"auto"}}>
          <table style={{width:"100%",borderCollapse:"collapse",fontSize:".82rem"}}>
            <thead>
              <tr style={{background:"var(--surface2,#f8f9fa)",borderBottom:"2px solid var(--border)"}}>
                {["Date","Name","Email","Plan","Amount","Status","Payment ID","Failure Reason"].map(h => (
                  <th key={h} style={{padding:"8px 10px",textAlign:"left",fontWeight:700,color:"var(--muted)",whiteSpace:"nowrap"}}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filteredPayments.length === 0 ? (
                <tr><td colSpan={8} style={{padding:24,textAlign:"center",color:"var(--muted)"}}>
                  {data?.payments?.length === 0
                    ? "No payment records yet. Run sql/subscription_payments.sql in Supabase first."
                    : "No records match your filter."}
                </td></tr>
              ) : filteredPayments.map((p, i) => (
                <tr key={p.id || i} style={{borderBottom:"1px solid var(--border)",background: i%2===0?"transparent":"rgba(0,0,0,.015)"}}>
                  <td style={{padding:"8px 10px",whiteSpace:"nowrap",color:"var(--muted)"}}>
                    {p.created_at ? p.created_at.replace("T"," ") : "—"}
                  </td>
                  <td style={{padding:"8px 10px",fontWeight:600}}>{p.username}</td>
                  <td style={{padding:"8px 10px",color:"var(--muted)"}}>{p.email}</td>
                  <td style={{padding:"8px 10px"}}>{planLabel(p.plan_key)}</td>
                  <td style={{padding:"8px 10px",fontWeight:700}}>₹{p.amount}</td>
                  <td style={{padding:"8px 10px"}}>
                    <span style={{
                      background:`${statusColor(p.status)}20`,
                      color:statusColor(p.status),
                      padding:"2px 8px",borderRadius:12,fontWeight:700,fontSize:".75rem",
                    }}>
                      {p.status.toUpperCase()}
                    </span>
                  </td>
                  <td style={{padding:"8px 10px",fontFamily:"monospace",fontSize:".75rem",color:"var(--muted)"}}>
                    {p.payment_id || "—"}
                  </td>
                  <td style={{padding:"8px 10px",color:"#ef4444",fontSize:".78rem"}}>
                    {p.failure_reason || "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {filteredPayments.length > 0 && (
          <p style={{fontSize:".78rem",color:"var(--muted)",marginTop:8}}>
            Showing {filteredPayments.length} of {data?.payments?.length || 0} records
          </p>
        )}
      </section>
    </div>
  );
}
