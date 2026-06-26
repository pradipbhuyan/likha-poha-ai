/**
 * AdminGlobalSearch.jsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Debounced global search for the Admin Console.
 *
 * Two-level results:
 *  1. Section-level — keyword → tab + description (always available)
 *  2. Record-level  — searches in-memory allStudents/allParents/allTeachers/offerCodes
 *
 * Props:
 *  handleTabChange(tabKey)   — navigate to a tab
 *  allStudents               — array from AdminControlPage state
 *  allParents                — array from AdminControlPage state
 *  allTeachers               — array from AdminControlPage state
 *  offerCodes                — array from AdminControlPage state
 */

import { useEffect, useRef, useState } from "react";

// ── Section-level search index ─────────────────────────────────────────────
const SECTION_INDEX = [
  { keywords: ["parent", "family", "families", "create parent"],  tab: "accounts",      label: "Create Parent",         icon: "👨‍👩‍👧" },
  { keywords: ["teacher", "create teacher", "school"],            tab: "accounts",      label: "Create Teacher",        icon: "🎓" },
  { keywords: ["student", "create student", "child", "pupil"],    tab: "accounts",      label: "Create Student",        icon: "📚" },
  { keywords: ["account", "accounts", "quick create"],            tab: "accounts",      label: "Accounts",              icon: "👤" },
  { keywords: ["offer", "code", "discount", "coupon", "promo"],   tab: "offers",        label: "Offer Codes",           icon: "🎟️" },
  { keywords: ["influencer", "incentive", "redemption"],          tab: "offers",        label: "Influencer Tracking",   icon: "📊" },
  { keywords: ["family", "families", "access", "subscription", "plan", "cbse", "token", "suspend"], tab: "families", label: "Families & Access", icon: "👨‍👩‍👧" },
  { keywords: ["association", "link", "parent-child", "assign"],  tab: "associations",  label: "Parent-Child Association", icon: "🔗" },
  { keywords: ["teacher-student", "assign student", "teacher association"], tab: "associations", label: "Teacher-Student Association", icon: "🎓" },
  { keywords: ["ai", "api", "openai", "groq", "gemini", "venice", "cerebras", "settings", "key", "model"], tab: "ai", label: "AI & Settings", icon: "🔑" },
  { keywords: ["logging", "log", "debug"],                        tab: "ai",            label: "Logging Settings",      icon: "📋" },
  { keywords: ["collaborator", "blog", "github"],                 tab: "ai",            label: "Blog Collaborators",    icon: "✍️" },
  { keywords: ["payment", "razorpay", "transaction", "webhook"],  tab: "operations",    label: "Payment Monitoring",    icon: "💳" },
  { keywords: ["expiry", "expiry job", "expire", "subscription expired"], tab: "operations", label: "Expiry Job", icon: "⏰" },
  { keywords: ["health", "system", "database", "config"],         tab: "operations",    label: "System Health",         icon: "❤️" },
  { keywords: ["alert", "incident", "rate limit", "error"],       tab: "operations",    label: "Alerts & Incidents",    icon: "🚨" },
  { keywords: ["operations", "dashboard", "monitoring"],          tab: "operations",    label: "Operations Dashboard",  icon: "🖥️" },
  { keywords: ["overview", "summary", "stats", "count"],          tab: "overview",      label: "Overview",              icon: "🏠" },
];

function searchSections(query) {
  const q = query.toLowerCase().trim();
  if (!q) return [];
  return SECTION_INDEX.filter((s) =>
    s.keywords.some((kw) => kw.includes(q) || q.includes(kw))
  ).slice(0, 4);
}

function searchRecords(query, { allStudents = [], allParents = [], allTeachers = [], offerCodes = [] }) {
  const q = query.toLowerCase().trim();
  if (!q || q.length < 2) return [];
  const results = [];

  allStudents.slice(0, 200).forEach((u) => {
    if ((u.username || "").toLowerCase().includes(q) || (u.email || "").toLowerCase().includes(q)) {
      results.push({ type: "student", icon: "📚", label: u.username, sub: u.email, tab: "families" });
    }
  });
  allParents.slice(0, 200).forEach((u) => {
    if ((u.username || "").toLowerCase().includes(q) || (u.email || "").toLowerCase().includes(q)) {
      results.push({ type: "parent", icon: "👨‍👩‍👧", label: u.username, sub: u.email, tab: "families" });
    }
  });
  allTeachers.slice(0, 200).forEach((u) => {
    if ((u.username || "").toLowerCase().includes(q) || (u.email || "").toLowerCase().includes(q)) {
      results.push({ type: "teacher", icon: "🎓", label: u.username, sub: u.email, tab: "accounts" });
    }
  });
  offerCodes.slice(0, 100).forEach((oc) => {
    if ((oc.code || "").toLowerCase().includes(q) || (oc.description || "").toLowerCase().includes(q)) {
      results.push({ type: "offer_code", icon: "🎟️", label: oc.code, sub: oc.description || "Offer code", tab: "offers" });
    }
  });

  return results.slice(0, 6);
}

