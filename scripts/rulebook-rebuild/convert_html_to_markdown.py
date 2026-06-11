#!/usr/bin/env python3
"""Convert extracted GBK HTML files to UTF-8 GFM Markdown using pandoc."""

import subprocess
import os
import re
import sys
from pathlib import Path

ROOT = Path("/home/hcc/projects/dnd-combat-sim/rulebook-clean")
SRC = ROOT / "_extracted_html"
DEST = ROOT / "books"

# Books organization: directory name → (category, ruleset)
# Derived from the original CLAUDE.md structure
BOOK_MAP = {
    "玩家手册2024": ("2024-core", "2024"),
    "城主指南2024": ("2024-core", "2024"),
    "怪物图鉴2025": ("2024-core", "2024"),
    "玩家手册": ("legacy-core", "2014"),
    "城主指南": ("legacy-core", "2014"),
    "怪物图鉴": ("legacy-core", "2014"),
    "贤者谏言2025": ("faq", "2024"),
    "速查": ("quick-reference", "2024"),
}

# Skip these - not rule content
SKIP_FILES = {
    "鸣谢列表.htm", "写在前面.html", "旧版说明.htm", "分隔符.htm",
    "更新日志.html", "style.css", "hhc_toc.json",
}

SKIP_DIRS = {"$WWAssociativeLinks", "$WWKeywordLinks", "#System"}

def detect_book_info(rel_path: Path) -> tuple:
    """Determine category and ruleset from path."""
    parts = rel_path.parts
    if len(parts) >= 1:
        book = parts[0]
        if book in BOOK_MAP:
            return BOOK_MAP[book]
    # Heuristic: files under directories with 2024/2025 in name
    for part in parts:
        if "2024" in part or "2025" in part:
            return ("2024-core", "2024")
    return ("legacy-supplements", "2014")

def convert_file(html_path: Path, md_path: Path, book: str, category: str, ruleset: str):
    """Convert one HTML file to Markdown with frontmatter."""
    try:
        # Read GBK HTML and convert to UTF-8
        raw = html_path.read_bytes()
        # Try GBK first, fall back to UTF-8
        try:
            html = raw.decode("gbk")
        except (UnicodeDecodeError, LookupError):
            try:
                html = raw.decode("gb2312")
            except (UnicodeDecodeError, LookupError):
                html = raw.decode("utf-8", errors="replace")

        # Get title from <title> tag
        title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
        title = title_match.group(1).strip() if title_match else html_path.stem

        # Remove CHM-specific metadata comments
        html = re.sub(r'<!--\s*coding:\s*gbk\s*-->', '', html, flags=re.IGNORECASE)

        # Write temp UTF-8 HTML for pandoc
        md_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = md_path.with_suffix(".tmp.html")
        tmp.write_text(html, encoding="utf-8")

        # Convert with pandoc
        result = subprocess.run(
            ["pandoc", "-f", "html", "-t", "gfm",
             "--wrap=none", "--markdown-headings=atx",
             str(tmp)],
            capture_output=True, text=True, timeout=30
        )

        if result.returncode != 0:
            # Fallback: just use the text content
            md_body = html
        else:
            md_body = result.stdout

        # Clean up pandoc output
        md_body = re.sub(r'\{#.*?\}', '', md_body)  # Remove anchor spans
        md_body = re.sub(r'<u>(.*?)</u>', r'*\1*', md_body)  # Convert underline to italic

        # Build frontmatter
        frontmatter = f"""---
title: "{title}"
source_collection: "DND五版不全书v2026.02.12"
book: "{book}"
ruleset: "{ruleset}"
category: "{category}"
---

"""
        # Write output
        md_path.write_text(frontmatter + md_body, encoding="utf-8")

        # Cleanup temp
        tmp.unlink()

        return True, title

    except Exception as e:
        return False, str(e)

def main():
    print("Converting HTML → Markdown...")
    count = 0
    errors = 0

    for html_file in sorted(SRC.rglob("*")):
        if not html_file.is_file():
            continue
        if html_file.suffix.lower() not in (".htm", ".html"):
            continue
        if html_file.name in SKIP_FILES:
            continue

        rel = html_file.relative_to(SRC)
        # Skip system directories
        if any(p in SKIP_DIRS for p in rel.parts):
            continue

        book = rel.parts[0] if len(rel.parts) > 0 else "other"
        category, ruleset = detect_book_info(rel)

        # Determine output path
        md_rel = Path(category) / rel.with_suffix(".md")
        md_path = DEST / md_rel

        ok, msg = convert_file(html_file, md_path, book, category, ruleset)
        if ok:
            count += 1
        else:
            errors += 1
            if errors <= 10:
                print(f"  ✗ {rel}: {msg}")

        if count % 500 == 0:
            print(f"  ... {count} files")

    print(f"\n✅ {count} files converted, {errors} errors")
    print(f"📁 Output: {DEST}")

if __name__ == "__main__":
    main()
