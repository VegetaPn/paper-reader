# Audience Profiles for Paper Interpretation

## Profile Selection Guide

The reader profile is built in a single round of questions:
1. **Base profile**: Select from the 4 profiles below
2. **Paper-specific knowledge**: Dynamically generated based on the paper's key concepts — user selects which ones they already know

Merge both: use the base profile as the default strategy, then overlay the paper-specific knowledge selections to skip known concepts and explain unknown ones thoroughly.

## Profiles

### 1. Programmer (Default)
- **Background**: Has coding experience, understands basic data structures and algorithms
- **Knows**: Python, basic linear algebra, what a neural network is
- **Doesn't know**: Detailed math behind attention, training dynamics, optimization theory
- **Strategy**:
  - Use code snippets (Python/PyTorch) as primary explanation medium
  - Explain math formulas by showing equivalent code
  - Use programming analogies (lists, caches, garbage collection, etc.)
  - Include pseudocode for core algorithms
  - Explain "why" before "what"

### 2. ML Practitioner
- **Background**: Has trained models, familiar with PyTorch/TensorFlow, understands Transformer basics
- **Knows**: Attention mechanism, loss functions, gradient descent, common architectures
- **Doesn't know**: Cutting-edge research details, theoretical proofs, infrastructure at scale
- **Strategy**:
  - Skip basic Transformer explanations
  - Focus on: what's new, why it works, how to implement
  - Include detailed architecture comparisons with existing methods
  - Emphasize practical implications (training cost, inference overhead, hyperparameters)
  - Discuss ablation results in depth

### 3. Researcher
- **Background**: Reads papers regularly, deep understanding of ML theory
- **Knows**: Advanced optimization, information theory, state-of-the-art methods
- **Doesn't know**: This specific paper's contributions and novelty
- **Strategy**:
  - Concise, dense writing style
  - Focus on theoretical contributions and novelty
  - Detailed comparison with related work
  - Discuss limitations and future directions
  - Include full mathematical formulations
  - Analyze experimental methodology critically

### 4. Non-technical / Manager
- **Background**: Understands technology at a high level, no coding or math background
- **Knows**: What AI/LLM is, business implications
- **Doesn't know**: Technical details of any kind
- **Strategy**:
  - Pure analogy-based explanations
  - Focus on: what problem it solves, how much it improves, business impact
  - No code, no math
  - Use visual diagrams and comparisons
  - Quantify improvements in plain language ("25% more efficient")

## Adapting with Paper-Specific Knowledge

The knowledge options are dynamically generated from the paper's content (not a fixed list). Use the user's selections to fine-tune the interpretation:

### Skip what they selected (already know)
- If the paper is about FlashAttention and user selected "Attention mechanism" → Don't explain what attention is; jump straight to the IO-aware optimization
- If user selected a concept like "KV Cache memory optimization" → Reference it as known context, don't re-explain

### Explain what they did NOT select (knowledge gaps)
- These are the concepts that need the most careful explanation
- Build up from foundations the user does have (base profile) to bridge the gap
- Use analogies from their domain to introduce unfamiliar concepts

### Deepen adjacent topics
- If user knows a related concept, go deeper on how this paper extends or differs from it
- If user mentioned specific tools/frameworks in "Other", connect the paper's ideas to those tools

### Match their tech stack
- Infer from base profile + "Other" text what frameworks/languages the user prefers
- Programmer + mentions "PyTorch" → Use PyTorch code examples
- ML Practitioner + mentions "CUDA" → Include kernel-level implications when relevant

### Tailor analogies to their domain
- Database expert → "like an index scan vs full table scan"
- Systems programmer → "like replacing a fixed-size ring buffer with a content-addressable cache"
- Frontend developer → "like React's selective re-rendering vs full DOM refresh"

### Example merged profile

> **Paper**: FlashAttention-2
> **Base**: Programmer
> **Paper-specific knowledge selected**: "Attention mechanism", "GPU memory hierarchy"
> **Not selected**: "IO complexity analysis", "CUDA kernel programming"
> **Other**: "了解 PyTorch，用过 LoRA"
>
> **Merged strategy**: Use PyTorch code as primary medium. Skip attention basics and GPU memory hierarchy explanation. Carefully explain IO complexity analysis with programming analogies (think of it as optimizing disk I/O vs in-memory operations). Explain CUDA kernel concepts at a high level using Python function analogies. When discussing parameter overhead, compare with LoRA.
