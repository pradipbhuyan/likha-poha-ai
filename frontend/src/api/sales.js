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


export async function getSalesCollaterals() {
  /** Load sales collateral entries visible to the current admin or sales user. */
  return authFetch("/api/sales/collaterals", {
    method: "GET",
  });
}


export async function uploadSalesCollateralFile(file, channel = "whatsapp") {
  /** Upload a collateral file through the backend so storage credentials stay server-side. */
  const formData = new FormData();
  formData.append("file", file);
  formData.append("channel", channel);

  return authFetch("/api/sales/collaterals/upload", {
    method: "POST",
    body: formData,
  });
}


export async function createSalesCollateral(payload) {
  /** Create a sales collateral item from the admin sales collateral page. */
  return authFetch("/api/sales/collaterals", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}


export async function updateSalesCollateral(collateralId, payload) {
  /** Update a sales collateral item from the admin page. */
  return authFetch(`/api/sales/collaterals/${collateralId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}


export async function deleteSalesCollateral(collateralId) {
  /** Delete a sales collateral item from the admin page. */
  return authFetch(`/api/sales/collaterals/${collateralId}`, {
    method: "DELETE",
  });
}
