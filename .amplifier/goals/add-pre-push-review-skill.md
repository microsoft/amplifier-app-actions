# Goal: add pre-push-review as a standalone skill (relocation, not new content)

## Outcome

A new, standalone skill `skills/pre-push-review/SKILL.md` exists in this repo
(`microsoft/amplifier-app-actions`), byte-identical in content to the copy
currently vendored in `kenotron-ms/amplifier-resolver-goal-batch` at
`src/amplifier_resolver_goal_batch/skills_data/pre-push-review/SKILL.md` --
this repo becomes its new canonical, public home. This is a **relocation**,
not new authoring: do not rewrite, genericize, or otherwise change the
skill's content or behavior. The goal is purely: get the exact same file
into this repo, in the same shape this repo's sibling `skills/pr-review/`
skill already uses, and prove it is genuinely reachable via a public
`#subdirectory=` git URL.

## Why

A separate design (goal-batch skill reachability) needs to source this
skill from a genuinely public location via `tool-skills`'s
`#subdirectory=` git-URL mechanism. Its current home
(`kenotron-ms/amplifier-resolver-goal-batch`) is a private repo and will
stay private by explicit decision -- so it needs a new public home. This
repo already hosts a closely related skill (`skills/pr-review/SKILL.md`,
which itself delegates to `agents/pr-review-agent.md`), making it the right
thematic neighbor. Unlike `pr-review`, `pre-push-review` is fully
self-contained (does its own review work inline, no agent dependency) --
that's exactly why it was chosen originally, and why simply pointing at
`pr-review` instead doesn't work for the consuming design's use case.

## Complete when

Complete when **either** every item below reaches a terminal state, **or**
it is conclusively demonstrated the remainder cannot, naming the blocker for
each. Items ending FAIL or BLOCKED are residuals, not failures of the goal.

Items (each independently terminal -- PASS / FAIL-named / BLOCKED-named /
PENDING-HUMAN):

1. `skills/pre-push-review/SKILL.md` exists in this repo, with content
   byte-identical to the source
   (`kenotron-ms/amplifier-resolver-goal-batch`'s
   `src/amplifier_resolver_goal_batch/skills_data/pre-push-review/SKILL.md`
   -- fetch it directly, e.g. via `gh api
   repos/kenotron-ms/amplifier-resolver-goal-batch/contents/src/amplifier_resolver_goal_batch/skills_data/pre-push-review/SKILL.md`
   or an equivalent read, since you may not have that repo cloned locally).
   Verify byte-identity with a checksum comparison, not a visual diff.
2. The new skill's placement matches this repo's existing convention for
   `skills/pr-review/` (a `SKILL.md` at the leaf of `skills/<name>/`, no
   extra nesting).
3. Any README or docs in this repo that list available skills (check for
   one -- do not assume; if none exists, this item is N/A, not skipped
   silently) are updated to mention `pre-push-review` alongside `pr-review`,
   for discoverability. If you find no such list exists anywhere in this
   repo, record that as the item's evidence (N/A, verified absent) rather
   than silently doing nothing.
4. Once pushed, the exact `#subdirectory=` git URL that a consumer would use
   is verified to actually resolve publicly, unauthenticated. Prove it with:
   `curl -s -o /dev/null -w "%{http_code}" https://raw.githubusercontent.com/microsoft/amplifier-app-actions/<your-branch>/skills/pre-push-review/SKILL.md`
   returning `200` (use your actual pushed branch name, not `main`, since
   `main` won't have it until merged). This is the load-bearing verification
   step -- the whole point of this goal is fixing a real 404 a consuming
   design hit; a passing HTTP check is the evidence that requirement was
   met, a plausible-looking file listing is not.

## Working directory

Work ONLY in this worktree. Do not touch the main checkout or sibling
worktrees. Branch: `goal-batch/add-pre-push-review-skill`. Base SHA:
pinned at worktree creation (origin/main at the time this goal file is
committed).

## File ownership

You own: the new `skills/pre-push-review/` directory and, if it exists, any
README/docs list of available skills that needs a one-line addition. Do not
modify `skills/pr-review/`, `agents/pr-review-agent.md`,
`bundles/pr-review.bundle.md`, or any other existing skill/agent/bundle file
in this repo -- this goal only ADDS a new, independent skill; it does not
touch the existing pr-review pathway. If you find you need to touch
anything else to make this work, STOP, record the needed edit as a
residual, and do not make the edit.

## Required quality bar (non-negotiable)

- This is a genuine content relocation into a real, actively-maintained
  public Microsoft repo. Do not alter the source content's meaning,
  wording, or structure beyond what's needed to fit this repo's existing
  skill-file conventions (e.g. if this repo's other skills have a slightly
  different frontmatter convention than the source file, that's worth
  checking and flagging as a residual if there's a real conflict -- but
  default to preserving the source content verbatim).
- Commit early, push as you commit.
- Never merge to main. Open no PR yourself -- the orchestrator opens it.
- If this repo has its own AGENTS.md, README contribution notes, or PR
  template, read and follow them for commit/PR hygiene even though you are
  not opening the PR yourself (your commits should already meet the bar).

## Host capability limits

You have git and gh CLI access. You do not have a live consumer session to
test `tool-skills` actually loading this skill end-to-end from your pushed
branch -- that live-reachability proof happens at the orchestrator level,
against the consuming design's own PR, once this lands. Your job is: get
the file there correctly, and prove the raw URL resolves publicly over
HTTP, which is the specific, concrete thing that was broken before.

## Time bound

2 hours wall-clock, 60 turns max. Exceeding either is a terminal `BUDGET`
state -- record it honestly, and make sure your last real commit is pushed
first.

## DONE.json

Add `DONE.json` to this repo's `.gitignore` if not already ignored (check
first). Write `DONE.json` in the worktree root as your final act, fields:
`lane, session_id, verdict, branch, head, pushed, items[], residuals[],
pending_human[], suite`. `verdict` exactly one of `COMPLETE` / `BLOCKED` /
`PARTIAL`. `session_id` is your own session's id.

## Known

- `kenotron-ms/amplifier-resolver-goal-batch` is a private repo -- you may
  not be able to `git clone` it directly without credentials you don't
  have. Use `gh api repos/kenotron-ms/amplifier-resolver-goal-batch/contents/<path>`
  (which authenticates via the `gh` CLI's own token) to fetch the source
  file's raw content instead, or ask for it to be provided if that also
  fails -- do not fabricate the content from memory or guesswork.
- This repo's recent history (commits around `fe89f1f`, `fc2a3a6`, `3c5ba77`,
  `1be944b`) shows its own maintainer actively working on exactly the
  pr-review skill/agent split -- read `skills/pr-review/SKILL.md` and
  `agents/pr-review-agent.md` first for this repo's current conventions
  before adding the new file.
