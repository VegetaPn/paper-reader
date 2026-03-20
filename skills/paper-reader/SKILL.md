---
name: paper-reader
description: 深度解读学术论文并生成带图片的详细中文解读文档。当用户要求解读论文、阅读论文、分析论文、论文解读、paper reading、读论文、看论文，或者提供了PDF论文文件要求理解其内容时触发。支持PDF论文的图表提取、按读者背景定制解读深度，输出保存到 ./research 目录。
---

# Paper Reader — 论文深度解读

将学术论文转化为面向特定读者的、带有完整图表的中文详细解读文档。

## Language

Detect the user's language from their first message. If the user writes in Chinese, use Chinese for all interactions (questions, status updates) and the output document. If the user writes in English, use English throughout. Maintain this language consistently across the entire workflow.

## Recovery After Context Compaction

**IMPORTANT: Read this section FIRST if context was compacted mid-workflow.**

If you find yourself with limited conversation history (e.g., after auto-compact or manual `/compact`):

1. Look for `./research/*/progress.json` — this file tracks which phase you're in
2. Read `progress.json` to determine:
   - `phase`: Which workflow phase was completed last
   - `pdf_path`: Where the source PDF is
   - `paper_name`: The short name used for the output directory
   - `profile`: The reader's background selection
   - `knowledge_gaps`: Concepts the reader doesn't know (need extra explanation)
   - `figures_manifest`: Path to `manifest.json` for figure extraction status
3. Read `./research/<name>/figures/manifest.json` for all extracted figure metadata
4. Read `./research/<name>/notes.md` for accumulated understanding from deep reading
5. **Resume from the NEXT phase** — do NOT re-run completed phases

Phase progression:
```
scan_done → figures_done → deep_read_done → writing_done → complete
```

## Workflow Overview

```
Phase A: Quick scan + User profiling     (low context)
Phase B: Figure extraction               (automated by script, minimal context)
Phase C: Deep read + Write interpretation (main context usage)
```

```
A1. Quick scan the PDF → identify structure, key concepts, prerequisites
A2. One-round dynamic profiling → ask audience background + knowledge
A3. Create output directory + write progress.json

B1. Run extract_figures.py → auto-extract all figures/tables
B2. Review manifest.json → check what was extracted
B3. Selective verification → only review low-confidence crops
B4. Update progress.json → phase: "figures_done"

C1. Deep read the PDF → build full understanding (chunked, 5 pages at a time)
C2. Write notes.md → persist key insights (survives compact)
C3. Write interpretation document → Markdown per template
C4. Embed figures → reference all extracted images
C5. Quality check → verify structure and image paths
C6. Follow-up Q&A → update document with new insights
```

---

## Phase A: Scan + User Profiling

### Step A1: Quick Scan the Paper & Create Output Directory

Read the PDF quickly (skim abstract, introduction, section headings, figure captions, conclusion) to extract:

1. **Paper topic & domain** — What field/subfield is this paper in?
2. **Core method/technique** — What is the key approach (e.g., sparse attention, mixture of experts, RLHF, diffusion)?
3. **Key prerequisite concepts** — What knowledge does a reader need to understand this paper? Extract 3-4 specific concepts that are central to this paper. These will become the knowledge-check options in Step A2.

Examples of extracted prerequisites by paper type:
- A paper on FlashAttention → prerequisites: "GPU memory hierarchy / SRAM vs HBM", "Attention mechanism", "IO complexity analysis", "CUDA kernel programming"
- A paper on MoE routing → prerequisites: "Mixture of Experts architecture", "Top-k gating / routing", "Load balancing in distributed systems", "Transformer architecture"
- A paper on RLHF → prerequisites: "Reinforcement Learning basics (reward, policy)", "Language model fine-tuning", "Human preference modeling", "PPO algorithm"
- A paper on visual generation → prerequisites: "Diffusion models / score matching", "VAE / latent space", "U-Net architecture", "CLIP / image-text alignment"

Create output directory:

```bash
# Default: ./research/<paper-short-name>/
mkdir -p ./research/<paper-short-name>/figures/
```

Use a short, descriptive name derived from the paper title (e.g., `attention-residuals`, `flash-attention-2`).

