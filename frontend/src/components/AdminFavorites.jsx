/**
 * AdminFavorites.jsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Pinned/favourited admin actions, persisted in localStorage.
 * Fails gracefully if localStorage is unavailable.
 *
 * Props:
 *  handleTabChange(tabKey)   — navigate to a tab
 *  exportUsersCSV()          — existing export function
 */

import { useEffect, useState } from "react";
import { QUICK_ACTIONS } from "./AdminQuickActions";

const STORAGE_KEY = "admin_console_favorites";

// Default pinned actions shown on first load
const DEFAULT_PINS = ["create-student", "parent-child-assoc", "create-offer-code", "export-users"];

// Extended actions available to pin (includes items not in quick actions)
const ALL_PINNABLE = [
  ...QUICK_ACTIONS,
  { id: "parent-child-assoc", icon: "🔗", label: "Parent-Child Association", tab: "associations", color: "#6366f1" },
  { id: "teacher-student-assoc", icon: "🎓", label: "Teacher-Student Association", tab: "associations", color: "#10b981" },
  { id: "ai-settings", icon: "🔑", label: "AI Settings", tab: "ai", color: "#8b5cf6" },
  { id: "operations-dashboard", icon: "🖥️", label: "Operations Dashboard", tab: "operations", color: "#0ea5e9" },
];

function loadPins() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_PINS;
    return JSON.parse(raw);
  } catch {
    return DEFAULT_PINS;
  }
}

function savePins(ids) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(ids));
  } catch {
    // localStorage unavailable — silently ignore
  }
}

export default function AdminFavorites({ handleTabChange, exportUsersCSV }) {
  const [pinnedIds, setPinnedIds] = useState(() => loadPins());

  useEffect(() => {
    savePins(pinnedIds);
  }, [pinnedIds]);

  function togglePin(id) {
    setPinnedIds((prev) =>
      prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id]
    );
  }

  function handleAction(action) {
    if (action.id === "export-users") {
      exportUsersCSV?.();
      return;
    }
    if (action.tab) {
      handleTabChange(action.tab);
    }
  }

  const pinnedActions = pinnedIds
    .map((id) => ALL_PINNABLE.find((a) => a.id === id))
    .filter(Boolean);

  if (pinnedActions.length === 0) {
    return (
      <div data-testid="admin-favorites">
        <h3 style={{ margin: "0 0 10px", fontSize: ".95rem", fontWeight: 700, color: "var(--text, #1e293b)" }}>
          📌 Pinned Actions
        </h3>
        <p style={{ color: "var(--muted, #64748b)", fontSize: ".82rem" }}>
          No pinned actions yet. Use the 📍 icon on Quick Actions to pin your most-used features here.
        </p>
      </div>
    );
  }

  return (
    <div data-testid="admin-favorites">
      <h3 style={{ margin: "0 0 10px", fontSize: ".95rem", fontWeight: 700, color: "var(--text, #1e293b)" }}>
        📌 Pinned Actions
      </h3>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
        {pinnedActions.map((action) => (
          <div key={action.id} style={{ display: "flex", alignItems: "center", gap: 0 }}>
            <button
              data-testid={`favorite-${action.id}`}
              aria-label={action.label}
              onClick={() => handleAction(action)}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
                padding: "6px 12px 6px 10px",
                borderRadius: "8px 0 0 8px",
                border: `1.5px solid ${action.color}44`,
                borderRight: "none",
                background: `${action.color}10`,
                cursor: "pointer",
                fontFamily: "inherit",
                fontSize: ".8rem",
                fontWeight: 600,
                color: action.color,
                whiteSpace: "nowrap",
              }}
            >
              <span>{action.icon}</span>
              <span>{action.label}</span>
            </button>
            <button
              data-testid={`unpin-${action.id}`}
              aria-label={`Unpin ${action.label}`}
              onClick={() => togglePin(action.id)}
              style={{
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                width: 24,
                borderRadius: "0 8px 8px 0",
                border: `1.5px solid ${action.color}44`,
                borderLeft: "1px solid transparent",
                background: `${action.color}10`,
                cursor: "pointer",
                fontSize: ".7rem",
                color: action.color,
                padding: "6px 6px",
                fontFamily: "inherit",
              }}
              title="Unpin"
            >
              ✕
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * Returns the set of pinned action ids for use in AdminQuickActions.
 * Reads from localStorage safely.
 */
export function usePinnedIds() {
  const [pinnedIds, setPinnedIds] = useState(() => loadPins());
  function togglePin(action) {
    setPinnedIds((prev) => {
      const next = prev.includes(action.id)
        ? prev.filter((p) => p !== action.id)
        : [...prev, action.id];
      savePins(next);
      return next;
    });
  }
  return { pinnedIds: new Set(pinnedIds), togglePin };
}
