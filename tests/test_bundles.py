"""Tests for bundle files in bundles/ — structure and composition validation."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).parent.parent
_BUNDLES_DIR = _REPO_ROOT / "bundles"
_BEHAVIORS_DIR = _REPO_ROOT / "behaviors"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_frontmatter(path: Path) -> dict:
    """Extract and parse YAML frontmatter between --- markers."""
    content = path.read_text()
    m = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not m:
        return {}
    return yaml.safe_load(m.group(1)) or {}


def _parse_yaml(path: Path) -> dict:
    """Parse a plain YAML bundle or behavior file."""
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _tool_modules(fm: dict) -> list[str]:
    return [t.get("module", "") for t in (fm.get("tools") or [])]


def _include_bundles(fm: dict) -> list[str]:
    return [i.get("bundle", "") for i in (fm.get("includes") or [])]


def _provider_modules(fm: dict) -> list[str]:
    return [p.get("module", "") for p in (fm.get("providers") or [])]


# ---------------------------------------------------------------------------
# App-facing bundles: provider-neutral --app policy
# ---------------------------------------------------------------------------


def test_app_actions_behavior_remains_a_minimal_provider_neutral_anchor():
    """The base --app behavior must not replace the user's provider or session policy."""
    behavior = _parse_yaml(_BEHAVIORS_DIR / "app-actions.yaml")

    assert set(behavior) == {"bundle"}, (
        "behaviors/app-actions.yaml is the persistent --app install target and must "
        "remain a metadata-only anchor. Adding providers, session, context, includes, "
        "or other policy here would apply it to every session and can override the "
        "user's configured provider, including OpenAI."
    )


def test_readme_migrates_runtime_app_bundle_before_provider_neutral_install():
    """README must remove provider-pinned runtime bundles before the safe --app install."""
    readme = (_REPO_ROOT / "README.md").read_text(encoding="utf-8")
    removal_command = "amplifier bundle remove pr-review --app"
    provider_neutral_target = "#subdirectory=behaviors/app-actions.yaml"

    assert removal_command in readme
    assert provider_neutral_target in readme
    assert readme.index(removal_command) < readme.index(provider_neutral_target)


def test_app_actions_attractor_overlay_only_includes_provider_neutral_core():
    """The optional --app overlay must add only the provider-neutral attractor core."""
    behavior = _parse_yaml(_BEHAVIORS_DIR / "app-actions-attractor.yaml")

    assert not {"providers", "session", "context"} & behavior.keys(), (
        "behaviors/app-actions-attractor.yaml is installed with --app and must not "
        "declare provider, session, or context policy that could override user defaults."
    )
    assert set(behavior) == {"bundle", "includes"}
    assert _include_bundles(behavior) == [
        "git+https://github.com/microsoft/amplifier-bundle-attractor@main#subdirectory=behaviors/attractor-core.yaml"
    ], (
        "The optional attractor overlay must include only the provider-neutral "
        "attractor-core behavior; additional includes may introduce provider policy "
        "into every --app-composed session."
    )


def test_legacy_app_actions_shim_only_includes_corrected_behavior():
    """The legacy --app URI must remain a policy-free compatibility shim."""
    shim = _parse_frontmatter(_BUNDLES_DIR / "app-actions.bundle.md")

    assert not {"providers", "session"} & shim.keys(), (
        "bundles/app-actions.bundle.md is still registered with --app by legacy users. "
        "Provider or session policy here would override their configured defaults."
    )
    assert set(shim) == {"bundle", "includes"}
    assert _include_bundles(shim) == ["app-actions:behaviors/app-actions"], (
        "The legacy --app shim must include only the corrected provider-neutral base "
        "behavior."
    )


# ---------------------------------------------------------------------------
# File existence
# ---------------------------------------------------------------------------


def test_github_tools_bundle_exists():
    """bundles/github-tools.bundle.md must exist."""
    assert (_BUNDLES_DIR / "github-tools.bundle.md").exists()


def test_github_tools_dtu_bundle_exists():
    """bundles/github-tools-dtu.bundle.md must exist."""
    assert (_BUNDLES_DIR / "github-tools-dtu.bundle.md").exists()


def test_github_tools_amplifier_dev_bundle_exists():
    """bundles/github-tools-amplifier-dev.bundle.md must exist."""
    assert (_BUNDLES_DIR / "github-tools-amplifier-dev.bundle.md").exists()


# ---------------------------------------------------------------------------
# github-tools: base tier — includes foundation, local tools, explicit provider
# ---------------------------------------------------------------------------


def test_github_tools_includes_foundation():
    """github-tools.bundle.md must include amplifier-foundation."""
    fm = _parse_frontmatter(_BUNDLES_DIR / "github-tools.bundle.md")
    includes = _include_bundles(fm)
    assert any("amplifier-foundation" in inc for inc in includes), (
        "github-tools must include amplifier-foundation"
    )


