import { describe, expect, test } from "vitest";

import {
  normalizeLatexParentheses,
  normalizeTutorMarkdown,
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
});
