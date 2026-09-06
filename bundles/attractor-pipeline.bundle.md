---
bundle:
  name: attractor-pipeline
  version: 0.1.0
  description: >
    Generic DOT pipeline runner for amplifier-app-actions. Mounts loop-pipeline
    as the outer session orchestrator so the module is installed at bundle-prepare
    time. The DOT graph is injected at runtime via a wrapper-generated overlay
    bundle (dot_source in orchestrator config).

    Child agent sessions (pipeline-agent-anthropic) get filesystem, bash, search,
    AND GitHub API tools so pipeline nodes can check out repos, post comments, and
    add labels without extra configuration.

includes:
  - bundle: git+https://github.com/microsoft/amplifier-bundle-attractor@main

providers:
  - module: provider-anthropic
    source: git+https://github.com/microsoft/amplifier-module-provider-anthropic@main
    config:
      default_model: claude-sonnet-4-6

# loop-pipeline IS the outer orchestrator — installed at bundle-prepare time.
# dot_source or dot_file is provided by the wrapper overlay; do not hardcode here.
session:
  orchestrator:
    module: loop-pipeline
    source: git+https://github.com/microsoft/amplifier-bundle-dot-runner@main#subdirectory=modules/loop-pipeline
    config:
      profiles:
        anthropic: pipeline-agent-anthropic
        anthropic-commenter: pipeline-agent-commenter
  context:
    module: context-simple
    source: git+https://github.com/microsoft/amplifier-module-context-simple@main

# Pipeline progress hook — emits [PIPELINE] log lines for every node start,
# node complete, edge selected, and provider response. Gives real-time
# visibility into investigate/quality_eval cycles in GH Actions logs.
hooks:
  - module: hooks-pipeline-progress
    source: git+https://github.com/microsoft/amplifier-bundle-dot-runner@main#subdirectory=modules/hooks-pipeline-progress

# Orchestrator-level tools (used for pipeline management, not child sessions)
tools:
  - module: tool-filesystem
    source: git+https://github.com/microsoft/amplifier-module-tool-filesystem@main
  - module: tool-bash
    source: git+https://github.com/microsoft/amplifier-module-tool-bash@main
    config:
      timeout: 120
  - module: tool-search
    source: git+https://github.com/microsoft/amplifier-module-tool-search@main

# Two child agent profiles:
#   pipeline-agent-anthropic  — investigation nodes (NO github_post_comment)
#   pipeline-agent-commenter  — comment_draft only (WITH github_post_comment)
#
# DOT usage: add  llm_provider="anthropic-commenter"  on the comment_draft node
# to select the commenter profile. All other nodes default to "anthropic" →
# pipeline-agent-anthropic, which cannot post to GitHub.
agents:
  pipeline-agent-anthropic:
    session:
      orchestrator:
        module: loop-agent
        source: git+https://github.com/microsoft/amplifier-bundle-dot-runner@main#subdirectory=modules/loop-agent
        config:
          max_tool_rounds_per_input: 50
          default_command_timeout_ms: 120000
      context:
        module: context-simple
        source: git+https://github.com/microsoft/amplifier-module-context-simple@main
    providers:
      - module: provider-anthropic
        source: git+https://github.com/microsoft/amplifier-module-provider-anthropic@main
        config:
          default_model: claude-sonnet-4-6
    hooks:
      - module: hooks-streaming-ui
        source: git+https://github.com/microsoft/amplifier-module-hooks-streaming-ui@main
        config:
          ui:
            show_thinking_stream: true
            show_tool_lines: 30
            show_token_usage: true
    tools:
      - module: tool-filesystem
        source: git+https://github.com/microsoft/amplifier-module-tool-filesystem@main
      - module: tool-bash
        source: git+https://github.com/microsoft/amplifier-module-tool-bash@main
        config:
          timeout: 120
      - module: tool-search
        source: git+https://github.com/microsoft/amplifier-module-tool-search@main
      - module: tool-github-add-label
      - module: tool-github-checkout-repo
      # NOTE: tool-report-outcome is intentionally NOT included.
      # When it IS available, the model calls it as a tool (turn 1), then the
      # loop-agent sends the tool result back to the LLM (turn 2), and the
      # turn-2 prose response replaces the JSON in last_text →
      # _parse_outcome sees plain text → SUCCESS regardless of the verdict.
      # Without the tool, quality_eval outputs ONLY the JSON in a single LLM
      # turn. _parse_outcome reads the JSON → correct FAIL/SUCCESS routing.

  pipeline-agent-commenter:
    session:
      orchestrator:
        module: loop-agent
        source: git+https://github.com/microsoft/amplifier-bundle-dot-runner@main#subdirectory=modules/loop-agent
        config:
          max_tool_rounds_per_input: 50
          default_command_timeout_ms: 120000
      context:
        module: context-simple
        source: git+https://github.com/microsoft/amplifier-module-context-simple@main
    providers:
      - module: provider-anthropic
        source: git+https://github.com/microsoft/amplifier-module-provider-anthropic@main
        config:
          default_model: claude-sonnet-4-6
    hooks:
      - module: hooks-streaming-ui
        source: git+https://github.com/microsoft/amplifier-module-hooks-streaming-ui@main
        config:
          ui:
            show_thinking_stream: true
            show_tool_lines: 30
            show_token_usage: true
    tools:
      # Same investigation tools as pipeline-agent-anthropic so the commenter
      # can re-verify findings in code before writing the final comment.
      - module: tool-filesystem
        source: git+https://github.com/microsoft/amplifier-module-tool-filesystem@main
      - module: tool-bash
        source: git+https://github.com/microsoft/amplifier-module-tool-bash@main
        config:
          timeout: 120
      - module: tool-search
        source: git+https://github.com/microsoft/amplifier-module-tool-search@main
      - module: tool-github-checkout-repo
      # Plus posting capability — the only thing investigate must not have.
      - module: tool-github-post-comment
      - module: tool-github-add-label
---

# attractor-pipeline Bundle

Generic DOT pipeline runner. Uses `loop-pipeline` as the outer session orchestrator
so the module is installed at bundle-prepare time — fixing the silent
`DirectProviderBackend` fallback that caused `nodes_completed: 0`.

## How the wrapper uses this bundle

1. `_run_attractor()` reads the DOT file from `attractor_source`
2. Generates a temp overlay bundle that `includes:` this bundle and adds
   `session.orchestrator.config.dot_source` with the DOT content inline
3. The wrapper calls the Python API: load_bundle → compose overlay → prepare → create_initialized_session → execute.

The outer `loop-pipeline` session then has AmplifierBackend available
(CLI registers `session.spawn`), spawning `pipeline-agent-anthropic` per node.

## Child agent tools

| Tool | Description |
|------|-------------|
| `tool-filesystem` | File read/write/list |
| `tool-bash` | Shell commands (120 s timeout) |
| `tool-search` | Web/code search |
| `github_post_comment` | Post or update issue/PR comments |
| `github_add_label` | Add labels to issues/PRs |
| `github_checkout_repo` | Shallow-clone repos for inspection |
