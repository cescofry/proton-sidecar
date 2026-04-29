import shutil
import subprocess
import sys
import traceback
from pathlib import Path

from sidecar import download, extract
from sidecar import hook as hook_module
from sidecar import launch, steam
from sidecar.context import InstallContext
from sidecar.manifest import Manifest
from sidecar.registry import find_hook_script
from sidecar.state import InstallState, write_state

SIDECAR_DIR = Path.home() / ".local" / "share" / "sidecar"


def install_app(manifest: Manifest, game_appid: int) -> None:
    """Orchestrate the full install flow for one app + game combination."""
    install_dir = SIDECAR_DIR / manifest.app.id / str(game_appid)
    install_dir.mkdir(parents=True, exist_ok=True)
    app_dir = install_dir / "app"
    log_path = install_dir / "install.log"

    try:
        _run_install(manifest, game_appid, install_dir, app_dir, log_path)
    except Exception as exc:
        _fail(exc, install_dir, log_path)
        sys.exit(1)


def _run_install(
    manifest: Manifest,
    game_appid: int,
    install_dir: Path,
    app_dir: Path,
    log_path: Path,
) -> None:
    steam_dir = steam.find_steam()
    games = steam.find_installed_games(manifest.requires.games)
    matching = [g for g in games if g[0] == game_appid]
    if not matching:
        raise RuntimeError(
            f"Game AppID {game_appid} is not installed or not found by Steam."
        )
    _, _, game_dir = matching[0]
    prefix_dir = steam.find_prefix(steam_dir, game_appid)
    proton_bin = steam.find_proton(steam_dir, game_appid)

    ctx = InstallContext(
        steam_dir=steam_dir,
        game_appid=game_appid,
        game_dir=game_dir,
        prefix_dir=prefix_dir,
        install_dir=install_dir,
        app_dir=app_dir,
        proton_bin=proton_bin,
    )

    # Phase: install Wine dependencies
    _write(install_dir, manifest.app.id, game_appid, "installing_deps")
    if manifest.requires.wine_components:
        _run_protontricks(game_appid, manifest.requires.wine_components, log_path)

    # Phase: download
    _write(install_dir, manifest.app.id, game_appid, "downloading")
    url = _resolve_source_url(manifest)
    dl_dir = install_dir / "_download"
    installer_path = download.download_file(url, dl_dir)

    # Phase: extract
    _write(install_dir, manifest.app.id, game_appid, "extracting")
    app_dir.mkdir(exist_ok=True)
    extract.extract(manifest.source, installer_path, app_dir, log_path)

    # Phase: run hook
    _write(install_dir, manifest.app.id, game_appid, "running_hook")
    if manifest.install.script:
        hook_path = find_hook_script(manifest.app.id, manifest.install.script)
        hook = hook_module.load_hook(hook_path, manifest)
        hook.post_install(ctx)

    # Generate standalone launcher
    launch.write_launcher(manifest, ctx)

    # Done
    _write(install_dir, manifest.app.id, game_appid, "done")
    _cleanup_download(dl_dir)

    print(f"\n{manifest.app.name} installed successfully.")
    if manifest.meta.linux_notes:
        print(f"\nNote:\n{manifest.meta.linux_notes}")
    print(f"Run with: sidecar run {manifest.app.id}")


def _write(install_dir: Path, app_id: str, game_appid: int, phase: str) -> None:
    write_state(install_dir, InstallState.new(app_id, game_appid, phase))


def _run_protontricks(appid: int, verbs: list[str], log_path: Path) -> None:
    cmd = ["protontricks", "--no-runtime-version-check", str(appid), *verbs]
    with open(log_path, "ab") as f:
        result = subprocess.run(cmd, stdout=f, stderr=f)
    if result.returncode != 0:
        raise RuntimeError(
            f"protontricks failed installing Wine components. See {log_path} for details."
        )


def _resolve_source_url(manifest: Manifest) -> str:
    if manifest.source.asset_pattern:
        return download.resolve_github_release_url(
            manifest.source.url, manifest.source.asset_pattern
        )
    return manifest.source.url


def _cleanup_download(dl_dir: Path) -> None:
    if dl_dir.exists():
        shutil.rmtree(dl_dir)


def _fail(exc: Exception, install_dir: Path, log_path: Path) -> None:
    tb = traceback.format_exc()
    try:
        with open(log_path, "a") as f:
            f.write(f"\n--- Installation failed ---\n{tb}\n")
    except OSError:
        pass
    print(f"Error: {exc}", file=sys.stderr)
    print(f"See {log_path} for details.", file=sys.stderr)
