import tomllib
from pathlib import Path

from sidecar.manifest import Manifest

_PACKAGE_DIR = Path(__file__).parent
_REPO_APPS_DIR = _PACKAGE_DIR.parent / "apps"
_BUNDLED_REGISTRY_DIR = _PACKAGE_DIR / "registry"


def get_registry_dir() -> Path:
    """Return the apps/ directory — repo root for editable installs, bundled for wheel installs."""
    if _REPO_APPS_DIR.is_dir():
        return _REPO_APPS_DIR
    return _BUNDLED_REGISTRY_DIR


def load_index() -> list[dict]:
    """Load the app index. Uses _index.toml if present, else scans manifest files."""
    registry = get_registry_dir()
    index_file = registry / "_index.toml"

    if index_file.is_file():
        try:
            with open(index_file, "rb") as f:
                data = tomllib.load(f)
            return data.get("apps", [])
        except tomllib.TOMLDecodeError:
            pass

    apps = []
    for mf in sorted(registry.glob("*/manifest.toml")):
        try:
            m = Manifest.from_toml(mf)
            apps.append(
                {
                    "id": m.app.id,
                    "name": m.app.name,
                    "description": m.app.description,
                    "homepage": m.app.homepage,
                    "tags": m.meta.tags,
                    "games": m.requires.games,
                }
            )
        except Exception:
            pass
    return apps


def find_manifest(app_id: str) -> Path:
    """Return the path to manifest.toml for the given app_id."""
    path = get_registry_dir() / app_id / "manifest.toml"
    if not path.is_file():
        raise LookupError(
            f"App '{app_id}' not found in registry. "
            f"Run 'sidecar list' to see available apps."
        )
    return path


def find_hook_script(app_id: str, script_name: str) -> Path:
    """Return the path to a hook script for the given app."""
    return get_registry_dir() / app_id / script_name
