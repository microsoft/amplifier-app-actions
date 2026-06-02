---
bundle:
  name: investigate
  version: 0.1.0
  description: >
    Issue investigation context + tools for GitHub Actions. Composes the
    built-in github-tools bundle and adds investigation context so the agent
    knows how to do deep analysis of issues, examine repository code, and post
    detailed findings as a comment. Use with `issue_comment` workflows triggered
    by a slash command (e.g. `/investigate`).

includes:
  # Compose the base tier — Foundation, Anthropic provider, GitHub API tools,
  # and Attractor pipeline support. Path is relative to the action root
  # (wrapper.py sets cwd=action_path).
  - bundle: ./bundles/github-tools.bundle.md

context:
  include:
    - investigate:context/investigate.md
---

# investigate Bundle

Issue investigation context + GitHub tools for `amplifier-app-actions` workflows.

Deep analysis of issues and pull requests. The agent examines repository code,
forms a root-cause hypothesis with `file:line` evidence, and posts its findings
as a comment. Use this bundle by setting `bundle: investigate` in your GitHub
Actions workflow step.

## Usage

```yaml
- uses: microsoft/amplifier-app-actions@v1
  with:
    bundle: investigate
    prompt: |
      A contributor requested investigation of this issue.
      Read the issue from the GitHub event context, examine the repository
      code, and post your findings as a comment.
  env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

## What it composes

- **github-tools** (base): Foundation agents, Anthropic provider,
  `github_post_comment`, `github_add_label`, `github_checkout_repo`
- **context/investigate.md**: Investigation methodology, evidence standards,
  and findings comment format
