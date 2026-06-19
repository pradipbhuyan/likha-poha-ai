const LATEX_COMMAND_PATTERN =
  /\\(?:frac|sqrt|neq|leq|geq|times|div|cdot|pi|theta|alpha|beta|gamma|delta|infty|pm|approx|equiv|propto|sum|int|left|right|text|overline|angle|parallel|perp)/;

const LATEX_FRAGMENT_PATTERN =
  /\\frac\{[^{}]+\}\{[^{}]+\}|\\sqrt\{[^{}]+\}|[A-Za-z0-9{}\s+\-*/=^_]*\\(?:neq|leq|geq|times|div|cdot|pm|approx|equiv|propto)[A-Za-z0-9{}\s+\-*/=^_]*/g;

const PLAIN_ALGEBRA_DOUBLE_PAREN_PATTERN =
  /\(\(([a-zA-Z][a-zA-Z0-9]*(?:[+\-]\d+)?)\)\^(\d+)\)/g;

const PLAIN_ALGEBRA_GROUPED_POWER_PATTERN =
  /\(\(([^()\n]{1,60})\)\^(\d+)([^()\n]{0,120})\)/g;

function transformOutsideCodeFences(text, transform) {
  /** Apply markdown cleanup only to prose, leaving fenced code blocks untouched. */
  return text
    .split(/(```[\s\S]*?```)/g)
    .map((part) => (part.startsWith("```") ? part : transform(part)))
    .join("");
}

function transformOutsideInlineMath(text, transform) {
  /** Apply cleanup only outside already-normalized inline math spans. */
  return text
    .split(/(\$[^$\n]*\$)/g)
    .map((part) => (part.startsWith("$") && part.endsWith("$") ? part : transform(part)))
    .join("");
}

