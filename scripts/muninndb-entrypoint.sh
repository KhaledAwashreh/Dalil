#!/bin/sh
# Maps EMBED_PROVIDER + EMBED_API_KEY to the correct MUNINN_*_KEY env var,
# then execs the original MuninnDB entrypoint.

if [ -n "$EMBED_PROVIDER" ] && [ -n "$EMBED_API_KEY" ]; then
  case "$EMBED_PROVIDER" in
    openai)  export MUNINN_OPENAI_KEY="$EMBED_API_KEY" ;;
    jina)    export MUNINN_JINA_KEY="$EMBED_API_KEY" ;;
    cohere)  export MUNINN_COHERE_KEY="$EMBED_API_KEY" ;;
    google)  export MUNINN_GOOGLE_KEY="$EMBED_API_KEY" ;;
    mistral) export MUNINN_MISTRAL_KEY="$EMBED_API_KEY" ;;
    voyage)  export MUNINN_VOYAGE_KEY="$EMBED_API_KEY" ;;
    *)       echo "WARNING: Unknown EMBED_PROVIDER '$EMBED_PROVIDER'" ;;
  esac
fi

# Exec the original command (MuninnDB server)
exec "$@"