export default function AdminGlobalSearch({
  handleTabChange,
  allStudents = [],
  allParents = [],
  allTeachers = [],
  offerCodes = [],
}) {
  const [query, setQuery]       = useState("");
  const [debouncedQ, setDQ]     = useState("");
  const [open, setOpen]         = useState(false);
  const inputRef                = useRef(null);
  const containerRef            = useRef(null);

  // Debounce
  useEffect(() => {
    const t = setTimeout(() => setDQ(query), 200);
    return () => clearTimeout(t);
  }, [query]);

  // Close on outside click
  useEffect(() => {
    function handleClick(e) {
      if (containerRef.current && !containerRef.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const sectionResults = debouncedQ ? searchSections(debouncedQ) : [];
  const recordResults  = debouncedQ ? searchRecords(debouncedQ, { allStudents, allParents, allTeachers, offerCodes }) : [];
  const hasResults     = sectionResults.length > 0 || recordResults.length > 0;

  function handleSelect(tab) {
    handleTabChange(tab);
    setQuery("");
    setOpen(false);
  }

  return (
    <div ref={containerRef} style={{ position: "relative", flex: 1, maxWidth: 400 }} data-testid="admin-global-search">
      <div style={{ position: "relative" }}>
        <span
          aria-hidden="true"
          style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", fontSize: ".9rem", pointerEvents: "none", color: "var(--muted, #94a3b8)" }}
        >
          🔍
        </span>
        <input
          ref={inputRef}
          type="search"
          value={query}
          onChange={(e) => { setQuery(e.target.value); setOpen(true); }}
          onFocus={() => query && setOpen(true)}
          placeholder="Search tabs, users, offer codes…"
          aria-label="Search admin console"
          data-testid="admin-search-input"
          style={{
            width: "100%",
            padding: "8px 12px 8px 32px",
            borderRadius: 8,
            border: "1px solid var(--border, #e5e7eb)",
            background: "var(--panel, #fff)",
            fontFamily: "inherit",
            fontSize: ".85rem",
            color: "var(--text, #1e293b)",
            outline: "none",
            boxSizing: "border-box",
          }}
        />
        {query && (
          <button
            onClick={() => { setQuery(""); setOpen(false); inputRef.current?.focus(); }}
            aria-label="Clear search"
            style={{
              position: "absolute", right: 8, top: "50%", transform: "translateY(-50%)",
              background: "none", border: "none", cursor: "pointer", color: "var(--muted, #94a3b8)", fontSize: ".85rem", padding: 2,
            }}
          >
            ✕
          </button>
        )}
      </div>

      {/* Dropdown */}
      {open && debouncedQ && (
        <div
          data-testid="admin-search-results"
          role="listbox"
          aria-label="Search results"
          style={{
            position: "absolute",
            top: "calc(100% + 4px)",
            left: 0,
            right: 0,
            background: "var(--panel, #fff)",
            border: "1px solid var(--border, #e5e7eb)",
            borderRadius: 10,
            boxShadow: "0 8px 24px rgba(0,0,0,0.12)",
            zIndex: 100,
            overflow: "hidden",
            maxHeight: 360,
            overflowY: "auto",
          }}
        >
          {!hasResults && (
            <div data-testid="admin-search-no-results" style={{ padding: "12px 14px", color: "var(--muted, #64748b)", fontSize: ".82rem" }}>
              No results for "{debouncedQ}"
            </div>
          )}

          {sectionResults.length > 0 && (
            <>
              <div style={{ padding: "6px 14px 2px", fontSize: ".7rem", fontWeight: 700, color: "var(--muted, #94a3b8)", letterSpacing: ".04em", textTransform: "uppercase" }}>
                Sections
              </div>
              {sectionResults.map((s, i) => (
                <button
                  key={`section-${i}`}
                  role="option"
                  data-testid={`search-result-section-${s.tab}`}
                  onClick={() => handleSelect(s.tab)}
                  style={{
                    width: "100%", display: "flex", alignItems: "center", gap: 10, padding: "8px 14px",
                    background: "none", border: "none", cursor: "pointer", fontFamily: "inherit", textAlign: "left",
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.background = "var(--surface2, #f8fafc)"}
                  onMouseLeave={(e) => e.currentTarget.style.background = "none"}
                >
                  <span style={{ fontSize: "1rem" }}>{s.icon}</span>
                  <span style={{ fontSize: ".85rem", fontWeight: 600, color: "var(--text, #1e293b)" }}>{s.label}</span>
                  <span style={{ marginLeft: "auto", fontSize: ".72rem", color: "var(--muted, #94a3b8)", background: "var(--surface2, #f1f5f9)", padding: "2px 7px", borderRadius: 5 }}>
                    {s.tab}
                  </span>
                </button>
              ))}
            </>
          )}

          {recordResults.length > 0 && (
            <>
              <div style={{ padding: "6px 14px 2px", fontSize: ".7rem", fontWeight: 700, color: "var(--muted, #94a3b8)", letterSpacing: ".04em", textTransform: "uppercase", borderTop: sectionResults.length ? "1px solid var(--border, #f1f5f9)" : "none", marginTop: sectionResults.length ? 4 : 0 }}>
                Records
              </div>
              {recordResults.map((r, i) => (
                <button
                  key={`record-${i}`}
                  role="option"
                  data-testid={`search-result-record-${r.type}-${i}`}
                  onClick={() => handleSelect(r.tab)}
                  style={{
                    width: "100%", display: "flex", alignItems: "center", gap: 10, padding: "7px 14px",
                    background: "none", border: "none", cursor: "pointer", fontFamily: "inherit", textAlign: "left",
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.background = "var(--surface2, #f8fafc)"}
                  onMouseLeave={(e) => e.currentTarget.style.background = "none"}
                >
                  <span style={{ fontSize: ".9rem" }}>{r.icon}</span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <span style={{ fontSize: ".82rem", fontWeight: 600, color: "var(--text, #1e293b)" }}>{r.label}</span>
                    {r.sub && <span style={{ fontSize: ".72rem", color: "var(--muted, #94a3b8)", marginLeft: 6 }}>{r.sub}</span>}
                  </div>
                  <span style={{ fontSize: ".7rem", color: "var(--muted, #94a3b8)", background: "var(--surface2, #f1f5f9)", padding: "2px 6px", borderRadius: 5 }}>
                    {r.type}
                  </span>
                </button>
              ))}
            </>
          )}
        </div>
      )}
    </div>
  );
}
