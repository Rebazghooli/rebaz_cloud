from datetime import datetime, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from utils.db import (is_authed, get_lang, get_folders, create_folder,
                      save_file, count_user_files, get_file_limit, get_folder, get_user)
from locales.strings import t
from config import STORAGE_CHANNEL, ADMIN_ID

# ── Conversation states ──────────────────────
# ASK_FILE must be declared before ASK_NAME so the ConversationHandler
# can route between them. The old code was missing ASK_FILE entirely,
# which caused files sent after clicking "Upload" to go unhandled.
ASK_FILE        = 9
ASK_NAME        = 10
ASK_FOLDER      = 11
ASK_NEW_FOLDER_NAME = 12
ASK_DESC        = 13
ASK_TAGS        = 14

FILE_FILTERS_TYPES = ("document", "video", "audio", "photo", "voice", "video_note", "sticker")

def folder_kb(lang, folders):
    kb = []
    for f in folders:
        kb.append([InlineKeyboardButton(f"{f['emoji']} {f['name']}", callback_data=f"folder_{f['id']}")])
    kb.append([
        InlineKeyboardButton(t("btn_new_folder", lang), callback_data="folder_new"),
        InlineKeyboardButton(t("btn_no_folder",  lang), callback_data="folder_none"),
    ])
    kb.append([InlineKeyboardButton(t("btn_cancel", lang), callback_data="menu_back")])
    return InlineKeyboardMarkup(kb)

async def upload_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Entry point when user clicks the Upload button from menu."""
    query = update.callback_query
    await query.answer()
    user  = query.from_user
    lang  = get_lang(user.id)
    if not is_authed(user.id):
        await query.edit_message_text(t("not_authed", lang))
        return ConversationHandler.END
    count = count_user_files(user.id)
    limit = get_file_limit(user.id)
    if count >= limit:
        await query.edit_message_text(t("limit_reached", lang, limit=limit), parse_mode="HTML")
        return ConversationHandler.END
    kb = [[InlineKeyboardButton(t("btn_cancel", lang), callback_data="upload_cancel")]]
    await query.edit_message_text(t("send_file", lang), reply_markup=InlineKeyboardMarkup(kb))
    # FIX: return ASK_FILE (not ASK_NAME) so the next message (the actual file) is caught
    return ASK_FILE

async def receive_file(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Receives the actual file — works as both an entry_point (direct send)
    and as a state handler for ASK_FILE (after clicking Upload button)."""
    user = update.effective_user
    lang = get_lang(user.id)
    if not is_authed(user.id):
        await update.message.reply_text(t("not_authed", lang))
        return ConversationHandler.END
    count = count_user_files(user.id)
    limit = get_file_limit(user.id)
    if count >= limit:
        await update.message.reply_text(t("limit_reached", lang, limit=limit), parse_mode="HTML")
        return ConversationHandler.END
    msg = update.message
    if msg.document:      orig, ftype = msg.document.file_name or "file", "document"
    elif msg.video:       orig, ftype = msg.video.file_name or "video.mp4", "video"
    elif msg.audio:       orig, ftype = msg.audio.file_name or "audio.mp3", "audio"
    elif msg.photo:       orig, ftype = "photo.jpg", "photo"
    elif msg.voice:       orig, ftype = "voice.ogg", "voice"
    elif msg.video_note:  orig, ftype = "videonote.mp4", "video_note"
    elif msg.sticker:     orig, ftype = "sticker", "sticker"
    else:
        return ConversationHandler.END
    ctx.user_data["upload"] = {"message": msg, "original_name": orig, "file_type": ftype}
    kb = [[InlineKeyboardButton(t("btn_cancel", lang), callback_data="upload_cancel")]]
    await msg.reply_text(
        t("ask_file_name", lang), reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML"
    )
    return ASK_NAME

async def receive_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user   = update.effective_user
    lang   = get_lang(user.id)
    text   = update.message.text.strip()
    upload = ctx.user_data.get("upload", {})
    upload["custom_name"] = upload.get("original_name", "file") if text == "/skip" else text
    ctx.user_data["upload"] = upload
    await update.message.reply_text(
        t("ask_folder", lang), reply_markup=folder_kb(lang, get_folders(user.id))
    )
    return ASK_FOLDER

