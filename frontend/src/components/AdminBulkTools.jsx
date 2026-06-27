/**
 * AdminBulkTools.jsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Bulk admin operations panel.
 * Tabs: Assign Teacher | Reset Passwords | Grant Access | Export | Import CSV
 *
 * Props:
 *  accessToken   — admin JWT
 *  allStudents   — in-memory students array
 *  allTeachers   — in-memory teachers array
 *  allParents    — in-memory parents array
 */

import { useState } from "react";

const API = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function apiFetch(path, opts = {}, token) {
  const r = await fetch(`${API}${path}`, {
    ...opts,
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}`, ...(opts.headers || {}) },
  });
  return r.json();
}

// ── Sub-section styles ────────────────────────────────────────────────────────
const cardStyle = {
  background: "var(--panel, #fff)",
  border: "1px solid var(--border, #e5e7eb)",
  borderRadius: 10,
  padding: "16px 18px",
  marginBottom: 14,
};

const inputStyle = {
  padding: "8px 10px",
  borderRadius: 7,
  border: "1px solid var(--border, #e5e7eb)",
  background: "var(--surface2, #f8fafc)",
  fontFamily: "inherit",
  fontSize: ".85rem",
  color: "var(--text, #1e293b)",
  width: "100%",
};

// ── Checkbox list helper ──────────────────────────────────────────────────────
function CheckList({ items, selected, onToggle, labelKey = "username", idKey = "id", subKey = "email" }) {
  const [filter, setFilter] = useState("");
  const filtered = items.filter(
    (i) => (i[labelKey] || "").toLowerCase().includes(filter.toLowerCase()) ||
             (i[subKey] || "").toLowerCase().includes(filter.toLowerCase())
  );
  return (
    <div>
      <input
        style={{ ...inputStyle, marginBottom: 8 }}
        placeholder="Filter by name or email…"
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
        aria-label="Filter list"
      />
      <div style={{ maxHeight: 220, overflowY: "auto", border: "1px solid var(--border, #e5e7eb)", borderRadius: 7 }}>
        {filtered.length === 0 && <div style={{ padding: "10px 12px", color: "var(--muted, #64748b)", fontSize: ".82rem" }}>No matches.</div>}
        {filtered.map((item) => (
          <label key={item[idKey]} style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 12px", cursor: "pointer", borderBottom: "1px solid var(--border, #f1f5f9)" }}>
            <input
              type="checkbox"
              checked={selected.has(item[idKey])}
              onChange={() => onToggle(item[idKey])}
            />
            <span style={{ fontSize: ".82rem", fontWeight: 600 }}>{item[labelKey]}</span>
            <span style={{ fontSize: ".72rem", color: "var(--muted, #94a3b8)", marginLeft: 4 }}>{item[subKey]}</span>
          </label>
        ))}
      </div>
      <div style={{ fontSize: ".72rem", color: "var(--muted, #94a3b8)", marginTop: 4 }}>
        {selected.size} selected of {items.length}
        {selected.size > 0 && (
          <button onClick={() => items.forEach(i => selected.has(i[idKey]) && onToggle(i[idKey]))}
            style={{ marginLeft: 8, background: "none", border: "none", cursor: "pointer", color: "#ef4444", fontSize: ".72rem", fontFamily: "inherit" }}>
            Clear all
          </button>
        )}
      </div>
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────
export default function AdminBulkTools({ accessToken, allStudents = [], allTeachers = [], allParents = [] }) {
  const [tab, setTab]           = useState("assign");
  const [loading, setLoading]   = useState(false);
  const [result, setResult]     = useState(null);

  // Assign teacher
  const [selectedTeacherId, setSelectedTeacherId] = useState("");
  const [selectedStudents, setSelectedStudents]   = useState(new Set());

  // Reset passwords / grant access
  const [selectedUsers, setSelectedUsers] = useState(new Set());

  // CSV import
  const [csvText, setCsvText]           = useState("");
  const [csvPreview, setCsvPreview]     = useState(null);

  const allUsers = [...allStudents, ...allParents];

  function toggleUser(id) {
    setSelectedUsers((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  function toggleStudent(id) {
    setSelectedStudents((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  async function runBulkAssign() {
    if (!selectedTeacherId || selectedStudents.size === 0) return;
    setLoading(true);
    setResult(null);
    const data = await apiFetch("/api/admin/bulk/assign-teacher", {
      method: "POST",
      body: JSON.stringify({ teacher_id: selectedTeacherId, student_ids: [...selectedStudents] }),
    }, accessToken);
    setResult(data);
    setLoading(false);
  }

  async function runBulkReset() {
    if (selectedStudents.size === 0) return;
    if (!window.confirm(`Reset passwords for ${selectedStudents.size} student(s)? New temporary passwords will be shown once only.`)) return;
    setLoading(true);
    setResult(null);
    const data = await apiFetch("/api/admin/bulk/reset-passwords", {
      method: "POST",
      body: JSON.stringify({ student_ids: [...selectedStudents] }),
    }, accessToken);
    setResult(data);
    setLoading(false);
  }

  async function runBulkGrant() {
    if (selectedUsers.size === 0) return;
    if (!window.confirm(`Grant Platform Access to ${selectedUsers.size} user(s)? Active paid subscriptions will be skipped.`)) return;
    setLoading(true);
    setResult(null);
    const data = await apiFetch("/api/admin/bulk/grant-access", {
      method: "POST",
      body: JSON.stringify({ user_ids: [...selectedUsers], skip_active_paid: true }),
    }, accessToken);
    setResult(data);
    setLoading(false);
  }

  async function runBulkExport() {
    if (selectedUsers.size === 0) return;
    setLoading(true);
    const r = await fetch(`${API}/api/admin/bulk/export`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${accessToken}` },
      body: JSON.stringify({ user_ids: [...selectedUsers] }),
    });
    if (r.ok) {
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `bulk_export_${new Date().toISOString().slice(0,10)}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      setResult({ success: true, message: `Exported ${selectedUsers.size} user(s).` });
    }
    setLoading(false);
  }

  function parseCsv(text) {
    const lines = text.trim().split("\n");
    if (lines.length < 2) return [];
    const headers = lines[0].split(",").map((h) => h.trim().toLowerCase());
    return lines.slice(1).map((line) => {
      const vals = line.split(",").map((v) => v.trim());
      const obj = {};
      headers.forEach((h, i) => { obj[h] = vals[i] || ""; });
      return { name: obj.name || "", grade: obj.grade || "Grade 9", email: obj.email || null, temporary_password: obj.temporary_password || null };
    });
  }

  function handleCsvPreview() {
    const rows = parseCsv(csvText);
    if (rows.length === 0) return;
    // Client-side preview validation
    const preview = rows.map((r, i) => ({
      row: i + 1, name: r.name, grade: r.grade, email: r.email,
      errors: !r.name ? ["name required"] : !r.grade.startsWith("Grade ") ? ["invalid grade"] : [],
    }));
    setCsvPreview(preview);
    setResult(null);
  }

  async function runCsvImport(confirmed) {
    const rows = parseCsv(csvText);
    setLoading(true);
    const data = await apiFetch("/api/admin/bulk/import-students", {
      method: "POST",
      body: JSON.stringify({ rows, confirmed }),
    }, accessToken);
    setResult(data);
    if (confirmed) setCsvPreview(null);
    setLoading(false);
  }

  const TABS = [
    { key: "assign", label: "Assign Teacher" },
    { key: "reset",  label: "Reset Passwords" },
    { key: "grant",  label: "Grant Access" },
    { key: "export", label: "Export" },
    { key: "import", label: "Import CSV" },
  ];

  return (
    <div data-testid="admin-bulk-tools">
      {/* Sub-tab nav */}
      <div style={{ display: "flex", gap: 4, flexWrap: "wrap", marginBottom: 16 }}>
        {TABS.map((t) => (
          <button key={t.key} onClick={() => { setTab(t.key); setResult(null); }}
            style={{
              padding: "6px 14px", borderRadius: 7, border: "1px solid var(--border, #e5e7eb)",
              background: tab === t.key ? "var(--primary, #6366f1)" : "var(--panel, #fff)",
              color: tab === t.key ? "#fff" : "var(--text, #374151)",
              fontWeight: 600, fontSize: ".82rem", cursor: "pointer", fontFamily: "inherit",
            }}
          >{t.label}</button>
        ))}
      </div>

      {/* Result banner */}
      {result && (
        <div style={{ marginBottom: 12, padding: "10px 14px", borderRadius: 8,
          background: result.success ? "#f0fdf4" : "#fef2f2",
          border: `1px solid ${result.success ? "#bbf7d0" : "#fecaca"}`,
          color: result.success ? "#166534" : "#dc2626", fontSize: ".82rem" }}>
          {result.success ? (
            <span>✓ {result.message || `Assigned: ${result.assigned ?? ""} Skipped: ${result.skipped ?? ""} Failed: ${result.failed ?? ""} Granted: ${result.granted ?? ""} Created: ${result.created ?? ""}`}</span>
          ) : (
            <span>✗ {result.error}</span>
          )}
        </div>
      )}

      {/* ── Assign Teacher ── */}
      {tab === "assign" && (
        <div style={cardStyle}>
          <h4 style={{ margin: "0 0 12px", fontSize: ".92rem" }}>Bulk Assign Students to Teacher</h4>
          <label style={{ display: "block", marginBottom: 10 }}>
            <span style={{ fontSize: ".82rem", fontWeight: 600 }}>Select Teacher</span>
            <select value={selectedTeacherId} onChange={e => setSelectedTeacherId(e.target.value)} style={{ ...inputStyle, marginTop: 4 }}>
              <option value="">— choose teacher —</option>
              {allTeachers.map(t => <option key={t.id} value={t.id}>{t.username} ({t.email})</option>)}
            </select>
          </label>
          <div style={{ marginBottom: 10 }}>
            <span style={{ fontSize: ".82rem", fontWeight: 600 }}>Select Students</span>
            <div style={{ marginTop: 4 }}>
              <CheckList items={allStudents} selected={selectedStudents} onToggle={toggleStudent} />
            </div>
          </div>
          <button onClick={runBulkAssign} disabled={loading || !selectedTeacherId || selectedStudents.size === 0}
            className="primary-btn" style={{ marginTop: 4 }}>
            {loading ? "Assigning…" : `Assign ${selectedStudents.size} Student(s)`}
          </button>
        </div>
      )}

      {/* ── Reset Passwords ── */}
      {tab === "reset" && (
        <div style={cardStyle}>
          <h4 style={{ margin: "0 0 12px", fontSize: ".92rem" }}>Bulk Reset Passwords</h4>
          <p style={{ color: "var(--muted, #64748b)", fontSize: ".82rem", marginBottom: 10 }}>
            New temporary passwords will be generated server-side and shown <strong>once only</strong>.
          </p>
          <CheckList items={allStudents} selected={selectedStudents} onToggle={toggleStudent} />
          <button onClick={runBulkReset} disabled={loading || selectedStudents.size === 0}
            className="danger-btn" style={{ marginTop: 12 }}>
            {loading ? "Resetting…" : `Reset ${selectedStudents.size} Password(s)`}
          </button>
          {/* Show generated passwords */}
          {result?.results?.filter(r => r.success && r.temp_password).map((r, i) => (
            <div key={i} style={{ marginTop: 6, padding: "6px 10px", background: "var(--surface2, #f8fafc)", borderRadius: 7, fontSize: ".78rem" }}>
              <strong>{r.username}</strong> / {r.email} → <code style={{ color: "#f59e0b" }}>{r.temp_password}</code>
            </div>
          ))}
        </div>
      )}

      {/* ── Grant Access ── */}
      {tab === "grant" && (
        <div style={cardStyle}>
          <h4 style={{ margin: "0 0 12px", fontSize: ".92rem" }}>Bulk Grant Access</h4>
          <p style={{ color: "var(--muted, #64748b)", fontSize: ".82rem", marginBottom: 10 }}>
            Sets <strong>Platform Access</strong> on selected users. Active paid subscriptions are skipped. Use this to manually enable access for users who need it.
          </p>
          <CheckList items={allUsers} selected={selectedUsers} onToggle={toggleUser} />
          <button onClick={runBulkGrant} disabled={loading || selectedUsers.size === 0}
            className="primary-btn" style={{ marginTop: 12 }}>
            {loading ? "Granting…" : `Grant Platform Access to ${selectedUsers.size} User(s)`}
          </button>
        </div>
      )}

      {/* ── Export ── */}
      {tab === "export" && (
        <div style={cardStyle}>
          <h4 style={{ margin: "0 0 12px", fontSize: ".92rem" }}>Bulk Export Users</h4>
          <p style={{ color: "var(--muted, #64748b)", fontSize: ".82rem", marginBottom: 10 }}>
            Exports selected users as CSV. No secrets, passwords, or tokens included.
          </p>
          <CheckList items={allUsers} selected={selectedUsers} onToggle={toggleUser} />
          <button onClick={runBulkExport} disabled={loading || selectedUsers.size === 0}
            className="primary-btn" style={{ marginTop: 12 }}>
            {loading ? "Exporting…" : `Export ${selectedUsers.size} User(s) as CSV`}
          </button>
        </div>
      )}

      {/* ── Import CSV ── */}
      {tab === "import" && (
        <div style={cardStyle}>
          <h4 style={{ margin: "0 0 12px", fontSize: ".92rem" }}>Import Students from CSV</h4>
          <p style={{ color: "var(--muted, #64748b)", fontSize: ".82rem", marginBottom: 6 }}>
            CSV columns: <code>name</code> (required), <code>grade</code>, <code>email</code>, <code>temporary_password</code>
          </p>
          <p style={{ fontSize: ".75rem", color: "var(--muted, #94a3b8)", marginBottom: 10 }}>
            Example: <code>name,grade,email</code><br/>
            <code>Arjun Sharma,Grade 8,arjun@example.com</code>
          </p>
          <textarea
            value={csvText}
            onChange={e => setCsvText(e.target.value)}
            placeholder="Paste CSV content here…"
            style={{ ...inputStyle, height: 140, resize: "vertical", marginBottom: 8 }}
            data-testid="csv-import-textarea"
          />
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button onClick={handleCsvPreview} disabled={!csvText.trim()}
              className="secondary-btn">
              👁 Preview & Validate
            </button>
            {csvPreview && csvPreview.every(r => r.errors.length === 0) && (
              <button onClick={() => runCsvImport(true)} disabled={loading}
                className="primary-btn">
                {loading ? "Importing…" : `✅ Import ${csvPreview.length} Student(s)`}
              </button>
            )}
          </div>

          {/* Preview table */}
          {csvPreview && (
            <div style={{ marginTop: 12, overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: ".78rem" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--border, #e5e7eb)", color: "var(--muted, #64748b)" }}>
                    <th style={{ padding: "4px 8px", textAlign: "left" }}>Row</th>
                    <th style={{ padding: "4px 8px", textAlign: "left" }}>Name</th>
                    <th style={{ padding: "4px 8px", textAlign: "left" }}>Grade</th>
                    <th style={{ padding: "4px 8px", textAlign: "left" }}>Email</th>
                    <th style={{ padding: "4px 8px", textAlign: "left" }}>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {csvPreview.map((r) => (
                    <tr key={r.row} style={{ borderBottom: "1px solid var(--border, #f1f5f9)", background: r.errors.length ? "#fef2f2" : "transparent" }}>
                      <td style={{ padding: "4px 8px" }}>{r.row}</td>
                      <td style={{ padding: "4px 8px", fontWeight: 600 }}>{r.name}</td>
                      <td style={{ padding: "4px 8px" }}>{r.grade}</td>
                      <td style={{ padding: "4px 8px", color: "var(--muted, #94a3b8)" }}>{r.email || "—"}</td>
                      <td style={{ padding: "4px 8px" }}>
                        {r.errors.length > 0 ? (
                          <span style={{ color: "#dc2626", fontWeight: 600 }}>✗ {r.errors.join(", ")}</span>
                        ) : (
                          <span style={{ color: "#166534" }}>✓ OK</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Import results */}
          {result?.results && (
            <div style={{ marginTop: 12 }}>
              {result.results.filter(r => r.success && r.temp_password).map((r, i) => (
                <div key={i} style={{ padding: "5px 10px", background: "var(--surface2, #f8fafc)", borderRadius: 6, fontSize: ".75rem", marginBottom: 4 }}>
                  Row {r.row}: <strong>{r.name}</strong> / {r.email} → <code style={{ color: "#f59e0b" }}>{r.temp_password}</code>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
