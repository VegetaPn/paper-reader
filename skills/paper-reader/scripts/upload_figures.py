#!/usr/bin/env python3
"""Upload extracted figures to Cloudflare R2 image hosting via Worker.

Reads figures/manifest.json, uploads each image to R2, and writes back
URL mappings. Gracefully degrades when R2 is not configured.

Usage:
    python3 upload_figures.py <research_dir>

    Example:
        python3 upload_figures.py ./research/flash-attention-2/

Configuration (checked in order):
    1. Environment variables: R2_WORKER_URL + R2_API_KEY
    2. .env file in <research_dir> or project root
    3. If neither → prints info message and exits with code 0 (graceful)

Output:
    <research_dir>/figures/urls.json   — {filename: url} mapping
    Updates manifest.json              — adds "url" field to each entry

Dependencies:
    Python standard library only (urllib.request). No pip install needed.
"""

import json
import os
import sys
import urllib.request
import urllib.error


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def load_env_file(path: str) -> dict:
    """Parse a simple .env file (KEY=VALUE lines, ignoring comments)."""
    env = {}
    if not os.path.isfile(path):
        return env
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip("'\"")
                env[key] = value
    return env


def get_config(research_dir: str) -> tuple:
    """Return (worker_url, api_key) or (None, None) if not configured.

    Priority:
      1. Environment variables
      2. .env in research_dir
      3. .env in project root (two levels up from research_dir)
    """
    # 1. Environment variables
    worker_url = os.environ.get("R2_WORKER_URL")
    api_key = os.environ.get("R2_API_KEY")
    if worker_url and api_key:
        return worker_url.rstrip("/"), api_key

    # 2. .env in research_dir
    env = load_env_file(os.path.join(research_dir, ".env"))
    worker_url = env.get("R2_WORKER_URL")
    api_key = env.get("R2_API_KEY")
    if worker_url and api_key:
        return worker_url.rstrip("/"), api_key

    # 3. .env in project root (best guess: walk up until we leave research/)
    # Typically: ./research/<name>/ → project root is ../../
    project_root = os.path.abspath(os.path.join(research_dir, "..", ".."))
    env = load_env_file(os.path.join(project_root, ".env"))
    worker_url = env.get("R2_WORKER_URL")
    api_key = env.get("R2_API_KEY")
    if worker_url and api_key:
        return worker_url.rstrip("/"), api_key

    return None, None


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

def upload_figure(
    filepath: str,
    worker_url: str,
    api_key: str,
    upload_path: str,
) -> str:
    """Upload a single file to R2 Worker via PUT. Returns the public URL.

    Args:
        filepath: Local path to the image file.
        worker_url: Base URL of the R2 Worker (e.g. https://r2-imagebed.xxx.workers.dev).
        api_key: API key for authentication.
        upload_path: Remote path (e.g. papers/flash-attention-2/fig1.png).

    Returns:
        The public URL of the uploaded file.
    """
    url = f"{worker_url}/{upload_path}"

    with open(filepath, "rb") as f:
        data = f.read()

    req = urllib.request.Request(
        url,
        data=data,
        method="PUT",
        headers={
            "X-API-Key": api_key,
            "Content-Type": "image/png",
            "User-Agent": "paper-reader/1.0",
        },
    )

    with urllib.request.urlopen(req, timeout=60) as resp:
        # Some workers return the URL in the response body
        body = resp.read().decode("utf-8", errors="replace")

    # The public URL is typically the same as the PUT URL for R2 Workers
    return url


def derive_paper_name(research_dir: str) -> str:
    """Extract the paper short name from the research directory path.

    e.g. ./research/flash-attention-2/ → flash-attention-2
    """
    # Normalize and get the last non-empty component
    parts = os.path.normpath(research_dir).split(os.sep)
    return parts[-1] if parts else "unknown"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 upload_figures.py <research_dir>")
        print("  Example: python3 upload_figures.py ./research/flash-attention-2/")
        sys.exit(1)

    research_dir = sys.argv[1]
    figures_dir = os.path.join(research_dir, "figures")
    manifest_path = os.path.join(figures_dir, "manifest.json")

    # Check manifest exists
    if not os.path.isfile(manifest_path):
        print(f"ERROR: manifest.json not found at {manifest_path}")
        print("Run extract_figures.py first to generate the manifest.")
        sys.exit(1)

    # Load manifest
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    figures = manifest.get("figures", [])
    if not figures:
        print("No figures in manifest.json. Nothing to upload.")
        sys.exit(0)

    # Get R2 configuration
    worker_url, api_key = get_config(research_dir)
    if not worker_url or not api_key:
        print("R2 image hosting is not configured.")
        print("To enable, set environment variables:")
        print("  export R2_WORKER_URL=https://your-r2-worker.workers.dev")
        print("  export R2_API_KEY=your-api-key")
        print("Or create a .env file with these variables.")
        print("")
        print("Skipping upload — figures will use local paths only.")
        sys.exit(0)

    # Derive paper name for R2 path
    paper_name = derive_paper_name(research_dir)
    print(f"\n=== Uploading figures to R2 ===")
    print(f"  Worker URL: {worker_url}")
    print(f"  Paper name: {paper_name}")
    print(f"  Figures to upload: {len(figures)}")
    print()

    # Upload each figure
    url_map = {}
    success_count = 0
    fail_count = 0

    for entry in figures:
        filename = entry["filename"]
        filepath = os.path.join(figures_dir, filename)

        if not os.path.isfile(filepath):
            print(f"  SKIP {filename} — file not found locally")
            fail_count += 1
            continue

        upload_path = f"papers/{paper_name}/{filename}"
        print(f"  Uploading {filename} → {upload_path} ...", end=" ")

        try:
            public_url = upload_figure(filepath, worker_url, api_key, upload_path)
            url_map[filename] = public_url
            entry["url"] = public_url
            success_count += 1
            print("OK")
        except urllib.error.HTTPError as e:
            print(f"FAILED (HTTP {e.code}: {e.reason})")
            fail_count += 1
        except urllib.error.URLError as e:
            print(f"FAILED (Network error: {e.reason})")
            fail_count += 1
        except Exception as e:
            print(f"FAILED ({e})")
            fail_count += 1

    # Write urls.json
    urls_path = os.path.join(figures_dir, "urls.json")
    with open(urls_path, "w", encoding="utf-8") as f:
        json.dump(url_map, f, indent=2, ensure_ascii=False)
    print(f"\nURL mapping written to {urls_path}")

    # Update manifest.json with url fields
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"Manifest updated at {manifest_path}")

    # Summary
    print(f"\n=== Upload Summary ===")
    print(f"  Successful: {success_count}")
    print(f"  Failed:     {fail_count}")
    print(f"  Total:      {len(figures)}")

    if fail_count > 0 and success_count == 0:
        print("\nAll uploads failed. Figures will use local paths.")
    elif fail_count > 0:
        print(f"\n{fail_count} upload(s) failed. Those figures will use local paths.")


if __name__ == "__main__":
    main()
