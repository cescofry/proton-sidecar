# ACC Connector

**Associated game:** Assetto Corsa Competizione (Steam App ID: 805550)
**Tool homepage:** https://github.com/lonemeow/acc-connector
**Tool author:** Ilpo Ruotsalainen (lonemeow)
**Sidecar manifest author:** Francesco Frison
**Added:** 2026-04-29

## What It Does

ACC Connector bypasses Assetto Corsa Competizione's LAN-only server discovery so you can join any dedicated server by direct IP address. It works by deploying a hook DLL (`hid.dll`) into ACC's game directory that intercepts network calls and injects configured server entries into the LAN discovery list. A WinForms GUI lets you manage server entries and communicates with the hook via Windows named pipes — both must share ACC's Proton prefix.

## Installation Requirements

- ACC must have been launched at least once under Proton to initialise its prefix

## Launch Requirements

- Start ACC Connector **before** launching ACC from Steam; the named pipe connecting the GUI to the hook DLL is set up when ACC loads

## Troubleshooting

- **GUI doesn't open:** Run `protontricks 805550 dotnetdesktop8` to install the .NET 8 Desktop Runtime, then try again
- **No servers appear in the LAN lobby:** Confirm ACC Connector is running before starting ACC; both must share the same Proton prefix (Steam App ID 805550)
- Check `~/.local/share/sidecar/acc-connector/*/install.log` for install errors
