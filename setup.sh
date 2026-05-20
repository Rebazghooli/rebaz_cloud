#!/bin/bash
set -e

echo "═══════════════════════════════════════════"
echo "   RebazCloud Bot — Setup Script v2"
echo "═══════════════════════════════════════════"

# ── Check Python ─────────────────────────────
if ! command -v python3 &>/dev/null; then
    echo "❌ Python3 not found. Install it first."
    exit 1
fi

# ── Virtual environment ──────────────────────
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
fi
source .venv/bin/activate

# ── Dependencies ─────────────────────────────
echo "📦 Installing dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

# ── .env check ───────────────────────────────
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo ""
    echo "⚠️  .env file created from template."
    echo "    Please edit .env with your settings before running the bot."
    echo ""
fi

# ── Systemd services ─────────────────────────
BOT_DIR=$(pwd)
PYTHON_PATH="$BOT_DIR/.venv/bin/python3"
USER_NAME=$(whoami)

echo "⚙️  Installing systemd services..."

# Bot service
cat > /tmp/rebazcloud-bot.service << EOF
[Unit]
Description=RebazCloud Telegram Bot
After=network.target

[Service]
Type=simple
User=$USER_NAME
WorkingDirectory=$BOT_DIR
ExecStart=$PYTHON_PATH bot.py
Restart=always
RestartSec=5
EnvironmentFile=$BOT_DIR/.env
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Webhook server service
cat > /tmp/rebazcloud-webhook.service << EOF
[Unit]
Description=RebazCloud Webhook Server (NowPayments IPN)
After=network.target

[Service]
Type=simple
User=$USER_NAME
WorkingDirectory=$BOT_DIR
ExecStart=$PYTHON_PATH webhook_server.py
Restart=always
RestartSec=5
EnvironmentFile=$BOT_DIR/.env
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo mv /tmp/rebazcloud-bot.service     /etc/systemd/system/rebazcloud-bot.service
sudo mv /tmp/rebazcloud-webhook.service /etc/systemd/system/rebazcloud-webhook.service

sudo systemctl daemon-reload
sudo systemctl enable rebazcloud-bot
sudo systemctl enable rebazcloud-webhook

echo ""
echo "═══════════════════════════════════════════"
echo "✅ Setup complete!"
echo ""
echo "Commands:"
echo "  sudo systemctl start   rebazcloud-bot"
echo "  sudo systemctl start   rebazcloud-webhook"
echo "  sudo systemctl status  rebazcloud-bot"
echo "  journalctl -u rebazcloud-bot -f"
echo "═══════════════════════════════════════════"
