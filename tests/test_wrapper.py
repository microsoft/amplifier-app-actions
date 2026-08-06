"""Tests for amplifier_app_actions.wrapper — in-process session runner.

Design notes:
  - Prompt/recipe modes use in-process sessions via _create_session().
    Tests mock amplifier_foundation.load_bundle and
    amplifier_app_cli.session_runner.create_initialized_session.
  - Attractor mode also uses the in-process Python API (Path B):
    load_bundle → Bundle compose overlay → prepare → create_initialized_session.
    Tests mock the same infrastructure plus amplifier_foundation.Bundle.
"""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from amplifier_app_actions.wrapper import run

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ISSUE_EVENT = {
    "action": "opened",
    "issue": {
        "number": 42,
        "title": "Login page throws 500 error",
        "body": "Steps to reproduce: ...",
        "user": {"login": "alice"},
        "labels": [],
    },
    "repository": {"name": "my-repo", "owner": {"login": "my-org"}},
}


def _make_mock_initialized():
    """Build a mock initialized session + recipe tool for in-process mode testing."""
    mock_recipe_tool = MagicMock()
    mock_recipe_tool.execute = AsyncMock(return_value=None)

    mock_coordinator = MagicMock()
    mock_coordinator.get = MagicMock(return_value={"recipes": mock_recipe_tool})

    mock_session = MagicMock()
    mock_session.execute = AsyncMock(return_value="response")
    mock_session.coordinator = mock_coordinator
    mock_session.cleanup = AsyncMock()

    mock_initialized = MagicMock()
    mock_initialized.session = mock_session
    mock_initialized.cleanup = AsyncMock()

    return mock_initialized, mock_recipe_tool


@contextmanager
def _in_process(mock_initialized, *, captured_paths: list[str] | None = None):
    """Patch all in-process session infrastructure for prompt/recipe tests.

    Pass ``captured_paths`` to record every path argument passed to load_bundle.
    """
    mock_bundle = MagicMock()
    mock_bundle.prepare = AsyncMock(return_value=MagicMock())

    if captured_paths is not None:

        async def _capture_lb(path, **kwargs):
            captured_paths.append(path)
            return mock_bundle

        lb_kwargs: dict = {"side_effect": _capture_lb}
    else:
        lb_kwargs = {"new_callable": AsyncMock, "return_value": mock_bundle}

    with (
        patch("amplifier_foundation.load_bundle", **lb_kwargs),
        patch(
            "amplifier_app_cli.session_runner.create_initialized_session",
            new_callable=AsyncMock,
            return_value=mock_initialized,
        ),
        patch("amplifier_app_cli.console.console"),
        patch("rich.markdown.Markdown"),
    ):
        yield mock_initialized


@contextmanager
def _attractor_in_process(
    mock_initialized, *, capture_bundle_kwargs: list | None = None
):
    """Patch in-process infrastructure for attractor tests.

    _run_attractor uses:
      load_bundle(path) -> base_bundle
      Bundle(...) -> overlay
      base_bundle.compose(overlay) -> composed
      await composed.prepare() -> prepared
      create_initialized_session(...) -> initialized
      _register_spawn_capability(session, prepared)
      await initialized.session.execute(goal)
    """
    mock_composed = MagicMock()
    mock_composed.prepare = AsyncMock(return_value=MagicMock())
    mock_base_bundle = MagicMock()
    mock_base_bundle.compose = MagicMock(return_value=mock_composed)

    def _capture_bundle(**kwargs):
        if capture_bundle_kwargs is not None:
            capture_bundle_kwargs.append(kwargs)
        return MagicMock()

    with (
        patch(
            "amplifier_foundation.load_bundle",
            new_callable=AsyncMock,
            return_value=mock_base_bundle,
        ),
        patch("amplifier_foundation.Bundle", side_effect=_capture_bundle),
        patch(
            "amplifier_app_cli.session_runner.create_initialized_session",
            new_callable=AsyncMock,
            return_value=mock_initialized,
        ),
        patch("amplifier_app_cli.console.console"),
        patch("rich.markdown.Markdown"),
    ):
        yield mock_base_bundle


# ---------------------------------------------------------------------------
# 1. Prompt — in-process session + execute()
# ---------------------------------------------------------------------------


async def test_prompt_creates_in_process_session(tmp_path):
    """Prompt mode creates an in-process session and calls session.execute()."""
    mock_initialized, _ = _make_mock_initialized()

    with _in_process(mock_initialized):
        result = await run(
            prompt="triage this issue",
            bundle="github-tools",
            action_path=tmp_path,
        )

    assert result == 0
    mock_initialized.session.execute.assert_called_once()
    prompt_arg = mock_initialized.session.execute.call_args[0][0]
    assert "triage this issue" in prompt_arg


