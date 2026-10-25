# AI Provider Model Catalog

**Last reviewed:** 2026-10-25

This is the allowlisted catalog used by **Admin → AI & Settings**. The backend rejects provider/model combinations outside this list. “Free” means the provider offers a free tier; rate, token, availability, and account limits remain controlled by each provider and can change.

## Free-tier provider models

| Provider | Allowlisted models |
|---|---|
| Groq | `llama-3.3-70b-versatile`, `llama-3.1-8b-instant` |
| Cerebras | `gpt-oss-120b`, `zai-glm-4.7` |
| Google Gemini | `gemini-2.5-flash` |
| SambaNova | `Meta-Llama-3.3-70B-Instruct`, `DeepSeek-V3.2`, `DeepSeek-V3.1`, `gemma-4-31B-it`, `gpt-oss-120b` |
| NVIDIA NIM | `meta/llama-4-scout-17b-16e-instruct` |
| Ollama Cloud | `gemma3:4b`, `gemma3:12b`, `gpt-oss:20b` |

## OpenAI exceptions requested for the admin catalog

| Provider | Allowlisted models | Billing status |
|---|---|---|
| OpenAI | `gpt-4`, `gpt-5-nano` | **Paid API usage** — not a free-tier offering |

GPT-4 and GPT-5 Nano are deliberately retained in the selector as requested. They must not be described as free models. The OpenAI project/API key must have access and billing configured for the selected model.

## Excluded providers and models

- **Venice AI** is excluded because the configured models consume Venice credits rather than qualifying as reviewed free-tier options.
- Gemini paid models, including Gemini Pro, are excluded.
- SambaNova paid models, including MiniMax, are excluded.
- Premium Ollama Cloud models are excluded.
- NVIDIA models not confirmed for the reviewed free-tier account are excluded.
- Deprecated and unavailable model IDs are excluded.

## Enforcement

The catalog is defined in:

```text
backend/app/routes/admin_ai_settings.py
```

The admin UI only renders the same reviewed choices, while the backend validates every save request. This prevents stale browser state, direct API requests, or legacy database values from reintroducing unreviewed model selections.
