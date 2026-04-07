#!/usr/bin/env python3
"""Smart figure/table extraction from academic PDFs.

Uses pdfplumber to detect captions, renders only relevant pages via pdftoppm,
and auto-crops each figure/table with heuristic boundary detection.

Usage:
    python3 extract_figures.py <pdf_path> <output_dir> [--dpi 300]

Output:
    <output_dir>/figures/fig1_xxx.png, table2_xxx.png, ...
    <output_dir>/figures/manifest.json
    <output_dir>/pages/page-XX.png  (only pages containing figures)

Dependencies:
    pip install pdfplumber Pillow
    brew install poppler  (for pdftoppm)
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Tuple

try:
    import pdfplumber
except ImportError:
    print("ERROR: pdfplumber not installed. Run: pip install pdfplumber")
    sys.exit(1)

try:
    from PIL import Image
except ImportError:
    print("ERROR: Pillow not installed. Run: pip install Pillow")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class CaptionHit:
    """A detected caption in the PDF."""
    caption_type: str          # "figure", "table", "algorithm"
    number: str                # "1", "2a", etc.
    caption_text: str          # Full caption line
    page_index: int            # 0-based page index
    page_number: int           # 1-based page number
    x0: float                  # PDF-coordinate left edge of caption
    y_top: float               # PDF-coordinate top of caption text
    y_bottom: float            # PDF-coordinate bottom of caption text
    page_width: float
    page_height: float


@dataclass
class FigureRegion:
    """Computed crop region for a figure/table."""
    caption: CaptionHit
    crop_top: float            # PDF y top of crop box
    crop_bottom: float         # PDF y bottom of crop box
    crop_left: float
    crop_right: float
    needs_review: bool = False
    confidence_note: str = ""


@dataclass
class ManifestEntry:
    """One entry in the output manifest.json."""
    filename: str
    caption_type: str
    number: str
    caption_text: str
    page_number: int
    needs_review: bool
    confidence_note: str
    crop_coords_pdf: dict = field(default_factory=dict)   # {left, top, right, bottom} in PDF points
    crop_coords_pixel: dict = field(default_factory=dict)  # pixel coords at render DPI


# ---------------------------------------------------------------------------
# Caption detection
# ---------------------------------------------------------------------------

# Regex patterns for captions.  We look for lines starting with
# "Figure N", "Table N", "Algorithm N" (case-insensitive) possibly
# followed by a colon, period or pipe, then the caption text.
CAPTION_PATTERNS = [
    # Figure 1: ..., Figure 1. ..., Figure 1 | ...
    (r'(?i)^(fig(?:ure)?)\s*\.?\s*(\d+[a-z]?)\s*[:\.\|–—\-]', "figure"),
    # Table 1: ...
    (r'(?i)^(table)\s*\.?\s*(\d+[a-z]?)\s*[:\.\|–—\-]', "table"),
    # Algorithm 1: ...
    (r'(?i)^(algorithm)\s*\.?\s*(\d+[a-z]?)\s*[:\.\|–—\-]', "algorithm"),
    # Fig. 1: ...  (abbreviated)
    (r'(?i)^(fig)\s*\.\s*(\d+[a-z]?)\s*[:\.\|–—\-]', "figure"),
]


def detect_captions(pdf_path: str) -> List[CaptionHit]:
    """Scan all pages for figure/table/algorithm captions using pdfplumber."""
    hits: List[CaptionHit] = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            page_w = float(page.width)
            page_h = float(page.height)

            # Extract words with positional info
            words = page.extract_words(
                x_tolerance=3,
                y_tolerance=3,
                keep_blank_chars=True,
                extra_attrs=["top", "bottom"],
            )
            if not words:
                continue

            # Reconstruct lines by grouping words with similar y-coordinates
            lines = _group_words_into_lines(words)

            for line_text, line_top, line_bottom, line_x0 in lines:
                stripped = line_text.strip()
                for pattern, cap_type in CAPTION_PATTERNS:
                    m = re.match(pattern, stripped)
                    if m:
                        number = m.group(2)
                        hits.append(CaptionHit(
                            caption_type=cap_type,
                            number=number,
                            caption_text=stripped,
                            page_index=page_idx,
                            page_number=page_idx + 1,
                            x0=line_x0,
                            y_top=line_top,
                            y_bottom=line_bottom,
                            page_width=page_w,
                            page_height=page_h,
                        ))
                        break  # one match per line

    return hits


def _group_words_into_lines(
    words: list, y_tolerance: float = 3.0
) -> List[Tuple[str, float, float, float]]:
    """Group words into text lines based on y-coordinate proximity.

    Returns list of (text, top, bottom, x0) tuples.
    """
    if not words:
        return []

    # Sort by top then x
    sorted_words = sorted(words, key=lambda w: (float(w["top"]), float(w["x0"])))

    lines: List[Tuple[str, float, float, float]] = []
    current_line_words = [sorted_words[0]]

    for word in sorted_words[1:]:
        if abs(float(word["top"]) - float(current_line_words[0]["top"])) <= y_tolerance:
            current_line_words.append(word)
        else:
            # Flush current line
            lines.append(_flush_line(current_line_words))
            current_line_words = [word]

    if current_line_words:
        lines.append(_flush_line(current_line_words))

    return lines


def _flush_line(words: list) -> Tuple[str, float, float, float]:
    """Convert a group of words into a single line record."""
    words_sorted = sorted(words, key=lambda w: float(w["x0"]))
    text = " ".join(w["text"] for w in words_sorted)
    top = min(float(w["top"]) for w in words_sorted)
    bottom = max(float(w["bottom"]) for w in words_sorted)
    x0 = float(words_sorted[0]["x0"])
    return text, top, bottom, x0


# ---------------------------------------------------------------------------
# Crop region computation
# ---------------------------------------------------------------------------

def compute_crop_regions(
    captions: List[CaptionHit],
    pdf_path: str,
    margin_expand_ratio: float = 0.15,
) -> List[FigureRegion]:
    """For each caption, compute the bounding box to crop.

    Strategy:
      - Figure/Algorithm: graphic is usually ABOVE the caption.
        Crop from (caption.y_top - generous_region) to caption.y_bottom.
      - Table: caption is usually ABOVE the table content.
        Crop from caption.y_top to (caption.y_bottom + generous_region).
      - Safety margin: expand top and bottom by margin_expand_ratio * page_height.
      - Left/right: use detected page margins or full width with small inset.
    """
    regions: List[FigureRegion] = []

    # Group captions by page for boundary detection
    captions_by_page: dict = {}
    for cap in captions:
        captions_by_page.setdefault(cap.page_index, []).append(cap)

    # Get text blocks for each page to find boundaries
    page_text_blocks = _get_page_text_blocks(pdf_path)

    for cap in captions:
        page_h = cap.page_height
        page_w = cap.page_width
        expand = margin_expand_ratio * page_h

        # Detect left/right margins from page content
        left_margin, right_margin = _detect_lr_margins(
            page_text_blocks.get(cap.page_index, []), page_w
        )

        # Determine crop region based on caption type
        needs_review = False
        confidence_note = ""

        if cap.caption_type in ("figure", "algorithm"):
            # Figure/Algorithm: content is above the caption.
            # Include the full caption (may span multiple lines) plus a buffer.
            crop_bottom = min(cap.y_bottom + 25, page_h)

            # Find the upper boundary: look for previous text block or caption
            upper_bound = _find_upper_boundary(
                cap, captions_by_page.get(cap.page_index, []),
                page_text_blocks.get(cap.page_index, []),
            )
            if upper_bound is not None:
                crop_top = max(upper_bound - 5, 0)
                confidence_note = "bounded by previous text"
            else:
                # Fallback: go up by expand amount or to page top
                crop_top = max(cap.y_top - expand * 2.5, 0)
                needs_review = True
                confidence_note = "no clear upper boundary, used page-top fallback"

            # Enforce a minimum figure height of 150 PDF points (~53 mm).
            # If the detected region is too small, expand upward generously.
            min_fig_height = 150
            if (cap.y_top - crop_top) < min_fig_height:
                crop_top = max(cap.y_top - min_fig_height - expand, 0)
                needs_review = True
                confidence_note = "expanded: detected region too small"

            # Safety expansion
            crop_top = max(crop_top - 20, 0)

        elif cap.caption_type == "table":
            # Table: caption is above, content is below
            crop_top = max(cap.y_top - 10, 0)  # small buffer above caption

            # Find the lower boundary
            lower_bound = _find_lower_boundary(
                cap, captions_by_page.get(cap.page_index, []),
                page_text_blocks.get(cap.page_index, []),
                pdf_path=pdf_path,
            )
            if lower_bound is not None:
                crop_bottom = min(lower_bound + 10, page_h)
                confidence_note = "bounded by next text"
            else:
                # Be generous when no boundary is found — it's better to include
                # extra whitespace than to truncate table content.
                crop_bottom = min(cap.y_bottom + expand * 3, page_h)
                needs_review = True
                confidence_note = "no clear lower boundary, used generous page-bottom fallback"

            # Safety expansion (generous for tables — truncation is worse than extra space)
            crop_bottom = min(crop_bottom + 40, page_h)

        else:
            # Generic fallback
            crop_top = max(cap.y_top - expand, 0)
            crop_bottom = min(cap.y_bottom + expand, page_h)
            needs_review = True
            confidence_note = "unknown caption type, generous fallback"

        regions.append(FigureRegion(
            caption=cap,
            crop_top=crop_top,
            crop_bottom=crop_bottom,
            crop_left=left_margin,
            crop_right=right_margin,
            needs_review=needs_review,
            confidence_note=confidence_note,
        ))

    return regions


def _get_page_text_blocks(pdf_path: str) -> dict:
    """Extract text blocks (lines) per page for boundary detection."""
    blocks: dict = {}
    with pdfplumber.open(pdf_path) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            words = page.extract_words(
                x_tolerance=3, y_tolerance=3,
                keep_blank_chars=True,
                extra_attrs=["top", "bottom"],
            )
            lines = _group_words_into_lines(words)
            blocks[page_idx] = lines
    return blocks


def _detect_lr_margins(
    lines: list, page_width: float
) -> Tuple[float, float]:
    """Detect left and right content margins from text lines."""
    if not lines:
        # Default: small inset from page edges
        return max(page_width * 0.05, 10), min(page_width * 0.95, page_width - 10)

    # Use the most common x0 as left margin, and rightmost extent
    x0_values = [line[3] for line in lines]  # line_x0
    left = max(min(x0_values) - 15, 0)
    right = min(page_width, page_width - left)  # symmetric, or page width
    return left, right


def _find_upper_boundary(
    caption: CaptionHit,
    page_captions: List[CaptionHit],
    page_lines: list,
) -> Optional[float]:
    """Find the bottom-y of the text element just above this figure.

    Strategy: The figure graphic sits BETWEEN the preceding body text and
    the caption below it.  We want to find body text / headings / other
    captions that are clearly ABOVE the graphic — not text that is part of
    the figure itself (axis labels, legend, annotations).

    Heuristics applied:
    - Require the candidate text to be full-width body text (len > 30)
      **or** another caption.
    - Require a minimum gap of MIN_FIGURE_HEIGHT between the candidate
      and the caption, since the figure graphic must fit in between.
    - Among valid candidates pick the one closest (max y) to the figure.
    """
    MIN_FIGURE_HEIGHT = 80  # ~28 mm at 72 dpi — minimum expected figure height

    candidates = []

    for line_text, line_top, line_bottom, line_x0 in page_lines:
        # Must be above our caption
        if line_bottom >= caption.y_top - 5:
            continue
        # Must leave enough room for the figure graphic between this
        # text and the caption
        gap = caption.y_top - line_bottom
        if gap < MIN_FIGURE_HEIGHT:
            continue  # too close — likely label inside the figure
        stripped = line_text.strip()
        # Accept substantial body text (paragraph text or headings)
        if len(stripped) > 30:
            candidates.append(line_bottom)
        # Also accept short but clearly structural text (section numbers, etc.)
        elif len(stripped) > 5 and re.match(r'^\d+[\.\s]', stripped):
            candidates.append(line_bottom)

    # Other captions on the same page
    for other_cap in page_captions:
        if other_cap is not caption and other_cap.y_bottom < caption.y_top - 5:
            gap = caption.y_top - other_cap.y_bottom
            if gap >= MIN_FIGURE_HEIGHT:
                candidates.append(other_cap.y_bottom)

    if candidates:
        # Pick the closest valid boundary (highest y value)
        return max(candidates)
    return None


def _looks_like_table_data(text: str) -> bool:
    """Heuristic: does this line look like a table data row?

    Table data rows typically contain structured numeric values mixed with
    text labels — e.g., "S2ORC_citations_abstracts 500,000 7.31B Scientific Literature".
    Body paragraphs are continuous prose with very few standalone numbers.

    We check for the presence of tabular numeric patterns: numbers with
    commas (e.g., "500,000"), numbers with units (e.g., "7.31B", "4.70B"),
    or sequences of numbers separated by whitespace.
    """
    # Count numeric-value patterns typical of table cells
    # Matches: "500,000", "7.31B", "0.45B", "158.95B", "1.68B", plain numbers, etc.
    numeric_patterns = re.findall(
        r'\b\d[\d,]*\.?\d*[BKMGT]?\b', text, re.IGNORECASE
    )
    return len(numeric_patterns) >= 2  # tables usually have at least 2 numeric fields


def _looks_like_body_paragraph(
    text: str,
    next_texts: List[str],
    min_consecutive: int = 3,
) -> bool:
    """Stricter body-paragraph detection requiring multiple consecutive prose lines.

    The old approach checked a single line (len > 50, alpha > 0.5) with one-line
    confirmation.  That misidentified text-heavy table cells (prompt templates,
    method descriptions) as body text, truncating the table.

    New approach: a line is body-paragraph only when at least `min_consecutive`
    consecutive lines (including itself) all look like flowing prose.

    Prose indicators (must satisfy ALL):
      - Length > 60 chars (table cells are usually shorter per line)
      - Starts with a lowercase letter or common sentence starters
      - Does NOT start with a bullet, dash-list, bold marker, or pipe (table formatting)
      - Alpha ratio > 0.55
      - Not a caption line
    """
    def _is_prose_line(s: str) -> bool:
        s = s.strip()
        if len(s) < 40:
            return False
        # Table-like patterns: starts with pipe, bullet, bold, or very short "cells"
        if re.match(r'^[\|•●▪◦\-\*]', s):
            return False
        # Caption line
        for pattern, _ in CAPTION_PATTERNS:
            if re.match(pattern, s):
                return False
        # Section heading
        if re.match(r'^\d+[\.\s]', s) and len(s) < 80:
            return False
        alpha_ratio = sum(1 for c in s if c.isalpha()) / max(len(s), 1)
        if alpha_ratio < 0.55:
            return False
        # Typical prose: starts with lowercase, or common sentence starters
        # Table rows often start with a proper-noun label (e.g., "Backbone Instances")
        # This is a soft signal — we rely on consecutive-line confirmation more.
        return True

    if not _is_prose_line(text):
        return False

    # Require min_consecutive - 1 additional consecutive prose lines after this one
    consecutive = 1
    for nt in next_texts:
        if _is_prose_line(nt):
            consecutive += 1
            if consecutive >= min_consecutive:
                return True
        else:
            break
    return False


def _detect_table_bottom_from_lines(
    pdf_path: str,
    page_index: int,
    caption_y_bottom: float,
    page_height: float,
) -> Optional[float]:
    """Use pdfplumber's line/rect detection to find the lowest horizontal
    rule below a table caption — this is typically the table's bottom border.

    Returns the y-coordinate (in PDF points) of the lowest horizontal line
    that is below the caption and plausibly part of the table, or None if
    no such line is found.
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if page_index >= len(pdf.pages):
                return None
            page = pdf.pages[page_index]

            # Collect horizontal lines from both explicit lines and rect edges
            h_lines_y: List[float] = []

            # 1. Explicit lines drawn on the page
            for line in (page.lines or []):
                y0, y1 = float(line.get("top", 0)), float(line.get("bottom", 0))
                x0, x1 = float(line.get("x0", 0)), float(line.get("x1", 0))
                # Horizontal if y-span is tiny and x-span is substantial
                if abs(y1 - y0) < 3 and abs(x1 - x0) > page.width * 0.2:
                    mid_y = (y0 + y1) / 2
                    if mid_y > caption_y_bottom + 10:  # below caption
                        h_lines_y.append(mid_y)

            # 2. Rectangle edges (tables often drawn with rects)
            for rect in (page.rects or []):
                top_y = float(rect.get("top", 0))
                bottom_y = float(rect.get("bottom", 0))
                x0, x1 = float(rect.get("x0", 0)), float(rect.get("x1", 0))
                width = abs(x1 - x0)
                if width > page.width * 0.2:
                    if bottom_y > caption_y_bottom + 10:
                        h_lines_y.append(bottom_y)
                    if top_y > caption_y_bottom + 10:
                        h_lines_y.append(top_y)

            if h_lines_y:
                # Return the lowest horizontal line — the table's bottom border
                return max(h_lines_y)
    except Exception:
        pass
    return None


