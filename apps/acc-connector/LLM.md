# LLM Integration Guide — Acc Connector

Use this file with Claude Code (or another LLM) to generate the manifest and install script for **Acc Connector**.

---

## Step 1 — Clone the app repository

```bash
git clone https://github.com/lonemeow/acc-connector /tmp/acc-connector-source
```

Read `/tmp/acc-connector-source` — look for installer files, READMEs, install scripts, and any existing Linux guides.

---

## Step 2 — Understand the tool

Answer these questions from the cloned repo and any linked documentation:

- What is the tool's name and description?
- Which Steam game(s) does it work with? (Steam App IDs at https://store.steampowered.com/app/\<ID\>)
- How is it distributed? (Inno Setup .exe, MSI, ZIP, standalone EXE, pre-extracted directory?)
- What Wine components does it need? (search for .NET, VC++ runtime requirements)
- What EXE is launched at runtime?
- Are there DLLs, config files, or registry entries that need to be deployed post-install?
- Does it need environment variables at launch?
- Are there manual steps the user must perform after install?

Read `../../Documentation/` for context:
- `Tech-spec.md` — architecture decisions and patterns
- `manifest.md` — full manifest schema reference with examples
- `Tech-notes.md` — ecosystem background and reference app patterns

---

## Step 3 — Present findings and get approval

Before writing any code, summarise your analysis:

| Field | Value |
|---|---|
| Tool Name | |
| Associated Game(s) | (name + Steam App ID) |
| Installer type | inno / msi / zip / raw_exe |
| Wine components required | |
| Launch EXE | |
| Custom install logic needed? | DLL deployment, config writing, etc. |
| Manual post-install steps | |

Ask: "Does this plan look correct? Shall I proceed?"

---

## Step 4 — Implement and test

After user confirmation:

1. Fill in `manifest.toml` — replace all TODO placeholders
2. Fill in `install.py` (or delete it and remove `[install].script` if no custom logic is needed)
3. Fill in `README.md`
4. Match style against other apps in `../../apps/`

Test:
```bash
sidecar doctor
sidecar install acc-connector
sidecar run acc-connector
```

---

## Step 5 — Submit a pull request

```bash
git checkout -b add-acc-connector
git add apps/acc-connector/
git commit -m "feat: add Acc Connector manifest"
git push origin add-acc-connector
```

Open a PR against the `main` branch of the proton-sidecar repository.
