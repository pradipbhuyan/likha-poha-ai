/**
 * ReportIssueModal.jsx — Student/User Issue Reporting
 * Opens as a modal overlay. Submits to POST /api/issues/report.
 * Auto-captures context: page, grade, subject, chapter, lesson step,
 * app version, and a human-readable device/browser string.
 *
 * Props:
 *   open        {boolean}
 *   onClose     {function}
 *   context     {object}  — { route, grade, subject, chapter, lessonId, lessonStep }
 *   user        {object}  — current user (for accessToken)
 */
import { useRef, useState } from "react";
import { authFetch } from "../api/authClient";
import { version as APP_VERSION } from "../../package.json";

// ── Screenshot compression (Canvas → JPEG base64, max 400KB) ─────────────────
async function compressScreenshot(file) {
  return new Promise((resolve) => {
    try {
      const reader = new FileReader();
      reader.onload = (ev) => {
        const img = new Image();
        img.onload = () => {
          try {
            const scale = Math.min(1, 900 / img.width);
            const w = Math.round(img.width * scale);
            const h = Math.round(img.height * scale);
            const canvas = document.createElement("canvas");
            canvas.width = w; canvas.height = h;
            canvas.getContext("2d").drawImage(img, 0, 0, w, h);
            const url = canvas.toDataURL("image/jpeg", 0.8);
            resolve(url.length > 400 * 1024 ? canvas.toDataURL("image/jpeg", 0.5) : url);
          } catch { resolve(null); }
        };
        img.onerror = () => resolve(null);
        img.src = ev.target.result;
      };
      reader.onerror = () => resolve(null);
      reader.readAsDataURL(file);
    } catch { resolve(null); }
  });
}

// ── Best-effort human-readable "Chrome 120 on Windows" string from the UA ────
function describeDevice() {
  try {
    const ua = navigator.userAgent || "";
    let browser = "Unknown browser";
    const bMatch = ua.match(/(Edg|Chrome|Firefox|Safari|OPR)\/([\d.]+)/);
    if (bMatch) {
      const names = { Edg: "Edge", OPR: "Opera" };
      browser = `${names[bMatch[1]] || bMatch[1]} ${bMatch[2].split(".")[0]}`;
    }
    let os = "Unknown OS";
    if (/Windows/.test(ua)) os = "Windows";
    else if (/Mac OS X/.test(ua)) os = "macOS";
    else if (/Android/.test(ua)) os = "Android";
    else if (/iPhone|iPad|iOS/.test(ua)) os = "iOS";
    else if (/Linux/.test(ua)) os = "Linux";
    return `${browser} on ${os}`;
  } catch { return null; }
}

// Grouped so the dropdown gives reporters many precise, friendly options
// instead of forcing everything into a vague "Other".
const ISSUE_TYPE_GROUPS = [
  {
    label: "📚 Content & Learning",
    items: [
      { value: "content_issue",       label: "Wrong or inaccurate content" },
      { value: "wrong_explanation",   label: "Confusing or wrong explanation" },
      { value: "missing_section",     label: "Missing lesson section" },
      { value: "wrong_formula",       label: "Wrong formula or calculation" },
      { value: "wrong_answer",        label: "Wrong answer / MCQ option" },
      { value: "translation_language",label: "Wrong language / translation" },
      { value: "audio_video_issue",   label: "Audio / video not working" },
    ],
  },
  {
    label: "⚙️ Technical",
    items: [
      { value: "broken_page",         label: "Broken page / button" },
      { value: "app_crash",           label: "App crashed or froze" },
      { value: "slow_performance",    label: "Slow / lagging" },
      { value: "sync_progress",       label: "Progress not saving" },
      { value: "notification_issue",  label: "Notification problem" },
      { value: "download_issue",      label: "Download / offline issue" },
    ],
  },
  {
    label: "🔐 Account & Billing",
    items: [
      { value: "login_issue",         label: "Login / access issue" },
      { value: "payment_billing",     label: "Payment / subscription issue" },
    ],
  },
  {
    label: "💡 Other",
    items: [
      { value: "accessibility_issue", label: "Accessibility problem" },
      { value: "feature_request",     label: "Feature request / suggestion" },
      { value: "other",               label: "Something else" },
    ],
  },
];

