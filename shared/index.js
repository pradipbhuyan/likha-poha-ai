/**
 * @likhapoha/shared — entry point
 *
 * This package contains pure-JS code shared by the web (frontend/) and
 * mobile (mobile/) apps. Import specific modules directly:
 *
 *   import { normalizeTutorMarkdown } from "@likhapoha/shared/utils/markdownCleanup";
 *   import { generateLesson }         from "@likhapoha/shared/api/lesson";
 *   import { hasPaidAccess }          from "@likhapoha/shared/utils/resolveSubscription";
 *
 * Nothing here is platform-specific. No DOM, no React, no native modules.
 */

// Utils
export * from "./utils/markdownCleanup.js";
export * from "./utils/resolveSubscription.js";
export * from "./utils/subjectAccess.js";
export * from "./utils/syllabusDefaults.js";

// Config
export * from "./config/subscriptionPlans.js";
