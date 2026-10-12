"""Tests for DTU profile YAML files under .amplifier/digital-twin-universe/profiles/."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

# Root of the amplifier-app-actions repo (parent of this tests/ directory)
_REPO_ROOT = Path(__file__).parent.parent
_DTU_ROOT = _REPO_ROOT / ".amplifier" / "digital-twin-universe"
_PROFILES_DIR = _DTU_ROOT / "profiles"
_FIXTURES_DIR = _DTU_ROOT / "fixtures"


class TestValidatePromptProfile:
    """Validates the validate-prompt.yaml DTU profile structure and content."""

    @pytest.fixture
    def profile_path(self) -> Path:
        return _PROFILES_DIR / "validate-prompt.yaml"

    @pytest.fixture
    def profile(self, profile_path: Path) -> dict:
        """Parse and return the profile YAML."""
        return yaml.safe_load(profile_path.read_text())

    def test_file_exists(self, profile_path: Path) -> None:
        assert profile_path.exists(), (
            f"validate-prompt.yaml not found at {profile_path}"
        )

    def test_valid_yaml(self, profile_path: Path) -> None:
        """Profile must be parseable YAML (no syntax errors)."""
        content = yaml.safe_load(profile_path.read_text())
        assert content is not None
        assert isinstance(content, dict)

    def test_name(self, profile: dict) -> None:
        assert profile["name"] == "validate-prompt"

    def test_base_image(self, profile: dict) -> None:
        assert profile["base"]["image"] == "ubuntu:24.04"

    def test_vars_declared(self, profile: dict) -> None:
        """GITEA_URL and GITEA_TOKEN must be required vars; core_ref and foundation_ref optional."""
        vars_list = profile["vars"]
        var_names = {v["name"] for v in vars_list}
        assert "GITEA_URL" in var_names, "GITEA_URL var not declared"
        assert "GITEA_TOKEN" in var_names, "GITEA_TOKEN var not declared"
        assert "core_ref" in var_names, "core_ref var not declared"
        assert "foundation_ref" in var_names, "foundation_ref var not declared"

    def test_gitea_url_required(self, profile: dict) -> None:
        gitea_url_var = next(v for v in profile["vars"] if v["name"] == "GITEA_URL")
        assert gitea_url_var.get("required") is True

    def test_gitea_token_required(self, profile: dict) -> None:
        gitea_token_var = next(v for v in profile["vars"] if v["name"] == "GITEA_TOKEN")
        assert gitea_token_var.get("required") is True

    def test_core_ref_default_empty(self, profile: dict) -> None:
        core_ref_var = next(v for v in profile["vars"] if v["name"] == "core_ref")
        assert core_ref_var.get("default") == ""

    def test_foundation_ref_default_empty(self, profile: dict) -> None:
        foundation_ref_var = next(
            v for v in profile["vars"] if v["name"] == "foundation_ref"
        )
        assert foundation_ref_var.get("default") == ""

    def test_passthrough_allow_external(self, profile: dict) -> None:
        assert profile["passthrough"]["allow_external"] is True

    def test_passthrough_anthropic_service(self, profile: dict) -> None:
        services = profile["passthrough"]["services"]
        service_names = [s["name"] for s in services]
        assert "anthropic" in service_names

    def test_anthropic_key_env(self, profile: dict) -> None:
        anthropic = next(
            s for s in profile["passthrough"]["services"] if s["name"] == "anthropic"
        )
        assert anthropic["key_env"] == "ANTHROPIC_API_KEY"

    def test_url_rewrites_auth(self, profile: dict) -> None:
        auth = profile["url_rewrites"]["auth"]
        assert auth["username"] == "admin"
        assert auth["token_var"] == "GITEA_TOKEN"

    def test_url_rewrites_no_fast_path(self, profile: dict) -> None:
        assert profile["url_rewrites"]["allow_uv_github_fast_path"] is False

    def test_url_rewrites_boundary_mode(self, profile: dict) -> None:
        assert profile["url_rewrites"]["default_match_mode"] == "boundary"

    def test_url_rewrite_app_actions_rule(self, profile: dict) -> None:
        rules = profile["url_rewrites"]["rules"]
        matches = [r["match"] for r in rules]
        assert "github.com/microsoft/amplifier-app-actions" in matches

    def test_url_rewrite_app_actions_target(self, profile: dict) -> None:
        rules = profile["url_rewrites"]["rules"]
        rule = next(
            r
            for r in rules
            if r["match"] == "github.com/microsoft/amplifier-app-actions"
        )
        assert "${GITEA_URL}/admin/amplifier-app-actions" in rule["target"]

    def test_provision_has_setup_cmds(self, profile: dict) -> None:
        assert "setup_cmds" in profile["provision"]
        assert len(profile["provision"]["setup_cmds"]) >= 5, (
            "Expected at least 5 setup_cmds steps"
        )

    def test_provision_installs_deps(self, profile: dict) -> None:
        """First setup cmd must install system dependencies including jq."""
        first_cmd = profile["provision"]["setup_cmds"][0]
        assert "apt-get" in first_cmd
        assert "jq" in first_cmd

    def test_provision_installs_uv(self, profile: dict) -> None:
        """One setup cmd installs uv via the official installer script."""
        cmds = profile["provision"]["setup_cmds"]
        assert any("astral.sh/uv" in cmd for cmd in cmds), (
            "No step installs uv via astral.sh"
        )

    def test_provision_creates_gitea_test_data(self, profile: dict) -> None:
        """One step creates test-org and test-repo in Gitea."""
        cmds = " ".join(str(c) for c in profile["provision"]["setup_cmds"])
        assert "test-org" in cmds
        assert "test-repo" in cmds

    def test_provision_installs_amplifier_triage(self, profile: dict) -> None:
        """One step installs amplifier-app-actions via uv tool install."""
        cmds = " ".join(str(c) for c in profile["provision"]["setup_cmds"])
        assert "uv tool install" in cmds
        assert "amplifier-app-actions" in cmds

    def test_provision_writes_event_json(self, profile: dict) -> None:
        """One step writes event.json with action='opened'."""
        cmds = " ".join(str(c) for c in profile["provision"]["setup_cmds"])
        assert "event.json" in cmds
        assert '"opened"' in cmds or "'opened'" in cmds or "opened" in cmds

    def test_provision_runs_amplifier_triage(self, profile: dict) -> None:
        """One step runs amplifier-triage with --prompt, --provider, --event-path."""
        cmds = " ".join(str(c) for c in profile["provision"]["setup_cmds"])
        assert "amplifier-triage" in cmds
        assert "--prompt" in cmds
        assert "--provider" in cmds
        assert "--event-path" in cmds

    def test_provision_verifies_comment_count(self, profile: dict) -> None:
        """Verification step checks COMMENT_COUNT >= 1."""
        cmds = " ".join(str(c) for c in profile["provision"]["setup_cmds"])
        assert "COMMENT_COUNT" in cmds
        assert "validation.done" in cmds

    def test_readiness_check(self, profile: dict) -> None:
        """Readiness check must verify /root/validation.done exists."""
        readiness = profile["readiness"]
        assert len(readiness) >= 1
        commands = [r.get("command", "") for r in readiness]
        assert any("validation.done" in cmd for cmd in commands), (
            "No readiness check tests for /root/validation.done"
        )


# ---------------------------------------------------------------------------
# Workspace-level fixture: triage-recipe.yaml
# ---------------------------------------------------------------------------


class TestTriageRecipeFixture:
    """Validates the workspace-level triage-recipe.yaml fixture structure and content."""

    @pytest.fixture
    def fixture_path(self) -> Path:
        return _FIXTURES_DIR / "triage-recipe.yaml"

    @pytest.fixture
    def recipe(self, fixture_path: Path) -> dict:
        """Parse and return the fixture YAML."""
        return yaml.safe_load(fixture_path.read_text())

    def test_file_exists(self, fixture_path: Path) -> None:
        assert fixture_path.exists(), f"triage-recipe.yaml not found at {fixture_path}"

    def test_valid_yaml(self, fixture_path: Path) -> None:
        """Fixture must be parseable YAML (no syntax errors)."""
        content = yaml.safe_load(fixture_path.read_text())
        assert content is not None
        assert isinstance(content, dict)

    def test_name(self, recipe: dict) -> None:
        assert recipe["name"] == "dtu-test-triage"

    def test_description_present(self, recipe: dict) -> None:
        assert "description" in recipe
        assert recipe["description"]

    def test_has_exactly_two_steps(self, recipe: dict) -> None:
        assert len(recipe["steps"]) == 2

    def test_classify_step_exists(self, recipe: dict) -> None:
        step_ids = [s["id"] for s in recipe["steps"]]
        assert "classify" in step_ids

    def test_report_step_exists(self, recipe: dict) -> None:
        step_ids = [s["id"] for s in recipe["steps"]]
        assert "report" in step_ids

    def test_classify_step_has_output_classification(self, recipe: dict) -> None:
        classify = next(s for s in recipe["steps"] if s["id"] == "classify")
        assert classify.get("output") == "classification"

    def test_classify_step_parse_json(self, recipe: dict) -> None:
        classify = next(s for s in recipe["steps"] if s["id"] == "classify")
        assert classify.get("parse_json") is True

    def test_report_step_depends_on_classify(self, recipe: dict) -> None:
        report = next(s for s in recipe["steps"] if s["id"] == "report")
        assert "classify" in report.get("depends_on", [])

    def test_classify_step_is_bash(self, recipe: dict) -> None:
        classify = next(s for s in recipe["steps"] if s["id"] == "classify")
        assert classify.get("type") == "bash"

    def test_report_step_is_bash(self, recipe: dict) -> None:
        report = next(s for s in recipe["steps"] if s["id"] == "report")
        assert report.get("type") == "bash"

    def test_classify_command_contains_bug_pattern(self, recipe: dict) -> None:
        """Classify step must detect bugs via keywords."""
        classify = next(s for s in recipe["steps"] if s["id"] == "classify")
        cmd = classify.get("command", "")
        assert "bug" in cmd.lower()

    def test_classify_command_adds_label(self, recipe: dict) -> None:
        """Classify step must call the GitHub API to add a label."""
        classify = next(s for s in recipe["steps"] if s["id"] == "classify")
        cmd = classify.get("command", "")
        assert "labels" in cmd

    def test_report_command_posts_comment(self, recipe: dict) -> None:
        """Report step must post a comment via GitHub API."""
        report = next(s for s in recipe["steps"] if s["id"] == "report")
        cmd = report.get("command", "")
        assert "comments" in cmd

    def test_classify_env_uses_title(self, recipe: dict) -> None:
        """Classify step env must pass issue title from template context."""
        classify = next(s for s in recipe["steps"] if s["id"] == "classify")
        env = classify.get("env", {})
        assert any("title" in v for v in env.values())

    def test_classify_env_uses_body(self, recipe: dict) -> None:
        """Classify step env must pass issue body from template context."""
        classify = next(s for s in recipe["steps"] if s["id"] == "classify")
        env = classify.get("env", {})
        assert any("body" in v for v in env.values())

    def test_report_env_uses_classification(self, recipe: dict) -> None:
        """Report step env must use the classification output from previous step."""
        report = next(s for s in recipe["steps"] if s["id"] == "report")
        env = report.get("env", {})
        assert any("classification" in v for v in env.values())


# ---------------------------------------------------------------------------
# Workspace-level profile: validate-recipe.yaml
# ---------------------------------------------------------------------------


class TestValidateRecipeProfile:
    """Validates the workspace-level validate-recipe.yaml DTU profile structure and content."""

    @pytest.fixture
    def profile_path(self) -> Path:
        return _PROFILES_DIR / "validate-recipe.yaml"

    @pytest.fixture
    def profile(self, profile_path: Path) -> dict:
        """Parse and return the profile YAML."""
        return yaml.safe_load(profile_path.read_text())

    def test_file_exists(self, profile_path: Path) -> None:
        assert profile_path.exists(), (
            f"validate-recipe.yaml not found at {profile_path}"
        )

    def test_valid_yaml(self, profile_path: Path) -> None:
        """Profile must be parseable YAML (no syntax errors)."""
        content = yaml.safe_load(profile_path.read_text())
        assert content is not None
        assert isinstance(content, dict)

    def test_name(self, profile: dict) -> None:
        assert profile["name"] == "validate-recipe"

    def test_base_image(self, profile: dict) -> None:
        assert profile["base"]["image"] == "ubuntu:24.04"

    def test_vars_declared(self, profile: dict) -> None:
        """GITEA_URL and GITEA_TOKEN must be required vars; core_ref and foundation_ref optional."""
        vars_list = profile["vars"]
        var_names = {v["name"] for v in vars_list}
        assert "GITEA_URL" in var_names, "GITEA_URL var not declared"
        assert "GITEA_TOKEN" in var_names, "GITEA_TOKEN var not declared"
        assert "core_ref" in var_names, "core_ref var not declared"
        assert "foundation_ref" in var_names, "foundation_ref var not declared"

    def test_gitea_url_required(self, profile: dict) -> None:
        gitea_url_var = next(v for v in profile["vars"] if v["name"] == "GITEA_URL")
        assert gitea_url_var.get("required") is True

    def test_gitea_token_required(self, profile: dict) -> None:
        gitea_token_var = next(v for v in profile["vars"] if v["name"] == "GITEA_TOKEN")
        assert gitea_token_var.get("required") is True

    def test_core_ref_default_empty(self, profile: dict) -> None:
        core_ref_var = next(v for v in profile["vars"] if v["name"] == "core_ref")
        assert core_ref_var.get("default") == ""

    def test_foundation_ref_default_empty(self, profile: dict) -> None:
        foundation_ref_var = next(
            v for v in profile["vars"] if v["name"] == "foundation_ref"
        )
        assert foundation_ref_var.get("default") == ""

    def test_passthrough_allow_external(self, profile: dict) -> None:
        assert profile["passthrough"]["allow_external"] is True

    def test_passthrough_anthropic_service(self, profile: dict) -> None:
        services = profile["passthrough"]["services"]
        service_names = [s["name"] for s in services]
        assert "anthropic" in service_names

    def test_anthropic_key_env(self, profile: dict) -> None:
        anthropic = next(
            s for s in profile["passthrough"]["services"] if s["name"] == "anthropic"
        )
        assert anthropic["key_env"] == "ANTHROPIC_API_KEY"

    def test_url_rewrites_auth(self, profile: dict) -> None:
        auth = profile["url_rewrites"]["auth"]
        assert auth["username"] == "admin"
        assert auth["token_var"] == "GITEA_TOKEN"

    def test_url_rewrites_no_fast_path(self, profile: dict) -> None:
        assert profile["url_rewrites"]["allow_uv_github_fast_path"] is False

    def test_url_rewrites_boundary_mode(self, profile: dict) -> None:
        assert profile["url_rewrites"]["default_match_mode"] == "boundary"

    def test_url_rewrite_app_actions_rule(self, profile: dict) -> None:
        rules = profile["url_rewrites"]["rules"]
        matches = [r["match"] for r in rules]
        assert "github.com/microsoft/amplifier-app-actions" in matches

    def test_url_rewrite_app_actions_target(self, profile: dict) -> None:
        rules = profile["url_rewrites"]["rules"]
        rule = next(
            r
            for r in rules
            if r["match"] == "github.com/microsoft/amplifier-app-actions"
        )
        assert "${GITEA_URL}/admin/amplifier-app-actions" in rule["target"]

    def test_provision_has_setup_cmds(self, profile: dict) -> None:
        assert "setup_cmds" in profile["provision"]
        assert len(profile["provision"]["setup_cmds"]) >= 5, (
            "Expected at least 5 setup_cmds steps"
        )

    def test_provision_installs_deps(self, profile: dict) -> None:
        """First setup cmd must install system dependencies including jq."""
        first_cmd = profile["provision"]["setup_cmds"][0]
        assert "apt-get" in first_cmd
        assert "jq" in first_cmd

    def test_provision_installs_uv(self, profile: dict) -> None:
        """One setup cmd installs uv via the official installer script."""
        cmds = profile["provision"]["setup_cmds"]
        assert any("astral.sh/uv" in cmd for cmd in cmds), (
            "No step installs uv via astral.sh"
        )

    def test_provision_creates_recipe_test_repo(self, profile: dict) -> None:
        """One step creates test-org and recipe-test-repo (not test-repo) in Gitea."""
        cmds = " ".join(str(c) for c in profile["provision"]["setup_cmds"])
        assert "test-org" in cmds
        assert "recipe-test-repo" in cmds

    def test_provision_creates_issue_with_error_title(self, profile: dict) -> None:
        """Issue #1 must have 'Login page' or '500' in its title."""
        cmds = " ".join(str(c) for c in profile["provision"]["setup_cmds"])
        assert "Login" in cmds or "500" in cmds

    def test_provision_installs_amplifier_triage(self, profile: dict) -> None:
        """One step installs amplifier-app-actions via uv tool install."""
        cmds = " ".join(str(c) for c in profile["provision"]["setup_cmds"])
        assert "uv tool install" in cmds
        assert "amplifier-app-actions" in cmds

    def test_provision_writes_recipe_file(self, profile: dict) -> None:
        """One step writes the triage recipe YAML to /root/triage-recipe.yaml."""
        cmds = " ".join(str(c) for c in profile["provision"]["setup_cmds"])
        assert "triage-recipe.yaml" in cmds
        assert "RECIPEEOF" in cmds

    def test_provision_writes_event_json(self, profile: dict) -> None:
        """One step writes event.json with action='opened' for recipe-test-repo."""
        cmds = " ".join(str(c) for c in profile["provision"]["setup_cmds"])
        assert "event.json" in cmds
        assert "recipe-test-repo" in cmds

    def test_provision_runs_amplifier_triage_recipe_mode(self, profile: dict) -> None:
        """One step runs amplifier-triage with --recipe-source, --provider, --event-path."""
        cmds = " ".join(str(c) for c in profile["provision"]["setup_cmds"])
        assert "amplifier-triage" in cmds
        assert "--recipe-source" in cmds
        assert "--provider" in cmds
        assert "--event-path" in cmds

    def test_provision_verifies_comment_count(self, profile: dict) -> None:
        """Verification step checks COMMENT_COUNT >= 1."""
        cmds = " ".join(str(c) for c in profile["provision"]["setup_cmds"])
        assert "COMMENT_COUNT" in cmds
        assert "validation.done" in cmds

    def test_provision_verifies_classification_language(self, profile: dict) -> None:
        """Verification step checks comment body for classification terms."""
        cmds = " ".join(str(c) for c in profile["provision"]["setup_cmds"])
        assert "bug" in cmds.lower()

    def test_readiness_check(self, profile: dict) -> None:
        """Readiness check must verify /root/validation.done exists."""
        readiness = profile["readiness"]
        assert len(readiness) >= 1
        commands = [r.get("command", "") for r in readiness]
        assert any("validation.done" in cmd for cmd in commands), (
            "No readiness check tests for /root/validation.done"
        )


