#!/bin/bash
set -e
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'

echo -e "${CYAN}"
echo "╔══════════════════════════════════════╗"
echo "║      RebazCloud Setup Wizard         ║"
echo "╚══════════════════════════════════════╝"
echo -e "${NC}"

apt install python3 python3-pip -y -q 2>/dev/null || true
pip3 install -r requirements.txt --break-system-packages -q
echo -e "${GREEN}✅ Dependencies نصب شد${NC}"
echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo -e "${YELLOW}1. توکن بات (از @BotFather):${NC}"
read -r BOT_TOKEN
while [[ -z "$BOT_TOKEN" ]]; do read -r BOT_TOKEN; done

echo -e "${YELLOW}2. آیدی عددی ادمین (از @userinfobot):${NC}"
read -r ADMIN_ID
while ! [[ "$ADMIN_ID" =~ ^[0-9]+$ ]]; do read -r ADMIN_ID; done

echo -e "${YELLOW}3. آیدی کانال پرایوت (مثال: -1001234567890):${NC}"
echo "   ← بات را ادمین کانال کن، بعد آیدی را بنویس"
read -r STORAGE_CHANNEL
while [[ -z "$STORAGE_CHANNEL" ]]; do read -r STORAGE_CHANNEL; done

echo -e "${YELLOW}4. رمز عبور بات (خالی = بدون رمز):${NC}"
read -r BOT_PASSWORD

echo -e "${YELLOW}5. کلید NowPayments (خالی = غیرفعال):${NC}"
read -r NOWPAYMENTS_KEY

echo -e "${YELLOW}6. محدودیت فایل پیش‌فرض (پیش‌فرض: 50):${NC}"
read -r FREE_LIMIT
FREE_LIMIT=${FREE_LIMIT:-50}

ADMIN_TOKEN=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")

cat > .env << EOF
BOT_TOKEN=${BOT_TOKEN}
ADMIN_ID=${ADMIN_ID}
ADMIN_TOKEN=${ADMIN_TOKEN}
STORAGE_CHANNEL=${STORAGE_CHANNEL}
BOT_PASSWORD=${BOT_PASSWORD}
NOWPAYMENTS_KEY=${NOWPAYMENTS_KEY}
FREE_LIMIT=${FREE_LIMIT}
EOF

python3 -c "from utils.db import init_db; init_db()"
echo -e "${GREEN}✅ دیتابیس ساخته شد${NC}"

BOT_USERNAME=$(python3 -c "
import urllib.request, json
try:
    r = urllib.request.urlopen('https://api.telegram.org/bot${BOT_TOKEN}/getMe')
    d = json.loads(r.read())
    print(d['result']['username'])
except: print('YOUR_BOT')
")

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  ✅ نصب کامل شد!${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}🔗 لینک ورود ادمین:${NC}"
echo -e "  ${GREEN}https://t.me/${BOT_USERNAME}?start=${ADMIN_TOKEN}${NC}"
echo ""
echo -e "${YELLOW}⚠️  این لینک را جای امنی ذخیره کن!${NC}"
echo ""
echo -e "${YELLOW}▶️  اجرا:${NC}  python3 bot.py"
echo ""

# Install as service
echo -e "${YELLOW}میخوای به عنوان سرویس systemd نصب بشه؟ (y/n)${NC}"
read -r INSTALL_SERVICE
if [[ "$INSTALL_SERVICE" == "y" ]]; then
    cat > /etc/systemd/system/rebazcloud.service << SEOF
[Unit]
Description=RebazCloud Telegram Bot
After=network.target

[Service]
WorkingDirectory=$(pwd)
ExecStart=/usr/bin/python3 bot.py
Restart=always
RestartSec=5
EnvironmentFile=$(pwd)/.env

[Install]
WantedBy=multi-user.target
SEOF
    systemctl enable --now rebazcloud
    echo -e "${GREEN}✅ سرویس نصب و اجرا شد${NC}"
    echo -e "وضعیت: ${CYAN}systemctl status rebazcloud${NC}"
fi
