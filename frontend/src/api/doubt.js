import { authFetch } from "./authClient";

export async function answerDoubt(payload) {
  /** Send an authenticated Ask Doubt request with optional subject/chapter context. */
  return authFetch("/api/doubt/answer", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function extractDoubtImage(file) {
  /** Upload one image for authenticated OCR extraction before asking a doubt. */
  const formData = new FormData();

  formData.append("file", file);

  return authFetch("/api/doubt/extract-image", {
    method: "POST",
    body: formData,
  });
}

export async function getDoubtHistory(limit = 20) {
  /** Load recent full Ask Doubt answers for the authenticated student. */
  return authFetch(`/api/doubt/history?limit=${limit}`);
}
