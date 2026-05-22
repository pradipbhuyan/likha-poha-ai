import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import MermaidBlock from "./MermaidBlock";

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
  return title
    .replace(/\*\*/g, "")
    .replace(/#/g, "")
    .trim();
}

function parseSections(markdown) {
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

function LessonSections({ lesson }) {
  const sections = parseSections(lesson);

  const [openSections, setOpenSections] = useState(
    sections.map((_, index) => index === 0)
  );

  function toggleSection(index) {
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
                remarkPlugins={[remarkGfm]}
                components={{
                  code({ className, children }) {
                    const match = /language-mermaid/.exec(className || "");

                    if (match) {
                      return (
                        <MermaidBlock
                          chart={String(children).replace(/\n$/, "")}
                        />
                      );
                    }

                    return <code className={className}>{children}</code>;
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