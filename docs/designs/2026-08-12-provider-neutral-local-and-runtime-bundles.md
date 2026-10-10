# Provider-Neutral Local Capabilities and GitHub Actions Runtime Bundles

**Date:** 2026-08-12
**Status:** Approved after self-review
**Target release:** v0.2.0
**Repository:** `microsoft/amplifier-app-actions`
**Pull request:** Replace PR #22's documentation-only correction with this structural fix

## Goal

Separate local Amplifier capabilities from GitHub Actions runtime policy so that:

- local `/pr-review` and `/github-actions` are independently installable and inherit the user's configured provider;
- GitHub Actions prompt, recipe, DTU, and reproduction execution supports Anthropic or OpenAI;
- bare `github-tools` contains no provider or model policy;
- the Action resolves exactly one provider before preparation;
- root-level child sessions cannot escape the selected provider; and
- `pr-review` names only the local review capability.

## Background

The repository currently combines three distinct surfaces:

1. local PR review through `modes/pr-review.md` and `agents/pr-review-agent.md`;
2. local GitHub Actions setup/debugging through `modes/github-actions.md` and three expert agents; and
3. GitHub Actions runtime execution through `bundles/github-tools.bundle.md`, workload bundles, and `amplifier_app_actions/wrapper.py`.

The local capabilities are conceptually provider-neutral. Local PR review reads a local diff and returns findings to the local session. Local GitHub Actions setup/debugging helps users build workflows while using the provider already configured for their Amplifier session.

The runtime architecture drifted. `github-tools` acquired an Anthropic declaration, all workload bundles inherited it, and the Action's `provider` and `model` inputs became no-ops after execution moved to in-process session creation. A user who installed the GitHub Actions `pr-review.bundle.md` with `--app` therefore composed Anthropic into every local session.

The initial PR #22 documentation fix explains cleanup but leaves the architectural defects intact. This design removes the defects.

## Problem and Root Cause

### Provider lock path

```text
local request for /pr-review
  → runtime bundles/pr-review.bundle.md installed with --app
  → runtime bundle includes bundles/github-tools.bundle.md
  → github-tools declares provider-anthropic
  → app bundle composition applies that provider to every local session
```

### Naming collision

`pr-review` currently refers to both:

- a local, stdout-oriented review mode; and
- a GitHub Actions runtime bundle that posts through GitHub API tools.

The two behaviors differ in environment, authority, outputs, and provider ownership. One name cannot represent both.

### Mode leakage

`behaviors/app-actions.yaml` is a metadata-only anchor in the repository root. Composing it makes the root `modes/` directory discoverable, so both root modes appear together. Two metadata-only anchors at the same root do not isolate discovery.

### Runtime configuration gap

The Action forwards `provider` and `model`, but the wrapper prepares the requested bundle without applying either input. Since provider lists merge instead of replace, adding an override after a provider-bearing bundle also risks two mounted providers.

### Child-provider gap

Root provider selection alone does not constrain spawned child sessions. Agent bundles and provider preferences can replace or add providers. A root-level spawn seam owned by this Action is required to preserve the invariant without changes to `amplifier-app-cli`, Amplifier Core, provider modules, or recipes.

## Goals

1. Create canonical focused directory behavior roots for local PR review and local GitHub Actions help.
2. Remove the shared root `modes/` directory.
3. Keep root agents and context addressable through `@app-actions:`.
4. Retain `behaviors/app-actions.yaml` as a deprecated provider-neutral aggregator.
5. Retain `bundles/app-actions.bundle.md` as a deprecated provider-neutral compatibility shim.
6. Make bare `github-tools` provider-neutral in v0.2.0.
7. Add exact-source Anthropic and OpenAI provider fragments with no model, credential, endpoint, or other provider policy.
8. Add explicit runnable Anthropic and OpenAI `github-tools` variants.
9. Rename GitHub Actions workloads into the `github-tools-*` family.
10. Make provider and model inputs blank by default at every boundary.
11. Resolve and validate exactly one provider entry before `prepare()`.
12. Apply an explicit model only to the selected provider entry.
13. Preserve provider source, identity, and effective model across every root-level non-Attractor spawn.
14. Exclude delegation from child tool inheritance and leave nested delegation unsupported.
15. Compose reproduction in the fixed order: capability tier, workload overlay, provider resolution, model override, prepare once.
16. Keep Attractor separate and Anthropic-only, including outer and child profiles.
17. Ship the transition in v0.2.0 and remove deprecated compatibility artifacts in v0.3.0 no sooner than 30 days after v0.2.0.
18. Update PR #22 with implementation and evidence for the structural fix.

## Non-Goals

1. OpenAI support for Attractor pipelines.
2. Nested child delegation.
3. Cross-repository changes to `amplifier-app-cli`, Amplifier Core, recipes, Foundation, or provider modules.
4. Support for more than one provider entry in an Action run.
5. Credential inference from ambient variables other than the selected provider's required credential variable.
6. Static provider-by-workload-by-runtime-tier bundle matrices.
7. A deny mechanism that removes GitHub mutation tools already supplied by a user's local parent bundle.
8. Changes to GitHub API tool behavior, token permissions, or approval policy.
9. Preservation of the ambiguous GitHub Actions path `bundles/pr-review.bundle.md`.

## Design Principles

### Capabilities do not select providers

Focused local behaviors, bare `github-tools`, workload overlays, DTU, and amplifier-dev tiers contain capability only.

### Action policy completes the runtime

The wrapper composes the fully effective non-Attractor bundle, resolves one provider entry, applies an explicit model, prepares once, creates the root session, and locks all root-level child spawns to the same provider.

### Effective post-Foundation entries determine cardinality

Provider cardinality is evaluated only on `effective_bundle.providers` after Foundation has resolved includes and composition. Foundation can merge same-module declarations that have no distinct provider identity before this point. The Action does not inventory pre-composition declarations. Same-module providers remain multiple effective entries only when distinct `id` or `instance_id` values preserve separate instances.

### Explicit failure beats silent replacement

Unsupported providers, conflicting identities, multiple entries, custom reproduction requests, child conflicts, and provider mount failures stop before the unsupported operation proceeds.

### Names expose scope and policy

- `pr-review` means local review.
- `github-actions` means local setup/debugging.
- `github-tools` means provider-neutral GitHub runtime capability.
- `github-tools-anthropic` and `github-tools-openai` name provider policy.
- GitHub workload aliases begin with `github-tools-`.
- Attractor's bundle name includes `anthropic`.

## Canonical Architecture

