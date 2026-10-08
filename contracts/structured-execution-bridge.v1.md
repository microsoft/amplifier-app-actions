# Structured Execution Bridge Contract — v1 (DRAFT)

How GitHub Actions, the action adapter, Amplifier, and Attractor share one structured run.

## Who builds against this

**Workflow authors** supply a graph reference, event, workspace, workload runtime, and GitHub
authority. **Action maintainers** resolve the invocation. **Amplifier maintainers** provide
child sessions; **Attractor maintainers** execute the graph. **Workflow operators** read the
bridge and native-result records without reconstructing the adapter's internal calls.

## What it is

The adapter resolves one DOT source, renders available GitHub event data as the goal, and
resolves the workflow-owned bundle, provider, and model into named Amplifier profiles. It
records that bridge, mounts Attractor inside Amplifier, and rejects unsupported worker kinds
without rewriting the graph. Attractor owns accepted graph semantics and returns its native
result. The adapter records that result and maps it into the terminal result owned by
`runtime-dependencies.v1`.

```yaml
bridge_record: # logs_dir/bridge.yaml; secret-free summary also goes to the step summary
  graph: {source: "git+https://github.com/owner/repo@ref#subdirectory=flow.dot", digest: "sha256:..."}
  goal: {present_fields: [event, repository, number], digest: "sha256:..."}
  workspace: /github/workspace
  profiles:
    analysis: {runtime: sha256:..., tools: [filesystem, bash, search]}
attractor_result: # logs_dir/attractor-result.json
  status: success | partial_success | fail
  failure_reason: null | <runner reason>
  nodes_completed: 7
  node_statuses: {node_id: success}
```

## The promises

1. **The adapter resolves one graph.** The workflow supplies one local or remote DOT source;
   the adapter resolves it once, hashes the exact text passed to Attractor, and writes source
   plus digest to `bridge.yaml`. A missing source maps to `missing`; multiple instruction sources
   map to `malformed`; both fail before session creation.

2. **Context keeps its source.** GitHub owns the event file, workspace, permissions, and
   credentials. `bridge.yaml` records which event fields were present plus a digest of the
   rendered goal, never secret values or the potentially sensitive goal text. Missing facts
   stay absent, and relative execution paths resolve beneath the recorded workspace.

3. **Profiles declare Amplifier authority.** Each agent profile records the resolved workload
   runtime from `runtime-dependencies.v1` and its Amplifier tools. Agent nodes may select only
   declared profiles. Unknown profiles map to `unsupported`; missing `session.spawn` maps to
   `unavailable`. Neither case constructs an empty child or selects another backend.

4. **Worker support is explicit.** v1 accepts Attractor tool nodes and Amplifier agent nodes.
   A graph requesting a direct LLM worker maps to `unsupported` before execution. For accepted
   graphs, Attractor alone selects nodes, edges, retries, gates, context updates, and
   convergence; the adapter makes zero node-selection or routing decisions.

5. **Native results translate once.** The adapter writes Attractor's native result unchanged,
   then emits the result owned by `runtime-dependencies.v1`: native `success` and
   `partial_success` map to `success/completed`; native `fail` maps to
   `failure/execution-failed`; malformed, empty, retry, skipped, and unknown results map to
   `failure/malformed`; an Attractor duration limit maps to `failure/timeout`.

6. **Evidence begins after resolution.** After graph resolution and before runner bundle
   preparation, the adapter allocates one unique directory, writes `bridge.yaml`, and publishes
   `logs_dir`. Attractor writes graph and node evidence there. GitHub owns durability through
   an explicit artifact-upload step; pre-resolution failures have no pipeline evidence.

7. **Session cleanup is unconditional.** Once Amplifier session creation begins, success,
   Attractor failure, and adapter exception each call cleanup exactly once. Adapter exceptions
   map to `execution-failed`. GitHub job cancellation remains governed by GitHub and
   `runtime-dependencies.v1`, not relabeled by this bridge.

## Not in v1

- **Graph authoring or repair** — belongs to workflow authors and Attractor tooling; promoted when execution can preserve authorship and review.
- **Automatic artifact upload** — belongs to the workflow; promoted when retention can be declared without taking repository policy.
- **Direct LLM workers** — promoted when their runtime and authority can be recorded like an Amplifier profile.
- **Non-DOT graph formats** — promoted when another format can preserve the same bridge and native-result records.

## How the kit checks it

- Run local and remote DOT fixtures, one missing source, and two simultaneous instruction sources;
  require exact digests, `missing`, and `malformed` respectively.
- Remove event fields and use no event file; require accurate `present_fields`, changed goal digests, and workspace-bounded relative paths.
- Remove a profile and `session.spawn`; require `unsupported` and `unavailable`, zero empty children, and zero backend fallback.
- Request tool, agent, and direct workers; require unchanged Attractor routing for the first two and preflight rejection for direct.
- Return success, partial success, fail, duration-limit, malformed, empty, retry, skipped, and unknown native results; require the stated mapping and unchanged native record.
- Fail before preparation and during execution; require `logs_dir` after resolution, then assert
  cleanup exactly once for success, Attractor fail, and exception paths plus `execution-failed`
  for adapter exceptions.

## Open questions
- Which minimum node evidence files must every compatible Attractor runner write?
- What recorded authority would permit direct LLM workers in a later version?

## Changelog

| Date | Change | Evidence |
|---|---|---|
| 2026-10-07 | Drafted v1 around graph resolution, sourced context, explicit profiles, accepted workers, native-result translation, and evidence custody. | Existing defects included silent backend fallback, accidental path resolution, green failed pipelines, and runner evidence lost after jobs. |
