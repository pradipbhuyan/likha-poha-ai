const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export async function saveWeakAreaAlert(accessToken, payload) {
  /** Save a weak-area alert after repeated low practice performance. */
  const response = await fetch(
    `${API_BASE_URL}/api/weak-area-alerts/save`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify(payload),
    }
  );

  if (!response.ok) {
    throw new Error("Failed to save weak area alert");
  }

  return response.json();
}
