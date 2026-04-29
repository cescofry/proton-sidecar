import io
import zipfile
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, call
from sidecar.extract import (
    ExtractionError,
    MissingToolError,
    extract,
    _require_tool,
    _extract_zip,
)
from sidecar.manifest import Source


def _source(type_: str) -> Source:
    return Source(url="https://example.com/file", type=type_)


def test_require_tool_found():
    with patch("sidecar.extract.shutil.which", return_value="/usr/bin/innoextract"):
        assert _require_tool("innoextract") == "/usr/bin/innoextract"


def test_require_tool_missing_raises():
    with patch("sidecar.extract.shutil.which", return_value=None):
        with pytest.raises(MissingToolError, match="innoextract"):
            _require_tool("innoextract")


def test_require_tool_missing_includes_hint():
    with patch("sidecar.extract.shutil.which", return_value=None):
        exc = pytest.raises(MissingToolError, _require_tool, "innoextract")
        assert "apt install innoextract" in str(exc.value)


def test_extract_inno_dispatches_correctly(tmp_path):
    installer = tmp_path / "setup.exe"
    installer.touch()
    log = tmp_path / "install.log"
    dest = tmp_path / "app"

    with (
        patch("sidecar.extract.shutil.which", return_value="/usr/bin/innoextract"),
        patch("sidecar.extract.subprocess.run") as mock_run,
    ):
        mock_run.return_value = MagicMock(returncode=0)
        extract(_source("inno"), installer, dest, log)

    cmd = mock_run.call_args[0][0]
    assert cmd[0] == "/usr/bin/innoextract"
    assert "--output-dir" in cmd
    assert str(dest) in cmd
    assert str(installer) in cmd


def test_extract_inno_missing_tool_raises(tmp_path):
    installer = tmp_path / "setup.exe"
    installer.touch()
    with patch("sidecar.extract.shutil.which", return_value=None):
        with pytest.raises(MissingToolError):
            extract(_source("inno"), installer, tmp_path / "app", tmp_path / "log")


def test_extract_subprocess_failure_raises(tmp_path):
    installer = tmp_path / "setup.exe"
    installer.touch()
    log = tmp_path / "install.log"
    dest = tmp_path / "app"

    with (
        patch("sidecar.extract.shutil.which", return_value="/usr/bin/innoextract"),
        patch("sidecar.extract.subprocess.run") as mock_run,
    ):
        mock_run.return_value = MagicMock(returncode=1)
        with pytest.raises(ExtractionError, match="Command failed"):
            extract(_source("inno"), installer, dest, log)


def test_extract_zip_real(tmp_path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("hello.txt", "hello world")
    installer = tmp_path / "archive.zip"
    installer.write_bytes(buf.getvalue())
    dest = tmp_path / "out"

    _extract_zip(installer, dest)

    assert (dest / "hello.txt").read_text() == "hello world"


def test_extract_zip_bad_file_raises(tmp_path):
    bad = tmp_path / "bad.zip"
    bad.write_bytes(b"not a zip")
    with pytest.raises(ExtractionError, match="Invalid ZIP"):
        _extract_zip(bad, tmp_path / "out")


def test_extract_raw_exe(tmp_path):
    installer = tmp_path / "app.exe"
    installer.write_bytes(b"\x4d\x5a")
    dest = tmp_path / "app"
    dest.mkdir()
    extract(_source("raw_exe"), installer, dest, tmp_path / "log")
    assert (dest / "app.exe").exists()


def test_extract_unknown_type_raises(tmp_path):
    with pytest.raises(ExtractionError, match="Unknown source type"):
        extract(_source("tarball"), tmp_path / "x", tmp_path / "out", tmp_path / "log")


def test_extract_msi_uses_msiextract_when_available(tmp_path):
    installer = tmp_path / "app.msi"
    installer.touch()
    log = tmp_path / "install.log"
    dest = tmp_path / "app"

    def which_side_effect(name: str):
        return "/usr/bin/msiextract" if name == "msiextract" else None

    with (
        patch("sidecar.extract.shutil.which", side_effect=which_side_effect),
        patch("sidecar.extract.subprocess.run") as mock_run,
    ):
        mock_run.return_value = MagicMock(returncode=0)
        extract(_source("msi"), installer, dest, log)

    cmd = mock_run.call_args[0][0]
    assert cmd[0] == "/usr/bin/msiextract"
