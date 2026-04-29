# Tech Spec — proton-sidecar

Technical decisions locked in before implementation. Use this as the reference during development.

---

## Language & Toolchain

**Python 3.11+**, distributed via `pipx`.

- protontricks is Python — same ecosystem, same install path
- `pathlib`, `tomllib`, `subprocess`, `urllib` cover most work in stdlib
- `Click` or `Typer` for subcommand CLI
- `pipx install` is a single-command user install with no virtualenv friction

**Manifest format: TOML**

- Python stdlib support since 3.11 (`tomllib` read-only; `tomli` for writing)
- No YAML footguns (indentation, `yes`/`on`/`true` ambiguity, auto-type coercion)
- Readable for multi-value lists and nested sections
- Familiar from `pyproject.toml`

---

## Dependency Chain

| Dependency | Status | Purpose |
|---|---|---|
| `steam` | required | locate prefixes and App IDs |
| `protontricks` | required | install Wine components and run setup executables |
| `python 3.11+` | required | runtime for the tool itself |
| `pipx` | recommended | install method |
| `innoextract` | optional | auto-installed when needed, for Inno Setup installers |
| `msitools` | optional | for MSI-based installers |

**No Lutris, no Bottles.**
- Bottles is Flatpak-sandboxed and cannot access Proton prefixes outside its sandbox
- Lutris adds a heavy GUI dependency with no benefit to the CLI workflow
- Lutris integration can be a future optional export feature (not a dependency)

---

## protontricks Integration

Treat protontricks as a **maintained dependency**. Version-pin it in `pyproject.toml`.

Import from `protontricks.steam` directly rather than shelling out to parse Steam paths:

```python
from protontricks.steam import find_steam_path, get_steam_apps, find_proton_app
```

`steam.py` in the sidecar tool is a thin wrapper around these imports — not a custom VDF parser.

> Pin the version and add a smoke test that exercises the import so breakage on upgrades is caught immediately. protontricks does not advertise a stable public API.

**Critical limitation:** Since Proton 6, you cannot run two programs simultaneously in the same prefix through protontricks. This is why the tool uses two distinct phases.

---

## Two-Phase Architecture

```
INSTALL PHASE (protontricks)         RUNTIME PHASE (direct Proton)
────────────────────────────         ──────────────────────────────
protontricks <APPID> <verbs>    →    export STEAM_COMPAT_DATA_PATH=".../compatdata/<APPID>"
protontricks -c "wine msiexec"       export STEAM_COMPAT_CLIENT_INSTALL_PATH="$STEAM_DIR"
                                     exec "$PROTON" run "Z:\path\to\companion.exe"
```

The install phase uses protontricks for all prefix work. The runtime phase generates a shell launcher script that invokes Proton directly — this avoids the concurrency lock because it uses the same mechanism Steam itself uses.

### Install Phase Steps

1. Parse manifest TOML
2. Detect Steam + find which `requires.games` are installed
3. Prompt user to select one game (skip if only one installed)
4. `protontricks <APPID> <wine_components...>`
5. Download source (GitHub API or direct URL)
6. Extract (innoextract / msiextract / unzip)
7. Run `install.py` → `post_install(ctx)`
8. Write launcher to `~/.local/share/sidecar/<app>/<game-appid>/launch.sh`
9. Create `.desktop` file + register URI handlers (`xdg-mime`)

### Runtime Phase (generated launcher script)

1. Run `pre_launch(ctx)` if defined
2. Locate Proton binary
3. Set `STEAM_COMPAT_DATA_PATH` + `STEAM_COMPAT_CLIENT_INSTALL_PATH`
4. `exec $PROTON run Z:\path\to\companion.exe [args]`
5. Run `post_launch(ctx)` after exit

---

## Directory Structure

### Git repo (source — what contributors work with)

```
proton-sidecar/
├── sidecar/                    # Python CLI tool
│   ├── __init__.py
│   ├── cli.py                  # Click/Typer entry point
│   ├── steam.py                # Steam/prefix detection (thin wrapper over protontricks.steam)
│   ├── install.py              # Download, extract, deploy, protontricks calls
│   ├── launch.py               # Generate and run Proton launcher scripts
│   ├── manifest.py             # TOML manifest loading and validation
│   ├── hook.py                 # Hook base class
│   └── context.py              # Shared types: AppID, SteamPaths, InstallContext, LaunchContext
│
├── apps/                       # App manifest registry — the contribution surface
│   ├── acc-connector/
│   │   ├── manifest.toml
│   │   └── install.py
│   ├── crewchief/
│   │   └── manifest.toml
│   └── simhub/
│       ├── manifest.toml
│       └── install.py
│
├── Documentation/
├── pyproject.toml
└── README.md
```

