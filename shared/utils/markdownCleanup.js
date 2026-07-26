const LATEX_COMMAND_PATTERN =
  /\\(?:frac|sqrt|neq|leq|geq|times|div|cdot|pi|theta|alpha|beta|gamma|delta|infty|pm|approx|equiv|propto|sum|int|left|right|text|overline|angle|parallel|perp)/;

const LATEX_FRAGMENT_PATTERN =
  /\\frac\{[^{}]+\}\{[^{}]+\}|\\sqrt\{[^{}]+\}|[A-Za-z0-9{}\s+\-*/=^_]*\\(?:neq|leq|geq|times|div|cdot|pm|approx|equiv|propto)[A-Za-z0-9{}\s+\-*/=^_]*/g;

// (?<!\\) on the first "(" — without it, both patterns match into an escaped
// "\((expr)^n\)" LaTeX inline-math sequence, treating the "\(" delimiter's own
// "(" as the first of the required "((" pair. "\((a + b)^2\)" becomes
// "\$(a + b)^2\$" (stray backslashes) instead of being left for
// normalizeSquareBracketMath's dedicated \( \) handler, which runs later and
// correctly includes the backslashes in its own match.
const PLAIN_ALGEBRA_DOUBLE_PAREN_PATTERN =
  /(?<!\\)\(\(([a-zA-Z][a-zA-Z0-9]*(?:[+\-]\d+)?)\)\^(\d+)\)/g;

const PLAIN_ALGEBRA_GROUPED_POWER_PATTERN =
  /(?<!\\)\(\(([^()\n]{1,60})\)\^(\d+)([^()\n]{0,120})\)/g;

// Single (not double-wrapped) "(expr)^n" — e.g. "(a + b)^2 = a^2 + 2ab + b^2"
// straight from the model with no outer wrap and no backslash escaping at
// all (a distinct case from both patterns above and from the \(...\) escape
// handled by normalizeEscapedBracketMath). Without this pattern,
// normalizePlainAlgebra's generic single-paren regex below matches only
// "(a + b)" and wraps it alone, stranding the "^2" outside the $...$ span:
// "$a + b$^2" (literal caret-2, not a superscript) instead of "$(a + b)^2$".
const PLAIN_ALGEBRA_PAREN_POWER_PATTERN =
  /(?<!\\)\(([^()\n]{1,140})\)\^(\d+)/g;

export function normalizeLeftRightDelimiters(text) {
  /**
   * Fix \left / \right LaTeX sizing commands missing their delimiter.
   *
   * \left and \right ALWAYS require a real bracket character immediately
   * after them (\left(, \left[, \left\{, etc.) — there is no valid LaTeX
   * where \left or \right is followed by a bare $. Models sometimes drop
   * the delimiter and write \left$ / \right$ instead (seen even from
   * claude-sonnet-5 on inverse-trig principal-value ranges), which reads
   * as a dangling dollar sign to remark-math and confuses every downstream
   * $-counting pass. This is unambiguous — unlike bare parentheses, there
   * is no legitimate content to preserve, so no gate is needed — and must
   * run FIRST, before anything else tries to balance/pair dollar signs.
   *
   *   \left$\frac{1}{2}\right$$  →  \left(\frac{1}{2}\right)
   */
  if (!text || !text.includes("\\left") && !text.includes("\\right")) return text;
  return transformOutsideCodeFences(text, (content) =>
    content
      .replace(/\\left\s*\$/g, "\\left(")
      .replace(/\\right\s*\$/g, "\\right)")
  );
}