# ---------------------------------------------------------------------------
# Workspace-level fixture: triage.dot
# ---------------------------------------------------------------------------


class TestTriageDotFixture:
    """Validates the workspace-level triage.dot attractor fixture structure."""

    @pytest.fixture
    def fixture_path(self) -> Path:
        return _FIXTURES_DIR / "triage.dot"

    @pytest.fixture
    def dot_content(self, fixture_path: Path) -> str:
        return fixture_path.read_text()

    def test_file_exists(self, fixture_path: Path) -> None:
        assert fixture_path.exists(), f"triage.dot not found at {fixture_path}"

    def test_is_digraph_named_triage(self, dot_content: str) -> None:
        """File must be a digraph named 'triage'."""
        assert "digraph triage" in dot_content, "Expected 'digraph triage' declaration"

    def test_has_label(self, dot_content: str) -> None:
        """Graph must have a label containing 'Issue Triage Attractor'."""
        assert "Issue Triage Attractor" in dot_content, (
            "Expected graph label 'Issue Triage Attractor (DTU Test)'"
        )

    def test_has_rankdir_tb(self, dot_content: str) -> None:
        """Graph must declare rankdir=TB."""
        assert "rankdir" in dot_content and "TB" in dot_content, (
            "Expected rankdir=TB in graph attributes"
        )

    def test_has_classify_node(self, dot_content: str) -> None:
        """Graph must declare a 'classify' node."""
        assert "classify" in dot_content, "Expected 'classify' node in DOT graph"

    def test_has_report_node(self, dot_content: str) -> None:
        """Graph must declare a 'report' node."""
        assert "report" in dot_content, "Expected 'report' node in DOT graph"

    def test_classify_has_label(self, dot_content: str) -> None:
        """Classify node must have label 'Classify Issue'."""
        assert "Classify Issue" in dot_content, (
            "Expected classify node label 'Classify Issue'"
        )

    def test_report_has_label(self, dot_content: str) -> None:
        """Report node must have label 'Post Report'."""
        assert "Post Report" in dot_content, "Expected report node label 'Post Report'"

    def test_classify_has_description(self, dot_content: str) -> None:
        """Classify node must have a description mentioning github_add_label."""
        assert "github_add_label" in dot_content, (
            "Expected classify node description mentioning github_add_label"
        )

    def test_report_has_description(self, dot_content: str) -> None:
        """Report node must have a description mentioning github_post_comment."""
        assert "github_post_comment" in dot_content, (
            "Expected report node description mentioning github_post_comment"
        )

    def test_edge_classify_to_report(self, dot_content: str) -> None:
        """Graph must have edge from classify to report."""
        assert "classify -> report" in dot_content, "Expected edge 'classify -> report'"

    def test_valid_dot_syntax(self, dot_content: str) -> None:
        """File must have balanced braces."""
        assert "{" in dot_content and "}" in dot_content, (
            "Expected opening and closing braces in DOT file"
        )
        open_count = dot_content.count("{")
        close_count = dot_content.count("}")
        assert open_count == close_count, (
            f"Unbalanced braces: {open_count} open, {close_count} close"
        )


