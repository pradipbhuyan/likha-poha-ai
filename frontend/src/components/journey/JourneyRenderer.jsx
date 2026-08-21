import { useState } from "react";
import {
  AlertTriangle,
  BookOpen,
  CheckCircle2,
  Compass,
  FlaskConical,
  HelpCircle,
  ImageIcon,
  Lightbulb,
  ListChecks,
  Sparkles,
  Star,
  Trophy,
} from "lucide-react";

import LessonMarkdown from "./LessonMarkdown";
import { CHAPTER_GLANCE_ANCHOR, CHAPTER_GLANCE_LABEL, findChapterGlance, scrollToChapterGlance } from "./chapterGlance";
import StructuredVisualBlock from "../StructuredVisualBlock";

/**
 * JourneyRenderer — Grades 5-8.
 * Colourful card feed: one idea per card, tap-to-answer quick checks,
 * tap-to-reveal "Students also ask", XP + milestone path at the top.
 * All interactions are local — zero API calls while scrolling.
 */

const CARD_COLOURS = {
  hook:         { bg: "rgba(14,148,136,.10)", border: "rgba(14,148,136,.45)", accent: "#0e9488", label: "Did you know?" },
  concept:      { bg: "rgba(59,130,246,.08)",  border: "rgba(59,130,246,.35)",  accent: "#3b82f6", label: "Concept" },
  example:      { bg: "rgba(34,197,94,.08)",   border: "rgba(34,197,94,.35)",   accent: "#16a34a", label: "Worked example" },
  quickcheck:   { bg: "rgba(232,96,76,.08)",   border: "rgba(232,96,76,.4)",    accent: "#e8604c", label: "Quick check" },
  watchout:     { bg: "rgba(242,169,34,.10)",  border: "rgba(242,169,34,.45)",  accent: "#d97706", label: "Watch out" },
  vocab:        { bg: "rgba(124,92,214,.08)",  border: "rgba(124,92,214,.35)",  accent: "#7c5cd6", label: "New words" },
  students_ask: { bg: "rgba(124,92,214,.08)",  border: "rgba(124,92,214,.35)",  accent: "#7c5cd6", label: "Students also ask" },
  recap:        { bg: "rgba(14,148,136,.10)",  border: "rgba(14,148,136,.45)",  accent: "#0e9488", label: "Wrap-up" },
};

const CARD_ICONS = {
  hook: Lightbulb,
  concept: BookOpen,
  example: FlaskConical,
  quickcheck: ListChecks,
  watchout: AlertTriangle,
  vocab: Sparkles,
  students_ask: HelpCircle,
  recap: Star,
};

