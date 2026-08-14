# Convert `pr-review` Mode to a Distributable Agent Skill Design

## Goal
Convert the local-only `pr-review` mode (`modes/pr-review.md`) into a distributable Agent Skill, so it can be installed standalone via a `skill add`-style command (`npx skill add microsoft/amplifier-app-actions --skill pr-review`), and document that in the README.

## Background
Today, `pr-review` only exists as a mode: a hard-gated, hidden entry point reachable via a shortcut, that immediately delegates to a dedicated review agent. This works, but it means the review capability can only be consumed by pulling in the whole mode mechanism (frontmatter tool-gating, `contributes`, shortcut discovery) rather than being installed on its own as a lightweight, portable unit the way an Agent Skill can be. The user wants a standalone, skill-native form of this capability so it can be distributed and installed independently, without carrying mode-only machinery that a skill doesn't need.

## Context / Current State
- `modes/pr-review.md` is a hard-gated mode: `default_action: block`, safe tools `[bash, read_file, glob, grep, todo, delegate]`, `advertised: false` (hidden from the standard mode menu, reachable only via `shortcut: pr-review`), and dynamically `contributes.agents.pr-review-agent` sourced from `@app-actions:agents/pr-review-agent`. The mode body never performs review logic itself — it always delegates to `pr-review-agent` for a clean-room review with fresh context.
- Two review approaches exist in the current mode body:
  - **Exhaustive**: 5 sequential lenses (correctness, architecture, patterns, tests, pedantic), then merged/deduplicated/prioritized.
  - **Prompt-shot**: single-pass five-check (Necessity, Layer fit, Pattern, Correctness, Calibration).
- There is a SEPARATE, same-named bundle at `bundles/pr-review.bundle.md` used for the GitHub Actions runtime (composes the github-tools bundle + PR review context files for posting structured review comments on `pull_request: [opened]` events). **This bundle is OUT OF SCOPE and must not be touched.**
- No `skills/` directory or `SKILL.md` file exists anywhere in this repo currently — this is greenfield for the repo.
- No `npx skill add <repo> --skill <name>` mechanism currently exists in this repo's docs or code — it is being introduced/documented as the new distribution convention, not reverse-engineered from existing repo precedent.
- Repo composable-unit conventions:
  - `agents/` — agent `.md` files
  - `behaviors/` — near-empty `--app`-installable capability anchors
  - `bundles/` — `*.bundle.md` files with `bundle.name`/`version`/`description`, `includes`, `context.include`
  - `context/` — plain markdown context docs
  - `modes/` — `*.md` files with `mode.name`/`description`/`shortcut`/`advertised`/`tools`/`contributes`
  - `pipelines/` — `*.dot` attractor pipeline files
- Root `bundle.md` establishes the `@app-actions:` namespace (`app-actions:modes/...`, `app-actions:agents/...`, `app-actions:context/...`).

