import { useState } from "react";
import { AlertTriangle, Award, BookOpen, CheckCircle2, GraduationCap, HelpCircle } from "lucide-react";

import LessonMarkdown from "./LessonMarkdown";
import StructuredVisualBlock from "../StructuredVisualBlock";

/**
 * StudyRenderer — Grades 9-12.
 * Exam-serious document: sticky milestone outline, dense concept sections,
 * worked examples with attempt-first answer reveals, inline quick checks.
 * All interactions are local — zero API calls while reading.
 */

function StudyQuickCheck({ block, blockKey, savedAnswer, onAnswer }) {
  const [picked, setPicked] = useState(savedAnswer ?? null);
  const answered = picked !== null && picked !== undefined;

  return (
    <div style={{
      background: "var(--panel, #fff)", border: "1px solid var(--border, #d6ddeb)",
      borderRadius: 10, padding: "14px 16px", margin: "12px 0",
    }}>
      <div style={{
        fontSize: ".7rem", fontWeight: 800, letterSpacing: ".1em",
        textTransform: "uppercase", color: "var(--accent, #2d4a8a)", marginBottom: 6,
      }}>
        Quick check
      </div>
      <div style={{ fontSize: ".92rem", fontWeight: 600, marginBottom: 8, lineHeight: 1.5 }}>
        <LessonMarkdown unwrapParagraph>{block.question}</LessonMarkdown>
      </div>
      {block.options.map((option, index) => {
        const isRight = index === block.answer_index;
        const isPicked = picked === index;
        return (
          <label key={index} style={{
            display: "flex", alignItems: "flex-start", gap: 8,
            fontSize: ".88rem", padding: "5px 4px", cursor: answered ? "default" : "pointer",
            color: answered && isRight ? "#15803d"
              : answered && isPicked ? "#b3261e"
              : "var(--text, #29324a)",
            fontWeight: answered && (isRight || isPicked) ? 700 : 500,
          }}>
            <input
              type="radio"
              name={`sqc-${blockKey}`}
              checked={isPicked}
              disabled={answered}
              onChange={() => {
                setPicked(index);
                onAnswer?.(blockKey, index, index === block.answer_index);
              }}
              style={{ marginTop: 3 }}
            />
            <LessonMarkdown unwrapParagraph>{option}</LessonMarkdown>
          </label>
        );
      })}
      {answered && block.explanation && (
        <div style={{
          borderTop: "1px dashed var(--border, #d6ddeb)", marginTop: 8, paddingTop: 8,
          fontSize: ".85rem", color: "var(--muted, #64748b)", lineHeight: 1.55,
        }}>
          <LessonMarkdown unwrapParagraph>{block.explanation}</LessonMarkdown>
        </div>
      )}
    </div>
  );
}

function StudyExample({ block }) {
  const [revealed, setRevealed] = useState(false);
  return (
    <div style={{
      background: "var(--panel, #fff)", border: "1px solid var(--border, #d6ddeb)",
      borderLeft: "3px solid var(--accent, #2d4a8a)",
      borderRadius: "0 10px 10px 0", padding: "14px 16px", margin: "12px 0",
    }}>
      <div style={{
        fontSize: ".7rem", fontWeight: 800, letterSpacing: ".1em",
        textTransform: "uppercase", color: "var(--accent, #2d4a8a)", marginBottom: 6,
      }}>
        Worked example
      </div>
      <div style={{ fontSize: ".92rem", fontWeight: 600, lineHeight: 1.55 }}>
        <LessonMarkdown unwrapParagraph>{block.question}</LessonMarkdown>
      </div>
      {revealed ? (
        <div className="lesson-section-body" style={{ marginTop: 10, fontSize: ".9rem", lineHeight: 1.6 }}>
          <LessonMarkdown>{block.body_md}</LessonMarkdown>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => setRevealed(true)}
          style={{
            marginTop: 10, font: "inherit", fontSize: ".8rem", fontWeight: 700,
            color: "var(--accent, #2d4a8a)", background: "none",
            border: "1px solid var(--border, #c3cfe6)", borderRadius: 7,
            padding: "5px 12px", cursor: "pointer",
          }}
        >
          Attempt it first, then show the solution
        </button>
      )}
    </div>
  );
}

