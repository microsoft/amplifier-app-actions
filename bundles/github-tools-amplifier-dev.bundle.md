---
bundle:
  name: github-tools-amplifier-dev
  version: 0.1.0

includes:
  # Compose the DTU tier (which includes github-tools + DTU)
  - bundle: git+https://github.com/microsoft/amplifier-app-actions@main#subdirectory=bundles/github-tools-dtu.bundle.md
  # TODO: add amplifier-dev bundle when URL is stabilised
  # - bundle: git+https://github.com/microsoft/amplifier-bundle-amplifier-dev@main
---

# github-tools-amplifier-dev Bundle

Extends `github-tools-dtu` with Amplifier-ecosystem tooling for triaging
issues in Amplifier core/foundation/module repositories.

## Future Extension

The `amplifier-dev` bundle (to be added above) will include:
- Amplifier module registry access
- Bundle graph tooling
- Cross-module dependency analysis
