---
bundle:
  name: issue-triage
  version: 0.1.0
  description: >
    Issue triage context + tools for GitHub Actions. Composes the built-in
    github-tools bundle and adds issue-triage context so the agent knows how
    to classify issues, apply labels, and post acknowledgment comments.
    Use with `issues: [opened]` workflows.

includes:
  # Compose the base tier — Foundation, Anthropic provider, GitHub API tools,
  # and Attractor pipeline support. Path is relative to the action root
  # (wrapper.py sets cwd=action_path).
  - bundle: ./bundles/github-tools.bundle.md

context:
  include:
    - issue-triage:context/issue-triage.md
---

# issue-triage Bundle

Issue triage context + GitHub tools for `amplifier-app-actions` workflows.

Classifies new issues, applies the appropriate label, and posts a friendly
acknowledgment comment. Use this bundle by setting `bundle: issue-triage` in
your GitHub Actions workflow step.

## Usage

```yaml
- uses: microsoft/amplifier-app-actions@v1
  with:
    bundle: issue-triage
    prompt: |
      A new issue was opened. Triage it.
  env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

## What it composes

- **github-tools** (base): Foundation agents, Anthropic provider,
  `github_post_comment`, `github_add_label`, `github_checkout_repo`
- **context/issue-triage.md**: Issue classification guidance, label taxonomy,
  and acknowledgment comment style
