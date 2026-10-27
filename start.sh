#!/usr/bin/env bash
# FilmHouse Stream Bot Deployment & Startup Script

set -e

echo "🚀 [FilmHouse] Preparing environment..."

# 1. Ensure Python3 virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv venv
fi

# 2. Activate virtual environment
source venv/bin/activate

# 3. Upgrade pip and install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# 4. Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️ .env file not found! Copying from .env.example..."
    cp .env.example .env
    echo "❗ Please edit .env with your Telegram API keys and BIN_CHANNEL_ID before starting."
    exit 1
fi

echo "✅ Environment ready. Starting FilmHouse Stream Server..."
exec python3 main.py
