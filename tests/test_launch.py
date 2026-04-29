import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, call
from sidecar.launch import write_launcher, run_app
from sidecar.context import InstallContext


def _make_ctx(tmp_path: Path) -> InstallContext:
    return InstallContext(
        steam_dir=tmp_path / "steam",
        game_appid=805550,
        game_dir=tmp_path / "steam/steamapps/common/ACC",
        prefix_dir=tmp_path / "steam/steamapps/compatdata/805550/pfx",
        install_dir=tmp_path / "sidecar/acc-connector/805550",
        app_dir=tmp_path / "sidecar/acc-connector/805550/app",
        proton_bin=tmp_path / "steam/steamapps/common/Proton 8.0/proton",
    )


def _make_manifest(script: str = "") -> MagicMock:
    m = MagicMock()
    m.app.id = "acc-connector"
    m.app.name = "ACC Connector"
    m.launch.exe = "ACCConnector.exe"
    m.launch.args = []
    m.launch.env = {}
    m.install.script = script
    return m


def test_write_launcher_creates_file(tmp_path):
    ctx = _make_ctx(tmp_path)
    ctx.install_dir.mkdir(parents=True, exist_ok=True)
    manifest = _make_manifest()

    write_launcher(manifest, ctx)

    launcher = ctx.install_dir / "launch.sh"
    assert launcher.exists()
    assert launcher.stat().st_mode & 0o111  # executable


def test_write_launcher_content(tmp_path):
    ctx = _make_ctx(tmp_path)
    ctx.install_dir.mkdir(parents=True, exist_ok=True)
    manifest = _make_manifest()

    write_launcher(manifest, ctx)

    content = (ctx.install_dir / "launch.sh").read_text()
    assert "STEAM_COMPAT_DATA_PATH" in content
    assert str(ctx.steam_dir) in content
    assert str(ctx.proton_bin) in content
    assert "ACCConnector.exe" in content
    assert "Z:" in content  # Wine path conversion applied


def test_write_launcher_includes_env_vars(tmp_path):
    ctx = _make_ctx(tmp_path)
    ctx.install_dir.mkdir(parents=True, exist_ok=True)
    manifest = _make_manifest()
    manifest.launch.env = {"MY_VAR": "my_value"}

    write_launcher(manifest, ctx)

    content = (ctx.install_dir / "launch.sh").read_text()
    assert 'export MY_VAR="my_value"' in content


def test_run_app_calls_proton(tmp_path):
    ctx = _make_ctx(tmp_path)
    manifest = _make_manifest()

    with patch("sidecar.launch.subprocess.run") as mock_run, \
         patch("sidecar.launch.sys.exit") as mock_exit:
        mock_run.return_value = MagicMock(returncode=0)
        run_app(manifest, ctx, [])

    mock_run.assert_called_once()
    cmd = mock_run.call_args[0][0]
    assert str(ctx.proton_bin) in cmd[0]
    assert "run" in cmd
    mock_exit.assert_called_with(0)


def test_run_app_passes_exit_code(tmp_path):
    ctx = _make_ctx(tmp_path)
    manifest = _make_manifest()

    with patch("sidecar.launch.subprocess.run") as mock_run, \
         patch("sidecar.launch.sys.exit") as mock_exit:
        mock_run.return_value = MagicMock(returncode=42)
        run_app(manifest, ctx, [])

    mock_exit.assert_called_with(42)


def test_run_app_sets_steam_env(tmp_path):
    ctx = _make_ctx(tmp_path)
    manifest = _make_manifest()

    with patch("sidecar.launch.subprocess.run") as mock_run, \
         patch("sidecar.launch.sys.exit"):
        mock_run.return_value = MagicMock(returncode=0)
        run_app(manifest, ctx, [])

    env = mock_run.call_args[1]["env"]
    assert "STEAM_COMPAT_DATA_PATH" in env
    assert "STEAM_COMPAT_CLIENT_INSTALL_PATH" in env


def test_run_app_calls_pre_and_post_launch_hooks(tmp_path):
    ctx = _make_ctx(tmp_path)
    manifest = _make_manifest(script="install.py")

    fake_hook = MagicMock()
    with (
        patch("sidecar.launch.find_hook_script", return_value=tmp_path / "install.py"),
        patch("sidecar.launch.load_hook", return_value=fake_hook),
        patch("sidecar.launch.subprocess.run", return_value=MagicMock(returncode=0)),
        patch("sidecar.launch.sys.exit"),
    ):
        run_app(manifest, ctx, [])

    fake_hook.pre_launch.assert_called_once()
    fake_hook.post_launch.assert_called_once()
