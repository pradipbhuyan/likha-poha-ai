import { describe, expect, test } from "vitest";

import {
  normalizeDollarMath,
  normalizeLatexParentheses,
  normalizePlainAlgebra,
  normalizeSquareBracketMath,
  normalizeTutorMarkdown,
  removeUnsupportedQuestionClosers,
} from "../utils/markdownCleanup";

// ---------------------------------------------------------------------------
// Regression: Defect 8467c3f3 — single-line display math ($$eq$$) was
// corrupted by normalizeInlineDisplayMath Step 3.  The regex used \S which
// matched the leading $ of a display-math line, causing $$eq$$ → $$eq
// (closing $$ stripped).  Subsequent pipeline steps then cascaded errors
// producing garbled output like "v = v0 + at x = x0 + v0t + 1/2at^2$$".
// Fix: Step 3 now uses [^\s$] so lines starting with $ are excluded.
// ---------------------------------------------------------------------------

describe("markdownCleanup", () => {
  test("converts parenthesized LaTeX expressions into inline math", () => {
    const input =
      "A rational number is (\\frac{p}{q}), where (p) and (q) are integers, and (q \\neq 0). Also (7 = \\frac{7}{1}).";

    expect(normalizeLatexParentheses(input)).toBe(
      "A rational number is $\\frac{p}{q}$, where $p$ and $q$ are integers, and $q \\neq 0$. Also $7 = \\frac{7}{1}$."
    );
  });

  test("leaves normal prose parentheses untouched", () => {
    expect(
      normalizeLatexParentheses("Rational numbers (also called ratios) are useful.")
    ).toBe("Rational numbers (also called ratios) are useful.");
  });

  test("keeps prose readable when a parenthetical contains a formula", () => {
    const input =
      "Whole numbers like 5 (which can be written as \\frac{5}{1}) are rational. Integers work (because an integer can be written as \\frac{a}{1}).";

    expect(normalizeLatexParentheses(input)).toBe(
      "Whole numbers like 5 which can be written as $\\frac{5}{1}$ are rational. Integers work because an integer can be written as $\\frac{a}{1}$."
    );
  });

  test("makes numeric dollar equations renderable as math instead of currency text", () => {
    const input = "Subtract twice the middle square: $10 - 2 \\times 4 = 10 - 8 = 2$.";

    expect(normalizeDollarMath(input)).toBe(
      "Subtract twice the middle square: $ 10 - 2 \\times 4 = 10 - 8 = 2 $."
    );
  });

  test("converts common plain algebra double parentheses into inline math", () => {
    const input = "Let the squares be ((n)^2), ((n+1)^2), and ((n+2)^2).";

    expect(normalizePlainAlgebra(input)).toBe(
      "Let the squares be $n^2$, $(n+1)^2$, and $(n+2)^2$."
    );
  });

  test("converts algebraic identity examples into inline math", () => {
    const input =
      "Mistake: Assuming ((a + b)^2 = a^2 + b^2). For (a = 10, b = 2), ((a + b)^2 = 12^2 = 144) and (a^2 + b^2 = 100 + 4 = 104).";

    expect(normalizePlainAlgebra(input)).toBe(
      "Mistake: Assuming $(a + b)^2 = a^2 + b^2$. For $a = 10, b = 2$, $(a + b)^2 = 12^2 = 144$ and $a^2 + b^2 = 100 + 4 = 104$."
    );
  });

  test("does not rewrite Mermaid code fences while cleaning prose", () => {
    const input = [
      "Use (\\frac{p}{q}) here.",
      "```mermaid",
      "graph TD",
      "A[(\\frac{p}{q})] --> B[Done]",
      "```",
    ].join("\n");

    expect(normalizeTutorMarkdown(input)).toContain("Use $\\frac{p}{q}$ here.");
    expect(normalizeTutorMarkdown(input)).toContain("A[(\\frac{p}{q})] --> B[Done]");
  });

  test("rewrites conversational lesson endings into next-step instructions", () => {
    const input =
      "This summary prepares you for the next idea. Would you like to try reading an introduction together from your textbook next?";

    expect(removeUnsupportedQuestionClosers(input)).toBe(
      "This summary prepares you for the next idea. Review these key points, then move to the next lesson section when ready."
    );
  });

  // ── Regression: defect 8467c3f3 ──────────────────────────────────────────
  test("preserves single-line display math $$eq$$ without stripping closing $$", () => {
    // LLM commonly writes each kinematic equation on its own line as $$eq$$.
    // The old Step 3 regex (\S) matched the leading $ and stripped the trailing
    // $$, breaking KaTeX rendering entirely.
    const input = [
      "$$v = v_0 + at$$",
      "$$x = x_0 + v_0t + \\frac{1}{2}at^2$$",
      "$$v^2 = v_0^2 + 2ax$$",
    ].join("\n");

    const result = normalizeTutorMarkdown(input);

    expect(result).toContain("$$v = v_0 + at$$");
    expect(result).toContain("$$x = x_0 + v_0t + \\frac{1}{2}at^2$$");
    expect(result).toContain("$$v^2 = v_0^2 + 2ax$$");
  });

  test("still strips genuinely dangling trailing $$ from prose lines", () => {
    // Lines that start with prose text (not $) and end with an orphan $$
    // must still be cleaned up by Step 3.
    const input = "The displacement is x = x_0 + v_0t + at^2$$";
    const result = normalizeTutorMarkdown(input);
    expect(result).not.toMatch(/at\^2\$\$/);
  });

  test("splits multiple $$eq$$ blocks on the same line into individual display-math lines", () => {
    // The LLM sometimes emits all three kinematic equations on one line:
    //   "$$v = v_0 + at$$ $$x = x_0 + v_0t + \frac{1}{2}at^2$$ $$v^2 = v_0^2 + 2ax$$"
    // The pre-step must split these at the "$$[space]$$" boundary and the
    // JS replacement must use a function to avoid "$$" → "$" string escaping.
    const input = [
      "$$v = v_0 + at$$",
      "$$x = x_0 + v_0t + \\frac{1}{2}at^2$$",
      "$$v^2 = v_0^2 + 2ax$$",
    ].join(" "); // intentionally joined with spaces (same line)

    const result = normalizeTutorMarkdown(input);

    expect(result).toContain("$$v = v_0 + at$$");
    expect(result).toContain("$$x = x_0 + v_0t + \\frac{1}{2}at^2$$");
    expect(result).toContain("$$v^2 = v_0^2 + 2ax$$");
  });

  test("splits multiple $$eq$$ blocks with NO separator between them (defect 8467c3f3)", () => {
    // The LLM sometimes concatenates display-math blocks with zero whitespace
    // between the closing $$ of one equation and the opening $$ of the next:
    //   "$$v = v_0 + at$$$$x = x_0 + v_0t + \frac{1}{2}at^2$$$$v^2 = v_0^2 + 2ax$$"
    // The old pre-step regex required at least one space/tab between the two
    // $$ pairs ([ \t]+), so a bare "$$$$" boundary fell through untouched and
    // the per-line Step 1 regex paired the dollar signs incorrectly, producing
    // garbled output like "v = v0 + at x = x0 + v0t + 1/2at^2$$ v^2 v0^2 + 2ax"
    // with stray literal "$$" and mismatched inline/display delimiters.
    const input =
      "$$v = v_0 + at$$$$x = x_0 + v_0t + \\frac{1}{2}at^2$$$$v^2 = v_0^2 + 2ax$$";

    const result = normalizeTutorMarkdown(input);

    expect(result).toBe(
      [
        "$$v = v_0 + at$$",
        "$$x = x_0 + v_0t + \\frac{1}{2}at^2$$",
        "$$v^2 = v_0^2 + 2ax$$",
      ].join("\n")
    );
    expect(result).not.toMatch(/\$\$\$/);
  });

  test("normalizeSquareBracketMath does not catastrophically backtrack on interval-style brackets", () => {
    // Discovered while auditing broken math rendering: a Grade 11 Trigonometric
    // Functions lesson containing interval notation like "[0°,360°)" mixed with
    // several backslash-letter LaTeX sequences (e.g. \circ) elsewhere in the
    // same paragraph froze the browser tab — normalizeTutorMarkdown() never
    // returned. Root cause: the old pattern
    //   /(?<![!])\[\s*((?:[^\[\]]*\\[a-zA-Z{][^\[\]]*)+)\s*\]/g
    // repeats a group containing two adjacent unbounded [^\[\]]* quantifiers,
    // which is catastrophically backtracking whenever the text has several
    // "\letter" anchors and the overall match ultimately fails (e.g. no closing
    // bracket). Fixed by dropping the redundant (?:...)+  repetition — a single
    // application already absorbs multiple backslash commands via the trailing
    // [^\[\]]*, so behavior is unchanged but there is nothing left to backtrack.
    //
    // This adversarial input (many "\b" anchors, no closing "]") took ~850ms
    // for just 10 repetitions with the old pattern and grows exponentially;
    // the fixed pattern must stay near-instant regardless of size.
    const evil = "[" + "a \\b ".repeat(40);

    const start = Date.now();
    normalizeSquareBracketMath(evil);
    normalizeTutorMarkdown(evil);
    const elapsed = Date.now() - start;

    expect(elapsed).toBeLessThan(500);
  });
});
