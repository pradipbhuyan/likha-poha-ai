import { useEffect, useState } from "react";
import { AlertTriangle, Award, BookOpen, CheckCircle2, Compass, GraduationCap, HelpCircle, ImageIcon, Trophy } from "lucide-react";

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
              style={{ width: "auto", flexShrink: 0, marginTop: 3 }}
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

function ExploreMoreSection({ block }) {
  return (
    <section id="study-explore-more" style={{ scrollMarginTop: 90, marginTop: 28 }}>
      <h3 style={{
        fontSize: "1.12rem", margin: "0 0 10px", display: "flex", alignItems: "center", gap: 8,
        paddingBottom: 8, borderBottom: "1px solid var(--border, #e5e7eb)",
      }}>
        <Compass size={17} strokeWidth={2.3} color="var(--accent, #2d4a8a)" aria-hidden="true" />
        Explore more (beyond the textbook)
      </h3>

      {block.beyond_the_textbook?.length > 0 && (
        <ul style={{ margin: "0 0 16px", paddingLeft: 20, display: "flex", flexDirection: "column", gap: 8 }}>
          {block.beyond_the_textbook.map((note, i) => (
            <li key={i} style={{ fontSize: ".9rem", lineHeight: 1.6 }}>
              <LessonMarkdown unwrapParagraph>{note}</LessonMarkdown>
            </li>
          ))}
        </ul>
      )}

      {block.suggested_web_images?.length > 0 && (
        <div>
          <div style={{
            fontSize: ".72rem", fontWeight: 800, textTransform: "uppercase",
            letterSpacing: ".08em", color: "var(--muted, #64748b)", marginBottom: 8,
            display: "flex", alignItems: "center", gap: 6,
          }}>
            <ImageIcon size={13} strokeWidth={2.4} aria-hidden="true" />
            Pictures worth looking up
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {block.suggested_web_images.map((img, i) => (
              <div key={i} style={{
                background: "var(--panel, #fff)", border: "1px solid var(--border, #d6ddeb)",
                borderRadius: 10, overflow: "hidden", fontSize: ".84rem", lineHeight: 1.5,
              }}>
                {img.resolved_image_url ? (
                  <>
                    <img
                      src={img.thumb_url || img.resolved_image_url}
                      alt={img.alt_text || img.topic || "Reference image"}
                      style={{ width: "100%", display: "block", maxHeight: 240, objectFit: "cover" }}
                      loading="lazy"
                    />
                    <div style={{ padding: "8px 12px" }}>
                      {img.topic && <strong style={{ display: "block", marginBottom: 2 }}>{img.topic}</strong>}
                      <span style={{ color: "var(--muted, #64748b)", fontSize: ".76rem" }}>
                        {img.license ? `${img.license}` : "Wikimedia Commons"}
                        {img.attribution ? ` — ${img.attribution}` : ""}
                        {img.source_page_url && (
                          <>
                            {" · "}
                            <a href={img.source_page_url} target="_blank" rel="noopener noreferrer" style={{ color: "var(--accent, #2d4a8a)" }}>
                              Source
                            </a>
                          </>
                        )}
                      </span>
                    </div>
                  </>
                ) : (
                  <div style={{ padding: "8px 12px" }}>
                    {img.topic && <strong style={{ display: "block", marginBottom: 2 }}>{img.topic}</strong>}
                    {img.search_description && (
                      <span style={{ color: "var(--muted, #64748b)" }}>
                        Search: "{img.search_description}"
                        {img.suggested_source ? ` (try ${img.suggested_source})` : ""}
                      </span>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
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
    case "textbook_image":
      return (
        <figure style={{
          margin: "14px 0", border: "1px solid var(--border, #d6ddeb)",
          borderRadius: 10, overflow: "hidden", background: "var(--panel, #fff)",
        }}>
          <img
            src={block.asset_url}
            alt={block.caption || "Textbook page"}
            style={{ width: "100%", display: "block" }}
            loading="lazy"
          />
          {block.caption && (
            <figcaption style={{
              padding: "8px 12px", fontSize: ".78rem", color: "var(--muted, #64748b)",
              borderTop: "1px solid var(--border, #eef1f6)", display: "flex",
              alignItems: "center", gap: 6,
            }}>
              <BookOpen size={13} strokeWidth={2.3} aria-hidden="true" />
              {block.caption}
              {block.page_number ? ` (NCERT page ${block.page_number})` : ""}
            </figcaption>
          )}
        </figure>
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

function useIsWide() {
  const query = "(min-width: 1024px)";
  const [matches, setMatches] = useState(
    () => typeof window !== "undefined" &&
      typeof window.matchMedia === "function" &&
      window.matchMedia(query).matches
  );
  useEffect(() => {
    if (typeof window.matchMedia !== "function") return undefined;
    const mql = window.matchMedia(query);
    const onChange = (e) => setMatches(e.matches);
    setMatches(mql.matches);
    mql.addEventListener?.("change", onChange);
    return () => mql.removeEventListener?.("change", onChange);
  }, []);
  return matches;
}

function StudyRenderer({ doc, quizAnswers, onQuickCheckAnswer, activeMilestone, onNavigate }) {
  const isWide = useIsWide();

  return (
    <div style={{
      display: "flex",
      flexDirection: isWide ? "row" : "column",
      gap: isWide ? 24 : 0,
      alignItems: "flex-start",
    }}>
      {/* Sticky outline — shown as a collapsible dropdown on mobile, sticky sidebar on desktop */}
      <nav className="study-outline" style={{
        position: isWide ? "sticky" : "static",
        top: isWide ? 84 : "auto",
        width: isWide ? 210 : "100%",
        flexShrink: 0,
        background: "var(--panel, #fff)", border: "1px solid var(--border, #e5e7eb)",
        borderRadius: 12, padding: "12px 0", fontSize: ".82rem",
        maxHeight: isWide ? "70vh" : "none",
        overflowY: isWide ? "auto" : "visible",
        marginBottom: isWide ? 0 : 16,
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
            Wrap-up
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
        {doc.explore_more && (
          <a href="#study-explore-more" style={{
            display: "block", padding: "7px 14px", textDecoration: "none",
            color: "var(--text, #374151)", fontWeight: 500, borderLeft: "3px solid transparent",
          }}>
            Explore more
          </a>
        )}
      </nav>

      {/* Document */}
      <div style={{ flex: 1, minWidth: 0 }}>
        {doc.milestones.map((milestone, mi) => (
          <section key={mi} id={`study-milestone-${mi}`} style={{
            scrollMarginTop: 90,
            marginBottom: 32,
            marginTop: mi > 0 ? 40 : 0,
          }}>
            {/* Strong section divider so a reader can immediately tell they've
                moved into a new topic area — previously a thin border-bottom
                blended into the surrounding content, making cross-milestone
                scrolling (e.g. plant tissue content flowing into joints/
                musculoskeletal content) read as one unbroken stream. */}
            <div style={{
              display: "flex", alignItems: "center", gap: 10,
              marginBottom: 14,
            }}>
              <span style={{
                fontSize: ".68rem", fontWeight: 800, letterSpacing: ".08em",
                textTransform: "uppercase", color: "#fff",
                background: "var(--accent, #2d4a8a)", borderRadius: 999,
                padding: "3px 10px", whiteSpace: "nowrap", flexShrink: 0,
              }}>
                Section {mi + 1} of {doc.milestones.length}
              </span>
              <div style={{ flex: 1, height: 2, background: "var(--border, #e5e7eb)" }} />
            </div>
            <h3 style={{
              fontSize: "1.28rem", fontWeight: 800, margin: "0 0 16px",
              paddingBottom: 12, borderBottom: "3px solid var(--accent, #2d4a8a)",
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
              <CheckCircle2 size={17} strokeWidth={2.3} color="#16a34a" aria-hidden="true" /> Wrap-up
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

        {doc.explore_more && <ExploreMoreSection block={doc.explore_more} />}

        {/* Finish card — id observed by ChapterJourneyView to save real
            completion once this card scrolls into view (no click required). */}
        <div id="study-finish-card" style={{
          background: "linear-gradient(150deg, #0e9488, #16a34a)",
          borderRadius: 16, padding: "22px 20px", textAlign: "center",
          color: "#fff", marginTop: 28,
        }}>
          <Trophy size={30} strokeWidth={2.2} aria-hidden="true" />
          <div style={{ fontWeight: 800, fontSize: "1.05rem", marginTop: 6 }}>
            Chapter complete — great work!
          </div>
          <div style={{ fontSize: ".85rem", opacity: .9, marginTop: 4 }}>
            Try a mock test or pick your next chapter to keep the streak going.
          </div>
        </div>
      </div>
    </div>
  );
}

export default StudyRenderer;
