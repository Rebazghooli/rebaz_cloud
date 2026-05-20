from datetime import datetime, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from utils.db import (get_lang, get_folders, get_files_by_folder, search_files,
                      get_file_by_id, update_file, delete_file, get_folder, get_user,
                      toggle_file_share)
from locales.strings import t
from config import STORAGE_CHANNEL, ADMIN_ID, BOT_USERNAME

EDIT_WAIT_NAME   = 20
EDIT_WAIT_DESC   = 21
EDIT_WAIT_TAGS   = 22
EDIT_WAIT_FOLDER = 23
SEARCH_WAIT      = 30

def fmt(ts):
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")

def file_action_kb(lang, file):
    """Build the action keyboard for a single file."""
    share_btn = (
        InlineKeyboardButton(t("btn_unshare_file", lang), callback_data=f"share_{file['id']}")
        if file.get("is_shared") else
        InlineKeyboardButton(t("btn_share_file",   lang), callback_data=f"share_{file['id']}")
    )
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t("btn_get_file",    lang), callback_data=f"get_{file['id']}"),
         InlineKeyboardButton(t("btn_edit_file",   lang), callback_data=f"edit_{file['id']}")],
        [share_btn,
         InlineKeyboardButton(t("btn_delete_file", lang), callback_data=f"del_{file['id']}")],
    ])

async def my_files(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await query.answer()
    user    = query.from_user
    lang    = get_lang(user.id)
    folders = get_folders(user.id)
    kb = []
    for f in folders:
        c = len(get_files_by_folder(user.id, f["id"]))
        kb.append([InlineKeyboardButton(f"{f['emoji']} {f['name']} ({c})", callback_data=f"browse_{f['id']}")])
    nf = get_files_by_folder(user.id, None)
    if nf:
        kb.append([InlineKeyboardButton(f"📭 بدون فولدر ({len(nf)})", callback_data="browse_none")])
    kb.append([InlineKeyboardButton(t("btn_back", lang), callback_data="menu_back")])
    if len(kb) == 1:
        await query.edit_message_text(
            t("no_folders", lang), reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML"
        )
        return
    await query.edit_message_text(
        t("my_files_title", lang), reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML"
    )

async def browse_folder(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user  = query.from_user
    lang  = get_lang(user.id)
    data  = query.data.replace("browse_", "")
    fid   = None if data == "none" else int(data)
    files = get_files_by_folder(user.id, fid)
    fname = "📭 بدون فولدر"
    if fid:
        f = get_folder(fid)
        if f:
            fname = f"{f['emoji']} {f['name']}"
    if not files:
        kb = [[InlineKeyboardButton(t("btn_back", lang), callback_data="menu_files")]]
        await query.edit_message_text(t("no_files_in_folder", lang), reply_markup=InlineKeyboardMarkup(kb))
        return
    await query.edit_message_text(
        f"📂 <b>{fname}</b> — {len(files)} فایل",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(t("btn_back", lang), callback_data="menu_files")]])
    )
    for file in files:
        text = t("file_item", lang,
                 name=file["custom_name"], tags=file["tags"] or "—",
                 code=file["unique_code"], date=fmt(file["uploaded_at"]))
        await query.message.reply_text(
            text, reply_markup=file_action_kb(lang, file), parse_mode="HTML"
        )

async def get_file_cb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user  = query.from_user
    fid   = int(query.data.replace("get_", ""))
    file  = get_file_by_id(fid, user.id)
    if not file:
        return
    try:
        await query.message.bot.forward_message(
            chat_id=user.id,
            from_chat_id=STORAGE_CHANNEL,
            message_id=file["channel_msg_id"]
        )
    except Exception as e:
        await query.message.reply_text(f"❌ {e}")

