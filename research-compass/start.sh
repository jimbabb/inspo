#!/bin/bash
set -e

cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

echo "Installing dependencies..."
pip install -q -r requirements.txt

if [ ! -f ".env" ]; then
    echo ""
    echo "No .env file found. Copy .env.example and add your Anthropic API key:"
    echo "  cp .env.example .env"
    echo "  # Then edit .env with your key"
    echo ""
    exit 1
fi

echo "Starting Research Compass on http://localhost:8000"
python app.py