export function removeUnsupportedQuestionClosers(text) {
  /**
   * Convert conversational invitation questions into actionable next steps.
   *
   * The lesson UI only evaluates explicit practice questions. Ending a summary
   * with "Would you like..." makes students answer a prompt the app will not
   * actually handle, so we rewrite those invitations into instructions.
   */
  if (!text) return "";

  const nextStep =
    "Review these key points, then move to the next lesson section when ready.";

  return transformOutsideCodeFences(text, (content) =>
    content
      .replace(
        /\bIf you want,[^.!?\n]*\?\s*/gi,
        nextStep
      )
      .replace(
        /\bWould you like(?:\s+to|\s+me to|\s+that)?[^.!?\n]*\?\s*/gi,
        nextStep
      )
      .replace(
        /\b(?:Do you want|Shall we|Should we|Can we now)[^.!?\n]*\?\s*/gi,
        nextStep
      )
  );
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

export function normalizeDollarMath(text) {
  /**
   * Make numeric inline equations parseable by remark-math.
   *
   * remark-math intentionally ignores `$10...$` because it looks like currency.
   * Tutor output sometimes uses that shape for equations, so add a tiny space
   * after the opening dollar only when the content is clearly mathematical.
   */
  if (!text) return "";

  return transformOutsideCodeFences(text, (content) =>
    content.replace(/\$([0-9][^$\n]*?(?:\\[a-zA-Z]+|[=+\-*/^])[^$\n]*?)\$/g, (_match, expression) => {
      const trimmed = expression.trim();
      return `$ ${trimmed} $`;
    })
  );
}

export function normalizePlainAlgebra(text) {
  /** Convert common plain-text algebra from the model into readable inline math. */
  if (!text) return "";

  return transformOutsideCodeFences(text, (content) =>
    transformOutsideInlineMath(textToNormalizePlainAlgebra(content), (part) =>
      part.replace(/\(([^()\n]{1,140})\)/g, (match, expression) => {
        if (!isPlainMathExpression(expression)) {
          return match;
        }

        return `$${expression.trim()}$`;
      })
    )
  );
}

function textToNormalizePlainAlgebra(content) {
  /** Normalize grouped powers before the wider parenthetical math pass. */
  return content
    .replace(
      PLAIN_ALGEBRA_DOUBLE_PAREN_PATTERN,
      (_match, base, exponent) => {
        const expression = /[+\-]/.test(base)
          ? `(${base})^${exponent}`
          : `${base}^${exponent}`;
        return `$${expression}$`;
      }
    )
    .replace(
      PLAIN_ALGEBRA_GROUPED_POWER_PATTERN,
      (_match, base, exponent, suffix) =>
        `$(${base.trim()})^${exponent}${suffix.trimEnd()}$`
    );
}

function isPlainMathExpression(expression) {
  /** Identify compact algebra expressions without catching normal prose. */
  const trimmed = expression.trim();

  if (!trimmed || !/^[A-Za-z0-9\s+\-*/=^_,.]+$/.test(trimmed)) {
    return false;
  }

  if (!/[=^+\-*/]/.test(trimmed)) {
    return false;
  }

  const words = trimmed.match(/[A-Za-z]{3,}/g) || [];
  return words.length === 0;
}

export function normalizePlainExponents(text) {
  /**
   * Convert plain-text caret exponents to inline KaTeX math.
   *
   * The LLM writes things like:
   *   Rs 50,000 x 10^7 = Rs 5 x 10^11
   *   Population = 50 x 10^6
   *   n^2 + 2n + 1
   *
   * These are outside any math delimiters so KaTeX ignores them.
   * This pass wraps only caret expressions in $...$ so they render as
   * proper superscripts. Handles:
   *   digit^digit  →  $10^7$
   *   letter^digit →  $n^2$
   *   word^{expr}  →  $x^{n+1}$
   */
  if (!text) return "";

  return transformOutsideCodeFences(text, (content) =>
    transformOutsideInlineMath(content, (part) =>
      part.replace(
        /\b([A-Za-z0-9]+)\^(\{[^{}]+\}|\d+)/g,
        (_match, base, exp) => {
          // Wrap multi-digit exponents in {} so KaTeX renders all digits
          // e.g. 10^11 → $10^{11}$ not $10^1$1
          const wrappedExp = /^\d{2,}$/.test(exp) ? `{${exp}}` : exp;
          return `$${base}^${wrappedExp}$`;
        }
      )
    )
  );
}

export function normalizeSquareBracketMath(text) {
  /**
   * Convert LaTeX display-math written with square-bracket notation to $$ delimiters.
   *
   * The LLM sometimes outputs:
   *   [ \text{Per Capita Income} = \frac{\text{Total Income}}{\text{Population}} ]
   *   \[ x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a} \]
   *
   * Both forms are valid LaTeX but remark-math only recognises $$ for display math.
   * This pass converts them so KaTeX can render them correctly.
   */
  if (!text) return "";

  return transformOutsideCodeFences(text, (content) => {
    // 1. \[ ... \] escaped bracket notation (most standard LaTeX form)
    let result = content.replace(
      /\\\[\s*([\s\S]*?)\s*\\\]/g,
      (_match, inner) => {
        if (/\\[a-zA-Z]/.test(inner) || /[=^_{}/]/.test(inner)) {
          return `$$${inner.trim()}$$`;
        }
        return _match;
      }
    );

    // 2. [ ... ] single square brackets where content contains a LaTeX command
    // Careful not to match markdown links [text](url) or list items
    result = result.replace(
      /(?<![!])\[\s*((?:[^\[\]]*\\[a-zA-Z{][^\[\]]*)+)\s*\]/g,
      (_match, inner) => {
        // Skip if it looks like a markdown link (has following parenthesis)
        return `$$${inner.trim()}$$`;
      }
    );

    return result;
  });
}

export function normalizeTutorMarkdown(text) {
  /** Normalize common model markdown mistakes before ReactMarkdown renders it.
   *
   * Order matters:
   *  1. normalizeMermaidBlocks      — wrap loose graph TD blocks
   *  2. normalizeLatexParentheses   — (\frac{}{}) → $...$
   *  3. normalizePlainAlgebra       — (a+b)^2 → $...$
   *  4. normalizeSquareBracketMath  — [ \LaTeX ] and \[...\] → $$...$$
   *                                  MUST run before normalizePlainExponents so
   *                                  10^{11} inside bracket formulas isn't
   *                                  pre-converted to $ 10^{11} $ first
   *  5. normalizePlainExponents     — 10^7 → $10^{7}$ (outside existing math)
   *  6. normalizeDollarMath         — fix $10...$ currency-lookalike spacing
   *  7. removeUnsupportedQuestionClosers — rewrite "Would you like..." prompts
   */
  return removeUnsupportedQuestionClosers(
    normalizeDollarMath(
      normalizePlainExponents(
        normalizeSquareBracketMath(
          normalizePlainAlgebra(normalizeLatexParentheses(normalizeMermaidBlocks(text)))
        )
      )
    )
  );
}