# ---------------------------------------------------------------------------
# Workspace-level profile: validate-attractor.yaml
# ---------------------------------------------------------------------------


class TestValidateAttractorProfile:
    """Validates the workspace-level validate-attractor.yaml DTU profile."""

    @pytest.fixture
    def profile_path(self) -> Path:
        return _PROFILES_DIR / "validate-attractor.yaml"

    @pytest.fixture
    def profile(self, profile_path: Path) -> dict:
        """Parse and return the profile YAML."""
        return yaml.safe_load(profile_path.read_text())

    def test_file_exists(self, profile_path: Path) -> None:
        assert profile_path.exists(), (
            f"validate-attractor.yaml not found at {profile_path}"
        )

    def test_valid_yaml(self, profile_path: Path) -> None:
        """Profile must be parseable YAML (no syntax errors)."""
        content = yaml.safe_load(profile_path.read_text())
        assert content is not None
        assert isinstance(content, dict)

    def test_name(self, profile: dict) -> None:
        assert profile["name"] == "validate-attractor"

    def test_base_image(self, profile: dict) -> None:
        assert profile["base"]["image"] == "ubuntu:24.04"

    def test_vars_declared(self, profile: dict) -> None:
        """Direct Gitea checkout needs only the URL and token, not dependency refs."""
        assert {v["name"] for v in profile["vars"]} == {"GITEA_URL", "GITEA_TOKEN"}

    def test_gitea_url_required(self, profile: dict) -> None:
        gitea_url_var = next(v for v in profile["vars"] if v["name"] == "GITEA_URL")
        assert gitea_url_var.get("required") is True

    def test_gitea_token_required(self, profile: dict) -> None:
        gitea_token_var = next(v for v in profile["vars"] if v["name"] == "GITEA_TOKEN")
        assert gitea_token_var.get("required") is True

    def test_passthrough_allow_external(self, profile: dict) -> None:
        assert profile["passthrough"]["allow_external"] is True

    def test_passthrough_anthropic_service(self, profile: dict) -> None:
        services = profile["passthrough"]["services"]
        service_names = [s["name"] for s in services]
        assert "anthropic" in service_names

    def test_anthropic_key_env(self, profile: dict) -> None:
        anthropic = next(
            s for s in profile["passthrough"]["services"] if s["name"] == "anthropic"
        )
        assert anthropic["key_env"] == "ANTHROPIC_API_KEY"

    def test_direct_gitea_clone_and_credentials(self, profile: dict) -> None:
        """Direct cloning authenticates without proxy URL rewrites."""
        install = next(
            cmd for cmd in profile["provision"]["setup_cmds"] if "git clone" in cmd
        )
        assert (
            'git clone "${GITEA_URL}/admin/amplifier-app-actions.git" '
            "/root/amplifier-app-actions"
        ) in [line.strip() for line in install.splitlines()]
        assert "git config --global credential.helper store" in install
        assert '"${GITEA_TOKEN}" "${GITEA_URL#http://}"' in install
        assert ">> /root/.git-credentials" in install

    def test_provision_has_setup_cmds(self, profile: dict) -> None:
        assert "setup_cmds" in profile["provision"]
        assert len(profile["provision"]["setup_cmds"]) >= 5, (
            "Expected at least 5 setup_cmds steps"
        )

    def test_provision_installs_deps(self, profile: dict) -> None:
        """First setup cmd must install system dependencies including jq."""
        first_cmd = profile["provision"]["setup_cmds"][0]
        assert "apt-get" in first_cmd
        assert "jq" in first_cmd

    def test_provision_installs_uv(self, profile: dict) -> None:
        """One setup cmd installs uv via the official installer script."""
        cmds = profile["provision"]["setup_cmds"]
        assert any("astral.sh/uv" in cmd for cmd in cmds), (
            "No step installs uv via astral.sh"
        )

    def test_provision_creates_attractor_test_repo(self, profile: dict) -> None:
        """One step creates test-org and attractor-test-repo in Gitea."""
        cmds = " ".join(str(c) for c in profile["provision"]["setup_cmds"])
        assert "test-org" in cmds
        assert "attractor-test-repo" in cmds

    def test_provision_creates_issue_with_connection_pool_title(
        self, profile: dict
    ) -> None:
        """Issue #1 must mention 'Connection pool' in its title."""
        cmds = " ".join(str(c) for c in profile["provision"]["setup_cmds"])
        assert "Connection pool" in cmds or "connection pool" in cmds.lower()

    def test_provision_creates_labels_including_performance(
        self, profile: dict
    ) -> None:
        """Setup step must create labels including bug and performance."""
        cmds = " ".join(str(c) for c in profile["provision"]["setup_cmds"])
        assert "bug" in cmds
        assert "performance" in cmds

    def test_provision_installs_amplifier_triage(self, profile: dict) -> None:
        """Sync the checkout so bundled files and the venv CLI remain colocated."""
        install = next(
            cmd for cmd in profile["provision"]["setup_cmds"] if "git clone" in cmd
        )
        lines = [line.strip() for line in install.splitlines()]
        assert "cd /root/amplifier-app-actions" in lines
        assert "uv sync" in lines
        assert lines.index("cd /root/amplifier-app-actions") < lines.index("uv sync")
        assert ".venv/bin/amplifier-triage --help" in lines

    def test_provision_copies_maintained_dot_fixture(self, profile: dict) -> None:
        """Use the maintained graph, not the obsolete start/end-less heredoc."""
        cmds = "\n".join(profile["provision"]["setup_cmds"]).replace("\\\n", "")
        lines = [" ".join(line.split()) for line in cmds.splitlines()]
        assert (
            "cp /root/amplifier-app-actions/.amplifier/digital-twin-universe/"
            "fixtures/triage.dot /root/triage.dot"
        ) in lines
        fixture = (_FIXTURES_DIR / "triage.dot").read_text()
        assert "shape=Mdiamond" in fixture
        assert "shape=Msquare" in fixture
        assert "start -> classify" in fixture
        assert "report -> end" in fixture

    def test_provision_writes_event_json_for_attractor_repo(
        self, profile: dict
    ) -> None:
        """One step writes event.json referencing attractor-test-repo."""
        cmds = " ".join(str(c) for c in profile["provision"]["setup_cmds"])
        assert "event.json" in cmds
        assert "attractor-test-repo" in cmds

    def test_provision_runs_amplifier_triage_attractor_mode(
        self, profile: dict
    ) -> None:
        """One step runs amplifier-triage with --attractor-source, --provider, --event-path."""
        cmds = " ".join(str(c) for c in profile["provision"]["setup_cmds"])
        assert "amplifier-triage" in cmds
        assert "--attractor-source" in cmds
        assert "--provider" in cmds
        assert "--event-path" in cmds

    def test_provision_sets_github_api_url(self, profile: dict) -> None:
        """Run step must set GITHUB_API_URL pointing to Gitea."""
        cmds = " ".join(str(c) for c in profile["provision"]["setup_cmds"])
        assert "GITHUB_API_URL" in cmds

    def test_provision_verifies_comment_count(self, profile: dict) -> None:
        """Verification step checks COMMENT_COUNT >= 1."""
        cmds = " ".join(str(c) for c in profile["provision"]["setup_cmds"])
        assert "COMMENT_COUNT" in cmds
        assert "validation.done" in cmds

    def test_readiness_check_for_attractor(self, profile: dict) -> None:
        """Readiness check must verify /root/validation.done exists."""
        readiness = profile["readiness"]
        assert len(readiness) >= 1
        commands = [r.get("command", "") for r in readiness]
        assert any("validation.done" in cmd for cmd in commands), (
            "No readiness check tests for /root/validation.done"
        )


