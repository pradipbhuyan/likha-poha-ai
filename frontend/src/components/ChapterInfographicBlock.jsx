import { useEffect, useState } from "react";
import { createPortal } from "react-dom";

import { validateChapterInfographic } from "../../../shared/utils/chapterInfographic.js";

export { validateChapterInfographic };

/**
 * ChapterInfographicBlock — renders a ```chapter-infographic fenced block as a
 * full-chapter revision poster at the end of a chapter's final lesson step.
 *
 * A revision poster is dense by nature: at lesson-column width the panel text
 * is too small to read, so the inline image is a preview and the real reading
 * experience is the full-screen viewer behind a click/tap. That mirrors
 * ExtractPopupBlock's scanned-textbook-page pattern, including the portal —
 * several app-shell ancestors use backdrop-filter, which silently breaks
 * position:fixed for any descendant not portaled out to document.body.
 *
 * Fails safe: an unparseable or unsafe payload renders nothing rather than a
 * broken image frame at the end of the chapter.
 */
function ChapterInfographicBlock({ raw }) {
  const [open, setOpen] = useState(false);
  const [failed, setFailed] = useState(false);
  const infographic = validateChapterInfographic(raw);

  // Esc closes the viewer, and body scroll is locked while it is open so the
  // lesson page behind does not scroll under the overlay on wheel/touch.
  useEffect(() => {
    if (!open) return undefined;
    const onKeyDown = (e) => { if (e.key === "Escape") setOpen(false); };
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  // A dead image URL would otherwise leave an empty framed box with a caption
  // under it, which reads as a bug to the student.
  if (!infographic || failed) return null;

  const { url, alt, caption, width, height } = infographic;
  // Reserve the correct box before the image arrives so a ~240KB poster does
  // not shove the rest of the lesson down the page as it loads.
  const aspectRatio = width && height ? `${width} / ${height}` : undefined;

  return (
    <>
      <figure className="chapter-infographic">
        <figcaption className="chapter-infographic-eyebrow">Chapter at a glance</figcaption>

        <button
          type="button"
          className="chapter-infographic-frame"
          onClick={() => setOpen(true)}
          aria-haspopup="dialog"
          aria-label={`${alt} — open full size`}
          style={aspectRatio ? { aspectRatio } : undefined}
        >
          <img
            src={url}
            alt={alt}
            width={width || undefined}
            height={height || undefined}
            loading="lazy"
            decoding="async"
            onError={() => setFailed(true)}
          />
          <span className="chapter-infographic-zoom-hint" aria-hidden="true">
            🔍 Tap to enlarge
          </span>
        </button>

        {caption && <figcaption className="chapter-infographic-caption">{caption}</figcaption>}
      </figure>

      {open && createPortal(
        <div
          role="dialog"
          aria-modal="true"
          aria-label={alt}
          className="chapter-infographic-viewer"
          onClick={(e) => { if (e.target === e.currentTarget) setOpen(false); }}
        >
          <div className="chapter-infographic-viewer-bar">
            <span>{caption || "Chapter at a glance"}</span>
            <div className="chapter-infographic-viewer-actions">
              <a href={url} target="_blank" rel="noopener noreferrer">Open full size</a>
              <button type="button" onClick={() => setOpen(false)} aria-label="Close">✕</button>
            </div>
          </div>

          {/* The scroll container is the zoom: the image renders at natural
              width so panel text is legible, and the student pans around it.
              Pinch-zoom still works on top of this on touch devices. */}
          <div
            className="chapter-infographic-viewer-scroll"
            onClick={(e) => { if (e.target === e.currentTarget) setOpen(false); }}
          >
            <img src={url} alt={alt} />
          </div>
        </div>,
        document.body,
      )}
    </>
  );
}

export default ChapterInfographicBlock;