function ExamQAItem({ item }) {
  const [revealed, setRevealed] = useState(false);
  return (
    <div style={{
      background: "var(--panel, #fff)", border: "1px solid var(--border, #d6ddeb)",
      borderRadius: 10, padding: "14px 16px", marginBottom: 12,
    }}>
      <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", marginBottom: 6 }}>
        <span style={{
          background: "var(--accent-soft, #eef3ff)", color: "var(--accent, #2d4a8a)",
          fontSize: ".68rem", fontWeight: 800, borderRadius: 5, padding: "2px 8px",
        }}>
          {item.marks} mark{item.marks === 1 ? "" : "s"}
        </span>
        {item.year && (
          <span style={{
            background: "var(--border, #f1f5f9)", color: "var(--muted, #64748b)",
            fontSize: ".68rem", fontWeight: 700, borderRadius: 5, padding: "2px 8px",
          }}>
            {item.year}
          </span>
        )}
      </div>
      <div style={{ fontSize: ".92rem", fontWeight: 600, lineHeight: 1.55 }}>
        <LessonMarkdown unwrapParagraph>{item.question}</LessonMarkdown>
      </div>
      {revealed ? (
        <div className="lesson-section-body" style={{
          borderTop: "1px dashed var(--border, #d6ddeb)", marginTop: 10, paddingTop: 10,
          fontSize: ".9rem", lineHeight: 1.6,
        }}>
          <LessonMarkdown>{item.model_answer_md}</LessonMarkdown>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => setRevealed(true)}
          style={{
            marginTop: 10, font: "inherit", fontSize: ".8rem", fontWeight: 700,
            color: "var(--accent, #2d4a8a)", background: "none",
            border: "1px solid var(--border, #c3cfe6)", borderRadius: 7,
            padding: "5px 12px", cursor: "pointer",
          }}
        >
          Show model answer
        </button>
      )}
    </div>
  );
}

function StudyBlock({ block, blockKey, savedAnswer, onAnswer }) {
  switch (block.type) {
    case "hook":
      return null; // Study mode skips the playful opener
    case "concept":
      return (
        <div style={{ margin: "16px 0" }}>
          {block.title && (
            <h4 style={{ fontSize: "1rem", margin: "0 0 6px", display: "flex", alignItems: "center", gap: 7 }}>
              <BookOpen size={15} strokeWidth={2.3} color="var(--accent, #2d4a8a)" aria-hidden="true" />
              <LessonMarkdown unwrapParagraph>{block.title}</LessonMarkdown>
            </h4>
          )}
          <div className="lesson-section-body" style={{ fontSize: ".92rem", lineHeight: 1.65 }}>
            <LessonMarkdown>{block.body_md}</LessonMarkdown>
          </div>
        </div>
      );
    case "example":
      return <StudyExample block={block} />;
    case "quickcheck":
      return (
        <StudyQuickCheck
          block={block}
          blockKey={blockKey}
          savedAnswer={savedAnswer}
          onAnswer={onAnswer}
        />
      );
    case "watchout":
      return (
        <div style={{
          borderLeft: "3px solid #d97706", background: "rgba(245,158,11,.07)",
          borderRadius: "0 8px 8px 0", padding: "10px 14px", margin: "12px 0",
          fontSize: ".88rem", lineHeight: 1.6,
        }}>
          <div style={{
            display: "flex", alignItems: "center", gap: 6, fontWeight: 800,
            fontSize: ".7rem", letterSpacing: ".1em", textTransform: "uppercase",
            color: "#b45309", marginBottom: 4,
          }}>
            <AlertTriangle size={13} strokeWidth={2.5} aria-hidden="true" /> Watch out
          </div>
          <LessonMarkdown>{block.body_md}</LessonMarkdown>
        </div>
      );
    case "vocab":
      return (
        <div style={{ margin: "12px 0", fontSize: ".88rem" }}>
          <strong style={{ fontSize: ".8rem", textTransform: "uppercase", letterSpacing: ".08em", color: "var(--muted, #64748b)" }}>
            Key vocabulary
          </strong>
          <ul style={{ margin: "6px 0 0", paddingLeft: 18 }}>
            {block.words.map((word) => (
              <li key={word.term} style={{ marginBottom: 4 }}>
                <strong>{word.term}</strong> — {word.meaning}
              </li>
            ))}
          </ul>
        </div>
      );
    case "visual":
      return (
        <div style={{ margin: "12px 0" }}>
          <StructuredVisualBlock raw={JSON.stringify(block.visual)} />
        </div>
      );
    case "students_ask":
      return (
        <details style={{
          background: "var(--panel, #fff)", border: "1px solid var(--border, #d6ddeb)",
          borderRadius: 10, padding: "10px 14px", margin: "10px 0", fontSize: ".9rem",
        }}>
          <summary style={{ cursor: "pointer", fontWeight: 600, display: "flex", gap: 7, alignItems: "center" }}>
            <HelpCircle size={14} strokeWidth={2.4} color="var(--accent, #2d4a8a)" aria-hidden="true" />
            <LessonMarkdown unwrapParagraph>{block.question}</LessonMarkdown>
          </summary>
          <div className="lesson-section-body" style={{ marginTop: 8, lineHeight: 1.6 }}>
            <LessonMarkdown>{block.answer_md}</LessonMarkdown>
          </div>
        </details>
      );
    default:
      return null;
  }
}

