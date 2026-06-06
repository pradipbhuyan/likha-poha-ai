import { authFetch } from "./authClient";


export async function getSalesSummary() {
  /** Load admin-wide or salesperson-scoped sales incentive data. */
  return authFetch("/api/sales/summary", {
    method: "GET",
  });
}


export async function createSalesPerson(payload) {
  /** Create a salesperson login/profile from the admin sales page. */
  return authFetch("/api/sales/people", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}


export async function createSalesAttribution(payload) {
  /** Save which salesperson onboarded which student and package. */
  return authFetch("/api/sales/attributions", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}


export async function updateSalesAttribution(attributionId, payload) {
  /** Update incentive tracking details for one student sale. */
  return authFetch(`/api/sales/attributions/${attributionId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}
