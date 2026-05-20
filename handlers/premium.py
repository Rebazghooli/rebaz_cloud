from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from utils.db import get_lang, count_user_files, get_file_limit, get_user, get_folders, delete_folder, upsert_user
from locales.strings import t
from config import ADMIN_ID, NOWPAYMENTS_KEY, PREMIUM_PER_PACK, PREMIUM_PRICE_USD

async def premium_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
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
    await query.edit_message_text(t("premium_info", lang, count=count, limit=lim),
                                   reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

async def premium_buy(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user  = query.from_user
    lang  = get_lang(user.id)
    if not NOWPAYMENTS_KEY:
        kb = [[InlineKeyboardButton(t("btn_back", lang), callback_data="menu_premium")]]
        await query.edit_message_text(
            "⚠️ درگاه پرداخت هنوز راه‌اندازی نشده.\nبرای خرید با ادمین تماس بگیرید.",
            reply_markup=InlineKeyboardMarkup(kb)
        )
        return
    import time
    ref = f"rc_{user.id}_{int(time.time())}"
    pay_url = f"https://nowpayments.io/payment/?iid={NOWPAYMENTS_KEY}&amount={PREMIUM_PRICE_USD}&currency=usd&order_id={ref}"
    kb = [
        [InlineKeyboardButton("💳 پرداخت", url=pay_url)],
        [InlineKeyboardButton(t("btn_back", lang), callback_data="menu_premium")],
    ]
    await query.edit_message_text(
        f"💎 <b>{PREMIUM_PER_PACK} فایل اضافه</b> = <b>${PREMIUM_PRICE_USD}</b>\n\nبعد از پرداخت رسید را به ادمین بده.",
        reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML"
    )

async def settings_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user  = query.from_user
    lang  = get_lang(user.id)
    kb = [
        [InlineKeyboardButton(t("btn_change_lang",    lang), callback_data="s_lang")],
        [InlineKeyboardButton(t("btn_manage_folders", lang), callback_data="s_folders")],
        [InlineKeyboardButton(t("btn_back",           lang), callback_data="menu_back")],
    ]
    await query.edit_message_text(t("settings_menu", lang), reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

async def settings_lang(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    kb = [[
        InlineKeyboardButton("🇮🇷 فارسی",   callback_data="cl_fa"),
        InlineKeyboardButton("🏳️ کوردی",   callback_data="cl_ku"),
        InlineKeyboardButton("🇬🇧 English", callback_data="cl_en"),
    ]]
    await query.edit_message_text("زبان را انتخاب کن:", reply_markup=InlineKeyboardMarkup(kb))

async def change_lang(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user  = query.from_user
    lang  = query.data.replace("cl_","")
    upsert_user(user.id, lang=lang)
    from handlers.auth import show_main_menu
    await show_main_menu(update, ctx)

async def manage_folders(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user  = query.from_user
    lang  = get_lang(user.id)
    folders = get_folders(user.id)
    if not folders:
        kb = [[InlineKeyboardButton(t("btn_back", lang), callback_data="menu_settings")]]
        await query.edit_message_text("📭 فولدری ندارید.", reply_markup=InlineKeyboardMarkup(kb))
        return
    kb = []
    for f in folders:
        kb.append([
            InlineKeyboardButton(f"{f['emoji']} {f['name']}", callback_data="noop"),
            InlineKeyboardButton("🗑️", callback_data=f"df_{f['id']}"),
        ])
    kb.append([InlineKeyboardButton(t("btn_back", lang), callback_data="menu_settings")])
    await query.edit_message_text("📂 فولدرهای شما:", reply_markup=InlineKeyboardMarkup(kb))

async def del_folder_cb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user  = query.from_user
    fid   = int(query.data.replace("df_",""))
    delete_folder(fid, user.id)
    await manage_folders(update, ctx)