const SEVERITIES = [
  { value: "low",      label: "Low",      color: "#94a3b8" },
  { value: "medium",   label: "Medium",   color: "#f59e0b" },
  { value: "high",     label: "High",     color: "#f97316" },
  { value: "critical", label: "Critical", color: "#ef4444" },
];

const REPRODUCIBILITY = [
  { value: "always",    label: "Every time" },
  { value: "sometimes", label: "Sometimes" },
  { value: "rarely",    label: "Rarely" },
  { value: "once",      label: "Just once" },
];

const EMPTY_FORM = {
  issue_type: "content_issue",
  severity: "medium",
  title: "",
  description: "",
  steps_to_reproduce: "",
  expected_behavior: "",
  actual_behavior: "",
  reproducibility: "",
};

export default function ReportIssueModal({ open, onClose, context = {}, user }) {
  const [form, setForm] = useState(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [defectNumber, setDefectNumber] = useState(null);
  const [error, setError] = useState(null);
  const [screenshotPreview, setScreenshotPreview] = useState(null);
  const [screenshotProcessing, setScreenshotProcessing] = useState(false);
  const [screenshotDataUrl, setScreenshotDataUrl] = useState(null);
  const fileInputRef = useRef(null);

  function reset() {
    setForm(EMPTY_FORM);
    setSuccess(false); setError(null); setDefectNumber(null);
    setScreenshotPreview(null); setScreenshotDataUrl(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  function update(field, value) {
    setForm(p => ({ ...p, [field]: value }));
  }

  async function handleFileChange(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.type.startsWith("image/")) { setError("Please attach an image file."); return; }
    setScreenshotProcessing(true); setError(null);
    setScreenshotPreview(URL.createObjectURL(file));
    setScreenshotDataUrl(await compressScreenshot(file));
    setScreenshotProcessing(false);
  }
  function removeScreenshot() {
    setScreenshotPreview(null); setScreenshotDataUrl(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
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
      // Merge window.__LIKHAPOHA_CONTEXT__ (written by LessonsPage and other pages)
      // with the explicit context prop so subject/chapter/lessonStep are always captured.
      const pageCtx = (typeof window !== "undefined" && window.__LIKHAPOHA_CONTEXT__) || {};
      const payload = {
        issue_type: form.issue_type,
        severity: form.severity,
        title: form.title.trim().slice(0, 200) || undefined,
        description: form.description.trim().slice(0, 2000),
        steps_to_reproduce: form.steps_to_reproduce.trim().slice(0, 1500) || undefined,
        expected_behavior: form.expected_behavior.trim().slice(0, 1000) || undefined,
        actual_behavior: form.actual_behavior.trim().slice(0, 1000) || undefined,
        reproducibility: form.reproducibility || undefined,
        route: context.route || pageCtx.page || window.location.pathname,
        grade: context.grade || pageCtx.grade || user?.grade || null,
        subject: context.subject || pageCtx.subject || null,
        chapter: context.chapter || pageCtx.chapter || null,
        lesson_id: context.lessonId || pageCtx.lessonId || null,
        lesson_step: context.lessonStep || pageCtx.lessonStep || null,
        app_version: APP_VERSION || null,
        device_info: describeDevice(),
        browser_info: (() => {
          const pageCtx2 = (typeof window !== "undefined" && window.__LIKHAPOHA_CONTEXT__) || {};
          let computedFont = null;
          try {
            const el = document.querySelector(".markdown-content") || document.querySelector(".lesson-output");
            if (el) computedFont = window.getComputedStyle(el).fontFamily?.slice(0, 150);
          } catch { /**/ }
          let elementAtCenter = null;
          try {
            const el = document.elementFromPoint(window.innerWidth / 2, window.innerHeight / 2);
            if (el && el !== document.body) {
              const cs = window.getComputedStyle(el);
              elementAtCenter = { tag: el.tagName, classes: el.className?.slice(0, 80),
                fontSize: cs.fontSize, fontFamily: cs.fontFamily?.slice(0, 80), display: cs.display };
            }
          } catch { /**/ }
          let stepTextContent = null;
          try {
            const el = document.querySelector(".markdown-content") || document.querySelector(".lesson-output");
            if (el) stepTextContent = el.textContent?.trim().slice(0, 500) || null;
          } catch { /**/ }
          let pageLoadMs = null;
          try {
            if (performance?.timing?.navigationStart) pageLoadMs = Date.now() - performance.timing.navigationStart;
          } catch { /**/ }
          return {
            userAgent: navigator.userAgent?.slice(0, 200),
            platform: navigator.platform,
            language: navigator.language,
            screenWidth: window.screen?.width, screenHeight: window.screen?.height,
            viewportWidth: window.innerWidth, viewportHeight: window.innerHeight,
            devicePixelRatio: window.devicePixelRatio,
            scrollY: Math.round(window.scrollY), online: navigator.onLine, pageLoadMs,
            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
            computedFont, elementAtCenter, stepTextContent,
            lessonStepIndex: context.lessonStepIndex ?? pageCtx2.lessonStepIndex ?? null,
            totalSteps: context.totalSteps ?? pageCtx2.totalSteps ?? null,
            url: window.location.href?.slice(0, 300),
            recentJsErrors: (window.__LIKHAPOHA_JS_ERRORS__ || []).slice(-5),
            recentApiErrors: (window.__LIKHAPOHA_API_ERRORS__ || []).slice(-5),
            screenshotDataUrl: screenshotDataUrl || null,
            screenshotCaptured: !!screenshotDataUrl,
          };
        })(),
      };

      const res = await authFetch("/api/issues/report", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      setDefectNumber(res?.defect_number || null);
      setSuccess(true);
      setForm(EMPTY_FORM);
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
    width: "100%", maxWidth: 520, boxShadow: "0 20px 60px rgba(0,0,0,0.2)",
    maxHeight: "90vh", overflowY: "auto",
  };
  const label = { display: "block", fontSize: ".8rem", fontWeight: 600, marginBottom: 5, color: "var(--text,#374151)" };
  const hint = { fontSize: ".72rem", color: "#94a3b8", marginTop: 3, marginBottom: 0 };
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
            {defectNumber && (
              <div style={{ textAlign: "center", marginBottom: 10 }}>
                <span data-testid="report-issue-defect-number" style={{
                  display: "inline-block", fontFamily: "monospace", fontWeight: 800,
                  fontSize: ".9rem", color: "#6366f1", background: "rgba(99,102,241,.08)",
                  borderRadius: 8, padding: "5px 12px",
                }}>{defectNumber}</span>
              </div>
            )}
            <p style={{ textAlign: "center", fontSize: ".85rem", color: "#64748b" }}>
              {defectNumber
                ? <>Save this reference ID — our team will review and fix it. Your feedback helps improve the platform.</>
                : <>Our team will review and fix this issue. Your feedback helps improve the platform.</>}
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
            {(() => {
              const pageCtx = (typeof window !== "undefined" && window.__LIKHAPOHA_CONTEXT__) || {};
              const mergedGrade = context.grade || pageCtx.grade;
              const mergedSubject = context.subject || pageCtx.subject;
              const mergedChapter = context.chapter || pageCtx.chapter;
              const mergedStep = context.lessonStep || pageCtx.lessonStep;
              return (mergedGrade || mergedSubject || mergedChapter) ? (
                <div style={{ background: "var(--surface2,#f8fafc)", borderRadius: 8, padding: "8px 12px",
                  fontSize: ".76rem", color: "#64748b", marginBottom: 16 }}>
                  <span style={{ fontWeight: 600 }}>Context: </span>
                  {[mergedGrade, mergedSubject, mergedChapter, mergedStep]
                    .filter(Boolean).join(" › ")}
                </div>
              ) : null;
            })()}

            {/* Issue type */}
            <div style={{ marginBottom: 14 }}>
              <label style={label}>What kind of issue is it?</label>
              <select style={input} value={form.issue_type}
                onChange={e => update("issue_type", e.target.value)}
                data-testid="issue-type-select">
                {ISSUE_TYPE_GROUPS.map(g => (
                  <optgroup key={g.label} label={g.label}>
                    {g.items.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                  </optgroup>
                ))}
              </select>
            </div>

            {/* Severity */}
            <div style={{ marginBottom: 14 }}>
              <label style={label}>How bad is it?</label>
              <div style={{ display: "flex", gap: 6 }}>
                {SEVERITIES.map(s => (
                  <button key={s.value} type="button"
                    onClick={() => update("severity", s.value)}
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

            {/* How often does it happen */}
            <div style={{ marginBottom: 14 }}>
              <label style={label}>How often does this happen? <span style={{ fontWeight: 400, color: "#94a3b8" }}>(optional)</span></label>
              <div style={{ display: "flex", gap: 6 }}>
                {REPRODUCIBILITY.map(r => (
                  <button key={r.value} type="button"
                    onClick={() => update("reproducibility", form.reproducibility === r.value ? "" : r.value)}
                    data-testid={`reproducibility-${r.value}`}
                    style={{
                      flex: 1, padding: "6px 4px", borderRadius: 7, fontFamily: "inherit",
                      fontSize: ".72rem", fontWeight: 600, cursor: "pointer",
                      border: "2px solid " + (form.reproducibility === r.value ? "#6366f1" : "var(--border,#e5e7eb)"),
                      background: form.reproducibility === r.value ? "#6366f115" : "transparent",
                      color: form.reproducibility === r.value ? "#6366f1" : "var(--text-muted,#64748b)",
                    }}>
                    {r.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Diagnostics summary badge */}
            {(() => {
              const jsErrCnt = (window.__LIKHAPOHA_JS_ERRORS__ || []).length;
              return (
                <div style={{ background: "rgba(16,185,129,.04)", borderRadius: 8, padding: "8px 12px",
                  fontSize: ".72rem", color: "#4b5563", marginBottom: 14, border: "1px solid rgba(16,185,129,.15)" }}>
                  <span style={{ fontWeight: 700, color: "#10b981" }}>Auto-captured: </span>
                  {[
                    "Viewport " + window.innerWidth + "x" + window.innerHeight,
                    "DPR " + window.devicePixelRatio,
                    window.innerWidth < 768 ? "Mobile" : "Desktop",
                    describeDevice(),
                    "v" + APP_VERSION,
                    jsErrCnt > 0 ? (jsErrCnt + " JS error(s)") : null,
                    screenshotDataUrl ? "Screenshot attached" : null,
                  ].filter(Boolean).join("  ·  ")}
                </div>
              );
            })()}

            {/* Screenshot attachment */}
            <div style={{ marginBottom: 14 }}>
              <label style={label}>Screenshot <span style={{ fontWeight: 400, color: "#94a3b8" }}>(optional, but a picture saves everyone time)</span></label>
              <input ref={fileInputRef} type="file" accept="image/*" data-testid="screenshot-input"
                onChange={handleFileChange} style={{ display: "none" }} />
              {!screenshotPreview ? (
                <button type="button" data-testid="attach-screenshot-btn"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={screenshotProcessing}
                  style={{ width: "100%", padding: "9px", borderRadius: 8, cursor: "pointer",
                    border: "1.5px dashed var(--border,#cbd5e1)", background: "transparent",
                    fontFamily: "inherit", fontSize: ".82rem", color: "#6366f1", fontWeight: 600 }}>
                  {screenshotProcessing ? "Compressing..." : "📎 Attach Screenshot"}
                </button>
              ) : (
                <div style={{ position: "relative", borderRadius: 8, overflow: "hidden",
                  border: "1px solid var(--border,#e5e7eb)" }}>
                  <img src={screenshotPreview} alt="Screenshot preview" data-testid="screenshot-preview"
                    style={{ width: "100%", display: "block", maxHeight: 200, objectFit: "contain" }} />
                  <button type="button" data-testid="remove-screenshot-btn"
                    onClick={removeScreenshot}
                    style={{ position: "absolute", top: 6, right: 6, background: "rgba(0,0,0,0.6)",
                      border: "none", borderRadius: "50%", width: 24, height: 24, color: "#fff",
                      cursor: "pointer", fontSize: ".8rem", lineHeight: 1 }}>✕</button>
                  <div style={{ padding: "4px 10px", fontSize: ".7rem", color: "#22c55e",
                    background: "rgba(34,197,94,.08)", fontWeight: 600 }}>
                    Screenshot attached and will be included in the report
                  </div>
                </div>
              )}
            </div>

            {/* Title (optional short summary) */}
            <div style={{ marginBottom: 14 }}>
              <label style={label}>Short summary <span style={{ fontWeight: 400, color: "#94a3b8" }}>(optional)</span></label>
              <input type="text" data-testid="issue-title"
                value={form.title} onChange={e => update("title", e.target.value)}
                placeholder="e.g. Submit button does nothing on Mock Test"
                maxLength={120} style={input} />
            </div>

            {/* Description */}
            <div style={{ marginBottom: 14 }}>
              <label style={label}>What happened? *</label>
              <textarea
                data-testid="issue-description"
                value={form.description}
                onChange={e => update("description", e.target.value)}
                placeholder="Describe what you found..."
                rows={3}
                style={{ ...input, resize: "vertical", minHeight: 76 }}
                maxLength={2000}
              />
              <div style={{ fontSize: ".72rem", color: "#94a3b8", textAlign: "right" }}>
                {form.description.length}/2000
              </div>
            </div>

            {/* Help us fix it faster — structured repro info, all optional but encouraged */}
            <div style={{ background: "var(--surface2,#f8fafc)", borderRadius: 10, padding: "12px 14px", marginBottom: 16 }}>
              <div style={{ fontSize: ".78rem", fontWeight: 700, color: "#6366f1", marginBottom: 8 }}>
                🔍 Help us fix it faster <span style={{ fontWeight: 400, color: "#94a3b8" }}>(optional, but this is what lets us close your report without asking follow-up questions)</span>
              </div>

              <div style={{ marginBottom: 10 }}>
                <label style={label}>Steps to reproduce</label>
                <textarea
                  data-testid="issue-steps"
                  value={form.steps_to_reproduce}
                  onChange={e => update("steps_to_reproduce", e.target.value)}
                  placeholder={"1. Go to...\n2. Tap/click...\n3. See the problem"}
                  rows={2}
                  style={{ ...input, resize: "vertical", minHeight: 54 }}
                  maxLength={1500}
                />
              </div>

              <div style={{ display: "flex", gap: 10, marginBottom: 2, flexWrap: "wrap" }}>
                <div style={{ flex: "1 1 200px" }}>
                  <label style={label}>What did you expect?</label>
                  <textarea
                    data-testid="issue-expected"
                    value={form.expected_behavior}
                    onChange={e => update("expected_behavior", e.target.value)}
                    placeholder="e.g. The quiz should submit"
                    rows={2}
                    style={{ ...input, resize: "vertical", minHeight: 54 }}
                    maxLength={1000}
                  />
                </div>
                <div style={{ flex: "1 1 200px" }}>
                  <label style={label}>What actually happened?</label>
                  <textarea
                    data-testid="issue-actual"
                    value={form.actual_behavior}
                    onChange={e => update("actual_behavior", e.target.value)}
                    placeholder="e.g. Nothing happens when I tap Submit"
                    rows={2}
                    style={{ ...input, resize: "vertical", minHeight: 54 }}
                    maxLength={1000}
                  />
                </div>
              </div>
              <p style={hint}>The more detail here, the faster we can confirm the fix and close your report.</p>
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
