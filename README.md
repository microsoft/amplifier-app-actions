# amplifier-app-actions

AI-assisted issue triage, PR review, and investigation that runs directly inside GitHub Actions, powered by [Amplifier](https://github.com/microsoft/amplifier). Drop in a workflow, point it at a purpose-built bundle, and your repo gets an agent that classifies issues, reviews diffs, and posts findings — no extra infrastructure needed.

## Quick start

### Local setup experts (provider-neutral)

To make the `/github-actions` setup and debugging experts available in every local Amplifier
session, register the base behavior once:

```bash
amplifier bundle add 'git+https://github.com/microsoft/amplifier-app-actions@main#subdirectory=behaviors/app-actions.yaml' --app
```

The `--app` flag belongs to `amplifier bundle add`, not `amplifier run`. After registration,
normal `amplifier run` sessions compose the app behavior automatically. This behavior declares no
provider policy, so it preserves the provider configured by the user, including OpenAI.

**Optional addition:** To give `dot-setup-expert` the full Attractor DOT documentation, also
register the provider-neutral Attractor overlay:

```bash
amplifier bundle add 'git+https://github.com/microsoft/amplifier-app-actions@main#subdirectory=behaviors/app-actions-attractor.yaml' --app
```

This overlay is an addition to `app-actions.yaml`, not a replacement for it.

These local setup behaviors are separate from the GitHub Action runtime bundles below. The local
behaviors inherit your configured provider; the purpose-built GitHub Action bundles intentionally
use Anthropic.

### PR review, locally and interactively (Agent Skill)

For fast, local, in-session PR review — no GitHub comment posted, no CI run, just a review
reported back directly in your session — install the `pr-review` Agent Skill:

```bash
npx skill add microsoft/amplifier-app-actions --skill pr-review
```

Once installed, ask any local Amplifier session to review a PR (e.g. *"review this PR"*). The
skill delegates to a dedicated review agent for a clean-room review with fresh context, and
reports its findings back in the session.

**This is a different install path from the GitHub Action runtime `pr-review` bundle** described
below — they solve different problems:

| | Skill (`npx skill add ... --skill pr-review`) | Bundle (`bundle:` workflow input → `pr-review.bundle.md`) |
|---|---|---|
| Runs | Locally, in an interactive Amplifier session | In CI, via GitHub Actions |
| Trigger | You ask for a review | `pull_request: [opened]` event |
| Output | Reported in-session | Posted as a PR comment |
| Use it for | Local/interactive review while you work | Automated, CI-triggered review |

### GitHub Action runtime (Anthropic)

Add `ANTHROPIC_API_KEY` as a repository secret (**Settings → Secrets and variables → Actions**),
then copy the workflow below. These runtime bundles intentionally configure Anthropic; this does
not change the provider used by your normal local Amplifier sessions.

#### Issue triage

No `actions/checkout` needed — the agent reads the event payload directly.

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
      - uses: microsoft/amplifier-app-actions@main
        with:
          bundle: git+https://github.com/microsoft/amplifier-app-actions@main#subdirectory=bundles/issue-triage.bundle.md
          prompt: A new issue was opened. Triage it.
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

#### PR review

> **Want local, interactive review instead of a CI comment?** See
> [PR review, locally and interactively](#pr-review-locally-and-interactively-agent-skill) above —
> install with `npx skill add microsoft/amplifier-app-actions --skill pr-review`. This section
> covers the separate GitHub Actions runtime path, which runs in CI and posts a comment on the PR.

`actions/checkout` with `fetch-depth: 0` is required so the agent can read the full diff.

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
        with:
          fetch-depth: 0
      - uses: microsoft/amplifier-app-actions@main
        with:
          bundle: git+https://github.com/microsoft/amplifier-app-actions@main#subdirectory=bundles/pr-review.bundle.md
          prompt: A pull request was opened. Review it.
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

> **Want a more thorough review?** The [`pipelines/pr-review-exhaustive.dot`](pipelines/pr-review-exhaustive.dot) attractor pipeline runs 5 independent reviewer lanes (correctness, architecture, patterns, tests, pedantic) and posts inline annotations on the Files Changed tab. See [Attractor pipeline](#c-attractor-pipeline-attractor_source) for usage.

> **Security warning:** Never use `pull_request_target` in workflows that call this action. `pull_request_target` runs with write permissions in the context of the base branch and can expose secrets to untrusted code from a fork. Use `pull_request` only. See [Preventing pwn requests](https://securitylab.github.com/research/github-actions-preventing-pwn-requests/).

## How it works

When a workflow triggers, the action runs an Amplifier agent session against the GitHub event (issue opened, PR opened, comment created, etc.). You supply **exactly one** instruction source — an inline `prompt`, a `prompt_source` file, a `recipe_source` YAML, or an `attractor_source` pipeline — plus a `bundle` that gives the agent its tools and context. The agent reads the event, does its work, and posts a comment and/or label back to GitHub.

## Three ways to drive it

### a. Default: let the bundle do it (recommended)

The specialized bundles — `issue-triage`, `pr-review`, and `investigate` — come pre-loaded with battle-tested guidance for their job. A one-line prompt is all you need; the bundle supplies the expertise. This is how the [setup agent](#get-help-setting-up) configures a new repo.

> **Important:** These bundles are **not** built-in aliases — setting `bundle:` to a bare name such as `issue-triage`, `pr-review`, or `investigate` **will not work**. Always reference them via their full `git+https://` URI.

**Issue triage** (no checkout needed):

```yaml
- uses: microsoft/amplifier-app-actions@main
  with:
    bundle: git+https://github.com/microsoft/amplifier-app-actions@main#subdirectory=bundles/issue-triage.bundle.md
    prompt: A new issue was opened. Triage it.
  env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

**PR review** (`actions/checkout` required):

```yaml
- uses: actions/checkout@v4
  with:
    fetch-depth: 0
- uses: microsoft/amplifier-app-actions@main
  with:
    bundle: git+https://github.com/microsoft/amplifier-app-actions@main#subdirectory=bundles/pr-review.bundle.md
    prompt: A pull request was opened. Review it.
  env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

**Issue investigation** (triggered by `/investigate` comment, `actions/checkout` required):

```yaml
- uses: actions/checkout@v4
  with:
    fetch-depth: 0
- uses: microsoft/amplifier-app-actions@main
  with:
    bundle: git+https://github.com/microsoft/amplifier-app-actions@main#subdirectory=bundles/investigate.bundle.md
    prompt: |
      A contributor requested investigation of this issue.
      Read the issue from the GitHub event context, examine the repository
      code, and post your findings as a comment.
  env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

### b. Custom prompt

Write your own instructions as an inline string or a file in your repo.

**`prompt:` (inline)** — best for short, self-contained instructions. No checkout needed when using an inline prompt with no local file dependencies.

```yaml
- uses: microsoft/amplifier-app-actions@main
  with:
    prompt: |
      Review the issue title and body.
      Add one of these labels: bug, feature-request, question, documentation.
      Post a brief acknowledgment comment.
  env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

**`prompt_source:` (file path or `git+https://` URI)** — best for longer prompts you want to version-control separately. For a local path, it is resolved from `$GITHUB_WORKSPACE`; pass a `git+https://` URI to fetch from another repo without a checkout step.

```yaml
- uses: actions/checkout@v4
- uses: microsoft/amplifier-app-actions@main
  with:
    prompt_source: .github/amplifier/triage-prompt.md
  env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

### c. Attractor pipeline (`attractor_source:`)

For multi-step triage or review, point `attractor_source:` at a Graphviz `.dot` file that defines a pipeline. The action **executes** the pipeline via the `loop-pipeline` orchestrator — it does not simply load the file as context.

How an attractor run works:

- The `bundle:` input is **ignored** — the built-in `attractor-pipeline` bundle is always used.
- The GitHub event becomes the pipeline's goal.
- Each node runs as a separate child session; analysis nodes can read code and call tools.
- One node must be designated as the commenter by setting `llm_provider="anthropic-commenter"` on it; only that node can post comments and labels.

`actions/checkout` is required for a local path (the `.dot` file lives in your repo); use a `git+https://` URI to reference a pipeline from this repo directly without a checkout step.

> **⚠️ `max_pipeline_duration` units trap.** loop-pipeline's DOT parser (`_try_parse_duration`) only recognizes a unit suffix — `"4h"`, `"14400s"`, `"30m"` — and normalizes it to milliseconds internally. **A bare, unsuffixed integer (`max_pipeline_duration=14400`) is stored as-is and treated as milliseconds, NOT seconds** — `14400` is 14.4 seconds, not 4 hours. This is easy to hit if you "simplify" a working `max_pipeline_duration="4h"` down to a bare number when porting a `.dot` into CI: the pipeline will die almost immediately with `max_pipeline_duration_exceeded`. Always include a unit suffix (`h`, `m`, `s`, or `ms`) on `max_pipeline_duration`.
>
> **Evidence for failed runs.** Every attractor run's log directory (per-node `status.json`, `command.txt`, `response.md`, and `graph.dot`) is surfaced as the `logs_dir` action output. Upload it as an artifact — with `if: always()` so it's captured on failed runs too, which is exactly when you need it most:
>
> ```yaml
> - uses: microsoft/amplifier-app-actions@main
>   id: amplifier
>   with:
>     attractor_source: .github/amplifier/pr-review-exhaustive.dot
>   env:
>     ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
> - uses: actions/upload-artifact@v4
>   if: always()
>   with:
>     name: attractor-logs
>     path: ${{ steps.amplifier.outputs.logs_dir }}
> ```

#### Ready-made pipelines

This repo ships ready-to-use attractor pipelines in the [`pipelines/`](pipelines/) directory. Reference them directly via `git+https://` — no local copy needed.

| Pipeline | What it does |
|----------|-------------|
| [`pipelines/pr-review-exhaustive.dot`](pipelines/pr-review-exhaustive.dot) | **Exhaustive PR review.** 5 thread-isolated reviewer lanes (correctness · architecture · patterns · tests · pedantic), each with a fresh LLM context so lanes cannot anchor on each other's conclusions. Findings are merged, deduplicated, and prioritized by an adversarial quality gate before posting one comprehensive PR review comment with inline annotations on the Files Changed tab. |

**Exhaustive PR review — zero-copy quickstart** (`actions/checkout` required for the diff):

```yaml
- uses: actions/checkout@v4
  with:
    fetch-depth: 0
- uses: microsoft/amplifier-app-actions@main
  with:
    attractor_source: git+https://github.com/microsoft/amplifier-app-actions@main#subdirectory=pipelines/pr-review-exhaustive.dot
  env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
    GH_TOKEN: ${{ github.token }}   # pipeline nodes use curl — needs GH_TOKEN
```

To customize the pipeline, copy `pipelines/pr-review-exhaustive.dot` to `.github/amplifier/pr-review-exhaustive.dot` in your repo and switch to a local path:

```yaml
attractor_source: .github/amplifier/pr-review-exhaustive.dot
```

A complete example workflow is at [`docs/examples/pr-review-attractor-workflow.yml`](docs/examples/pr-review-attractor-workflow.yml).

**Per-repo context for attractor nodes.** The Amplifier session search path includes `$GITHUB_WORKSPACE`, so a node prompt can `@mention` a file from the consumer repo without hardcoding owner/name:

```dot
node [prompt="@.github/amplifier/review-context.md"]
```

This is the recommended way to inject project-specific architecture rules, layer boundaries, or naming conventions into a shared pipeline — ship the `.dot` file here and let each consumer repo provide its own context file.

## Local vs remote sourcing

`bundle:` has supported `git+https://` URIs since launch; `prompt_source`, `attractor_source`, and `recipe_source` now support them too.

| Input | Local path | Remote (`git+https://`) | Needs `actions/checkout`? |
|-------|:----------:|:-----------------------:|:-------------------------:|
| `bundle` | ✓ | ✓ | No |
| `prompt_source` | ✓ | ✓ | Only for local paths |
| `recipe_source` | ✓ | ✓ | Only for local paths |
| `attractor_source` | ✓ | ✓ | Only for local paths |

Local paths for `prompt_source`, `recipe_source`, and `attractor_source` are resolved relative to `$GITHUB_WORKSPACE` (the root of the checked-out repo). If the file is missing from disk (e.g. `actions/checkout` was skipped), the action fails with a `FileNotFoundError` telling you to add `actions/checkout`.

Remote `git+https://` URIs are fetched directly via the GitHub Contents API — no checkout step needed.

### Remote sourcing via `git+https://`

All three `*_source` inputs accept the same URI grammar as `bundle:`:

```
git+https://github.com/<org>/<repo>@<ref>#subdirectory=<path/to/file>
```

- `@<ref>` is optional and defaults to `main`.
- `#subdirectory=<file>` carries the path to the single file to fetch.
- Fetched via the GitHub Contents API; the `GITHUB_API_URL` environment variable is honoured as the base (same override used for Gitea/DTU).

**Private repositories:** `github_token` must have read access to the source repo. The default `${{ github.token }}` is scoped to the workflow's own repository — to fetch from a *different* private repo, supply a PAT (or any token with cross-repo read access) via the `github_token` input.

```yaml
- uses: microsoft/amplifier-app-actions@main
  with:
    prompt_source: git+https://github.com/my-org/shared-prompts@main#subdirectory=prompts/triage.md
  env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

The same form works for `attractor_source` (a `.dot` file) and `recipe_source` (a YAML).

## Configuration reference

**Exactly one of `prompt`, `prompt_source`, `recipe_source`, or `attractor_source` must be set.** Setting zero, or more than one, raises a `ValueError`.

| Input | Description | Default |
|-------|-------------|---------|
| `prompt` | Inline prompt text | — |
| `prompt_source` | Path to a prompt file in the checked-out repo (local path or `git+https://` URI; `actions/checkout` required for local paths) | — |
| `recipe_source` | Path to an Amplifier recipe YAML in the checked-out repo (local path or `git+https://` URI; `actions/checkout` required for local paths) | — |
| `attractor_source` | Path to an attractor `.dot` pipeline in the checked-out repo (local path or `git+https://` URI; `actions/checkout` required for local paths) | — |
| `bundle` | Bundle alias, local path, or `git+https://` URI. See [Bundles](#bundles). | `github-tools` |
| `provider` | *Accepted but currently a no-op — the bundle controls provider/model.* Valid values: `anthropic`, `openai`, `github-copilot`. | `anthropic` |
| `model` | *Accepted but currently a no-op — the bundle controls provider/model.* | — |
| `github_token` | GitHub token for API calls | `${{ github.token }}` |
| `enable_reproduction` | When `true`, installs Incus and upgrades to `github-tools-dtu`. Requires `ubuntu-latest` full VM runner (not a container-based runner). | `false` |
| `target_dir` | Attractor runs only: working directory `tool_command=` / `must_write=` nodes resolve relative paths against. | `$GITHUB_WORKSPACE` |

## Bundles

A bundle gives the agent its tools, provider, and context. The `bundle:` input accepts a built-in alias (bare name), a local path, or a `git+https://` URI.

### Built-in aliases (bare names work)

| Alias | What it includes |
|-------|-----------------|
| `github-tools` | Foundation agents · Anthropic provider (claude-sonnet-4-6) · `github_post_comment`, `github_add_label`, `github_checkout_repo`. **Default when `bundle:` is omitted.** |
| `github-tools-dtu` | Everything in `github-tools` + Digital Twin Universe for containerised reproduction |
| `github-tools-amplifier-dev` | Everything in `github-tools-dtu` (placeholder for future Amplifier-ecosystem tooling) |
| `attractor-pipeline` | Used automatically for `attractor_source` runs. Do not set this manually. |

### Specialized workflow bundles (must use `git+https://` — bare names do not work)

These bundles layer job-specific context on top of `github-tools`. They live in this repo but are **not** registered as built-in aliases — you must reference them via their full URI.

| Bundle | Trigger event | Adds on top of `github-tools` |
|--------|---------------|-------------------------------|
| `issue-triage` | `issues: [opened]` | Issue classification guidance, label taxonomy, acknowledgment comment style |
| `pr-review` | `pull_request: [opened]` | Five-check review framework (Necessity · Layer fit · Pattern · Correctness · Calibration) |
| `investigate` | `issue_comment` slash-command (e.g. `/investigate`) | Investigation methodology, evidence standards, findings comment format |

```yaml
# Issue triage
bundle: git+https://github.com/microsoft/amplifier-app-actions@main#subdirectory=bundles/issue-triage.bundle.md

# PR review
bundle: git+https://github.com/microsoft/amplifier-app-actions@main#subdirectory=bundles/pr-review.bundle.md

# Investigation
bundle: git+https://github.com/microsoft/amplifier-app-actions@main#subdirectory=bundles/investigate.bundle.md
```

### Bringing your own bundle

Point `bundle:` at any bundle file via a `git+https://` URI:

```yaml
bundle: git+https://github.com/my-org/my-bundles@main#subdirectory=bundles/my-bundle.bundle.md
```

Your bundle can compose `github-tools` to inherit all standard tools while adding its own context and behaviors.

## Provider API keys

Provider credentials are passed as environment variables, not action inputs. Set the appropriate secret for your provider:

| Provider | Environment variable |
|----------|---------------------|
| Anthropic | `ANTHROPIC_API_KEY` |
| OpenAI | `OPENAI_API_KEY` |
| GitHub Copilot | (no key needed — uses `GITHUB_TOKEN`) |

The `provider` and `model` inputs are accepted but are **no-ops**; the active bundle decides which provider and model to use. The default `github-tools` bundle (and the specialized bundles built on it) uses Anthropic with `claude-sonnet-4-6`.

## Advanced

### Recipes (`recipe_source:`)

Point `recipe_source:` at an Amplifier recipe YAML to run a multi-step pipeline. The file can be a local path in the checked-out repo (requires `actions/checkout`) or a `git+https://` URI. Staged (approval-gated) recipes are not supported in CI and will fail with a clear error.

Recipe step prompts support Jinja2 templating. GitHub event fields are injected automatically:

```yaml
steps:
  - id: understand
    agent: foundation:zen-architect
    prompt: |
      Analyze issue #{{ context.number }} in {{ context.owner }}/{{ context.repo }}.
      Title: {{ context.title }}
      Body:  {{ context.body }}
      Respond with JSON: {"problem_statement": "...", "affected_repos": [...]}
    parse_json: true

  - id: investigate
    agent: foundation:bug-hunter
    prompt: |
      Problem: {{ understand.problem_statement }}
      Repos:   {{ understand.affected_repos }}
```

Variables like `context.number`, `context.owner`, `context.title`, `context.body`, etc. are automatically injected by the action before execution.

### Issue reproduction (`enable_reproduction: true`)

Setting `enable_reproduction: true` installs Incus on the runner and automatically upgrades the bundle to `github-tools-dtu`, which adds Digital Twin Universe support. The agent can then:

1. Mirror affected repos into a local Gitea instance using `amplifier-gitea mirror-from-github`
2. Generate a DTU profile with `url_rewrites` pointing those repos at Gitea
3. Launch an ephemeral Ubuntu container, run the reproduction script from the issue body, capture output, and destroy the container — leaving no trace on the host

`GITHUB_TOKEN` is automatically injected into the container. Requires `runs-on: ubuntu-latest` (full VM runner — **not** a container-based runner).

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
      - uses: microsoft/amplifier-app-actions@main
        with:
          enable_reproduction: true
          prompt: |
            You are triaging a new GitHub issue.
            Review the issue title and body. Classify it and add the appropriate label.
            If the issue describes a crash or unexpected behaviour and includes version
            information, attempt reproduction in an isolated container.
            Be concise. Do not speculate about causes or promise timelines.
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

### Local Gitea / DTU testing

Override the GitHub API and clone endpoints to run against a local Gitea sandbox or Digital Twin Universe instance:

```yaml
env:
  GITHUB_API_URL: http://localhost:3000/api/v1   # point at Gitea
  GITHUB_CLONE_URL: http://localhost:3000         # redirect clones
  ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

| Env var | Purpose |
|---------|---------|
| `GITHUB_API_URL` | Redirect GitHub REST API calls (e.g. to a local Gitea instance) |
| `GITHUB_CLONE_URL` | Redirect `git clone` calls |

### Local CLI testing

Install the `amplifier-triage` CLI to test prompts, recipes, and attractors locally without round-tripping through GitHub Actions.

**Install:**

```bash
# From this repo's checkout
uv tool install --editable .

# Or run without installing (one-off)
uv run amplifier-triage --help
```

**Run against a test event:**

```bash
ANTHROPIC_API_KEY=sk-ant-... \
GITHUB_TOKEN=ghp_...         \
amplifier-triage              \
  --recipe-source .github/amplifier/investigate-recipe.yaml \
  --event-path    ./test-event.json
```

`--event-path` defaults to `$GITHUB_EVENT_PATH`. A minimal test event:

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

## Get help setting up

First complete the provider-neutral [local setup expert installation](#local-setup-experts-provider-neutral)
from Quick Start. It carries zero always-on cost and preserves your configured provider. Normal
`amplifier run` sessions then compose the registered behavior automatically.

Activate the mode in any session, then ask naturally:

```
/github-actions
```

- *"Help me set up issue triage and PR reviews for my repo"* — produces ready-to-use workflow YAML with correct permissions, bot-comment guards, and sane default prompts.
- *"Create a .dot attractor pipeline for manager-supervisor issue investigation"* — designs the pipeline with quality gate, thread isolation, and comment-draft node.
- *"Show me the full four-workflow pattern"* — issue triage, investigation, PR review, and triage-continue with slash commands.

Three expert agents are available: `github-actions-expert` (front door — start here), `app-actions-expert` (workflow YAML), and `dot-setup-expert` (attractor pipeline design). The session routes to the right one based on your question — you don't call them directly.

For full Attractor DOT documentation, add the optional overlay described in the
[local installation instructions](#local-setup-experts-provider-neutral).

Prefer a one-off session instead of a persistent `--app` install? Run the standalone bundle
directly (no `--app`, nothing added to your registry):

```bash
amplifier run --bundle git+https://github.com/microsoft/amplifier-app-actions@main "Help me set up issue triage"
```

## Versioning

Reference the action with `@main`. To freeze a specific version, pin to a commit SHA (e.g. `microsoft/amplifier-app-actions@<sha>`).

## Security

This action is designed for private repositories. The agent's capability surface is intentionally bounded: it reads files, posts comments, and adds labels — nothing else.

> **Warning:** Never use `pull_request_target` in workflows that call this action. `pull_request_target` runs with write permissions in the context of the base branch and can expose secrets to untrusted code from a fork. Use `pull_request` only. See [Preventing pwn requests](https://securitylab.github.com/research/github-actions-preventing-pwn-requests/).

## Contributing

> [!NOTE]
> This project is not currently accepting external contributions, but we're actively working toward opening this up. We value community input and look forward to collaborating in the future. For now, feel free to fork and experiment!

Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit [Contributor License Agreements](https://cla.opensource.microsoft.com).

When you submit a pull request, a CLA bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

## Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft
trademarks or logos is subject to and must follow
[Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/legal/intellectualproperty/trademarks/usage/general).
Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship.
Any use of third-party trademarks or logos are subject to those third-party's policies.
