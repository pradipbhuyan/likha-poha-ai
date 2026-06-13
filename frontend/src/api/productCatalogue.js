import { authFetch } from "./authClient";

/**
 * Fetch the full product catalogue (grades + coaching programs).
 * Admin-only endpoint.
 */
export async function getProductCatalogue() {
  return authFetch("/api/product-catalogue");
}

/**
 * Toggle a grade's student-facing visibility.
 * @param {string} grade  e.g. "Grade 11"
 * @param {boolean} visible
 */
export async function setGradeVisibility(grade, visible) {
  return authFetch("/api/product-catalogue/grade", {
    method: "PATCH",
    body: JSON.stringify({ grade, visible }),
  });
}

/**
 * Toggle a coaching program's student-facing visibility.
 * @param {string} program  e.g. "JEE", "NEET", "CUET"
 * @param {boolean} visible
 */
export async function setProgramVisibility(program, visible) {
  return authFetch("/api/product-catalogue/program", {
    method: "PATCH",
    body: JSON.stringify({ program, visible }),
  });
}
