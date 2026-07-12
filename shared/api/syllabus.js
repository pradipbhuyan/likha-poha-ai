const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  "http://localhost:8000";

function authHeaders(accessToken) {
  /** Build headers for protected syllabus admin endpoints. */
  return {
    Authorization: `Bearer ${accessToken}`,
    "Content-Type": "application/json",
  };
}

async function parseError(response, fallbackMessage) {
  /** Return a useful backend error message when available. */
  try {
    const data = await response.json();
    return data.detail || data.message || fallbackMessage;
  } catch {
    return fallbackMessage;
  }
}

export async function getSyllabus() {
  /** Load the syllabus tree and lesson-step labels used across learning pages. */
  const response = await fetch(`${API_BASE_URL}/api/syllabus`);

  if (!response.ok) {
    throw new Error("Failed to load syllabus");
  }

  return response.json();
}

export async function getAdminSyllabusReview(accessToken) {
  /** Load effective dropdowns and saved overrides for admin validation. */
  const response = await fetch(`${API_BASE_URL}/api/syllabus/admin-review`, {
    headers: authHeaders(accessToken),
  });

  if (!response.ok) {
    throw new Error(await parseError(response, "Failed to load syllabus review"));
  }

  return response.json();
}

export async function saveAdminSyllabusOverride(payload, accessToken) {
  /** Save one admin-approved chapter dropdown list. */
  const response = await fetch(
    `${API_BASE_URL}/api/syllabus/admin-review/override`,
    {
      method: "POST",
      headers: authHeaders(accessToken),
      body: JSON.stringify(payload),
    }
  );

  if (!response.ok) {
    throw new Error(await parseError(response, "Failed to save syllabus dropdown"));
  }

  return response.json();
}

export async function saveAdminSubjectOverride(payload, accessToken) {
  /** Save the admin-approved visible subject list for one grade/mode. */
  const response = await fetch(
    `${API_BASE_URL}/api/syllabus/admin-review/subjects`,
    {
      method: "POST",
      headers: authHeaders(accessToken),
      body: JSON.stringify(payload),
    }
  );

  if (!response.ok) {
    throw new Error(await parseError(response, "Failed to save subject list"));
  }

  return response.json();
}
