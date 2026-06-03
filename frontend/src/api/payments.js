import { authFetch } from "./authClient";

export async function getPaymentConfig() {
  return authFetch("/api/payments/config", {
    method: "GET",
  });
}

export async function createPaymentOrder(payload) {
  return authFetch("/api/payments/create-order", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function verifyPayment(payload) {
  return authFetch("/api/payments/verify", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
