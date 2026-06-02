# Issue Handling Process

A systematic approach for handling GitHub issues — investigation first, evidence-based conclusions, inductive communication.

---

## Core Principles

### 1. Investigation Before Action

**Never jump to conclusions until you understand the complete picture.**

- Use specialized agents or tooling to gather information (codebase expert, code navigation, debugging)
- Trace the actual code paths involved
- Compare working vs broken scenarios
- Identify the EXACT divergence point

**Anti-pattern:** Jump to fixes based on assumptions  
**Correct pattern:** Investigate → understand → reproduce → report

### 2. Evidence-Based Findings

**Define specific, measurable proof requirements BEFORE testing.**

Each finding must have concrete evidence:
- "The error occurs at `file:line` because X" ✓
- "No normalization layer exists between the reporter's path and the enforcement point" ✓
- "Reproduced in isolated test environment: [exact output]" ✓
- "Current main still exhibits the bug: [specific output]" ✓

**Anti-pattern:** "I think this is the issue"  
**Correct pattern:** "Here's the evidence: [specific code path, specific output]"

### 3. User Time is Sacred

**Complete the investigation fully before presenting findings.**

- Do ALL investigation first, then present ONE complete picture
- If the answer is in the codebase, go find it
- Don't ask the user to verify things you can check yourself

**Only bring design/philosophy decisions to the user, not missing research.**

### 4. Follow Your Reasoning to Its Conclusion

**If your analysis establishes a premise, trace it all the way through.**

When you've built the logical case for a position, follow that reasoning to its natural endpoint. Don't stop short and present half-conclusions that require the user to connect the final dots.

**Anti-pattern:** "X seems to be the cause. Consider investigating further."  
**Correct pattern:** "X is the cause. Here's the evidence: [file:line]. Here's what it means: [explanation]."

**The test:** After writing a finding, ask: "Does my conclusion follow from my premises? Or am I hedging on something I've already resolved?"

---

## The Process (4-Phase Workflow)

### Phase 1: Reconnaissance

**Goal:** Understand what's broken and what's involved.

**Actions:**
1. Read the issue carefully — what's the user scenario?
2. Check recent commits in potentially affected repos (the bug may already be fixed)
3. Delegate investigation to appropriate specialists:
   - A codebase/architecture expert — "What modules/components are involved?"
   - A code-navigation agent — "How does this code path work?"
   - A call-hierarchy tool or agent — "What calls what?"

**Deliverable:** Complete understanding of the problem and affected components.

---

### Phase 2: Root Cause Analysis

**Goal:** Identify the EXACT cause, not just symptoms.

**Actions:**
1. Trace the complete flow for both working and broken scenarios
2. Find the divergence point (where do they split?)
3. Understand WHY the divergence exists
4. Verify your hypothesis with code inspection

**Deliverable:** Specific `file:line` where the issue lives.

**Red flags:**
- "I think this might be the issue" — not specific enough
- "Probably something in this function" — keep narrowing
- "Could be related to..." — find the exact relationship

---

### Phase 3: Reproduction

**Goal:** Confirm the issue is reproducible and gather evidence.

Attempt reproduction in an isolated test environment (container, VM, or clean checkout):

1. Set up an environment mirroring the reported configuration
2. Attempt to reproduce the reported failure
3. Capture evidence of whether reproduction succeeded or failed

**Evidence collection:**
- Exact command output and error messages
- Exit codes
- Version information
- Whether the issue reproduces on current main or only on a specific version

**Outcomes:**
- **Reproduced** — capture the exact error output; this confirms root cause and provides evidence for the fix PR
- **Cannot reproduce** — document exactly what was tried and what happened; version mismatch is likely
- **Partial** — document which aspect reproduces and which doesn't

**Don't present findings until reproduction is attempted** (unless the issue clearly has no runnable reproduction — e.g., a documentation gap or a design question).

---

### Phase 4: Present Findings

**Goal:** Post a complete, inductive investigation summary.

**Structure:**
1. **Conclusion first** — what is the root cause, and is it reproduced?
2. **Evidence** — `file:line` references, reproduction output
3. **Proposed fix** — specific changes with rationale
4. **Impact** — who is affected, how severely
5. **Recommended next step** — not just options; a specific recommendation

**Post directly as a comment** on the triggering issue. The comment IS the deliverable.

**Draft the comment text before posting.** Read it as if you are the reporter seeing it cold. Does the first paragraph tell them the answer? Is every claim backed by evidence?

---

## PR Review Gates

PR reviews have their own gate structure.

### PR Review Gate

When reviewing a PR:

**Present:**
1. Review findings — per-file verdicts, required fixes, non-blocking notes
2. Specific `file:line` evidence for every finding
3. Overall recommendation: approve, request changes, or defer

Every finding must be backed by code evidence. "The diff looks clean" is not a finding.