```text
Local Amplifier
├── behaviors/pr-review/
│   ├── bundle.yaml
│   └── modes/pr-review.md
│       └── @app-actions:agents/pr-review-agent
├── behaviors/github-actions/
│   ├── bundle.yaml
│   └── modes/github-actions.md
│       ├── @app-actions:agents/github-actions-expert
│       ├── @app-actions:agents/app-actions-expert
│       └── @app-actions:agents/dot-setup-expert
├── behaviors/github-actions-attractor.yaml
├── behaviors/app-actions.yaml                  # deprecated aggregator
└── behaviors/app-actions-attractor.yaml        # deprecated overlay shim

GitHub Actions non-Attractor runtime
├── capability tiers
│   ├── github-tools
│   ├── github-tools-dtu
│   └── github-tools-amplifier-dev
├── workload overlays
│   ├── github-tools-issue-triage
│   ├── github-tools-pr-review
│   └── github-tools-investigate
├── provider fragments
│   ├── provider-anthropic
│   └── provider-openai
├── explicit runnable variants
│   ├── github-tools-anthropic
│   └── github-tools-openai
├── provider-empty completion
│   └── provider_fragment.compose(effective_bundle)
│       └── effective bundle retains name, instruction, base_path, and resources
└── Action-owned locked session.spawn adapter

GitHub Actions Attractor runtime
└── github-tools-attractor-anthropic
    ├── outer provider-anthropic
    └── child profiles provider-anthropic
```

## Artifact Layout

```text
amplifier-app-actions/
├── bundle.md
├── behaviors/
│   ├── pr-review/
│   │   ├── bundle.yaml
│   │   └── modes/
│   │       └── pr-review.md
│   ├── github-actions/
│   │   ├── bundle.yaml
│   │   └── modes/
│   │       └── github-actions.md
│   ├── github-actions-attractor.yaml
│   ├── app-actions.yaml
│   └── app-actions-attractor.yaml
├── agents/
│   ├── pr-review-agent.md
│   ├── github-actions-expert.md
│   ├── app-actions-expert.md
│   └── dot-setup-expert.md
├── context/
├── providers/
│   ├── anthropic.yaml
│   └── openai.yaml
├── bundles/
│   ├── app-actions.bundle.md
│   ├── github-tools.bundle.md
│   ├── github-tools-anthropic.bundle.md
│   ├── github-tools-openai.bundle.md
│   ├── github-tools-dtu.bundle.md
│   ├── github-tools-amplifier-dev.bundle.md
│   ├── github-tools-issue-triage.bundle.md
│   ├── github-tools-pr-review.bundle.md
│   ├── github-tools-investigate.bundle.md
│   └── github-tools-attractor-anthropic.bundle.md
├── docs/
│   ├── designs/
│   └── examples/
├── action.yml
├── main.py
├── pyproject.toml
└── amplifier_app_actions/wrapper.py
```

The repository root `modes/` directory is deleted. Focused directory roots are the complete and validated isolation mechanism. No mode discovery override is added.

## Focused Local Directory Behaviors

### Canonical PR-review root

Files:

```text
behaviors/pr-review/bundle.yaml
behaviors/pr-review/modes/pr-review.md
```

Canonical install:

```bash
amplifier bundle add \
  'git+https://github.com/microsoft/amplifier-app-actions@main#subdirectory=behaviors/pr-review' \
  --app
```

The directory is the bundle root. Mode discovery sees only its sibling `modes/pr-review.md`. The mode keeps the shared agent reference:

```text
@app-actions:agents/pr-review-agent
```

The root `app-actions` namespace remains registered by the enclosing repository bundle, so shared root agents and context resolve without duplication.

### Canonical GitHub Actions root

Files:

```text
behaviors/github-actions/bundle.yaml
behaviors/github-actions/modes/github-actions.md
```

Canonical install:

```bash
amplifier bundle add \
  'git+https://github.com/microsoft/amplifier-app-actions@main#subdirectory=behaviors/github-actions' \
  --app
```

The directory is the bundle root. Mode discovery sees only its sibling `modes/github-actions.md`. The mode keeps these shared references:

```text
@app-actions:agents/github-actions-expert
@app-actions:agents/app-actions-expert
@app-actions:agents/dot-setup-expert
```

### Installing both

```bash
amplifier bundle add \
  'git+https://github.com/microsoft/amplifier-app-actions@main#subdirectory=behaviors/pr-review' \
  --app
amplifier bundle add \
  'git+https://github.com/microsoft/amplifier-app-actions@main#subdirectory=behaviors/github-actions' \
  --app
```

Each install contributes only its sibling mode. Installing both contributes both modes.

### Deprecated aggregator

`behaviors/app-actions.yaml` explicitly includes both directory behaviors:

```yaml
includes:
  - bundle: app-actions:behaviors/pr-review
  - bundle: app-actions:behaviors/github-actions
```

It contains no providers, session, tools, hooks, or context. Its bundle description starts with:

```text
DEPRECATED in v0.2.0; remove in v0.3.0 no sooner than 30 days after v0.2.0. Install behaviors/pr-review or behaviors/github-actions directly.
```

`bundles/app-actions.bundle.md` remains a thin shim that includes only `app-actions:behaviors/app-actions`.

`behaviors/github-actions-attractor.yaml` is the canonical optional local overlay for `dot-setup-expert`. `behaviors/app-actions-attractor.yaml` remains a deprecated shim that includes only the canonical overlay and carries the same removal schedule.

## Local PR-Review Authority Boundary

The local PR-review behavior provides these guarantees:

1. Its bundle contributes no GitHub mutation tool, GitHub mutation capability, provider, or session policy.
2. Its mode tool declaration does not add `github_post_comment`, `github_add_label`, or another GitHub mutation tool.
3. Its agent instructions require local findings output and prohibit invoking GitHub mutation tools.
4. Installing the behavior does not authorize a GitHub mutation.

A user's parent bundle can already contain GitHub mutation tools. This design does not remove parent tools and does not claim an absolute technical denial against capabilities supplied independently by the parent. The local contract is contribution-neutral and instruction-constrained. A hard deny requires a separate explicit policy mechanism and is outside this scope.

## Local Mode-Discovery Data Flow

### PR-review only

```text
install URI #subdirectory=behaviors/pr-review
  → load behaviors/pr-review/bundle.yaml as directory root
  → discover behaviors/pr-review/modes/pr-review.md
  → register /pr-review
  → resolve @app-actions:agents/pr-review-agent from repository root
  → do not scan a root modes/ directory because it does not exist
  → /github-actions remains absent
```

### GitHub Actions only

```text
install URI #subdirectory=behaviors/github-actions
  → load behaviors/github-actions/bundle.yaml as directory root
  → discover behaviors/github-actions/modes/github-actions.md
  → register /github-actions
  → resolve three @app-actions: agent references from repository root
  → do not scan a root modes/ directory because it does not exist
  → /pr-review remains absent
```

### Deprecated aggregator

```text
load behaviors/app-actions.yaml
  → include directory root behaviors/pr-review
  → include directory root behaviors/github-actions
  → discover one mode from each directory root
  → register /pr-review and /github-actions
  → add no provider or session policy
```

## Non-Attractor Runtime Composition

### Capability tiers

- `github-tools` contains Foundation, recipes, required GitHub runtime capabilities, and the three GitHub API tools. It contains zero provider entries.
- `github-tools-dtu` extends `github-tools` with Digital Twin Universe and amplifier-tester capability. It contains zero provider entries.
- `github-tools-amplifier-dev` extends `github-tools-dtu` with Amplifier development capability. It contains zero provider entries.

### Workload overlays

These built-in bundles contain workload context only and zero provider entries:

- `github-tools-issue-triage`
- `github-tools-pr-review`
- `github-tools-investigate`

The wrapper maps a built-in workload alias to a capability tier plus the corresponding workload overlay. New documentation uses built-in aliases instead of full workload file URIs.

