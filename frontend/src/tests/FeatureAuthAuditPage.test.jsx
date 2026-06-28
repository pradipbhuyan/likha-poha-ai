/**
 * FeatureAuthAuditPage.test.jsx
 */
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, expect, test, vi, beforeEach } from "vitest";

vi.mock("../api/authClient", () => ({ authFetch: vi.fn() }));
import FeatureAuthAuditPage from "../pages/FeatureAuthAuditPage";
import { authFetch } from "../api/authClient";

const ADMIN = { id:"admin-1", username:"admin", role:"admin" };
const EMPTY = { success:true, available:false, message:"No feature authorization audit has been run yet." };
const REPORT = {
  success:true, available:true, audited_at:"2026-06-28T10:00:00Z",
  summary:{ overall:"PASS", total:42, passed:42, failed:0, critical:0, pass_rate:100 },
  failed_checks:[],
};
const FAIL_REPORT = {
  success:true, available:true, audited_at:"2026-06-28T10:00:00Z",
  summary:{ overall:"CRITICAL", total:42, passed:40, failed:2, critical:1, pass_rate:95.2 },
  failed_checks:[
    { feature:"EXEMPLAR", plan:"FREE_TIER", scenario:"Free user denied Exemplar",
      expected:"denied", actual:"full", passed:false, severity:"critical", detail:"leakage detected" },
  ],
};
const RUN_RESP = { success:true, job_id:"job-fa-1", message:"Started" };
const STATUS_DONE = { success:true, job:{ id:"job-fa-1", status:"completed", overall:"PASS", total:42, passed:42, critical:0 } };

describe("FeatureAuthAuditPage", () => {
  beforeEach(() => { vi.clearAllMocks(); });

  test("renders feature auth audit page", async () => {
    authFetch.mockResolvedValueOnce(EMPTY);
    render(<FeatureAuthAuditPage user={ADMIN} />);
    expect(await screen.findByTestId("feature-auth-audit-page")).toBeInTheDocument();
    expect(document.body.textContent).toContain("Feature Authorization Audit");
  });

  test("shows empty state when no report", async () => {
    authFetch.mockResolvedValueOnce(EMPTY);
    render(<FeatureAuthAuditPage user={ADMIN} />);
    expect(await screen.findByTestId("fa-no-report")).toBeInTheDocument();
    expect(document.body.textContent).toContain("No feature authorization audit");
  });

  test("shows summary cards when report exists", async () => {
    authFetch.mockResolvedValueOnce(REPORT);
    render(<FeatureAuthAuditPage user={ADMIN} />);
    expect(await screen.findByTestId("fa-summary-cards")).toBeInTheDocument();
    expect(document.body.textContent).toContain("PASS");
    expect(document.body.textContent).toContain("42");
  });

  test("run button calls backend", async () => {
    authFetch.mockResolvedValueOnce(EMPTY);
    authFetch.mockResolvedValueOnce(RUN_RESP);
    authFetch.mockResolvedValue(STATUS_DONE);
    render(<FeatureAuthAuditPage user={ADMIN} />);
    await screen.findByTestId("fa-run-btn");
    fireEvent.click(screen.getByTestId("fa-run-btn"));
    await waitFor(() => expect(authFetch).toHaveBeenCalledWith(
      expect.stringContaining("/feature-authorization/run"), expect.anything()
    ));
  });

  test("sample mode button works", async () => {
    authFetch.mockResolvedValueOnce(EMPTY);
    render(<FeatureAuthAuditPage user={ADMIN} />);
    await screen.findByTestId("fa-mode-sample");
    fireEvent.click(screen.getByTestId("fa-mode-sample"));
    expect(document.body.textContent).toContain("Sample");
  });

  test("full mode shows warning", async () => {
    authFetch.mockResolvedValueOnce(EMPTY);
    render(<FeatureAuthAuditPage user={ADMIN} />);
    await screen.findByTestId("fa-mode-full");
    fireEvent.click(screen.getByTestId("fa-mode-full"));
    await waitFor(() => expect(document.body.textContent).toContain("Full audit checks all features"));
  });

  test("shows failed checks when report has failures", async () => {
    authFetch.mockResolvedValueOnce(FAIL_REPORT);
    render(<FeatureAuthAuditPage user={ADMIN} />);
    expect(await screen.findByTestId("fa-failed-checks")).toBeInTheDocument();
    expect(document.body.textContent).toContain("Free user denied Exemplar");
  });

  test("severity filter works", async () => {
    authFetch.mockResolvedValueOnce(FAIL_REPORT);
    render(<FeatureAuthAuditPage user={ADMIN} />);
    await screen.findByTestId("fa-sev-filter");
    fireEvent.change(screen.getByTestId("fa-sev-filter"), { target:{ value:"critical" } });
    await waitFor(() => expect(document.body.textContent).toContain("Free user denied Exemplar"));
  });

  test("download buttons render when report exists", async () => {
    authFetch.mockResolvedValueOnce(REPORT);
    render(<FeatureAuthAuditPage user={ADMIN} />);
    await screen.findByTestId("fa-summary-cards");
    expect(screen.getByTestId("fa-download-json")).toBeInTheDocument();
    expect(screen.getByTestId("fa-download-md")).toBeInTheDocument();
    expect(screen.getByTestId("fa-download-csv")).toBeInTheDocument();
  });

  test("critical badge visible on CRITICAL overall", async () => {
    authFetch.mockResolvedValueOnce(FAIL_REPORT);
    render(<FeatureAuthAuditPage user={ADMIN} />);
    await screen.findByTestId("fa-summary-cards");
    expect(document.body.textContent).toContain("CRITICAL");
  });
});