# ---------------------------------------------------------------------------
# Workspace-level profile: triage-sandbox.yaml
# ---------------------------------------------------------------------------


class TestTriageSandboxProfile:
    """Validates the workspace-level triage-sandbox.yaml DTU profile."""

    @pytest.fixture
    def profile_path(self) -> Path:
        return _PROFILES_DIR / "triage-sandbox.yaml"

    @pytest.fixture
    def profile(self, profile_path: Path) -> dict:
        """Parse and return the profile YAML."""
        return yaml.safe_load(profile_path.read_text())

    def test_file_exists(self, profile_path: Path) -> None:
        assert profile_path.exists(), f"triage-sandbox.yaml not found at {profile_path}"

    def test_valid_yaml(self, profile_path: Path) -> None:
        """Profile must be parseable YAML (no syntax errors)."""
        content = yaml.safe_load(profile_path.read_text())
        assert content is not None
        assert isinstance(content, dict)

    def test_name(self, profile: dict) -> None:
        assert profile["name"] == "triage-sandbox"

    def test_base_image(self, profile: dict) -> None:
        assert profile["base"]["image"] == "ubuntu:24.04"

    def test_description_mentions_persistent_gitea(self, profile: dict) -> None:
        """Description must mention persistent Gitea sandbox."""
        desc = profile.get("description", "")
        assert "Gitea" in desc or "gitea" in desc, "Description must mention Gitea"
        assert "persist" in desc.lower() or "sandbox" in desc.lower(), (
            "Description must mention 'persist' or 'sandbox'"
        )

    def test_networking_expose_port_3000(self, profile: dict) -> None:
        """networking.expose_ports must forward host:3000 → container:3000."""
        expose_ports = profile["networking"]["expose_ports"]
        assert any(
            p.get("host_port") == 3000 and p.get("container_port") == 3000
            for p in expose_ports
        ), "Expected host_port=3000, container_port=3000 in networking.expose_ports"

    def test_lifecycle_persist_true(self, profile: dict) -> None:
        """lifecycle.persist must be true (non-ephemeral sandbox)."""
        assert profile["lifecycle"]["persist"] is True, "lifecycle.persist must be true"

    def test_vars_repos_required(self, profile: dict) -> None:
        """repos var must be declared and required."""
        var_names = {v["name"] for v in profile["vars"]}
        assert "repos" in var_names, "'repos' var not declared"
        repos_var = next(v for v in profile["vars"] if v["name"] == "repos")
        assert repos_var.get("required") is True, "'repos' var must be required"

    def test_vars_seed_from_default_manual(self, profile: dict) -> None:
        """seed_from var must default to 'manual'."""
        var_names = {v["name"] for v in profile["vars"]}
        assert "seed_from" in var_names, "'seed_from' var not declared"
        seed_var = next(v for v in profile["vars"] if v["name"] == "seed_from")
        assert seed_var.get("default") == "manual", "seed_from must default to 'manual'"

    def test_vars_gh_token_default_empty(self, profile: dict) -> None:
        """GH_TOKEN var must default to empty string."""
        var_names = {v["name"] for v in profile["vars"]}
        assert "GH_TOKEN" in var_names, "'GH_TOKEN' var not declared"
        gh_token_var = next(v for v in profile["vars"] if v["name"] == "GH_TOKEN")
        assert gh_token_var.get("default") == "", (
            "GH_TOKEN must default to empty string"
        )

    def test_vars_gitea_port_default_3000(self, profile: dict) -> None:
        """GITEA_PORT var must default to '3000'."""
        var_names = {v["name"] for v in profile["vars"]}
        assert "GITEA_PORT" in var_names, "'GITEA_PORT' var not declared"
        port_var = next(v for v in profile["vars"] if v["name"] == "GITEA_PORT")
        assert str(port_var.get("default")) == "3000", (
            "GITEA_PORT must default to '3000'"
        )

    def test_passthrough_allow_external(self, profile: dict) -> None:
        assert profile["passthrough"]["allow_external"] is True

    def test_passthrough_env_includes_gh_token(self, profile: dict) -> None:
        """passthrough.env must include GH_TOKEN for GitHub seeding."""
        env_list = profile["passthrough"].get("env", [])
        assert "GH_TOKEN" in env_list, "passthrough.env must include GH_TOKEN"

    def test_provision_has_setup_cmds(self, profile: dict) -> None:
        assert "setup_cmds" in profile["provision"]
        assert len(profile["provision"]["setup_cmds"]) >= 4, (
            "Expected at least 4 setup_cmds steps"
        )

    def test_provision_installs_system_deps(self, profile: dict) -> None:
        """First setup cmd installs git, curl, jq, python3."""
        first_cmd = profile["provision"]["setup_cmds"][0]
        assert "apt-get" in first_cmd
        assert "jq" in first_cmd
        assert "git" in first_cmd

    def test_provision_installs_gitea(self, profile: dict) -> None:
        """One step downloads gitea binary and configures it."""
        cmds = " ".join(str(c) for c in profile["provision"]["setup_cmds"])
        assert "gitea" in cmds.lower()
        assert "1.21.11" in cmds or "gitea" in cmds

    def test_provision_starts_gitea_web(self, profile: dict) -> None:
        """One step starts the Gitea web server."""
        cmds = " ".join(str(c) for c in profile["provision"]["setup_cmds"])
        assert "gitea web" in cmds or "nohup gitea" in cmds

    def test_provision_creates_admin_user(self, profile: dict) -> None:
        """One step creates the Gitea admin user."""
        cmds = " ".join(str(c) for c in profile["provision"]["setup_cmds"])
        assert "admin" in cmds
        assert "admin123" in cmds

    def test_provision_generates_api_token(self, profile: dict) -> None:
        """One step generates and saves the Gitea API token."""
        cmds = " ".join(str(c) for c in profile["provision"]["setup_cmds"])
        assert "GITEA_TOKEN" in cmds
        assert "gitea_env" in cmds or "GITEA_TOKEN=" in cmds

    def test_provision_provisions_repos_from_var(self, profile: dict) -> None:
        """One step parses the repos var and provisions each org/repo."""
        cmds = " ".join(str(c) for c in profile["provision"]["setup_cmds"])
        assert "${repos}" in cmds or "repos" in cmds
        # Must use IFS or loop to parse comma-separated list
        assert "IFS" in cmds or "for " in cmds

    def test_provision_creates_org_idempotent(self, profile: dict) -> None:
        """Org creation must be idempotent (ignore 422)."""
        cmds = " ".join(str(c) for c in profile["provision"]["setup_cmds"])
        assert "orgs" in cmds
        assert "|| true" in cmds or "422" in cmds

    def test_provision_handles_github_seeding(self, profile: dict) -> None:
        """Repo provisioning checks seed_from=github and mirrors repos."""
        cmds = " ".join(str(c) for c in profile["provision"]["setup_cmds"])
        assert "github" in cmds.lower()
        assert "seed_from" in cmds or "mirror" in cmds

    def test_provision_prints_export_commands(self, profile: dict) -> None:
        """Final step prints export commands for GITHUB_API_URL, GITHUB_CLONE_URL, GITHUB_TOKEN."""
        cmds = " ".join(str(c) for c in profile["provision"]["setup_cmds"])
        assert "GITHUB_API_URL" in cmds
        assert "GITHUB_CLONE_URL" in cmds
        assert "GITHUB_TOKEN" in cmds

    def test_provision_prints_amplifier_triage_example(self, profile: dict) -> None:
        """Final step prints an example amplifier-triage command."""
        cmds = " ".join(str(c) for c in profile["provision"]["setup_cmds"])
        assert "amplifier-triage" in cmds

    def test_provision_touches_sandbox_ready(self, profile: dict) -> None:
        """Final step touches /root/sandbox.ready."""
        cmds = " ".join(str(c) for c in profile["provision"]["setup_cmds"])
        assert "sandbox.ready" in cmds

    def test_readiness_check_sandbox_ready(self, profile: dict) -> None:
        """Readiness check must verify /root/sandbox.ready exists."""
        readiness = profile["readiness"]
        assert len(readiness) >= 1
        commands = [r.get("command", "") for r in readiness]
        assert any("sandbox.ready" in cmd for cmd in commands), (
            "No readiness check tests for /root/sandbox.ready"
        )

    def test_no_assertions_section(self, profile: dict) -> None:
        """Triage sandbox must NOT have an assertions section."""
        assert "assertions" not in profile, (
            "triage-sandbox must not have assertions — human reviews Gitea"
        )