# ---------------------------------------------------------------------------
# 2. Context block before prompt
# ---------------------------------------------------------------------------


async def test_context_block_before_prompt(tmp_path):
    """With an event file, context block is prepended before the user prompt."""
    event_file = tmp_path / "event.json"
    event_file.write_text(json.dumps(_ISSUE_EVENT))

    mock_initialized, _ = _make_mock_initialized()

    with _in_process(mock_initialized):
        await run(
            prompt="Please triage.",
            event_path=str(event_file),
            bundle="github-tools",
            action_path=tmp_path,
        )

    full_prompt = mock_initialized.session.execute.call_args[0][0]
    assert "my-org/my-repo" in full_prompt
    assert "Please triage." in full_prompt
    context_idx = full_prompt.index("my-org/my-repo")
    prompt_idx = full_prompt.index("Please triage.")
    assert context_idx < prompt_idx, "Context block must appear before user prompt"


# ---------------------------------------------------------------------------
# 3. Injection title — stays in single prompt string
# ---------------------------------------------------------------------------


async def test_injection_title_in_single_prompt_string(tmp_path):
    """Injection title appears in the prompt string passed to execute(), never split."""
    evil_title = "Fix bug]; import os; os.system('evil')"
    event = {
        **_ISSUE_EVENT,
        "issue": {**_ISSUE_EVENT["issue"], "title": evil_title},
    }
    event_file = tmp_path / "event.json"
    event_file.write_text(json.dumps(event))

    mock_initialized, _ = _make_mock_initialized()

    with _in_process(mock_initialized):
        await run(
            prompt="Triage.",
            event_path=str(event_file),
            bundle="github-tools",
            action_path=tmp_path,
        )

    full_prompt = mock_initialized.session.execute.call_args[0][0]
    # The injection string must appear in the single prompt string
    assert evil_title in full_prompt


# ---------------------------------------------------------------------------
# 4. Recipe — in-process session + recipe_tool.execute()
# ---------------------------------------------------------------------------


async def test_recipe_calls_recipe_tool(tmp_path):
    """Recipe mode creates an in-process session and calls recipe_tool.execute()."""
    recipe_file = tmp_path / "triage.yaml"
    recipe_file.write_text("steps: []")

    mock_initialized, mock_recipe_tool = _make_mock_initialized()

    with _in_process(mock_initialized):
        result = await run(
            recipe_source=str(recipe_file),
            bundle="github-tools",
            action_path=tmp_path,
        )

    assert result == 0
    mock_recipe_tool.execute.assert_called_once()
    call_kwargs = mock_recipe_tool.execute.call_args[0][0]
    assert call_kwargs["operation"] == "execute"
    assert "recipe_path" in call_kwargs
    assert str(recipe_file) in call_kwargs["recipe_path"]


# ---------------------------------------------------------------------------
# 5. Recipe context data
# ---------------------------------------------------------------------------


async def test_recipe_context_data(tmp_path):
    """Recipe context contains event fields nested under 'context' key."""
    recipe_file = tmp_path / "triage.yaml"
    recipe_file.write_text("steps: []")

    event_file = tmp_path / "event.json"
    event_file.write_text(json.dumps(_ISSUE_EVENT))

    mock_initialized, mock_recipe_tool = _make_mock_initialized()

    with _in_process(mock_initialized):
        await run(
            recipe_source=str(recipe_file),
            event_path=str(event_file),
            bundle="github-tools",
            action_path=tmp_path,
        )

    call_kwargs = mock_recipe_tool.execute.call_args[0][0]
    context_data = call_kwargs["context"]

    assert "context" in context_data, "Event fields must be nested under 'context' key"
    ctx = context_data["context"]
    assert ctx["number"] == 42
    assert ctx["owner"] == "my-org"
    assert ctx["repo"] == "my-repo"
    assert ctx["title"] == "Login page throws 500 error"
    assert ctx["author"] == "alice"
    assert isinstance(ctx["labels"], list)


# ---------------------------------------------------------------------------
# 6. Attractor — in-process session with loop-pipeline overlay
# ---------------------------------------------------------------------------


