import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from sidecar.hook import Hook, load_hook


@pytest.fixture
def minimal_manifest():
    m = MagicMock()
    m.app.id = "test-app"
    return m


def test_base_hook_methods_are_noop(minimal_manifest):
    h = Hook(minimal_manifest)
    ctx = MagicMock()
    h.post_install(ctx)
    h.pre_launch(ctx)
    h.post_launch(ctx)
    h.uninstall(ctx)


def test_load_hook_valid(tmp_path, minimal_manifest):
    script = tmp_path / "install.py"
    script.write_text(
        "from sidecar.hook import Hook as BaseHook\n"
        "class Hook(BaseHook):\n"
        "    def post_install(self, ctx):\n"
        "        self.called = True\n"
    )
    hook = load_hook(script, minimal_manifest)
    assert isinstance(hook, Hook)
    assert hook.manifest is minimal_manifest


def test_load_hook_calls_method(tmp_path, minimal_manifest):
    script = tmp_path / "install.py"
    script.write_text(
        "from sidecar.hook import Hook as BaseHook\n"
        "class Hook(BaseHook):\n"
        "    def post_install(self, ctx):\n"
        "        ctx.marker = 'hit'\n"
    )
    hook = load_hook(script, minimal_manifest)
    ctx = MagicMock()
    hook.post_install(ctx)
    assert ctx.marker == "hit"


def test_load_hook_no_class_raises(tmp_path, minimal_manifest):
    script = tmp_path / "install.py"
    script.write_text("x = 1\n")
    with pytest.raises(ImportError, match="No 'Hook' class"):
        load_hook(script, minimal_manifest)


def test_load_hook_wrong_base_class_raises(tmp_path, minimal_manifest):
    script = tmp_path / "install.py"
    script.write_text("class Hook:\n    pass\n")
    with pytest.raises(ImportError, match="subclasses sidecar.hook.Hook"):
        load_hook(script, minimal_manifest)
