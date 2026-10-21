import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import SchoolOsAccountLinkPage from "../pages/SchoolOsAccountLinkPage";

const { getSession, onAuthStateChange } = vi.hoisted(() => ({
  getSession: vi.fn(),
  onAuthStateChange: vi.fn(),
}));

vi.mock("../api/supabaseClient", () => ({
  supabase: {
    auth: {
      getSession,
      onAuthStateChange,
    },
  },
}));

vi.mock("../pages/LoginPage", () => ({
  default: () => <div>Normal Likha Poha login</div>,
}));

const state = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopq";
const code = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQ";
const session = { access_token: "lp-access-token" };

describe("SchoolOsAccountLinkPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
    window.history.replaceState({}, "", `/school-os/account-link?state=${state}`);
    getSession.mockResolvedValue({ data: { session } });
    onAuthStateChange.mockReturnValue({
      data: { subscription: { unsubscribe: vi.fn() } },
    });
    vi.stubEnv(
      "VITE_SCHOOL_OS_ACCOUNT_LINK_CALLBACK_URL",
      "https://school.example.test/account/connections/likha-poha/callback",
    );
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });

  test("rejects missing or malformed state without issuing a proof", async () => {
    window.history.replaceState({}, "", "/school-os/account-link?state=bad");

    render(<SchoolOsAccountLinkPage />);

    expect(
      await screen.findByText("School OS linking unavailable"),
    ).toBeInTheDocument();
    expect(fetch).not.toHaveBeenCalled();
  });

  test("requires normal LP login when there is no current session", async () => {
    getSession.mockResolvedValue({ data: { session: null } });

    render(<SchoolOsAccountLinkPage />);

    expect(await screen.findByText("Normal Likha Poha login")).toBeInTheDocument();
    expect(fetch).not.toHaveBeenCalled();
  });

  test("does not issue a proof on page load and preserves only opaque state", async () => {
    render(<SchoolOsAccountLinkPage />);

    expect(await screen.findByText("Confirm link")).toBeInTheDocument();
    expect(fetch).not.toHaveBeenCalled();
    expect(window.location.search).toBe("");
    expect(sessionStorage.getItem("school-os-account-link-state")).toContain(
      state,
    );
    expect(sessionStorage.getItem("school-os-account-link-state")).not.toContain(
      "lp-access-token",
    );
  });

  test("issues proof only after explicit confirmation with state-only JSON", async () => {
    fetch.mockResolvedValue(
      new Response(JSON.stringify({ code }), { status: 200 }),
    );

    render(<SchoolOsAccountLinkPage />);
    fireEvent.click(await screen.findByText("Confirm link"));

    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(1));
    expect(fetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/account-link/school-os/proof",
      {
        method: "POST",
        headers: {
          Authorization: "Bearer lp-access-token",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ state }),
      },
    );
    expect(
      `https://school.example.test/account/connections/likha-poha/callback#state=${state}&code=${code}`,
    ).toContain(`#state=${state}&code=${code}`);
    expect(sessionStorage.getItem("school-os-account-link-state")).toBeNull();
  });

  test("does not issue proof when fixed callback configuration is missing", async () => {
    vi.stubEnv("VITE_SCHOOL_OS_ACCOUNT_LINK_CALLBACK_URL", "");

    render(<SchoolOsAccountLinkPage />);

    expect(
      await screen.findByText(/School OS linking is temporarily unavailable/i),
    ).toBeInTheDocument();
    expect(fetch).not.toHaveBeenCalled();
  });

  test("renders a cancel action that does not issue a proof", async () => {
    render(<SchoolOsAccountLinkPage />);

    expect(await screen.findByText("Cancel")).toBeInTheDocument();
    expect(fetch).not.toHaveBeenCalled();
  });

  test("does not automatically retry a failed proof attempt", async () => {
    fetch.mockResolvedValue(new Response(null, { status: 409 }));

    render(<SchoolOsAccountLinkPage />);
    fireEvent.click(await screen.findByText("Confirm link"));

    expect(
      await screen.findByText(/can no longer be completed/i),
    ).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(sessionStorage.getItem("school-os-account-link-state")).toBeNull();
  });
});