async def test_attractor_builds_overlay_and_executes(tmp_path):
    """Attractor mode builds a Bundle overlay with dot_source and calls session.execute()."""
    attractor_file = tmp_path / "triage.dot"
    dot_source = "digraph G { A -> B; }"
    attractor_file.write_text(dot_source)

    mock_initialized, _ = _make_mock_initialized()
    mock_initialized.session.execute = AsyncMock(
        return_value=json.dumps({"status": "success", "notes": "ok"})
    )
    captured_bundle_kwargs: list = []

    with _attractor_in_process(
        mock_initialized, capture_bundle_kwargs=captured_bundle_kwargs
    ):
        result = await run(
            attractor_source=str(attractor_file),
            bundle="github-tools",
            action_path=tmp_path,
        )

    assert result == 0
    mock_initialized.session.execute.assert_called_once()
    goal = mock_initialized.session.execute.call_args[0][0]
    # No event context → goal defaults to "Triage the GitHub issue."
    assert goal == "Triage the GitHub issue."
    # Bundle overlay carries the DOT source in the orchestrator config
    assert len(captured_bundle_kwargs) == 1
    session_cfg = captured_bundle_kwargs[0].get("session", {})
    orch_cfg = session_cfg.get("orchestrator", {}).get("config", {})
    assert orch_cfg.get("dot_source") == dot_source


# ---------------------------------------------------------------------------
# 7. Attractor — goal derived from event context
# ---------------------------------------------------------------------------


async def test_attractor_goal_derived_from_event(tmp_path):
    """When an event file is present, the goal encodes the issue reference."""
    attractor_file = tmp_path / "triage.dot"
    attractor_file.write_text("digraph G { A -> B; }")

    event_file = tmp_path / "event.json"
    event_file.write_text(json.dumps(_ISSUE_EVENT))

    mock_initialized, _ = _make_mock_initialized()
    mock_initialized.session.execute = AsyncMock(
        return_value=json.dumps({"status": "success", "notes": "ok"})
    )

    with _attractor_in_process(mock_initialized):
        await run(
            attractor_source=str(attractor_file),
            event_path=str(event_file),
            bundle="github-tools",
            action_path=tmp_path,
        )

    goal = mock_initialized.session.execute.call_args[0][0]
    assert "42" in goal  # issue number
    assert "my-org/my-repo" in goal


# ---------------------------------------------------------------------------
# 8. Bundle alias resolution — github-tools
# ---------------------------------------------------------------------------


async def test_bundle_alias_github_tools_resolution(tmp_path):
    """Built-in alias 'github-tools' resolves to action_path/bundles/github-tools.bundle.md."""
    mock_initialized, _ = _make_mock_initialized()
    captured: list[str] = []

    with _in_process(mock_initialized, captured_paths=captured):
        await run(prompt="test", bundle="github-tools", action_path=tmp_path)

    assert captured, "load_bundle must have been called"
    expected = "file://" + str(tmp_path / "bundles" / "github-tools.bundle.md")
    assert captured[0] == expected


# ---------------------------------------------------------------------------
# 9. Bundle alias resolution — github-tools-dtu
# ---------------------------------------------------------------------------


async def test_bundle_alias_github_tools_dtu_resolution(tmp_path):
    """Built-in alias 'github-tools-dtu' resolves to action_path/bundles/github-tools-dtu.bundle.md."""
    mock_initialized, _ = _make_mock_initialized()
    captured: list[str] = []

    with _in_process(mock_initialized, captured_paths=captured):
        await run(prompt="test", bundle="github-tools-dtu", action_path=tmp_path)

    assert captured, "load_bundle must have been called"
    expected = "file://" + str(tmp_path / "bundles" / "github-tools-dtu.bundle.md")
    assert captured[0] == expected


# ---------------------------------------------------------------------------
# 10. Unknown bundle passthrough
# ---------------------------------------------------------------------------


async def test_unknown_bundle_passthrough(tmp_path):
    """Unknown bundle values pass through to load_bundle unchanged."""
    custom_bundle = "git+https://example.com/my.bundle.md"

    mock_initialized, _ = _make_mock_initialized()
    captured: list[str] = []

    with _in_process(mock_initialized, captured_paths=captured):
        await run(prompt="test", bundle=custom_bundle, action_path=tmp_path)

    assert captured[0] == custom_bundle


# ---------------------------------------------------------------------------
# 11. enable_reproduction promotes default bundle
# ---------------------------------------------------------------------------


async def test_enable_reproduction_promotes_default_bundle(tmp_path):
    """enable_reproduction=True upgrades default 'github-tools' to 'github-tools-dtu'."""
    mock_initialized, _ = _make_mock_initialized()
    captured: list[str] = []

    with _in_process(mock_initialized, captured_paths=captured):
        await run(
            prompt="test",
            bundle="github-tools",
            enable_reproduction=True,
            action_path=tmp_path,
        )

    assert captured, "load_bundle must have been called"
    assert "github-tools-dtu" in captured[0]


# ---------------------------------------------------------------------------
# 12. Explicit bundle not overridden by enable_reproduction
# ---------------------------------------------------------------------------


