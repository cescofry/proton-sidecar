# Tech Notes — proton-sidecar

Reference material, research context, and ecosystem knowledge. Not decisions — background that informs them.

---

## What We're Building

A Linux CLI tool that manages the lifecycle of **companion apps** — Windows applications that need to run alongside a Proton/Wine game, sharing its prefix for IPC.

Think of it as a package manager where each "package" is a Windows app that hooks into a specific game. The tool hosts a registry of app manifests. Installation clones the git repo — this is how users can contribute new manifests.

The tool has NO TUI, just normal script output.

---

## Reference Projects

These two are the first candidates to be turned into manifests. Not part of the tool itself.

### acc-connector (ACC — Assetto Corsa Competizione)

**Purpose:** Bypass ACC's LAN-only server discovery so players can connect by direct IP.

**How it works:**
- A hook DLL (`client-hooks.dll`) deployed as `hid.dll` inside ACC's game directory intercepts `sendto()`/`recvfrom()` from `ws2_32.dll` via DLL search order hijacking
- The hook communicates with a WinForms GUI via Windows named pipes
- Both must share ACC's Proton prefix (named pipes are isolated per Wine prefix)
- An alternative pure-Python TUI (`acc-connector-py/`) works natively on Linux without DLL injection

**Install complexity:**
- Source: GitHub releases, Inno Setup `.exe` installer
- Extraction: `innoextract`
- DLL deployment: `client-hooks.dll` → `<ACC_DIR>/AC2/Binaries/Win64/hid.dll`
- Desktop: `.desktop` file + `xdg-mime` for `acc-connect://` URI handler
- Runtime: `.NET 8` may be needed if build is not self-contained (`protontricks 805550 dotnetdesktop8`)

**Launch pattern:** Direct Proton invocation with `STEAM_COMPAT_DATA_PATH` pointing to ACC's `compatdata/805550/`

**Uninstall:** Remove `hid.dll`, restore `hid.dll.bak` if present

> `setup-linux.sh` in that repo is an early prototype of the install flow this tool would automate. It was written as a proof-of-concept and has not been tested.

### CrewChief V4 (ACC and others)

**Purpose:** AI race engineer — reads live telemetry and gives voice feedback on tyre wear, fuel, gaps, damage, penalties, pit strategy. Also accepts voice commands.

**Supported sims:** ACC, iRacing, rFactor2, LMU, Project Cars, RaceRoom, F1, AMS2, and more.

**How it works:**
- Reads Windows Memory-Mapped Files (MMF) that ACC writes in real time:
  - `Local\acpmf_physics` — vehicle telemetry
  - `Local\acpmf_graphics` — HUD/visual data
  - `Local\acpmf_static` — session/track data
- Optional UDP broadcasting client for remote ACC server telemetry
- Text-to-speech output + optional speech recognition for voice commands

**Install complexity:**
- Source: `.msi` installer
- Requires: `.NET 4.7.2` in the prefix (`protontricks 805550 dotnet472`)
- Optional: Microsoft Speech Platform runtime + language pack (MSI installers)
- After install: user must click "Download sound pack" and "Download driver names" in the UI

**Launch pattern:** Same Proton prefix as ACC (required for shared memory access)

**No existing Linux setup script** — this is the gap the tool fills.

---

## Ecosystem Survey — How Many Companion Apps Exist?

Sim racing is the densest ecosystem, but the pattern extends to other genres.

### Sim Racing (per-simulator apps)

| Category | Examples |
|---|---|
| Race engineer / spotter | CrewChief, Crew Chief for iRacing |
| Telemetry dashboards | SimHub, iDash, Sim Racing Studio, SIMRacingApps |
| Overlays | RaceLab, Delta, benofficial2 overlays, SDK Gaming |
| Server connectivity | acc-connector, BeamMP |
| Force feedback | iRFFB (iRacing), Oversteer (wheel manager, native Linux) |
| Setup sync | Delta (auto-installs setups), Trading Paints (liveries) |
| Analysis | MoTeC i2, Simetriq, Track Titan |
| Hardware config | Sim Racing Studio (motion, shakers, lighting) |