### Provider fragments

`providers/anthropic.yaml` contains exactly:

```yaml
bundle:
  name: app-actions-provider-anthropic
  version: 0.2.0

providers:
  - module: provider-anthropic
    source: git+https://github.com/microsoft/amplifier-module-provider-anthropic@main
```

`providers/openai.yaml` contains exactly:

```yaml
bundle:
  name: app-actions-provider-openai
  version: 0.2.0

providers:
  - module: provider-openai
    source: git+https://github.com/microsoft/amplifier-module-provider-openai@main
```

The fragments omit `default_model`, API keys, endpoints, authentication choices, retry settings, and every other provider policy.

A blank `model` therefore uses the provider module's internal default. That default tracks the provider module version and can change when its source advances. This rolling-default behavior is intentional. Workflows that require model stability set `model` explicitly.

### Explicit runnable variants

- `github-tools-anthropic` includes `github-tools` plus `providers/anthropic.yaml`.
- `github-tools-openai` includes `github-tools` plus `providers/openai.yaml`.

Each variant resolves to one provider entry and remains directly runnable.

## Input Defaults and Canonical Mapping

### Blank defaults at every boundary

The v0.2.0 implementation sets both provider and model defaults to blank at every entry point:

| Boundary | Provider default | Model default |
|---|---|---|
| `action.yml` input | `''` | `''` |
| composite action environment forwarding | `''` | `''` |
| `main.py` environment fallback | `''` | `''` |
| `wrapper.run()` signature | `''` | `''` |
| `amplifier-triage --provider/--model` parser | `''` | `''` |
| tests and helper invocation defaults | `''` | `''` |

No boundary injects `anthropic` before the fully effective non-Attractor bundle is composed and inspected.

### Canonical input mapping

```text
anthropic → provider-anthropic
openai    → provider-openai
```

Input values are trimmed and lowercased. A non-empty value outside this mapping fails before bundle preparation:

```text
Unsupported provider '<value>'. Supported providers: anthropic, openai.
```

Provider entries are classified by exact `module` string. Prefix, suffix, substring, source URL, display name, and instance identity do not affect classification.

The exact module mapping also defines the canonical provider name used for default mount identity:

```text
provider-anthropic → anthropic
provider-openai    → openai
```

The provider identity fingerprint is normalized `instance_id` when present; otherwise it is this canonical provider name. The module ID is never used as the default mount identity.

## Provider Entry Normalization

The wrapper normalizes only the effective post-Foundation entries in `effective_bundle.providers`. Foundation has already resolved includes and module-list composition. The Action does not build or validate a pre-composition provider inventory.

Foundation merges same-module declarations that do not carry distinct identities. Those declarations appear as one effective entry and are validated as one. Distinct same-module instances require distinct `id` or `instance_id` values so Foundation preserves them as separate effective entries; cardinality validation then rejects the resulting count above one.

For each effective entry, the wrapper deep-copies the entry and normalizes the copy before `prepare()`:

1. `module` must be a non-empty string.
2. `id` and `instance_id`, when present, must be strings after trimming.
3. Empty `id` and empty `instance_id` are treated as absent.
4. When `id` is present and `instance_id` is absent, copy the normalized `id` value to `instance_id`.
5. When both non-empty values exist, they must match exactly.
6. Preserve the original `id` field and its metadata after copying it to `instance_id`.
7. The provider identity fingerprint is normalized `instance_id` when present; otherwise use the canonical provider name from the exact module mapping (`anthropic` or `openai`). Never use the module ID as the default identity.
8. The source comparison value is the trimmed `source`, or an empty string when absent.
9. Replace the effective entry with its normalized copy; do not append an entry.

Identity conflict error:

```text
Invalid provider entry <index>: id '<id>' and instance_id '<instance_id>' differ. Use matching provider identity values.
```

Missing module error:

```text
Invalid provider entry <index>: a non-empty module is required.
```

## Provider Resolution State Machine

Provider resolution runs after capability tier and workload composition and before model override and preparation.

### Zero provider entries

- Non-empty input: select the mapped provider fragment.
- Blank input: select `provider-anthropic` as the v0.2.0 compatibility fragment.

The compatibility default applies only in this state. It does not override a variant or custom one-provider bundle.

After confirming that the fully effective bundle is provider-empty, add the selected fragment with this exact composition direction:

```python
effective_bundle = provider_fragment.compose(effective_bundle)
```

The provider fragment is first and the effective workload/custom bundle is last. The effective bundle therefore retains its `name`, instruction, `base_path`, namespace/resource mappings, relative agent/context/tool resolution, and all other workload-owned fields while gaining the fragment's single provider entry. The opposite composition direction is forbidden because it transfers resource ownership to the fragment.

### One supported provider entry

Supported means exact module `provider-anthropic` or `provider-openai`.

- Blank input: retain the bundle entry. Provider-specific variants and supported custom one-provider bundles therefore win.
- Non-empty input mapping to the same exact module: retain the entry.
- Non-empty input mapping to the other module: fail before model override and preparation.

Conflict error:

```text
Provider conflict: bundle '<bundle>' declares '<bundle-module>' but input provider '<input>' maps to '<input-module>'. Use a provider-neutral bundle or the matching provider input.
```

### One unsupported provider entry

An entry whose exact module is neither supported module fails before model override and preparation, regardless of input:

```text
Unsupported bundle provider module '<module>' in bundle '<bundle>'. Supported modules: provider-anthropic, provider-openai.
```

The Action does not replace an unsupported custom provider with an input-selected provider.

### Multiple provider entries

Two or more effective post-Foundation entries fail before model override and preparation:

```text
Provider conflict: bundle '<bundle>' resolves to <count> effective provider entries; amplifier-app-actions requires exactly one. Entries: <module>[<provider-identity>], ...
```

Same-module declarations without distinct identities can already have merged into one effective entry and are not reconstructed or counted from source declarations. Tests that require two effective entries for the same module assign distinct `id` or `instance_id` values.

### Post-composition invariant

After provider-empty completion with `provider_fragment.compose(effective_bundle)`, the wrapper repeats normalization and cardinality validation on the resulting effective post-Foundation list. The final effective bundle must contain exactly one supported normalized provider entry. Zero, unsupported, or multiple entries are internal configuration failures and stop before `prepare()`.

## Model Override

A blank `model` leaves the selected provider entry unchanged and uses the provider module's rolling internal default.

A non-empty model:

1. is trimmed;
2. requires exactly one supported normalized effective provider entry;
3. deep-copies that selected effective entry after provider completion;
4. preserves module, source, `id`, normalized `instance_id`, and all unrelated config;
5. sets `config.default_model` to the explicit input; and
6. replaces the single effective entry in place without appending another entry.

The final provider descriptor records the effective model:

- explicit `config.default_model` when configured; or
- the mounted provider's active default from its public provider information after initialization.

If the mounted provider does not expose an active default and no explicit model exists, root initialization fails before execution:

```text
Provider model resolution failed for '<module>': no configured or mounted default model was reported. Set the Action model input explicitly.
```

## Credential and Provider Mount Errors

Credential variables are fixed by selected provider module:

