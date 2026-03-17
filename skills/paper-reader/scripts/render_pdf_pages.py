#!/usr/bin/env python3
"""Render all pages of a PDF to high-resolution PNGs using pdftoppm.

Usage:
    python3 render_pdf_pages.py <pdf_path> <output_dir> [--dpi 300] [--pages 1-5]

Output:
    <output_dir>/page01.png, page02.png, ...
"""
import argparse
import os
import subprocess
import sys
import shutil


def find_pdftoppm():
    """Find pdftoppm binary, checking common locations."""
    path = shutil.which("pdftoppm")
    if path:
        return path
    for candidate in ["/opt/homebrew/bin/pdftoppm", "/usr/local/bin/pdftoppm", "/usr/bin/pdftoppm"]:
        if os.path.isfile(candidate):
            return candidate
    return None


def render_pages(pdf_path, output_dir, dpi=300, pages=None):
    pdftoppm = find_pdftoppm()
    if not pdftoppm:
        print("ERROR: pdftoppm not found. Install poppler:")
        print("  macOS:  brew install poppler")
        print("  Ubuntu: sudo apt-get install poppler-utils")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)

    cmd = [pdftoppm, "-r", str(dpi), "-png"]
    if pages:
        first, last = (pages.split("-") + [None])[:2]
        cmd += ["-f", first]
        if last:
            cmd += ["-l", last]

    cmd += [pdf_path, os.path.join(output_dir, "page")]
    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)

    rendered = sorted(f for f in os.listdir(output_dir) if f.startswith("page") and f.endswith(".png"))
    print(f"Rendered {len(rendered)} page(s) to {output_dir}/")
    for f in rendered:
        print(f"  {f}")
    return rendered


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Render PDF pages to PNG")
    parser.add_argument("pdf_path", help="Path to the PDF file")
    parser.add_argument("output_dir", help="Directory for output PNGs")
    parser.add_argument("--dpi", type=int, default=300, help="Resolution (default: 300)")
    parser.add_argument("--pages", help="Page range, e.g. '1-5' or '3'")
    args = parser.parse_args()
    render_pages(args.pdf_path, args.output_dir, args.dpi, args.pages)
