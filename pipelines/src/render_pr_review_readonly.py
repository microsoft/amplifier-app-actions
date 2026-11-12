"""Render pipelines/pr-review-readonly.dot from its template and trusted script.

The DOT pipeline must be self-contained (a remote materializer fetches only the
DOT file), so the four tool nodes embed ``pr_review_readonly.py`` verbatim as a
quoted heredoc. This renderer is the only supported way to update the embedded
copies; ``tests/test_pr_review_readonly.py`` fails when the committed DOT file
differs from a fresh render.

Usage::

    python pipelines/src/render_pr_review_readonly.py          # rewrite the DOT file
    python pipelines/src/render_pr_review_readonly.py --check  # exit 1 when stale
"""

from __future__ import annotations

import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent
SCRIPT = SRC_DIR / "pr_review_readonly.py"
TEMPLATE = SRC_DIR / "pr-review-readonly.dot.in"
OUTPUT = SRC_DIR.parent / "pr-review-readonly.dot"

HEREDOC = "PYEOF"
# A double quote or backslash would be rewritten by the DOT string unescaper and
# a dollar sign would be expanded by the engine's tool_command substitution.
FORBIDDEN_CHARACTERS = ('"', "\\", "$")
PLACEHOLDERS = {
    "@@COLLECT_COMMAND@@": "collect",
    "@@EXPAND1_COMMAND@@": "expand1",
    "@@EXPAND2_COMMAND@@": "expand2",
    "@@FINALIZE_COMMAND@@": "finalize",
}
GENERATED_NOTICE = (
    "// GENERATED FILE - do not edit. Source: pipelines/src/pr-review-readonly.dot.in\n"
    "// and pipelines/src/pr_review_readonly.py; regenerate with\n"
    "// python pipelines/src/render_pr_review_readonly.py\n"
)


def check_embeddable(source: str) -> None:
    """Raise ValueError when *source* cannot be embedded byte-for-byte."""
    for char in FORBIDDEN_CHARACTERS:
        if char in source:
            raise ValueError(f"embedded script must not contain {char!r}")
    if any(line.strip() == HEREDOC for line in source.splitlines()):
        raise ValueError(f"embedded script must not contain a {HEREDOC} line")
    if not source.endswith("\n"):
        raise ValueError("embedded script must end with a newline")


def tool_command(source: str, subcommand: str) -> str:
    """The exact shell text a tool node runs: isolated python3 reading a quoted heredoc.

    ``-I`` keeps the working directory and PYTHONPATH off ``sys.path``, so
    nothing next to the process can shadow a standard library module.
    """
    return f"python3 -I - {subcommand} <<'{HEREDOC}'\n{source}{HEREDOC}\n"


def render(script: str | None = None, template: str | None = None) -> str:
    source = SCRIPT.read_text(encoding="utf-8") if script is None else script
    text = TEMPLATE.read_text(encoding="utf-8") if template is None else template
    check_embeddable(source)
    for placeholder, subcommand in PLACEHOLDERS.items():
        if text.count(placeholder) != 1:
            raise ValueError(f"template must contain {placeholder} exactly once")
        text = text.replace(placeholder, tool_command(source, subcommand))
    return GENERATED_NOTICE + text


def main(argv: list[str]) -> int:
    rendered = render()
    if argv == ["--check"]:
        current = OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else ""
        if current != rendered:
            print(f"{OUTPUT} is stale; run {Path(__file__).name}", file=sys.stderr)
            return 1
        return 0
    if argv:
        print(__doc__, file=sys.stderr)
        return 64
    OUTPUT.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
