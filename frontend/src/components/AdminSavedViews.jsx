/**
 * AdminSavedViews.jsx — Prebuilt admin saved views panel.
 * Props: accessToken
 */
import { useEffect, useState } from "react";

const API = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const STORAGE_KEY = "admin_saved_views_custom";

function loadCustomViews() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]"); }
  catch { return []; }
}

export default function AdminSavedViews({ accessToken }) {
  const [views, setViews]           = useState([]);
  const [selectedView, setSelected] = useState(null);
  const [rows, setRows]             = useState([]);
  const [loading, setLoading]       = useState(false);
  const [error, setError]           = useState(null);
  const [count, setCount]           = useState(0);
  const [page, setPage]             = useState(1);
  const [customViews, setCustomViews] = useState(loadCustomViews);

  useEffect(() => {
    if (!accessToken) return;
    fetch(`${API}/api/admin/views`, { headers: { Authorization: `Bearer ${accessToken}` } })
      .then(r => r.json())
      .then(d => setViews(d.views || []))
      .catch(() => {});
  }, [accessToken]);

  async function runView(viewId, pg = 1) {
    setLoading(true); setError(null); setPage(pg);
    try {
      const r = await fetch(`${API}/api/admin/views/${viewId}?page=${pg}&page_size=20`, {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      const d = await r.json();
      setRows(d.rows || []);
      setCount(d.count || 0);
      if (d.error) setError(d.error);
    } catch (e) { setError(e.message); }
    setLoading(false);
  }

  function selectView(v) {
    setSelected(v);
    setRows([]); setPage(1); setError(null);
    runView(v.id, 1);
  }

  const CATEGORY_COLORS = { subscriptions: "#6366f1", teachers: "#10b981", families: "#f59e0b", payments: "#ef4444", users: "#0ea5e9", offers: "#8b5cf6" };

  return (
    <div data-testid="admin-saved-views" style={{ display: "grid", gridTemplateColumns: "220px 1fr", gap: 16, minHeight: 400 }}>
      {/* Sidebar */}
      <div style={{ borderRight: "1px solid var(--border, #e5e7eb)", paddingRight: 12 }}>
        <h4 style={{ margin: "0 0 10px", fontSize: ".88rem", fontWeight: 700 }}>Prebuilt Views</h4>
        {views.map(v => (
          <button key={v.id} onClick={() => selectView(v)}
            data-testid={`view-btn-${v.id}`}
            style={{
              display: "block", width: "100%", textAlign: "left", padding: "7px 10px",
              marginBottom: 3, borderRadius: 7, border: "none",
              background: selectedView?.id === v.id ? "rgba(99,102,241,.12)" : "transparent",
              color: selectedView?.id === v.id ? "#6366f1" : "var(--text, #374151)",
              fontFamily: "inherit", fontSize: ".82rem", fontWeight: selectedView?.id === v.id ? 700 : 400, cursor: "pointer",
            }}>
            <span style={{ display: "inline-block", width: 8, height: 8, borderRadius: "50%", background: CATEGORY_COLORS[v.category] || "#94a3b8", marginRight: 7 }} />
            {v.label}
          </button>
        ))}
        {customViews.length > 0 && (
          <>
            <div style={{ margin: "12px 0 6px", fontSize: ".72rem", fontWeight: 700, color: "var(--muted, #94a3b8)", textTransform: "uppercase" }}>Saved Custom</div>
            {customViews.map((cv, i) => (
              <div key={i} style={{ display: "flex", alignItems: "center", gap: 4, marginBottom: 3 }}>
                <button onClick={() => selectView(cv)}
                  style={{ flex: 1, textAlign: "left", padding: "5px 8px", borderRadius: 6, border: "none", background: "var(--surface2, #f8fafc)", fontSize: ".78rem", cursor: "pointer", fontFamily: "inherit" }}>
                  {cv.label}
                </button>
                <button onClick={() => setCustomViews(p => p.filter((_, j) => j !== i))}
                  style={{ background: "none", border: "none", cursor: "pointer", color: "#ef4444", fontSize: ".7rem" }}>✕</button>
              </div>
            ))}
          </>
        )}
      </div>

      {/* Results panel */}
      <div>
        {!selectedView && (
          <div style={{ color: "var(--muted, #64748b)", fontSize: ".85rem", padding: "20px 0" }}>
            Select a view from the sidebar to see live results.
          </div>
        )}
        {selectedView && (
          <>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12, flexWrap: "wrap", gap: 8 }}>
              <div>
                <h4 style={{ margin: 0, fontSize: ".95rem" }}>{selectedView.label}</h4>
                <p style={{ margin: "2px 0 0", fontSize: ".78rem", color: "var(--muted, #64748b)" }}>{selectedView.description}</p>
              </div>
              <div style={{ display: "flex", gap: 6 }}>
                <span style={{ fontSize: ".78rem", color: "var(--muted, #64748b)", alignSelf: "center" }}>{count} row(s)</span>
                <button onClick={() => runView(selectedView.id, page)} disabled={loading}
                  style={{ padding: "4px 10px", fontSize: ".78rem", borderRadius: 6, border: "1px solid var(--border, #e5e7eb)", background: "var(--panel, #fff)", cursor: "pointer", fontFamily: "inherit", color: "#6366f1", fontWeight: 600 }}>
                  {loading ? "Loading…" : "↺ Refresh"}
                </button>
              </div>
            </div>
            {error && <div style={{ color: "#dc2626", fontSize: ".8rem", marginBottom: 8 }}>⚠ {error}</div>}
            {!loading && rows.length === 0 && !error && (
              <div style={{ color: "var(--muted, #64748b)", fontSize: ".85rem" }}>No results for this view.</div>
            )}
            {rows.length > 0 && (
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: ".78rem" }}>
                  <thead>
                    <tr style={{ borderBottom: "1px solid var(--border, #e5e7eb)" }}>
                      {Object.keys(rows[0]).map(k => (
                        <th key={k} style={{ padding: "5px 8px", textAlign: "left", color: "var(--muted, #64748b)", fontWeight: 600, whiteSpace: "nowrap" }}>{k}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((row, i) => (
                      <tr key={i} style={{ borderBottom: "1px solid var(--border, #f1f5f9)" }}>
                        {Object.values(row).map((v, j) => (
                          <td key={j} style={{ padding: "5px 8px", maxWidth: 160, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                            {v === null || v === undefined ? "—" : String(v)}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
                <div style={{ display: "flex", gap: 6, marginTop: 8, alignItems: "center" }}>
                  <button onClick={() => { const p = Math.max(1, page-1); runView(selectedView.id, p); }} disabled={page <= 1 || loading}
                    style={{ padding: "3px 10px", fontSize: ".78rem", borderRadius: 5, border: "1px solid var(--border, #e5e7eb)", background: "var(--panel)", cursor: "pointer", fontFamily: "inherit" }}>← Prev</button>
                  <span style={{ fontSize: ".78rem", color: "var(--muted, #64748b)" }}>Page {page}</span>
                  <button onClick={() => runView(selectedView.id, page+1)} disabled={rows.length < 20 || loading}
                    style={{ padding: "3px 10px", fontSize: ".78rem", borderRadius: 5, border: "1px solid var(--border, #e5e7eb)", background: "var(--panel)", cursor: "pointer", fontFamily: "inherit" }}>Next →</button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
