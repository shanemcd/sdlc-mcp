"""Tests for config loading and merging."""

from sdlc_mcp.config import load_config


def test_parse_list_config(tmp_path):
    config_file = tmp_path / "config.yml"
    config_file.write_text("""
- name: company
  sources:
    - type: local
      path: /content/company/

- name: org
  sources:
    - type: local
      path: /content/org/
""")
    config = load_config(config_paths=[config_file])
    assert len(config.scopes) == 2
    assert config.scopes[0].name == "company"
    assert config.scopes[1].name == "org"


def test_parse_single_dict_config(tmp_path):
    config_file = tmp_path / "config.yml"
    config_file.write_text("""
name: aap
sources:
  - type: local
    path: /content/
""")
    config = load_config(config_paths=[config_file])
    assert len(config.scopes) == 1
    assert config.scopes[0].name == "aap"


def test_repo_filter(tmp_path):
    config_file = tmp_path / "config.yml"
    config_file.write_text("""
- name: org
  sources:
    - type: local
      path: /org/

- name: controller
  repos: [awx, controller]
  sources:
    - type: local
      path: /team/
""")
    config = load_config(config_paths=[config_file])
    awx = config.scopes_for_repo("ansible/awx")
    assert len(awx) == 2

    galaxy = config.scopes_for_repo("ansible/galaxy_ng")
    assert len(galaxy) == 1
    assert galaxy[0].name == "org"


def test_relative_paths(tmp_path):
    content_dir = tmp_path / "content"
    content_dir.mkdir()

    config_file = tmp_path / "config.yml"
    config_file.write_text("""
- name: org
  sources:
    - type: local
      path: content/
""")
    config = load_config(config_paths=[config_file])
    assert config.scopes[0].sources[0].path == str(content_dir)


def test_absolute_paths_unchanged(tmp_path):
    config_file = tmp_path / "config.yml"
    config_file.write_text("""
- name: co
  sources:
    - type: local
      path: /absolute/path/
""")
    config = load_config(config_paths=[config_file])
    assert config.scopes[0].sources[0].path == "/absolute/path/"


def test_file_include(tmp_path):
    included = tmp_path / "base.yml"
    included.write_text("""
- name: company
  sources:
    - type: local
      path: /company/
""")

    config_file = tmp_path / "config.yml"
    config_file.write_text(f"""
- name: org
  include:
    - file://{included}
  sources:
    - type: local
      path: /org/
""")
    config = load_config(config_paths=[config_file])
    assert len(config.scopes) == 2
    assert config.scopes[0].name == "company"
    assert config.scopes[1].name == "org"


def test_file_include_relative(tmp_path):
    sub = tmp_path / "included.yml"
    sub.write_text("""
- name: company
""")

    config_file = tmp_path / "config.yml"
    config_file.write_text("""
- name: org
  include:
    - file://included.yml
""")
    config = load_config(config_paths=[config_file])
    assert len(config.scopes) == 2
    assert config.scopes[0].name == "company"
    assert config.scopes[1].name == "org"


def test_file_include_sdlc_dir(tmp_path):
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    sdlc_dir = repo_dir / ".sdlc"
    sdlc_dir.mkdir()
    (sdlc_dir / "config.yml").write_text("""
name: public
sources:
  - type: local
    path: .sdlc/content/
""")

    config_file = tmp_path / "config.yml"
    config_file.write_text(f"""
- name: org
  include:
    - file://{repo_dir}
""")
    config = load_config(config_paths=[config_file])
    names = [s.name for s in config.scopes]
    assert "public" in names
    assert "org" in names


def test_nested_includes(tmp_path):
    c = tmp_path / "c.yml"
    c.write_text("- name: company\n")

    b = tmp_path / "b.yml"
    b.write_text(f"""
- name: org
  include:
    - file://{c}
""")

    a = tmp_path / "a.yml"
    a.write_text(f"""
- name: team
  include:
    - file://{b}
""")
    config = load_config(config_paths=[a])
    names = [s.name for s in config.scopes]
    assert names == ["company", "org", "team"]


def test_circular_include(tmp_path):
    a = tmp_path / "a.yml"
    b = tmp_path / "b.yml"

    a.write_text(f"""
- name: a
  include:
    - file://{b}
""")
    b.write_text(f"""
- name: b
  include:
    - file://{a}
""")
    config = load_config(config_paths=[a])
    names = [s.name for s in config.scopes]
    assert "a" in names
    assert "b" in names


def test_missing_include_fails(tmp_path):
    import pytest

    from sdlc_mcp.config import IncludeError

    config_file = tmp_path / "config.yml"
    config_file.write_text("""
- name: org
  include:
    - file:///nonexistent/path
  sources:
    - type: local
      path: /org/
""")
    with pytest.raises(IncludeError):
        load_config(config_paths=[config_file])


def test_merge_order(tmp_path):
    """Later scopes override earlier ones for same-name files."""
    base_dir = tmp_path / "base"
    base_dir.mkdir()
    (base_dir / "testing.md").write_text("# Base Testing")

    override_dir = tmp_path / "override"
    override_dir.mkdir()
    (override_dir / "testing.md").write_text("# Override Testing")

    config_file = tmp_path / "config.yml"
    config_file.write_text(f"""
- name: org
  sources:
    - type: local
      path: {base_dir}

- name: team
  repos: [awx]
  sources:
    - type: local
      path: {override_dir}
""")
    config = load_config(config_paths=[config_file])

    from sdlc_mcp.hierarchy import resolve_hierarchy
    from sdlc_mcp.merge import merge_content
    from sdlc_mcp.sources import local as _local  # noqa: F401

    h = resolve_hierarchy(config, "awx")
    merged = merge_content(h)
    assert "Override Testing" in merged.get("testing.md").content


def test_multiple_config_paths(tmp_path):
    a = tmp_path / "a.yml"
    a.write_text("- name: from-a\n")

    b = tmp_path / "b.yml"
    b.write_text("- name: from-b\n")

    config = load_config(config_paths=[a, b])
    names = [s.name for s in config.scopes]
    assert names == ["from-a", "from-b"]
