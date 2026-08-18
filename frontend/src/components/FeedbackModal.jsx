/**
 * FeedbackModal.jsx — general product feedback (not a bug report)
 * Opens as a modal overlay. Submits to POST /api/feedback/report.
 *
 * Props:
 *   open        {boolean}
 *   onClose     {function}
 *   context     {object}  — { route, grade, subject, chapter, triggerEvent }
 *   user        {object}  — current user
 */
import { useState } from "react";
import { submitFeedback } from "../api/feedback";

const FEEDBACK_TYPES = [
  { value: "bug",                 label: "Bug",             icon: "🐛" },
  { value: "feature_request",     label: "Feature idea",    icon: "💡" },
  { value: "content_suggestion",  label: "Content idea",    icon: "📚" },
  { value: "praise",              label: "Praise",          icon: "🌟" },
  { value: "other",               label: "Other",           icon: "💬" },
];

const EMPTY_FORM = { feedback_type: "feature_request", rating: null, message: "" };

export default function FeedbackModal({ open, onClose, context = {}, user: _user }) {
  const [form, setForm] = useState(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState(null);

  function reset() {
    setForm(EMPTY_FORM);
    setSuccess(false);
    setError(null);
  }

  function handleClose() {
    reset();
    onClose();
  }

  function update(field, value) {
    setForm((p) => ({ ...p, [field]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!form.message.trim() || form.message.trim().length < 5) {
      setError("Please share a few words of feedback.");
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const pageCtx = (typeof window !== "undefined" && window.__LIKHAPOHA_CONTEXT__) || {};
      await submitFeedback({
        feedback_type: form.feedback_type,
        rating: form.rating,
        message: form.message.trim().slice(0, 2000),
        trigger_event: context.triggerEvent || null,
        route: context.route || pageCtx.page || window.location.pathname,
        grade: context.grade || pageCtx.grade || null,
        subject: context.subject || pageCtx.subject || null,
        chapter: context.chapter || pageCtx.chapter || null,
      });
      setSuccess(true);
      setForm(EMPTY_FORM);
    } catch (err) {
      setError(err.message || "Failed to submit feedback. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  if (!open) return null;

  const overlay = {
    position: "fixed", inset: 0, background: "rgba(15,23,42,0.5)", zIndex: 2000,
    display: "flex", alignItems: "center", justifyContent: "center", padding: 16,
  };
  const box = {
    background: "var(--panel,#fff)", borderRadius: 16, padding: "26px 28px",
    width: "100%", maxWidth: 440, boxShadow: "0 12px 32px rgba(79,70,229,.12),0 2px 8px rgba(15,23,42,.08)",
    maxHeight: "90vh", overflowY: "auto",
  };
  const label = { display: "block", fontSize: ".78rem", fontWeight: 600, marginBottom: 8, color: "var(--text,#0f172a)" };
  const chipBase = {
    display: "inline-flex", alignItems: "center", gap: 6, padding: "8px 14px",
    borderRadius: 20, fontSize: ".8rem", fontWeight: 600, cursor: "pointer",
    fontFamily: "inherit", border: "1.5px solid var(--border,#dde2f0)", background: "var(--panel,#fff)",
    color: "var(--text-muted,#475569)",
  };
  const chipActive = { borderColor: "#4f46e5", background: "rgba(79,70,229,.08)", color: "#4f46e5" };

  const pageCtx = (typeof window !== "undefined" && window.__LIKHAPOHA_CONTEXT__) || {};
  const mergedGrade = context.grade || pageCtx.grade;
  const mergedSubject = context.subject || pageCtx.subject;
  const mergedChapter = context.chapter || pageCtx.chapter;
  const contextLabel = [mergedGrade, mergedSubject, mergedChapter].filter(Boolean).join(" · ");

  return (
    <div style={overlay} onClick={(e) => { if (e.target === e.currentTarget) handleClose(); }}>
      <div style={box} data-testid="feedback-modal">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 4 }}>
          <h3 style={{ margin: 0, fontWeight: 800, fontSize: "1.05rem" }}>Share your feedback</h3>
          <button onClick={handleClose} aria-label="Close"
            style={{ background: "none", border: "none", cursor: "pointer", fontSize: "1.2rem", color: "#94a3b8", lineHeight: 1 }}>
            ✕
          </button>
        </div>

        {success ? (
          <div data-testid="feedback-success">
            <p style={{ textAlign: "center", fontSize: "2rem", margin: "12px 0 8px" }}>✅</p>
            <p style={{ textAlign: "center", fontWeight: 700, marginBottom: 6 }}>Thanks for sharing!</p>
            <p style={{ textAlign: "center", fontSize: ".85rem", color: "#64748b" }}>
              Our team reads every note — it genuinely helps shape what we build next.
            </p>
            <button onClick={handleClose} data-testid="feedback-close-success"
              style={{ width: "100%", marginTop: 16, padding: "10px", borderRadius: 10, border: "none",
                background: "#4f46e5", color: "#fff", fontWeight: 700, fontSize: ".85rem",
                cursor: "pointer", fontFamily: "inherit" }}>
              Close
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} data-testid="feedback-form">
            <p style={{ fontSize: ".78rem", color: "#64748b", margin: "4px 0 16px" }}>
              Takes less than a minute — we read every note.
            </p>

            {contextLabel && (
              <div style={{ display: "inline-flex", alignItems: "center", gap: 6, background: "rgba(79,70,229,.08)",
                color: "#4f46e5", fontWeight: 700, fontSize: ".72rem", padding: "6px 12px", borderRadius: 8, marginBottom: 18 }}>
                📍 {contextLabel}
              </div>
            )}

            <label style={label}>What's this about?</label>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 20 }} role="radiogroup" aria-label="Feedback type">
              {FEEDBACK_TYPES.map((t) => (
                <button type="button" key={t.value} data-testid={`feedback-type-${t.value}`}
                  onClick={() => update("feedback_type", t.value)}
                  style={form.feedback_type === t.value ? { ...chipBase, ...chipActive } : chipBase}>
                  {t.icon} {t.label}
                </button>
              ))}
            </div>

            <label style={label}>
              How's it going overall? <span style={{ fontWeight: 400, color: "#94a3b8" }}>(optional)</span>
            </label>
            <div style={{ display: "flex", gap: 4, marginBottom: 20, fontSize: "1.4rem", lineHeight: 1 }} data-testid="feedback-rating">
              {[1, 2, 3, 4, 5].map((n) => (
                <button type="button" key={n} onClick={() => update("rating", form.rating === n ? null : n)}
                  aria-label={`${n} star${n > 1 ? "s" : ""}`}
                  style={{ background: "none", border: "none", cursor: "pointer", padding: 0,
                    color: form.rating && n <= form.rating ? "#f59e0b" : "#cbd5e1" }}>
                  {form.rating && n <= form.rating ? "★" : "☆"}
                </button>
              ))}
            </div>

            <label style={label}>Tell us more</label>
            <textarea
              data-testid="feedback-message-input"
              value={form.message}
              onChange={(e) => update("message", e.target.value)}
              rows={4}
              placeholder="What's on your mind?"
              style={{ width: "100%", padding: "11px 13px", borderRadius: 8,
                border: "1px solid var(--border,#dde2f0)", fontFamily: "inherit", fontSize: ".82rem",
                background: "var(--surface2,#f8fafc)", color: "var(--text,#0f172a)",
                boxSizing: "border-box", resize: "vertical", marginBottom: 8 }}
            />

            {error && <p style={{ color: "#dc2626", fontSize: ".78rem", marginBottom: 10 }}>{error}</p>}

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 12 }}>
              <span style={{ fontSize: ".7rem", color: "#94a3b8" }}>🔒 Shared with our product team only</span>
              <button type="submit" disabled={submitting} data-testid="feedback-submit-btn"
                style={{ display: "inline-flex", alignItems: "center", gap: 6,
                  background: submitting ? "#94a3b8" : "#4f46e5", color: "#fff", fontWeight: 700,
                  fontSize: ".85rem", padding: "10px 20px", borderRadius: 10, border: "none",
                  cursor: submitting ? "not-allowed" : "pointer", fontFamily: "inherit" }}>
                {submitting ? "Sending…" : "Send feedback →"}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