Major sims: ACC, iRacing, rFactor2, LMU, AMS2, BeamNG, AC (original), PCARS2, RaceRoom, F1 series.
Rough estimate: **30–50 companion apps** across major sim racing titles.

### Beyond Sim Racing

- **Flight sims:** MSFS has SimBridge, FSUIPC, Navigraph, Little Navmap
- **Multiplayer overlays:** voice chat apps, stream overlays
- **Game-specific tools:** anything using a published shared memory/SDK API

Sim racing is the right v1 scope — densest ecosystem, most active Linux community doing this today.

---

## Existing Tools and the Gap

| Tool | What it does | Relevance |
|---|---|---|
| **Lutris** | Game launcher + YAML install scripts | Has install script format to learn from; not focused on companion apps |
| **Bottles** | GUI Wine prefix manager | GUI-only, Flatpak-sandboxed; not suitable as dependency |
| **protontricks** | CLI winetricks wrapper for Proton prefixes | **Core dependency** |
| **protontricks-launch** | Launch an EXE in a game's Proton prefix | Useful for install phase; has Proton 6+ concurrency limitation for runtime |
| **ProtonPlus** | Manages Proton/Wine runner versions | Out of scope |
| **simshmbridge** | Maps Windows MMF into Linux `/dev/shm` | Interesting architecture pattern |
| **Datalink** | Bridges Proton shared memory to dbus | Similar; specific solution not a platform |
| **SimBridge** | Linux-native SimHub replacement | Best architecture example: tiny Windows relay binary + native Linux server |
| **protonfixes** | Per-game runtime fixes via `user_settings.py` | Different approach (hooks into Proton launch); inspiration for runtime hooks |

**The gap:** No tool manages the install/configure/launch lifecycle of companion apps for Proton games.

---

## Protontricks Reference

### What It Does

Protontricks reverse-engineers Steam's game config (parsing `appmanifest_*.acf` files and `libraryfolders.vdf`) to determine — for a given App ID — which Proton version is selected and where the `compatdata/` prefix is. It sets up the full Proton environment and runs whatever you give it.

You don't need to know where Steam is, which Proton version is active, or where the prefix lives. Protontricks resolves all of that.

### The Three Commands

```bash
# Install winetricks verbs into a game's prefix
protontricks <APPID> <verb> [verb ...]
protontricks 805550 dotnet472 vcrun2019

# Run an arbitrary shell command in the game's Wine/Proton environment
protontricks -c "<command>" <APPID>
protontricks -c "wine msiexec /i 'Z:\path\to\CrewChiefV4.msi'" 805550

# Launch a Windows EXE inside a game's prefix
protontricks-launch --appid <APPID> <path/to/exe>
protontricks-launch --appid 805550 ~/apps/crewchief/CrewChiefV4.exe
```

### Discovery Commands

```bash
protontricks -s "assetto"    # search by game name → returns App ID
protontricks -l              # list all Steam games with Proton prefixes
```

### Environment Variables

| Variable | Purpose |
|---|---|
| `$STEAM_DIR` | Override Steam install location |
| `$STEAM_COMPAT_DATA_PATH` | Override which `compatdata/` prefix to use |
| `$PROTON_VERSION` | Force a specific Proton version |
| `$WINETRICKS` | Point to a local winetricks installation |

### Winetricks Verb Reference

**.NET**

| Verb | Installs |
|---|---|
| `dotnet35` … `dotnet48` | .NET Framework 3.5 through 4.8 (classic) |
| `dotnet471`, `dotnet472` | .NET Framework 4.7.1 / 4.7.2 |
| `dotnet6` … `dotnet10` | .NET (Core) 6–10 runtimes |
| `dotnetdesktop6` … `dotnetdesktop10` | .NET Desktop Runtime (WinForms/WPF) |

**Visual C++ Runtimes**

