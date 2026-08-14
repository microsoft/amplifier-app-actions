---
name: pr-review
description: >
  Local PR review in your session — exhaustive (5 independent review lenses with quality
  synthesis) or prompt-shot (single-pass five-check framework). No GitHub comment posted.
  Use when the user wants a local code review of a branch diff, staged changes, or PR
  before pushing/merging.
---

PR REVIEW: Local code review against a branch diff. Findings go to stdout — no GitHub post.

## Two review approaches

**Exhaustive** — The agent works through 5 focused review lenses sequentially (correctness ·
architecture · patterns · tests · pedantic), each with explicit focus on only that dimension.
Findings are merged, deduplicated, and prioritized by severity before the final output.
Mirrors the structure of `pipelines/pr-review-exhaustive.dot` without needing the GHA attractor runtime.

**Prompt-shot** — Single-pass five-check review (Necessity · Layer fit · Pattern · Correctness ·
Calibration). Fast. Best for quick sanity checks or small diffs.

## How to start

Tell me what to review — I'll orient and delegate to `pr-review-agent`:

- *"Exhaustive review of my branch vs main"*
- *"Prompt-shot review — just the staged changes"*
- *"Quick review of feature/auth-refactor before I push"*
- *"Review the diff at HEAD vs origin/main, exhaustive"*

I do not attempt review logic myself. All review work runs inside a clean-room
`pr-review-agent` delegate with fresh context:

```
delegate(
    agent="app-actions:agents/pr-review-agent",
    instruction="<review approach (exhaustive/prompt-shot) and diff scope>",
    context_depth="none"
)
```
