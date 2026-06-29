/**
 * ReportIssueModal.jsx — Enhanced Issue Reporting with Screenshot + Dev Context
 * Auto-captures: page context, lesson/chapter/step, JS errors, performance,
 * localStorage keys (no values), window size, and optional screenshot.
 * Window.__LIKHAPOHA_CONTEXT__ can be set by any page to pass lesson context.
 */
import { useEffect, useState } from "react";
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

// ── Global JS error + API error tracker ──────────────────────────────────────
if (typeof window !== "undefined" && !window.__LIKHAPOHA_ERRORS__) {
  window.__LIKHAPOHA_ERRORS__ = [];
  window.__LIKHAPOHA_API_ERRORS__ = [];
  window.addEventListener("error", (e) => {
    window.__LIKHAPOHA_ERRORS__.push({
      message: e.message?.slice(0, 200),
      filename: e.filename?.split("/").slice(-2).join("/"),
      lineno: e.lineno,
      ts: new Date().toISOString(),
    });
    if (window.__LIKHAPOHA_ERRORS__.length > 10) window.__LIKHAPOHA_ERRORS__.shift();
  });
  window.addEventListener("unhandledrejection", (e) => {
    window.__LIKHAPOHA_ERRORS__.push({
      message: String(e.reason)?.slice(0, 200),
      type: "unhandledrejection",
      ts: new Date().toISOString(),
    });
    if (window.__LIKHAPOHA_ERRORS__.length > 10) window.__LIKHAPOHA_ERRORS__.shift();
  });
}

function captureDevContext() {
  const pageCtx = (typeof window !== "undefined" && window.__LIKHAPOHA_CONTEXT__) || {};
  const jsErrors = (typeof window !== "undefined" && window.__LIKHAPOHA_ERRORS__) || [];
  const apiErrors = (typeof window !== "undefined" && window.__LIKHAPOHA_API_ERRORS__) || [];
  return {
    page: pageCtx.page || (typeof document !== "undefined" ? document.title : "") || "unknown",
    grade: pageCtx.grade || null,
    subject: pageCtx.subject || null,
    chapter: pageCtx.chapter || null,
    lessonId: pageCtx.lessonId || null,
    lessonStep: pageCtx.lessonStep || null,
    lessonStepIndex: pageCtx.lessonStepIndex != null ? pageCtx.lessonStepIndex : null,
    totalSteps: pageCtx.totalSteps || null,
    url: typeof window !== "undefined" ? window.location.href : "",
    userAgent: typeof navigator !== "undefined" ? navigator.userAgent?.slice(0, 300) : "",
    platform: typeof navigator !== "undefined" ? navigator.platform : "",
    language: typeof navigator !== "undefined" ? navigator.language : "",
    screenWidth: typeof window !== "undefined" ? window.screen?.width : null,
    screenHeight: typeof window !== "undefined" ? window.screen?.height : null,
    viewportWidth: typeof window !== "undefined" ? window.innerWidth : null,
    viewportHeight: typeof window !== "undefined" ? window.innerHeight : null,
    devicePixelRatio: typeof window !== "undefined" ? window.devicePixelRatio : null,
    timezone: typeof Intl !== "undefined" ? Intl.DateTimeFormat().resolvedOptions().timeZone : "",
    online: typeof navigator !== "undefined" ? navigator.onLine : true,
    pageLoadMs: (() => {
      try {
        const t = performance.timing;
        const ms = t.loadEventEnd - t.navigationStart;
        return ms > 0 ? ms : null;
      } catch { return null; }
    })(),
    recentJsErrors: jsErrors.slice(-5),
    recentApiErrors: apiErrors.slice(-5),
    localStorageKeys: (() => {
      try { return Object.keys(localStorage).filter(k => k.startsWith("tutor_")); }
      catch { return []; }
    })(),
    capturedAt: new Date().toISOString(),
  };
}