async def test_explicit_bundle_not_overridden_by_enable_reproduction(tmp_path):
    """An explicit non-default bundle is NOT promoted even when enable_reproduction=True."""
    mock_initialized, _ = _make_mock_initialized()
    captured: list[str] = []

    with _in_process(mock_initialized, captured_paths=captured):
        await run(
            prompt="test",
            bundle="github-tools-amplifier-dev",
            enable_reproduction=True,
            action_path=tmp_path,
        )

    assert captured, "load_bundle must have been called"
    assert "github-tools-amplifier-dev" in captured[0]
    assert "github-tools-dtu" not in captured[0]


# ---------------------------------------------------------------------------
# 13. GITHUB_TOKEN setdefault
# ---------------------------------------------------------------------------


async def test_github_token_set_in_env_when_missing(tmp_path, monkeypatch):
    """GITHUB_TOKEN is set in env via setdefault when it was absent."""
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    mock_initialized, _ = _make_mock_initialized()

    with _in_process(mock_initialized):
        await run(
            prompt="test",
            github_token="ghp_testtoken",
            action_path=tmp_path,
        )

    assert os.environ.get("GITHUB_TOKEN") == "ghp_testtoken"


async def test_github_token_not_overwritten_when_present(tmp_path, monkeypatch):
    """GITHUB_TOKEN already in env is NOT overwritten (setdefault semantics)."""
    monkeypatch.setenv("GITHUB_TOKEN", "existing-runner-token")

    mock_initialized, _ = _make_mock_initialized()

    with _in_process(mock_initialized):
        await run(
            prompt="test",
            github_token="different-token",
            action_path=tmp_path,
        )

    assert os.environ.get("GITHUB_TOKEN") == "existing-runner-token"


# ---------------------------------------------------------------------------
# 14. prompt_source inlines contents
# ---------------------------------------------------------------------------


async def test_prompt_source_inlines_file_contents(tmp_path):
    """prompt_source reads file and uses its contents as the prompt text."""
    prompt_file = tmp_path / "instructions.md"
    prompt_file.write_text("You are a helpful triage assistant. Label this bug.")

    mock_initialized, _ = _make_mock_initialized()

    with _in_process(mock_initialized):
        await run(
            prompt_source=str(prompt_file),
            bundle="github-tools",
            action_path=tmp_path,
        )

    full_prompt = mock_initialized.session.execute.call_args[0][0]
    assert "You are a helpful triage assistant. Label this bug." in full_prompt


# ---------------------------------------------------------------------------
# 15. Return codes
# ---------------------------------------------------------------------------


async def test_return_code_zero_on_success(tmp_path):
    """wrapper.run() returns 0 when session.execute() succeeds."""
    mock_initialized, _ = _make_mock_initialized()

    with _in_process(mock_initialized):
        returncode = await run(prompt="test", action_path=tmp_path)

    assert returncode == 0


async def test_return_code_one_on_session_error(tmp_path):
    """wrapper.run() returns 1 when session.execute() raises an exception."""
    mock_initialized, _ = _make_mock_initialized()
    mock_initialized.session.execute = AsyncMock(
        side_effect=RuntimeError("provider error")
    )

    with _in_process(mock_initialized):
        returncode = await run(prompt="test", action_path=tmp_path)

    assert returncode == 1


# ---------------------------------------------------------------------------
# 16. No event — no context prefix
# ---------------------------------------------------------------------------


async def test_no_event_no_context_prefix(tmp_path):
    """Without event_path, prompt is passed unmodified to session.execute()."""
    mock_initialized, _ = _make_mock_initialized()

    with _in_process(mock_initialized):
        await run(
            prompt="Just do this task.",
            action_path=tmp_path,
        )

    full_prompt = mock_initialized.session.execute.call_args[0][0]
    assert full_prompt == "Just do this task."


# ---------------------------------------------------------------------------
# 17. action_path defaults to parent of package
# ---------------------------------------------------------------------------


async def test_action_path_defaults_correctly():
    """When action_path is None, load_bundle receives a file:// path under the action root."""
    from amplifier_app_actions import wrapper

    mock_initialized, _ = _make_mock_initialized()
    captured: list[str] = []

    with _in_process(mock_initialized, captured_paths=captured):
        await run(prompt="test")

    assert captured, "load_bundle must have been called"
    actual_parent = str(Path(wrapper.__file__).parent.parent)
    assert actual_parent in captured[0]


# ---------------------------------------------------------------------------
# _register_spawn_capability
# ---------------------------------------------------------------------------


