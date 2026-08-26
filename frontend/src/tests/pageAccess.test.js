import { describe, expect, test } from "vitest";

import { ADMIN_ONLY_PAGES, isPageBlockedForRole } from "../utils/pageAccess";

describe("isPageBlockedForRole()", () => {
  test("REGRESSION: a non-admin role is blocked from every admin-only page", () => {
    // Before this fix, App.jsx's renderPage() switch statement mounted
    // admin-only pages (AdminPaymentsPage, AdminSubscriptionSettingsPage,
    // etc.) for ANY role — the nav sidebar hid the links, but activePage
    // could be forced via localStorage ("tutor_active_page") to reach them
    // directly. Every page in ADMIN_ONLY_PAGES must now be blocked for
    // every non-admin role.
    for (const page of ADMIN_ONLY_PAGES) {
      for (const role of ["student", "parent", "teacher", "sales", undefined, null]) {
        expect(isPageBlockedForRole(page, role)).toBe(true);
      }
    }
  });

  test("admin role is never blocked from an admin-only page", () => {
    for (const page of ADMIN_ONLY_PAGES) {
      expect(isPageBlockedForRole(page, "admin")).toBe(false);
    }
  });

  test("a non-restricted page is never blocked, regardless of role", () => {
    for (const role of ["student", "parent", "teacher", "sales", "admin", undefined]) {
      expect(isPageBlockedForRole("dashboard", role)).toBe(false);
      expect(isPageBlockedForRole("lessons", role)).toBe(false);
    }
  });

  test("specific named examples from the audit finding are covered", () => {
    expect(ADMIN_ONLY_PAGES.has("paymentLogs")).toBe(true); // AdminPaymentsPage
    expect(ADMIN_ONLY_PAGES.has("subscriptionSettings")).toBe(true); // AdminSubscriptionSettingsPage
    expect(isPageBlockedForRole("paymentLogs", "student")).toBe(true);
    expect(isPageBlockedForRole("subscriptionSettings", "parent")).toBe(true);
  });
});
