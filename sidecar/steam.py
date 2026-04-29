import re
from pathlib import Path

from protontricks.steam import (
    find_steam_path,
    find_proton_app,
    find_appid_proton_prefix,
    get_steam_apps,
    get_steam_lib_paths,
)


class SteamNotFoundError(RuntimeError):
    pass


class GameNotInstalledError(RuntimeError):
    pass


class ProtonNotFoundError(RuntimeError):
    pass


def find_steam() -> Path:
    """Return the Steam root directory (the one containing steamapps/)."""
    steam_path, _steam_root = find_steam_path()
    if steam_path is None:
        raise SteamNotFoundError(
            "Steam directory not found. "
            "Set the STEAM_DIR environment variable if Steam is in a non-standard location."
        )
    return Path(steam_path)


def find_installed_games(appids: list[int]) -> list[tuple[int, str, Path]]:
    """Return (appid, name, install_path) for each of appids that is currently installed."""
    steam_path, steam_root = find_steam_path()
    if steam_path is None:
        return []

    steam_path = Path(steam_path)
    steam_root = Path(steam_root)
    lib_paths = get_steam_lib_paths(steam_root)
    apps = get_steam_apps(steam_root, steam_path, lib_paths)

    results: list[tuple[int, str, Path]] = []
    for app in apps:
        if app.appid in appids:
            results.append((app.appid, app.name, Path(app.install_path)))
    return results


def find_prefix(steam_dir: Path, appid: int) -> Path:
    """Return the Wine prefix (pfx/) path for the given game."""
    steam_path, steam_root = find_steam_path()
    if steam_path and steam_root:
        lib_paths = get_steam_lib_paths(Path(steam_root))
        prefix = find_appid_proton_prefix(appid, lib_paths)
        if prefix is not None:
            return Path(prefix)
    # Fallback: standard path layout
    return steam_dir / "steamapps" / "compatdata" / str(appid) / "pfx"


def find_proton(steam_dir: Path, appid: int) -> Path:
    """Return the Proton binary path used by the given game."""
    steam_path, steam_root = find_steam_path()
    if steam_path is None or steam_root is None:
        raise ProtonNotFoundError("Steam not found.")

    steam_path = Path(steam_path)
    steam_root = Path(steam_root)
    lib_paths = get_steam_lib_paths(steam_root)
    apps = get_steam_apps(steam_root, steam_path, lib_paths)

    proton_app = find_proton_app(steam_path, apps, appid=appid)
    if proton_app is None:
        raise ProtonNotFoundError(
            f"No Proton version found for AppID {appid}. "
            "Launch the game once through Steam to initialise Proton."
        )
    return Path(proton_app.install_path) / "proton"


def linux_to_wine_path(path: Path) -> str:
    """Convert a Linux path to its Wine Z: drive equivalent."""
    return "Z:" + str(path).replace("/", "\\")


def slugify_game_name(name: str) -> str:
    """Convert 'Assetto Corsa Competizione' to 'assetto-corsa-competizione'."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower())
    return re.sub(r"-+", "-", slug).strip("-")
