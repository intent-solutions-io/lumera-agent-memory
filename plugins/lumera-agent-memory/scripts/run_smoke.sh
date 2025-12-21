#!/bin/bash
# Run 90-second smoke test

set -e

echo "=== Lumera Agent Memory: 90-Second Smoke Test ==="

# Check if venv exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Run: ./scripts/dev_setup.sh"
    exit 1
fi

# Activate venv
source .venv/bin/activate

# Check encryption key
if [ -z "$LUMERA_MEMORY_KEY" ]; then
    echo "⚠️  LUMERA_MEMORY_KEY not set. Using temporary key for smoke test."
    export LUMERA_MEMORY_KEY=$(openssl rand -hex 32)
fi

# Clean cache
rm -rf .cache

# Run smoke test
echo ""
echo "Running smoke test (timeout: 90 seconds)..."
pytest tests/smoke_test_90s.py -v -s --timeout=90

echo ""
echo "✅ Smoke test passed!"