### Step A2: Dynamic One-Round Profiling

Use a single `AskUserQuestion` call with **two questions** to collect the reader's background and paper-specific knowledge simultaneously.

#### Question 1: Technical background (base profile)

This is always the same 4 options:

**Chinese:**
```
question: "您的技术背景是？这将决定解读的深度和风格。"
options:
  - label: "程序员 (Recommended)"
    description: "有编程经验，了解基本数据结构，用代码和类比解释论文"
  - label: "ML 从业者"
    description: "熟悉 PyTorch/TF，了解 Transformer，关注实现细节和实验"
  - label: "研究者"
    description: "经常读论文，深入理论，关注创新点和方法论"
  - label: "非技术背景"
    description: "了解 AI 大方向，不需要代码和数学，纯类比解释"
```

**English:**
```
question: "What's your technical background? This determines the depth and style."
options:
  - label: "Programmer (Recommended)"
    description: "Has coding experience; will use code snippets and analogies"
  - label: "ML Practitioner"
    description: "Familiar with PyTorch/TF and Transformers; focus on implementation"
  - label: "Researcher"
    description: "Reads papers regularly; focus on theory and novelty"
  - label: "Non-technical"
    description: "High-level understanding; no code or math, pure analogies"
```

#### Question 2: Paper-specific knowledge (dynamically generated)

Generate 3-4 options based on the **key prerequisite concepts extracted in Step A1**. Each option should name a specific concept/technique that is central to understanding THIS paper.

**Chinese template:**
```
question: "这篇论文涉及以下关键概念，您了解哪些？（可多选，也可以在"其他"中自由补充）"
multiSelect: true
options:
  - label: "<Concept 1 from the paper>"
    description: "<Brief description of what this concept entails>"
  - label: "<Concept 2 from the paper>"
    description: "<Brief description>"
  - label: "<Concept 3 from the paper>"
    description: "<Brief description>"
  - label: "<Concept 4 from the paper>"   # optional, only if 4 distinct concepts
    description: "<Brief description>"
```

**English template:**
```
question: "This paper involves the following key concepts. Which are you familiar with? (Multi-select, or describe in 'Other')"
multiSelect: true
options:
  - label: "<Concept 1>"
    description: "<Brief description>"
  - ...
```

**Guidelines for generating good options:**
- Each option should be a **specific concept from this paper**, not a generic field (e.g., "FlashAttention's tiling strategy" not "machine learning")
- Options should cover the **major prerequisites** — knowing which ones the user understands determines what needs extra explanation
- Descriptions should be concrete enough for the user to honestly self-assess (e.g., "了解 KV Cache 的内存占用问题及其优化方法" not just "KV Cache")
- The user can always select "Other" to add anything not listed

#### How to use the collected profile

Read [references/audience_profiles.md](references/audience_profiles.md) for the base strategy per profile, then adjust based on the paper-specific knowledge selections:

- **Skip** concepts the user already knows (e.g., if they selected the attention mechanism option, don't explain what attention is — jump straight to what's new)
- **Explain thoroughly** concepts the user did NOT select — these are the knowledge gaps to bridge
- **Use their tech stack** in code examples (infer from base profile + any mentions in "Other")
- **Go deeper** on topics adjacent to their selected expertise
- **Choose analogies** from their domain

### Step A3: Persist State

Write `./research/<name>/progress.json`:

```json
{
  "phase": "scan_done",
  "pdf_path": "<absolute path to PDF>",
  "paper_name": "<short-name>",
  "profile": "<selected profile>",
  "knowledge_gaps": ["<concept user did NOT select>", "..."],
  "known_concepts": ["<concept user selected>", "..."],
  "figures_manifest": "figures/manifest.json",
  "notes_file": "notes.md",
  "output_file": "论文解读_<PaperTitle>.md"
}
```

---

## Phase B: Figure Extraction (Automated)

This phase uses `extract_figures.py` to automatically detect and crop all figures and tables, **dramatically reducing context usage** compared to manually viewing each page.

### Step B1: Run extract_figures.py

