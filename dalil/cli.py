"""Dalil CLI - friendly wrapper around MuninnDB management."""

import asyncio
import json
import re
import subprocess
import sys
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import click

CONTAINER_NAME = "dalil-muninndb"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
VAULTS_FILE = PROJECT_ROOT / ".dalil" / "vaults.json"

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
        try:
            return json.loads(VAULTS_FILE.read_text())
        except (json.JSONDecodeError, OSError) as e:
            click.echo(f"Warning: could not read {VAULTS_FILE}: {e}", err=True)
            return {}
    return {}


def _save_vaults(vaults: dict) -> None:
    """Save vault registry to .dalil/vaults.json."""
    try:
        VAULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        VAULTS_FILE.write_text(json.dumps(vaults, indent=2) + "\n")
    except OSError as e:
        click.echo(f"Warning: could not save {VAULTS_FILE}: {e}", err=True)


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
    try:
        from dalil.api.main import main
        main()
    except ImportError as e:
        click.echo(f"Error: could not load API server — missing dependency: {e}", err=True)
        sys.exit(1)
    except OSError as e:
        click.echo(f"Error: could not start server: {e}", err=True)
        sys.exit(1)
    except KeyboardInterrupt:
        click.echo("\nServer stopped.")


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
    token = vaults[name].get("token")
    if not token:
        click.echo(f"Error: vault '{name}' entry exists but has no token.", err=True)
        sys.exit(1)
    click.echo(token)


def _load_oauth_settings():
    """Load OAuth settings and return (settings, storage, providers) tuple."""
    try:
        from dalil.config.settings import load_settings
        from dalil.auth.storage import TokenStorage
        from dalil.auth.models import ProviderType
    except ImportError as e:
        click.echo(f"Error: missing dependency for auth: {e}", err=True)
        sys.exit(1)

    try:
        config_path = str(PROJECT_ROOT / "config.json")
        settings = load_settings(config_path)
    except (json.JSONDecodeError, OSError) as e:
        click.echo(f"Error: could not load config.json: {e}", err=True)
        sys.exit(1)

    try:
        storage_path = settings.oauth.storage_path
        if not Path(storage_path).is_absolute():
            storage_path = str(PROJECT_ROOT / storage_path)
        storage = TokenStorage(storage_path=storage_path)
    except Exception as e:
        click.echo(f"Error: could not initialize token storage: {e}", err=True)
        sys.exit(1)

    providers = {}
    if settings.oauth.atlassian.client_id:
        from dalil.auth.providers.atlassian import AtlassianOAuthProvider
        providers[ProviderType.ATLASSIAN] = AtlassianOAuthProvider(
            client_id=settings.oauth.atlassian.client_id,
            client_secret=settings.oauth.atlassian.client_secret,
            redirect_uri=settings.oauth.atlassian.redirect_uri,
        )
    if settings.oauth.openai.client_id:
        from dalil.auth.providers.openai import OpenAIOAuthProvider
        providers[ProviderType.OPENAI] = OpenAIOAuthProvider(
            client_id=settings.oauth.openai.client_id,
            client_secret=settings.oauth.openai.client_secret,
            redirect_uri=settings.oauth.openai.redirect_uri,
        )
    if settings.oauth.anthropic.client_id:
        from dalil.auth.providers.anthropic import AnthropicOAuthProvider
        providers[ProviderType.ANTHROPIC] = AnthropicOAuthProvider(
            client_id=settings.oauth.anthropic.client_id,
            client_secret=settings.oauth.anthropic.client_secret,
            redirect_uri=settings.oauth.anthropic.redirect_uri,
        )
    return settings, storage, providers


@click.group("auth")
def auth():
    """Authenticate with OAuth providers."""


