from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from utils.db import get_user, upsert_user, is_authed, get_lang, count_user_files, get_file_limit, get_setting
from locales.strings import t
from config import ADMIN_ID, ADMIN_TOKEN

ASK_PASSWORD = 0
ASK_LANGUAGE = 1

def main_menu_kb(lang, is_admin=False):
    kb = [
        [InlineKeyboardButton(t("btn_upload",   lang), callback_data="menu_upload"),
         InlineKeyboardButton(t("btn_my_files", lang), callback_data="menu_files")],
        [InlineKeyboardButton(t("btn_search",   lang), callback_data="menu_search"),
         InlineKeyboardButton(t("btn_premium",  lang), callback_data="menu_premium")],
        [InlineKeyboardButton(t("btn_settings", lang), callback_data="menu_settings")],
    ]
    if is_admin:
        kb.append([InlineKeyboardButton("👑 Admin Panel", callback_data="menu_admin")])
    return InlineKeyboardMarkup(kb)

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = ctx.args or []

    # Admin token
    if args and args[0] == ADMIN_TOKEN and ADMIN_TOKEN:
        upsert_user(user.id, username=user.username, first_name=user.first_name, authed=True, is_admin=True)
        lang = get_lang(user.id)
        count = count_user_files(user.id)
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
            reply_markup=main_menu_kb(lang, is_admin=(user.id == ADMIN_ID)),
            parse_mode="HTML"
        )
        return ConversationHandler.END

    upsert_user(user.id, username=user.username, first_name=user.first_name)
    kb = [[
        InlineKeyboardButton("🇮🇷 فارسی",   callback_data="setlang_fa"),
        InlineKeyboardButton("🏳️ کوردی",   callback_data="setlang_ku"),
        InlineKeyboardButton("🇬🇧 English", callback_data="setlang_en"),
    ]]
    await update.message.reply_text(t("welcome","fa"), reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
    return ASK_LANGUAGE

async def handle_set_language(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user  = query.from_user
    lang  = query.data.replace("setlang_","")
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
        reply_markup=main_menu_kb(lang, is_admin=(user.id==ADMIN_ID)), parse_mode="HTML"
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
        reply_markup=main_menu_kb(lang, is_admin=(user.id==ADMIN_ID)), parse_mode="HTML"
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
        reply_markup=main_menu_kb(lang, is_admin=(user.id==ADMIN_ID)), parse_mode="HTML"
    )