function CardShell({ type, title, children, anchorId }) {
  const colours = CARD_COLOURS[type] || CARD_COLOURS.concept;
  const Icon = CARD_ICONS[type] || BookOpen;
  return (
    <div
      id={anchorId}
      className={`journey-card journey-card-${type}`}
      style={{
        // scrollMarginTop keeps the sticky topbar off the card when the
        // "Chapter at a glance" rail link scrolls to it.
        scrollMarginTop: anchorId ? 90 : undefined,
        background: colours.bg,
        border: `1.5px solid ${colours.border}`,
        borderRadius: 16,
        padding: "16px 18px",
        marginBottom: 14,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
        <span style={{
          width: 28, height: 28, borderRadius: 8, flexShrink: 0,
          background: colours.border,
          display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          <Icon size={15} strokeWidth={2.4} color="#fff" aria-hidden="true" />
        </span>
        <span style={{
          fontSize: ".68rem", fontWeight: 800, textTransform: "uppercase",
          letterSpacing: ".09em", color: colours.accent,
        }}>
          {colours.label}
        </span>
        {title && (
          <span style={{ fontSize: ".98rem", fontWeight: 700, lineHeight: 1.3 }}>
            <LessonMarkdown unwrapParagraph>{title}</LessonMarkdown>
          </span>
        )}
      </div>
      {children}
    </div>
  );
}

function QuickCheckCard({ block, blockKey, savedAnswer, onAnswer }) {
  const [picked, setPicked] = useState(savedAnswer ?? null);
  const answered = picked !== null && picked !== undefined;

  function handlePick(index) {
    if (answered) return;
    setPicked(index);
    onAnswer?.(blockKey, index, index === block.answer_index);
  }

  return (
    <CardShell type="quickcheck">
      <div style={{ fontSize: ".95rem", fontWeight: 700, marginBottom: 10, lineHeight: 1.45 }}>
        <LessonMarkdown unwrapParagraph>{block.question}</LessonMarkdown>
      </div>
      {block.options.map((option, index) => {
        const isPicked = picked === index;
        const isRight = index === block.answer_index;
        let background = "var(--panel, #fff)";
        let border = "2px solid var(--border, #e5e7eb)";
        if (answered && isRight) { background = "rgba(34,197,94,.15)"; border = "2px solid #16a34a"; }
        else if (answered && isPicked && !isRight) { background = "rgba(232,96,76,.14)"; border = "2px solid #e8604c"; }
        return (
          <button
            key={index}
            type="button"
            onClick={() => handlePick(index)}
            disabled={answered}
            style={{
              display: "block", width: "100%", textAlign: "left",
              font: "inherit", fontSize: ".9rem", fontWeight: 600,
              color: "var(--text, #111827)",
              background, border, borderRadius: 12,
              padding: "10px 13px", marginTop: 8,
              cursor: answered ? "default" : "pointer",
            }}
          >
            <LessonMarkdown unwrapParagraph>{option}</LessonMarkdown>
          </button>
        );
      })}
      {answered && (
        <div style={{
          marginTop: 10, fontSize: ".86rem", fontWeight: 600, lineHeight: 1.5,
          color: picked === block.answer_index ? "#15803d" : "#b45309",
          display: "flex", gap: 6, alignItems: "flex-start",
        }}>
          {picked === block.answer_index
            ? <CheckCircle2 size={16} strokeWidth={2.4} style={{ flexShrink: 0, marginTop: 2 }} aria-hidden="true" />
            : <AlertTriangle size={16} strokeWidth={2.4} style={{ flexShrink: 0, marginTop: 2 }} aria-hidden="true" />}
          <span>
            {picked === block.answer_index ? "Correct!" : "Not quite — the highlighted answer is correct."}
            {block.explanation && (
              <span style={{ display: "block", fontWeight: 500, color: "var(--muted, #6b7280)", marginTop: 3 }}>
                <LessonMarkdown unwrapParagraph>{block.explanation}</LessonMarkdown>
              </span>
            )}
          </span>
        </div>
      )}
    </CardShell>
  );
}

function StudentsAskCard({ block }) {
  const [open, setOpen] = useState(false);
  return (
    <CardShell type="students_ask">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        style={{
          display: "flex", width: "100%", justifyContent: "space-between",
          alignItems: "center", gap: 8, font: "inherit", fontSize: ".92rem",
          fontWeight: 700, color: "var(--text, #111827)",
          background: "none", border: "none", padding: 0, cursor: "pointer",
          textAlign: "left",
        }}
      >
        <LessonMarkdown unwrapParagraph>{block.question}</LessonMarkdown>
        <span style={{ fontSize: ".72rem", fontWeight: 800, color: "#7c5cd6", flexShrink: 0 }}>
          {open ? "HIDE" : "REVEAL"}
        </span>
      </button>
      {open && (
        <div className="lesson-section-body" style={{ marginTop: 10, fontSize: ".9rem", lineHeight: 1.6 }}>
          <LessonMarkdown>{block.answer_md}</LessonMarkdown>
        </div>
      )}
    </CardShell>
  );
}

function JourneyBlock({ block, blockKey, savedAnswer, onAnswer, anchorId }) {
  switch (block.type) {
    case "hook":
      return (
        <CardShell type="hook">
          <div style={{ fontSize: "1.05rem", fontWeight: 700, lineHeight: 1.5 }}>
            <LessonMarkdown unwrapParagraph>{block.text}</LessonMarkdown>
          </div>
        </CardShell>
      );
    case "concept":
      return (
        <CardShell type="concept" title={block.title} anchorId={anchorId}>
          <div className="lesson-section-body" style={{ fontSize: ".95rem", lineHeight: 1.65 }}>
            <LessonMarkdown>{block.body_md}</LessonMarkdown>
          </div>
          {block.key_terms?.length > 0 && (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 10 }}>
              {block.key_terms.map((kt) => (
                <span key={kt.term} title={kt.meaning} style={{
                  fontSize: ".76rem", fontWeight: 700, color: "#3b82f6",
                  background: "rgba(59,130,246,.12)", borderRadius: 99, padding: "3px 10px",
                }}>
                  {kt.term}
                </span>
              ))}
            </div>
          )}
        </CardShell>
      );
    case "example":
      return (
        <CardShell type="example">
          <div style={{ fontSize: ".93rem", fontWeight: 700, marginBottom: 8, lineHeight: 1.5 }}>
            <LessonMarkdown unwrapParagraph>{`Question: ${block.question}`}</LessonMarkdown>
          </div>
          <div className="lesson-section-body" style={{ fontSize: ".92rem", lineHeight: 1.6 }}>
            <LessonMarkdown>{block.body_md}</LessonMarkdown>
          </div>
        </CardShell>
      );
    case "quickcheck":
      return (
        <QuickCheckCard
          block={block}
          blockKey={blockKey}
          savedAnswer={savedAnswer}
          onAnswer={onAnswer}
        />
      );
    case "freetext_qa":
      // Open-ended Question/Answer/Explanation triple that doesn't fit the
      // lettered-options QuickCheckCard (e.g. a storybook riddle or an
      // interpretive "what happens next" question). Rendered as three
      // clearly separated lines/blocks instead of one run-on paragraph —
      // fixes the reported "Question: ... Answer: ... Explanation: ..."
      // glued-together text (2026-07-29).
      return (
        <CardShell type="concept" title="Quick check question">
          <div style={{ fontSize: ".95rem", fontWeight: 700, lineHeight: 1.5, marginBottom: 10 }}>
            <LessonMarkdown unwrapParagraph>{`Question: ${block.question}`}</LessonMarkdown>
          </div>
          <div style={{
            background: "rgba(34,197,94,.08)", border: "1px solid rgba(34,197,94,.25)",
            borderRadius: 10, padding: "10px 13px", marginBottom: block.explanation ? 8 : 0,
          }}>
            <div style={{ fontSize: ".78rem", fontWeight: 800, letterSpacing: ".03em", color: "#15803d", marginBottom: 4 }}>
              ANSWER
            </div>
            <div style={{ fontSize: ".92rem", fontWeight: 600, lineHeight: 1.5, color: "var(--text, #111827)" }}>
              <LessonMarkdown unwrapParagraph>{block.answer}</LessonMarkdown>
            </div>
          </div>
          {block.explanation && (
            <div style={{
              background: "var(--panel-soft, #f8fafc)", border: "1px solid var(--border, #e5e7eb)",
              borderRadius: 10, padding: "10px 13px",
            }}>
              <div style={{ fontSize: ".78rem", fontWeight: 800, letterSpacing: ".03em", color: "var(--muted, #6b7280)", marginBottom: 4 }}>
                EXPLANATION
              </div>
              <div style={{ fontSize: ".88rem", lineHeight: 1.55, color: "var(--text, #111827)" }}>
                <LessonMarkdown unwrapParagraph>{block.explanation}</LessonMarkdown>
              </div>
            </div>
          )}
        </CardShell>
      );
    case "watchout":
      return (
        <CardShell type="watchout">
          <div className="lesson-section-body" style={{ fontSize: ".92rem", lineHeight: 1.6 }}>
            <LessonMarkdown>{block.body_md}</LessonMarkdown>
          </div>
        </CardShell>
      );
    case "vocab":
      return (
        <CardShell type="vocab">
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {block.words.map((word) => (
              <div key={word.term} style={{ fontSize: ".9rem", lineHeight: 1.5 }}>
                <strong style={{ color: "#7c5cd6" }}>{word.term}</strong>
                <span style={{ color: "var(--muted, #6b7280)" }}> — {word.meaning}</span>
              </div>
            ))}
          </div>
        </CardShell>
      );
    case "students_ask":
      return <StudentsAskCard block={block} />;
    case "visual":
      return (
        <div style={{ marginBottom: 14 }}>
          <StructuredVisualBlock raw={JSON.stringify(block.visual)} />
        </div>
      );
    case "textbook_image":
      return (
        <figure style={{
          marginBottom: 14, border: "1.5px solid var(--border, #e5e7eb)",
          borderRadius: 16, overflow: "hidden", background: "var(--panel, #fff)",
        }}>
          <img
            src={block.asset_url}
            alt={block.caption || "Textbook page"}
            style={{ width: "100%", display: "block" }}
            loading="lazy"
          />
          {block.caption && (
            <figcaption style={{
              padding: "10px 14px", fontSize: ".8rem", color: "var(--muted, #6b7280)",
              display: "flex", alignItems: "center", gap: 6,
            }}>
              <BookOpen size={13} strokeWidth={2.3} aria-hidden="true" />
              {block.caption}
              {block.page_number ? ` (NCERT page ${block.page_number})` : ""}
            </figcaption>
          )}
        </figure>
      );
    default:
      return null;
  }
}

function ExploreMoreCard({ block }) {
  return (
    <div style={{
      background: "rgba(59,130,246,.06)", border: "1.5px solid rgba(59,130,246,.3)",
      borderRadius: 16, padding: "16px 18px", marginTop: 6,
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
        <span style={{
          width: 28, height: 28, borderRadius: 8, flexShrink: 0,
          background: "rgba(59,130,246,.35)",
          display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          <Compass size={15} strokeWidth={2.4} color="#fff" aria-hidden="true" />
        </span>
        <span style={{
          fontSize: ".68rem", fontWeight: 800, textTransform: "uppercase",
          letterSpacing: ".09em", color: "#3b82f6",
        }}>
          Explore more (beyond the textbook)
        </span>
      </div>

      {block.beyond_the_textbook?.length > 0 && (
        <ul style={{ margin: "0 0 14px", paddingLeft: 20, display: "flex", flexDirection: "column", gap: 8 }}>
          {block.beyond_the_textbook.map((note, i) => (
            <li key={i} style={{ fontSize: ".9rem", lineHeight: 1.55 }}>
              <LessonMarkdown unwrapParagraph>{note}</LessonMarkdown>
            </li>
          ))}
        </ul>
      )}

      {block.suggested_web_images?.length > 0 && (
        <div>
          <div style={{
            fontSize: ".72rem", fontWeight: 800, textTransform: "uppercase",
            letterSpacing: ".08em", color: "var(--muted, #6b7280)", marginBottom: 8,
            display: "flex", alignItems: "center", gap: 6,
          }}>
            <ImageIcon size={13} strokeWidth={2.4} aria-hidden="true" />
            Pictures worth looking up
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {block.suggested_web_images.map((img, i) => (
              <div key={i} style={{
                background: "var(--panel, #fff)", border: "1px solid var(--border, #e5e7eb)",
                borderRadius: 10, overflow: "hidden", fontSize: ".84rem", lineHeight: 1.5,
              }}>
                {img.resolved_image_url ? (
                  <>
                    <img
                      src={img.thumb_url || img.resolved_image_url}
                      alt={img.alt_text || img.topic || "Reference image"}
                      style={{ width: "100%", display: "block", maxHeight: 220, objectFit: "cover" }}
                      loading="lazy"
                    />
                    <div style={{ padding: "8px 12px" }}>
                      {img.topic && <strong style={{ display: "block", marginBottom: 2 }}>{img.topic}</strong>}
                      <span style={{ color: "var(--muted, #6b7280)", fontSize: ".76rem" }}>
                        {img.license ? `${img.license}` : "Wikimedia Commons"}
                        {img.attribution ? ` — ${img.attribution}` : ""}
                        {img.source_page_url && (
                          <>
                            {" · "}
                            <a href={img.source_page_url} target="_blank" rel="noopener noreferrer" style={{ color: "#3b82f6" }}>
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
                      <span style={{ color: "var(--muted, #6b7280)" }}>
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
    </div>
  );
}

function MilestoneRail({ doc, activeMilestone, activeBeyond }) {
  const chapterGlance = findChapterGlance(doc);
  /** Sticky left rail on wide screens: chapter path, always visible. */
  return (
    <nav className="journey-rail" style={{
      position: "sticky", top: 84, width: 224, flexShrink: 0,
      background: "var(--panel, #fff)", border: "1.5px solid var(--border, #e5e7eb)",
      borderRadius: 16, padding: "14px 0 8px",
      maxHeight: "78vh", overflowY: "auto",
    }}>
      <div style={{ padding: "0 14px 12px" }}>
        <span style={{
          fontSize: ".66rem", fontWeight: 800, letterSpacing: ".11em",
          textTransform: "uppercase", color: "var(--muted, #6b7280)",
        }}>
          Chapter path
        </span>
      </div>
      {doc.milestones.map((milestone, mi) => {
        const isDone = mi < activeMilestone;
        const isCurrent = mi === activeMilestone;
        return (
          <a
            key={mi}
            href={`#journey-milestone-${mi}`}
            style={{
              display: "flex", alignItems: "center", gap: 10,
              padding: "8px 14px", textDecoration: "none", lineHeight: 1.3,
              fontSize: ".84rem",
              fontWeight: isCurrent ? 800 : 600,
              color: isCurrent ? "#0e9488" : isDone ? "var(--text, #374151)" : "var(--muted, #9ca3af)",
              borderLeft: isCurrent ? "3px solid #e8604c" : "3px solid transparent",
              background: isCurrent ? "rgba(14,148,136,.07)" : "none",
            }}
          >
            <span style={{
              width: 24, height: 24, borderRadius: "50%", flexShrink: 0,
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: ".72rem", fontWeight: 800,
              background: isDone || isCurrent ? "#0e9488" : "var(--border, #e5e7eb)",
              color: isDone || isCurrent ? "#fff" : "var(--muted, #9ca3af)",
            }}>
              {isDone
                ? <CheckCircle2 size={13} strokeWidth={3} aria-hidden="true" />
                : mi + 1}
            </span>
            <span>{milestone.title}</span>
          </a>
        );
      })}
      {chapterGlance && (
        // Sits directly under the last milestone, matching where the poster
        // actually appears in the feed. Highlighted the same way milestone
        // links are (teal text + red left bar + filled dot) when the poster
        // is the section currently in view — driven by activeBeyond from
        // ChapterJourneyView's scroll-spy, since this section has no
        // "journey-milestone-N" id for the milestone observer to pick up.
        <a
          href={`#${CHAPTER_GLANCE_ANCHOR}`}
          onClick={scrollToChapterGlance}
          style={{
            display: "flex", alignItems: "center", gap: 10, padding: "8px 14px",
            textDecoration: "none", fontSize: ".84rem",
            fontWeight: activeBeyond === "glance" ? 800 : 600,
            color: activeBeyond === "glance" ? "#0e9488" : "var(--muted, #9ca3af)",
            borderLeft: activeBeyond === "glance" ? "3px solid #e8604c" : "3px solid transparent",
            background: activeBeyond === "glance" ? "rgba(14,148,136,.07)" : "none",
          }}
        >
          <span style={{
            width: 24, height: 24, borderRadius: "50%", flexShrink: 0,
            display: "flex", alignItems: "center", justifyContent: "center",
            background: activeBeyond === "glance" ? "#0e9488" : "var(--border, #e5e7eb)",
            color: activeBeyond === "glance" ? "#fff" : "var(--muted, #9ca3af)",
          }}>
            <ImageIcon size={13} strokeWidth={2.6} aria-hidden="true" />
          </span>
          <span>{CHAPTER_GLANCE_LABEL}</span>
        </a>
      )}
      {doc.recap && (
        <a href="#journey-recap" style={{
          display: "flex", alignItems: "center", gap: 10, padding: "8px 14px",
          textDecoration: "none", fontSize: ".84rem",
          fontWeight: activeBeyond === "recap" ? 800 : 600,
          color: activeBeyond === "recap" ? "#0e9488" : "var(--muted, #9ca3af)",
          borderLeft: activeBeyond === "recap" ? "3px solid #e8604c" : "3px solid transparent",
          background: activeBeyond === "recap" ? "rgba(14,148,136,.07)" : "none",
        }}>
          <span style={{
            width: 24, height: 24, borderRadius: "50%", flexShrink: 0,
            display: "flex", alignItems: "center", justifyContent: "center",
            background: activeBeyond === "recap" ? "#0e9488" : "var(--border, #e5e7eb)",
            color: activeBeyond === "recap" ? "#fff" : "var(--muted, #9ca3af)",
          }}>
            <Star size={13} strokeWidth={2.6} aria-hidden="true" />
          </span>
          <span>Wrap-up</span>
        </a>
      )}
    </nav>
  );
}

function JourneyRenderer({ doc, onQuickCheckAnswer, quizAnswers, activeMilestone = 0, activeBeyond = null, isWide = false }) {
  const chapterGlance = findChapterGlance(doc);
  return (
    <div style={isWide ? { display: "flex", gap: 26, alignItems: "flex-start" } : undefined}>
      {isWide && <MilestoneRail doc={doc} activeMilestone={activeMilestone} activeBeyond={activeBeyond} />}

      <div
        className="journey-feed"
        style={isWide
          ? { flex: 1, minWidth: 0, maxWidth: 860 }
          : { maxWidth: 640, margin: "0 auto" }}
      >
      {doc.milestones.map((milestone, mi) => (
        <section key={mi} id={`journey-milestone-${mi}`} style={{ scrollMarginTop: 90 }}>
          <div style={{
            display: "flex", alignItems: "center", gap: 10,
            margin: mi === 0 ? "4px 0 12px" : "26px 0 12px",
          }}>
            <span style={{
              width: 30, height: 30, borderRadius: "50%", flexShrink: 0,
              background: "#0e9488", color: "#fff", fontWeight: 800, fontSize: ".82rem",
              display: "flex", alignItems: "center", justifyContent: "center",
            }}>
              {mi + 1}
            </span>
            <h3 style={{ margin: 0, fontSize: "1.05rem" }}>{milestone.title}</h3>
          </div>
          {milestone.blocks.map((block, bi) => (
            <JourneyBlock
              key={bi}
              block={block}
              blockKey={`${mi}:${bi}`}
              savedAnswer={quizAnswers?.[`${mi}:${bi}`]}
              onAnswer={onQuickCheckAnswer}
              anchorId={
                chapterGlance && chapterGlance.mi === mi && chapterGlance.bi === bi
                  ? CHAPTER_GLANCE_ANCHOR
                  : undefined
              }
            />
          ))}
        </section>
      ))}

      {doc.recap && (
        <div id="journey-recap" style={{ scrollMarginTop: 90 }}>
          <CardShell type="recap">
            <div className="lesson-section-body" style={{ fontSize: ".93rem", lineHeight: 1.6 }}>
              <LessonMarkdown>{doc.recap.body_md}</LessonMarkdown>
            </div>
          </CardShell>
        </div>
      )}

      {doc.explore_more && (
        <div id="journey-explore-more" style={{ scrollMarginTop: 90 }}>
          <ExploreMoreCard block={doc.explore_more} />
        </div>
      )}

      {/* Finish card, id observed by ChapterJourneyView to save real completion
          once this card scrolls into view (no click required). */}
      <div id="journey-finish-card" style={{
        background: "linear-gradient(150deg, #0e9488, #16a34a)",
        borderRadius: 16, padding: "22px 20px", textAlign: "center",
        color: "#fff", marginTop: 6,
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

export default JourneyRenderer;
