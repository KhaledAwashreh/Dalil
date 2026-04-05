# Configuration

## config.json

Dalil reads `config.json` at startup. See [config.example.json](../dalil/config/config.example.json) for a complete template.

### Full Schema

```json
{
  "muninn": {
    "base_url": "http://localhost:8475",
    "mcp_url": "http://localhost:8750/mcp",
    "token": "",
    "default_vault": "default",
    "timeout": 10.0
  },
  "llm": {
    "type": "api",
    "provider": "ollama",
    "model": "mistral",
    "api_key": "",
    "base_url": "http://localhost:11434/v1",
    "temperature": 0.3,
    "max_tokens": 2048
  },
  "ingestion": {
    "chunk_size": 1000,
    "chunk_overlap": 200,
    "confluence_base_url": "",
    "confluence_token": "",
    "confluence_email": ""
  },
  "embeddings": {
    "enabled": false,
    "model_name": "all-MiniLM-L6-v2"
  },
  "log_level": "INFO",
  "api_host": "0.0.0.0",
  "api_port": 8000
}
```

### Configuration Options

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `muninn.base_url` | string | `http://localhost:8475` | MuninnDB REST endpoint. Docker: `http://muninndb:8475`. |
| `muninn.mcp_url` | string | `http://localhost:8750/mcp` | MuninnDB MCP endpoint. Docker: `http://muninndb:8750/mcp`. |
| `muninn.token` | string | `""` | Vault API key (`mk_...` format). Leave empty for local dev with default vault. |
| `muninn.default_vault` | string | `"default"` | Default vault name for requests that don't specify one. |
| `muninn.timeout` | float | `10.0` | Request timeout in seconds. |
| `llm.type` | string | `"api"` | `"api"` for remote/Ollama, `"local"` for HuggingFace transformers. |
| `llm.provider` | string | `"ollama"` | Provider hint: `"ollama"`, `"openai"`, `"anthropic"`, `"deepseek"`, or any string. |
| `llm.model` | string | `"mistral"` | Model identifier. |
| `llm.api_key` | string | `""` | API key (not needed for Ollama). |
| `llm.base_url` | string | `""` | API base URL. Auto-detected from provider if empty. |
| `llm.temperature` | float | `0.3` | Sampling temperature (0.0–1.0). Lower = more deterministic. |
| `llm.max_tokens` | int | `2048` | Max output tokens. |
| `ingestion.chunk_size` | int | `1000` | Max characters per chunk for PDF/Confluence. |
| `ingestion.chunk_overlap` | int | `200` | Overlap between chunks. |
| `ingestion.confluence_base_url` | string | `""` | Confluence instance URL. |
| `ingestion.confluence_token` | string | `""` | Confluence API token. |
| `ingestion.confluence_email` | string | `""` | Confluence account email. |
| `embeddings.enabled` | bool | `false` | Enable local embeddings (MuninnDB handles embeddings by default). |
| `embeddings.model_name` | string | `"all-MiniLM-L6-v2"` | Local embedding model name. |
| `log_level` | string | `"INFO"` | Python log level. |
| `api_host` | string | `"0.0.0.0"` | API server bind address. |
| `api_port` | int | `8000` | API server port. |

## Environment Variables

Environment variables override config file values. Create a `.env` file in the project root:

```bash
# LLM provider keys (set only the one you use)
LLM_API_KEY=sk-...
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=mistral

# MuninnDB overrides
MUNINN_URL=http://localhost:8475
MUNINN_MCP_URL=http://localhost:8750/mcp
MUNINN_TOKEN=mk_...

# Embedding provider
EMBED_PROVIDER=openai
EMBED_API_KEY=sk-...

# Config file path
DALIL_CONFIG=config.json
```

Only set the variables you need. See [SETUP.md](../SETUP.md) for the full override table.

## Vault Management

Vaults are isolated knowledge bases per client. The CLI manages them via `dalil vault`:

```bash
# Create a new vault (auto-generates an API key)
dalil vault create client-alpha

# Create a public vault (no auth required)
dalil vault create shared-kb --public

# List all vaults
dalil vault list

# Clone a vault
dalil vault clone production staging

# Show stored API key for a vault
dalil vault key client-alpha

# Clear all memories from a vault (keeps the vault)
dalil vault clear client-alpha

# Delete a vault and all its memories (irreversible)
dalil vault delete old-project
```

API keys are stored in `.dalil/vaults.json` (Git-ignored, local only).

## Docker Environment

When running with Docker Compose, configuration is injected via:

1. `config.json` — mounted at `/app/config.json`
2. `.env` file — automatically loaded by the container
3. `docker-compose.yml` — environment variables override settings

Example `docker-compose.override.yml` for custom settings:

```yaml
services:
  dalil:
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    volumes:
      - ./config.json:/app/config.json:ro
```

## Provider-Specific Setup

See [LLM & Embedding Providers](LLM_PROVIDERS.md) for detailed configuration per provider.