def test_register_spawn_capability_registers_on_coordinator():
    """_register_spawn_capability calls register_capability('session.spawn', ...) on coordinator."""
    import asyncio

    from amplifier_app_actions.wrapper import _register_spawn_capability

    mock_coordinator = MagicMock()
    mock_session = MagicMock()
    mock_session.coordinator = mock_coordinator

    mock_prepared = MagicMock()
    mock_prepared.bundle = MagicMock()
    mock_prepared.bundle.agents = {}

    _register_spawn_capability(mock_session, mock_prepared)

    mock_coordinator.register_capability.assert_called_once()
    name, fn = mock_coordinator.register_capability.call_args[0]
    assert name == "session.spawn"
    assert asyncio.iscoroutinefunction(fn)


# ---------------------------------------------------------------------------
# _run_attractor: reads DOT and configures loop-pipeline
# ---------------------------------------------------------------------------


async def test_run_attractor_reads_dot_and_configures_loop_pipeline(tmp_path):
    """_run_attractor reads DOT file and composes Bundle overlay with loop-pipeline config."""
    dot_file = tmp_path / "pipeline.dot"
    dot_source = "digraph G { A -> B; }"
    dot_file.write_text(dot_source)

    mock_initialized, _ = _make_mock_initialized()
    mock_initialized.session.execute = AsyncMock(
        return_value=json.dumps({"status": "success", "notes": "ok"})
    )
    captured_bundle_kwargs: list = []

    with _attractor_in_process(
        mock_initialized, capture_bundle_kwargs=captured_bundle_kwargs
    ):
        from amplifier_app_actions.wrapper import _run_attractor

        result = await _run_attractor(
            content=str(dot_file),
            ctx_prefix="",
            bundle_path="some-bundle",
            cwd=None,
        )

    assert result == 0
    assert len(captured_bundle_kwargs) == 1
    session_cfg = captured_bundle_kwargs[0].get("session", {})
    orch_cfg = session_cfg.get("orchestrator", {}).get("config", {})
    assert orch_cfg.get("dot_source") == dot_source


# ---------------------------------------------------------------------------
# _run_attractor: missing file raises
# ---------------------------------------------------------------------------


async def test_run_attractor_missing_dot_file_raises(tmp_path):
    """_run_attractor raises FileNotFoundError when the DOT file does not exist."""
    from amplifier_app_actions.wrapper import _run_attractor

    with pytest.raises(FileNotFoundError, match="Attractor DOT file not found"):
        await _run_attractor(
            content=str(tmp_path / "nonexistent.dot"),
            ctx_prefix="",
            bundle_path="some-bundle",
            cwd=None,
        )


# ---------------------------------------------------------------------------
# _run_attractor: returns 1 on session error
# ---------------------------------------------------------------------------


async def test_run_attractor_returns_1_on_session_error(tmp_path):
    """_run_attractor returns 1 when session.execute raises an exception."""
    dot_file = tmp_path / "pipeline.dot"
    dot_file.write_text("digraph G { A -> B; }")

    mock_initialized, _ = _make_mock_initialized()
    mock_initialized.session.execute = AsyncMock(
        side_effect=RuntimeError("provider error")
    )

    with _attractor_in_process(mock_initialized):
        from amplifier_app_actions.wrapper import _run_attractor

        result = await _run_attractor(
            content=str(dot_file),
            ctx_prefix="",
            bundle_path="some-bundle",
            cwd=None,
        )

    assert result == 1


# ---------------------------------------------------------------------------
# run() routing — attractor dispatches to _run_attractor
# ---------------------------------------------------------------------------


async def test_run_routes_attractor_to_run_attractor(tmp_path):
    """run() with attractor_source dispatches to _run_attractor, not _run_prompt_or_attractor."""
    dot_file = tmp_path / "pipeline.dot"
    dot_file.write_text("digraph G { A -> B; }")

    with (
        patch(
            "amplifier_app_actions.wrapper._run_attractor",
            new_callable=AsyncMock,
            return_value=0,
        ) as mock_attractor,
        patch(
            "amplifier_app_actions.wrapper._run_prompt_or_attractor",
            new_callable=AsyncMock,
            return_value=0,
        ) as mock_prompt,
    ):
        result = await run(
            attractor_source=str(dot_file),
            action_path=tmp_path,
        )

    assert result == 0
    mock_attractor.assert_called_once()
    mock_prompt.assert_not_called()


# ---------------------------------------------------------------------------
# _session_search_paths: repo-local file access via GITHUB_WORKSPACE
# ---------------------------------------------------------------------------


def test_session_search_paths_includes_github_workspace(tmp_path, monkeypatch):
    """When GITHUB_WORKSPACE is a real dir it is added to the session search
    paths so repo-local files (e.g. .github/amplifier/*) resolve without the
    DOT hardcoding the repo name."""
    from amplifier_app_actions.wrapper import _session_search_paths

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setenv("GITHUB_WORKSPACE", str(workspace))

    action_root = tmp_path / "action"
    action_root.mkdir()

    paths = _session_search_paths(str(action_root))

    assert Path(action_root) in paths, "action root must remain a search path"
    assert workspace in paths, "GITHUB_WORKSPACE must be added as a search path"


