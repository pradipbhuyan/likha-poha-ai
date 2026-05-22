const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  "http://localhost:8000";

export async function getResources(subject, chapter) {
  const params = new URLSearchParams({
    subject,
    chapter,
  });

  const response = await fetch(`${API_BASE_URL}/api/resources?${params.toString()}`);

  if (!response.ok) {
    throw new Error("Failed to load resources");
  }

  return response.json();
}