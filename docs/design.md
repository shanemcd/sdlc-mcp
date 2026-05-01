# Context-as-a-Service: Dynamic SDLC Context Delivery via MCP

## Context

The AI SDLC initiative needs to deliver organizational context to AI agents working across 30+ repositories, with 200+ developers. This context exists at multiple levels:

- **Company-wide:** security standards, CDE processes, documentation format
- **Org (AAP):** architecture principles, SDP/proposal process, testing strategy, Jira conventions
- **Team:** component ownership, team testing patterns, review conventions
- **Repo:** language, framework, directory structure, CI setup

Different audiences need different subsets. Community contributors working on public upstream repos (AWX, Galaxy NG, EDA, etc.) should only see what's in the repo. Employees need the internal organizational context layered on top, without that context being visible in the repo itself.

## The Idea

**An open-source MCP server that resolves hierarchical context on demand. The server is generic infrastructure. The content and config are pluggable and private.**

The server itself knows nothing about Red Hat, AAP, or any specific organization. It reads a config that defines a hierarchy (company > org > team > repo), points at content sources (markdown in git repos, local directories, URLs), resolves the hierarchy with "most specific wins" semantics, and serves the merged result via MCP tools. Any organization can use it.

What makes it work for a specific org is the *config*: a private config that maps repos to teams, points at internal standards repos, and defines the hierarchy. This config ships in a container image or lives in a private repo. The server is open. The knowledge is private.

### Config Hierarchy

The config itself is hierarchical, just like the content it serves:

```
System config (/etc/sdlc-context/config.yml or container image)
  merged with
User config (~/.config/sdlc-context/config.yml)
  merged with
Repo config (.sdlc/config.yml, optional)
```

Each level can add content sources, override settings, or extend the hierarchy. The server merges them the same way it merges content: most specific wins.

- **System config** (from container image): provides org defaults, points at internal content sources, defines the team/repo registry. Every employee gets this.
- **User config**: personal overrides. A team lead could add team-specific sources. A developer could add experimental content.
- **Repo config** (optional): for repos that want to declare their own context sources. Optional and minimal, not required.

This means:
- A community contributor runs the server with no config. It does nothing (or serves whatever the repo provides). The repo works fine without it.
- An employee gets the system config from the container image, which points at all the internal content. Full org context, zero setup.
- A team lead adds a user config with team-specific sources.
- An internal repo can optionally carry a repo config for truly repo-specific overrides.

### Why MCP?

MCP is a context protocol. Agents already connect to remote services over MCP to get tools. The Skills Over MCP Working Group (SEP-2640) is standardizing how to serve structured workflow instructions through the same channel. Key use cases that map to this problem:

- **Version-adaptive content** (Use Case 8): different context based on runtime environment
- **Multi-tenant skills** (Use Case 9): different users get different content based on role
- **Enterprise distribution** (Use Case 7): centralized management with RBAC

Building on MCP means the solution works with any MCP-capable agent (not just Claude Code) and aligns with the ecosystem direction.

## Architecture

### Source Layout

```
sdlc-context/
  src/sdlc_context/
    __main__.py        # CLI entry point (serve command)
    server.py          # FastMCP server, MCP tool definitions
    config.py          # Config loading + merging (system + user + repo)
    hierarchy.py       # Hierarchy resolution engine
    sources/           # Pluggable content source adapters
      __init__.py      # Source protocol definition
      local.py         # Read from a local directory
      git.py           # Clone a repo, read markdown from a path
    merge.py           # "Most specific wins" content merging
  examples/            # Sample configs and content for testing
  docs/
    design.md          # This file
  pyproject.toml
  README.md
  CLAUDE.md
```

The server is generic. It doesn't know about Jira, AWX, or any specific org. It knows how to:
1. Load and merge configs from system/user/repo levels
2. Read content from pluggable sources (git repos, local dirs)
3. Resolve a hierarchy (walk the tree from repo up to company)
4. Merge content at each level (most specific wins)
5. Serve the result via MCP tools

### Config Format

```yaml
# Example: system-level config shipped in a container image
# Lives at /etc/sdlc-context/config.yml or $SDLC_CONTEXT_CONFIG

hierarchy:
  levels: [company, org, team, repo]

  company:
    name: acme
    sources:
      - type: git
        url: https://github.com/acme/standards.git
        path: company/

  org:
    name: platform
    sources:
      - type: git
        url: https://github.com/acme/engineering-handbook.git
        path: standards/

  teams:
    api:
      repos: [acme/api-gateway, acme/api-auth]
      sources:
        - type: git
          url: https://github.com/acme/platform-standards.git
          path: teams/api/

    frontend:
      repos: [acme/web-app, acme/design-system]
      sources:
        - type: git
          url: https://github.com/acme/platform-standards.git
          path: teams/frontend/
```

