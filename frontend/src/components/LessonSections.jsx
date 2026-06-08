import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";

import StructuredVisualBlock from "./StructuredVisualBlock";
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

function cleanQuestionText(text) {
  return text
    .replace(/```[\s\S]*?```/g, "")
    .replace(/!\[[^\]]*\]\([^)]*\)/g, "")
    .replace(/\[[^\]]*\]\([^)]*\)/g, "")
    .replace(/[#*_`>]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function getQuestionPrompt(section) {
  const title = section.title.toLowerCase();
  const content = cleanQuestionText(section.content);
  const invitationOnly =
    /would you like (that|to|me to)\??$/i.test(content) ||
    /^(if you want|would you like|do you want|shall we|we can now)\b/i.test(
      content
    );

  if (invitationOnly) {
    return "";
  }

  const isQuestionSection =
    title.includes("question") ||
    title.includes("quick check") ||
    title.includes("self check") ||
    title.includes("practice");

  const labelledQuestionMatch = content.match(
    /(?:^|\s)(?:question|quick check|try this|your turn)\s*:\s*([^]+?)(?=(?:\s(?:answer|hint|solution)\s*:)|$)/i
  );

  if (labelledQuestionMatch) {
    const prompt = labelledQuestionMatch[1].trim();
    if (/^would you like (that|to|me to)\??$/i.test(prompt)) {
      return "";
    }

    return prompt.slice(0, 420);
  }

  if (isQuestionSection) {
    return content.slice(0, 420);
  }

  return "";
}

function LessonSections({ lesson, onEvaluateQuestion }) {
  /** Presents a generated lesson as expandable sections with validated visual support. */
  const sections = parseSections(normalizeTutorMarkdown(lesson));

  const [openSections, setOpenSections] = useState(
    sections.map((_, index) => index === 0)
  );
  const [questionModes, setQuestionModes] = useState({});
  const [questionAnswers, setQuestionAnswers] = useState({});
  const [questionFeedback, setQuestionFeedback] = useState({});
  const [questionLoading, setQuestionLoading] = useState({});

  function toggleSection(index) {
    /** Open or close a single lesson section without changing the others. */
    setOpenSections((prev) =>
      prev.map((item, i) => (i === index ? !item : item))
    );
  }

  async function handleEvaluateQuestion(index, question) {
    const answer = questionAnswers[index] || "";

    if (!answer.trim() || !onEvaluateQuestion) {
      return;
    }

    setQuestionLoading((prev) => ({ ...prev, [index]: true }));
    setQuestionFeedback((prev) => ({ ...prev, [index]: "" }));

    try {
      const result = await onEvaluateQuestion({ question, answer });

      setQuestionFeedback((prev) => ({
        ...prev,
        [index]:
          result?.evaluation ||
          result?.message ||
          "Your answer has been reviewed.",
      }));
    } catch {
      setQuestionFeedback((prev) => ({
        ...prev,
        [index]: "Could not evaluate this answer right now.",
      }));
    } finally {
      setQuestionLoading((prev) => ({ ...prev, [index]: false }));
    }
  }

  return (
    <div className="lesson-sections">
      {sections.map((section, index) => {
        const questionPrompt = getQuestionPrompt(section);
        const questionMode = questionModes[index] || "";
        const answer = questionAnswers[index] || "";
        const feedback = questionFeedback[index] || "";
        const loading = questionLoading[index] || false;

        return (
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
                  }}
                >
                  {section.content}
                </ReactMarkdown>

                {questionPrompt && (
                  <div className="lesson-inline-question-box">
                    <div>
                      <p className="lesson-inline-question-label">
                        Want to try this question?
                      </p>
                      <p className="lesson-inline-question-text">
                        {questionPrompt}
                      </p>
                    </div>

                    <div className="lesson-inline-question-actions">
                      <button
                        type="button"
                        className={
                          questionMode === "answer"
                            ? "inline-question-choice active"
                            : "inline-question-choice"
                        }
                        onClick={() =>
                          setQuestionModes((prev) => ({
                            ...prev,
                            [index]: "answer",
                          }))
                        }
                      >
                        Answer and evaluate
                      </button>

                      <button
                        type="button"
                        className={
                          questionMode === "think"
                            ? "inline-question-choice active muted"
                            : "inline-question-choice muted"
                        }
                        onClick={() =>
                          setQuestionModes((prev) => ({
                            ...prev,
                            [index]: "think",
                          }))
                        }
                      >
                        Leave for thinking
                      </button>
                    </div>

                    {questionMode === "think" && (
                      <p className="lesson-inline-thinking-note">
                        Saved as a thinking prompt. No answer will be checked.
                      </p>
                    )}

                    {questionMode === "answer" && (
                      <div className="lesson-inline-answer-panel">
                        <textarea
                          value={answer}
                          onChange={(event) =>
                            setQuestionAnswers((prev) => ({
                              ...prev,
                              [index]: event.target.value,
                            }))
                          }
                          placeholder="Write your answer here..."
                          rows={4}
                        />

                        <button
                          type="button"
                          className="primary-btn lesson-inline-evaluate-btn"
                          disabled={!answer.trim() || loading}
                          onClick={() =>
                            handleEvaluateQuestion(index, questionPrompt)
                          }
                        >
                          {loading ? "Evaluating..." : "Evaluate my answer"}
                        </button>

                        {feedback && (
                          <div className="lesson-inline-feedback">
                            <ReactMarkdown
                              remarkPlugins={[remarkGfm, remarkMath]}
                              rehypePlugins={[rehypeKatex]}
                            >
                              {feedback}
                            </ReactMarkdown>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

export default LessonSections;
