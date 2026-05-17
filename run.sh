#!/bin/bash
# Start the AI Resume Screener application

set -e
cd "$(dirname "$0")"

PORT=${PORT:-5000}

# Create virtualenv if missing
if [ ! -d "venv" ]; then
  echo "[*] Creating virtual environment..."
  python3 -m venv venv
  source venv/bin/activate
  echo "[*] Installing dependencies..."
  pip install --quiet -r requirements.txt
  echo "[*] Downloading spaCy model..."
  python -m spacy download en_core_web_sm
else
  source venv/bin/activate
fi

# Ensure required directories exist
mkdir -p resumes exports data

# Copy env example if .env doesn't exist
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "[*] Created .env from .env.example — edit it to configure email/secrets"
fi

echo ""
echo "========================================================"
echo "  AI Resume Screener is starting..."
echo "  URL    : http://localhost:${PORT}"
echo "  Login  : admin / admin123"
echo "  To stop: Ctrl+C"
echo "========================================================"
echo ""

# Use PORT env var if set (e.g. PORT=5001 ./run.sh)
python -c "
from app import app
import os
app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
"
