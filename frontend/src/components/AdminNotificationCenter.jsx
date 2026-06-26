/**
 * AdminNotificationCenter.jsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Badge + dropdown notification panel in the Admin Console tab nav.
 *
 * Sources: GET /api/admin/operations/notifications
 * Sanitised: counts only, no secrets, raw payloads, or user identifiers.
 *
 * Props:
 *  accessToken            — admin JWT
 *  onNavigate(tabKey)     — navigate to a tab when notification clicked
 */

import { useEffect, useRef, useState } from "react";
import { getNotifications } from "../api/adminOperations";

const SEVERITY_COLOR = {
  error:   "#ef4444",
  warning: "#f59e0b",
  info:    "#6366f1",
};

export default function AdminNotificationCenter({ accessToken, onNavigate }) {
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading]             = useState(false);
  const [open, setOpen]                   = useState(false);
  const [error, setError]                 = useState(null);
  const dropdownRef                       = useRef(null);

  // Fetch on mount and every 5 minutes
  function fetchNotifications() {
    if (!accessToken) return;
    setLoading(true);
    getNotifications()
      .then((data) => {
        setNotifications(data.notifications || []);
        setError(null);
      })
      .catch((err) => setError(err?.message || "Failed to load notifications"))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 5 * 60 * 1000);
    return () => clearInterval(interval);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accessToken]);

  // Close on outside click
  useEffect(() => {
    function handle(e) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", handle);
    return () => document.removeEventListener("mousedown", handle);
  }, []);

  const count = notifications.length;
  const hasError = notifications.some((n) => n.severity === "error");
  const badgeColor = hasError ? "#ef4444" : count > 0 ? "#f59e0b" : "#22c55e";

  return (
    <div ref={dropdownRef} style={{ position: "relative" }} data-testid="admin-notification-center">
      {/* Bell button */}
      <button
        aria-label={`Notifications${count > 0 ? ` — ${count} active` : " — none"}`}
        aria-expanded={open}
        aria-haspopup="true"
        data-testid="notification-bell"
        onClick={() => setOpen((o) => !o)}
        style={{
          position: "relative",
          background: "none",
          border: "none",
          cursor: "pointer",
          padding: "6px 8px",
          borderRadius: 8,
          fontSize: "1.1rem",
          lineHeight: 1,
          color: open ? "var(--primary, #6366f1)" : "var(--muted, #64748b)",
        }}
      >
        🔔
        {/* Badge */}
        <span
          data-testid="notification-badge"
          aria-hidden="true"
          style={{
            position: "absolute",
            top: 2,
            right: 2,
            width: 14,
            height: 14,
            borderRadius: "50%",
            background: badgeColor,
            border: "2px solid var(--panel, #fff)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: ".55rem",
            fontWeight: 800,
            color: "#fff",
            lineHeight: 1,
          }}
        >
          {count > 9 ? "9+" : count}
        </span>
      </button>

      {/* Dropdown panel */}
      {open && (
        <div
          data-testid="notification-dropdown"
          role="dialog"
          aria-label="Notifications"
          style={{
            position: "absolute",
            top: "calc(100% + 4px)",
            right: 0,
            width: 320,
            background: "var(--panel, #fff)",
            border: "1px solid var(--border, #e5e7eb)",
            borderRadius: 12,
            boxShadow: "0 8px 24px rgba(0,0,0,0.14)",
            zIndex: 200,
            overflow: "hidden",
          }}
        >
          <div style={{ padding: "10px 14px", borderBottom: "1px solid var(--border, #f1f5f9)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <strong style={{ fontSize: ".88rem", color: "var(--text, #1e293b)" }}>🔔 Notifications</strong>
            <button
              onClick={() => { fetchNotifications(); }}
              disabled={loading}
              style={{ background: "none", border: "none", cursor: loading ? "not-allowed" : "pointer", fontSize: ".75rem", color: "var(--primary, #6366f1)", fontFamily: "inherit", padding: 0 }}
            >
              {loading ? "Loading…" : "↺ Refresh"}
            </button>
          </div>

          <div style={{ maxHeight: 280, overflowY: "auto" }}>
            {error && (
              <div style={{ padding: "10px 14px", color: "#dc2626", fontSize: ".8rem" }}>⚠ {error}</div>
            )}
            {!error && notifications.length === 0 && (
              <div data-testid="notification-empty" style={{ padding: "16px 14px", color: "var(--muted, #64748b)", fontSize: ".82rem", textAlign: "center" }}>
                ✅ No active alerts — all systems normal.
              </div>
            )}
            {notifications.map((n, i) => (
              <button
                key={`notif-${i}`}
                data-testid={`notification-item-${n.type}`}
                onClick={() => { onNavigate?.(n.link_tab || "operations"); setOpen(false); }}
                style={{
                  width: "100%",
                  display: "flex",
                  alignItems: "flex-start",
                  gap: 10,
                  padding: "10px 14px",
                  background: "none",
                  border: "none",
                  borderBottom: "1px solid var(--border, #f1f5f9)",
                  cursor: "pointer",
                  textAlign: "left",
                  fontFamily: "inherit",
                }}
                onMouseEnter={(e) => e.currentTarget.style.background = "var(--surface2, #f8fafc)"}
                onMouseLeave={(e) => e.currentTarget.style.background = "none"}
              >
                <span
                  style={{
                    width: 8,
                    height: 8,
                    borderRadius: "50%",
                    background: SEVERITY_COLOR[n.severity] || SEVERITY_COLOR.info,
                    flexShrink: 0,
                    marginTop: 5,
                  }}
                />
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: ".82rem", fontWeight: 600, color: "var(--text, #1e293b)", lineHeight: 1.3 }}>
                    {n.message}
                  </div>
                  <div style={{ fontSize: ".72rem", color: "var(--muted, #94a3b8)", marginTop: 2 }}>
                    → Go to {n.link_tab || "operations"} tab
                  </div>
                </div>
              </button>
            ))}
          </div>

          <div style={{ padding: "8px 14px", borderTop: "1px solid var(--border, #f1f5f9)" }}>
            <button
              onClick={() => { onNavigate?.("operations"); setOpen(false); }}
              data-testid="notification-view-operations"
              style={{ background: "none", border: "none", cursor: "pointer", color: "var(--primary, #6366f1)", fontSize: ".78rem", fontWeight: 600, fontFamily: "inherit", padding: 0 }}
            >
              View Operations Dashboard →
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
