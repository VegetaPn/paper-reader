#!/usr/bin/env python3
"""Extract structured metadata from an academic PDF.

Uses pdfplumber to programmatically extract title, authors, abstract,
section headings, and first-page text. This provides ground-truth text
that the LLM must use for summarization, preventing hallucination.

Usage:
    python3 extract_metadata.py <pdf_path> <output_dir>

Output:
    <output_dir>/metadata.json

Dependencies:
    pip install pdfplumber
"""

import argparse
import json
import os
import re
import sys

try:
    import pdfplumber
except ImportError:
    print("ERROR: pdfplumber not installed. Run: pip install pdfplumber")
    sys.exit(1)


def extract_text_with_fonts(page) -> list:
    """Extract words with font size info from a page.

    Returns list of dicts: {text, top, bottom, x0, x1, size, fontname}
    """
    chars = page.chars
    if not chars:
        return []

    # Group chars into words by proximity
    words = page.extract_words(
        x_tolerance=3,
        y_tolerance=3,
        keep_blank_chars=True,
        extra_attrs=["top", "bottom"],
    )

    # Attach font size to each word by finding the dominant char size
    enriched = []
    for w in words:
        # Find chars that overlap with this word's bounding box
        word_chars = [
            c for c in chars
            if abs(float(c["top"]) - float(w["top"])) < 5
            and float(c["x0"]) >= float(w["x0"]) - 2
            and float(c["x1"]) <= float(w["x1"]) + 2
        ]
        if word_chars:
            # Use the most common font size among chars in this word
            sizes = [float(c.get("size", 0)) for c in word_chars]
            dominant_size = max(set(sizes), key=sizes.count) if sizes else 0
            fontnames = [c.get("fontname", "") for c in word_chars]
            dominant_font = max(set(fontnames), key=fontnames.count) if fontnames else ""
        else:
            dominant_size = 0
            dominant_font = ""

        enriched.append({
            "text": w["text"],
            "top": float(w["top"]),
            "bottom": float(w["bottom"]),
            "x0": float(w["x0"]),
            "x1": float(w["x1"]),
            "size": dominant_size,
            "fontname": dominant_font,
        })

    return enriched


def group_words_into_lines(words: list, y_tolerance: float = 3.0) -> list:
    """Group words into text lines based on y-coordinate proximity.

    Returns list of dicts: {text, top, bottom, x0, max_size, fonts}
    """
    if not words:
        return []

    sorted_words = sorted(words, key=lambda w: (w["top"], w["x0"]))

    lines = []
    current = [sorted_words[0]]

    for w in sorted_words[1:]:
        if abs(w["top"] - current[0]["top"]) <= y_tolerance:
            current.append(w)
        else:
            # Finish current line
            text = " ".join(ww["text"] for ww in current)
            sizes = [ww["size"] for ww in current]
            lines.append({
                "text": text,
                "top": current[0]["top"],
                "bottom": max(ww["bottom"] for ww in current),
                "x0": current[0]["x0"],
                "max_size": max(sizes) if sizes else 0,
                "avg_size": sum(sizes) / len(sizes) if sizes else 0,
            })
            current = [w]

    # Don't forget last line
    if current:
        text = " ".join(ww["text"] for ww in current)
        sizes = [ww["size"] for ww in current]
        lines.append({
            "text": text,
            "top": current[0]["top"],
            "bottom": max(ww["bottom"] for ww in current),
            "x0": current[0]["x0"],
            "max_size": max(sizes) if sizes else 0,
            "avg_size": sum(sizes) if sizes else 0,
        })

    return lines


def extract_title(first_page_lines: list, second_page_lines: list = None) -> str:
    """Extract paper title by finding the largest font text in the top region of page 1.

    Strategy: The title is the largest-font text in the TOP portion of the first page
    (top 40% by y-coordinate). This excludes figure/table text that may have large fonts
    but appears lower on the page. The title may span multiple consecutive lines.
    """
    if not first_page_lines:
        return ""

    # Determine page height from the last line's bottom position
    page_bottom = max(line["bottom"] for line in first_page_lines)
    # Only consider lines in the top 40% of the page for title detection
    top_region_cutoff = page_bottom * 0.4

    top_lines = [l for l in first_page_lines if l["top"] < top_region_cutoff]
    if not top_lines:
        top_lines = first_page_lines[:5]  # fallback: just use first 5 lines

    # Filter out noise lines where avg_size is much lower than max_size
    # (these are figure/chart text where a stray large char inflates max_size)
    # A real title line has consistent font size: avg should be close to max
    coherent_lines = [
        l for l in top_lines
        if l["avg_size"] > 0 and l["avg_size"] >= l["max_size"] * 0.6
    ]
    if not coherent_lines:
        coherent_lines = top_lines  # fallback

    # Find the max font size among coherent top-region lines
    max_size = max(line["max_size"] for line in coherent_lines)

    # Collect consecutive lines with that font size (within 1.5pt tolerance)
    title_lines = []
    title_started = False

    for line in coherent_lines:
        text = line["text"].strip()
        if not text:
            continue

        if line["max_size"] >= max_size - 1.5 and line["avg_size"] >= max_size - 3.0:
            title_started = True
            title_lines.append(text)
        elif title_started:
            # Title ended — stop collecting
            break

    title = " ".join(title_lines).strip()

    # Clean up common artifacts
    title = re.sub(r'\s+', ' ', title)

    return title


