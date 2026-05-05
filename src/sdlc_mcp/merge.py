"""Content merging with "most specific wins" semantics.

When the same filename exists at multiple hierarchy levels, the most specific
level's version is used. Content that only exists at one level passes through
unchanged. Merging is by filename, not by concatenation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from .config import SourceConfig
from .hierarchy import ResolvedHierarchy
from .sources import ContentItem, get_source_class
from .workflows import Workflow, _load_workflows_from_file, merge_workflows

logger = logging.getLogger(__name__)


@dataclass
class MergedContent:
    items: dict[str, ContentItem] = field(default_factory=dict)
    provenance: dict[str, str] = field(default_factory=dict)

    def get(self, filename: str) -> ContentItem | None:
        return self.items.get(filename)

    def filenames(self) -> list[str]:
        return sorted(self.items.keys())


def _read_sources(sources: list[SourceConfig]) -> list[ContentItem]:
    items = []
    for source_config in sources:
        try:
            source_cls = get_source_class(source_config.type)
        except ValueError:
            logger.warning("Skipping unknown source type: %s", source_config.type)
            continue

        source = source_cls(source_config)
        items.extend(source.read())
    return items


def merge_content(hierarchy: ResolvedHierarchy) -> MergedContent:
    """Merge content from all hierarchy levels.

    Levels are processed from most general to most specific. When the same
    filename appears at multiple levels, the most specific version wins.
    """
    merged = MergedContent()

    for level in hierarchy.levels:
        items = _read_sources(level.sources)
        for item in items:
            merged.items[item.filename] = item
            merged.provenance[item.filename] = f"{level.level}:{level.name}"

    return merged


def merge_content_for_category(hierarchy: ResolvedHierarchy, category: str) -> ContentItem | None:
    """Get a single content item by category (filename without .md extension)."""
    merged = merge_content(hierarchy)

    filename = category if category.endswith(".md") else f"{category}.md"
    return merged.get(filename)


def _collect_workflow_paths(sources: list[SourceConfig]) -> list[Path]:
    """Find workflows.yml files in local source directories."""
    paths = []
    for source_config in sources:
        if source_config.type == "local" and source_config.path:
            wf_path = Path(source_config.path) / "workflows.yml"
            if wf_path.exists():
                paths.append(wf_path)
    return paths


def merge_workflows_for_hierarchy(hierarchy: ResolvedHierarchy) -> dict[str, Workflow]:
    """Load and merge workflow definitions from all hierarchy levels."""
    levels_data = []
    for level in hierarchy.levels:
        level_workflows: dict[str, Workflow] = {}
        for wf_path in _collect_workflow_paths(level.sources):
            level_workflows.update(_load_workflows_from_file(wf_path))
        levels_data.append(level_workflows)
    return merge_workflows(levels_data)
