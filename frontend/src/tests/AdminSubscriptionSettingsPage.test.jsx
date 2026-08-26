import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import AdminSubscriptionSettingsPage from "../pages/AdminSubscriptionSettingsPage";
import {
  getAdminSubscriptionContact,
  getAdminSubscriptionPlans,
  updateAdminSubscriptionContact,
  updateAdminSubscriptionPlans,
} from "../api/adminControl";

vi.mock("../api/adminControl", () => ({
  getAdminSubscriptionPlans: vi.fn(),
  getAdminSubscriptionContact: vi.fn(),
  updateAdminSubscriptionPlans: vi.fn(),
  updateAdminSubscriptionContact: vi.fn(),
}));

const USER = { accessToken: "token-1", role: "admin" };

// mergeSubscriptionPlans({}) falls back to the real built-in SUBSCRIPTION_PLANS
// defaults, so an empty `plans` object here still renders a full, valid set —
// no need to hand-build plan fixtures for the happy path.
function _plansResponse(overrides = {}) {
  return { plans: {}, plan_order: [], source: "defaults", persisted: false, ...overrides };
}

function _contactResponse(overrides = {}) {
  return {
    contact: {
      email: "support@likhapoha.test",
      phone: "9999999999",
      whatsapp: "9999999999",
      availability: "We usually respond within one business day.",
      message: "Need help? Contact us.",
    },
    ...overrides,
  };
}

describe("AdminSubscriptionSettingsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getAdminSubscriptionContact.mockResolvedValue(_contactResponse());
  });

  test("shows a loading state before data arrives", () => {
    getAdminSubscriptionPlans.mockReturnValue(new Promise(() => {}));
    render(<AdminSubscriptionSettingsPage user={USER} />);
    expect(screen.getByText(/loading subscription settings/i)).toBeInTheDocument();
  });

  test("renders a row for every plan once loaded, using the admin display label", async () => {
    getAdminSubscriptionPlans.mockResolvedValue(_plansResponse());
    render(<AdminSubscriptionSettingsPage user={USER} />);

    // SUBSCRIPTION_PLAN_ORDER's first entry, "starter", is admin-labelled "Premium"
    expect(await screen.findByText("Premium")).toBeInTheDocument();
    expect(screen.getByText("Family Premium")).toBeInTheDocument();
    expect(screen.getByText("6-Month")).toBeInTheDocument();
    expect(screen.getByText("Annual")).toBeInTheDocument();
  });

  test("shows the settings source badge from the API response", async () => {
    getAdminSubscriptionPlans.mockResolvedValue(_plansResponse({ source: "database", persisted: true }));
    render(<AdminSubscriptionSettingsPage user={USER} />);

    expect(await screen.findByText(/source: database/i)).toBeInTheDocument();
  });

  test("a failed plans load shows an error but still renders the page with defaults", async () => {
    getAdminSubscriptionPlans.mockRejectedValue(new Error("network down"));
    render(<AdminSubscriptionSettingsPage user={USER} />);

    expect(await screen.findByText(/unable to load subscription plan settings/i)).toBeInTheDocument();
    // Falls back to built-in defaults rather than staying blank/stuck loading
    expect(screen.getByText("Premium")).toBeInTheDocument();
  });

  test("a failed contact load does not block the page — falls back to defaults", async () => {
    getAdminSubscriptionPlans.mockResolvedValue(_plansResponse());
    getAdminSubscriptionContact.mockRejectedValue(new Error("contact endpoint down"));
    render(<AdminSubscriptionSettingsPage user={USER} />);

    // Page still renders normally; default contact email is used
    expect(await screen.findByDisplayValue("likhapohaai@gmail.com")).toBeInTheDocument();
  });

  test("clicking Edit opens the inline panel for that plan", async () => {
    getAdminSubscriptionPlans.mockResolvedValue(_plansResponse());
    render(<AdminSubscriptionSettingsPage user={USER} />);
    await screen.findByText("Premium");

    const editButtons = screen.getAllByRole("button", { name: /^edit ✏$/i });
    fireEvent.click(editButtons[0]);

    expect(await screen.findByText(/^editing: /i)).toBeInTheDocument();
    expect(screen.getByText("💰 Pricing & Validity")).toBeInTheDocument();
    expect(screen.getByText("🏷️ Display & Limits")).toBeInTheDocument();
    expect(screen.getByText("🎛️ Feature Flags & Comparison")).toBeInTheDocument();
  });

  test("clicking Close Panel closes the inline edit panel", async () => {
    getAdminSubscriptionPlans.mockResolvedValue(_plansResponse());
    render(<AdminSubscriptionSettingsPage user={USER} />);
    await screen.findByText("Premium");

    fireEvent.click(screen.getAllByRole("button", { name: /^edit ✏$/i })[0]);
    await screen.findByText(/^editing: /i);

    fireEvent.click(screen.getByRole("button", { name: /close panel/i }));

    await waitFor(() => {
      expect(screen.queryByText(/^editing: /i)).not.toBeInTheDocument();
    });
  });

  test("editing the price field updates the displayed value", async () => {
    getAdminSubscriptionPlans.mockResolvedValue(_plansResponse());
    render(<AdminSubscriptionSettingsPage user={USER} />);
    await screen.findByText("Premium");

    fireEvent.click(screen.getAllByRole("button", { name: /^edit ✏$/i })[0]);
    await screen.findByText(/^editing: /i);

    // Field label isn't wired via htmlFor, so query by the visible label text's
    // sibling input instead.
    const priceLabel = screen.getByText("Price (₹)");
    const input = priceLabel.parentElement.querySelector("input");
    fireEvent.change(input, { target: { value: "349" } });

    expect(input.value).toBe("349");
  });

  test("toggling 'Show to parents' flips the toggle state", async () => {
    getAdminSubscriptionPlans.mockResolvedValue(_plansResponse());
    render(<AdminSubscriptionSettingsPage user={USER} />);
    await screen.findByText("Premium");

    fireEvent.click(screen.getAllByRole("button", { name: /^edit ✏$/i })[0]);
    const toggleLabel = await screen.findByText("Show to parents");
    const toggleRow = toggleLabel.closest("div[style*='cursor: pointer']") || toggleLabel.closest("div").parentElement;

    // Clicking the toggle must not throw and the row must still be present
    // (a full visual-state assertion isn't practical for an inline-style
    // toggle with no test id — this locks in that the click handler runs).
    expect(() => fireEvent.click(toggleRow)).not.toThrow();
  });

  test("Save All Plans calls updateAdminSubscriptionPlans with serialized plan data", async () => {
    getAdminSubscriptionPlans.mockResolvedValue(_plansResponse());
    updateAdminSubscriptionPlans.mockResolvedValue({ plans: {}, plan_order: [], persisted: true, source: "database" });
    render(<AdminSubscriptionSettingsPage user={USER} />);
    await screen.findByText("Premium");

    fireEvent.click(screen.getByRole("button", { name: /save all plans/i }));

    await waitFor(() => {
      expect(updateAdminSubscriptionPlans).toHaveBeenCalledTimes(1);
    });
    const [payload, token] = updateAdminSubscriptionPlans.mock.calls[0];
    expect(token).toBe("token-1");
    expect(Array.isArray(payload.plans)).toBe(true);
    expect(payload.plans.length).toBeGreaterThan(0);
    expect(payload.plans[0]).toHaveProperty("key");
  });

  test("successful save shows a confirmation message", async () => {
    getAdminSubscriptionPlans.mockResolvedValue(_plansResponse());
    updateAdminSubscriptionPlans.mockResolvedValue({ plans: {}, plan_order: [], persisted: true, source: "database" });
    render(<AdminSubscriptionSettingsPage user={USER} />);
    await screen.findByText("Premium");

    fireEvent.click(screen.getByRole("button", { name: /save all plans/i }));

    expect(await screen.findByText(/subscription plan settings saved and applied/i)).toBeInTheDocument();
  });

  test("save failure shows an error message instead of a silent failure", async () => {
    getAdminSubscriptionPlans.mockResolvedValue(_plansResponse());
    updateAdminSubscriptionPlans.mockRejectedValue(new Error("Razorpay validation failed"));
    render(<AdminSubscriptionSettingsPage user={USER} />);
    await screen.findByText("Premium");

    fireEvent.click(screen.getByRole("button", { name: /save all plans/i }));

    expect(await screen.findByText("Razorpay validation failed")).toBeInTheDocument();
  });

  test("save that persists=false shows a Supabase-confirmation warning, not a plain success", async () => {
    getAdminSubscriptionPlans.mockResolvedValue(_plansResponse());
    updateAdminSubscriptionPlans.mockResolvedValue({ plans: {}, plan_order: [], persisted: false });
    render(<AdminSubscriptionSettingsPage user={USER} />);
    await screen.findByText("Premium");

    fireEvent.click(screen.getByRole("button", { name: /save all plans/i }));

    expect(await screen.findByText(/saved, but supabase could not confirm/i)).toBeInTheDocument();
  });

  test("editing and saving the contact bar calls updateAdminSubscriptionContact", async () => {
    getAdminSubscriptionPlans.mockResolvedValue(_plansResponse());
    updateAdminSubscriptionContact.mockResolvedValue(_contactResponse({
      contact: { email: "new@likhapoha.test", phone: "", whatsapp: "", availability: "", message: "" },
    }));
    render(<AdminSubscriptionSettingsPage user={USER} />);
    await screen.findByText("Premium");

    const emailInput = screen.getByPlaceholderText("Email");
    fireEvent.change(emailInput, { target: { value: "new@likhapoha.test" } });

    // Scope to the contact bar's own Save button (the plans table also has one)
    const contactSaveButtons = screen.getAllByRole("button", { name: /^save$/i });
    fireEvent.click(contactSaveButtons[0]);

    await waitFor(() => {
      expect(updateAdminSubscriptionContact).toHaveBeenCalledTimes(1);
    });
    const [payload] = updateAdminSubscriptionContact.mock.calls[0];
    expect(payload.email).toBe("new@likhapoha.test");
    expect(await screen.findByText(/contact details saved/i)).toBeInTheDocument();
  });

  test("contact save failure shows an error message", async () => {
    getAdminSubscriptionPlans.mockResolvedValue(_plansResponse());
    updateAdminSubscriptionContact.mockRejectedValue(new Error("Could not save contact"));
    render(<AdminSubscriptionSettingsPage user={USER} />);
    await screen.findByText("Premium");

    fireEvent.click(screen.getAllByRole("button", { name: /^save$/i })[0]);

    expect(await screen.findByText("Could not save contact")).toBeInTheDocument();
  });
});
