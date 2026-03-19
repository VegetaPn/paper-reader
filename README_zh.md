# Paper Reader — 论文深度解读工具

[![English](https://img.shields.io/badge/doc-English-blue)](./README.md)

一个 [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 技能（Skill），能够将学术论文 PDF 自动转化为面向特定读者的、带有完整图表的详细解读文档。

## 功能特点

- **读者画像定制** — 根据你的技术背景（程序员 / ML 从业者 / 研究者 / 非技术人员）自动调整解读深度和风格
- **智能图表提取** — 用 pdfplumber 检测 caption 位置，仅渲染包含图表的页面，自动裁剪并生成 manifest.json 元数据
- **R2 图床支持** — 可选上传图片到 Cloudflare R2，文档中使用在线链接，方便直接分享
- **断点续传** — 分阶段工作流 + `progress.json` 状态持久化，context 压缩后自动恢复进度
- **结构化解读文档** — 按模板生成完整的 Markdown 解读（背景知识、核心方案、实验分析、关键结论等）
- **多语言支持** — 自动检测用户语言，支持中文和英文输出

## 前置依赖

| 依赖 | 用途 | 安装方式 |
|------|------|----------|
| [Python 3](https://www.python.org/) | 运行图表提取脚本 | 系统通常自带 |
| [Pillow](https://python-pillow.org/) | 图片裁剪 | `pip install Pillow` |
| [pdfplumber](https://github.com/jsvine/pdfplumber) | 智能 caption 检测 | `pip install pdfplumber` |
| [Poppler](https://poppler.freedesktop.org/) | PDF 渲染为 PNG | macOS: `brew install poppler`<br>Ubuntu: `sudo apt-get install poppler-utils` |
| [Claude Code](https://docs.anthropic.com/en/docs/claude-code) | 运行 Skill | `npm install -g @anthropic-ai/claude-code` |

## 安装

### 方式一：通过 skills.sh 一键安装（推荐）

一条命令安装到 Claude Code、Cursor、Copilot 等 35+ Agent 平台：

```bash
npx skills add VegetaPn/paper-reader
```

CLI 会自动检测已安装的 Agent，安装到正确位置。

### 方式二：通过 Claude Code Plugin Marketplace

```
/plugin marketplace add VegetaPn/paper-reader
/plugin install paper-reader@paper-reader
```

### 方式三：手动安装

将仓库直接克隆到 Claude Code 个人技能目录，即刻生效：

```bash
git clone https://github.com/VegetaPn/paper-reader.git ~/.claude/skills/paper-reader
```

下次启动 Claude Code 时会自动发现此 Skill。

#### 仅安装到单个项目

如果只想在某个项目中使用：

```bash
cd /path/to/your/project
git clone https://github.com/VegetaPn/paper-reader.git .claude/skills/paper-reader
```

#### 通过 `--add-dir` 加载

也可以克隆到任意位置，启动时指定目录：

```bash
git clone https://github.com/VegetaPn/paper-reader.git ~/tools/paper-reader
claude --add-dir ~/tools/paper-reader
```

### 安装系统依赖

Skill 使用外部工具来提取图表，需要一次性安装：

```bash
# Python 库（必需）
pip install Pillow pdfplumber

# PDF 渲染工具（必需）
# macOS
brew install poppler
# Ubuntu / Debian
sudo apt-get install poppler-utils
```

## 使用方法

安装完成后，在 Claude Code 中直接与论文交互即可：

```
帮我解读这篇论文 /path/to/paper.pdf
```

```
Read this paper /path/to/paper.pdf
```

### 使用流程

工作流分三个阶段，每个阶段的状态会持久化到 `progress.json`，即使 context 被压缩也能恢复进度：

**阶段 A — 扫描 & 用户画像**
1. **快速扫描** — Claude 浏览 PDF，识别结构、领域和前置知识
2. **选择读者画像** — 选择最匹配的角色：
   - **程序员** — 用代码片段和编程类比解释论文
   - **ML 从业者** — 关注实现细节、消融实验和训练开销
   - **研究者** — 聚焦理论贡献和与相关工作的联系
   - **非技术背景** — 纯类比解释，无代码无公式
3. **知识确认** — 可多选你已掌握的技术，Claude 会跳过已知概念，深入你关心的部分

**阶段 B — 图表提取（自动化）**
4. **智能提取** — `extract_figures.py` 用 pdfplumber 扫描 PDF，检测所有图表 caption，仅渲染需要的页面，自动裁剪
5. **选择性验证** — 仅对低置信度的裁剪做人工验证，高置信度的直接通过
6. **R2 上传**（可选）— 配置后自动上传图片到 Cloudflare R2，方便在线分享

**阶段 C — 深度阅读 & 写作**
7. **深度阅读** — Claude 分块阅读全文，关键理解写入 `notes.md`
8. **撰写解读** — 生成结构化 Markdown 文档，嵌入所有图表
9. **质量检查** — 验证完整性和正确性

### 输出结果

```
./research/<paper-short-name>/
├── 论文解读_<PaperTitle>.md    # 解读文档
├── progress.json               # 工作流状态（用于恢复）
├── notes.md                    # 阅读笔记（用于恢复）
├── figures/
│   ├── manifest.json           # 图表元数据 + R2 URL
│   ├── urls.json               # 文件名 → URL 映射（上传后生成）
│   ├── fig1_architecture.png
│   ├── table2_results.png
│   └── ...
└── pages/                      # 渲染的 PDF 页面（仅包含图表的页）
    ├── page-01.png
    └── ...
```

### R2 图床配置（可选）

配置 Cloudflare R2 后，图片会自动上传到云端，解读文档使用在线链接：

```bash
export R2_WORKER_URL=https://your-r2-worker.workers.dev
export R2_API_KEY=your-api-key
```

也可以在项目根目录创建 `.env` 文件。配置后解读文档中的图片链接会自动替换为在线 URL，无需打包图片即可分享。

### 触发关键词

以下关键词会触发论文解读功能：

> 解读论文、阅读论文、分析论文、论文解读、paper reading、读论文、看论文

## 项目结构

```
paper-reader/
├── .claude-plugin/
│   ├── plugin.json                   # Claude Code 插件元数据
│   └── marketplace.json              # Claude Code Marketplace 清单
├── skills/
│   └── paper-reader/
│       ├── SKILL.md                  # Skill 定义文件（Claude Code 入口）
│       ├── scripts/
│       │   ├── extract_figures.py    # 智能图表提取（pdfplumber + pdftoppm + PIL）
│       │   ├── upload_figures.py     # 上传图片到 Cloudflare R2
│       │   ├── render_pdf_pages.py   # PDF 页面渲染为 PNG
│       │   └── crop_figure.py        # 从页面图片中手动裁剪图表
│       └── references/
│           ├── document_template.md  # 写作指南与质量检查清单
│           └── audience_profiles.md  # 各读者画像的解读策略
├── README.md                         # 英文文档
└── README_zh.md                      # 本文件
```

### 脚本说明

#### `extract_figures.py` — 智能图表提取

自动检测并裁剪 PDF 中的所有图表（Figure / Table / Algorithm）。

```bash
python3 scripts/extract_figures.py <pdf_path> <output_dir> [--dpi 300]
```

工作原理：
1. 用 pdfplumber 扫描全文，通过正则匹配 `Figure N |` / `Table N |` / `Algorithm N` 定位 caption
2. 用启发式规则推断裁剪区域（Figure 在 caption 上方，Table 在 caption 下方）
3. **仅渲染包含图表的页面**（而非全部页面）
4. 带安全边距裁剪，保存到 `figures/` 目录
5. 生成 `figures/manifest.json`，记录每张图的元信息（页码、caption、坐标、置信度）

#### `upload_figures.py` — R2 图片上传

将提取的图片上传到 Cloudflare R2 图床。

```bash
python3 scripts/upload_figures.py <research_dir>
```

- 读取 `figures/manifest.json` 获取图片列表
- 上传到 R2 的 `papers/<name>/<filename>` 路径
- 生成 `figures/urls.json` 并在 manifest 中添加 `"url"` 字段
- R2 未配置时优雅退出（exit code 0），不影响后续流程
- 无 pip 依赖（仅使用标准库）

#### `render_pdf_pages.py` — PDF 页面渲染

将 PDF 的每一页渲染为高分辨率 PNG 图片。

```bash
python3 scripts/render_pdf_pages.py <pdf_path> <output_dir> [--dpi 300] [--pages 1-5]
```

| 参数 | 说明 |
|------|------|
| `pdf_path` | PDF 文件路径 |
| `output_dir` | 输出目录 |
| `--dpi` | 分辨率，默认 300 |
| `--pages` | 页码范围，如 `1-5` 或 `3` |

#### `crop_figure.py` — 手动裁剪图表

从渲染的页面图片中裁剪出指定区域。当智能提取遗漏图表时用作兜底方案。

```bash
python3 scripts/crop_figure.py <page_image> <output_path> <left> <top> <right> <bottom>
```

| 参数 | 说明 |
|------|------|
| `page_image` | 页面 PNG 图片路径 |
| `output_path` | 裁剪后的输出路径 |
| `left top right bottom` | 裁剪区域的像素坐标 |

**裁剪坐标参考（300 DPI）：**
- Letter 纸张：约 2550 × 3300 像素
- A4 纸张：约 2480 × 3508 像素
- 典型左边距：x ≈ 120
- 典型右边距：x ≈ 2430

## 自定义

### 修改写作指南

编辑 `skills/paper-reader/references/document_template.md` 可调整写作原则、图表嵌入格式或质量检查清单。该文件只包含指导原则而非固定模板 — Claude 会根据每篇论文的内容自行决定文档结构。

### 修改读者画像

编辑 `skills/paper-reader/references/audience_profiles.md` 可自定义各角色的解读策略，或添加新的读者类型。

## 常见问题

**Q: 提示 `pdftoppm not found` 怎么办？**

安装 Poppler：
```bash
# macOS
brew install poppler
# Ubuntu
sudo apt-get install poppler-utils
```

**Q: 提示 `pdfplumber not installed` 怎么办？**

```bash
pip install pdfplumber
```

**Q: 提示 `Pillow not installed` 怎么办？**

```bash
pip install Pillow
```

**Q: 图表裁剪不完整怎么办？**

智能提取采用"宁大勿小"的保守策略。如果仍有裁剪不完整的情况，工作流会自动回退到手动验证和重新裁剪。也可以直接用 `crop_figure.py` 调整坐标。

**Q: 如何更改输出目录？**

默认输出到 `./research/<paper-short-name>/`。你可以在请求时告诉 Claude 使用其他路径。

**Q: Context 太长被压缩了怎么办？**

分阶段工作流会将进度保存到 `progress.json`，阅读笔记保存到 `notes.md`，图表元数据保存到 `manifest.json`。Context 压缩后 Claude 会读取这些文件并从中断处继续，不会丢失已完成的工作。

**Q: 如何配置 R2 图床？**

参见 [R2 图床配置](#r2-图床配置可选) 部分。你需要一个 Cloudflare 账号、一个 R2 Bucket 和一个部署好的 Worker。设置 `R2_WORKER_URL` 和 `R2_API_KEY` 环境变量即可。

## License

MIT
