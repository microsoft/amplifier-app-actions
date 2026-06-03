---
bundle:
  name: app-actions
  version: 0.1.0
  description: >
    Expert agents for setting up and customizing GitHub repo automation with
    amplifier-app-actions. Load this bundle in your local development session
    when you want AI-assisted help configuring issue tracking, PR reviews,
    or attractor DOT pipelines for any GitHub repo.

    Activate with /github-actions to enter the mode. Three specialist experts
    are mode-gated — zero context cost until you type that command:
      - github-actions-expert: unified front-door consultant for the FULL lifecycle
        (zero setup → fully automated → custom prompts and pipelines)
      - app-actions-expert: workflow YAML templates, bundle selection, sane default prompts
      - dot-setup-expert: attractor DOT pipeline design and customization

includes:
  # Full foundation — registers foundation: namespace and provides
  # explorer, zen-architect, bug-hunter, and other foundation agents
  # as well as the delegate tool for agent orchestration.
  # Foundation transitively brings in the modes runtime (via superpowers),
  # so amplifier-bundle-modes does NOT need to be listed separately.
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main
  # Attractor bundle — registers attractor: namespace so dot-setup-expert
  # can @-mention attractor:docs/ for DOT syntax and authoring guides.
  - bundle: git+https://github.com/microsoft/amplifier-bundle-attractor@main

providers:
  - module: provider-anthropic
    source: git+https://github.com/microsoft/amplifier-module-provider-anthropic@main
    config:
      default_model: claude-sonnet-4-6
---

# app-actions Bundle

Expert agents for setting up and customizing GitHub repo automation with `amplifier-app-actions`.
Load this bundle in your **local development session** (not in GitHub Actions) when you want
AI assistance configuring issue tracking, PR reviews, or attractor pipelines for any GitHub repo.

## Quick Start

```
amplifier bundle add git+https://github.com/microsoft/amplifier-app-actions@main#subdirectory=bundles/app-actions.bundle.md --app
```

Then activate the GitHub Actions expert mode with:
```
/github-actions
```

The three expert agents are **mode-gated** — they consume zero context tokens until you type
`/github-actions`. Once active:
- "Help me set up issue triage and PR reviews for my repo"
- "Create a .dot file for an investigation pipeline"
- "Show me the four-workflow pattern for GitHub automation"
- "Help me customize the quality gate for my codebase"
- "My issue triage workflow runs but posts no comment — what's wrong?"

Use `/mode off` when done to return to normal (zero-cost) baseline.

## Expert Agents (mode-gated)

All three experts are contributed by the `/github-actions` mode. They are **not** loaded into
session context until the mode is active.

### `github-actions-expert` ← **START HERE**

The unified front-door consultant for the full amplifier-app-actions lifecycle. Covers:
- **Zero → first workflow**: ANTHROPIC_API_KEY setup, choosing the right bundle tier,
  writing your first issue-triage or PR-review workflow
- **Full automation**: the four-workflow pattern (issue triage, investigation, PR review,
  triage-continue with slash commands)
- **Custom pipelines**: attractor `.dot` design, manager-supervisor quality gates,
  thread isolation, remote sourcing via `git+https://`
- **Debugging**: trigger failures, permission errors, missing comments, bot-comment loops,
  `nodes_completed: 0`, local CLI testing

Coordinates with `app-actions-expert` (workflow YAML) and `dot-setup-expert` (DOT design)
for deep implementation work. **Route all questions here first.**

### `app-actions-expert`

Specialist for workflow YAML generation and action configuration. Provides:
- Ready-to-use workflow YAML for all four workflow types (issue-triage, investigate,
  pr-review, triage-continue)
- Sane default inline prompts for issue triage and PR review
- Bundle selection guide (when to use `github-tools` vs `attractor-pipeline` vs external)
- Security patterns: bot-comment guard, slash-command auth gate, minimal permissions
- Action input reference

### `dot-setup-expert`

Specialist for attractor DOT pipeline design and debugging. Provides:
- Complete DOT syntax reference for attractor pipelines
- Manager-supervisor pattern (the canonical issue triage pipeline design)
- Quality gate design with adversarial independence via thread isolation
- Commenter node pattern (`llm_provider="anthropic-commenter"`)
- Common mistake fixes (`nodes_completed: 0`, `DirectProviderBackend`, pipeline never exits)
- Customization guidance for non-Amplifier repos

## Architecture: Mode-Gated Context Sink

The bundle contributes **zero tokens** to the baseline session. The three expert agents are
mode-gated — contributed by the `/github-actions` mode and loaded only when active. All heavy
documentation lives in the agent `.md` files, which load only when an agent is spawned.

```
app-actions bundle (this file)
├── modes/github-actions.md         ← mode definition (advertised: false)
│   └── contributes on activation:
│       ├── agents/github-actions-expert.md   ← heavy agent (context sink)
│       ├── agents/app-actions-expert.md      ← heavy agent (context sink)
│       └── agents/dot-setup-expert.md        ← heavy agent (context sink)
│
└── baseline session                ← ZERO GHA tokens until /github-actions
```

Token cost model:
- **Baseline (mode off)**: 0 tokens from this bundle
- **Mode active**: mode body (~40 lines) injected per turn; agents loaded on spawn only
- **Agent spawned**: full agent knowledge in isolated sub-session

## Relationship to the Example Repo

This bundle produces the setup that `amplifier-actions-example` demonstrates.
The example repo (`kenotron-ms/amplifier-actions-example`) shows the finished
`.github/workflows/` and `.github/amplifier/triage-review.dot` — activate
`/github-actions` and `github-actions-expert` will coordinate `app-actions-expert`
and `dot-setup-expert` to get there for your own repo.
