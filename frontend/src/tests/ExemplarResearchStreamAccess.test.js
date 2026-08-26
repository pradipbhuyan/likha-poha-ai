import { describe, expect, test } from "vitest";

import { getSubjectsForGrade } from "../utils/exemplarResearchAccess";

describe("ExemplarResearchPage — getSubjectsForGrade stream filtering", () => {
  test("Grade 9 (non-upper-secondary) always gets Maths + Science", () => {
    expect(getSubjectsForGrade("Grade 9", { stream: "PCM" })).toEqual([
      "Maths",
      "Science",
    ]);
  });

  test("PCM stream sees Physics, Chemistry, Maths (no Biology)", () => {
    const subjects = getSubjectsForGrade("Grade 11", { stream: "PCM" });
    expect(subjects).toEqual(["Physics", "Chemistry", "Maths"]);
  });

  test("PCB stream sees Physics, Chemistry, Biology (no Maths)", () => {
    const subjects = getSubjectsForGrade("Grade 12", { stream: "PCB" });
    expect(subjects).toEqual(["Physics", "Chemistry", "Biology"]);
  });

  test("PCMB stream sees all four Science subjects", () => {
    const subjects = getSubjectsForGrade("Grade 11", { stream: "PCMB" });
    expect(subjects).toEqual(["Physics", "Chemistry", "Maths", "Biology"]);
  });

  test("no stream chosen yet still shows all four (not a mismatch)", () => {
    const subjects = getSubjectsForGrade("Grade 11", { stream: "" });
    expect(subjects).toEqual(["Physics", "Chemistry", "Maths", "Biology"]);
  });

  test("REGRESSION: Commerce stream sees no Science subjects, not all four", () => {
    // Before this fix, any stream other than PCM/PCB/PCMB fell through to
    // "show all four Science subjects" — wrong for a real Commerce student,
    // who studies none of them. Exemplar Research has no Commerce content.
    const subjects = getSubjectsForGrade("Grade 11", { stream: "Commerce" });
    expect(subjects).toEqual([]);
  });

  test("REGRESSION: Humanities stream sees no Science subjects, not all four", () => {
    const subjects = getSubjectsForGrade("Grade 12", { stream: "Humanities" });
    expect(subjects).toEqual([]);
  });

  test("the all-access QA test account sees all four regardless of stream", () => {
    const subjects = getSubjectsForGrade("Grade 11", {
      stream: "Commerce",
      isTestAccount: true,
    });
    expect(subjects).toEqual(["Physics", "Chemistry", "Maths", "Biology"]);
  });
});
