"""
Test all NVIDIA NIM models in parallel to find which ones work on this account.
Run: python3 scripts/test_nvidia_models.py
"""
import sys
import os
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI
from app.services.openai_service import get_effective_settings

s = get_effective_settings()
key = s.get("nvidia_api_key") or os.environ.get("NVIDIA_API_KEY", "")
print(f"Key: {key[:15]}...\n")

MODELS = [
    "meta/llama-3.1-8b-instruct",
    "meta/llama-3.1-70b-instruct",
    "meta/llama-3.2-3b-instruct",
    "meta/llama-4-scout-17b-16e-instruct",
    "deepseek-ai/deepseek-v4-flash",
    "google/gemma-3-4b-it",
    "google/gemma-3-12b-it",
    "google/gemma-4-31b-it",
]

results = {}
lock = threading.Lock()


def test_model(model):
    client = OpenAI(
        api_key=key,
        base_url="https://integrate.api.nvidia.com/v1",
        timeout=15.0,
    )
    try:
        r = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Reply with just: OK"}],
            max_tokens=5,
            temperature=0.1,
        )
        reply = r.choices[0].message.content.strip()[:20]
        with lock:
            results[model] = ("✅", reply)
    except Exception as e:
        with lock:
            results[model] = ("❌", str(e)[:120])


threads = [threading.Thread(target=test_model, args=(m,), daemon=True) for m in MODELS]
for t in threads:
    t.start()
for t in threads:
    t.join(timeout=18)

print("═" * 65)
working = []
failing = []
for m in MODELS:
    status, detail = results.get(m, ("⏳", "timed out — no response in 18s"))
    if status == "✅":
        working.append(m)
        print(f"✅  {m}")
        print(f"     reply: {detail!r}")
    elif status == "⏳":
        failing.append(m)
        print(f"⏳  {m}")
        print(f"     └─ {detail}")
    else:
        failing.append(m)
        print(f"❌  {m}")
        print(f"     └─ {detail}")

print("\n" + "═" * 65)
print(f"\n{'✅ WORKING (' + str(len(working)) + ')':}")
for m in working:
    print(f"  • {m}")
print(f"\n{'❌ FAILING (' + str(len(failing)) + ')':}")
for m in failing:
    print(f"  • {m}")
