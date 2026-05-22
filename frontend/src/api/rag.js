const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  "http://localhost:8000";

export async function uploadRagFile({
  username,
  grade,
  subject,
  chapter,
  title,
  file,
}) {
  const formData = new FormData();

  formData.append("username", username);
  formData.append("grade", grade);
  formData.append("subject", subject);
  formData.append("chapter", chapter);
  formData.append("title", title);
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/api/rag/upload-file`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error("Failed to upload RAG file");
  }

  return response.json();
}