"""Tests for workflow routing: loading and merging."""

from sdlc_mcp.config import Config, Scope, SourceConfig
from sdlc_mcp.hierarchy import resolve_hierarchy
from sdlc_mcp.merge import merge_workflows_for_hierarchy
from sdlc_mcp.server import get_workflows, init_config
from sdlc_mcp.sources import local as _local  # noqa: F401
from sdlc_mcp.workflows import (
    Workflow,
    _load_workflows_from_file,
    merge_workflows,
)


def test_load_workflows_from_file(tmp_path):
    wf_file = tmp_path / "workflows.yml"
    wf_file.write_text("""
workflows:
  bugfix:
    type: workflow
    triggers: ["fix bug", "bugfix"]
    jira_types: ["Bug"]
    requires: ["git"]
    description: "Fix a bug"
  code-review:
    type: review
    triggers: ["review code"]
    description: "Review code changes"
""")
    workflows = _load_workflows_from_file(wf_file)
    assert len(workflows) == 2
    assert workflows["bugfix"].triggers == ["fix bug", "bugfix"]
    assert workflows["bugfix"].jira_types == ["Bug"]
    assert workflows["code-review"].type == "review"


def test_load_missing_file(tmp_path):
    workflows = _load_workflows_from_file(tmp_path / "nope.yml")
    assert workflows == {}


def test_load_empty_file(tmp_path):
    wf_file = tmp_path / "workflows.yml"
    wf_file.write_text("")
    assert _load_workflows_from_file(wf_file) == {}


def test_merge_workflows_field_level():
    org = {
        "bugfix": Workflow(
            id="bugfix",
            triggers=["fix bug", "bugfix"],
            jira_types=["Bug"],
            requires=["git"],
            description="Fix a bug",
        ),
    }
    team = {
        "bugfix": Workflow(
            id="bugfix",
            requires=["git", "controller-ci"],
        ),
    }
    merged = merge_workflows([org, team])

    wf = merged["bugfix"]
    assert wf.triggers == ["fix bug", "bugfix"]
    assert wf.requires == ["git", "controller-ci"]
    assert wf.description == "Fix a bug"


def test_merge_workflows_additive():
    org = {
        "bugfix": Workflow(id="bugfix", triggers=["fix bug"]),
    }
    team = {
        "deploy": Workflow(id="deploy", triggers=["deploy"]),
    }
    merged = merge_workflows([org, team])
    assert "bugfix" in merged
    assert "deploy" in merged


def test_merge_workflows_empty_levels():
    org = {
        "bugfix": Workflow(id="bugfix", triggers=["fix bug"]),
    }
    merged = merge_workflows([{}, org, {}])
    assert "bugfix" in merged


def _setup_with_workflows(tmp_path):
    org_dir = tmp_path / "org"
    org_dir.mkdir()
    (org_dir / "testing.md").write_text("# Testing")
    (org_dir / "workflows.yml").write_text("""
workflows:
  bugfix:
    type: workflow
    triggers: ["fix bug", "bugfix"]
    jira_types: ["Bug"]
    requires: ["git", "jira"]
    description: "Fix a triaged bug"
  story-implementation:
    type: workflow
    triggers: ["implement story", "start story"]
    jira_types: ["Story"]
    requires: ["git", "jira"]
    description: "Implement a Jira story"
""")

    team_dir = tmp_path / "team"
    team_dir.mkdir()
    (team_dir / "workflows.yml").write_text("""
workflows:
  bugfix:
    requires: ["git", "jira", "controller-ci"]
  controller-deploy:
    type: workflow
    triggers: ["deploy controller"]
    description: "Controller-specific deployment"
""")

    return Config(
        scopes=[
            Scope(
                name="aap",
                sources=[SourceConfig(type="local", path=str(org_dir))],
            ),
            Scope(
                name="controller",
                repos=["awx"],
                sources=[SourceConfig(type="local", path=str(team_dir))],
            ),
        ]
    )


def test_merge_workflows_for_hierarchy(tmp_path):
    config = _setup_with_workflows(tmp_path)
    hierarchy = resolve_hierarchy(config, "ansible/awx")
    workflows = merge_workflows_for_hierarchy(hierarchy)

    assert "bugfix" in workflows
    assert "story-implementation" in workflows
    assert "controller-deploy" in workflows

    assert workflows["bugfix"].triggers == ["fix bug", "bugfix"]
    assert "controller-ci" in workflows["bugfix"].requires
    assert workflows["bugfix"].description == "Fix a triaged bug"


def test_get_workflows_tool(tmp_path):
    config = _setup_with_workflows(tmp_path)
    init_config(config)
    result = get_workflows(repo="ansible/awx")

    assert "bugfix" in result
    assert "story-implementation" in result
    assert "controller-deploy" in result
    assert "Fix a triaged bug" in result


def test_get_workflows_no_workflows(tmp_path):
    config = Config(
        scopes=[
            Scope(
                name="aap",
                sources=[SourceConfig(type="local", path=str(tmp_path))],
            ),
        ]
    )
    init_config(config)
    result = get_workflows(repo="ansible/awx")
    assert "No workflows defined" in result