def _find_lower_boundary(
    caption: CaptionHit,
    page_captions: List[CaptionHit],
    page_lines: list,
    pdf_path: str = "",
) -> Optional[float]:
    """Find the top-y of the text element just below this table content.

    Uses a three-tier approach:
      1. **Structural signals** (other captions, section headings) — always trusted.
      2. **PDF line/rect detection** — pdfplumber can find the table's bottom
         border line, giving a precise boundary.
      3. **Body-paragraph detection** — requires 3+ consecutive prose lines to
         confirm we've left the table, avoiding false positives on text-heavy
         table cells (prompt templates, method descriptions, etc.).
    """
    min_table_height = 80  # minimum expected table height in PDF points

    strong_candidates: List[float] = []
    line_based_candidates: List[float] = []
    weak_candidates: List[float] = []

    # --- Signal 1: Other captions on the same page ---
    for other_cap in page_captions:
        if other_cap is not caption and other_cap.y_top > caption.y_bottom + min_table_height:
            strong_candidates.append(other_cap.y_top)

    # --- Signal 2: PDF line/rect detection for table bottom border ---
    if pdf_path:
        table_bottom = _detect_table_bottom_from_lines(
            pdf_path, caption.page_index, caption.y_bottom, caption.page_height
        )
        if table_bottom is not None:
            # Add some padding below the last line (for caption below table, etc.)
            line_based_candidates.append(table_bottom + 15)

    # Pre-filter to lines below the table's minimum extent
    lines_below = [
        (text, top, bottom, x0)
        for text, top, bottom, x0 in page_lines
        if top > caption.y_bottom + min_table_height
    ]

    for i, (line_text, line_top, line_bottom, line_x0) in enumerate(lines_below):
        stripped = line_text.strip()

        # --- Strong signal: another figure/table/algorithm caption ---
        is_caption = False
        for pattern, _ in CAPTION_PATTERNS:
            if re.match(pattern, stripped):
                strong_candidates.append(line_top)
                is_caption = True
                break
        if is_caption:
            continue

        # --- Strong signal: section heading (e.g., "3.2 Results") ---
        if re.match(r'^\d+[\.\s]', stripped) and len(stripped) > 5:
            strong_candidates.append(line_top)
            continue

        # --- Skip lines that look like table data rows ---
        if _looks_like_table_data(stripped):
            continue

        # --- Weak signal: body-paragraph detection (strict, needs 3 consecutive) ---
        next_texts = [lines_below[j][0] for j in range(i + 1, min(i + 4, len(lines_below)))]
        if _looks_like_body_paragraph(stripped, next_texts, min_consecutive=3):
            weak_candidates.append(line_top)

    # Priority: strong > line-based > weak
    # For strong candidates, pick the closest below
    if strong_candidates:
        best_strong = min(strong_candidates)
        # If we also have a line-based candidate, use the LARGER of the two
        # (line-based may capture extra content that strong signals miss)
        if line_based_candidates:
            best_line = max(line_based_candidates)
            # But don't go past the next structural element
            return min(best_strong, max(best_strong, best_line))
        return best_strong

    if line_based_candidates:
        best_line = max(line_based_candidates)
        # If we also have weak (paragraph) signals, use the earlier one as a sanity check
        if weak_candidates:
            best_weak = min(weak_candidates)
            return min(best_line, best_weak)
        return best_line

    if weak_candidates:
        return min(weak_candidates)

    return None