function StudyRenderer({ doc, quizAnswers, onQuickCheckAnswer, activeMilestone, onNavigate }) {
  return (
    <div style={{ display: "flex", gap: 24, alignItems: "flex-start" }}>
      {/* Sticky outline */}
      <nav className="study-outline" style={{
        position: "sticky", top: 84, width: 210, flexShrink: 0,
        background: "var(--panel, #fff)", border: "1px solid var(--border, #e5e7eb)",
        borderRadius: 12, padding: "12px 0", fontSize: ".82rem",
        maxHeight: "70vh", overflowY: "auto",
      }}>
        <div style={{
          padding: "0 14px 8px", fontSize: ".66rem", fontWeight: 800,
          letterSpacing: ".11em", textTransform: "uppercase", color: "var(--muted, #6b7280)",
          display: "flex", alignItems: "center", gap: 6,
        }}>
          <GraduationCap size={13} strokeWidth={2.4} aria-hidden="true" /> On this chapter
        </div>
        {doc.milestones.map((milestone, mi) => (
          <a
            key={mi}
            href={`#study-milestone-${mi}`}
            onClick={() => onNavigate?.(mi)}
            style={{
              display: "block", padding: "7px 14px", textDecoration: "none",
              color: activeMilestone === mi ? "var(--accent, #2d4a8a)" : "var(--text, #374151)",
              fontWeight: activeMilestone === mi ? 700 : 500,
              borderLeft: activeMilestone === mi
                ? "3px solid var(--accent, #2d4a8a)"
                : "3px solid transparent",
              lineHeight: 1.35,
            }}
          >
            {milestone.title}
          </a>
        ))}
        {doc.recap && (
          <a href="#study-recap" style={{
            display: "block", padding: "7px 14px", textDecoration: "none",
            color: "var(--text, #374151)", fontWeight: 500, borderLeft: "3px solid transparent",
          }}>
            Recap
          </a>
        )}
        {doc.exam?.length > 0 && (
          <a href="#study-exam" style={{
            display: "block", padding: "7px 14px", textDecoration: "none",
            color: "var(--text, #374151)", fontWeight: 500, borderLeft: "3px solid transparent",
          }}>
            Board questions ({doc.exam.length})
          </a>
        )}
      </nav>

      {/* Document */}
      <div style={{ flex: 1, minWidth: 0 }}>
        {doc.milestones.map((milestone, mi) => (
          <section key={mi} id={`study-milestone-${mi}`} style={{ scrollMarginTop: 90, marginBottom: 28 }}>
            <h3 style={{
              fontSize: "1.12rem", margin: "0 0 4px",
              paddingBottom: 8, borderBottom: "1px solid var(--border, #e5e7eb)",
            }}>
              {milestone.title}
            </h3>
            {milestone.blocks.map((block, bi) => (
              <StudyBlock
                key={bi}
                block={block}
                blockKey={`${mi}:${bi}`}
                savedAnswer={quizAnswers?.[`${mi}:${bi}`]}
                onAnswer={onQuickCheckAnswer}
              />
            ))}
          </section>
        ))}

        {doc.recap && (
          <section id="study-recap" style={{ scrollMarginTop: 90 }}>
            <h3 style={{
              fontSize: "1.12rem", margin: "0 0 8px", display: "flex", alignItems: "center", gap: 8,
              paddingBottom: 8, borderBottom: "1px solid var(--border, #e5e7eb)",
            }}>
              <CheckCircle2 size={17} strokeWidth={2.3} color="#16a34a" aria-hidden="true" /> Recap
            </h3>
            <div className="lesson-section-body" style={{ fontSize: ".92rem", lineHeight: 1.65 }}>
              <LessonMarkdown>{doc.recap.body_md}</LessonMarkdown>
            </div>
          </section>
        )}

        {doc.exam?.length > 0 && (
          <section id="study-exam" style={{ scrollMarginTop: 90, marginTop: 28 }}>
            <h3 style={{
              fontSize: "1.12rem", margin: "0 0 10px", display: "flex", alignItems: "center", gap: 8,
              paddingBottom: 8, borderBottom: "1px solid var(--border, #e5e7eb)",
            }}>
              <Award size={17} strokeWidth={2.3} color="var(--accent, #2d4a8a)" aria-hidden="true" />
              Board questions
            </h3>
            {doc.exam.map((item, index) => (
              <ExamQAItem key={index} item={item} />
            ))}
          </section>
        )}
      </div>
    </div>
  );
}

export default StudyRenderer;
