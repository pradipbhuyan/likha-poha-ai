/**
 * examPrepPacks.js — JEE / NEET / CUET Exam Prep Pack Purchase API
 * ─────────────────────────────────────────────────────────────────
 * Exam prep packs are independent of CBSE subscription tiers.
 * Any Grade 11/12 student can purchase them.
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

function authHeaders(token) {
  return { Authorization: `Bearer ${token}`, "Content-Type": "application/json" };
}

/**
 * Get which exam prep packs the current user has active.
 * Returns: { packs: { jee_main, neet_ug, cuet_ug }, grade_eligible }
 */
export async function getMyPacks(accessToken) {
  const r = await fetch(`${API_BASE}/api/exam-prep/my-packs`, {
    headers: authHeaders(accessToken),
  });
  if (!r.ok) throw new Error("Failed to load exam prep packs");
  return r.json();
}

/**
 * Get current pack prices from admin settings (no auth needed).
 * Returns: { prices: { jee_main, neet_ug, cuet_ug }, razorpay_configured }
 */
export async function getPackPrices() {
  const r = await fetch(`${API_BASE}/api/exam-prep/pack-prices`);
  if (!r.ok) throw new Error("Failed to load pack prices");
  return r.json();
}

/**
 * Create a Razorpay order for an exam prep pack.
 * examType: 'jee_main' | 'neet_ug' | 'cuet_ug'
 */
export async function createPackOrder(examType, accessToken) {
  const r = await fetch(`${API_BASE}/api/exam-prep/pack-order`, {
    method: "POST",
    headers: authHeaders(accessToken),
    body: JSON.stringify({ exam_type: examType }),
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to create pack order");
  }
  return r.json();
}

/**
 * Verify Razorpay payment and activate the exam prep pack.
 */
export async function verifyPackPayment({ razorpay_order_id, razorpay_payment_id, razorpay_signature, exam_type }, accessToken) {
  const r = await fetch(`${API_BASE}/api/exam-prep/pack-verify`, {
    method: "POST",
    headers: authHeaders(accessToken),
    body: JSON.stringify({ razorpay_order_id, razorpay_payment_id, razorpay_signature, exam_type }),
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error(err.detail || "Payment verification failed");
  }
  return r.json();
}
