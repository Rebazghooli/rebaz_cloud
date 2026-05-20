"""
NowPayments IPN Webhook Server
-------------------------------
Run this alongside bot.py to receive automatic payment confirmations.

Usage:
    python webhook_server.py

NowPayments Dashboard setup:
    IPN Callback URL: http://YOUR_SERVER_IP:8080/nowpayments-ipn
    IPN Secret Key: set as NOWPAYMENTS_IPN_SECRET in .env
"""
import asyncio
import json
import logging
from aiohttp import web
from telegram import Bot

from config import BOT_TOKEN, WEBHOOK_PORT, ADMIN_ID
from handlers.premium import handle_nowpayments_webhook, send_purchase_confirmed_notify

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("webhook_server")

bot = Bot(token=BOT_TOKEN)


async def health(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


async def nowpayments_ipn(request: web.Request) -> web.Response:
    """Handle NowPayments IPN callback."""
    try:
        raw_body  = await request.read()
        sig       = request.headers.get("x-nowpayments-sig", "")
        data      = json.loads(raw_body)

        logger.info(f"IPN received: status={data.get('payment_status')} id={data.get('invoice_id')}")

        ok = await handle_nowpayments_webhook(data, raw_body, sig)

        if ok and data.get("payment_status") in ("finished", "confirmed"):
            # Find which user this belongs to and notify them
            from utils.db import get_purchase_by_payment_id
            payment_id = str(data.get("invoice_id") or data.get("order_id", ""))
            purchase = get_purchase_by_payment_id(payment_id)
            if purchase and purchase["status"] == "confirmed":
                await send_purchase_confirmed_notify(bot, purchase["user_id"], purchase["files_added"])
                # Also notify admin
                try:
                    await bot.send_message(
                        chat_id=ADMIN_ID,
                        text=(
                            f"✅ <b>پرداخت خودکار تأیید شد</b>\n\n"
                            f"👤 User: <code>{purchase['user_id']}</code>\n"
                            f"📁 +{purchase['files_added']} فایل\n"
                            f"🆔 <code>{payment_id}</code>"
                        ),
                        parse_mode="HTML"
                    )
                except Exception:
                    pass

        return web.json_response({"ok": ok}, status=200 if ok else 400)

    except Exception as e:
        logger.error(f"IPN handler error: {e}")
        return web.json_response({"error": str(e)}, status=500)


def make_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/health",              health)
    app.router.add_post("/nowpayments-ipn",    nowpayments_ipn)
    return app


if __name__ == "__main__":
    logger.info(f"🌐 Webhook server starting on port {WEBHOOK_PORT}...")
    web.run_app(make_app(), host="0.0.0.0", port=WEBHOOK_PORT)
