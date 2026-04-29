import tomllib
from dataclasses import dataclass, field
from pathlib import Path

_VALID_SOURCE_TYPES = frozenset({"inno", "msi", "zip", "raw_exe", "raw_dir"})
_VALID_TARGET_PREFIXES = frozenset({"game", "standalone"})
_GITHUB_RELEASES_PATTERN = "/releases/"


class ManifestError(ValueError):
    pass


@dataclass
class AppMeta:
    id: str
    name: str
    description: str
    homepage: str = ""


@dataclass
class Requires:
    games: list[int]
    wine_components: list[str] = field(default_factory=list)


@dataclass
class Source:
    url: str
    type: str
    asset_pattern: str = ""


@dataclass
class Install:
    target_prefix: str = "game"
    script: str = ""


@dataclass
class Launch:
    exe: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)


@dataclass
class Meta:
    tags: list[str] = field(default_factory=list)
    linux_notes: str = ""


@dataclass
class Manifest:
    app: AppMeta
    requires: Requires
    source: Source
    launch: Launch
    install: Install = field(default_factory=Install)
    meta: Meta = field(default_factory=Meta)

    @classmethod
    def from_toml(cls, path: Path) -> "Manifest":
        try:
            with open(path, "rb") as f:
                data = tomllib.load(f)
        except tomllib.TOMLDecodeError as exc:
            raise ManifestError(f"Invalid TOML in {path}: {exc}") from exc

        try:
            app = AppMeta(**data["app"])
            requires_data = data["requires"]
            requires = Requires(
                games=list(requires_data["games"]),
                wine_components=list(requires_data.get("wine_components", [])),
            )
            src_data = data["source"]
            source = Source(
                url=src_data["url"],
                type=src_data["type"],
                asset_pattern=src_data.get("asset_pattern", ""),
            )
            launch_data = data["launch"]
            launch = Launch(
                exe=launch_data["exe"],
                args=list(launch_data.get("args", [])),
                env=dict(launch_data.get("env", {})),
            )
            install_data = data.get("install", {})
            install = Install(
                target_prefix=install_data.get("target_prefix", "game"),
                script=install_data.get("script", ""),
            )
            meta_data = data.get("meta", {})
            meta = Meta(
                tags=list(meta_data.get("tags", [])),
                linux_notes=str(meta_data.get("linux_notes", "")),
            )
        except (KeyError, TypeError) as exc:
            raise ManifestError(f"Missing required field in {path}: {exc}") from exc

        manifest = cls(
            app=app,
            requires=requires,
            source=source,
            launch=launch,
            install=install,
            meta=meta,
        )
        _validate(manifest, path)
        return manifest


def _validate(manifest: Manifest, path: Path) -> None:
    if manifest.source.type not in _VALID_SOURCE_TYPES:
        raise ManifestError(
            f"{path}: source.type must be one of {sorted(_VALID_SOURCE_TYPES)}, "
            f"got {manifest.source.type!r}"
        )

    if not manifest.requires.games:
        raise ManifestError(f"{path}: requires.games must not be empty")

    if not all(isinstance(g, int) for g in manifest.requires.games):
        raise ManifestError(f"{path}: requires.games must contain integers only")

    if manifest.install.target_prefix not in _VALID_TARGET_PREFIXES:
        raise ManifestError(
            f"{path}: install.target_prefix must be one of {sorted(_VALID_TARGET_PREFIXES)}, "
            f"got {manifest.install.target_prefix!r}"
        )

    if _GITHUB_RELEASES_PATTERN in manifest.source.url and not manifest.source.asset_pattern:
        raise ManifestError(
            f"{path}: source.asset_pattern is required when source.url is a GitHub releases URL"
        )
