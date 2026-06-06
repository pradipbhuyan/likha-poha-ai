const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

function authHeaders(accessToken) {
  /** Build admin API headers with the current Supabase access token. */
  return {
    Authorization: `Bearer ${accessToken}`,
    "Content-Type": "application/json",
  };
}

async function parseError(response, fallbackMessage) {
  /** Prefer backend detail/message fields when surfacing admin API errors. */
  try {
    const data = await response.json();
    return data.detail || data.message || fallbackMessage;
  } catch {
    return fallbackMessage;
  }
}

async function adminFetch(path, options = {}) {
  /** Wrap admin fetches so backend-offline errors are actionable in the UI. */
  try {
    return await fetch(`${API_BASE_URL}${path}`, options);
  } catch (err) {
    throw new Error(
      `Cannot reach backend API at ${API_BASE_URL}. Start the FastAPI backend and try again.`
    );
  }
}

export async function getAdminFamilies(accessToken) {
  /** Load all families, parents, children, admins, and child activity summaries. */
  const response = await adminFetch("/api/admin-control/families", {
    headers: authHeaders(accessToken),
  });

  if (!response.ok) {
    throw new Error(await parseError(response, "Failed to load families"));
  }

  return response.json();
}

export async function createAdminParent(payload, accessToken) {
  /** Create a parent account/profile from the admin control page. */
  const response = await adminFetch("/api/admin-control/parents", {
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
  /** Create a student account/profile under an existing family. */
  const response = await adminFetch("/api/admin-control/children", {
    method: "POST",
    headers: authHeaders(accessToken),
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(await parseError(response, "Failed to create child"));
  }

  return response.json();
}

export async function createAdminTeacher(payload, accessToken) {
  /** Create a teacher login/profile from the admin control page. */
  const response = await adminFetch("/api/admin-control/teachers", {
    method: "POST",
    headers: authHeaders(accessToken),
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(await parseError(response, "Failed to create teacher"));
  }

  return response.json();
}

export async function assignTeacherStudent(payload, accessToken) {
  /** Link a teacher to a student for a grade/subject/section context. */
  const response = await adminFetch(
    "/api/admin-control/teacher-assignments",
    {
      method: "POST",
      headers: authHeaders(accessToken),
      body: JSON.stringify(payload),
    }
  );

  if (!response.ok) {
    throw new Error(await parseError(response, "Failed to assign student"));
  }

  return response.json();
}

export async function deleteTeacherAssignment(assignmentId, accessToken) {
  /** Remove one teacher-student assignment from the admin control page. */
  const response = await adminFetch(
    `/api/admin-control/teacher-assignments/${assignmentId}`,
    {
      method: "DELETE",
      headers: authHeaders(accessToken),
    }
  );

  if (!response.ok) {
    throw new Error(
      await parseError(response, "Failed to remove teacher assignment")
    );
  }

  return response.json();
}

export async function updateChildAccess(childId, payload, accessToken) {
  /** Save a student's subscription plan, status, and CBSE/SOF access flags. */
  const response = await adminFetch(
    `/api/admin-control/access/${childId}`,
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
  /** Save a student's daily and monthly token limits. */
  const response = await adminFetch(
    `/api/admin-control/limits/${childId}`,
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
  /** Delete a profile/auth user by id from the admin control page. */
  const response = await adminFetch(
    `/api/admin-control/users/${userId}`,
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
  /** Load editable subscription-plan settings for the admin pricing page. */
  const response = await adminFetch(
    "/api/admin-control/subscription-plans",
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
  /** Persist admin-edited subscription prices, discounts, access, and inclusions. */
  const response = await adminFetch(
    "/api/admin-control/subscription-plans",
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

export async function getAdminSubscriptionContact(accessToken) {
  /** Load editable subscription support contact settings for the admin pricing page. */
  const response = await adminFetch(
    "/api/admin-control/subscription-contact",
    {
      headers: authHeaders(accessToken),
    }
  );

  if (!response.ok) {
    throw new Error(
      await parseError(response, "Failed to load subscription contact settings")
    );
  }

  return response.json();
}

export async function updateAdminSubscriptionContact(payload, accessToken) {
  /** Persist parent-facing support contact settings for subscriptions. */
  const response = await adminFetch(
    "/api/admin-control/subscription-contact",
    {
      method: "PUT",
      headers: authHeaders(accessToken),
      body: JSON.stringify(payload),
    }
  );

  if (!response.ok) {
    throw new Error(
      await parseError(response, "Failed to save subscription contact settings")
    );
  }

  return response.json();
}
