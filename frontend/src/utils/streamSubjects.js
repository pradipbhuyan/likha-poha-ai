/**
 * Stream → Subject mapping for Grade 11 & 12 CBSE.
 * These streams apply identically to both Grade 11 and Grade 12.
 *
 * Used by:
 *   - SignupPage      → stream picker for self-signup students
 *   - ParentDashboardPage → stream picker in Add Child modal
 *   - AdminControlPage    → stream shortcut for admin student editing
 *
 * When a stream is chosen, the listed subjects are saved to
 * cbse_subjects on the student profile.  The existing
 * hasCbseSubjectAccess() / filterAllowedSubjects() logic then
 * automatically restricts the Lessons / Doubt / Mock-test dropdowns.
 */

export const GRADE_11_12_STREAMS = [
  "Science (PCM)",
  "Science (PCB)",
  "Science (PCMB)",
  "Commerce",
  "Arts / Humanities",
];

/** Subjects included in each stream (always visible to the student). */
export const STREAM_SUBJECTS = {
  "Science (PCM)": [
    "Physics",
    "Chemistry",
    "Mathematics",
    "English",
    "Hindi",
  ],
  "Science (PCB)": [
    "Physics",
    "Chemistry",
    "Biology",
    "English",
    "Hindi",
  ],
  "Science (PCMB)": [
    "Physics",
    "Chemistry",
    "Mathematics",
    "Biology",
    "English",
    "Hindi",
  ],
  "Commerce": [
    "Accountancy",
    "Business Studies",
    "Economics",
    "Mathematics",
    "English",
    "Hindi",
  ],
  "Arts / Humanities": [
    "History",
    "Geography",
    "Political Science",
    "Sociology",
    "English",
    "Hindi",
  ],
};

/** Return true when the grade needs stream selection. */
export function isStreamGrade(grade) {
  return grade === "Grade 11" || grade === "Grade 12";
}

/**
 * Return the cbse_subjects array for a given stream.
 * Falls back to [] (all subjects) when stream is unrecognised.
 */
export function getSubjectsForStream(stream) {
  return STREAM_SUBJECTS[stream] || [];
}
