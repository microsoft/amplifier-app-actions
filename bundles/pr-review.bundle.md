---
bundle:
  name: pr-review
  version: 0.1.0
  description: >
    PR review context + tools for GitHub Actions. Composes the built-in
    github-tools bundle and adds PR review context (five-check framework and
    workflow guidance) so the agent knows how to evaluate diffs and post
    structured review comments. Use with `pull_request: [opened]` workflows.

includes:
  # Compose the base tier — Foundation, Anthropic provider, GitHub API tools,
  # and Attractor pipeline support. Path is relative to the action root
  # (wrapper.py sets cwd=action_path).
  - bundle: ./bundles/github-tools.bundle.md

context:
  include:
    - pr-review:context/pr-review.md
    - pr-review:context/pr-review-workflow.md
---

# pr-review Bundle

PR review context + GitHub tools for `amplifier-app-actions` workflows.

Reviews pull request diffs and posts a structured review comment. Applies the
five-check framework: Necessity, Layer fit, Pattern, Correctness, Calibration.
Use this bundle by setting `bundle: pr-review` in your GitHub Actions workflow step.

## Usage

```yaml
- uses: microsoft/amplifier-app-actions@v1
  with:
    bundle: pr-review
    prompt: |
      A pull request was opened. Review it.
  env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

## What it composes

- **github-tools** (base): Foundation agents, Anthropic provider,
  `github_post_comment`, `github_add_label`, `github_checkout_repo`
- **context/pr-review.md**: Five-check review framework and comment style guide
- **context/pr-review-workflow.md**: PR review workflow process and sequencing
