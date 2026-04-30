# OAuth Integration Guide

Dalil supports OAuth2/OpenID Connect authentication with Atlassian, OpenAI, and Anthropic.

## Supported Providers

| Provider | Status | Use Case |
|----------|--------|----------|
| **Atlassian** | ✅ Complete | Confluence ingestion with user's account |
| **OpenAI** | ✅ Complete | Future SSO for ChatGPT/API access |
| **Anthropic** | ✅ Complete | Future SSO for Claude API access |

## Quick Start

1. Create OAuth apps with your providers
2. Configure `config.json` with client credentials
3. Run `dalil oauth login <provider>`
4. Complete authorization in browser
5. Tokens are automatically stored and used for API calls

## Atlassian OAuth Setup

### 1. Create a Confluence App

1. Go to https://developer.atlassian.com/
2. Create a new OAuth 2.0 (3LO) app
3. Configure the app:
   - **Name**: Dalil
   - **Description**: Consulting memory system
   - **Callback URL**: `http://localhost:8000/auth/callback/atlassian`

### 2. Configure Permissions

Add these scopes to your app:
- `read:confluence-content.all` - Read Confluence pages
- `read:confluence-space.summary` - List spaces
- `offline_access` - Refresh tokens

### 3. Get Credentials

After creating the app, you'll get:
- **Client ID** - Public identifier
- **Client Secret** - Keep this private!

### 4. Update config.json

```json
{
  "oauth": {
    "atlassian": {
      "client_id": "your-client-id",
      "client_secret": "your-client-secret",
      "redirect_uri": "http://localhost:8000/auth/callback/atlassian"
    },
    "storage_path": ".dalil_auth"
  }
}
```

## Using OAuth

### Login Flow

1. **Initiate login**:
   ```bash
   curl http://localhost:8000/auth/login/atlassian
   ```
   This redirects to Atlassian's authorization page.

2. **Callback**: After authorization, Atlassian redirects back to your callback URL with a code.

3. **Token exchange**: The callback handler exchanges the code for an access token automatically.

### Check Auth Status

```bash
curl http://localhost:8000/auth/status?provider=atlassian
```

Response:
```json
{
  "authenticated": true,
  "provider": "atlassian",
  "user": {
    "id": "account-id",
    "email": "user@company.com",
    "name": "John Doe",
    "provider": "atlassian"
  }
}
```

### Get Access Token

```bash
curl http://localhost:8000/auth/tokens/atlassian
```

Use this token for API calls to Confluence.

### Logout

```bash
curl -X POST http://localhost:8000/auth/logout?provider=atlassian
```

## Token Storage

Tokens are encrypted using Fernet (symmetric encryption) before storage:
- Stored in `.dalil_auth/` directory (configurable via `oauth.storage_path`)
- Encryption key is stored in `.dalil_auth/.key`
- Access tokens, refresh tokens, and user info are all encrypted

**Security note**: Keep the `.dalil_auth/` directory secure. If the encryption key is compromised, tokens can be decrypted.

## Token Refresh

When access tokens expire, the system can automatically refresh them using the refresh token (if available).

The refresh logic is handled in:
- `dalil/auth/providers/atlassian.py` - `refresh_token()` method
- Called automatically when making API calls with expired tokens

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/login/{provider}` | GET | Initiate OAuth login |
| `/auth/callback/{provider}` | GET | OAuth callback handler |
| `/auth/status` | GET | Check authentication status |
| `/auth/tokens/{provider}` | GET | Get stored access token |
| `/auth/logout` | POST | Logout and clear tokens |

## Environment Variables

OAuth settings can also be set via config file (`config.json`) - see `docs/CONFIGURATION.md`.

## Troubleshooting

### "Unsupported provider" error
Make sure the provider is configured in `config.json` under `oauth.<provider>`.

### "Invalid state parameter" error
This is a CSRF protection. Make sure cookies are enabled and you're not modifying the callback URL.

### Token expired
Use the refresh token endpoint or re-authenticate by logging in again.
