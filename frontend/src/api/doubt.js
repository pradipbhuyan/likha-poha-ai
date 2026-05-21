const API_BASE_URL = "http://localhost:8000";

export async function answerDoubt(payload) {
  const response = await fetch(`${API_BASE_URL}/api/doubt/answer`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error("Failed to answer doubt");
  }

  return response.json();
}