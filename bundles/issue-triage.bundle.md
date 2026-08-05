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
  # and Attractor pipeline support.
  - bundle: git+https://github.com/microsoft/amplifier-app-actions@main#subdirectory=bundles/github-tools.bundle.md

context:
  include:
    - app-actions:context/issue-triage.md
---

# issue-triage Bundle

Issue triage context + GitHub tools for `amplifier-app-actions` workflows.

Classifies new issues, applies the appropriate label, and posts a friendly
acknowledgment comment. Reference this bundle via its full `git+https://` URI
(setting `bundle:` to the bare name `issue-triage` does not work).

## Usage

```yaml
- uses: microsoft/amplifier-app-actions@main
  with:
    bundle: git+https://github.com/microsoft/amplifier-app-actions@main#subdirectory=bundles/issue-triage.bundle.md
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
