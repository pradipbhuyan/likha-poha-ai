import { describe, expect, it } from "vitest";

import { getKeywordHint, normalizeKeywordText } from "../utils/keywordHints";

describe("keywordHints", () => {
  it("explains science keywords with useful definitions", () => {
    expect(getKeywordHint("atoms")).toContain("smallest units of matter");
  });

  it("explains multi-word science laws", () => {
    expect(getKeywordHint("Law of Conservation of Mass")).toContain(
      "neither created nor destroyed"
    );
  });

  it("explains maths terms", () => {
    expect(getKeywordHint("Rational numbers")).toContain("p/q");
  });

  it("extracts text from nested React-like children", () => {
    const children = ["Law of ", { props: { children: "Definite Proportions" } }];

    expect(normalizeKeywordText(children)).toBe("Law of Definite Proportions");
    expect(getKeywordHint(children)).toContain("fixed ratio");
  });

  it("does not highlight generic labels or unknown generated phrases", () => {
    expect(getKeywordHint("Question:")).toBe("");
    expect(getKeywordHint("Activity from the textbook:")).toBe("");
    expect(getKeywordHint("rare lesson phrase")).toBe("");
  });
});
