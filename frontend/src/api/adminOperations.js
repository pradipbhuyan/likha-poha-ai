import { authFetch } from "./authClient";

const BASE = "/api/admin/operations";

export const getOperationsSummary = () =>
  authFetch(`${BASE}/summary`);

export const getOperationsHealth = () =>
  authFetch(`${BASE}/health`);

export const getOperationsPayments = (days = 30, page = 1, pageSize = 20) =>
  authFetch(`${BASE}/payments?days=${days}&page=${page}&page_size=${pageSize}`);

export const getOperationsWebhooks = (days = 30) =>
  authFetch(`${BASE}/webhooks?days=${days}`);

export const getOperationsSubscriptions = (days = 30, page = 1, pageSize = 20) =>
  authFetch(`${BASE}/subscriptions?days=${days}&page=${page}&page_size=${pageSize}`);

export const getOperationsUsage = () =>
  authFetch(`${BASE}/usage`);

export const getOperationsAlerts = (days = 7, page = 1, pageSize = 20) =>
  authFetch(`${BASE}/alerts?days=${days}&page=${page}&page_size=${pageSize}`);

export const getExpiryJobStatus = () =>
  authFetch(`${BASE}/expiry-job-status`);

export const runExpiryJob = () =>
  authFetch(`${BASE}/run-expiry-job`, { method: "POST" });

export const getRecentActivity = (limit = 20) =>
  authFetch(`${BASE}/recent-activity?limit=${limit}`);

export const getNotifications = () =>
  authFetch(`${BASE}/notifications`);
