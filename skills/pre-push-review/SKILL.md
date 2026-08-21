---
name: pre-push-review
description: >
  Pre-PR self-review using the same criteria as the automated review-pr-opened GitHub Action.
  Catches stale mock patch targets, dead imports with noqa suppressors, fixture env-var leaks,
  and silent ineffective patches BEFORE they are flagged by CI. Run before pushing any branch to
  a PR on microsoft/amplifier-resolve. Triggers on: "review before push", "pre-PR check",
  "self-review before pushing", "catch issues before CI", "is this ready to push".
user-invocable: true
allowed-tools:
  - bash
  - grep
  - read_file
  - delegate
  - web_fetch
model_role: critique
context: fork
---

# Pre-Push Review

Run the same review the automated `review-pr-opened` GitHub Action will run — catch issues
before CI does. The #1 recurring pattern on `amplifier-resolve`: **stale mock patch targets**
after module splits. When a monolithic module is split into a package, tests that
`patch("old.module._X")` or `from old.module import _X` must become
`patch("new.module.submodule._X")`. Patching a re-export is silently ineffective — the call
inside the real module uses its own local binding, not the re-export.

**Success artifact:** A list of Required / Advisory findings that match what CI would flag,
returned before the branch is pushed.

## Inputs

- ``: Branch name to review (defaults to current branch). Optionally include the repo path.

## Steps

### 1. Orient on the diff

```bash
git diff origin/main...HEAD --name-only  # files changed
git diff origin/main...HEAD              # full diff for orientation
```

Identify which source modules changed and whether any module splits occurred
(a `.py` file deleted and a same-name `/` directory created).

**Success criteria**: You know which files changed and whether module splits happened.

---

### 2. Check stale patch targets (the #1 issue)

For every split module, grep ALL test files for references to the old path:

```bash
# Replace <old_module> with the split module name (e.g. cli, routes.instances)
grep -rn "patch.*amplifier_resolve\.<old_module>\." tests/
grep -rn "from amplifier_resolve\.<old_module> import _" tests/
```

Rules:
- `patch("a.b.symbol")` is correct ONLY if `symbol` ACTUALLY LIVES in `a.b` — not just re-exported there
- Patching a re-export binds the mock in the wrong namespace; the production code path is untouched
- Correct target: `patch("the.module.that.calls.symbol")` — where it is IMPORTED, not defined

**Success criteria**: Every stale patch target identified with exact `file:line` references.

---

### 3. Check dead imports with noqa suppressors

```bash
grep -rn "# noqa: F401" src/
```

For each hit: is the import legitimately kept (backward-compat re-export, TYPE_CHECKING guard)?
If not, it is silencing a real lint warning — flag it.

**Success criteria**: Every `# noqa: F401` is justified or flagged.

---

### 4. Check fixture env-var safety

```bash
grep -rn "os\.environ\[" tests/
grep -rn "os\.environ\.pop" tests/
```

Manual `os.environ[key] = value` in fixtures leaks the env var if the test raises before
teardown. The correct pattern is `monkeypatch.setenv(key, value)` — pytest handles cleanup.

**Success criteria**: No unguarded `os.environ` mutations in test fixtures.

---

### 5. Full review using pr-review.md criteria

Fetch the review criteria, then delegate a full review.

Fetch: `https://raw.githubusercontent.com/microsoft/amplifier-app-actions/main/context/pr-review.md`

Delegate to `superpowers:code-reviewer` with:
- The pr-review.md content as the review instructions
- The branch name and what the PR is supposed to do
- Explicit instruction to read FULL files, not just the diff
- Explicit instruction to grep for all callers/tests of any changed interface

Key pr-review.md criteria:
- **Read full files, not just diffs** — the diff orients; the full file is the review
- **Verify through code, not proxies** — PR descriptions and agent summaries are hypotheses
- **Five checks**: Necessity, Layer fit, Pattern, Correctness, Calibration
- **Patch target correctness**: for every `unittest.mock.patch()` in changed test files,
  verify the target is the module where the symbol actually lives after any rename/split

**Execution**: Delegate to `superpowers:code-reviewer`, model_role=critique

**Success criteria**: All findings returned with `file:line` references.

---

### 6. Report

Group findings by severity:

```
## Pre-Push Review: <branch>

### Required (will trigger CI CHANGES_REQUESTED)
1. `file:line` — description + exact fix

### Advisory (should fix, won't block merge)
1. `file:line` — description

### Verdict: READY TO PUSH  /  NEEDS FIXES FIRST
```

**Success criteria**: User receives actionable list; verdict is explicit.
