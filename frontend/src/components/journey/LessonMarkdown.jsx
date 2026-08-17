import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";

import StructuredVisualBlock from "../StructuredVisualBlock";
import ExtractPopupBlock from "../ExtractPopupBlock";
import ChapterSummaryBlock from "../ChapterSummaryBlock";
import ChapterInfographicBlock from "../ChapterInfographicBlock";
import { normalizeTutorMarkdown } from "../../utils/markdownCleanup";

/** Shared markdown renderer for Chapter Journey blocks.
 *  Handles visual-json fences (structured visuals), extract-ref fences
 *  (clickable citation pill -> popup showing the actual source text a
 *  bare citation like "NCERT Critical Reflection I.2(iv)" refers to),
 *  strips mermaid, and keeps tables scrollable on mobile. */

// Custom fenced-code languages that render as interactive components
// (a clickable pill / a structured visual card) rather than literal code
// text. ReactMarkdown wraps EVERY fenced code block in a <pre> by default —
// fine for real code, but a <pre> imposes monospace font, white-space:pre
// and (via several .lesson-section-body pre/code CSS rules across the app)
// layout quirks that can visually shrink or hide a nested interactive
// element (seen: an extract-ref citation pill rendering with zero visible
// size when several such fences are interleaved with bullet-list items,
// e.g. Grade 10 Science Activity 1.4-1.8 citations). Detecting the
// language on the <pre> itself (via its single child's className) lets us
// skip the <pre> wrapper entirely for these block types and render the
// interactive component as a normal sibling <div>/<button> instead.
const _CUSTOM_BLOCK_LANGUAGE_RE = /language-(?:visual-json|extract-ref|chapter-summary|chapter-infographic|mermaid)/;

function JourneyCode({ className, children }) {
  const language = className || "";
  const raw = String(children).replace(/\n$/, "");
  if (/language-visual-json/.test(language)) return <StructuredVisualBlock raw={raw} />;
  if (/language-extract-ref/.test(language)) return <ExtractPopupBlock raw={raw} />;
  if (/language-chapter-summary/.test(language)) return <ChapterSummaryBlock raw={raw} />;
  if (/language-chapter-infographic/.test(language)) return <ChapterInfographicBlock raw={raw} />;
  if (/language-mermaid/.test(language)) return null;
  return <code className={className}>{children}</code>;
}

function JourneyPre({ node, children }) {
  // IMPORTANT: cannot detect the fence language by inspecting `children`'s
  // rendered props — by the time <pre>'s children reach this component,
  // the nested <code> element has ALREADY been converted by JourneyCode
  // into e.g. <ExtractPopupBlock raw={...} />, which has no `className`
  // prop at all (JourneyCode never forwards it). Checking children props
  // here is therefore always a no-op miss. `node` is react-markdown's
  // original hast AST node for this <pre> BEFORE any component mapping
  // was applied, so node.children[0].properties.className still holds
  // the real "language-x" class — that's what must be checked instead.
  const codeNode = node?.children?.find((c) => c.tagName === "code");
  const codeClassName = (codeNode?.properties?.className || []).join(" ");
  if (_CUSTOM_BLOCK_LANGUAGE_RE.test(codeClassName)) {
    // Render the custom component directly, no <pre> wrapper.
    return <>{children}</>;
  }
  return <pre>{children}</pre>;
}

function JourneyTable({ children }) {
  return (
    <div style={{ overflowX: "auto", WebkitOverflowScrolling: "touch", marginBottom: "1em", maxWidth: "100%" }}>
      <table style={{ borderCollapse: "collapse", minWidth: "100%", fontSize: "0.92rem" }}>
        {children}
      </table>
    </div>
  );
}

function LessonMarkdown({ children, unwrapParagraph = false }) {
  const components = { code: JourneyCode, pre: JourneyPre, table: JourneyTable };
  if (unwrapParagraph) {
    components.p = ({ children: inner }) => <>{inner}</>;
  }
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm, remarkMath]}
      rehypePlugins={[rehypeKatex]}
      components={components}
    >
      {normalizeTutorMarkdown(String(children || ""))}
    </ReactMarkdown>
  );
}

export default LessonMarkdown;
