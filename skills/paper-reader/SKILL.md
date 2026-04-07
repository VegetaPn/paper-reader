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
   - `pdf_path`: Filename of the PDF saved in the research directory (always a local copy)
   - `source_url`: The original URL if the paper was downloaded (null if local file)
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
A0. Resolve input → if URL, download PDF; detect/reuse existing directory
A1. Quick scan the PDF → identify structure, key concepts, prerequisites
A2. One-round dynamic profiling → ask audience background + knowledge
A3. Create output directory (if needed) + write progress.json

B1. Run extract_figures.py → auto-extract all figures/tables
B2. Review manifest.json → check what was extracted
B3. Selective verification → only review low-confidence crops
B3.5. Run upload_figures.py → upload to R2 if configured (ALWAYS attempt)
B4. Update progress.json → phase: "figures_done"
B5. /compact → free context for Phase C (MANDATORY)

C1. Deep read the PDF → build full understanding (chunked, 5 pages at a time)
C2. Write notes.md → persist key insights (survives compact)
C3. Write interpretation document → Markdown per template
C4. Embed figures → reference all extracted images
C5. Quality check → verify structure and image paths
C6. Follow-up Q&A → update document with new insights
```

---

## Phase A: Scan + User Profiling

### Step A0: Resolve Input Source

Before scanning, determine what the user provided and prepare the PDF file.

#### If the user provides a URL (not a local file path):

Download the PDF and save it locally. Common URL patterns:

- **Direct PDF link** (e.g., `https://arxiv.org/pdf/2301.12345.pdf`):
  ```bash
  curl -L -o ./research/<paper-short-name>/paper.pdf "<url>"
  ```

- **arXiv abstract page** (e.g., `https://arxiv.org/abs/2301.12345`):
  Convert to PDF URL by replacing `/abs/` with `/pdf/` and appending `.pdf`:
  ```bash
  curl -L -o ./research/<paper-short-name>/paper.pdf "https://arxiv.org/pdf/2301.12345.pdf"
  ```

- **Other paper hosting sites** (Semantic Scholar, OpenReview, ACL Anthology, etc.):
  Use `curl -L` to follow redirects and download the PDF. If the URL is an HTML page, try to extract the actual PDF link first.

- **Non-PDF URL** (e.g., HTML page of a blog post or paper summary):
  Use `curl -L` to download the content. If it's HTML, save it as-is for reference. Try to find a linked PDF on the page.

**Important**: Create a minimal directory first (just enough to save the PDF), then determine the proper short name after scanning. If needed, rename later.

```bash
# Temporary download — may rename directory after scanning
mkdir -p ./research/tmp-download/
curl -L -o ./research/tmp-download/paper.pdf "<url>"
```

After downloading, verify it's a valid PDF:
```bash
file ./research/tmp-download/paper.pdf
```

#### Fallback: Use `/web-access` or `/agent-browser` when `curl` fails

If `curl` fails (e.g., 403 Forbidden, CAPTCHA, JavaScript-rendered page, requires login, or the downloaded file is not a valid PDF), use the `/web-access` or `/agent-browser` skill as a fallback:

1. **Try `/web-access` first** — invoke it via the Skill tool to navigate to the URL, which can handle JavaScript rendering, anti-bot protections, and dynamic pages. Ask it to:
   - Navigate to the paper URL
   - Find and download the PDF file (look for download buttons, PDF links, etc.)
   - Save the PDF to `./research/tmp-download/paper.pdf`

2. **If `/web-access` also fails, try `/agent-browser`** — it provides full browser automation and can handle more complex scenarios like:
   - Sites requiring cookie acceptance or CAPTCHA solving
   - Multi-step navigation to reach the PDF (e.g., click "Download PDF" button)
   - Pages that serve PDFs via JavaScript redirects

3. **If the URL points to a non-PDF resource** (e.g., an HTML blog post, a conference talk page), use `/web-access` to fetch and save the page content as HTML/text for reference, then check if there's a linked PDF on the page.

**Decision flow:**
```
curl -L → success + valid PDF? → done
  ↓ fail
/web-access → navigate + download PDF → success? → done
  ↓ fail
/agent-browser → full browser automation → success? → done
  ↓ fail
Ask user for alternative source or local file
```

Only ask the user for an alternative source after all automated methods have been exhausted.

#### If the user provides a local file path:

No download needed — just verify the file exists and is readable. Record the absolute path.

#### Detect and reuse existing directory

**IMPORTANT**: Before creating any new directory, check if the user has already created or specified a target directory:

