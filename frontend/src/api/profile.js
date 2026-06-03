import API_BASE_URL from "./client";

export async function logStudentActivity({
  username,
  activity_type,
}) {
  /** Record one gamified student activity such as lesson completion or test. */
  const response = await fetch(
    `${API_BASE_URL}/api/profile/activity`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        username,
        activity_type,
      }),
    }
  );

  if (!response.ok) {
    throw new Error("Failed to log student activity");
  }

  return response.json();
}

export async function getStudentProfile(username) {
  /** Load gamified profile counters, XP, level, rank, and streak details. */
  const response = await fetch(
    `${API_BASE_URL}/api/profile/${username}`
  );

  if (!response.ok) {
    throw new Error("Failed to load student profile");
  }

  return response.json();
}
