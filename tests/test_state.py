import pytest
from pathlib import Path
from sidecar.state import InstallState, write_state, read_state, is_installed


def test_write_read_roundtrip(tmp_path):
    state = InstallState.new("test-app", 12345, "done")
    write_state(tmp_path, state)
    loaded = read_state(tmp_path)
    assert loaded is not None
    assert loaded.app_id == "test-app"
    assert loaded.game_appid == 12345
    assert loaded.phase == "done"
    assert loaded.started_at == state.started_at


def test_read_state_missing_file(tmp_path):
    assert read_state(tmp_path) is None


def test_is_installed_when_done(tmp_path):
    write_state(tmp_path, InstallState.new("a", 1, "done"))
    assert is_installed(tmp_path) is True


def test_is_installed_when_in_progress(tmp_path):
    write_state(tmp_path, InstallState.new("a", 1, "extracting"))
    assert is_installed(tmp_path) is False


def test_is_installed_no_state(tmp_path):
    assert is_installed(tmp_path) is False


def test_state_file_content(tmp_path):
    state = InstallState.new("my-app", 99999, "downloading")
    write_state(tmp_path, state)
    import json
    data = json.loads((tmp_path / "state.json").read_text())
    assert data["phase"] == "downloading"
    assert data["app_id"] == "my-app"
    assert data["game_appid"] == 99999


def test_corrupted_state_raises(tmp_path):
    (tmp_path / "state.json").write_text("not json {{{")
    with pytest.raises(Exception):
        read_state(tmp_path)
