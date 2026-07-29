#!/usr/bin/env python3
"""Fix: Add 'Semiconductor Electronics' alias and improve prefix matching."""
import sys
sys.path.insert(0, 'backend')

FILE = "backend/app/data/resources.py"
with open(FILE, encoding="utf-8") as f:
    src = f.read()

# ── 1. Improve fuzzy matcher with prefix matching ──────────────────────────────
old_fuzzy = (
    "    # Priority 1b: Fuzzy match for chapter name variants (e.g. plural/singular, extra words)\n"
    "    if not resources and grade_map.get(subject):\n"
    "        import difflib as _dl\n"
    "        subject_map = grade_map[subject]\n"
    "        close = _dl.get_close_matches(cleaned_chapter, subject_map.keys(), n=1, cutoff=0.82)\n"
    "        if close:\n"
    "            resources = subject_map[close[0]]"
)
new_fuzzy = (
    "    # Priority 1b: Fuzzy/prefix match for chapter name variants\n"
    "    if not resources and grade_map.get(subject):\n"
    "        import difflib as _dl\n"
    "        subject_map = grade_map[subject]\n"
    "        ch_lower = cleaned_chapter.lower()\n"
    "        # Prefix match: 'Semiconductor Electronics' -> 'Semiconductor Electronics: ...'\n"
    "        prefix_match = next(\n"
    "            (k for k in subject_map if k.lower().startswith(ch_lower) or ch_lower.startswith(k.lower()[:28])),\n"
    "            None\n"
    "        )\n"
    "        if prefix_match:\n"
    "            resources = subject_map[prefix_match]\n"
    "        else:\n"
    "            close = _dl.get_close_matches(cleaned_chapter, subject_map.keys(), n=1, cutoff=0.82)\n"
    "            if close:\n"
    "                resources = subject_map[close[0]]"
)

if old_fuzzy in src:
    src = src.replace(old_fuzzy, new_fuzzy, 1)
    print("Updated fuzzy matcher with prefix match")
else:
    print("ERROR: fuzzy matcher pattern not found")

with open(FILE, "w", encoding="utf-8") as f:
    f.write(src)
print("File saved.")

# ── 2. Verify ──────────────────────────────────────────────────────────────────
import importlib, app.data.resources as r
importlib.reload(r)
from app.data.resources import get_learning_resources

res = get_learning_resources("Physics", "Semiconductor Electronics", "Grade 12")
fb = "YouTube Search" in res[0].get("title", "")
print(f"'Semiconductor Electronics' lookup: {'FALLBACK' if fb else 'OK'}")
if not fb:
    print(f"  slot[0]: {res[0]['title'][:65]}")

res2 = get_learning_resources("Physics", "Semiconductor Electronics: Materials, Devices and Simple Circuits", "Grade 12")
fb2 = "YouTube Search" in res2[0].get("title", "")
print(f"Full key lookup: {'FALLBACK' if fb2 else 'OK'}")
