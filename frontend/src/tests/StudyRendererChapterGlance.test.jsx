import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import StudyRenderer from "../components/journey/StudyRenderer";

const INFOGRAPHIC = {
  url: "https://cdn.example.com/chapter-9.webp",
  alt: "One-page revision poster for Biotechnology: Principles and Processes.",
  caption: "Full-chapter revision poster.",
  width: 1183,
  height: 1329,
};

/** Mirrors the real chapter doc: the poster is a `concept` block sitting last
 *  in the final milestone ("Revision and recap"). */
function buildDoc({ withInfographic }) {
  const recapBlocks = [
    { type: "concept", title: "Simple explanation", body_md: "Cloning a gene is not the final objective." },
  ];
  if (withInfographic) {
    recapBlocks.push({
      type: "concept",
      title: "Chapter at a glance",
      body_md: ["```chapter-infographic", JSON.stringify(INFOGRAPHIC, null, 2), "```"].join("\n"),
    });
  }
  return {
    milestones: [
      { title: "Concept introduction", blocks: [{ type: "concept", body_md: "Intro." }] },
      { title: "Revision and recap", blocks: recapBlocks },
    ],
    recap: { body_md: "Wrap-up text." },
    exam: [],
  };
}

describe("StudyRenderer — Chapter at a glance outline link", () => {
  test("adds the outline link when the chapter has a poster", () => {
    render(<StudyRenderer doc={buildDoc({ withInfographic: true })} />);

    const link = screen.getByRole("link", { name: /chapter at a glance/i });
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute("href", "#study-chapter-at-a-glance");
  });

  test("the link target exists, so it actually scrolls somewhere", () => {
    const { container } = render(<StudyRenderer doc={buildDoc({ withInfographic: true })} />);

    const target = container.querySelector("#study-chapter-at-a-glance");
    expect(target).toBeInTheDocument();
    // The anchored block is the one holding the poster.
    expect(target.querySelector(".chapter-infographic")).toBeInTheDocument();
    expect(screen.getByAltText(INFOGRAPHIC.alt)).toBeInTheDocument();
  });

  test("sits below the last milestone and above Wrap-up", () => {
    const { container } = render(<StudyRenderer doc={buildDoc({ withInfographic: true })} />);

    const outline = container.querySelector(".study-outline");
    const labels = Array.from(outline.querySelectorAll("a")).map((a) => a.textContent.trim());

    expect(labels).toEqual([
      "Concept introduction",
      "Revision and recap",
      "Chapter at a glance",
      "Wrap-up",
    ]);
  });

  test("no link when the poster sits in a block type that cannot be anchored", () => {
    const doc = buildDoc({ withInfographic: true });
    // Only the "concept" branch of StudyBlock renders anchorId; a link here
    // would scroll nowhere.
    doc.milestones[1].blocks[1].type = "watchout";

    const { container } = render(<StudyRenderer doc={doc} />);

    expect(screen.queryByRole("link", { name: /chapter at a glance/i })).toBeNull();
    expect(container.querySelector("#study-chapter-at-a-glance")).toBeNull();
  });

  test("is absent for a chapter with no poster", () => {
    const { container } = render(<StudyRenderer doc={buildDoc({ withInfographic: false })} />);

    expect(screen.queryByRole("link", { name: /chapter at a glance/i })).toBeNull();
    expect(container.querySelector("#study-chapter-at-a-glance")).toBeNull();
    // The anchor id is never stamped on an unrelated block.
    expect(container.querySelectorAll("[id^='study-chapter']")).toHaveLength(0);
  });
});
