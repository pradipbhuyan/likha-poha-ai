/**
 * ReportIssueModal.jsx — Student/User Issue Reporting
 * Opens as a modal overlay. Submits to POST /api/issues/report.
 * Auto-captures context: page, grade, subject, chapter, lesson step.
 *
 * Props:
 *   open        {boolean}
 *   onClose     {function}
 *   context     {object}  — { route, grade, subject, chapter, lessonId, lessonStep }
 *   user        {object}  — current user (for accessToken)
 */
import { useState } from "react";
import { authFetch } from "../api/authClient";

const ISSUE_TYPES = [
  { value: "content_issue",      label: "Content issue" },
  { value: "wrong_explanation",  label: "Wrong explanation" },
  { value: "missing_section",    label: "Missing lesson section" },
  { value: "wrong_formula",      label: "Wrong formula" },
  { value: "wrong_answer",       label: "Wrong answer / MCQ" },
  { value: "broken_page",        label: "Broken page / button" },
  { value: "login_issue",        label: "Login / access issue" },
  { value: "other",              label: "Other" },
];

const SEVERITIES = [
  { value: "low",      label: "Low",      color: "#94a3b8" },
  { value: "medium",   label: "Medium",   color: "#f59e0b" },
  { value: "high",     label: "High",     color: "#f97316" },
  { value: "critical", label: "Critical", color: "#ef4444" },
];

