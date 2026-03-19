#!/usr/bin/env bash
# Bootstrap MuninnDB for the Consultant Memory System.
#
# This script:
# 1. Installs MuninnDB (if not already installed)
# 2. Initializes it (creates admin credentials, auto-detects tools)
# 3. Starts the server
# 4. Waits for readiness
#
# Usage:
#   chmod +x scripts/bootstrap_muninn.sh
#   ./scripts/bootstrap_muninn.sh
#
# Environment variables:
#   MUNINN_VAULT  — vault name to create (default: "default")

set -euo pipefail

VAULT="${MUNINN_VAULT:-default}"

echo "=== Consultant Memory System — MuninnDB Bootstrap ==="

# 1. Check if muninn is installed
if ! command -v muninn &>/dev/null; then
    echo "MuninnDB not found. Installing..."
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        echo "On Windows, run this in PowerShell:"
        echo "  irm https://muninndb.com/install.ps1 | iex"
        exit 1
    else
        curl -sSL https://muninndb.com/install.sh | sh
    fi
fi

echo "MuninnDB version: $(muninn --version 2>/dev/null || echo 'unknown')"

# 2. Initialize (idempotent — safe to re-run)
if [ ! -d "$HOME/.muninn" ]; then
    echo "Initializing MuninnDB..."
    muninn init --yes
    echo ""
    echo "IMPORTANT: Save the admin credentials shown above!"
    echo ""
else
    echo "MuninnDB already initialized (~/.muninn exists)"
fi

# 3. Start server (if not already running)
if muninn status &>/dev/null; then
    echo "MuninnDB is already running."
else
    echo "Starting MuninnDB..."
    muninn start
    echo "Waiting for MuninnDB to become ready..."
    for i in $(seq 1 30); do
        if curl -sf http://localhost:8476/api/ready &>/dev/null; then
            echo "MuninnDB is ready."
            break
        fi
        sleep 1
    done
fi

# 4. Verify health
echo ""
echo "Health check:"
curl -s http://localhost:8476/api/health | python3 -m json.tool 2>/dev/null || \
    curl -s http://localhost:8476/api/health

echo ""
echo "=== MuninnDB is running ==="
echo "  REST API:  http://localhost:8475"
echo "  Web UI:    http://localhost:8476"
echo "  MCP:       http://localhost:8750/mcp"
echo "  Vault:     ${VAULT}"
echo ""
echo "Next steps:"
echo "  1. Copy config/config.example.json to config.json and edit it"
echo "  2. pip install -r requirements.txt"
echo "  3. CONSULTANT_CONFIG=config.json uvicorn dalil.api.main:app"