def test_github_tools_has_all_three_github_tools():
    """github-tools.bundle.md must declare the three local GitHub tools."""
    fm = _parse_frontmatter(_BUNDLES_DIR / "github-tools.bundle.md")
    modules = _tool_modules(fm)
    assert "tool-github-post-comment" in modules
    assert "tool-github-add-label" in modules
    assert "tool-github-checkout-repo" in modules


def test_github_tools_use_entry_points():
    """GitHub tools in github-tools must NOT have a source: path (they use entry points)."""
    fm = _parse_frontmatter(_BUNDLES_DIR / "github-tools.bundle.md")
    tools = {t.get("module", ""): t for t in (fm.get("tools") or [])}
    for name in [
        "tool-github-post-comment",
        "tool-github-add-label",
        "tool-github-checkout-repo",
    ]:
        assert "source" not in tools.get(name, {}), (
            f"{name} must not have a source: path — registered via pyproject.toml entry points"
        )


def test_github_tools_no_session_override():
    """github-tools.bundle.md must NOT declare a session: block (fat bundle anti-pattern)."""
    fm = _parse_frontmatter(_BUNDLES_DIR / "github-tools.bundle.md")
    assert "session" not in fm, (
        "github-tools must not override session (use foundation defaults)"
    )


def test_github_tools_has_explicit_provider():
    """github-tools.bundle.md must declare provider-anthropic for in-process session creation."""
    fm = _parse_frontmatter(_BUNDLES_DIR / "github-tools.bundle.md")
    providers = _provider_modules(fm)
    assert "provider-anthropic" in providers, (
        "github-tools must declare provider-anthropic "
        "(required for in-process session creation via _create_session)"
    )


# ---------------------------------------------------------------------------
# github-tools-dtu: extends github-tools with Digital Twin Universe
# ---------------------------------------------------------------------------


def test_github_tools_dtu_includes_github_tools():
    """github-tools-dtu.bundle.md must include the github-tools bundle."""
    fm = _parse_frontmatter(_BUNDLES_DIR / "github-tools-dtu.bundle.md")
    includes = _include_bundles(fm)
    assert any("github-tools" in inc for inc in includes), (
        "github-tools-dtu must include github-tools"
    )


def test_github_tools_dtu_includes_digital_twin_universe():
    """github-tools-dtu.bundle.md must include amplifier-bundle-digital-twin-universe."""
    fm = _parse_frontmatter(_BUNDLES_DIR / "github-tools-dtu.bundle.md")
    includes = _include_bundles(fm)
    assert any("digital-twin-universe" in inc for inc in includes), (
        "github-tools-dtu must include digital-twin-universe"
    )


def test_github_tools_dtu_no_session_override():
    """github-tools-dtu.bundle.md must NOT declare a session: block."""
    fm = _parse_frontmatter(_BUNDLES_DIR / "github-tools-dtu.bundle.md")
    assert "session" not in fm


def test_github_tools_dtu_no_providers_override():
    """github-tools-dtu.bundle.md must NOT declare a providers: block."""
    fm = _parse_frontmatter(_BUNDLES_DIR / "github-tools-dtu.bundle.md")
    assert "providers" not in fm


# ---------------------------------------------------------------------------
# github-tools-amplifier-dev: extends github-tools-dtu with Amplifier dev tooling
# ---------------------------------------------------------------------------


def test_github_tools_amplifier_dev_includes_dtu():
    """github-tools-amplifier-dev.bundle.md must include the github-tools-dtu bundle."""
    fm = _parse_frontmatter(_BUNDLES_DIR / "github-tools-amplifier-dev.bundle.md")
    includes = _include_bundles(fm)
    assert any("github-tools-dtu" in inc for inc in includes), (
        "github-tools-amplifier-dev must include github-tools-dtu"
    )


def test_github_tools_amplifier_dev_no_launch_dtu():
    """github-tools-amplifier-dev.bundle.md must NOT declare tool-launch-dtu."""
    fm = _parse_frontmatter(_BUNDLES_DIR / "github-tools-amplifier-dev.bundle.md")
    modules = _tool_modules(fm)
    assert "tool-launch-dtu" not in modules


def test_github_tools_amplifier_dev_no_session_override():
    """github-tools-amplifier-dev.bundle.md must NOT declare a session: block."""
    fm = _parse_frontmatter(_BUNDLES_DIR / "github-tools-amplifier-dev.bundle.md")
    assert "session" not in fm


def test_github_tools_amplifier_dev_no_providers_override():
    """github-tools-amplifier-dev.bundle.md must NOT declare a providers: block."""
    fm = _parse_frontmatter(_BUNDLES_DIR / "github-tools-amplifier-dev.bundle.md")
    assert "providers" not in fm
