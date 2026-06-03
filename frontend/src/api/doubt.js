import { authFetch } from "./authClient";

export async function answerDoubt(payload) {
  return authFetch("/api/doubt/answer", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
