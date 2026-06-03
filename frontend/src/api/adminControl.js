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

export async function getAdminFamilies(accessToken) {
  const response = await fetch(`${API_BASE_URL}/api/admin-control/families`, {
    headers: authHeaders(accessToken),
  });

  if (!response.ok) {
    throw new Error(await parseError(response, "Failed to load families"));
  }

  return response.json();
}

export async function createAdminParent(payload, accessToken) {
  const response = await fetch(`${API_BASE_URL}/api/admin-control/parents`, {
    method: "POST",
    headers: authHeaders(accessToken),
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(await parseError(response, "Failed to create parent"));
  }

  return response.json();
}

export async function createAdminChild(payload, accessToken) {
  const response = await fetch(`${API_BASE_URL}/api/admin-control/children`, {
    method: "POST",
    headers: authHeaders(accessToken),
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(await parseError(response, "Failed to create child"));
  }

  return response.json();
}

export async function updateChildAccess(childId, payload, accessToken) {
  const response = await fetch(
    `${API_BASE_URL}/api/admin-control/access/${childId}`,
    {
      method: "PATCH",
      headers: authHeaders(accessToken),
      body: JSON.stringify(payload),
    }
  );

  if (!response.ok) {
    throw new Error(await parseError(response, "Failed to update access"));
  }

  return response.json();
}

export async function updateChildLimits(childId, payload, accessToken) {
  const response = await fetch(
    `${API_BASE_URL}/api/admin-control/limits/${childId}`,
    {
      method: "PATCH",
      headers: authHeaders(accessToken),
      body: JSON.stringify(payload),
    }
  );

  if (!response.ok) {
    throw new Error(await parseError(response, "Failed to update limits"));
  }

  return response.json();
}

export async function deleteUser(userId, accessToken) {
  const response = await fetch(
    `${API_BASE_URL}/api/admin-control/users/${userId}`,
    {
      method: "DELETE",
      headers: authHeaders(accessToken),
    }
  );

  if (!response.ok) {
    throw new Error(await parseError(response, "Failed to delete user"));
  }

  return response.json();
}

export async function getAdminSubscriptionPlans(accessToken) {
  const response = await fetch(
    `${API_BASE_URL}/api/admin-control/subscription-plans`,
    {
      headers: authHeaders(accessToken),
    }
  );

  if (!response.ok) {
    throw new Error(
      await parseError(response, "Failed to load subscription plans")
    );
  }

  return response.json();
}

export async function updateAdminSubscriptionPlans(payload, accessToken) {
  const response = await fetch(
    `${API_BASE_URL}/api/admin-control/subscription-plans`,
    {
      method: "PUT",
      headers: authHeaders(accessToken),
      body: JSON.stringify(payload),
    }
  );

  if (!response.ok) {
    throw new Error(
      await parseError(response, "Failed to save subscription plans")
    );
  }

  return response.json();
}
