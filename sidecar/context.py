from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class InstallContext:
    steam_dir: Path
    game_appid: int
    game_dir: Path
    prefix_dir: Path
    install_dir: Path
    app_dir: Path
    proton_bin: Path


@dataclass
class LaunchContext(InstallContext):
    exe_path: Path = field(default_factory=Path)
    args: list[str] = field(default_factory=list)
