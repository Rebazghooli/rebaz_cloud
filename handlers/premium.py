import hmac
import hashlib
import json
import time
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from utils.db import (get_lang, get_user, count_user_files, get_file_limit,
                      save_purchase, get_pending_purchases, confirm_purchase_by_id,
                      update_purchase_status, get_purchase_by_payment_id, add_file_quota, add_log)
from locales.strings import t
from config import (NOWPAYMENTS_KEY, NOWPAYMENTS_IPN_SECRET,
                    PREMIUM_PER_PACK, PREMIUM_PRICE_USD, ADMIN_ID)


def _create_nowpayments_invoice(uid: int, files_added: int) -> dict | None:
    """
    Call NowPayments API to create an invoice.
    Returns the full response dict on success, None on failure.
    """
    if not NOWPAYMENTS_KEY:
        return None
    try:
        resp = requests.post(
            "https://api.nowpayments.io/v1/invoice",
            headers={
                "x-api-key": NOWPAYMENTS_KEY,
                "Content-Type": "application/json",
            },
            json={
                "price_amount":   PREMIUM_PRICE_USD,
                "price_currency": "usd",
                "order_id":       f"rebazcloud_{uid}_{int(time.time())}",
                "order_description": f"RebazCloud +{files_added} files for user {uid}",
                "ipn_callback_url": None,  # Set via NowPayments dashboard
            },
            timeout=10,
        )
        data = resp.json()
        if resp.status_code == 200 and "id" in data:
            return data
        return None
    except Exception:
        return None


async def show_premium(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user  = query.from_user
    lang  = get_lang(user.id)
    u     = get_user(user.id)
    count = count_user_files(user.id)
    limit = get_file_limit(user.id)
    lim   = "∞" if (u and (u["is_admin"] or u["is_vip"])) else str(limit)
    kb = [
        [InlineKeyboardButton(t("btn_buy", lang), callback_data="premium_buy")],
        [InlineKeyboardButton(t("btn_back", lang), callback_data="menu_back")],
    ]
    await query.edit_message_text(
        t("premium_info", lang, count=count, limit=lim),
        reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML"
    )


async def buy_premium(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user  = query.from_user
    lang  = get_lang(user.id)

    if not NOWPAYMENTS_KEY:
        await query.edit_message_text(
            t("payment_gateway_disabled", lang),
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(t("btn_back", lang), callback_data="menu_premium")]]
            ),
            parse_mode="HTML"
        )
        return

    invoice = _create_nowpayments_invoice(user.id, PREMIUM_PER_PACK)
    if not invoice:
        await query.edit_message_text(
            t("payment_error", lang),
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(t("btn_back", lang), callback_data="menu_premium")]]
            ),
            parse_mode="HTML"
        )
        return

    payment_id  = str(invoice["id"])
    invoice_url = invoice.get("invoice_url", "")

    save_purchase(user.id, PREMIUM_PRICE_USD, PREMIUM_PER_PACK, payment_id)
    add_log(user.id, "purchase_created", f"payment_id={payment_id}")

    # Notify admin
    try:
        u = get_user(user.id)
        name = (u["first_name"] or u["username"] or str(user.id)) if u else str(user.id)
        await query.message.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                f"💰 <b>خرید جدید</b>\n\n"
                f"👤 {name} | <code>{user.id}</code>\n"
                f"💵 ${PREMIUM_PRICE_USD} — +{PREMIUM_PER_PACK} فایل\n"
                f"🆔 <code>{payment_id}</code>"
            ),
            parse_mode="HTML"
        )
    except Exception:
        pass

    kb = [
        [InlineKeyboardButton("💳 پرداخت", url=invoice_url)] if invoice_url else [],
        [InlineKeyboardButton(t("btn_back", lang), callback_data="menu_premium")],
    ]
    kb = [row for row in kb if row]  # remove empty rows

    await query.edit_message_text(
        t("payment_created", lang,
          files=PREMIUM_PER_PACK,
          payment_id=payment_id),
        reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML"
    )


async def handle_nowpayments_webhook(data: dict, raw_body: bytes, sig_header: str) -> bool:
    """
    Validate NowPayments IPN webhook and confirm purchase.
    Returns True if valid and processed, False otherwise.
    Call this from your aiohttp/webhook server.
    """
    # ── Signature verification ─────────────────────────────────────
    if NOWPAYMENTS_IPN_SECRET:
        expected = hmac.new(
            NOWPAYMENTS_IPN_SECRET.encode(),
            raw_body,
            hashlib.sha512
        ).hexdigest()
        if not hmac.compare_digest(expected, sig_header):
            return False

    payment_status = data.get("payment_status", "")
    payment_id     = str(data.get("invoice_id") or data.get("order_id", ""))

    if payment_status not in ("finished", "confirmed", "partially_paid"):
        return True  # valid webhook, just not a confirming status

    purchase = get_purchase_by_payment_id(payment_id)
    if not purchase or purchase["status"] == "confirmed":
        return True

    update_purchase_status(payment_id, "confirmed")
    add_file_quota(purchase["user_id"], purchase["files_added"])
    add_log(purchase["user_id"], "purchase_confirmed_webhook",
            f"+{purchase['files_added']} files payment_id={payment_id}")
    return True


async def send_purchase_confirmed_notify(bot, uid: int, files_added: int):
    """Send a Telegram notification to user after payment confirmed."""
    lang = get_lang(uid)
    try:
        await bot.send_message(
            chat_id=uid,
            text=t("purchase_confirmed_notify", lang, files=files_added),
            parse_mode="HTML"
        )
    except Exception:
        pass


# ─── Admin: manual confirm ─────────────────────────────────────────────────────

async def adm_pending_purchases(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Show pending (unconfirmed) purchases for admin manual confirmation."""
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        return
    purchases = get_pending_purchases()
    if not purchases:
        kb = [[InlineKeyboardButton("🔙 بازگشت", callback_data="menu_admin")]]
        await query.edit_message_text(
            "📭 هیچ پرداخت در انتظار تأییدی وجود ندارد.",
            reply_markup=InlineKeyboardMarkup(kb)
        )
        return
    kb = []
    for p in purchases:
        uname = p.get("username") or str(p["user_id"])
        label = f"@{uname} — ${p['amount_usd']} — +{p['files_added']} فایل"
        kb.append([
            InlineKeyboardButton(label, callback_data="noop"),
            InlineKeyboardButton("✅ تأیید", callback_data=f"adm_confirm_pay_{p['id']}"),
        ])
    kb.append([InlineKeyboardButton("🔙 بازگشت", callback_data="menu_admin")])
    await query.edit_message_text(
        f"💰 <b>پرداخت‌های در انتظار تأیید ({len(purchases)}):</b>",
        reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML"
    )


async def adm_confirm_pay(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Admin manually confirms a purchase."""
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        return
    purchase_id = int(query.data.replace("adm_confirm_pay_", ""))
    result = confirm_purchase_by_id(purchase_id)
    if not result:
        await query.answer("❌ این پرداخت قبلاً تأیید شده یا وجود ندارد.", show_alert=True)
        return
    uid, files_added = result
    await query.answer(f"✅ تأیید شد! +{files_added} فایل به کاربر {uid} اضافه شد.", show_alert=True)
    await send_purchase_confirmed_notify(query.message.bot, uid, files_added)
    # Refresh the list
    await adm_pending_purchases(update, ctx)
