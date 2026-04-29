import re
import sys
from pathlib import Path

import requests

GITHUB_API_BASE = "https://api.github.com"
_GITHUB_REPO_RE = re.compile(
    r"https://github\.com/([^/]+/[^/]+)/releases/(latest|tag/[^/]+)$"
)


class DownloadError(RuntimeError):
    pass


def resolve_github_release_url(releases_url: str, asset_pattern: str) -> str:
    """
    Resolve a GitHub releases page URL to a direct asset download URL.
    asset_pattern is a regex matched against the asset filename.
    """
    m = _GITHUB_REPO_RE.match(releases_url.rstrip("/"))
    if not m:
        raise DownloadError(
            f"Cannot parse GitHub releases URL: {releases_url!r}. "
            "Expected format: https://github.com/owner/repo/releases/latest"
        )

    repo = m.group(1)
    ref = m.group(2)
    api_path = f"releases/latest" if ref == "latest" else f"releases/tags/{ref[4:]}"
    api_url = f"{GITHUB_API_BASE}/repos/{repo}/{api_path}"

    headers = {"Accept": "application/vnd.github+json"}
    token = _github_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        resp = requests.get(api_url, headers=headers, timeout=30)
    except requests.RequestException as exc:
        raise DownloadError(f"GitHub API request failed: {exc}") from exc

    if resp.status_code == 403:
        raise DownloadError(
            f"GitHub API rate-limited (403). Set the GITHUB_TOKEN environment variable "
            f"to authenticate and raise the rate limit."
        )
    if not resp.ok:
        raise DownloadError(
            f"GitHub API returned {resp.status_code} for {api_url}"
        )

    assets = resp.json().get("assets", [])
    pattern = re.compile(asset_pattern)
    for asset in assets:
        if pattern.search(asset["name"]):
            return asset["browser_download_url"]

    names = [a["name"] for a in assets]
    raise DownloadError(
        f"No release asset matching {asset_pattern!r} found in {releases_url}. "
        f"Available assets: {names}"
    )


def download_file(url: str, dest_dir: Path, show_progress: bool = True) -> Path:
    """Download url into dest_dir, streaming the response. Returns the saved file path."""
    dest_dir.mkdir(parents=True, exist_ok=True)

    filename = url.rstrip("/").split("/")[-1].split("?")[0] or "download"
    dest = dest_dir / filename

    try:
        resp = requests.get(url, stream=True, timeout=60)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise DownloadError(f"Download failed for {url}: {exc}") from exc

    total = int(resp.headers.get("content-length", 0))
    downloaded = 0

    with open(dest, "wb") as f:
        for chunk in resp.iter_content(chunk_size=65536):
            f.write(chunk)
            downloaded += len(chunk)
            if show_progress and total:
                _print_progress(downloaded, total)

    if show_progress and total:
        print(file=sys.stderr)

    return dest


def _github_token() -> str:
    import os
    return os.environ.get("GITHUB_TOKEN", "")


def _print_progress(downloaded: int, total: int) -> None:
    pct = downloaded * 100 // total
    mb = downloaded / 1_048_576
    print(f"\r  Downloading... {mb:.1f} MB ({pct}%)", end="", file=sys.stderr, flush=True)
