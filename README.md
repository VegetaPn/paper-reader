# Paper Reader

[![中文文档](https://img.shields.io/badge/文档-中文版-blue)](./README_zh.md)

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill that transforms academic paper PDFs into detailed, figure-rich interpretation documents tailored to your technical background.

## Features

- **Audience-Aware** — Adapts depth and style based on your profile: Programmer, ML Practitioner, Researcher, or Non-technical
- **Automatic Figure Extraction** — Renders PDF pages at 300 DPI and crops every figure and table at high resolution
- **Structured Output** — Generates a complete Markdown interpretation following a proven template (background, core method, experiments, takeaways)
- **Bilingual** — Automatically detects your language (Chinese or English) and produces the entire document accordingly

## Prerequisites

| Dependency | Purpose | Installation |
|------------|---------|-------------|
| [Python 3](https://www.python.org/) | Run figure extraction scripts | Usually pre-installed |
| [Pillow](https://python-pillow.org/) | Image cropping | `pip install Pillow` |
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

The skill uses two external tools for figure extraction. Install them once:

```bash
# Python image library (required)
pip install Pillow

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

1. **Choose your profile** — Claude asks about your technical background:
   - **Programmer** — explanations use code snippets and programming analogies
   - **ML Practitioner** — focuses on implementation details, ablations, and training cost
   - **Researcher** — emphasizes theoretical novelty and connections to related work
   - **Non-technical** — pure analogies, no code or math

2. **Supplement your knowledge** — multi-select skills you already have (Transformer, distributed training, PyTorch, etc.). Claude skips what you know and dives deeper where it matters.

3. **Automatic interpretation** — Claude will:
   - Read the full PDF
   - Extract all figures and tables (high-res crops)
   - Generate a structured Markdown interpretation
   - Embed every figure in context

4. **Output** — saved to:
   ```
   ./research/<paper-short-name>/
   ├── 论文解读_<PaperTitle>.md   # interpretation document
   └── figures/                    # extracted figures
       ├── fig1_architecture.png
       ├── fig2_results.png
       └── ...
   ```

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
│       │   ├── render_pdf_pages.py   # Render PDF pages to PNG
│       │   └── crop_figure.py        # Crop figures from page images
│       └── references/
│           ├── document_template.md  # Writing guidelines and quality checklist
│           └── audience_profiles.md  # Interpretation strategies per audience
├── README.md                         # This file
└── README_zh.md                      # Chinese documentation
```

### Scripts

#### `skills/paper-reader/scripts/render_pdf_pages.py`

Renders each page of a PDF to a high-resolution PNG.

```bash
python3 skills/paper-reader/scripts/render_pdf_pages.py <pdf_path> <output_dir> [--dpi 300] [--pages 1-5]
```

| Argument | Description |
|----------|-------------|
| `pdf_path` | Path to the PDF file |
| `output_dir` | Directory for output PNGs |
| `--dpi` | Resolution, default 300 |
| `--pages` | Page range, e.g. `1-5` or `3` |

#### `skills/paper-reader/scripts/crop_figure.py`

Crops a rectangular region from a rendered page image.

```bash
python3 skills/paper-reader/scripts/crop_figure.py <page_image> <output_path> <left> <top> <right> <bottom>
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

**Q: `Pillow not installed`**

```bash
pip install Pillow
```

**Q: A figure is cropped incompletely**

The automatic workflow verifies every image and re-crops with extended boundaries if truncation is detected. If running scripts manually, increase the `bottom` coordinate to include the full caption.

**Q: How to change the output directory?**

The default is `./research/<paper-short-name>/`. Tell Claude to use a different path when making your request.

## License

MIT
