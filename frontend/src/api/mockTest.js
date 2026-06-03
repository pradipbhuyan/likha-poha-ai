import { authFetch } from "./authClient";

export async function generateMockTest(payload) {
  return authFetch("/api/mock-test/generate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