```text
provider-anthropic → ANTHROPIC_API_KEY
provider-openai    → OPENAI_API_KEY
```

Before preparation, the wrapper verifies that the selected credential environment variable contains a non-empty value. It never logs the value.

Anthropic error:

```text
Missing credential for provider 'anthropic' (provider-anthropic). Set ANTHROPIC_API_KEY as a GitHub Actions secret and pass it through the workflow env block.
```

OpenAI error:

```text
Missing credential for provider 'openai' (provider-openai). Set OPENAI_API_KEY as a GitHub Actions secret and pass it through the workflow env block.
```

After root session initialization, the wrapper verifies the mounted provider using the provider identity fingerprint: normalized `instance_id` when present, otherwise canonical provider name from the exact module mapping (`anthropic` or `openai`). When the source entry supplied `id`, normalization has copied it to `instance_id` while preserving `id` metadata, so the explicit identity wins. The module ID is never used as the default mounted-provider lookup key. Mount verification, the root fingerprint, diagnostics, and the child lock use the same provider identity. If mounting failed despite a present variable, execution stops with:

```text
Provider mount failed for '<input-name>' (<module>, provider identity '<provider-identity>'). Verify <CREDENTIAL_ENV> and the provider configuration. No provider session was started.
```

The same credential checks apply to the Anthropic-only Attractor path.

## Fixed Non-Attractor Composition Order

The wrapper builds one effective bundle in this exact order:

```text
1. select capability tier
2. compose workload overlay and obtain the effective workload/custom bundle
3. let Foundation resolve includes and module-list composition
4. normalize and validate effective post-Foundation provider entries
5. when the effective provider count is zero, run provider_fragment.compose(effective_bundle)
6. re-normalize and validate exactly one supported effective provider entry
7. copy and mutate the selected effective provider entry for an explicit model
8. prepare once
9. initialize root session once
10. verify the mounted provider identity fingerprint (`instance_id` or canonical provider name)
11. install locked root session.spawn adapter
12. execute prompt or recipe
```

No provider-aware path calls `prepare()` before step 8. Prompt and recipe use the same prepared object. Step 5 keeps the effective bundle last so its name, instruction, `base_path`, and resource mappings remain authoritative.

## Reproduction Composition

### Built-in base tier

```text
bundle: github-tools + enable_reproduction: true
  → capability tier github-tools-dtu
  → no workload overlay
  → normalize effective post-Foundation provider entries
  → if provider-empty, run provider_fragment.compose(effective_bundle)
  → copy and mutate the selected effective provider entry for model override
  → prepare once
```

### Built-in workload

```text
bundle: github-tools-pr-review + enable_reproduction: true
  → capability tier github-tools-dtu
  → compose github-tools-pr-review workload overlay
  → normalize effective post-Foundation provider entries
  → if provider-empty, run provider_fragment.compose(effective_bundle)
  → copy and mutate the selected effective provider entry for model override
  → prepare once
```

The same rule applies to `github-tools-issue-triage` and `github-tools-investigate`.

### Already-DTU and amplifier-dev tiers

- `github-tools-dtu` remains `github-tools-dtu` when reproduction is enabled.
- `github-tools-amplifier-dev` remains `github-tools-amplifier-dev` when reproduction is enabled.

The operation is idempotent and does not compose a second DTU layer.

### Provider-specific variants

```text
bundle: github-tools-openai + enable_reproduction: true
  → compose capability tier github-tools-dtu
  → compose github-tools-openai variant
  → inspect the resulting one provider entry
  → retain provider-openai because input is blank
  → model override
  → prepare once
```

The Anthropic variant follows the same sequence. Duplicate capability modules merge by normal bundle module rules; provider entry count is still validated independently.

### Custom bundles

A bundle value outside the built-in alias set is custom. `enable_reproduction: true` with a custom bundle fails before loading or preparation:

```text
Unsupported reproduction composition for custom bundle '<bundle>'. Include the required reproduction capability in the custom bundle and run with enable_reproduction: false.
```

A custom bundle that owns its reproduction capability runs with `enable_reproduction: false` and proceeds through normal provider classification.

## Locked Root Spawn Invariant

### Scope

Every root non-Attractor session receives an Action-owned locked `session.spawn` adapter immediately after root initialization and before prompt or recipe execution. The implementation replaces the root capability with this adapter inside `amplifier-app-actions`; it does not modify `amplifier-app-cli`.

Recipe steps use the same root coordinator capability, so recipe child sessions pass through the same adapter.

### Root provider lock

The adapter captures one immutable descriptor from the normalized effective root entry:

```text
module
source
preserved id metadata
provider identity fingerprint (normalized instance_id or canonical provider name)
full provider config
effective model
```

When the root entry supplied `id` without `instance_id`, the prepared root entry and the lock both carry `instance_id = id` while retaining `id`. When the root entry has no `instance_id`, the lock records canonical provider name (`anthropic` or `openai`) as its identity. Root fingerprinting, mount verification, child comparison, child provider injection, and diagnostics use this same identity function; none substitute the module ID.

The effective model is materialized after root mount. A rolling provider default therefore becomes an explicit child `default_model`, ensuring all root-level children use the same model as the root run.

### Child provider rules

Before child initialization, Foundation resolves the child bundle and the adapter evaluates only the child's effective post-Foundation provider entries:

1. Child bundle has zero effective provider entries:
   - inject an exact deep copy of the locked normalized root provider entry;
   - preserve root `id` metadata, normalized `instance_id`, and provider identity fingerprint;
   - set `config.default_model` to the locked effective model.
2. Child bundle has one effective provider entry:
   - deep-copy and normalize it using the root rules, including `instance_id = id` when required;
   - derive its provider identity as normalized `instance_id` or canonical provider name;
   - require exact module, source, and provider identity fingerprint equality;
   - require its explicit model to be blank or equal to the locked effective model;
   - replace it with the locked normalized root provider entry and materialized model.
3. Child bundle has one unsupported effective provider entry:
   - fail before child preparation or initialization.
4. Child bundle has multiple effective provider entries:
   - fail before child preparation or initialization.

Same-module child declarations without distinct identities can merge during Foundation composition. Multiple-provider child tests use distinct identities so separate effective entries survive to adapter validation.

Child conflict error:

```text
Child provider conflict for '<agent>': root is <module>[<provider-identity>] from '<source>' with model '<model>', but the child requested <child-description>. Root-level child sessions must use the locked root provider.
```

### Provider preferences

- Empty provider preferences are accepted.
- One preference is accepted only when its provider maps to the locked exact module and its model is blank or equal to the locked effective model.
- More than one preference fails because it introduces fallback selection.
- A differing provider or model fails before child initialization.

Preference error:

```text
Child provider preference conflict for '<agent>': requested '<preference>' but the root provider lock is <module>[<provider-identity>] with model '<model>'.
```

### Delegation exclusion

Before child preparation, the locked adapter removes tool configuration and inheritance entries whose module ID is `tool-delegate` or `tool-task`. `delegate` is the mounted tool name, not a pre-mount module ID, so it is used only for post-initialization verification.

After child initialization, the adapter verifies that the child exposes no mounted tool named `delegate` and no `session.spawn` capability. Failure of either check aborts the child before it executes user instructions. A child therefore cannot initiate another spawn that bypasses the root adapter.

