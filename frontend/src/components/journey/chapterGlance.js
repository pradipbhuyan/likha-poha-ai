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

/**
 * Scroll to the "Chapter at a glance" poster, correcting for layout shift
 * caused by content that sits ABOVE the poster in the same milestone but
 * loads asynchronously without reserved space:
 *   - Matched textbook page images (TextbookImageBlock) have no width/height
 *     reserved and use loading="lazy" — see chapter_doc_service.py.
 *   - The poster itself DOES reserve its aspect ratio via width/height on
 *     the fence payload, so once everything above it has settled, the
 *     anchor's position is stable.
 *
 * A single scrollIntoView() at click time can land correctly and then get
 * pushed further down the page a moment later as those images above the
 * anchor finish loading — this was reported by a user as the nav link
 * "goes to images above it and I need to scroll down". Re-issuing the
 * scroll for ~2 seconds after the click corrects for that shift without
 * needing to know in advance how many images are still loading or how
 * large they will render.
 */
export function scrollToChapterGlance(event) {
  if (event) event.preventDefault();
  const el = document.getElementById(CHAPTER_GLANCE_ANCHOR);
  if (!el) return;

  let attempts = 0;
  const maxAttempts = 10; // ~2s total at 200ms apart
  const rescroll = () => {
    el.scrollIntoView({ behavior: "smooth", block: "start" });
    attempts += 1;
    if (attempts < maxAttempts) {
      setTimeout(rescroll, 200);
    }
  };
  rescroll();
}
