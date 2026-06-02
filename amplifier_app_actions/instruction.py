"""Instruction field resolution for amplifier-app-actions.

Resolves exactly one of: prompt, prompt_source, recipe_source, or attractor_source
into a typed (InstructionType, value) pair.

Local paths are resolved from the filesystem as before.  Remote paths that begin
with ``git+https://`` are fetched from the GitHub Contents API and either returned
as text (prompt_source) or written to a temporary file (attractor_source,
recipe_source).
"""

from __future__ import annotations

import os
import tempfile
from enum import Enum
from pathlib import Path


class InstructionType(Enum):
    """Identifies which instruction field was provided."""

    PROMPT = "prompt"
    PROMPT_SOURCE = "prompt_source"
    RECIPE = "recipe_source"
    ATTRACTOR = "attractor_source"


# ---------------------------------------------------------------------------
# Remote-source helpers
# ---------------------------------------------------------------------------


def _is_remote_source(uri: str) -> bool:
    """Return True if *uri* is a remote git+https:// URI rather than a local path."""
    return uri.strip().startswith("git+https://")


def _fetch_remote_file(uri: str, github_token: str = "") -> str:
    """Fetch the content of a file from a remote GitHub repository.

    The URI must follow the pip/uv convention::

        git+https://github.com/<owner>/<repo>@<ref>#subdirectory=<file-path>

    The ``#subdirectory=`` fragment is repurposed here to specify the path of
    the *file* inside the repository (not a directory).  ``@<ref>`` is optional
    and defaults to ``main``.

    Parameters
    ----------
    uri:
        ``git+https://`` URI identifying the remote file.
    github_token:
        GitHub PAT or Actions token for private repositories.  An empty string
        means no ``Authorization`` header is sent.

    Returns
    -------
    str
        Raw text content of the file.

    Raises
    ------
    ValueError
        If the URI does not include ``#subdirectory=<file>`` or the
        ``<owner>/<repo>`` path is malformed.
    PermissionError
        On HTTP 401 / 403 responses.  The message mentions ``github_token``
        and the ``owner/repo`` slug.
    FileNotFoundError
        On HTTP 404.  The message does *not* contain the
        ``actions/checkout`` hint.
    RuntimeError
        On any other non-2xx response or transport error.
    """
    import httpx
    from amplifier_foundation import parse_uri

    parsed = parse_uri(uri)

    # Validate that a file path was given via #subdirectory=
    if not parsed.subpath:
        raise ValueError(
            f"Remote source URI must include a file path via #subdirectory=: {uri!r}"
        )

    # Extract owner and repo from the path component ('/owner/repo')
    raw_path = parsed.path.lstrip("/")
    parts = raw_path.split("/", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(
            f"Remote source URI must include both owner and repo (got {parsed.path!r}): {uri!r}"
        )
    owner, repo = parts

    ref = parsed.ref or "main"
    file_path = parsed.subpath
    api_base = os.environ.get("GITHUB_API_URL", "https://api.github.com")
    url = f"{api_base}/repos/{owner}/{repo}/contents/{file_path}?ref={ref}"

    headers: dict[str, str] = {"Accept": "application/vnd.github.raw+json"}
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"

    try:
        with httpx.Client() as client:
            response = client.get(url, headers=headers)
    except httpx.TransportError as exc:
        raise RuntimeError(f"Transport error fetching {uri!r}: {exc}") from exc

    if response.status_code in (401, 403):
        raise PermissionError(
            f"Access denied to {owner}/{repo} (HTTP {response.status_code}). "
            f"Check github_token and repository visibility."
        )
    if response.status_code == 404:
        raise FileNotFoundError(f"Remote source not found: {uri!r} (HTTP 404).")
    if not response.is_success:
        raise RuntimeError(f"Unexpected HTTP {response.status_code} fetching {uri!r}.")

    return response.text


def _write_temp_source(content: str, suffix: str) -> str:
    """Write *content* to a NamedTemporaryFile with the given *suffix* and return its path.

    The file is **not** deleted on close (``delete=False``) because the path is
    handed to downstream readers.  It is the caller's responsibility to clean up
    the file when it is no longer needed.

    Parameters
    ----------
    content:
        Text content to write.
    suffix:
        File suffix including the leading dot, e.g. ``".dot"`` or ``".yaml"``.

    Returns
    -------
    str
        Absolute path of the temporary file.
    """
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=suffix, delete=False, encoding="utf-8"
    )
    tmp.write(content)
    tmp.flush()
    tmp.close()
    return tmp.name


