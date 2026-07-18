/**
 * @likhapoha/shared — entry point
 *
 * This package contains pure-JS code shared by the web (frontend/) and
 * mobile (mobile/) apps. Import specific modules directly:
 *
 *   import { normalizeTutorMarkdown } from "@likhapoha/shared/utils/markdownCleanup";
 *   import { hasPaidAccess }          from "@likhapoha/shared/utils/resolveSubscription";
 *
 * Nothing here is platform-specific. No DOM, no React, no native modules,
 * no bundler-specific syntax (e.g. import.meta.env) — that's why there is
 * no shared/api/ layer: frontend's and mobile's HTTP clients are each tied
 * to their own auth flow (Supabase JS SDK browser sessions vs. SecureStore)
 * and bundler env-var convention (Vite's import.meta.env.VITE_* vs. Expo's
 * process.env.EXPO_PUBLIC_*), so they can't be genuinely shared as-is.
 */

// Utils
export * from "./utils/markdownCleanup.js";
export * from "./utils/resolveSubscription.js";
export * from "./utils/subjectAccess.js";
export * from "./utils/syllabusDefaults.js";
export * from "./utils/testAccounts.js";

// Config
export * from "./config/subscriptionPlans.js";
