const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

/**
 * Fetch the active lesson section card style and colour theme.
 * Public endpoint — no auth required.
 * Returns { success, card_style, card_theme }
 * Defaults to { card_style: "default", card_theme: "brand" } on failure.
 */
export async function getLessonCardPublicSettings() {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/platform-settings/lesson-card`
    );
    if (!response.ok) return { card_style: "default", card_theme: "brand" };
    return response.json();
  } catch {
    return { card_style: "default", card_theme: "brand" };
  }
}
