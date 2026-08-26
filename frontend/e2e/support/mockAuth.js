/**
 * Shared Playwright network mocks for the Supabase + backend calls made
 * during email/password login (see LoginPage.jsx's handleLogin/buildLoginUser
 * and App.jsx's handleLogin). Login is mocked at the network layer — rather
 * than the real Supabase project — so these E2E tests are deterministic and
 * don't depend on live credentials or mutate real auth/profile data.
 *
 * Route patterns match on path suffix only (not full origin), so they work
 * regardless of the Supabase project ref or API base URL configured locally.
 */

const FAKE_USER_ID = "00000000-0000-4000-8000-000000000001";

/** A `profiles` table row as returned by supabase-js `.from("profiles").select("*").eq("id", ...).single()`. */
function profileRow(overrides = {}) {
  return {
    id: FAKE_USER_ID,
    username: "e2e.user",
    role: "student",
    grade: "Grade 9",
    board: "CBSE",
    parent_id: null,
    family_id: null,
    access_cbse: false,
    is_test_account: false,
    access_sof_science: false,
    access_sof_maths: false,
    access_sof_english: false,
    cbse_subjects: [],
    stream: null,
    avatar: "",
    daily_token_limit: 50000,
    monthly_token_limit: 1000000,
    subscription_plan: "free",
    account_status: "active",
    ...overrides,
  };
}

/** The enriched-profile shape returned by backend `GET /api/auth/profile` (see App.jsx handleLogin). */
function authApiProfile(overrides = {}) {
  return {
    access_cbse: false,
    is_test_account: false,
    access_sof_science: false,
    access_sof_maths: false,
    access_sof_english: false,
    subscription_plan: "free",
    subscription_expires_at: null,
    subscription_days_remaining: null,
    subscription_expiring_soon: false,
    cbse_subjects: [],
    stream: null,
    daily_token_limit: 50000,
    monthly_token_limit: 1000000,
    account_status: "active",
    grade: "Grade 9",
    avatar: "",
    can_report_issues: true,
    ...overrides,
  };
}

/**
 * Registers page.route() intercepts covering the full email/password login
 * network sequence. Call this BEFORE navigating/submitting the login form.
 *
 * Pass `failure: { status, message }` to simulate a failed sign-in instead
 * (LoginPage maps well-known Supabase error strings to friendly text).
 */
async function mockSupabaseLogin(page, { profile = {}, authProfile = {}, offerAccess = {}, failure = null } = {}) {
  const resolvedProfile = profileRow(profile);
  const resolvedAuthProfile = authApiProfile(authProfile);

  await page.route("**/auth/v1/logout**", (route) =>
    route.fulfill({ status: 204, body: "" })
  );

  await page.route("**/auth/v1/token**", async (route) => {
    if (failure) {
      await route.fulfill({
        status: failure.status || 400,
        contentType: "application/json",
        body: JSON.stringify({
          error: "invalid_grant",
          error_description: failure.message,
          msg: failure.message,
        }),
      });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        access_token: "e2e-fake-access-token",
        token_type: "bearer",
        expires_in: 3600,
        refresh_token: "e2e-fake-refresh-token",
        user: {
          id: resolvedProfile.id,
          aud: "authenticated",
          role: "authenticated",
          email: resolvedProfile.email || "e2e.user@example.com",
          app_metadata: { provider: "email", providers: ["email"] },
          user_metadata: {},
          created_at: "2026-01-01T00:00:00Z",
        },
      }),
    });
  });

  await page.route("**/rest/v1/profiles**", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(resolvedProfile),
    })
  );

  await page.route("**/api/offer/my-access", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ has_offer_access: false, ...offerAccess }),
    })
  );

  await page.route("**/api/auth/profile", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(resolvedAuthProfile),
    })
  );
}

export { mockSupabaseLogin, profileRow, authApiProfile, FAKE_USER_ID };
