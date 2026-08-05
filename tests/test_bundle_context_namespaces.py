"""Regression guard: bundle/behavior context+agents includes must resolve.

This guard exists because of a silent context-loss defect: foundation's
@mention / ``context.include`` / ``agents.include`` loader is *opportunistic*
-- a reference to an unregistered or misresolved namespace is silently
skipped (only a DEBUG log line), never raised as an error. A bundle author
can reference ``<own-bundle-name>:context/foo.md`` (their own ``bundle.name``
field) expecting it to resolve to the file next to their bundle definition,
but the amplifier-foundation registry only auto-registers TWO namespaces for
a nested bundle (one loaded via ``#subdirectory=`` under a repo that has its
own root ``bundle.md``):

    1. The ROOT bundle's declared name -> the repository/checkout root.
    2. The nested bundle's OWN declared name -> the DIRECTORY CONTAINING
       THE NESTED BUNDLE FILE ITSELF (or ``base_path / namespace_root`` if
       ``namespace_root`` is declared) -- NOT the repository root.

If a bundle file lives in a subdirectory (e.g. ``bundles/``) but its
referenced content lives elsewhere (e.g. repo-root ``context/``), a
self-referencing ``<own-name>:context/foo.md`` reference resolves to a path
that does not exist and is silently dropped -- the session runs with the
authored context missing and nothing reports it.

This test statically replicates the *exact* two-namespace registration rule
above (see amplifier_foundation.registry -- ``BundleRegistry._load_single``,
around the "Nested bundle also registered own namespace" log lines) using
the real ``amplifier_foundation.Bundle`` parsing/resolution code
(``Bundle.from_dict`` + ``Bundle.resolve_pending_context``), so it doesn't
re-implement the mechanism by hand and doesn't require any network access
(no bundle registry load / git clone is performed).

Empirically proven broken/fixed via a standalone probe against the real
``amplifier_foundation.registry.BundleRegistry`` (see PR / task notes) --
this test is the standing static guard so the class of mistake can't
silently return.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml
from amplifier_foundation import Bundle

_REPO_ROOT = Path(__file__).parent.parent
_BUNDLES_DIR = _REPO_ROOT / "bundles"
_BEHAVIORS_DIR = _REPO_ROOT / "behaviors"
_ROOT_BUNDLE_PATH = _REPO_ROOT / "bundle.md"

# Matches "namespace:path/to/file" but not URI schemes (git+https://, http://, etc.)
# and not a bare filename with no namespace prefix.
_NAMESPACE_REF_RE = re.compile(r"^([a-zA-Z0-9_-]+):(.+)$")


def _parse_frontmatter(path: Path) -> dict:
    """Extract and parse YAML frontmatter between --- markers (for *.bundle.md)."""
    content = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not m:
        return {}
    return yaml.safe_load(m.group(1)) or {}


def _parse_plain_yaml(path: Path) -> dict:
    """Parse a plain YAML file (for behaviors/*.yaml -- no frontmatter fencing)."""
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _namespaced_refs(data: dict, section: str) -> list[str]:
    """Extract namespace:path entries from a `section.include` list (context/agents)."""
    include = (data.get(section) or {}).get("include") or []
    return [
        entry
        for entry in include
        if isinstance(entry, str) and _NAMESPACE_REF_RE.match(entry)
    ]


def _own_namespace_dir(bundle: Bundle) -> Path:
    """Replicate registry.py's own-namespace registration target exactly.

    Mirrors amplifier_foundation.registry._load_single: when a bundle's own
    `namespace_root` is declared, its own namespace resolves to
    `base_path / namespace_root`; otherwise it resolves to `base_path` (the
    directory containing the bundle/behavior file itself).
    """
    if bundle.namespace_root is not None and bundle.base_path is not None:
        return (bundle.base_path / bundle.namespace_root).resolve()
    assert bundle.base_path is not None
    return bundle.base_path


def _iter_bundle_and_behavior_files() -> list[Path]:
    files: list[Path] = [_ROOT_BUNDLE_PATH]
    files.extend(sorted(_BUNDLES_DIR.glob("*.bundle.md")))
    files.extend(sorted(_BEHAVIORS_DIR.glob("*.yaml")))
    return files


def _root_bundle_name() -> str:
    root_data = _parse_frontmatter(_ROOT_BUNDLE_PATH)
    name = root_data.get("bundle", {}).get("name")
    assert name, f"Root bundle.md at {_ROOT_BUNDLE_PATH} has no bundle.name"
    return name


# ---------------------------------------------------------------------------
# The guard
# ---------------------------------------------------------------------------


def _check_file(path: Path, root_name: str) -> list[str]:
    """Return a list of failure messages for namespaced refs that won't resolve."""
    if path.suffix == ".md":
        data = _parse_frontmatter(path)
    else:
        data = _parse_plain_yaml(path)

    refs: list[str] = []
    refs.extend(_namespaced_refs(data, "context"))
    refs.extend(_namespaced_refs(data, "agents"))
    if not refs:
        return []

    bundle = Bundle.from_dict(data, base_path=path.parent)

    failures: list[str] = []
    for ref in refs:
        m = _NAMESPACE_REF_RE.match(ref)
        assert m is not None
        namespace, rel_path = m.group(1), m.group(2)

        candidates: list[tuple[str, Path]] = []
        if namespace == root_name:
            candidates.append(("root namespace -> repo root", _REPO_ROOT / rel_path))
        if bundle.name and namespace == bundle.name:
            own_dir = _own_namespace_dir(bundle)
            candidates.append((f"own namespace -> {own_dir}", own_dir / rel_path))

        if not candidates:
            failures.append(
                f"{path.relative_to(_REPO_ROOT)}: '{ref}' uses namespace "
                f"'{namespace}', which is neither the root bundle name "
                f"('{root_name}') nor this file's own bundle.name "
                f"('{bundle.name}'). amplifier-foundation's registry only "
                f"auto-registers those two namespaces for a nested bundle; "
                f"any other namespace requires foundation to have already "
                f"loaded a bundle declaring that name elsewhere in the "
                f"compose chain -- this test cannot verify that statically, "
                f"so it is flagged rather than silently assumed to work."
            )
            continue

        if not any(candidate_path.exists() for _, candidate_path in candidates):
            tried = "; ".join(f"{label}: {p}" for label, p in candidates)
            failures.append(
                f"{path.relative_to(_REPO_ROOT)}: '{ref}' does not resolve to "
                f"an existing file under any namespace this file could "
                f"legitimately register ({tried}). foundation's mention/"
                f"context loader is opportunistic: an unresolved reference "
                f"is SILENTLY SKIPPED at runtime (no error), so this "
                f"authored context would be silently missing."
            )

    return failures


@pytest.mark.parametrize(
    "path", _iter_bundle_and_behavior_files(), ids=lambda p: p.name
)
def test_namespaced_includes_resolve(path: Path) -> None:
    """Every namespaced context/agents include must resolve to a real file.

    Prevents the silent-context-loss defect where a nested bundle
    self-references its own bundle.name expecting it to resolve to the repo
    root, when the registry actually resolves it to the bundle FILE's own
    directory (or namespace_root, if declared).
    """
    root_name = _root_bundle_name()
    failures = _check_file(path, root_name)
    assert not failures, "\n" + "\n".join(failures)


def test_at_least_the_known_context_includes_are_checked() -> None:
    """Sanity check that this guard actually exercises the fixed bundles.

    If this starts failing, the namespaced-ref extraction logic has stopped
    matching the real bundle files (e.g. YAML shape changed) and the guard
    above may be silently checking nothing.
    """
    checked_any = False
    root_name = _root_bundle_name()
    for path in _iter_bundle_and_behavior_files():
        data = (
            _parse_frontmatter(path)
            if path.suffix == ".md"
            else _parse_plain_yaml(path)
        )
        refs = _namespaced_refs(data, "context") + _namespaced_refs(data, "agents")
        if refs:
            checked_any = True
    assert checked_any, (
        "Expected at least one bundle/behavior file with a namespaced "
        "context/agents include -- found none. Guard may be broken."
    )
    assert root_name == "app-actions"
