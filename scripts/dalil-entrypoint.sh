#!/bin/sh
# Entrypoint script for dalil-api
# Fixes permissions on mounted volumes before starting the app

# Fix permissions on .dalil_auth directory
if [ -d "/app/.dalil_auth" ]; then
    chown -R dalil:dalil /app/.dalil_auth
fi

# Fix permissions on logs directory
if [ -d "/app/logs" ]; then
    chown -R dalil:dalil /app/logs
fi

# Execute the command as dalil user
exec su-exec dalil "$@"