export function normalizeEscapedBracketMath(text) {
  /**
   * Convert \( ... \) and \[ ... \] escaped-bracket math (LaTeX's other
   * standard delimiters, alongside $...$ / $$...$$) to $...$ / $$...$$.
   *
   * remark-math only recognises $ / $$, so \(x\) and \[x\] render as
   * literal backslash-bracket text otherwise. Seen from models that default
   * to \( \) / \[ \] style regardless of prompt instructions to use $ (e.g.
   * Ollama gpt-oss:120b, and claude-sonnet-5 via Venice on worked-example
   * "Combine all parts: \[ (3x + 4)^2 = 9x^2 + 24x + 16 \]" steps). No
   * content gate needed — unlike bare ( ) / [ ], the literal "\(" / "\)" /
   * "\[" / "\]" escape sequence never occurs by accident in ordinary prose,
   * so a gate only causes false negatives (e.g. a bare single-variable
   * "\(p\)" has no LaTeX command to match on).
   *
   * MUST run early, before normalizeLatexParentheses / normalizePlainAlgebra
   * / normalizeSquareBracketMath — all match bare "(...)" / "[...]" patterns
   * and none can reliably tell "this bracket is nested inside an outer
   * \(...\) / \[...\] escape" from a one-character lookbehind (the bracket
   * immediately after "\(" / "\[" is preceded by another "(" / "[", not a
   * literal backslash). Converting the escape to clean $/$$ first means
   * those later passes see an already-protected math span and skip it via
   * their own transformOutsideInlineMath guard, instead of matching into
   * the escape and leaving the backslashes stranded:
   * "\((a + b)^2\)" → "\($a + b$^2\)" instead of "$(a + b)^2$", and
   * "\[(3x + 4)^2 = ...\]" → "\[$3x + 4$^2 = ...\]" instead of
   * "$$(3x + 4)^2 = ...$$".
   */
  if (!text) return "";
  return transformOutsideCodeFences(text, (content) =>
    content
      .replace(
        /\\\(\s*([\s\S]*?)\s*\\\)/g,
        (_match, inner) => `$${inner.trim()}$`
      )
      .replace(
        /\\\[\s*([\s\S]*?)\s*\\\]/g,
        (_match, inner) => `$$${inner.trim()}$$`
      )
  );
}

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
  /**
   * Detect parentheticals that mix normal sentence text with a LaTeX formula.
   *
   * Uses a global-flagged copy of LATEX_COMMAND_PATTERN, not the shared
   * constant directly — LATEX_COMMAND_PATTERN is reused elsewhere with
   * .test(), and a global regex's .test() carries lastIndex state between
   * calls (alternating true/false on repeated calls with the same object).
   * A non-global .replace() here also only strips the FIRST command match,
   * so an expression with the same command repeated (e.g. three \sqrt{}
   * terms) left the other two miscounted as prose words — sending it down
   * the wrong branch (split into multiple $ pairs instead of one).
   */
  const proseWords =
    expression
      .replace(new RegExp(LATEX_COMMAND_PATTERN.source, "g"), "")
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
      // (?<!\\) — skip when the "(" is itself part of a "\(" LaTeX inline-math
      // escape sequence. Without this, "\(\sqrt{2},\sqrt{3},\sqrt{5}\)" gets
      // its "(...)" matched as if it were a plain parenthetical, stripping
      // the parens and leaving the surrounding backslashes stranded as
      // literal text — normalizeSquareBracketMath's dedicated \( \) handler
      // (which runs later and includes the backslashes in its own match)
      // is the correct place to convert this, not here.
      //
      // (?<!\\left) — skip when the "(" is the required delimiter for a
      // \left sizing command. \left(...\right) is already valid, complete
      // LaTeX on its own — it doesn't need (and must not get) its own
      // separate $...$ wrap. Without this, "\left(\dfrac{-\sqrt{3}}{2}\right)"
      // gets its "(...)" matched as a plain parenthetical and rewrapped into
      // "\left$\dfrac{-\sqrt{3}}{2}$\right" — recreating the exact bare-$
      // delimiter bug normalizeLeftRightDelimiters exists to fix, just from
      // the opposite direction.
      /(?<!\\)(?<!\\left)\(([^()\n]*\\[^()\n]*)\)/g,
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

    // Ranges already inside a $...$ / $$...$$ math span — the single-letter
    // paren pass below must never fire inside these, or it nests a new
    // $...$ pair inside an already-open one. Seen on chemistry state symbols:
    // "$\mathrm{C(s) + O_2(g) \rightarrow CO_2(g)}$" has its "(s)" and "(g)"
    // rewritten to "$s$"/"$g$" because the surrounding text already contains
    // a "$...$" pattern (the very span they're inside), which used to satisfy
    // the nearby-math heuristic below. The stray inner $ pairs throw off
    // remark-math's $ count for the rest of the document, so KaTeX fails to
    // parse the equation (and everything after it) and renders raw source.
    const mathRanges = [];
    const mathSpanPattern = /\$\$[\s\S]*?\$\$|\$[^$\n]*\$/g;
    let spanMatch;
    while ((spanMatch = mathSpanPattern.exec(withLatexCommands))) {
      mathRanges.push([spanMatch.index, spanMatch.index + spanMatch[0].length]);
    }
    const insideExistingMath = (pos) =>
      mathRanges.some(([start, end]) => pos >= start && pos < end);

    return withLatexCommands.replace(
      /\(([a-zA-Z])\)/g,
      (match, variable, offset) => {
        if (insideExistingMath(offset)) {
          return match;
        }

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
      // Nested transformOutsideInlineMath: PLAIN_ALGEBRA_PAREN_POWER_PATTERN
      // below introduces its own new $...$ spans within `part`, and the
      // generic single-paren regex after it must not re-scan into those —
      // its own (?<!\\) lookbehind only rules out a backslash immediately
      // before the "(", not "preceded by an already-inserted $", so without
      // this re-split "$(a + b)^2$" would have its inner "(a + b)" matched
      // again, producing "$$(a + b)^2$$" (stray extra $$ pair).
      transformOutsideInlineMath(
        part.replace(
          PLAIN_ALGEBRA_PAREN_POWER_PATTERN,
          (_match, base, exponent) => `$(${base.trim()})^${exponent}$`
        ),
        (innerPart) =>
          // (?<!\\) — skip when the "(" is itself the delimiter of a "\(" LaTeX
          // inline-math escape. Without it, "\((a + b)^2\)" has its INNER
          // "(a + b)" matched and wrapped in $...$, leaving the outer \( \)
          // backslashes stranded: "\($a + b$^2\)" instead of a clean "$(a+b)^2$"
          // — normalizeEscapedBracketMath (which runs much earlier and
          // includes the backslashes in its own match) is the correct place
          // to convert the whole thing, not here.
          innerPart.replace(/(?<!\\)\(([^()\n]{1,140})\)/g, (match, expression) => {
            if (!isPlainMathExpression(expression)) {
              return match;
            }

            return `$${expression.trim()}$`;
          })
      )
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
        // Negative lookbehind (?<![/}\)]) prevents matching bases that immediately
        // follow / (fraction denominators: "1/2at^2"), } (LaTeX braces:
        // "\frac{1}{2}at^2"), or ) (parenthesised fractions: "(1/2)at^2" — common
        // physics phrasing for kinematic equations). Without it, normalizePlainExponents
        // converts "at^2" → "$at^2$" right after a separately-wrapped "(1/2)" → "$1/2$"
        // span, and the two adjacent closing/opening $ signs form a "$$" junction that
        // remark-math reads as a display-math delimiter, breaking the whole expression.
        /(?<![/})])\b([A-Za-z0-9]+)\^(\{[^{}]+\}|\d+)/g,
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
   * Convert LaTeX written with plain (non-escaped) square-bracket notation
   * to $$ delimiters:
   *   [ \text{Per Capita Income} = \frac{\text{Total Income}}{\text{Population}} ]
   *
   * remark-math only recognises $ (inline) and $$ (display). This pass
   * converts the plain-bracket form so KaTeX can render it correctly.
   *
   * (The escaped \[...\] / \(...\) forms are handled by
   * normalizeEscapedBracketMath, which runs much earlier in the pipeline —
   * see that function's docstring for why they can't share this one's
   * lookbehind-based approach.)
   */
  if (!text) return "";

  return transformOutsideCodeFences(text, (content) =>
    // [ ... ] single square brackets where content contains a LaTeX command
    // Careful not to match markdown links [text](url) or list items
    //
    // NOT `(?:[^\[\]]*\\[a-zA-Z{][^\[\]]*)+` (repeated group) — that shape is
    // catastrophically backtracking: two adjacent unbounded `[^\[\]]*` inside a
    // `+`-repeated group gives the engine exponentially many ways to split a
    // long bracket-free run across repetitions before failing, which hangs the
    // browser tab for seconds-to-indefinitely on real lesson content (observed
    // hang on Grade 11 Trigonometric Functions content with interval notation
    // like "[0°,360°)" mixed with "\[...\]" elsewhere in the same paragraph).
    // A single (non-repeated) application already matches multiple backslash
    // commands inside one bracket pair, since the trailing `[^\[\]]*` freely
    // absorbs any further commands up to the closing `]` — verified behaviorally
    // identical to the old pattern on every non-hanging test case.
    content.replace(
      /(?<![!])\[\s*([^\[\]]*\\[a-zA-Z{][^\[\]]*)\s*\]/g,
      (_match, inner) => `$$${inner.trim()}$$`
    )
  );
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
 * Insert a space between a $...$ inline-math span and an adjacent word with
 * no space between them — "$a$and$b$are coprime" → "$a$ and $b$ are coprime".
 *
 * The MATH RULES prompt now tells the LLM to always space inline math from
 * surrounding words, but this is a defensive client-side backstop: some
 * models (seen with Ollama gpt-oss:120b) don't reliably follow that
 * instruction every time it's asked, even on separate generations of the
 * same content. Without the space, "$a$and$b$" isn't just a rendering
 * quirk — it merges what should be two separate math spans and their
 * surrounding text into one visually squashed run.
 *
 * (?<!\$)/(?!\$) on each delimiter keeps this from touching $$ display math.
 */
function normalizeInlineMathWordSpacing(text) {
  if (!text || !text.includes("$")) return text;
  return transformOutsideCodeFences(text, (content) =>
    // Match one whole $...$ span, then look at the actual characters just
    // outside the match in the ORIGINAL string (not lookaround assertions
    // embedded in the pattern) — a $ is both the open and close delimiter,
    // so a lookaround-only approach can't tell "letter right before the
    // closing $ (part of the math content)" apart from "letter right
    // before the opening $ (surrounding prose)"; reading the real
    // before/after characters removes that ambiguity.
    content.replace(/(?<!\$)\$([^$\n]+?)\$(?!\$)/g, (match, inner, offset, full) => {
      const before = full[offset - 1];
      const after = full[offset + match.length];
      const spaceBefore = before && /[A-Za-z]/.test(before) ? " " : "";
      const spaceAfter = after && /[A-Za-z]/.test(after) ? " " : "";
      return `${spaceBefore}$${inner}$${spaceAfter}`;
    })
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
    // Pre-step: when two $$...$$ blocks are separated only by whitespace (or
    // nothing at all) on the same line, the closing $$ of block N and the
    // opening $$ of block N+1 form a "$$[spaces]$$" or bare "$$$$" sequence.
    // Split it onto separate lines so Step 1 cannot treat the gap — or the
    // adjacent block — as inline formula content.
    //   "$$eq1$$ $$eq2$$ $$eq3$$"  →  "$$eq1$$\n$$eq2$$\n$$eq3$$"
    //   "$$eq1$$$$eq2$$$$eq3$$"    →  "$$eq1$$\n$$eq2$$\n$$eq3$$"
    // NOTE: replacement must be a function — in a string replacement "$$" → "$"
    // (JS special pattern), so "$$\n$$" would produce "$\n$" which is wrong.
    .replace(/\$\$([ \t]*)\$\$/g, () => "$$\n$$")
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
    .replace(/^(\s*[^\s$][^\n]*?)\$\$\s*$/gm, (_m, before) => before.trimEnd())
    // Step 3b: $$ immediately before sentence punctuation at end of line.
    //   "$formula$ \text{m/s}$$."  →  "$formula$ \text{m/s}."
    // The LLM sometimes doubles the closing $ delimiter accidentally (writes $$
    // instead of $ or nothing). This is distinct from a legitimate $$eq$$ display
    // block — those are always on a line where $$ appears first, which Step 3b
    // catches only when there is non-$ content BEFORE the stray $$. Lines that
    // start with $ (like $$eq$$.) are excluded by [^\s$] so display blocks
    // immediately followed by punctuation (which render fine) are left alone.
    .replace(/^(\s*[^\s$][^\n]*?)\$\$([.,;:!?]\s*)$/gm, (_m, before, punct) =>
      before.trimEnd() + punct.trim());
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

/**
 * Strip a stray trailing "}" immediately before a math span's closing
 * delimiter when it has no matching "{" — an unbalanced-brace typo the LLM
 * occasionally makes while chaining several \mathrm{...} chemistry terms:
 *
 *   $\mathrm{C(s) + O_2(g)} + \mathrm{CO_2(g)} \rightarrow
 *    \mathrm{CO_2(g)} + \mathrm{CO(g)} + ½O_2(g)}$
 *
 * Four "\mathrm{" opens, only three "}" close them before a stray extra "}"
 * arrives right before the closing $. KaTeX cannot recover from this — the
 * closing $ arrives with a macro argument still open — so it renders the
 * whole span as raw error text instead of the equation.
 *
 * Only fires when a span's total "{"/"}" counts differ by exactly one AND
 * the span's last character is that extra "}" — a narrow, unambiguous
 * signature chosen to avoid touching any span whose brace mismatch might
 * mean something else.
 */
function normalizeOrphanedMathBraces(text) {
  if (!text || !text.includes("{")) return text;
  return transformOutsideCodeFences(text, (content) =>
    content.replace(/\$\$([\s\S]*?)\$\$|\$([^$\n]+?)\$/g, (match, display, inline) => {
      const isDisplay = display !== undefined;
      const inner = isDisplay ? display : inline;
      const openCount = (inner.match(/\{/g) || []).length;
      const closeCount = (inner.match(/\}/g) || []).length;

      if (closeCount === openCount + 1 && inner.endsWith("}")) {
        const trimmedInner = inner.slice(0, -1);
        return isDisplay ? `$$${trimmedInner}$$` : `$${trimmedInner}$`;
      }

      return match;
    })
  );
}

/**
 * Insert a space between two well-formed single-$ math spans that ended up
 * touching with zero characters between them — "$1/2$$at^2$" — a shape
 * several EARLIER steps can independently produce (e.g. normalizePlainAlgebra
 * wrapping a parenthesised fraction like "(1/2)" right before
 * normalizePlainExponents wraps the very next token, "at^2", with nothing
 * separating the two insertions). The closing "$" of the first span and the
 * opening "$" of the second read as one "$$" run to remark-math, which
 * requires an EXACT-length run to close a span (like code-span fencing) — so
 * it skips the "$$" entirely and keeps hunting for a lone "$", swallowing
 * both spans' content into one malformed expression that KaTeX then fails to
 * parse and falls back to showing as raw text, "$$" and all.
 *
 * This is the same visual defect as 8467c3f3 (see test file), but from a
 * DIFFERENT source: 8467c3f3 was the LLM emitting adjacent "$$eq$$" display
 * blocks directly; this is the pipeline's OWN later steps colliding two
 * spans it inserted itself into originally plain (no "$" at all) text.
 * Deliberately runs LAST, after every other $-inserting step, so it catches
 * a collision regardless of which earlier step caused it.
 *
 * Must NOT touch genuine "$$...$$" display math: the regex requires a
 * non-"$" character immediately after the first "$" (so it can't start
 * inside a "$$" open) and requires two SEPARATE content groups, so a lone
 * "$$X$$" block or two already-adjacent "$$A$$$$B$$" display blocks (the
 * 8467c3f3 shape, handled earlier by normalizeInlineDisplayMath) both fail
 * to match here.
 */
export function normalizeAdjacentSingleDollarSpans(text) {
  /**
   * Single-pass `.replace(/g/)` only resolves the LEFTMOST collision in a run
   * of N adjacent spans — e.g. "$A$$B$$C$" becomes "$A$ $B$$C$" (one fixed,
   * one remains) because the regex engine moves past the consumed match before
   * it can see the now-adjacent second "$$". Iterating until the text
   * stabilises catches any length of adjacent-span runs (2, 3, …) in at most
   * N-1 iterations, which is bounded by the number of math spans on a line —
   * small in practice and each pass is O(n) in the string length.
   */
  if (!text || !text.includes("$$")) return text;
  return transformOutsideCodeFences(text, (content) => {
    let prev;
    let result = content;
    do {
      prev = result;
      result = result.replace(
        /\$([^$\n]+?)\$\$([^$\n]+?)\$/g,
        (_match, first, second) => `$${first}$ $${second}$`
      );
    } while (result !== prev && result.includes("$$"));
    return result;
  });
}

export function normalizeTutorMarkdown(text) {
  /** Normalize common model markdown mistakes before ReactMarkdown renders it.
   *
   * Order matters:
   *  0. normalizeLeftRightDelimiters — \left$ / \right$ → \left( / \right)
   *     (must run first — an unfixed \left$ reads as a dangling $ to every
   *     later $-counting/pairing pass below)
   *  1. normalizeEscapedBracketMath  — \(...\) → $...$, \[...\] → $$...$$
   *     (must also run early — normalizeLatexParentheses/normalizePlainAlgebra/
   *     normalizeSquareBracketMath match bare "(...)" / "[...]" and can't
   *     tell a bracket nested inside an outer \(...\) / \[...\] escape from
   *     a real one via a one-character lookbehind; converting to $/$$ first
   *     lets their existing "already inside $" guard skip it instead of
   *     matching into the escape)
   *  2. normalizeNestedDollarSignsInDisplay — strip $...$ inside $$...$$ blocks
   *  3. normalizeSpacedDollarMath    — "$ expr $" (spaced) → "$expr$" for remark-math
   *  4. normalizeInlineDisplayMath   — $$ used inline → $ $; trailing $$ stripped
   *  5. normalizeOrphanedDollarSigns — odd $ count on a line → strip trailing orphan
   *  6. normalizeBulletPoints        — • Point → - Point (LKB answers)
   *  7. normalizeMermaidBlocks       — wrap loose graph TD blocks
   *  8. normalizeLatexParentheses    — (\frac{}{}) → $...$
   *  9. normalizePlainAlgebra        — (a+b)^2 → $...$
   * 10. normalizeSquareBracketMath   — [ \LaTeX ] → $$...$$
   * 11. normalizePlainExponents      — 10^7 → $10^{7}$ (outside existing math)
   * 12. normalizeAdjacentSingleDollarSpans — "$A$$B$" (steps 8/9/11 colliding
   *     into each other with nothing between) → "$A$ $B$"
   * 13. normalizeOrphanedMathBraces  — stray trailing "}" before closing $ → stripped
   * 14. normalizeDollarMath          — fix $10...$ currency-lookalike: adds "$ ... $"
   * 14b. normalizeSpacedDollarMath   — (second call) strips the "$ ... $" spaces
   *      normalizeDollarMath introduced so remark-math can parse them as math.
   *      Must run AGAIN after step 14 — the first call (step 3) ran before
   *      normalizeDollarMath existed and cannot clean up what step 14 adds.
   * 15. normalizeInlineMathWordSpacing — "$a$and$b$" → "$a$ and $b$"
   * 16. removeUnsupportedQuestionClosers — rewrite "Would you like..." prompts
   */
  let result = text;
  result = normalizeLeftRightDelimiters(result);
  result = normalizeEscapedBracketMath(result);
  result = normalizeNestedDollarSignsInDisplay(result);
  result = normalizeSpacedDollarMath(result);
  result = normalizeInlineDisplayMath(result);
  result = normalizeOrphanedDollarSigns(result);
  result = normalizeBulletPoints(result);
  result = normalizeMermaidBlocks(result);
  result = normalizeLatexParentheses(result);
  result = normalizePlainAlgebra(result);
  result = normalizeSquareBracketMath(result);
  result = normalizePlainExponents(result);
  result = normalizeAdjacentSingleDollarSpans(result);
  result = normalizeOrphanedMathBraces(result);
  result = normalizeDollarMath(result);
  result = normalizeSpacedDollarMath(result);  // must run AFTER normalizeDollarMath: step 14 adds "$ ... $" spacing that step 3 never saw
  result = normalizeInlineMathWordSpacing(result);
  result = removeUnsupportedQuestionClosers(result);
  return result;
}
