/**
 * chapterInfographic.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Single source of truth for the ```chapter-infographic fenced block — a
 * full-chapter revision poster image shown at the end of a chapter's final
 * lesson step.
 *
 * Companion to chapterSummary.js: that one renders a wall-chart from structured
 * text, this one renders an authored image. Both are shared by web
 * (frontend/src/components/ChapterInfographicBlock.jsx) and mobile
 * (mobile/components/ChapterInfographicCard.tsx) so the two platforms agree on
 * exactly what is renderable.
 *
 * Payload shape:
 *   {
 *     "url":     "https://.../chapter-9-biotechnology.webp",  // required, https
 *     "alt":     "Short description for screen readers",      // required
 *     "caption": "Optional line shown under the image",       // optional
 *     "width":   1183,                                        // optional, px
 *     "height":  1329                                         // optional, px
 *   }
 *
 * width/height are optional but strongly preferred: they let the renderer
 * reserve the correct aspect ratio before the image loads, so a heavy poster
 * does not shove the rest of the lesson down the page as it arrives.
 */

// Only https remote assets and app-relative paths are renderable. This blocks
// javascript:/data: URIs, which must never reach an <img src> built from
// database-stored content.
const SAFE_URL_RE = /^(https:\/\/|\/)[^\s<>"']+$/i;

const MAX_ALT_LENGTH = 300;
const MAX_CAPTION_LENGTH = 300;
const MAX_DIMENSION = 20000;

function cleanText(value) {
  return typeof value === "string" ? value.replace(/\s+/g, " ").trim() : "";
}

function validateDimension(value) {
  /** Accept only a sane positive pixel count; anything else is ignored. */
  const n = typeof value === "number" ? value : Number.parseInt(value, 10);
  return Number.isFinite(n) && n > 0 && n <= MAX_DIMENSION ? Math.round(n) : null;
}

/**
 * Parse and validate a chapter-infographic payload.
 * Accepts a JSON string or an already-parsed object.
 * Returns a normalized object, or null when the payload cannot be rendered
 * safely — showing nothing beats showing a broken image frame.
 */
export function validateChapterInfographic(raw) {
  let data = raw;
  if (typeof raw === "string") {
    try {
      data = JSON.parse(raw);
    } catch {
      return null;
    }
  }

  if (!data || typeof data !== "object") return null;

  const url = cleanText(data.url);
  if (!url || !SAFE_URL_RE.test(url)) return null;

  // Alt text is required, not optional: replacing a chapter's text recap with
  // an image removes everything a screen reader had to work with, so a payload
  // without a description is treated as incomplete rather than rendered blind.
  const alt = cleanText(data.alt);
  if (alt.length < 2 || alt.length > MAX_ALT_LENGTH) return null;

  const caption = cleanText(data.caption);

  return {
    url,
    alt,
    caption: caption.length >= 2 && caption.length <= MAX_CAPTION_LENGTH ? caption : "",
    width: validateDimension(data.width),
    height: validateDimension(data.height),
  };
}

// Matches a ```chapter-infographic fenced block, tolerating extra backticks and
// stray whitespace after the language tag, mirroring the other fence helpers.
const FENCED_CHAPTER_INFOGRAPHIC_RE = /```+\s*chapter-infographic\s*\n?([\s\S]*?)```+/gi;

/**
 * Pull every chapter-infographic fence out of a markdown string.
 *
 * Returns { text, infographics }: `text` is the markdown with the fences
 * removed, `infographics` are the validated payloads to render natively.
 *
 * Platforms without a fenced-code component hook (React Native's markdown
 * renderer) call this first, so an unparseable payload is dropped entirely
 * rather than dumped on the student as raw JSON.
 */
export function extractChapterInfographics(content) {
  const infographics = [];
  const text = String(content ?? "").replace(
    FENCED_CHAPTER_INFOGRAPHIC_RE,
    (_match, payload) => {
      const parsed = validateChapterInfographic(payload);
      if (parsed) infographics.push(parsed);
      // Unparseable — drop from text, never show raw JSON.
      return "";
    },
  );
  return { text: text.trim(), infographics };
}
