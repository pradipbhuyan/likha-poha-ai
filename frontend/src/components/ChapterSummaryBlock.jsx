import ReactMarkdown from "react-markdown";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";

import { normalizePlainExponents, normalizePlainAlgebra } from "../utils/markdownCleanup";
import { validateChapterSummary } from "../../../shared/utils/chapterSummary.js";

export { validateChapterSummary };

/** Whole-chapter revision infographic, rendered from structured JSON.
 *
 *  Authored as a ```chapter-summary fenced block at the end of a chapter's
 *  final lesson step, so a student finishing the chapter gets the same
 *  one-glance recap a printed wall-chart would give — but as real DOM text
 *  rather than a flat image, so it reflows on phones, honours dark mode,
 *  stays selectable/searchable/translatable, and can be corrected by
 *  editing one JSON field instead of regenerating a picture.
 *
 *  Deliberately mirrors StructuredVisualBlock's contract: parse, validate
 *  hard, and render NOTHING when the payload is malformed or unsafe. A
 *  half-rendered summary at the end of a chapter is worse than none.
 */

/** Render short summary text that may carry inline math.
 *
 *  Same rationale as StructuredVisualBlock's VisualItemText: content inside a
 *  code fence never passes through normalizeTutorMarkdown, so plain-text
 *  notation like "42 degrees C" or "v^2" needs the two cheap normalizations
 *  applied here to render correctly.
 */
function SummaryText({ children }) {
  if (!children) return <>{children}</>;

  const normalized = normalizePlainAlgebra(normalizePlainExponents(children));

  if (!normalized.includes("$") && !normalized.includes("\\")) {
    return <>{normalized}</>;
  }
  return (
    <ReactMarkdown
      remarkPlugins={[remarkMath]}
      rehypePlugins={[rehypeKatex]}
      components={{ p: ({ children: c }) => <>{c}</> }}
    >
      {normalized}
    </ReactMarkdown>
  );
}

function ChapterSummaryBlock({ raw }) {
  const summary = validateChapterSummary(raw);

  if (!summary) {
    return null;
  }

  return (
    <section className="chapter-summary-card" aria-label={`Chapter summary: ${summary.title}`}>
      <header className="chapter-summary-header">
        <span className="chapter-summary-eyebrow">Chapter summary</span>
        <h3 className="chapter-summary-title">{summary.title}</h3>
        {summary.subtitle && <p className="chapter-summary-subtitle">{summary.subtitle}</p>}
      </header>

      {summary.definition && (
        <p className="chapter-summary-definition">
          <SummaryText>{summary.definition}</SummaryText>
        </p>
      )}

      {summary.panels.length > 0 && (
        <div className="chapter-summary-panels">
          {summary.panels.map((panel, index) => (
            <article className="chapter-summary-panel" key={`${panel.heading}-${index}`}>
              <h4>
                <span className="chapter-summary-panel-index" aria-hidden="true">{index + 1}</span>
                {panel.heading}
              </h4>
              <ul>
                {panel.points.map((point, pi) => (
                  <li key={pi}><SummaryText>{point}</SummaryText></li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      )}

      {summary.pipeline && (
        <div className="chapter-summary-pipeline">
          <h4 className="chapter-summary-section-heading">{summary.pipeline.heading}</h4>
          {/* Horizontal strip on wide screens, stacked list on phones — the CSS
              switches grid-auto-flow, so no JS breakpoint logic is needed. */}
          <ol className="chapter-summary-pipeline-track">
            {summary.pipeline.steps.map((step, index) => (
              <li className="chapter-summary-pipeline-step" key={`${step.label}-${index}`}>
                <span className="chapter-summary-pipeline-index" aria-hidden="true">{index + 1}</span>
                <span className="chapter-summary-pipeline-label">{step.label}</span>
                {step.detail && (
                  <span className="chapter-summary-pipeline-detail">
                    <SummaryText>{step.detail}</SummaryText>
                  </span>
                )}
              </li>
            ))}
          </ol>
        </div>
      )}

      {(summary.terms.length > 0 || summary.remember.length > 0) && (
        <div className="chapter-summary-footer">
          {summary.remember.length > 0 && (
            <div className="chapter-summary-remember">
              <h4 className="chapter-summary-section-heading">Points to remember</h4>
              <ul>
                {summary.remember.map((point, index) => (
                  <li key={index}><SummaryText>{point}</SummaryText></li>
                ))}
              </ul>
            </div>
          )}

          {summary.terms.length > 0 && (
            <div className="chapter-summary-terms">
              <h4 className="chapter-summary-section-heading">Key terms</h4>
              <dl>
                {summary.terms.map((entry, index) => (
                  <div className="chapter-summary-term-row" key={`${entry.term}-${index}`}>
                    <dt>{entry.term}</dt>
                    <dd><SummaryText>{entry.meaning}</SummaryText></dd>
                  </div>
                ))}
              </dl>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

export default ChapterSummaryBlock;
