/**
 * markdownCleanup.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Re-exports the canonical markdown/LaTeX cleanup pipeline from shared/, which
 * is the single source of truth used by both the web frontend and the mobile
 * app. See shared/utils/markdownCleanup.js for the implementation.
 */
export * from "../../../shared/utils/markdownCleanup.js";
