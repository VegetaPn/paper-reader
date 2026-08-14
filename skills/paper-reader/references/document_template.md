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
7. **Avoid AI flavor** — Write like someone who actually understands the paper jotting it down, not like a generated summary. Suppress the default patterns (`→`/`——` as connectors, 「关键/本质/核心」 clichés, 「招1招2」 subheadings, list-count previews, bold pile-ups). See [writing_style.md](writing_style.md) and apply it throughout.
8. **Write formulas as LaTeX** — Use `$...$` for inline mathematical expressions and `$$...$$` for display equations. Never substitute inline code, fenced code blocks, ASCII equations, or Unicode pseudo-math.

## Formula Formatting (MANDATORY)

Every mathematical expression in the generated interpretation must use valid LaTeX, regardless of where it appears in the Markdown document.

- Inline notation: `策略为 $\pi_\theta(a\mid s)$。`
- Display equation:

  ```markdown
  $$
  J(\theta)=\mathbb{E}_{\tau\sim\pi_\theta}\left[\sum_{t=0}^{T}\gamma^t r_t\right]
  $$
  ```

- The fenced block above demonstrates the Markdown source only. In the interpretation itself, write the equation directly between `$$` delimiters, without a code fence.
- Apply the same formatting inside prose, lists, tables, blockquotes, figure captions, and follow-up additions.
- Backticks remain appropriate for literal code such as `value_head`, but mathematical objects such as $V_\theta(s)$ must use LaTeX.
- If rendering support is uncertain, retain the LaTeX source and warn about viewer compatibility; do not downgrade the formula.

## Content Balance (CRITICAL)

The interpretation must focus on **background, problem definition, and solution mechanism**. Results/evaluation are supporting evidence, not the main content.

**Target proportions:**
- Background + Problem definition: 25–30% — What landscape does this paper enter? What specific gaps or limitations existed? Why is the problem hard?
- Solution / Method in detail: 50–60% — How does it work? What are the design choices? What's novel compared to prior art? Write enough detail that the reader could explain the method to a colleague.
- Results + Discussion: 15–20% — Compact summary of key findings with one table or paragraph. Highlight what the results reveal about the method's strengths/weaknesses. Do NOT enumerate every benchmark or embed every results table.

**Anti-pattern: "results dumping"** — Listing benchmark after benchmark with separate figure embeds and per-table commentary. The reader can look at tables themselves; the interpretation's job is to help them understand the *method*, not reformat the leaderboard.

**When to include a results table:** Only when it directly illuminates a design decision (e.g., an ablation showing why component X matters) or reveals a surprising insight about the method. Omit tables that just show "we beat baselines" without analytical value.

**Case studies:** Include only when they help the reader understand how the method works in practice. Skip if they're just "look, we got the right answer."

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

When adding your own analysis that goes beyond what the paper explicitly states, distinguish it through **prose framing, not bracketed tags**. Do NOT use `[解读者注]` / `[Interpreter's note]` style labels — they read like stickers and add AI flavor.

Start the paragraph with a phrase that makes the source-vs-interpretation boundary audible:
- "This resembles X from another paper" → 另起一段：「这与 Y 论文的 Z 方法类似，是我用来帮助理解的类比，不是论文的说法」
- Speculation about why something works → 「论文没解释为什么，一个可能的解释是…（这是我的推测）」
- Implications the paper didn't discuss → 「论文没展开，但对从业者而言这意味着…」

Examples of what does NOT need framing (these are factual descriptions): restating what a figure shows, summarizing a table's numbers, paraphrasing the paper's own explanation.

Full anti-AI-flavor discipline (punctuation, template structures, clichés, bold overuse, scope) is in [writing_style.md](writing_style.md). Apply it while writing.

## Quality Checklist

Before finalizing, verify:

- [ ] All major figures and tables from the paper are extracted and embedded
- [ ] Every embedded image is complete (captions not truncated, tables not cut off)
- [ ] Language and depth match the selected audience profile
- [ ] All image paths are correct (R2 URLs when available, relative paths otherwise)
- [ ] The interpretation tells a coherent story, not a section-by-section summary
- [ ] **Factual grounding**: Every number and key claim has a source reference (Table N, Section N, p.N)
- [ ] **No fabricated specifics**: No invented file names, concrete examples, variable names, or causal explanations absent from the paper
- [ ] **LaTeX formulas**: Every mathematical expression uses `$...$` or `$$...$$`; none is written as inline code, a fenced code block, ASCII, or Unicode pseudo-math
- [ ] **Interpretation framed in prose**: Your own commentary is distinguished from paper claims through sentence framing (「我的理解是」「论文没展开」), NOT through `[解读者注]` / `[Interpreter's note]` tags
- [ ] **No AI flavor**: Ran the self-check in [writing_style.md](writing_style.md) — no `→`/`——` overuse, no 「关键/本质/核心」 clichés, no 「招1招2」, no list-count previews, ≤2 bold per paragraph

## Document Updates from Follow-up Questions

When updating the document based on user follow-up questions:

- **Integrate, don't append** — Weave new content into the existing narrative. The document should read as a coherent whole, not show seams between "original" and "added" content.
- **Preserve structure** — If the new content fits an existing section, expand it there. Only create a new section if the topic is genuinely distinct.
- **Maintain voice** — Keep the same audience profile, language, and depth throughout. A follow-up answer inserted into the Programmer-profile document should still use code snippets and programming analogies.
- **Preserve LaTeX formulas** — New or revised mathematical expressions must use `$...$` or `$$...$$`, never inline code or ASCII formatting.
- **Update figures if needed** — If a follow-up requires showing a new figure or table from the paper, extract and embed it following the standard figure embedding format.
