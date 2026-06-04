const LATEX_COMMAND_PATTERN =
  /\\(?:frac|sqrt|neq|leq|geq|times|div|cdot|pi|theta|alpha|beta|gamma|delta|infty|pm|approx|equiv|propto|sum|int|left|right|text|overline|angle|parallel|perp)/;

const LATEX_FRAGMENT_PATTERN =
  /\\frac\{[^{}]+\}\{[^{}]+\}|\\sqrt\{[^{}]+\}|[A-Za-z0-9{}\s+\-*/=^_]*\\(?:neq|leq|geq|times|div|cdot|pm|approx|equiv|propto)[A-Za-z0-9{}\s+\-*/=^_]*/g;

function transformOutsideCodeFences(text, transform) {
  /** Apply markdown cleanup only to prose, leaving fenced code blocks untouched. */
  return text
    .split(/(```[\s\S]*?```)/g)
    .map((part) => (part.startsWith("```") ? part : transform(part)))
    .join("");
}

export function normalizeMermaidBlocks(text) {
  /** Wrap loose Mermaid graph text in code fences so ReactMarkdown renders diagrams correctly. */
  if (!text) return "";

  if (text.includes("graph TD") && !text.includes("```mermaid")) {
    const lines = text.split("\n");
    const output = [];
    let inMermaid = false;

    for (const line of lines) {
      const trimmed = line.trim();

      if (trimmed.startsWith("graph TD")) {
        output.push("```mermaid");
        output.push(line);
        inMermaid = true;
        continue;
      }

      if (inMermaid) {
        const isMermaidLine =
          trimmed === "" ||
          trimmed.includes("-->") ||
          trimmed.includes("-.->") ||
          /^[A-Za-z0-9_]+\[.*\]$/.test(trimmed);

        if (isMermaidLine) {
          output.push(line);
        } else {
          output.push("```");
          output.push(line);
          inMermaid = false;
        }

        continue;
      }

      output.push(line);
    }

    if (inMermaid) {
      output.push("```");
    }

    return output.join("\n");
  }

  return text;
}

function hasProseAroundLatex(expression) {
  /** Detect parentheticals that mix normal sentence text with a LaTeX formula. */
  const proseWords =
    expression
      .replace(LATEX_COMMAND_PATTERN, "")
      .match(/[A-Za-z]{2,}/g) || [];

  return proseWords.length >= 2;
}

function normalizeLatexFragments(expression) {
  /** Wrap only the formula fragments inside a prose sentence. */
  return expression.replace(LATEX_FRAGMENT_PATTERN, (fragment) => {
    const trimmed = fragment.trim();

    if (!trimmed || trimmed.startsWith("$")) {
      return fragment;
    }

    return `$${trimmed}$`;
  });
}

export function normalizeLatexParentheses(text) {
  /** Convert parenthesized LaTeX commands like (\frac{p}{q}) into inline math. */
  if (!text) return "";

  return transformOutsideCodeFences(text, (content) => {
    const withLatexCommands = content.replace(
      /\(([^()\n]*\\[^()\n]*)\)/g,
      (match, expression) => {
        if (!LATEX_COMMAND_PATTERN.test(expression)) {
          return match;
        }

        if (hasProseAroundLatex(expression)) {
          return normalizeLatexFragments(expression.trim());
        }

        return `$${expression.trim()}$`;
      }
    );

    return withLatexCommands.replace(
      /\(([a-zA-Z])\)/g,
      (match, variable, offset) => {
        const nearbyText = withLatexCommands.slice(
          Math.max(0, offset - 100),
          offset + 100
        );

        if (!/\\(?:frac|neq|leq|geq|times|sqrt)|\$[^$]+\$/.test(nearbyText)) {
          return match;
        }

        return `$${variable}$`;
      }
    );
  });
}

export function normalizeTutorMarkdown(text) {
  /** Normalize common model markdown mistakes before ReactMarkdown renders it. */
  return normalizeLatexParentheses(normalizeMermaidBlocks(text));
}
