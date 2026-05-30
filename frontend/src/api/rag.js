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

export async function uploadRagFilesBatch({
  username,
  grade,
  subject,
  chapter,
  titles,
  files,
}) {
  const formData = new FormData();

  formData.append("username", username);
  formData.append("grade", grade);
  formData.append("subject", subject);
  formData.append("chapter", chapter);
  formData.append("titles", titles);

  files.forEach((file) => {
    formData.append("files", file);
  });

  const response = await fetch(`${API_BASE_URL}/api/rag/upload-files`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error("Batch upload failed");
  }

  return response.json();
}

export async function getRagDocuments() {
  const response = await fetch(`${API_BASE_URL}/api/rag/documents`);

  if (!response.ok) {
    throw new Error("Failed to load RAG documents");
  }

  return response.json();
}


export async function deleteRagDocument(documentId) {
  const response = await fetch(
    `${API_BASE_URL}/api/rag/documents/${documentId}`,
    {
      method: "DELETE",
    }
  );

  if (!response.ok) {
    throw new Error("Failed to delete RAG document");
  }

  return response.json();
}

export async function analyzeRagImage(file) {
  const formData = new FormData();

  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/api/rag/analyze-image`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error("Failed to analyze image");
  }

  return response.json();
}

export async function analyzeSofImages({
  grade,
  files,
}) {
  const formData = new FormData();

  formData.append("grade", grade);

  files.forEach((file) => {
    formData.append("files", file);
  });

  const response = await fetch(
    `${API_BASE_URL}/api/rag/analyze-sof-images`,
    {
      method: "POST",
      body: formData,
    }
  );

  if (!response.ok) {
    throw new Error("SOF image analysis failed");
  }

  return response.json();
}


export async function confirmSofUpload({
  username,
  groups,
}) {
  const response = await fetch(
    `${API_BASE_URL}/api/rag/confirm-sof-upload`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        username,
        groups,
      }),
    }
  );

  if (!response.ok) {
    throw new Error("SOF upload failed");
  }

  return response.json();
}