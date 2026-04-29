import importlib.util
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sidecar.context import InstallContext, LaunchContext
    from sidecar.manifest import Manifest


class Hook:
    """Base class for app-specific install and launch hooks. All methods are no-ops by default."""

    def __init__(self, manifest: "Manifest") -> None:
        self.manifest = manifest

    def post_install(self, ctx: "InstallContext") -> None:
        pass

    def pre_launch(self, ctx: "LaunchContext") -> None:
        pass

    def post_launch(self, ctx: "LaunchContext") -> None:
        pass

    def uninstall(self, ctx: "InstallContext") -> None:
        pass


def load_hook(script_path: Path, manifest: "Manifest") -> Hook:
    """Dynamically import an app's install.py and return an instantiated Hook."""
    spec = importlib.util.spec_from_file_location("_app_hook", script_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {script_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]

    hook_cls = getattr(module, "Hook", None)
    if hook_cls is None:
        raise ImportError(f"No 'Hook' class found in {script_path}")
    if not (isinstance(hook_cls, type) and issubclass(hook_cls, Hook)):
        raise ImportError(
            f"'Hook' in {script_path} must be a class that subclasses sidecar.hook.Hook"
        )

    return hook_cls(manifest)
