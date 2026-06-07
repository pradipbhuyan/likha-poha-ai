import { authFetch } from "./authClient";


export function getPerformanceScenarios() {
  /** Load backend-defined performance scenarios without exposing test tokens. */
  return authFetch("/api/performance-tests/scenarios");
}


export function getPerformanceRuns(limit = 20) {
  /** Load recent persisted performance runs for admin trend review. */
  return authFetch(`/api/performance-tests/runs?limit=${limit}`);
}


export function getPerformanceRun(runId) {
  /** Load one persisted performance run including detailed timings. */
  return authFetch(`/api/performance-tests/runs/${runId}`);
}


export function startPerformanceRun(payload) {
  /** Queue one backend-run performance test with admin-selected limits. */
  return authFetch("/api/performance-tests/runs", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