# ---------------------------------------------------------------------------
# Public resolver
# ---------------------------------------------------------------------------


def resolve_instruction(
    prompt: str = "",
    prompt_source: str = "",
    recipe_source: str = "",
    attractor_source: str = "",
    github_token: str = "",
) -> tuple[InstructionType, str]:
    """Resolve exactly one instruction field into a typed value pair.

    Empty strings and whitespace-only values are treated as not set.

    Each ``*_source`` field now accepts either a local filesystem path **or** a
    remote ``git+https://`` URI pointing to a file inside a GitHub repository::

        git+https://github.com/<owner>/<repo>@<ref>#subdirectory=<file-path>

    Parameters
    ----------
    prompt:
        Inline prompt text to use directly.
    prompt_source:
        Filesystem path **or** ``git+https://`` URI to a file whose contents are
        the prompt.
    recipe_source:
        Filesystem path **or** ``git+https://`` URI to an Amplifier recipe YAML
        file.
    attractor_source:
        Filesystem path **or** ``git+https://`` URI to an attractor (guidance)
        file.
    github_token:
        GitHub token used to authenticate remote fetches.  Ignored for local
        paths.  An empty string means no ``Authorization`` header is sent (works
        for public repositories).

    Returns
    -------
    tuple[InstructionType, str]
        - For PROMPT: (PROMPT, prompt_text)
        - For PROMPT_SOURCE: (PROMPT_SOURCE, file_contents)
        - For RECIPE: (RECIPE, path_string)
        - For ATTRACTOR: (ATTRACTOR, path_string)

    Raises
    ------
    ValueError
        If zero fields are set (message contains 'none') or multiple fields are
        set (message contains 'multiple' listing the field names).  Also raised
        for malformed remote URIs.
    FileNotFoundError
        If a *local* source path does not exist on the filesystem.  The error
        message includes an 'actions/checkout' reminder.  For remote 404s the
        message does *not* include the 'actions/checkout' hint.
    PermissionError
        If a remote fetch returns HTTP 401/403.
    RuntimeError
        If a remote fetch returns any other non-2xx status or encounters a
        transport error.
    """
    _FIELD_NAMES = ("prompt", "prompt_source", "recipe_source", "attractor_source")

    fields = {
        "prompt": prompt,
        "prompt_source": prompt_source,
        "recipe_source": recipe_source,
        "attractor_source": attractor_source,
    }

    # Treat empty / whitespace-only as unset
    set_fields = [name for name, val in fields.items() if val and val.strip()]

    if len(set_fields) == 0:
        raise ValueError(f"Exactly one of {_FIELD_NAMES} must be set. Got none.")

    if len(set_fields) > 1:
        raise ValueError(
            f"Exactly one of {_FIELD_NAMES} must be set. Got multiple: {set_fields}."
        )

    (field_name,) = set_fields

    if field_name == "prompt":
        return (InstructionType.PROMPT, fields["prompt"])

    if field_name == "prompt_source":
        if _is_remote_source(prompt_source):
            content = _fetch_remote_file(prompt_source, github_token)
            return (InstructionType.PROMPT_SOURCE, content)
        path = Path(prompt_source)
        if not path.exists():
            raise FileNotFoundError(
                f"prompt_source path not found: {prompt_source!r}. "
                "Make sure to use actions/checkout before running this action."
            )
        return (InstructionType.PROMPT_SOURCE, path.read_text())

    if field_name == "recipe_source":
        if _is_remote_source(recipe_source):
            content = _fetch_remote_file(recipe_source, github_token)
            tmp_path = _write_temp_source(content, ".yaml")
            return (InstructionType.RECIPE, tmp_path)
        path = Path(recipe_source)
        if not path.exists():
            raise FileNotFoundError(
                f"recipe_source path not found: {recipe_source!r}. "
                "Make sure to use actions/checkout before running this action."
            )
        return (InstructionType.RECIPE, recipe_source)

    # field_name == "attractor_source"
    if _is_remote_source(attractor_source):
        content = _fetch_remote_file(attractor_source, github_token)
        tmp_path = _write_temp_source(content, ".dot")
        return (InstructionType.ATTRACTOR, tmp_path)
    path = Path(attractor_source)
    if not path.exists():
        raise FileNotFoundError(
            f"attractor_source path not found: {attractor_source!r}. "
            "Make sure to use actions/checkout before running this action."
        )
    return (InstructionType.ATTRACTOR, attractor_source)