async def share_toggle_cb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Toggle sharing for a file and show the share link or confirmation."""
    query = update.callback_query
    await query.answer()
    user  = query.from_user
    lang  = get_lang(user.id)
    fid   = int(query.data.replace("share_", ""))
    file  = get_file_by_id(fid, user.id)
    if not file:
        return
    new_state = toggle_file_share(fid, user.id)
    if new_state is None:
        return
    if new_state:
        bot_username = BOT_USERNAME or (await query.message.bot.get_me()).username
        await query.answer(t("share_enabled", lang,
                             bot_username=bot_username,
                             code=file["unique_code"])[:200], show_alert=True)
        # Also send as a proper message so they can copy the link easily
        await query.message.reply_text(
            t("share_enabled", lang, bot_username=bot_username, code=file["unique_code"]),
            parse_mode="HTML"
        )
    else:
        await query.answer(t("share_disabled", lang), show_alert=True)

async def del_ask(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user  = query.from_user
    lang  = get_lang(user.id)
    fid   = int(query.data.replace("del_", ""))
    ctx.user_data["del_fid"] = fid
    kb = [
        [InlineKeyboardButton(t("btn_yes_delete", lang), callback_data=f"delok_{fid}")],
        [InlineKeyboardButton(t("btn_cancel",     lang), callback_data="menu_files")],
    ]
    await query.edit_message_text(t("confirm_delete", lang), reply_markup=InlineKeyboardMarkup(kb))

async def del_confirm(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user  = query.from_user
    lang  = get_lang(user.id)
    fid   = int(query.data.replace("delok_", ""))
    delete_file(fid, user.id)
    await query.edit_message_text(t("file_deleted", lang))

async def edit_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user  = query.from_user
    lang  = get_lang(user.id)
    fid   = int(query.data.replace("edit_", ""))
    ctx.user_data["edit_fid"] = fid
    kb = [
        [InlineKeyboardButton(t("btn_edit_name",   lang), callback_data="ef_name"),
         InlineKeyboardButton(t("btn_edit_folder", lang), callback_data="ef_folder")],
        [InlineKeyboardButton(t("btn_edit_desc",   lang), callback_data="ef_desc"),
         InlineKeyboardButton(t("btn_edit_tags",   lang), callback_data="ef_tags")],
        [InlineKeyboardButton(t("btn_back",        lang), callback_data="menu_files")],
    ]
    await query.edit_message_text(t("edit_menu", lang), reply_markup=InlineKeyboardMarkup(kb))

async def edit_ask(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query  = update.callback_query
    await query.answer()
    user   = query.from_user
    lang   = get_lang(user.id)
    action = query.data
    kb     = [[InlineKeyboardButton(t("btn_cancel", lang), callback_data="menu_files")]]
    if action == "ef_name":
        ctx.user_data["ef"] = "custom_name"
        await query.edit_message_text(t("ask_new_name", lang), reply_markup=InlineKeyboardMarkup(kb))
        return EDIT_WAIT_NAME
    elif action == "ef_desc":
        ctx.user_data["ef"] = "description"
        await query.edit_message_text(t("ask_new_desc", lang), reply_markup=InlineKeyboardMarkup(kb))
        return EDIT_WAIT_DESC
    elif action == "ef_tags":
        ctx.user_data["ef"] = "tags"
        await query.edit_message_text(t("ask_new_tags", lang), reply_markup=InlineKeyboardMarkup(kb))
        return EDIT_WAIT_TAGS
    elif action == "ef_folder":
        ctx.user_data["ef"] = "folder_id"
        from handlers.upload import folder_kb
        await query.edit_message_text(
            t("ask_folder", lang), reply_markup=folder_kb(lang, get_folders(user.id))
        )
        return EDIT_WAIT_FOLDER

async def edit_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user  = update.effective_user
    lang  = get_lang(user.id)
    text  = update.message.text.strip()
    field = ctx.user_data.get("ef")
    fid   = ctx.user_data.get("edit_fid")
    update_file(fid, user.id, **{field: text})
    from handlers.auth import main_menu_kb
    await update.message.reply_text(
        t("edit_done", lang),
        reply_markup=main_menu_kb(lang, is_admin=(user.id == ADMIN_ID))
    )
    return ConversationHandler.END

async def edit_folder_cb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user  = query.from_user
    lang  = get_lang(user.id)
    data  = query.data
    fid   = ctx.user_data.get("edit_fid")
    if data == "folder_none":
        update_file(fid, user.id, folder_id=None)
    elif data.startswith("folder_") and data != "folder_new":
        update_file(fid, user.id, folder_id=int(data.replace("folder_", "")))
    from handlers.auth import main_menu_kb
    await query.edit_message_text(
        t("edit_done", lang),
        reply_markup=main_menu_kb(lang, is_admin=(user.id == ADMIN_ID))
    )
    return ConversationHandler.END

async def search_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user  = query.from_user
    lang  = get_lang(user.id)
    kb    = [[InlineKeyboardButton(t("btn_cancel", lang), callback_data="menu_back")]]
    await query.edit_message_text(t("ask_search", lang), reply_markup=InlineKeyboardMarkup(kb))
    return SEARCH_WAIT

async def search_recv(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user    = update.effective_user
    lang    = get_lang(user.id)
    q       = update.message.text.strip()
    results = search_files(user.id, q)
    from handlers.auth import main_menu_kb
    if not results:
        await update.message.reply_text(
            t("no_results", lang),
            reply_markup=main_menu_kb(lang, is_admin=(user.id == ADMIN_ID))
        )
        return ConversationHandler.END
    await update.message.reply_text(t("search_results", lang, count=len(results)), parse_mode="HTML")
    for file in results:
        text = t("file_item", lang,
                 name=file["custom_name"], tags=file["tags"] or "—",
                 code=file["unique_code"], date=fmt(file["uploaded_at"]))
        await update.message.reply_text(
            text, reply_markup=file_action_kb(lang, file), parse_mode="HTML"
        )
    return ConversationHandler.END