# ---------------------------------------------------------------------------
# Generic dependency override: pypi_overrides + url_rewrites foundation rule
# validate-attractor deliberately uses default dependencies instead.
# ---------------------------------------------------------------------------


class TestGenericDepOverrideValidateRecipe:
    """pypi_overrides block and foundation url_rewrite in validate-recipe.yaml."""

    @pytest.fixture
    def profile(self) -> dict:
        return yaml.safe_load((_PROFILES_DIR / "validate-recipe.yaml").read_text())

    def test_pypi_overrides_present(self, profile: dict) -> None:
        """Profile must declare a pypi_overrides block."""
        assert "pypi_overrides" in profile, "pypi_overrides block is missing"

    def test_pypi_overrides_has_amplifier_core(self, profile: dict) -> None:
        """pypi_overrides must include an amplifier-core package entry."""
        packages = profile["pypi_overrides"]["packages"]
        names = [p["name"] for p in packages]
        assert "amplifier-core" in names, "pypi_overrides missing amplifier-core entry"

    def test_amplifier_core_wheel_from_git(self, profile: dict) -> None:
        """amplifier-core override uses wheel_from_git pointing to Gitea mirror."""
        packages = profile["pypi_overrides"]["packages"]
        core_pkg = next(p for p in packages if p["name"] == "amplifier-core")
        wfg = core_pkg["wheel_from_git"]
        assert "${GITEA_URL}/admin/amplifier-core.git" in wfg["repo"]
        assert "${core_ref}" in wfg["ref"]

    def test_url_rewrite_foundation_rule(self, profile: dict) -> None:
        """url_rewrites must include a rule for amplifier-foundation."""
        rules = profile["url_rewrites"]["rules"]
        matches = [r["match"] for r in rules]
        assert "github.com/microsoft/amplifier-foundation" in matches, (
            "Missing url_rewrite rule for amplifier-foundation"
        )

    def test_url_rewrite_foundation_target(self, profile: dict) -> None:
        """amplifier-foundation rule must redirect to local Gitea mirror."""
        rules = profile["url_rewrites"]["rules"]
        rule = next(
            r
            for r in rules
            if r["match"] == "github.com/microsoft/amplifier-foundation"
        )
        assert "${GITEA_URL}/admin/amplifier-foundation" in rule["target"]


