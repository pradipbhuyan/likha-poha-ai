import { authFetch } from "./authClient";

export async function generateMockTest(payload) {
  /** Generate an authenticated CBSE mock test. */
  return authFetch("/api/mock-test/generate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
