export function getDefaultGrade(syllabusData, preferredGrade = "Grade 9") {
  /** Pick a stable default grade while allowing Class 1-10 syllabus expansion. */
  const grades = Object.keys(syllabusData || {});

  if (grades.includes(preferredGrade)) {
    return preferredGrade;
  }

  return grades[0] || "";
}

export function getDefaultSelection(
  syllabusData,
  preferredGrade = "Grade 9",
  preferredMode = "CBSE"
) {
  /** Return a valid grade/mode/subject/chapter selection for any syllabus tree. */
  const grade = getDefaultGrade(syllabusData, preferredGrade);
  const gradeData = syllabusData?.[grade] || {};
  const modes = Object.keys(gradeData);
  const mode = modes.includes(preferredMode)
    ? preferredMode
    : modes.includes("CBSE")
      ? "CBSE"
      : modes[0] || "";
  const subjectData = gradeData?.[mode] || {};
  const subject = Object.keys(subjectData)[0] || "";
  const chapter = subjectData?.[subject]?.[0] || "";

  return {
    grade,
    mode,
    subject,
    chapter,
  };
}

export function getUserBoard(user, fallbackBoard = "CBSE") {
  /** Normalize the school board stored on a student profile. */
  const rawBoard = user?.board || user?.schoolBoard || user?.school_board;

  if (!rawBoard) {
    return fallbackBoard;
  }

  const text = String(rawBoard).trim().toLowerCase();

  if (text === "cbse") {
    return "CBSE";
  }

  if (text === "icse") {
    return "ICSE";
  }

  if (text === "state" || text === "state board") {
    return "State Board";
  }

  return rawBoard;
}

export function getUserGrade(user, fallbackGrade = "Grade 9") {
  /** Normalize the grade stored on a student profile into the app's Grade N label. */
  const rawGrade = user?.grade || user?.studentGrade || user?.class_grade;

  if (!rawGrade) {
    return fallbackGrade;
  }

  const text = String(rawGrade).trim();
  const gradeMatch = text.match(/\d+/);

  if (gradeMatch) {
    return `Grade ${Number(gradeMatch[0])}`;
  }

  return text;
}

export function getVisibleGrades(syllabusData, user) {
  /** Restrict student-facing grade dropdowns to the student's onboarded grade. */
  const allGrades = Object.keys(syllabusData || {});

  if (user?.role !== "student") {
    return allGrades;
  }

  const studentGrade = getUserGrade(user);

  if (allGrades.includes(studentGrade)) {
    return [studentGrade];
  }

  return allGrades.includes("Grade 9") ? ["Grade 9"] : allGrades.slice(0, 1);
}
