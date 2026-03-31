# Writing Guidelines

Guidelines for producing a high-quality paper interpretation. These are principles, not a rigid template — adapt the structure to fit the paper.

## Document Header

Always start with basic metadata:

```markdown
# [Paper Title] — 解读

> **论文来源**: Authors / Institution
> **GitHub**: link (if available)
> **面向读者**: audience description based on selected profile
```

## Writing Principles

1. **Lead with the punchline** — Open with a one-sentence summary that conveys the core insight. Use a vivid analogy to make it stick.
2. **Motivation before mechanism** — Explain *why* this work exists before explaining *how* it works. What's broken? What's expensive? What's missing?
3. **Intuition before formalism** — Build the reader's mental model first, then layer on math/code/details as needed for the audience.
4. **Show, don't just tell** — Use the paper's own figures, tables, and diagrams. Every major figure should appear in the interpretation near the text that discusses it.
5. **Compare to what came before** — The reader needs an anchor. Show what the previous approach was and what changed.
6. **Match the audience** — A programmer wants code snippets; a researcher wants theoretical grounding; a non-technical reader wants analogies. Let the reader profile drive every paragraph.

## Structure

Let the paper's content determine the structure. A systems paper, a theory paper, and a survey paper should not look the same.

Ask yourself:
- What is the **one thing** the reader must understand after reading this?
- What background does **this specific reader** need to follow the argument?
- What are the **key figures** — and what story does each one tell?
- What did the **experiments prove** (or fail to prove)?
- What should the reader **take away** for their own work?

Organize your sections around the answers. Skip sections that add no value for the target audience. Add sections the paper warrants that no template would predict.

## Figure Embedding

Every major figure and table from the paper should be extracted and embedded. Prefer online URLs when available so the document can be shared directly.

Check each entry in `manifest.json` for a `"url"` field:

**With R2 URL** (document is shareable online):
```markdown
> **Figure N: Descriptive Title**
> Brief explanation of what the figure shows and the key takeaway.
>
> ![Figure N: Title](https://r2-imagebed.xxx.workers.dev/papers/xxx/figN.png)
```

**Without R2 URL** (local fallback):
```markdown
> **Figure N: Descriptive Title**
> Brief explanation of what the figure shows and the key takeaway.
>
> ![Figure N: Title](figures/figN_descriptive_name.png)
```

- Place figures near the text that discusses them
- If `manifest.json` entries have a `"url"` field, use that URL directly
- Otherwise fall back to relative paths: `figures/fig1_descriptive_name.png`
- Always include a brief description — don't just drop an image without context

## Source Attribution

Anchor every key claim to the paper. Use inline references to help readers (and yourself) trace claims back to the source:

- After numbers/results: "平均准确率 48.6%（Table 2）"
- After method descriptions: "proposer 通过文件系统访问所有历史候选（Section 3, p.3）"
- After quoting the paper's claims: "论文指出 harness 差异可产生 6× 的性能差距（Section 1, [47]）"

This also serves as a self-check: **if you cannot point to a specific source for a claim, you may be hallucinating.**

## Distinguishing Interpretation from Fact

When adding your own analysis that goes beyond what the paper explicitly states, use clear markers:

- *[解读者注]* for Chinese documents
- *[Interpreter's note]* for English documents

Examples of when to mark:
- "This resembles X from another paper" → *[解读者注]* 这与 Y 论文中的 Z 方法类似
- Speculation about why something works → *[解读者注]* 一个可能的解释是...
- Implications the paper didn't discuss → *[解读者注]* 对从业者而言，这意味着...

Examples of what does NOT need marking (these are factual descriptions):
- Restating what a figure shows
- Summarizing a table's numbers
- Paraphrasing the paper's own explanation

## Quality Checklist

Before finalizing, verify:

- [ ] All major figures and tables from the paper are extracted and embedded
- [ ] Every embedded image is complete (captions not truncated, tables not cut off)
- [ ] Language and depth match the selected audience profile
- [ ] All image paths are correct (R2 URLs when available, relative paths otherwise)
- [ ] The interpretation tells a coherent story, not a section-by-section summary
- [ ] **Factual grounding**: Every number and key claim has a source reference (Table N, Section N, p.N)
- [ ] **No fabricated specifics**: No invented file names, concrete examples, variable names, or causal explanations absent from the paper
- [ ] **Interpretation marked**: Your own commentary is distinguished from paper claims with *[解读者注]* or equivalent

## Document Updates from Follow-up Questions

When updating the document based on user follow-up questions:

- **Integrate, don't append** — Weave new content into the existing narrative. The document should read as a coherent whole, not show seams between "original" and "added" content.
- **Preserve structure** — If the new content fits an existing section, expand it there. Only create a new section if the topic is genuinely distinct.
- **Maintain voice** — Keep the same audience profile, language, and depth throughout. A follow-up answer inserted into the Programmer-profile document should still use code snippets and programming analogies.
- **Update figures if needed** — If a follow-up requires showing a new figure or table from the paper, extract and embed it following the standard figure embedding format.
