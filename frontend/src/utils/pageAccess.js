/**
 * pageAccess.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Admin-only pages — mirrors the `roles: ["admin"]` entries in
 * components/Sidebar.jsx's nav config (kept as a separate static list here
 * rather than importing that array directly, since it closes over component
 * state like `isAdmin` for a couple of dynamic labels and isn't safe to
 * hoist to module scope as-is). The sidebar already hides these links from
 * non-admins, but App.jsx's `activePage` can be forced directly via
 * localStorage (`tutor_active_page`) or a restored session, bypassing the
 * nav entirely — isPageBlockedForRole() guards the actual render, not just
 * the link that gets you there. Keep in sync with Sidebar.jsx's `pages`
 * array if either changes.
 */
export const ADMIN_ONLY_PAGES = new Set([
  "adminControl", "adminOperations", "adminIssues", "adminFeedback",
  "adminTechDebt", "cacheManagement", "ragUpload", "syllabusReview",
  "lessonRepair", "lessonExperience", "lessonCardStyle", "unansweredReview",
  "adminQACenter", "learningSimulation", "performanceTests", "aiStudio",
  "guideThemes", "subscriptionSettings", "pricingCalculator",
  "productCatalogue", "paymentLogs", "usage", "salesIncentives", "adminChat",
]);

/** Return true when `role` must not render `activePage`. */
export function isPageBlockedForRole(activePage, role) {
  return ADMIN_ONLY_PAGES.has(activePage) && role !== "admin";
}
