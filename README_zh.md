# Paper Reader — 论文深度解读工具

[![English](https://img.shields.io/badge/doc-English-blue)](./README.md)

一个 [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 技能（Skill），能够将学术论文 PDF 自动转化为面向特定读者的、带有完整图表的详细解读文档。

## 功能特点

- **读者画像定制** — 根据你的技术背景（程序员 / ML 从业者 / 研究者 / 非技术人员）自动调整解读深度和风格
- **自动图表提取** — 以 300 DPI 渲染 PDF 页面，高分辨率裁剪所有图表和表格
- **结构化解读文档** — 按模板生成完整的 Markdown 解读（背景知识、核心方案、实验分析、关键结论等）
- **多语言支持** — 自动检测用户语言，支持中文和英文输出

## 前置依赖

| 依赖 | 用途 | 安装方式 |
|------|------|----------|
| [Python 3](https://www.python.org/) | 运行图表提取脚本 | 系统通常自带 |
| [Pillow](https://python-pillow.org/) | 图片裁剪 | `pip install Pillow` |
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

Skill 使用两个外部工具来提取图表，需要一次性安装：

```bash
# Python 图片库（必需）
pip install Pillow

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

1. **选择读者画像** — Claude 会询问你的技术背景，选择最匹配的角色：
   - **程序员** — 用代码片段和编程类比解释论文
   - **ML 从业者** — 关注实现细节、消融实验和训练开销
   - **研究者** — 聚焦理论贡献和与相关工作的联系
   - **非技术背景** — 纯类比解释，无代码无公式

2. **补充专业知识** — 可多选你已掌握的技术（Transformer、分布式训练、PyTorch 等），Claude 会跳过你已知的概念，深入你关心的部分

3. **自动解读** — Claude 将：
   - 阅读 PDF 全文
   - 提取所有图表（高分辨率裁剪）
   - 按模板生成结构化解读文档
   - 在文档中嵌入所有图表

4. **输出结果** — 解读文档保存在：
   ```
   ./research/<paper-short-name>/
   ├── 论文解读_<PaperTitle>.md    # 解读文档
   └── figures/                     # 提取的图表
       ├── fig1_architecture.png
       ├── fig2_results.png
       └── ...
   ```

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
│       │   ├── render_pdf_pages.py   # PDF 页面渲染为 PNG
│       │   └── crop_figure.py        # 从页面图片中裁剪图表
│       └── references/
│           ├── document_template.md  # 写作指南与质量检查清单
│           └── audience_profiles.md  # 各读者画像的解读策略
├── README.md                         # 英文文档
└── README_zh.md                      # 本文件
```

### 脚本说明

#### `skills/paper-reader/scripts/render_pdf_pages.py`

将 PDF 的每一页渲染为高分辨率 PNG 图片。

```bash
python3 skills/paper-reader/scripts/render_pdf_pages.py <pdf_path> <output_dir> [--dpi 300] [--pages 1-5]
```

| 参数 | 说明 |
|------|------|
| `pdf_path` | PDF 文件路径 |
| `output_dir` | 输出目录 |
| `--dpi` | 分辨率，默认 300 |
| `--pages` | 页码范围，如 `1-5` 或 `3` |

#### `skills/paper-reader/scripts/crop_figure.py`

从渲染的页面图片中裁剪出指定区域（图表）。

```bash
python3 skills/paper-reader/scripts/crop_figure.py <page_image> <output_path> <left> <top> <right> <bottom>
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

**Q: 提示 `Pillow not installed` 怎么办？**

```bash
pip install Pillow
```

**Q: 图表裁剪不完整怎么办？**

自动流程会验证每张图片的完整性，发现截断会自动扩大范围重新裁剪。如果手动使用脚本，增大 `bottom` 坐标值即可确保图注（caption）完整包含在内。

**Q: 如何更改输出目录？**

默认输出到 `./research/<paper-short-name>/`。你可以在请求时告诉 Claude 使用其他路径。

## License

MIT
