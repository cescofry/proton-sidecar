# Manifest Reference

Each app in the registry is defined by a `manifest.toml` file, with an optional `install.py`
hook for custom logic.

**Design rule:** TOML declares *what* the app is and *where* to get it.
The Python hook handles *how* to install it when the defaults aren't enough.
Most apps need no hook at all.

---

## Minimal Example

An app that just needs to be downloaded, installed into a prefix, and launched:

```toml
[app]
id          = "crewchief"
name        = "Crew Chief V4"
description = "AI race engineer — voice feedback for tyres, fuel, gaps, penalties"
homepage    = "https://thecrewchief.org"

[requires]
games           = [805550, 266410, 365960]   # ACC, iRacing, rFactor 2
wine_components = ["dotnet472"]

[source]
url  = "https://thecrewchief.org/downloads/CrewChiefV4.msi"
type = "msi"

[launch]
exe = "CrewChiefV4.exe"

[meta]
tags        = ["sim-racing", "voice", "telemetry"]
linux_notes = """
After install, open the app and click:
  1. Download sound pack
  2. Download driver names
Then select your game and click Start Application.
"""
```

---

## Full Example (all optional fields shown)

```toml
[app]
id          = "acc-connector"
name        = "ACC Connector"
description = "Direct IP connection for Assetto Corsa Competizione"
homepage    = "https://github.com/lonemeow/acc-connector"

[requires]
games           = [805550]
wine_components = []        # conditional deps go in install.py

[source]
url           = "https://github.com/lonemeow/acc-connector/releases/latest"
type          = "inno"
asset_pattern = "Setup.*\\.exe$"

[install]
target_prefix = "game"
script        = "install.py"

[launch]
exe  = "ACC Connector.exe"
args = []

[launch.env]
# SOME_VAR = "value"

[meta]
tags        = ["sim-racing", "connectivity", "acc"]
linux_notes = ""
```

---

## Section Reference

### `[app]` — Identity

| Field | Required | Type | Description |
|---|---|---|---|
| `id` | yes | string | Unique slug used in CLI commands (`sidecar install acc-connector`) |
| `name` | yes | string | Human-readable display name |
| `description` | yes | string | One-line description |
| `homepage` | no | string | Project URL shown by `sidecar list` |

No version field. The tool always fetches the latest release from `[source]`.

---

### `[requires]` — Dependencies

| Field | Required | Type | Description |
|---|---|---|---|
| `games` | yes | list of integers | Steam App IDs. At least one must be installed. The first found is used as the target prefix. |
| `wine_components` | no | list of strings | winetricks verbs installed before the app. Unconditional only — conditional deps go in `install.py`. |

System tool requirements (`innoextract`, `msitools`) are inferred automatically from
`[source].type` and do not need to be declared.

---

### `[source]` — Download

| Field | Required | Type | Description |
|---|---|---|---|
| `url` | yes | string | Direct download URL, or a GitHub releases page URL (e.g. `.../releases/latest`) |
| `type` | yes | string | Installer format: `inno`, `msi`, `zip`, `raw_exe`, `raw_dir` |
| `asset_pattern` | no | string | Regex matched against asset filenames on a GitHub releases page. Required when `url` points to GitHub releases. |

**`type` values:**

| Value | Tool used | When to use |
|---|---|---|
| `inno` | `innoextract` | Inno Setup `.exe` installer |
| `msi` | `msiextract` or `wine msiexec` | Windows Installer `.msi` |
| `zip` | Python `zipfile` | Plain ZIP archive |
| `raw_exe` | — (copy as-is) | Standalone executable, no installer |
| `raw_dir` | — (copy as-is) | Pre-extracted directory |

---

### `[install]` — Install Behaviour

| Field | Required | Type | Description |
|---|---|---|---|
| `target_prefix` | no | string | `"game"` (default) shares the first matched game's Proton prefix. `"standalone"` creates a dedicated prefix — use only for apps that don't need game IPC. |
| `script` | no | string | Filename of the Python hook module (e.g. `"install.py"`). Omit when no custom logic is needed. |

---

### `[launch]` — Runtime

| Field | Required | Type | Description |
|---|---|---|---|
| `exe` | yes | string | Path to the Windows EXE relative to the app's extracted directory |
| `args` | no | list of strings | Default arguments passed to the EXE. The user can append extra args with `sidecar run <app> -- <args>`. |

---

### `[launch.env]` — Environment Variables

Key-value pairs added to the environment when Proton launches the EXE.
Useful for flags the app reads from the environment. Omit the section entirely if not needed.

```toml
[launch.env]
SOME_FLAG = "1"
ANOTHER   = "value"
```

---

### `[meta]` — Discovery and Notes

| Field | Required | Type | Description |
|---|---|---|---|
| `tags` | no | list of strings | Used by `sidecar list` filtering. Conventions: game slug (`acc`, `iracing`), category (`telemetry`, `voice`, `overlay`). |
| `linux_notes` | no | string | Printed after install. Use for manual steps the tool cannot automate (e.g. clicking "Download sound pack"). |

