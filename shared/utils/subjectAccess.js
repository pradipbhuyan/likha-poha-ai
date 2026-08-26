import { isAllAccessTestUser } from "./testAccounts";

/** Map stream key → subjects shown in Grade 11/12 lesson selector
 *  @type {Record<string, string[]>} */
export const STREAM_SUBJECTS = {
  PCM:        ["Physics", "Chemistry", "Mathematics", "English", "Hindi"],
  PCB:        ["Physics", "Chemistry", "Biology", "English", "Hindi"],
  PCMB:       ["Physics", "Chemistry", "Mathematics", "Biology", "English", "Hindi"],
  Commerce:   ["Mathematics", "Business Studies", "Accountancy", "Economics", "English", "Hindi"],
  Humanities: ["History", "Geography", "Political Science", "Sociology", "English", "Hindi"],
};

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

export function getSubjectsForStream(stream) {
  /** Return the subject list for a given stream key. Returns null if unknown. */
  if (!stream) return null;
  return STREAM_SUBJECTS[stream] || null;
}

export function hasCbseSubjectAccess(user, subjectName) {
  /** Empty cbseSubjects means all CBSE subjects are allowed — unless stream is set for Grade 11/12. */
  if (isAllAccessTestUser(user)) return true;

  const allowedSubjects = user?.cbseSubjects || [];

  // For Grade 11/12: if cbseSubjects is empty but stream is set, derive from stream
  if (!allowedSubjects.length) {
    const grade = (user?.grade || "").toLowerCase();
    const isUpperSecondary = grade === "grade 11" || grade === "grade 12";
    if (isUpperSecondary && user?.stream) {
      const streamSubjects = getSubjectsForStream(user.stream);
      if (streamSubjects) {
        const subjectKey = normalizeSubjectName(subjectName);
        return streamSubjects.some(s => normalizeSubjectName(s) === subjectKey);
      }
      // Stream was set but doesn't match a known stream (STREAM_SUBJECTS is an
      // exact, case-sensitive match) — fail closed instead of showing every
      // subject across all streams. A grade 11/12 student with no stream at
      // all still falls through to the permissive `return true` below.
      return false;
    }
    return true;
  }

  const subjectKey = normalizeSubjectName(subjectName);

  return allowedSubjects.some(
    (allowedSubject) => normalizeSubjectName(allowedSubject) === subjectKey
  );
}

export function isSchoolBoardMode(selectedMode) {
  /** Return true for school-board modes that share subject-access controls. */
  return ["CBSE", "ICSE", "State Board"].includes(selectedMode);
}

export function filterAllowedSubjects(user, allSubjects, selectedMode) {
  /** Apply subscription and custom CBSE subject access to a subject list. */
  if (user?.role === "admin" || isAllAccessTestUser(user)) return allSubjects;

  if (isSchoolBoardMode(selectedMode)) {
    // Always filter by hasCbseSubjectAccess first — it applies stream-based
    // subject filtering for Grade 11/12 students regardless of subscription.
    // For free/offer-code users (accessCbse=false), the server enforces
    // DKB-only gates; the frontend still restricts to enrolled subjects.
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