def test_session_search_paths_omits_unset_workspace(tmp_path, monkeypatch):
    """An unset GITHUB_WORKSPACE leaves search paths as cwd only (no change)."""
    from amplifier_app_actions.wrapper import _session_search_paths

    monkeypatch.delenv("GITHUB_WORKSPACE", raising=False)
    action_root = tmp_path / "action"
    action_root.mkdir()

    paths = _session_search_paths(str(action_root))

    assert paths == [Path(action_root)]


def test_session_search_paths_ignores_nonexistent_workspace(tmp_path, monkeypatch):
    """A GITHUB_WORKSPACE that does not exist on disk is ignored (additive-only)."""
    from amplifier_app_actions.wrapper import _session_search_paths

    monkeypatch.setenv("GITHUB_WORKSPACE", str(tmp_path / "missing"))
    action_root = tmp_path / "action"
    action_root.mkdir()

    paths = _session_search_paths(str(action_root))

    assert paths == [Path(action_root)]


# ---------------------------------------------------------------------------
# Defect 1: a FAILed pipeline must exit non-zero, not 0
# ---------------------------------------------------------------------------


async def test_attractor_fail_status_yields_nonzero_exit(tmp_path):
    """A pipeline that terminates with status=fail must NOT return exit 0.

    Regression guard for the "green check mark on a failed convergence run"
    defect: session.execute() not raising is not the same as the pipeline
    succeeding — PipelineOrchestrator.execute() returns a JSON string with a
    'status' field and does not raise on FAIL. Without the fix, this test
    fails (result == 0) because _run_attractor never inspected the status.
    """
    dot_file = tmp_path / "pipeline.dot"
    dot_file.write_text("digraph G { A -> B; }")

    mock_initialized, _ = _make_mock_initialized()
    mock_initialized.session.execute = AsyncMock(
        return_value=json.dumps(
            {
                "status": "fail",
                "notes": "Pipeline completed: 1/2 nodes succeeded.",
                "failure_reason": "max_pipeline_duration_exceeded",
                "nodes_completed": 1,
                "node_statuses": {"A": "fail"},
            }
        )
    )

    with _attractor_in_process(mock_initialized):
        from amplifier_app_actions.wrapper import _run_attractor

        result = await _run_attractor(
            content=str(dot_file),
            ctx_prefix="",
            bundle_path="some-bundle",
            cwd=None,
        )

    assert result != 0, (
        "A FAIL pipeline status must not yield exit 0 (green check mark on "
        "a failed convergence run)"
    )


async def test_attractor_partial_success_yields_zero_exit(tmp_path):
    """status=partial_success is a converged, acceptable terminal state."""
    dot_file = tmp_path / "pipeline.dot"
    dot_file.write_text("digraph G { A -> B; }")

    mock_initialized, _ = _make_mock_initialized()
    mock_initialized.session.execute = AsyncMock(
        return_value=json.dumps({"status": "partial_success", "notes": "ok"})
    )

    with _attractor_in_process(mock_initialized):
        from amplifier_app_actions.wrapper import _run_attractor

        result = await _run_attractor(
            content=str(dot_file),
            ctx_prefix="",
            bundle_path="some-bundle",
            cwd=None,
        )

    assert result == 0


async def test_attractor_missing_status_field_fails_closed(tmp_path):
    """A response with no 'status' key must NOT silently pass as success.

    Documents the fail-closed policy: we cannot tell "the pipeline actually
    succeeded but the response shape changed" from "something is silently
    broken", so an unrecognized/absent status is treated as a failure.
    """
    dot_file = tmp_path / "pipeline.dot"
    dot_file.write_text("digraph G { A -> B; }")

    mock_initialized, _ = _make_mock_initialized()
    mock_initialized.session.execute = AsyncMock(
        return_value=json.dumps({"notes": "no status field here"})
    )

    with _attractor_in_process(mock_initialized):
        from amplifier_app_actions.wrapper import _run_attractor

        result = await _run_attractor(
            content=str(dot_file),
            ctx_prefix="",
            bundle_path="some-bundle",
            cwd=None,
        )

    assert result != 0


async def test_attractor_non_json_response_fails_closed(tmp_path):
    """A non-JSON response (unexpected shape) also fails closed, not silently 0."""
    dot_file = tmp_path / "pipeline.dot"
    dot_file.write_text("digraph G { A -> B; }")

    mock_initialized, _ = _make_mock_initialized()
    mock_initialized.session.execute = AsyncMock(return_value="not json at all")

    with _attractor_in_process(mock_initialized):
        from amplifier_app_actions.wrapper import _run_attractor

        result = await _run_attractor(
            content=str(dot_file),
            ctx_prefix="",
            bundle_path="some-bundle",
            cwd=None,
        )

    assert result != 0