`vcrun2003`, `vcrun2005`, `vcrun2008`, `vcrun2010`, `vcrun2012`, `vcrun2013`,
`vcrun2015`, `vcrun2017`, `vcrun2019`, `vcrun2022`

**DirectX / Graphics**

`d3dx9`, `d3dx10`, `d3dx11`, `dxvk` (versioned), `vkd3d`, `d2gl`

**Prefix Settings (no download)**

| Verb | Effect |
|---|---|
| `win7` / `win10` / `win11` | Windows version emulation |
| `sandbox` | Isolate prefix from real home |
| `vd=1920x1080` | Enable virtual desktop |
| `nocrashdialog` | Suppress Wine crash popups |
| `sound=pulse` / `sound=alsa` | Audio driver |

### Python API

```python
from protontricks.steam import find_steam_path, get_steam_apps, find_proton_app

steam_path = find_steam_path()                              # respects $STEAM_DIR
apps = get_steam_apps(steam_root, steam_path, lib_paths)   # returns SteamApp objects
proton_app = find_proton_app(steam_path, steam_apps, appid)
```

`SteamApp` objects expose: `.appid`, `.name`, `.prefix_path`, `.install_path`

These handle VDF parsing internally and cover native, Flatpak, and snap Steam layouts.

### Critical Limitation

**Since Proton 6, you cannot run two programs simultaneously in the same prefix through protontricks.** Proton serializes prefix access. This is why the tool generates a direct Proton launcher for runtime instead of using `protontricks-launch`.

---

## Technical Patterns from Reference Projects

### Steam Path Locations

Native and Flatpak Steam install paths to check:

```
~/.local/share/Steam
~/.steam/steam
~/.steam/root
~/.var/app/com.valvesoftware.Steam/data/Steam
~/.var/app/com.valvesoftware.Steam/.steam/steam
~/snap/steam/common/.steam/steam
```

Prefix for a game: `<STEAM_DIR>/steamapps/compatdata/<APPID>/pfx/`

Game install location: parse `<STEAM_DIR>/steamapps/libraryfolders.vdf`, check each library path for `steamapps/appmanifest_<APPID>.acf`.

> In practice, use `protontricks.steam` functions — they handle all of this already.

### Proton Binary Search Locations

```
<STEAM_DIR>/steamapps/common/Proton*/proton
<STEAM_DIR>/compatibilitytools.d/*/proton
~/.steam/root/compatibilitytools.d/*/proton
~/.local/share/Steam/compatibilitytools.d/*/proton   # Proton-GE
<Flatpak STEAM_DIR>/steamapps/common/Proton*/proton
<Flatpak STEAM_DIR>/compatibilitytools.d/*/proton
```

### DLL Deployment Pattern (from acc-connector)

1. Identify game binary directory from game install path
2. Back up any existing file at the target path
3. Copy hook DLL to target name
4. Store deployed path to disk so uninstall can reverse it

---

## Sources and References

- [protontricks GitHub](https://github.com/Matoking/protontricks)
- [winetricks verb list](https://github.com/Winetricks/winetricks/blob/master/files/verbs/all.txt)
- [protonfixes on PyPI](https://pypi.org/project/protonfixes/)
- [simshmbridge — shared memory bridge pattern](https://github.com/Spacefreak18/simshmbridge)
- [Datalink — Proton shared memory → /dev/shm](https://github.com/LukasLichten/Datalink)
- [SimBridge — Linux-native SimHub replacement](https://github.com/Carlos-Diaz-07/simbridge)
- [Lutris installer script format](https://github.com/lutris/lutris/blob/master/docs/installers.rst)
- [SimHub on Linux guide](https://www.simhubdash.com/community-2/simhub-support/guide-simhub-on-linux/)
- [How to run another .exe in a Proton prefix](https://gist.github.com/michaelbutler/f364276f4030c5f449252f2c4d960bd2)
- [A Proton Field Guide](https://www.brainvitamins.net/blog/proton-field-guide/)
