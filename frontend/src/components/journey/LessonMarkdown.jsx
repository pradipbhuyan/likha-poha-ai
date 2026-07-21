import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";

import StructuredVisualBlock from "../StructuredVisualBlock";
import { normalizeTutorMarkdown } from "../../utils/markdownCleanup";

/** Shared markdown renderer for Chapter Journey blocks.
 *  Handles visual-json fences (structured visuals), strips mermaid,
 *  and keeps tables scrollable on mobile. */

function JourneyCode({ className, children }) {
  const language = className || "";
  const raw = String(children).replace(/\n$/, "");
  if (/language-visual-json/.test(language)) return <StructuredVisualBlock raw={raw} />;
  if (/language-mermaid/.test(language)) return null;
  return <code className={className}>{children}</code>;
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
  const components = { code: JourneyCode, table: JourneyTable };
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