def extract_abstract(all_lines: list) -> str:
    """Extract the abstract text.

    Strategy: Find any line containing 'Abstract' (as standalone word or prefix),
    then collect body text lines until we hit a section heading, keyword line,
    or significant font size increase.

    Handles multiple formats:
    - "Abstract" on its own line, body follows
    - "Abstract The performance of..." (inline)
    - "Abstract" embedded in a line with figure noise (search for the word)
    """
    abstract_lines = []
    in_abstract = False
    abstract_body_size = None

    for i, line in enumerate(all_lines):
        text = line["text"].strip()

        if not in_abstract:
            # Look for "Abstract" as standalone line
            if re.match(r'^abstract\s*$', text, re.IGNORECASE):
                in_abstract = True
                continue

            # "Abstract" followed by text on the same line
            m = re.match(r'^abstract\s*[:\.\s]\s*(.+)', text, re.IGNORECASE)
            if m:
                in_abstract = True
                rest = m.group(1).strip()
                if rest and len(rest) > 10:
                    abstract_lines.append(rest)
                    abstract_body_size = line["avg_size"]
                continue

            # Check if "Abstract" appears as a word in a mixed line
            # (some PDFs merge figure text with body text in extraction)
            if re.search(r'\babstract\b', text, re.IGNORECASE) and line["avg_size"] >= 8:
                m = re.search(r'\babstract\b\s*[:\.\s]\s*(.+)', text, re.IGNORECASE)
                if m:
                    in_abstract = True
                    rest = m.group(1).strip()
                    if rest and len(rest) > 10:
                        abstract_lines.append(rest)
                        abstract_body_size = line["avg_size"]
                    continue
        else:
            # Check for end of abstract
            # End markers: numbered section headings, "Introduction", "1."
            if re.match(r'^(\d+\.?\s+[A-Z]\w|introduction\b|1\s+[A-Z])', text, re.IGNORECASE):
                break
            if re.match(r'^keywords?\s*:', text, re.IGNORECASE):
                break

            # Skip very short lines that are likely noise (figure labels, page numbers)
            if len(text) < 5 and not abstract_lines:
                continue

            # If we have a reference body size, stop on significant size INCREASE
            # (heading fonts are larger than body)
            if abstract_body_size and line["avg_size"] > abstract_body_size + 2:
                break

            # Also stop if the line's body size drops significantly (entering figure area)
            if abstract_body_size and line["avg_size"] < abstract_body_size - 3:
                continue  # skip noise lines but don't end abstract

            if text and len(text) > 3:
                abstract_lines.append(text)
                if abstract_body_size is None and line["avg_size"] >= 8:
                    abstract_body_size = line["avg_size"]

    return " ".join(abstract_lines).strip()


def extract_authors(first_page_lines: list, title: str) -> str:
    """Extract author names from between title and abstract."""
    if not first_page_lines or not title:
        return ""

    # Find where the title ends and where abstract begins
    title_end_idx = None
    abstract_idx = None

    for i, line in enumerate(first_page_lines):
        text = line["text"].strip()
        # Check if this line is part of the title
        if title_end_idx is None and text and text in title:
            title_end_idx = i

        if re.match(r'^abstract', text, re.IGNORECASE):
            abstract_idx = i
            break

    if title_end_idx is None:
        title_end_idx = 0
    if abstract_idx is None:
        abstract_idx = len(first_page_lines)

    # Collect lines between title and abstract
    author_lines = []
    for line in first_page_lines[title_end_idx + 1:abstract_idx]:
        text = line["text"].strip()
        if not text:
            continue
        # Skip lines that look like affiliations, emails, URLs
        if re.match(r'^(https?://|www\.|project\s+page|\{)', text, re.IGNORECASE):
            continue
        # Skip lines that are just numbers (footnotes, page numbers)
        if re.match(r'^\d+$', text):
            continue
        author_lines.append(text)

    # Take only the first few lines (authors typically 1-3 lines)
    return " ".join(author_lines[:4]).strip()


