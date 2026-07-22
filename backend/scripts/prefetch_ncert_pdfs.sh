#!/bin/bash
# Pre-fetch NCERT chapter PDFs for fix_grade1112_hindi_rag.py.
# Run this via the Bash tool directly (not from inside the python pipeline —
# curl's SSL breaks there once app service modules are imported).
CACHE_DIR="/private/tmp/claude-501/-Users-pradipbhuyan-likha-poha-ai/faba8cd3-1c9e-44e5-9056-9a35860f5710/scratchpad/ncert_toc"
mkdir -p "$CACHE_DIR"
BASE="https://ncert.nic.in/textbook/pdf"
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
REF="https://ncert.nic.in/textbook.php"

fetch() {
  local code=$1 num=$2
  local fname="${code}$(printf '%02d' "$num").pdf"
  local path="$CACHE_DIR/$fname"
  if [ -f "$path" ] && [ "$(wc -c < "$path")" -gt 100 ]; then
    echo "  [cached] $fname"
    return
  fi
  local http=""
  for attempt in 1 2 3; do
    http=$(curl -sk --connect-timeout 20 --max-time 60 -H "User-Agent: $UA" -H "Referer: $REF" -o "$path" -w "%{http_code}" "$BASE/$fname" 2>/dev/null || echo "000")
    [ "$http" = "200" ] && break
    sleep 1
  done
  if [ "$http" = "200" ]; then
    echo "  [ok] $fname ($(wc -c < "$path") bytes)"
  else
    echo "  [FAIL $http] $fname"
    rm -f "$path"
  fi
}

echo "=== khar1 (Grade 11 Aroh, 16 ch) ==="
for n in $(seq 1 16); do fetch khar1 $n; done

echo "=== lhar1 (Grade 12 Aroh, 15 ch) ==="
for n in $(seq 1 15); do fetch lhar1 $n; done

echo "=== khvt1 (Grade 11 Vitan, 3 ch used) ==="
for n in $(seq 1 3); do fetch khvt1 $n; done

echo "=== lhvt1 (Grade 12 Vitan, 3 ch) ==="
for n in $(seq 1 3); do fetch lhvt1 $n; done

echo "done"
