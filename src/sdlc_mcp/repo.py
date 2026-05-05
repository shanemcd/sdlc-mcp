"""Shared git repository helpers for cloning and caching."""

from __future__ import annotations

import hashlib
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

CACHE_DIR = Path.home() / ".cache" / "sdlc-mcp" / "repos"


def cache_key(url: str, ref: str = "") -> str:
    slug = hashlib.sha256(f"{url}:{ref}".encode()).hexdigest()[:12]
    name = url.rstrip("/").rsplit("/", 1)[-1].removesuffix(".git")
    return f"{name}-{slug}"


def run_git(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=120,
    )


def ensure_cloned(url: str, ref: str, dest: Path) -> None:
    if dest.exists():
        logger.debug("Pulling updates for %s", url)
        result = run_git(["fetch", "--quiet", "origin"], cwd=dest)
        if result.returncode != 0:
            logger.warning("git fetch failed for %s: %s", url, result.stderr.strip())
            return

        target = f"origin/{ref}" if ref else "origin/HEAD"
        result = run_git(["reset", "--hard", target], cwd=dest)
        if result.returncode != 0:
            logger.warning("git reset failed for %s: %s", url, result.stderr.strip())
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)
        logger.debug("Cloning %s to %s", url, dest)
        clone_args = ["clone", "--quiet", "--depth", "1"]
        if ref:
            clone_args.extend(["--branch", ref])
        clone_args.extend([url, str(dest)])
        result = run_git(clone_args)
        if result.returncode != 0:
            logger.error("git clone failed for %s: %s", url, result.stderr.strip())