Nested delegation is unsupported in v0.2.0 and remains outside this design.

## Attractor Boundary

Attractor remains a separate runtime bundle:

```text
bundles/github-tools-attractor-anthropic.bundle.md
```

It retains `provider-anthropic` in:

- the outer pipeline session;
- `pipeline-agent-anthropic`; and
- `pipeline-agent-commenter`.

Attractor input rules:

- blank provider selects Anthropic;
- `provider: anthropic` selects Anthropic;
- `provider: openai` fails before Attractor bundle loading or preparation;
- unsupported provider input fails through the common input mapping error;
- blank model leaves all Anthropic declarations on their internal rolling default;
- explicit model sets `config.default_model` on the outer provider and every Anthropic child profile before preparation.

OpenAI error:

```text
Attractor execution supports provider 'anthropic' only in v0.2.0. Use provider: anthropic, or use prompt/recipe execution for OpenAI.
```

Attractor uses its existing pipeline-specific spawn adapter. The locked non-Attractor adapter is not composed into the pipeline runtime.

## Naming and Migration

| v0.1.x artifact | v0.2.0 artifact or status | v0.2.0 behavior |
|---|---|---|
| root `modes/pr-review.md` | `behaviors/pr-review/modes/pr-review.md` | Root mode removed; focused directory root only. |
| root `modes/github-actions.md` | `behaviors/github-actions/modes/github-actions.md` | Root mode removed; focused directory root only. |
| `behaviors/app-actions.yaml` | retained deprecated aggregator | Explicitly includes both directory roots; no provider/session policy. |
| `behaviors/app-actions-attractor.yaml` | retained deprecated shim | Includes only `behaviors/github-actions-attractor.yaml`. |
| `bundles/app-actions.bundle.md` | retained deprecated shim | Includes only `app-actions:behaviors/app-actions`. |
| provider-bearing `github-tools.bundle.md` | provider-neutral `github-tools.bundle.md` | Provider removed immediately in v0.2.0. |
| none | `providers/anthropic.yaml` | Exact-source provider fragment without model or credentials. |
| none | `providers/openai.yaml` | Exact-source provider fragment without model or credentials. |
| none | `github-tools-anthropic.bundle.md` | Explicit runnable Anthropic variant. |
| none | `github-tools-openai.bundle.md` | Explicit runnable OpenAI variant. |
| `issue-triage.bundle.md` | `github-tools-issue-triage.bundle.md` | Built-in workload overlay name. |
| `pr-review.bundle.md` | `github-tools-pr-review.bundle.md` | Old path removed; no shim. |
| `investigate.bundle.md` | `github-tools-investigate.bundle.md` | Built-in workload overlay name. |
| `github-tools-dtu.bundle.md` | same path | Provider-neutral and idempotent under reproduction. |
| `github-tools-amplifier-dev.bundle.md` | same path | Provider-neutral and idempotent under reproduction. |
| `attractor-pipeline.bundle.md` | `github-tools-attractor-anthropic.bundle.md` | Old built-in alias retained with runtime warning until v0.3.0. |
| Action provider default `anthropic` | blank | Compatibility default applied only after zero-provider effective bundle inspection. |
| Action model default blank | blank | Explicit model targets selected provider; blank uses rolling module default. |

The old workload files `issue-triage.bundle.md`, `pr-review.bundle.md`, and `investigate.bundle.md` are removed in v0.2.0. Keeping `pr-review.bundle.md` would preserve the naming collision, so no workload-path shim is retained.

## Version and Deprecation Policy

### v0.2.0 transition

The implementation updates:

- `pyproject.toml` project version to `0.2.0`;
- root bundle metadata when changed;
- every changed behavior metadata version to `0.2.0`;
- every changed runtime bundle metadata version to `0.2.0`; and
- new provider fragment metadata version to `0.2.0`.

Bare `github-tools` becomes provider-neutral in v0.2.0.

### Retained legacy compatibility artifacts

The following artifacts remain through the v0.2.x line:

1. `behaviors/app-actions.yaml`
2. `behaviors/app-actions-attractor.yaml`
3. `bundles/app-actions.bundle.md`
4. built-in alias `attractor-pipeline`, which resolves to `github-tools-attractor-anthropic`

The three file-based shims carry `DEPRECATED` in metadata/body with the v0.3.0 removal rule. The wrapper writes this warning to GitHub Actions logs when `attractor-pipeline` is selected:

```text
::warning::Bundle alias 'attractor-pipeline' is deprecated in v0.2.0; use 'github-tools-attractor-anthropic'. It is removed in v0.3.0 no sooner than 30 days after v0.2.0.
```

### v0.3.0 removal

v0.3.0 removes all four retained compatibility artifacts no sooner than 30 calendar days after the v0.2.0 release date. No earlier release removes them.

### Local cleanup commands

Users remove stale and deprecated local app registrations by the registered names present in their configuration:

```bash
amplifier bundle remove pr-review --app
amplifier bundle remove app-actions-behavior --app
amplifier bundle remove app-actions-legacy --app
amplifier bundle remove app-actions-attractor --app
```

They then install one or both focused directory roots:

```bash
amplifier bundle add \
  'git+https://github.com/microsoft/amplifier-app-actions@main#subdirectory=behaviors/pr-review' \
  --app
amplifier bundle add \
  'git+https://github.com/microsoft/amplifier-app-actions@main#subdirectory=behaviors/github-actions' \
  --app
```

README migration text states that users run only the removal commands matching installed registrations.

## Documentation Surfaces

The v0.2.0 change updates all surfaces that teach names, provider policy, spawn policy, reproduction, or migration:

1. `README.md`
   - focused local install choices and combined install;
   - cleanup commands;
   - retained deprecations and dates;
   - blank provider/model defaults;
   - explicit Anthropic and OpenAI workflow examples;
   - rolling model default warning;
   - built-in workload aliases;
   - custom reproduction error contract;
   - locked root child-provider behavior;
   - Anthropic-only Attractor boundary.
2. `bundle.md`
3. focused directory behavior bundle files and mode files
4. deprecated behavior shims
5. every runtime bundle and provider fragment
6. `agents/pr-review-agent.md`
7. `agents/github-actions-expert.md`
8. `agents/app-actions-expert.md`
9. `agents/dot-setup-expert.md`
10. all files under `docs/examples/`
11. `docs/designs/2026-05-17-amplifier-bundle-dev-support.md`, marked superseded by this specification
12. `.github/workflows/` self-tests and examples
13. `action.yml`
14. `main.py`
15. wrapper docstrings and CLI help
16. tests that encode v0.1.x names or provider behavior
17. `pyproject.toml` version
18. generated `bundle.dot` and `bundle.png`

New workflow examples set provider explicitly even though the zero-provider compatibility path defaults to Anthropic in v0.2.0.

## Test Strategy

### Test-driven sequence

Each production behavior starts with a failing test that demonstrates the v0.1.x defect. The test is observed failing for the intended reason, then the minimum implementation makes it pass.

### Directory-root isolation tests

Use actual Foundation loading and mode discovery:

