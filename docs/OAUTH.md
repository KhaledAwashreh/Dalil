# OAuth Integration Guide

Dalil supports OAuth2 authentication with Atlassian (Confluence/Jira). Tokens are encrypted and stored locally.

## Supported Providers

| Provider | Status | Use Case |
|----------|--------|----------|
| **Atlassian** | Active | Confluence ingestion via OAuth |
| **OpenAI** | Placeholder | Future SSO |
| **Anthropic** | Placeholder | Future SSO |

## Quick Start

1. Create an OAuth 2.0 (3LO) app at https://developer.atlassian.com/
2. Add granular scopes (see below)
3. Configure `config.json` with client credentials
4. Start the API server: `docker compose up -d`
5. Authenticate: visit `http://localhost:8000/auth/login/atlassian`
6. Tokens are stored and used automatically for Confluence API calls

## Atlassian OAuth Setup

### 1. Create an App

1. Go to https://developer.atlassian.com/console/myapps/
2. Create a new OAuth 2.0 (3LO) app
3. Under **Authorization > OAuth 2.0 (3LO)**, set callback URL to:
   ```
   http://localhost:8000/auth/callback/atlassian
   ```

### 2. Configure Permissions (Granular Scopes)

Under **Permissions > Confluence API**, add these granular scopes:

- `read:page:confluence` — Read pages
- `read:space:confluence` — List spaces
- `read:content-details:confluence` — Read page body content
- `read:label:confluence` — Read page labels

Also request `offline_access` for refresh tokens (handled automatically in the auth flow).

**Important:** Do not mix classic scopes (`read:confluence-content.all`) with granular scopes in the same app. The v2 API requires granular scopes only.

### 3. Get Credentials

After creating the app, copy:
- **Client ID**
- **Client Secret**

### 4. Update config.json

```json
{
  "oauth": {
    "storage_path": ".dalil_auth",
    "atlassian": {
      "client_id": "your-client-id",
      "client_secret": "your-client-secret",
      "redirect_uri": "http://localhost:8000/auth/callback/atlassian"
    }
  }
}
```

### 5. Distribution (Optional)

For personal/development use, the app works in development mode (only the owner can authorize).

To allow other users in your org:
1. Go to **Distribution** in the Developer Console
2. Fill in required fields (app name, privacy policy URL)
3. Enable distribution

## Authentication

### Via Browser (API Server)

With the API server running (`docker compose up -d`):

1. Visit `http://localhost:8000/auth/login/atlassian`
2. Authorize the app on Atlassian's page
3. Token is exchanged and stored automatically

Use incognito mode to pick a different Atlassian account.

### Via CLI

```bash
dalil auth login atlassian     # Opens browser, catches callback
dalil auth status              # Check all providers
dalil auth status atlassian    # Check specific provider
dalil auth logout              # Logout all providers
dalil auth logout atlassian    # Logout specific provider
```

The CLI starts a temporary local server to catch the OAuth callback, so the API server does not need to be running.

### Check Status via API

```bash
curl http://localhost:8000/auth/status?provider=atlassian
```

### Logout via API

```bash
curl -X POST http://localhost:8000/auth/logout?provider=atlassian
```

## How It Works

Dalil uses the Atlassian cloud proxy for all OAuth API calls:

```
https://api.atlassian.com/ex/confluence/{cloud_id}/wiki/api/v2/...
```

The cloud ID is fetched dynamically from the `accessible-resources` API using the OAuth token. This means:
- The `confluence_base_url` in config is only used for display links and API token auth fallback
- OAuth tokens always go through the cloud proxy regardless of config

The Confluence v2 API is used for OAuth, while v1 (`/rest/api/content/...`) is used as fallback for API token auth.

## Token Storage

Tokens are encrypted using Fernet (symmetric encryption):
- Stored in `.dalil_auth/` directory (configurable via `oauth.storage_path`)
- Encryption key at `.dalil_auth/.key`
- Access tokens, refresh tokens, and user info are all encrypted
- Shared between the CLI and Docker container via bind mount

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/login/{provider}` | GET | Initiate OAuth login (redirects to provider) |
| `/auth/callback/{provider}` | GET | OAuth callback handler |
| `/auth/status` | GET | Check authentication status |
| `/auth/tokens/{provider}` | GET | Get stored access token |
| `/auth/logout` | POST | Logout and clear tokens |

## Troubleshooting

### "Unsupported provider" error
Provider not configured in `config.json`. Add `oauth.<provider>.client_id` and `client_secret`.

### "scope does not match" / 401 on API calls
You're mixing classic and granular scopes. Use only granular scopes listed above.

### "This application is in development"
Only the app owner can authorize in dev mode. Enable distribution for other users.

### Browser defaults to wrong Atlassian account
Use incognito mode. The auth flow includes `prompt=login consent` to force account selection, but cached sessions may override this.

### Token expired
Re-authenticate via `http://localhost:8000/auth/login/atlassian` or `dalil auth login atlassian`. Refresh tokens are supported with `offline_access` scope.
