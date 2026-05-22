const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  "http://localhost:8000";

export async function generateSpeech(payload) {
  const response = await fetch(`${API_BASE_URL}/api/tts/generate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error("Failed to generate speech");
  }

  const blob = await response.blob();
  return URL.createObjectURL(blob);
}