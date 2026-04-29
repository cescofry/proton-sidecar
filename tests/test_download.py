import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from sidecar.download import DownloadError, resolve_github_release_url, download_file


def _fake_release_response(asset_names: list[str], status_code: int = 200):
    resp = MagicMock()
    resp.ok = status_code < 400
    resp.status_code = status_code
    resp.json.return_value = {
        "assets": [
            {"name": name, "browser_download_url": f"https://example.com/{name}"}
            for name in asset_names
        ]
    }
    return resp


def test_resolve_github_release_url_matches_pattern():
    with patch("sidecar.download.requests.get", return_value=_fake_release_response(
        ["OtherSetup.exe", "ACCConnector-Setup-1.0.exe"]
    )):
        url = resolve_github_release_url(
            "https://github.com/owner/repo/releases/latest",
            r"ACCConnector-Setup.*\.exe$",
        )
    assert url == "https://example.com/ACCConnector-Setup-1.0.exe"


def test_resolve_github_release_url_no_match_raises():
    with patch("sidecar.download.requests.get", return_value=_fake_release_response(
        ["source.tar.gz", "README.md"]
    )):
        with pytest.raises(DownloadError, match="No release asset matching"):
            resolve_github_release_url(
                "https://github.com/owner/repo/releases/latest",
                r"Setup.*\.exe$",
            )


def test_resolve_github_release_url_rate_limit_raises():
    resp = MagicMock()
    resp.ok = False
    resp.status_code = 403
    with patch("sidecar.download.requests.get", return_value=resp):
        with pytest.raises(DownloadError, match="GITHUB_TOKEN"):
            resolve_github_release_url(
                "https://github.com/owner/repo/releases/latest",
                r"Setup.*\.exe$",
            )


def test_resolve_github_release_url_bad_url_raises():
    with pytest.raises(DownloadError, match="Cannot parse GitHub releases URL"):
        resolve_github_release_url("https://example.com/not-github", r".*\.exe$")


def test_download_file_saves_to_dest(tmp_path):
    content = b"fake binary content"
    resp = MagicMock()
    resp.ok = True
    resp.headers = {"content-length": str(len(content))}
    resp.iter_content = MagicMock(return_value=[content])
    resp.raise_for_status = MagicMock()

    with patch("sidecar.download.requests.get", return_value=resp):
        result = download_file(
            "https://example.com/Setup.exe", tmp_path, show_progress=False
        )

    assert result == tmp_path / "Setup.exe"
    assert result.read_bytes() == content


def test_download_file_creates_dest_dir(tmp_path):
    dest = tmp_path / "subdir"
    content = b"data"
    resp = MagicMock()
    resp.ok = True
    resp.headers = {}
    resp.iter_content = MagicMock(return_value=[content])
    resp.raise_for_status = MagicMock()

    with patch("sidecar.download.requests.get", return_value=resp):
        download_file("https://example.com/file.zip", dest, show_progress=False)

    assert dest.is_dir()


def test_download_file_request_error_raises(tmp_path):
    import requests as req_lib
    with patch("sidecar.download.requests.get", side_effect=req_lib.ConnectionError("fail")):
        with pytest.raises(DownloadError, match="Download failed"):
            download_file("https://example.com/x.exe", tmp_path, show_progress=False)
