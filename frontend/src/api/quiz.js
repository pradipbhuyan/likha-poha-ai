const API_BASE_URL = "http://localhost:8000";

export async function generateQuiz(payload) {
  const response = await fetch(`${API_BASE_URL}/api/quiz/generate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error("Failed to generate quiz");
  }

  return response.json();
}