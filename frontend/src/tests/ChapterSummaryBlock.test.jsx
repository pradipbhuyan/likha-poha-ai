import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

// The real authored content that ships to Grade 12 students. Imported directly
// so a cap breach in the source file fails CI rather than silently rendering as
// a missing section at the end of the chapter.
import authoredFile from "../../../backend/app/data/chapter_summaries/grade-12/biology/chapter-9-biotechnology-principles-and-processes.json";

import ChapterSummaryBlock, {
  validateChapterSummary,
} from "../components/ChapterSummaryBlock";
import LessonMarkdown from "../components/journey/LessonMarkdown";
import LessonSections from "../components/LessonSections";
import { extractChapterSummaries } from "../../../shared/utils/chapterSummary.js";

const VALID = {
  title: "Biotechnology: Principles and Processes",
  subtitle: "Whole-chapter recap.",
  definition: "Biotechnology uses living organisms to make useful products.",
  panels: [
    {
      heading: "Restriction enzymes",
      points: [
        "Endonucleases cut at positions within DNA.",
        "Staggered cutting leaves sticky ends.",
      ],
    },
  ],
  pipeline: {
    heading: "Major steps",
    steps: [
      { label: "Isolation of DNA", detail: "Lysozyme breaks the bacterial wall." },
      { label: "Ligation", detail: "DNA ligase seals the backbones." },
    ],
  },
  terms: [{ term: "Vector", meaning: "DNA molecule that carries foreign DNA into a host." }],
  remember: ["DNA migrates toward the anode because it is negatively charged."],
};

