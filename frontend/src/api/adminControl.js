const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

function authHeaders(accessToken) {
  return {
    Authorization: `Bearer ${accessToken}`,
    "Content-Type": "application/json",
  };
}

export async function getAdminFamilies(accessToken) {
    const response = await fetch(`${API_BASE_URL}/api/admin-control/families`, {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });
  
    if (!response.ok) {
      throw new Error("Failed to load families");
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
    throw new Error("Failed to update access");
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
    throw new Error("Failed to update limits");
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
    throw new Error("Failed to delete user");
  }

  return response.json();
}