class TestDefaultDepsValidateAttractor:
    """The direct checkout uses default deps, without implicit local overrides."""

    @pytest.fixture
    def profile(self) -> dict:
        return yaml.safe_load((_PROFILES_DIR / "validate-attractor.yaml").read_text())

    def test_no_implicit_pypi_override(self, profile: dict) -> None:
        assert "pypi_overrides" not in profile

    def test_no_proxy_rewrites(self, profile: dict) -> None:
        assert "url_rewrites" not in profile

    def test_external_dependency_access(self, profile: dict) -> None:
        assert profile["passthrough"]["allow_external"] is True


# ---------------------------------------------------------------------------
# Workspace-level profile: validate-multi-repo.yaml
# ---------------------------------------------------------------------------


class TestValidateMultiRepoProfile:
    """Validates the workspace-level validate-multi-repo.yaml DTU profile."""

    @pytest.fixture
    def profile_path(self) -> Path:
        return _PROFILES_DIR / "validate-multi-repo.yaml"

    @pytest.fixture
    def profile(self, profile_path: Path) -> dict:
        return yaml.safe_load(profile_path.read_text())

    def test_file_exists(self, profile_path: Path) -> None:
        assert profile_path.exists(), (
            f"validate-multi-repo.yaml not found at {profile_path}"
        )

    def test_valid_yaml(self, profile_path: Path) -> None:
        content = yaml.safe_load(profile_path.read_text())
        assert content is not None
        assert isinstance(content, dict)

    def test_name(self, profile: dict) -> None:
        assert profile["name"] == "validate-multi-repo"

    def test_base_image(self, profile: dict) -> None:
        assert profile["base"]["image"] == "ubuntu:24.04"

    def test_vars_declared(self, profile: dict) -> None:
        var_names = {v["name"] for v in profile["vars"]}
        assert "GITEA_URL" in var_names
        assert "GITEA_TOKEN" in var_names
        assert "core_ref" in var_names
        assert "foundation_ref" in var_names

    def test_core_ref_default_empty(self, profile: dict) -> None:
        core_ref_var = next(v for v in profile["vars"] if v["name"] == "core_ref")
        assert core_ref_var.get("default") == ""

    def test_foundation_ref_default_empty(self, profile: dict) -> None:
        foundation_ref_var = next(
            v for v in profile["vars"] if v["name"] == "foundation_ref"
        )
        assert foundation_ref_var.get("default") == ""

    def test_url_rewrite_app_actions_rule(self, profile: dict) -> None:
        rules = profile["url_rewrites"]["rules"]
        matches = [r["match"] for r in rules]
        assert "github.com/microsoft/amplifier-app-actions" in matches

    def test_url_rewrite_foundation_rule(self, profile: dict) -> None:
        rules = profile["url_rewrites"]["rules"]
        matches = [r["match"] for r in rules]
        assert "github.com/microsoft/amplifier-foundation" in matches

    def test_pypi_overrides_present(self, profile: dict) -> None:
        assert "pypi_overrides" in profile

    def test_pypi_overrides_has_amplifier_core(self, profile: dict) -> None:
        packages = profile["pypi_overrides"]["packages"]
        names = [p["name"] for p in packages]
        assert "amplifier-core" in names

    def test_amplifier_core_wheel_from_git(self, profile: dict) -> None:
        packages = profile["pypi_overrides"]["packages"]
        core_pkg = next(p for p in packages if p["name"] == "amplifier-core")
        wfg = core_pkg["wheel_from_git"]
        assert "${GITEA_URL}/admin/amplifier-core.git" in wfg["repo"]
        assert "${core_ref}" in wfg["ref"]

    def test_provision_creates_three_repos(self, profile: dict) -> None:
        cmds = " ".join(str(c) for c in profile["provision"]["setup_cmds"])
        assert "service-api" in cmds
        assert "shared-lib" in cmds
        assert "client-sdk" in cmds

    def test_provision_uses_workspace_map(self, profile: dict) -> None:
        cmds = " ".join(str(c) for c in profile["provision"]["setup_cmds"])
        assert "workspace-map" in cmds or "TRIAGE_CONTEXT_MAP_PATH" in cmds

    def test_provision_verifies_repo_names_in_comment(self, profile: dict) -> None:
        cmds = " ".join(str(c) for c in profile["provision"]["setup_cmds"])
        assert "service-api" in cmds
        assert "validation.done" in cmds

    def test_readiness_check(self, profile: dict) -> None:
        readiness = profile["readiness"]
        commands = [r.get("command", "") for r in readiness]
        assert any("validation.done" in cmd for cmd in commands)