| Loaded root | `/pr-review` | `/github-actions` | Shared agent resolution |
|---|---:|---:|---:|
| `behaviors/pr-review` | present | absent | `@app-actions:agents/pr-review-agent` resolves |
| `behaviors/github-actions` | absent | present | all three setup agents resolve |
| both focused roots | present | present | all references resolve |
| deprecated aggregator | present | present | all references resolve |

Additional assertions:

- repository root `modes/` does not exist;
- focused behavior files contain no provider/session/GitHub mutation contributions;
- PR-review mode does not contribute GitHub mutation tools;
- aggregator includes exactly the two focused directory roots.

### Provider fragment structural tests

- Anthropic fragment has one `provider-anthropic` entry and the exact source URL.
- OpenAI fragment has one `provider-openai` entry and the exact source URL.
- Both fragments omit config, model, credentials, endpoint, and authentication policy.
- Bare `github-tools`, workload overlays, DTU, and amplifier-dev have zero provider entries.
- Explicit variants resolve to one provider entry.

### Provider resolution matrix

| Effective bundle entries | Input | Result |
|---:|---|---|
| 0 | blank | compose Anthropic compatibility fragment |
| 0 | `anthropic` | compose Anthropic fragment |
| 0 | `openai` | compose OpenAI fragment |
| 1 `provider-anthropic` | blank | retain Anthropic entry |
| 1 `provider-openai` | blank | retain OpenAI entry |
| 1 `provider-anthropic` | `anthropic` | retain one entry |
| 1 `provider-openai` | `openai` | retain one entry |
| 1 `provider-anthropic` | `openai` | conflict error before prepare |
| 1 `provider-openai` | `anthropic` | conflict error before prepare |
| 1 unsupported | blank or explicit | unsupported bundle provider error |
| same-module declarations without distinct identities | any | Foundation merges them; validate the resulting effective entry only |
| 2 same-module effective entries with distinct `id`/`instance_id` values | any | multiple-entry error |
| 2 different-module effective entries | any | multiple-entry error |
| effective entry without module | any | invalid-entry error |
| one Anthropic entry without `id`/`instance_id` | matching or blank | provider identity is canonical name `anthropic` |
| one OpenAI entry without `id`/`instance_id` | matching or blank | provider identity is canonical name `openai` |
| one entry with `id` only | matching or blank | copy `id` to `instance_id`, preserve `id`, use that identity |
| one entry with equal `id`/`instance_id` | matching or blank | preserve both, use normalized `instance_id` identity |
| one entry with differing `id`/`instance_id` | any | identity error |
| unsupported input | any | unsupported-input error |

Every error-path test asserts that `prepare()` and root initialization were not called.

### Model and resource-ownership tests

- blank model leaves provider config unchanged;
- explicit model copies and writes only `config.default_model` on the selected normalized effective entry;
- unrelated config plus preserved `id` and normalized `instance_id` survive;
- no provider entry is appended;
- rolling default is read from mounted provider information;
- missing mounted default with blank input produces the specified resolution error;
- provider-empty completion calls `provider_fragment.compose(effective_bundle)` in that direction;
- the completed built-in workload retains its name, instruction, `base_path`, agents, context, tools, and namespace/resource mappings;
- a provider-empty custom bundle with relative context, agent, tool, and instruction resources retains the custom `base_path` and resolves every relative resource after provider completion; and
- the reverse composition direction is rejected by a regression test because it would transfer bundle/resource ownership to the fragment.

### Credential and mount tests

| Selected provider | Missing variable | Expected error reference |
|---|---|---|
| Anthropic | `ANTHROPIC_API_KEY` | exact Anthropic missing-credential message |
| OpenAI | `OPENAI_API_KEY` | exact OpenAI missing-credential message |
| Anthropic | present but provider absent after init | mount-failure message names `ANTHROPIC_API_KEY` |
| OpenAI | present but provider absent after init | mount-failure message names `OPENAI_API_KEY` |

Tests assert that secret values never appear in logs or exceptions. A provider entry with `id` and no `instance_id` is verified as mounted under the copied `instance_id`, and the final normalized entry still contains the original `id` metadata. A default Anthropic entry with no identity fields is verified under mounted name `anthropic`; a default OpenAI entry is verified under `openai`. Negative tests prove that `provider-anthropic` and `provider-openai` are not accepted as fallback mounted names.

### Composition and reproduction matrix

| Bundle class | Reproduction | Expected composition |
|---|---:|---|
| `github-tools` | false | github-tools → post-Foundation normalize → fragment-first completion if empty → model-copy override → prepare |
| `github-tools` | true | github-tools-dtu → post-Foundation normalize → fragment-first completion if empty → model-copy override → prepare |
| built-in workload | false | github-tools → workload → post-Foundation normalize → fragment-first completion if empty → model-copy override → prepare |
| built-in workload | true | github-tools-dtu → same workload → post-Foundation normalize → fragment-first completion if empty → model-copy override → prepare |
| github-tools-dtu | true | one DTU tier → post-Foundation normalize → fragment-first completion if empty → model-copy override → prepare |
| github-tools-amplifier-dev | true | one amplifier-dev tier → post-Foundation normalize → fragment-first completion if empty → model-copy override → prepare |
| provider variant | false | variant → post-Foundation normalize → retain one provider → model-copy override → prepare |
| provider variant | true | github-tools-dtu + variant → post-Foundation normalize → retain one provider → model-copy override → prepare |
| custom bundle | false | custom bundle → preserve custom ownership → post-Foundation normalize → fragment-first completion if empty → model-copy override → prepare |
| custom bundle | true | unsupported-composition error before load/prepare |

Each success test asserts one `prepare()` call and one root initialization call.

### Locked spawn tests

| Child request | Expected result |
|---|---|
| zero effective providers | exact root module/source/id/instance_id/provider-identity/effective-model fingerprint injected |
| default Anthropic child without identity fields | canonical provider identity `anthropic` matches root default identity |
| default OpenAI child without identity fields | canonical provider identity `openai` matches root default identity |
| one exact provider with `id` only | copy child `id` to `instance_id`, preserve `id`, use that provider identity, then accept |
| one exact provider, blank child model | root locked model materialized |
| one exact provider, same model | accepted and canonicalized to normalized root entry |
| different module | conflict before child init |
| same module, different source | conflict before child init |
| same module/source, different normalized instance identity | conflict before child init |
| same provider, different model | conflict before child init |
| unsupported provider | conflict before child init |
| multiple same-module effective entries with distinct identities | conflict before child init |
| multiple different-module effective entries | conflict before child init |
| empty preferences | accepted |
| one exact preference | accepted |
| conflicting preference | rejected before child init |
| multiple preferences | rejected before child init |

Additional assertions:

- prompt delegation uses the locked adapter;
- recipe steps use the same root adapter;
- pre-mount child tool configuration and inheritance exclude module IDs `tool-delegate` and `tool-task`;
- post-initialization child tools contain no mounted tool named `delegate`;
- child coordinator has no nested `session.spawn` capability;
- root fingerprinting and mount verification use normalized `instance_id` when present, otherwise canonical provider name (`anthropic` or `openai`), and retain `id` metadata; and
- no cross-repository patch is required.

### Attractor tests

