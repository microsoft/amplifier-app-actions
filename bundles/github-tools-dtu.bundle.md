---
bundle:
  name: github-tools-dtu
  version: 0.1.0

includes:
  # Compose the base tier.
  - bundle: git+https://github.com/microsoft/amplifier-app-actions@main#subdirectory=bundles/github-tools.bundle.md
  # Add DTU infrastructure — dtu-profile-builder agent, amplifier-digital-twin CLI
  - bundle: git+https://github.com/microsoft/amplifier-bundle-digital-twin-universe@main
  # Add Amplifier Tester — registers amplifier-tester: namespace (setup-digital-twin agent)
  # Required by investigate-recipe.yaml reproduce step.
  - bundle: git+https://github.com/microsoft/amplifier-bundle-amplifier-tester@main
---

# github-tools-dtu Bundle

Extends `github-tools` with Digital Twin Universe support for isolated
containerized execution.

Use when `enable_reproduction: true` in the GitHub Actions workflow.

Requires an Ubuntu full-VM runner with Incus installed (see `action.yml`).

## Incus Requirements

The `enable_reproduction: true` action input installs Incus from the Zabbly stable
channel before this bundle is used.  Ubuntu 24.04's bundled Incus has an AppArmor
bug blocking dockerd; the Zabbly channel fixes this.
