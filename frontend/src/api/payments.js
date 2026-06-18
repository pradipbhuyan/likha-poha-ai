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

export async function getStudentPaymentConfig() {
  /** Load Razorpay configuration for a standalone student (no parent_id). */
  return authFetch("/api/payments/student-config", {
    method: "GET",
  });
}

export async function createStudentPaymentOrder(payload) {
  /** Create a Razorpay order for a standalone student paying for themselves.
   *  payload: { plan_key: string }
   */
  return authFetch("/api/payments/student-create-order", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function verifyStudentPayment(payload) {
  /** Verify Razorpay callback for a standalone student payment. */
  return authFetch("/api/payments/student-verify", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
