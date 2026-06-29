/**
 * AdminAIStudioPage.jsx — Admin AI Studio
 *
 * 7 tabs:
 *  1. Providers       — configure provider API keys, models, connection test
 *  2. Model Routing   — per-feature provider/model assignment
 *  3. Prompt Templates — versioned system/user prompts
 *  4. Knowledge Sources — RAG/DKB/content status (read-only + coming soon)
 *  5. Generation Jobs — AI job history
 *  6. Usage & Costs   — token/cost summary by provider/feature
 *  7. Quality Metrics — repair/validation quality stats
 *
 * Security: API keys shown only as masked strings. Never send back masked value.
 * Admin-only — backend enforces require_admin on all endpoints.
 */
import { useCallback, useEffect, useState } from "react";
import {
  Plug, GitBranch, FileText, BookOpen,
  Settings, DollarSign, BarChart2,
} from "lucide-react";
import {
  getGenerationJobs,
  getKnowledgeSources,
  getModelProfiles,
  getPromptTemplates,
  getProviders,
  getQualityMetrics,
  getUsageSummary,
  testProviderConnection,
  updateModelProfile,
  updatePromptTemplate,
  updateProvider,
} from "../api/aiStudio";

// ── Shared styles ─────────────────────────────────────────────────────────────
const card = {
  background: "var(--panel,#fff)", border: "1px solid var(--border,#e5e7eb)",
  borderRadius: 12, padding: "16px 18px", marginBottom: 14,
};
const inp = {
  background: "var(--surface2,#f8fafc)", border: "1px solid var(--border,#e5e7eb)",
  borderRadius: 8, padding: "7px 10px", fontFamily: "inherit", fontSize: ".82rem",
  color: "var(--text,#374151)", width: "100%", boxSizing: "border-box",
};
const btn = {
  padding: "7px 14px", borderRadius: 8, border: "none", fontFamily: "inherit",
  fontWeight: 700, fontSize: ".8rem", cursor: "pointer",
};

const TABS = [
  { key: "providers",  label: "Providers",        Icon: Plug },
  { key: "routing",    label: "Model Routing",     Icon: GitBranch },
  { key: "prompts",    label: "Prompt Templates",  Icon: FileText },
  { key: "knowledge",  label: "Knowledge Sources", Icon: BookOpen },
  { key: "jobs",       label: "Generation Jobs",   Icon: Settings },
  { key: "usage",      label: "Usage & Costs",     Icon: DollarSign },
  { key: "quality",    label: "Quality Metrics",   Icon: BarChart2 },
];

function StatusBadge({ ok, label }) {
  return (
    <span style={{
      padding: "2px 8px", borderRadius: 10, fontSize: ".7rem", fontWeight: 700,
      background: ok ? "rgba(34,197,94,.1)" : "rgba(239,68,68,.1)",
      color: ok ? "#166534" : "#dc2626",
    }}>{label}</span>
  );
}

