/**
 * AdminQuickActions.jsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Quick-action shortcut cards on the Admin Console Overview tab.
 *
 * Each card navigates to the correct tab (via handleTabChange) and optionally
 * focuses a section anchor on that tab.
 *
 * Props:
 *  handleTabChange(tabKey)  — provided by AdminControlPage
 *  exportUsersCSV()         — existing export function
 *  onPinToggle(action)      — optional: notify AdminFavorites of pin change
 *  pinnedIds                — Set of pinned action ids (from AdminFavorites)
 */

import { useState } from "react";

const QUICK_ACTIONS = [
  {
    id: "create-parent",
    icon: "👨‍👩‍👧",
    label: "Create Parent",
    description: "Add a new family with a parent account",
    tab: "accounts",
    anchor: "create-parent-form",
    color: "#6366f1",
  },
  {
    id: "create-teacher",
    icon: "🎓",
    label: "Create Teacher",
    description: "Add a teacher login for a school or independent tutor",
    tab: "accounts",
    anchor: "create-teacher-form",
    color: "#10b981",
  },
  {
    id: "create-student",
    icon: "📚",
    label: "Create Student",
    description: "Add a standalone student account",
    tab: "accounts",
    anchor: "create-student-form",
    color: "#f59e0b",
  },
  {
    id: "create-offer-code",
    icon: "🎟️",
    label: "Create Offer Code",
    description: "Generate a new access code for students",
    tab: "offers",
    anchor: "create-offer-form",
    color: "#8b5cf6",
  },
  {
    id: "run-expiry-job",
    icon: "⏰",
    label: "Run Expiry Job",
    description: "Trigger subscription expiry check now",
    tab: "operations",
    anchor: "expiry-job",
    color: "#ef4444",
  },
  {
    id: "export-users",
    icon: "📥",
    label: "Export Users",
    description: "Download all users as a CSV file",
    tab: null,      // handled inline
    anchor: null,
    color: "#0ea5e9",
  },
];

export default function AdminQuickActions({
  handleTabChange,
  exportUsersCSV,
  onPinToggle = null,
  pinnedIds = new Set(),
}) {
  const [hovered, setHovered] = useState(null);

  function handleAction(action) {
    if (action.id === "export-users") {
      exportUsersCSV?.();
      return;
    }
    if (action.tab) {
      handleTabChange(action.tab);
      // Focus the anchor element after the tab panel mounts
      if (action.anchor) {
        requestAnimationFrame(() => {
          setTimeout(() => {
            const el = document.getElementById(action.anchor);
            if (el) {
              el.scrollIntoView({ behavior: "smooth", block: "start" });
              el.focus?.();
            }
          }, 80);
        });
      }
    }
  }

  return (
    <div data-testid="admin-quick-actions">
      <div style={{ marginBottom: 12, display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
        <h3 style={{ margin: 0, fontSize: ".95rem", fontWeight: 700, color: "var(--text, #1e293b)" }}>
          ⚡ Quick Actions
        </h3>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))",
          gap: 10,
        }}
      >
        {QUICK_ACTIONS.map((action) => {
          const isPinned = pinnedIds.has(action.id);
          const isHov = hovered === action.id;
          return (
            // Use div+role="button" so the optional pin <button> doesn't nest inside a <button>
            <div
              key={action.id}
              role="button"
              tabIndex={0}
              data-testid={`quick-action-${action.id}`}
              aria-label={action.label}
              onMouseEnter={() => setHovered(action.id)}
              onMouseLeave={() => setHovered(null)}
              onClick={() => handleAction(action)}
              onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); handleAction(action); } }}
              style={{
                position: "relative",
                display: "flex",
                flexDirection: "column",
                alignItems: "flex-start",
                gap: 6,
                padding: "12px 14px",
                background: isHov ? `${action.color}14` : "var(--panel, #fff)",
                border: `1.5px solid ${isHov ? action.color : "var(--border, #e5e7eb)"}`,
                borderRadius: 10,
                cursor: "pointer",
                fontFamily: "inherit",
                textAlign: "left",
                transition: "all 0.15s",
                minHeight: 80,
              }}
            >
              <span style={{ fontSize: "1.4rem", lineHeight: 1 }}>{action.icon}</span>
              <span style={{ fontSize: ".82rem", fontWeight: 700, color: isHov ? action.color : "var(--text, #1e293b)", lineHeight: 1.2 }}>
                {action.label}
              </span>
              <span style={{ fontSize: ".72rem", color: "var(--muted, #64748b)", lineHeight: 1.3 }}>
                {action.description}
              </span>

              {/* Pin/unpin — proper <button> since it's no longer inside a <button> */}
              {onPinToggle && (
                <button
                  aria-label={isPinned ? `Unpin ${action.label}` : `Pin ${action.label}`}
                  data-testid={`pin-${action.id}`}
                  onClick={(e) => {
                    e.stopPropagation();
                    onPinToggle(action);
                  }}
                  style={{
                    position: "absolute",
                    top: 6,
                    right: 6,
                    background: "none",
                    border: "none",
                    cursor: "pointer",
                    fontSize: ".75rem",
                    opacity: isPinned || isHov ? 1 : 0.3,
                    transition: "opacity 0.15s",
                    padding: 2,
                  }}
                >
                  {isPinned ? "📌" : "📍"}
                </button>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// Export the action list for use in AdminFavorites seed
export { QUICK_ACTIONS };