- blank provider selects Anthropic;
- explicit Anthropic selects Anthropic;
- OpenAI produces the exact pre-load error;
- missing `ANTHROPIC_API_KEY` produces the exact credential error;
- explicit model reaches outer provider and both child profiles;
- blank model leaves all three provider configs without `default_model`;
- old alias writes the exact deprecation warning and resolves to the new bundle;
- non-Attractor locked spawn code is not installed in the pipeline runtime.

### Documentation tests

Assert canonical commands and aliases:

- directory install URI for PR review;
- directory install URI for GitHub Actions;
- explicit combined installation;
- all cleanup commands;
- v0.2.0/v0.3.0 and 30-day policy;
- Anthropic and OpenAI workflows;
- blank input defaults;
- rolling model default statement;
- no recommended old workload paths;
- custom reproduction error guidance;
- precise local PR-review authority boundary;
- explicit Anthropic-only Attractor statement.

### DTU validation

Validate branch contents in an isolated Digital Twin Universe:

1. Anthropic prompt run;
2. OpenAI prompt run;
3. Anthropic recipe run with a root child spawn;
4. OpenAI recipe run with a root child spawn;
5. built-in workload reproduction with Anthropic;
6. built-in workload reproduction with OpenAI;
7. provider-specific variant plus reproduction;
8. custom bundle reproduction rejection;
9. child provider conflict rejection; and
10. OpenAI Attractor rejection.

Evidence records final provider module, source, preserved `id`, normalized `instance_id` when present, provider identity fingerprint (`instance_id` or canonical provider name), effective model, effective post-Foundation provider entry count, effective bundle name/`base_path`, prepare count, and spawn result.

### Full and live verification

Before PR #22 is presented for merge:

- formatting, linting, type checking, focused tests, bundle validation, and full suite pass;
- live Anthropic GitHub Actions prompt/workload run passes;
- live OpenAI GitHub Actions prompt/workload run passes;
- live recipe spawn path proves the locked provider invariant;
- live Anthropic Attractor self-test passes; and
- logs prove exactly one provider mounted without printing credentials.

## Risks and Mitigations

| Risk | Consequence | Mitigation |
|---|---|---|
| Focused mode files still share a discovery root | Installing one exposes both | Use directory bundle roots with sibling `modes/`; delete root `modes/`; integration-test actual discovery. |
| Root namespace references stop resolving after mode move | Expert agents fail to load | Keep `@app-actions:` references and test them through Foundation loading. |
| Blank input is converted to Anthropic too early | OpenAI variant/custom bundle is overridden | Keep every boundary blank; apply compatibility default only after effective bundle provider count is zero. |
| Fragments pin a stale model | Model choice silently freezes | Omit model config; document rolling provider-module default; set explicit model for stability. |
| Same-module declarations merge before validation | A source-level duplicate is mistaken for two effective providers | Define cardinality only over post-Foundation entries; use distinct identities in multiple-instance tests; do not inventory pre-composition declarations. |
| `id` exists without `instance_id` | Mount and child lookup use different identities | Copy normalized `id` to `instance_id` before prepare, preserve `id`, and use normalized `instance_id` for mount/child checks. |
| `id` and `instance_id` disagree | Root/child identity changes across layers | Fail before prepare when both non-empty values differ. |
| Provider fragment becomes the resource owner | Custom relative resources resolve from the fragment path | Compose exactly `provider_fragment.compose(effective_bundle)` and test name, instruction, `base_path`, and resource mappings. |
| Default mount identity falls back to module ID | Default providers are looked up under names they never mount with | Use normalized `instance_id` when present; otherwise use canonical provider name (`anthropic` or `openai`) for root fingerprinting, mount verification, child locks, and diagnostics. |
| Child agent overrides provider | Root and child run on different provider/model | Install Action-owned locked root spawn adapter and validate effective child entries before child initialization. |
| Nested child delegation bypasses lock | Grandchild escapes provider invariant | Remove pre-mount module IDs `tool-delegate` and `tool-task`, then verify no mounted `delegate` tool and no child spawn capability. |
| Recipe uses a separate spawn seam | Recipe children escape lock | Register one root adapter before recipe tool execution and test recipe steps through it. |
| Reproduction loses workload context | DTU run performs the wrong job | Compose capability tier first, then the same workload overlay. |
| DTU tier is duplicated | Conflicting capability state | Treat DTU and amplifier-dev tiers idempotently and assert one tier composition. |
| Custom reproduction is guessed incorrectly | Broken or unsafe custom composition | Reject custom bundle plus reproduction and provide the exact corrective action. |
| OpenAI enters pipeline child profiles | Mixed provider pipeline fails late | Reject OpenAI before Attractor load and keep model override Anthropic-wide. |
| Local PR review is described as an absolute deny | Contract exceeds mechanism | State contribution and authorization limits; acknowledge parent-supplied tools. |
| Deprecations linger indefinitely | Permanent compatibility complexity | Release in v0.2.0; remove in v0.3.0 after at least 30 days; name every retained artifact. |
| Old workload path remains discoverable | `pr-review` stays ambiguous | Remove old workload files in v0.2.0 and provide exact migration names. |
| Cross-repository changes become a hidden dependency | Fix cannot ship atomically | Implement provider completion and spawn lock entirely in this Action repository. |

## Success Criteria

The change is complete only when all statements below are proven:

1. `behaviors/pr-review` exposes `/pr-review` and not `/github-actions`.
2. `behaviors/github-actions` exposes `/github-actions` and not `/pr-review`.
3. Root `modes/` is removed.
4. Shared `@app-actions:` agent and context references resolve from both directory roots.
5. Deprecated aggregator exposes both modes and contributes no provider/session policy.
6. Local PR-review contributes no GitHub mutation tool or capability and authorizes only local output.
7. Bare `github-tools` has zero provider entries in v0.2.0.
8. Provider fragments have exact module/source pairs and no config policy.
9. Provider and model defaults are blank at every boundary.
10. Anthropic compatibility default applies only to a fully effective zero-provider non-Attractor bundle.
11. OpenAI variants and supported custom one-provider bundles win when input is blank.
12. Provider cardinality is evaluated only on effective post-Foundation entries; same-module multiple-instance tests use distinct identities.
13. An `id` without `instance_id` is copied to `instance_id` before prepare, `id` metadata remains present, and differing values fail.
14. Zero, supported one, unsupported one, effective multiple, input conflict, and identity conflict states produce the specified outcomes.
15. Missing credentials and provider mount failure name the correct credential variable and provider identity fingerprint; default identities are `anthropic` and `openai`, never module IDs, and no secret value is exposed.
16. Explicit model overrides only a copied selected effective entry; blank model uses the rolling provider default.
17. Provider-empty completion uses `provider_fragment.compose(effective_bundle)` and preserves effective name, instruction, `base_path`, resource mappings, and relative custom resources.
18. Prompt and recipe prepare exactly once from the same fixed composition order.
19. Built-in workload reproduction composes DTU plus the same workload.
20. DTU and amplifier-dev reproduction are idempotent.
21. Provider variants compose with DTU and validate normally.
22. Custom bundle plus reproduction fails with the exact unsupported-composition error.
23. The locked root spawn adapter preserves exact provider module, source, preserved `id`, normalized `instance_id` when present, canonical-name fallback identity when absent, and effective model; module ID is never the fallback identity.
24. Recipe child sessions use the same adapter.
25. Pre-mount child configuration excludes `tool-delegate` and `tool-task`; initialized children expose no `delegate` tool and no `session.spawn` capability.
26. Attractor remains Anthropic-only and explicit model reaches outer and child profiles.
27. v0.2.0 versions, deprecations, warnings, cleanup commands, and v0.3.0/30-day removal rule are documented and tested.
28. README and examples show focused local installs plus Anthropic/OpenAI GitHub Actions choices.
29. Focused tests, full suite, DTU evidence, live Anthropic/OpenAI evidence, and live Anthropic Attractor evidence pass.
30. PR #22 contains the structural implementation and complete evidence.

