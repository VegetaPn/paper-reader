# Audience Profiles for Paper Interpretation

## Profile Selection Guide

The reader profile is built in two rounds:
1. **Base profile**: Select from the 4 profiles below
2. **Specific knowledge**: User supplements with their concrete skills/knowledge via multi-select + free text

After collecting both, merge them: use the base profile as the default strategy, then overlay the user's specific knowledge to skip/deepen/adjust.

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

## Adapting with User-Supplied Knowledge

After the base profile is selected, the user may supplement with specific skills (multi-select or free text). Use these to fine-tune the interpretation:

### Skip what they already know
- User selected "Transformer / Attention" → Don't explain what self-attention or multi-head attention is; jump straight to what's different in this paper.
- User mentioned "熟悉 FlashAttention" → Reference FlashAttention as a known baseline when comparing IO efficiency.

### Deepen adjacent topics
- User selected "分布式训练" → Elaborate on pipeline parallelism, cross-stage communication, activation checkpointing implications.
- User mentioned "做过 RLHF" → Discuss how the method might interact with reward model training or PPO gradients if relevant.

### Match their tech stack
- User selected "PyTorch / JAX" → Use their preferred framework in code examples.
- User mentioned "C++ / CUDA" → Include low-level implementation notes, kernel-level implications when relevant.

### Tailor analogies to their domain
- Database expert → "like an index scan vs full table scan"
- Systems programmer → "like replacing a fixed-size ring buffer with a content-addressable cache"
- Frontend developer → "like React's selective re-rendering vs full DOM refresh"

### Example merged profile

> Base: Programmer
> Supplements: "Transformer / Attention", "PyTorch", free text: "了解 LoRA 和量化"
>
> **Merged strategy**: Use PyTorch code as primary medium. Skip basic attention explanation. When discussing parameter overhead, compare with LoRA's parameter count. When discussing inference, mention quantization compatibility if relevant.
