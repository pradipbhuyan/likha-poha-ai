import { authFetch } from "./authClient";

export async function getBoardPapersOverview(grade) {
  /** Every year + subject + paper for this grade in one request — replaces
   * the old fan-out of one /years + one /subjects + one /list call per
   * visible year, which meant a single dropped request left that year's
   * row stuck loading forever with no retry. */
  const qs = new URLSearchParams({ grade }).toString();
  return authFetch(`/api/board-papers/overview?${qs}`);
}

export async function listBoardPaperYears(grade) {
  /** Distinct academic years available for a grade. */
  const qs = new URLSearchParams({ grade }).toString();
  return authFetch(`/api/board-papers/years?${qs}`);
}

export async function listBoardPaperSubjects(grade, academicYear) {
  /** Distinct subjects available for a grade + year. */
  const qs = new URLSearchParams({ grade, academic_year: academicYear }).toString();
  return authFetch(`/api/board-papers/subjects?${qs}`);
}

export async function listBoardPapers({ grade, subject, academicYear }) {
  /** List paper metadata, filterable by subject / academic year. */
  const params = { grade };
  if (subject) params.subject = subject;
  if (academicYear) params.academic_year = academicYear;
  const qs = new URLSearchParams(params).toString();
  return authFetch(`/api/board-papers/list?${qs}`);
}

export async function getBoardPaperQuestions(paperId, grade) {
  /** Full question set (with answers, once status=answered) for one paper. */
  const qs = new URLSearchParams({ grade }).toString();
  return authFetch(`/api/board-papers/${paperId}/questions?${qs}`);
}

export async function submitBoardPaperAttempt(paperId, attempt) {
  /** Persist one Timed Test attempt. Scoring is computed client-side (MCQ
   * auto-graded, subjective self-marked) — this just records the result. */
  return authFetch(`/api/board-papers/${paperId}/attempts`, {
    method: "POST",
    body: JSON.stringify(attempt),
  });
}

export async function listBoardPaperAttempts(paperId) {
  /** This user's past Timed Test attempts for one paper, most recent first. */
  return authFetch(`/api/board-papers/${paperId}/attempts`);
}
