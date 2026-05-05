"""CLI entry point for sdlc-mcp."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="sdlc-mcp",
        description="MCP server for hierarchical organizational context",
    )
    subparsers = parser.add_subparsers(dest="command")

    serve_parser = subparsers.add_parser("serve", help="Start the MCP server")
    serve_parser.add_argument(
        "--config",
        type=Path,
        action="append",
        default=None,
        help="Path to config file (can be specified multiple times, merged in order)",
    )
    serve_parser.add_argument(
        "--repo-path",
        type=Path,
        default=None,
        help="Path to repo root (for .sdlc/config.yml lookup)",
    )
    serve_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    if args.command == "serve":
        logging.basicConfig(
            level=logging.DEBUG if args.verbose else logging.INFO,
            format="%(name)s - %(levelname)s - %(message)s",
        )

        from .server import init_config_from_path, mcp

        init_config_from_path(
            config_paths=args.config,
            repo_path=args.repo_path,
        )
        mcp.run()


if __name__ == "__main__":
    main()
