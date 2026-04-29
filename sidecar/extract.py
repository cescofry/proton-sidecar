import shutil
import subprocess
import zipfile
from pathlib import Path

from sidecar.manifest import Source


class ExtractionError(RuntimeError):
    pass


class MissingToolError(RuntimeError):
    def __init__(self, tool: str, hint: str = "") -> None:
        self.tool = tool
        msg = f"Required tool '{tool}' not found in PATH."
        if hint:
            msg += f" Install it with: {hint}"
        super().__init__(msg)


_INSTALL_HINTS: dict[str, str] = {
    "innoextract": "sudo apt install innoextract  # or: brew install innoextract",
    "msiextract": "sudo apt install msitools",
}


def extract(source: Source, installer: Path, dest: Path, log: Path) -> None:
    """Dispatch extraction to the correct handler based on source.type."""
    dest.mkdir(parents=True, exist_ok=True)
    match source.type:
        case "inno":
            _extract_inno(installer, dest, log)
        case "msi":
            _extract_msi(installer, dest, log)
        case "zip":
            _extract_zip(installer, dest)
        case "raw_exe":
            _copy_raw(installer, dest)
        case "raw_dir":
            _copy_raw_dir(installer, dest)
        case _:
            raise ExtractionError(f"Unknown source type: {source.type!r}")


def _require_tool(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        raise MissingToolError(name, _INSTALL_HINTS.get(name, ""))
    return path


def _run(cmd: list[str], log: Path) -> None:
    with open(log, "ab") as f:
        result = subprocess.run(cmd, stdout=f, stderr=f)
    if result.returncode != 0:
        raise ExtractionError(
            f"Command failed (exit {result.returncode}): {' '.join(cmd)}. "
            f"See {log} for details."
        )


def _extract_inno(src: Path, dest: Path, log: Path) -> None:
    tool = _require_tool("innoextract")
    _run([tool, "--output-dir", str(dest), str(src)], log)


def _extract_msi(src: Path, dest: Path, log: Path) -> None:
    if shutil.which("msiextract"):
        tool = _require_tool("msiextract")
        _run([tool, "-C", str(dest), str(src)], log)
    else:
        wine = _require_tool("wine")
        _run(
            [wine, "msiexec", "/a", str(src), "/qb", f"TARGETDIR={dest}"],
            log,
        )


def _extract_zip(src: Path, dest: Path) -> None:
    try:
        with zipfile.ZipFile(src, "r") as zf:
            zf.extractall(dest)
    except zipfile.BadZipFile as exc:
        raise ExtractionError(f"Invalid ZIP file {src}: {exc}") from exc


def _copy_raw(src: Path, dest: Path) -> None:
    shutil.copy2(src, dest / src.name)


def _copy_raw_dir(src: Path, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)