---

## Python Hook (`install.py`)

When `[install].script` is set, the tool imports the file as a Python module and looks
for a class named `Hook` that subclasses `sidecar.hook.Hook`. The tool instantiates it
with the parsed manifest, then calls whichever methods are defined. All are optional —
override only what you need.

```python
# sidecar/hook.py  (base class — do not import directly in manifests)
class Hook:
    def __init__(self, manifest: Manifest) -> None:
        self.manifest = manifest   # full parsed manifest always available

    def post_install(self, ctx: InstallContext) -> None: ...
    def pre_launch(self, ctx: LaunchContext) -> None: ...
    def post_launch(self, ctx: LaunchContext) -> None: ...
    def uninstall(self, ctx: InstallContext) -> None: ...
```

The base implementations are no-ops. Subclasses override only what they need.

### `InstallContext` fields

Passed as `ctx` to `post_install` and `uninstall`. Carries everything resolved at
install time that a hook might need.

| Field | Type | Description |
|---|---|---|
| `steam_dir` | `Path` | Detected Steam root directory |
| `game_appid` | `int` | Steam App ID of the matched game |
| `game_dir` | `Path` | Game installation directory (where the game EXE lives) |
| `prefix_dir` | `Path` | Proton prefix root (`compatdata/<APPID>/pfx/`) |
| `install_dir` | `Path` | Sidecar's directory for this app (`~/.local/share/sidecar/<app-id>/`) |
| `app_dir` | `Path` | Extracted app files (`install_dir/app/`) |
| `proton_bin` | `Path` | Path to the Proton binary |

### `LaunchContext` fields

All `InstallContext` fields, plus:

| Field | Type | Description |
|---|---|---|
| `exe_path` | `Path` | Linux path to the EXE being launched |
| `args` | `list[str]` | Arguments that will be passed to the EXE |

### Hook example — acc-connector

```python
# apps/acc-connector/install.py
import shutil
from pathlib import Path
from sidecar.hook import Hook as BaseHook

class Hook(BaseHook):
    def post_install(self, ctx):
        hook_dll = ctx.app_dir / "client-hooks.dll"
        target   = ctx.game_dir / "AC2/Binaries/Win64/hid.dll"

        if target.exists():
            shutil.copy2(target, target.with_suffix(".dll.bak"))

        shutil.copy2(hook_dll, target)

        # record deployed path so uninstall() can find it
        (ctx.install_dir / ".acc_path").write_text(str(ctx.game_dir))

        # check DLL count to decide if .NET 8 desktop runtime is needed
        dll_count = len(list(ctx.app_dir.glob("*.dll")))
        if dll_count < 10:
            print(f"NOTE: {self.manifest.app.name} may need dotnetdesktop8 — "
                  f"run `protontricks 805550 dotnetdesktop8` if the GUI fails to start.")

    def uninstall(self, ctx):
        acc_path = ctx.install_dir / ".acc_path"
        if not acc_path.exists():
            return
        game_dir = Path(acc_path.read_text().strip())
        hid      = game_dir / "AC2/Binaries/Win64/hid.dll"
        bak      = hid.with_suffix(".dll.bak")
        hid.unlink(missing_ok=True)
        if bak.exists():
            bak.rename(hid)
```

---

## Real Manifests

### CrewChief V4

```toml
[app]
id          = "crewchief"
name        = "Crew Chief V4"
description = "AI race engineer — voice feedback for tyres, fuel, gaps, penalties"
homepage    = "https://thecrewchief.org"

[requires]
games           = [805550, 266410, 365960]   # ACC, iRacing, rFactor 2
wine_components = ["dotnet472"]

[source]
url           = "https://thecrewchief.org/downloads/CrewChiefV4.msi"
type          = "msi"

[launch]
exe = "CrewChiefV4.exe"

[meta]
tags        = ["sim-racing", "voice", "telemetry", "acc", "iracing", "rf2"]
linux_notes = """
After install, open the app and click:
  1. Download sound pack
  2. Download driver names
Then select your game and click Start Application.
"""
```

No hook needed. The tool handles the MSI install; the post-install steps are manual and documented in `linux_notes`.

---

### ACC Connector

```toml
[app]
id          = "acc-connector"
name        = "ACC Connector"
description = "Direct IP connection for Assetto Corsa Competizione"
homepage    = "https://github.com/lonemeow/acc-connector"

[requires]
games           = [805550]
wine_components = []

[source]
url           = "https://github.com/lonemeow/acc-connector/releases/latest"
type          = "inno"
asset_pattern = "Setup.*\\.exe$"

[install]
script = "install.py"

[launch]
exe = "ACC Connector.exe"

[meta]
tags = ["sim-racing", "connectivity", "acc"]
```

Hook (`install.py`) handles: DLL deploy with backup, `.desktop` files, `acc-connect://` protocol handler, conditional .NET 8 warning, and uninstall.
