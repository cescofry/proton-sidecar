import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

PHASES = ("downloading", "extracting", "installing_deps", "running_hook", "done")


@dataclass
class InstallState:
    phase: str
    app_id: str
    game_appid: int
    started_at: str

    @classmethod
    def new(cls, app_id: str, game_appid: int, phase: str) -> "InstallState":
        return cls(
            phase=phase,
            app_id=app_id,
            game_appid=game_appid,
            started_at=datetime.now(timezone.utc).isoformat(),
        )


def write_state(install_dir: Path, state: InstallState) -> None:
    (install_dir / "state.json").write_text(json.dumps(asdict(state), indent=2))


def read_state(install_dir: Path) -> InstallState | None:
    path = install_dir / "state.json"
    if not path.exists():
        return None
    return InstallState(**json.loads(path.read_text()))


def is_installed(install_dir: Path) -> bool:
    state = read_state(install_dir)
    return state is not None and state.phase == "done"
