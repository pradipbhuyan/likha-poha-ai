import { useEffect, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const SOURCE_LABELS = {
  chatbot: { label: "💬 Chatbot", color: "#6366f1", bg: "rgba(99,102,241,.12)" },
  doubt: { label: "❓ Ask Doubt", color: "#10b981", bg: "rgba(16,185,129,.12)" },
  lesson_followup: { label: "📚 Lesson Follow-up", color: "#f59e0b", bg: "rgba(245,158,11,.12)" },
};

export default function AdminUnansweredQuestionsPage({ user }) {
  const [items, setItems] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("pending");
  const [sourceFilter, setSourceFilter] = useState("");
  const [selected, setSelected] = useState(null);
  const [answer, setAnswer] = useState("");
  const [target, setTarget] = useState("dkb");
  const [grade, setGrade] = useState("");
  const [subject, setSubject] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const headers = {
    "Content-Type": "application/json",
    Authorization: `Bearer ${user?.accessToken}`,
  };

  async function loadData() {
    setLoading(true);
    try {
      const [itemsRes, statsRes] = await Promise.all([
        fetch(`${API_BASE}/api/unanswered-review?status=${statusFilter}&source=${sourceFilter}&limit=100`, { headers }),
        fetch(`${API_BASE}/api/unanswered-review/stats`, { headers }),
      ]);
      const itemsData = await itemsRes.json();
      const statsData = await statsRes.json();
      setItems(itemsData.items || []);
      setStats(statsData);
    } catch (e) {
      setError("Could not load unanswered questions. Run the SQL migration first.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadData(); }, [statusFilter, sourceFilter]);

  function selectItem(item) {
    setSelected(item);
    setAnswer("");
    setTarget(item.source === "chatbot" ? "chatbot" : "dkb");
    setGrade(item.grade || "");
    setSubject(item.subject || "");
    setMessage("");
    setError("");
  }

  async function handleApprove() {
    if (!answer.trim()) { setError("Please write an answer before approving."); return; }
    setSaving(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE}/api/unanswered-review/${selected.id}/approve`, {
        method: "POST",
        headers,
        body: JSON.stringify({ answer: answer.trim(), target, grade: grade || null, subject: subject || null }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Approve failed");
      setMessage(`✅ Approved and saved to ${target.toUpperCase()}`);
      setSelected(null);
      await loadData();
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleReject() {
    setSaving(true);
    try {
      await fetch(`${API_BASE}/api/unanswered-review/${selected.id}/reject`, {
        method: "POST", headers,
      });
      setMessage("❌ Rejected");
      setSelected(null);
      await loadData();
    } catch { setError("Reject failed"); }
    finally { setSaving(false); }
  }

  async function handleDelete(id) {
    if (!window.confirm("Delete this entry permanently?")) return;
    try {
      await fetch(`${API_BASE}/api/unanswered-review/${id}`, { method: "DELETE", headers });
      setItems(prev => prev.filter(i => i.id !== id));
      if (selected?.id === id) setSelected(null);
    } catch { setError("Delete failed"); }
  }

  return (
    <div className="premium-page" style={{ padding: "24px 28px", maxWidth: 1200, margin: "0 auto" }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <p className="eyebrow">Intelligence Management</p>
        <h2 style={{ margin: "4px 0 8px" }}>🧠 Unanswered Questions Review</h2>
        <p style={{ color: "var(--muted)", fontSize: ".9rem" }}>
          Questions that could not be answered by the Chatbot, Ask Doubt, or Lesson Follow-up.
          Approve with a human-written answer to add it to the AI's knowledge. Reject to dismiss.
        </p>
      </div>

      {/* Stats */}
      {stats && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 20 }}>
          {[
            { label: "Total", value: stats.total, color: "#6366f1" },
            { label: "Pending Review", value: stats.pending, color: "#f59e0b" },
            { label: "Approved", value: stats.approved, color: "#10b981" },
            { label: "Rejected", value: stats.rejected, color: "#94a3b8" },
          ].map(s => (
            <div key={s.label} className="premium-card" style={{ padding: "14px 16px", textAlign: "center" }}>
              <div style={{ fontSize: "1.8rem", fontWeight: 800, color: s.color }}>{s.value}</div>
              <div style={{ fontSize: ".78rem", color: "var(--muted)", marginTop: 2 }}>{s.label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Source breakdown */}
      {stats?.pending_by_source && Object.keys(stats.pending_by_source).length > 0 && (
        <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
          <span style={{ fontSize: ".78rem", color: "var(--muted)", alignSelf: "center" }}>Pending by source:</span>
          {Object.entries(stats.pending_by_source).map(([src, n]) => {
            const s = SOURCE_LABELS[src] || { label: src, color: "#94a3b8", bg: "rgba(148,163,184,.12)" };
            return (
              <span key={src} style={{ background: s.bg, color: s.color, borderRadius: 20, padding: "3px 10px", fontSize: ".78rem", fontWeight: 600 }}>
                {s.label}: {n}
              </span>
            );
          })}
        </div>
      )}

      {/* Filters */}
      <div style={{ display: "flex", gap: 10, marginBottom: 16, flexWrap: "wrap" }}>
        <div style={{ display: "flex", gap: 0, background: "var(--panel)", border: "1px solid var(--border)", borderRadius: 8, overflow: "hidden" }}>
          {["pending", "approved", "rejected"].map(s => (
            <button key={s} onClick={() => setStatusFilter(s)}
              style={{ padding: "7px 14px", border: "none", background: statusFilter === s ? "var(--accent, #6366f1)" : "transparent",
                       color: statusFilter === s ? "#fff" : "var(--muted)", fontFamily: "inherit", fontSize: ".82rem",
                       fontWeight: statusFilter === s ? 700 : 400, cursor: "pointer", textTransform: "capitalize" }}>
              {s}
            </button>
          ))}
        </div>
        <div style={{ display: "flex", gap: 0, background: "var(--panel)", border: "1px solid var(--border)", borderRadius: 8, overflow: "hidden" }}>
          <button onClick={() => setSourceFilter("")}
            style={{ padding: "7px 12px", border: "none", background: !sourceFilter ? "var(--accent, #6366f1)" : "transparent",
                     color: !sourceFilter ? "#fff" : "var(--muted)", fontFamily: "inherit", fontSize: ".82rem", cursor: "pointer" }}>
            All
          </button>
          {Object.entries(SOURCE_LABELS).map(([src, s]) => (
            <button key={src} onClick={() => setSourceFilter(sourceFilter === src ? "" : src)}
              style={{ padding: "7px 12px", border: "none", background: sourceFilter === src ? s.bg : "transparent",
                       color: sourceFilter === src ? s.color : "var(--muted)", fontFamily: "inherit", fontSize: ".82rem",
                       fontWeight: sourceFilter === src ? 700 : 400, cursor: "pointer" }}>
              {s.label}
            </button>
          ))}
        </div>
        <button onClick={loadData} className="secondary-btn" style={{ fontSize: ".82rem" }}>🔄 Refresh</button>
      </div>

      {message && <div className="info-box" style={{ marginBottom: 12 }}>{message}</div>}
      {error && <div className="error-box" style={{ marginBottom: 12 }}>{error}</div>}

      {/* Main layout: list + detail */}
      <div style={{ display: "grid", gridTemplateColumns: selected ? "1fr 1fr" : "1fr", gap: 16 }}>

        {/* Question list */}
        <div>
          {loading ? <p>Loading...</p> : items.length === 0 ? (
            <div className="premium-card" style={{ textAlign: "center", padding: 32, color: "var(--muted)" }}>
              <div style={{ fontSize: "2rem", marginBottom: 8 }}>✅</div>
              <p>No {statusFilter} questions to review.</p>
              {statusFilter === "pending" && <p style={{ fontSize: ".82rem" }}>Questions will appear here when chatbot/doubt can't answer them.</p>}
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {items.map(item => {
                const src = SOURCE_LABELS[item.source] || { label: item.source, color: "#94a3b8", bg: "rgba(148,163,184,.12)" };
                const isSelected = selected?.id === item.id;
                return (
                  <div key={item.id}
                    onClick={() => selectItem(item)}
                    className="premium-card"
                    style={{
                      padding: "12px 14px", cursor: "pointer",
                      border: `1.5px solid ${isSelected ? "var(--accent, #6366f1)" : "var(--border)"}`,
                      background: isSelected ? "rgba(99,102,241,.06)" : "var(--panel)",
                    }}>
                    <div style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontWeight: 600, fontSize: ".9rem", marginBottom: 4, wordBreak: "break-word" }}>
                          {item.question}
                        </div>
                        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                          <span style={{ background: src.bg, color: src.color, borderRadius: 10, padding: "1px 8px", fontSize: ".72rem", fontWeight: 600 }}>
                            {src.label}
                          </span>
                          {item.grade && <span style={{ background: "rgba(99,102,241,.1)", color: "#a5b4fc", borderRadius: 10, padding: "1px 8px", fontSize: ".72rem" }}>{item.grade}</span>}
                          {item.subject && <span style={{ background: "rgba(16,185,129,.1)", color: "#6ee7b7", borderRadius: 10, padding: "1px 8px", fontSize: ".72rem" }}>{item.subject}</span>}
                        </div>
                        <div style={{ fontSize: ".7rem", color: "var(--muted)", marginTop: 4 }}>
                          {new Date(item.created_at).toLocaleString("en-IN")}
                        </div>
                      </div>
                      <button onClick={e => { e.stopPropagation(); handleDelete(item.id); }}
                        style={{ background: "none", border: "none", cursor: "pointer", color: "#ef4444", fontSize: ".8rem", flexShrink: 0, padding: "2px 4px" }}
                        title="Delete">🗑</button>
                    </div>
                    {item.approved_answer && (
                      <div style={{ marginTop: 8, padding: "6px 10px", background: "rgba(16,185,129,.08)", borderRadius: 6, fontSize: ".8rem", color: "#6ee7b7" }}>
                        ✅ Approved → {item.target?.toUpperCase()} | {item.approved_by}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Detail / Approve panel */}
        {selected && (
          <div>
            <div className="premium-card" style={{ padding: 20, position: "sticky", top: 20 }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
                <h3 style={{ margin: 0, fontSize: "1rem" }}>Review Question</h3>
                <button onClick={() => setSelected(null)}
                  style={{ background: "none", border: "none", cursor: "pointer", color: "var(--muted)", fontSize: 18 }}>×</button>
              </div>

              <div style={{ background: "var(--surface2, #111827)", borderRadius: 8, padding: "10px 12px", marginBottom: 16 }}>
                <div style={{ fontSize: ".75rem", color: "var(--muted)", marginBottom: 4 }}>Question</div>
                <div style={{ fontWeight: 600, fontSize: ".9rem" }}>{selected.question}</div>
              </div>

              {(selected.grade || selected.subject || selected.chapter) && (
                <div style={{ display: "flex", gap: 6, marginBottom: 14, flexWrap: "wrap" }}>
                  {selected.grade && <span style={{ background: "rgba(99,102,241,.1)", color: "#a5b4fc", borderRadius: 10, padding: "2px 8px", fontSize: ".75rem" }}>{selected.grade}</span>}
                  {selected.subject && <span style={{ background: "rgba(16,185,129,.1)", color: "#6ee7b7", borderRadius: 10, padding: "2px 8px", fontSize: ".75rem" }}>{selected.subject}</span>}
                  {selected.chapter && <span style={{ background: "rgba(245,158,11,.1)", color: "#fcd34d", borderRadius: 10, padding: "2px 8px", fontSize: ".75rem" }}>{selected.chapter}</span>}
                </div>
              )}

              {/* Save target */}
              <div style={{ marginBottom: 14 }}>
                <label style={{ display: "block", fontSize: ".8rem", fontWeight: 600, color: "var(--muted)", marginBottom: 6 }}>
                  Save approved answer to:
                </label>
                <div style={{ display: "flex", gap: 8 }}>
                  {[
                    { value: "dkb", label: "📖 DKB (Doubt & Lesson)", desc: "Searchable by students" },
                    { value: "chatbot", label: "💬 Chatbot KB", desc: "Chatbot widget only" },
                  ].map(t => (
                    <button key={t.value} onClick={() => setTarget(t.value)}
                      style={{
                        flex: 1, padding: "8px 10px", borderRadius: 8, border: `2px solid ${target === t.value ? "var(--accent, #6366f1)" : "var(--border)"}`,
                        background: target === t.value ? "rgba(99,102,241,.1)" : "var(--panel)",
                        color: target === t.value ? "#a5b4fc" : "var(--muted)", fontFamily: "inherit",
                        cursor: "pointer", textAlign: "left",
                      }}>
                      <div style={{ fontWeight: 700, fontSize: ".82rem" }}>{t.label}</div>
                      <div style={{ fontSize: ".7rem", marginTop: 2 }}>{t.desc}</div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Grade/Subject override for DKB */}
              {target === "dkb" && (
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 14 }}>
                  <div>
                    <label style={{ display: "block", fontSize: ".75rem", color: "var(--muted)", marginBottom: 4 }}>Grade</label>
                    <input value={grade} onChange={e => setGrade(e.target.value)} placeholder="e.g. Grade 9"
                      style={{ width: "100%", padding: "7px 10px", borderRadius: 6, border: "1px solid var(--border)", background: "var(--surface2, #111827)", color: "var(--text)", fontFamily: "inherit", fontSize: ".83rem" }} />
                  </div>
                  <div>
                    <label style={{ display: "block", fontSize: ".75rem", color: "var(--muted)", marginBottom: 4 }}>Subject</label>
                    <input value={subject} onChange={e => setSubject(e.target.value)} placeholder="e.g. Science"
                      style={{ width: "100%", padding: "7px 10px", borderRadius: 6, border: "1px solid var(--border)", background: "var(--surface2, #111827)", color: "var(--text)", fontFamily: "inherit", fontSize: ".83rem" }} />
                  </div>
                </div>
              )}

              {/* Answer textarea */}
              <div style={{ marginBottom: 14 }}>
                <label style={{ display: "block", fontSize: ".8rem", fontWeight: 600, color: "var(--muted)", marginBottom: 6 }}>
                  Your Answer (Markdown supported)
                </label>
                <textarea
                  rows={8}
                  value={answer}
                  onChange={e => setAnswer(e.target.value)}
                  placeholder="Write a clear, accurate answer. Markdown is supported — use **bold**, bullet lists, etc."
                  style={{
                    width: "100%", padding: "10px 12px", borderRadius: 8,
                    border: "1px solid var(--border)", background: "var(--surface2, #111827)",
                    color: "var(--text)", fontFamily: "inherit", fontSize: ".85rem",
                    resize: "vertical", outline: "none", lineHeight: 1.55,
                  }}
                />
                <div style={{ fontSize: ".72rem", color: "var(--muted)", marginTop: 3 }}>
                  {answer.length} characters
                </div>
              </div>

              {error && <div className="error-box" style={{ marginBottom: 10 }}>{error}</div>}

              {/* Actions */}
              <div style={{ display: "flex", gap: 8 }}>
                <button onClick={handleApprove} disabled={saving || !answer.trim()} className="primary-btn"
                  style={{ flex: 2, fontSize: ".85rem" }}>
                  {saving ? "Saving..." : `✅ Approve → ${target.toUpperCase()}`}
                </button>
                <button onClick={handleReject} disabled={saving} className="secondary-btn"
                  style={{ flex: 1, fontSize: ".85rem", color: "#f87171", borderColor: "#f87171" }}>
                  ❌ Reject
                </button>
              </div>

              <p style={{ fontSize: ".72rem", color: "var(--muted)", marginTop: 8, textAlign: "center" }}>
                Approved answers become part of the platform's AI knowledge — they serve future questions instantly.
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Setup instructions if table missing */}
      {error?.includes("SQL migration") && (
        <div className="premium-card" style={{ marginTop: 20, borderLeft: "4px solid #f59e0b" }}>
          <h3 style={{ marginBottom: 8, color: "#fcd34d" }}>⚠️ Database Table Setup Required</h3>
          <p style={{ fontSize: ".85rem", marginBottom: 12 }}>Run this SQL in your Supabase project → SQL Editor:</p>
          <pre style={{ background: "#0f172a", borderRadius: 8, padding: 14, fontSize: ".78rem", overflowX: "auto", color: "#cbd5e1" }}>
{`-- Copy from: backend/sql/add_unanswered_questions.sql
-- Or run it directly in Supabase SQL Editor`}
          </pre>
          <p style={{ fontSize: ".82rem", color: "var(--muted)" }}>
            File path: <code>backend/sql/add_unanswered_questions.sql</code>
          </p>
        </div>
      )}
    </div>
  );
}
