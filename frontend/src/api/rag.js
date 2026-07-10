const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  "http://localhost:8000";

function authHeaders(accessToken) {
  /** Build JSON headers for protected RAG admin endpoints. */
  return {
    Authorization: `Bearer ${accessToken}`,
    "Content-Type": "application/json",
  };
}

function authFormHeaders(accessToken) {
  /** Build auth-only headers for protected multipart/form-data endpoints. */
  return accessToken
    ? {
        Authorization: `Bearer ${accessToken}`,
      }
    : {};
}

async function parseError(response, fallbackMessage) {
  /** Prefer backend detail/message fields for admin-visible failures. */
  try {
    const data = await response.json();
    return data.detail || data.message || fallbackMessage;
  } catch {
    return fallbackMessage;
  }
}

export async function uploadRagFile({
  username,
  grade,
  board = "CBSE",
  subject,
  chapter,
  title,
  file,
}) {
  /** Upload one file as one RAG document after extracting text server-side. */
  const formData = new FormData();

  formData.append("username", username);
  formData.append("grade", grade);
  formData.append("board", board);
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
  board = "CBSE",
  subject,
  chapter,
  titles,
  files,
}) {
  /** Upload up to 20 files as separate RAG documents in one request. */
  const formData = new FormData();

  formData.append("username", username);
  formData.append("grade", grade);
  formData.append("board", board);
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
  board = "CBSE",
  subject,
  bookTitle,
  sectionTitles,
  files,
}) {
  /** Upload one book that is split into TOC/chapter files. */
  const formData = new FormData();

  formData.append("username", username);
  formData.append("grade", grade);
  formData.append("board", board);
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

export async function analyzeFullBookPdf({
  file,
  ocrScanned = false,
}) {
  /** Analyze one full PDF and suggest chapter page ranges before RAG upload. */
  const formData = new FormData();

  formData.append("ocr_scanned", String(ocrScanned));
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/api/rag/analyze-full-book`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error("Full book analysis failed");
  }

  return response.json();
}

export async function startFullBookAnalysisJob({
  file,
  ocrScanned = false,
  accessToken,
}) {
  /** Start background full-book analysis and return a pollable job id. */
  const formData = new FormData();

  formData.append("ocr_scanned", String(ocrScanned));
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/api/rag/jobs/analyze-full-book`, {
    method: "POST",
    headers: authFormHeaders(accessToken),
    body: formData,
  });

  if (!response.ok) {
    throw new Error(await parseError(response, "Full book analysis job failed"));
  }

  return response.json();
}

export async function uploadFullBookSections({
  username,
  grade,
  board = "CBSE",
  subject,
  bookTitle,
  chapters,
  ocrScanned = false,
  file,
}) {
  /** Upload reviewed full-book chapter ranges as separate RAG documents. */
  const formData = new FormData();

  formData.append("username", username);
  formData.append("grade", grade);
  formData.append("board", board);
  formData.append("subject", subject);
  formData.append("book_title", bookTitle);
  formData.append("chapters_json", JSON.stringify(chapters));
  formData.append("ocr_scanned", String(ocrScanned));
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/api/rag/upload-full-book-sections`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error("Full book chapter upload failed");
  }

  return response.json();
}

export async function startFullBookUploadJob({
  username,
  grade,
  board = "CBSE",
  subject,
  bookTitle,
  chapters,
  ocrScanned = false,
  file,
  accessToken,
}) {
  /** Start background full-book RAG chapter upload and embedding. */
  const formData = new FormData();

  formData.append("username", username);
  formData.append("grade", grade);
  formData.append("board", board);
  formData.append("subject", subject);
  formData.append("book_title", bookTitle);
  formData.append("chapters_json", JSON.stringify(chapters));
  formData.append("ocr_scanned", String(ocrScanned));
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/api/rag/jobs/upload-full-book-sections`, {
    method: "POST",
    headers: authFormHeaders(accessToken),
    body: formData,
  });

  if (!response.ok) {
    throw new Error(await parseError(response, "Full book chapter upload job failed"));
  }

  return response.json();
}

export async function getRagUploadJob(jobId, accessToken) {
  /** Poll one background RAG upload job. */
  const response = await fetch(`${API_BASE_URL}/api/rag/jobs/${jobId}`, {
    headers: authFormHeaders(accessToken),
  });

  if (!response.ok) {
    throw new Error(await parseError(response, "Failed to load RAG upload job"));
  }

  return response.json();
}