# ---------------------------------------------------------------------------
# Workspace-level profile: validate-prompt.yaml (generic dependency overrides)
# ---------------------------------------------------------------------------


class TestValidatePromptWorkspaceProfile:
    """Validates the workspace-level validate-prompt.yaml DTU profile."""

    @pytest.fixture
    def profile_path(self) -> Path:
        return _PROFILES_DIR / "validate-prompt.yaml"

    @pytest.fixture
    def profile(self, profile_path: Path) -> dict:
        return yaml.safe_load(profile_path.read_text())

    def test_file_exists(self, profile_path: Path) -> None:
        assert profile_path.exists(), (
            f"workspace validate-prompt.yaml not found at {profile_path}"
        )

    def test_valid_yaml(self, profile_path: Path) -> None:
        content = yaml.safe_load(profile_path.read_text())
        assert content is not None
        assert isinstance(content, dict)

    def test_name(self, profile: dict) -> None:
        assert profile["name"] == "validate-prompt"

    def test_base_image(self, profile: dict) -> None:
        assert profile["base"]["image"] == "ubuntu:24.04"

    def test_vars_declared(self, profile: dict) -> None:
        var_names = {v["name"] for v in profile["vars"]}
        assert "GITEA_URL" in var_names
        assert "GITEA_TOKEN" in var_names
        assert "core_ref" in var_names
        assert "foundation_ref" in var_names

    def test_core_ref_default_empty(self, profile: dict) -> None:
        core_ref_var = next(v for v in profile["vars"] if v["name"] == "core_ref")
        assert core_ref_var.get("default") == ""

    def test_foundation_ref_default_empty(self, profile: dict) -> None:
        foundation_ref_var = next(
            v for v in profile["vars"] if v["name"] == "foundation_ref"
        )
        assert foundation_ref_var.get("default") == ""

    def test_passthrough_anthropic_service(self, profile: dict) -> None:
        services = profile["passthrough"]["services"]
        service_names = [s["name"] for s in services]
        assert "anthropic" in service_names

    def test_url_rewrite_app_actions_rule(self, profile: dict) -> None:
        rules = profile["url_rewrites"]["rules"]
        matches = [r["match"] for r in rules]
        assert "github.com/microsoft/amplifier-app-actions" in matches

    def test_url_rewrite_foundation_rule(self, profile: dict) -> None:
        """Foundation url_rewrite rule must be present (generic dep override pattern)."""
        rules = profile["url_rewrites"]["rules"]
        matches = [r["match"] for r in rules]
        assert "github.com/microsoft/amplifier-foundation" in matches

    def test_pypi_overrides_present(self, profile: dict) -> None:
        """pypi_overrides block must exist."""
        assert "pypi_overrides" in profile

    def test_pypi_overrides_has_amplifier_core(self, profile: dict) -> None:
        packages = profile["pypi_overrides"]["packages"]
        names = [p["name"] for p in packages]
        assert "amplifier-core" in names

    def test_amplifier_core_wheel_from_git(self, profile: dict) -> None:
        packages = profile["pypi_overrides"]["packages"]
        core_pkg = next(p for p in packages if p["name"] == "amplifier-core")
        wfg = core_pkg["wheel_from_git"]
        assert "${GITEA_URL}/admin/amplifier-core.git" in wfg["repo"]
        assert "${core_ref}" in wfg["ref"]

    def test_provision_creates_gitea_test_data(self, profile: dict) -> None:
        cmds = " ".join(str(c) for c in profile["provision"]["setup_cmds"])
        assert "test-org" in cmds
        assert "test-repo" in cmds

    def test_provision_installs_amplifier_triage(self, profile: dict) -> None:
        cmds = " ".join(str(c) for c in profile["provision"]["setup_cmds"])
        assert "uv tool install" in cmds
        assert "amplifier-app-actions" in cmds

    def test_provision_verifies_comment_count(self, profile: dict) -> None:
        cmds = " ".join(str(c) for c in profile["provision"]["setup_cmds"])
        assert "COMMENT_COUNT" in cmds
        assert "validation.done" in cmds

    def test_readiness_check(self, profile: dict) -> None:
        readiness = profile["readiness"]
        commands = [r.get("command", "") for r in readiness]
        assert any("validation.done" in cmd for cmd in commands)


