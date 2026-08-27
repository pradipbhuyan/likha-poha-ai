import { authFetch } from "./authClient";

/**
 * Fetch the full product catalogue (grades + coaching programs).
 * Admin-only endpoint.
 */
export async function getProductCatalogue() {
  return authFetch("/api/product-catalogue");
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
