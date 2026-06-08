const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

function authHeaders(accessToken) {
  return {
    Authorization: `Bearer ${accessToken}`,
    "Content-Type": "application/json",
  };
}

async function parseError(response, fallbackMessage) {
  try {
    const data = await response.json();
    return data.detail || data.message || fallbackMessage;
  } catch {
    return fallbackMessage;
  }
}

export async function getOnboardingGuideSettings() {
  /** Load public guide settings used by the role-aware first-time overlay. */
  const response = await fetch(`${API_BASE_URL}/api/onboarding-guide/settings`);

  if (!response.ok) {
    throw new Error(
      await parseError(response, "Failed to load onboarding guide settings")
    );
  }

  return response.json();
}

export async function updateOnboardingGuideSettings(payload, accessToken) {
  /** Persist admin-configured onboarding guide theme settings. */
  const response = await fetch(`${API_BASE_URL}/api/onboarding-guide/settings`, {
    method: "PUT",
    headers: authHeaders(accessToken),
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(
      await parseError(response, "Failed to save onboarding guide settings")
    );
  }

  return response.json();
}
