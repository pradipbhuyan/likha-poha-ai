import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import SchoolOsSsoPage from "../pages/SchoolOsSsoPage";

const { getSession, setSession } = vi.hoisted(() => ({
  getSession: vi.fn(),
  setSession: vi.fn(),
}));

vi.mock("../api/supabaseClient", () => ({
  supabase: {
    auth: {
      getSession,
      setSession,
    },
  },
}));

const code = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopq";
const accessToken = "lp-access-token";
const refreshToken = "lp-refresh-token";

describe("SchoolOsSsoPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    sessionStorage.clear();
    window.history.replaceState({}, "", `/school-os/sso#code=${code}`);
    vi.stubGlobal("fetch", vi.fn());
    vi.spyOn(window.history, "replaceState");
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  test("clears a valid launch fragment before completing SSO and sends code only", async () => {
    fetch.mockResolvedValue(
      new Response(
        JSON.stringify({
          access_token: accessToken,
          refresh_token: refreshToken,
        }),
        { status: 200 }
      )
    );
    setSession.mockResolvedValue({ error: null });
    getSession.mockResolvedValue({
      data: { session: { user: { id: "likhapoha-user" } } },
      error: null,
    });

    render(<SchoolOsSsoPage />);

    expect(window.location.hash).toBe("");
    expect(window.history.replaceState).toHaveBeenCalledWith(
      window.history.state,
      "",
      "/school-os/sso"
    );
    expect(screen.getByText("Opening Likha Poha…")).toBeInTheDocument();

    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(1));
    expect(fetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/sso/school-os/complete",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code }),
      }
    );
    expect(fetch.mock.calls[0][1].body).not.toContain("email");
    expect(fetch.mock.calls[0][1].body).not.toContain("organization");
    expect(fetch.mock.calls[0][1].body).not.toContain("role");

    await waitFor(() =>
      expect(setSession).toHaveBeenCalledWith({
        access_token: accessToken,
        refresh_token: refreshToken,
      })
    );
    expect(setSession).toHaveBeenCalledTimes(1);
    expect(getSession).toHaveBeenCalledTimes(1);
    expect(document.body.textContent).not.toContain(code);
    expect(document.body.textContent).not.toContain(accessToken);
    expect(document.body.textContent).not.toContain(refreshToken);
    expect(localStorage.getItem("school-os-sso-code")).toBeNull();
    expect(sessionStorage.getItem("school-os-sso-code")).toBeNull();
  });

  test("rejects malformed or ambiguous fragments before any API call", async () => {
    window.history.replaceState(
      {},
      "",
      `/school-os/sso#code=${code}&code=${code}`
    );

    render(<SchoolOsSsoPage />);

    expect(window.location.hash).toBe("");
    expect(
      await screen.findByText("Unable to open Likha Poha from School OS.")
    ).toBeInTheDocument();
    expect(fetch).not.toHaveBeenCalled();
    expect(setSession).not.toHaveBeenCalled();
  });

  test("does not retry a failed completion and never installs partial tokens", async () => {
    fetch.mockResolvedValue(new Response(null, { status: 409 }));

    render(<SchoolOsSsoPage />);

    expect(
      await screen.findByText("Unable to open Likha Poha from School OS.")
    ).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(setSession).not.toHaveBeenCalled();
    expect(getSession).not.toHaveBeenCalled();
  });

  test("replaces an existing browser session through setSession", async () => {
    fetch.mockResolvedValue(
      new Response(
        JSON.stringify({
          access_token: accessToken,
          refresh_token: refreshToken,
        }),
        { status: 200 }
      )
    );
    setSession.mockResolvedValue({ error: null });
    getSession.mockResolvedValue({
      data: { session: { user: { id: "new-likhapoha-user" } } },
      error: null,
    });

    localStorage.setItem("existing-lp-session-marker", "different-user");
    render(<SchoolOsSsoPage />);

    await waitFor(() => expect(setSession).toHaveBeenCalledTimes(1));
    expect(setSession).toHaveBeenCalledWith({
      access_token: accessToken,
      refresh_token: refreshToken,
    });
  });

  test("shows a safe failure when session verification fails", async () => {
    fetch.mockResolvedValue(
      new Response(
        JSON.stringify({
          access_token: accessToken,
          refresh_token: refreshToken,
        }),
        { status: 200 }
      )
    );
    setSession.mockResolvedValue({ error: null });
    getSession.mockResolvedValue({ data: { session: null }, error: null });

    render(<SchoolOsSsoPage />);

    expect(
      await screen.findByText("Unable to open Likha Poha from School OS.")
    ).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(setSession).toHaveBeenCalledTimes(1);
  });
});
