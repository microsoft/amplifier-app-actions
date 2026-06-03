---
bundle:
  name: app-actions
  version: 0.1.0
  description: >
    Expert agents for setting up and customizing GitHub repo automation with
    amplifier-app-actions. Load this bundle in your local development session
    when you want AI-assisted help configuring issue tracking, PR reviews,
    or attractor DOT pipelines for any GitHub repo.

    Provides three expert agents and the /github-actions slash command:
      - github-actions-expert: unified front-door consultant for the FULL lifecycle
        (zero setup → fully automated → custom prompts and pipelines)
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

tools:
  # Register this bundle's own skills/ dir so the /github-actions command is discovered.
  # Mirrors foundation's tool-skills config and adds @app-actions:skills, so the result is
  # correct whether bundle composition merges or replaces the skills source list.
  - module: tool-skills
    source: git+https://github.com/microsoft/amplifier-bundle-skills@main#subdirectory=modules/tool-skills
    config:
      skills:
        - "git+https://github.com/microsoft/amplifier-bundle-skills@main#subdirectory=skills"
        - "@app-actions:skills"
      visibility:
        enabled: true
        inject_role: "user"
        max_skills_visible: 50
        ephemeral: true
        priority: 20

agents:
  include:
    # Note: agent loading searches /agents/ dir automatically — "agents/" not needed in path
    - app-actions:github-actions-expert
    - app-actions:app-actions-expert
    - app-actions:dot-setup-expert

context:
  include:
    # Thin awareness pointers — just enough to know the experts exist and to force delegation.
    # Heavy documentation lives in the agent files (context sink pattern).
    # github-actions-awareness is listed first: it is the front door and covers the other two.
    - app-actions:context/github-actions-awareness.md
    - app-actions:context/app-actions-awareness.md
    - app-actions:context/dot-setup-awareness.md
---

# app-actions Bundle

Expert agents for setting up and customizing GitHub repo automation with `amplifier-app-actions`.
Load this bundle in your **local development session** (not in GitHub Actions) when you want
AI assistance configuring issue tracking, PR reviews, or attractor pipelines for any GitHub repo.

## Quick Start

```
amplifier bundle add git+https://github.com/microsoft/amplifier-app-actions@main#subdirectory=bundles/app-actions.bundle.md --app
```

Then invoke the expert directly with:
```
/github-actions
```
Or ask naturally:
- "Help me set up issue triage and PR reviews for my repo"
- "Create a .dot file for an investigation pipeline"
- "Show me the four-workflow pattern for GitHub automation"
- "Help me customize the quality gate for my codebase"
- "My issue triage workflow runs but posts no comment — what's wrong?"

## Expert Agents

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

## Slash Command

The `/github-actions` command spawns the `github-actions-expert` in an isolated sub-session.
Use it from any session where this bundle is loaded:

```
/github-actions help me set up automated PR reviews
/github-actions my workflow isn't posting comments — what's wrong?
/github-actions design a manager-supervisor pipeline for my repo
```

## Architecture: Context Sink Pattern

The bundle's context files are thin pointers (~35 lines each). All heavy documentation lives
in the agent `.md` files, which are only loaded when an agent is actually spawned — keeping
your local session lean while the experts carry their full knowledge in isolated sub-sessions.

```
app-actions bundle (this file)
├── context/github-actions-awareness.md   ← thin pointer (~35 lines)  ← front door
├── context/app-actions-awareness.md      ← thin pointer (~40 lines)
├── context/dot-setup-awareness.md        ← thin pointer (~44 lines)
├── agents/github-actions-expert.md       ← heavy agent (loaded on spawn only) ← coordinator
├── agents/app-actions-expert.md          ← heavy agent (loaded on spawn only)
├── agents/dot-setup-expert.md            ← heavy agent (loaded on spawn only)
└── skills/github-actions/SKILL.md        ← /github-actions slash command
```

## Relationship to the Example Repo

This bundle produces the setup that `amplifier-actions-example` demonstrates.
The example repo (`kenotron-ms/amplifier-actions-example`) shows the finished
`.github/workflows/` and `.github/amplifier/triage-review.dot` — use `github-actions-expert`
as your front door and it will coordinate `app-actions-expert` and `dot-setup-expert`
to get there for your own repo.
