import os
import shutil
import subprocess
from pathlib import Path

from sidecar.hook import Hook as BaseHook
from sidecar.context import InstallContext, LaunchContext


class Hook(BaseHook):
    def post_install(self, ctx: InstallContext) -> None:
        hook_dll = ctx.app_dir / "client-hooks.dll"
        target   = ctx.game_dir / "AC2/Binaries/Win64/hid.dll"

        if target.exists():
            shutil.copy2(target, target.with_suffix(".dll.bak"))
        shutil.copy2(hook_dll, target)

        (ctx.install_dir / ".acc_path").write_text(str(ctx.game_dir))

        dll_count = len(list(ctx.app_dir.glob("*.dll")))
        if dll_count < 10:
            print(
                f"NOTE: {self.manifest.app.name} may need dotnetdesktop8 — "
                f"run `protontricks {ctx.game_appid} dotnetdesktop8` if the GUI fails to start."
            )

        self._register_wine_protocol(ctx)

    def _register_wine_protocol(self, ctx: InstallContext) -> None:
        # innoextract extracts files only — the Inno Setup [Registry] section is not executed,
        # so we must add the acc-connect:// handler to the Wine prefix registry ourselves.
        exe_linux = str(ctx.app_dir / "ACC Connector.exe")
        exe_reg   = "Z:" + exe_linux.replace("/", "\\\\")

        reg_file = ctx.install_dir / "acc-connect.reg"
        reg_file.write_text("\n".join([
            "Windows Registry Editor Version 5.00",
            "",
            "[HKEY_CLASSES_ROOT\\acc-connect]",
            '@="URL:Custom Protocol"',
            '"URL Protocol"=""',
            "",
            "[HKEY_CLASSES_ROOT\\acc-connect\\DefaultIcon]",
            f'@="{exe_reg},0"',
            "",
            "[HKEY_CLASSES_ROOT\\acc-connect\\shell\\open\\command]",
            f'@="\\"{ exe_reg }\\" \\"%1\\""',
            "",
        ]))

        reg_win = "Z:" + str(reg_file).replace("/", "\\")
        env = {
            **os.environ,
            "STEAM_COMPAT_DATA_PATH": str(ctx.prefix_dir.parent),
            "STEAM_COMPAT_CLIENT_INSTALL_PATH": str(ctx.steam_dir),
        }
        subprocess.run(
            [str(ctx.proton_bin), "run", "regedit", reg_win],
            env=env,
            check=True,
        )

    def uninstall(self, ctx: InstallContext) -> None:
        acc_path = ctx.install_dir / ".acc_path"
        if not acc_path.exists():
            return
        game_dir = Path(acc_path.read_text().strip())
        hid = game_dir / "AC2/Binaries/Win64/hid.dll"
        bak = hid.with_suffix(".dll.bak")
        hid.unlink(missing_ok=True)
        if bak.exists():
            bak.rename(hid)
