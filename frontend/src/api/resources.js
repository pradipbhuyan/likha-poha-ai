const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  "http://localhost:8000";

export async function getResources(subject, chapter, grade = "Grade 9") {
  /** Load curated free learning resources for one subject/chapter pair. */
  const params = new URLSearchParams({
    grade,
    subject,
    chapter,
  });

  const response = await fetch(`${API_BASE_URL}/api/resources?${params.toString()}`);

  if (!response.ok) {
    throw new Error("Failed to load resources");
  }

  return response.json();
}