def extract_section_headings(all_pages_lines: list) -> list:
    """Extract section headings from the entire document.

    Strategy: Section headings must satisfy BOTH:
    1. Match a heading pattern (numbered sections, appendix letters)
    2. Have a font size larger than body text

    This dual requirement filters out table/figure data that happens to
    start with numbers (e.g., "40 Few-Shot(32) 13.0 72.2 ...").
    """
    if not all_pages_lines:
        return []

    # Estimate body text size (most common font size)
    all_sizes = [line["avg_size"] for line in all_pages_lines if line["avg_size"] > 0]
    if not all_sizes:
        return []

    # Body size is the most frequent avg_size (rounded to 0.5pt)
    size_counts = {}
    for s in all_sizes:
        rounded = round(s * 2) / 2  # round to nearest 0.5
        size_counts[rounded] = size_counts.get(rounded, 0) + 1
    body_size = max(size_counts, key=size_counts.get)

    headings = []
    seen_texts = set()  # deduplicate

    for line in all_pages_lines:
        text = line["text"].strip()
        if not text or len(text) < 3:
            continue

        # BOTH conditions required: pattern match AND larger font
        is_larger_font = line["avg_size"] > body_size + 0.5

        if not is_larger_font:
            continue

        # Pattern: numbered sections like "1 Introduction", "2.1 Method"
        # Must start with a section number followed by a capitalized word
        # The word must be mostly alphabetic (not "40 Few-Shot(32) 13.0...")
        m = re.match(r'^(\d+(?:\.\d+)*)\s+([A-Z][A-Za-z].*)', text)
        if m:
            section_num = m.group(1)
            section_title = m.group(2)
            # Filter: section numbers should be reasonable (1-99, subsections 1.1-9.9.9)
            parts = section_num.split('.')
            if all(p.isdigit() and int(p) < 100 for p in parts):
                # Filter: heading text should be mostly words, not numbers
                words_in_title = section_title.split()
                alpha_words = sum(1 for w in words_in_title if re.match(r'^[A-Za-z]', w))
                if alpha_words >= len(words_in_title) * 0.5 and len(text) < 80:
                    dedup_key = text[:50]
                    if dedup_key not in seen_texts:
                        seen_texts.add(dedup_key)
                        headings.append(text)
                    continue

        # Pattern: lettered appendix sections "A Appendix Details", "B Proofs"
        if re.match(r'^[A-F]\.?\s+[A-Z][a-z]', text) and len(text) < 80:
            dedup_key = text[:50]
            if dedup_key not in seen_texts:
                seen_texts.add(dedup_key)
                headings.append(text)
                continue

    return headings


def extract_first_page_text(page) -> str:
    """Extract full text from the first page as fallback."""
    text = page.extract_text()
    return text.strip() if text else ""


def extract_title_from_plain_text(plain_text: str, font_lines: list) -> str:
    """Extract title using a hybrid approach.

    Primary: Use font-size analysis from page 1 (top region, coherent lines).
    Fallback: Use the first non-empty line of extract_text() output that isn't
    a conference name, arXiv ID, or other boilerplate.
    """
    # Try font-based extraction first
    title = extract_title(font_lines)
    if title and len(title) > 5:
        return title

    # Fallback: parse plain text
    lines = plain_text.strip().split('\n')
    for line in lines[:10]:
        text = line.strip()
        if not text or len(text) < 5:
            continue
        # Skip common boilerplate
        if re.match(r'^(preprint|arxiv|under review|published|proceedings)', text, re.IGNORECASE):
            continue
        if re.match(r'^https?://', text):
            continue
        # First substantial line is likely the title
        return text

    return ""


