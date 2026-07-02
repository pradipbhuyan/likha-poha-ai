/**
 * learningSimulation.js — Admin Learning Simulation API client
 * All endpoints are admin-only.
 */
import { authFetch } from "./authClient";

const BASE = "/api/admin/simulation/learning";

export const getSimulationStatus = () =>
  authFetch(`${BASE}/status`);

export const runSimulation = (payload) =>
  authFetch(`${BASE}/run`, {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const resetSimulation = () =>
  authFetch(`${BASE}/reset`, { method: "POST" });

export const listSimulationRuns = (limit = 20, offset = 0) =>
  authFetch(`${BASE}/runs?limit=${limit}&offset=${offset}`);

export const getSimulationRun = (runId) =>
  authFetch(`${BASE}/runs/${runId}`);

export const getSimulationAnomalies = (runId) =>
  authFetch(`${BASE}/anomalies${runId ? `?run_id=${runId}` : ""}`);

export const createBugForAnomaly = (anomalyId) =>
  authFetch(`${BASE}/anomalies/${anomalyId}/create-bug`, { method: "POST" });
