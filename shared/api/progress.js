const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  "http://localhost:8000";

export async function getChapterProgress(payload) {
  /** Load saved lesson progress for one chapter selection. */
  const response = await fetch(`${API_BASE_URL}/api/progress/chapter`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error("Failed to load progress");
  }

  return response.json();
}

export async function saveChapterProgress(payload) {
  /** Save current step, unlock state, completion flag, and cached lesson text. */
  const response = await fetch(`${API_BASE_URL}/api/progress/save`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error("Failed to save progress");
  }

  return response.json();
}

export async function getUserProgress(username) {
  /** Load all saved chapter progress for one student. */
  const response = await fetch(`${API_BASE_URL}/api/progress/user/${username}`);

  if (!response.ok) {
    throw new Error("Failed to load user progress");
  }

  return response.json();
}
