import { describe, expect, test } from "vitest";

import {
  normalizeDollarMath,
  normalizeLatexParentheses,
  normalizePlainAlgebra,
  normalizeTutorMarkdown,
  removeUnsupportedQuestionClosers,
} from "../utils/markdownCleanup";

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
});
