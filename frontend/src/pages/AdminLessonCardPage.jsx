import { useEffect, useState } from "react";
import { Layers, Save } from "lucide-react";
import { getLessonCardSettings, updateLessonCardSettings } from "../api/adminControl";

const CARD_STYLES = [
  {
    key: "default",
    label: "Default",
    icon: "📋",
    description:
      "Plain white/light-grey cards with a subtle border — the original layout. Clean and minimal.",
    preview: "default",
  },
  {
    key: "A",
    label: "Option A — Gradient Glow",
    icon: "✨",
    description:
      "Soft pastel gradient background per section with a coloured glow shadow. Premium and inviting.",
    preview: "A",
  },
  {
    key: "B",
    label: "Option B — Game Cards",
    icon: "🎮",
    description:
      "White card with a coloured top stripe, XP progress dots, and category tag. Gamified and motivating.",
    preview: "B",
  },
  {
    key: "C",
    label: "Option C — Bold Header",
    icon: "🏷️",
    description:
      "Numbered badge + emoji in a coloured header band. Strong visual hierarchy — accordion-style.",
    preview: "C",
  },
];

const THEMES = [
  {
    key: "brand",
    label: "🎓 Likha Poha AI",
    description: "Blue → Indigo → Violet — the platform's signature indigo-to-purple palette.",
    gradient: "linear-gradient(135deg,#2563eb,#7c3aed)",
  },
  {
    key: "forest",
    label: "🌿 Forest Trail",
    description: "Emerald → Teal → Green — a calm, nature-inspired palette.",
    gradient: "linear-gradient(135deg,#166534,#0f766e)",
  },
];

// Mini preview colours per theme per section index (0-2)
const PREVIEW_COLORS = {
  brand: [
    { light: "#dbeafe", dark: "#0c1a3a", accent: "#2563eb", text: "#1e3a8a" },
    { light: "#eef2ff", dark: "#1e1b4b", accent: "#4f46e5", text: "#312e81" },
    { light: "#f5f3ff", dark: "#2e1065", accent: "#7c3aed", text: "#3730a3" },
  ],
  forest: [
    { light: "#d1fae5", dark: "#022c22", accent: "#059669", text: "#064e3b" },
    { light: "#ccfbf1", dark: "#042f2e", accent: "#0f766e", text: "#134e4a" },
    { light: "#dcfce7", dark: "#14532d", accent: "#16a34a", text: "#166534" },
  ],
};

const SAMPLE_SECTIONS = ["Introduction", "What you will learn", "Simple explanation"];
const SAMPLE_EMOJIS = ["📚", "🎯", "📖"];

function MiniCardA({ idx, theme }) {
  const c = PREVIEW_COLORS[theme][idx];
  return (
    <div style={{
      borderRadius: 10, padding: "8px 12px", display: "flex", alignItems: "center", gap: 8,
      background: `linear-gradient(135deg,${c.light},#fff)`,
      border: `1px solid ${c.accent}33`,
      boxShadow: `0 3px 12px ${c.accent}22`,
      marginBottom: 5,
    }}>
      <span style={{ fontSize: 16, width: 28, height: 28, borderRadius: 7, background: `${c.accent}18`, display: "flex", alignItems: "center", justifyContent: "center" }}>
        {SAMPLE_EMOJIS[idx]}
      </span>
      <span style={{ flex: 1, fontSize: 11, fontWeight: 700, color: c.text }}>
        {idx + 1}. {SAMPLE_SECTIONS[idx]}
      </span>
      <span style={{ color: c.accent, fontSize: 13, opacity: 0.5 }}>›</span>
    </div>
  );
}

function MiniCardB({ idx, theme }) {
  const c = PREVIEW_COLORS[theme][idx];
  return (
    <div style={{ borderRadius: 9, overflow: "hidden", background: "#fff", border: "1px solid rgba(0,0,0,.07)", marginBottom: 5, boxShadow: "0 2px 10px rgba(0,0,0,.08)" }}>
      <div style={{ height: 4, background: c.accent }} />
      <div style={{ display: "flex", alignItems: "center", padding: "7px 10px", gap: 8 }}>
        <span style={{ width: 26, height: 26, borderRadius: "50%", background: `${c.accent}18`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 13, flexShrink: 0 }}>
          {SAMPLE_EMOJIS[idx]}
        </span>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: c.text }}>{idx + 1}. {SAMPLE_SECTIONS[idx]}</div>
          <div style={{ fontSize: 9, fontWeight: 700, color: c.accent, textTransform: "uppercase", letterSpacing: ".5px", marginTop: 1 }}>
            {["STARTER", "GOALS", "CONCEPT"][idx]}
          </div>
        </div>
        <span style={{ fontSize: 10, fontWeight: 800, color: c.accent }}>+{(idx + 1) * 5} XP</span>
      </div>
    </div>
  );
}