# ---------------------------------------------------------------------------
# Page rendering (only pages with figures)
# ---------------------------------------------------------------------------

def find_pdftoppm():
    """Find pdftoppm binary."""
    path = shutil.which("pdftoppm")
    if path:
        return path
    for candidate in ["/opt/homebrew/bin/pdftoppm", "/usr/local/bin/pdftoppm", "/usr/bin/pdftoppm"]:
        if os.path.isfile(candidate):
            return candidate
    return None


def render_needed_pages(
    pdf_path: str,
    page_numbers: List[int],
    output_dir: str,
    dpi: int = 300,
) -> dict:
    """Render only the specified pages. Returns {page_number: png_path}."""
    pdftoppm = find_pdftoppm()
    if not pdftoppm:
        print("ERROR: pdftoppm not found. Install poppler:")
        print("  macOS:  brew install poppler")
        print("  Ubuntu: sudo apt-get install poppler-utils")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)
    page_map = {}

    unique_pages = sorted(set(page_numbers))
    for pg in unique_pages:
        prefix = os.path.join(output_dir, f"page")
        cmd = [
            pdftoppm, "-r", str(dpi), "-png",
            "-f", str(pg), "-l", str(pg),
            pdf_path, prefix,
        ]
        subprocess.run(cmd, check=True, capture_output=True)

        # pdftoppm names files like page-01.png or page-1.png depending on total pages
        # Find the rendered file
        for fname in os.listdir(output_dir):
            if fname.startswith("page") and fname.endswith(".png"):
                # Extract page number from filename
                m = re.search(r'page-?0*(\d+)\.png$', fname)
                if m and int(m.group(1)) == pg:
                    page_map[pg] = os.path.join(output_dir, fname)

    print(f"Rendered {len(page_map)} page(s) to {output_dir}/")
    return page_map


