# Goal: readme-docs

## Outcome

`README.md` documents `npx skill add microsoft/amplifier-app-actions --skill
pr-review` as a fast, local-only install path for PR review, clearly
distinguished from the existing bundle-based install path used for the
GitHub Actions runtime, with no contradictions between the two.

## Exit condition

Complete when **either** all three items below reach a terminal state, **or**
it is conclusively demonstrated the remainder cannot, naming the blocker for
each. An item ending FAIL or BLOCKED is a residual, not a failure of the goal.

1. **New install path documented** — `README.md` includes a section
   documenting `npx skill add microsoft/amplifier-app-actions --skill
   pr-review` as the fast/lightweight way to get local, in-session PR review
   (no GitHub comment posted).
   Terminal: PASS (section present, command shown verbatim) / FAIL-named /
   BLOCKED-named.

2. **Skill vs bundle distinction is clear** — Existing sections that
   currently document `amplifier bundle add '<git+https URI>#subdirectory=...'
   --app` (used for the GHA `pr-review` bundle that posts PR comments) are
   left intact or updated only to cross-reference the new skill path, and it
   is unambiguous to a reader which path is for local interactive review
   (the skill) vs. which is for the GitHub Actions runtime (the bundle).
   Terminal: PASS (no contradiction, distinction is legible) / FAIL-named /
   BLOCKED-named.

3. **Markdown is valid** — The edited `README.md` renders correctly: no
   broken tables, no unclosed code fences, no broken internal links
   introduced by the edit.
   Terminal: PASS (spot-checked, valid) / FAIL-named / BLOCKED-named.

## SCOPE-OUTS

- Do NOT modify anything under `skills/`, `modes/`, or
  `bundles/pr-review.bundle.md` — those are owned by a sibling lane
  (`skill-migration`) or explicitly out of scope.
- Do NOT change the behavior or documented semantics of the existing
  `pr-review` GHA bundle — only clarify/cross-reference it if needed for the
  skill-vs-bundle distinction.
- A full rewrite/reorganization of `README.md` is NOT required — only the
  additions/clarifications needed for this change.

## Working directory + branch

Work ONLY in this worktree. Do not touch the main checkout or sibling
worktrees. Base SHA and branch are provided by the launcher.

## File ownership

You own: `README.md` only. If you find you need to touch any other file,
STOP — record the needed edit as a residual in `DONE.json` instead of making
it.

## Commit and push

Commit early and often. Push every commit — do not wait until the end.
Never merge to main yourself; the orchestrator merges.

## Host capability limits

This is a documentation-only change — there is no build step to run.

## Time bound

20 minutes. Exceeding this is a terminal `BUDGET` state — commit whatever is
real and report, do not rush the remaining work to beat the clock.

## Final step

Write `DONE.json` in the worktree root as your final act, with fields:
`lane, verdict, branch, head, pushed, items[], residuals[], pending_human[],
suite`. Use `lane: "readme-docs"`. `suite: "none"` (no automated test suite
exists in this repo).

## KNOWN

- Base commit: `7cfd2863d79e9fe9864a46fcb91cea8efb6ee836` (main, clean at
  time of planning).
- Relevant existing README sections (per prior repo survey): a "Quick
  start / local setup" section documenting `amplifier bundle add '<git+https
  URI>#subdirectory=...' --app`; a "Three ways to drive it" section
  explicitly warning that bare names like `pr-review` don't resolve without
  the full `git+https://...#subdirectory=` URI; a "Bundles" table listing
  built-in aliases vs. specialized workflow bundles including `pr-review`; a
  "Get help setting up" section describing mode activation.
  Read these sections directly in this worktree before editing — do not rely
  on this summary alone, verify against the live file.
- No `npx skill add` mechanism exists anywhere in this repo currently (this
  is new terminology/convention being introduced by this change, not
  reverse-engineered from existing precedent). Present it as a new install
  path without claiming it was already documented.
- No automated test suite exists in this repo.