function MiniCardC({ idx, theme }) {
  const c = PREVIEW_COLORS[theme][idx];
  return (
    <div style={{ borderRadius: 9, overflow: "hidden", background: "#fff", border: "1px solid rgba(0,0,0,.07)", marginBottom: 5 }}>
      <div style={{ display: "flex", alignItems: "center", padding: "8px 10px", gap: 8, background: `${c.accent}14` }}>
        <span style={{ width: 20, height: 20, borderRadius: 5, background: `${c.accent}28`, color: c.accent, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 10, fontWeight: 900, flexShrink: 0 }}>
          {idx + 1}
        </span>
        <span style={{ fontSize: 13 }}>{SAMPLE_EMOJIS[idx]}</span>
        <span style={{ flex: 1, fontSize: 11, fontWeight: 800, color: c.text }}>{idx + 1}. {SAMPLE_SECTIONS[idx]}</span>
        <span style={{ color: c.accent, fontSize: 12, opacity: 0.5 }}>⌄</span>
      </div>
    </div>
  );
}

function MiniCardDefault({ idx }) {
  return (
    <div style={{ borderRadius: 12, overflow: "hidden", background: "#fff", border: "1px solid #e5e7eb", marginBottom: 5, boxShadow: "0 2px 8px rgba(0,0,0,.05)" }}>
      <button style={{ width: "100%", border: "none", background: [
        "#ecfdf5","#eff6ff","#f5f3ff"
      ][idx], padding: "10px 12px", display: "flex", alignItems: "center", gap: 8, cursor: "default" }}>
        <span style={{ width: 26, height: 26, borderRadius: 8, background: "#f0f0f0", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 13, flexShrink: 0 }}>
          {SAMPLE_EMOJIS[idx]}
        </span>
        <span style={{ flex: 1, fontSize: 11, fontWeight: 700, color: ["#047857","#1d4ed8","#6d28d9"][idx], textAlign: "left" }}>
          {idx + 1}. {SAMPLE_SECTIONS[idx]}
        </span>
        <span style={{ opacity: 0.4, fontSize: 12 }}>⌄</span>
      </button>
    </div>
  );
}

const MINI_RENDERERS = { default: MiniCardDefault, A: MiniCardA, B: MiniCardB, C: MiniCardC };