# ---------------------------------------------------------------------------
# Cropping
# ---------------------------------------------------------------------------

def crop_figures(
    regions: List[FigureRegion],
    page_images: dict,
    figures_dir: str,
    dpi: int = 300,
) -> List[ManifestEntry]:
    """Crop all figure regions from rendered page images."""
    os.makedirs(figures_dir, exist_ok=True)
    scale = dpi / 72.0  # PDF points to pixels
    entries: List[ManifestEntry] = []

    for region in regions:
        cap = region.caption
        pg_num = cap.page_number
        img_path = page_images.get(pg_num)
        if not img_path or not os.path.exists(img_path):
            print(f"WARNING: No rendered image for page {pg_num}, skipping {cap.caption_type} {cap.number}")
            continue

        img = Image.open(img_path)
        img_w, img_h = img.size

        # Convert PDF coordinates to pixel coordinates
        px_left = max(int(region.crop_left * scale), 0)
        px_top = max(int(region.crop_top * scale), 0)
        px_right = min(int(region.crop_right * scale), img_w)
        px_bottom = min(int(region.crop_bottom * scale), img_h)

        # Additional safety: expand by 50px (about 4mm at 300dpi)
        px_top = max(px_top - 50, 0)
        px_bottom = min(px_bottom + 50, img_h)
        px_left = max(px_left - 20, 0)
        px_right = min(px_right + 20, img_w)

        if px_left >= px_right or px_top >= px_bottom:
            print(f"WARNING: Invalid crop region for {cap.caption_type} {cap.number}, skipping")
            continue

        # Generate descriptive filename
        type_prefix = cap.caption_type[:3]  # fig, tab, alg
        short_caption = _slugify(cap.caption_text[:60])
        filename = f"{type_prefix}{cap.number}_{short_caption}.png"
        output_path = os.path.join(figures_dir, filename)

        cropped = img.crop((px_left, px_top, px_right, px_bottom))
        cropped.save(output_path, "PNG")
        print(f"  Cropped {cap.caption_type} {cap.number} -> {filename} ({cropped.size[0]}x{cropped.size[1]})")

        entries.append(ManifestEntry(
            filename=filename,
            caption_type=cap.caption_type,
            number=cap.number,
            caption_text=cap.caption_text,
            page_number=pg_num,
            needs_review=region.needs_review,
            confidence_note=region.confidence_note,
            crop_coords_pdf={
                "left": round(region.crop_left, 1),
                "top": round(region.crop_top, 1),
                "right": round(region.crop_right, 1),
                "bottom": round(region.crop_bottom, 1),
            },
            crop_coords_pixel={
                "left": px_left,
                "top": px_top,
                "right": px_right,
                "bottom": px_bottom,
            },
        ))

    return entries


