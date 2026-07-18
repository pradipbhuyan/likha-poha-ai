/**
 * Full-label stream picker for Grade 11 & 12 CBSE, used by:
 *   - AdminControlPage → "stream shortcut" that auto-fills subject checkboxes
 *
 * This is a UI-only concern (display labels like "Science (PCM)" for a
 * <select>) layered on top of the canonical short-code STREAM_SUBJECTS in
 * shared/utils/subjectAccess.js (imported here as CANONICAL_STREAM_SUBJECTS)
 * — that is the single source of truth for which subjects belong to which
 * stream. Do NOT hand-duplicate subject lists here; add new streams/subjects
 * to the canonical map and extend LABEL_TO_CODE below.
 *
 * When a stream is chosen, the listed subjects are saved to cbse_subjects on
 * the student profile. The existing hasCbseSubjectAccess() /
 * filterAllowedSubjects() logic then automatically restricts the
 * Lessons / Doubt / Mock-test dropdowns.
 */
import { STREAM_SUBJECTS as CANONICAL_STREAM_SUBJECTS } from "./subjectAccess";

/** Full display label → canonical short stream code. */
const LABEL_TO_CODE = {
  "Science (PCM)": "PCM",
  "Science (PCB)": "PCB",
  "Science (PCMB)": "PCMB",
  "Commerce": "Commerce",
  "Arts / Humanities": "Humanities",
};

export const GRADE_11_12_STREAMS = Object.keys(LABEL_TO_CODE);

/** Subjects included in each stream (always visible to the student). */
export const STREAM_SUBJECTS = Object.fromEntries(
  Object.entries(LABEL_TO_CODE).map(([label, code]) => [
    label,
    CANONICAL_STREAM_SUBJECTS[code] || [],
  ])
);

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
