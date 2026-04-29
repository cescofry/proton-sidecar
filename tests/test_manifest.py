import pytest
from pathlib import Path
from sidecar.manifest import Manifest, ManifestError

FIXTURES = Path(__file__).parent / "fixtures"


def test_load_minimal_manifest():
    m = Manifest.from_toml(FIXTURES / "minimal_manifest.toml")
    assert m.app.id == "test-app"
    assert m.app.name == "Test App"
    assert m.requires.games == [12345]
    assert m.requires.wine_components == ["dotnet48"]
    assert m.source.url == "https://example.com/setup.exe"
    assert m.source.type == "inno"
    assert m.install.target_prefix == "game"
    assert m.launch.exe == "app/TestApp.exe"
    assert m.launch.args == []
    assert m.launch.env == {}
    assert m.meta.tags == ["test"]
    assert m.meta.linux_notes == ""


def test_optional_fields_have_defaults(tmp_path):
    toml = tmp_path / "manifest.toml"
    toml.write_text(
        '[app]\nid="a"\nname="A"\ndescription=""\n'
        "[requires]\ngames=[1]\n"
        '[source]\nurl="https://example.com/a.zip"\ntype="zip"\n'
        '[launch]\nexe="a.exe"\n'
    )
    m = Manifest.from_toml(toml)
    assert m.install.target_prefix == "game"
    assert m.install.script == ""
    assert m.meta.tags == []
    assert m.launch.env == {}


def test_launch_env_parsed(tmp_path):
    toml = tmp_path / "manifest.toml"
    toml.write_text(
        '[app]\nid="a"\nname="A"\ndescription=""\n'
        "[requires]\ngames=[1]\n"
        '[source]\nurl="https://example.com/a.zip"\ntype="zip"\n'
        '[launch]\nexe="a.exe"\n'
        '[launch.env]\nFOO="bar"\nBAZ="qux"\n'
    )
    m = Manifest.from_toml(toml)
    assert m.launch.env == {"FOO": "bar", "BAZ": "qux"}


def test_missing_required_field_raises(tmp_path):
    toml = tmp_path / "manifest.toml"
    toml.write_text('[app]\nid="a"\nname="A"\n')  # missing description, requires, source, launch
    with pytest.raises(ManifestError, match="Missing required field"):
        Manifest.from_toml(toml)


def test_invalid_source_type_raises(tmp_path):
    toml = tmp_path / "manifest.toml"
    toml.write_text(
        '[app]\nid="a"\nname="A"\ndescription=""\n'
        "[requires]\ngames=[1]\n"
        '[source]\nurl="https://example.com/a.exe"\ntype="nsis"\n'
        '[launch]\nexe="a.exe"\n'
    )
    with pytest.raises(ManifestError, match="source.type"):
        Manifest.from_toml(toml)


def test_invalid_target_prefix_raises(tmp_path):
    toml = tmp_path / "manifest.toml"
    toml.write_text(
        '[app]\nid="a"\nname="A"\ndescription=""\n'
        "[requires]\ngames=[1]\n"
        '[source]\nurl="https://example.com/a.zip"\ntype="zip"\n'
        '[install]\ntarget_prefix="shared"\n'
        '[launch]\nexe="a.exe"\n'
    )
    with pytest.raises(ManifestError, match="install.target_prefix"):
        Manifest.from_toml(toml)


def test_empty_games_raises(tmp_path):
    toml = tmp_path / "manifest.toml"
    toml.write_text(
        '[app]\nid="a"\nname="A"\ndescription=""\n'
        "[requires]\ngames=[]\n"
        '[source]\nurl="https://example.com/a.zip"\ntype="zip"\n'
        '[launch]\nexe="a.exe"\n'
    )
    with pytest.raises(ManifestError, match="requires.games must not be empty"):
        Manifest.from_toml(toml)


def test_github_releases_url_requires_asset_pattern(tmp_path):
    toml = tmp_path / "manifest.toml"
    toml.write_text(
        '[app]\nid="a"\nname="A"\ndescription=""\n'
        "[requires]\ngames=[1]\n"
        '[source]\nurl="https://github.com/owner/repo/releases/latest"\ntype="inno"\n'
        '[launch]\nexe="a.exe"\n'
    )
    with pytest.raises(ManifestError, match="asset_pattern"):
        Manifest.from_toml(toml)


def test_github_releases_url_with_asset_pattern_ok(tmp_path):
    toml = tmp_path / "manifest.toml"
    toml.write_text(
        '[app]\nid="a"\nname="A"\ndescription=""\n'
        "[requires]\ngames=[1]\n"
        '[source]\nurl="https://github.com/owner/repo/releases/latest"\ntype="inno"\nasset_pattern="Setup.*\\\\.exe$"\n'
        '[launch]\nexe="a.exe"\n'
    )
    m = Manifest.from_toml(toml)
    assert m.source.asset_pattern == "Setup.*\\.exe$"


def test_invalid_toml_raises(tmp_path):
    toml = tmp_path / "manifest.toml"
    toml.write_text("this is not valid toml ][")
    with pytest.raises(ManifestError, match="Invalid TOML"):
        Manifest.from_toml(toml)
