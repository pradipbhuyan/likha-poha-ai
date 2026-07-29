import os

path = '/Users/a0247716/Pradips_Project/cbse-tutor-platform/frontend/src/components/ReportIssueModal.jsx'

content = r"""/**
 * ReportIssueModal.jsx — Student/User Issue Reporting
 * Enhanced: viewport, DPR, computed font, JS errors, screenshot attachment.
 */
import { useRef, useState } from "react";
import { authFetch } from "../api/authClient";

const ISSUE_TYPES = [
  { value: "content_issue",     label: "Content issue" },
  { value: "wrong_explanation", label: "Wrong explanation" },
  { value: "missing_section",   label: "Missing lesson section" },
  { value: "wrong_formula",     label: "Wrong formula" },
  { value: "wrong_answer",      label: "Wrong answer / MCQ" },
  { value: "broken_page",       label: "Broken page / button" },
  { value: "login_issue",       label: "Login / access issue" },
  { value: "other",             label: "Other" },
];
const SEVERITIES = [
  { value: "low",      label: "Low",      color: "#94a3b8" },
  { value: "medium",   label: "Medium",   color: "#f59e0b" },
  { value: "high",     label: "High",     color: "#f97316" },
  { value: "critical", label: "Critical", color: "#ef4444" },
];

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

function buildBrowserInfo(context, screenshotDataUrl) {
  const pageCtx = (typeof window !== "undefined" && window.__LIKHAPOHA_CONTEXT__) || {};
  let computedFont = null;
  try {
    const el = document.querySelector(".markdown-content") || document.querySelector(".lesson-output");
    if (el) computedFont = window.getComputedStyle(el).fontFamily?.slice(0, 150);
  } catch { /* non-critical */ }
  let elementAtCenter = null;
  try {
    const el = document.elementFromPoint(window.innerWidth / 2, window.innerHeight / 2);
    if (el && el !== document.body) {
      const cs = window.getComputedStyle(el);
      elementAtCenter = { tag: el.tagName, classes: el.className?.slice(0, 80),
        fontSize: cs.fontSize, fontFamily: cs.fontFamily?.slice(0, 80), display: cs.display };
    }
  } catch { /* non-critical */ }
  let stepTextContent = null;
  try {
    const el = document.querySelector(".markdown-content") || document.querySelector(".lesson-output");
    if (el) stepTextContent = el.textContent?.trim().slice(0, 500) || null;
  } catch { /* non-critical */ }
  let pageLoadMs = null;
  try {
    if (performance?.timing?.navigationStart) pageLoadMs = Date.now() - performance.timing.navigationStart;
  } catch { /* */ }
  return {
    userAgent: navigator.userAgent?.slice(0, 200),
    platform: navigator.platform,
    screenWidth: window.screen?.width,
    screenHeight: window.screen?.height,
    viewportWidth: window.innerWidth,
    viewportHeight: window.innerHeight,
    devicePixelRatio: window.devicePixelRatio,
    scrollY: Math.round(window.scrollY),
    online: navigator.onLine,
    pageLoadMs,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    computedFont,
    elementAtCenter,
    stepTextContent,
    lessonStepIndex: context.lessonStepIndex ?? pageCtx.lessonStepIndex ?? null,
    totalSteps: context.totalSteps ?? pageCtx.totalSteps ?? null,
    grade: context.grade || pageCtx.grade || null,
    subject: context.subject || pageCtx.subject || null,
    chapter: context.chapter || pageCtx.chapter || null,
    lessonStep: context.lessonStep || pageCtx.lessonStep || null,
    url: window.location.href?.slice(0, 300),
    recentJsErrors: (window.__LIKHAPOHA_JS_ERRORS__ || []).slice(-5),
    recentApiErrors: (window.__LIKHAPOHA_API_ERRORS__ || []).slice(-5),
    screenshotDataUrl: screenshotDataUrl || null,
    screenshotCaptured: !!screenshotDataUrl,
  };
}

export default function ReportIssueModal({ open, onClose, context, user }) {
  const ctx = context || {};
  const [form, setForm] = useState({ issue_type: "content_issue", severity: "medium", description: "" });
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState(null);
  const [screenshotPreview, setScreenshotPreview] = useState(null);
  const [screenshotProcessing, setScreenshotProcessing] = useState(false);
  const [screenshotDataUrl, setScreenshotDataUrl] = useState(null);
  const fileInputRef = useRef(null);

  function reset() {
    setForm({ issue_type: "content_issue", severity: "medium", description: "" });
    setSuccess(false); setError(null); setScreenshotPreview(null); setScreenshotDataUrl(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }
  function handleClose() { reset(); onClose(); }

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

  async function handleSubmit(e) {
    e.preventDefault();
    if (!form.description.trim() || form.description.trim().length < 10) {
      setError("Please describe the issue in at least 10 characters."); return;
    }
    setSubmitting(true); setError(null);
    try {
      const pageCtx = (typeof window !== "undefined" && window.__LIKHAPOHA_CONTEXT__) || {};
      await authFetch("/api/issues/report", {
        method: "POST",
        body: JSON.stringify({
          issue_type: form.issue_type,
          severity: form.severity,
          description: form.description.trim().slice(0, 2000),
          route: ctx.route || pageCtx.page || window.location.pathname,
          grade: ctx.grade || pageCtx.grade || user?.grade || null,
          subject: ctx.subject || pageCtx.subject || null,
          chapter: ctx.chapter || pageCtx.chapter || null,
          lesson_id: ctx.lessonId || pageCtx.lessonId || null,
          lesson_step: ctx.lessonStep || pageCtx.lessonStep || null,
          browser_info: buildBrowserInfo(ctx, screenshotDataUrl),
        }),
      });
      setSuccess(true); reset();
    } catch (err) { setError(err.message || "Failed to submit. Please try again."); }
    finally { setSubmitting(false); }
  }

  if (!open) return null;

  const pageCtx = (typeof window !== "undefined" && window.__LIKHAPOHA_CONTEXT__) || {};
  const mGrade   = ctx.grade   || pageCtx.grade;
  const mSubject = ctx.subject || pageCtx.subject;
  const mChapter = ctx.chapter || pageCtx.chapter;
  const mStep    = ctx.lessonStep || pageCtx.lessonStep;
  const mIdx     = ctx.lessonStepIndex ?? pageCtx.lessonStepIndex;
  const mTotal   = ctx.totalSteps ?? pageCtx.totalSteps;
  const jsErrs   = (window.__LIKHAPOHA_JS_ERRORS__ || []).length;

  const inp = {
    width: "100%", padding: "9px 12px", borderRadius: 8,
    border: "1px solid var(--border,#e5e7eb)", fontFamily: "inherit", fontSize: ".85rem",
    background: "var(--panel,#fff)", color: "var(--text,#374151)", boxSizing: "border-box",
  };

  return (
    <div onClick={e => { if (e.target === e.currentTarget) handleClose(); }}
      style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.55)", zIndex: 2000,
        display: "flex", alignItems: "center", justifyContent: "center", padding: 16 }}>
      <div data-testid="report-issue-modal"
        style={{ background: "var(--panel,#fff)", borderRadius: 14, padding: "24px 26px",
          width: "100%", maxWidth: 500, boxShadow: "0 20px 60px rgba(0,0,0,0.25)",
          maxHeight: "92vh", overflowY: "auto" }}>

        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <h3 style={{ margin: 0, fontWeight: 800, fontSize: "1rem" }}>Report an Issue</h3>
          <button onClick={handleClose} aria-label="Close"
            style={{ background: "none", border: "none", cursor: "pointer", fontSize: "1.2rem", color: "#94a3b8" }}>
            X
          </button>
        </div>

        {success ? (
          <div data-testid="report-issue-success">
            <p style={{ textAlign: "center", fontWeight: 700, marginBottom: 8 }}>Thank you for reporting!</p>
            <p style={{ textAlign: "center", fontSize: ".85rem", color: "#64748b" }}>
              Our team will review and fix this issue.
            </p>
            <button onClick={handleClose} data-testid="report-issue-close-success"
              style={{ width: "100%", marginTop: 16, padding: "10px", borderRadius: 8, border: "none",
                background: "#6366f1", color: "#fff", fontWeight: 700, fontSize: ".85rem",
                cursor: "pointer", fontFamily: "inherit" }}>Close</button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} data-testid="report-issue-form">

            {(mGrade || mSubject || mChapter) && (
              <div style={{ background: "rgba(99,102,241,.06)", borderRadius: 8, padding: "8px 12px",
                fontSize: ".76rem", color: "#4b5563", marginBottom: 12,
                border: "1px solid rgba(99,102,241,.15)" }}>
                <strong style={{ color: "#6366f1" }}>Context: </strong>
                {[mGrade, mSubject, mChapter, mStep].filter(Boolean).join(" > ")}
                {mIdx != null && mTotal != null &&
                  <span style={{ color: "#94a3b8" }}> (step {mIdx + 1}/{mTotal})</span>}
              </div>
            )}

            <div style={{ background: "rgba(16,185,129,.04)", borderRadius: 8, padding: "8px 12px",
              fontSize: ".72rem", color: "#4b5563", marginBottom: 14,
              border: "1px solid rgba(16,185,129,.15)" }}>
              <div style={{ fontWeight: 700, color: "#10b981", marginBottom: 4 }}>Auto-captured diagnostics:</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                {[
                  "Viewport " + window.innerWidth + "x" + window.innerHeight,
                  "DPR " + window.devicePixelRatio,
                  navigator.platform,
                  window.innerWidth < 768 ? "Mobile" : "Desktop",
                  jsErrs > 0 ? (jsErrs + " JS error(s) logged") : null,
                  "Scroll " + Math.round(window.scrollY) + "px",
                  screenshotDataUrl ? "Screenshot attached" : null,
                ].filter(Boolean).map((tag, i) => (
                  <span key={i} style={{ background: "rgba(16,185,129,.1)", color: "#065f46",
                    padding: "1px 7px", borderRadius: 12 }}>{tag}</span>
                ))}
              </div>
            </div>

            <div style={{ marginBottom: 14 }}>
              <label style={{ display: "block", fontSize: ".8rem", fontWeight: 600, marginBottom: 5,
                color: "var(--text,#374151)" }}>Issue Type</label>
              <select style={inp} value={form.issue_type}
                onChange={e => setForm(p => ({ ...p, issue_type: e.target.value }))}
                data-testid="issue-type-select">
                {ISSUE_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </div>

            <div style={{ marginBottom: 14 }}>
              <label style={{ display: "block", fontSize: ".8rem", fontWeight: 600, marginBottom: 5,
                color: "var(--text,#374151)" }}>Severity</label>
              <div style={{ display: "flex", gap: 6 }}>
                {SEVERITIES.map(s => (
                  <button key={s.value} type="button"
                    onClick={() => setForm(p => ({ ...p, severity: s.value }))}
                    data-testid={"severity-" + s.value}
                    style={{
                      flex: 1, padding: "6px 4px", borderRadius: 7, fontFamily: "inherit",
                      fontSize: ".76rem
