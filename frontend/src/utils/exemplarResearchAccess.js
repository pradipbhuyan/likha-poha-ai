import { isAllAccessTestUser } from "./testAccounts";

/**
 * Return the Exemplar Research subjects available for a grade, filtered by
 * academic stream for Grade 11/12 (this page only has Science content).
 */
export function getSubjectsForGrade(grade, user) {
  if (grade === "Grade 11" || grade === "Grade 12") {
    const all = ["Physics", "Chemistry", "Maths", "Biology"];
    // All-access QA test account — browses every grade/stream's content.
    if (isAllAccessTestUser(user)) return all;

    const stream = (user?.stream || "").toUpperCase();
    if (stream === "PCM")  return ["Physics", "Chemistry", "Maths"];
    if (stream === "PCB")  return ["Physics", "Chemistry", "Biology"];
    if (stream === "PCMB") return ["Physics", "Chemistry", "Maths", "Biology"];
    // No stream chosen yet — show all rather than block a student who
    // hasn't completed that step (distinct from the case below).
    if (!stream) return all;
    // A real but non-Science stream (Commerce/Humanities) or any other
    // unrecognized value — Exemplar Research has no content for it, so
    // fail closed instead of showing all four Science subjects.
    return [];
  }
  return ["Maths", "Science"];
}