`${CLAUDE_SKILL_DIR}` is the absolute path where this skill is installed — use it to locate bundled scripts.

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/extract_figures.py <pdf_path> ./research/<name>/ --dpi 300
```

This script will:
- Scan all pages with pdfplumber to find Figure/Table/Algorithm captions
- Render **only pages that contain figures** (not all pages)
- Auto-crop each figure using heuristic boundary detection
- Output cropped images to `./research/<name>/figures/`
- Generate `./research/<name>/figures/manifest.json` with metadata

If `pdftoppm` is not available, install it first:
- macOS: `brew install poppler`
- Ubuntu: `sudo apt-get install poppler-utils`

If `pdfplumber` is not available:
```bash
pip install pdfplumber Pillow
```

### Step B2: Review Manifest

Read `./research/<name>/figures/manifest.json` (this is a small JSON file, very low context cost).

Check:
- `total_figures`: Does this match the expected count from your scan?
- `needs_review_count`: How many figures need manual verification?
- Each figure entry has `filename`, `caption_type`, `number`, `caption_text`, `page_number`

If the total count seems low (the script may miss some figures), note which ones are missing.

### Step B3: Selective Verification

**For ALL tables** (regardless of `needs_review` flag):
Tables are particularly prone to truncation because their content rows (especially description columns like "Task/Domain") can be mistaken for body text by the auto-cropper.

1. Use the Read tool to view the cropped image
2. Check: Is the **last row** of the table visible? Is there a clear bottom border or whitespace below the last data row?
3. If the table appears truncated (content cut off at the bottom, missing rows), re-crop with expanded bounds

**For figures/algorithms where `"needs_review": true`** in the manifest:

1. Use the Read tool to view the cropped image
2. Check: Is the full figure visible? Is the caption complete? Are there cut-off edges?

**For any bad crops**, re-crop manually using the existing crop_figure.py:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/crop_figure.py <page_image> <output_path> <left> <top> <right> <bottom>
```

For any figures the script missed entirely:
1. Render the specific page: `python3 ${CLAUDE_SKILL_DIR}/scripts/render_pdf_pages.py <pdf_path> ./research/<name>/pages/ --dpi 300 --pages <N>`
2. View the page with Read tool
3. Crop manually with crop_figure.py

### Step B3.5: Upload Figures to R2 (Optional)

If the user has configured R2 image hosting (environment variables `R2_WORKER_URL` and `R2_API_KEY`, or a `.env` file), automatically upload all extracted figures:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/upload_figures.py ./research/<name>/
```

The script will:
- Read `figures/manifest.json` for all extracted images
- Upload each to R2 at path `papers/<name>/<filename>`
- Generate `figures/urls.json` (filename → R2 URL mapping)
- Update `manifest.json`, adding a `"url"` field to each entry

If R2 is not configured or upload fails, the script exits gracefully (exit code 0). Subsequent steps will automatically fall back to local relative paths — no manual intervention needed.

### Step B4: Update Progress

Update `progress.json`:
```json
{
  "phase": "figures_done",
  ...
}
```

---

## Phase C: Deep Read + Write

### Step C1: Deep Read the Paper

Read the PDF using the Read tool. For long papers (>10 pages), read in chunks of ~5 pages using the `pages` parameter.

Build a mental map:
- What problem does it solve?
- What's the core method?
- What are the key figures and tables?
- What experiments validate the approach?
- What's the main insight/contribution?

### Step C2: Write Notes (Persist Understanding)

Write key insights to `./research/<name>/notes.md` as you read. This file **survives context compaction** and ensures you don't lose understanding.

Format:
```markdown
# Reading Notes: <Paper Title>

## Core Problem
<1-2 sentences>

## Key Method
<description>

## Main Results
- ...

## Important Figures
- Figure 1: <what it shows>
- Table 2: <what it shows>

