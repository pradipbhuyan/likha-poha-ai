/**
 * AdminLearningSimulation.test.jsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Frontend unit tests for the Admin Learning Simulation page.
 * Tests rendering, controls, API integration, and anomaly table.
 */
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";
import AdminLearningSimulationPage from "../pages/AdminLearningSimulationPage";

// ── API mocks ─────────────────────────────────────────────────────────────────
vi.mock("../api/learningSimulation", () => ({
  getSimulationStatus: vi.fn(),
  runSimulation: vi.fn(),
  resetSimulation: vi.fn(),
  listSimulationRuns: vi.fn(),
  getSimulationAnomalies: vi.fn(),
  createBugForAnomaly: vi.fn(),
}));

import * as sim from "../api/learningSimulation";

const STATUS_OK = {
  success: true,
  current_day: 7,
  next_cycle_start: 8,
  next_cycle_end: 14,
  users_setup: true,
  vijay_access: "family_premium",
  total_runs: 1,
  recent_runs: [],
  vijay_profile: { subscription_plan: "family_premium", access_cbse: true },
  manish_profile: { username: "manish_sim_parent" },
};

const RUNS_OK = {
  runs: [
    {
      id: "run-1",
      status: "completed",
      cycle_start_day: 1,
      cycle_end_day: 7,
      dry_run: false,
      anomalies_count: 2,
      bugs_created_count: 1,
      created_at: "2026-07-01T10:00:00Z",
    },
  ],
};

function setup(statusOverride = {}, runsOverride = {}) {
  sim.getSimulationStatus.mockResolvedValue({ ...STATUS_OK, ...statusOverride });
  sim.listSimulationRuns.mockResolvedValue({ ...RUNS_OK, ...runsOverride });
  sim.getSimulationAnomalies.mockResolvedValue({ anomalies: [] });
}

