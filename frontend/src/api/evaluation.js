const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export async function evaluateStudentAnswer(payload) {
  /** Send a written practice answer for AI evaluation and pass/retry scoring. */
  const response = await fetch(`${API_BASE_URL}/api/evaluation/evaluate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  return response.json();
}

export async function generatePracticeQuestions(payload) {
  /** Generate written-answer practice questions for the current lesson step. */
  const response = await fetch(`${API_BASE_URL}/api/evaluation/practice-questions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  return response.json();
}
