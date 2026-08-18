/**
 * chapterGlance.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Locates the chapter-infographic poster inside a chapter doc so both renderers
 * can offer a "Chapter at a glance" entry in their navigation:
 *   - StudyRenderer  (Grades 9-12, "On this chapter" outline)
 *   - JourneyRenderer (Grades 5-8, "Chapter path" rail)
 *
 * Shared rather than duplicated because the two must agree: the nav link and
 * the anchor it scrolls to are derived from the same lookup, so a poster can
 * never gain a link without a target or vice versa.
 *
 * See docs/CHAPTER_INFOGRAPHIC_FEATURE.md.
 */

/** Anchor id stamped on the block holding the poster. */
export const CHAPTER_GLANCE_ANCHOR = "chapter-at-a-glance";

/** Label used for the navigation entry in both renderers. */
export const CHAPTER_GLANCE_LABEL = "Chapter at a glance";

const FENCE_RE = /```+\s*chapter-infographic/i;

/**
 * Find the block carrying a ```chapter-infographic fence.
 * Returns { mi, bi } or null.
 *
 * Derived from content rather than keyed to a chapter name, so the entry
 * appears exactly for chapters that actually have a poster and needs no
 * per-chapter wiring as more are authored.
 *
 * Restricted to "concept" blocks because that is the only block type in either
 * renderer that stamps the anchor — matching a type whose anchor is never
 * rendered would put a dead link in the navigation. The chapter-doc converter
 * currently emits the "## Chapter at a glance" section as a concept block for
 * every grade (verified Grade 5 EVS and Grade 12 Biology).
 */
export function findChapterGlance(doc) {
  const milestones = doc?.milestones || [];
  for (let mi = 0; mi < milestones.length; mi += 1) {
    const blocks = milestones[mi]?.blocks || [];
    for (let bi = 0; bi < blocks.length; bi += 1) {
      const block = blocks[bi];
      if (block?.type === "concept" && FENCE_RE.test(block.body_md || "")) {
        return { mi, bi };
      }
    }
  }
  return null;
}
