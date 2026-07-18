import { supabase } from "./supabaseClient";

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
  /** Prefer backend detail/message fields when surfacing admin API errors.
   * Handles FastAPI 422 validation errors (detail is an array of objects)
   * and standard string error messages.
   */
  try {
    const data = await response.json();
    const detail = data.detail || data.message;
    if (!detail) return fallbackMessage;
    // FastAPI 422 — detail is an array of {loc, msg, type} validation errors
    if (Array.isArray(detail)) {
      return detail
        .map((e) => {
          const loc = Array.isArray(e.loc) ? e.loc.join(".") : String(e.loc || "");
          return `${loc}: ${e.msg || e.type || JSON.stringify(e)}`;
        })
        .join(" | ");
    }
    if (typeof detail === "string") return detail;
    // Object error (e.g. nested FastAPI error)
    return JSON.stringify(detail);
  } catch {
    return fallbackMessage;
  }
}

async function adminFetch(path, options = {}) {
  /**
   * Wrap admin fetches with automatic token refresh.
   *
   * Always retrieves a fresh Supabase session token so stale tokens from React
   * state (which go stale after inactivity) never cause "Unable to load admin
   * control data" errors. The passed accessToken in options.headers is replaced
   * with the freshly-obtained one.
   */
  let freshToken = null;
  try {
    const { data } = await supabase.auth.getSession();
    freshToken = data.session?.access_token;
    if (!freshToken) {
      const refreshed = await supabase.auth.refreshSession();
      freshToken = refreshed.data.session?.access_token;
    }
  } catch (_e) {
    // If session fetch fails, fall back to the token already in headers
  }

  const headers = {
    ...(options.headers || {}),
    ...(freshToken ? { Authorization: `Bearer ${freshToken}` } : {}),
  };

  try {
    return await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
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
  /** Save a student's subscription plan, status, and CBSE access flags. */
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

export async function reactivateOfferCode(codeId, accessToken) {
/** Reactivate a previously deactivated offer code. */
  const response = await adminFetch(
    `/api/admin-control/offer-codes/${codeId}/reactivate`,
    {
      method: "PATCH",
      headers: authHeaders(accessToken),
    }
  );

  if (!response.ok) {
    throw new Error(await parseError(response, "Failed to reactivate offer code"));
  }

  return response.json();
}

export async function extendOfferCodeValidity(codeId, validUntil, accessToken) {
  /**
   * Extend the valid_until date for an offer code and cascade to all redemptions.
   * validUntil: ISO string e.g. "2026-12-31T23:59:59"
   */
  const response = await adminFetch(
    `/api/admin-control/offer-codes/${codeId}/extend-validity`,
    {
      method: "PATCH",
      headers: { ...authHeaders(accessToken), "Content-Type": "application/json" },
      body: JSON.stringify({ valid_until: validUntil }),
    }
  );

  if (!response.ok) {
    throw new Error(await parseError(response, "Failed to extend offer code validity"));
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
   *
   * NOTE: must use the absolute API base URL — relative /api/ paths are
   * caught by Vercel's catch-all rewrite and return the React app HTML.
   */
  const response = await fetch(`${API_BASE_URL}/api/offer/redeem`, {
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
   *
   * NOTE: must use the absolute API base URL (same Vercel rewrite reason).
   */
  const response = await fetch(`${API_BASE_URL}/api/offer/my-access`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });

  if (!response.ok) return { has_offer_access: false, valid_until: null };
  return response.json();
}

export async function getLessonCardSettings(accessToken) {
  /** Load the active lesson card style and colour theme for the admin console. */
  const response = await adminFetch("/api/admin-control/lesson-card-settings", {
    headers: authHeaders(accessToken),
  });
  if (!response.ok) {
    throw new Error(await parseError(response, "Failed to load lesson card settings"));
  }
  return response.json();
}

export async function updateLessonCardSettings(payload, accessToken) {
  /** Persist the active lesson card style ("default"|"A"|"B"|"C") and theme ("brand"|"forest"). */
  const response = await adminFetch("/api/admin-control/lesson-card-settings", {
    method: "PUT",
    headers: authHeaders(accessToken),
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(await parseError(response, "Failed to save lesson card settings"));
  }
  return response.json();
}

export async function adminOfferGateTest(payload, accessToken) {
  /** Toggle offer-gate mode on a test user without touching Supabase directly.
   *  payload: { username: string, action: "enable"|"disable"|"status" }
   */
  const response = await adminFetch("/api/admin-control/offer-gate-test", {
    method: "POST",
    headers: authHeaders(accessToken),
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(await parseError(response, `Offer gate test failed (${response.status})`));
  }
  return response.json();
}

export async function getEgressHealth(accessToken) {
  /** Estimate Supabase DB egress from ai_usage_logs (last 30 days).
   *  Returns: { status: "green"|"yellow"|"red", estimated_gb, pct_of_free_limit,
   *             message, top_features, total_calls_30d }
   */
  const response = await adminFetch("/api/admin-control/egress-health", {
    headers: authHeaders(accessToken),
  });
  if (!response.ok) return null;
  return response.json();
}