def extract_abstract_from_plain_text(pages_text: list) -> str:
    """Extract abstract from plain text extracted by pdfplumber.

    Uses extract_text() which handles column merging much better than
    position-based word grouping. Searches the first 3 pages.

    Returns the abstract text.
    """
    # Combine first few pages
    combined = '\n'.join(pages_text[:3])
    lines = combined.split('\n')

    abstract_lines = []
    in_abstract = False

    for line in lines:
        text = line.strip()

        if not in_abstract:
            if re.match(r'^abstract\s*$', text, re.IGNORECASE):
                in_abstract = True
                continue
            m = re.match(r'^abstract\s*[:\.\s]\s*(.+)', text, re.IGNORECASE)
            if m:
                in_abstract = True
                rest = m.group(1).strip()
                if rest and len(rest) > 10:
                    abstract_lines.append(rest)
                continue
        else:
            # End markers
            if re.match(r'^(\d+\.?\s+[A-Z]\w|introduction\b|1\s+[A-Z])', text, re.IGNORECASE):
                break
            if re.match(r'^keywords?\s*:', text, re.IGNORECASE):
                break
            # Empty line after abstract content may indicate end
            if not text and abstract_lines:
                # Check if next non-empty line looks like a heading
                # For now, allow one empty line
                continue

            if text and len(text) > 3:
                abstract_lines.append(text)

    return " ".join(abstract_lines).strip()


def extract_authors_from_plain_text(plain_text: str, title: str) -> str:
    """Extract authors from between title and abstract in plain text."""
    lines = plain_text.strip().split('\n')

    # Find title line and abstract line
    title_idx = None
    abstract_idx = None

    title_lower = title.lower().strip() if title else ""

    for i, line in enumerate(lines):
        text = line.strip()
        if title_idx is None and title_lower and title_lower[:30] in text.lower():
            title_idx = i
        if re.match(r'^abstract', text, re.IGNORECASE):
            abstract_idx = i
            break

    if title_idx is None:
        title_idx = 0
    if abstract_idx is None:
        abstract_idx = min(15, len(lines))  # assume first 15 lines

    # Collect lines between title and abstract
    author_lines = []
    for line in lines[title_idx + 1:abstract_idx]:
        text = line.strip()
        if not text:
            continue
        if re.match(r'^(https?://|www\.|project\s+page|\{|equal\s+contrib)', text, re.IGNORECASE):
            continue
        if re.match(r'^\d+$', text):
            continue
        # Skip very long lines (likely not author names)
        if len(text) > 200:
            continue
        author_lines.append(text)

    return " | ".join(author_lines[:5]).strip()


def main():
    parser = argparse.ArgumentParser(
        description="Extract structured metadata from an academic PDF"
    )
    parser.add_argument("pdf_path", help="Path to the PDF file")
    parser.add_argument("output_dir", help="Directory to write metadata.json")
    args = parser.parse_args()

    if not os.path.exists(args.pdf_path):
        print(f"ERROR: PDF not found: {args.pdf_path}")
        sys.exit(1)

    os.makedirs(args.output_dir, exist_ok=True)

    print(f"=== Extracting metadata from: {args.pdf_path} ===")

    with pdfplumber.open(args.pdf_path) as pdf:
        page_count = len(pdf.pages)
        print(f"  Pages: {page_count}")

        # ---- Plain text extraction (for title, abstract, authors) ----
        # extract_text() handles column merging well and avoids figure noise
        pages_text = []
        for i in range(min(3, page_count)):
            text = pdf.pages[i].extract_text() or ""
            pages_text.append(text)

        first_page_text = pages_text[0] if pages_text else ""

        # ---- Font-aware extraction (for title font detection, section headings) ----
        first_page_words = extract_text_with_fonts(pdf.pages[0]) if page_count > 0 else []
        first_page_lines = group_words_into_lines(first_page_words)

        # Extract all pages for section headings
        all_lines = []
        for page in pdf.pages:
            words = extract_text_with_fonts(page)
            lines = group_words_into_lines(words)
            all_lines.extend(lines)

        # ---- Extract metadata ----
        title = extract_title_from_plain_text(first_page_text, first_page_lines)
        print(f"  Title: {title}")

        authors = extract_authors_from_plain_text(first_page_text, title)
        print(f"  Authors: {authors[:100]}{'...' if len(authors) > 100 else ''}")

        abstract = extract_abstract_from_plain_text(pages_text)
        print(f"  Abstract: {abstract[:120]}{'...' if len(abstract) > 120 else ''}")

        headings = extract_section_headings(all_lines)
        print(f"  Section headings: {len(headings)} found")
        for h in headings:
            print(f"    - {h}")

    metadata = {
        "title": title,
        "authors": authors,
        "abstract": abstract,
        "section_headings": headings,
        "page_count": page_count,
        "first_page_text": first_page_text,
    }

    output_path = os.path.join(args.output_dir, "metadata.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"\n=== Metadata written to: {output_path} ===")


if __name__ == "__main__":
    main()