def test_exit_code_for_attractor_result_success_statuses():
    """Unit-level check of the status -> exit code mapping (no mocking needed)."""
    from amplifier_app_actions.wrapper import _exit_code_for_attractor_result

    assert _exit_code_for_attractor_result(json.dumps({"status": "success"})) == 0
    assert (
        _exit_code_for_attractor_result(json.dumps({"status": "partial_success"})) == 0
    )
    assert _exit_code_for_attractor_result(json.dumps({"status": "fail"})) == 1
    assert _exit_code_for_attractor_result(json.dumps({"status": "retry"})) == 1
    assert _exit_code_for_attractor_result(json.dumps({"status": "skipped"})) == 1
    assert _exit_code_for_attractor_result("") == 1
    assert _exit_code_for_attractor_result("{}") == 1
    assert _exit_code_for_attractor_result("not json") == 1


# ---------------------------------------------------------------------------
# Defects 2 & 3: tool_command / must_write= must anchor to the workspace,
# not wherever the ambient process cwd happens to be.
# ---------------------------------------------------------------------------


async def test_attractor_threads_target_dir_into_source_dir_config(tmp_path):
    """target_dir is passed through as the orchestrator's source_dir config.

    This is the seam ToolHandler's cwd resolution falls back to
    (``context.get("context.target_dir") or graph.source_dir or None``) when
    the mounted PipelineOrchestrator has no way to seed context.target_dir
    directly. Without the fix, the orchestrator config carries only
    dot_source/logs_root and tool_command nodes fall through to cwd=None.
    """
    dot_file = tmp_path / "pipeline.dot"
    dot_file.write_text("digraph G { A -> B; }")
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    mock_initialized, _ = _make_mock_initialized()
    mock_initialized.session.execute = AsyncMock(
        return_value=json.dumps({"status": "success"})
    )
    captured_bundle_kwargs: list = []

    with _attractor_in_process(
        mock_initialized, capture_bundle_kwargs=captured_bundle_kwargs
    ):
        from amplifier_app_actions.wrapper import _run_attractor

        await _run_attractor(
            content=str(dot_file),
            ctx_prefix="",
            bundle_path="some-bundle",
            cwd=None,
            target_dir=str(workspace),
        )

    assert len(captured_bundle_kwargs) == 1
    orch_cfg = captured_bundle_kwargs[0]["session"]["orchestrator"]["config"]
    assert orch_cfg.get("source_dir") == str(workspace)


async def test_attractor_target_dir_defaults_to_github_workspace(tmp_path, monkeypatch):
    """When target_dir isn't passed explicitly, $GITHUB_WORKSPACE is used."""
    dot_file = tmp_path / "pipeline.dot"
    dot_file.write_text("digraph G { A -> B; }")
    workspace = tmp_path / "gha-workspace"
    workspace.mkdir()
    monkeypatch.setenv("GITHUB_WORKSPACE", str(workspace))

    mock_initialized, _ = _make_mock_initialized()
    mock_initialized.session.execute = AsyncMock(
        return_value=json.dumps({"status": "success"})
    )
    captured_bundle_kwargs: list = []

    with _attractor_in_process(
        mock_initialized, capture_bundle_kwargs=captured_bundle_kwargs
    ):
        from amplifier_app_actions.wrapper import _run_attractor

        await _run_attractor(
            content=str(dot_file),
            ctx_prefix="",
            bundle_path="some-bundle",
            cwd=None,
        )

    orch_cfg = captured_bundle_kwargs[0]["session"]["orchestrator"]["config"]
    assert orch_cfg.get("source_dir") == str(workspace)


async def test_attractor_cwd_during_execute_is_target_dir(tmp_path):
    """The process cwd during session.execute() is target_dir, not action_path.

    This is what fixes must_write='s ``os.getcwd()`` fallback (must_write.py
    has no graph.source_dir fallback, only context.target_dir then
    os.getcwd()) — proving empirically that a must_write= relative path is
    satisfied by a file the node wrote into the workspace, per the task's
    request to verify Defect 3 is fixed BY Defect 2's fix rather than assumed.

    Without the fix, os.getcwd() during execute() is whatever the ambient
    cwd happened to be (action_path's original cwd in this test), which
    would NOT equal the workspace dir asserted here.
    """
    dot_file = tmp_path / "pipeline.dot"
    dot_file.write_text("digraph G { A -> B; }")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    action_dir = tmp_path / "action"
    action_dir.mkdir()

    captured_cwd: dict[str, str] = {}
    mock_initialized, _ = _make_mock_initialized()

    async def _capture_execute(goal):
        captured_cwd["cwd"] = os.getcwd()
        return json.dumps({"status": "success"})

    mock_initialized.session.execute = _capture_execute

    with _attractor_in_process(mock_initialized):
        from amplifier_app_actions.wrapper import _run_attractor

        await _run_attractor(
            content=str(dot_file),
            ctx_prefix="",
            bundle_path="some-bundle",
            cwd=str(action_dir),
            target_dir=str(workspace),
        )

    assert captured_cwd["cwd"] == str(workspace), (
        f"Expected cwd during session.execute() to be the workspace "
        f"({workspace}), got {captured_cwd['cwd']!r} — must_write='s "
        "os.getcwd() fallback would resolve against the wrong directory"
    )