@auth.command("login")
@click.argument("provider", type=click.Choice(["atlassian", "openai", "anthropic"]))
def auth_login(provider):
    """Login with an OAuth provider. Opens browser for authorization."""
    import time
    from dalil.auth.models import ProviderType

    provider_type = ProviderType(provider)
    settings, storage, providers = _load_oauth_settings()

    if provider_type not in providers:
        click.echo(f"Error: provider '{provider}' is not configured in config.json.", err=True)
        click.echo(f"Add oauth.{provider}.client_id and client_secret to your config.", err=True)
        sys.exit(1)

    handler = providers[provider_type]
    state = handler.generate_state()
    auth_url = handler.get_authorization_url(state)

    parsed = urlparse(handler.redirect_uri)
    callback_port = parsed.port or 8000
    callback_path = parsed.path

    auth_code = None
    returned_state = None
    error_msg = None

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            nonlocal auth_code, returned_state, error_msg

            try:
                parsed_path = urlparse(self.path)
                if not parsed_path.path.startswith(callback_path):
                    self.send_response(404)
                    self.end_headers()
                    return

                params = parse_qs(parsed_path.query)

                if "error" in params:
                    error_msg = params["error"][0]
                    self._respond("Authorization failed. You can close this tab.")
                    return

                auth_code = params.get("code", [None])[0]
                returned_state = params.get("state", [None])[0]
                self._respond("Authorization successful! You can close this tab.")
            except Exception:
                error_msg = "malformed callback request"
                try:
                    self.send_response(400)
                    self.end_headers()
                except Exception:
                    pass

        def _respond(self, message):
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            html = f"<html><body><h2>{message}</h2></body></html>"
            self.wfile.write(html.encode())

        def log_message(self, format, *args):
            pass

    try:
        server = HTTPServer(("127.0.0.1", callback_port), CallbackHandler)
    except OSError as e:
        click.echo(f"Error: could not start callback server on port {callback_port}: {e}", err=True)
        if "address already in use" in str(e).lower() or "10048" in str(e):
            click.echo("Another process is using that port. Stop it or change the redirect_uri port in config.json.")
        sys.exit(1)

    server.timeout = 5
    timeout_seconds = 120

    click.echo(f"Opening browser for {provider} authorization...")
    if not webbrowser.open(auth_url):
        click.echo(f"Could not open browser. Visit this URL manually:\n  {auth_url}")

    click.echo("Waiting for authorization callback (timeout: 2 minutes)...")

    deadline = time.monotonic() + timeout_seconds
    try:
        while auth_code is None and error_msg is None:
            if time.monotonic() > deadline:
                error_msg = "timed out waiting for callback"
                break
            server.handle_request()
    except KeyboardInterrupt:
        click.echo("\nLogin cancelled.")
        server.server_close()
        sys.exit(1)

    server.server_close()

    if error_msg:
        click.echo(f"Authorization failed: {error_msg}", err=True)
        sys.exit(1)

    if not auth_code:
        click.echo("Error: no authorization code received.", err=True)
        sys.exit(1)

    if returned_state != state:
        click.echo("Error: state mismatch — possible CSRF attack.", err=True)
        sys.exit(1)

    click.echo("Exchanging code for token...")
    try:
        token = asyncio.run(handler.exchange_code_for_token(auth_code))
    except Exception as e:
        click.echo(f"Error: token exchange failed: {e}", err=True)
        sys.exit(1)

    try:
        user = asyncio.run(handler.get_user_info(token))
    except Exception as e:
        click.echo(f"Warning: could not fetch user info: {e}", err=True)
        click.echo("Token was obtained but user details are unavailable.")
        from dalil.auth.models import User
        user = User(id="unknown", email="", name="unknown", provider=provider_type)

    try:
        storage.save_token(token)
        storage.save_user(user)
    except Exception as e:
        click.echo(f"Error: could not save token to storage: {e}", err=True)
        sys.exit(1)

    click.echo(f"Authenticated as {user.name} ({user.email})")
    click.echo(f"Token stored in {settings.oauth.storage_path}/")


@auth.command("status")
@click.argument("provider", required=False, type=click.Choice(["atlassian", "openai", "anthropic"]))
def auth_status(provider):
    """Check authentication status for providers."""
    from dalil.auth.models import ProviderType

    _, storage, _ = _load_oauth_settings()

    if provider:
        provider_type = ProviderType(provider)
        try:
            token = storage.get_token(provider_type)
        except Exception as e:
            click.echo(f"{provider}: error reading token ({e})", err=True)
            sys.exit(1)
        if token:
            click.echo(f"{provider}: authenticated")
            if token.expires_at:
                click.echo(f"  expires: {token.expires_at.isoformat()}")
        else:
            click.echo(f"{provider}: not authenticated")
        return

    for p in ProviderType:
        try:
            token = storage.get_token(p)
            status = "authenticated" if token else "not authenticated"
        except Exception:
            status = "error reading token"
        click.echo(f"{p.value}: {status}")


@auth.command("logout")
@click.argument("provider", required=False, type=click.Choice(["atlassian", "openai", "anthropic"]))
def auth_logout(provider):
    """Logout and clear stored tokens."""
    from dalil.auth.models import ProviderType

    _, storage, _ = _load_oauth_settings()

    try:
        if provider:
            storage.delete_token(ProviderType(provider))
            click.echo(f"Logged out from {provider}.")
        else:
            for p in ProviderType:
                storage.delete_token(p)
            click.echo("Logged out from all providers.")
    except Exception as e:
        click.echo(f"Error: could not clear tokens: {e}", err=True)
        sys.exit(1)


cli.add_command(auth)


if __name__ == "__main__":
    cli()