function AdminLessonCardPage({ user }) {
  const [settings, setSettings] = useState({ card_style: "default", card_theme: "brand" });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const res = await getLessonCardSettings(user.accessToken);
        setSettings({ card_style: res.card_style || "default", card_theme: res.card_theme || "brand" });
      } catch (err) {
        setError(err.message || "Could not load card settings.");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  async function save() {
    setSaving(true);
    setMessage("");
    setError("");
    try {
      const res = await updateLessonCardSettings(settings, user.accessToken);
      setSettings({ card_style: res.card_style, card_theme: res.card_theme });
      setMessage("Lesson card settings saved. Students will see the new style immediately.");
    } catch (err) {
      setError(err.message || "Could not save settings.");
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <p>Loading lesson card settings...</p>;

  // eslint-disable-next-line no-unused-vars
  const MiniCard = MINI_RENDERERS[settings.card_style] || MiniCardDefault;
  const themeNeedsColor = settings.card_style !== "default";

  return (
    <div className="premium-page">
      <section className="premium-section" style={{ marginBottom: 28 }}>
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 24, flexWrap: "wrap" }}>
          <div>
            <p className="eyebrow">Lesson Experience</p>
            <h2 style={{ margin: "6px 0 10px", fontSize: "clamp(22px,3vw,32px)", letterSpacing: "-.03em" }}>
              <Layers size={28} style={{ marginRight: 10, verticalAlign: "middle", color: "var(--primary)" }} />
              Lesson Section Card Style
            </h2>
            <p style={{ color: "var(--muted)", maxWidth: 680, lineHeight: 1.65 }}>
              Choose how the lesson accordion sections look for students. Changes apply instantly — no reload needed.
              Preview each style below, then click <strong>Activate</strong> to select it.
            </p>
          </div>
          <div style={{ padding: "14px 18px", borderRadius: 16, background: "var(--panel)", border: "1px solid var(--border)", minWidth: 200 }}>
            <p style={{ fontSize: 12, color: "var(--muted)", fontWeight: 700, marginBottom: 6 }}>Currently Active</p>
            <strong style={{ fontSize: 17 }}>
              {CARD_STYLES.find(s => s.key === settings.card_style)?.label || "Default"}
            </strong>
            <p style={{ fontSize: 12, color: "var(--muted)", marginTop: 4 }}>
              Theme: {THEMES.find(t => t.key === settings.card_theme)?.label || "Likha Poha AI"}
            </p>
          </div>
        </div>
      </section>

      {message && <div className="info-box" style={{ marginBottom: 20 }}>{message}</div>}
      {error && <div className="error-box" style={{ marginBottom: 20 }}>{error}</div>}

      {/* Colour Theme selector */}
      <section className="premium-section" style={{ marginBottom: 28 }}>
        <h3 style={{ margin: "0 0 6px", fontSize: 18 }}>🎨 Colour Theme</h3>
        <p style={{ color: "var(--muted)", fontSize: 13, marginBottom: 18 }}>
          Applies to styles A, B, and C. Default style uses its own fixed section colours.
        </p>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(2,minmax(0,1fr))", gap: 16, maxWidth: 680 }}>
          {THEMES.map(theme => (
            <button
              key={theme.key}
              type="button"
              onClick={() => setSettings(prev => ({ ...prev, card_theme: theme.key }))}
              style={{
                padding: "18px 20px", borderRadius: 16, textAlign: "left", cursor: "pointer",
                border: settings.card_theme === theme.key ? "2px solid #2563eb" : "1px solid var(--border)",
                background: settings.card_theme === theme.key ? "var(--panel)" : "var(--panel)",
                boxShadow: settings.card_theme === theme.key ? "0 0 0 3px rgba(37,99,235,.14)" : "none",
                fontFamily: "inherit",
                transition: "all .18s",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
                <span style={{ width: 32, height: 32, borderRadius: 10, background: theme.gradient, flexShrink: 0 }} />
                <strong style={{ fontSize: 14, color: "var(--text)" }}>{theme.label}</strong>
                {settings.card_theme === theme.key && (
                  <span style={{ marginLeft: "auto", fontSize: 11, fontWeight: 800, padding: "3px 8px", borderRadius: 999, background: "#eff6ff", color: "#1d4ed8" }}>Active</span>
                )}
              </div>
              <p style={{ margin: 0, fontSize: 12, color: "var(--muted)", lineHeight: 1.5 }}>{theme.description}</p>
            </button>
          ))}
        </div>
      </section>

      {/* Card style grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(260px,1fr))", gap: 20, marginBottom: 32 }}>
        {CARD_STYLES.map(style => {
          const isActive = settings.card_style === style.key;
          const Renderer = MINI_RENDERERS[style.key] || MiniCardDefault;
          return (
            <div
              key={style.key}
              style={{
                borderRadius: 20, background: "var(--panel)", overflow: "hidden",
                border: isActive ? "2px solid #2563eb" : "1px solid var(--border)",
                boxShadow: isActive ? "0 0 0 3px rgba(37,99,235,.14), 0 18px 40px rgba(15,23,42,.08)" : "0 8px 24px rgba(15,23,42,.06)",
                transition: "all .2s",
              }}
            >
              {/* Header */}
              <div style={{ padding: "18px 18px 14px", borderBottom: "1px solid var(--border-soft)" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
                  <span style={{ fontSize: 22 }}>{style.icon}</span>
                  <strong style={{ fontSize: 15, color: "var(--text)" }}>{style.label}</strong>
                  {isActive && (
                    <span style={{ marginLeft: "auto", fontSize: 11, fontWeight: 800, padding: "3px 8px", borderRadius: 999, background: "#eff6ff", color: "#1d4ed8" }}>
                      ✓ Active
                    </span>
                  )}
                </div>
                <p style={{ margin: 0, fontSize: 12, color: "var(--muted)", lineHeight: 1.55 }}>{style.description}</p>
              </div>

              {/* Mini preview */}
              <div style={{ padding: "14px", background: "var(--panel-soft)" }}>
                {[0, 1, 2].map(idx => (
                  <Renderer
                    key={idx}
                    idx={idx}
                    theme={themeNeedsColor ? settings.card_theme : "brand"}
                  />
                ))}
              </div>

              {/* Activate button */}
              <div style={{ padding: "14px 18px" }}>
                <button
                  type="button"
                  className={isActive ? "primary-btn" : "secondary-btn"}
                  style={{ width: "100%", margin: 0 }}
                  onClick={() => setSettings(prev => ({ ...prev, card_style: style.key }))}
                >
                  {isActive ? "✓ Currently Selected" : "Select This Style"}
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Save button */}
      <button
        className="primary-btn"
        onClick={save}
        disabled={saving}
        style={{ display: "inline-flex", alignItems: "center", gap: 10, minWidth: 260, height: 54, borderRadius: 16 }}
      >
        <Save size={18} strokeWidth={2.4} />
        {saving ? "Saving…" : "Save Lesson Card Settings"}
      </button>
    </div>
  );
}

export default AdminLessonCardPage;