### Gate Efficiency Rule

**Never have two consecutive approval points.** When you reach a conclusion that warrants a GitHub interaction (close, label, comment), present the draft text at the same time as the conclusion — not in a follow-up round.

Bundle the investigation output and the comment to post together simultaneously. Never present findings in one message and ask "should I post this?" in a follow-up.

---

## Investigation Patterns

### Pattern 1: Parallel Agent Dispatch

For complex issues, dispatch multiple specialists in parallel:

```
Architecture expert    — Consult on which modules/components are involved
Code-navigation agent  — Survey the code paths
Debugging agent        — Trace call hierarchies and hypothesis-driven analysis
```

Different perspectives reveal different aspects of the problem. Parallel dispatch surfaces ground truth through convergence.

### Pattern 2: Compare Working vs Broken

Always find a working scenario and compare:
- What does the working path do that the broken path doesn't?
- Where do they diverge?
- What's different about the setup/config?

**Example:** Command A works, command B doesn't → compare the initialization flows

### Pattern 3: Follow the Data

Trace where critical data (config, providers, modules) flows:
- Where does it originate? (config files, CLI flags)
- Where does it get transformed? (merge functions, override logic)
- Where does it get consumed? (session creation, module loading)
- Where does it get lost? (conditional guards, missing handoffs)

---

## Agent Usage Strategy

### Investigation Phase

| Role | When to Use | What They Provide |
|------|-------------|-------------------|
| Codebase/architecture expert | Always first for unfamiliar issues | Ecosystem knowledge, architecture context |
| Code-path explorer | Code path tracing, comparison | Structured survey of code flows |
| Call-hierarchy / code-intel agent | Call hierarchy, definitions | Deterministic code relationships |
| Debugging agent | When you have errors/stack traces | Hypothesis-driven debugging |

### Reproduction Phase

| Approach | When to Use | What It Provides |
|----------|-------------|------------------|
| Isolated test environment (container, VM, or clean checkout) | Reproducing reported issues | Environment matching reporter's config |
| Automated verification pass | After reproduction attempt | Objective PASS/FAIL verdict |

### Delegation Discovers What Direct Work Misses

Direct tool calls (reading files, grepping) consume tokens in YOUR context. Delegation to expert agents is not just efficient — it surfaces insights you would miss.

| Approach | Insights Found |
|----------|----------------|
| Direct file reading | Surface-level observations |
| Delegated investigation | Surface observations + architectural issues + ecosystem context |

Expert agents carry specialized documentation you don't have loaded. They find architectural issues because they have architectural context.

---

## Process Checklist

### Investigation
- [ ] Read issue and understand user scenario
- [ ] Check recent commits in affected repos (already fixed?)
- [ ] Determine issue category (bug / LLM behavior / feature request / user error)
- [ ] Delegate investigation to appropriate specialists
- [ ] Trace code paths (working vs broken if applicable)
- [ ] Identify exact root cause with `file:line` references

### Reproduction
- [ ] Attempt reproduction in an isolated test environment
- [ ] Capture exact output (reproduced / cannot reproduce / partial)
- [ ] Check version — if reporter's code doesn't match main, version mismatch is likely
- [ ] Document what was tried and what happened

### Reporting
- [ ] Draft comment: conclusion first, evidence second
- [ ] Every claim cites a specific `file:line` or reproduction output
- [ ] Appropriate label applied
- [ ] Post comment to the triggering issue

---

## Distilled Lessons

### Investigation Discipline
- Multiple wrong hypotheses preceded the correct one in every major incident.
  Keep investigating until you can point to the exact line of code.
- When the user asks clarifying questions, it signals incomplete understanding.
  Dig deeper, don't treat it as a disruption.
- Even technical reporters need independent code verification. Trust but verify.

### Reproduction
- "Cannot reproduce" is a complete finding — document it clearly with version info.
- Reproduction on current main is more informative than reproduction on the reporter's version.
  Check both.
- If reproduction fails unexpectedly, check whether the bug was recently fixed before
  concluding user error.

### PR Review
- Each fix round changes the attack surface. Review adversarially every time.
- Tests must guard contracts, not implementations. If "X is overridable" is
  the design claim, test the override.
- Even owner PRs need independent expert review.
- Don't ship fragile approaches with caveats. If it breaks for edge cases,
  find a reliable approach or leave it out entirely.

### Multiple Perspectives
- Parallel agent dispatch surfaces ground truth through convergence.
  Different agents find different aspects of the same problem.
- Constraints that eliminate quick workarounds force finding the REAL fix.

---

## Templates

### Investigation Report Template

