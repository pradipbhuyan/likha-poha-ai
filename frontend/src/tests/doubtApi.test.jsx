import { describe, expect, test, vi } from "vitest";

import { authFetch } from "../api/authClient";
import { answerDoubt } from "../api/doubt";

vi.mock("../api/authClient", () => ({
  authFetch: vi.fn(async () => ({ success: true })),
}));

describe("answerDoubt", () => {
  test("uses authenticated API client for protected doubt endpoint", async () => {
    const payload = {
      username: "student_one",
      grade: "Grade 9",
      mode: "CBSE",
      subject: "",
      chapter: "",
      question: "What is matter?",
    };

    await answerDoubt(payload);

    expect(authFetch).toHaveBeenCalledWith("/api/doubt/answer", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  });
});
