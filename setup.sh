#!/bin/bash
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}"
echo "═══════════════════════════════════════════"
echo "     RebazCloud Bot — Setup Wizard v2     "
echo "═══════════════════════════════════════════"
echo -e "${NC}"

# ── Check Python ─────────────────────────────
if ! command -v python3 &>/dev/null; then
    echo -e "${RED}❌ Python3 not found. Installing...${NC}"
    apt install python3 python3-pip python3-venv -y -q
fi

# ── Virtual environment ──────────────────────
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}📦 Creating virtual environment...${NC}"
    python3 -m venv .venv
fi
source .venv/bin/activate

# ── Dependencies ─────────────────────────────
echo -e "${YELLOW}📦 Installing dependencies...${NC}"
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo -e "${GREEN}✅ Dependencies installed${NC}"
echo ""

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}   اطلاعات مورد نیاز را وارد کنید       ${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# ── BOT_TOKEN ────────────────────────────────
echo -e "${YELLOW}1. توکن بات تلگرام${NC}"
echo "   → به @BotFather برو و /newbot بزن"
echo -n "   توکن بات: "
read -r BOT_TOKEN
while [[ -z "$BOT_TOKEN" ]]; do
    echo -n "   ❌ خالی است. دوباره وارد کن: "
    read -r BOT_TOKEN
done
echo ""

# ── ADMIN_ID ─────────────────────────────────
echo -e "${YELLOW}2. آیدی عددی ادمین${NC}"
echo "   → به @userinfobot پیام بده"
echo -n "   آیدی عددی: "
read -r ADMIN_ID
while ! [[ "$ADMIN_ID" =~ ^[0-9]+$ ]]; do
    echo -n "   ❌ باید عدد باشد: "
    read -r ADMIN_ID
done
echo ""

# ── ADMIN_TOKEN ──────────────────────────────
echo -e "${YELLOW}3. رمز ورود ادمین به بات${NC}"
echo "   → یه رمز دلخواه برای ورود با لینک ادمین"
echo -n "   رمز ادمین: "
read -r ADMIN_TOKEN
while [[ -z "$ADMIN_TOKEN" ]]; do
    echo -n "   ❌ خالی است: "
    read -r ADMIN_TOKEN
done
echo ""

# ── BOT_USERNAME ─────────────────────────────
echo -e "${YELLOW}4. یوزرنیم بات${NC}"
echo "   → بدون @ (مثال: rebazcloud_bot)"
echo -n "   یوزرنیم: "
read -r BOT_USERNAME
while [[ -z "$BOT_USERNAME" ]]; do
    echo -n "   ❌ خالی است: "
    read -r BOT_USERNAME
done
echo ""

# ── STORAGE_CHANNEL ──────────────────────────
echo -e "${YELLOW}5. آیدی کانال پرایوت${NC}"
echo "   → بات را ادمین کانال کن"
echo "   → فرمت: -100xxxxxxxxxx"
echo -n "   آیدی کانال: "
read -r STORAGE_CHANNEL
while [[ -z "$STORAGE_CHANNEL" ]]; do
    echo -n "   ❌ خالی است: "
    read -r STORAGE_CHANNEL
done
echo ""

# ── BOT_PASSWORD ─────────────────────────────
echo -e "${YELLOW}6. رمز عبور بات (خالی = بدون رمز)${NC}"
echo "   → کاربران برای ورود این رمز را وارد می‌کنند"
echo -n "   رمز عبور: "
read -r BOT_PASSWORD
echo ""

# ── FREE_LIMIT ───────────────────────────────
echo -e "${YELLOW}7. محدودیت فایل رایگان (پیش‌فرض: 50)${NC}"
echo -n "   محدودیت: "
read -r FREE_LIMIT
FREE_LIMIT=${FREE_LIMIT:-50}
echo ""

# ── NOWPAYMENTS ──────────────────────────────
echo -e "${YELLOW}8. کلید NowPayments (خالی = غیرفعال)${NC}"
echo "   → از nowpayments.io بگیر"
echo -n "   API Key: "
read -r NOWPAYMENTS_KEY
echo ""

NOWPAYMENTS_IPN_SECRET=""
if [[ -n "$NOWPAYMENTS_KEY" ]]; then
    echo -e "${YELLOW}9. IPN Secret از داشبورد NowPayments${NC}"
    echo -n "   IPN Secret: "
    read -r NOWPAYMENTS_IPN_SECRET
    echo ""
fi

# ── Write .env ───────────────────────────────
cat > .env << EOF
BOT_TOKEN=${BOT_TOKEN}
ADMIN_ID=${ADMIN_ID}
ADMIN_TOKEN=${ADMIN_TOKEN}
BOT_USERNAME=${BOT_USERNAME}
STORAGE_CHANNEL=${STORAGE_CHANNEL}
BOT_PASSWORD=${BOT_PASSWORD}
FREE_LIMIT=${FREE_LIMIT}
NOWPAYMENTS_KEY=${NOWPAYMENTS_KEY}
NOWPAYMENTS_IPN_SECRET=${NOWPAYMENTS_IPN_SECRET}
WEBHOOK_PORT=8080
EOF

echo -e "${GREEN}✅ فایل .env ساخته شد${NC}"

# ── Systemd services ─────────────────────────
BOT_DIR=$(pwd)
PYTHON_PATH="$BOT_DIR/.venv/bin/python3"
USER_NAME=$(whoami)

echo -e "${YELLOW}⚙️  Installing systemd services...${NC}"

cat > /tmp/rebazcloud-bot.service << SEOF
[Unit]
Description=RebazCloud Telegram Bot
After=network.target

[Service]
Type=simple
User=${USER_NAME}
WorkingDirectory=${BOT_DIR}
ExecStart=${PYTHON_PATH} bot.py
Restart=always
RestartSec=5
EnvironmentFile=${BOT_DIR}/.env
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SEOF

cat > /tmp/rebazcloud-webhook.service << SEOF
[Unit]
Description=RebazCloud Webhook Server
After=network.target

[Service]
Type=simple
User=${USER_NAME}
WorkingDirectory=${BOT_DIR}
ExecStart=${PYTHON_PATH} webhook_server.py
Restart=always
RestartSec=5
EnvironmentFile=${BOT_DIR}/.env
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SEOF

mv /tmp/rebazcloud-bot.service     /etc/systemd/system/rebazcloud-bot.service
mv /tmp/rebazcloud-webhook.service /etc/systemd/system/rebazcloud-webhook.service

systemctl daemon-reload
systemctl enable --now rebazcloud-bot
systemctl enable --now rebazcloud-webhook

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  ✅ نصب با موفقیت انجام شد!${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}🔗 لینک ورود ادمین:${NC}"
echo -e "  ${GREEN}https://t.me/${BOT_USERNAME}?start=${ADMIN_TOKEN}${NC}"
echo ""
echo -e "${YELLOW}📋 دستورات مفید:${NC}"
echo "  systemctl status rebazcloud-bot"
echo "  systemctl status rebazcloud-webhook"
echo "  journalctl -u rebazcloud-bot -f"
echo ""
