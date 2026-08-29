import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import AdminSchoolOutreachPage from "../pages/AdminSchoolOutreachPage";
import {
  getOutreachSummary,
  listOutreachPrincipals,
  sendOutreachEmails,
  markOutreachResponded,
  getOutreachStates,
} from "../api/schoolOutreach";

vi.mock("../api/schoolOutreach", () => ({
  getOutreachSummary: vi.fn(),
  listOutreachPrincipals: vi.fn(),
  sendOutreachEmails: vi.fn(),
  markOutreachResponded: vi.fn(),
  getOutreachStates: vi.fn(),
}));

function mockSummary() {
  return {
    success: true,
    summary: { total: 28485, pending: 28483, sent: 2, failed: 0, sent_today: 2, reminders_sent: 0, responded: 1 },
  };
}

function mockPrincipals() {
  return {
    success: true,
    total: 2,
    principals: [
      { email: "a@example.com", principal_name: "Pushpa Kumari Singh", school_name: "Atal Adarsh Vidyalaya", status: "pending", sent_at: null, reminder_sent_at: null, responded: false },
      { email: "b@example.com", principal_name: "R K Sharma", school_name: "Kendriya Vidyalaya", status: "sent", sent_at: "2026-08-28T10:00:00Z", reminder_sent_at: null, responded: true },
    ],
  };
}

describe("AdminSchoolOutreachPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(window, "confirm").mockReturnValue(true);
    getOutreachSummary.mockResolvedValue(mockSummary());
    listOutreachPrincipals.mockResolvedValue(mockPrincipals());
    sendOutreachEmails.mockResolvedValue({ success: true, queued: 1, message: "Queued 1 email(s)." });
    markOutreachResponded.mockResolvedValue({ success: true, updated: 1 });
    getOutreachStates.mockResolvedValue({ success: true, states: ["Delhi", "Haryana"] });
  });

  test("renders summary stats and the principal roster", async () => {
    render(<AdminSchoolOutreachPage />);
    expect(await screen.findByText("28485")).toBeInTheDocument();
    expect(screen.getByText("Pushpa Kumari Singh")).toBeInTheDocument();
    expect(screen.getByText("R K Sharma")).toBeInTheDocument();
  });

  test("selecting a row and sending calls the API with that email", async () => {
    render(<AdminSchoolOutreachPage />);
    await screen.findByText("Pushpa Kumari Singh");

    const checkboxes = screen.getAllByRole("checkbox").filter((c) => !c.closest("label") && c.dataset.testid !== "select-all-page");
    fireEvent.click(checkboxes[0]);

    fireEvent.click(screen.getByText(/Send to Selected/));

    await waitFor(() => {
      expect(sendOutreachEmails).toHaveBeenCalledWith(["a@example.com"], "initial");
    });
  });

  test("toggling 'needs reminder' switches send type to reminder", async () => {
    render(<AdminSchoolOutreachPage />);
    await screen.findByText("Pushpa Kumari Singh");

    fireEvent.click(screen.getByLabelText(/Needs reminder/i));

    await waitFor(() => {
      expect(listOutreachPrincipals).toHaveBeenCalledWith(
        expect.objectContaining({ needsReminder: true })
      );
    });

    const checkboxes = screen.getAllByRole("checkbox").filter((c) => !c.closest("label") && c.dataset.testid !== "select-all-page");
    fireEvent.click(checkboxes[0]);
    fireEvent.click(screen.getByText(/Send to Selected/));

    await waitFor(() => {
      expect(sendOutreachEmails).toHaveBeenCalledWith(["a@example.com"], "reminder");
    });
  });

  test("marking a selected principal as responded calls the API", async () => {
    render(<AdminSchoolOutreachPage />);
    await screen.findByText("Pushpa Kumari Singh");

    const checkboxes = screen.getAllByRole("checkbox").filter((c) => !c.closest("label") && c.dataset.testid !== "select-all-page");
    fireEvent.click(checkboxes[0]);
    fireEvent.click(screen.getByText("Mark as Responded"));

    await waitFor(() => {
      expect(markOutreachResponded).toHaveBeenCalledWith(["a@example.com"]);
    });
  });

  test("send button is disabled with nothing selected", async () => {
    render(<AdminSchoolOutreachPage />);
    await screen.findByText("Pushpa Kumari Singh");
    expect(screen.getByText(/Send to Selected/).closest("button")).toBeDisabled();
  });

  test("the header checkbox selects then unselects everyone on the page", async () => {
    render(<AdminSchoolOutreachPage />);
    await screen.findByText("Pushpa Kumari Singh");

    const selectAll = screen.getByTestId("select-all-page");
    fireEvent.click(selectAll);
    expect(screen.getByLabelText("Select a@example.com")).toBeChecked();
    expect(screen.getByLabelText("Select b@example.com")).toBeChecked();

    fireEvent.click(selectAll);
    expect(screen.getByLabelText("Select a@example.com")).not.toBeChecked();
    expect(screen.getByLabelText("Select b@example.com")).not.toBeChecked();
  });

  test("picking a state filters the roster by that state", async () => {
    render(<AdminSchoolOutreachPage />);
    await screen.findByText("Pushpa Kumari Singh");
    await waitFor(() => expect(screen.getByText("Delhi")).toBeInTheDocument());

    fireEvent.change(screen.getByDisplayValue("All states"), { target: { value: "Delhi" } });

    await waitFor(() => {
      expect(listOutreachPrincipals).toHaveBeenCalledWith(
        expect.objectContaining({ state: "Delhi" })
      );
    });
  });
});
