import { isAllAccessTestUser } from "./testAccounts";

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
  if (isAllAccessTestUser(user)) return true;

  const allowedSubjects = user?.cbseSubjects || [];

  if (!allowedSubjects.length) return true;

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
    // Offer-code users have accessCbse=false. The backend server-side gate
    // (DKB-only for doubts, cache-only for lessons) is the real access control.
    // The frontend should always show CBSE subjects for free-plan users so
    // they can browse and generate lessons — don't block on the frontend.
    //
    // We only hide subjects when access_cbse=false AND the user has a non-free
    // paid plan (which would be a misconfiguration — show nothing rather than
    // serving content they haven't paid for).
    const hasPaidPlan = user?.subscriptionPlan && user.subscriptionPlan !== "free";
    if (user?.accessCbse === false && !user?.offerAccess && hasPaidPlan) return [];
    if (user?.accessCbse === false && !user?.offerAccess && !hasPaidPlan) {
      // Free-plan student with access_cbse=false — offer-code user.
      // Show all CBSE subjects; server enforces DKB/cache-only gate.
      return allSubjects;
    }
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
