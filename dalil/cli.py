"""Dalil CLI - friendly wrapper around MuninnDB management."""

import json
import re
import subprocess
import sys
from pathlib import Path

import click

CONTAINER_NAME = "dalil-muninndb"
VAULTS_FILE = Path(".dalil") / "vaults.json"

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]|\x1b\].*?\x07|\x1b[^[\]].?")


def _clean(text: str) -> str:
    """Strip ANSI escape sequences and terminal control characters."""
    return _ANSI_RE.sub("", text).strip()


def _docker_exec(*args: str) -> tuple[int, str]:
    """Run a command inside the MuninnDB container. Returns (returncode, output)."""
    cmd = ["docker", "exec", CONTAINER_NAME, "muninndb-server", *args]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        click.echo("Error: docker not found. Is Docker Desktop running?", err=True)
        sys.exit(1)
    output = _clean(result.stdout) or _clean(result.stderr)
    return result.returncode, output


def _container_running() -> bool:
    """Check if the MuninnDB container is running."""
    try:
        result = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.Status}}", CONTAINER_NAME],
            capture_output=True,
            text=True,
        )
        return result.stdout.strip() == "running"
    except FileNotFoundError:
        return False


def _load_vaults() -> dict:
    """Load vault registry from .dalil/vaults.json."""
    if VAULTS_FILE.exists():
        return json.loads(VAULTS_FILE.read_text())
    return {}


def _save_vaults(vaults: dict) -> None:
    """Save vault registry to .dalil/vaults.json."""
    VAULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    VAULTS_FILE.write_text(json.dumps(vaults, indent=2) + "\n")


def _parse_token(output: str) -> str | None:
    """Extract the mk_... token from api-key create output."""
    match = re.search(r"(mk_\S+)", output)
    return match.group(1) if match else None


@click.group()
def cli():
    """Dalil - consulting memory system."""


@cli.command()
def status():
    """Check if MuninnDB is running and responsive."""
    if not _container_running():
        click.echo(f"MuninnDB container ({CONTAINER_NAME}) is not running.")
        click.echo("Start it with: docker compose up -d")
        sys.exit(1)
    rc, output = _docker_exec("show", "vaults")
    if rc == 0:
        click.echo("MuninnDB is running and responsive.")
        click.echo(output)
    else:
        click.echo("MuninnDB container is running but not responding.")
        click.echo(output)
        sys.exit(1)


@cli.command()
def serve():
    """Start the Dalil API server."""
    from dalil.api.main import main

    main()


# -- Vault subcommands --------------------------------------------------------


@cli.group()
def vault():
    """Manage MuninnDB vaults."""


@vault.command("list")
@click.option("--pattern", default=None, help="Glob pattern to filter vaults.")
@click.option("--keys", is_flag=True, help="Show stored API keys.")
def vault_list(pattern, keys):
    """List all vaults."""
    args = ["vault", "list"]
    if pattern:
        args += ["--pattern", pattern]
    rc, output = _docker_exec(*args)
    # The raw output indents non-first vaults; normalize to one per line
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    for line in lines:
        click.echo(line)

    if keys:
        vaults = _load_vaults()
        if vaults:
            click.echo("\nStored API keys:")
            for name, info in vaults.items():
                token = info["token"]
                masked = token[:6] + "..." + token[-4:]
                click.echo(f"  {name}: {masked}")
    sys.exit(rc)


@vault.command("create")
@click.argument("name")
@click.option("--public", is_flag=True, help="Create a public vault (no auth required).")
def vault_create(name, public):
    """Create a new vault and generate an API key for it."""
    args = ["vault", "create", name]
    if public:
        args.append("--public")
    rc, output = _docker_exec(*args)
    click.echo(output)
    if rc != 0:
        sys.exit(rc)

    if public:
        sys.exit(0)

    # Auto-generate an API key
    rc_key, key_output = _docker_exec(
        "api-key", "create", "--vault", name, "--label", "dalil-auto",
    )
    if rc_key != 0:
        click.echo(f"Warning: vault created but API key generation failed:\n{key_output}", err=True)
        sys.exit(1)

    token = _parse_token(key_output)
    if not token:
        click.echo(f"Warning: vault created but could not parse API key from output:\n{key_output}", err=True)
        sys.exit(1)

    # Store the key
    vaults = _load_vaults()
    vaults[name] = {"token": token}
    _save_vaults(vaults)

    click.echo(f"\nAPI key generated and saved to {VAULTS_FILE}")
    click.echo(f"Token: {token}")


@vault.command("delete")
@click.argument("name")
@click.option("--yes", is_flag=True, help="Skip confirmation prompt.")
@click.option("--force", is_flag=True, help="Force delete even if vault has memories.")
def vault_delete(name, yes, force):
    """Delete a vault and all its memories."""
    if not yes:
        click.confirm(f"Delete vault '{name}' and all its memories?", abort=True)
    args = ["vault", "delete", name, "--yes"]
    if force:
        args.append("--force")
    rc, output = _docker_exec(*args)
    click.echo(output)

    if rc == 0:
        vaults = _load_vaults()
        if vaults.pop(name, None):
            _save_vaults(vaults)
            click.echo(f"Removed stored API key for '{name}'.")
    sys.exit(rc)


@vault.command("clear")
@click.argument("name")
@click.option("--yes", is_flag=True, help="Skip confirmation prompt.")
def vault_clear(name, yes):
    """Remove all memories from a vault (keeps the vault)."""
    if not yes:
        click.confirm(f"Clear all memories from vault '{name}'?", abort=True)
    args = ["vault", "clear", name, "--yes"]
    rc, output = _docker_exec(*args)
    click.echo(output)
    sys.exit(rc)


@vault.command("clone")
@click.argument("source")
@click.argument("new_name")
def vault_clone(source, new_name):
    """Clone a vault into a new one."""
    rc, output = _docker_exec("vault", "clone", source, new_name)
    click.echo(output)
    sys.exit(rc)


@vault.command("key")
@click.argument("name")
def vault_key(name):
    """Show the stored API key for a vault."""
    vaults = _load_vaults()
    if name not in vaults:
        click.echo(f"No stored key for vault '{name}'.")
        click.echo("Keys are auto-generated when you run: dalil vault create <name>")
        sys.exit(1)
    click.echo(vaults[name]["token"])


if __name__ == "__main__":
    cli()
