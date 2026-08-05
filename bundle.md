---
bundle:
  name: app-actions
  version: 0.2.0
  description: >
    Root namespace anchor for amplifier-app-actions, AND the standalone
    entry point for local development sessions. Establishes the repo root
    as the @app-actions: namespace so that modes/, agents/, and context/
    resolve correctly whether this file is loaded directly (no
    #subdirectory needed — this is the root) or a nested file under this
    repo is loaded via #subdirectory=... (e.g. behaviors/app-actions.yaml,
    installed as an --app target — see README for the recommended install
    command). Composes foundation plus this repo's own behavior so that
    running this file directly is a complete, ready-to-use local session.

includes:
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main
  - bundle: app-actions:behaviors/app-actions
---

# amplifier-app-actions

Expert agents for setting up and customizing GitHub repo automation with `amplifier-app-actions`.
Use this **local development session** (not in GitHub Actions) when you want AI-assisted help
configuring issue tracking, PR reviews, or attractor DOT pipelines for any GitHub repo.

## Quick Start

Recommended — install just the behavior as an `--app` add-on, composed onto every session:

```
amplifier bundle add git+https://github.com/microsoft/amplifier-app-actions@main#subdirectory=behaviors/app-actions.yaml --app
```

Alternative — run this file directly as a standalone bundle for a one-off session (no `--app`,
no persistent install):

```
amplifier run --bundle git+https://github.com/microsoft/amplifier-app-actions@main "Help me set up issue triage"
```

Optional — if you also want `dot-setup-expert` to have the full attractor DOT documentation
(rather than a degraded reference that silently skips), add the attractor overlay too:

```
amplifier bundle add git+https://github.com/microsoft/amplifier-app-actions@main#subdirectory=behaviors/app-actions-attractor.yaml --app
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

Requires the opt-in `app-actions-attractor` behavior for full DOT documentation — see Quick
Start above. Without it, the expert runs a preflight check and tells you the exact install
command rather than answering from a silently-degraded context.

## Architecture: Behavior + Standalone Entry Point

`behaviors/app-actions.yaml` is the reusable capability — the correct `--app` install target.
It carries zero includes, zero session config, zero providers: adding it via `--app` only pins
this repo into the registry so the modes hook can discover `modes/` at the repo root. The two
modes (`/github-actions`, `/pr-review`) contribute their expert agents dynamically via
`contributes.agents`, loaded only while active.

This file (`bundle.md`) is the root namespace anchor AND, separately, a ready-to-run standalone
bundle for anyone who wants a complete one-off session (foundation + the behavior) without an
`--app` install.

```
app-actions repo
├── bundle.md                      ← root namespace anchor + standalone entry point
│   └── includes: foundation + app-actions:behaviors/app-actions
├── behaviors/app-actions.yaml      ← the --app install target (near-empty; modes discoverable)
├── behaviors/app-actions-attractor.yaml  ← opt-in: attractor DOT docs for dot-setup-expert
├── modes/github-actions.md        ← mode definition (advertised: false)
│   └── contributes on activation:
│       ├── agents/github-actions-expert.md   ← heavy agent (context sink)
│       ├── agents/app-actions-expert.md      ← heavy agent (context sink)
│       └── agents/dot-setup-expert.md        ← heavy agent (context sink)
└── modes/pr-review.md             ← local review mode (advertised: false)
    └── contributes on activation:
        └── agents/pr-review-agent.md         ← heavy agent (context sink)
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
