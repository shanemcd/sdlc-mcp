"""Workflow routing: loading, hierarchical merging, and intent matching.

Workflow definitions live in workflows.yml files alongside markdown content
at each hierarchy level. They merge with field-level "most specific wins"
semantics: a team can override just the `requires` field of an org-level
workflow without losing the org-level triggers and description.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


@dataclass
class Workflow:
    id: str
    type: str = "workflow"
    triggers: list[str] = field(default_factory=list)
    jira_types: list[str] = field(default_factory=list)
    requires: list[str] = field(default_factory=list)
    description: str = ""

    @classmethod
    def from_dict(cls, id: str, data: dict[str, Any]) -> Workflow:
        return cls(
            id=id,
            type=data.get("type", "workflow"),
            triggers=data.get("triggers", []),
            jira_types=data.get("jira_types", []),
            requires=data.get("requires", []),
            description=data.get("description", ""),
        )


def _load_workflows_from_file(path: Path) -> dict[str, Workflow]:
    if not path.exists():
        return {}

    with open(path) as f:
        data = yaml.safe_load(f)

    if not data or "workflows" not in data:
        return {}

    workflows = {}
    for wf_id, wf_data in data["workflows"].items():
        if isinstance(wf_data, dict):
            workflows[wf_id] = Workflow.from_dict(wf_id, wf_data)

    return workflows


def _merge_workflow(base: Workflow, override: Workflow) -> Workflow:
    """Merge two workflow definitions with field-level override."""
    return Workflow(
        id=base.id,
        type=override.type if override.type != "workflow" else base.type,
        triggers=override.triggers if override.triggers else base.triggers,
        jira_types=override.jira_types if override.jira_types else base.jira_types,
        requires=override.requires if override.requires else base.requires,
        description=override.description if override.description else base.description,
    )


def merge_workflows(levels: list[dict[str, Workflow]]) -> dict[str, Workflow]:
    """Merge workflow definitions from multiple hierarchy levels.

    Levels are ordered from most general to most specific.
    Field-level merging: specific levels override individual fields.
    """
    merged: dict[str, Workflow] = {}

    for level_workflows in levels:
        for wf_id, workflow in level_workflows.items():
            if wf_id in merged:
                merged[wf_id] = _merge_workflow(merged[wf_id], workflow)
            else:
                merged[wf_id] = workflow

    return merged


def format_workflow(wf: Workflow) -> str:
    lines = [f"**{wf.id}** ({wf.type})"]
    if wf.description:
        lines.append(f"  {wf.description}")
    if wf.triggers:
        lines.append(f"  Triggers: {', '.join(repr(t) for t in wf.triggers)}")
    if wf.jira_types:
        lines.append(f"  Jira types: {', '.join(wf.jira_types)}")
    if wf.requires:
        lines.append(f"  Requires: {', '.join(wf.requires)}")
    return "\n".join(lines)


def format_workflow_list(workflows: dict[str, Workflow]) -> str:
    if not workflows:
        return "No workflows defined."
    sections = [format_workflow(wf) for wf in sorted(workflows.values(), key=lambda w: w.id)]
    return "\n\n".join(sections)
