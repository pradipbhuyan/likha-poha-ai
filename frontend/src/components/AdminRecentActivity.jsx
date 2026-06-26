/**
 * AdminRecentActivity.jsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Fetches and displays recent platform audit events as human-readable entries.
 * Sanitised: no metadata, secrets, passwords, or tokens.
 *
 * Props:
 *  accessToken  — admin JWT for API auth
 *  onViewMore() — optional: navigate to Operations tab
 */

import { useEffect, useState } from "react";
import { getRecentActivity } from "../api/adminOperations";

const SEVERITY_STYLES = {
  error:   { bg: "#fef2f2", color: "#dc2626", dot: "#ef4444" },
  warning: { bg: "#fffbeb", color: "#92400e", dot: "#f59e0b" },
  success: { bg: "#f0fdf4", color: "#166534", dot: "#22c55e" },
  info:    { bg: "var(--surface2, #f8fafc)", color: "var(--muted, #64748b)", dot: "#94a3b8" },
};

function timeAgo(ts) {
  if (!ts) return "";
  try {
    const diff = Math.floor((Date.now() - new Date(ts + "Z").getTime()) / 1000);
    if (diff < 60)   return `${diff}s ago`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
  } catch { return ts; }
}

export default function AdminRecentActivity({ accessToken, onViewMore }) {
  const [activities, setActivities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!accessToken) return;
    setLoading(true);
    setError(null);
    getRecentActivity(20)
      .then((data) => {
        setActivities(data.activities || []);
        if (data.error) setError(data.error);
      })
      .catch((err) => setError(err?.message || "Failed to load recent activity"))
      .finally(() => setLoading(false));
  }, [accessToken]);

  return (
    <div data-testid="admin-recent-activity">
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12, flexWrap: "wrap", gap: 8 }}>
        <h3 style={{ margin: 0, fontSize: ".95rem", fontWeight: 700, color: "var(--text, #1e293b)" }}>
          🕐 Recent Activity
        </h3>
        {onViewMore && (
          <button
            onClick={onViewMore}
            data-testid="recent-activity-view-more"
            style={{
              background: "none",
              border: "none",
              cursor: "pointer",
              color: "var(--primary, #6366f1)",
              fontSize: ".78rem",
              fontWeight: 600,
              fontFamily: "inherit",
              padding: 0,
            }}
          >
            View all in Operations →
          </button>
        )}
      </div>

      {loading && (
        <div data-testid="recent-activity-loading" style={{ color: "var(--muted, #64748b)", fontSize: ".82rem", padding: "10px 0" }}>
          Loading recent activity…
        </div>
      )}

      {!loading && error && (
        <div data-testid="recent-activity-error" style={{ color: "#dc2626", fontSize: ".82rem", padding: "8px 12px", background: "#fef2f2", borderRadius: 8, border: "1px solid #fecaca" }}>
          ⚠ {error}
        </div>
      )}

      {!loading && !error && activities.length === 0 && (
        <div data-testid="recent-activity-empty" style={{ color: "var(--muted, #64748b)", fontSize: ".82rem", padding: "10px 0" }}>
          No recent activity.
        </div>
      )}

      {!loading && activities.length > 0 && (
        <div
          data-testid="recent-activity-list"
          style={{ display: "flex", flexDirection: "column", gap: 4, maxHeight: 320, overflowY: "auto" }}
        >
          {activities.map((a, i) => {
            const style = SEVERITY_STYLES[a.severity] || SEVERITY_STYLES.info;
            return (
              <div
                key={`${a.event_type}-${i}`}
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: 10,
                  padding: "7px 10px",
                  borderRadius: 7,
                  background: style.bg,
                  border: `1px solid ${style.dot}22`,
                }}
              >
                {/* Severity dot */}
                <span
                  aria-hidden="true"
                  style={{
                    width: 8,
                    height: 8,
                    borderRadius: "50%",
                    background: style.dot,
                    flexShrink: 0,
                    marginTop: 5,
                  }}
                />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <span style={{ fontSize: ".82rem", fontWeight: 600, color: style.color }}>
                    {a.summary}
                  </span>
                  {a.entity_type && (
                    <span style={{ fontSize: ".72rem", color: "var(--muted, #94a3b8)", marginLeft: 6 }}>
                      · {a.entity_type}
                    </span>
                  )}
                </div>
                <span
                  style={{ fontSize: ".7rem", color: "var(--muted, #94a3b8)", whiteSpace: "nowrap", flexShrink: 0 }}
                  title={a.timestamp}
                >
                  {timeAgo(a.timestamp)}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
