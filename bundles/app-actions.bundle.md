---
bundle:
  name: app-actions
  version: 0.1.0
  description: >
    Expert agents for setting up and customizing GitHub repo automation with
    amplifier-app-actions. Load this bundle in your local development session
    when you want AI-assisted help configuring issue tracking, PR reviews,
    or attractor DOT pipelines for your repo.

    Provides two expert agents:
      - app-actions-expert: workflow YAML templates, bundle selection, sane default prompts
      - dot-setup-expert: attractor DOT pipeline design and customization

includes:
  # Full foundation — registers foundation: namespace and provides
  # explorer, zen-architect, bug-hunter, and other foundation agents
  # as well as the delegate tool for agent orchestration.
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main
  # Attractor bundle — registers attractor: namespace so dot-setup-expert
  # can @-mention attractor:docs/ for DOT syntax and authoring guides.
  - bundle: git+https://github.com/microsoft/amplifier-bundle-attractor@main

providers:
  - module: provider-anthropic
    source: git+https://github.com/microsoft/amplifier-module-provider-anthropic@main
    config:
      default_model: claude-sonnet-4-6

agents:
  include:
    # Note: agent loading searches /agents/ dir automatically — "agents/" not needed in path
    - app-actions:app-actions-expert
    - app-actions:dot-setup-expert

context:
  include:
    # Thin awareness pointers — just enough to know the experts exist and to force delegation.
    # Heavy documentation lives in the agent files (context sink pattern).
    - app-actions:context/app-actions-awareness.md
    - app-actions:context/dot-setup-awareness.md
---

# app-actions Bundle

Expert agents for setting up and customizing GitHub repo automation with `amplifier-app-actions`.
Load this bundle in your **local development session** (not in GitHub Actions) when you want
AI assistance configuring issue tracking, PR reviews, or attractor pipelines for any GitHub repo.

## When to Use This Bundle

```
amplifier run --bundle git+https://github.com/microsoft/amplifier-app-actions@main#subdirectory=bundles/app-actions.bundle.md
```

Then ask the agent:
- "Help me set up issue triage and PR reviews for my repo"
- "Create a .dot file for an investigation pipeline"
- "Show me the four-workflow pattern for GitHub automation"
- "Help me customize the quality gate for my codebase"

## Expert Agents

### `app-actions-expert`

Helps you set up GitHub issue tracking and PR reviews. Provides:
- Ready-to-use workflow YAML for all four workflow types (issue-triage, investigate, pr-review, triage-continue)
- Sane default inline prompts for issue triage and PR review
- Bundle selection guide (when to use `github-tools` vs `attractor-pipeline` vs external)
- Security patterns: bot-comment guard, slash-command auth gate, minimal permissions
- Action input reference

### `dot-setup-expert`

Helps you design and customize attractor DOT pipelines. Provides:
- Complete DOT syntax reference for attractor pipelines
- Manager-supervisor pattern (the canonical issue triage pipeline design)
- Quality gate design with adversarial independence via thread isolation
- Commenter node pattern (`llm_provider="anthropic-commenter"`)
- Common mistake fixes (`nodes_completed: 0`, `DirectProviderBackend`, pipeline never exits)
- Customization guidance for non-Amplifier repos

## Architecture: Context Sink Pattern

The bundle's context files are thin pointers (~30 lines each). All heavy documentation lives
in the agent `.md` files, which are only loaded when an agent is actually spawned — keeping
your local session lean while the experts carry their full knowledge in isolated sub-sessions.

```
app-actions bundle (this file)
├── context/app-actions-awareness.md      ← thin pointer (~30 lines)
├── context/dot-setup-awareness.md        ← thin pointer (~30 lines)
├── agents/app-actions-expert.md          ← heavy agent (loaded on spawn only)
└── agents/dot-setup-expert.md            ← heavy agent (loaded on spawn only)
```

## Relationship to the Example Repo

This bundle produces the setup that `amplifier-actions-example` demonstrates.
The example repo (`kenotron-ms/amplifier-actions-example`) shows the finished
`.github/workflows/` and `.github/amplifier/triage-review.dot` — use `app-actions-expert`
and `dot-setup-expert` to get there for your own repo.
