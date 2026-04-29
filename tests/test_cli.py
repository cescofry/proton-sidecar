import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from click.testing import CliRunner
from sidecar.cli import main


@pytest.fixture
def runner():
    return CliRunner()


def test_help_shows_commands(runner):
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "install" in result.output
    assert "remove" in result.output
    assert "run" in result.output
    assert "doctor" in result.output
    assert "init" in result.output
    assert "list" in result.output


def test_no_args_shows_help_and_list(runner):
    with patch("sidecar.cli.registry.load_index", return_value=[]):
        result = runner.invoke(main, [])
    assert result.exit_code == 0
    assert "proton-sidecar" in result.output


def test_list_shows_apps(runner):
    apps = [
        {"id": "test-app", "name": "Test App", "description": "A test app",
         "homepage": "", "tags": [], "games": [12345]}
    ]
    with patch("sidecar.cli.registry.load_index", return_value=apps):
        result = runner.invoke(main, ["list"])
    assert result.exit_code == 0
    assert "test-app" in result.output
    assert "Test App" in result.output


def test_list_empty_registry(runner):
    with patch("sidecar.cli.registry.load_index", return_value=[]):
        result = runner.invoke(main, ["list"])
    assert result.exit_code == 0
    assert "No apps found" in result.output


def test_install_unknown_app_shows_error(runner):
    with patch("sidecar.cli.registry.find_manifest", side_effect=LookupError("not found")):
        result = runner.invoke(main, ["install", "unknown-app"])
    assert result.exit_code != 0
    assert "not found" in result.output.lower() or "Error" in result.output


def test_install_with_game_option(runner):
    manifest = MagicMock()
    manifest.requires.games = [12345]
    manifest.app.id = "test-app"

    with (
        patch("sidecar.cli._resolve_manifest", return_value=Path("/fake/manifest.toml")),
        patch("sidecar.cli.Manifest.from_toml", return_value=manifest),
        patch("sidecar.cli.install_mod.install_app") as mock_install,
    ):
        result = runner.invoke(main, ["install", "test-app", "--game", "12345"])

    mock_install.assert_called_once_with(manifest, 12345)


def test_doctor_runs_without_crash(runner):
    with (
        patch("sidecar.cli.steam.find_steam", return_value=Path("/fake/steam")),
        patch("sidecar.cli.shutil.which", return_value=None),
    ):
        result = runner.invoke(main, ["doctor"])
    assert result.exit_code == 0
    assert "Python" in result.output
    assert "Steam" in result.output
    assert "protontricks" in result.output


def test_doctor_shows_ok_for_found_tools(runner):
    def which_side_effect(name):
        return f"/usr/bin/{name}" if name in ("protontricks", "innoextract") else None

    with (
        patch("sidecar.cli.steam.find_steam", return_value=Path("/fake/steam")),
        patch("sidecar.cli.shutil.which", side_effect=which_side_effect),
        patch("sidecar.cli.subprocess.run", return_value=MagicMock(
            stdout="1.0.0\n", stderr="", returncode=0
        )),
    ):
        result = runner.invoke(main, ["doctor"])
    assert "[OK]" in result.output


def test_init_creates_app_directory(runner, tmp_path):
    with (
        patch("sidecar.cli.registry.get_registry_dir", return_value=tmp_path),
        runner.isolated_filesystem(),
    ):
        result = runner.invoke(
            main, ["init", "https://github.com/owner/my-cool-app"], input="\n"
        )

    assert result.exit_code == 0, result.output
    app_dir = tmp_path / "my-cool-app"
    assert app_dir.is_dir()
    assert (app_dir / "manifest.toml").is_file()
    assert (app_dir / "install.py").is_file()
    assert (app_dir / "README.md").is_file()
    assert (app_dir / "LLM.md").is_file()


def test_init_manifest_contains_repo_url(runner, tmp_path):
    with patch("sidecar.cli.registry.get_registry_dir", return_value=tmp_path):
        runner.invoke(
            main,
            ["init", "https://github.com/owner/my-app", "--name", "my-app"],
        )

    content = (tmp_path / "my-app" / "manifest.toml").read_text()
    assert "https://github.com/owner/my-app" in content


def test_init_strips_git_suffix(runner, tmp_path):
    with patch("sidecar.cli.registry.get_registry_dir", return_value=tmp_path):
        result = runner.invoke(
            main,
            ["init", "https://github.com/owner/my-app.git", "--name", "my-app"],
        )
    assert result.exit_code == 0
    content = (tmp_path / "my-app" / "manifest.toml").read_text()
    assert ".git" not in content


def test_init_existing_dir_raises(runner, tmp_path):
    (tmp_path / "existing-app").mkdir()
    with patch("sidecar.cli.registry.get_registry_dir", return_value=tmp_path):
        result = runner.invoke(
            main,
            ["init", "https://github.com/owner/existing-app", "--name", "existing-app"],
        )
    assert result.exit_code != 0
    assert "already exists" in result.output


def test_remove_not_installed_raises(runner, tmp_path):
    with patch("sidecar.cli.Path.home", return_value=tmp_path):
        result = runner.invoke(main, ["remove", "not-installed"])
    assert result.exit_code != 0


def test_version_flag(runner):
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "version" in result.output.lower() or "0." in result.output
