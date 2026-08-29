/**
 * AdminSupportTools.jsx — Admin support tools: user search, profile summary,
 * subscription/audit history, and password reset.
 *
 * UI states: idle | loading | results | no-results | error | detail-loading | detail
 * No .json() called on already-parsed responses — uses raw fetch + .json().
 * Props: accessToken
 */
import { useState, useEffect, useCallback } from "react";

const API = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function apiFetch(path, token) {
  const r = await fetch(`${API}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!r.ok) {
    const body = await r.json().catch(() => ({}));
    throw new Error(body.detail || body.error || `HTTP ${r.status}`);
  }
  return r.json();
}

async function apiPost(path, token) {
  const r = await fetch(`${API}${path}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!r.ok) {
    const body = await r.json().catch(() => ({}));
    throw new Error(body.detail || body.error || `HTTP ${r.status}`);
  }
  return r.json();
}

const TAG = { fontSize: ".72rem", padding: "2px 7px", borderRadius: 5, fontWeight: 600 };
const ROLE_COLOR = {
  student: "#6366f1", parent: "#10b981", teacher: "#f59e0b", admin: "#ef4444",
};

function Section({ title, children }) {
  return (
    <div style={{ background: "var(--panel,#fff)", border: "1px solid var(--border,#e5e7eb)", borderRadius: 10, padding: "14px 16px", marginBottom: 12 }}>
      <h4 style={{ margin: "0 0 10px", fontSize: ".88rem", fontWeight: 700 }}>{title}</h4>
      {children}
    </div>
  );
}

// ── Search states ─────────────────────────────────────────────────────────────
const S_IDLE        = "idle";
const S_LOADING     = "loading";
const S_RESULTS     = "results";
const S_NO_RESULTS  = "no_results";
const S_ERROR       = "error";
const S_DETAIL_LOAD = "detail_loading";

