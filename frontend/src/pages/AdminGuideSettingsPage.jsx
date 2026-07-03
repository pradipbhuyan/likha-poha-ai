import { useEffect, useState } from "react";
import { Compass, RotateCcw, Save, Sparkles } from "lucide-react";

import {
  getOnboardingGuideSettings,
  updateOnboardingGuideSettings,
} from "../api/onboardingGuide";

const THEMES = [
  {
    key: "clean",
    label: "Clean Coach",
    icon: "🧭",
    description: "Calm cards, simple steps, best for parents and first-time family setup.",
  },
  {
    key: "quest",
    label: "Quest Mode",
    icon: "🏅",
    description: "Game-like mission cards for students who respond well to progress cues.",
  },
  {
    key: "space",
    label: "Space Mission",
    icon: "🚀",
    description: "Bright launch-themed walkthrough for a fresh, energetic weekly feel.",
  },
  {
    key: "forest",
    label: "Forest Trail",
    icon: "🌿",
    description: "Soft guided trail that suits teacher and parent walkthroughs.",
  },
];

const DEFAULT_SETTINGS = {
  enabled: true,
  active_theme: "quest",
  rotation_enabled: false,
  rotation_days: 14,
  student_theme: "quest",
  parent_theme: "clean",
  teacher_theme: "forest",
  show_once_per_theme: true,
  auto_open: true,
  message:
    "A friendly first-time guide helps new users understand the main pages without feeling lost.",
};

function AdminGuideSettingsPage({ user }) {
  /** Admin screen for configuring the first-time guide visual themes. */
  const [settings, setSettings] = useState(DEFAULT_SETTINGS);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadSettings() {
      try {
        const response = await getOnboardingGuideSettings();
        setSettings({
          ...DEFAULT_SETTINGS,
          ...(response.settings || {}),
        });
      } catch (err) {
        setError(err.message || "Unable to load guide settings.");
      } finally {
        setLoading(false);
      }
    }

    loadSettings();
  }, []);

  function updateSetting(field, value) {
    /** Update one guide setting before saving. */
    setSettings((prev) => ({
      ...prev,
      [field]: value,
    }));
  }

  async function saveSettings() {
    /** Persist the current guide configuration for all users. */
    setSaving(true);
    setMessage("");
    setError("");

    try {
      const response = await updateOnboardingGuideSettings(
        settings,
        user.accessToken
      );
      setSettings({
        ...DEFAULT_SETTINGS,
        ...(response.settings || {}),
      });
      setMessage("First-time guide settings saved.");
    } catch (err) {
      setError(err.message || "Unable to save guide settings.");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return <p>Loading guide settings...</p>;
  }

  return (
    <div className="premium-page admin-guide-page">
      <section className="premium-section admin-guide-hero">
        <div>
          <p className="eyebrow">First Visit Experience</p>
          <h2>Likha Poha AI Guide</h2>
          <p>
            Configure a friendly walkthrough for students, parents, and teachers.
            You can rotate visual styles every couple of weeks to keep the product
            feeling fresh without changing the actual learning flow.
          </p>
        </div>

        <div className="admin-guide-preview-token">
          <Sparkles size={24} strokeWidth={2.4} />
          <strong>
            {settings.enabled
              ? "Likha Poha AI Guide enabled"
              : "Likha Poha AI Guide paused"}
          </strong>
          <span>
            {settings.rotation_enabled
              ? `Rotating every ${settings.rotation_days} days`
              : "Fixed role themes"}
          </span>
        </div>
      </section>

      {message && <div className="info-box">{message}</div>}
      {error && <div className="error-box">{error}</div>}

      <section className="premium-section admin-guide-controls">
        <div className="subscription-section-heading">
          <Compass size={22} strokeWidth={2.4} />
          <h3>Behavior</h3>
        </div>

        <div className="admin-guide-toggle-grid">
          <label>
            <input
              type="checkbox"
              checked={settings.enabled}
              onChange={(e) => updateSetting("enabled", e.target.checked)}
            />
            Enable first-time guide
          </label>

          <label>
            <input
              type="checkbox"
              checked={settings.auto_open}
              onChange={(e) => updateSetting("auto_open", e.target.checked)}
            />
            Auto-open for new users
          </label>

          <label>
            <input
              type="checkbox"
              checked={settings.show_once_per_theme}
              onChange={(e) =>
                updateSetting("show_once_per_theme", e.target.checked)
              }
            />
            Show once per user/theme
          </label>

          <label>
            <input
              type="checkbox"
              checked={settings.rotation_enabled}
              onChange={(e) => updateSetting("rotation_enabled", e.target.checked)}
            />
            Rotate themes automatically
          </label>
        </div>

        <div className="form-grid premium-rag-form-grid admin-guide-form-grid">
          <label>
            <RotateCcw size={16} strokeWidth={2.4} /> Rotation Days
            <input
              type="number"
              min="7"
              max="60"
              value={settings.rotation_days}
              onChange={(e) =>
                updateSetting("rotation_days", Number(e.target.value || 14))
              }
            />
          </label>

          <label>
            Default Theme
            <select
              value={settings.active_theme}
              onChange={(e) => updateSetting("active_theme", e.target.value)}
            >
              {THEMES.map((theme) => (
                <option key={theme.key} value={theme.key}>
                  {theme.label}
                </option>
              ))}
            </select>
          </label>

          <label>
            Student Theme
            <select
              value={settings.student_theme}
              onChange={(e) => updateSetting("student_theme", e.target.value)}
            >
              {THEMES.map((theme) => (
                <option key={theme.key} value={theme.key}>
                  {theme.label}
                </option>
              ))}
            </select>
          </label>

          <label>
            Parent Theme
            <select
              value={settings.parent_theme}
              onChange={(e) => updateSetting("parent_theme", e.target.value)}
            >
              {THEMES.map((theme) => (
                <option key={theme.key} value={theme.key}>
                  {theme.label}
                </option>
              ))}
            </select>
          </label>

          <label>
            Teacher Theme
            <select
              value={settings.teacher_theme}
              onChange={(e) => updateSetting("teacher_theme", e.target.value)}
            >
              {THEMES.map((theme) => (
                <option key={theme.key} value={theme.key}>
                  {theme.label}
                </option>
              ))}
            </select>
          </label>
        </div>

        <label className="admin-plan-full-label">
          Likha Poha AI Guide Footer Message
          <textarea
            rows={3}
            value={settings.message}
            onChange={(e) => updateSetting("message", e.target.value)}
          />
        </label>
      </section>

      <section className="admin-guide-theme-grid">
        {THEMES.map((theme) => (
          <article
            key={theme.key}
            className={`admin-guide-theme-card admin-guide-theme-${theme.key}`}
          >
            <span>{theme.icon}</span>
            <h3>{theme.label}</h3>
            <p>{theme.description}</p>

            <button
              className={
                settings.active_theme === theme.key ? "primary-btn" : "secondary-btn"
              }
              onClick={() => updateSetting("active_theme", theme.key)}
            >
              {settings.active_theme === theme.key ? "Active" : "Use as Default"}
            </button>
          </article>
        ))}
      </section>

      <button
        className="primary-btn admin-guide-save"
        onClick={saveSettings}
        disabled={saving}
      >
        <Save size={18} strokeWidth={2.4} />
        {saving ? "Saving..." : "Save Likha Poha AI Guide Settings"}
      </button>
    </div>
  );
}

export default AdminGuideSettingsPage;
