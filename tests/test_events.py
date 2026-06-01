"""Tests for amplifier_app_actions.events — parse_event and format_context_block."""

import json
import pytest

from amplifier_app_actions.events import format_context_block, parse_event


# ---------------------------------------------------------------------------
# parse_event tests
# ---------------------------------------------------------------------------


async def test_parse_issue_extracts_all_fields(tmp_path):
    """parse_event returns correct flat dict for a basic issue payload."""
    payload = {
        "action": "opened",
        "issue": {
            "number": 1,
            "title": "Test issue",
            "body": "Something is broken in the auth module",
            "user": {"login": "test-user"},
            "labels": [],
        },
        "repository": {
            "name": "test-repo",
            "owner": {"login": "test-org"},
        },
    }
    event_file = tmp_path / "event.json"
    event_file.write_text(json.dumps(payload))

    event = parse_event(str(event_file))

    assert event["event_type"] == "issues"
    assert event["owner"] == "test-org"
    assert event["repo"] == "test-repo"
    assert event["number"] == 1
    assert event["title"] == "Test issue"
    assert event["body"] == "Something is broken in the auth module"
    assert event["author"] == "test-user"
    assert event["labels"] == []
    assert event["base_ref"] == ""
    assert event["head_ref"] == ""


async def test_parse_issue_with_labels(tmp_path):
    """parse_event extracts label names from an issue's labels list."""
    payload = {
        "action": "labeled",
        "issue": {
            "number": 5,
            "title": "Labelled issue",
            "body": "Has labels",
            "user": {"login": "labeller"},
            "labels": [{"name": "bug"}, {"name": "help wanted"}],
        },
        "repository": {
            "name": "my-repo",
            "owner": {"login": "my-org"},
        },
    }
    event_file = tmp_path / "issue_labels.json"
    event_file.write_text(json.dumps(payload))

    event = parse_event(str(event_file))

    assert event["labels"] == ["bug", "help wanted"]


async def test_parse_pr_extracts_fields_including_refs(tmp_path):
    """parse_event correctly extracts all PR fields including base/head refs."""
    payload = {
        "action": "opened",
        "pull_request": {
            "number": 2,
            "title": "Fix auth module bug",
            "body": "This PR fixes the bug reported in the auth module.",
            "user": {"login": "test-user"},
            "labels": [],
            "base": {"ref": "main"},
            "head": {"ref": "feature/test"},
        },
        "repository": {
            "name": "test-repo",
            "owner": {"login": "test-org"},
        },
    }
    event_file = tmp_path / "pr_event.json"
    event_file.write_text(json.dumps(payload))

    event = parse_event(str(event_file))

    assert event["event_type"] == "pull_request"
    assert event["owner"] == "test-org"
    assert event["repo"] == "test-repo"
    assert event["number"] == 2
    assert event["title"] == "Fix auth module bug"
    assert event["body"] == "This PR fixes the bug reported in the auth module."
    assert event["author"] == "test-user"
    assert event["labels"] == []
    assert event["base_ref"] == "main"
    assert event["head_ref"] == "feature/test"


async def test_parse_issue_comment_event(tmp_path):
    """parse_event extracts comment body/author for issue_comment events."""
    payload = {
        "action": "created",
        "comment": {
            "body": "/triage-continue please analyze this",
            "user": {"login": "commenter-user"},
        },
        "issue": {
            "number": 123,
            "title": "Original issue title",
            "body": "Original issue body that should NOT appear",
            "user": {"login": "original-author"},
            "labels": [{"name": "bug"}],
        },
        "repository": {
            "name": "test-repo",
            "owner": {"login": "test-org"},
        },
    }
    event_file = tmp_path / "issue_comment.json"
    event_file.write_text(json.dumps(payload))

    event = parse_event(str(event_file))

    assert event["event_type"] == "issue_comment"
    assert event["body"] == "/triage-continue please analyze this"
    assert event["author"] == "commenter-user"
    assert event["number"] == 123
    assert event["title"] == "Original issue title"
    assert event["labels"] == ["bug"]


