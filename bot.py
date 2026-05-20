import logging
from dotenv import load_dotenv
load_dotenv()

from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ConversationHandler, filters
)
from handlers.auth import start, handle_set_language, handle_password, show_main_menu, ASK_PASSWORD, ASK_LANGUAGE
from handlers.upload import (upload_start, receive_file, receive_name, handle_folder_choice,
    receive_new_folder_name, receive_description, receive_tags, upload_cancel,
    ASK_NAME, ASK_FOLDER, ASK_NEW_FOLDER_NAME, ASK_DESC, ASK_TAGS)
from handlers.files import (my_files, browse_folder, get_file_cb, del_ask, del_confirm,
    edit_menu, edit_ask, edit_text, edit_folder_cb, search_start, search_recv,
    EDIT_WAIT_NAME, EDIT_WAIT_DESC, EDIT_WAIT_TAGS, EDIT_WAIT_FOLDER, SEARCH_WAIT)
from handlers.premium import (premium_menu, premium_buy, settings_menu, settings_lang,
    change_lang, manage_folders, del_folder_cb)
from handlers.admin import (admin_panel, adm_stats, adm_users, adm_user_detail,
    adm_block, adm_unblock, adm_vip, adm_unvip, adm_deluser, adm_ulog, adm_ufiles,
    adm_delf, adm_quota_ask, adm_quota_recv, adm_msg_ask, adm_msg_recv,
    adm_broadcast_ask, adm_broadcast_recv, adm_logs, adm_search_ask, adm_search_recv,
    adm_purchases, adm_bot_settings, adm_setpwd_ask, adm_setpwd_recv,
    adm_setlimit_ask, adm_setlimit_recv, adm_daily_report,
    cmd_adduser, cmd_addquota,
    ADMIN_BROADCAST, ADMIN_MSG_USER, ADMIN_SET_LIMIT, ADMIN_SET_PWD,
    ADMIN_SEARCH_FILE, ADMIN_ADD_QUOTA)
from utils.db import init_db
from config import BOT_TOKEN

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO,
    handlers=[logging.FileHandler("rebazcloud.log"), logging.StreamHandler()])

def main():
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Auth
    auth_conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_LANGUAGE: [CallbackQueryHandler(handle_set_language, pattern="^setlang_")],
            ASK_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_password)],
        },
        fallbacks=[CommandHandler("start", start)], per_message=False,
    )

    # Upload
    upload_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(upload_start, pattern="^menu_upload$"),
            MessageHandler(filters.Document.ALL | filters.PHOTO | filters.VIDEO |
                           filters.AUDIO | filters.VOICE | filters.VIDEO_NOTE | filters.Sticker.ALL, receive_file),
        ],
        states={
            ASK_NAME:            [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_name),
                                  CommandHandler("skip", receive_name)],
            ASK_FOLDER:          [CallbackQueryHandler(handle_folder_choice, pattern="^folder_")],
            ASK_NEW_FOLDER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_new_folder_name)],
            ASK_DESC:            [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_description),
                                  CommandHandler("skip", receive_description)],
            ASK_TAGS:            [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_tags),
                                  CommandHandler("skip", receive_tags)],
        },
        fallbacks=[CallbackQueryHandler(upload_cancel, pattern="^upload_cancel$")], per_message=False,
    )

    # Edit
    edit_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(edit_ask, pattern="^ef_(name|desc|tags|folder)$")],
        states={
            EDIT_WAIT_NAME:   [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_text)],
            EDIT_WAIT_DESC:   [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_text)],
            EDIT_WAIT_TAGS:   [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_text)],
            EDIT_WAIT_FOLDER: [CallbackQueryHandler(edit_folder_cb, pattern="^folder_")],
        },
        fallbacks=[CallbackQueryHandler(my_files, pattern="^menu_files$")], per_message=False,
    )

    # Search
    search_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(search_start, pattern="^menu_search$")],
        states={SEARCH_WAIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_recv)]},
        fallbacks=[CallbackQueryHandler(show_main_menu, pattern="^menu_back$")], per_message=False,
    )

    # Admin conversations
    admin_broadcast_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(adm_broadcast_ask, pattern="^adm_broadcast$")],
        states={ADMIN_BROADCAST: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_broadcast_recv)]},
        fallbacks=[CallbackQueryHandler(admin_panel, pattern="^menu_admin$")], per_message=False,
    )
    admin_msg_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(adm_msg_ask, pattern="^adm_msg_")],
        states={ADMIN_MSG_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_msg_recv)]},
        fallbacks=[], per_message=False,
    )
    admin_quota_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(adm_quota_ask, pattern="^adm_quota_")],
        states={ADMIN_ADD_QUOTA: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_quota_recv)]},
        fallbacks=[], per_message=False,
    )
    admin_pwd_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(adm_setpwd_ask, pattern="^adm_setpwd$")],
        states={ADMIN_SET_PWD: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_setpwd_recv)]},
        fallbacks=[], per_message=False,
    )
    admin_limit_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(adm_setlimit_ask, pattern="^adm_setlimit$")],
        states={ADMIN_SET_LIMIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_setlimit_recv)]},
        fallbacks=[], per_message=False,
    )
    admin_search_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(adm_search_ask, pattern="^adm_search_files$")],
        states={ADMIN_SEARCH_FILE: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_search_recv)]},
        fallbacks=[], per_message=False,
    )

    for conv in [auth_conv, upload_conv, edit_conv, search_conv,
                 admin_broadcast_conv, admin_msg_conv, admin_quota_conv,
                 admin_pwd_conv, admin_limit_conv, admin_search_conv]:
        app.add_handler(conv)

    # Callbacks
    cbs = [
        ("^menu_back$",         show_main_menu),
        ("^menu_files$",        my_files),
        ("^browse_",            browse_folder),
        ("^get_",               get_file_cb),
        ("^del_",               del_ask),
        ("^delok_",             del_confirm),
        ("^edit_",              edit_menu),
        ("^menu_premium$",      premium_menu),
        ("^premium_buy$",       premium_buy),
        ("^menu_settings$",     settings_menu),
        ("^s_lang$",            settings_lang),
        ("^cl_",                change_lang),
        ("^s_folders$",         manage_folders),
        ("^df_",                del_folder_cb),
        ("^menu_admin$",        admin_panel),
        ("^adm_stats$",         adm_stats),
        ("^adm_users$",         adm_users),
        ("^adm_user_",          adm_user_detail),
        ("^adm_block_",         adm_block),
        ("^adm_unblock_",       adm_unblock),
        ("^adm_vip_",           adm_vip),
        ("^adm_unvip_",         adm_unvip),
        ("^adm_deluser_",       adm_deluser),
        ("^adm_ulog_",          adm_ulog),
        ("^adm_ufiles_",        adm_ufiles),
        ("^adm_delf_",          adm_delf),
        ("^adm_logs$",          adm_logs),
        ("^adm_purchases$",     adm_purchases),
        ("^adm_bot_settings$",  adm_bot_settings),
        ("^adm_daily_report$",  adm_daily_report),
    ]
    for pattern, handler in cbs:
        app.add_handler(CallbackQueryHandler(handler, pattern=pattern))

    app.add_handler(CommandHandler("adduser",  cmd_adduser))
    app.add_handler(CommandHandler("addquota", cmd_addquota))

    print("☁️ RebazCloud is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