export default function AdminSupportTools({ accessToken }) {
  const [query, setQuery]         = useState("");
  const [searchState, setSearchState] = useState(S_IDLE);
  const [searchErr, setSearchErr] = useState(null);
  const [results, setResults]     = useState([]);
  const [lastQuery, setLastQuery] = useState("");

  const [selected, setSelected]   = useState(null);
  const [detailState, setDetailState] = useState(S_IDLE);
  const [summary, setSummary]     = useState(null);
  const [subHistory, setSubHistory] = useState(null);
  const [auditHist, setAudit]     = useState(null);

  const [actionMsg, setActionMsg] = useState(null);
  const [resetResult, setResetResult] = useState(null);

  // ── Pending teacher approvals ─────────────────────────────────────────────────
  const [pendingTeachers, setPendingTeachers] = useState([]);
  const [pendingState, setPendingState] = useState(S_IDLE);
  const [pendingActioningId, setPendingActioningId] = useState(null);

  const loadPendingTeachers = useCallback(async () => {
    setPendingState(S_LOADING);
    try {
      const d = await apiFetch("/api/admin/support/pending-teachers", accessToken);
      setPendingTeachers(d.teachers || []);
      setPendingState(S_IDLE);
    } catch {
      setPendingState(S_ERROR);
    }
  }, [accessToken]);

  useEffect(() => { loadPendingTeachers(); }, [loadPendingTeachers]);

  async function approveTeacher(userId) {
    setPendingActioningId(userId);
    try {
      const d = await apiPost(`/api/admin/support/users/${userId}/verify-teacher`, accessToken);
      if (d.success) {
        setPendingTeachers((prev) => prev.filter((t) => t.id !== userId));
      } else {
        setActionMsg(`⚠ ${d.error || "Could not verify teacher"}`);
      }
    } catch (e) {
      setActionMsg(`⚠ ${e.message}`);
    } finally {
      setPendingActioningId(null);
    }
  }

  // ── Pending principal / school approvals ──────────────────────────────────────
  const [pendingSchools, setPendingSchools] = useState([]);
  const [pendingSchoolsState, setPendingSchoolsState] = useState(S_IDLE);
  const [pendingSchoolActioningId, setPendingSchoolActioningId] = useState(null);
  const [pendingSchoolActionMsg, setPendingSchoolActionMsg] = useState(null);

  const loadPendingSchools = useCallback(async () => {
    setPendingSchoolsState(S_LOADING);
    try {
      const d = await apiFetch("/api/admin/schools/pending", accessToken);
      setPendingSchools(d.schools || []);
      setPendingSchoolsState(S_IDLE);
    } catch {
      setPendingSchoolsState(S_ERROR);
    }
  }, [accessToken]);

  useEffect(() => { loadPendingSchools(); }, [loadPendingSchools]);

  async function approveSchool(schoolId) {
    setPendingSchoolActioningId(schoolId);
    setPendingSchoolActionMsg(null);
    try {
      const d = await apiPost(`/api/admin/schools/${schoolId}/verify`, accessToken);
      if (d.success) {
        setPendingSchools((prev) => prev.filter((s) => s.id !== schoolId));
      } else {
        setPendingSchoolActionMsg(`⚠ ${d.error || "Could not verify school"}`);
      }
    } catch (e) {
      setPendingSchoolActionMsg(`⚠ ${e.message}`);
    } finally {
      setPendingSchoolActioningId(null);
    }
  }

  async function rejectSchool(schoolId) {
    if (!window.confirm("Reject this school? The principal's join code will stop working for new links.")) return;
    setPendingSchoolActioningId(schoolId);
    setPendingSchoolActionMsg(null);
    try {
      const d = await apiPost(`/api/admin/schools/${schoolId}/reject`, accessToken);
      if (d.success) {
        setPendingSchools((prev) => prev.filter((s) => s.id !== schoolId));
      } else {
        setPendingSchoolActionMsg(`⚠ ${d.error || "Could not reject school"}`);
      }
    } catch (e) {
      setPendingSchoolActionMsg(`⚠ ${e.message}`);
    } finally {
      setPendingSchoolActioningId(null);
    }
  }

  // ── Search ──────────────────────────────────────────────────────────────────
  async function doSearch() {
    const q = query.trim();
    if (!q) return;
    setSearchState(S_LOADING);
    setSearchErr(null);
    setLastQuery(q);
    try {
      const d = await apiFetch(
        `/api/admin/support/user-search?q=${encodeURIComponent(q)}&limit=20`,
        accessToken,
      );
      const users = d.users || [];
      setResults(users);
      setSearchState(users.length > 0 ? S_RESULTS : S_NO_RESULTS);
    } catch (e) {
      setSearchErr(e.message || "Search failed");
      setSearchState(S_ERROR);
      setResults([]);
    }
  }

  // ── Load user detail ────────────────────────────────────────────────────────
  async function loadUser(user) {
    setSelected(user);
    setSummary(null);
    setSubHistory(null);
    setAudit(null);
    setActionMsg(null);
    setResetResult(null);
    setDetailState(S_DETAIL_LOAD);

    const [s, sh, ah] = await Promise.all([
      apiFetch(`/api/admin/support/users/${user.id}/summary`, accessToken).catch((e) => ({ success: false, _err: e.message })),
      apiFetch(`/api/admin/support/users/${user.id}/subscription-history`, accessToken).catch(() => null),
      apiFetch(`/api/admin/support/users/${user.id}/audit-history`, accessToken).catch(() => null),
    ]);
    setSummary(s);
    setSubHistory(sh);
    setAudit(ah);
    setDetailState(S_RESULTS);
  }

  function goBack() {
    setSelected(null);
    setSummary(null);
    setSubHistory(null);
    setAudit(null);
    setDetailState(S_IDLE);
  }

  // ── Actions ─────────────────────────────────────────────────────────────────
  async function doResetPassword() {
    if (!selected) return;
    if (!window.confirm(`Reset password for ${selected.username}? New temp password shown once only.`)) return;
    setResetResult(null);
    try {
      const d = await apiPost(
        `/api/admin/support/students/${selected.id}/reset-password`,
        accessToken,
      );
      setResetResult(d);
    } catch (e) {
      setResetResult({ success: false, error: e.message });
    }
  }

  async function doResendWelcome() {
    if (!selected) return;
    setActionMsg(null);
    try {
      const d = await apiPost(
        `/api/admin/support/users/${selected.id}/resend-welcome`,
        accessToken,
      );
      setActionMsg(d.invite_sent ? "✅ Welcome invite sent." : `ℹ ${d.note || "Done."}`);
    } catch (e) {
      setActionMsg(`⚠ ${e.message}`);
    }
  }

  const isStudent = selected?.role === "student" || selected?.role === "child";
  const rs = summary?.resolved_subscription;

  return (
    <div data-testid="admin-support-tools">
      {/* ── Pending teacher approvals ────────────────────────────────────── */}
      {!selected && pendingState === S_LOADING && (
        <div style={{ color: "var(--muted,#94a3b8)", fontSize: ".8rem", marginBottom: 8 }}>
          Checking for pending teacher signups…
        </div>
      )}
      {!selected && pendingTeachers.length > 0 && (
        <Section title={`Pending Teacher Approvals (${pendingTeachers.length})`}>
          <div data-testid="pending-teachers-list" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {pendingTeachers.map((t) => (
              <div key={t.id} data-testid={`pending-teacher-${t.id}`}
                style={{
                  display: "flex", alignItems: "center", justifyContent: "space-between",
                  gap: 10, padding: "8px 10px", borderRadius: 7,
                  border: "1px solid var(--border,#e5e7eb)", background: "var(--surface2,#f8fafc)",
                }}>
                <div style={{ fontSize: ".82rem" }}>
                  <strong>{t.username}</strong> — {t.email}
                  <div style={{ color: "var(--muted,#94a3b8)", fontSize: ".76rem" }}>
                    {t.school_name || "No school provided"}
                  </div>
                </div>
                <button
                  onClick={() => approveTeacher(t.id)}
                  disabled={pendingActioningId === t.id}
                  data-testid={`approve-teacher-${t.id}`}
                  className="primary-btn"
                >
                  {pendingActioningId === t.id ? "Approving…" : "Approve"}
                </button>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* ── Pending principal / school approvals ─────────────────────────── */}
      {!selected && pendingSchoolsState === S_LOADING && (
        <div style={{ color: "var(--muted,#94a3b8)", fontSize: ".8rem", marginBottom: 8 }}>
          Checking for pending school signups…
        </div>
      )}
      {!selected && pendingSchools.length > 0 && (
        <Section title={`Pending School Approvals (${pendingSchools.length})`}>
          {pendingSchoolActionMsg && (
            <div data-testid="pending-school-action-msg" style={{ marginBottom: 8, fontSize: ".82rem", color: "#b45309" }}>
              {pendingSchoolActionMsg}
            </div>
          )}
          <div data-testid="pending-schools-list" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {pendingSchools.map((s) => (
              <div key={s.id} data-testid={`pending-school-${s.id}`}
                style={{
                  display: "flex", alignItems: "center", justifyContent: "space-between",
                  gap: 10, padding: "8px 10px", borderRadius: 7,
                  border: "1px solid var(--border,#e5e7eb)", background: "var(--surface2,#f8fafc)",
                }}>
                <div style={{ fontSize: ".82rem" }}>
                  <strong>{s.name}</strong>
                  {s.school_code && <span style={{ fontFamily: "monospace", marginLeft: 8, color: "var(--muted,#94a3b8)" }}>{s.school_code}</span>}
                  <div style={{ color: "var(--muted,#94a3b8)", fontSize: ".76rem" }}>
                    Principal: {s.principal_username || "—"} ({s.principal_email || "no email"})
                    {(s.city || s.state) && ` · ${[s.city, s.state].filter(Boolean).join(", ")}`}
                    {s.udise_code && ` · UDISE ${s.udise_code}`}
                  </div>
                </div>
                <div style={{ display: "flex", gap: 6 }}>
                  <button
                    onClick={() => rejectSchool(s.id)}
                    disabled={pendingSchoolActioningId === s.id}
                    data-testid={`reject-school-${s.id}`}
                    style={{ padding: "6px 12px", borderRadius: 6, border: "1px solid var(--border,#e5e7eb)", background: "var(--panel,#fff)", cursor: "pointer", fontFamily: "inherit", fontSize: ".82rem" }}
                  >
                    Reject
                  </button>
                  <button
                    onClick={() => approveSchool(s.id)}
                    disabled={pendingSchoolActioningId === s.id}
                    data-testid={`approve-school-${s.id}`}
                    className="primary-btn"
                  >
                    {pendingSchoolActioningId === s.id ? "Approving…" : "Approve"}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* ── Search bar ──────────────────────────────────────────────────── */}
      <div style={{ display: "flex", gap: 8, marginBottom: 12, flexWrap: "wrap" }}>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && doSearch()}
          placeholder="Search user by name or email…"
          data-testid="support-search-input"
          style={{
            flex: 1, minWidth: 200, padding: "8px 10px", borderRadius: 7,
            border: "1px solid var(--border,#e5e7eb)", fontFamily: "inherit", fontSize: ".85rem",
            background: "var(--surface2,#f8fafc)", color: "var(--text,#1e293b)",
          }}
        />
        <button
          onClick={doSearch}
          disabled={searchState === S_LOADING || !query.trim()}
          className="primary-btn"
          aria-label="search"
        >
          {searchState === S_LOADING ? "Searching…" : "Search"}
        </button>
        {selected && (
          <button
            onClick={goBack}
            style={{ padding: "6px 12px", borderRadius: 6, border: "1px solid var(--border,#e5e7eb)", background: "var(--panel,#fff)", cursor: "pointer", fontFamily: "inherit", fontSize: ".82rem" }}>
            ← Back
          </button>
        )}
      </div>

      {/* ── Search state messages ────────────────────────────────────────── */}
      {!selected && (
        <>
          {searchState === S_IDLE && (
            <div data-testid="search-idle"
              style={{ color: "var(--muted,#94a3b8)", fontSize: ".82rem", padding: "8px 0" }}>
              Enter a name or email address above and press Search or Enter.
            </div>
          )}

          {searchState === S_LOADING && (
            <div data-testid="search-loading"
              style={{ color: "var(--muted,#94a3b8)", fontSize: ".82rem", padding: "8px 0" }}>
              Searching…
            </div>
          )}

          {searchState === S_ERROR && (
            <div data-testid="search-error"
              style={{ color: "#dc2626", fontSize: ".82rem", marginBottom: 8, padding: "8px 12px", background: "rgba(239,68,68,.07)", borderRadius: 7, border: "1px solid rgba(239,68,68,.2)" }}>
              ⚠ {searchErr}
            </div>
          )}

          {searchState === S_NO_RESULTS && (
            <div data-testid="search-no-results"
              style={{ color: "var(--muted,#94a3b8)", fontSize: ".82rem", padding: "10px 14px", background: "var(--surface2,#f8fafc)", borderRadius: 8, border: "1px solid var(--border,#e5e7eb)" }}>
              No users found matching <strong>"{lastQuery}"</strong>. Try a different name or email.
            </div>
          )}

          {/* ── Results list ────────────────────────────────────────────── */}
          {searchState === S_RESULTS && results.map((u) => (
            <div
              key={u.id}
              data-testid={`support-result-${u.id}`}
              style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "9px 14px", borderRadius: 8, background: "var(--surface2,#f8fafc)", border: "1px solid var(--border,#e5e7eb)", marginBottom: 6, flexWrap: "wrap", gap: 6 }}>
              <div>
                <strong style={{ fontSize: ".85rem" }}>{u.username}</strong>
                <span style={{ ...TAG, marginLeft: 8, background: `${ROLE_COLOR[u.role] || "#94a3b8"}22`, color: ROLE_COLOR[u.role] || "#64748b" }}>
                  {u.role}
                </span>
                <div style={{ fontSize: ".72rem", color: "var(--muted,#94a3b8)", marginTop: 2 }}>
                  {u.email} · {u.grade || "—"} · {u.subscription_plan || "free"}
                </div>
              </div>
              <button
                onClick={() => loadUser(u)}
                style={{ padding: "4px 10px", borderRadius: 6, border: "1px solid #6366f1", background: "rgba(99,102,241,.08)", color: "#6366f1", fontWeight: 600, fontSize: ".78rem", cursor: "pointer", fontFamily: "inherit" }}>
                Open
              </button>
            </div>
          ))}
        </>
      )}

      {/* ── Detail loading ───────────────────────────────────────────────── */}
      {selected && detailState === S_DETAIL_LOAD && (
        <div data-testid="detail-loading"
          style={{ color: "var(--muted,#94a3b8)", fontSize: ".82rem", padding: "12px 0" }}>
          Loading user details…
        </div>
      )}

      {/* ── User detail view ─────────────────────────────────────────────── */}
      {selected && detailState === S_RESULTS && summary && (
        <>
          {/* Header */}
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14, flexWrap: "wrap" }}>
            <h3 style={{ margin: 0, fontSize: "1rem" }}>{selected.username}</h3>
            <span style={{ ...TAG, background: `${ROLE_COLOR[selected.role] || "#94a3b8"}22`, color: ROLE_COLOR[selected.role] || "#64748b" }}>
              {selected.role}
            </span>
            <span style={{ fontSize: ".78rem", color: "var(--muted,#94a3b8)" }}>{selected.email}</span>
          </div>

          {/* Summary fetch error */}
          {summary._err && (
            <div style={{ color: "#dc2626", fontSize: ".82rem", marginBottom: 8 }}>
              ⚠ Could not load user summary: {summary._err}
            </div>
          )}

          {/* Resolved subscription */}
          {rs && !rs.error && (
            <Section title="Resolved Subscription State">
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                {[
                  ["Plan", rs.plan_name || rs.subscription_plan],
                  ["Platform Access", rs.access_cbse ? "✓ Active" : "✗ Restricted"],
                  ["Source", rs.source],
                  ["Expires", rs.expires_at ? rs.expires_at.slice(0, 10) : "No expiry"],
                ].map(([k, v]) => (
                  <div key={k} style={{ background: "var(--surface2,#f8fafc)", border: "1px solid var(--border,#e5e7eb)", borderRadius: 7, padding: "7px 12px", minWidth: 90 }}>
                    <div style={{ fontSize: ".7rem", color: "#64748b" }}>{k}</div>
                    <div style={{ fontSize: ".85rem", fontWeight: 700 }}>{v ?? "—"}</div>
                  </div>
                ))}
              </div>
            </Section>
          )}

          {/* Teacher assignments */}
          {summary.teacher_assignments?.length > 0 && (
            <Section title="Teacher Assignments">
              {summary.teacher_assignments.map((a, i) => (
                <div key={i} style={{ fontSize: ".8rem", padding: "4px 0", borderBottom: "1px solid var(--border,#f1f5f9)" }}>
                  Teacher {a.teacher_id} · {a.grade || "—"} · {a.subject || "General"}
                </div>
              ))}
            </Section>
          )}

          {/* Linked children */}
          {summary.linked_children?.length > 0 && (
            <Section title="Linked Children">
              {summary.linked_children.map((c) => (
                <div key={c.id} style={{ fontSize: ".8rem", padding: "4px 0", borderBottom: "1px solid var(--border,#f1f5f9)" }}>
                  {c.username} · {c.grade || "—"}
                </div>
              ))}
            </Section>
          )}

          {/* Subscription timeline */}
          {subHistory?.timeline_events?.length > 0 && (
            <Section title="Subscription Timeline">
              <div style={{ maxHeight: 200, overflowY: "auto" }}>
                {subHistory.timeline_events.map((e, i) => (
                  <div key={i} style={{ display: "flex", gap: 8, padding: "4px 0", borderBottom: "1px solid var(--border,#f1f5f9)", fontSize: ".78rem" }}>
                    <span style={{ color: "var(--muted,#94a3b8)", minWidth: 90 }}>{(e.created_at || "").slice(0, 16)}</span>
                    <span style={{ fontWeight: 600 }}>{e.event_type}</span>
                    {e.from_plan && <span style={{ color: "var(--muted,#94a3b8)" }}>{e.from_plan} → {e.to_plan}</span>}
                  </div>
                ))}
              </div>
            </Section>
          )}

          {/* Payment history */}
          {subHistory?.payment_history?.length > 0 && (
            <Section title="Payment History">
              <div style={{ maxHeight: 180, overflowY: "auto" }}>
                {subHistory.payment_history.map((p, i) => (
                  <div key={i} style={{ display: "flex", gap: 10, padding: "4px 0", borderBottom: "1px solid var(--border,#f1f5f9)", fontSize: ".78rem" }}>
                    <span style={{ color: "var(--muted,#94a3b8)", minWidth: 90 }}>{(p.created_at || "").slice(0, 10)}</span>
                    <span style={{ fontWeight: 600, color: p.status === "paid" ? "#166534" : "#dc2626" }}>{p.status}</span>
                    <span>{p.plan_key}</span>
                    {p.amount && <span style={{ color: "var(--muted,#94a3b8)" }}>₹{p.amount}</span>}
                  </div>
                ))}
              </div>
            </Section>
          )}

          {/* Audit history */}
          {auditHist?.audit_events?.length > 0 && (
            <Section title="Audit History (sanitised)">
              <div style={{ maxHeight: 180, overflowY: "auto" }}>
                {auditHist.audit_events.map((e, i) => (
                  <div key={i} style={{ display: "flex", gap: 8, padding: "4px 0", borderBottom: "1px solid var(--border,#f1f5f9)", fontSize: ".78rem" }}>
                    <span style={{ color: "var(--muted,#94a3b8)", minWidth: 90 }}>{(e.created_at || "").slice(0, 16)}</span>
                    <span style={{ fontWeight: 600 }}>{e.event_type}</span>
                    {e.entity_type && <span style={{ color: "var(--muted,#94a3b8)" }}>{e.entity_type}</span>}
                  </div>
                ))}
              </div>
            </Section>
          )}

          {/* Actions */}
          <Section title="Actions">
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <button onClick={doResendWelcome} className="secondary-btn">📧 Resend Welcome</button>
              {isStudent && (
                <button onClick={doResetPassword} className="danger-btn">🔑 Reset Password</button>
              )}
            </div>
            {actionMsg && <div style={{ marginTop: 8, fontSize: ".82rem", color: "#166534" }}>{actionMsg}</div>}
            {resetResult && (
              <div style={{ marginTop: 8, padding: "8px 12px", borderRadius: 7, background: resetResult.success ? "#f0fdf4" : "#fef2f2", border: `1px solid ${resetResult.success ? "#bbf7d0" : "#fecaca"}`, fontSize: ".82rem" }}>
                {resetResult.success ? (
                  <span>🔑 New temp password for <strong>{resetResult.username}</strong>: <code style={{ color: "#f59e0b", fontWeight: 700 }}>{resetResult.temp_password}</code><br /><small style={{ color: "#64748b" }}>{resetResult.warning}</small></span>
                ) : (
                  <span style={{ color: "#dc2626" }}>✗ {resetResult.error}</span>
                )}
              </div>
            )}
          </Section>
        </>
      )}
    </div>
  );
}
