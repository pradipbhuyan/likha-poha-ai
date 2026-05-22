const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  "http://localhost:8000";

export async function getSyllabus() {
  const response = await fetch(`${API_BASE_URL}/api/syllabus`);

  if (!response.ok) {
    throw new Error("Failed to load syllabus");
  }

  return response.json();
}