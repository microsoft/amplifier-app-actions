"""Tests for amplifier_app_actions.instruction — resolve_instruction."""

from pathlib import Path

import httpx
import pytest
import respx

from amplifier_app_actions.instruction import InstructionType, resolve_instruction


# ---------------------------------------------------------------------------
# Validation error tests
# ---------------------------------------------------------------------------


def test_raises_value_error_none_when_nothing_set():
    """resolve_instruction raises ValueError mentioning 'none' when no fields provided."""
    with pytest.raises(ValueError, match="none"):
        resolve_instruction()


def test_raises_value_error_multiple_when_two_fields_set(tmp_path):
    """resolve_instruction raises ValueError mentioning 'multiple' when 2+ fields set."""
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("hello")
    with pytest.raises(ValueError, match="multiple"):
        resolve_instruction(prompt="hello", prompt_source=str(prompt_file))


# ---------------------------------------------------------------------------
# Whitespace handling
# ---------------------------------------------------------------------------


def test_whitespace_only_prompt_treated_as_not_set():
    """Whitespace-only prompt string is treated as unset (raises ValueError for none)."""
    with pytest.raises(ValueError, match="none"):
        resolve_instruction(prompt="   ")


# ---------------------------------------------------------------------------
# PROMPT type tests
# ---------------------------------------------------------------------------


def test_inline_prompt_returns_prompt_type_with_text():
    """resolve_instruction with inline prompt returns (PROMPT, text)."""
    result = resolve_instruction(prompt="Review this issue carefully.")
    assert result[0] is InstructionType.PROMPT
    assert result[1] == "Review this issue carefully."


# ---------------------------------------------------------------------------
# PROMPT_SOURCE type tests
# ---------------------------------------------------------------------------


def test_prompt_source_reads_file_contents(tmp_path):
    """resolve_instruction with prompt_source returns (PROMPT_SOURCE, file_contents)."""
    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text("You are a helpful triage assistant.\n")

    result = resolve_instruction(prompt_source=str(prompt_file))

    assert result[0] is InstructionType.PROMPT_SOURCE
    assert result[1] == "You are a helpful triage assistant.\n"


def test_prompt_source_missing_file_raises_file_not_found_with_checkout_hint(tmp_path):
    """resolve_instruction raises FileNotFoundError mentioning 'actions/checkout' for missing prompt_source."""
    missing = str(tmp_path / "nonexistent.md")
    with pytest.raises(FileNotFoundError, match="actions/checkout"):
        resolve_instruction(prompt_source=missing)


# ---------------------------------------------------------------------------
# RECIPE type tests
# ---------------------------------------------------------------------------


def test_recipe_source_returns_path_not_contents(tmp_path):
    """resolve_instruction with recipe_source returns (RECIPE, path_string), not file contents."""
    recipe_file = tmp_path / "triage.yaml"
    recipe_file.write_text("steps:\n  - agent: triage\n")

    result = resolve_instruction(recipe_source=str(recipe_file))

    assert result[0] is InstructionType.RECIPE
    assert result[1] == str(recipe_file)
    # Must return the PATH, not the file contents
    assert "steps:" not in result[1]


def test_recipe_source_missing_file_raises_file_not_found_with_checkout_hint(tmp_path):
    """resolve_instruction raises FileNotFoundError mentioning 'actions/checkout' for missing recipe_source."""
    missing = str(tmp_path / "nonexistent.yaml")
    with pytest.raises(FileNotFoundError, match="actions/checkout"):
        resolve_instruction(recipe_source=missing)


# ---------------------------------------------------------------------------
# ATTRACTOR type tests
# ---------------------------------------------------------------------------


def test_attractor_source_returns_path_not_contents(tmp_path):
    """resolve_instruction with attractor_source returns (ATTRACTOR, path_string), not file contents."""
    attractor_file = tmp_path / "attractor.md"
    attractor_file.write_text("# Attractor\nFocus on critical bugs.\n")

    result = resolve_instruction(attractor_source=str(attractor_file))

    assert result[0] is InstructionType.ATTRACTOR
    assert result[1] == str(attractor_file)
    # Must return the PATH, not the file contents
    assert "# Attractor" not in result[1]


def test_attractor_source_missing_file_raises_file_not_found_with_checkout_hint(
    tmp_path,
):
    """resolve_instruction raises FileNotFoundError mentioning 'actions/checkout' for missing attractor_source."""
    missing = str(tmp_path / "nonexistent.md")
    with pytest.raises(FileNotFoundError, match="actions/checkout"):
        resolve_instruction(attractor_source=missing)


# ---------------------------------------------------------------------------
# Remote source — _is_remote_source helper
# ---------------------------------------------------------------------------