async def test_attractor_no_target_dir_preserves_prior_behavior(tmp_path, monkeypatch):
    """With no target_dir and no GITHUB_WORKSPACE, behaviour is unchanged.

    No chdir is attempted and no source_dir config key is added — this is
    the local/test-run fallback path, not a regression vector.
    """
    monkeypatch.delenv("GITHUB_WORKSPACE", raising=False)
    dot_file = tmp_path / "pipeline.dot"
    dot_file.write_text("digraph G { A -> B; }")

    mock_initialized, _ = _make_mock_initialized()
    mock_initialized.session.execute = AsyncMock(
        return_value=json.dumps({"status": "success"})
    )
    captured_bundle_kwargs: list = []

    with _attractor_in_process(
        mock_initialized, capture_bundle_kwargs=captured_bundle_kwargs
    ):
        from amplifier_app_actions.wrapper import _run_attractor

        result = await _run_attractor(
            content=str(dot_file),
            ctx_prefix="",
            bundle_path="some-bundle",
            cwd=None,
        )

    assert result == 0
    orch_cfg = captured_bundle_kwargs[0]["session"]["orchestrator"]["config"]
    assert "source_dir" not in orch_cfg


# ---------------------------------------------------------------------------
# Defect 4: the logs_root directory must be surfaced as a GITHUB_OUTPUT entry
# ---------------------------------------------------------------------------


async def test_attractor_writes_logs_dir_to_github_output(tmp_path, monkeypatch):
    """logs_root is written to $GITHUB_OUTPUT as 'logs_dir=<path>'.

    Without this, a failed run's evidence (status.json/command.txt/
    response.md/graph.dot per node) lives only in a mkdtemp() dir that is
    discarded when the runner tears down — there is no way for a caller to
    actions/upload-artifact it.
    """
    dot_file = tmp_path / "pipeline.dot"
    dot_file.write_text("digraph G { A -> B; }")
    output_file = tmp_path / "github_output.txt"
    output_file.write_text("")
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))

    mock_initialized, _ = _make_mock_initialized()
    mock_initialized.session.execute = AsyncMock(
        return_value=json.dumps({"status": "success"})
    )

    with _attractor_in_process(mock_initialized):
        from amplifier_app_actions.wrapper import _run_attractor

        await _run_attractor(
            content=str(dot_file),
            ctx_prefix="",
            bundle_path="some-bundle",
            cwd=None,
        )

    output_content = output_file.read_text()
    assert output_content.startswith("logs_dir=/"), (
        f"Expected a logs_dir= entry in GITHUB_OUTPUT, got: {output_content!r}"
    )


async def test_attractor_writes_logs_dir_even_when_pipeline_fails(
    tmp_path, monkeypatch
):
    """The logs_dir output must be present even for a FAILed pipeline run.

    Evidence matters most exactly when the run failed — this must not be
    contingent on success.
    """
    dot_file = tmp_path / "pipeline.dot"
    dot_file.write_text("digraph G { A -> B; }")
    output_file = tmp_path / "github_output.txt"
    output_file.write_text("")
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))

    mock_initialized, _ = _make_mock_initialized()
    mock_initialized.session.execute = AsyncMock(
        return_value=json.dumps({"status": "fail", "failure_reason": "boom"})
    )

    with _attractor_in_process(mock_initialized):
        from amplifier_app_actions.wrapper import _run_attractor

        result = await _run_attractor(
            content=str(dot_file),
            ctx_prefix="",
            bundle_path="some-bundle",
            cwd=None,
        )

    assert result != 0
    assert output_file.read_text().startswith("logs_dir=/")


def test_write_github_output_noop_without_env(monkeypatch):
    """_write_github_output is a no-op when GITHUB_OUTPUT is unset (local runs)."""
    from amplifier_app_actions.wrapper import _write_github_output

    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
    # Must not raise even though there's nowhere to write.
    _write_github_output("logs_dir", "/tmp/whatever")
