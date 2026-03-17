#!/usr/bin/env python3
"""Crop a figure region from a rendered PDF page image.

Usage:
    python3 crop_figure.py <page_image> <output_path> <left> <top> <right> <bottom>

Example:
    python3 crop_figure.py pages/page01.png figures/fig1.png 120 60 2430 1100

Tips for finding crop coordinates:
  - Full page at 300 DPI is typically 2550x3300 (letter) or 2480x3508 (A4)
  - Left margin usually starts around x=120
  - Right margin usually ends around x=2430
  - Use the Read tool to view full page images and estimate y coordinates
  - Always include figure caption in the crop area
  - If a figure is cut off, increase the bottom coordinate and re-crop
"""
import argparse
import sys

try:
    from PIL import Image
except ImportError:
    print("ERROR: Pillow not installed. Run: pip install Pillow")
    sys.exit(1)


def crop_figure(page_path, output_path, left, top, right, bottom):
    img = Image.open(page_path)
    w, h = img.size
    # Clamp coordinates
    right = min(right, w)
    bottom = min(bottom, h)
    if left >= right or top >= bottom:
        print(f"ERROR: Invalid crop region ({left},{top},{right},{bottom}) for image {w}x{h}")
        sys.exit(1)

    cropped = img.crop((left, top, right, bottom))
    cropped.save(output_path)
    print(f"Cropped {page_path} ({w}x{h}) -> {output_path} ({cropped.size[0]}x{cropped.size[1]})")
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Crop figure from PDF page image")
    parser.add_argument("page_image", help="Path to the rendered page PNG")
    parser.add_argument("output_path", help="Output path for cropped figure")
    parser.add_argument("left", type=int)
    parser.add_argument("top", type=int)
    parser.add_argument("right", type=int)
    parser.add_argument("bottom", type=int)
    args = parser.parse_args()
    crop_figure(args.page_image, args.output_path, args.left, args.top, args.right, args.bottom)
