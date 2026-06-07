import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import SalesCollateralPage from "../pages/SalesCollateralPage";
import {
  createSalesCollateral,
  deleteSalesCollateral,
  getSalesCollaterals,
  uploadSalesCollateralFile,
} from "../api/sales";

vi.mock("../api/sales", () => ({
  createSalesCollateral: vi.fn(),
  deleteSalesCollateral: vi.fn(),
  getSalesCollaterals: vi.fn(),
  uploadSalesCollateralFile: vi.fn(),
}));

const sampleCollateral = {
  id: "asset-1",
  title: "WhatsApp Parent Poster",
  audience: "parents",
  channel: "whatsapp",
  format: "image",
  description: "Use after a school demo.",
  caption: "Try Likha Poha AI today.",
  asset_url: "https://example.com/poster.png",
  thumbnail_url: "",
  status: "active",
};

describe("SalesCollateralPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getSalesCollaterals.mockResolvedValue({
      success: true,
      collaterals: [sampleCollateral],
    });
    createSalesCollateral.mockResolvedValue({
      success: true,
      collateral: sampleCollateral,
    });
    deleteSalesCollateral.mockResolvedValue({ success: true });
    uploadSalesCollateralFile.mockResolvedValue({
      success: true,
      asset_url: "https://storage.example.com/poster.png",
      format: "image",
    });
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: {
        writeText: vi.fn().mockResolvedValue(undefined),
      },
    });
  });

  test("lets salespeople copy captions and download approved collateral", async () => {
    render(<SalesCollateralPage user={{ role: "sales", username: "Seller" }} />);

    expect(await screen.findByText("WhatsApp Parent Poster")).toBeInTheDocument();
    expect(screen.getByText("Try Likha Poha AI today.")).toBeInTheDocument();
    expect(screen.queryByText("Admin upload")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /copy caption/i }));

    await waitFor(() => {
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
        "Try Likha Poha AI today."
      );
    });
    expect(screen.getByRole("link", { name: /download/i })).toHaveAttribute(
      "href",
      "https://example.com/poster.png"
    );
  });

  test("lets admins add and delete collateral", async () => {
    render(
      <SalesCollateralPage user={{ role: "admin", username: "Pradip Admin" }} />
    );

    expect(await screen.findByText("Add Sales Collateral")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/^title$/i), {
      target: { value: "Insta Reel Intro" },
    });
    fireEvent.change(screen.getByLabelText(/asset url/i), {
      target: { value: "https://example.com/reel.mp4" },
    });
    fireEvent.click(screen.getByRole("button", { name: /add collateral/i }));

    await waitFor(() => {
      expect(createSalesCollateral).toHaveBeenCalledWith(
        expect.objectContaining({
          title: "Insta Reel Intro",
          asset_url: "https://example.com/reel.mp4",
        })
      );
    });

    fireEvent.click(screen.getByRole("button", { name: /delete/i }));

    await waitFor(() => {
      expect(deleteSalesCollateral).toHaveBeenCalledWith("asset-1");
    });
  });

  test("lets admins upload a collateral file before saving metadata", async () => {
    render(
      <SalesCollateralPage user={{ role: "admin", username: "Pradip Admin" }} />
    );

    expect(await screen.findByText("Add Sales Collateral")).toBeInTheDocument();

    const file = new File(["poster"], "Parent Poster.png", {
      type: "image/png",
    });

    fireEvent.change(screen.getByLabelText(/upload file/i), {
      target: { files: [file] },
    });

    await waitFor(() => {
      expect(uploadSalesCollateralFile).toHaveBeenCalledWith(file, "whatsapp");
    });

    expect(screen.getByLabelText(/asset url/i)).toHaveValue(
      "https://storage.example.com/poster.png"
    );
    expect(screen.getByText(/collateral file uploaded/i)).toBeInTheDocument();
  });
});
