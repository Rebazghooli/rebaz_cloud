from datetime import datetime, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from utils.db import (get_user, upsert_user, is_authed, get_lang,
                      count_user_files, get_file_limit, get_setting,
                      get_file_by_unique_code, get_user_stats)
from locales.strings import t
from config import ADMIN_ID, ADMIN_TOKEN, STORAGE_CHANNEL

ASK_PASSWORD = 0
ASK_LANGUAGE = 1

def fmt(ts):
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")

def main_menu_kb(lang, is_admin=False):
    kb = [
        [InlineKeyboardButton(t("btn_upload",   lang), callback_data="menu_upload"),
         InlineKeyboardButton(t("btn_my_files", lang), callback_data="menu_files")],
        [InlineKeyboardButton(t("btn_search",   lang), callback_data="menu_search"),
         InlineKeyboardButton(t("btn_premium",  lang), callback_data="menu_premium")],
        [InlineKeyboardButton(t("btn_stats",    lang), callback_data="menu_stats"),
         InlineKeyboardButton(t("btn_settings", lang), callback_data="menu_settings")],
    ]
    if is_admin:
        kb.append([InlineKeyboardButton("👑 Admin Panel", callback_data="menu_admin")])
    return InlineKeyboardMarkup(kb)

def _is_admin(user_id):
    """Consistent admin check: must match ADMIN_ID config."""
    return user_id == ADMIN_ID

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = ctx.args or []

    # ── Handle shared file deep link: /start file_XXXXXX ──
    if args and args[0].startswith("file_"):
        code = args[0][5:]
        file = get_file_by_unique_code(code)
        lang = get_lang(user.id) if get_user(user.id) else "fa"
        if not file:
            await update.message.reply_text(t("shared_file_not_found", lang))
            return ConversationHandler.END
        try:
            await update.message.reply_text(t("shared_file_sent", lang))
            await update.message.bot.forward_message(
                chat_id=user.id,
                from_chat_id=STORAGE_CHANNEL,
                message_id=file["channel_msg_id"]
            )
        except Exception as e:
            await update.message.reply_text(f"❌ {e}")
        return ConversationHandler.END

    # ── Handle admin token: /start ADMIN_TOKEN ──
    if args and args[0] == ADMIN_TOKEN and ADMIN_TOKEN:
        upsert_user(user.id, username=user.username, first_name=user.first_name,
                    authed=True, is_admin=True)
        lang = get_lang(user.id)
        await update.message.reply_text(
            t("auth_done", lang, name=user.first_name or "Admin"),
            reply_markup=main_menu_kb(lang, is_admin=True), parse_mode="HTML"
        )
        return ConversationHandler.END

    u = get_user(user.id)
    if u and u["is_blocked"]:
        await update.message.reply_text(t("blocked", "fa"))
        return ConversationHandler.END

    if is_authed(user.id):
        lang = get_lang(user.id)
        count = count_user_files(user.id)
        limit = get_file_limit(user.id)
        lim = "∞" if (u and (u["is_admin"] or u["is_vip"])) else str(limit)
        await update.message.reply_text(
            t("main_menu", lang, count=count, limit=lim),
            reply_markup=main_menu_kb(lang, is_admin=_is_admin(user.id)),
            parse_mode="HTML"
        )
        return ConversationHandler.END

    upsert_user(user.id, username=user.username, first_name=user.first_name)
    kb = [[
        InlineKeyboardButton("🇮🇷 فارسی",   callback_data="setlang_fa"),
        InlineKeyboardButton("🏳️ کوردی",   callback_data="setlang_ku"),
        InlineKeyboardButton("🇬🇧 English", callback_data="setlang_en"),
    ]]
    await update.message.reply_text(
        t("welcome", "fa"), reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML"
    )
    return ASK_LANGUAGE

async def handle_set_language(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    lang = query.data.replace("setlang_", "")
    upsert_user(user.id, lang=lang)

    pwd = get_setting("bot_password") or ""
    if pwd:
        await query.edit_message_text(t("ask_password", lang), parse_mode="HTML")
        return ASK_PASSWORD

    upsert_user(user.id, authed=True)
    u = get_user(user.id)
    count = count_user_files(user.id)
    limit = get_file_limit(user.id)
    lim = "∞" if (u and (u["is_admin"] or u["is_vip"])) else str(limit)
    await query.edit_message_text(
        t("auth_done", lang, name=user.first_name or ""),
        reply_markup=main_menu_kb(lang, is_admin=_is_admin(user.id)), parse_mode="HTML"
    )
    return ConversationHandler.END

async def handle_password(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user    = update.effective_user
    lang    = get_lang(user.id)
    entered = update.message.text.strip()
    pwd     = get_setting("bot_password") or ""

    if entered != pwd:
        await update.message.reply_text(t("wrong_password", lang))
        return ASK_PASSWORD

    upsert_user(user.id, authed=True)
    u = get_user(user.id)
    count = count_user_files(user.id)
    limit = get_file_limit(user.id)
    lim = "∞" if (u and (u["is_admin"] or u["is_vip"])) else str(limit)
    await update.message.reply_text(
        t("auth_done", lang, name=user.first_name or ""),
        reply_markup=main_menu_kb(lang, is_admin=_is_admin(user.id)), parse_mode="HTML"
    )
    return ConversationHandler.END

async def show_main_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user  = query.from_user
    lang  = get_lang(user.id)
    u     = get_user(user.id)
    count = count_user_files(user.id)
    limit = get_file_limit(user.id)
    lim   = "∞" if (u and (u["is_admin"] or u["is_vip"])) else str(limit)
    await query.edit_message_text(
        t("main_menu", lang, count=count, limit=lim),
        reply_markup=main_menu_kb(lang, is_admin=_is_admin(user.id)),
        parse_mode="HTML"
    )

async def show_user_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user  = query.from_user
    lang  = get_lang(user.id)
    stats = get_user_stats(user.id)
    if not stats:
        await query.edit_message_text("❌ خطا در دریافت آمار.")
        return
    u = stats["user"]
    name   = u["first_name"] or u["username"] or str(user.id)
    status = "👑 ادمین" if u["is_admin"] else ("⭐ VIP" if u["is_vip"] else "👤 عادی")
    limit  = get_file_limit(user.id)
    lim    = "∞" if (u["is_admin"] or u["is_vip"]) else str(limit)
    joined = fmt(u["added_at"]) if u.get("added_at") else "—"
    kb = [[InlineKeyboardButton(t("btn_back", lang), callback_data="menu_back")]]
    await query.edit_message_text(
        t("user_stats", lang,
          name=name, uid=user.id, status=status,
          files=stats["total_files"], limit=lim,
          shared=stats["shared_files"],
          folders=stats["folder_count"],
          purchases=stats["purchases"],
          bought=stats["total_bought"],
          joined=joined),
        reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML"
    )
