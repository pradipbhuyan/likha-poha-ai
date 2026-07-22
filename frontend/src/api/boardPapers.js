import { authFetch } from "./authClient";

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
