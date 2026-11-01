"""Guard the unconditional, secret-free, locked baseline test gate."""

import re
from pathlib import Path

import pytest
import yaml


_ROOT = Path(__file__).parent.parent


@pytest.fixture
def workflow() -> dict:
    # BaseLoader preserves GitHub's YAML 1.2 `on` key (SafeLoader uses YAML 1.1).
    return yaml.load(
        (_ROOT / ".github/workflows/pytest.yml").read_text(), Loader=yaml.BaseLoader
    )


def test_runs_on_every_push_and_pull_request(workflow: dict) -> None:
    assert workflow["on"] == {"push": "", "pull_request": ""}
    assert "if" not in workflow["jobs"]["pytest"]


def test_readonly_without_secrets_or_persisted_credentials(workflow: dict) -> None:
    assert workflow["permissions"] == {"contents": "read"}
    assert not re.search(
        r"\bsecrets\s*[.\[]", (_ROOT / ".github/workflows/pytest.yml").read_text()
    )
    job = workflow["jobs"]["pytest"]
    assert "permissions" not in job
    checkout = next(
        s for s in job["steps"] if s.get("uses", "").startswith("actions/checkout@")
    )
    assert checkout["with"]["persist-credentials"] == "false"


def test_external_actions_are_immutable(workflow: dict) -> None:
    steps = workflow["jobs"]["pytest"]["steps"]
    actions = [s["uses"] for s in steps if "uses" in s]
    assert actions
    assert all(re.fullmatch(r"[\w.-]+/[\w.-]+@[0-9a-f]{40}", a) for a in actions)


def test_full_suite_with_locked_dependencies(workflow: dict) -> None:
    steps = workflow["jobs"]["pytest"]["steps"]
    commands = [s["run"] for s in steps if "run" in s]
    assert commands == ["uv sync --locked --group dev", "uv run --locked pytest"]
    assert all("if" not in s and "continue-on-error" not in s for s in steps)


def test_action_install_and_run_are_locked() -> None:
    action = yaml.safe_load((_ROOT / "action.yml").read_text())
    commands = "\n".join(s.get("run", "") for s in action["runs"]["steps"])
    assert "uv sync --locked --project" in commands
    assert "uv run --locked --project" in commands
