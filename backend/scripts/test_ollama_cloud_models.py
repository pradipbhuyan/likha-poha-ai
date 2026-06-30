#!/usr/bin/env python3
"""
test_ollama_cloud_models.py
───────────────────────────
Tests all Ollama Cloud free-tier models with a real lesson-generation prompt.
Fetches the Ollama Cloud API key from the DB (admin_settings.ai_settings).

Usage:
    cd backend
    python3 scripts/test_ollama_cloud_models.py
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests

BASE_URL = "https://api.ollama.com"

# Free-tier confirmed models + some premium ones to test
MODELS_TO_TEST = [
    ("gemma3:4b",    "Free tier"),
    ("gemma3:12b",   "Free tier"),
    ("gpt-oss:20b",  "Free tier"),
    ("glm-5.2",      "Premium (may need subscription)"),
    ("minimax-m2.1", "Premium (may need subscription)"),
    ("kimi-k2.6",    "Premium (may need subscription)"),
]

SYSTEM_PROMPT = (
    "You are an expert CBSE educator. Write clear, accurate lesson content "
    "for the specified topic."
)

# Short prompt to test speed without generating full lesson
USER_PROMPT = (
    "Write a 2-sentence introduction to the topic: "
    "Force and Laws of Motion — CBSE Grade 9 Science. "
    "Be concise and accurate."
)


def get_ollama_api_key() -> str:
    """Fetch the Ollama Cloud API key from admin_settings in Supabase."""
    try:
        from app.services.auth_service import admin_client
        resp = (
            admin_client.table("admin_settings")
            .select("value")
            .eq("key", "ai_settings")
            .limit(1)
            .execute()
        )
        if resp.data:
            val = resp.data[0].get("value") or {}
            key = val.get("ollama_cloud_api_key", "")
            if key:
                return key
    except Exception as e:
        print(f"  Could not load key from DB: {e}")
    return ""


def test_model(api_key: str, model: str, tier_note: str) -> dict:
    """Test a single Ollama Cloud model. Returns result dict."""
    t0 = time.perf_counter()
    try:
        r = requests.post(
            f"{BASE_URL}/api/chat",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "stream": False,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": USER_PROMPT},
                ],
            },
            timeout=60,
        )
        latency_ms = round((time.perf_counter() - t0) * 1000)

        if r.status_code == 200:
            data = r.json()
            content = (data.get("message") or {}).get("content", "")
            return {
                "model": model,
                "tier": tier_note,
                "status": "✅ OK",
                "latency_ms": latency_ms,
                "preview": content[:120].replace("\n", " "),
                "error": None,
            }
        elif r.status_code == 403:
            err = r.json().get("error", "")
            msg = "Subscription required" if "subscription" in err.lower() else f"Forbidden: {err}"
            return {"model": model, "tier": tier_note, "status": "⛔ 403", "latency_ms": latency_ms, "preview": "", "error": msg}
        elif r.status_code == 404:
            return {"model": model, "tier": tier_note, "status": "❌ 404", "latency_ms": latency_ms, "preview": "", "error": "Model not found"}
        else:
            return {"model": model, "tier": tier_note, "status": f"❌ {r.status_code}", "latency_ms": latency_ms, "preview": "", "error": r.text[:100]}

    except requests.exceptions.Timeout:
        latency_ms = round((time.perf_counter() - t0) * 1000)
        return {"model": model, "tier": tier_note, "status": "⏱ TIMEOUT", "latency_ms": latency_ms, "preview": "", "error": "60s timeout exceeded"}
    except Exception as e:
        latency_ms = round((time.perf_counter() - t0) * 1000)
        return {"model": model, "tier": tier_note, "status": "❌ ERROR", "latency_ms": latency_ms, "preview": "", "error": str(e)[:100]}


def main():
    print("=" * 65)
    print("Ollama Cloud Model Test — Lesson Prewarm Suitability")
    print("=" * 65)

    print("\nFetching Ollama Cloud API key from DB…")
    api_key = get_ollama_api_key()
    if not api_key:
        print("ERROR: No Ollama Cloud API key found in admin_settings.")
        print("Set it in AI Studio → Providers → Ollama Cloud → Save Configuration")
        sys.exit(1)
    print(f"Key loaded: {api_key[:4]}••••{api_key[-4:]}\n")

    results = []
    for model, tier in MODELS_TO_TEST:
        print(f"  Testing {model} ({tier})…", end="", flush=True)
        result = test_model(api_key, model, tier)
        results.append(result)
        print(f" {result['status']} [{result['latency_ms']}ms]")

    print("\n" + "=" * 65)
    print("RESULTS SUMMARY")
    print("=" * 65)
    print(f"{'Model':<22} {'Tier':<30} {'Status':<12} {'Latency'}")
    print("-" * 65)
    for r in results:
        print(f"{r['model']:<22} {r['tier']:<30} {r['status']:<12} {r['latency_ms']}ms")
        if r["error"]:
            print(f"  └─ {r['error']}")
        elif r["preview"]:
            print(f"  └─ \"{r['preview']}\"")

    # Recommendation
    working = [r for r in results if r["status"] == "✅ OK"]
    print("\n" + "=" * 65)
    if working:
        fastest = min(working, key=lambda x: x["latency_ms"])
        print("RECOMMENDATION for lesson prewarm:")
        for r in sorted(working, key=lambda x: x["latency_ms"]):
            print(f"  ✅ {r['model']} — {r['latency_ms']}ms ({r['tier']})")
        print(f"\n  Best choice: {fastest['model']} ({fastest['latency_ms']}ms)")
        print(f"\n  Set in AI Studio → Providers → Ollama Cloud → Model field → Save")
    else:
        print("No Ollama Cloud models responded successfully.")
        print("Recommendation: Switch primary provider to Groq or Gemini.")
        print("  Groq:   llama-3.3-70b-versatile (14,400 req/day free)")
        print("  Gemini: gemini-2.5-flash (1M tokens/day free)")
    print("=" * 65)


if __name__ == "__main__":
    main()