# ---------------------------------------------------------------------------
# action.yml: enable_reproduction input + conditional Incus bootstrap steps
# ---------------------------------------------------------------------------


class TestActionYml:
    """Validates enable_reproduction input and conditional Incus bootstrap steps in action.yml."""

    @pytest.fixture(scope="class")
    def action(self) -> dict:
        """Parse and return the action.yml from the repo root."""
        action_path = _REPO_ROOT / "action.yml"
        return yaml.safe_load(action_path.read_text())

    def test_enable_reproduction_input_exists(self, action: dict) -> None:
        """action.yml inputs must include enable_reproduction key."""
        assert "enable_reproduction" in action["inputs"]

    def test_enable_reproduction_default_is_false(self, action: dict) -> None:
        """enable_reproduction default must be the string 'false' (not bool)."""
        default = action["inputs"]["enable_reproduction"]["default"]
        assert default == "false"

    def test_conditional_steps_exist(self, action: dict) -> None:
        """At least one step must be gated with if: inputs.enable_reproduction == 'true'."""
        steps = action["runs"]["steps"]
        conditional = [
            s for s in steps if s.get("if") == "inputs.enable_reproduction == 'true'"
        ]
        assert len(conditional) >= 1

    def test_iptables_fix_step_present(self, action: dict) -> None:
        """A conditional step must contain 'nft flush ruleset'."""
        steps = action["runs"]["steps"]
        conditional_runs = [
            s.get("run", "")
            for s in steps
            if s.get("if") == "inputs.enable_reproduction == 'true'"
        ]
        combined = " ".join(conditional_runs)
        assert "nft flush ruleset" in combined

    def test_incus_init_step_present(self, action: dict) -> None:
        """A conditional step must contain 'incus admin init'."""
        steps = action["runs"]["steps"]
        conditional_runs = [
            s.get("run", "")
            for s in steps
            if s.get("if") == "inputs.enable_reproduction == 'true'"
        ]
        combined = " ".join(conditional_runs)
        assert "incus admin init" in combined
