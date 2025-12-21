#!/bin/bash
# Development environment setup script

set -e

echo "=== Lumera Agent Memory: Development Setup ==="

# Check Python version
python_version=$(python3 --version 2>&1 | grep -oP '3\.\d+')
required_version="3.10"

if [[ $(echo -e "$python_version\n$required_version" | sort -V | head -n1) != "$required_version" ]]; then
    echo "❌ Python 3.10+ required (found: $python_version)"
    exit 1
fi

echo "✓ Python $python_version detected"

# Create virtual environment
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment exists"
fi

# Activate venv
source .venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r scripts/requirements.txt
echo "✓ Dependencies installed"

# Generate encryption key if not exists
if [ -z "$LUMERA_MEMORY_KEY" ]; then
    echo ""
    echo "⚠️  LUMERA_MEMORY_KEY not set"
    echo "Generate a key with:"
    echo "  export LUMERA_MEMORY_KEY=\$(openssl rand -hex 32)"
    echo ""
    echo "Add to .env file for persistence (DO NOT COMMIT):"
    echo "  echo \"LUMERA_MEMORY_KEY=\$(openssl rand -hex 32)\" > .env"
    echo ""
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Activate venv: source .venv/bin/activate"
echo "2. Set encryption key: export LUMERA_MEMORY_KEY=\$(openssl rand -hex 32)"
echo "3. Run tests: pytest tests/ -v"
echo "4. Run smoke test: ./scripts/run_smoke.sh"