## Implementation Task Breakdown

The work remains organized as 27 ordered tasks.

1. **Lock the revised specification.** Use this document as the implementation contract for PR #22.
2. **Inventory every v0.1.x reference.** Enumerate root modes, behavior URIs, workload files, provider defaults, CLI defaults, aliases, examples, agents, workflows, tests, and metadata versions.
3. **Write failing directory-root isolation tests.** Require the two canonical directories, sibling modes, no root `modes/`, and shared root agent resolution.
4. **Write failing local authority tests.** Require zero provider/session/GitHub mutation contributions from focused PR review and local-output agent constraints.
5. **Write failing legacy shim tests.** Require exact aggregator includes, overlay shim include, bundle shim include, deprecation text, v0.2.0 metadata, v0.3.0 removal, and 30-day floor.
6. **Write failing provider fragment tests.** Require exact module/source pairs and no provider config policy.
7. **Write failing provider-neutral tier/workload tests.** Require zero providers in bare core, DTU, amplifier-dev, and workload overlays.
8. **Write failing blank-boundary tests.** Require blank provider/model defaults in Action YAML, environment fallback, wrapper signature, CLI parser, and helpers.
9. **Write failing provider state-machine tests.** Cover exact input mapping, unsupported input, zero, supported one, unsupported one, post-Foundation effective counts, same-module merging without identity, same-module effective instances with distinct identities, different-module entries, no pre-composition inventory, and prepare-not-called errors.
10. **Write failing identity normalization tests.** Cover absent, equal, differing, empty, and invalid `id`/`instance_id` values; require `instance_id = id` before prepare, preserved `id` metadata, canonical fallback identity `anthropic`/`openai`, and rejection of module-ID fallback.
11. **Write failing model/resource-ownership tests.** Cover rolling default, explicit override on a copied selected effective entry, config preservation, one-entry replacement, missing mounted default, exact `provider_fragment.compose(effective_bundle)` direction, and relative custom resource/`base_path` preservation.
12. **Write failing credential/mount tests.** Cover both credential variables, missing values, mount absence, explicit normalized `instance_id` lookup, default canonical-name lookup, negative module-ID lookup, preserved `id`, exact errors, and secret redaction.
13. **Write failing reproduction composition tests.** Cover base, workload, DTU, amplifier-dev, provider variants, custom rejection, post-Foundation provider validation, resource ownership, fixed order, idempotence, and one prepare call.
14. **Write failing locked-spawn tests.** Cover root fingerprint capture using normalized `instance_id` or canonical provider name, preserved `id`, neutral child injection, exact child acceptance, effective child counts with distinct identities, provider/source/identity/model conflicts, preference conflicts, recipe seam, and pre-init failure.
15. **Write failing delegation exclusion tests.** Require pre-mount removal of module IDs `tool-delegate` and `tool-task`, no mounted child tool named `delegate`, and no child `session.spawn` capability.
16. **Write failing Attractor boundary tests.** Cover Anthropic selection, OpenAI rejection, credential error, outer/child model override, and deprecated alias warning.
17. **Create focused directory bundle roots.** Add both `bundle.yaml` files, move modes beside them, preserve `@app-actions:` references, and delete root `modes/`.
18. **Convert local compatibility artifacts.** Make the aggregator include both directories, create the canonical GitHub Actions Attractor overlay, retain exact shims, and add deprecation text.
19. **Neutralize runtime capability artifacts.** Remove Anthropic from bare core, add exact-source fragments, add runnable provider variants, and keep tiers provider-neutral.
20. **Rename workload and Attractor artifacts.** Create `github-tools-*` workload overlays, remove old workload files, rename the Anthropic Attractor bundle, and retain only the specified alias warning.
21. **Implement the provider state machine.** Evaluate post-Foundation effective entries only, normalize `id` to `instance_id` while preserving `id`, derive provider identity from `instance_id` or exact canonical-name mapping, count surviving effective entries, classify exact modules, resolve blank input, apply compatibility default only for zero entries with `provider_fragment.compose(effective_bundle)`, validate conflicts, and prepare once.
22. **Implement model, credentials, mount verification, and resource ownership.** Copy the selected effective provider entry for explicit model mutation, preserve effective name/instruction/`base_path`/resource mappings, resolve rolling mounted default, preflight credential env, and verify the mounted provider by normalized `instance_id` or canonical provider name while rejecting module-ID fallback.
23. **Implement fixed capability/workload/reproduction composition.** Enforce the exact order, post-Foundation validation, idempotent built-in tiers, provider-variant composition, relative custom resource preservation, and custom reproduction rejection.
24. **Implement the locked non-Attractor spawn adapter.** Preserve root provider/source/`id`/`instance_id`/provider-identity/model fingerprint, use canonical provider name when `instance_id` is absent, validate effective child entries and preferences, route recipe steps through it, remove pre-mount `tool-delegate` and `tool-task`, then verify no mounted `delegate` and no child `session.spawn`.
25. **Update versions and documentation.** Set changed package/bundle/behavior metadata to 0.2.0; rewrite README, bundle bodies, agents, examples, workflows, stale design references, cleanup guidance, and generated bundle docs.
26. **Run complete local and isolated verification.** Run formatting, linting, type checks, focused tests, full suite, bundle validation, and the full DTU matrix; resolve every load-bearing finding.
27. **Run live evidence and update PR #22.** Prove Anthropic, OpenAI, locked recipe spawn, reproduction, and Anthropic Attractor in live GitHub Actions; attach exact evidence and present the structural PR for merge approval.

## Final Decision

v0.2.0 introduces two isolated local directory behaviors, a provider-neutral runtime core, exact-source policy-light provider fragments, post-Foundation effective-entry validation, pre-prepare identity normalization with canonical provider-name fallback (`anthropic`/`openai`) and no module-ID fallback, ownership-preserving `provider_fragment.compose(effective_bundle)` completion, fixed reproduction composition, and an Action-owned locked spawn seam. `pr-review` means local review. GitHub runtime workloads use `github-tools-*`. Provider/model inputs stay blank until the effective bundle is inspected. Child inheritance removes `tool-delegate` and `tool-task`, and initialized children expose neither mounted `delegate` nor `session.spawn`. Attractor remains explicitly Anthropic-only. Deprecated local shims and the old Attractor alias survive only until v0.3.0, released no sooner than 30 days after v0.2.0.
