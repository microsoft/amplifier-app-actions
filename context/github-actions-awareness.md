# GitHub Actions Automation Expert

You have access to `app-actions:github-actions-expert` — the unified authoritative expert for
GitHub Actions automation with `amplifier-app-actions`, covering the FULL lifecycle: zero-install
setup → fully automated repo → custom prompt and pipeline design.

## When to Delegate

**ALWAYS delegate to `app-actions:github-actions-expert` when the user:**

- Wants to add ANY GitHub Actions automation to their repo (issue triage, PR review, investigation)
- Asks how to set up or configure `amplifier-app-actions`
- Needs workflow YAML, prompt templates, or the four-workflow pattern
- Asks which bundle to use or how instruction types differ
- Wants to debug a failing or misbehaving GitHub Actions workflow
- Needs help with security patterns (bot-comment guard, auth gate, permissions)
- Wants to customize prompts for their domain or use remote sourcing (`git+https://`)
- Asks about attractor pipelines, `.dot` files, or the manager-supervisor pattern
- Asks about local CLI testing with `amplifier-triage`
- Types `/github-actions`

## Do NOT DIY

Do not attempt to explain `amplifier-app-actions` inputs, write workflow YAML, or describe
bundle tiers from memory. The expert has the complete reference, live docs, and ready-to-use
templates — including coordination with `app-actions-expert` (workflow YAML) and
`dot-setup-expert` (DOT pipeline design).

```python
delegate(
    agent="app-actions:github-actions-expert",
    instruction="<what the user needs>",
    context_depth="recent",
    context_scope="conversation"
)
```

## What the Expert Provides

- Full lifecycle guide: zero → first workflow → four-workflow pattern → custom pipelines
- Workflow debugging (trigger failures, missing comments, bot loops, permission errors)
- Bundle tier selection and instruction-type (`prompt` vs `attractor_source`) decision guide
- Security essentials (bot-comment guard, auth gate, safe trigger rules)
- Prompt customization strategy for any domain
- Coordination with `app-actions-expert` for complete workflow YAML generation
- Coordination with `dot-setup-expert` for attractor DOT pipeline design
