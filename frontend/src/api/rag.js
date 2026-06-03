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
  /** Upload one file as one RAG document after extracting text server-side. */
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
  /** Upload up to 20 files as separate RAG documents in one request. */
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

export async function uploadBulkBooks({
  username,
  books,
}) {
  /** Upload Class 1-10 books with one metadata record per file. */
  const formData = new FormData();
  const metadata = books.map(({ file, ...book }) => book);

  formData.append("username", username);
  formData.append("metadata_json", JSON.stringify(metadata));

  books.forEach((book) => {
    formData.append("files", book.file);
  });

  const response = await fetch(`${API_BASE_URL}/api/rag/bulk-book-upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error("Bulk book upload failed");
  }

  return response.json();
}

export async function uploadBookSet({
  username,
  grade,
  subject,
  bookTitle,
  sectionTitles,
  files,
}) {
  /** Upload one book that is split into TOC/chapter files. */
  const formData = new FormData();

  formData.append("username", username);
  formData.append("grade", grade);
  formData.append("subject", subject);
  formData.append("book_title", bookTitle);
  formData.append("section_titles", sectionTitles);

  files.forEach((file) => {
    formData.append("files", file);
  });

  const response = await fetch(`${API_BASE_URL}/api/rag/book-set-upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error("Book set upload failed");
  }

  return response.json();
}

export async function analyzeBookSetFiles({
  files,
}) {
  /** Suggest TOC/chapter labels before uploading a multi-file book to RAG. */
  const formData = new FormData();

  files.forEach((file) => {
    formData.append("files", file);
  });

  const response = await fetch(`${API_BASE_URL}/api/rag/analyze-book-set`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error("Book set analysis failed");
  }

  return response.json();
}

export async function getRagDocuments() {
  /** Load metadata for uploaded RAG documents. */
  const response = await fetch(`${API_BASE_URL}/api/rag/documents`);

  if (!response.ok) {
    throw new Error("Failed to load RAG documents");
  }

  return response.json();
}


export async function deleteRagDocument(documentId) {
  /** Delete a RAG document and its chunks by document id. */
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
  /** OCR and classify one image before admin decides whether to upload it. */
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
  /** OCR and group SOF files into canonical subject/chapter upload groups. */
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
  /** Persist reviewed SOF upload groups into the RAG database. */
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

export async function searchRag({
  grade,
  subject,
  chapter,
  query,
  matchCount = 5,
}) {
  /** Run a manual RAG search for admin verification/debugging. */
  const response = await fetch(
    `${API_BASE_URL}/api/rag/search`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        grade,
        subject,
        chapter,
        query,
        match_count: matchCount,
      }),
    }
  );

  if (!response.ok) {
    throw new Error("RAG search failed");
  }

  return response.json();
}
