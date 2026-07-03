const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  "http://localhost:8000";

export async function generateSpeech(payload) {
  /** Generate lesson audio and return a browser object URL for playback. */
  const response = await fetch(`${API_BASE_URL}/api/tts/generate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error("Failed to generate speech");
  }

  const blob = await response.blob();
  return URL.createObjectURL(blob);
}

/**
 * Check if pre-warmed audio exists for a lesson step.
 * Returns { cached: true, url: "https://..." } or { cached: false }.
 *
 * If cached=true, the URL points directly to Supabase CDN — instant playback
 * with no Edge TTS generation delay.
 */
export async function getCachedAudioUrl({ grade, subject, chapter, stepTitle }) {
  try {
    const params = new URLSearchParams({
      grade,
      subject,
      chapter,
      step_title: stepTitle,
    });
    const response = await fetch(`${API_BASE_URL}/api/tts/cached-url?${params}`);
    if (!response.ok) return { cached: false };
    return await response.json();
  } catch {
    return { cached: false };
  }
}
