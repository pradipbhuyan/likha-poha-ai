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

export async function getAiSettings(accessToken) {
  /** Load the master API switch state and active key prefix for the admin console. */
  const response = await adminFetch("/api/admin-control/ai-settings", {
    headers: authHeaders(accessToken),
  });

  if (!response.ok) {
    throw new Error(await parseError(response, "Failed to load AI settings"));
  }

  return response.json();
}

export async function updateAiSettings(payload, accessToken) {
  /**
   * Persist the master API on/off switch and optionally a new OpenAI API key.
   * payload: { api_enabled: bool, openai_api_key?: string }
   */
  const response = await adminFetch("/api/admin-control/ai-settings", {
    method: "PUT",
    headers: authHeaders(accessToken),
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(await parseError(response, "Failed to save AI settings"));
  }

  return response.json();
}

// ─── Create Student (standalone, no parent required) ────────────────────────

export async function createAdminStudent(payload, accessToken) {
  /**
   * Create a standalone student account from the admin panel.
   * payload: { email, username, password, grade, board, skip_email_confirmation,
   *            parent_id? (optional), family_id? (optional) }
   */
  const response = await adminFetch("/api/admin-control/children", {
    method: "POST",
    headers: authHeaders(accessToken),
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(await parseError(response, "Failed to create student"));
  }

  return response.json();
}

// ─── Offer Codes ─────────────────────────────────────────────────────────────

export async function listOfferCodes(accessToken) {
  /** List all offer codes for the admin panel. */
  const response = await adminFetch("/api/admin-control/offer-codes", {
    method: "GET",
    headers: authHeaders(accessToken),
  });

  if (!response.ok) {
    throw new Error(await parseError(response, "Failed to load offer codes"));
  }

  return response.json();
}

export async function createOfferCode(payload, accessToken) {
  /**
   * Create a new offer code.
   * payload: { description, valid_until (ISO string), max_uses, valid_from? }
   */
  const response = await adminFetch("/api/admin-control/offer-codes", {
    method: "POST",
    headers: authHeaders(accessToken),
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(await parseError(response, "Failed to create offer code"));
  }

  return response.json();
}

export async function deactivateOfferCode(codeId, accessToken) {
  /** Deactivate an offer code so it can no longer be redeemed. */
  const response = await adminFetch(
    `/api/admin-control/offer-codes/${codeId}/deactivate`,
    {
      method: "PATCH",
      headers: authHeaders(accessToken),
    }
  );

  if (!response.ok) {
    throw new Error(await parseError(response, "Failed to deactivate offer code"));
  }

  return response.json();
}

export async function getInfluencerSummary(accessToken) {
  /** Load per-influencer redemption stats and incentive totals. */
  const response = await adminFetch("/api/admin-control/offer-codes/influencer-summary", {
    method: "GET",
    headers: authHeaders(accessToken),
  });
  if (!response.ok) {
    throw new Error(await parseError(response, "Failed to load influencer summary"));
  }
  return response.json();
}

export async function markInfluencerIncentivePaid(codeId, accessToken) {
  /** Mark a specific offer code's influencer incentive as paid. */
  const response = await adminFetch(
    `/api/admin-control/offer-codes/${codeId}/mark-incentive-paid`,
    { method: "PATCH", headers: authHeaders(accessToken) }
  );
  if (!response.ok) {
    throw new Error(await parseError(response, "Failed to mark incentive as paid"));
  }
  return response.json();
}

export async function getAdminPaymentLogs(accessToken) {
  /** Load payment logs with revenue summary, trend data and plan distribution. */
  const response = await adminFetch("/api/admin-control/payment-logs", {
    method: "GET",
    headers: authHeaders(accessToken),
  });
  if (!response.ok) {
    throw new Error(await parseError(response, "Failed to load payment logs"));
  }
  return response.json();
}

export async function getOfferCodeEnrollments(accessToken) {
  /** Load all students enrolled per offer code for admin tracking. */
  const response = await adminFetch("/api/admin-control/offer-codes/enrollments", {
    method: "GET",
    headers: authHeaders(accessToken),
  });
  if (!response.ok) {
    throw new Error(await parseError(response, "Failed to load offer code enrollments"));
  }
  return response.json();
}

export async function regeneratePromoImages(payload, accessToken) {
  /**
   * Regenerate all WhatsApp promo images with the given offer code and
   * re-upload them to sales-collaterals/whatsapp/ in Supabase.
   * payload: { offer_code: string, valid_until?: string }
   * Returns { success, uploaded, files, errors }
   */
  const response = await adminFetch(
    "/api/admin-control/offer-codes/regenerate-promo-images",
    {
      method: "POST",
      headers: authHeaders(accessToken),
      body: JSON.stringify(payload),
    }
  );
  if (!response.ok) {
    throw new Error(await parseError(response, "Failed to regenerate promo images"));
  }
  return response.json();
}

// ─── Student: redeem offer code ──────────────────────────────────────────────

export async function redeemOfferCode(code, accessToken) {
  /**
   * Redeem an 8-char offer code for the currently logged-in user.
   * Returns { success, valid_until, message, already_redeemed }
   */
  const response = await fetch("/api/offer/redeem", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify({ code }),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || "Failed to redeem offer code");
  }

  return response.json();
}

export async function getMyOfferAccess(accessToken) {
  /**
   * Check if the current user has a valid (non-expired) offer redemption.
   * Returns { has_offer_access: bool, valid_until: string|null }
   */
  const response = await fetch("/api/offer/my-access", {
    headers: { Authorization: `Bearer ${accessToken}` },
  });

  if (!response.ok) return { has_offer_access: false, valid_until: null };
  return response.json();
}
