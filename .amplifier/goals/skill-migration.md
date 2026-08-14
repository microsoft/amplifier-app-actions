# Goal: skill-migration

## Outcome

`skills/pr-review/SKILL.md` exists as a valid Agent-Skills-spec skill that
ports the local PR-review behavior currently implemented as the `pr-review`
mode, and `modes/pr-review.md` no longer exists in the repo.

## Exit condition

Complete when **either** all three items below reach a terminal state, **or**
it is conclusively demonstrated the remainder cannot, naming the blocker for
each. An item ending FAIL or BLOCKED is a residual, not a failure of the goal.

1. **Skill file created** — `skills/pr-review/SKILL.md` exists, has valid
   Agent Skills spec YAML frontmatter (at minimum `name: pr-review` and a
   `description` adapted from the mode's description below), and a body that
   ports the mode's "Two review approaches" and "How to start" content,
   instructing the host agent to delegate the actual review work to the
   existing `app-actions:agents/pr-review-agent` (reuse it directly — do not
   duplicate or reimplement its logic).
   Terminal: PASS (file exists, frontmatter valid, delegates to
   `app-actions:agents/pr-review-agent`) / FAIL-named / BLOCKED-named.

2. **Old mode removed** — `modes/pr-review.md` is deleted from the repo.
   Terminal: PASS (file absent) / FAIL-named / BLOCKED-named.

3. **Skill loads and behaves correctly** — In a live Amplifier session inside
   this worktree, `load_skill(skill_name="pr-review")` loads successfully
   (no error) and the returned content presents both review approaches
   (Exhaustive and Prompt-shot) and instructs delegation to
   `pr-review-agent`. Record the exact `load_skill` call and its output as
   evidence.
   Terminal: PASS (evidence recorded showing successful load + correct
   content) / FAIL-named / BLOCKED-named.

## SCOPE-OUTS

- Do NOT modify `bundles/pr-review.bundle.md` — that is a separate bundle for
  the GitHub Actions runtime (posts PR comments) and is out of scope.
- Do NOT modify `README.md` — owned by a sibling lane (`readme-docs`).
- Do NOT create a new `tool-skills` configuration entry — none exists in this
  repo currently and none is required for this change.
- Do NOT duplicate `pr-review-agent` logic into the skill — reference the
  existing agent.
- Uniformity/parity with any other skill in the ecosystem is NOT required —
  only that this skill loads and behaves correctly.

## Working directory + branch

Work ONLY in this worktree. Do not touch the main checkout or sibling
worktrees. Base SHA and branch are provided by the launcher.

## File ownership

You own: `skills/pr-review/SKILL.md` (create), `modes/pr-review.md` (delete).
If you find you need to touch any other file (e.g. `README.md`,
`bundles/pr-review.bundle.md`), STOP — record the needed edit as a residual
in `DONE.json` instead of making it. Crossing into another lane's files is a
defect, not a courtesy.

## Commit and push

Commit early and often. Push every commit — do not wait until the end.
Never merge to main yourself; the orchestrator merges.

## Host capability limits

This is a documentation/config-file change, not a compiled artifact — there
is no build step to run. Live shared services (if any are referenced) are
read-only evidence; do not assume network services beyond what's needed for
`load_skill`.

## Time bound

20 minutes. Exceeding this is a terminal `BUDGET` state — commit whatever is
real and report, do not rush the remaining work to beat the clock.

## Final step

Write `DONE.json` in the worktree root as your final act, with fields:
`lane, verdict, branch, head, pushed, items[], residuals[], pending_human[],
suite`. Use `lane: "skill-migration"`. `suite: "none"` (no automated test
suite exists in this repo).

## KNOWN

- Base commit: `7cfd2863d79e9fe9864a46fcb91cea8efb6ee836` (main, clean at
  time of planning).
- Current `modes/pr-review.md` frontmatter (for reference/porting):
  ```yaml
  mode:
    name: pr-review
    description: >
      Local PR review in your session — exhaustive (5 independent review lenses with quality
      synthesis) or prompt-shot (single-pass five-check framework). No GitHub comment posted.
      Zero context cost until activated.
    shortcut: pr-review
    advertised: false
    default_action: block
    tools:
      safe: [bash, read_file, glob, grep, todo, delegate]
    contributes:
      agents:
        pr-review-agent:
          source: "@app-actions:agents/pr-review-agent"
  ```
- Mode body content to port: "Two review approaches" (Exhaustive = 5
  sequential lenses — correctness, architecture, patterns, tests, pedantic —
  merged/deduplicated/prioritized by severity, mirrors
  `pipelines/pr-review-exhaustive.dot`; Prompt-shot = single-pass five-check —
  Necessity, Layer fit, Pattern, Correctness, Calibration) and "How to start"
  (tell it what to review, it delegates to `pr-review-agent`, never does
  review logic itself, uses clean-room delegate with fresh context).
- The skill schema differs from the mode schema — drop mode-only concerns
  (`tools:`, `contributes:`, `shortcut:`, `advertised:`, `default_action:`);
  skills rely on the host session already having `delegate()` available.
- No automated test suite exists in this repo.
