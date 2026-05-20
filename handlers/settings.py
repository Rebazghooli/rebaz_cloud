from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from utils.db import get_lang, get_folders, delete_folder, get_folder, upsert_user
from locales.strings import t
from config import ADMIN_ID

ASK_FOLDER_NAME = 60

async def show_settings(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    lang = get_lang(user.id)
    kb = [
        [InlineKeyboardButton(t("btn_change_lang",    lang), callback_data="settings_lang")],
        [InlineKeyboardButton(t("btn_manage_folders", lang), callback_data="settings_folders")],
        [InlineKeyboardButton(t("btn_back",           lang), callback_data="menu_back")],
    ]
    await query.edit_message_text(t("settings_menu", lang), reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

async def change_lang(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    kb = [[
        InlineKeyboardButton("🇮🇷 فارسی",   callback_data="chglang_fa"),
        InlineKeyboardButton("🏳️ کوردی",   callback_data="chglang_ku"),
        InlineKeyboardButton("🇬🇧 English", callback_data="chglang_en"),
    ]]
    await query.edit_message_text("🌐 زبان جدید:", reply_markup=InlineKeyboardMarkup(kb))

async def set_lang(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    lang = query.data.replace("chglang_", "")
    upsert_user(user.id, lang=lang)
    from handlers.auth import show_main_menu
    await show_main_menu(update, ctx)

async def manage_folders(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await query.answer()
    user    = query.from_user
    lang    = get_lang(user.id)
    folders = get_folders(user.id)
    kb = []
    for f in folders:
        kb.append([
            InlineKeyboardButton(f"{f['emoji']} {f['name']}", callback_data="noop"),
            InlineKeyboardButton("🗑️", callback_data=f"del_folder_{f['id']}"),
        ])
    kb.append([InlineKeyboardButton(t("btn_back", lang), callback_data="menu_settings")])
    await query.edit_message_text(
        "📂 <b>مدیریت فولدرها</b>",
        reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML"
    )

async def del_folder_ask(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Ask for confirmation before deleting a folder (was missing before)."""
    query = update.callback_query
    await query.answer()
    user  = query.from_user
    lang  = get_lang(user.id)
    fid   = int(query.data.replace("del_folder_", ""))
    f     = get_folder(fid)
    if not f or f.get("user_id") != user.id:
        await query.answer("❌ فولدر پیدا نشد.", show_alert=True)
        return
    ctx.user_data["del_folder_id"] = fid
    kb = [
        [InlineKeyboardButton(t("btn_confirm_del_folder", lang), callback_data=f"del_folder_ok_{fid}")],
        [InlineKeyboardButton(t("btn_cancel",             lang), callback_data="settings_folders")],
    ]
    await query.edit_message_text(
        t("confirm_del_folder", lang, name=f["name"]),
        reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML"
    )

async def del_folder_confirm(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Execute folder deletion after confirmation."""
    query = update.callback_query
    await query.answer()
    user  = query.from_user
    lang  = get_lang(user.id)
    fid   = int(query.data.replace("del_folder_ok_", ""))
    f     = get_folder(fid)
    if not f or f.get("user_id") != user.id:
        await query.answer("❌ فولدر پیدا نشد.", show_alert=True)
        return
    delete_folder(fid, user.id)
    await query.edit_message_text(t("folder_deleted", lang))
    await manage_folders(update, ctx)
