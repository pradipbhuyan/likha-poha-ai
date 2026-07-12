import { authFetch } from "./authClient";

export async function generateMockTest(payload) {
  /** Generate an authenticated CBSE or SOF mock test. */
  return authFetch("/api/mock-test/generate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