## Approach
1. **Create `skills/pr-review/SKILL.md`** following the Agent Skills spec (YAML frontmatter with `name` and `description`; body content adapted from the mode's "Two review approaches" and "How to start" sections). The skill body instructs delegation to the SAME existing agent, `app-actions:agents/pr-review-agent` (no duplication of agent logic — reuse via the same bundle namespace reference). The skill drops mode-only frontmatter concerns (`tools:` gating, `contributes:`) since those are mode-specific mechanisms; the skill relies on `delegate()` being available in the host session like any other skill.
2. **Retire `modes/pr-review.md` — delete it.** Rationale: the user's request was to turn `pr-review` into a skill *rather than* a mode — one canonical form should exist going forward, not both, to avoid divergent maintenance.
3. **Update `README.md`**: add `npx skill add microsoft/amplifier-app-actions --skill pr-review` as the lightweight/fast install path for local PR review, documented alongside (not replacing) the existing `amplifier bundle add '<git+https URI>#subdirectory=...' --app` install mechanism used for the GHA bundle. Update the bundles/quick-start tables/sections as needed so the two paths (skill vs. bundle) aren't conflated — the skill is for local interactive review, the bundle is for the GitHub Actions runtime.
4. **Explicitly OUT OF SCOPE**: `bundles/pr-review.bundle.md` and its GHA-runtime behavior — unchanged.

## Architecture
```
skills/pr-review/SKILL.md   (NEW — distributable, delegates to app-actions:agents/pr-review-agent)
modes/pr-review.md          (DELETED — superseded by the skill)
bundles/pr-review.bundle.md (UNCHANGED — GHA runtime, out of scope)
agents/pr-review-agent.md   (UNCHANGED — reused by the new skill, same as before by the mode)
```

The `pr-review-agent` remains the single source of review logic. Both the retired mode and the new skill were/are thin front doors that delegate to it — the skill just becomes the sole surviving front door for local/interactive use, distributed independently of the mode system.

## Components

### `skills/pr-review/SKILL.md` (new)
- YAML frontmatter: `name`, `description` per the Agent Skills spec.
- Body: adapted from the mode's "Two review approaches" (Exhaustive / Prompt-shot) and "How to start" sections.
- Delegation instruction: explicitly delegates to `app-actions:agents/pr-review-agent` for a clean-room review with fresh context — matching the mode's prior behavior.
- No `tools:` gating or `contributes:` block — those are mode-only mechanisms not applicable to skills.

### `modes/pr-review.md` (removed)
- Deleted in full. No redirect stub — the skill is the sole successor.

### `README.md` (updated)
- New install line: `npx skill add microsoft/amplifier-app-actions --skill pr-review`.
- Existing bundle install line for the GHA bundle retained, unchanged in mechanism.
- Any table/section that previously listed `pr-review` as a mode is updated to reflect it as a skill; sections covering the GHA bundle are reviewed for wording only, to keep the two paths (skill vs. bundle) clearly distinguished rather than conflated.

## Data Flow
1. User installs the skill: `npx skill add microsoft/amplifier-app-actions --skill pr-review`.
2. In an Amplifier session, the skill is loaded (e.g. via `load_skill(skill_name="pr-review")`).
3. The skill presents the two review approaches (Exhaustive / Prompt-shot) per its body content.
4. On a review request, the skill delegates to `app-actions:agents/pr-review-agent`, which performs the clean-room review with fresh context (unchanged agent behavior).
5. The GHA runtime path (`bundles/pr-review.bundle.md` on `pull_request: [opened]`) is entirely separate and unaffected by any of the above.

## Error Handling
- If `app-actions:agents/pr-review-agent` cannot be resolved from within a skill context (bundle-qualified `@mention` resolution differs from mode `contributes:` resolution), the live-invocation verification step (see below) will surface this directly as a failed delegation — this is the mechanism by which such a gap is caught, not a runtime error path to design around speculatively. See Open Questions.
- No new error-handling logic is introduced by this change beyond what the existing agent already handles; this is a packaging/distribution change, not a behavior change to the review logic itself.

## Verification Approach
Real-path verification, not static-only: after implementation, load the new skill in a live Amplifier session via `load_skill(skill_name="pr-review")` and confirm it produces the expected behavior — presents the two review approaches and, when given a review request, delegates to `pr-review-agent` for a clean-room review. This is the falsifiable check: a broken skill (bad frontmatter, wrong agent reference, missing delegation instruction) would fail this load-and-invoke check. Frontmatter/schema linting is a supporting static check, not a substitute for the live invocation.

## Open Questions
- Exact `npx skill add` invocation semantics/tooling are assumed based on the user's stated command; if the actual Amplifier skill-distribution CLI differs, the README section may need adjustment post-implementation.
- Whether `skills/pr-review/SKILL.md` needs to reference `app-actions:agents/pr-review-agent` via a full bundle-qualified path or a relative one depends on how skill-hosted `@mention` resolution behaves outside of mode `contributes:` — to be confirmed during implementation against the foundation skill-loading convention.

## Base Commit
`7cfd2863d79e9fe9864a46fcb91cea8efb6ee836` (main, clean working directory)
