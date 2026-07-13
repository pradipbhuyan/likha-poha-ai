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
  /** Apply cleanup only outside already-normalized math spans.
   *  Protects both $...$ inline math AND $$...$$ display math blocks.
   */
  return text
    .split(/(\$\$[\s\S]*?\$\$|\$[^$\n]*\$)/g)
    .map((part) => (part.startsWith("$") ? part : transform(part)))
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
        // Negative lookbehind (?<!\/) prevents matching digit-starting bases like
        // "2at^2" that appear as fraction denominators (e.g. "1/2at^2").  Without
        // it, normalizePlainExponents converts "2at^2" → "$2at^2$", which then
        // sits adjacent to a neighbouring "$...$" block, creating a "$$" junction
        // that remark-math reads as a display-math delimiter.
        /(?<!\/)\b([A-Za-z0-9]+)\^(\{[^{}]+\}|\d+)/g,
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

function normalizeBulletPoints(text) {
  /** Convert • bullet format (used in LKB answers) to markdown list items.
   *  Input:  "• Point one\n• Point two\n• Point three"
   *  Output: "- Point one\n- Point two\n- Point three"
   *  Each bullet on its own line so ReactMarkdown renders a proper <ul>.
   */
  if (!text || !text.includes("•")) return text;
  // Split on bullet character, remove empty entries, rebuild as - list items
  const lines = text.split("\n");
  return lines
    .map(line => {
      const trimmed = line.trim();
      if (trimmed.startsWith("•")) {
        return "- " + trimmed.slice(1).trim();
      }
      return line;
    })
    .join("\n");
}

/**
 * Fix $ expr $ patterns where remark-math ignores inline math when the opening
 * dollar sign is immediately followed by a space.
 *
 * remark-math rule: opening $ must NOT be followed by whitespace.
 * So "$ 1/2 $" is treated as literal text, not math.
 *
 * This pass strips the inner leading/trailing spaces:
 *   "$ 1/2 $"  →  "$1/2$"   ← remark-math now parses it as math
 *   "$ at^2 $" →  "$at^2$"
 *
 * Only matches $ SPACE content SPACE $ (single-space-padded) to avoid
 * touching legitimate prose like "$100 and $200 are different".
 */
function normalizeSpacedDollarMath(text) {
  if (!text || !text.includes("$ ")) return text;
  return transformOutsideCodeFences(text, (content) =>
    // $ space content space $ — strip the padding spaces
    content.replace(/\$ ([^$\n]+?) \$/g, (_m, inner) => `$${inner.trim()}$`)
  );
}

/**
 * Strip nested $...$ inline-math delimiters that appear INSIDE a $$...$$ display
 * math block.  The LLM sometimes writes things like:
 *
 *   $$\frac{7.50$\times 10^{4}$\;\text{m}}{4500}$$
 *
 * Inside a display-math block, $ is not a valid delimiter — it breaks KaTeX
 * tokenisation.  Stripping the inner $ signs (keeping the content) fixes it:
 *
 *   $$\frac{7.50\times 10^{4}\;\text{m}}{4500}$$
 *
 * Only acts on CLOSED $$...$$  blocks.  Unclosed ones are left to
 * normalizeInlineDisplayMath.
 */
function normalizeNestedDollarSignsInDisplay(text) {
  if (!text || !text.includes("$$")) return text;
  const PLACEHOLDER = "\u2060\u2060"; // word-joiners — won't appear in LaTeX content
  return transformOutsideCodeFences(text, (content) =>
    // Match $$...$$  (non-greedy, any character including newlines)
    content.replace(/\$\$([\s\S]*?)\$\$/g, (_m, inner) => {
      // Inside display math: strip any $ that is NOT part of a $$ pair
      const cleaned = inner
        .replace(/\$\$/g, PLACEHOLDER)     // temporarily hide $$ pairs
        .replace(/\$/g, "")               // strip lone $
        .replace(new RegExp(PLACEHOLDER.replace(/./g, (c) => `\\u${c.charCodeAt(0).toString(16).padStart(4,"0")}`), "g"), "$$"); // restore $$
      return `$$${cleaned}$$`;
    })
  );
}

/**
 * Fix $$ used INLINE (mid-sentence) by downgrading to $ $ inline math.
 *
 * Proper display math: $$ on its own line as a block.
 * Bad LLM output: "x = v0t + 1/2 $$at^2$$" or "use equation $$at^2"
 *
 * Strategy (multiline per-line matching):
 *   - If a line contains $$ with non-whitespace before it → inline usage
 *   - Closed inline: text $$expr$$ more → text $expr$ more
 *   - Unclosed inline: text $$expr         → text $expr$
 *   - Trailing $$: text$$  (end-of-line) → text  (strip the dangling $$)
 *
 * IMPORTANT: lines that START with $ (i.e. display-math blocks like $$eq$$)
 * must NEVER be touched by Step 3.  The old pattern used \S which matched the
 * leading $ itself, causing $$eq$$ → $$eq (closing $$ stripped).  The fix
 * uses [^\s$] so the first captured character must be neither whitespace nor $,
 * which excludes any line that opens with a display-math delimiter.
 */
