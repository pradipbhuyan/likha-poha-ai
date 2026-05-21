const API_BASE_URL = "http://localhost:8000";

export async function generateLesson(payload) {
  const response = await fetch(`${API_BASE_URL}/api/lesson/generate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error("Failed to generate lesson");
  }

  return response.json();
}