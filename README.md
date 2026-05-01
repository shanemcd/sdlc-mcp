# sdlc-context

An MCP server that serves hierarchical organizational context to AI agents.

Organizations have standards, conventions, and process knowledge at multiple levels: company-wide, org, team, and repo. This server resolves those layers on demand, merges them with "most specific wins" semantics, and returns the result via MCP tools. The server is generic. The content and config are yours.

## Quick Start

```bash
uv sync
uv run sdlc-context serve
```

## How It Works

The server reads a config that defines a hierarchy and points at content sources (markdown in git repos, local directories). When an agent calls `get_context(repo="myorg/myrepo")`, the server:

1. Looks up which team owns the repo
2. Walks the hierarchy: repo -> team -> org -> company
3. Reads content from sources at each level
4. Merges with "most specific wins" (team testing docs override org testing docs)
5. Returns the merged result

### Config

Config is loaded from three levels (each overrides the previous):

| Level | Path | Purpose |
|---|---|---|
| System | `/etc/sdlc-context/config.yml` or `$SDLC_CONTEXT_CONFIG` | Org defaults from container image |
| User | `~/.config/sdlc-context/config.yml` | Personal overrides |
| Repo | `.sdlc/config.yml` (optional) | Repo-specific sources |

See `examples/` for sample configs.

### MCP Tools

| Tool | Purpose |
|---|---|
| `get_context(repo?, task?)` | Get merged context for a repo and task |
| `get_conventions(repo?, category?)` | Get conventions for a specific category |
| `get_hierarchy(repo?)` | Show the resolved hierarchy (for debugging) |

### Content Sources

| Type | Description |
|---|---|
| `local` | Read markdown from a local directory |
| `git` | Clone a repo and read from a path within it |

## Design

See [docs/design.md](docs/design.md) for the full design document, including architecture, config format, content resolution flow, and SEP-2640 compatibility plan.
