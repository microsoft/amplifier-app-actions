---
name: github-actions
description: "Invoke the GitHub Actions automation expert — setup, debugging, prompt design, and pipeline customization with amplifier-app-actions. Use when the user wants help with GitHub Actions automation."
context: fork
disable-model-invocation: true
user-invocable: true
model_role: general
---

# GitHub Actions Automation Consultant

The user invoked `/github-actions` to get expert help with GitHub Actions automation using
`amplifier-app-actions`.

## User Request

$ARGUMENTS

If no specific request was provided, greet the user and ask what aspect of GitHub Actions
automation they need help with — setup, debugging, prompt design, attractor pipelines, or
something else.

## Instructions

Delegate this request to the `app-actions:github-actions-expert`. That expert is the
authoritative front-door consultant for the full lifecycle: zero-install setup through fully
automated repo through custom prompt and pipeline design. It coordinates with
`app-actions-expert` (workflow YAML) and `dot-setup-expert` (DOT pipeline design) as needed.

Use the delegate tool, passing the user's request as the instruction:

```python
delegate(
    agent="app-actions:github-actions-expert",
    instruction="<the user's request from $ARGUMENTS above>",
    context_depth="recent",
    context_scope="conversation"
)
```

If the user provided no request, pass a greeting instruction such as: "The user invoked
/github-actions with no specific request. Greet them warmly and ask what aspect of
amplifier-app-actions GitHub automation they need help with."