_PROMPT_URI = "git+https://github.com/owner/repo@main#subdirectory=prompts/review.md"
_ATTRACTOR_URI = (
    "git+https://github.com/owner/repo@main#subdirectory=context/guidance.dot"
)
_RECIPE_URI = "git+https://github.com/owner/repo@main#subdirectory=recipes/triage.yaml"
_PROMPT_URI_NO_REF = "git+https://github.com/owner/repo#subdirectory=prompts/review.md"
_PROMPT_URI_CUSTOM_REF = (
    "git+https://github.com/owner/repo@v2.0#subdirectory=prompts/review.md"
)
_CONTENTS_API_PROMPT = (
    "https://api.github.com/repos/owner/repo/contents/prompts/review.md?ref=main"
)
_CONTENTS_API_ATTRACTOR = (
    "https://api.github.com/repos/owner/repo/contents/context/guidance.dot?ref=main"
)
_CONTENTS_API_RECIPE = (
    "https://api.github.com/repos/owner/repo/contents/recipes/triage.yaml?ref=main"
)


def test_is_remote_source_detects_git_https_uri():
    """_is_remote_source returns True for git+https:// URIs."""
    from amplifier_app_actions.instruction import _is_remote_source

    assert _is_remote_source("git+https://github.com/owner/repo@main#subdirectory=x.md")
    assert _is_remote_source(
        "git+https://github.example.com/org/repo#subdirectory=f.yaml"
    )


def test_is_remote_source_false_for_local_paths():
    """_is_remote_source returns False for local filesystem paths."""
    from amplifier_app_actions.instruction import _is_remote_source

    assert not _is_remote_source("/absolute/path/to/file.md")
    assert not _is_remote_source("./relative/path.yaml")
    assert not _is_remote_source("relative/path.yaml")
    assert not _is_remote_source("")


# ---------------------------------------------------------------------------
# Remote source — happy paths via GitHub Contents API
# ---------------------------------------------------------------------------


@respx.mock
def test_remote_prompt_source_returns_content():
    """Remote prompt_source fetches content via GitHub Contents API and returns it directly."""
    respx.get(_CONTENTS_API_PROMPT).mock(
        return_value=httpx.Response(200, text="You are a helpful reviewer.")
    )

    itype, content = resolve_instruction(prompt_source=_PROMPT_URI, github_token="tok")

    assert itype is InstructionType.PROMPT_SOURCE
    assert content == "You are a helpful reviewer."


@respx.mock
def test_remote_attractor_source_writes_temp_file_with_dot_suffix():
    """Remote attractor_source writes fetched content to a temp .dot file and returns its path."""
    respx.get(_CONTENTS_API_ATTRACTOR).mock(
        return_value=httpx.Response(200, text="digraph G { A -> B }")
    )

    itype, path = resolve_instruction(
        attractor_source=_ATTRACTOR_URI, github_token="tok"
    )

    assert itype is InstructionType.ATTRACTOR
    assert path.endswith(".dot"), f"Expected .dot suffix, got: {path!r}"
    assert Path(path).read_text() == "digraph G { A -> B }"


@respx.mock
def test_remote_recipe_source_writes_temp_file_with_yaml_suffix():
    """Remote recipe_source writes fetched content to a temp .yaml file and returns its path."""
    respx.get(_CONTENTS_API_RECIPE).mock(
        return_value=httpx.Response(200, text="steps:\n  - agent: triage\n")
    )

    itype, path = resolve_instruction(recipe_source=_RECIPE_URI, github_token="tok")

    assert itype is InstructionType.RECIPE
    assert path.endswith(".yaml"), f"Expected .yaml suffix, got: {path!r}"
    assert Path(path).read_text() == "steps:\n  - agent: triage\n"


# ---------------------------------------------------------------------------
# Remote source — auth header behaviour
# ---------------------------------------------------------------------------


@respx.mock
def test_remote_bearer_auth_header_sent_when_token_provided():
    """Bearer Authorization header is sent when github_token is non-empty."""
    route = respx.get(_CONTENTS_API_PROMPT).mock(
        return_value=httpx.Response(200, text="content")
    )

    resolve_instruction(prompt_source=_PROMPT_URI, github_token="my-secret-token")

    request = route.calls.last.request
    assert request.headers.get("authorization") == "Bearer my-secret-token"


@respx.mock
def test_remote_no_auth_header_when_token_empty():
    """No Authorization header is sent when github_token is empty."""
    route = respx.get(_CONTENTS_API_PROMPT).mock(
        return_value=httpx.Response(200, text="content")
    )

    resolve_instruction(prompt_source=_PROMPT_URI, github_token="")

    request = route.calls.last.request
    assert "authorization" not in {k.lower() for k in request.headers}