1. **User explicitly provides an output directory** (e.g., "save to ./research/my-paper/") → use that directory as-is. Only create `figures/` subdirectory if it doesn't exist.
2. **User previously created a directory** for this paper (e.g., there's already a `./research/<name>/` with a `progress.json` or other files) → reuse it. Do NOT create a new directory with a different name.
3. **Check for existing directories** before creating:
   ```bash
   ls ./research/ 2>/dev/null
   ```
   If a directory clearly matches the paper being analyzed (by name similarity or by containing a `progress.json` referencing the same PDF), reuse it.

If a URL was downloaded to `./research/tmp-download/`, move the PDF to the final directory once the short name is determined:
```bash
mv ./research/tmp-download/paper.pdf ./research/<paper-short-name>/paper.pdf
rmdir ./research/tmp-download/ 2>/dev/null
```

### Step A1: Quick Scan the Paper

#### ⚠️ ANTI-HALLUCINATION RULE

**NEVER summarize the paper based on the URL, the arXiv ID, or your training data.** You MUST base ALL descriptions of the paper (title, topic, method, summary) on text programmatically extracted from the actual PDF. If `extract_metadata.py` fails and you cannot extract text, tell the user instead of guessing.

#### Step A1.1: Programmatic Metadata Extraction (MANDATORY — run BEFORE any PDF reading)

```bash
python3 <skill_base_dir>/scripts/extract_metadata.py <pdf_path> ./research/tmp-download/
```

This script uses pdfplumber to extract the **actual** title, authors, abstract, and section headings from the PDF. Its output is ground truth.

After running, **immediately** read the output:

```bash
cat ./research/tmp-download/metadata.json
```

#### Step A1.2: Summarize Based on metadata.json ONLY

Using the extracted `title`, `abstract`, and `section_headings` from `metadata.json`:

1. **Paper topic & domain** — Determine from the abstract and section headings. Do NOT guess from the URL.
2. **Core method/technique** — Identify from the abstract text.
3. **Key prerequisite concepts** — Extract 3-4 specific concepts based on the abstract and headings. These will become the knowledge-check options in Step A2.

**When presenting the paper summary to the user, you MUST quote or closely paraphrase the extracted title and abstract. Do NOT rephrase in a way that changes the paper's actual topic.**

Examples of extracted prerequisites by paper type:
- A paper on FlashAttention → prerequisites: "GPU memory hierarchy / SRAM vs HBM", "Attention mechanism", "IO complexity analysis", "CUDA kernel programming"
- A paper on MoE routing → prerequisites: "Mixture of Experts architecture", "Top-k gating / routing", "Load balancing in distributed systems", "Transformer architecture"
- A paper on RLHF → prerequisites: "Reinforcement Learning basics (reward, policy)", "Language model fine-tuning", "Human preference modeling", "PPO algorithm"
- A paper on visual generation → prerequisites: "Diffusion models / score matching", "VAE / latent space", "U-Net architecture", "CLIP / image-text alignment"

#### Step A1.3: Determine Output Directory

After confirming the paper title from metadata.json, determine the output directory:

```bash
# Only create if no existing directory is being reused (see Step A0)
mkdir -p ./research/<paper-short-name>/figures/
```

Use a short, descriptive name derived from the **extracted** paper title (e.g., `attention-residuals`, `flash-attention-2`). If the PDF was initially downloaded to `tmp-download/`, move both the PDF and `metadata.json` to the final directory.

#### Save the original PDF to the research directory

**MANDATORY**: The original PDF must always be saved inside the research directory so the user has a permanent local copy alongside the interpretation. Use a descriptive filename with the arXiv ID or paper title.

- **If downloaded from URL** → move/rename from temp location:
  ```bash
  mv ./research/tmp-download/paper.pdf ./research/<paper-short-name>/<PaperTitle>_<arXivID>.pdf
  rmdir ./research/tmp-download/ 2>/dev/null
  ```
  Example: `./research/flash-attention/FlashAttention2_2307.08691.pdf`

- **If user provided a local file path** → copy it into the research directory:
  ```bash
  cp <user-provided-path> ./research/<paper-short-name>/<PaperTitle>_<arXivID>.pdf
  ```

- **If downloaded to /tmp/** → copy it before it gets cleaned up:
  ```bash
  cp /tmp/<filename>.pdf ./research/<paper-short-name>/<PaperTitle>_<arXivID>.pdf
  ```

The saved PDF path should be recorded in `progress.json` as `pdf_path` (relative to the research directory).

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

Ensure the output directory and `figures/` subdirectory exist (skip if already present from Step A0):

```bash
mkdir -p ./research/<name>/figures/
```

Write `./research/<name>/progress.json`:

```json
{
  "phase": "scan_done",
  "pdf_path": "<filename of PDF saved in research dir, e.g. FlashAttention2_2307.08691.pdf>",
  "source_url": "<original URL if provided, null otherwise>",
  "paper_name": "<short-name>",
  "paper_title": "<exact title from metadata.json — this is the ground truth reference>",
  "profile": "<selected profile>",
  "knowledge_gaps": ["<concept user did NOT select>", "..."],
  "known_concepts": ["<concept user selected>", "..."],
  "figures_manifest": "figures/manifest.json",
  "metadata_file": "metadata.json",
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

### Step B3: Verification — Tables First, Then Flagged Figures

Tables are the #1 source of cropping failures. The auto-cropper uses text heuristics to find table boundaries, but **text-heavy tables** (prompt templates, method descriptions, theoretical comparisons) have content that looks like body paragraphs, causing premature truncation.

#### B3.1: Verify ALL tables (MANDATORY, every single one)

For each table in the manifest:

1. **Read the PDF first to know what to expect.** Before viewing the cropped image, read the page in the PDF where the table lives (use the `pages` parameter of the Read tool). Count the number of rows/columns the table should have. This gives you ground truth.

2. **View the cropped image** with the Read tool.

3. **Cross-check against the PDF:**
   - Does the crop contain ALL rows from the PDF version?
   - Is the caption complete (not cut off mid-sentence)?
   - Is there content below the visible area that was cut off?
   - For text-heavy tables (prompts, descriptions): is the last line of content visible?

4. **If ANY content is missing**, re-crop with generous bounds:
   ```bash
   # First, render the full page if not already available
   python3 ${CLAUDE_SKILL_DIR}/scripts/render_pdf_pages.py <pdf_path> ./research/<name>/pages/ --dpi 300 --pages <N>
   # View the full page to find correct bounds
   # Then crop with generous margins (better to have extra whitespace than truncation)
   python3 ${CLAUDE_SKILL_DIR}/scripts/crop_figure.py <page_image> <output_path> <left> <top> <right> <bottom>
   ```

**Why tables fail:** The cropper's `_find_lower_boundary` tries to detect where the table ends by finding "body paragraph" text below it. But tables containing long descriptions, formulas, or prompt templates have content rows that resemble body text. The improved script uses PDF line/rect detection and requires 3+ consecutive prose lines for confirmation, but edge cases will always exist.

#### B3.2: Verify flagged figures (`needs_review: true`)

For figures/algorithms marked `needs_review`:
1. Use the Read tool to view the cropped image
2. Check: Is the full figure visible? Is the caption complete? Are there cut-off edges?
3. Re-crop if needed using crop_figure.py

#### B3.3: Check for missing figures

Compare the manifest count against the expected total from the paper scan:
- Missing figures usually happen when captions use unusual formatting (e.g., "Fig." vs "Figure", no colon/period after the number)
- For missing figures: render the page, view it, crop manually

For any figures the script missed entirely:
1. Render the specific page: `python3 ${CLAUDE_SKILL_DIR}/scripts/render_pdf_pages.py <pdf_path> ./research/<name>/pages/ --dpi 300 --pages <N>`
2. View the page with Read tool
3. Crop manually with crop_figure.py

### Step B3.5: Upload Figures to R2 (Auto — runs if R2 is configured)

**IMPORTANT: Always attempt this step.** Run the upload script unconditionally — it will detect whether R2 is configured and gracefully skip if not. Do NOT skip this step yourself.

If R2 image hosting is configured (environment variables `R2_WORKER_URL` and `R2_API_KEY`, or a `.env` file), the script uploads all extracted figures:

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

### Step B5: Compact Before Phase C

**MANDATORY**: After completing Phase B, you MUST run `/compact` before starting Phase C.

Phase B (especially figure verification with image reads) consumes a large amount of context. Phase C (deep reading + writing) needs substantial context space for reading the full PDF and generating the interpretation document. Without compacting, the session will likely run out of context mid-Phase C, forcing a disruptive manual compact or auto-compact at a bad time.

Run `/compact` with a focused instruction to preserve what matters:

```
/compact Preserve: paper_name, pdf_path, reader profile, knowledge_gaps, all figure filenames from manifest.json, and any figure issues found during verification. Discard: raw image data, intermediate crop attempts, tool error messages.
```

After compact completes, re-read `progress.json` and `manifest.json` to restore working state, then proceed to Phase C.

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

#### ⚠️ WRITING-PHASE ANTI-HALLUCINATION RULES

The most dangerous hallucinations are not inventing a wrong paper title (Phase A prevents that). They are **fabricating concrete details to fill in gaps** in the paper's description. Follow these rules strictly:

1. **NEVER fabricate specific examples the paper didn't give.** If the paper says "the proposer compares candidates", do NOT invent a concrete example like "candidate A scored 14 on LawBench using method X...". Instead, describe the behavior in general terms, or quote the paper directly.

2. **NEVER invent specific names, filenames, or structures the paper didn't mention.** If the paper says "stores code, scores, and traces in a filesystem", do NOT fabricate file names like `harness.py`, `scores.json`, `traces/`. Use the paper's own terms.

3. **NEVER fill in details of a figure/table you haven't actually read.** If you describe what Figure 5 shows, you MUST have viewed the extracted image or read the caption text. Do not guess based on the figure's title alone.

4. **Distinguish "paper says" from "I interpret".** When adding your own analysis, commentary, or connections to other work, use explicit markers like *[解读者注]* or "从这个结果可以推断..." to separate your interpretation from the paper's claims.

5. **Numbers must come from the paper.** Every percentage, score, count, or comparison number in your interpretation must be traceable to a specific table, figure, or sentence in the PDF. Do not round, approximate, or "remember" numbers — re-read the source.

6. **Do not over-specify model details.** If the paper says "we use Model X", do not add qualifiers (e.g., "with extended thinking", "version 3.5") unless the paper explicitly states them. Conversely, do not omit important qualifiers the paper does mention.

7. **Do not fabricate motivation or causation.** If the paper shows a result but doesn't explain *why* it happened, do not invent a causal narrative. Say "the paper observes X but does not explain the mechanism" rather than fabricating an explanation.

8. **Inline source references for every key claim.** This is the primary defense against hallucination during writing. Every number, result, and important factual claim in the interpretation MUST have an inline source reference pointing back to the paper:
   - After numbers/results: "平均准确率 48.6%（Table 2）"
   - After method claims: "proposer 通过文件系统检索信息（Section 3, p.3）"
   - After the paper's own arguments: "论文指出 harness 差异可达 6× 性能差距（Section 1）"

   **If you cannot cite a specific source for a claim, you are likely hallucinating — stop and re-read the PDF.**

9. **Mark your own interpretation explicitly.** Use *[解读者注]* (Chinese) or *[Interpreter's note]* (English) to separate your commentary from the paper's claims. This includes: analogies to other work, speculation about why something works, implications the paper didn't discuss, and any limitations you infer but the paper didn't state.

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
- [ ] **Factual accuracy**: Every number, percentage, and comparison is traceable to a specific table/figure/sentence in the PDF
- [ ] **No fabricated details**: No invented file names, specific examples, variable names, or causal explanations that don't appear in the paper
- [ ] **Source attribution**: Key claims are marked with page/section/table references (e.g., "(Section 3)", "(Table 2)", "(p.6)")
- [ ] **Interpretation vs fact**: Your own analysis/commentary is clearly distinguished from the paper's claims (use markers like *[解读者注]*)
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

- **`scripts/extract_metadata.py`** — **MUST run before any PDF reading in Step A1.** Extracts title, authors, abstract, and section headings from PDF using pdfplumber text extraction. Outputs `metadata.json` as ground truth to prevent hallucination. Run with `python3 ${CLAUDE_SKILL_DIR}/scripts/extract_metadata.py <pdf> <output_dir>`
- **`scripts/extract_figures.py`** — Smart figure/table extraction. Scans PDF for captions with pdfplumber, renders only needed pages, auto-crops with heuristic boundaries, outputs manifest.json. Run with `python3 ${CLAUDE_SKILL_DIR}/scripts/extract_figures.py <pdf> <output_dir> [--dpi 300]`
- **`scripts/upload_figures.py`** — Upload extracted figures to Cloudflare R2 image hosting. Reads manifest.json, uploads via R2 Worker, writes urls.json and updates manifest with URLs. No pip dependencies (stdlib only). Gracefully skips when R2 is not configured. Run with `python3 ${CLAUDE_SKILL_DIR}/scripts/upload_figures.py <research_dir>`
- **`scripts/render_pdf_pages.py`** — Render PDF pages to high-res PNGs via pdftoppm. Run with `python3 ${CLAUDE_SKILL_DIR}/scripts/render_pdf_pages.py <pdf> <output_dir> [--dpi 300] [--pages 1-5]`
- **`scripts/crop_figure.py`** — Crop a rectangular region from a page image. Run with `python3 ${CLAUDE_SKILL_DIR}/scripts/crop_figure.py <page_img> <output> <left> <top> <right> <bottom>`

## References

- **`references/audience_profiles.md`** — Detailed interpretation strategies for each audience profile. Read after user selects their background.
- **`references/document_template.md`** — Recommended Markdown structure for the interpretation document, with figure embedding guidelines.