```yaml
# Example: user-level config
# Lives at ~/.config/sdlc-context/config.yml

sources:
  - type: local
    path: ~/notes/coding-standards/
    level: user
```

```yaml
# Example: repo-level config (optional)
# Lives at .sdlc/config.yml in the repo

team: api

sources:
  - type: local
    path: .sdlc/guides/
    level: repo
```

### MCP Tools

```python
@server.tool()
def get_context(repo: str | None = None, task: str | None = None) -> str:
    """Get merged organizational context for the current repo and task.

    The server resolves the hierarchy (company > org > team > repo),
    merges applicable standards with 'most specific wins', and returns
    the result.

    Args:
        repo: Repository identifier (e.g., "acme/api-gateway"). Auto-detected
              from git remote if not provided.
        task: Optional task type (e.g., "implement-story", "code-review")
              to filter context to what's relevant.
    """

@server.tool()
def get_conventions(repo: str | None = None, category: str | None = None) -> str:
    """Get conventions for a specific category (testing, jira, code-review, etc.).

    Args:
        repo: Repository identifier. Auto-detected if not provided.
        category: Convention category to retrieve.
    """

@server.tool()
def get_hierarchy(repo: str | None = None) -> str:
    """Show the resolved hierarchy for a repo: which team, org, company,
    and what content sources are active at each level.

    Useful for debugging: 'why did the agent get this context?'
    """
```

### Content Resolution Flow

```
Agent calls get_context(repo="acme/api-gateway")
  |
  v
Config merger loads: system config + user config + repo config (if exists)
  |
  v
Hierarchy resolver:
  1. repo = "acme/api-gateway"
  2. team = "api" (from registry in config)
  3. org = "platform" (from config)
  4. company = "acme" (from config)
  |
  v
Source reader fetches content at each level:
  - company: security-standards.md, docs-format.md
  - org: architecture-principles.md, testing-strategy.md
  - team/api: api-testing.md, openapi-conventions.md
  - repo: (auto-discovered from repo itself, or from repo config)
  |
  v
Merger combines with "most specific wins":
  - If api team has testing.md AND org has testing.md, api team's wins
  - If only org has architecture-principles.md, that's used as-is
  |
  v
Returns merged context to agent
```

## SEP-2640 Compatibility (Skills Over MCP)

The architecture is designed so that SEP-2640 support is an additive layer, not a rewrite. The core logic (load config, resolve hierarchy, merge content) is the same regardless of delivery mechanism.

**Today:** Content is served via MCP tools (`get_context()`, `get_conventions()`).

**When SEP-2640 lands:** The same server additionally registers `skill://{repo}/SKILL.md` as an MCP resource template. Calling `resources/read` on that URI runs the same hierarchy resolution and returns merged content as a skill resource. The `skill://index.json` well-known resource enumerates available contexts, and resource templates let hosts offer completion on repo names for unbounded catalogs. This gives automatic host-side discovery, progressive disclosure, and UI integration for free, without changing the resolution engine.

## Tradeoffs

**Gains:**
- Open-source, org-agnostic server
- No files in public repos
- Central maintenance (update once, apply everywhere)
- Server-side hierarchy resolution (one call, no chain to debug)
- Hierarchical config (system + user + repo)
- Works with any MCP agent

**Costs:**
- Requires a running service (mitigated: lightweight, bundled in container)
- Content pipeline has sync latency (mitigated: refresh on startup or short interval)
- Someone builds and maintains the server

## Implementation Plan

### Phase 1: Skeleton
- Python project with `uv`, FastMCP server
- Config loading and merging (system + user + repo)
- Hierarchy resolution engine
- `get_context()` and `get_hierarchy()` MCP tools
- Local directory source adapter (simplest first)
- Sample config and content for testing

### Phase 2: Git source adapter
- Git repo cloning as a content source
- Test with real repos as sources

### Phase 3: Real content
- Write an org-specific system config (hierarchy registry, source pointers)
- Populate initial content for 2-3 teams
- Validate end-to-end: agent in a public repo gets correct merged context

### Phase 4: SEP-2640 skill:// resource layer
- Register `skill://{repo}/SKILL.md` as an MCP resource template
- Expose `skill://index.json` for discovery
- Same resolution engine, different transport wrapper
- Hosts that support the spec get automatic discovery and UI integration

### Phase 5: Distribution
- Container image integration
- AGENTS.md template with "if available" pattern
- README and docs for the open-source project
