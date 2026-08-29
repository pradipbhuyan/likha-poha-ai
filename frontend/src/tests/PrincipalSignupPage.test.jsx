/**
 * PrincipalSignupPage.test.jsx
 * Regression tests for the dedicated principal self-signup path.
 */
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

vi.mock("../assets/AITutorLogo1.png", () => ({ default: "logo.png" }));

const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

import PrincipalSignupPage from "../pages/PrincipalSignupPage";

const SUCCESS_RESPONSE = {
  ok: true,
  status: 200,
  json: async () => ({ success: true, role: "principal", account_status: "pending_verification", school_code: "SUN-7F3K2" }),
};

function fillRequiredFields() {
  fireEvent.change(screen.getByTestId("principal-signup-name"), { target: { value: "Meera Kalita" } });
  fireEvent.change(screen.getByTestId("principal-signup-email"), { target: { value: "meera@example.com" } });
  fireEvent.change(screen.getByTestId("principal-signup-school"), { target: { value: "Sunrise Public School" } });
  fireEvent.change(screen.getByTestId("principal-signup-password"), { target: { value: "strongpass1" } });
}

describe("PrincipalSignupPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetch.mockResolvedValue(SUCCESS_RESPONSE);
  });

  test("renders the principal signup form", () => {
    render(<PrincipalSignupPage onBackToLogin={vi.fn()} />);
    expect(screen.getByTestId("principal-signup-page")).toBeInTheDocument();
    expect(screen.getByTestId("principal-signup-name")).toBeInTheDocument();
    expect(screen.getByTestId("principal-signup-school")).toBeInTheDocument();
  });

  test("blocks submit when required fields are missing", () => {
    render(<PrincipalSignupPage onBackToLogin={vi.fn()} />);
    fireEvent.click(screen.getByTestId("principal-signup-submit"));
    expect(screen.getByTestId("principal-signup-error")).toBeInTheDocument();
    expect(mockFetch).not.toHaveBeenCalled();
  });

  test("submits to /api/auth/principal-signup with the right payload", async () => {
    render(<PrincipalSignupPage onBackToLogin={vi.fn()} />);
    fillRequiredFields();
    fireEvent.click(screen.getByTestId("principal-signup-submit"));

    await waitFor(() => expect(mockFetch).toHaveBeenCalled());
    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toContain("/api/auth/principal-signup");
    const body = JSON.parse(options.body);
    expect(body).toMatchObject({
      name: "Meera Kalita",
      email: "meera@example.com",
      school_name: "Sunrise Public School",
      password: "strongpass1",
    });
  });

  test("shows the school code on the confirmation screen after signup", async () => {
    render(<PrincipalSignupPage onBackToLogin={vi.fn()} />);
    fillRequiredFields();
    fireEvent.click(screen.getByTestId("principal-signup-submit"));

    expect(await screen.findByTestId("principal-signup-done")).toBeInTheDocument();
    expect(screen.getByText("SUN-7F3K2")).toBeInTheDocument();
  });

  test("shows a friendly message for a duplicate email", async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 409,
      json: async () => ({ success: false, detail: "already registered" }),
    });
    render(<PrincipalSignupPage onBackToLogin={vi.fn()} />);
    fillRequiredFields();
    fireEvent.click(screen.getByTestId("principal-signup-submit"));

    expect(await screen.findByTestId("principal-signup-error")).toHaveTextContent(/already registered/i);
  });
});
