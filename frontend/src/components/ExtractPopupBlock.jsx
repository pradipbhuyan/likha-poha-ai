import { useState } from "react";
import { createPortal } from "react-dom";
import ReactMarkdown from "react-markdown";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";

/**
 * ExtractPopupBlock — renders a clickable citation pill for a fenced
 * ```extract-ref``` JSON block. Clicking it opens a small modal showing the
 * actual referenced source text (e.g. an NCERT "Critical Reflection" extract
 * or exercise question), so a bare citation like "NCERT Critical Reflection
 * I.2(iv)" is never left dangling with nothing for the student to refer to.
 *
 * Expected JSON shape (see prepare_gpt55_prompts.py for the generation
 * rule that requires this block wherever a humanities/language worked
 * example or quick-check cites a specific NCERT extract/exercise number):
 *   {
 *     "citation": "NCERT Critical Reflection I.2(iv)",
 *     "extract_text": "The actual excerpt or exercise text, verbatim from
 *                       the source PDF, that the citation refers to.",
 *     "note": "optional short context line, e.g. chapter/section name"
 *   }
 *
 * Fails safe: if the raw JSON is malformed or missing required fields,
 * renders nothing rather than showing a broken block.
 */

function parseExtract(raw) {
  try {
    const data = JSON.parse(raw);
    if (
      data &&
      typeof data.citation === "string" &&
      data.citation.trim().length > 0 &&
      typeof data.extract_text === "string" &&
      data.extract_text.trim().length > 0
    ) {
      return {
        citation: data.citation.trim(),
        extract_text: data.extract_text.trim(),
        note: typeof data.note === "string" ? data.note.trim() : "",
      };
    }
    return null;
  } catch {
    return null;
  }
}

function ExtractText({ children }) {
  if (!children) return null;
  if (!children.includes("$") && !children.includes("\\")) {
    return <>{children}</>;
  }
  return (
    <ReactMarkdown
      remarkPlugins={[remarkMath]}
      rehypePlugins={[rehypeKatex]}
      components={{ p: ({ children: c }) => <>{c}</> }}
    >
      {children}
    </ReactMarkdown>
  );
}

function ExtractPopupBlock({ raw }) {
  const [open, setOpen] = useState(false);
  const extract = parseExtract(raw);

  if (!extract) return null;

  return (
    <>
      <button
        type="button"
        className="extract-ref-pill"
        onClick={() => setOpen(true)}
        aria-haspopup="dialog"
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: 6,
          padding: "4px 12px",
          borderRadius: 20,
          border: "1.5px solid rgba(99,102,241,.35)",
          background: "rgba(99,102,241,.08)",
          color: "#6366f1",
          fontSize: ".82rem",
          fontWeight: 600,
          fontFamily: "inherit",
          cursor: "pointer",
          margin: "2px 0",
        }}
      >
        <span aria-hidden="true">📖</span>
        {extract.citation}
        <span style={{ opacity: 0.7, fontWeight: 500 }}>· view text</span>
      </button>

      {open && createPortal(
        <div
          role="dialog"
          aria-modal="true"
          onClick={(e) => { if (e.target === e.currentTarget) setOpen(false); }}
          style={{
            position: "fixed",
            inset: 0,
            // Solid enough to fully hide whatever is behind it in BOTH
            // themes — a semi-transparent rgba(0,0,0,.45) scrim let the
            // underlying scanned-textbook-page image and lesson text show
            // through in dark mode (reported via screenshot: the popup's
            // own text overlapped with a bleed-through page image behind
            // it, making both unreadable). Rendered via a portal straight
            // into document.body (see createPortal below) so this fixed
            // overlay is always positioned relative to the real viewport —
            // any ancestor with backdrop-filter/filter/transform (the app
            // shell's topbar and cards use backdrop-filter: blur(...) in
            // several places) breaks position:fixed for descendants that
            // aren't portaled out, which was the root cause of the
            // mispositioned/overlapping modal in the screenshot.
            background: "rgba(2,6,23,0.72)",
            zIndex: 2100,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: 16,
          }}
        >
          <div
            style={{
              background: "var(--panel, #fff)",
              border: "1px solid var(--border, #e2e8f0)",
              borderRadius: 14,
              padding: "22px 26px",
              width: "100%",
              maxWidth: 560,
              maxHeight: "80vh",
              overflowY: "auto",
              boxShadow: "0 20px 60px rgba(0,0,0,0.45)",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "flex-start",
                gap: 12,
                marginBottom: 14,
              }}
            >
              <div>
                <div style={{ fontSize: ".72rem", fontWeight: 700, color: "#6366f1", letterSpacing: ".03em", textTransform: "uppercase" }}>
                  Source text
                </div>
                <h4 style={{ margin: "4px 0 0", fontSize: "1rem", fontWeight: 800, color: "var(--text,#1f2937)" }}>
                  {extract.citation}
                </h4>
              </div>
              <button
                onClick={() => setOpen(false)}
                aria-label="Close"
                style={{ background: "none", border: "none", cursor: "pointer", fontSize: "1.2rem", color: "#94a3b8", flexShrink: 0 }}
              >
                ✕
              </button>
            </div>

            {extract.note && (
              <p style={{ fontSize: ".78rem", color: "#64748b", marginBottom: 10, fontStyle: "italic" }}>
                {extract.note}
              </p>
            )}

            <div
              style={{
                background: "var(--surface2,#f8fafc)",
                borderRadius: 10,
                padding: "14px 16px",
                fontSize: ".92rem",
                lineHeight: 1.6,
                color: "var(--text,#374151)",
                whiteSpace: "pre-wrap",
              }}
            >
              <ExtractText>{extract.extract_text}</ExtractText>
            </div>

            <button
              onClick={() => setOpen(false)}
              style={{
                width: "100%",
                marginTop: 16,
                padding: "10px",
                borderRadius: 8,
                border: "none",
                background: "#6366f1",
                color: "#fff",
                fontWeight: 700,
                fontSize: ".85rem",
                cursor: "pointer",
                fontFamily: "inherit",
              }}
            >
              Close
            </button>
          </div>
        </div>,
        document.body,
      )}
    </>
  );
}

export default ExtractPopupBlock;