async def test_parse_pr_comment_event(tmp_path):
    """parse_event handles issue_comment events on pull requests."""
    payload = {
        "action": "created",
        "comment": {
            "body": "/pr-review",
            "user": {"login": "reviewer"},
        },
        "issue": {
            "number": 456,
            "title": "PR: Add feature X",
            "body": "PR description",
            "user": {"login": "pr-author"},
            "labels": [{"name": "enhancement"}],
        },
        "pull_request": {"url": "https://api.github.com/repos/test-org/test-repo/pulls/456"},
        "repository": {
            "name": "test-repo",
            "owner": {"login": "test-org"},
        },
    }
    event_file = tmp_path / "pr_comment.json"
    event_file.write_text(json.dumps(payload))

    event = parse_event(str(event_file))

    assert event["event_type"] == "issue_comment"
    assert event["body"] == "/pr-review"
    assert event["author"] == "reviewer"
    assert "pull_request" in event


async def test_unknown_event_raises_value_error(tmp_path):
    """parse_event raises ValueError starting with 'Unknown event' for unknown payloads."""
    payload = {
        "action": "created",
        "unknown_key": "unknown_value",
        "repository": {
            "name": "test-repo",
            "owner": {"login": "test-org"},
        },
    }
    event_file = tmp_path / "unknown_event.json"
    event_file.write_text(json.dumps(payload))

    with pytest.raises(ValueError, match="Unknown event"):
        parse_event(str(event_file))


# ---------------------------------------------------------------------------
# format_context_block tests
# ---------------------------------------------------------------------------


async def test_format_context_block_issue_has_correct_format_no_base_head():
    """format_context_block for issue events has the right structure without Base/Head lines."""
    event = {
        "event_type": "issues",
        "owner": "test-org",
        "repo": "test-repo",
        "number": 1,
        "title": "Test issue",
        "body": "Something is broken in the auth module",
        "author": "test-user",
        "labels": [],
        "base_ref": "",
        "head_ref": "",
    }

    result = format_context_block(event)

    assert result.startswith("[issues: #1 in test-org/test-repo]")
    assert "Title: Test issue" in result
    assert "Body:" in result
    assert "Something is broken in the auth module" in result
    assert "Labels: (none)" in result
    assert "Author: test-user" in result
    # Issue events must NOT have Base/Head lines
    assert "Base:" not in result
    assert "Head:" not in result


async def test_format_pr_includes_base_head():
    """format_context_block for PR events appends Base/Head ref line with Unicode arrow."""
    event = {
        "event_type": "pull_request",
        "owner": "test-org",
        "repo": "test-repo",
        "number": 2,
        "title": "Fix auth module bug",
        "body": "This PR fixes the bug.",
        "author": "test-user",
        "labels": [],
        "base_ref": "main",
        "head_ref": "feature/test",
    }

    result = format_context_block(event)

    assert "Base: main \u2192 Head: feature/test" in result


async def test_labels_join_with_comma_space():
    """format_context_block joins multiple labels with ', '."""
    event = {
        "event_type": "issues",
        "owner": "test-org",
        "repo": "test-repo",
        "number": 3,
        "title": "Multi-label issue",
        "body": "Has multiple labels",
        "author": "someone",
        "labels": ["bug", "help wanted"],
        "base_ref": "",
        "head_ref": "",
    }

    result = format_context_block(event)

    assert "Labels: bug, help wanted" in result


async def test_empty_or_none_body_renders_as_empty_not_none():
    """format_context_block renders empty/None body as '(empty)', never as 'None'."""
    # Test with empty string
    event_empty = {
        "event_type": "issues",
        "owner": "test-org",
        "repo": "test-repo",
        "number": 4,
        "title": "No body issue",
        "body": "",
        "author": "someone",
        "labels": [],
        "base_ref": "",
        "head_ref": "",
    }
    result_empty = format_context_block(event_empty)
    assert "(empty)" in result_empty
    assert "None" not in result_empty

    # Test that body='' (what parse_event emits when body is None) renders as '(empty)'
    event_none_body = {
        "event_type": "issues",
        "owner": "test-org",
        "repo": "test-repo",
        "number": 5,
        "title": "No-body issue",
        "body": "",  # parse_event converts None → '' per spec
        "author": "someone",
        "labels": [],
        "base_ref": "",
        "head_ref": "",
    }
    result_none = format_context_block(event_none_body)
    assert "(empty)" in result_none
    # body line must never contain the literal string 'None'
    body_line_index = result_none.index("Body:") + len("Body:\n")
    body_text_line = result_none[body_line_index:].split("\n")[0]
    assert body_text_line != "None"
