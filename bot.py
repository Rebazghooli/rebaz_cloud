import asyncio
import logging
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, filters
)
from config import BOT_TOKEN
from utils.db import init_db

# ── Handlers ────────────────────────────────────────────────────────────────
from handlers.auth import (
    start, handle_set_language, handle_password,
    show_main_menu, show_user_stats,
    ASK_PASSWORD, ASK_LANGUAGE,
)
from handlers.upload import (
    upload_start, receive_file, receive_name,
    handle_folder_choice, receive_new_folder_name,
    receive_description, receive_tags, upload_cancel,
    ASK_FILE, ASK_NAME, ASK_FOLDER, ASK_NEW_FOLDER_NAME, ASK_DESC, ASK_TAGS,
)
from handlers.files import (
    my_files, browse_folder, get_file_cb, share_toggle_cb,
    del_ask, del_confirm, edit_menu, edit_ask, edit_text,
    edit_folder_cb, search_start, search_recv,
    EDIT_WAIT_NAME, EDIT_WAIT_DESC, EDIT_WAIT_TAGS, EDIT_WAIT_FOLDER, SEARCH_WAIT,
)
from handlers.settings import (
    show_settings, change_lang, set_lang,
    manage_folders, del_folder_ask, del_folder_confirm,
)
from handlers.premium import (
    show_premium, buy_premium,
    adm_pending_purchases, adm_confirm_pay,
)
from handlers.admin import (
    admin_panel, adm_stats, adm_users, adm_user_detail,
    adm_block, adm_unblock, adm_vip, adm_unvip, adm_deluser,
    adm_ulog, adm_ufiles, adm_delf,
    adm_quota_ask, adm_quota_recv,
    adm_msg_ask, adm_msg_recv,
    adm_broadcast_ask, adm_broadcast_recv,
    adm_logs, adm_search_ask, adm_search_recv,
    adm_purchases, adm_bot_settings,
    adm_setpwd_ask, adm_setpwd_recv,
    adm_setlimit_ask, adm_setlimit_recv,
    adm_daily_report,
    cmd_adduser, cmd_addquota,
    ADMIN_BROADCAST, ADMIN_MSG_USER, ADMIN_SET_LIMIT, ADMIN_SET_PWD,
    ADMIN_SEARCH_FILE, ADMIN_ADD_QUOTA,
)

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def build_app() -> Application:
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    # ── Auth ConversationHandler ─────────────────────────────────────────────
    auth_conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_LANGUAGE: [CallbackQueryHandler(handle_set_language, pattern="^setlang_")],
            ASK_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_password)],
        },
        fallbacks=[CommandHandler("start", start)],
        name="auth_conv",
        persistent=False,
    )

    # ── Upload ConversationHandler ───────────────────────────────────────────
    upload_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(upload_start, pattern="^menu_upload$"),
            # Also allow direct file sends (when user sends a file without clicking Upload)
            MessageHandler(
                (filters.Document.ALL | filters.PHOTO | filters.VIDEO |
                 filters.AUDIO | filters.VOICE | filters.VIDEO_NOTE | filters.Sticker.ALL)
                & ~filters.COMMAND,
                receive_file,
            ),
        ],
        states={
            # FIX: ASK_FILE state receives the actual file
            ASK_FILE: [
                MessageHandler(
                    (filters.Document.ALL | filters.PHOTO | filters.VIDEO |
                     filters.AUDIO | filters.VOICE | filters.VIDEO_NOTE | filters.Sticker.ALL)
                    & ~filters.COMMAND,
                    receive_file,
                ),
                CallbackQueryHandler(upload_cancel, pattern="^upload_cancel$"),
            ],
            ASK_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_name),
                CommandHandler("skip", receive_name),
                CallbackQueryHandler(upload_cancel, pattern="^upload_cancel$"),
            ],
            ASK_FOLDER: [
                CallbackQueryHandler(handle_folder_choice, pattern="^folder_"),
                CallbackQueryHandler(upload_cancel,        pattern="^upload_cancel$"),
            ],
            ASK_NEW_FOLDER_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_new_folder_name),
                CallbackQueryHandler(upload_cancel, pattern="^upload_cancel$"),
            ],
            ASK_DESC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_description),
                CommandHandler("skip", receive_description),
                CallbackQueryHandler(upload_cancel, pattern="^upload_cancel$"),
            ],
            ASK_TAGS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_tags),
                CommandHandler("skip", receive_tags),
                CallbackQueryHandler(upload_cancel, pattern="^upload_cancel$"),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(upload_cancel, pattern="^upload_cancel$"),
            CallbackQueryHandler(show_main_menu, pattern="^menu_back$"),
        ],
        name="upload_conv",
        persistent=False,
    )

    # ── Edit ConversationHandler ─────────────────────────────────────────────
    edit_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(edit_ask, pattern="^ef_")],
        states={
            EDIT_WAIT_NAME:   [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_text)],
            EDIT_WAIT_DESC:   [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_text)],
            EDIT_WAIT_TAGS:   [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_text)],
            EDIT_WAIT_FOLDER: [CallbackQueryHandler(edit_folder_cb, pattern="^folder_")],
        },
        fallbacks=[CallbackQueryHandler(show_main_menu, pattern="^menu_back$")],
        name="edit_conv",
        persistent=False,
    )

    # ── Search ConversationHandler ───────────────────────────────────────────
    search_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(search_start, pattern="^menu_search$")],
        states={
            SEARCH_WAIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_recv)],
        },
        fallbacks=[CallbackQueryHandler(show_main_menu, pattern="^menu_back$")],
        name="search_conv",
        persistent=False,
    )

    # ── Admin ConversationHandlers ───────────────────────────────────────────
    admin_broadcast_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(adm_broadcast_ask, pattern="^adm_broadcast$")],
        states={ADMIN_BROADCAST: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_broadcast_recv)]},
        fallbacks=[CallbackQueryHandler(admin_panel, pattern="^menu_admin$")],
        name="broadcast_conv", persistent=False,
    )
    admin_msg_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(adm_msg_ask, pattern=r"^adm_msg_\d+$")],
        states={ADMIN_MSG_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_msg_recv)]},
        fallbacks=[CallbackQueryHandler(admin_panel, pattern="^menu_admin$")],
        name="admin_msg_conv", persistent=False,
    )
    admin_quota_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(adm_quota_ask, pattern=r"^adm_quota_\d+$")],
        states={ADMIN_ADD_QUOTA: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_quota_recv)]},
        fallbacks=[CallbackQueryHandler(admin_panel, pattern="^menu_admin$")],
        name="admin_quota_conv", persistent=False,
    )
    admin_search_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(adm_search_ask, pattern="^adm_search_files$")],
        states={ADMIN_SEARCH_FILE: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_search_recv)]},
        fallbacks=[CallbackQueryHandler(admin_panel, pattern="^menu_admin$")],
        name="admin_search_conv", persistent=False,
    )
    admin_setpwd_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(adm_setpwd_ask, pattern="^adm_setpwd$")],
        states={ADMIN_SET_PWD: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_setpwd_recv)]},
        fallbacks=[CallbackQueryHandler(adm_bot_settings, pattern="^adm_bot_settings$")],
        name="admin_setpwd_conv", persistent=False,
    )
    admin_setlimit_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(adm_setlimit_ask, pattern="^adm_setlimit$")],
        states={ADMIN_SET_LIMIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_setlimit_recv)]},
        fallbacks=[CallbackQueryHandler(adm_bot_settings, pattern="^adm_bot_settings$")],
        name="admin_setlimit_conv", persistent=False,
    )

    # ── Register all handlers (order matters!) ───────────────────────────────
    for conv in [
        auth_conv, upload_conv, edit_conv, search_conv,
        admin_broadcast_conv, admin_msg_conv, admin_quota_conv,
        admin_search_conv, admin_setpwd_conv, admin_setlimit_conv,
    ]:
        app.add_handler(conv)

    # Admin commands
    app.add_handler(CommandHandler("adduser",  cmd_adduser))
    app.add_handler(CommandHandler("addquota", cmd_addquota))

    # ── Callback query handlers ──────────────────────────────────────────────
    cbs = [
        ("^menu_back$",                show_main_menu),
        ("^menu_files$",               my_files),
        ("^menu_premium$",             show_premium),
        ("^menu_settings$",            show_settings),
        ("^menu_admin$",               admin_panel),
        ("^menu_stats$",               show_user_stats),
        (r"^browse_",                  browse_folder),
        (r"^get_\d+$",                 get_file_cb),
        (r"^share_\d+$",               share_toggle_cb),
        (r"^del_\d+$",                 del_ask),
        (r"^delok_\d+$",               del_confirm),
        (r"^edit_\d+$",                edit_menu),
        ("^premium_buy$",              buy_premium),
        ("^settings_lang$",            change_lang),
        (r"^chglang_",                 set_lang),
        ("^settings_folders$",         manage_folders),
        (r"^del_folder_\d+$",          del_folder_ask),
        (r"^del_folder_ok_\d+$",       del_folder_confirm),
        ("^adm_stats$",                adm_stats),
        ("^adm_users$",                adm_users),
        (r"^adm_user_\d+$",            adm_user_detail),
        (r"^adm_block_\d+$",           adm_block),
        (r"^adm_unblock_\d+$",         adm_unblock),
        (r"^adm_vip_\d+$",             adm_vip),
        (r"^adm_unvip_\d+$",           adm_unvip),
        (r"^adm_deluser_\d+$",         adm_deluser),
        (r"^adm_ulog_\d+$",            adm_ulog),
        (r"^adm_ufiles_\d+$",          adm_ufiles),
        (r"^adm_delf_\d+$",            adm_delf),
        ("^adm_logs$",                 adm_logs),
        ("^adm_purchases$",            adm_purchases),
        ("^adm_pending_pays$",         adm_pending_purchases),
        (r"^adm_confirm_pay_\d+$",     adm_confirm_pay),
        ("^adm_bot_settings$",         adm_bot_settings),
        ("^adm_daily_report$",         adm_daily_report),
        ("^noop$",                     lambda u, c: u.callback_query.answer()),
    ]
    for pattern, handler in cbs:
        app.add_handler(CallbackQueryHandler(handler, pattern=pattern))

    return app


def main():
    app = build_app()
    logger.info("🤖 RebazCloud bot started (polling)...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
