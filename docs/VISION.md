# Amplifier App Actions — Vision (DRAFT)

The end state this project converges toward, written as though already true. This page
is never edited to record what shipped; that belongs in issues and release records. It
changes by amendment first — a dated row in the changelog carrying the evidence — and
work is derived from the gap afterwards, never the other way round. Specific promises
about runtime selection and compatibility live in `contracts/` and are not repeated here.

## What Amplifier App Actions is

Amplifier App Actions is a standard GitHub Action that bridges a workflow to one
unattended Amplifier run. A workflow author declares intent with a natural-language
prompt or declares structure with a graph, then supplies the Amplifier configuration,
credentials, permissions, dependencies, and runner environment that the work needs. The
action translates that declaration into a run without changing its meaning or authority
and returns a terminal result through the ordinary GitHub Actions experience.

## Principles

### 1. Work has intent or structure

A prompt expresses work when the desired outcome matters more than the exact path. A
graph expresses work when stages, branches, checks, or completion conditions must be
explicit. These two forms rule out a fixed catalog of named jobs and rule out hiding a
structured process inside an ever-longer prompt.

### 2. The workflow supplies the runtime

The workflow author chooses and supplies the workload configuration, provider and model,
credentials, permissions, dependencies, workspace, and runner environment. The action
owns the adapter needed to launch that workload, not a managed AI environment. This
rules out an action that silently chooses a vendor, model, reviewer, bundle, or authority
because one happened to work when the action was written.

### 3. The bridge preserves the declaration

The action preserves the declared work, supplied configuration, and limits of authority
while translating a GitHub invocation into an Amplifier run. It validates and maps only
what its contracts permit. An unavailable or incompatible choice produces a visible
failure instead of a quiet substitution that makes the run mean something else.

### 4. Every run is unattended

A run begins with all of its work and runtime inputs available from the GitHub job and
ends inside that job with a result or a clear failure. It never pauses for conversation,
clarification, approval, or later human input. A requirement for a person's decision
fails visibly rather than bypassing the decision or preserving a hidden session; later
human follow-up begins a new GitHub event and a new run.

### 5. The action is the integration point

Workflow authors operate the bridge through standard GitHub Actions YAML, inputs,
environment variables, secrets, permissions, steps, status, outputs, logs, and artifacts.
Amplifier-specific workload configuration remains theirs, while the action absorbs the
adapter work required to honor its public contract. This rules out a second control
plane, credential store, installer, or lifecycle beside GitHub Actions.

### 6. Dependencies serve stable capabilities

Providers, models, bundles, agents, reviewers, and orchestration engines may advance or
be replaced without redefining what the action promises. A dependency is adopted only
behind a named capability and an observable compatibility check. This rules out making a
fast-moving implementation name part of the product merely because it is today's best
choice, and it rules out assuming that a moving branch will remain compatible by luck.

## What this deliberately resists

- **A managed AI runtime.** Provider service, model access, credentials, and workload
  configuration belong to the workflow author and the services they choose.
- **An interactive session.** Interactive work belongs in an interactive Amplifier host;
  a GitHub follow-up is a new event and an independent unattended run.
- **A parallel operating model.** GitHub Actions owns orchestration, authority, secrets,
  and run observation; Amplifier configuration describes only the Amplifier workload.
- **A permanent dependency catalog.** Current providers, models, bundles, reviewers, and
  graph formats belong in versioned contracts or examples, not in the enduring vision.
- **A menu of named jobs.** Workflow authors own task intent; examples may demonstrate
  triage or review without making those examples the boundary of the action.
- **A general automation framework.** GitHub Actions and other actions own automation
  unrelated to invoking Amplifier; this project remains the bridge to Amplifier work.

## How you can tell it is working

- A **workflow author** completes **2 representative runs** — one prompt-driven and one
  graph-driven — through the action without operating a separate orchestration service.
- A **maintainer** observes **0 silent substitutions across 6 failure fixtures**:
  malformed, unavailable, unsupported, human-input, timeout, and cancellation.
- A **security reviewer** observes **0 approval bypasses in 1 human-input fixture**;
  that fixture ends with a failing GitHub Actions status.
- A **workflow operator** finds **1 terminal status and 1 named cause for every run** across
  the successful run and all **6 failure fixtures**.
- A **workflow author** sees **0 credential values** in the resolution record, logs, and
  uploaded artifacts for both representative runs.
- A **maintainer** advances **1 fast-moving dependency** while both representative runs
  keep their public action shape and receive fresh compatibility verdicts.

## Changelog

| Date | Change | Evidence |
|---|---|---|
| 2026-10-07 | Drafted the bridge, ownership, unattended-run, GitHub-native, and stable-capability direction. | Steward's stated intent; current defaults silently select Anthropic and named reviewer/bundle implementations that have already aged. |
