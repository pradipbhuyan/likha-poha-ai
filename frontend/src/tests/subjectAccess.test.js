import { describe, expect, test } from "vitest";

import {
  filterAllowedSubjects,
  parseSubjectList,
  hasCbseSubjectAccess,
  getSubjectsForStream,
} from "../utils/subjectAccess";

describe("subjectAccess", () => {
  test("filters CBSE subjects when a custom access list is configured", () => {
    /** A Science+Maths plan should hide other CBSE subjects. */
    const subjects = ["English", "Maths", "Science", "Social Science"];
    const user = {
      role: "student",
      accessCbse: true,
      cbseSubjects: ["Science", "Maths"],
    };

    expect(filterAllowedSubjects(user, subjects, "CBSE")).toEqual([
      "Maths",
      "Science",
    ]);
  });

  test("keeps all CBSE subjects when no custom list is configured", () => {
    /** Empty subject lists preserve legacy all-CBSE access. */
    const subjects = ["English", "Maths", "Science"];
    const user = {
      role: "student",
      accessCbse: true,
      cbseSubjects: [],
    };

    expect(filterAllowedSubjects(user, subjects, "CBSE")).toEqual(subjects);
  });

  test("allows the QA test student to access every subject", () => {
    /** An account flagged is_test_account is intentionally unrestricted. */
    const user = {
      role: "student",
      username: "akshita.teststudent",
      isTestAccount: true,
      accessCbse: false,
      cbseSubjects: ["Science"],
    };

    expect(
      filterAllowedSubjects(user, ["English", "Maths", "Science"], "ICSE")
    ).toEqual(["English", "Maths", "Science"]);
  });

  test("parses comma and newline subject lists without duplicates", () => {
    expect(parseSubjectList("Science, Maths\nscience")).toEqual([
      "Science",
      "Maths",
    ]);
  });
});

describe("hasCbseSubjectAccess — Grade 11/12 stream derivation", () => {
  const streamStudent = (stream) => ({
    role: "student",
    grade: "Grade 11",
    stream,
    cbseSubjects: [],
  });

  test("a recognized stream restricts subjects to that stream's list", () => {
    const user = streamStudent("PCM");
    expect(hasCbseSubjectAccess(user, "Physics")).toBe(true);
    expect(hasCbseSubjectAccess(user, "Biology")).toBe(false);
  });

  test("REGRESSION: an unrecognized stream value fails closed, not open", () => {
    // Before this fix, getSubjectsForStream() returning null for a mismatched
    // stream string caused hasCbseSubjectAccess() to fall through to "allow
    // every subject" instead of restricting — the fail direction was backwards.
    const user = streamStudent("pcm"); // lowercase — STREAM_SUBJECTS keys are exact-case
    expect(hasCbseSubjectAccess(user, "Physics")).toBe(false);
    expect(hasCbseSubjectAccess(user, "History")).toBe(false);
  });

  test("no stream chosen yet still allows all subjects (not a mismatch)", () => {
    const user = streamStudent(undefined);
    expect(hasCbseSubjectAccess(user, "Physics")).toBe(true);
    expect(hasCbseSubjectAccess(user, "History")).toBe(true);
  });

  test("getSubjectsForStream returns null for an unknown stream key", () => {
    expect(getSubjectsForStream("PCM")).toEqual(
      expect.arrayContaining(["Physics", "Chemistry", "Mathematics"])
    );
    expect(getSubjectsForStream("pcm")).toBeNull();
    expect(getSubjectsForStream("Not A Real Stream")).toBeNull();
  });
});