async def handle_folder_choice(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query  = update.callback_query
    await query.answer()
    user   = query.from_user
    lang   = get_lang(user.id)
    data   = query.data
    upload = ctx.user_data.get("upload", {})
    if data == "folder_new":
        kb = [[InlineKeyboardButton(t("btn_cancel", lang), callback_data="upload_cancel")]]
        await query.edit_message_text(
            t("ask_new_folder_name", lang), reply_markup=InlineKeyboardMarkup(kb)
        )
        return ASK_NEW_FOLDER_NAME
    elif data == "folder_none":
        upload["folder_id"] = None
        upload["folder_name"] = "—"
    elif data.startswith("folder_"):
        fid = int(data.replace("folder_", ""))
        f   = get_folder(fid)
        upload["folder_id"]   = fid
        upload["folder_name"] = f"{f['emoji']} {f['name']}" if f else "—"
    ctx.user_data["upload"] = upload
    kb = [[InlineKeyboardButton(t("btn_cancel", lang), callback_data="upload_cancel")]]
    await query.edit_message_text(
        t("ask_description", lang), reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML"
    )
    return ASK_DESC

async def receive_new_folder_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = get_lang(user.id)
    name = update.message.text.strip()
    if not create_folder(user.id, name):
        await update.message.reply_text(t("folder_exists", lang))
        return ASK_NEW_FOLDER_NAME
    await update.message.reply_text(t("folder_created", lang, name=name))
    await update.message.reply_text(
        t("ask_folder", lang), reply_markup=folder_kb(lang, get_folders(user.id))
    )
    return ASK_FOLDER

async def receive_description(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user   = update.effective_user
    lang   = get_lang(user.id)
    text   = update.message.text.strip()
    upload = ctx.user_data.get("upload", {})
    upload["description"] = "" if text == "/skip" else text
    ctx.user_data["upload"] = upload
    kb = [[InlineKeyboardButton(t("btn_cancel", lang), callback_data="upload_cancel")]]
    await update.message.reply_text(
        t("ask_tags", lang), reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML"
    )
    return ASK_TAGS

async def receive_tags(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user   = update.effective_user
    lang   = get_lang(user.id)
    text   = update.message.text.strip()
    upload = ctx.user_data.get("upload", {})
    upload["tags"] = "" if text == "/skip" else text
    ctx.user_data["upload"] = upload
    await update.message.reply_text(t("uploading", lang))
    await do_upload(update, ctx)
    return ConversationHandler.END

async def do_upload(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user     = update.effective_user
    lang     = get_lang(user.id)
    upload   = ctx.user_data.get("upload", {})
    orig_msg = upload["message"]
    now      = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    caption  = (
        f"👤 <b>{user.first_name or ''}</b> (@{user.username or 'N/A'}) | <code>{user.id}</code>\n"
        f"📁 {upload.get('custom_name', '')}\n"
        f"📂 {upload.get('folder_name', '—')}\n"
        f"📝 {upload.get('description', '—') or '—'}\n"
        f"🏷️ {upload.get('tags', '—') or '—'}\n"
        f"📅 {now}"
    )
    try:
        sent = await ctx.bot.copy_message(
            chat_id=STORAGE_CHANNEL, from_chat_id=orig_msg.chat_id,message_id = orig_msg.message_id ,caption=caption, parse_mode="HTML"
        )
        channel_msg_id = sent.message_id
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {e}")
        return

    code = save_file(
        user.id, upload.get("custom_name", ""), upload.get("folder_id"),
        upload.get("description", ""), upload.get("tags", ""),
        upload.get("file_type", ""), channel_msg_id
    )
    ctx.user_data.pop("upload", None)
    from handlers.auth import main_menu_kb
    await update.message.reply_text(
        t("upload_done", lang, code=code, name=upload.get("custom_name", ""),
          folder=upload.get("folder_name", "—"), tags=upload.get("tags", "—") or "—"),
        reply_markup=main_menu_kb(lang, is_admin=(user.id == ADMIN_ID)), parse_mode="HTML"
    )

async def upload_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    ctx.user_data.pop("upload", None)
    from handlers.auth import show_main_menu
    await show_main_menu(update, ctx)
    return ConversationHandler.END
