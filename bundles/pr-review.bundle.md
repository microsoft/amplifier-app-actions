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
  # and Attractor pipeline support.
  - bundle: git+https://github.com/microsoft/amplifier-app-actions@main#subdirectory=bundles/github-tools.bundle.md

context:
  include:
    - app-actions:context/pr-review.md
    - app-actions:context/pr-review-workflow.md
---

# pr-review Bundle

PR review context + GitHub tools for `amplifier-app-actions` workflows.

Reviews pull request diffs and posts a structured review comment. Applies the
five-check framework: Necessity, Layer fit, Pattern, Correctness, Calibration.
Reference this bundle via its full `git+https://` URI
(setting `bundle:` to the bare name `pr-review` does not work).

## Usage

```yaml
- uses: actions/checkout@v4
  with:
    fetch-depth: 0
- uses: microsoft/amplifier-app-actions@main
  with:
    bundle: git+https://github.com/microsoft/amplifier-app-actions@main#subdirectory=bundles/pr-review.bundle.md
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
