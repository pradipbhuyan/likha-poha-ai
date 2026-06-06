import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import SalesIncentivePage from "../pages/SalesIncentivePage";
import {
  createSalesAttribution,
  createSalesPerson,
  getSalesSummary,
} from "../api/sales";

vi.mock("../api/sales", () => ({
  getSalesSummary: vi.fn(),
  createSalesPerson: vi.fn(),
  createSalesAttribution: vi.fn(),
}));

const adminUser = {
  role: "admin",
  username: "Pradip Admin",
};

const salesUser = {
  role: "sales",
  username: "Sales Partner",
};

function mockSalesSummary() {
  /** Return a dashboard payload shared by admin and sales page tests. */
  return {
    success: true,
    summary: {
      sales_people: 1,
      tracked_students: 1,
      total_revenue: 999,
      incentive_payable: 74.93,
    },
    sales_people: [
      {
        id: "sales-1",
        username: "Sales Partner",
        email: "sales@example.com",
        sales_profile: {
          default_incentive_percent: 7.5,
        },
      },
    ],
    students: [
      {
        id: "student-1",
        username: "Akshita",
        grade: "Grade 9",
      },
    ],
    attributions: [
      {
        id: "attr-1",
        sales_profile_id: "sales-1",
        student_id: "student-1",
        package_label: "Premium SOF",
        package_amount: 999,
        incentive_percent: 7.5,
        incentive_amount: 74.93,
        status: "active",
        salesperson: {
          username: "Sales Partner",
        },
        student: {
          username: "Akshita",
        },
      },
    ],
  };
}

describe("SalesIncentivePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getSalesSummary.mockResolvedValue(mockSalesSummary());
    createSalesPerson.mockResolvedValue({ success: true });
    createSalesAttribution.mockResolvedValue({ success: true });
  });

  test("lets admin create a salesperson and track a student sale", async () => {
    render(<SalesIncentivePage user={adminUser} />);

    expect(await screen.findByText("Onboard Salesperson")).toBeInTheDocument();
    expect(screen.getByText("Sales Attribution Ledger")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/^name$/i), {
      target: { value: "New Seller" },
    });
    fireEvent.change(screen.getByLabelText(/^email$/i), {
      target: { value: "seller@example.com" },
    });
    fireEvent.change(screen.getByLabelText(/temporary password/i), {
      target: { value: "password123" },
    });
    fireEvent.change(screen.getByLabelText(/region/i), {
      target: { value: "Assam" },
    });

    fireEvent.click(screen.getByRole("button", { name: /create salesperson/i }));

    await waitFor(() => {
      expect(createSalesPerson).toHaveBeenCalledWith(
        expect.objectContaining({
          username: "New Seller",
          email: "seller@example.com",
          password: "password123",
          region: "Assam",
          default_incentive_percent: 5,
        })
      );
    });

    fireEvent.change(screen.getAllByLabelText(/incentive %/i)[1], {
      target: { value: "7.5" },
    });
    fireEvent.click(screen.getByRole("button", { name: /save student sale/i }));

    await waitFor(() => {
      expect(createSalesAttribution).toHaveBeenCalledWith(
        expect.objectContaining({
          sales_profile_id: "sales-1",
          student_id: "student-1",
          package_key: "starter",
          package_amount: 499,
          incentive_percent: 7.5,
        })
      );
    });
  });

  test("shows read-only salesperson ledger without admin onboarding forms", async () => {
    render(<SalesIncentivePage user={salesUser} />);

    expect(await screen.findByText("My Sales Ledger")).toBeInTheDocument();
    expect(screen.getByText("Premium SOF")).toBeInTheDocument();
    expect(screen.getByText(/7.5%/i)).toBeInTheDocument();
    expect(screen.queryByText("Onboard Salesperson")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /save student sale/i })).not.toBeInTheDocument();
  });
});