# ---------------------------------------------------------------------------
# Remote source — ref handling
# ---------------------------------------------------------------------------


@respx.mock
def test_remote_ref_defaults_to_main_when_uri_has_no_at_ref():
    """When the URI has no @ref the Contents API is called with ref=main."""
    respx.get(_CONTENTS_API_PROMPT).mock(
        return_value=httpx.Response(200, text="default ref content")
    )

    itype, content = resolve_instruction(
        prompt_source=_PROMPT_URI_NO_REF, github_token="tok"
    )

    assert itype is InstructionType.PROMPT_SOURCE
    assert content == "default ref content"


@respx.mock
def test_remote_custom_ref_used_in_api_url():
    """Custom @ref in the URI is forwarded to the Contents API."""
    respx.get(
        "https://api.github.com/repos/owner/repo/contents/prompts/review.md?ref=v2.0"
    ).mock(return_value=httpx.Response(200, text="v2 content"))

    itype, content = resolve_instruction(
        prompt_source=_PROMPT_URI_CUSTOM_REF, github_token="tok"
    )

    assert content == "v2 content"


# ---------------------------------------------------------------------------
# Remote source — error contract
# ---------------------------------------------------------------------------


@respx.mock
def test_remote_401_raises_permission_error_mentioning_token_and_repo():
    """HTTP 401 → PermissionError mentioning github_token and owner/repo."""
    respx.get(_CONTENTS_API_PROMPT).mock(return_value=httpx.Response(401))

    with pytest.raises(PermissionError, match="github_token") as exc_info:
        resolve_instruction(prompt_source=_PROMPT_URI, github_token="bad-tok")
    assert "owner/repo" in str(exc_info.value)


@respx.mock
def test_remote_403_raises_permission_error_mentioning_token_and_repo():
    """HTTP 403 → PermissionError mentioning github_token and owner/repo."""
    respx.get(_CONTENTS_API_PROMPT).mock(return_value=httpx.Response(403))

    with pytest.raises(PermissionError, match="github_token") as exc_info:
        resolve_instruction(prompt_source=_PROMPT_URI, github_token="bad-tok")
    assert "owner/repo" in str(exc_info.value)


@respx.mock
def test_remote_404_raises_file_not_found_without_checkout_hint():
    """HTTP 404 → FileNotFoundError without the 'actions/checkout' hint."""
    respx.get(_CONTENTS_API_PROMPT).mock(return_value=httpx.Response(404))

    with pytest.raises(FileNotFoundError) as exc_info:
        resolve_instruction(prompt_source=_PROMPT_URI, github_token="tok")
    assert "actions/checkout" not in str(exc_info.value)


@respx.mock
def test_remote_5xx_raises_runtime_error():
    """Non-401/403/404 HTTP errors → RuntimeError."""
    respx.get(_CONTENTS_API_PROMPT).mock(return_value=httpx.Response(500))

    with pytest.raises(RuntimeError):
        resolve_instruction(prompt_source=_PROMPT_URI, github_token="tok")


def test_remote_malformed_missing_subdirectory_raises_value_error_no_network():
    """URI without #subdirectory= fragment → ValueError, no network call made."""
    bad_uri = "git+https://github.com/owner/repo@main"  # no #subdirectory=
    with pytest.raises(ValueError, match="subdirectory"):
        resolve_instruction(prompt_source=bad_uri, github_token="tok")


# ---------------------------------------------------------------------------
# Remote source — local path unaffected under respx.mock
# ---------------------------------------------------------------------------


@respx.mock
def test_local_path_still_works_under_respx_mock_no_http_calls(tmp_path):
    """Local path resolves correctly with no HTTP calls even when respx is active."""
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("local content")

    # respx.mock with no routes — any accidental HTTP request would raise
    result = resolve_instruction(prompt_source=str(prompt_file))

    assert result[0] is InstructionType.PROMPT_SOURCE
    assert result[1] == "local content"


# ---------------------------------------------------------------------------
# Remote source — GITHUB_API_URL environment variable override
# ---------------------------------------------------------------------------


@respx.mock
def test_github_api_url_env_override_used_for_request(monkeypatch):
    """GITHUB_API_URL env var overrides the default api.github.com base URL."""
    monkeypatch.setenv("GITHUB_API_URL", "https://api.github.example.com")

    respx.get(
        "https://api.github.example.com/repos/owner/repo/contents/prompts/review.md?ref=main"
    ).mock(return_value=httpx.Response(200, text="enterprise content"))

    itype, content = resolve_instruction(prompt_source=_PROMPT_URI, github_token="tok")

    assert itype is InstructionType.PROMPT_SOURCE
    assert content == "enterprise content"
