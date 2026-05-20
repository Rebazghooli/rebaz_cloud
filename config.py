import os
from dotenv import load_dotenv
load_dotenv()

BOT_TOKEN        = os.getenv("BOT_TOKEN", "")
ADMIN_ID         = int(os.getenv("ADMIN_ID", "0"))
ADMIN_TOKEN      = os.getenv("ADMIN_TOKEN", "")
STORAGE_CHANNEL  = os.getenv("STORAGE_CHANNEL", "")
BOT_PASSWORD     = os.getenv("BOT_PASSWORD", "")
NOWPAYMENTS_KEY  = os.getenv("NOWPAYMENTS_KEY", "")
DB_FILE          = "rebazcloud.db"

FREE_LIMIT        = int(os.getenv("FREE_LIMIT", "50"))
PREMIUM_PER_PACK  = 100
PREMIUM_PRICE_USD = 3
