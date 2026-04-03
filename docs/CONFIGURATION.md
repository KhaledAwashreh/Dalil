# Configuration

## config.json

Dalil reads `config.json` at startup. See [config.example.json](../config.json/config.example.json) for a complete template.

### Full Schema

```json
{
  "llm_provider": "anthropic",
  "llm_model": "claude-3-5-sonnet-20241022",
  "llm_temperature": 0.7,
  "embedding_provider": "onnx",
  "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
  "muninndb": {
    "endpoint": "http://muninndb:8475",
    "mcp_endpoint": "http://muninndb:8750",
    "max_hops": 3,
    "health_check_interval_seconds": 10
  }
}
```

### Configuration Options

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `llm_provider` | string | `openai` | LLM provider: `openai`, `anthropic`, `ollama`, `deepseek`, etc. |
| `llm_model` | string | `gpt-4o` | Model identifier (e.g., `claude-3-5-sonnet-20241022`). |
| `llm_temperature` | float | `0.7` | Sampling temperature (0.0–1.0). Lower = more deterministic. |
| `embedding_provider` | string | `onnx` | Embedding provider: `onnx` (local), `openai`, `jina`, `cohere`, `google`, etc. |
| `embedding_model` | string | `sentence-transformers/all-MiniLM-L6-v2` | Embedding model name. |
| `muninndb.endpoint` | string | `http://localhost:8475` | MuninnDB REST endpoint. Docker: `http://muninndb:8475`. |
| `muninndb.mcp_endpoint` | string | `http://localhost:8750` | MuninnDB MCP endpoint. Docker: `http://muninndb:8750`. |
| `muninndb.max_hops` | int | `3` | Maximum graph traversal hops for ACTIVATE pipeline. |
| `muninndb.health_check_interval_seconds` | int | `10` | How often to check MuninnDB health. |

## Environment Variables

Create a `.env` file in the project root:

```bash
OPENAI_API_KEY=sk-proj-...
ANTHROPIC_API_KEY=sk-ant-...
DEEPSEEK_API_KEY=sk-...
COHERE_API_KEY=...
GOOGLE_API_KEY=...
JINA_API_KEY=...
VOYAGE_API_KEY=...
```

The application loads `.env` automatically. Only set the keys for providers you use.

## Vault Management

Vaults are isolated knowledge bases per client. The CLI automatically creates and manages them:

```bash
# Create a new vault for a client
dalil vault create --client client-alpha

# List all vaults
dalil vault list

# Get vault information
dalil vault stats --vault myproject

# Clone an existing vault (backups, templates)
dalil vault clone --source production --destination staging

# Generate an API key for a client
dalil vault key --vault myproject

# Delete a vault (irreversible)
dalil vault delete --vault old-project
```

All vault data is stored in `.dalil/vaults.json` (Git-ignored, local only).

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