def _slugify(text: str) -> str:
    """Convert caption text to a filesystem-safe slug."""
    # Remove the "Figure N:" prefix
    text = re.sub(r'(?i)^(fig(?:ure)?|table|algorithm)\s*\.?\s*\d+[a-z]?\s*[:\.\|–—\-]\s*', '', text)
    # Keep only alphanumeric and spaces
    text = re.sub(r'[^a-zA-Z0-9\s]', '', text)
    # Collapse whitespace and convert to underscore
    text = re.sub(r'\s+', '_', text.strip())
    return text[:50].rstrip('_').lower() or "untitled"


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------

def write_manifest(entries: List[ManifestEntry], manifest_path: str):
    """Write manifest.json with metadata for all extracted figures."""
    data = {
        "total_figures": len(entries),
        "needs_review_count": sum(1 for e in entries if e.needs_review),
        "figures": [asdict(e) for e in entries],
    }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Manifest written to {manifest_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Smart figure/table extraction from academic PDFs"
    )
    parser.add_argument("pdf_path", help="Path to the PDF file")
    parser.add_argument("output_dir", help="Base output directory")
    parser.add_argument("--dpi", type=int, default=300, help="Render DPI (default: 300)")
    args = parser.parse_args()

    pdf_path = args.pdf_path
    output_dir = args.output_dir
    dpi = args.dpi

    if not os.path.isfile(pdf_path):
        print(f"ERROR: PDF not found: {pdf_path}")
        sys.exit(1)

    figures_dir = os.path.join(output_dir, "figures")
    pages_dir = os.path.join(output_dir, "pages")
    manifest_path = os.path.join(figures_dir, "manifest.json")

    # Step 1: Detect captions
    print(f"\n=== Step 1: Scanning PDF for captions ===")
    captions = detect_captions(pdf_path)
    if not captions:
        print("No figure/table/algorithm captions detected.")
        # Still write an empty manifest
        os.makedirs(figures_dir, exist_ok=True)
        write_manifest([], manifest_path)
        return

    print(f"Found {len(captions)} caption(s):")
    for cap in captions:
        print(f"  Page {cap.page_number}: {cap.caption_type} {cap.number} - {cap.caption_text[:80]}")

    # Step 2: Compute crop regions
    print(f"\n=== Step 2: Computing crop regions ===")
    regions = compute_crop_regions(captions, pdf_path)
    review_count = sum(1 for r in regions if r.needs_review)
    print(f"  {len(regions)} regions computed, {review_count} need review")

    # Step 3: Render only needed pages
    print(f"\n=== Step 3: Rendering pages with figures ===")
    needed_pages = sorted(set(cap.page_number for cap in captions))
    print(f"  Pages to render: {needed_pages}")
    page_images = render_needed_pages(pdf_path, needed_pages, pages_dir, dpi)

    # Step 4: Crop figures
    print(f"\n=== Step 4: Cropping figures ===")
    entries = crop_figures(regions, page_images, figures_dir, dpi)

    # Step 5: Write manifest
    print(f"\n=== Step 5: Writing manifest ===")
    write_manifest(entries, manifest_path)

    # Summary
    print(f"\n=== Done ===")
    print(f"  Extracted: {len(entries)} figure(s)/table(s)")
    print(f"  Need review: {sum(1 for e in entries if e.needs_review)}")
    print(f"  Figures dir: {figures_dir}/")
    print(f"  Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
