import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import ChapterInfographicBlock, {
  validateChapterInfographic,
} from "../components/ChapterInfographicBlock";
import LessonMarkdown from "../components/journey/LessonMarkdown";
import LessonSections from "../components/LessonSections";
import { extractChapterInfographics } from "../../../shared/utils/chapterInfographic.js";

// The real applied poster for Grade 12 Biology Chapter 9.
import authoredFile from "../../../backend/app/data/chapter_infographics/grade-12/biology/chapter-9-biotechnology-principles-and-processes.json";

const VALID = {
  url: "https://cdn.example.com/chapter-9.webp",
  alt: "One-page revision poster for Biotechnology: Principles and Processes.",
  caption: "Full-chapter revision poster.",
  width: 1183,
  height: 1329,
};

describe("ChapterInfographicBlock", () => {
  test("renders the poster with alt text, caption and a zoom affordance", () => {
    render(<ChapterInfographicBlock raw={JSON.stringify(VALID)} />);

    const img = screen.getByAltText(VALID.alt);
    expect(img).toBeInTheDocument();
    expect(img).toHaveAttribute("src", VALID.url);
    expect(img).toHaveAttribute("loading", "lazy");
    expect(screen.getByText("Chapter at a glance")).toBeInTheDocument();
    expect(screen.getByText(VALID.caption)).toBeInTheDocument();
    expect(screen.getByText(/Tap to enlarge/)).toBeInTheDocument();
  });

  test("reserves the aspect ratio so the poster does not shift the page as it loads", () => {
    const { container } = render(<ChapterInfographicBlock raw={JSON.stringify(VALID)} />);

    const frame = container.querySelector(".chapter-infographic-frame");
    expect(frame).toHaveStyle({ aspectRatio: "1183 / 1329" });
  });

  test("clicking opens a full-screen viewer, and closing dismisses it", () => {
    render(<ChapterInfographicBlock raw={JSON.stringify(VALID)} />);

    expect(document.querySelector(".chapter-infographic-viewer")).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: /open full size/i }));
    expect(document.querySelector(".chapter-infographic-viewer")).toBeInTheDocument();
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    // Body scroll is locked while the viewer is open.
    expect(document.body.style.overflow).toBe("hidden");

    fireEvent.click(screen.getByRole("button", { name: "Close" }));
    expect(document.querySelector(".chapter-infographic-viewer")).toBeNull();
    expect(document.body.style.overflow).not.toBe("hidden");
  });

  test("Escape closes the viewer", () => {
    render(<ChapterInfographicBlock raw={JSON.stringify(VALID)} />);

    fireEvent.click(screen.getByRole("button", { name: /open full size/i }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();

    fireEvent.keyDown(window, { key: "Escape" });
    expect(document.querySelector(".chapter-infographic-viewer")).toBeNull();
  });

  test("renders nothing when the image fails to load", () => {
    const { container } = render(<ChapterInfographicBlock raw={JSON.stringify(VALID)} />);

    fireEvent.error(screen.getByAltText(VALID.alt));
    expect(container).toBeEmptyDOMElement();
  });

  test("rejects invalid JSON", () => {
    const { container } = render(<ChapterInfographicBlock raw="not json" />);
    expect(container).toBeEmptyDOMElement();
  });

  // Content comes from the database, so an <img src> built from it must never
  // be able to carry an executable or inline-data URI.
  test("rejects unsafe URL schemes", () => {
    for (const url of [
      "javascript:alert(1)",
      "data:image/svg+xml;base64,PHN2Zz48L3N2Zz4=",
      "http://insecure.example.com/a.png",
      "",
    ]) {
      expect(validateChapterInfographic(JSON.stringify({ ...VALID, url }))).toBeNull();
    }
  });

  test("accepts https and app-relative URLs", () => {
    expect(validateChapterInfographic({ ...VALID, url: "https://a.example/b.webp" })).not.toBeNull();
    expect(validateChapterInfographic({ ...VALID, url: "/assets/b.webp" })).not.toBeNull();
  });

  test("requires alt text, since the poster replaces the chapter's text recap", () => {
    expect(validateChapterInfographic(JSON.stringify({ ...VALID, alt: "" }))).toBeNull();
    expect(validateChapterInfographic(JSON.stringify({ ...VALID, alt: "x".repeat(400) }))).toBeNull();
  });

  test("drops a nonsensical caption or dimensions rather than rejecting the poster", () => {
    const result = validateChapterInfographic({
      ...VALID,
      caption: "x".repeat(400),
      width: -5,
      height: "not a number",
    });

    expect(result).not.toBeNull();
    expect(result.caption).toBe("");
    expect(result.width).toBeNull();
    expect(result.height).toBeNull();
  });

  describe("extractChapterInfographics (mobile safety net)", () => {
    test("removes the fence from the text and returns the parsed poster", () => {
      const md = `## Chapter at a glance\n\n\`\`\`chapter-infographic\n${JSON.stringify(VALID)}\n\`\`\`\n`;
      const { text, infographics } = extractChapterInfographics(md);

      expect(text).toBe("## Chapter at a glance");
      expect(text).not.toContain("chapter-infographic");
      expect(text).not.toContain("https://");
      expect(infographics).toHaveLength(1);
      expect(infographics[0].url).toBe(VALID.url);
    });

    test("drops an unparseable fence entirely rather than leaking JSON", () => {
      const { text, infographics } = extractChapterInfographics(
        "Before\n\n```chapter-infographic\n{ not json\n```\n\nAfter",
      );

      expect(infographics).toEqual([]);
      expect(text).not.toContain("not json");
      expect(text).toContain("Before");
      expect(text).toContain("After");
    });

    test("handles empty and nullish input", () => {
      expect(extractChapterInfographics("")).toEqual({ text: "", infographics: [] });
      expect(extractChapterInfographics(null)).toEqual({ text: "", infographics: [] });
    });
  });

  test("a chapter-infographic fence renders as the poster, not as code", () => {
    const md = `\`\`\`chapter-infographic\n${JSON.stringify(VALID)}\n\`\`\``;
    const { container } = render(<LessonMarkdown>{md}</LessonMarkdown>);

    expect(container.querySelector(".chapter-infographic")).toBeInTheDocument();
    expect(screen.getByAltText(VALID.alt)).toBeInTheDocument();
    expect(container.querySelector("pre")).toBeNull();
  });

  test("renders through LessonSections as its own trailing section", () => {
    const lesson = [
      "## Summary",
      "- Gene expression produces the desired recombinant protein.",
      "",
      "## Chapter at a glance",
      "",
      "```chapter-infographic",
      JSON.stringify(VALID, null, 2),
      "```",
    ].join("\n");

    const { container } = render(<LessonSections lesson={lesson} subject="Biology" grade="Grade 12" />);

    expect(container.querySelector(".chapter-infographic")).toBeInTheDocument();
    expect(screen.getByAltText(VALID.alt)).toBeInTheDocument();
    expect(container.querySelector(".chapter-infographic pre")).toBeNull();
    expect(
      screen.getByText(/Gene expression produces the desired recombinant protein/),
    ).toBeInTheDocument();
  });

  // Guards what actually ships to Grade 12 students.
  test("the applied Grade 12 Biology poster is renderable", () => {
    const applied = validateChapterInfographic(authoredFile.infographic);

    expect(applied).not.toBeNull();
    expect(applied.url).toMatch(/^https:\/\/.+\.webp$/);
    expect(applied.alt.length).toBeGreaterThan(20);
    expect(applied.width).toBeGreaterThan(0);
    expect(applied.height).toBeGreaterThan(0);
  });
});
