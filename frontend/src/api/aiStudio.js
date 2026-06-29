/**
 * aiStudio.js — Admin AI Studio API Client
 * All endpoints require admin role. API keys are NEVER returned raw.
 */
import { authFetch } from "./authClient";

const BASE = "/api/admin/ai-studio";

// ── Providers ─────────────────────────────────────────────────────────────────

/** Get all AI providers with masked keys and current config */
export async function getProviders() {
  return authFetch(`${BASE}/providers`);
}

/**
 * Update a provider's configuration.
 * Pass api_key only if changing it; omit to keep existing key.
 * NEVER send an unmasked key back after reading masked value.
 */
export async function updateProvider(providerKey, data) {
  return authFetch(`${BASE}/providers/${providerKey}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

/**
 * Test connection to a provider.
 * Optionally pass api_key to test a key WITHOUT saving it.
 */
export async function testProviderConnection(providerKey, opts = {}) {
  return authFetch(`${BASE}/providers/${providerKey}/test`, {
    method: "POST",
    body: JSON.stringify({ api_key: opts.api_key || null }),
  });
}

/** Get model list for a provider (only works for ollama_local) */
export async function getProviderModels(providerKey, baseUrl = null) {
  const qs = baseUrl ? `?base_url=${encodeURIComponent(baseUrl)}` : "";
  return authFetch(`${BASE}/providers/${providerKey}/models${qs}`);
}

// ── Model Profiles ────────────────────────────────────────────────────────────

/** Get model routing profiles for all features */
export async function getModelProfiles() {
  return authFetch(`${BASE}/model-profiles`);
}

/** Update the provider/model for a specific feature */
export async function updateModelProfile(featureKey, data) {
  return authFetch(`${BASE}/model-profiles/${featureKey}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

// ── Prompt Templates ──────────────────────────────────────────────────────────

/** Get all prompt templates with active version content */
export async function getPromptTemplates() {
  return authFetch(`${BASE}/prompts`);
}

/** Save a new version of a prompt template */
export async function updatePromptTemplate(templateId, data) {
  return authFetch(`${BASE}/prompts/${templateId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

/** Activate (roll back to) a specific version */
export async function activatePromptVersion(templateId, versionNumber) {
  return authFetch(`${BASE}/prompts/${templateId}/activate-version`, {
    method: "POST",
    body: JSON.stringify({ version_number: versionNumber }),
  });
}

/** Get version history for a prompt template */
export async function getPromptVersions(templateId) {
  return authFetch(`${BASE}/prompts/${templateId}/versions`);
}

// ── Knowledge Sources ─────────────────────────────────────────────────────────

/** Get knowledge source status */
export async function getKnowledgeSources() {
  return authFetch(`${BASE}/knowledge-sources`);
}

// ── Generation Jobs ───────────────────────────────────────────────────────────

/** Get recent AI generation jobs */
export async function getGenerationJobs(limit = 50) {
  return authFetch(`${BASE}/jobs?limit=${limit}`);
}

/** Retry a failed generation job */
export async function retryGenerationJob(jobId) {
  return authFetch(`${BASE}/jobs/${jobId}/retry`, { method: "POST" });
}

// ── Usage & Costs ─────────────────────────────────────────────────────────────

/** Get usage and cost summary */
export async function getUsageSummary(days = 30) {
  return authFetch(`${BASE}/usage?days=${days}`);
}

// ── Quality Metrics ───────────────────────────────────────────────────────────

/** Get AI output quality metrics */
export async function getQualityMetrics() {
  return authFetch(`${BASE}/quality`);
}
