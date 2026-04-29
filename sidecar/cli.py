import re
import shutil
import subprocess
import sys
from datetime import date
from importlib.resources import files
from pathlib import Path

import click
from jinja2 import Environment, FileSystemLoader

from sidecar import __version__, registry, steam
from sidecar import install as install_mod
from sidecar import launch as launch_mod
from sidecar.manifest import Manifest
from sidecar.state import is_installed, read_state


@click.group(invoke_without_command=True, context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, "-V", "--version")
@click.pass_context
def main(ctx: click.Context) -> None:
    """proton-sidecar — manage Windows companion apps for Proton games on Linux."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        click.echo()
        _print_app_list(installed=False)


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------

@main.command("list")
@click.option("--installed", is_flag=True, help="Show only installed apps")
def cmd_list(installed: bool) -> None:
    """List available apps."""
    _print_app_list(installed=installed)


def _print_app_list(installed: bool) -> None:
    apps = registry.load_index()
    if not apps:
        click.echo("No apps found in registry.")
        return

    if installed:
        sidecar_dir = Path.home() / ".local" / "share" / "sidecar"
        apps = [
            a for a in apps
            if any(
                is_installed(sidecar_dir / a["id"] / d.name)
                for d in (sidecar_dir / a["id"]).iterdir()
                if (sidecar_dir / a["id"]).is_dir() and d.is_dir()
            )
        ]
        if not apps:
            click.echo("No apps installed yet. Run 'sidecar install <app-id>' to install one.")
            return

    click.echo(f"{'ID':<25} {'Name':<30} Description")
    click.echo("-" * 80)
    for app in apps:
        click.echo(f"{app['id']:<25} {app['name']:<30} {app.get('description', '')}")


# ---------------------------------------------------------------------------
# install
# ---------------------------------------------------------------------------

@main.command("install")
@click.argument("app_id")
@click.option("--game", "game_appid", type=int, default=None,
              help="Steam AppID of the target game (skips interactive prompt)")
def cmd_install(app_id: str, game_appid: int | None) -> None:
    """Install a companion app."""
    manifest_path = _resolve_manifest(app_id)
    manifest = Manifest.from_toml(manifest_path)
    game_appid = game_appid or _pick_game(manifest)
    install_mod.install_app(manifest, game_appid)


# ---------------------------------------------------------------------------
# remove / delete
# ---------------------------------------------------------------------------

@main.command("remove")
@click.argument("app_id")
@click.option("--game", "game_appid", type=int, default=None,
              help="Remove only the install for this game AppID")
def cmd_remove(app_id: str, game_appid: int | None) -> None:
    """Remove an installed app."""
    sidecar_dir = Path.home() / ".local" / "share" / "sidecar"
    app_base = sidecar_dir / app_id

    if not app_base.is_dir():
        raise click.ClickException(f"'{app_id}' is not installed.")

    installs = [d for d in app_base.iterdir() if d.is_dir()]
    if not installs:
        raise click.ClickException(f"'{app_id}' is not installed.")

    if game_appid:
        targets = [app_base / str(game_appid)]
    elif len(installs) == 1:
        targets = installs
    else:
        choices = {str(d.name): d for d in installs}
        click.echo("Installed game IDs:")
        for i, name in enumerate(choices, 1):
            click.echo(f"  [{i}] AppID {name}")
        idx = click.prompt("Which install to remove?", type=click.IntRange(1, len(choices)))
        targets = [list(choices.values())[idx - 1]]

    manifest_path = _resolve_manifest(app_id)
    manifest = Manifest.from_toml(manifest_path)

    for target in targets:
        if not target.is_dir():
            raise click.ClickException(f"Install directory not found: {target}")
        _run_uninstall_hook(manifest, target)
        shutil.rmtree(target)
        click.echo(f"Removed {app_id} (game {target.name}).")

    if not any(app_base.iterdir()):
        app_base.rmdir()


def _run_uninstall_hook(manifest: Manifest, install_dir: Path) -> None:
    if not manifest.install.script:
        return
    from sidecar import hook as hook_mod
    from sidecar.context import InstallContext

    hook_path = registry.find_hook_script(manifest.app.id, manifest.install.script)
    if not hook_path.is_file():
        return

    try:
        steam_dir = steam.find_steam()
        appid = int(install_dir.name)
        ctx = InstallContext(
            steam_dir=steam_dir,
            game_appid=appid,
            game_dir=Path("/"),
            prefix_dir=steam.find_prefix(steam_dir, appid),
            install_dir=install_dir,
            app_dir=install_dir / "app",
            proton_bin=Path("/"),
        )
        hook = hook_mod.load_hook(hook_path, manifest)
        hook.uninstall(ctx)
    except Exception as exc:
        click.echo(f"Warning: uninstall hook raised an error: {exc}", err=True)


# ---------------------------------------------------------------------------
# run / launch
# ---------------------------------------------------------------------------

@main.command("run")
@click.argument("app_id")
@click.option("--game", "game_appid", type=int, default=None)
@click.argument("extra_args", nargs=-1, type=click.UNPROCESSED)
def cmd_run(app_id: str, game_appid: int | None, extra_args: tuple[str, ...]) -> None:
    """Launch an installed app."""
    manifest_path = _resolve_manifest(app_id)
    manifest = Manifest.from_toml(manifest_path)

    sidecar_dir = Path.home() / ".local" / "share" / "sidecar"
    app_base = sidecar_dir / app_id

    installs = _find_installs(app_base)
    if not installs:
        raise click.ClickException(
            f"'{app_id}' is not installed. Run 'sidecar install {app_id}' first."
        )

    if game_appid:
        install_dir = app_base / str(game_appid)
    elif len(installs) == 1:
        install_dir = installs[0]
    else:
        install_dir = _pick_install(installs)

    appid = int(install_dir.name)
    try:
        steam_dir = steam.find_steam()
        ctx_obj = __import__("sidecar.context", fromlist=["InstallContext"]).InstallContext(
            steam_dir=steam_dir,
            game_appid=appid,
            game_dir=Path("/"),
            prefix_dir=steam.find_prefix(steam_dir, appid),
            install_dir=install_dir,
            app_dir=install_dir / "app",
            proton_bin=steam.find_proton(steam_dir, appid),
        )
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc

    launch_mod.run_app(manifest, ctx_obj, list(extra_args))


def _find_installs(app_base: Path) -> list[Path]:
    if not app_base.is_dir():
        return []
    return [
        d for d in app_base.iterdir()
        if d.is_dir() and is_installed(d)
    ]


def _pick_install(installs: list[Path]) -> Path:
    click.echo("Multiple game installs found:")
    for i, d in enumerate(installs, 1):
        click.echo(f"  [{i}] AppID {d.name}")
    idx = click.prompt("Which install to run?", type=click.IntRange(1, len(installs)))
    return installs[idx - 1]


# ---------------------------------------------------------------------------
# doctor
# ---------------------------------------------------------------------------

@main.command("doctor")
def cmd_doctor() -> None:
    """Check system dependencies."""
    click.echo("proton-sidecar doctor\n")

    _check_python()
    _check_steam()
    _check_tool("protontricks", required=True, install="pipx install protontricks")
    _check_tool("innoextract", required=False, install="sudo apt install innoextract")
    _check_tool("msiextract", required=False, install="sudo apt install msitools")


def _check_python() -> None:
    v = sys.version_info
    ver = f"{v.major}.{v.minor}.{v.micro}"
    ok = v >= (3, 11)
    _status("Python", ver, ok, required=True)


def _check_steam() -> None:
    try:
        path = steam.find_steam()
        _status("Steam", str(path), ok=True, required=True)
    except steam.SteamNotFoundError:
        _status("Steam", "not found", ok=False, required=True)


def _check_tool(name: str, required: bool, install: str) -> None:
    path = shutil.which(name)
    if path:
        try:
            result = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=5)
            version = result.stdout.strip().split("\n")[0] or result.stderr.strip().split("\n")[0]
        except Exception:
            version = path
        _status(name, version, ok=True, required=required)
    else:
        hint = f"Install with: {install}"
        _status(name, f"not found ({hint})", ok=False, required=required)


def _status(label: str, value: str, ok: bool, required: bool) -> None:
    tag = "[OK]  " if ok else ("[WARN]" if not required else "[FAIL]")
    click.echo(f"  {tag} {label:<15} {value}")


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------

@main.command("init")
@click.argument("repo_url")
@click.option("--name", default=None, help="App folder name (default: inferred from repo URL)")
def cmd_init(repo_url: str, name: str | None) -> None:
    """Scaffold a new app manifest from a repository URL."""
    repo_url = repo_url.rstrip("/").removesuffix(".git")

    if name is None:
        inferred = _slugify(repo_url.rstrip("/").split("/")[-1])
        name = click.prompt("App folder name", default=inferred)

    app_name = _slugify(name)
    apps_dir = registry.get_registry_dir()
    app_dir = apps_dir / app_name

    if app_dir.exists():
        raise click.ClickException(
            f"'{app_dir}' already exists. Choose a different name or delete the existing folder."
        )

    app_dir.mkdir(parents=True)

    templates_dir = Path(__file__).parent / "templates"
    env = Environment(loader=FileSystemLoader(str(templates_dir)), keep_trailing_newline=True)

    context = {
        "repo_url": repo_url,
        "app_name": app_name,
        "app_name_title": app_name.replace("-", " ").title(),
        "today": date.today().isoformat(),
    }

    files_to_render = [
        ("manifest.toml.j2", "manifest.toml"),
        ("install.py.j2", "install.py"),
        ("README.md.j2", "README.md"),
        ("LLM.md.j2", "LLM.md"),
    ]

    for template_name, output_name in files_to_render:
        tmpl = env.get_template(template_name)
        (app_dir / output_name).write_text(tmpl.render(**context))

    click.echo(f"Created {app_dir}/")
    for _, out in files_to_render:
        click.echo(f"  {out}")
    click.echo(
        f"\nNext steps:\n"
        f"  1. Fill in apps/{app_name}/manifest.toml (replace all TODO placeholders)\n"
        f"  2. Or use LLM.md with Claude Code to fill it in automatically\n"
        f"  3. Test with: sidecar install {app_name}"
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower())
    return re.sub(r"-+", "-", slug).strip("-")


# Command aliases
main.add_command(cmd_remove, "delete")
main.add_command(cmd_run, "launch")


def _resolve_manifest(app_id: str) -> Path:
    try:
        return registry.find_manifest(app_id)
    except LookupError as exc:
        raise click.ClickException(str(exc)) from exc


def _pick_game(manifest: Manifest) -> int:
    try:
        games = steam.find_installed_games(manifest.requires.games)
    except Exception:
        games = []

    if not games:
        raise click.ClickException(
            f"None of the required games are installed: "
            f"{manifest.requires.games}. Install at least one via Steam."
        )
    if len(games) == 1:
        appid, gname, _ = games[0]
        click.echo(f"Using {gname} ({appid})")
        return appid

    click.echo(f"Found {len(games)} compatible installed games:")
    for i, (appid, gname, _) in enumerate(games, 1):
        click.echo(f"  [{i}] {gname} ({appid})")
    idx = click.prompt("Which game?", type=click.IntRange(1, len(games)), default=1)
    return games[idx - 1][0]