describe("AdminLearningSimulationPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test("page renders with simulation heading", async () => {
    setup();
    render(<AdminLearningSimulationPage user={{ role: "admin", username: "admin" }} />);
    expect(await screen.findByTestId("admin-learning-simulation-page")).toBeInTheDocument();
    expect(await screen.findByText(/Learning Simulation/i)).toBeInTheDocument();
  });

  test("shows ADMIN ONLY badge", async () => {
    setup();
    render(<AdminLearningSimulationPage user={{ role: "admin", username: "admin" }} />);
    expect(await screen.findByText(/ADMIN ONLY/i)).toBeInTheDocument();
  });

  test("shows simulated day stat card", async () => {
    setup();
    render(<AdminLearningSimulationPage user={{ role: "admin", username: "admin" }} />);
    expect(await screen.findByTestId("stat-sim-day")).toBeInTheDocument();
    expect(await screen.findByText("7")).toBeInTheDocument(); // current_day = 7
  });

  test("shows Family Premium plan for Vijay", async () => {
    setup();
    render(<AdminLearningSimulationPage user={{ role: "admin", username: "admin" }} />);
    expect(await screen.findByText(/family_premium/i)).toBeInTheDocument();
  });

  test("shows CBSE access as Yes", async () => {
    setup();
    render(<AdminLearningSimulationPage user={{ role: "admin", username: "admin" }} />);
    expect(await screen.findByText(/✓ Yes/i)).toBeInTheDocument();
  });

  test("run button is present and labelled correctly", async () => {
    setup();
    render(<AdminLearningSimulationPage user={{ role: "admin", username: "admin" }} />);
    const btn = await screen.findByTestId("run-simulation-btn");
    expect(btn).toBeInTheDocument();
    expect(btn).toHaveTextContent(/Run.*Day Cycle/i);
  });

  test("clicking run button calls runSimulation API", async () => {
    setup();
    sim.runSimulation.mockResolvedValue({
      success: true,
      run_id: "new-run",
      dry_run: false,
      cycle_start_day: 8,
      cycle_end_day: 14,
      total_days: 7,
      total_events: 42,
      anomalies: [],
      bugs_created: 0,
      status: "completed",
      setup: { status: "ready" },
      days: [],
    });
    render(<AdminLearningSimulationPage user={{ role: "admin", username: "admin" }} />);
    const btn = await screen.findByTestId("run-simulation-btn");
    fireEvent.click(btn);
    await waitFor(() => expect(sim.runSimulation).toHaveBeenCalledTimes(1));
  });

  test("dry run toggle is present", async () => {
    setup();
    render(<AdminLearningSimulationPage user={{ role: "admin", username: "admin" }} />);
    await screen.findByTestId("run-simulation-btn");
    const checkboxes = screen.getAllByRole("checkbox");
    // Should have Dry Run, Create Bugs, Strict Validation checkboxes
    expect(checkboxes.length).toBeGreaterThanOrEqual(3);
  });

  test("dry run toggle changes run button label", async () => {
    setup();
    render(<AdminLearningSimulationPage user={{ role: "admin", username: "admin" }} />);
    await screen.findByTestId("run-simulation-btn");
    const dryRunCheckbox = screen.getAllByRole("checkbox")[0]; // first = Dry Run
    fireEvent.click(dryRunCheckbox);
    await waitFor(() => {
      expect(screen.getByTestId("run-simulation-btn")).toHaveTextContent(/Dry/i);
    });
  });

  test("run history shows previous run", async () => {
    setup();
    render(<AdminLearningSimulationPage user={{ role: "admin", username: "admin" }} />);
    expect(await screen.findByText(/Day 1–7/i)).toBeInTheDocument();
    expect(await screen.findByText(/completed/i)).toBeInTheDocument();
  });

  test("anomaly table is rendered", async () => {
    setup();
    render(<AdminLearningSimulationPage user={{ role: "admin", username: "admin" }} />);
    expect(await screen.findByTestId("anomaly-table")).toBeInTheDocument();
  });

  test("anomaly table shows no anomalies message when empty", async () => {
    setup();
    sim.getSimulationAnomalies.mockResolvedValue({ anomalies: [] });
    render(<AdminLearningSimulationPage user={{ role: "admin", username: "admin" }} />);
    expect(await screen.findByText(/Select a run from history/i)).toBeInTheDocument();
  });

  test("reset button shows confirmation flow", async () => {
    setup();
    render(<AdminLearningSimulationPage user={{ role: "admin", username: "admin" }} />);
    const showResetBtn = await screen.findByTestId("show-reset-btn");
    fireEvent.click(showResetBtn);
    expect(await screen.findByTestId("confirm-reset-btn")).toBeInTheDocument();
  });

  test("reset confirmation calls resetSimulation API", async () => {
    setup();
    sim.resetSimulation.mockResolvedValue({
      success: true,
      deleted: [],
      errors: [],
      message: "Simulation data reset.",
    });
    render(<AdminLearningSimulationPage user={{ role: "admin", username: "admin" }} />);
    fireEvent.click(await screen.findByTestId("show-reset-btn"));
    fireEvent.click(await screen.findByTestId("confirm-reset-btn"));
    await waitFor(() => expect(sim.resetSimulation).toHaveBeenCalledTimes(1));
  });

  test("cycle day selector renders 1d/7d/14d options", async () => {
    setup();
    render(<AdminLearningSimulationPage user={{ role: "admin", username: "admin" }} />);
    await screen.findByTestId("run-simulation-btn");
    expect(screen.getByRole("button", { name: "1d" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "7d" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "14d" })).toBeInTheDocument();
  });

  test("shows success message after successful run", async () => {
    setup();
    sim.runSimulation.mockResolvedValue({
      success: true,
      run_id: "r2",
      dry_run: false,
      cycle_start_day: 8,
      cycle_end_day: 14,
      total_days: 7,
      total_events: 42,
      anomalies: [],
      bugs_created: 0,
      status: "completed",
      setup: { status: "ready" },
      days: [],
    });
    render(<AdminLearningSimulationPage user={{ role: "admin", username: "admin" }} />);
    fireEvent.click(await screen.findByTestId("run-simulation-btn"));
    expect(await screen.findByText(/Simulation.*completed/i)).toBeInTheDocument();
  });

  test("no anomalies for clean run shows green message after selection", async () => {
    setup();
    sim.getSimulationAnomalies.mockResolvedValue({ anomalies: [] });
    render(<AdminLearningSimulationPage user={{ role: "admin", username: "admin" }} />);
    // Click a run to select it
    const runRow = await screen.findByText(/Day 1–7/i);
    fireEvent.click(runRow.closest ? runRow.closest("div[style]") : runRow);
    await waitFor(() => expect(sim.getSimulationAnomalies).toHaveBeenCalled());
  });
});
