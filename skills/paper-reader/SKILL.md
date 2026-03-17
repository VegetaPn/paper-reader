---
name: paper-reader
description: 深度解读学术论文并生成带图片的详细中文解读文档。当用户要求解读论文、阅读论文、分析论文、论文解读、paper reading、读论文、看论文，或者提供了PDF论文文件要求理解其内容时触发。支持PDF论文的图表提取、按读者背景定制解读深度，输出保存到 ./research 目录。
---

# Paper Reader — 论文深度解读

将学术论文转化为面向特定读者的、带有完整图表的中文详细解读文档。

## Language

Detect the user's language from their first message. If the user writes in Chinese, use Chinese for all interactions (questions, status updates) and the output document. If the user writes in English, use English throughout. Maintain this language consistently across the entire workflow.

## Workflow

```
1. Confirm audience → select interpretation strategy
2. Read the PDF → understand structure and core contributions
3. Extract figures → render pages + crop all figures/tables
4. Write interpretation → generate Markdown document per template
5. Embed figures → reference all extracted images in the document
6. Quality check → verify all images complete, structure correct
7. Follow-up Q&A → update document with new insights
```

## Step 1: Confirm Audience & Create Output Directory

Use two rounds of `AskUserQuestion` to build a complete reader profile.

### Round 1: Select base profile

Adapt question text to the detected language. Examples below show both:

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

### Round 2: Gather specific knowledge & skills

After the user selects a base profile, ask a follow-up to collect their specific background. This helps tailor analogies, skip known concepts, and deep-dive where needed.

**Chinese:**
```
question: "您还掌握哪些相关知识或技术？（可多选，也可以在"其他"中自由补充）"
multiSelect: true
options:
  - label: "Transformer / Attention"
    description: "了解自注意力机制、多头注意力、位置编码等"
  - label: "分布式训练"
    description: "了解数据并行、模型并行、Pipeline 并行等"
  - label: "PyTorch / JAX"
    description: "能读写训练代码，熟悉 autograd、模块化 API"
  - label: "线性代数 / 优化理论"
    description: "矩阵分解、梯度下降、收敛性分析等"
```

**English:**
```
question: "What specific knowledge or skills do you have? (Multi-select, or describe in 'Other')"
multiSelect: true
options:
  - label: "Transformer / Attention"
    description: "Self-attention, multi-head attention, positional encoding, etc."
  - label: "Distributed Training"
    description: "Data parallel, model parallel, pipeline parallel, etc."
  - label: "PyTorch / JAX"
    description: "Can read/write training code, familiar with autograd"
  - label: "Linear Algebra / Optimization"
    description: "Matrix decomposition, gradient descent, convergence analysis"
```

The user can also select "Other" to freely describe additional expertise (e.g., "做过 RLHF 微调", "familiar with FlashAttention", "了解 MoE 架构").

### How to use the collected profile

Read [references/audience_profiles.md](references/audience_profiles.md) for the base strategy per profile, then adjust:

- **Skip** concepts the user already knows (e.g., if they selected "Transformer / Attention", don't explain what attention is)
- **Use their tech stack** in code examples (e.g., PyTorch vs JAX)
- **Go deeper** on topics adjacent to their expertise (e.g., if they know distributed training, elaborate on pipeline parallel communication)
- **Choose analogies** from their domain (e.g., for a programmer familiar with databases, compare attention to indexed lookups)

Create output directory:

```bash
# Default: ./research/<paper-short-name>/
mkdir -p ./research/<paper-short-name>/figures/
```

Use a short, descriptive name derived from the paper title (e.g., `attention-residuals`, `flash-attention-2`).

## Step 2: Read the Paper

Read the PDF using the Read tool. For long papers (>10 pages), read in chunks using the `pages` parameter.

Build a mental map:
- What problem does it solve?
- What's the core method?
- What are the key figures and tables?
- What experiments validate the approach?
- What's the main insight/contribution?

## Step 3: Extract All Figures and Tables

This is a critical step. Every significant figure and table must be extracted.

### 3a. Render PDF pages to PNG

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/render_pdf_pages.py <pdf_path> ./research/<name>/pages/ --dpi 300
```

If `pdftoppm` is not available, install it first:
- macOS: `brew install poppler`
- Ubuntu: `sudo apt-get install poppler-utils`

### 3b. Identify figures by viewing rendered pages

Use the Read tool to view each rendered page image. Note the location of every figure and table.

### 3c. Crop each figure

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/crop_figure.py <page_image> <output_path> <left> <top> <right> <bottom>
```

Cropping guidelines:
- At 300 DPI, letter-size pages are ~2550×3300, A4 is ~2480×3508
- Typical left margin: x ≈ 120, right margin: x ≈ 2430
- **Always include the full figure caption** — extend bottom boundary generously
- Use descriptive filenames: `fig1_architecture_overview.png`, `table2_model_configs.png`

### 3d. Verify every cropped image

**Use the Read tool to view every cropped image.** Check for:
- Caption text not truncated at the bottom
- All subfigures/columns visible (not cut off on the right)
- Axis labels readable
- Table rows complete (not missing bottom rows)

If any image is incomplete, re-crop with extended boundaries. This is the most common error — always err on the side of larger crop regions.

## Step 4: Write the Interpretation Document

Read [references/document_template.md](references/document_template.md) for writing guidelines and the quality checklist.

Let the paper's content determine the document structure — a systems paper, a theory paper, and a survey paper should not look the same. Do not force every paper into the same section outline.

Save as `./research/<name>/论文解读_<PaperTitle>.md`.

## Step 5: Embed Figures

Embed every extracted figure using this format:

```markdown
> **Figure N: Descriptive Title**
> Brief explanation of what the figure shows and the key takeaway
>
> ![Figure N: Title](figures/figN_descriptive_name.png)
```

Place figures near the text that discusses them. Every figure and table in the paper should appear in the interpretation.

## Step 6: Quality Check

Run through this checklist before finalizing:

- [ ] All figures and tables from the paper are extracted and embedded
- [ ] Every embedded image is complete (view with Read tool to verify)
- [ ] No truncated captions, missing axis labels, or cut-off table rows
- [ ] The interpretation tells a coherent story, not a section-by-section summary
- [ ] Language and depth match the selected audience profile
- [ ] All image paths in the Markdown are correct relative paths

If any image fails verification, re-crop from the source page with extended boundaries and re-verify.

## Step 7: Follow-up Q&A — Update the Document

After delivering the interpretation, the user may ask follow-up questions. **Always update the interpretation document** with your answers — don't let knowledge stay only in the conversation.

### When to update

Any follow-up that adds substantive knowledge about the paper:
- Deeper explanation of a concept, method, or result
- Clarification of something the user found confusing
- Additional context or comparison the user asked about
- Corrections to the original interpretation

Do NOT update for meta-questions (e.g., "can you export this as PDF?", "where is the file saved?").

### How to update

1. **Answer the user** in the conversation first (so they get an immediate response)
2. **Determine placement** — find the most relevant section in the existing document
3. **Update the document** using the Edit tool:
   - If the follow-up deepens an existing section → expand that section in-place
   - If the follow-up covers a new topic → add a new subsection where it fits logically
   - If the follow-up corrects an error → fix the original text directly
4. **Notify the user** that the document has been updated, with a brief note on what changed

### Writing style for updates

- Integrate seamlessly — the updated document should read as if the content was always there, not as a patched-on Q&A appendix
- Maintain the same audience profile and language as the original document
- If the follow-up requires a new figure extraction, extract and embed it following Step 3

## Scripts

- **`scripts/render_pdf_pages.py`** — Render PDF pages to high-res PNGs via pdftoppm. Run with `python3 ${CLAUDE_SKILL_DIR}/scripts/render_pdf_pages.py <pdf> <output_dir> [--dpi 300] [--pages 1-5]`
- **`scripts/crop_figure.py`** — Crop a rectangular region from a page image. Run with `python3 ${CLAUDE_SKILL_DIR}/scripts/crop_figure.py <page_img> <output> <left> <top> <right> <bottom>`

## References

- **`references/audience_profiles.md`** — Detailed interpretation strategies for each audience profile. Read after user selects their background.
- **`references/document_template.md`** — Recommended Markdown structure for the interpretation document, with figure embedding guidelines.
