export const COMMON_CBSE_SUBJECTS = [
  "English",
  "Hindi",
  "Maths",
  "Science",
  "Social Science",
];

export function normalizeSubjectName(subject) {
  /** Normalize subject names for plan/access comparisons. */
  return String(subject || "").trim().replace(/\s+/g, " ").toLowerCase();
}

export function parseSubjectList(value) {
  /** Convert a comma/newline list into unique subject names. */
  const seen = new Set();

  return String(value || "")
    .split(/[,\n]/)
    .map((subject) => subject.trim())
    .filter((subject) => {
      const key = normalizeSubjectName(subject);

      if (!key || seen.has(key)) return false;
      seen.add(key);
      return true;
    });
}

export function hasCbseSubjectAccess(user, subjectName) {
  /** Empty cbseSubjects means all CBSE subjects are allowed. */
  const allowedSubjects = user?.cbseSubjects || [];

  if (!allowedSubjects.length) return true;

  const subjectKey = normalizeSubjectName(subjectName);

  return allowedSubjects.some(
    (allowedSubject) => normalizeSubjectName(allowedSubject) === subjectKey
  );
}

export function filterAllowedSubjects(user, allSubjects, selectedMode) {
  /** Apply subscription and custom CBSE subject access to a subject list. */
  if (user?.role === "admin") return allSubjects;

  if (selectedMode === "CBSE") {
    if (user?.accessCbse === false) return [];
    return allSubjects.filter((subjectName) =>
      hasCbseSubjectAccess(user, subjectName)
    );
  }

  if (selectedMode === "SOF") {
    return allSubjects.filter((subjectName) => {
      if (subjectName === "Science Olympiad") return user?.accessSofScience;
      if (subjectName === "Maths Olympiad") return user?.accessSofMaths;
      if (subjectName === "English Olympiad") return user?.accessSofEnglish;
      return false;
    });
  }

  return [];
}