describe("ChapterSummaryBlock", () => {
  test("renders every populated section", () => {
    render(<ChapterSummaryBlock raw={JSON.stringify(VALID)} />);

    expect(screen.getByText("Chapter summary")).toBeInTheDocument();
    expect(screen.getByText("Biotechnology: Principles and Processes")).toBeInTheDocument();
    expect(screen.getByText("Whole-chapter recap.")).toBeInTheDocument();
    expect(screen.getByText(/Biotechnology uses living organisms/)).toBeInTheDocument();
    expect(screen.getByText("Restriction enzymes")).toBeInTheDocument();
    expect(screen.getByText("Staggered cutting leaves sticky ends.")).toBeInTheDocument();
    expect(screen.getByText("Major steps")).toBeInTheDocument();
    expect(screen.getByText("Isolation of DNA")).toBeInTheDocument();
    expect(screen.getByText("Vector")).toBeInTheDocument();
    expect(screen.getByText(/migrates toward the anode/)).toBeInTheDocument();
  });

  test("rejects invalid JSON", () => {
    const { container } = render(<ChapterSummaryBlock raw="not json" />);
    expect(container).toBeEmptyDOMElement();
  });

  test("rejects a payload with a title but no populated section", () => {
    expect(validateChapterSummary(JSON.stringify({ title: "Only a title" }))).toBeNull();
  });

  test("rejects a missing or unsafe title", () => {
    expect(validateChapterSummary(JSON.stringify({ ...VALID, title: "" }))).toBeNull();
    expect(
      validateChapterSummary(JSON.stringify({ ...VALID, title: "<script>alert(1)</script>" })),
    ).toBeNull();
  });

  test("drops over-long panel points instead of rendering a clipped card", () => {
    const summary = validateChapterSummary(
      JSON.stringify({
        ...VALID,
        panels: [
          {
            heading: "Restriction enzymes",
            points: ["x".repeat(300), "Short and safe point."],
          },
        ],
      }),
    );

    expect(summary.panels[0].points).toEqual(["Short and safe point."]);
  });

  test("drops a panel whose points are all unusable", () => {
    const summary = validateChapterSummary(
      JSON.stringify({ ...VALID, panels: [{ heading: "Empty panel", points: ["x".repeat(300)] }] }),
    );

    expect(summary.panels).toEqual([]);
  });

  test("drops a pipeline with fewer than two steps", () => {
    const summary = validateChapterSummary(
      JSON.stringify({
        ...VALID,
        pipeline: { heading: "Major steps", steps: [{ label: "Isolation of DNA" }] },
      }),
    );

    expect(summary.pipeline).toBeNull();
  });

  test("caps section lengths so a runaway payload cannot blow out the page", () => {
    const summary = validateChapterSummary(
      JSON.stringify({
        ...VALID,
        panels: Array.from({ length: 20 }, (_, i) => ({
          heading: `Panel ${i}`,
          points: Array.from({ length: 20 }, (_, j) => `Point ${j}`),
        })),
        terms: Array.from({ length: 20 }, (_, i) => ({ term: `Term ${i}`, meaning: "A meaning." })),
        remember: Array.from({ length: 20 }, (_, i) => `Remember ${i}`),
      }),
    );

    expect(summary.panels).toHaveLength(8);
    expect(summary.panels[0].points).toHaveLength(6);
    expect(summary.terms).toHaveLength(10);
    expect(summary.remember).toHaveLength(8);
  });

  test("accepts an already-parsed object as well as a JSON string", () => {
    expect(validateChapterSummary(VALID)).not.toBeNull();
  });

  test("a chapter-summary fence in lesson markdown renders as the card, not code", () => {
    const markdown = [
      "## Chapter at a glance",
      "",
      "```chapter-summary",
      JSON.stringify(VALID, null, 2),
      "```",
    ].join("\n");

    const { container } = render(<LessonMarkdown>{markdown}</LessonMarkdown>);

    expect(container.querySelector(".chapter-summary-card")).toBeInTheDocument();
    expect(screen.getByText("Restriction enzymes")).toBeInTheDocument();
    // The <pre> wrapper would force monospace + white-space:pre onto the card.
    expect(container.querySelector("pre")).toBeNull();
  });

  // End-to-end through the layout students actually see (USE_WORKBOOK_LAYOUT).
  test("renders through LessonSections as its own trailing section", () => {
    const lesson = [
      "# Expression, bioreactors and downstream processing",
      "",
      "## Summary",
      "- Gene expression produces the desired recombinant protein.",
      "",
      "## Chapter at a glance",
      "",
      "```chapter-summary",
      JSON.stringify(VALID, null, 2),
      "```",
    ].join("\n");

    const { container } = render(<LessonSections lesson={lesson} subject="Biology" grade="Grade 12" />);

    expect(container.querySelector(".chapter-summary-card")).toBeInTheDocument();
    expect(screen.getByText("Isolation of DNA")).toBeInTheDocument();
    expect(screen.getByText("Vector")).toBeInTheDocument();
    // The original lesson content is untouched by the appended section.
    expect(screen.getByText(/Gene expression produces the desired recombinant protein/)).toBeInTheDocument();
  });

  // extractChapterSummaries is what keeps raw JSON off the MOBILE screen —
  // React Native's markdown renderer has no per-fence component hook, so the
  // fence must be removed from the text before it is handed to the renderer.
  describe("extractChapterSummaries (mobile safety net)", () => {
    const fence = ["```chapter-summary", JSON.stringify(VALID), "```"].join("\n");

    test("removes the fence from the text and returns the parsed summary", () => {
      const { text, summaries } = extractChapterSummaries(
        `## Chapter at a glance\n\n${fence}\n`,
      );

      expect(text).toBe("## Chapter at a glance");
      expect(text).not.toContain("chapter-summary");
      expect(text).not.toContain("{");
      expect(summaries).toHaveLength(1);
      expect(summaries[0].title).toBe(VALID.title);
    });

    test("drops an unparseable fence entirely rather than leaking JSON", () => {
      const { text, summaries } = extractChapterSummaries(
        "Before\n\n```chapter-summary\n{ not json\n```\n\nAfter",
      );

      expect(summaries).toEqual([]);
      expect(text).not.toContain("not json");
      expect(text).toContain("Before");
      expect(text).toContain("After");
    });

    test("leaves markdown without a chapter-summary fence untouched", () => {
      const markdown = "## Summary\n\n- A point.\n\n```visual-json\n{}\n```";
      const { text, summaries } = extractChapterSummaries(markdown);

      expect(text).toBe(markdown.trim());
      expect(summaries).toEqual([]);
    });

    test("handles empty and nullish input", () => {
      expect(extractChapterSummaries("")).toEqual({ text: "", summaries: [] });
      expect(extractChapterSummaries(null)).toEqual({ text: "", summaries: [] });
      expect(extractChapterSummaries(undefined)).toEqual({ text: "", summaries: [] });
    });

    test("extracts the real authored block from the stored lesson format", () => {
      const stored = [
        "## Summary",
        "- Gene expression produces the desired recombinant protein.",
        "",
        "## Chapter at a glance",
        "",
        "```chapter-summary",
        JSON.stringify(authoredFile.summary, null, 2),
        "```",
      ].join("\n");

      const { text, summaries } = extractChapterSummaries(stored);

      expect(summaries).toHaveLength(1);
      expect(summaries[0].panels).toHaveLength(authoredFile.summary.panels.length);
      expect(text).not.toContain("chapter-summary");
      expect(text).toContain("Gene expression produces the desired recombinant protein.");
    });
  });

  test("the authored Grade 12 Biology summary survives validation intact", () => {
    const file = authoredFile;
    const summary = validateChapterSummary(file.summary);

    expect(summary).not.toBeNull();
    // Nothing was silently dropped by a cap or a length check.
    expect(summary.panels).toHaveLength(file.summary.panels.length);
    file.summary.panels.forEach((panel, i) => {
      expect(summary.panels[i].points).toHaveLength(panel.points.length);
    });
    expect(summary.pipeline.steps).toHaveLength(file.summary.pipeline.steps.length);
    expect(summary.terms).toHaveLength(file.summary.terms.length);
    expect(summary.remember).toHaveLength(file.summary.remember.length);
    expect(summary.definition).not.toBe("");
    expect(summary.subtitle).not.toBe("");
  });
});
