"""GitHub event parsing and context block formatting."""

from __future__ import annotations

import json
from typing import Any


def parse_event(event_path: str) -> dict[str, Any]:
    """Parse a GitHub webhook JSON file into a flat event dict.

    Parameters
    ----------
    event_path:
        Filesystem path to the JSON event payload file.

    Returns
    -------
    dict with keys:
        event_type, owner, repo, number, title, body, author, labels,
        base_ref, head_ref

    Raises
    ------
    FileNotFoundError
        If event_path does not exist (propagated from open()).
    ValueError
        If the payload contains neither a 'pull_request' nor an 'issue' key.
    """
    with open(event_path) as fh:
        data: dict[str, Any] = json.load(fh)

    repo_data = data["repository"]
    owner: str = repo_data["owner"]["login"]
    repo: str = repo_data["name"]

    # Handle issue_comment events (comments on issues or PRs)
    # Must be checked before the generic "issue" branch to prevent fallthrough
    if "comment" in data and "issue" in data:
        comment = data["comment"]
        issue = data["issue"]
        result = {
            "event_type": "issue_comment",
            "owner": owner,
            "repo": repo,
            "number": issue["number"],
            "title": issue["title"],
            "body": comment.get("body") or "",
            "author": comment["user"]["login"],
            "labels": [label["name"] for label in issue.get("labels", [])],
            "base_ref": "",
            "head_ref": "",
        }
        # For PR-attached comments, include pull_request context if present
        if "pull_request" in data:
            result["pull_request"] = data["pull_request"]
        return result

    if "pull_request" in data:
        pr = data["pull_request"]
        return {
            "event_type": "pull_request",
            "owner": owner,
            "repo": repo,
            "number": pr["number"],
            "title": pr["title"],
            "body": pr.get("body") or "",
            "author": pr["user"]["login"],
            "labels": [label["name"] for label in pr.get("labels", [])],
            "base_ref": pr["base"]["ref"],
            "head_ref": pr["head"]["ref"],
        }

    if "issue" in data:
        issue = data["issue"]
        return {
            "event_type": "issues",
            "owner": owner,
            "repo": repo,
            "number": issue["number"],
            "title": issue["title"],
            "body": issue.get("body") or "",
            "author": issue["user"]["login"],
            "labels": [label["name"] for label in issue.get("labels", [])],
            "base_ref": "",
            "head_ref": "",
        }

    raise ValueError(
        "Unknown event: neither 'pull_request' nor 'issue' key found in payload"
    )


def format_context_block(event: dict[str, Any]) -> str:
    """Format a parsed event dict into a human-readable context block string.

    Parameters
    ----------
    event:
        Dict returned by :func:`parse_event`.

    Returns
    -------
    Formatted multiline string.  PR events include a ``Base → Head`` line;
    issue events do not.
    """
    body_text = event["body"] or "(empty)"
    labels_text = ", ".join(event["labels"]) if event["labels"] else "(none)"

    lines = [
        f"[{event['event_type']}: #{event['number']} in {event['owner']}/{event['repo']}]",
        f"Title: {event['title']}",
        "Body:",
        body_text,
        f"Labels: {labels_text}",
        f"Author: {event['author']}",
    ]

    if event["event_type"] == "pull_request":
        lines.append(f"Base: {event['base_ref']} \u2192 Head: {event['head_ref']}")

    return "\n".join(lines)
