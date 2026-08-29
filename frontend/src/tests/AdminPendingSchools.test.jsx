/**
 * AdminPendingSchools.test.jsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Regression tests for the "Pending School Approvals" panel added to
 * AdminSupportTools.jsx — the admin-facing UI for POST /api/admin/schools/*.
 *
 * Covers:
 *   - Panel is hidden when there are no pending schools
 *   - Pending schools render with principal identity attached
 *   - Approve calls /verify and removes the row on success
 *   - Reject asks for confirmation, then calls /reject and removes the row
 *   - A failed approve shows an error message, not a silent no-op
 */
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";
import AdminSupportTools from "../components/AdminSupportTools";

const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

function jsonResponse(body, status = 200) {
  return Promise.resolve({
    ok: status < 400,
    status,
    json: () => Promise.resolve(body),
  });
}

const PENDING_SCHOOL = {
  id: "school-1",
  name: "Sunrise Public School",
  school_code: "SUN-7F3K2",
  city: "Guwahati",
  state: "Assam",
  udise_code: null,
  principal_id: "principal-1",
  principal_username: "Meera Kalita",
  principal_email: "meera@example.com",
};

describe("AdminSupportTools — pending school approvals", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(window, "confirm").mockReturnValue(true);
  });

  test("panel is hidden when there are no pending schools", async () => {
    mockFetch.mockImplementation((url) => {
      if (url.includes("/api/admin/schools/pending")) return jsonResponse({ success: true, schools: [] });
      return jsonResponse({});
    });
    render(<AdminSupportTools accessToken="tok" />);
    await waitFor(() => expect(mockFetch).toHaveBeenCalled());
    expect(screen.queryByTestId("pending-schools-list")).not.toBeInTheDocument();
  });

  test("renders a pending school with the principal's identity", async () => {
    mockFetch.mockImplementation((url) => {
      if (url.includes("/api/admin/schools/pending")) return jsonResponse({ success: true, schools: [PENDING_SCHOOL] });
      return jsonResponse({});
    });
    render(<AdminSupportTools accessToken="tok" />);

    expect(await screen.findByTestId("pending-school-school-1")).toBeInTheDocument();
    expect(screen.getByText("Sunrise Public School")).toBeInTheDocument();
    expect(screen.getByText(/Meera Kalita/)).toBeInTheDocument();
    expect(screen.getByText(/meera@example.com/)).toBeInTheDocument();
    expect(screen.getByText("SUN-7F3K2")).toBeInTheDocument();
  });

  test("approving a school calls /verify and removes it from the list", async () => {
    mockFetch.mockImplementation((url) => {
      if (url.includes("/api/admin/schools/pending")) return jsonResponse({ success: true, schools: [PENDING_SCHOOL] });
      if (url.includes("/api/admin/schools/school-1/verify")) return jsonResponse({ success: true, status: "active" });
      return jsonResponse({});
    });
    render(<AdminSupportTools accessToken="tok" />);
    await screen.findByTestId("pending-school-school-1");

    fireEvent.click(screen.getByTestId("approve-school-school-1"));

    await waitFor(() => {
      expect(screen.queryByTestId("pending-school-school-1")).not.toBeInTheDocument();
    });
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/admin/schools/school-1/verify"),
      expect.objectContaining({ method: "POST" }),
    );
  });

  test("rejecting a school confirms, then calls /reject and removes it from the list", async () => {
    mockFetch.mockImplementation((url) => {
      if (url.includes("/api/admin/schools/pending")) return jsonResponse({ success: true, schools: [PENDING_SCHOOL] });
      if (url.includes("/api/admin/schools/school-1/reject")) return jsonResponse({ success: true, status: "rejected" });
      return jsonResponse({});
    });
    render(<AdminSupportTools accessToken="tok" />);
    await screen.findByTestId("pending-school-school-1");

    fireEvent.click(screen.getByTestId("reject-school-school-1"));

    expect(window.confirm).toHaveBeenCalled();
    await waitFor(() => {
      expect(screen.queryByTestId("pending-school-school-1")).not.toBeInTheDocument();
    });
  });

  test("a failed approval shows an error instead of silently removing the row", async () => {
    mockFetch.mockImplementation((url) => {
      if (url.includes("/api/admin/schools/pending")) return jsonResponse({ success: true, schools: [PENDING_SCHOOL] });
      if (url.includes("/api/admin/schools/school-1/verify")) {
        return jsonResponse({ success: false, error: "School is not pending verification" });
      }
      return jsonResponse({});
    });
    render(<AdminSupportTools accessToken="tok" />);
    await screen.findByTestId("pending-school-school-1");

    fireEvent.click(screen.getByTestId("approve-school-school-1"));

    expect(await screen.findByText(/School is not pending verification/)).toBeInTheDocument();
    // The row must still be there — a failed approval isn't a silent success.
    expect(screen.getByTestId("pending-school-school-1")).toBeInTheDocument();
  });
});
