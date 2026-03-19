# Paper Reader

[![中文文档](https://img.shields.io/badge/文档-中文版-blue)](./README_zh.md)

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill that transforms academic paper PDFs into detailed, figure-rich interpretation documents tailored to your technical background.

## Features

- **Audience-Aware** — Adapts depth and style based on your profile: Programmer, ML Practitioner, Researcher, or Non-technical
- **Smart Figure Extraction** — Uses pdfplumber to detect captions, renders only pages with figures, and auto-crops with heuristic boundary detection. Falls back to manual cropping when needed
- **R2 Image Hosting** — Optionally uploads figures to Cloudflare R2 so documents can be shared with online images
- **Context-Resilient** — Phased workflow with `progress.json` state persistence. Survives context compaction without losing progress
- **Structured Output** — Generates a complete Markdown interpretation following a proven template (background, core method, experiments, takeaways)
- **Bilingual** — Automatically detects your language (Chinese or English) and produces the entire document accordingly

## Prerequisites

| Dependency | Purpose | Installation |
|------------|---------|-------------|
| [Python 3](https://www.python.org/) | Run figure extraction scripts | Usually pre-installed |
| [Pillow](https://python-pillow.org/) | Image cropping | `pip install Pillow` |
| [pdfplumber](https://github.com/jsvine/pdfplumber) | Smart caption detection | `pip install pdfplumber` |
| [Poppler](https://poppler.freedesktop.org/) | PDF-to-PNG rendering | macOS: `brew install poppler`<br>Ubuntu: `sudo apt-get install poppler-utils` |
| [Claude Code](https://docs.anthropic.com/en/docs/claude-code) | Run the skill | `npm install -g @anthropic-ai/claude-code` |

## Installation

### Option 1: Via skills.sh (Recommended)

One command to install across Claude Code, Cursor, Copilot, and 35+ other agents:

```bash
npx skills add VegetaPn/paper-reader
```

The CLI auto-detects your installed agents and installs to the correct location.

### Option 2: Via Claude Code Plugin Marketplace

```
/plugin marketplace add VegetaPn/paper-reader
/plugin install paper-reader@paper-reader
```

### Option 3: Manual install

Clone the repo directly into your Claude Code personal skills directory:

```bash
git clone https://github.com/VegetaPn/paper-reader.git ~/.claude/skills/paper-reader
```

That's it — Claude Code will discover the skill automatically in your next session.

#### Install to a specific project only

If you prefer to scope the skill to a single project:

```bash
cd /path/to/your/project
git clone https://github.com/VegetaPn/paper-reader.git .claude/skills/paper-reader
```

#### Install via `--add-dir`

You can also clone the repo anywhere and point Claude Code to it at launch:

```bash
git clone https://github.com/VegetaPn/paper-reader.git ~/tools/paper-reader
claude --add-dir ~/tools/paper-reader
```

### Install system dependencies

The skill uses external tools for figure extraction. Install them once:

```bash
# Python libraries (required)
pip install Pillow pdfplumber

# PDF renderer (required)
# macOS
brew install poppler
# Ubuntu / Debian
sudo apt-get install poppler-utils
```

## Usage

Once installed, simply ask Claude Code to read a paper:

```
Read this paper /path/to/paper.pdf
```

```
帮我解读这篇论文 /path/to/paper.pdf
```

### Workflow

The skill runs in three phases, each persisting state to `progress.json` so work survives context compaction:

**Phase A — Scan & Profile**
1. **Quick scan** — Claude skims the PDF to identify structure, domain, and prerequisites
2. **Choose your profile** — Select your technical background:
   - **Programmer** — explanations use code snippets and programming analogies
   - **ML Practitioner** — focuses on implementation details, ablations, and training cost
   - **Researcher** — emphasizes theoretical novelty and connections to related work
   - **Non-technical** — pure analogies, no code or math
3. **Knowledge check** — Multi-select concepts you already know. Claude skips what you know and dives deeper where it matters

**Phase B — Figure Extraction (automated)**
4. **Smart extraction** — `extract_figures.py` scans the PDF with pdfplumber, detects all figure/table captions, renders only needed pages, and auto-crops each figure
5. **Selective review** — Only low-confidence crops are manually verified; high-confidence ones pass through
6. **R2 upload** (optional) — If configured, figures are uploaded to Cloudflare R2 for online sharing

**Phase C — Deep Read & Write**
7. **Deep read** — Claude reads the full PDF in chunks, writing notes to `notes.md`
8. **Interpretation** — Generates a structured Markdown document with all figures embedded
9. **Quality check** — Verifies completeness and correctness

### Output

```
./research/<paper-short-name>/
├── 论文解读_<PaperTitle>.md    # interpretation document
├── progress.json               # workflow state (for recovery)
├── notes.md                    # reading notes (for recovery)
├── figures/
│   ├── manifest.json           # figure metadata + R2 URLs
│   ├── urls.json               # filename → URL mapping (if uploaded)
│   ├── fig1_architecture.png
│   ├── table2_results.png
│   └── ...
└── pages/                      # rendered PDF pages (only those with figures)
    ├── page-01.png
    └── ...
```

### R2 Image Hosting (Optional)

To enable automatic figure upload to Cloudflare R2:

```bash
export R2_WORKER_URL=https://your-r2-worker.workers.dev
export R2_API_KEY=your-api-key
```

Or create a `.env` file in your project root with these variables. When configured, the interpretation document will use online URLs instead of local paths, making it shareable without bundling image files.

### Trigger Keywords

The skill activates when you use phrases like:

> read paper, paper reading, interpret paper, analyze paper, 解读论文, 阅读论文, 分析论文, 读论文, 看论文

## Project Structure

```
paper-reader/
├── .claude-plugin/
│   ├── plugin.json                   # Claude Code plugin metadata
│   └── marketplace.json              # Claude Code marketplace manifest
├── skills/
│   └── paper-reader/
│       ├── SKILL.md                  # Skill definition (Claude Code entry point)
│       ├── scripts/
│       │   ├── extract_figures.py    # Smart figure extraction (pdfplumber + pdftoppm + PIL)
│       │   ├── upload_figures.py     # Upload figures to Cloudflare R2
│       │   ├── render_pdf_pages.py   # Render PDF pages to PNG
│       │   └── crop_figure.py        # Crop figures from page images
│       └── references/
│           ├── document_template.md  # Writing guidelines and quality checklist
│           └── audience_profiles.md  # Interpretation strategies per audience
├── README.md                         # This file
└── README_zh.md                      # Chinese documentation
```

### Scripts

#### `extract_figures.py` — Smart Figure Extraction

Automatically detects and crops all figures, tables, and algorithms from a PDF.

```bash
python3 scripts/extract_figures.py <pdf_path> <output_dir> [--dpi 300]
```

How it works:
1. Scans all pages with pdfplumber to find `Figure N |` / `Table N |` / `Algorithm N` captions
2. Computes crop boundaries using heuristic rules (figures above captions, tables below captions)
3. Renders **only pages that contain figures** via pdftoppm (not all pages)
4. Crops each figure with safety margins and saves to `figures/`
5. Generates `figures/manifest.json` with metadata for each figure

#### `upload_figures.py` — R2 Image Upload

Uploads extracted figures to Cloudflare R2 for online sharing.

```bash
python3 scripts/upload_figures.py <research_dir>
```

- Reads `figures/manifest.json` for the list of images
- Uploads each to R2 at `papers/<name>/<filename>`
- Writes `figures/urls.json` and adds `"url"` field to each manifest entry
- Gracefully exits when R2 is not configured (exit code 0)
- No pip dependencies (stdlib only)

#### `render_pdf_pages.py` — PDF Page Renderer

Renders each page of a PDF to a high-resolution PNG.

```bash
python3 scripts/render_pdf_pages.py <pdf_path> <output_dir> [--dpi 300] [--pages 1-5]
```

| Argument | Description |
|----------|-------------|
| `pdf_path` | Path to the PDF file |
| `output_dir` | Directory for output PNGs |
| `--dpi` | Resolution, default 300 |
| `--pages` | Page range, e.g. `1-5` or `3` |

#### `crop_figure.py` — Manual Figure Cropping

Crops a rectangular region from a rendered page image. Used as fallback when auto-extraction misses a figure.

```bash
python3 scripts/crop_figure.py <page_image> <output_path> <left> <top> <right> <bottom>
```

| Argument | Description |
|----------|-------------|
| `page_image` | Path to the rendered page PNG |
| `output_path` | Output path for the cropped figure |
| `left top right bottom` | Pixel coordinates of the crop region |

**Coordinate reference (300 DPI):**
- Letter size: ~2550 × 3300 px
- A4 size: ~2480 × 3508 px
- Typical left margin: x ≈ 120
- Typical right margin: x ≈ 2430

## Customization

### Modify writing guidelines

Edit `skills/paper-reader/references/document_template.md` to adjust writing principles, figure embedding format, or the quality checklist. The file contains guidelines rather than a fixed template — Claude decides the document structure based on each paper's content.

### Modify audience profiles

Edit `skills/paper-reader/references/audience_profiles.md` to customize interpretation strategies or add new reader profiles.

## FAQ

**Q: `pdftoppm not found`**

Install Poppler:
```bash
# macOS
brew install poppler
# Ubuntu
sudo apt-get install poppler-utils
```

**Q: `pdfplumber not installed`**

```bash
pip install pdfplumber
```

**Q: `Pillow not installed`**

```bash
pip install Pillow
```

**Q: A figure is cropped incompletely**

The smart extraction uses conservative "crop large, not small" heuristics. If a crop is still incomplete, the workflow automatically falls back to manual verification and re-cropping. You can also run `crop_figure.py` directly with adjusted coordinates.

**Q: How to change the output directory?**

The default is `./research/<paper-short-name>/`. Tell Claude to use a different path when making your request.

**Q: What happens when context gets too long?**

The phased workflow saves progress to `progress.json`, reading notes to `notes.md`, and figure metadata to `manifest.json`. After context compaction, Claude reads these files and resumes from where it left off — no work is lost.

**Q: How do I set up R2 image hosting?**

See the [R2 Image Hosting](#r2-image-hosting-optional) section. You need a Cloudflare account with an R2 bucket and a Worker deployed. Set `R2_WORKER_URL` and `R2_API_KEY` environment variables.

## License

MIT
