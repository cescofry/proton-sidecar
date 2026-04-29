import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from sidecar.steam import (
    SteamNotFoundError,
    ProtonNotFoundError,
    find_steam,
    find_prefix,
    linux_to_wine_path,
    slugify_game_name,
)


def test_slugify_game_name():
    assert slugify_game_name("Assetto Corsa Competizione") == "assetto-corsa-competizione"
    assert slugify_game_name("iRacing") == "iracing"
    assert slugify_game_name("  Game -- Name!!  ") == "game-name"
    assert slugify_game_name("F1 23") == "f1-23"
    assert slugify_game_name("GRID Legends") == "grid-legends"


def test_linux_to_wine_path():
    assert linux_to_wine_path(Path("/home/user/app/Game.exe")) == "Z:\\home\\user\\app\\Game.exe"
    assert linux_to_wine_path(Path("/tmp/setup.exe")) == "Z:\\tmp\\setup.exe"


def test_linux_to_wine_path_with_spaces():
    p = Path("/home/user/My Games/app.exe")
    assert linux_to_wine_path(p) == "Z:\\home\\user\\My Games\\app.exe"


def test_find_prefix_fallback(tmp_path):
    with patch("sidecar.steam.find_steam_path", return_value=(None, None)):
        result = find_prefix(tmp_path / "steam", 805550)
    assert result == tmp_path / "steam" / "steamapps" / "compatdata" / "805550" / "pfx"


def test_find_steam_success():
    fake_path = Path("/home/user/.steam/steam")
    with patch("sidecar.steam.find_steam_path", return_value=(fake_path, fake_path)):
        result = find_steam()
    assert result == fake_path


def test_find_steam_not_found():
    with patch("sidecar.steam.find_steam_path", return_value=(None, None)):
        with pytest.raises(SteamNotFoundError, match="Steam directory not found"):
            find_steam()


def test_find_proton_not_found():
    fake_path = Path("/fake/steam")
    with (
        patch("sidecar.steam.find_steam_path", return_value=(fake_path, fake_path)),
        patch("sidecar.steam.get_steam_lib_paths", return_value=[]),
        patch("sidecar.steam.get_steam_apps", return_value=[]),
        patch("sidecar.steam.find_proton_app", return_value=None),
    ):
        with pytest.raises(ProtonNotFoundError, match="No Proton version found"):
            from sidecar.steam import find_proton
            find_proton(fake_path, 805550)


def test_find_proton_success():
    fake_path = Path("/fake/steam")
    fake_proton = MagicMock()
    fake_proton.install_path = "/fake/steam/steamapps/common/Proton 8.0"
    with (
        patch("sidecar.steam.find_steam_path", return_value=(fake_path, fake_path)),
        patch("sidecar.steam.get_steam_lib_paths", return_value=[]),
        patch("sidecar.steam.get_steam_apps", return_value=[]),
        patch("sidecar.steam.find_proton_app", return_value=fake_proton),
    ):
        from sidecar.steam import find_proton
        result = find_proton(fake_path, 805550)
    assert result == Path("/fake/steam/steamapps/common/Proton 8.0/proton")
