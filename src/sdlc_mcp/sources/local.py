"""Local directory content source."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from . import ContentItem, register_source

if TYPE_CHECKING:
    from ..config import SourceConfig

logger = logging.getLogger(__name__)


class LocalSource:
    def __init__(self, config: SourceConfig) -> None:
        self.path = Path(config.path).expanduser().resolve()

    def read(self) -> list[ContentItem]:
        if self.path.is_file():
            return [
                ContentItem.from_file(
                    filename=self.path.name,
                    raw_content=self.path.read_text(),
                    source_path=str(self.path),
                )
            ]

        if not self.path.is_dir():
            logger.warning("Local source path does not exist: %s", self.path)
            return []

        items = []
        for md_file in sorted(self.path.glob("*.md")):
            if not md_file.is_file():
                continue
            items.append(
                ContentItem.from_file(
                    filename=md_file.name,
                    raw_content=md_file.read_text(),
                    source_path=str(md_file),
                )
            )
        return items


register_source("local", LocalSource)
