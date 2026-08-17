/**
 * chapterSummary.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Single source of truth for the ```chapter-summary fenced block — the
 * whole-chapter revision wall-chart appended to a chapter's final lesson step
 * by backend/scripts/apply_chapter_summary.py.
 *
 * Shared by web (frontend/src/components/ChapterSummaryBlock.jsx) and mobile
 * (mobile/components/ChapterSummaryCard.tsx) so both platforms agree on exactly
 * what is renderable. Without a shared schema the two drift, and a payload that
 * looks fine on the web silently degrades to a raw JSON blob on a phone.
 *
 * The caps below are mirrored in backend/scripts/apply_chapter_summary.py so an
 * over-long field is rejected at authoring time rather than being quietly
 * dropped from the student's page.
 */

export const MAX_PANELS = 8;
export const MAX_POINTS_PER_PANEL = 6;
export const MAX_PIPELINE_STEPS = 12;
export const MAX_TERMS = 10;
export const MAX_REMEMBER = 8;

/** Normalize label text without changing its meaning. */
function cleanText(value) {
  return typeof value === "string" ? value.replace(/\s+/g, " ").trim() : "";
}

/** Keep summary text complete, bounded, and markup-safe. */
function isSafeLabel(value, maxLength) {
  const text = cleanText(value);
  return text.length >= 2 && text.length <= maxLength && !/[<>]/.test(text);
}

function validateStringList(raw, { max, maxLength }) {
  if (!Array.isArray(raw)) return [];
  return raw
    .filter((item) => isSafeLabel(item, maxLength))
    .slice(0, max)
    .map(cleanText);
}

function validatePanels(raw) {
  if (!Array.isArray(raw)) return [];
  return raw
    .map((panel) => {
      if (!panel || typeof panel !== "object") return null;
      const heading = cleanText(panel.heading);
      if (!isSafeLabel(heading, 60)) return null;
      const points = validateStringList(panel.points, {
        max: MAX_POINTS_PER_PANEL,
        maxLength: 180,
      });
      // A panel with a heading and no readable points is an empty box.
      return points.length ? { heading, points } : null;
    })
    .filter(Boolean)
    .slice(0, MAX_PANELS);
}

function validatePipeline(raw) {
  if (!raw || typeof raw !== "object") return null;
  const heading = cleanText(raw.heading);
  if (!isSafeLabel(heading, 80)) return null;

  const steps = (Array.isArray(raw.steps) ? raw.steps : [])
    .map((step) => {
      if (!step || typeof step !== "object") return null;
      const label = cleanText(step.label);
      if (!isSafeLabel(label, 45)) return null;
      const detail = cleanText(step.detail);
      return { label, detail: isSafeLabel(detail, 160) ? detail : "" };
    })
    .filter(Boolean)
    .slice(0, MAX_PIPELINE_STEPS);

  // A pipeline is a sequence; fewer than two steps is not one.
  return steps.length >= 2 ? { heading, steps } : null;
}

function validateTerms(raw) {
  if (!Array.isArray(raw)) return [];
  return raw
    .map((entry) => {
      if (!entry || typeof entry !== "object") return null;
      const term = cleanText(entry.term);
      const meaning = cleanText(entry.meaning);
      if (!isSafeLabel(term, 45) || !isSafeLabel(meaning, 180)) return null;
      return { term, meaning };
    })
    .filter(Boolean)
    .slice(0, MAX_TERMS);
}

/**
 * Parse and validate a chapter-summary payload.
 * Accepts a JSON string or an already-parsed object.
 * Returns a normalized summary, or null when nothing renderable survives —
 * showing nothing is better than showing a half-built card at a chapter's end.
 */
export function validateChapterSummary(raw) {
  let summary = raw;
  if (typeof raw === "string") {
    try {
      summary = JSON.parse(raw);
    } catch {
      return null;
    }
  }

  if (!summary || typeof summary !== "object") return null;

  const title = cleanText(summary.title);
  if (!isSafeLabel(title, 90)) return null;

  const subtitle = cleanText(summary.subtitle);
  const definition = cleanText(summary.definition);

  const panels = validatePanels(summary.panels);
  const pipeline = validatePipeline(summary.pipeline);
  const terms = validateTerms(summary.terms);
  const remember = validateStringList(summary.remember, {
    max: MAX_REMEMBER,
    maxLength: 200,
  });

  // A title alone is not a summary — require at least one populated section.
  if (!panels.length && !pipeline && !terms.length && !remember.length) {
    return null;
  }

  return {
    title,
    subtitle: isSafeLabel(subtitle, 140) ? subtitle : "",
    definition: isSafeLabel(definition, 260) ? definition : "",
    panels,
    pipeline,
    terms,
    remember,
  };
}

// Matches a ```chapter-summary fenced block, tolerating extra backticks and
// stray whitespace after the language tag the way the mobile visual-json /
// extract-ref safety nets already do.
const FENCED_CHAPTER_SUMMARY_RE = /```+\s*chapter-summary\s*\n?([\s\S]*?)```+/gi;

/**
 * Pull every chapter-summary fence out of a markdown string.
 *
 * Returns { text, summaries }: `text` is the markdown with the fences removed,
 * `summaries` are the validated payloads to render natively alongside it.
 *
 * Platforms without a fenced-code component hook (React Native's markdown
 * renderer) call this first, so an unparseable payload is dropped entirely
 * rather than dumped on the student as a wall of raw JSON.
 */
export function extractChapterSummaries(content) {
  const summaries = [];
  const text = String(content ?? "").replace(FENCED_CHAPTER_SUMMARY_RE, (_match, payload) => {
    const parsed = validateChapterSummary(payload);
    if (parsed) summaries.push(parsed);
    // Unparseable — drop from text, never show raw JSON.
    return "";
  });
  return { text: text.trim(), summaries };
}