export default function ReportIssueModal({ open, onClose, context = {}, user }) {
  const [form, setForm] = useState({ issue_type: "content_issue", severity: "medium", description: "" });
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState(null);
  const [screenshotDataUrl, setScreenshotDataUrl] = useState(null);
  const [capturing, setCapturing] = useState(false);
  const [devCtx, setDevCtx] = useState({});

  useEffect(() => {
    if (open) setDevCtx(captureDevContext());
  }, [open]);

  function reset() {
    setForm({ issue_type: "content_issue", severity: "medium", description: "" });
    setSuccess(false); setError(null); setScreenshotDataUrl(null);
  }

  function handleClose() { reset(); onClose(); }

  async function captureScreenshot() {
    setCapturing(true); setError(null);
    try {
      if (navigator.mediaDevices?.getDisplayMedia) {
        const stream = await navigator.mediaDevices.getDisplayMedia({
          video: true, preferCurrentTab: true,
        });
        const video = document.createElement("video");
        video.srcObject = stream;
        await new Promise(r => { video.onloadedmetadata = r; });
        await video.play();
        await new Promise(r => setTimeout(r, 200));
        const canvas = document.createElement("canvas");
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext("2d").drawImage(video, 0, 0);
        stream.getTracks().forEach(t => t.stop());
        const dataUrl = canvas.toDataURL("image/jpeg", 0.6);
        setScreenshotDataUrl(dataUrl);
      } else {
        setError("Screenshot capture not supported in this browser.");
      }
    } catch (e) {
      if (!String(e.message).toLowerCase().includes("cancel") &&
          !String(e.name).toLowerCase().includes("notallowed")) {
        setError("Screenshot failed: " + e.message);
      }
    } finally { setCapturing(false); }
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!form.description.trim() || form.description.trim().length < 10) {
      setError("Please describe the issue in at least 10 characters.");
      return;
    }
    setSubmitting(true); setError(null);
    try {
      const devCtxSnap = Object.keys(devCtx).length > 0 ? devCtx : captureDevContext();
      const payload = {
        issue_type: form.issue_type,
        severity: form.severity,
        description: form.description.trim().slice(0, 2000),
        route: context.route || devCtxSnap.page,
        grade: context.grade || devCtxSnap.grade || user?.grade || null,
        subject: context.subject || devCtxSnap.subject || null,
        chapter: context.chapter || devCtxSnap.chapter || null,
        lesson_id: context.lessonId || devCtxSnap.lessonId || null,
        lesson_step: context.lessonStep || devCtxSnap.lessonStep || null,
        screenshot_url: screenshotDataUrl ? "[data-url-captured]" : null,
        browser_info: {
          userAgent: devCtxSnap.userAgent,
          platform: devCtxSnap.platform,
          language: devCtxSnap.language,
          screenWidth: devCtxSnap.screenWidth,
          screenHeight: devCtxSnap.screenHeight,
          viewportWidth: devCtxSnap.viewportWidth,
          viewportHeight: devCtxSnap.viewportHeight,
          devicePixelRatio: devCtxSnap.devicePixelRatio,
          timezone: devCtxSnap.timezone,
          online: devCtxSnap.online,
          url: devCtxSnap.url,
          grade: devCtxSnap.grade,
          subject: devCtxSnap.subject,
          chapter: devCtxSnap.chapter,
          lessonStep: devCtxSnap.lessonStep,
          lessonStepIndex: devCtxSnap.lessonStepIndex,
          totalSteps: devCtxSnap.totalSteps,
          pageLoadMs: devCtxSnap.pageLoadMs,
          recentJsErrors: devCtxSnap.recentJsErrors,
          recentApiErrors: devCtxSnap.recentApiErrors,
          localStorageKeys: devCtxSnap.localStorageKeys,
          capturedAt: devCtxSnap.capturedAt,
          screenshotCaptured: !!screenshotDataUrl,
        },
      };
      await authFetch("/api/issues/report", { method: "POST", body: JSON.stringify(payload) });
      // Store screenshot in sessionStorage for admin to retrieve if needed
      if (screenshotDataUrl) {
        try { sessionStorage.setItem("last_report_screenshot", screenshotDataUrl); }
        catch { /* quota exceeded */ }
      }
      setSuccess(true);
      setForm({ issue_type: "content_issue", severity: "medium", description: "" });
    } catch (err) {
      setError(err.message || "Failed to submit issue. Please try again.");
    } finally { setSubmitting(false); }
  }

  if (!open) return null;

  const overlay = {
    position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", zIndex: 2000,
    display: "flex", alignItems: "center", justifyContent: "center", padding: 16,
  };
  const box = {
    background: "var(--panel,#fff)", borderRadius: 14, padding: "22px 26px",
    width: "100%", maxWidth: 500, boxShadow: "0 20px 60px rgba(0,0,0,0.25)",
    maxHeight: "92vh", overflowY: "auto",
  };
  const lbl = { display: "block", fontSize: ".8rem", fontWeight: 600, marginBottom: 5, color: "var(--text,#374151)" };
  const inp = {
    width: "100%", padding: "9px 12px", borderRadius: 8,
    border: "1px solid var(--border,#e5e7eb)", fontFamily: "inherit", fontSize: ".85rem",
    background: "var(--panel,#fff)", color: "var(--text,#374151)", boxSizing: "border-box",
  };

  const ctxItems = [
    devCtx.page && ["Page", devCtx.page],
    devCtx.grade && ["Grade", devCtx.grade],
    devCtx.subject && ["Subject", devCtx.subject],
    devCtx.chapter && ["Chapter", devCtx.chapter],
    devCtx.lessonStep && ["Step", `${devCtx.lessonStep}${devCtx.lessonStepIndex != null ? ` (${Number(devCtx.lessonStepIndex)+1}/${devCtx.totalSteps})` : ""}`],
    devCtx.recentJsErrors?.length > 0 && ["⚠ JS Errors", devCtx.recentJsErrors.length + " recent"],
  ].filter(Boolean);

  return (
    <div style={overlay} onClick={e => { if (e.target === e.currentTarget) handleClose(); }}>
      <div style={box} data-testid="report-issue-modal">
        <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:16 }}>
          <h3 style={{ margin:0, fontWeight:800, fontSize:"1rem" }}>🐛 Report an Issue</h3>
          <button onClick={handleClose} aria-label="Close"
            style={{ background:"none", border:"none", cursor:"pointer", fontSize:"1.3rem", color:"#94a3b8" }}>✕</button>
        </div>

        {success ? (
          <div data-testid="report-issue-success" style={{ textAlign:"center" }}>
            <div style={{ fontSize:"2.5rem", marginBottom:10 }}>✅</div>
            <p style={{ fontWeight:700, marginBottom:6 }}>Thank you for reporting!</p>
            <p style={{ fontSize:".85rem", color:"#64748b", marginBottom:16 }}>
              Our team will review and fix this issue.
            </p>
            <button onClick={handleClose} data-testid="report-issue-close-success"
              style={{ width:"100%", padding:"10px", borderRadius:8, border:"none",
                background:"#6366f1", color:"#fff", fontWeight:700, fontSize:".85rem",
                cursor:"pointer", fontFamily:"inherit" }}>
              Close
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} data-testid="report-issue-form">
            {/* Auto-captured context */}
            {ctxItems.length > 0 && (
              <div style={{ background:"var(--surface2,#f0f4ff)", borderRadius:8, padding:"8px 12px",
                fontSize:".73rem", color:"#4b5563", marginBottom:14, lineHeight:1.6 }}>
                <span style={{ fontWeight:700, color:"#6366f1" }}>📍 Auto-captured context: </span>
                {ctxItems.map(([k, v]) => (
                  <span key={k} style={{ marginRight:8 }}>
                    <span style={{ fontWeight:600 }}>{k}:</span> {v}
                  </span>
                ))}
              </div>
            )}

            {/* Issue type */}
            <div style={{ marginBottom:14 }}>
              <label style={lbl}>Issue Type</label>
              <select style={inp} value={form.issue_type}
                onChange={e => setForm(p => ({ ...p, issue_type: e.target.value }))}
                data-testid="issue-type-select">
                {ISSUE_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </div>

            {/* Severity */}
            <div style={{ marginBottom:14 }}>
              <label style={lbl}>Severity</label>
              <div style={{ display:"flex", gap:6 }}>
                {SEVERITIES.map(s => (
                  <button key={s.value} type="button"
                    onClick={() => setForm(p => ({ ...p, severity: s.value }))}
                    data-testid={`severity-${s.value}`}
                    style={{
                      flex:1, padding:"6px 4px", borderRadius:7, fontFamily:"inherit",
                      fontSize:".76rem", fontWeight:600, cursor:"pointer",
                      border:`2px solid ${form.severity === s.value ? s.color : "var(--border,#e5e7eb)"}`, b)"}`,
                      background: form.severity === s.value ? s.color + "15" : "transparent",
                      color: form.severity === s.value ? s.color : "var(--text-muted,#64748b)",
                    }}>
                    {s.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Description */}
            <div style={{ marginBottom:14 }}>
              <label style={lbl}>Description *</label>
              <textarea
                data-testid="issue-description"
                value={form.description}
                onChange={e => setForm(p => ({ ...p, description: e.target.value }))}
                placeholder="Describe what you found, what you expected, and any steps to reproduce..."
                rows={4}
                style={{ ...inp, resize:"vertical", minHeight:90 }}
                maxLength={2000}
              />
              <div style={{ fontSize:".7rem", color:"#94a3b8", textAlign:"right" }}>
                {form.description.length}/2000
              </div>
            </div>

            {/* Screenshot */}
            <div style={{ marginBottom:14 }}>
              <label style={lbl}>Screenshot (optional)</label>
              <div style={{ display:"flex", gap:8, alignItems:"center", flexWrap:"wrap" }}>
                <button type="button" onClick={captureScreenshot} disabled={capturing}
                  data-testid="capture-screenshot-btn"
                  style={{ padding:"7px 14px", borderRadius:8, border:"1px solid var(--border,#e5e7eb)",
                    background:"transparent", color:"#6366f1", fontWeight:600, fontSize:".8rem",
                    cursor:capturing?"not-allowed":"pointer", fontFamily:"inherit" }}>
                  {capturing ? "Capturing…" : screenshotDataUrl ? "📷 Retake" : "📷 Capture Screen"}
                </button>
                {screenshotDataUrl && (
                  <div style={{ position:"relative", display:"inline-block" }}>
                    <img src={screenshotDataUrl} alt="Screenshot preview"
                      style={{ height:48, borderRadius:6, border:"1px solid var(--border,#e5e7eb)", cursor:"pointer" }}
                      onClick={() => window.open(screenshotDataUrl, "_blank")}
                      title="Click to view full size" />
                    <button type="button" onClick={() => setScreenshotDataUrl(null)}
                      style={{ position:"absolute", top:-6, right:-6, background:"#ef4444", color:"#fff",
                        border:"none", borderRadius:"50%", width:18, height:18, fontSize:".65rem",
                        cursor:"pointer", lineHeight:"18px", textAlign:"center" }}>✕</button>
                  </div>
                )}
              </div>
              <div style={{ fontSize:".72rem", color:"#94a3b8", marginTop:4 }}>
                Uses browser screen capture — you control what is shared.
              </div>
            </div>

            {error && (
              <div data-testid="report-issue-error"
                style={{ background:"#fef2f2", border:"1px solid #fecaca", borderRadius:8,
                  padding:"8px 12px", color:"#dc2626", fontSize:".8rem", marginBottom:12 }}>
                {error}
              </div>
            )}

            <button type="submit" disabled={submitting} data-testid="submit-issue-btn"
              style={{ width:"100%", padding:"10px", borderRadius:8, border:"none",
                background:submitting?"#94a3b8":"#6366f1", color:"#fff", fontWeight:700,
                fontSize:".85rem", cursor:submitting?"not-allowed":"pointer", fontFamily:"inherit" }}>
              {submitting ? "Submitting…" : "Submit Report"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
