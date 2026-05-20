"""
Admin Panel — Full
"""
import time
from datetime import datetime, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from utils.db import (get_lang, get_stats, get_all_users, get_user,
                      upsert_user, add_file_quota, get_all_user_ids,
                      get_user_logs, get_recent_logs, search_all_files,
                      get_all_purchases, add_log, set_setting, get_setting,
                      admin_delete_file, get_file_by_id_admin)
from config import ADMIN_ID

ADMIN_BROADCAST   = 40
ADMIN_MSG_USER    = 41
ADMIN_SET_LIMIT   = 42
ADMIN_SET_PWD     = 43
ADMIN_SEARCH_FILE = 44
ADMIN_ADD_QUOTA   = 45

def fmt(ts): return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")

def is_admin(uid): return uid == ADMIN_ID

def admin_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 مدیریت کاربران",    callback_data="adm_users"),
         InlineKeyboardButton("📊 آمار کلی",          callback_data="adm_stats")],
        [InlineKeyboardButton("📢 Broadcast",          callback_data="adm_broadcast"),
         InlineKeyboardButton("📋 لاگ‌های اخیر",      callback_data="adm_logs")],
        [InlineKeyboardButton("🔍 جستجو در همه فایل‌ها", callback_data="adm_search_files"),
         InlineKeyboardButton("💰 خریدها",             callback_data="adm_purchases")],
        [InlineKeyboardButton("⚙️ تنظیمات بات",       callback_data="adm_bot_settings"),
         InlineKeyboardButton("📊 گزارش روزانه",       callback_data="adm_daily_report")],
        [InlineKeyboardButton("🔙 بازگشت",             callback_data="menu_back")],
    ])

# ─── Main panel ─────────────────────────────
async def admin_panel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id): return
    s = get_stats()
    await query.edit_message_text(
        f"👑 <b>Admin Panel</b>\n\n"
        f"👥 کل کاربران: <b>{s['users']}</b>\n"
        f"📁 کل فایل‌ها: <b>{s['files']}</b>\n"
        f"⭐ VIP: <b>{s['vip']}</b>\n"
        f"🚫 بلاک: <b>{s['blocked']}</b>\n"
        f"🆕 کاربر امروز: <b>{s['new_users']}</b>\n"
        f"📤 آپلود امروز: <b>{s['new_files']}</b>",
        reply_markup=admin_kb(), parse_mode="HTML"
    )

# ─── Stats ──────────────────────────────────
async def adm_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id): return
    s = get_stats()
    kb = [[InlineKeyboardButton("🔙 بازگشت", callback_data="menu_admin")]]
    await query.edit_message_text(
        f"📊 <b>آمار کامل</b>\n\n"
        f"👥 کل کاربران: <b>{s['users']}</b>\n"
        f"📁 کل فایل‌ها: <b>{s['files']}</b>\n"
        f"⭐ VIP: <b>{s['vip']}</b>\n"
        f"🚫 بلاک‌شده: <b>{s['blocked']}</b>\n"
        f"🆕 کاربر جدید امروز: <b>{s['new_users']}</b>\n"
        f"📤 آپلود امروز: <b>{s['new_files']}</b>",
        reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML"
    )

# ─── Users list ─────────────────────────────
async def adm_users(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id): return
    users = get_all_users()
    kb = []
    for u in users[:20]:
        name = u["first_name"] or u["username"] or str(u["user_id"])
        badge = "👑" if u["is_admin"] else ("⭐" if u["is_vip"] else ("🚫" if u["is_blocked"] else "👤"))
        kb.append([InlineKeyboardButton(f"{badge} {name}", callback_data=f"adm_user_{u['user_id']}")])
    kb.append([InlineKeyboardButton("🔙 بازگشت", callback_data="menu_admin")])
    await query.edit_message_text(
        f"👥 <b>کاربران ({len(users)})</b>",
        reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML"
    )

