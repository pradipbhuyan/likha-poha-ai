import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import AdminPricingCalculatorPage from "../pages/AdminPricingCalculatorPage";

describe("AdminPricingCalculatorPage", () => {
  test("shows cost cards and recalculates margin when price changes", () => {
    /** The calculator should expose break-even and planned-margin guidance. */
    render(<AdminPricingCalculatorPage />);

    expect(screen.getByText(/token cost/i)).toBeInTheDocument();
    expect(screen.getByText(/platform share/i)).toBeInTheDocument();
    expect(screen.getByText(/suggested price/i)).toBeInTheDocument();

    const plannedPriceInput = screen.getByLabelText(/planned price/i);

    fireEvent.change(plannedPriceInput, {
      target: { value: "1" },
    });

    expect(screen.getByText(/estimated margin is/i)).toBeInTheDocument();
    expect(screen.getByText(/\(-/)).toBeInTheDocument();
  });

  test("can include SOF subjects in the monthly usage mix", () => {
    /** Enabling SOF rows should be possible for premium-plan pricing checks. */
    render(<AdminPricingCalculatorPage />);

    const sofScienceRow = screen.getByText("SOF Science").closest(".pricing-usage-row");
    const sofCheckbox = sofScienceRow.querySelector("input[type='checkbox']");

    expect(sofCheckbox.checked).toBe(false);

    fireEvent.click(sofCheckbox);

    expect(sofCheckbox.checked).toBe(true);
  });
});