export default function ReportIssueModal({ open, onClose, context = {}, user }) {
  const [form, setForm] = useState({
    issue_type: "content_issue",
    severity: "medium",
    description: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState(null);

  function reset() {
    setForm({ issue_type: "content_issue", severity: "medium", description: "" });
    setSuccess(false);
    setError(null);
  }

  function handleClose() {
    reset();
    onClose();
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!form.description.trim() || form.description.trim().length < 10) {
      setError("Please describe the issue in at least 10 characters.");
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const payload = {
        issue_type: form.issue_type,
        severity: form.severity,
        description: form.description.trim().slice(0, 2000),
        route: context.route || window.location.pathname,
        grade: context.grade || user?.grade || null,
        subject: context.subject || null,
        chapter: context.chapter || null,
        lesson_id: context.lessonId || null,
        lesson_step: context.lessonStep || null,
        browser_info: {
          userAgent: navigator.userAgent?.slice(0, 200),
          platform: navigator.platform,
          language: navigator.language,
          screenWidth: window.screen?.width,
          screenHeight: window.screen?.height,
          timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        },
      };

      await authFetch("/api/issues/report", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      setSuccess(true);
      setForm({ issue_type: "content_issue", severity: "medium", description: "" });
    } catch (err) {
      setError(err.message || "Failed to submit issue. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  if (!open) return null;

  const overlay = {
    position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)", zIndex: 2000,
    display: "flex", alignItems: "center", justifyContent: "center", padding: 16,
  };
  const box = {
    background: "var(--panel,#fff)", borderRadius: 14, padding: "24px 28px",
    width: "100%", maxWidth: 480, boxShadow: "0 20px 60px rgba(0,0,0,0.2)",
    maxHeight: "90vh", overflowY: "auto",
  };
  const label = { display: "block", fontSize: ".8rem", fontWeight: 600, marginBottom: 5, color: "var(--text,#374151)" };
  const input = {
    width: "100%", padding: "9px 12px", borderRadius: 8,
    border: "1px solid var(--border,#e5e7eb)", fontFamily: "inherit", fontSize: ".85rem",
    background: "var(--panel,#fff)", color: "var(--text,#374151)", boxSizing: "border-box",
  };

  return (
    <div style={overlay} onClick={e => { if (e.target === e.currentTarget) handleClose(); }}>
      <div style={box} data-testid="report-issue-modal">
        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 18 }}>
          <h3 style={{ margin: 0, fontWeight: 800, fontSize: "1rem" }}>🐛 Report an Issue</h3>
          <button onClick={handleClose} aria-label="Close"
            style={{ background: "none", border: "none", cursor: "pointer", fontSize: "1.2rem", color: "#94a3b8" }}>
            ✕
          </button>
        </div>

        {success ? (
          <div data-testid="report-issue-success">
            <div style={{ fontSize: "2rem", textAlign: "center", marginBottom: 10 }}>✅</div>
            <p style={{ textAlign: "center", fontWeight: 700, marginBottom: 8 }}>Thank you for reporting!</p>
            <p style={{ textAlign: "center", fontSize: ".85rem", color: "#64748b" }}>
              Our team will review and fix this issue. Your feedback helps improve the platform.
            </p>
            <button onClick={handleClose} data-testid="report-issue-close-success"
              style={{ width: "100%", marginTop: 16, padding: "10px", borderRadius: 8, border: "none",
                background: "#6366f1", color: "#fff", fontWeight: 700, fontSize: ".85rem",
                cursor: "pointer", fontFamily: "inherit" }}>
              Close
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} data-testid="report-issue-form">
            {/* Auto-captured context */}
            {(context.grade || context.subject || context.chapter) && (
              <div style={{ background: "var(--surface2,#f8fafc)", borderRadius: 8, padding: "8px 12px",
                fontSize: ".76rem", color: "#64748b", marginBottom: 16 }}>
                <span style={{ fontWeight: 600 }}>Context: </span>
                {[context.grade, context.subject, context.chapter, context.lessonStep]
                  .filter(Boolean).join(" › ")}
              </div>
            )}

            {/* Issue type */}
            <div style={{ marginBottom: 14 }}>
              <label style={label}>Issue Type</label>
              <select style={input} value={form.issue_type}
                onChange={e => setForm(p => ({ ...p, issue_type: e.target.value }))}
                data-testid="issue-type-select">
                {ISSUE_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </div>

            {/* Severity */}
            <div style={{ marginBottom: 14 }}>
              <label style={label}>Severity</label>
              <div style={{ display: "flex", gap: 6 }}>
                {SEVERITIES.map(s => (
                  <button key={s.value} type="button"
                    onClick={() => setForm(p => ({ ...p, severity: s.value }))}
                    data-testid={`severity-${s.value}`}
                    style={{
                      flex: 1, padding: "6px 4px", borderRadius: 7, fontFamily: "inherit",
                      fontSize: ".76rem", fontWeight: 600, cursor: "pointer",
                      border: "2px solid " + (form.severity === s.value ? s.color : "var(--border,#e5e7eb)"),
                      background: form.severity === s.value ? s.color + "15" : "transparent",
                      color: form.severity === s.value ? s.color : "var(--text-muted,#64748b)",
                    }}>
                    {s.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Description */}
            <div style={{ marginBottom: 16 }}>
              <label style={label}>Description *</label>
              <textarea
                data-testid="issue-description"
                value={form.description}
                onChange={e => setForm(p => ({ ...p, description: e.target.value }))}
                placeholder="Describe what you found, what you expected, and any steps to reproduce..."
                rows={4}
                style={{ ...input, resize: "vertical", minHeight: 100 }}
                maxLength={2000}
              />
              <div style={{ fontSize: ".72rem", color: "#94a3b8", textAlign: "right" }}>
                {form.description.length}/2000
              </div>
            </div>

            {error && (
              <div data-testid="report-issue-error"
                style={{ background: "#fef2f2", border: "1px solid #fecaca", borderRadius: 8,
                  padding: "8px 12px", color: "#dc2626", fontSize: ".8rem", marginBottom: 14 }}>
                {error}
              </div>
            )}

            <button type="submit" disabled={submitting} data-testid="submit-issue-btn"
              style={{ width: "100%", padding: "10px", borderRadius: 8, border: "none",
                background: submitting ? "#94a3b8" : "#6366f1", color: "#fff", fontWeight: 700,
                fontSize: ".85rem", cursor: submitting ? "not-allowed" : "pointer", fontFamily: "inherit" }}>
              {submitting ? "Submitting…" : "Submit Report"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
