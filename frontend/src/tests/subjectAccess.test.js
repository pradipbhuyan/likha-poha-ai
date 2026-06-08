import { describe, expect, test } from "vitest";

import {
  filterAllowedSubjects,
  parseSubjectList,
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
    /** akshita.teststudent is intentionally unrestricted for test coverage. */
    const user = {
      role: "student",
      username: "akshita.teststudent",
      accessCbse: false,
      accessSofScience: false,
      accessSofMaths: false,
      accessSofEnglish: false,
      cbseSubjects: ["Science"],
    };

    expect(
      filterAllowedSubjects(user, ["English", "Maths", "Science"], "ICSE")
    ).toEqual(["English", "Maths", "Science"]);
    expect(
      filterAllowedSubjects(
        user,
        ["Science Olympiad", "Maths Olympiad", "English Olympiad"],
        "SOF"
      )
    ).toEqual(["Science Olympiad", "Maths Olympiad", "English Olympiad"]);
  });

  test("parses comma and newline subject lists without duplicates", () => {
    expect(parseSubjectList("Science, Maths\nscience")).toEqual([
      "Science",
      "Maths",
    ]);
  });
});
