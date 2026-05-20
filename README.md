# amplifier-app-actions

AI-powered issue triage and PR review for your GitHub repos.

## Quick start

1. Add `ANTHROPIC_API_KEY` as a repository secret (Settings → Secrets and variables → Actions).
2. Create one of the workflow files below in `.github/workflows/`.

### Issue triage

```yaml
# .github/workflows/issue-triage.yml
name: Issue Triage

on:
  issues:
    types: [opened]

permissions:
  issues: write
  contents: read

jobs:
  triage:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: microsoft/amplifier-app-actions@v1
        with:
          prompt: |
            You are triaging a new GitHub issue.

            Review the issue title and body. Then:
            1. Classify the issue type and add the appropriate label: bug, feature-request, question, or documentation
            2. Post a comment that acknowledges the issue, confirms its type, and briefly describes what happens next

            Be concise. Do not speculate about causes or promise timelines.
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

### PR review

```yaml
# .github/workflows/pr-review.yml
name: PR Review

on:
  pull_request:
    types: [opened]

permissions:
  pull-requests: write
  contents: read

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: microsoft/amplifier-app-actions@v1
        with:
          prompt: |
            You are reviewing a new pull request.

            Review the changed files and the PR description. Post a comment that:
            1. Summarizes what this PR changes and why, in 2-3 sentences
            2. Lists any bugs, logic errors, or security concerns — be specific, cite file and line where possible
            3. Notes any improvements that would strengthen the PR

            Be direct. Focus detail on concerns. Do not block on style preferences.
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

## Get help setting up

Load the `app-actions` bundle in your local Amplifier session to get AI-assisted help configuring workflows, writing prompts, or designing attractor pipelines:

```bash
amplifier run --bundle git+https://github.com/microsoft/amplifier-app-actions@main#subdirectory=bundles/app-actions.bundle.md
```

Then ask naturally:

- *"Help me set up issue triage and PR reviews for my repo"* — produces ready-to-use workflow YAML with sane default prompts, correct permissions, and the bot-comment guard.
- *"Create a .dot attractor pipeline for manager-supervisor issue investigation"* — designs the pipeline with quality gate, thread isolation, and comment-draft node.
- *"Show me the full four-workflow pattern"* — issue triage, investigation, PR review, and triage-continue with slash commands.

Two expert agents are available: `app-actions-expert` (workflow setup) and `dot-setup-expert` (attractor pipeline design). You don't call them directly — the session routes to the right one based on your question.

## What it does

The action reads the GitHub event (issue or PR), runs an Amplifier agent session against it, and posts findings back as a comment and/or label. It can run a one-shot prompt or a multi-step recipe. The agent has a bounded capability surface: it can read repo files, post a comment, and add a label. Nothing else.

## Configuration

| Input | Description | Default |
|-------|-------------|---------|
| `prompt` | Inline prompt text | — |
| `prompt_source` | Path or URL to a prompt file | — |
| `recipe_source` | Path or URL to an Amplifier recipe YAML | — |
| `attractor_source` | Path or URL to an attractor `.dot` file | — |
| `bundle` | Bundle to load — local path or `git+https://host/org/repo@ref#subdirectory=bundle.md` URI. When omitted, the built-in `github-tools` bundle is used. | `github-tools` |
| `provider` | LLM provider: `anthropic`, `openai`, `azure`, `ollama` | `anthropic` |
| `model` | Model name override — falls back to provider default if omitted | — |
| `github_token` | GitHub token for API calls | `${{ github.token }}` |

Exactly one of `prompt`, `prompt_source`, `recipe_source`, or `attractor_source` must be set.

### Built-in bundle tiers

When no `bundle:` is specified the action uses `github-tools`. Two higher tiers are also available as built-in aliases:

| Alias | What it adds |
|-------|-------------|
| `github-tools` | Foundation agents, Anthropic provider, `github_post_comment`, `github_add_label`, `github_checkout_repo` |
| `github-tools-dtu` | Everything in `github-tools` + Digital Twin Universe for containerised reproduction (`enable_reproduction: true`) |
| `github-tools-amplifier-dev` | Everything in `github-tools-dtu` (placeholder for future Amplifier-ecosystem tooling) |

### Bringing your own bundle

Point `bundle:` at any bundle file via a `git+https://` URI:

```yaml
bundle: git+https://github.com/kenotron-ms/amplifier-bundle-dev-support@main#subdirectory=bundles/issue-triage.bundle.md
```

The `#subdirectory=` fragment selects a specific file inside the repo. The named bundle becomes the active bundle for the entire run — it can compose the built-in `github-tools` bundle to inherit all standard tools while adding its own context and behaviors on top.

