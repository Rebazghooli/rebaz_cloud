# ☁️ RebazCloud v2

ربات تلگرام برای مدیریت و ذخیره فایل‌ها با قابلیت پرداخت آنلاین.

---

## ✨ قابلیت‌ها

| قابلیت | توضیح |
|--------|-------|
| 📤 آپلود فایل | ذخیره همه نوع فایل در کانال |
| 📁 فولدربندی | سازماندهی فایل‌ها در فولدر |
| 🔍 جستجو | جستجو بر اساس نام، کد، تگ |
| 🔗 اشتراک‌گذاری | لینک عمومی برای هر فایل |
| 📊 آمار کاربر | تعداد فایل، خرید، فولدر |
| 💎 پرداخت آنلاین | NowPayments (کریپتو) |
| ✅ تأیید خودکار | Webhook + تأیید دستی ادمین |
| 👑 پنل ادمین | مدیریت کامل کاربران و فایل‌ها |
| 🌐 چندزبانه | فارسی، کوردی، انگلیسی |

---

## 🚀 راه‌اندازی

### ۱. پیش‌نیازها
```bash
Python 3.10+
```

### ۲. کلون و نصب
```bash
git clone https://github.com/your-username/rebazcloud.git
cd rebazcloud
chmod +x setup.sh
./setup.sh
```

### ۳. تنظیم `.env`
```bash
cp .env.example .env
nano .env
```

| متغیر | توضیح |
|-------|-------|
| `BOT_TOKEN` | توکن ربات از @BotFather |
| `ADMIN_ID` | آیدی عددی ادمین |
| `ADMIN_TOKEN` | رمز ورود ادمین با `/start TOKEN` |
| `BOT_USERNAME` | یوزرنیم ربات (بدون @) |
| `STORAGE_CHANNEL` | آیدی کانال ذخیره فایل (مثل `-100xxx`) |
| `BOT_PASSWORD` | رمز ورود کاربران (خالی = بدون رمز) |
| `FREE_LIMIT` | محدودیت فایل رایگان (پیش‌فرض: 50) |
| `NOWPAYMENTS_KEY` | کلید API از nowpayments.io |
| `NOWPAYMENTS_IPN_SECRET` | رمز IPN از داشبورد NowPayments |
| `WEBHOOK_PORT` | پورت سرور webhook (پیش‌فرض: 8080) |

### ۴. اجرا
```bash
# توسعه (مستقیم)
python bot.py
python webhook_server.py   # در ترمینال جدا

# پروداکشن (systemd)
sudo systemctl start rebazcloud-bot
sudo systemctl start rebazcloud-webhook
```

---

## 💳 راه‌اندازی NowPayments

1. اکانت بساز در [nowpayments.io](https://nowpayments.io)
2. API Key را در `.env` قرار بده
3. در داشبورد → **IPN Settings**:
   - Callback URL: `http://YOUR_SERVER:8080/nowpayments-ipn`
   - IPN Secret را کپی کن و در `.env` قرار بده
4. سرور webhook را اجرا کن

---

## 🔗 اشتراک‌گذاری فایل

روی هر فایل دکمه **🔗 اشتراک‌گذاری** را بزن تا یک لینک یونیک بگیری:

```
https://t.me/YourBot?start=file_XXXXXXXX
```

هر کسی با این لینک می‌تواند فایل را مستقیم از ربات دریافت کند.

---

## 👑 دستورات ادمین

| دستور | توضیح |
|-------|-------|
| `/start ADMIN_TOKEN` | ورود به عنوان ادمین |
| `/adduser <id>` | اضافه کردن کاربر دستی |
| `/addquota <id> <amount>` | اضافه کردن فضا به کاربر |

---

## 📂 ساختار پروژه

```
rebazcloud/
├── bot.py                # فایل اصلی ربات
├── webhook_server.py     # سرور IPN پرداخت
├── config.py             # تنظیمات
├── requirements.txt
├── setup.sh
├── .env.example
├── handlers/
│   ├── auth.py           # احراز هویت + منوی اصلی + آمار
│   ├── upload.py         # آپلود فایل (fixed)
│   ├── files.py          # مدیریت فایل + اشتراک‌گذاری
│   ├── premium.py        # پرداخت NowPayments (fixed)
│   ├── settings.py       # تنظیمات + فولدرها
│   └── admin.py          # پنل ادمین
├── locales/
│   └── strings.py        # رشته‌های چندزبانه
└── utils/
    └── db.py             # SQLite helpers
```

---

## 🔧 تغییرات نسخه ۲

- ✅ **باگ آپلود** برطرف شد (ASK_FILE state اضافه شد)
- ✅ **باگ NowPayments URL** برطرف شد (invoice API واقعی)
- ✅ **Webhook تأیید پرداخت** اضافه شد
- ✅ **تأیید دستی ادمین** برای پرداخت‌های pending
- ✅ **تأیید قبل از حذف فولدر** اضافه شد
- ✅ **لینک اشتراک‌گذاری فایل** اضافه شد
- ✅ **آمار کاربر** اضافه شد
- ✅ **چک ادمین یکپارچه** (ADMIN_ID در همه جا)
- ✅ **README و .env.example** اضافه شد
