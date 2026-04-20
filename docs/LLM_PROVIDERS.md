# LLM & Embedding Providers

## LLM Providers

Dalil is LLM-agnostic: you pick the provider and model.

### Supported LLM Providers

| Provider | Model | Setup | Recommended |
|----------|-------|-------|-------------|
| **OpenAI** | `gpt-4o`, `gpt-4-turbo`, `gpt-3.5-turbo` | API key in `OPENAI_API_KEY` | ✅ Best general-purpose |
| **Anthropic** | `claude-3-5-sonnet-20241022`, `claude-3-opus-20240229` | API key in `ANTHROPIC_API_KEY` | ✅ Best reasoning |
| **Ollama** | `llama2`, `mistral`, `neural-chat`, etc. | Local binary + `OLLAMA_BASE_URL` | 🟡 No cloud cost |
| **DeepSeek** | `deepseek-chat`, `deepseek-reasoner` | API key in `DEEPSEEK_API_KEY` | 🟡 Good value |
| **Cohere** | `command-r-plus`, `command` | API key in `COHERE_API_KEY` | 🟡 Multilingual |
| **Together AI** | Various open models | API key in `TOGETHER_API_KEY` | 🟡 Cheap scale |

### Configuration

Set in `config.json`:

```json
{
  "llm": {
    "type": "api",
    "provider": "anthropic",
    "model": "claude-3-5-sonnet-20241022",
    "api_key": "sk-ant-...",
    "temperature": 0.7
  }
}
```

Or set the API key via environment variable: `LLM_API_KEY=sk-ant-...`

### Ollama (Local)

If you choose Ollama:

1. Install Ollama: https://ollama.com
2. Pull a model: `ollama pull mistral`
3. Start Ollama: `ollama serve` (default: `http://localhost:11434`)
4. Set in `config.json`:

```json
{
  "llm": {
    "type": "api",
    "provider": "ollama",
    "model": "mistral",
    "base_url": "http://localhost:11434/v1"
  }
}
```

No API key needed — fully local, zero cost, privacy-preserved.

---

## Embedding Providers

Embeddings power semantic search in MuninnDB. Dalil supports multiple providers.

### Supported Embedding Providers

| Provider | Model | Setup | Notes |
|----------|-------|-------|-------|
| **ONNX (Local)** | `sentence-transformers/all-MiniLM-L6-v2` (default) | No setup | ✅ Default, no latency, no cost |
| **OpenAI** | `text-embedding-3-small`, `text-embedding-3-large` | API key in `OPENAI_API_KEY` | Dimensions: 512–3072 |
| **Jina AI** | `jina-embeddings-v2-base-en`, etc. | API key in `JINA_API_KEY` | Dimensions: 768–2048 |
| **Cohere** | `embed-english-v3.0` | API key in `COHERE_API_KEY` | Multilingual |
| **Google Vertex AI** | `text-embedding-004` | `GOOGLE_API_KEY` + project | Multilingual |
| **Mistral** | `mistral-embed` | API key in `MISTRAL_API_KEY` | Large context |
| **Voyage AI** | `voyage-2`, `voyage-code-2` | API key in `VOYAGE_API_KEY` | Specialized models |

### Configuration

Embeddings are configured in MuninnDB, not in Dalil directly. MuninnDB handles all embedding generation internally.

To pass an embedding provider through to MuninnDB, set it in `config.json`:

```json
{
  "embeddings": {
    "provider": "openai",
    "api_key": "sk-...",
    "model_name": ""
  }
}
```

Leave `provider` empty (or omit the section) to use MuninnDB's default ONNX embeddings — no configuration needed.

### Local ONNX (MuninnDB Default)

MuninnDB uses ONNX by default for embeddings:

**Advantages:**
- Zero API cost
- No network latency
- No external dependencies
- Privacy-preserving (all data stays local)
- Consistent reproducible results

**Supported ONNX models** (from Hugging Face):
- `all-MiniLM-L6-v2` (384-dim, fast)
- `all-mpnet-base-v2` (768-dim, higher quality)
- `all-roberta-large-v1` (768-dim, very good)
- `sentence-transformers/multilingual-MiniLM-L12-v2` (multilingual)

---

## MuninnDB + Embedding Integration

MuninnDB contains the configured embedding provider. When you ingest:

1. Dalil's loader normalizes the data into `ConsultingCase` objects
2. Dalil sends cases to MuninnDB via `muninn_remember`
3. MuninnDB generates embeddings and stores them in the vault's index
4. On retrieval (`POST /consult`), MuninnDB's ACTIVATE pipeline searches via semantic + full-text hybrid fusion

**You never call the embedding provider directly** — MuninnDB abstracts it entirely.

---

## Switching Providers

To switch providers at runtime:

1. Edit `config.json`:
   ```json
   {
     "llm": {
       "provider": "anthropic",
       "model": "claude-3-5-sonnet-20241022",
       "api_key": "sk-ant-..."
     }
   }
   ```

2. Restart Dalil:
   ```bash
   docker compose down
   docker compose up -d
   ```

No data migration needed. Existing embedded cases stay in MuninnDB; new ingestion uses the new provider.
