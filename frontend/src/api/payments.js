import { authFetch } from "./authClient";

export async function getPaymentConfig() {
  /** Load safe Razorpay configuration for the parent subscription page. */
  return authFetch("/api/payments/config", {
    method: "GET",
  });
}

export async function createPaymentOrder(payload) {
  /** Create a Razorpay order for the selected child and subscription plan. */
  return authFetch("/api/payments/create-order", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function verifyPayment(payload) {
  /** Verify Razorpay checkout callback ids/signature with the backend. */
  return authFetch("/api/payments/verify", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
