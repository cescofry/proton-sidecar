import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, call
from sidecar import install as install_mod
from sidecar.state import read_state


@pytest.fixture
def tmp_sidecar_dir(tmp_path):
    with patch.object(install_mod, "SIDECAR_DIR", tmp_path):
        yield tmp_path


def _make_manifest(app_id: str = "test-app", game_appid: int = 12345) -> MagicMock:
    m = MagicMock()
    m.app.id = app_id
    m.app.name = "Test App"
    m.meta.linux_notes = ""
    m.requires.games = [game_appid]
    m.requires.wine_components = []
    m.source.url = "https://example.com/setup.exe"
    m.source.asset_pattern = ""
    m.install.script = ""
    m.launch.exe = "TestApp.exe"
    m.launch.args = []
    m.launch.env = {}
    return m


def _mock_steam(game_appid: int, tmp_path: Path):
    return {
        "sidecar.install.steam.find_steam": MagicMock(return_value=tmp_path / "steam"),
        "sidecar.install.steam.find_installed_games": MagicMock(
            return_value=[(game_appid, "Test Game", tmp_path / "game")]
        ),
        "sidecar.install.steam.find_prefix": MagicMock(
            return_value=tmp_path / "compatdata/pfx"
        ),
        "sidecar.install.steam.find_proton": MagicMock(
            return_value=tmp_path / "proton"
        ),
    }


def test_install_app_phases_written_in_order(tmp_sidecar_dir, tmp_path):
    manifest = _make_manifest(game_appid=12345)
    install_dir = tmp_sidecar_dir / "test-app" / "12345"

    phases_written = []

    def capture_state(d, state):
        phases_written.append(state.phase)

    with (
        patch("sidecar.install.steam.find_steam", return_value=tmp_path / "steam"),
        patch("sidecar.install.steam.find_installed_games",
              return_value=[(12345, "Test Game", tmp_path / "game")]),
        patch("sidecar.install.steam.find_prefix", return_value=tmp_path / "pfx"),
        patch("sidecar.install.steam.find_proton", return_value=tmp_path / "proton"),
        patch("sidecar.install.write_state", side_effect=capture_state),
        patch("sidecar.install.download.download_file",
              return_value=tmp_path / "setup.exe"),
        patch("sidecar.install.extract.extract"),
        patch("sidecar.install.launch.write_launcher"),
    ):
        install_mod.install_app(manifest, 12345)

    assert phases_written == [
        "installing_deps", "downloading", "extracting", "running_hook", "done"
    ]


def test_install_app_cleans_up_download_dir(tmp_sidecar_dir, tmp_path):
    manifest = _make_manifest(game_appid=12345)

    def fake_download(url, dest_dir, show_progress=True):
        dest_dir.mkdir(parents=True, exist_ok=True)
        f = dest_dir / "setup.exe"
        f.touch()
        return f

    with (
        patch("sidecar.install.steam.find_steam", return_value=tmp_path / "steam"),
        patch("sidecar.install.steam.find_installed_games",
              return_value=[(12345, "Test Game", tmp_path / "game")]),
        patch("sidecar.install.steam.find_prefix", return_value=tmp_path / "pfx"),
        patch("sidecar.install.steam.find_proton", return_value=tmp_path / "proton"),
        patch("sidecar.install.download.download_file", side_effect=fake_download),
        patch("sidecar.install.extract.extract"),
        patch("sidecar.install.launch.write_launcher"),
    ):
        install_mod.install_app(manifest, 12345)

    dl_dir = tmp_sidecar_dir / "test-app" / "12345" / "_download"
    assert not dl_dir.exists()


def test_install_app_game_not_found_raises(tmp_sidecar_dir, tmp_path):
    manifest = _make_manifest(game_appid=99999)

    with (
        patch("sidecar.install.steam.find_steam", return_value=tmp_path / "steam"),
        patch("sidecar.install.steam.find_installed_games", return_value=[]),
        patch("sidecar.install.sys.exit") as mock_exit,
    ):
        install_mod.install_app(manifest, 99999)

    mock_exit.assert_called_with(1)


def test_install_app_with_wine_components_calls_protontricks(tmp_sidecar_dir, tmp_path):
    manifest = _make_manifest(game_appid=12345)
    manifest.requires.wine_components = ["dotnet48", "vcrun2019"]

    with (
        patch("sidecar.install.steam.find_steam", return_value=tmp_path / "steam"),
        patch("sidecar.install.steam.find_installed_games",
              return_value=[(12345, "Test Game", tmp_path / "game")]),
        patch("sidecar.install.steam.find_prefix", return_value=tmp_path / "pfx"),
        patch("sidecar.install.steam.find_proton", return_value=tmp_path / "proton"),
        patch("sidecar.install.subprocess.run") as mock_run,
        patch("sidecar.install.download.download_file",
              return_value=tmp_path / "setup.exe"),
        patch("sidecar.install.extract.extract"),
        patch("sidecar.install.launch.write_launcher"),
    ):
        mock_run.return_value = MagicMock(returncode=0)
        install_mod.install_app(manifest, 12345)

    cmd = mock_run.call_args[0][0]
    assert "protontricks" in cmd[0]
    assert "dotnet48" in cmd
    assert "vcrun2019" in cmd


def test_install_app_protontricks_failure_exits(tmp_sidecar_dir, tmp_path):
    manifest = _make_manifest(game_appid=12345)
    manifest.requires.wine_components = ["dotnet48"]

    with (
        patch("sidecar.install.steam.find_steam", return_value=tmp_path / "steam"),
        patch("sidecar.install.steam.find_installed_games",
              return_value=[(12345, "Test Game", tmp_path / "game")]),
        patch("sidecar.install.steam.find_prefix", return_value=tmp_path / "pfx"),
        patch("sidecar.install.steam.find_proton", return_value=tmp_path / "proton"),
        patch("sidecar.install.subprocess.run",
              return_value=MagicMock(returncode=1)),
        patch("sidecar.install.sys.exit") as mock_exit,
    ):
        install_mod.install_app(manifest, 12345)

    mock_exit.assert_called_with(1)
