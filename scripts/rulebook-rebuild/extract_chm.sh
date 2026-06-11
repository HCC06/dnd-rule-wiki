#!/bin/bash
# Extract CHM file to raw HTML
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
CHM="$ROOT/DND五版不全书v2026.02.12.chm"
OUT="$ROOT/_extracted_html"
rm -rf "$OUT"
mkdir -p "$OUT"
echo "Extracting CHM..."
7z x -o"$OUT" "$CHM" -y > /dev/null
echo "Done: $(find "$OUT" -name '*.htm' -o -name '*.html' | wc -l) HTML files extracted"
