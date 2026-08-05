---
bundle:
  name: app-actions-legacy
  version: 0.1.0
  description: >
    DEPRECATED — thin backward-compatibility shim for anyone who already ran
    `amplifier bundle add git+https://github.com/microsoft/amplifier-app-actions@main#subdirectory=bundles/app-actions.bundle.md --app`.

    This file used to be a fat bundle mounted via --app onto EVERY session:
    it carried `includes:` of both foundation and attractor, plus a
    `providers:` block pinning claude-sonnet-4-6 — force-installing those
    dependencies and silently overriding the user's chosen provider/model
    globally. That was a bundle-as-behavior misuse. The fix is
    `behaviors/app-actions.yaml`, the correct --app install target (see
    bundle.md and README.md for the current recommended install command).

    This shim now only includes that corrected behavior, so anyone still
    pinned to the old --app target keeps working, with none of the old
    side effects (no forced foundation/attractor install, no global
    provider override).

    Replacement command:
      amplifier bundle add git+https://github.com/microsoft/amplifier-app-actions@main#subdirectory=behaviors/app-actions.yaml --app

    Removal plan: delete this file in the release after next, giving one
    full release's notice to anyone still referencing the old --app target.

includes:
  - bundle: app-actions:behaviors/app-actions
---
