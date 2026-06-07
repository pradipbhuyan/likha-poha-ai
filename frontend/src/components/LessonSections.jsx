import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";

import StructuredVisualBlock from "./StructuredVisualBlock";
import { getKeywordHint } from "../utils/keywordHints";
import { normalizeTutorMarkdown } from "../utils/markdownCleanup";

const SECTION_ICONS = {
  "What you will learn": "🎯",
  "Simple explanation": "📘",
  "Step-by-step breakdown": "🧩",
  "Worked example": "🧪",
  "Common mistake": "⚠️",
  "Quick check question": "✅",
  "Summary": "📌",
};

function cleanTitle(title) {
  /** Remove markdown heading noise so generated section titles render cleanly. */
  return title
    .replace(/\*\*/g, "")
    .replace(/#/g, "")
    .trim();
}

function parseSections(markdown) {
  /** Split the generated lesson markdown into collapsible, student-friendly sections. */
  const lines = markdown.split("\n");
  const sections = [];

  let currentTitle = "Introduction";
  let currentContent = [];

  for (const line of lines) {
    const match = line.match(/^#{0,3}\s*\**\s*\d+\.\s+(.*?)\**\s*$/);

    if (match) {
      if (currentContent.join("\n").trim()) {
        sections.push({
          title: cleanTitle(currentTitle),
          content: currentContent.join("\n"),
        });
      }

      currentTitle = cleanTitle(match[1]);
      currentContent = [];
    } else {
      currentContent.push(line);
    }
  }

  if (currentContent.join("\n").trim()) {
    sections.push({
      title: cleanTitle(currentTitle),
      content: currentContent.join("\n"),
    });
  }

  return sections;
}

function HighlightedStrong({ children }) {
  /** Turn generated bold key terms into hoverable study hints. */
  const hint = getKeywordHint(children);

  if (!hint) {
    return <strong>{children}</strong>;
  }

  return (
    <strong className="keyword-highlight" title={hint} aria-label={hint}>
      {children}
    </strong>
  );
}

function LessonSections({ lesson }) {
  /** Presents a generated lesson as expandable sections with validated visual support. */
  const sections = parseSections(normalizeTutorMarkdown(lesson));

  const [openSections, setOpenSections] = useState(
    sections.map((_, index) => index === 0)
  );

  function toggleSection(index) {
    /** Open or close a single lesson section without changing the others. */
    setOpenSections((prev) =>
      prev.map((item, i) => (i === index ? !item : item))
    );
  }

  return (
    <div className="lesson-sections">
      {sections.map((section, index) => (
        <div
          key={index}
          className={`lesson-section-card section-${index + 1}`}
        >
          <button
            type="button"
            className="lesson-section-header"
            onClick={() => toggleSection(index)}
          >
            <div className="lesson-section-title">
              <span className="lesson-section-icon">
                {SECTION_ICONS[section.title] || "📚"}
              </span>

              <span>
                {index + 1}. {section.title}
              </span>
            </div>

            <span className="lesson-section-arrow">
              {openSections[index] ? "⌃" : "⌄"}
            </span>
          </button>

          {openSections[index] && (
            <div className="lesson-section-body">
              <ReactMarkdown
                remarkPlugins={[remarkGfm, remarkMath]}
                rehypePlugins={[rehypeKatex]}
                components={{
                  code({ className, children }) {
                    const language = className || "";

                    if (/language-visual-json/.test(language)) {
                      return (
                        <StructuredVisualBlock
                          raw={String(children).replace(/\n$/, "")}
                        />
                      );
                    }

                    if (/language-mermaid/.test(language)) {
                      return null;
                    }

                    return <code className={className}>{children}</code>;
                  },
                  strong({ children }) {
                    return <HighlightedStrong>{children}</HighlightedStrong>;
                  },
                }}
              >
                {section.content}
              </ReactMarkdown>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

export default LessonSections;
