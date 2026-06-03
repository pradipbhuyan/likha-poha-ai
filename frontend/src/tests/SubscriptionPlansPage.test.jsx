import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import SubscriptionPlansPage from "../pages/SubscriptionPlansPage";
import {
  createPaymentOrder,
  getPaymentConfig,
  verifyPayment,
} from "../api/payments";

vi.mock("../api/parentDashboard", () => ({
  getParentChildren: vi.fn(async () => ({
    children: [
      {
        id: "child-1",
        username: "Student One",
        subscription_plan: "free",
        account_status: "active",
      },
    ],
  })),
  getParentSubscriptionPlans: vi.fn(async () => ({
    success: true,
    persisted: true,
    source: "database",
    plans: {
      free: {
        key: "free",
        label: "Free Trial",
        short_label: "Free",
        price: 0,
        billing_label: "14 days",
        is_public: true,
        display_order: 1,
        included: ["1 child profile"],
        not_included: [],
        comparison: {
          children: "1",
          aiUsage: "Limited",
          cbse: "Limited",
          sof: "Locked",
          ragSof: "Locked",
          parentDashboard: "Basic",
        },
      },
      starter: {
        key: "starter",
        label: "Standard",
        short_label: "Standard",
        price: 499,
        billing_label: "month",
        discount_percent: 10,
        discount_label: "Summer Special",
        is_public: true,
        display_order: 2,
        access_cbse: true,
        access_sof_science: false,
        included: ["Everything in Free Trial"],
        not_included: ["SOF RAG mock tests"],
        comparison: {
          children: "1",
          aiUsage: "Higher limit",
          cbse: "Included",
          sof: "Locked",
          ragSof: "Locked",
          parentDashboard: "Full",
        },
      },
    },
    plan_order: ["free", "starter"],
  })),
}));

vi.mock("../api/payments", () => ({
  getPaymentConfig: vi.fn(),
  createPaymentOrder: vi.fn(),
  verifyPayment: vi.fn(),
}));

function renderPage() {
  /** Render the subscription page with a minimal mocked parent user. */
  return render(
    <SubscriptionPlansPage
      user={{
        role: "parent",
        email: "parent@example.com",
        username: "Parent User",
      }}
    />
  );
}

describe("SubscriptionPlansPage payments", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    delete window.Razorpay;
    getPaymentConfig.mockResolvedValue({
      configured: false,
      provider: "razorpay",
      currency: "INR",
      key_id: null,
    });
  });

  test("shows safe payment pending state when Razorpay is not configured", async () => {
    /*
     * This validates the no-Razorpay setup path.
     *
     * Expected result:
     * - Discounted Standard plan is shown from mocked Supabase settings.
     * - Button says Payment Setup Pending.
     * - Clicking it does not call payment APIs and shows manual activation text.
     */
    renderPage();

    expect(
      await screen.findByRole("button", { name: /choose standard/i })
    ).toBeInTheDocument();
    expect(screen.getByText("₹449")).toBeInTheDocument();
    expect(screen.getByText("Summer Special")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /choose standard/i }));

    const paymentButton = screen.getByRole("button", {
      name: /payment setup pending/i,
    });

    expect(paymentButton).toBeInTheDocument();
    fireEvent.click(paymentButton);

    expect(
      await screen.findByText(/admin can activate standard from admin control/i)
    ).toBeInTheDocument();
    expect(createPaymentOrder).not.toHaveBeenCalled();
    expect(verifyPayment).not.toHaveBeenCalled();
  });

  test("creates Razorpay order and verifies successful checkout callback", async () => {
    /*
     * This validates the configured-payment happy path using a mocked
     * Razorpay Checkout object.
     *
     * Expected result:
     * - Payment button changes to Pay with UPI.
     * - createPaymentOrder is called with child and plan.
     * - Razorpay checkout opens.
     * - handler calls verifyPayment with Razorpay ids/signature.
     */
    getPaymentConfig.mockResolvedValue({
      configured: true,
      provider: "razorpay",
      currency: "INR",
      key_id: "rzp_test_key",
    });
    createPaymentOrder.mockResolvedValue({
      key_id: "rzp_test_key",
      order: {
        id: "order_123",
        amount: 44900,
        currency: "INR",
      },
    });
    verifyPayment.mockResolvedValue({ success: true });

    const open = vi.fn();
    window.Razorpay = vi.fn(function Razorpay(options) {
      setTimeout(() => {
        options.handler({
          razorpay_order_id: "order_123",
          razorpay_payment_id: "pay_123",
          razorpay_signature: "signature_123",
        });
      }, 0);

      return { open };
    });

    renderPage();

    expect(
      await screen.findByRole("button", { name: /choose standard/i })
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /choose standard/i }));
    fireEvent.click(screen.getByRole("button", { name: /pay with upi/i }));

    await waitFor(() => {
      expect(createPaymentOrder).toHaveBeenCalledWith({
        child_id: "child-1",
        plan_key: "starter",
      });
    });

    expect(window.Razorpay).toHaveBeenCalledWith(
      expect.objectContaining({
        key: "rzp_test_key",
        amount: 44900,
        currency: "INR",
        order_id: "order_123",
        method: {
          upi: true,
        },
      })
    );
    await waitFor(() => {
      expect(open).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(verifyPayment).toHaveBeenCalledWith({
        razorpay_order_id: "order_123",
        razorpay_payment_id: "pay_123",
        razorpay_signature: "signature_123",
      });
    });

    expect(
      await screen.findByText(/payment verified/i)
    ).toBeInTheDocument();
  });
});