## Key Insights for Interpretation
- <insight 1>
- <insight 2>
```

Update `progress.json` phase to `"deep_read_done"` after completing the read.

### Step C3: Write the Interpretation Document

Read [references/document_template.md](references/document_template.md) for writing guidelines and the quality checklist.

Let the paper's content determine the document structure — a systems paper, a theory paper, and a survey paper should not look the same. Do not force every paper into the same section outline.

Save as `./research/<name>/论文解读_<PaperTitle>.md`.

### Step C4: Embed Figures

Check each entry in `manifest.json` for a `"url"` field (added by Step B3.5 if R2 upload succeeded):

- **Has `"url"` field** → use the R2 online URL (document can be shared directly):
  ```markdown
  > **Figure N: Descriptive Title**
  > Brief explanation of what the figure shows and the key takeaway
  >
  > ![Figure N: Title](https://r2-imagebed.xxx.workers.dev/papers/xxx/figN.png)
  ```

- **No `"url"` field** → fall back to local relative path:
  ```markdown
  > **Figure N: Descriptive Title**
  > Brief explanation of what the figure shows and the key takeaway
  >
  > ![Figure N: Title](figures/figN_descriptive_name.png)
  ```

Use the actual filenames from `manifest.json`. Place figures near the text that discusses them. Every figure and table in the paper should appear in the interpretation.

### Step C5: Quality Check

Run through this checklist before finalizing:

- [ ] All figures and tables from the paper are extracted and embedded
- [ ] Verify all image paths exist using `ls ./research/<name>/figures/` (do NOT Read every image again)
- [ ] The interpretation tells a coherent story, not a section-by-section summary
- [ ] Language and depth match the selected audience profile
- [ ] All image paths in the Markdown are correct (R2 URLs if uploaded, relative paths otherwise)
- [ ] `progress.json` phase updated to `"writing_done"`

Update `progress.json` phase to `"complete"`.

### Step C6: Follow-up Q&A — Update the Document

After delivering the interpretation, the user may ask follow-up questions. **Always update the interpretation document** with your answers — don't let knowledge stay only in the conversation.

#### When to update

Any follow-up that adds substantive knowledge about the paper:
- Deeper explanation of a concept, method, or result
- Clarification of something the user found confusing
- Additional context or comparison the user asked about
- Corrections to the original interpretation

Do NOT update for meta-questions (e.g., "can you export this as PDF?", "where is the file saved?").

#### How to update

1. **Answer the user** in the conversation first (so they get an immediate response)
2. **Determine placement** — find the most relevant section in the existing document
3. **Update the document** using the Edit tool:
   - If the follow-up deepens an existing section → expand that section in-place
   - If the follow-up covers a new topic → add a new subsection where it fits logically
   - If the follow-up corrects an error → fix the original text directly
4. **Notify the user** that the document has been updated, with a brief note on what changed

#### Writing style for updates

- Integrate seamlessly — the updated document should read as if the content was always there, not as a patched-on Q&A appendix
- Maintain the same audience profile and language as the original document
- If the follow-up requires a new figure extraction, extract and embed it following Phase B steps

## Scripts

- **`scripts/extract_figures.py`** — Smart figure/table extraction. Scans PDF for captions with pdfplumber, renders only needed pages, auto-crops with heuristic boundaries, outputs manifest.json. Run with `python3 ${CLAUDE_SKILL_DIR}/scripts/extract_figures.py <pdf> <output_dir> [--dpi 300]`
- **`scripts/upload_figures.py`** — Upload extracted figures to Cloudflare R2 image hosting. Reads manifest.json, uploads via R2 Worker, writes urls.json and updates manifest with URLs. No pip dependencies (stdlib only). Gracefully skips when R2 is not configured. Run with `python3 ${CLAUDE_SKILL_DIR}/scripts/upload_figures.py <research_dir>`
- **`scripts/render_pdf_pages.py`** — Render PDF pages to high-res PNGs via pdftoppm. Run with `python3 ${CLAUDE_SKILL_DIR}/scripts/render_pdf_pages.py <pdf> <output_dir> [--dpi 300] [--pages 1-5]`
- **`scripts/crop_figure.py`** — Crop a rectangular region from a page image. Run with `python3 ${CLAUDE_SKILL_DIR}/scripts/crop_figure.py <page_img> <output> <left> <top> <right> <bottom>`

## References

- **`references/audience_profiles.md`** — Detailed interpretation strategies for each audience profile. Read after user selects their background.
- **`references/document_template.md`** — Recommended Markdown structure for the interpretation document, with figure embedding guidelines.