export async function getRagUploadJobs(accessToken) {
  /** Load recent background RAG upload jobs. */
  const response = await fetch(`${API_BASE_URL}/api/rag/jobs`, {
    headers: authFormHeaders(accessToken),
  });

  if (!response.ok) {
    throw new Error(await parseError(response, "Failed to load RAG upload jobs"));
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

export async function previewRagDocument(documentId, accessToken) {
  /** Load a short stored-content preview for one RAG document. */
  const response = await fetch(
    `${API_BASE_URL}/api/rag/documents/${documentId}/preview`,
    {
      headers: authHeaders(accessToken),
    }
  );

  if (!response.ok) {
    throw new Error(await parseError(response, "Failed to preview RAG document"));
  }

  return response.json();
}

export async function updateRagDocumentMetadata(documentId, payload, accessToken) {
  /** Save corrected RAG document title and chapter metadata. */
  const response = await fetch(
    `${API_BASE_URL}/api/rag/documents/${documentId}/metadata`,
    {
      method: "PATCH",
      headers: authHeaders(accessToken),
      body: JSON.stringify(payload),
    }
  );

  if (!response.ok) {
    throw new Error(await parseError(response, "Failed to update RAG metadata"));
  }

  return response.json();
}

export async function getRagDocumentVisuals(documentId, accessToken) {
  /** Load textbook page visuals linked to one RAG document. */
  const response = await fetch(
    `${API_BASE_URL}/api/rag/documents/${documentId}/visuals`,
    {
      headers: authFormHeaders(accessToken),
    }
  );

  if (!response.ok) {
    throw new Error(await parseError(response, "Failed to load textbook visuals"));
  }

  return response.json();
}

export async function backfillRagDocumentVisuals({
  documentId,
  file,
  startPage,
  endPage,
  accessToken,
}) {
  /** Upload source PDF pages and link rendered visuals to a RAG document. */
  const formData = new FormData();

  formData.append("file", file);

  if (startPage) {
    formData.append("start_page", String(startPage));
  }

  if (endPage) {
    formData.append("end_page", String(endPage));
  }

  const response = await fetch(
    `${API_BASE_URL}/api/rag/documents/${documentId}/visuals/backfill`,
    {
      method: "POST",
      headers: authFormHeaders(accessToken),
      body: formData,
    }
  );

  if (!response.ok) {
    throw new Error(await parseError(response, "Failed to extract textbook visuals"));
  }

  return response.json();
}

export async function updateRagVisualAsset(visualId, payload, accessToken) {
  /** Save review status/caption for one textbook visual asset. */
  const response = await fetch(`${API_BASE_URL}/api/rag/visuals/${visualId}`, {
    method: "PATCH",
    headers: authHeaders(accessToken),
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(await parseError(response, "Failed to update textbook visual"));
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
  board = "CBSE",
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
        board,
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

export async function uploadRagText({ username, grade, board, subject, chapter, title, text }, accessToken) {
  /** Upload plain text as a RAG document — embeddings generated server-side. */
  const response = await fetch(`${API_BASE_URL}/api/rag/upload-text`, {
    method: "POST",
    headers: authHeaders(accessToken),
    body: JSON.stringify({ username, grade, board, subject, chapter, title, text }),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || "RAG text upload failed");
  }
  return response.json();
}

// ── Lesson Prewarm — ChatGPT manual lesson import ─────────────────────────

export async function generatePrewarmPrompt(
  accessToken,
  { grade, subject, chapter, stepTitle, mode = "CBSE", board = "CBSE" }
) {
  const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
  const response = await fetch(`${API_BASE}/api/lesson/prewarm/prompt`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify({ grade, subject, chapter, step_title: stepTitle, mode, board }),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to generate prewarm prompt");
  }
  return response.json();
}

export async function storePrewarmLesson(
  accessToken,
  { grade, subject, chapter, stepTitle, lessonContent, mode = "CBSE", board = "CBSE", force = false }
) {
  const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
  const response = await fetch(`${API_BASE}/api/lesson/prewarm/store`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify({
      grade, subject, chapter, step_title: stepTitle,
      lesson_content: lessonContent, mode, board, force,
    }),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to store prewarm lesson");
  }
  return response.json();
}
