"""Tests for hierarchy resolution."""

from sdlc_mcp.config import Config, Scope, SourceConfig
from sdlc_mcp.hierarchy import resolve_hierarchy


def _make_config():
    return Config(
        scopes=[
            Scope(
                name="acme",
                sources=[SourceConfig(type="local", path="/content/company/")],
            ),
            Scope(
                name="platform",
                sources=[SourceConfig(type="local", path="/content/org/")],
            ),
            Scope(
                name="api",
                repos=["api-gateway", "api-auth"],
                sources=[SourceConfig(type="local", path="/content/teams/api/")],
            ),
            Scope(
                name="frontend",
                repos=["web-app"],
                sources=[SourceConfig(type="local", path="/content/teams/frontend/")],
            ),
        ]
    )


def test_resolve_known_repo():
    config = _make_config()
    h = resolve_hierarchy(config, "acme/api-gateway")

    assert h.repo == "acme/api-gateway"
    assert len(h.levels) == 3
    assert h.levels[0].name == "acme"
    assert h.levels[1].name == "platform"
    assert h.levels[2].name == "api"


def test_resolve_unknown_repo():
    config = _make_config()
    h = resolve_hierarchy(config, "acme/unknown-repo")

    assert len(h.levels) == 2
    assert h.levels[0].name == "acme"
    assert h.levels[1].name == "platform"


def test_get_level():
    config = _make_config()
    h = resolve_hierarchy(config, "acme/api-gateway")
    assert h.get_level("acme") is not None
    assert h.get_level("nonexistent") is None


def test_resolve_different_repos():
    config = _make_config()
    api = resolve_hierarchy(config, "acme/api-gateway")
    fe = resolve_hierarchy(config, "acme/web-app")

    assert api.levels[2].name == "api"
    assert fe.levels[2].name == "frontend"


def test_resolve_ignores_org_prefix():
    config = _make_config()
    h1 = resolve_hierarchy(config, "acme/api-gateway")
    h2 = resolve_hierarchy(config, "somefork/api-gateway")
    h3 = resolve_hierarchy(config, "api-gateway")

    assert h1.get_level("api") is not None
    assert h2.get_level("api") is not None
    assert h3.get_level("api") is not None
