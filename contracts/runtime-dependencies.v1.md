# Runtime Dependencies Contract — v1 (DRAFT)

How workflow-owned choices and action-owned adapters produce an observable Amplifier run.

## Who builds against this

**Workflow authors** supply workload choices and authority. **Action maintainers** ship the
adapter and its tested dependency matrix. **Workflow operators** read resolution and result
records. None may treat an implementation default as an agreed choice.

## What it is

A request names one work form and every fast-moving workload choice: configuration bundle,
provider, and model. Credentials arrive through the workflow environment. The action resolves
the author's complete bundle graph, probes that runtime during the run, and separately records
its own adapter dependencies. Four capabilities govern v1: `intent-run` completes one prompt;
`structured-run` completes one graph; `bounded-authority` stays inside declared authority; and
`terminal-result` ends with a GitHub status and named cause.

```yaml
request:
  work: {form: intent, source: prompt} # form may instead be structured
  workload: {bundle: owner/repo@ref:path, provider: provider-id, model: model-id}
  authority: {permissions: read, credentials: [PROVIDER_API_KEY]}
resolution:
  workload: {bundle_graph_digest: sha256:..., provider: provider-id, model: model-id, identity: mutable}
  adapter: {action: owner/repo@sha, engine: package@version, provider_adapter: package@version}
  capabilities: [intent-run, bounded-authority, terminal-result]
result: {status: success, reason: completed, contract: runtime-dependencies.v1}
```

An incompatible result has `status: failure` and one reason: `missing`, `malformed`,
`unavailable`, `unsupported`, `human-input-required`, `timeout`, or `cancelled`.

## The promises

1. **Workload choices are explicit.** Bundle, provider, and model have no action-selected
   default. Omit one and the author sees `missing` before work starts. Credentials remain
   environment-owned and are recorded only by variable name, never by value.

2. **Author choices are probed.** Custom and private workload choices do not need a maintainer
   allowlist. Each run resolves the full bundle dependency graph, checks provider and model
   availability, then observes the requested work capability. A failed probe produces its
   named result instead of a claim of compatibility.

3. **Adapter compatibility is released.** Maintainer CI proves every adapter matrix row against
   all four capabilities before releasing the action. A row contains the immutable action
   revision plus engine, provider-adapter, GitHub-tool, and graph-runner identities. Movement
   in any row member requires a fresh verdict; an untested row is not released.

4. **Records identify what ran.** The action writes the request and resolution to the step
   summary before execution, then appends exactly one result. A missing workload-graph digest,
   adapter identity, contract name, terminal status, or reason makes the step fail rather than
   leaving the operator with an unverifiable green run.

5. **Substitution is never implicit.** Unavailable or unsupported choices fail by name. The
   action does not replace a bundle, provider, model, reviewer, graph runner, or authority.
   v1 has no fallback path, and a transitive dependency change produces a new graph digest.

6. **Mutable identities stay visible.** When a provider or model exposes no immutable revision,
   `resolution.workload.identity` says `mutable`. The per-run availability and capability probe
   still decides that run; neither maintainers nor operators mistake its result for a durable pin.

7. **Human input terminates work.** A request requiring conversation or approval produces
   `human-input-required` and a failing terminal status. The action does not pause, bypass the
   requirement, or leave a resumable session behind.

## Not in v1

- **Automatic upgrades or fallback** — promoted when authors can declare them without permitting silent substitution.
- **Compatibility with every old pin** — promoted when measured demand justifies a bounded support window.
- **Interactive approval** — belongs in an interactive host or later event until GitHub supplies an unattended protocol.

## How the kit checks it

- Omit bundle, provider, and model in turn; require three `missing` results and zero runs.
- Run one prompt and one graph fixture for every adapter matrix row; require the matching work
  capability, bounded authority, one terminal status, and one named cause.
- Run custom bundle, provider, and model fixtures outside the matrix; require per-run probes,
  not allowlist rejection, and both compatible and incompatible observations.
- Change one transitive bundle source and each adapter dependency; require changed identities
  or digest and fresh verdicts rather than reuse of the previous records.
- Request malformed, unavailable, unsupported, human-input, timeout, and cancellation fixtures;
  require six distinct reasons, six terminal failures, and zero substitutions.
- Scan summaries, logs, and artifacts; require dependency identities and zero credential values.
- Use one immutable and one mutable model fixture; require the identity marker and a fresh per-run probe for both.

## Open questions

- Which service observation best distinguishes model replacement from ordinary model drift?
- Which providers expose a useful immutable service or model revision today?

## Changelog

| Date | Change | Evidence |
|---|---|---|
| 2026-10-07 | Drafted v1 with explicit choices, per-run workload probes, adapter matrix releases, and expiring mutable-service verdicts. | A named reviewer aged out; Anthropic and a Claude model are silent or ineffective defaults; transitive runtime sources track moving branches. |
