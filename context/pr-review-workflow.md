# PR Review Workflow

Step-by-step procedure for PR review runs. Principles and guidelines live in @pr-review.md.

---

## PR Review Procedure

### Path A: PR opened

Run the structured review using a code-navigation agent, an architecture expert agent, and an implementation agent. Apply the five checks below. Post your findings as a comment directly on the PR using your GitHub comment tool.

### Path B: /review-pr comment on issue

Find the PR URL or reference (owner/repo#N) in the issue body. Then:

1. Read the PR diff to orient, then read every changed file **IN FULL**
2. Read related files: callers, tests, interfaces, canonical examples
3. Apply the five checks in order:
   - **Necessity** — Does this change unblock something that is currently impossible? Apply The Three Scope Questions.
   - **Layer fit** — Is this at the right layer? Who does it NOT protect?
   - **Pattern** — Does this match how similar problems are solved elsewhere in the codebase? Read canonical examples.
   - **Correctness** — Does the code do what it claims? Trace it. Read the callers. Check the tests guard contracts not implementations.
   - **Calibration** — Is the scope right? Does it fix the root cause or just a symptom?
4. Every finding must cite a specific file:line — no finding without evidence
5. Post your findings as a comment on the issue using your GitHub comment tool

---

## Repo Scope Rules

- Post findings as a comment directly on the PR (Path A) or on the issue (Path B) using your GitHub comment tool.
- Never reference private repos, internal project names, or org-internal specifics in comments. Public artifacts — zero-exposure posture.

---

## Calibration

For every observation during review, decide before presenting: this either blocks merge or it doesn't. No "minor things worth mentioning" tier.

If raising the finding is worth a review roundtrip, it blocks. If it isn't, it doesn't appear in the output.
