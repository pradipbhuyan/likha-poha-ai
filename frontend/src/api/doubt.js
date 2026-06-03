import { authFetch } from "./authClient";

export async function answerDoubt(payload) {
  return authFetch("/api/doubt/answer", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function extractDoubtImage(file) {
  const formData = new FormData();

  formData.append("file", file);

  return authFetch("/api/doubt/extract-image", {
    method: "POST",
    body: formData,
  });
}
