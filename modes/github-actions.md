---
mode:
  name: github-actions
  description: Set up, debug, and customize GitHub Actions automation (amplifier-app-actions) in your repo
  shortcut: github-actions
  advertised: false
  default_action: block
  tools:
    safe: [read_file, glob, grep, web_search, web_fetch, load_skill, LSP, todo, delegate]
    warn: [write_file, edit_file, bash]
  contributes:
    agents:
      github-actions-expert:
        source: "@app-actions:agents/github-actions-expert"
      app-actions-expert:
        source: "@app-actions:agents/app-actions-expert"
      dot-setup-expert:
        source: "@app-actions:agents/dot-setup-expert"
---

GITHUB ACTIONS MODE: set up, debug, and customize amplifier-app-actions automation in this repo.

## Specialist Agents (available via `delegate`)

- **`github-actions-expert`** ← FRONT DOOR — route everything here first. Unified consultant for
  the full lifecycle: zero-install setup → four-workflow automation → custom prompt design →
  debugging. Coordinates the other two specialists as needed.

- **`app-actions-expert`** — workflow YAML specialist. Handles ready-to-use workflow YAML,
  bundle selection, security patterns, and action input reference. Reached via
  `github-actions-expert` for deep workflow work.

- **`dot-setup-expert`** — attractor `.dot` pipeline specialist. Handles DOT syntax,
  manager-supervisor patterns, quality gates, thread isolation, and pipeline debugging.
  Reached via `github-actions-expert` for deep DOT work.

## Workflow

DO: Read repo files, search docs, delegate to `github-actions-expert` for any user request.

DO NOT: Attempt GitHub Actions YAML or attractor DOT pipeline work yourself — delegate first.

Lifecycle: zero-install setup → add the four workflows → customize prompts and pipelines → debug.

Use /mode off when done.
