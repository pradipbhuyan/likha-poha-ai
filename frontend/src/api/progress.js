const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  "http://localhost:8000";

export async function getChapterProgress(payload) {
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
  const response = await fetch(`${API_BASE_URL}/api/progress/user/${username}`);

  if (!response.ok) {
    throw new Error("Failed to load user progress");
  }

  return response.json();
}