### `~/.local/share/sidecar/` (artifacts — generated at runtime, never committed)

Each app install is scoped to a specific game prefix. Installing the same app for multiple games creates separate artifact directories.

```
~/.local/share/sidecar/
└── <app-id>/
    └── <game-appid>/
        ├── app/                # extracted app files
        ├── launch.sh           # generated Proton launcher
        ├── state.json          # install state
        ├── install.log         # full install log
        └── <hook files>        # anything a hook writes (e.g. .acc_path)
```

---

## Manifest Design

**Design rule:** TOML declares *what* the app is and *where* to get it. Python hook handles *how* to install when defaults aren't enough. Most apps need no hook.

Key decisions:
- **No `version` field** — always fetch the latest release from `[source]`
- **No system field** — required tools (`innoextract`, `msitools`) are inferred from `[source].type`
- **No `[install.deploy]` section** — file deployment goes in `install.py`

Full schema reference: [`manifest.md`](manifest.md)

---

## Hook System

Each app can optionally include `install.py` with a class named `Hook` subclassing `sidecar.hook.Hook`.

```python
# sidecar/hook.py
class Hook:
    def __init__(self, manifest: Manifest) -> None:
        self.manifest = manifest

    def post_install(self, ctx: InstallContext) -> None: ...
    def pre_launch(self, ctx: LaunchContext) -> None: ...
    def post_launch(self, ctx: LaunchContext) -> None: ...
    def uninstall(self, ctx: InstallContext) -> None: ...
```

- The tool imports `install.py`, finds `Hook` by name, instantiates it, calls the appropriate method
- Subclasses override only what they need; base implementations are no-ops
- All app-specific logic lives here: DLL deployment, protocol handlers, `.desktop` files, conditional deps, uninstall cleanup

Context types (`InstallContext`, `LaunchContext`) are documented in [`manifest.md`](manifest.md).

---

## CLI Commands

```bash
sidecar list                         # list all available apps in the registry
sidecar list --installed             # list only installed apps (shows per-game installs)

sidecar install <app-id>             # install — prompts user to pick a game from requires.games
sidecar remove <app-id>              # remove all installs of the app
sidecar remove <app-id>-<game-slug>  # remove a specific game install

sidecar run <app-id>                 # launch (only valid when exactly one game is installed)
sidecar run <app-id>-<game-slug>     # launch for a specific game
sidecar run <app-id>-<game-slug> -- <args>  # pass extra args to the Windows EXE

sidecar doctor                       # check system: Steam, protontricks, Proton versions
```

**`<game-slug>` derivation:** lowercased game name, non-alphanumeric characters replaced with hyphens, consecutive hyphens collapsed.
Example: `"Assetto Corsa Competizione"` → `assetto-corsa-competizione`

---

## Installer Extraction

| Installer type | Tool | Detection |
|---|---|---|
| Inno Setup `.exe` | `innoextract` | File header or try and check exit code |
| MSI | `msiextract` (msitools) or `wine msiexec` | `.msi` extension |
| ZIP | Python `zipfile` stdlib | `.zip` extension |
| NSIS `.exe` | out of scope for v1 | — |
| Raw `.exe` | copy as-is | `type = "raw_exe"` in manifest |

---

## Error Handling

### State file

`state.json` written at the start of each phase boundary so a crash leaves a record of where it stopped.

```json
{
  "phase": "extracting",
  "app_id": "crewchief",
  "started_at": "2026-04-29T14:03:00Z",
  "game_appid": 805550
}
```

Phases in order: `downloading` → `extracting` → `installing_deps` → `running_hook` → `done`

### Subprocess output

All subprocess calls redirect stdout and stderr to `install.log`. No streaming to terminal during normal install.

### On failure

Catch exception, write traceback to `install.log`, print one-line message to stderr:

```
Error: install failed during 'extracting' — see ~/.local/share/sidecar/crewchief/install.log
```

**No automatic rollback.** `install_dir` is left in place to preserve the log. Re-running `sidecar install <app>` overwrites `state.json` and `install.log`. protontricks/winetricks verb installs are idempotent — re-running is safe.

---

## Windows Path Construction

Wine maps `Z:` to the Linux root:

```
/home/user/.local/share/sidecar/crewchief/app/CrewChiefV4.exe
→ Z:\home\user\.local\share\sidecar\crewchief\app\CrewChiefV4.exe
```

In Python: `"Z:" + str(path).replace("/", "\\")`