function normalizeInlineDisplayMath(text) {
  if (!text || !text.includes("$$")) return text;
  return text
    // Compact step: re-join $$...$$ equations that the LLM line-wrapped.
    //   "$$eq_start +\ncontinuation$$"  →  "$$eq_start + continuation$$"
    // Only matches when line N starts with $$ + content (not a bare $$) and
    // line N+1 ends with $$ — i.e. the continuation of that equation.
    // This runs BEFORE the pre-step split so the pre-step sees intact blocks.
    .replace(/^(\$\$[^$\n][^\n]*)\n([^\n]*\$\$)/gm, (_m, a, b) => `${a} ${b}`)
    // Pre-step: when two $$...$$ blocks are separated only by whitespace on the
    // same line, the closing $$ of block N and the opening $$ of block N+1 form
    // a "$$[spaces]$$" sequence.  Split it onto separate lines so Step 1 cannot
    // treat the gap as inline formula content.
    //   "$$eq1$$ $$eq2$$ $$eq3$$"  →  "$$eq1$$\n$$eq2$$\n$$eq3$$"
    // NOTE: replacement must be a function — in a string replacement "$$" → "$"
    // (JS special pattern), so "$$\n$$" would produce "$\n$" which is wrong.
    .replace(/\$\$([ \t]+)\$\$/g, () => "$$\n$$")
    // Step 1: closed inline $$...$$ on same line with text before the first $$
    .replace(/^(.+?)\$\$([^\n$]+?)\$\$(.*)$/gm, (_m, before, content, after) =>
      `${before}$${content.trim()}$${after}`)
    // Step 2: unclosed inline $$ on same line with text before it AND content after $$
    .replace(/^(.+?)\$\$([^\n$][^\n]*)$/gm, (_m, before, content) => {
      if (/\S/.test(before)) return `${before}$${content.trim()}$`;
      return _m;
    })
    // Step 3: trailing $$ at end of line with non-$ non-whitespace content before.
    //   "at^2$$"  →  "at^2"   (dangling closing $$ with nothing after)
    //   "x = ...$$ "  →  "x = ..."
    //   Lines starting with $ ($$eq$$ display blocks) are intentionally excluded
    //   so that valid single-line display math like $$v = v_0 + at$$ is preserved.
    .replace(/^(\s*[^\s$][^\n]*?)\$\$\s*$/gm, (_m, before) => before.trimEnd());
}

/**
 * Remove orphaned (unmatched) trailing $ signs on a line that break KaTeX.
 *
 * The LLM sometimes emits lines like:
 *   "$v^2$ = $v0^2$ + 2ax$"   ← 3 dollar signs, last one unmatched
 *   "x = x0 + v0t + $ 1/2 $at^2$"  ← trailing $ after at^2
 *
 * Strategy: count unescaped $ signs per line (outside code fences).
 * If the count is odd, one $ is unmatched. Remove the last standalone $
 * that is NOT part of a $$ pair and is followed only by whitespace/end.
 */
function normalizeOrphanedDollarSigns(text) {
  if (!text || !text.includes("$")) return text;
  return transformOutsideCodeFences(text, (content) =>
    content.split("\n").map((line) => {
      // Count single $ signs (not part of $$)
      // Replace $$ with a placeholder so they don't count as two singles
      const withoutPairs = line.replace(/\$\$/g, "##");
      const singleCount = (withoutPairs.match(/\$/g) || []).length;
      if (singleCount % 2 === 0) return line; // even → balanced
      // Odd count: strip the last trailing $ that's not preceded by another $
      return line.replace(/(?<!\$)\$\s*$/, "");
    }).join("\n")
  );
}

export function normalizeTutorMarkdown(text) {
  /** Normalize common model markdown mistakes before ReactMarkdown renders it.
   *
   * Order matters:
   *  0. normalizeNestedDollarSignsInDisplay — strip $...$ inside $$...$$ blocks
   *  1. normalizeSpacedDollarMath    — "$ expr $" (spaced) → "$expr$" for remark-math
   *  2. normalizeInlineDisplayMath   — $$ used inline → $ $; trailing $$ stripped
   *  3. normalizeOrphanedDollarSigns — odd $ count on a line → strip trailing orphan
   *  4. normalizeBulletPoints        — • Point → - Point (LKB answers)
   *  5. normalizeMermaidBlocks       — wrap loose graph TD blocks
   *  6. normalizeLatexParentheses    — (\frac{}{}) → $...$
   *  7. normalizePlainAlgebra        — (a+b)^2 → $...$
   *  8. normalizeSquareBracketMath   — [ \LaTeX ] and \[...\] → $$...$$
   *  9. normalizePlainExponents      — 10^7 → $10^{7}$ (outside existing math)
   * 10. normalizeDollarMath          — fix $10...$ currency-lookalike spacing
   * 11. removeUnsupportedQuestionClosers — rewrite "Would you like..." prompts
   */
  return removeUnsupportedQuestionClosers(
    normalizeDollarMath(
      normalizePlainExponents(
        normalizeSquareBracketMath(
          normalizePlainAlgebra(normalizeLatexParentheses(normalizeMermaidBlocks(normalizeBulletPoints(
            normalizeOrphanedDollarSigns(normalizeInlineDisplayMath(
              normalizeSpacedDollarMath(normalizeNestedDollarSignsInDisplay(text))
            ))
          ))))
        )
      )
    )
  );
}
