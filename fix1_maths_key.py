#!/usr/bin/env python3
"""Fix 1: Rename 'Maths' key to 'Mathematics' inside GRADE_11_RESOURCES."""
FILE = "/Users/a0247716/Pradips_Project/cbse-tutor-platform/backend/app/data/resources.py"

with open(FILE, encoding="utf-8") as f:
    s = f.read()

g11s = s.find("GRADE_11_RESOURCES: dict")
g11e = s.find("GRADE_RESOURCES_MAP", g11s)
block = s[g11s:g11e]

parts = block.rsplit('"Maths": {', 1)
if len(parts) == 2:
    block = parts[0] + '"Mathematics": {' + parts[1]
    s = s[:g11s] + block + s[g11e:]
    with open(FILE, "w", encoding="utf-8") as f:
        f.write(s)
    print("OK: Renamed 'Maths' -> 'Mathematics' in GRADE_11_RESOURCES")
else:
    print("SKIP: 'Maths' key not found in GRADE_11_RESOURCES block")