```markdown
## Investigation Complete

### Root Cause
[Exact file:line with code evidence — or "not a code bug" with explanation]

### Reproduction
[REPRODUCED / COULD NOT REPRODUCE / PARTIAL]
[Test environment: what was set up]
[Steps attempted: exact commands run]
[Output: error messages or confirmation]

### Proposed Fix
[Specific changes with rationale]

### Files to Change
[List with line numbers]

### Impact
[Who is affected, how severely, workaround if any]

### Recommended Next Step
[Specific action — not a list of options]
```

---

## Anti-Patterns to Avoid

✗ **"I'll investigate and see what happens"** → Know what you're looking for before you look  
✗ **"This might be related"** → Find the exact relationship  
✗ **"Consider investigating further"** → If your analysis supports a conclusion, state it  
✗ **"Here are 4 options"** → When your analysis has a clear winner, present the winner  
✗ **Same approach, fourth attempt** → If it failed three times, the approach is wrong — re-investigate  
✗ **Presenting partial findings** → Do ALL investigation, then present ONE complete picture  
✗ **Burying the conclusion in analysis** → Lead with the answer on its own line, then the evidence  
✗ **"Cannot reproduce" without detail** → Document exactly what was tried, what version, what output  
✗ **Skipping reproduction** → Attempt it; "cannot reproduce" is a valid and useful finding  

---

## Success Metrics

An issue is properly handled when:

- [x] Root cause identified with specific `file:line` references (or correctly categorized as non-code-bug)
- [x] Root cause verified through code, not proxies
- [x] Reproduction attempted and result documented
- [x] Comment posted with plain-English summary + technical evidence
- [x] Appropriate label applied
- [x] Issue closed or next steps clearly stated

---

## Autonomy Guidelines

### 1. Make Recommendations, Not Option Lists

When you have enough information to recommend, **recommend**. Don't present "consider X" when your analysis supports "do X."

**Anti-pattern:** "Here are options A, B, C, D. Which would you like?"  
**Correct pattern:** "Root cause is X at `file:line`. Reproduced in isolated test environment [evidence]. Recommended fix: [specific approach]."

### 2. Unknown Terms = Custom Code Heuristic

When an issue report mentions terms not found in this codebase:
1. Assume custom app-layer code until proven otherwise
2. Proactively hypothesize the most likely explanation
3. Include workaround for custom code in response if applicable

### 3. Reproduction Before Advising

**Attempt reproduction before proposing any workaround or fix direction.**

Even when the root cause seems obvious from code inspection, reproduction evidence is qualitatively different from a code hypothesis. If reproduction fails, say so with detail — that's still useful information.

### 4. Multi-Scenario Investigation

When an issue could have multiple explanations:
1. List all plausible scenarios before investigating
2. Design an investigation plan covering all scenarios
3. Execute comprehensively rather than iterating scenario-by-scenario

### 5. Version Mismatch Detection

When the reporter describes code that doesn't match current main:
1. Note the discrepancy
2. Check if the fix already exists on main
3. If fixed: state that and provide update instructions rather than re-investigating

### 6. Decisiveness Over Hedging

When you have enough information, say what to do. Hedging wastes the reader's time.

**Signs you're hedging unnecessarily:**
- You wrote "consider" but your analysis clearly supports one answer
- You listed pros and cons but didn't say which side wins

**The litmus test:** "If someone asked 'so what should I do?', would I immediately know the answer?" If yes, just say it.

**Exception:** When there's a genuine unresolved trade-off, present it — but make clear that it's unresolved, not that you're deferring a resolved question.

### 7. Post-Action = Next-Action

After completing any action, propose the logical next step. Never leave a dead end.

**Anti-pattern:** "Investigation complete." [silence]  
**Correct pattern:** "Root cause confirmed at `file:line`, reproduced in isolated test environment. Recommended next step: [specific action]."

### 8. Follow the Process

When the workflow defines the next step, execute it. Deference is for design decisions, not for executing agreed processes.

---

## Issue Category Validation

Before investigating HOW a problem occurs, determine WHETHER it has a code-level root cause. Spend 30 seconds on category before 30 minutes on investigation:

| Category | Has code fix? | Example |
|----------|--------------|---------| 
| Code bug | Yes | Hardcoded unsafe patterns, missing event subscription |
| LLM behavior | No | Non-deterministic agent output quality |
| Feature request | **Apply The Three Scope Questions first** | Missing capability |
| User error | No | Wrong configuration, outdated version |

**Don't accept the reporter's failure categorization.** When a reporter says "the model made a bad choice," the question is: "could the framework have prevented this?" Verify the mechanism before accepting the category.

## Issue Lifecycle

- **Don't close issues until the fixing PR is merged** (for bugs requiring code fixes).
- **Close environmental issues immediately** with explanation.
- **Cascade issues:** When multiple issues trace to one root cause, keep the root issue open. Close the rest as duplicates.
- **Update labels as issue state changes.** Labels reflect current state, not history.