function SaveBanner({ msg, error, onClose }) {
  if (!msg && !error) return null;
  return (
    <div style={{
      padding: "8px 14px", borderRadius: 8, marginBottom: 12, fontSize: ".82rem",
      background: error ? "rgba(239,68,68,.08)" : "rgba(34,197,94,.08)",
      border: `1px solid ${error ? "rgba(239,68,68,.3)" : "rgba(34,197,94,.3)"}`,
      color: error ? "#dc2626" : "#166534",
      display: "flex", justifyContent: "space-between", alignItems: "center",
    }}>
      <span>{error || msg}</span>
      <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", fontSize: ".9rem" }}>✕</button>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Tab 1: Providers
// ─────────────────────────────────────────────────────────────────────────────
function ProvidersTab() {
  const [providers, setProviders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);
  const [form, setForm] = useState({});
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [banner, setBanner] = useState({ msg: null, error: null });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const d = await getProviders();
      setProviders(d?.providers || []);
    } catch { /* non-critical */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  function selectProvider(p) {
    setSelected(p.provider_key);
    setForm({
      api_key: "",      // always blank on open — never pre-fill masked value
      model: p.current_model || "",
      base_url: p.base_url || "",
      temperature: p.temperature,
      max_tokens: p.max_tokens,
      timeout_s: p.timeout_s,
      is_enabled: p.is_enabled,
    });
    setTestResult(null);
    setBanner({ msg: null, error: null });
  }

  async function handleSave() {
    setSaving(true);
    setBanner({ msg: null, error: null });
    try {
      const payload = { ...form };
      // Strip blank api_key so we don't overwrite existing key with empty string
      if (!payload.api_key || payload.api_key.startsWith("••")) delete payload.api_key;
      const r = await updateProvider(selected, payload);
      setBanner({ msg: r?.message || "Saved.", error: null });
      await load();
    } catch (e) {
      setBanner({ msg: null, error: e.message || "Save failed." });
    } finally {
      setSaving(false);
    }
  }

  async function handleSetPrimary() {
    try {
      await updateProvider(selected, { set_as_primary: true });
      setBanner({ msg: "Set as primary provider.", error: null });
      await load();
    } catch (e) {
      setBanner({ msg: null, error: e.message });
    }
  }

  async function handleSetFallback() {
    try {
      await updateProvider(selected, { set_as_fallback: true });
      setBanner({ msg: "Set as fallback provider.", error: null });
      await load();
    } catch (e) {
      setBanner({ msg: null, error: e.message });
    }
  }

  async function handleTest() {
    setTesting(true);
    setTestResult(null);
    try {
      // If user has entered a new (non-masked) key, test with that key only
      const testKey = (form.api_key && !form.api_key.startsWith("••"))
        ? form.api_key : null;
      // Always pass the model from the form so Test works before Save
      const testModel = (form.model && form.model.trim()) ? form.model.trim() : null;
      const r = await testProviderConnection(selected, { api_key: testKey, model: testModel });
      setTestResult(r);
    } catch (e) {
      setTestResult({ success: false, message: e.message });
    } finally {
      setTesting(false);
    }
  }

  const prov = providers.find(p => p.provider_key === selected);

  return (
    <div data-testid="tab-providers">
      <div style={{ display: "grid", gridTemplateColumns: "220px 1fr", gap: 16 }}>
        {/* Provider list */}
        <div>
          {loading && <p style={{ color: "#94a3b8", fontSize: ".82rem" }}>Loading…</p>}
          {providers.map(p => (
            <button
              key={p.provider_key}
              onClick={() => selectProvider(p)}
              style={{
                width: "100%", textAlign: "left", padding: "9px 12px",
                borderRadius: 8, marginBottom: 4, fontFamily: "inherit",
                fontSize: ".8rem", fontWeight: selected === p.provider_key ? 700 : 400,
                background: selected === p.provider_key
                  ? "rgba(99,102,241,.12)" : "var(--surface2,#f8fafc)",
                border: `1px solid ${selected === p.provider_key ? "#6366f1" : "var(--border,#e5e7eb)"}`,
                cursor: "pointer",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span>{p.display_name}</span>
                <span style={{ display: "flex", gap: 4 }}>
                  {p.is_primary && <span style={{ fontSize: ".6rem", background: "#6366f1", color: "#fff", padding: "1px 5px", borderRadius: 4 }}>PRIMARY</span>}
                  {p.is_fallback && <span style={{ fontSize: ".6rem", background: "#8b5cf6", color: "#fff", padding: "1px 5px", borderRadius: 4 }}>FALLBACK</span>}
                </span>
              </div>
              <div style={{ fontSize: ".68rem", color: p.has_api_key ? "#16a34a" : "#dc2626", marginTop: 2 }}>
                {p.has_api_key ? "✓ Key configured" : "✗ No key"}{p.free_tier ? " · Free tier" : ""}
              </div>
            </button>
          ))}
        </div>

        {/* Config panel */}
        <div>
          {!selected && (
            <div style={{ color: "#94a3b8", fontSize: ".88rem", padding: "32px 0", textAlign: "center" }}>
              Select a provider to configure
            </div>
          )}
          {selected && prov && (
            <div style={card}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 14 }}>
                <div>
                  <h3 style={{ margin: 0, fontSize: ".95rem", fontWeight: 800 }}>{prov.display_name}</h3>
                  <a href={prov.docs_url} target="_blank" rel="noreferrer"
                    style={{ fontSize: ".72rem", color: "#6366f1" }}>Docs ↗</a>
                  {prov.free_tier && (
                    <span style={{ fontSize: ".72rem", color: "#16a34a", marginLeft: 8 }}>
                      ✓ {prov.free_tier_notes || "Free tier available"}
                    </span>
                  )}
                </div>
                <div style={{ display: "flex", gap: 6 }}>
                  <button onClick={handleSetPrimary} style={{ ...btn, background: "#6366f1", color: "#fff", fontSize: ".72rem" }}>
                    Set Primary
                  </button>
                  <button onClick={handleSetFallback} style={{ ...btn, background: "#8b5cf6", color: "#fff", fontSize: ".72rem" }}>
                    Set Fallback
                  </button>
                </div>
              </div>

              <SaveBanner msg={banner.msg} error={banner.error} onClose={() => setBanner({ msg: null, error: null })} />

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 10 }}>
                <div>
                  <label style={{ fontSize: ".75rem", fontWeight: 600, display: "block", marginBottom: 3 }}>
                    API Key {prov.key_prefix && <span style={{ color: "#94a3b8" }}>({prov.key_prefix}...)</span>}
                  </label>
                  <input
                    type="password"
                    placeholder={prov.has_api_key ? "Leave blank to keep existing key" : `Enter ${prov.display_name} key`}
                    value={form.api_key || ""}
                    onChange={e => setForm(f => ({ ...f, api_key: e.target.value }))}
                    style={inp}
                    data-testid={`provider-key-${selected}`}
                  />
                  {prov.has_api_key && (
                    <div style={{ fontSize: ".68rem", color: "#16a34a", marginTop: 2 }}>
                      ✓ Key stored: {prov.masked_key}
                    </div>
                  )}
                </div>
                <div>
                  <label style={{ fontSize: ".75rem", fontWeight: 600, display: "block", marginBottom: 3 }}>Model</label>
                  <input
                    type="text"
                    placeholder={prov.suggested_models?.[0] || "e.g. gpt-4.1-nano"}
                    value={form.model || ""}
                    onChange={e => setForm(f => ({ ...f, model: e.target.value }))}
                    style={inp}
                    list={`models-${selected}`}
                    data-testid={`provider-model-${selected}`}
                  />
                  <datalist id={`models-${selected}`}>
                    {(prov.suggested_models || []).map(m => <option key={m} value={m} />)}
                  </datalist>
                </div>
                {(selected === "ollama_cloud" || selected === "ollama_local") && (
                  <div style={{ gridColumn: "1/-1" }}>
                    <label style={{ fontSize: ".75rem", fontWeight: 600, display: "block", marginBottom: 3 }}>Server URL</label>
                    <input
                      type="text"
                      placeholder={selected === "ollama_local" ? "http://localhost:11434" : "https://api.ollama.com"}
                      value={form.base_url || ""}
                      onChange={e => setForm(f => ({ ...f, base_url: e.target.value }))}
                      style={inp}
                    />
                  </div>
                )}
                <div>
                  <label style={{ fontSize: ".75rem", fontWeight: 600, display: "block", marginBottom: 3 }}>Temperature</label>
                  <input type="number" step="0.1" min="0" max="2" value={form.temperature ?? 0.4}
                    onChange={e => setForm(f => ({ ...f, temperature: parseFloat(e.target.value) }))}
                    style={{ ...inp, width: "auto" }} />
                </div>
                <div>
                  <label style={{ fontSize: ".75rem", fontWeight: 600, display: "block", marginBottom: 3 }}>Max Tokens</label>
                  <input type="number" min="128" max="32768" value={form.max_tokens ?? 4096}
                    onChange={e => setForm(f => ({ ...f, max_tokens: parseInt(e.target.value) }))}
                    style={{ ...inp, width: "auto" }} />
                </div>
              </div>

              {/* Test result */}
              {testResult && (
                <div style={{
                  padding: "8px 12px", borderRadius: 8, marginBottom: 10,
                  background: testResult.success ? "rgba(34,197,94,.08)" : "rgba(239,68,68,.08)",
                  border: `1px solid ${testResult.success ? "rgba(34,197,94,.3)" : "rgba(239,68,68,.3)"}`,
                  fontSize: ".78rem", color: testResult.success ? "#166534" : "#dc2626",
                }}>
                  {testResult.success ? "✓" : "✗"} {testResult.message}
                  {testResult.latency_ms > 0 && (
                    <span style={{ marginLeft: 8, color: "#64748b" }}>({testResult.latency_ms}ms)</span>
                  )}
                </div>
              )}

              {/* Action buttons */}
              <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                <button onClick={handleSave} disabled={saving}
                  style={{ ...btn, background: "#6366f1", color: "#fff" }}
                  data-testid="provider-save-btn">
                  {saving ? "Saving…" : "Save Configuration"}
                </button>
                <button onClick={handleTest} disabled={testing}
                  style={{ ...btn, background: "var(--surface2,#f8fafc)", border: "1px solid var(--border,#e5e7eb)" }}
                  data-testid="provider-test-btn">
                  {testing ? "Testing…" : "Test Connection"}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Tab 2: Model Routing
// ─────────────────────────────────────────────────────────────────────────────
function ModelRoutingTab() {
  const [profiles, setProfiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({});
  const [saving, setSaving] = useState(false);
  const [banner, setBanner] = useState({ msg: null, error: null });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const d = await getModelProfiles();
      setProfiles(d?.profiles || []);
    } catch { /* */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  async function handleSave(fk) {
    setSaving(true);
    try {
      const r = await updateModelProfile(fk, form);
      setBanner({ msg: r?.message || "Saved.", error: null });
      await load();
      setEditing(null);
    } catch (e) {
      setBanner({ msg: null, error: e.message });
    } finally { setSaving(false); }
  }

  if (loading) return <p style={{ color: "#94a3b8" }}>Loading…</p>;

  return (
    <div data-testid="tab-model-routing">
      <SaveBanner msg={banner.msg} error={banner.error} onClose={() => setBanner({ msg: null, error: null })} />
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: ".8rem" }}>
        <thead>
          <tr style={{ color: "#64748b", borderBottom: "1px solid var(--border,#e5e7eb)" }}>
            {["Feature", "Provider", "Model", "Temp", "Max Tokens", "Fallback", ""].map(h => (
              <th key={h} style={{ textAlign: "left", padding: "6px 8px" }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {profiles.map(p => (
            <tr key={p.feature_key} style={{ borderBottom: "1px solid var(--border,#f1f5f9)" }}>
              {editing === p.feature_key ? (
                <>
                  <td style={{ padding: "6px 8px" }}><strong>{p.display_name}</strong></td>
                  <td><input value={form.provider_key || ""} onChange={e => setForm(f => ({ ...f, provider_key: e.target.value }))} style={{ ...inp, width: 100 }} /></td>
                  <td><input value={form.model || ""} onChange={e => setForm(f => ({ ...f, model: e.target.value }))} style={{ ...inp, width: 140 }} /></td>
                  <td><input type="number" step="0.1" value={form.temperature ?? 0.4} onChange={e => setForm(f => ({ ...f, temperature: parseFloat(e.target.value) }))} style={{ ...inp, width: 60 }} /></td>
                  <td><input type="number" value={form.max_tokens ?? 4096} onChange={e => setForm(f => ({ ...f, max_tokens: parseInt(e.target.value) }))} style={{ ...inp, width: 80 }} /></td>
                  <td><input placeholder="fallback provider" value={form.fallback_provider || ""} onChange={e => setForm(f => ({ ...f, fallback_provider: e.target.value }))} style={{ ...inp, width: 110 }} /></td>
                  <td>
                    <button onClick={() => handleSave(p.feature_key)} disabled={saving}
                      style={{ ...btn, background: "#22c55e", color: "#fff", marginRight: 4 }}>Save</button>
                    <button onClick={() => setEditing(null)}
                      style={{ ...btn, background: "var(--surface2,#f8fafc)" }}>Cancel</button>
                  </td>
                </>
              ) : (
                <>
                  <td style={{ padding: "6px 8px" }}>{p.display_name}</td>
                  <td style={{ padding: "6px 8px" }}><code style={{ fontSize: ".75rem" }}>{p.provider_key}</code></td>
                  <td style={{ padding: "6px 8px" }}><code style={{ fontSize: ".75rem" }}>{p.model}</code></td>
                  <td style={{ padding: "6px 8px" }}>{p.temperature}</td>
                  <td style={{ padding: "6px 8px" }}>{p.max_tokens}</td>
                  <td style={{ padding: "6px 8px", color: "#64748b", fontSize: ".72rem" }}>
                    {p.fallback_provider ? `${p.fallback_provider}/${p.fallback_model || ""}` : "—"}
                  </td>
                  <td style={{ padding: "6px 8px" }}>
                    <button onClick={() => { setEditing(p.feature_key); setForm({ ...p }); }}
                      style={{ ...btn, background: "var(--surface2,#f8fafc)", border: "1px solid var(--border,#e5e7eb)", fontSize: ".72rem" }}>
                      Edit
                    </button>
                  </td>
                </>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Tab 3: Prompt Templates
// ─────────────────────────────────────────────────────────────────────────────
function PromptTemplatesTab() {
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);
  const [form, setForm] = useState({ system_prompt: "", user_prompt: "", change_summary: "" });
  const [saving, setSaving] = useState(false);
  const [banner, setBanner] = useState({ msg: null, error: null });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const d = await getPromptTemplates();
      setTemplates(d?.templates || []);
    } catch { /* */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  function selectTemplate(t) {
    setSelected(t.id);
    setForm({ system_prompt: t.system_prompt || "", user_prompt: t.user_prompt || "", change_summary: "" });
    setBanner({ msg: null, error: null });
  }

  async function handleSave() {
    setSaving(true);
    try {
      const r = await updatePromptTemplate(selected, form);
      setBanner({ msg: r?.message || "Saved.", error: null });
      await load();
    } catch (e) {
      setBanner({ msg: null, error: e.message });
    } finally { setSaving(false); }
  }

  const tmpl = templates.find(t => t.id === selected);

  return (
    <div data-testid="tab-prompts">
      <div style={{ display: "grid", gridTemplateColumns: "200px 1fr", gap: 16 }}>
        <div>
          {loading && <p style={{ color: "#94a3b8", fontSize: ".82rem" }}>Loading…</p>}
          {templates.length === 0 && !loading && (
            <p style={{ color: "#94a3b8", fontSize: ".8rem" }}>
              No templates yet. Run the DB migration to create default templates.
            </p>
          )}
          {templates.map(t => (
            <button key={t.id} onClick={() => selectTemplate(t)}
              style={{
                width: "100%", textAlign: "left", padding: "8px 10px", borderRadius: 8,
                marginBottom: 4, fontFamily: "inherit", fontSize: ".78rem",
                background: selected === t.id ? "rgba(99,102,241,.12)" : "var(--surface2,#f8fafc)",
                border: `1px solid ${selected === t.id ? "#6366f1" : "var(--border,#e5e7eb)"}`,
                cursor: "pointer", fontWeight: selected === t.id ? 700 : 400,
              }}>
              {t.display_name}
              <div style={{ fontSize: ".65rem", color: "#94a3b8", marginTop: 1 }}>v{t.active_version}/{t.latest_version}</div>
            </button>
          ))}
        </div>

        <div>
          {!selected && <p style={{ color: "#94a3b8", textAlign: "center", padding: "32px 0" }}>Select a template</p>}
          {selected && tmpl && (
            <div style={card}>
              <h3 style={{ margin: "0 0 8px", fontSize: ".9rem", fontWeight: 800 }}>
                {tmpl.display_name} <span style={{ fontSize: ".72rem", color: "#94a3b8", fontWeight: 400 }}>Active: v{tmpl.active_version}</span>
              </h3>
              <SaveBanner msg={banner.msg} error={banner.error} onClose={() => setBanner({ msg: null, error: null })} />
              <div style={{ marginBottom: 10 }}>
                <label style={{ fontSize: ".75rem", fontWeight: 600, display: "block", marginBottom: 3 }}>System Prompt</label>
                <textarea
                  value={form.system_prompt}
                  onChange={e => setForm(f => ({ ...f, system_prompt: e.target.value }))}
                  rows={6}
                  style={{ ...inp, resize: "vertical", fontFamily: "monospace", fontSize: ".75rem" }}
                />
              </div>
              <div style={{ marginBottom: 10 }}>
                <label style={{ fontSize: ".75rem", fontWeight: 600, display: "block", marginBottom: 3 }}>User Prompt Template</label>
                <textarea
                  value={form.user_prompt}
                  onChange={e => setForm(f => ({ ...f, user_prompt: e.target.value }))}
                  rows={8}
                  style={{ ...inp, resize: "vertical", fontFamily: "monospace", fontSize: ".75rem" }}
                />
              </div>
              <div style={{ marginBottom: 10 }}>
                <label style={{ fontSize: ".75rem", fontWeight: 600, display: "block", marginBottom: 3 }}>Change Summary (optional)</label>
                <input type="text" value={form.change_summary}
                  onChange={e => setForm(f => ({ ...f, change_summary: e.target.value }))}
                  placeholder="e.g. Improved clarity of instructions" style={inp} />
              </div>
              <button onClick={handleSave} disabled={saving}
                style={{ ...btn, background: "#6366f1", color: "#fff" }}>
                {saving ? "Saving…" : "Save as New Version"}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Tab 4: Knowledge Sources
// ─────────────────────────────────────────────────────────────────────────────
function KnowledgeSourcesTab() {
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getKnowledgeSources().then(d => setSources(d?.sources || [])).catch(() => {}).finally(() => setLoading(false));
  }, []);

  if (loading) return <p style={{ color: "#94a3b8" }}>Loading…</p>;

  return (
    <div data-testid="tab-knowledge">
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(280px,1fr))", gap: 12 }}>
        {sources.map(s => (
          <div key={s.key} style={{ ...card, marginBottom: 0 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 6 }}>
              <strong style={{ fontSize: ".85rem" }}>{s.display_name}</strong>
              {s.status === "coming_soon"
                ? <span style={{ fontSize: ".68rem", padding: "2px 8px", borderRadius: 8, background: "rgba(99,102,241,.1)", color: "#6366f1", fontWeight: 700 }}>Coming Soon</span>
                : <StatusBadge ok={s.status === "active"} label={s.status === "active" ? "Active" : s.status} />
              }
            </div>
            <p style={{ margin: 0, fontSize: ".75rem", color: "#64748b" }}>{s.description}</p>
            {s.document_count !== undefined && (
              <div style={{ marginTop: 6, fontSize: ".72rem", color: "#94a3b8" }}>
                {s.document_count} document chunks indexed
              </div>
            )}
            {s.action === "coming_soon" && (
              <div style={{ marginTop: 8, fontSize: ".72rem", color: "#6366f1", fontStyle: "italic" }}>
                This feature is planned for a future release.
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Tab 5: Generation Jobs
// ─────────────────────────────────────────────────────────────────────────────
function GenerationJobsTab() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getGenerationJobs(50).then(d => setJobs(d?.jobs || [])).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const statusColor = { queued:"#6366f1", running:"#b45309", completed:"#166534", failed:"#dc2626", cancelled:"#64748b" };

  if (loading) return <p style={{ color: "#94a3b8" }}>Loading…</p>;

  return (
    <div data-testid="tab-jobs">
      {jobs.length === 0 && (
        <div style={{ textAlign: "center", color: "#94a3b8", padding: "40px 0" }}>
          No generation jobs yet. Jobs appear here when you run Lesson Repair, Prewarm, or other AI tasks.
        </div>
      )}
      {jobs.length > 0 && (
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: ".78rem" }}>
          <thead>
            <tr style={{ color: "#64748b", borderBottom: "1px solid var(--border,#e5e7eb)" }}>
              {["Job Type", "Status", "Provider/Model", "Items", "Score", "Started", "Completed"].map(h => (
                <th key={h} style={{ textAlign: "left", padding: "6px 8px", fontWeight: 600 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {jobs.map(j => (
              <tr key={j.id} style={{ borderBottom: "1px solid var(--border,#f1f5f9)" }}>
                <td style={{ padding: "6px 8px" }}>{j.job_type?.replace(/_/g, " ")}</td>
                <td style={{ padding: "6px 8px" }}>
                  <span style={{ color: statusColor[j.status] || "#64748b", fontWeight: 700, fontSize: ".72rem" }}>
                    {j.status}
                  </span>
                </td>
                <td style={{ padding: "6px 8px", color: "#64748b" }}>{j.provider_key}/{j.model_used || "—"}</td>
                <td style={{ padding: "6px 8px" }}>{j.completed_items}/{j.total_items}</td>
                <td style={{ padding: "6px 8px" }}>{j.validation_score != null ? `${j.validation_score}%` : "—"}</td>
                <td style={{ padding: "6px 8px", color: "#94a3b8" }}>{j.started_at?.slice(0,16) || "—"}</td>
                <td style={{ padding: "6px 8px", color: "#94a3b8" }}>{j.completed_at?.slice(0,16) || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Tab 6: Usage & Costs
// ─────────────────────────────────────────────────────────────────────────────
function UsageTab() {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(30);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const d = await getUsageSummary(days);
      setSummary(d || null);
    } catch { /* */ }
    finally { setLoading(false); }
  }, [days]);

  useEffect(() => { load(); }, [load]);

  if (loading) return <p style={{ color: "#94a3b8" }}>Loading…</p>;

  return (
    <div data-testid="tab-usage">
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
        <label style={{ fontSize: ".8rem", fontWeight: 600 }}>Period:</label>
        {[7, 30, 90].map(d => (
          <button key={d} onClick={() => setDays(d)}
            style={{ ...btn, background: days === d ? "#6366f1" : "var(--surface2,#f8fafc)",
              color: days === d ? "#fff" : "var(--text,#374151)",
              border: `1px solid ${days === d ? "#6366f1" : "var(--border,#e5e7eb)"}`,
              padding: "5px 12px" }}>
            {d}d
          </button>
        ))}
      </div>

      {summary && (
        <>
          {summary.cost_note && (
            <div style={{ padding: "8px 12px", borderRadius: 8, marginBottom: 12,
              background: "rgba(34,197,94,.06)", border: "1px solid rgba(34,197,94,.2)",
              fontSize: ".78rem", color: "#166534" }}>
              ✓ {summary.cost_note}
            </div>
          )}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(160px,1fr))", gap: 10, marginBottom: 16 }}>
            {[
              { label: "Total Requests", value: summary.total_requests?.toLocaleString() || "0" },
              { label: "Today", value: summary.today_requests?.toLocaleString() || "0" },
              { label: "Total Tokens", value: summary.total_tokens?.toLocaleString() || "0" },
              { label: "Est. Cost (USD)", value: `$${(summary.estimated_cost_usd || 0).toFixed(4)}` },
              { label: "Provider", value: summary.provider || "—" },
              { label: "Model", value: (summary.model || "—").slice(0, 20) },
            ].map(({ label, value }) => (
              <div key={label} style={{ ...card, marginBottom: 0, textAlign: "center", padding: "12px 14px" }}>
                <div style={{ fontSize: "1.2rem", fontWeight: 800, color: "var(--text,#1e293b)" }}>{value}</div>
                <div style={{ fontSize: ".7rem", color: "#64748b", marginTop: 2 }}>{label}</div>
              </div>
            ))}
          </div>

          {(summary.by_feature || []).length > 0 && (
            <div style={card}>
              <h4 style={{ margin: "0 0 10px", fontSize: ".85rem", fontWeight: 700 }}>By Feature (top 10)</h4>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: ".78rem" }}>
                <thead>
                  <tr style={{ color: "#64748b", borderBottom: "1px solid var(--border,#e5e7eb)" }}>
                    <th style={{ textAlign: "left", padding: "4px 6px" }}>Feature</th>
                    <th style={{ textAlign: "right", padding: "4px 6px" }}>Requests</th>
                    <th style={{ textAlign: "right", padding: "4px 6px" }}>Tokens</th>
                    <th style={{ textAlign: "right", padding: "4px 6px" }}>Cost</th>
                  </tr>
                </thead>
                <tbody>
                  {(summary.by_feature || []).map(f => (
                    <tr key={f.feature_key} style={{ borderBottom: "1px solid var(--border,#f1f5f9)" }}>
                      <td style={{ padding: "4px 6px" }}>{f.feature_key}</td>
                      <td style={{ padding: "4px 6px", textAlign: "right" }}>{f.requests}</td>
                      <td style={{ padding: "4px 6px", textAlign: "right" }}>{f.tokens?.toLocaleString()}</td>
                      <td style={{ padding: "4px 6px", textAlign: "right" }}>${(f.cost || 0).toFixed(5)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Tab 7: Quality Metrics
// ─────────────────────────────────────────────────────────────────────────────
function QualityMetricsTab() {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getQualityMetrics().then(d => setMetrics(d || null)).catch(() => {}).finally(() => setLoading(false));
  }, []);

  if (loading) return <p style={{ color: "#94a3b8" }}>Loading…</p>;

  const pct = (v) => v != null ? `${v}%` : "N/A";
  const score = (v) => v != null ? `${v}/100` : "N/A";

  return (
    <div data-testid="tab-quality">
      {metrics?.note && (
        <p style={{ fontSize: ".78rem", color: "#94a3b8", marginBottom: 12 }}>{metrics.note}</p>
      )}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(180px,1fr))", gap: 10, marginBottom: 16 }}>
        {[
          { label: "Repair Success Rate", value: pct(metrics?.repair_success_rate) },
          { label: "Validation Failure Rate", value: pct(metrics?.validation_failure_rate) },
          { label: "Avg Score Before Repair", value: score(metrics?.avg_before_score) },
          { label: "Avg Score After Repair", value: score(metrics?.avg_after_score) },
          { label: "Formula Pass Rate", value: pct(metrics?.formula_validation_pass_rate) },
          { label: "MCQ Pass Rate", value: pct(metrics?.mcq_validation_pass_rate) },
        ].map(({ label, value }) => (
          <div key={label} style={{ ...card, marginBottom: 0, textAlign: "center", padding: "12px 14px" }}>
            <div style={{ fontSize: "1.3rem", fontWeight: 800, color: value === "N/A" ? "#94a3b8" : "var(--text,#1e293b)" }}>
              {value}
            </div>
            <div style={{ fontSize: ".7rem", color: "#64748b", marginTop: 2 }}>{label}</div>
          </div>
        ))}
      </div>
      {metrics?.repair_success_rate == null && (
        <div style={{ textAlign: "center", color: "#94a3b8", fontSize: ".85rem", padding: "20px 0" }}>
          No repair data yet. Quality metrics appear after running Lesson Repair jobs.
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Main Page
// ─────────────────────────────────────────────────────────────────────────────
export default function AdminAIStudioPage({ user }) { // eslint-disable-line no-unused-vars
  const [activeTab, setActiveTab] = useState("providers");

  const tabContent = {
    providers:  <ProvidersTab />,
    routing:    <ModelRoutingTab />,
    prompts:    <PromptTemplatesTab />,
    knowledge:  <KnowledgeSourcesTab />,
    jobs:       <GenerationJobsTab />,
    usage:      <UsageTab />,
    quality:    <QualityMetricsTab />,
  };

  return (
    <div data-testid="admin-ai-studio-page" style={{ maxWidth: 1100, margin: "0 auto", padding: "0 14px 60px", fontFamily: "inherit" }}>
      <div style={{ marginBottom: 16 }}>
        <h2 style={{ margin: "0 0 4px", fontSize: "1.05rem", fontWeight: 800 }}>🎛️ AI Studio</h2>
        <p style={{ margin: 0, fontSize: ".82rem", color: "#64748b" }}>
          Configure AI providers, model routing, prompt templates, and monitor usage and quality.
        </p>
      </div>

      {/* Tabs */}
      <div style={{ display: "flex", gap: 4, flexWrap: "wrap", marginBottom: 20, borderBottom: "1px solid var(--border,#e5e7eb)", paddingBottom: 4 }}>
        {TABS.map(t => (
          <button
            key={t.key}
            data-testid={`ai-studio-tab-${t.key}`}
            onClick={() => setActiveTab(t.key)}
            style={{
              display: "flex", alignItems: "center", gap: 5,
              padding: "7px 14px", borderRadius: "8px 8px 0 0", border: "none",
              fontFamily: "inherit", fontSize: ".8rem", fontWeight: 600, cursor: "pointer",
              background: activeTab === t.key ? "var(--panel,#fff)" : "transparent",
              color: activeTab === t.key ? "#6366f1" : "var(--text-muted,#64748b)",
              borderBottom: activeTab === t.key ? "2px solid #6366f1" : "2px solid transparent",
            }}
          >
            <t.Icon size={13} strokeWidth={2} />{t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div>
        {tabContent[activeTab]}
      </div>
    </div>
  );
}