async def adm_user_detail(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id): return
    uid = int(query.data.replace("adm_user_",""))
    u   = get_user(uid)
    if not u: return
    from utils.db import count_user_files
    fcount = count_user_files(uid)
    name   = u["first_name"] or u["username"] or str(uid)
    status = "👑 ادمین" if u["is_admin"] else ("⭐ VIP" if u["is_vip"] else ("🚫 بلاک" if u["is_blocked"] else "👤 عادی"))
    text = (
        f"👤 <b>{name}</b>\n"
        f"🆔 <code>{uid}</code>\n"
        f"📛 @{u['username'] or 'N/A'}\n"
        f"📊 وضعیت: {status}\n"
        f"📁 فایل‌ها: {fcount}/{u['file_limit']}\n"
        f"🌐 زبان: {u['lang']}\n"
        f"📅 عضویت: {fmt(u['added_at'])}"
    )
    kb = [
        [InlineKeyboardButton("➕ اضافه کردن فضا",   callback_data=f"adm_quota_{uid}"),
         InlineKeyboardButton("📋 لاگ کاربر",        callback_data=f"adm_ulog_{uid}")],
        [InlineKeyboardButton("💬 ارسال پیام",        callback_data=f"adm_msg_{uid}"),
         InlineKeyboardButton("🔍 فایل‌های کاربر",   callback_data=f"adm_ufiles_{uid}")],
    ]
    if u["is_blocked"]:
        kb.append([InlineKeyboardButton("✅ آنبلاک",  callback_data=f"adm_unblock_{uid}")])
    else:
        kb.append([InlineKeyboardButton("🚫 بلاک",   callback_data=f"adm_block_{uid}")])
    if u["is_vip"]:
        kb.append([InlineKeyboardButton("❌ حذف VIP", callback_data=f"adm_unvip_{uid}")])
    else:
        kb.append([InlineKeyboardButton("⭐ VIP کردن", callback_data=f"adm_vip_{uid}")])
    kb.append([InlineKeyboardButton("🗑️ حذف کاربر", callback_data=f"adm_deluser_{uid}")])
    kb.append([InlineKeyboardButton("🔙 بازگشت",     callback_data="adm_users")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

async def adm_block(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id): return
    uid = int(query.data.replace("adm_block_",""))
    upsert_user(uid, is_blocked=True)
    add_log(ADMIN_ID, "block_user", str(uid))
    await query.answer("🚫 کاربر بلاک شد", show_alert=True)
    ctx.args = [str(uid)]
    await adm_user_detail(update, ctx)

async def adm_unblock(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id): return
    uid = int(query.data.replace("adm_unblock_",""))
    upsert_user(uid, is_blocked=False)
    add_log(ADMIN_ID, "unblock_user", str(uid))
    await query.answer("✅ کاربر آنبلاک شد", show_alert=True)
    ctx.args = [str(uid)]
    await adm_user_detail(update, ctx)

async def adm_vip(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id): return
    uid = int(query.data.replace("adm_vip_",""))
    upsert_user(uid, is_vip=True)
    add_log(ADMIN_ID, "set_vip", str(uid))
    await query.answer("⭐ VIP شد", show_alert=True)
    ctx.args = [str(uid)]
    await adm_user_detail(update, ctx)

async def adm_unvip(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id): return
    uid = int(query.data.replace("adm_unvip_",""))
    upsert_user(uid, is_vip=False)
    add_log(ADMIN_ID, "remove_vip", str(uid))
    await query.answer("❌ VIP حذف شد", show_alert=True)
    ctx.args = [str(uid)]
    await adm_user_detail(update, ctx)

async def adm_deluser(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id): return
    uid = int(query.data.replace("adm_deluser_",""))
    import sqlite3
    conn = __import__("utils.db", fromlist=["get_conn"]).get_conn()
    conn.execute("UPDATE files SET deleted=1 WHERE user_id=?", (uid,))
    conn.execute("DELETE FROM users WHERE user_id=?", (uid,))
    conn.commit(); conn.close()
    add_log(ADMIN_ID, "delete_user", str(uid))
    await query.answer("🗑️ کاربر حذف شد", show_alert=True)
    await adm_users(update, ctx)

async def adm_ulog(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id): return
    uid  = int(query.data.replace("adm_ulog_",""))
    logs = get_user_logs(uid, 20)
    u    = get_user(uid)
    name = (u["first_name"] or u["username"] or str(uid)) if u else str(uid)
    if not logs:
        text = f"📋 لاگ <b>{name}</b>:\n\nهیچ فعالیتی ثبت نشده."
    else:
        lines = [f"📋 لاگ <b>{name}</b>:\n"]
        for l in logs:
            lines.append(f"• {fmt(l['created_at'])} | {l['action']} | {l['detail']}")
        text = "\n".join(lines)
    kb = [[InlineKeyboardButton("🔙 بازگشت", callback_data=f"adm_user_{uid}")]]
    await query.edit_message_text(text[:4000], reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

async def adm_ufiles(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id): return
    uid = int(query.data.replace("adm_ufiles_",""))
    from utils.db import get_files_by_folder, get_folders
    from datetime import datetime, timezone
    all_files = []
    for f in get_folders(uid):
        all_files.extend(get_files_by_folder(uid, f["id"]))
    all_files.extend(get_files_by_folder(uid, None))
    if not all_files:
        kb = [[InlineKeyboardButton("🔙", callback_data=f"adm_user_{uid}")]]
        await query.edit_message_text("📭 هیچ فایلی ندارد.", reply_markup=InlineKeyboardMarkup(kb))
        return
    kb = []
    for file in all_files[:15]:
        kb.append([
            InlineKeyboardButton(f"📄 {file['custom_name'][:25]}", callback_data="noop"),
            InlineKeyboardButton("🗑️", callback_data=f"adm_delf_{file['id']}"),
        ])
    kb.append([InlineKeyboardButton("🔙 بازگشت", callback_data=f"adm_user_{uid}")])
    await query.edit_message_text(f"📁 فایل‌های کاربر ({len(all_files)}):",
                                   reply_markup=InlineKeyboardMarkup(kb))

async def adm_delf(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id): return
    fid = int(query.data.replace("adm_delf_",""))
    admin_delete_file(fid)
    add_log(ADMIN_ID, "admin_delete_file", str(fid))
    await query.answer("🗑️ فایل حذف شد", show_alert=True)

# ─── Add quota ──────────────────────────────
async def adm_quota_ask(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id): return
    uid = int(query.data.replace("adm_quota_",""))
    ctx.user_data["quota_uid"] = uid
    kb = [[InlineKeyboardButton("🔙 انصراف", callback_data=f"adm_user_{uid}")]]
    await query.edit_message_text(
        f"➕ چند فایل به کاربر <code>{uid}</code> اضافه کنم؟\n\n(عدد بنویس)",
        reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML"
    )
    return ADMIN_ADD_QUOTA

async def adm_quota_recv(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return ConversationHandler.END
    text = update.message.text.strip()
    uid  = ctx.user_data.get("quota_uid")
    try:
        amount = int(text)
        add_file_quota(uid, amount)
        add_log(ADMIN_ID, "add_quota", f"{uid} +{amount}")
        await update.message.reply_text(f"✅ {amount} فایل به کاربر {uid} اضافه شد.")
    except:
        await update.message.reply_text("❌ عدد معتبر وارد کن.")
    return ConversationHandler.END

# ─── Message to user ────────────────────────
async def adm_msg_ask(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id): return
    uid = int(query.data.replace("adm_msg_",""))
    ctx.user_data["msg_uid"] = uid
    kb = [[InlineKeyboardButton("🔙 انصراف", callback_data=f"adm_user_{uid}")]]
    await query.edit_message_text(
        f"💬 پیام خود را برای کاربر <code>{uid}</code> بنویس:",
        reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML"
    )
    return ADMIN_MSG_USER

async def adm_msg_recv(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return ConversationHandler.END
    uid = ctx.user_data.get("msg_uid")
    try:
        await update.message.bot.send_message(chat_id=uid, text=f"📨 <b>پیام از ادمین:</b>\n\n{update.message.text}", parse_mode="HTML")
        await update.message.reply_text("✅ پیام ارسال شد.")
        add_log(ADMIN_ID, "msg_user", str(uid))
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {e}")
    return ConversationHandler.END

# ─── Broadcast ──────────────────────────────
async def adm_broadcast_ask(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id): return
    kb = [[InlineKeyboardButton("🔙 انصراف", callback_data="menu_admin")]]
    await query.edit_message_text("📢 متن پیام broadcast را بنویس:", reply_markup=InlineKeyboardMarkup(kb))
    return ADMIN_BROADCAST

async def adm_broadcast_recv(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return ConversationHandler.END
    text  = update.message.text
    users = get_all_user_ids()
    sent  = 0; fail = 0
    await update.message.reply_text(f"📢 در حال ارسال به {len(users)} نفر...")
    for uid in users:
        try:
            await update.message.bot.send_message(chat_id=uid, text=f"📢 <b>اطلاعیه:</b>\n\n{text}", parse_mode="HTML")
            sent += 1
        except: fail += 1
    add_log(ADMIN_ID, "broadcast", f"sent={sent} fail={fail}")
    await update.message.reply_text(f"✅ ارسال شد: {sent}\n❌ خطا: {fail}")
    return ConversationHandler.END

# ─── Logs ───────────────────────────────────
async def adm_logs(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id): return
    logs = get_recent_logs(30)
    if not logs:
        kb = [[InlineKeyboardButton("🔙", callback_data="menu_admin")]]
        await query.edit_message_text("📭 لاگی وجود ندارد.", reply_markup=InlineKeyboardMarkup(kb))
        return
    lines = ["📋 <b>لاگ‌های اخیر:</b>\n"]
    for l in logs:
        uname = l.get("username") or str(l["user_id"])
        lines.append(f"• {fmt(l['created_at'])} | @{uname} | {l['action']} | {l['detail']}")
    kb = [[InlineKeyboardButton("🔙 بازگشت", callback_data="menu_admin")]]
    await query.edit_message_text("\n".join(lines)[:4000], reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

# ─── Search all files ───────────────────────
async def adm_search_ask(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id): return
    kb = [[InlineKeyboardButton("🔙 انصراف", callback_data="menu_admin")]]
    await query.edit_message_text("🔍 نام یا کد یا تگ فایل را بنویس:", reply_markup=InlineKeyboardMarkup(kb))
    return ADMIN_SEARCH_FILE

async def adm_search_recv(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return ConversationHandler.END
    q = update.message.text.strip()
    results = search_all_files(q)
    if not results:
        await update.message.reply_text("❌ نتیجه‌ای یافت نشد.")
        return ConversationHandler.END
    await update.message.reply_text(f"🔍 {len(results)} فایل پیدا شد:")
    for f in results:
        uname = f.get("username") or str(f["user_id"])
        text  = (f"📄 <b>{f['custom_name']}</b>\n"
                 f"👤 @{uname} | <code>{f['user_id']}</code>\n"
                 f"📌 <code>{f['unique_code']}</code>\n"
                 f"📅 {fmt(f['uploaded_at'])}")
        kb = [[InlineKeyboardButton("🗑️ حذف", callback_data=f"adm_delf_{f['id']}")]]
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
    return ConversationHandler.END

# ─── Purchases ──────────────────────────────
async def adm_purchases(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id): return
    purchases = get_all_purchases()
    if not purchases:
        kb = [[InlineKeyboardButton("🔙", callback_data="menu_admin")]]
        await query.edit_message_text("📭 هیچ خریدی ثبت نشده.", reply_markup=InlineKeyboardMarkup(kb))
        return
    lines = ["💰 <b>خریدهای اخیر:</b>\n"]
    for p in purchases[:20]:
        uname = p.get("username") or str(p["user_id"])
        lines.append(f"• @{uname} | ${p['amount_usd']} | +{p['files_added']} فایل | {fmt(p['created_at'])}")
    kb = [[InlineKeyboardButton("🔙 بازگشت", callback_data="menu_admin")]]
    await query.edit_message_text("\n".join(lines)[:4000], reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

# ─── Bot settings ───────────────────────────
async def adm_bot_settings(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id): return
    pwd   = get_setting("bot_password") or "(بدون رمز)"
    limit = get_setting("free_limit") or "50"
    kb = [
        [InlineKeyboardButton("🔑 تغییر رمز بات",       callback_data="adm_setpwd")],
        [InlineKeyboardButton("📊 تغییر محدودیت پیش‌فرض", callback_data="adm_setlimit")],
        [InlineKeyboardButton("🔙 بازگشت",               callback_data="menu_admin")],
    ]
    await query.edit_message_text(
        f"⚙️ <b>تنظیمات بات</b>\n\n🔑 رمز: <code>{pwd}</code>\n📊 محدودیت پیش‌فرض: <b>{limit}</b> فایل",
        reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML"
    )

async def adm_setpwd_ask(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id): return
    kb = [[InlineKeyboardButton("🔙 انصراف", callback_data="adm_bot_settings")]]
    await query.edit_message_text("🔑 رمز جدید را بنویس:\n(برای حذف رمز، /clear بنویس)", reply_markup=InlineKeyboardMarkup(kb))
    return ADMIN_SET_PWD

async def adm_setpwd_recv(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return ConversationHandler.END
    text = update.message.text.strip()
    new_pwd = "" if text == "/clear" else text
    set_setting("bot_password", new_pwd)
    add_log(ADMIN_ID, "change_password", "")
    msg = "✅ رمز حذف شد." if not new_pwd else "✅ رمز تغییر کرد."
    await update.message.reply_text(msg)
    return ConversationHandler.END

async def adm_setlimit_ask(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id): return
    kb = [[InlineKeyboardButton("🔙 انصراف", callback_data="adm_bot_settings")]]
    await query.edit_message_text("📊 محدودیت پیش‌فرض جدید (عدد):", reply_markup=InlineKeyboardMarkup(kb))
    return ADMIN_SET_LIMIT

async def adm_setlimit_recv(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return ConversationHandler.END
    try:
        limit = int(update.message.text.strip())
        set_setting("free_limit", str(limit))
        add_log(ADMIN_ID, "set_free_limit", str(limit))
        await update.message.reply_text(f"✅ محدودیت پیش‌فرض به {limit} تغییر کرد.")
    except:
        await update.message.reply_text("❌ عدد معتبر وارد کن.")
    return ConversationHandler.END

# ─── Daily report ───────────────────────────
async def adm_daily_report(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id): return
    s = get_stats()
    kb = [[InlineKeyboardButton("🔙 بازگشت", callback_data="menu_admin")]]
    await query.edit_message_text(
        f"📊 <b>گزارش امروز</b>\n\n"
        f"🆕 کاربر جدید: <b>{s['new_users']}</b>\n"
        f"📤 فایل آپلود شده: <b>{s['new_files']}</b>\n"
        f"👥 کل کاربران: <b>{s['users']}</b>\n"
        f"📁 کل فایل‌ها: <b>{s['files']}</b>\n"
        f"⭐ VIP: <b>{s['vip']}</b>\n"
        f"🚫 بلاک: <b>{s['blocked']}</b>",
        reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML"
    )

# ─── Commands ───────────────────────────────
async def cmd_adduser(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    args = ctx.args
    if not args or not args[0].isdigit():
        await update.message.reply_text("Usage: /adduser <user_id>"); return
    upsert_user(int(args[0]), authed=True)
    await update.message.reply_text(f"✅ کاربر {args[0]} اضافه شد.")

async def cmd_addquota(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    args = ctx.args
    if not args or len(args) < 2:
        await update.message.reply_text("Usage: /addquota <user_id> <amount>"); return
    try:
        add_file_quota(int(args[0]), int(args[1]))
        await update.message.reply_text(f"✅ {args[1]} فایل به {args[0]} اضافه شد.")
    except Exception as e:
        await update.message.reply_text(f"❌ {e}")
