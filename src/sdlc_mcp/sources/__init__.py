"""Pluggable content source protocol and registry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import yaml


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Parse YAML frontmatter from markdown content.

    Returns (metadata dict, body without frontmatter).
    """
    if not text.startswith("---"):
        return {}, text

    end = text.find("---", 3)
    if end == -1:
        return {}, text

    raw = text[3:end].strip()
    body = text[end + 3 :].lstrip("\n")

    try:
        meta = yaml.safe_load(raw) or {}
    except yaml.YAMLError:
        return {}, text

    return meta, body


@dataclass
class ContentItem:
    filename: str
    content: str
    source_path: str
    tool_name: str = ""
    tool_description: str = ""

    @classmethod
    def from_file(cls, filename: str, raw_content: str, source_path: str) -> ContentItem:
        meta, body = _parse_frontmatter(raw_content)
        return cls(
            filename=filename,
            content=body,
            source_path=source_path,
            tool_name=meta.get("name", filename.removesuffix(".md")),
            tool_description=meta.get("description", ""),
        )


class Source(Protocol):
    def read(self) -> list[ContentItem]:
        """Read all markdown content items from this source."""
        ...


_SOURCE_TYPES: dict[str, type] = {}


def register_source(type_name: str, cls: type) -> None:
    _SOURCE_TYPES[type_name] = cls


def get_source_class(type_name: str) -> type:
    if type_name not in _SOURCE_TYPES:
        raise ValueError(f"Unknown source type: {type_name!r}")
    return _SOURCE_TYPES[type_name]