[`kenotron-ms/amplifier-bundle-dev-support`](https://github.com/kenotron-ms/amplifier-bundle-dev-support) is the reference bundle for Amplifier development workflows (issue triage, deep investigation, PR review).

Provider API keys are passed as environment variables, not action inputs. Set the appropriate secret for your provider:

| Provider | Environment variable |
|----------|---------------------|
| Anthropic | `ANTHROPIC_API_KEY` |
| OpenAI | `OPENAI_API_KEY` |
| Azure OpenAI | `AZURE_OPENAI_API_KEY` |
| Ollama | (no key needed) |

## Recipes and attractors (advanced)

For runs more involved than a single prompt, point the action at a recipe or attractor file. Each accepts a local workspace path or an HTTPS URL.

- **`recipe_source`** — a multi-step Amplifier recipe YAML. The action loads the recipe and runs it against the event context. Requires `actions/checkout` to be present when the source is a local path. Staged (approval-gated) recipes are not supported in CI and will fail with a clear error.
- **`attractor_source`** — a Graphviz `.dot` attractor file describing the shape of the desired outcome. The action loads it as additional context for the agent, useful for steering recipes or prompts toward a known-good structure.

### Recipe Context Variables

Recipe step prompts support Jinja2 templating. Context variables from the GitHub event are passed to the recipe runner via the standard `recipes` tool `context` argument. Refer to the [Amplifier recipes documentation](https://github.com/microsoft/amplifier-bundle-recipes) for the full list of template variables and step-output variable patterns.

Example recipe:

```yaml
steps:
  - id: understand
    agent: foundation:zen-architect
    prompt: |
      Analyze issue #{{ context.number }} in {{ context.owner }}/{{ context.repo }}.
      Title: {{ context.title }}
      Body: {{ context.body }}
      Respond with JSON: {"problem_statement": "...", "affected_repos": [...]}
    parse_json: true

  - id: investigate
    agent: foundation:bug-hunter
    prompt: |
      Problem: {{ understand.problem_statement }}
      Repos:   {{ understand.affected_repos }}
```

Context variables like `context.number`, `context.owner`, `context.title`, `context.body`, etc. are automatically injected into the recipe context by the action before execution.

## Local testing

### Install

From your local checkout, install the `amplifier-triage` command as a uv tool:

```bash
uv tool install --editable .
```

Or run without installing (one-off):

```bash
uv run amplifier-triage --help
```

### Test a recipe

This example uses issue #3 from `kenotron-ms/amplifier-actions-example` and the five-stage investigation recipe from that repo (understand → clone → investigate → reproduce → report).

**1. Create `test-event.json`:**

```json
{
  "action": "labeled",
  "issue": {
    "number": 3,
    "title": "Sub-agent sessions ignore routing matrix fallback chains — child always uses first model, never falls back",
    "body": "## Problem\n\nWhen the routing matrix bundle defines a fallback chain (e.g. `claude-opus → claude-sonnet → claude-haiku`), the parent session correctly walks the chain when a model is unavailable. However, child sessions spawned via `delegate()` only receive the first resolved model — the rest of the chain is dropped. If that model fails, the child errors rather than falling back.\n\n## Affected repos\n\n- `microsoft/amplifier-core` — `session.spawn` / config propagation into child sessions\n- `microsoft/amplifier-bundle-routing-matrix` — how routing config and fallback chains are structured in the bundle\n- `microsoft/amplifier-foundation` — `delegate()` implementation and how config is passed to spawned sessions\n\n## Steps to reproduce\n\n1. Install the routing matrix bundle with a multi-model fallback chain configured\n2. Run a session that delegates to a sub-agent with `model_role: coding`\n3. Simulate the first model being unavailable (rate limit or disable it)\n4. Observe parent session falls back to next model in chain — works correctly\n5. Observe child session errors with model unavailable rather than falling back\n\n## Expected behaviour\n\nChild sessions inherit the full routing config including the complete fallback chain.\n\n## Actual behaviour\n\nChild sessions only have the first/resolved model. The fallback chain is not present in the child's config. Child fails hard on model unavailability.",
    "user": { "login": "kenotron-ms" },
    "labels": [
      { "name": "bug" },
      { "name": "high-priority" },
      { "name": "needs-investigation" }
    ]
  },
  "repository": {
    "name": "amplifier-actions-example",
    "owner": { "login": "kenotron-ms" }
  }
}
```

**2. Run:**

```bash
ANTHROPIC_API_KEY=sk-ant-... \
GITHUB_TOKEN=ghp_...         \
amplifier-triage              \
  --recipe-source ~/workspace/ms/amplifier-actions-example/.github/amplifier/investigate-recipe.yaml \
  --event-path    ./test-event.json
```

The recipe runs five stages: extract a structured understanding of the issue, clone the three affected Amplifier repos (`amplifier-core`, `amplifier-bundle-routing-matrix`, `amplifier-foundation`), read source and form a root-cause hypothesis with `file:line` evidence, attempt reproduction in a DTU container, then post a structured report comment and apply `bug-confirmed`, `needs-repro-steps`, or `investigation-complete` as appropriate.

### Test an attractor

```bash
ANTHROPIC_API_KEY=sk-ant-... \
GITHUB_TOKEN=ghp_...         \
amplifier-triage              \
  --attractor-source ./path/to/attractor.dot \
  --event-path       ./test-event.json
```

`--event-path` defaults to `$GITHUB_EVENT_PATH`. Omit it (and leave the env var unset) to run without GitHub event context.

### Minimal test event

Save this as `test-event.json` to simulate a GitHub issue:

```json
{
  "action": "opened",
  "issue": {
    "number": 1,
    "title": "Example issue",
    "body": "Steps to reproduce...",
    "user": { "login": "octocat" },
    "labels": []
  },
  "repository": {
    "name": "my-repo",
    "owner": { "login": "my-org" }
  }
}
```

For a pull request event, replace `"issue"` with `"pull_request"` and add `"base": {"ref": "main"}` and `"head": {"ref": "my-branch"}` inside it.

### Point at Gitea or a DTU

You can run this action against a local Gitea sandbox or a Digital Twin Universe (DTU) instance instead of github.com. Override the API and clone endpoints via environment variables:

```yaml
env:
  GITHUB_API_URL: http://localhost:3000/api/v1   # point at Gitea
  GITHUB_CLONE_URL: http://localhost:3000         # redirect clones
  ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

This is useful for iterating on prompts, recipes, or the action itself without round-tripping through github.com — for example, when running inside a DTU profile or against an ephemeral Gitea container.

| Env var | Purpose |
|---------|---------|
| `GITHUB_API_URL` | Redirect GitHub REST API calls (e.g. to a local Gitea instance) |
| `GITHUB_CLONE_URL` | Redirect `git clone` calls (e.g. to a local Gitea instance) |

## Requirements

- A private GitHub repository
- An API key for your chosen LLM provider
- `actions/checkout@v4` in your workflow (required for PR review; recommended for issue triage)

## Security

This action is designed for private repositories. The agent's capability surface is intentionally bounded: it reads files, posts comments, and adds labels — nothing else. The workflow must not use `pull_request_target`; use `pull_request` only.

## Issue reproduction (advanced)

When `enable_reproduction: true` is set, the action uses `amplifier-tester:setup-digital-twin` to spin up an ephemeral, isolated Ubuntu container for reproduction. The agent:

1. Mirrors the affected repos into a local Gitea instance using `amplifier-gitea mirror-from-github`
2. Generates a DTU profile with `url_rewrites` pointing those repos at Gitea
3. Launches the container, runs the reproduction script from the issue body, captures the output, and destroys the container — leaving no trace on the host

This is useful for verifying that a bug exists at a reported version and is fixed in a newer one without touching the host system.

### Private repositories

`GITHUB_TOKEN` is automatically injected into the container from the host environment. No extra configuration is needed — private repos are cloned via `x-access-token:<token>@github.com`.

### Runner requirements

> **Note:** `enable_reproduction: true` requires a full VM runner — `runs-on: ubuntu-latest` — **not** a container-based runner. Self-hosted runners with Incus pre-installed are also supported.

When `enable_reproduction: true` is set, the action automatically bootstraps Incus in three steps before running the agent:

1. Install the Incus package.
2. Initialise Incus with a minimal `preseed` configuration.
3. Verify the daemon is healthy.

No manual setup is required when using the `ubuntu-latest` hosted runner.

### Complete workflow example

```yaml
# .github/workflows/issue-triage-with-reproduction.yml
name: Issue Triage with Reproduction

on:
  issues:
    types: [opened]

permissions:
  issues: write
  contents: read

jobs:
  triage:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: microsoft/amplifier-app-actions@v1
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          enable_reproduction: true
          prompt: |
            You are triaging a new GitHub issue.

            Review the issue title and body. Then:
            1. Classify the issue type and add the appropriate label: bug, feature-request, question, or documentation
            2. Post a comment that acknowledges the issue, confirms its type, and briefly describes what happens next

            If the issue describes a crash or unexpected behaviour and includes version information,
            use the triage-repro bundle (enable_reproduction: true) to reproduce the failure in an isolated container.

            Be concise. Do not speculate about causes or promise timelines.
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

## Contributing

This project welcomes contributions and suggestions. Most contributions require
you to agree to a Contributor License Agreement (CLA) declaring that you have
the right to, and actually do, grant us the rights to use your contribution.
For details, visit https://cla.opensource.microsoft.com.

When you submit a pull request, a CLA bot will automatically determine whether
you need to provide a CLA and decorate the PR appropriately (e.g., status
check, comment). Simply follow the instructions provided by the bot. You will
only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

## Trademarks

This project may contain trademarks or logos for projects, products, or services.
Authorized use of Microsoft trademarks or logos is subject to and must follow
[Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/en-us/legal/intellectualproperty/trademarks/usage/general).
Use of Microsoft trademarks or logos in modified versions of this project must
not cause confusion or imply Microsoft sponsorship.
Any use of third-party trademarks or logos are subject to those third-party's policies.
