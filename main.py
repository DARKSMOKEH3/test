import asyncio
import random
import re
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.enums import ButtonStyle, ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from telethon import TelegramClient
from telethon.tl.functions.users import GetFullUserRequest
from telethon.errors import UsernameNotOccupiedError, UsernameInvalidError

BOT_TOKEN = "8827544517:AAGWx24zKPOxscSOMueY4C8MQZJKhLc49Rk"
API_ID    = 31444671
API_HASH  = "1910216a5f7270cb07413f66f45183f9"
ADMIN_ID  = 7316971152
BAN_PRICE = 500000

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


class GiftFlow(StatesGroup):
    choosing_language     = State()
    waiting_rules         = State()
    choosing_platform     = State()
    waiting_for_id        = State()
    confirming            = State()
    choosing_payment      = State()
    choosing_crypto       = State()
    waiting_card_receipt  = State()
    waiting_ton_receipt   = State()
    waiting_trx_receipt   = State()
    settings_menu         = State()
    settings_change_lang  = State()
    wallet_menu           = State()
    wallet_choose_method  = State()
    wallet_choose_crypto  = State()
    wallet_wait_amount    = State()
    wallet_card_receipt   = State()
    wallet_ton_receipt    = State()
    wallet_trx_receipt    = State()


user_langs: dict = {}
user_balances: dict = {}
ban_orders: dict = {}
topup_orders: dict = {}
tg_client: TelegramClient = None

HEX_RE = re.compile(r"^[0-9a-fA-F]{64}$")
TON_B64_RE = re.compile(r"^[A-Za-z0-9+/=_-]{40,90}$")


LANG_NAMES = {
    "fa": "🇮🇷 فارسی", "en": "🇬🇧 English", "ru": "🇷🇺 Русский",
    "ar": "🇸🇦 العربية", "tr": "🇹🇷 Türkçe", "hi": "🇮🇳 हिन्दी",
    "es": "🇪🇸 Español", "fr": "🇫🇷 Français", "de": "🇩🇪 Deutsch",
    "zh": "🇨🇳 中文",
}


TRANSLATIONS = {
    "fa": {
        "welcome_lang": "〽️ <b>Welcome To BannTel Bot !</b>\n\n🌐 لطفاً زبان خود را انتخاب کنید:",
        "rules": "❇️ <b>قوانین و مقررات سرویس BannTel</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n🛡 <b>به سرویس BannTel خوش آمدید.</b> لطفاً پیش از استفاده، کلیه بندهای زیر را با دقت مطالعه فرمایید. استفاده از هر یک از خدمات این سرویس به منزله پذیرش کامل و بدون قید و شرط این شرایط می‌باشد.\n\n⭕️ <b>۱. ماهیت خدمات</b>\nاین سرویس اقدام به ارائه خدمات مسدود سازی اکانت به صورت متود 2027 می‌نماید. تمامی سفارشات پس از ثبت نهایی، وارد صف پردازش می‌شوند و نهایتاً ۱ الی ۱۰ دقیقه در سرور اجرا می‌شوند.\n\n⭕️ <b>۲. صحت اطلاعات ورودی</b>\nکاربر موظف است آیدی عددی یا یوزرنیم اکانت مقصد را با دقت وارد نماید. سرویس هیچ‌گونه مسئولیتی در قبال بن کردن آیدی اشتباه ندارد.\n\n⭕️ <b>۳. اصالت رسید پرداخت</b>\nارسال هرگونه رسید جعلی، تخلف محسوب شده و منجر به مسدودسازی دائمی می‌شود.\n\n⭕️ <b>۴. نظارت و لاگ‌برداری</b>\nتمامی تراکنش‌ها در سیستم امنیتی ثبت می‌شوند.\n\n⭕️ <b>۵. زمان‌بندی انجام عملیات</b>\nزمان تخمینی صرفاً یک تخمین است.\n\n⭕️ <b>۶. بازگشت وجه</b>\nبازگشت وجه تنها در صورت عدم انجام سفارش امکان‌پذیر است.\n\n⭕️ <b>۷. مسئولیت کاربر</b>\nتمامی استفاده از این متود بر عهده‌ی کاربر می‌باشد.\n\n⭕️ <b>۸. تغییر شرایط</b>\nسرویس محفوظ است شرایط را تغییر دهد.\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n✅ با انتخاب گزینه زیر، تأیید می‌کنید که کلیه بندهای فوق را مطالعه کرده و می‌پذیرید.",
        "btn_accept_rules": "✅ قوانین را می‌پذیرم و ادامه می‌دهم",
        "btn_reject_rules": "❌ نمی‌پذیرم و لغو می‌کنم",
        "btn_platform_tg": "✈️ تلگرام", "btn_platform_wa": "✅ واتساپ",
        "btn_start_gift": "🟥 چک تخلف اکانت و فریز",
        "btn_buy_ban": "🛒 خرید متود بن",
        "btn_settings": "⚙️ تنظیمات",
        "btn_help": "🆘 راهنما", "btn_support": "🔰 پشتیبانی",
        "btn_back_platform": "🔙 بازگشت به انتخاب پلتفرم",
        "btn_confirm_yes": "✅ تأیید و ادامه", "btn_confirm_no": "❌ لغو",
        "btn_pay_card": "💳 کارت به کارت", "btn_pay_crypto": "🪙 ارز دیجیتال",
        "btn_pay_balance": "💰 پرداخت از موجودی",
        "btn_back_menu": "🔙 بازگشت به منو",
        "btn_crypto_ton": "💎 TON", "btn_crypto_trx": "⚡ TRX",
        "btn_back": "🔙 بازگشت",
        "btn_my_account": "👤 حساب کاربری من",
        "btn_change_lang": "🌐 تغییر زبان",
        "btn_wallet": "💰 کیف پول",
        "rules_accepted": "✅ پذیرفته شد", "rules_rejected": "❌ لغو شد",
        "rules_rejected_text": "❌ <b>شما قوانین را نپذیرفتید.</b>\n\nبرای استفاده از سرویس، لطفاً با /start دوباره شروع کنید.",
        "wa_soon": "⏳ به زودی فعال می‌شود",
        "platform_text": "🌐 <b>انتخاب پلتفرم</b>\n━━━━━━━━━━━━━━━━━━━━\nسرویس مورد نظر خود را انتخاب کنید:",
        "welcome": "〽️ <b>Welcome</b>\n📶 درود <b>{name}</b>\n\n⭕️ متود و سرور بن کردن اکانت تلگرام فقط بین یک تا ۱۰ دقیقه !\n\n⭕️ قدرتمند ترین متود 2026\n\n⭕️ قابلیت تشخیص خودکار تخلف اکانت و انتخاب نوع متود بن کردن\n\n‼️ برای شروع یکی از گزینه‌های زیر رو انتخاب کنید:",
        "ask_id": "🔎 <b>موتور هوشمند تست اکانت — مرحله ۱ از ۳</b>\n\nلطفاً <b>آیدی عددی</b> یا <b>یوزرنیم</b> اکانت مقصد را ارسال کنید.\n\n<i>مثال:</i> <code>@username</code> یا <code>123456789</code>",
        "checking": "⭕️ در حال استعلام از سرورهای تلگرام...",
        "not_found": "❌ <b>اکانت پیدا نشد.</b>\n\nمطمئن شوید آیدی یا یوزرنیم درست وارد شده.",
        "analysis_header": "⭕️ <b>نتیجه آنالیز هوشمند اکانت</b>",
        "lbl_name": "🟩 <b>نام:</b>", "lbl_last": "🟩 <b>لست:</b>",
        "lbl_id": "🟩 <b>آیدی عددی:</b>", "lbl_username": "🟦 <b>یوزرنیم:</b>",
        "lbl_phone": "🟥 <b>شماره:</b>", "lbl_premium": "🟦 <b>پریمیوم:</b>",
        "lbl_bot": "🟦 <b>ربات:</b>", "lbl_bio": "🟩 <b>بیو:</b>",
        "has": "دارد", "not_has": "ندارد", "yes": "بله", "no": "خیر",
        "lbl_violation": "⭕️ <b>درصد تخلف اکانت:</b>",
        "lbl_freeze_time": "✅ <b>زمان فریز کامل :</b>", "minute": "دقیقه",
        "ask_confirm": "⭕️ آیا از خرید سرویس فریز اکانت برای این اکانت مطمئن هستید؟",
        "payment_header": "💠 <b>مرحله ۲ از ۳ — انتخاب روش پرداخت</b>\n━━━━━━━━━━━━━━━━━━━━\n<b>هزینه بن کردن اکانت مقصد:</b>\n<b>۵۰۰,۰۰۰ تومان</b>\n━━━━━━━━━━━━━━━━━━━━\n\nروش پرداخت مورد نظرتون رو انتخاب کنید:",
        "card_text": "✅ <b>پرداخت کارت به کارت</b>\n━━━━━━━━━━━━━━━━━━━━\nمبلغ قابل پرداخت: <b>۵۰۰,۰۰۰ تومان</b>\n\nشماره کارت:\n<blockquote><code>6037998133013256</code></blockquote>\nبه نام: <b>محمود محمدی</b>\n━━━━━━━━━━━━━━━━━━━━\n\n پس از واریز، <b>عکس تراکنش</b> را ارسال کنید.",
        "crypto_text": "🪙 <b>پرداخت با ارز دیجیتال</b>\n━━━━━━━━━━━━━━━━━━━━\nارز مورد نظر خود را انتخاب کنید:",
        "ton_text": "💎 <b>پرداخت با TON</b>\n━━━━━━━━━━━━━━━━━━━━\nمبلغ قابل پرداخت: <b>1.3 TON</b>\n\nآدرس ولت:\n<blockquote><code>UQDMEy9GsZ6uph0yPtUdj4hRlBaa5hczi1CvOVgmZx7ZIguR</code></blockquote>\n━━━━━━━━━━━━━━━━━━━━\n\nپس از پرداخت، <b>عکس و آدرس هش پرداخت</b> را ارسال کنید.",
        "trx_text": "⚡ <b>پرداخت با TRX</b>\n━━━━━━━━━━━━━━━━━━━━\nمبلغ قابل پرداخت: <b>5.70 TRX</b>\n\nآدرس ولت:\n<blockquote><code>TAE7ZdjFKxkMMSr2AQKq6t3PxwDcSdH4WU</code></blockquote>\n━━━━━━━━━━━━━━━━━━━━\n\n پس از پرداخت، <b>عکس و آدرس هش پرداخت</b> را ارسال کنید.",
        "help_text": "✅ <b>راهنمای کامل استفاده از سرویس</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n🔹 <b>مرحله ۱ — انتخاب پلتفرم</b>\nدر ابتدای ورود، پلتفرم مورد نظر خود را انتخاب می‌کنید.\n\n🔹 <b>مرحله ۲ — ثبت آیدی مقصد</b>\nروی «خرید متود بن» بزنید و آیدی مقصد را وارد کنید.\n\n🔹 <b>مرحله ۳ — آنالیز هوشمند</b>\nسیستم مشخصات اکانت و درصد تخلف را نمایش می‌دهد.\n\n🔹 <b>مرحله ۴ — انتخاب روش پرداخت</b>\n• کارت به کارت — ۵۰۰,۰۰۰ تومان\n• ارز دیجیتال — TON یا TRX\n• موجودی حساب — کسر خودکار\n\n🔹 <b>مرحله ۵ — ارسال رسید</b>\nعکس تراکنش و هش را ارسال کنید.\n\n🔹 <b>مرحله ۶ — تأیید و انجام</b>\nپس از تأیید ادمین، عملیات بن آغاز می‌شود.\n\n✅ <b>زمان انجام</b>\nبه‌طور میانگین بین ۵ تا ۱۰ دقیقه.\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n🛜 پشتیبانی: @BanTel_Support",
        "support_text": "⭕️ <b>پشتیبانی سرویس BannTel</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n✅ تیم سایبری پشتیبانی ما به‌صورت ۲۴ ساعته آماده پاسخگویی است\n\n❇️ <b>راه‌های ارتباطی:</b>\n• تلگرام: @BanTel_Support\n• پاسخگویی: حداکثر تا یک ساعت\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n🟩 پیش از ارسال پیام، شماره سفارش خود را آماده داشته باشید.",
        "cancelled": "❌ عملیات لغو شد.\n\nبرای شروع مجدد از منو استفاده کنید.",
        "confirmed_yes": "✅ تأیید شد", "confirmed_no": "❌ لغو شد",
        "receipt_photo_ok": "✅ <b>عکس دریافت شد.</b>\n\nحالا <b>هش پرداخت</b> را ارسال کنید.",
        "receipt_hash_ok": "✅ <b>هش دریافت شد.</b>\n\nحالا <b>عکس تراکنش</b> را ارسال کنید.",
        "receipt_done": "✅ <b>اطلاعات دریافت شد.</b>\n\n⏳ چند دقیقه برای تأیید منتظر بمانید.",
        "photo_already": "⚠️ عکس قبلاً دریافت شده. لطفاً <b>هش پرداخت</b> را ارسال کنید.",
        "hash_already": "⚠️ هش قبلاً دریافت شده. لطفاً <b>عکس تراکنش</b> را ارسال کنید.",
        "invalid_hash_ton": "❌ <b>هش نامعتبر است.</b>\n\nلطفاً <b>هش صحیح TON</b> را ارسال نمایید.",
        "invalid_hash_trx": "❌ <b>هش نامعتبر است.</b>\n\nلطفاً <b>هش صحیح TRX</b> را ارسال نمایید.",
        "ask_photo_or_hash": "⚠️ لطفاً <b>عکس یا هش پرداخت</b> را ارسال کنید.",
        "ask_photo_only": "⚠️ لطفاً <b>عکس تراکنش</b> را ارسال کنید.",
        "ask_id_valid": "⚠️ لطفاً یک آیدی معتبر ارسال کنید.",
        "order_new": "✅ <b>سفارش جدید</b>",
        "order_buyer": "✅ <b>خریدار:</b>",
        "order_buyer_id": "✅ <b>آیدی عددی خریدار:</b>",
        "order_method": "✅ <b>روش پرداخت:</b>",
        "order_target": "✅ <b>اکانت مقصد:</b>",
        "order_target_name": "✅ <b>نام مقصد:</b>",
        "order_sent_from": "✅ <b>ارسال‌شده از این اکانت</b>",
        "order_hash": "📝 <b>هش پرداخت:</b>",
        "order_desc": "📝 <b>توضیح/هش ارسال‌شده:</b>",
        "order_text": "📝 <b>متن:</b>",
        "admin_denied": "⛔ دسترسی ندارید.",
        "admin_ok_msg": "✅ سفارش <b>#{order_id}</b> تأیید شد.",
        "admin_no_msg": "❌ سفارش <b>#{order_id}</b> کنسل شد.",
        "user_order_ok": "🎉 <b>سفارش شما تأیید شد</b>\n━━━━━━━━━━━━━━━━━━━━\n🧾 شماره سفارش: <code>{order_id}</code>\n💳 روش پرداخت: {method}\n━━━━━━━━━━━━━━━━━━━━\n🚀 عملیات بن کردن اکانت به‌زودی آغاز می‌شود.",
        "user_order_no": "❌ <b>سفارش شما کنسل شد</b>\n━━━━━━━━━━━━━━━━━━━━\n🧾 شماره سفارش: <code>{order_id}</code>\n━━━━━━━━━━━━━━━━━━━━\nدر صورت واریز وجه، مبلغ طی ۲۴ ساعت آینده بازگردانده می‌شود.\nبرای پیگیری: @BanTel_Support",
        "method_card": "💳 کارت به کارت", "method_ton": "💎 TON",
        "method_trx": "⚡ TRX", "method_balance": "💰 موجودی حساب",
        "settings_text": "⚙️ <b>تنظیمات</b>\n━━━━━━━━━━━━━━━━━━━━\nاز گزینه‌های زیر انتخاب کنید:",
        "account_text": "👤 <b>حساب کاربری من</b>\n━━━━━━━━━━━━━━━━━━━━\n🟩 <b>نام:</b> {name}\n🟩 <b>فامیلی:</b> {last}\n🟩 <b>آیدی عددی:</b> <code>{uid}</code>\n🟦 <b>یوزرنیم:</b> {username}\n🟥 <b>وضعیت:</b> {status}\n💰 <b>موجودی کیف پول:</b> <b>{balance:,} تومان</b>\n━━━━━━━━━━━━━━━━━━━━",
        "wallet_text": "💰 <b>کیف پول شما</b>\n━━━━━━━━━━━━━━━━━━━━\n💳 <b>موجودی فعلی:</b> <b>{balance:,} تومان</b>\n━━━━━━━━━━━━━━━━━━━━\n\nبرای افزایش موجودی، یکی از روش‌های زیر را انتخاب کنید:",
        "wallet_method_text": "💰 <b>افزایش موجودی</b>\n━━━━━━━━━━━━━━━━━━━━\nروش پرداخت را انتخاب کنید:",
        "topup_ask_amount_card": "💳 <b>افزایش موجودی با کارت</b>\n\n💰 لطفاً مبلغ مورد نظر (به تومان) را به صورت عدد انگلیسی ارسال کنید.\n\n<i>مثال:</i> <code>500000</code>",
        "topup_ask_amount_crypto": "🪙 <b>افزایش موجودی با ارز دیجیتال</b>\n\n💰 لطفاً مبلغ مورد نظر (به تومان) را به صورت عدد انگلیسی ارسال کنید.\n\n<i>مثال:</i> <code>500000</code>",
        "topup_invalid_amount": "❌ مبلغ نامعتبر است. لطفاً فقط عدد انگلیسی ارسال کنید (حداقل ۱۰,۰۰۰ تومان).",
        "topup_card_info": "💳 <b>اطلاعات پرداخت کارتی</b>\n━━━━━━━━━━━━━━━━━━━━\n💰 مبلغ: <b>{amount:,} تومان</b>\n\nشماره کارت:\n<blockquote><code>6037998133013256</code></blockquote>\nبه نام: <b>محمود محمدی</b>\n━━━━━━━━━━━━━━━━━━━━\n\n📸 پس از واریز، <b>عکس تراکنش</b> را ارسال کنید.",
        "topup_ton_info": "💎 <b>افزایش با TON</b>\n━━━━━━━━━━━━━━━━━━━━\n💰 مبلغ: <b>{amount:,} تومان</b>\n\nآدرس ولت:\n<blockquote><code>UQDMEy9GsZ6uph0yPtUdj4hRlBaa5hczi1CvOVgmZx7ZIguR</code></blockquote>\n━━━━━━━━━━━━━━━━━━━━\n\n📸 پس از پرداخت، <b>عکس تراکنش</b> را ارسال کنید.",
        "topup_trx_info": "⚡ <b>افزایش با TRX</b>\n━━━━━━━━━━━━━━━━━━━━\n💰 مبلغ: <b>{amount:,} تومان</b>\n\nآدرس ولت:\n<blockquote><code>TAE7ZdjFKxkMMSr2AQKq6t3PxwDcSdH4WU</code></blockquote>\n━━━━━━━━━━━━━━━━━━━━\n\n📸 پس از پرداخت، <b>عکس تراکنش</b> را ارسال کنید.",
        "topup_receipt_done": "✅ <b>رسید دریافت شد.</b>\n\n⏳ منتظر تأیید ادمین برای افزایش موجودی باشید.",
        "balance_insufficient": "❌ <b>موجودی کافی نیست.</b>\n\n💰 موجودی فعلی: <b>{balance:,} تومان</b>\n💳 مبلغ مورد نیاز: <b>۵۰۰,۰۰۰ تومان</b>\n\nبرای افزایش موجودی به بخش «کیف پول» در تنظیمات مراجعه کنید.",
        "balance_paid_msg": "✅ <b>پرداخت از موجودی انجام شد.</b>\n\n💰 مبلغ کسر شده: <b>۵۰۰,۰۰۰ تومان</b>\n💳 موجودی باقی‌مانده: <b>{balance:,} تومان</b>\n\n⏳ سفارش شما در حال پردازش است.",
        "tup_new": "💰 <b>درخواست افزایش موجودی</b>",
        "tup_amount_lbl": "💰 <b>مبلغ درخواستی:</b>",
        "tup_method_lbl": "💳 <b>روش واریز:</b>",
        "tup_ok_msg": "✅ <b>موجودی شما افزایش یافت.</b>\n\n💰 مبلغ واریزی: <b>{amount:,} تومان</b>\n💳 موجودی جدید: <b>{balance:,} تومان</b>",
        "tup_no_msg": "❌ <b>درخواست افزایش موجودی رد شد.</b>\n\nدر صورت واریز وجه، مبلغ بازگردانده می‌شود.\nبرای پیگیری: @BanTel_Support",
    },
    "en": {
        "welcome_lang": "〽️ <b>Welcome to BannTel Bot</b>\n\n🌐 Please select your language:",
        "rules": "❇️ <b>BannTel Service — Terms & Conditions</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n🛡 <b>Welcome to BannTel.</b> Please read all clauses carefully before use.\n\n⭕️ <b>1. Nature of Services</b>\nAccount suspension (ban) via the 2027 method. Orders execute within 1-10 minutes.\n\n⭕️ <b>2. Accuracy of Input Data</b>\nThe user must enter the correct ID or username. We are not responsible for wrong IDs.\n\n⭕️ <b>3. Authenticity of Payment Receipt</b>\nFake receipts result in permanent suspension.\n\n⭕️ <b>4. Monitoring & Logging</b>\nAll transactions are logged.\n\n⭕️ <b>5. Operation Timing</b>\nDisplayed time is an estimate.\n\n⭕️ <b>6. Refunds</b>\nRefunds only if the order cannot be fulfilled.\n\n⭕️ <b>7. User Responsibility</b>\nAll use of this method rests with the user.\n\n⭕️ <b>8. Changes to Terms</b>\nWe reserve the right to update these terms.\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n✅ By selecting the option below, you confirm acceptance of all clauses.",
        "btn_accept_rules": "✅ I accept the terms and continue",
        "btn_reject_rules": "❌ I do not accept and cancel",
        "btn_platform_tg": "✈️ Telegram", "btn_platform_wa": "✅ WhatsApp",
        "btn_start_gift": "🟥 Check Violations & Freeze",
        "btn_buy_ban": "🛒 Buy Ban Method",
        "btn_settings": "⚙️ Settings",
        "btn_help": "🆘 Help", "btn_support": "🔰 Support",
        "btn_back_platform": "🔙 Back to platform selection",
        "btn_confirm_yes": "✅ Confirm and continue", "btn_confirm_no": "❌ Cancel",
        "btn_pay_card": "💳 Card to Card", "btn_pay_crypto": "🪙 Cryptocurrency",
        "btn_pay_balance": "💰 Pay from Balance",
        "btn_back_menu": "🔙 Back to menu",
        "btn_crypto_ton": "💎 TON", "btn_crypto_trx": "⚡ TRX",
        "btn_back": "🔙 Back",
        "btn_my_account": "👤 My Account",
        "btn_change_lang": "🌐 Change Language",
        "btn_wallet": "💰 Wallet",
        "rules_accepted": "✅ Accepted", "rules_rejected": "❌ Canceled",
        "rules_rejected_text": "❌ <b>You did not accept the terms.</b>\n\nRestart with /start.",
        "wa_soon": "⏳ Coming soon",
        "platform_text": "🌐 <b>Select Platform</b>\n━━━━━━━━━━━━━━━━━━━━\nChoose your service:",
        "welcome": "〽️ <b>Welcome</b>\n📶 Hello <b>{name}</b>\n\n⭕️ Telegram account ban method in just 1 to 10 minutes!\n\n⭕️ The most powerful 2026 method\n\n⭕️ Auto violation detection\n\n‼️ Choose an option to begin:",
        "ask_id": "🔎 <b>Smart Tester — Step 1 of 3</b>\n\nSend the target account's <b>numeric ID</b> or <b>username</b>.\n\n<i>Example:</i> <code>@username</code> or <code>123456789</code>",
        "checking": "⭕️ Fetching from Telegram servers...",
        "not_found": "❌ <b>Account not found.</b>\n\nMake sure the ID or username is correct.",
        "analysis_header": "⭕️ <b>Smart Account Analysis</b>",
        "lbl_name": "🟩 <b>Name:</b>", "lbl_last": "🟩 <b>Last:</b>",
        "lbl_id": "🟩 <b>Numeric ID:</b>", "lbl_username": "🟦 <b>Username:</b>",
        "lbl_phone": "🟥 <b>Phone:</b>", "lbl_premium": "🟦 <b>Premium:</b>",
        "lbl_bot": "🟦 <b>Bot:</b>", "lbl_bio": "🟩 <b>Bio:</b>",
        "has": "Yes", "not_has": "No", "yes": "Yes", "no": "No",
        "lbl_violation": "⭕️ <b>Violation Rate:</b>",
        "lbl_freeze_time": "✅ <b>Full Freeze Time:</b>", "minute": "min",
        "ask_confirm": "⭕️ Are you sure you want to purchase the account freeze for this account?",
        "payment_header": "💠 <b>Step 2 of 3 — Payment Method</b>\n━━━━━━━━━━━━━━━━━━━━\n<b>Ban fee:</b>\n<b>500,000 Toman</b>\n━━━━━━━━━━━━━━━━━━━━\n\nChoose your method:",
        "card_text": "✅ <b>Card to Card Payment</b>\n━━━━━━━━━━━━━━━━━━━━\nAmount: <b>500,000 Toman</b>\n\nCard:\n<blockquote><code>6037998133013256</code></blockquote>\nHolder: <b>Mahmoud Mohammadi</b>\n━━━━━━━━━━━━━━━━━━━━\n\n After payment, send the <b>transaction photo</b>.",
        "crypto_text": "🪙 <b>Crypto Payment</b>\n━━━━━━━━━━━━━━━━━━━━\nChoose your currency:",
        "ton_text": "💎 <b>TON Payment</b>\n━━━━━━━━━━━━━━━━━━━━\nAmount: <b>1.3 TON</b>\n\nWallet:\n<blockquote><code>UQDMEy9GsZ6uph0yPtUdj4hRlBaa5hczi1CvOVgmZx7ZIguR</code></blockquote>\n━━━━━━━━━━━━━━━━━━━━\n\nAfter payment send <b>photo and hash</b>.",
        "trx_text": "⚡ <b>TRX Payment</b>\n━━━━━━━━━━━━━━━━━━━━\nAmount: <b>5.70 TRX</b>\n\nWallet:\n<blockquote><code>TAE7ZdjFKxkMMSr2AQKq6t3PxwDcSdH4WU</code></blockquote>\n━━━━━━━━━━━━━━━━━━━━\n\n After payment send <b>photo and hash</b>.",
        "help_text": "✅ <b>Complete Guide</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n🔹 <b>Step 1 — Platform</b>\nChoose Telegram or WhatsApp.\n\n🔹 <b>Step 2 — Target ID</b>\nClick «Buy Ban Method» and enter the ID.\n\n🔹 <b>Step 3 — Smart Analysis</b>\nViolation rate and estimated time.\n\n🔹 <b>Step 4 — Payment</b>\n• Card — 500,000 Toman\n• Crypto — TON or TRX\n• Balance — auto deduct\n\n🔹 <b>Step 5 — Receipt</b>\nSend photo and hash.\n\n🔹 <b>Step 6 — Confirm</b>\nBan starts after admin approval.\n\n✅ <b>Time</b>\n5 to 10 minutes average.\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n🛜 Support: @BanTel_Support",
        "support_text": "⭕️ <b>BannTel Support</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n✅ Our cyber support team is available 24/7.\n\n❇️ <b>Contact:</b>\n• Telegram: @BanTel_Support\n• Response: within 1 hour\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n🟩 Have your order number ready.",
        "cancelled": "❌ Operation canceled.",
        "confirmed_yes": "✅ Confirmed", "confirmed_no": "❌ Canceled",
        "receipt_photo_ok": "✅ <b>Photo received.</b>\n\nNow send the <b>hash</b>.",
        "receipt_hash_ok": "✅ <b>Hash received.</b>\n\nNow send the <b>photo</b>.",
        "receipt_done": "✅ <b>Information received.</b>\n\n⏳ Wait a few minutes for approval.",
        "photo_already": "⚠️ Photo already received. Send the <b>hash</b>.",
        "hash_already": "⚠️ Hash already received. Send the <b>photo</b>.",
        "invalid_hash_ton": "❌ <b>Invalid hash.</b>\n\nSend a valid <b>TON hash</b>.",
        "invalid_hash_trx": "❌ <b>Invalid hash.</b>\n\nSend a valid <b>TRX hash</b>.",
        "ask_photo_or_hash": "⚠️ Send the <b>photo or hash</b>.",
        "ask_photo_only": "⚠️ Send the <b>transaction photo</b>.",
        "ask_id_valid": "⚠️ Send a valid ID.",
        "order_new": "✅ <b>New Order</b>",
        "order_buyer": "✅ <b>Buyer:</b>",
        "order_buyer_id": "✅ <b>Buyer Numeric ID:</b>",
        "order_method": "✅ <b>Payment Method:</b>",
        "order_target": "✅ <b>Target Account:</b>",
        "order_target_name": "✅ <b>Target Name:</b>",
        "order_sent_from": "✅ <b>Sent from this account</b>",
        "order_hash": "📝 <b>Payment Hash:</b>",
        "order_desc": "📝 <b>Description/Hash:</b>",
        "order_text": "📝 <b>Text:</b>",
        "admin_denied": "⛔ Access denied.",
        "admin_ok_msg": "✅ Order <b>#{order_id}</b> confirmed.",
        "admin_no_msg": "❌ Order <b>#{order_id}</b> canceled.",
        "user_order_ok": "🎉 <b>Your order is confirmed</b>\n━━━━━━━━━━━━━━━━━━━━\n🧾 Order: <code>{order_id}</code>\n💳 Payment: {method}\n━━━━━━━━━━━━━━━━━━━━\n🚀 The ban operation will begin shortly.",
        "user_order_no": "❌ <b>Your order was canceled</b>\n━━━━━━━━━━━━━━━━━━━━\n🧾 Order: <code>{order_id}</code>\n━━━━━━━━━━━━━━━━━━━━\nIf payment was made, refund within 24 hours.\n@BanTel_Support",
        "method_card": "💳 Card", "method_ton": "💎 TON",
        "method_trx": "⚡ TRX", "method_balance": "💰 Balance",
        "settings_text": "⚙️ <b>Settings</b>\n━━━━━━━━━━━━━━━━━━━━\nChoose an option below:",
        "account_text": "👤 <b>My Account</b>\n━━━━━━━━━━━━━━━━━━━━\n🟩 <b>Name:</b> {name}\n🟩 <b>Last:</b> {last}\n🟩 <b>Numeric ID:</b> <code>{uid}</code>\n🟦 <b>Username:</b> {username}\n🟥 <b>Status:</b> {status}\n💰 <b>Wallet Balance:</b> <b>{balance:,} Toman</b>\n━━━━━━━━━━━━━━━━━━━━",
        "wallet_text": "💰 <b>Your Wallet</b>\n━━━━━━━━━━━━━━━━━━━━\n💳 <b>Current Balance:</b> <b>{balance:,} Toman</b>\n━━━━━━━━━━━━━━━━━━━━\n\nChoose a top-up method:",
        "wallet_method_text": "💰 <b>Top-up Balance</b>\n━━━━━━━━━━━━━━━━━━━━\nChoose a payment method:",
        "topup_ask_amount_card": "💳 <b>Card Top-up</b>\n\n💰 Send the amount (in Toman) as a number.\n\n<i>Example:</i> <code>500000</code>",
        "topup_ask_amount_crypto": "🪙 <b>Crypto Top-up</b>\n\n💰 Send the amount (in Toman) as a number.\n\n<i>Example:</i> <code>500000</code>",
        "topup_invalid_amount": "❌ Invalid amount. Send a valid number (min 10,000 Toman).",
        "topup_card_info": "💳 <b>Card Payment Info</b>\n━━━━━━━━━━━━━━━━━━━━\n💰 Amount: <b>{amount:,} Toman</b>\n\nCard:\n<blockquote><code>6037998133013256</code></blockquote>\nHolder: <b>Mahmoud Mohammadi</b>\n━━━━━━━━━━━━━━━━━━━━\n\n📸 After payment send the <b>transaction photo</b>.",
        "topup_ton_info": "💎 <b>TON Top-up</b>\n━━━━━━━━━━━━━━━━━━━━\n💰 Amount: <b>{amount:,} Toman</b>\n\nWallet:\n<blockquote><code>UQDMEy9GsZ6uph0yPtUdj4hRlBaa5hczi1CvOVgmZx7ZIguR</code></blockquote>\n━━━━━━━━━━━━━━━━━━━━\n\n📸 After payment send the <b>transaction photo</b>.",
        "topup_trx_info": "⚡ <b>TRX Top-up</b>\n━━━━━━━━━━━━━━━━━━━━\n💰 Amount: <b>{amount:,} Toman</b>\n\nWallet:\n<blockquote><code>TAE7ZdjFKxkMMsr2AQKq6t3PxwDcSdH4WU</code></blockquote>\n━━━━━━━━━━━━━━━━━━━━\n\n📸 After payment send the <b>transaction photo</b>.",
        "topup_receipt_done": "✅ <b>Receipt received.</b>\n\n⏳ Wait for admin approval.",
        "balance_insufficient": "❌ <b>Insufficient balance.</b>\n\n💰 Current: <b>{balance:,} Toman</b>\n💳 Required: <b>500,000 Toman</b>\n\nTop up via Wallet in Settings.",
        "balance_paid_msg": "✅ <b>Paid from balance.</b>\n\n💰 Deducted: <b>500,000 Toman</b>\n💳 Remaining: <b>{balance:,} Toman</b>\n\n⏳ Your order is being processed.",
        "tup_new": "💰 <b>Balance Top-up Request</b>",
        "tup_amount_lbl": "💰 <b>Requested Amount:</b>",
        "tup_method_lbl": "💳 <b>Method:</b>",
        "tup_ok_msg": "✅ <b>Balance topped up.</b>\n\n💰 Amount: <b>{amount:,} Toman</b>\n💳 New Balance: <b>{balance:,} Toman</b>",
        "tup_no_msg": "❌ <b>Top-up request rejected.</b>\n\nIf payment was made, refund within 24 hours.\n@BanTel_Support",
    },
    "ru": {
        "welcome_lang": "〽️ <b>Добро пожаловать в BannTel Bot</b>\n\n🌐 Выберите язык:",
        "rules": "❇️ <b>Условия использования BannTel</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n🛡 Добро пожаловать. Прочтите условия перед использованием.\n\n⭕️ 1. Услуги: блокировка аккаунтов методом 2027, 1–10 минут.\n⭕️ 2. Вводите правильный ID.\n⭕️ 3. Поддельные чеки → постоянная блокировка.\n⭕️ 4. Все транзакции логируются.\n⭕️ 5. Время — оценка.\n⭕️ 6. Возврат только при невозможности выполнения.\n⭕️ 7. Ответственность на пользователе.\n⭕️ 8. Условия могут меняться.\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n✅ Нажав ниже, вы принимаете условия.",
        "btn_accept_rules": "✅ Принимаю", "btn_reject_rules": "❌ Не принимаю",
        "btn_platform_tg": "✈️ Telegram", "btn_platform_wa": "✅ WhatsApp",
        "btn_start_gift": "🟥 Проверка и заморозка",
        "btn_buy_ban": "🛒 Купить метод бана",
        "btn_settings": "⚙️ Настройки",
        "btn_help": "🆘 Помощь", "btn_support": "🔰 Поддержка",
        "btn_back_platform": "🔙 Назад к выбору платформы",
        "btn_confirm_yes": "✅ Подтвердить", "btn_confirm_no": "❌ Отмена",
        "btn_pay_card": "💳 Карта", "btn_pay_crypto": "🪙 Крипто",
        "btn_pay_balance": "💰 С баланса",
        "btn_back_menu": "🔙 Назад",
        "btn_crypto_ton": "💎 TON", "btn_crypto_trx": "⚡ TRX",
        "btn_back": "🔙 Назад",
        "btn_my_account": "👤 Мой аккаунт",
        "btn_change_lang": "🌐 Изменить язык",
        "btn_wallet": "💰 Кошелёк",
        "rules_accepted": "✅ Принято", "rules_rejected": "❌ Отменено",
        "rules_rejected_text": "❌ <b>Вы не приняли условия.</b>\n\n/start чтобы начать заново.",
        "wa_soon": "⏳ Скоро",
        "platform_text": "🌐 <b>Выберите платформу</b>\n━━━━━━━━━━━━━━━━━━━━\nВыберите сервис:",
        "welcome": "〽️ <b>Welcome</b>\n📶 Привет <b>{name}</b>\n\n⭕️ Метод бана Telegram за 1–10 минут!\n\n⭕️ Самый мощный метод 2026\n\n⭕️ Автоопределение нарушений\n\n‼️ Выберите опцию:",
        "ask_id": "🔎 <b>Умный тестер — Шаг 1/3</b>\n\nОтправьте <b>ID</b> или <b>юзернейм</b> цели.\n\n<i>Пример:</i> <code>@username</code>",
        "checking": "⭕️ Запрос к Telegram...",
        "not_found": "❌ <b>Аккаунт не найден.</b>",
        "analysis_header": "⭕️ <b>Анализ аккаунта</b>",
        "lbl_name": "🟩 <b>Имя:</b>", "lbl_last": "🟩 <b>Фамилия:</b>",
        "lbl_id": "🟩 <b>ID:</b>", "lbl_username": "🟦 <b>Юзернейм:</b>",
        "lbl_phone": "🟥 <b>Телефон:</b>", "lbl_premium": "🟦 <b>Премиум:</b>",
        "lbl_bot": "🟦 <b>Бот:</b>", "lbl_bio": "🟩 <b>Био:</b>",
        "has": "Есть", "not_has": "Нет", "yes": "Да", "no": "Нет",
        "lbl_violation": "⭕️ <b>Нарушения:</b>",
        "lbl_freeze_time": "✅ <b>Время заморозки:</b>", "minute": "мин",
        "ask_confirm": "⭕️ Купить услугу заморозки для этого аккаунта?",
        "payment_header": "💠 <b>Шаг 2/3 — Оплата</b>\n━━━━━━━━━━━━━━━━━━━━\n<b>Стоимость бана:</b> <b>500,000 Toman</b>\n━━━━━━━━━━━━━━━━━━━━\n\nВыберите метод:",
        "card_text": "✅ <b>Оплата картой</b>\n━━━━━━━━━━━━━━━━━━━━\nСумма: <b>500,000 Toman</b>\n\nКарта:\n<blockquote><code>6037998133013256</code></blockquote>\nВладелец: <b>Mahmoud Mohammadi</b>\n━━━━━━━━━━━━━━━━━━━━\n\n После оплаты отправьте <b>фото</b>.",
        "crypto_text": "🪙 <b>Крипто-оплата</b>\n━━━━━━━━━━━━━━━━━━━━\nВыберите валюту:",
        "ton_text": "💎 <b>Оплата TON</b>\n━━━━━━━━━━━━━━━━━━━━\nСумма: <b>1.3 TON</b>\n\nАдрес:\n<blockquote><code>UQDMEy9GsZ6uph0yPtUdj4hRlBaa5hczi1CvOVgmZx7ZIguR</code></blockquote>\n━━━━━━━━━━━━━━━━━━━━\n\nОтправьте <b>фото и хэш</b>.",
        "trx_text": "⚡ <b>Оплата TRX</b>\n━━━━━━━━━━━━━━━━━━━━\nСумма: <b>5.70 TRX</b>\n\nАдрес:\n<blockquote><code>TAE7ZdjFKxkMMSr2AQKq6t3PxwDcSdH4WU</code></blockquote>\n━━━━━━━━━━━━━━━━━━━━\n\n Отправьте <b>фото и хэш</b>.",
        "help_text": "✅ <b>Полное руководство</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n🔹 Шаг 1 — Платформа\n🔹 Шаг 2 — Ввод ID\n🔹 Шаг 3 — Анализ\n🔹 Шаг 4 — Оплата (карта / крипто / баланс)\n🔹 Шаг 5 — Чек\n🔹 Шаг 6 — Подтверждение\n\n✅ Среднее: 5–10 мин.\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n🛜 @BanTel_Support",
        "support_text": "⭕️ <b>Поддержка BannTel</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n✅ Доступно 24/7.\n\n❇️ <b>Контакт:</b>\n• @BanTel_Support\n• Ответ: до 1 часа",
        "cancelled": "❌ Операция отменена.",
        "confirmed_yes": "✅ Подтверждено", "confirmed_no": "❌ Отменено",
        "receipt_photo_ok": "✅ <b>Фото получено.</b>\n\nОтправьте <b>хэш</b>.",
        "receipt_hash_ok": "✅ <b>Хэш получен.</b>\n\nОтправьте <b>фото</b>.",
        "receipt_done": "✅ <b>Информация получена.</b>\n\n⏳ Ждите подтверждения.",
        "photo_already": "⚠️ Фото уже получено. Отправьте <b>хэш</b>.",
        "hash_already": "⚠️ Хэш уже получен. Отправьте <b>фото</b>.",
        "invalid_hash_ton": "❌ <b>Неверный хэш TON.</b>",
        "invalid_hash_trx": "❌ <b>Неверный хэш TRX.</b>",
        "ask_photo_or_hash": "⚠️ Отправьте <b>фото или хэш</b>.",
        "ask_photo_only": "⚠️ Отправьте <b>фото</b>.",
        "ask_id_valid": "⚠️ Отправьте корректный ID.",
        "order_new": "✅ <b>Новый заказ</b>",
        "order_buyer": "✅ <b>Покупатель:</b>",
        "order_buyer_id": "✅ <b>ID покупателя:</b>",
        "order_method": "✅ <b>Оплата:</b>",
        "order_target": "✅ <b>Цель:</b>",
        "order_target_name": "✅ <b>Имя цели:</b>",
        "order_sent_from": "✅ <b>Отправлено с этого аккаунта</b>",
        "order_hash": "📝 <b>Хэш:</b>",
        "order_desc": "📝 <b>Описание:</b>",
        "order_text": "📝 <b>Текст:</b>",
        "admin_denied": "⛔ Нет доступа.",
        "admin_ok_msg": "✅ Заказ <b>#{order_id}</b> подтверждён.",
        "admin_no_msg": "❌ Заказ <b>#{order_id}</b> отменён.",
        "user_order_ok": "🎉 <b>Заказ подтверждён</b>\n🧾 ID: <code>{order_id}</code>\n💳 Оплата: {method}\n🚀 Скоро начнётся.",
        "user_order_no": "❌ <b>Заказ отменён</b>\n🧾 <code>{order_id}</code>\nВозврат в 24 ч.\n@BanTel_Support",
        "method_card": "💳 Карта", "method_ton": "💎 TON",
        "method_trx": "⚡ TRX", "method_balance": "💰 Баланс",
        "settings_text": "⚙️ <b>Настройки</b>\n━━━━━━━━━━━━━━━━━━━━\nВыберите опцию:",
        "account_text": "👤 <b>Мой аккаунт</b>\n━━━━━━━━━━━━━━━━━━━━\n🟩 <b>Имя:</b> {name}\n🟩 <b>Фамилия:</b> {last}\n🟩 <b>ID:</b> <code>{uid}</code>\n🟦 <b>Юзернейм:</b> {username}\n🟥 <b>Статус:</b> {status}\n💰 <b>Баланс:</b> <b>{balance:,} Toman</b>\n━━━━━━━━━━━━━━━━━━━━",
        "wallet_text": "💰 <b>Ваш кошелёк</b>\n━━━━━━━━━━━━━━━━━━━━\n💳 <b>Баланс:</b> <b>{balance:,} Toman</b>\n━━━━━━━━━━━━━━━━━━━━\n\nВыберите метод пополнения:",
        "wallet_method_text": "💰 <b>Пополнение</b>\n━━━━━━━━━━━━━━━━━━━━\nВыберите способ:",
        "topup_ask_amount_card": "💳 <b>Пополнение картой</b>\n\n💰 Отправьте сумму числом (Toman).\n\n<i>Пример:</i> <code>500000</code>",
        "topup_ask_amount_crypto": "🪙 <b>Крипто-пополнение</b>\n\n💰 Отправьте сумму числом (Toman).\n\n<i>Пример:</i> <code>500000</code>",
        "topup_invalid_amount": "❌ Неверная сумма. Число, минимум 10,000.",
        "topup_card_info": "💳 <b>Реквизиты карты</b>\n━━━━━━━━━━━━━━━━━━━━\n💰 Сумма: <b>{amount:,} Toman</b>\n\nКарта:\n<blockquote><code>6037998133013256</code></blockquote>\n<b>Mahmoud Mohammadi</b>\n━━━━━━━━━━━━━━━━━━━━\n\n📸 Отправьте <b>фото</b>.",
        "topup_ton_info": "💎 <b>Пополнение TON</b>\n━━━━━━━━━━━━━━━━━━━━\n💰 Сумма: <b>{amount:,} Toman</b>\n\nАдрес:\n<blockquote><code>UQDMEy9GsZ6uph0yPtUdj4hRlBaa5hczi1CvOVgmZx7ZIguR</code></blockquote>\n━━━━━━━━━━━━━━━━━━━━\n\n📸 Отправьте <b>фото</b>.",
        "topup_trx_info": "⚡ <b>Пополнение TRX</b>\n━━━━━━━━━━━━━━━━━━━━\n💰 Сумма: <b>{amount:,} Toman</b>\n\nАдрес:\n<blockquote><code>TAE7ZdjFKxkMMsr2AQKq6t3PxwDcSdH4WU</code></blockquote>\n━━━━━━━━━━━━━━━━━━━━\n\n📸 Отправьте <b>фото</b>.",
        "topup_receipt_done": "✅ <b>Чек получен.</b>\n\n⏳ Ждите подтверждения.",
        "balance_insufficient": "❌ <b>Недостаточно средств.</b>\n\n💰 Баланс: <b>{balance:,} Toman</b>\n💳 Нужно: <b>500,000</b>\n\nПополните кошелёк.",
        "balance_paid_msg": "✅ <b>Оплачено с баланса.</b>\n\n💰 Списано: <b>500,000</b>\n💳 Остаток: <b>{balance:,} Toman</b>",
        "tup_new": "💰 <b>Запрос пополнения</b>",
        "tup_amount_lbl": "💰 <b>Сумма:</b>",
        "tup_method_lbl": "💳 <b>Метод:</b>",
        "tup_ok_msg": "✅ <b>Баланс пополнен.</b>\n💰 {amount:,} Toman\n💳 Новый баланс: <b>{balance:,} Toman</b>",
        "tup_no_msg": "❌ <b>Запрос отклонён.</b>\n@BanTel_Support",
    },
    "ar": {
        "welcome_lang": "〽️ <b>مرحباً بك في BannTel</b>\n\n🌐 اختر لغتك:",
        "rules": "❇️ <b>شروط خدمة BannTel</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n🛡 مرحباً. اقرأ الشروط قبل الاستخدام.\n\n⭕️ 1. حظر الحسابات بطريقة 2027.\n⭕️ 2. أدخل ID صحيح.\n⭕️ 3. الإيصالات المزيفة → حظر دائم.\n⭕️ 4. جميع المعاملات مسجلة.\n⭕️ 5. الوقت تقديري.\n⭕️ 6. الاسترداد عند عدم التنفيذ.\n⭕️ 7. المسؤولية على المستخدم.\n⭕️ 8. نحتفظ بحق التغيير.\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n✅ بالضغط أدناه أنت تقبل الشروط.",
        "btn_accept_rules": "✅ أوافق", "btn_reject_rules": "❌ لا أوافق",
        "btn_platform_tg": "✈️ تيليجرام", "btn_platform_wa": "✅ واتساب",
        "btn_start_gift": "🟥 فحص وتجميد",
        "btn_buy_ban": "🛒 شراء طريقة الحظر",
        "btn_settings": "⚙️ الإعدادات",
        "btn_help": "🆘 مساعدة", "btn_support": "🔰 دعم",
        "btn_back_platform": "🔙 العودة لاختيار المنصة",
        "btn_confirm_yes": "✅ تأكيد", "btn_confirm_no": "❌ إلغاء",
        "btn_pay_card": "💳 بطاقة", "btn_pay_crypto": "🪙 عملة رقمية",
        "btn_pay_balance": "💰 من الرصيد",
        "btn_back_menu": "🔙 العودة",
        "btn_crypto_ton": "💎 TON", "btn_crypto_trx": "⚡ TRX",
        "btn_back": "🔙 رجوع",
        "btn_my_account": "👤 حسابي",
        "btn_change_lang": "🌐 تغيير اللغة",
        "btn_wallet": "💰 المحفظة",
        "rules_accepted": "✅ تم القبول", "rules_rejected": "❌ تم الإلغاء",
        "rules_rejected_text": "❌ <b>لم تقبل الشروط.</b>\n\n/start للبدء من جديد.",
        "wa_soon": "⏳ قريباً",
        "platform_text": "🌐 <b>اختر المنصة</b>\n━━━━━━━━━━━━━━━━━━━━\nاختر الخدمة:",
        "welcome": "〽️ <b>Welcome</b>\n📶 مرحباً <b>{name}</b>\n\n⭕️ طريقة حظر حساب تيليجرام في 1-10 دقائق!\n\n⭕️ أقوى طريقة 2026\n\n⭕️ كشف تلقائي للمخالفات\n\n‼️ اختر:",
        "ask_id": "🔎 <b>الفاحص الذكي — 1 من 3</b>\n\nأرسل <b>ID</b> أو <b>اسم المستخدم</b>.\n\n<i>مثال:</i> <code>@username</code>",
        "checking": "⭕️ جاري الاستعلام...",
        "not_found": "❌ <b>الحساب غير موجود.</b>",
        "analysis_header": "⭕️ <b>نتيجة التحليل</b>",
        "lbl_name": "🟩 <b>الاسم:</b>", "lbl_last": "🟩 <b>اللقب:</b>",
        "lbl_id": "🟩 <b>ID:</b>", "lbl_username": "🟦 <b>المستخدم:</b>",
        "lbl_phone": "🟥 <b>الهاتف:</b>", "lbl_premium": "🟦 <b>بريميوم:</b>",
        "lbl_bot": "🟦 <b>بوت:</b>", "lbl_bio": "🟩 <b>بايو:</b>",
        "has": "يوجد", "not_has": "لا يوجد", "yes": "نعم", "no": "لا",
        "lbl_violation": "⭕️ <b>المخالفات:</b>",
        "lbl_freeze_time": "✅ <b>وقت التجميد:</b>", "minute": "دقيقة",
        "ask_confirm": "⭕️ تأكيد شراء خدمة التجميد؟",
        "payment_header": "💠 <b>2 من 3 — الدفع</b>\n━━━━━━━━━━━━━━━━━━━━\n<b>تكلفة الحظر:</b> <b>500,000 Toman</b>\n━━━━━━━━━━━━━━━━━━━━\n\nاختر:",
        "card_text": "✅ <b>الدفع بالبطاقة</b>\n━━━━━━━━━━━━━━━━━━━━\nالمبلغ: <b>500,000 Toman</b>\n\n<blockquote><code>6037998133013256</code></blockquote>\n<b>Mahmoud Mohammadi</b>\n━━━━━━━━━━━━━━━━━━━━\n\n أرسل <b>الصورة</b>.",
        "crypto_text": "🪙 <b>الدفع بالعملة</b>\n━━━━━━━━━━━━━━━━━━━━\nاختر:",
        "ton_text": "💎 <b>TON</b>\n━━━━━━━━━━━━━━━━━━━━\nالمبلغ: <b>1.3 TON</b>\n\n<blockquote><code>UQDMEy9GsZ6uph0yPtUdj4hRlBaa5hczi1CvOVgmZx7ZIguR</code></blockquote>\n━━━━━━━━━━━━━━━━━━━━\n\nأرسل <b>الصورة والهاش</b>.",
        "trx_text": "⚡ <b>TRX</b>\n━━━━━━━━━━━━━━━━━━━━\nالمبلغ: <b>5.70 TRX</b>\n\n<blockquote><code>TAE7ZdjFKxkMMSr2AQKq6t3PxwDcSdH4WU</code></blockquote>\n━━━━━━━━━━━━━━━━━━━━\n\n أرسل <b>الصورة والهاش</b>.",
        "help_text": "✅ <b>الدليل الكامل</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n🔹 1 — المنصة\n🔹 2 — ID\n🔹 3 — التحليل\n🔹 4 — الدفع (بطاقة/عملة/رصيد)\n🔹 5 — الإيصال\n🔹 6 — التأكيد\n\n✅ 5–10 دقائق.\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n🛜 @BanTel_Support",
        "support_text": "⭕️ <b>دعم BannTel</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n✅ 24/7\n\n❇️ @BanTel_Support\n• الرد: خلال ساعة",
        "cancelled": "❌ تم الإلغاء.",
        "confirmed_yes": "✅ تم التأكيد", "confirmed_no": "❌ تم الإلغاء",
        "receipt_photo_ok": "✅ <b>تم استلام الصورة.</b>\n\nأرسل <b>الهاش</b>.",
        "receipt_hash_ok": "✅ <b>تم استلام الهاش.</b>\n\nأرسل <b>الصورة</b>.",
        "receipt_done": "✅ <b>تم استلام المعلومات.</b>\n\n⏳ انتظر التأكيد.",
        "photo_already": "⚠️ الصورة موجودة. أرسل <b>الهاش</b>.",
        "hash_already": "⚠️ الهاش موجود. أرسل <b>الصورة</b>.",
        "invalid_hash_ton": "❌ <b>هاش TON غير صالح.</b>",
        "invalid_hash_trx": "❌ <b>هاش TRX غير صالح.</b>",
        "ask_photo_or_hash": "⚠️ أرسل <b>الصورة أو الهاش</b>.",
        "ask_photo_only": "⚠️ أرسل <b>الصورة</b>.",
        "ask_id_valid": "⚠️ أرسل ID صالح.",
        "order_new": "✅ <b>طلب جديد</b>",
        "order_buyer": "✅ <b>المشتري:</b>",
        "order_buyer_id": "✅ <b>ID المشتري:</b>",
        "order_method": "✅ <b>الدفع:</b>",
        "order_target": "✅ <b>الحساب المستهدف:</b>",
        "order_target_name": "✅ <b>اسم الهدف:</b>",
        "order_sent_from": "✅ <b>أُرسل من هذا الحساب</b>",
        "order_hash": "📝 <b>الهاش:</b>",
        "order_desc": "📝 <b>الوصف:</b>",
        "order_text": "📝 <b>النص:</b>",
        "admin_denied": "⛔ لا تملك صلاحية.",
        "admin_ok_msg": "✅ تم تأكيد <b>#{order_id}</b>.",
        "admin_no_msg": "❌ تم إلغاء <b>#{order_id}</b>.",
        "user_order_ok": "🎉 <b>تم تأكيد طلبك</b>\n🧾 <code>{order_id}</code>\n💳 {method}\n🚀 سيبدأ قريباً.",
        "user_order_no": "❌ <b>تم الإلغاء</b>\n🧾 <code>{order_id}</code>\nالاسترداد خلال 24 ساعة.\n@BanTel_Support",
        "method_card": "💳 بطاقة", "method_ton": "💎 TON",
        "method_trx": "⚡ TRX", "method_balance": "💰 الرصيد",
        "settings_text": "⚙️ <b>الإعدادات</b>\n━━━━━━━━━━━━━━━━━━━━\nاختر:",
        "account_text": "👤 <b>حسابي</b>\n━━━━━━━━━━━━━━━━━━━━\n🟩 <b>الاسم:</b> {name}\n🟩 <b>اللقب:</b> {last}\n🟩 <b>ID:</b> <code>{uid}</code>\n🟦 <b>المستخدم:</b> {username}\n🟥 <b>الحالة:</b> {status}\n💰 <b>الرصيد:</b> <b>{balance:,} Toman</b>\n━━━━━━━━━━━━━━━━━━━━",
        "wallet_text": "💰 <b>محفظتك</b>\n━━━━━━━━━━━━━━━━━━━━\n💳 <b>الرصيد:</b> <b>{balance:,} Toman</b>\n━━━━━━━━━━━━━━━━━━━━\n\nاختر طريقة:",
        "wallet_method_text": "💰 <b>إضافة رصيد</b>\n━━━━━━━━━━━━━━━━━━━━\nاختر:",
        "topup_ask_amount_card": "💳 <b>إضافة بالبطاقة</b>\n\n💰 أرسل المبلغ رقماً.\n\n<i>مثال:</i> <code>500000</code>",
        "topup_ask_amount_crypto": "🪙 <b>إضافة بالعملة</b>\n\n💰 أرسل المبلغ رقماً.\n\n<i>مثال:</i> <code>500000</code>",
        "topup_invalid_amount": "❌ مبلغ غير صالح. الحد الأدنى 10,000.",
        "topup_card_info": "💳 <b>معلومات الدفع</b>\n━━━━━━━━━━━━━━━━━━━━\n💰 <b>{amount:,} Toman</b>\n\n<blockquote><code>6037998133013256</code></blockquote>\n<b>Mahmoud Mohammadi</b>\n━━━━━━━━━━━━━━━━━━━━\n\n📸 أرسل <b>الصورة</b>.",
        "topup_ton_info": "💎 <b>TON</b>\n━━━━━━━━━━━━━━━━━━━━\n💰 <b>{amount:,} Toman</b>\n\n<blockquote><code>UQDMEy9GsZ6uph0yPtUdj4hRlBaa5hczi1CvOVgmZx7ZIguR</code></blockquote>\n━━━━━━━━━━━━━━━━━━━━\n\n📸 أرسل <b>الصورة</b>.",
        "topup_trx_info": "⚡ <b>TRX</b>\n━━━━━━━━━━━━━━━━━━━━\n💰 <b>{amount:,} Toman</b>\n\n<blockquote><code>TAE7ZdjFKxkMMsr2AQKq6t3PxwDcSdH4WU</code></blockquote>\n━━━━━━━━━━━━━━━━━━━━\n\n📸 أرسل <b>الصورة</b>.",
        "topup_receipt_done": "✅ <b>تم استلام الإيصال.</b>\n\n⏳ انتظر الموافقة.",
        "balance_insufficient": "❌ <b>الرصيد غير كافٍ.</b>\n\n💰 <b>{balance:,} Toman</b>\n💳 المطلوب: <b>500,000</b>",
        "balance_paid_msg": "✅ <b>تم الدفع من الرصيد.</b>\n💰 خصم: <b>500,000</b>\n💳 المتبقي: <b>{balance:,} Toman</b>",
        "tup_new": "💰 <b>طلب إضافة رصيد</b>",
        "tup_amount_lbl": "💰 <b>المبلغ:</b>",
        "tup_method_lbl": "💳 <b>الطريقة:</b>",
        "tup_ok_msg": "✅ <b>تمت الإضافة.</b>\n💰 {amount:,} Toman\n💳 الرصيد الجديد: <b>{balance:,} Toman</b>",
        "tup_no_msg": "❌ <b>تم الرفض.</b>\n@BanTel_Support",
    },
    "tr": {
        "welcome_lang": "〽️ <b>BannTel'e Hoş Geldiniz</b>\n\n🌐 Dil seçin:",
        "rules": "❇️ <b>BannTel Şartları</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n🛡 Hoş geldiniz. Kullanmadan önce okuyun.\n\n⭕️ 1. Hesap banlama 2027 yöntemi.\n⭕️ 2. Doğru ID girin.\n⭕️ 3. Sahte makbuz → kalıcı yasak.\n⭕️ 4. Tüm işlemler kaydedilir.\n⭕️ 5. Süre tahminidir.\n⭕️ 6. İade sadece yapılamazsa.\n⭕️ 7. Sorumluluk kullanıcıda.\n⭕️ 8. Şartlar değişebilir.\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n✅ Kabul ediyorsanız devam edin.",
        "btn_accept_rules": "✅ Kabul ediyorum", "btn_reject_rules": "❌ Kabul etmiyorum",
        "btn_platform_tg": "✈️ Telegram", "btn_platform_wa": "✅ WhatsApp",
        "btn_start_gift": "🟥 İhlal & Dondurma",
        "btn_buy_ban": "🛒 Ban Metodu Satın Al",
        "btn_settings": "⚙️ Ayarlar",
        "btn_help": "🆘 Yardım", "btn_support": "🔰 Destek",
        "btn_back_platform": "🔙 Platforma dön",
        "btn_confirm_yes": "✅ Onayla", "btn_confirm_no": "❌ İptal",
        "btn_pay_card": "💳 Kart", "btn_pay_crypto": "🪙 Kripto",
        "btn_pay_balance": "💰 Bakiyeden",
        "btn_back_menu": "🔙 Menüye dön",
        "btn_crypto_ton": "💎 TON", "btn_crypto_trx": "⚡ TRX",
        "btn_back": "🔙 Geri",
        "btn_my_account": "👤 Hesabım",
        "btn_change_lang": "🌐 Dil Değiştir",
        "btn_wallet": "💰 Cüzdan",
        "rules_accepted": "✅ Kabul", "rules_rejected": "❌ İptal",
        "rules_rejected_text": "❌ <b>Şartları kabul etmediniz.</b>\n\n/start ile yeniden.",
        "wa_soon": "⏳ Yakında",
        "platform_text": "🌐 <b>Platform Seçin</b>\n━━━━━━━━━━━━━━━━━━━━\nSeçin:",
        "welcome": "〽️ <b>Welcome</b>\n📶 Merhaba <b>{name}</b>\n\n⭕️ Telegram ban yöntemi 1-10 dakikada!\n\n⭕️ 2026'nın en güçlü yöntemi\n\n⭕️ Otomatik ihlal tespiti\n\n‼️ Seçin:",
        "ask_id": "🔎 <b>Akıllı Test — 1/3</b>\n\nHedef hesabın <b>ID</b> veya <b>kullanıcı adı</b>.\n\n<i>Örnek:</i> <code>@username</code>",
        "checking": "⭕️ Sorgulanıyor...",
        "not_found": "❌ <b>Hesap bulunamadı.</b>",
        "analysis_header": "⭕️ <b>Akıllı Analiz</b>",
        "lbl_name": "🟩 <b>İsim:</b>", "lbl_last": "🟩 <b>Soyisim:</b>",
        "lbl_id": "🟩 <b>ID:</b>", "lbl_username": "🟦 <b>K.A:</b>",
        "lbl_phone": "🟥 <b>Tel:</b>", "lbl_premium": "🟦 <b>Premium:</b>",
        "lbl_bot": "🟦 <b>Bot:</b>", "lbl_bio": "🟩 <b>Bio:</b>",
        "has": "Var", "not_has": "Yok", "yes": "Evet", "no": "Hayır",
        "lbl_violation": "⭕️ <b>İhlal:</b>",
        "lbl_freeze_time": "✅ <b>Süre:</b>", "minute": "dk",
        "ask_confirm": "⭕️ Bu hesap için dondurma hizmeti almak istiyor musunuz?",
        "payment_header": "💠 <b>2/3 — Ödeme</b>\n━━━━━━━━━━━━━━━━━━━━\n<b>Ban ücreti:</b> <b>500,000 Toman</b>\n━━━━━━━━━━━━━━━━━━━━\n\nSeçin:",
        "card_text": "✅ <b>Kart Ödeme</b>\n━━━━━━━━━━━━━━━━━━━━\n<b>500,000 Toman</b>\n\n<blockquote><code>6037998133013256</code></blockquote>\n<b>Mahmoud Mohammadi</b>\n━━━━━━━━━━━━━━━━━━━━\n\n <b>Fotoğraf</b> gönderin.",
        "crypto_text": "🪙 <b>Kripto</b>\n━━━━━━━━━━━━━━━━━━━━\nSeçin:",
        "ton_text": "💎 <b>TON</b>\n━━━━━━━━━━━━━━━━━━━━\n<b>1.3 TON</b>\n\n<blockquote><code>UQDMEy9GsZ6uph0yPtUdj4hRlBaa5hczi1CvOVgmZx7ZIguR</code></blockquote>\n━━━━━━━━━━━━━━━━━━━━\n\n<b>Fotoğraf ve hash</b> gönderin.",
        "trx_text": "⚡ <b>TRX</b>\n━━━━━━━━━━━━━━━━━━━━\n<b>5.70 TRX</b>\n\n<blockquote><code>TAE7ZdjFKxkMMSr2AQKq6t3PxwDcSdH4WU</code></blockquote>\n━━━━━━━━━━━━━━━━━━━━\n\n <b>Fotoğraf ve hash</b> gönderin.",
        "help_text": "✅ <b>Tam Kılavuz</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n🔹 1 — Platform\n🔹 2 — ID\n🔹 3 — Analiz\n🔹 4 — Ödeme (Kart/Kripto/Bakiye)\n🔹 5 — Makbuz\n🔹 6 — Onay\n\n✅ 5–10 dk.\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n🛜 @BanTel_Support",
        "support_text": "⭕️ <b>BannTel Destek</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n✅ 24/7\n\n❇️ @BanTel_Support\n• Yanıt: 1 saat",
        "cancelled": "❌ İptal edildi.",
        "confirmed_yes": "✅ Onaylandı", "confirmed_no": "❌ İptal",
        "receipt_photo_ok": "✅ <b>Fotoğraf alındı.</b>\n\n<b>Hash</b> gönderin.",
        "receipt_hash_ok": "✅ <b>Hash alındı.</b>\n\n<b>Fotoğraf</b> gönderin.",
        "receipt_done": "✅ <b>Bilgiler alındı.</b>\n\n⏳ Onay bekleyin.",
        "photo_already": "⚠️ Fotoğraf var. <b>Hash</b> gönderin.",
        "hash_already": "⚠️ Hash var. <b>Fotoğraf</b> gönderin.",
        "invalid_hash_ton": "❌ <b>Geçersiz TON hash.</b>",
        "invalid_hash_trx": "❌ <b>Geçersiz TRX hash.</b>",
        "ask_photo_or_hash": "⚠️ <b>Fotoğraf veya hash</b> gönderin.",
        "ask_photo_only": "⚠️ <b>Fotoğraf</b> gönderin.",
        "ask_id_valid": "⚠️ Geçerli ID gönderin.",
        "order_new": "✅ <b>Yeni Sipariş</b>",
        "order_buyer": "✅ <b>Alıcı:</b>",
        "order_buyer_id": "✅ <b>Alıcı ID:</b>",
        "order_method": "✅ <b>Ödeme:</b>",
        "order_target": "✅ <b>Hedef:</b>",
        "order_target_name": "✅ <b>Hedef İsim:</b>",
        "order_sent_from": "✅ <b>Bu hesaptan</b>",
        "order_hash": "📝 <b>Hash:</b>",
        "order_desc": "📝 <b>Açıklama:</b>",
        "order_text": "📝 <b>Metin:</b>",
        "admin_denied": "⛔ Erişim yok.",
        "admin_ok_msg": "✅ <b>#{order_id}</b> onaylandı.",
        "admin_no_msg": "❌ <b>#{order_id}</b> iptal edildi.",
        "user_order_ok": "🎉 <b>Onaylandı</b>\n🧾 <code>{order_id}</code>\n💳 {method}\n🚀 Başlıyor.",
        "user_order_no": "❌ <b>İptal edildi</b>\n🧾 <code>{order_id}</code>\n24 saat içinde iade.\n@BanTel_Support",
        "method_card": "💳 Kart", "method_ton": "💎 TON",
        "method_trx": "⚡ TRX", "method_balance": "💰 Bakiye",
        "settings_text": "⚙️ <b>Ayarlar</b>\n━━━━━━━━━━━━━━━━━━━━\nSeçin:",
        "account_text": "👤 <b>Hesabım</b>\n━━━━━━━━━━━━━━━━━━━━\n🟩 <b>İsim:</b> {name}\n🟩 <b>Soyisim:</b> {last}\n🟩 <b>ID:</b> <code>{uid}</code>\n🟦 <b>K.A:</b> {username}\n🟥 <b>Durum:</b> {status}\n💰 <b>Bakiye:</b> <b>{balance:,} Toman</b>\n━━━━━━━━━━━━━━━━━━━━",
        "wallet_text": "💰 <b>Cüzdanınız</b>\n━━━━━━━━━━━━━━━━━━━━\n💳 <b>Bakiye:</b> <b>{balance:,} Toman</b>\n━━━━━━━━━━━━━━━━━━━━\n\nYöntem seçin:",
        "wallet_method_text": "💰 <b>Bakiye Yükle</b>\n━━━━━━━━━━━━━━━━━━━━\nSeçin:",
        "topup_ask_amount_card": "💳 <b>Kart ile Yükleme</b>\n\n💰 Tutarı yazın (Toman).\n\n<i>Örnek:</i> <code>500000</code>",
        "topup_ask_amount_crypto": "🪙 <b>Kripto Yükleme</b>\n\n💰 Tutarı yazın (Toman).\n\n<i>Örnek:</i> <code>500000</code>",
        "topup_invalid_amount": "❌ Geçersiz. Sayı girin (min 10,000).",
        "topup_card_info": "💳 <b>Kart Bilgileri</b>\n━━━━━━━━━━━━━━━━━━━━\n💰 <b>{amount:,} Toman</b>\n\n<blockquote><code>6037998133013256</code></blockquote>\n<b>Mahmoud Mohammadi</b>\n━━━━━━━━━━━━━━━━━━━━\n\n📸 <b>Fotoğraf</b> gönderin.",
        "topup_ton_info": "💎 <b>TON</b>\n━━━━━━━━━━━━━━━━━━━━\n💰 <b>{amount:,} Toman</b>\n\n<blockquote><code>UQDMEy9GsZ6uph0yPtUdj4hRlBaa5hczi1CvOVgmZx7ZIguR</code></blockquote>\n━━━━━━━━━━━━━━━━━━━━\n\n📸 <b>Fotoğraf</b> gönderin.",
        "topup_trx_info": "⚡ <b>TRX</b>\n━━━━━━━━━━━━━━━━━━━━\n💰 <b>{amount:,} Toman</b>\n\n<blockquote><code>TAE7ZdjFKxkMMSr2AQKq6t3PxwDcSdH4WU</code></blockquote>\n━━━━━━━━━━━━━━━━━━━━\n\n📸 <b>Fotoğraf</b> gönderin.",
        "topup_receipt_done": "✅ <b>Makbuz alındı.</b>\n\n⏳ Onay bekleyin.",
        "balance_insufficient": "❌ <b>Yetersiz bakiye.</b>\n\n💰 <b>{balance:,}</b>\n💳 Gerekli: <b>500,000</b>",
        "balance_paid_msg": "✅ <b>Bakiyeden ödendi.</b>\n💰 Kesişen: <b>500,000</b>\n💳 Kalan: <b>{balance:,}</b>",
        "tup_new": "💰 <b>Bakiye Yükleme</b>",
        "tup_amount_lbl": "💰 <b>Tutar:</b>",
        "tup_method_lbl": "💳 <b>Yöntem:</b>",
        "tup_ok_msg": "✅ <b>Yüklendi.</b>\n💰 {amount:,}\n💳 Yeni: <b>{balance:,}</b>",
        "tup_no_msg": "❌ <b>Reddedildi.</b>\n@BanTel_Support",
    },
    "hi": {
        "welcome_lang": "〽️ <b>BannTel Bot में आपका स्वागत है</b>\n\n🌐 भाषा चुनें:",
        "rules": "❇️ <b>BannTel सेवा की शर्तें</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n🛡 स्वागत। उपयोग से पहले पढ़ें।\n\n⭕️ 1. 2027 विधि से खाता प्रतिबंध।\n⭕️ 2. सही ID दर्ज करें।\n⭕️ 3. नकली रसीद → स्थायी प्रतिबंध।\n⭕️ 4. सभी लेनदेन लॉग।\n⭕️ 5. समय अनुमानित।\n⭕️ 6. केवल पूर्ति न होने पर रिफंड।\n⭕️ 7. जिम्मेदारी उपयोगकर्ता की।\n⭕️ 8. शर्तें बदल सकती हैं।\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n✅ नीचे क्लिक करके स्वीकार करें।",
        "btn_accept_rules": "✅ स्वीकार करता हूँ", "btn_reject_rules": "❌ अस्वीकार",
        "btn_platform_tg": "✈️ टेलीग्राम", "btn_platform_wa": "✅ व्हाट्सएप",
        "btn_start_gift": "🟥 जाँच & फ्रीज़",
        "btn_buy_ban": "🛒 बैन मेथड खरीदें",
        "btn_settings": "⚙️ सेटिंग्स",
        "btn_help": "🆘 सहायता", "btn_support": "🔰 समर्थन",
        "btn_back_platform": "🔙 प्लेटफ़ॉर्म चयन पर",
        "btn_confirm_yes": "✅ पुष्टि", "btn_confirm_no": "❌ रद्द",
        "btn_pay_card": "💳 कार्ड", "btn_pay_crypto": "🪙 क्रिप्टो",
        "btn_pay_balance": "💰 बैलेंस से",
        "btn_back_menu": "🔙 मेनू",
        "btn_crypto_ton": "💎 TON", "btn_crypto_trx": "⚡ TRX",
        "btn_back": "🔙 वापस",
        "btn_my_account": "👤 मेरा खाता",
        "btn_change_lang": "🌐 भाषा बदलें",
        "btn_wallet": "💰 वॉलेट",
        "rules_accepted": "✅ स्वीकृत", "rules_rejected": "❌ रद्द",
        "rules_rejected_text": "❌ <b>आपने शर्तें स्वीकार नहीं कीं।</b>\n\n/start से फिर शुरू करें।",
        "wa_soon": "⏳ जल्द",
        "platform_text": "🌐 <b>प्लेटफ़ॉर्म चुनें</b>\n━━━━━━━━━━━━━━━━━━━━\nचुनें:",
        "welcome": "〽️ <b>Welcome</b>\n📶 नमस्ते <b>{name}</b>\n\n⭕️ टेलीग्राम बैन 1-10 मिनट!\n\n⭕️ 2026 की सबसे मजबूत विधि\n\n⭕️ ऑटो पहचान\n\n‼️ चुनें:",
        "ask_id": "🔎 <b>स्मार्ट टेस्ट — 1/3</b>\n\nलक्ष्य का <b>ID</b> या <b>यूज़रनेम</b> भेजें।\n\n<i>उदाहरण:</i> <code>@username</code>",
        "checking": "⭕️ क्वेरी...",
        "not_found": "❌ <b>खाता नहीं मिला।</b>",
        "analysis_header": "⭕️ <b>स्मार्ट विश्लेषण</b>",
        "lbl_name": "🟩 <b>नाम:</b>", "lbl_last": "🟩 <b>उपनाम:</b>",
        "lbl_id": "🟩 <b>ID:</b>", "lbl_username": "🟦 <b>यूज़रनेम:</b>",
        "lbl_phone": "🟥 <b>फोन:</b>", "lbl_premium": "🟦 <b>प्रीमियम:</b>",
        "lbl_bot": "🟦 <b>बॉट:</b>", "lbl_bio": "🟩 <b>बायो:</b>",
        "has": "है", "not_has": "नहीं", "yes": "हाँ", "no": "नहीं",
        "lbl_violation": "⭕️ <b>उल्लंघन:</b>",
        "lbl_freeze_time": "✅ <b>समय:</b>", "minute": "मिनट",
        "ask_confirm": "⭕️ इस खाते के लिए फ्रीज़ खरीदना चाहते हैं?",
        "payment_header": "💠 <b>2/3 — भुगतान</b>\n━━━━━━━━━━━━━━━━━━━━\n<b>शुल्क:</b> <b>500,000 Toman</b>\n━━━━━━━━━━━━━━━━━━━━\n\nचुनें:",
        "card_text": "✅ <b>कार्ड भुगतान</b>\n━━━━━━━━━━━━━━━━━━━━\n<b>500,000 Toman</b>\n\n<blockquote><code>6037998133013256</code></blockquote>\n<b>Mahmoud Mohammadi</b>\n━━━━━━━━━━━━━━━━━━━━\n\n <b>फोटो</b> भेजें।",
        "crypto_text": "🪙 <b>क्रिप्टो</b>\n━━━━━━━━━━━━━━━━━━━━\nचुनें:",
        "ton_text": "💎 <b>TON</b>\n━━━━━━━━━━━━━━━━━━━━\n<b>1.3 TON</b>\n\n<blockquote><code>UQDMEy9GsZ6uph0yPtUdj4hRlBaa5hczi1CvOVgmZx7ZIguR</code></blockquote>\n━━━━━━━━━━━━━━━━━━━━\n\n<b>फोटो और हैश</b> भेजें।",
        "trx_text": "⚡ <b>TRX</b>\n━━━━━━━━━━━━━━━━━━━━\n<b>5.70 TRX</b>\n\n<blockquote><code>TAE7ZdjFKxkMMSr2AQKq6t3PxwDcSdH4WU</code></blockquote>\n━━━━━━━━━━━━━━━━━━━━\n\n <b>फोटो और हैश</b> भेजें।",
        "help_text": "✅ <b>पूर्ण गाइड</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n🔹 1 — प्लेटफ़ॉर्म\n🔹 2 — ID\n🔹 3 — विश्लेषण\n🔹 4 — भुगतान (कार्ड/क्रिप्टो/बैलेंस)\n🔹 5 — रसीद\n🔹 6 — पुष्टि\n\n✅ 5–10 मिनट।\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n🛜 @BanTel_Support",
        "support_text": "⭕️ <b>BannTel सहायता</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n✅ 24/7\n\n❇️ @BanTel_Support\n• उत्तर: 1 घंटा",
        "cancelled": "❌ रद्द।",
        "confirmed_yes": "✅ पुष्टि", "confirmed_no": "❌ रद्द",
        "receipt_photo_ok": "✅ <b>फोटो मिली।</b>\n\n<b>हैश</b> भेजें।",
        "receipt_hash_ok": "✅ <b>हैश मिला।</b>\n\n<b>फोटो</b> भेजें।",
        "receipt_done": "✅ <b>जानकारी मिली।</b>\n\n⏳ इंतज़ार करें।",
        "photo_already": "⚠️ फोटो है। <b>हैश</b> भेजें।",
        "hash_already": "⚠️ हैश है। <b>फोटो</b> भेजें।",
        "invalid_hash_ton": "❌ <b>अमान्य TON हैश।</b>",
        "invalid_hash_trx": "❌ <b>अमान्य TRX हैश।</b>",
        "ask_photo_or_hash": "⚠️ <b>फोटो या हैश</b> भेजें।",
        "ask_photo_only": "⚠️ <b>फोटो</b> भेजें।",
        "ask_id_valid": "⚠️ वैध ID भेजें।",
        "order_new": "✅ <b>नया ऑर्डर</b>",
        "order_buyer": "✅ <b>खरीदार:</b>",
        "order_buyer_id": "✅ <b>खरीदार ID:</b>",
        "order_method": "✅ <b>भुगतान:</b>",
        "order_target": "✅ <b>लक्ष्य:</b>",
        "order_target_name": "✅ <b>लक्ष्य नाम:</b>",
        "order_sent_from": "✅ <b>इस खाते से</b>",
        "order_hash": "📝 <b>हैश:</b>",
        "order_desc": "📝 <b>विवरण:</b>",
        "order_text": "📝 <b>पाठ:</b>",
        "admin_denied": "⛔ पहुँच नहीं।",
        "admin_ok_msg": "✅ <b>#{order_id}</b> पुष्ट।",
        "admin_no_msg": "❌ <b>#{order_id}</b> रद्द।",
        "user_order_ok": "🎉 <b>पुष्ट हुआ</b>\n🧾 <code>{order_id}</code>\n💳 {method}\n🚀 शुरू होगा।",
        "user_order_no": "❌ <b>रद्द</b>\n🧾 <code>{order_id}</code>\n24 घंटे में रिफंड।\n@BanTel_Support",
        "method_card": "💳 कार्ड", "method_ton": "💎 TON",
        "method_trx": "⚡ TRX", "method_balance": "💰 बैलेंस",
        "settings_text": "⚙️ <b>सेटिंग्स</b>\n━━━━━━━━━━━━━━━━━━━━\nचुनें:",
        "account_text": "👤 <b>मेरा खाता</b>\n━━━━━━━━━━━━━━━━━━━━\n🟩 <b>नाम:</b> {name}\n🟩 <b>उपनाम:</b> {last}\n🟩 <b>ID:</b> <code>{uid}</code>\n🟦 <b>यूज़रनेम:</b> {username}\n🟥 <b>स्थिति:</b> {status}\n💰 <b>बैलेंस:</b> <b>{balance:,} Toman</b>\n━━━━━━━━━━━━━━━━━━━━",
        "wallet_text": "💰 <b>वॉलेट</b>\n━━━━━━━━━━━━━━━━━━━━\n💳 <b>बैलेंस:</b> <b>{balance:,} Toman</b>\n━━━━━━━━━━━━━━━━━━━━\n\nतरीका चुनें:",
        "wallet_method_text": "💰 <b>बैलेंस टॉप-अप</b>\n━━━━━━━━━━━━━━━━━━━━\nचुनें:",
        "topup_ask_amount_card": "💳 <b>कार्ड टॉप-अप</b>\n\n💰 राशि भेजें।\n\n<i>उदा:</i> <code>500000</code>",
        "topup_ask_amount_crypto": "🪙 <b>क्रिप्टो टॉप-अप</b>\n\n💰 राशि भेजें।\n\n<i>उदा:</i> <code>500000</code>",
        "topup_invalid_amount": "❌ अमान्य। संख्या भेजें (min 10,000)।",
        "topup_card_info": "💳 <b>कार्ड जानकारी</b>\n━━━━━━━━━━━━━━━━━━━━\n💰 <b>{amount:,} Toman</b>\n\n<blockquote><code>6037998133013256</code></blockquote>\n<b>Mahmoud Mohammadi</b>\n━━━━━━━━━━━━━━━━━━━━\n\n📸 <b>फोटो</b> भेजें।",
        "topup_ton_info": "💎 <b>TON</b>\n━━━━━━━━━━━━━━━━━━━━\n💰 <b>{amount:,} Toman</b>\n\n<blockquote><code>UQDMEy9GsZ6uph0yPtUdj4hRlBaa5hczi1CvOVgmZx7ZIguR</code></blockquote>\n━━━━━━━━━━━━━━━━━━━━\n\n📸 <b>फोटो</b> भेजें।",
        "topup_trx_info": "⚡ <b>TRX</b>\n━━━━━━━━━━━━━━━━━━━━\n💰 <b>{amount:,} Toman</b>\n\n<blockquote><code>TAE7ZdjFKxkMMSr2AQKq6t3PxwDcSdH4WU</code></blockquote>\n━━━━━━━━━━━━━━━━━━━━\n\n📸 <b>फोटो</b> भेजें।",
        "topup_receipt_done": "✅ <b>रसीद मिली।</b>\n\n⏳ इंतज़ार।",
        "balance_insufficient": "❌ <b>अपर्याप्त।</b>\n\n💰 <b>{balance:,}</b>\n💳 चाहिए: <b>500,000</b>",
        "balance_paid_msg": "✅ <b>बैलेंस से भुगतान।</b>\n💰 कटा: <b>500,000</b>\n💳 शेष: <b>{balance:,}</b>",
        "tup_new": "💰 <b>टॉप-अप</b>",
        "tup_amount_lbl": "💰 <b>राशि:</b>",
        "tup_method_lbl": "💳 <b>तरीका:</b>",
        "tup_ok_msg": "✅ <b>हो गया।</b>\n💰 {amount:,}\n💳 नया: <b>{balance:,}</b>",
        "tup_no_msg": "❌ <b>अस्वीकृत।</b>\n@BanTel_Support",
    },
    "es": {
        "welcome_lang": "〽️ <b>Bienvenido a BannTel</b>\n\n🌐 Selecciona idioma:",
        "rules": "❇️ <b>Términos de BannTel</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n🛡 Bienvenido. Lee antes de usar.\n\n⭕️ 1. Ban de cuentas método 2027.\n⭕️ 2. ID correcto.\n⭕️ 3. Recibos falsos → ban permanente.\n⭕️ 4. Todo registrado.\n⭕️ 5. Tiempo estimado.\n⭕️ 6. Reembolso si no se ejecuta.\n⭕️ 7. Responsabilidad del usuario.\n⭕️ 8. Cambios posibles.\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n✅ Al pulsar aceptas.",
        "btn_accept_rules": "✅ Acepto", "btn_reject_rules": "❌ No acepto",
        "btn_platform_tg": "✈️ Telegram", "btn_platform_wa": "✅ WhatsApp",
        "btn_start_gift": "🟥 Verificación y Congelación",
        "btn_buy_ban": "🛒 Comprar Método Ban",
        "btn_settings": "⚙️ Ajustes",
        "btn_help": "🆘 Ayuda", "btn_support": "🔰 Soporte",
        "btn_back_platform": "🔙 Volver a plataformas",
        "btn_confirm_yes": "✅ Confirmar", "btn_confirm_no": "❌ Cancelar",
        "btn_pay_card": "💳 Tarjeta", "btn_pay_crypto": "🪙 Cripto",
        "btn_pay_balance": "💰 Desde saldo",
        "btn_back_menu": "🔙 Menú",
        "btn_crypto_ton": "💎 TON", "btn_crypto_trx": "⚡ TRX",
        "btn_back": "🔙 Atrás",
        "btn_my_account": "👤 Mi cuenta",
        "btn_change_lang": "🌐 Cambiar idioma",
        "btn_wallet": "💰 Cartera",
        "rules_accepted": "✅ Aceptado", "rules_rejected": "❌ Cancelado",
        "rules_rejected_text": "❌ <b>No aceptaste.</b>\n\n/start de nuevo.",
        "wa_soon": "⏳ Pronto",
        "platform_text": "🌐 <b>Elige plataforma</b>\n━━━━━━━━━━━━━━━━━━━━\nElige:",
        "welcome": "〽️ <b>Welcome</b>\n📶 Hola <b>{name}</b>\n\n⭕️ Ban de Telegram en 1-10 min!\n\n⭕️ El método más potente de 2026\n\n⭕️ Detección automática\n\n‼️ Elige:",
        "ask_id": "🔎 <b>Test — Paso 1/3</b>\n\nEnvía el <b>ID</b> o <b>usuario</b> objetivo.\n\n<i>Ejemplo:</i> <code>@username</code>",
        "checking": "⭕️ Consultando...",
        "not_found": "❌ <b>Cuenta no encontrada.</b>",
        "analysis_header": "⭕️ <b>Análisis inteligente</b>",
        "lbl_name": "🟩 <b>Nombre:</b>", "lbl_last": "🟩 <b>Apellido:</b>",
        "lbl_id": "🟩 <b>ID:</b>", "lbl_username": "🟦 <b>Usuario:</b>",
        "lbl_phone": "🟥 <b>Tel:</b>", "lbl_premium": "🟦 <b>Premium:</b>",
        "lbl_bot": "🟦 <b>Bot:</b>", "lbl_bio": "🟩 <b>Bio:</b>",
        "has": "Sí", "not_has": "No", "yes": "Sí", "no": "No",
        "lbl_violation": "⭕️ <b>Violaciones:</b>",
        "lbl_freeze_time": "✅ <b>Tiempo:</b>", "minute": "min",
        "ask_confirm": "⭕️ ¿Comprar el servicio para esta cuenta?",
        "payment_header": "💠 <b>Paso 2/3 — Pago</b>\n━━━━━━━━━━━━━━━━━━━━\n<b>Tarifa:</b> <b>500,000 Toman</b>\n━━━━━━━━━━━━━━━━━━━━\n\nElige:",
        "card_text": "✅ <b>Pago por tarjeta</b>\n━━━━━━━━━━━━━━━━━━━━\n<b>500,000 Toman</b>\n\n<blockquote><code>6037998133013256</code></blockquote>\n<b>Mahmoud Mohammadi</b>\n━━━━━━━━━━━━━━━━━━━━\n\n Envía la <b>foto</b>.",
        "crypto_text": "🪙 <b>Cripto</b>\n━━━━━━━━━━━━━━━━━━━━\nElige:",
        "ton_text": "💎 <b>TON</b>\n━━━━━━━━━━━━━━━━━━━━\n<b>1.3 TON</b>\n\n<blockquote><code>UQDMEy9GsZ6uph0yPtUdj4hRlBaa5hczi1CvOVgmZx7ZIguR</code></blockquote>\n━━━━━━━━━━━━━━━━━━━━\n\nEnvía <b>foto y hash</b>.",
        "trx_text": "⚡ <b>TRX</b>\n━━━━━━━━━━━━━━━━━━━━\n<b>5.70 TRX</b>\n\n<blockquote><code>TAE7ZdjFKxkMMSr2AQKq6t3PxwDcSdH4WU</code></blockquote>\n━━━━━━━━━━━━━━━━━━━━\n\n Envía <b>foto y hash</b>.",
        "help_text": "✅ <b>Guía Completa</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n🔹 1 — Plataforma\n🔹 2 — ID\n🔹 3 — Análisis\n🔹 4 — Pago (Tarjeta/Cripto/Saldo)\n🔹 5 — Recibo\n🔹 6 — Confirmación\n\n✅ 5–10 min.\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n🛜 @BanTel_Support",
        "support_text": "⭕️ <b>Soporte BannTel</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n✅ 24/7\n\n❇️ @BanTel_Support\n• Respuesta: 1h",
        "cancelled": "❌ Cancelado.",
        "confirmed_yes": "✅ Confirmado", "confirmed_no": "❌ Cancelado",
        "receipt_photo_ok": "✅ <b>Foto recibida.</b>\n\nEnvía el <b>hash</b>.",
        "receipt_hash_ok": "✅ <b>Hash recibido.</b>\n\nEnvía la <b>foto</b>.",
        "receipt_done": "✅ <b>Información recibida.</b>\n\n⏳ Espera.",
        "photo_already": "⚠️ Foto ya recibida. <b>Hash</b>.",
        "hash_already": "⚠️ Hash ya recibido. <b>Foto</b>.",
        "invalid_hash_ton": "❌ <b>Hash TON inválido.</b>",
        "invalid_hash_trx": "❌ <b>Hash TRX inválido.</b>",
        "ask_photo_or_hash": "⚠️ Envía <b>foto o hash</b>.",
        "ask_photo_only": "⚠️ Envía <b>foto</b>.",
        "ask_id_valid": "⚠️ ID válido.",
        "order_new": "✅ <b>Nuevo pedido</b>",
        "order_buyer": "✅ <b>Comprador:</b>",
        "order_buyer_id": "✅ <b>ID comprador:</b>",
        "order_method": "✅ <b>Pago:</b>",
        "order_target": "✅ <b>Cuenta:</b>",
        "order_target_name": "✅ <b>Nombre:</b>",
        "order_sent_from": "✅ <b>Desde esta cuenta</b>",
        "order_hash": "📝 <b>Hash:</b>",
        "order_desc": "📝 <b>Descripción:</b>",
        "order_text": "📝 <b>Texto:</b>",
        "admin_denied": "⛔ Sin acceso.",
        "admin_ok_msg": "✅ <b>#{order_id}</b> confirmado.",
        "admin_no_msg": "❌ <b>#{order_id}</b> cancelado.",
        "user_order_ok": "🎉 <b>Confirmado</b>\n🧾 <code>{order_id}</code>\n💳 {method}\n🚀 Comenzando.",
        "user_order_no": "❌ <b>Cancelado</b>\n🧾 <code>{order_id}</code>\nReembolso 24h.\n@BanTel_Support",
        "method_card": "💳 Tarjeta", "method_ton": "💎 TON",
        "method_trx": "⚡ TRX", "method_balance": "💰 Saldo",
        "settings_text": "⚙️ <b>Ajustes</b>\n━━━━━━━━━━━━━━━━━━━━\nElige:",
        "account_text": "👤 <b>Mi cuenta</b>\n━━━━━━━━━━━━━━━━━━━━\n🟩 <b>Nombre:</b> {name}\n🟩 <b>Apellido:</b> {last}\n🟩 <b>ID:</b> <code>{uid}</code>\n🟦 <b>Usuario:</b> {username}\n🟥 <b>Estado:</b> {status}\n💰 <b>Saldo:</b> <b>{balance:,} Toman</b>\n━━━━━━━━━━━━━━━━━━━━",
        "wallet_text": "💰 <b>Tu cartera</b>\n━━━━━━━━━━━━━━━━━━━━\n💳 <b>Saldo:</b> <b>{balance:,} Toman</b>\n━━━━━━━━━━━━━━━━━━━━\n\nElige método:",
        "wallet_method_text": "💰 <b>Recargar saldo</b>\n━━━━━━━━━━━━━━━━━━━━\nElige:",
        "topup_ask_amount_card": "💳 <b>Recarga con tarjeta</b>\n\n💰 Envía el monto (Toman).\n\n<i>Ejemplo:</i> <code>500000</code>",
        "topup_ask_amount_crypto": "🪙 <b>Recarga cripto</b>\n\n💰 Envía el monto (Toman).\n\n<i>Ejemplo:</i> <code>500000</code>",
        "topup_invalid_amount": "❌ Inválido. Número mínimo 10,000.",
        "topup_card_info": "💳 <b>Datos de pago</b>\n━━━━━━━━━━━━━━━━━━━━\n💰 <b>{amount:,} Toman</b>\n\n<blockquote><code>6037998133013256</code></blockquote>\n<b>Mahmoud Mohammadi</b>\n━━━━━━━━━━━━━━━━━━━━\n\n📸 Envía <b>foto</b>.",
        "topup_ton_info": "💎 <b>TON</b>\n━━━━━━━━━━━━━━━━━━━━\n💰 <b>{amount:,} Toman</b>\n\n<blockquote><code>UQDMEy9GsZ6uph0yPtUdj4hRlBaa5hczi1CvOVgmZx7ZIguR</code></blockquote>\n━━━━━━━━━━━━━━━━━━━━\n\n📸 Envía <b>foto</b>.",
        "topup_trx_info": "⚡ <b>TRX</b>\n━━━━━━━━━━━━━━━━━━━━\n💰 <b>{amount:,} Toman</b>\n\n<blockquote><code>TAE7ZdjFKxkMMSr2AQKq6t3PxwDcSdH4WU</code></blockquote>\n━━━━━━━━━━━━━━━━━━━━\n\n📸 Envía <b>foto</b>.",
        "topup_receipt_done": "✅ <b>Recibo recibido.</b>\n\n⏳ Espera.",
        "balance_insufficient": "❌ <b>Saldo insuficiente.</b>\n\n💰 <b>{balance:,}</b>\n💳 Necesario: <b>500,000</b>",
        "balance_paid_msg": "✅ <b>Pagado del saldo.</b>\n💰 Restado: <b>500,000</b>\n💳 Restante: <b>{balance:,}</b>",
        "tup_new": "💰 <b>Recarga</b>",
        "tup_amount_lbl": "💰 <b>Monto:</b>",
        "tup_method_lbl": "💳 <b>Método:</b>",
        "tup_ok_msg": "✅ <b>Recargado.</b>\n💰 {amount:,}\n💳 Nuevo: <b>{balance:,}</b>",
        "tup_no_msg": "❌ <b>Rechazado.</b>\n@BanTel_Support",
    },
    "fr": {
        "welcome_lang": "〽️ <b>Bienvenue sur BannTel</b>\n\n🌐 Choisissez la langue :",
        "rules": "❇️ <b>Conditions BannTel</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n🛡 Bienvenue. Lisez avant usage.\n\n⭕️ 1. Ban de comptes méthode 2027.\n⭕️ 2. ID correct.\n⭕️ 3. Faux reçus → ban permanent.\n⭕️ 4. Tout est enregistré.\n⭕️ 5. Délais estimés.\n⭕️ 6. Remboursement si non exécutable.\n⭕️ 7. Responsabilité utilisateur.\n⭕️ 8. Modifications réservées.\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n✅ En cliquant, vous acceptez.",
        "btn_accept_rules": "✅ J'accepte", "btn_reject_rules": "❌ Je refuse",
        "btn_platform_tg": "✈️ Telegram", "btn_platform_wa": "✅ WhatsApp",
        "btn_start_gift": "🟥 Vérif & Gel",
        "btn_buy_ban": "🛒 Acheter Méthode Ban",
        "btn_settings": "⚙️ Paramètres",
        "btn_help": "🆘 Aide", "btn_support": "🔰 Support",
        "btn_back_platform": "🔙 Retour plateformes",
        "btn_confirm_yes": "✅ Confirmer", "btn_confirm_no": "❌ Annuler",
        "btn_pay_card": "💳 Carte", "btn_pay_crypto": "🪙 Crypto",
        "btn_pay_balance": "💰 Du solde",
        "btn_back_menu": "🔙 Menu",
        "btn_crypto_ton": "💎 TON", "btn_crypto_trx": "⚡ TRX",
        "btn_back": "🔙 Retour",
        "btn_my_account": "👤 Mon compte",
        "btn_change_lang": "🌐 Changer langue",
        "btn_wallet": "💰 Portefeuille",
        "rules_accepted": "✅ Accepté", "rules_rejected": "❌ Annulé",
        "rules_rejected_text": "❌ <b>Non accepté.</b>\n\n/start à nouveau.",
        "wa_soon": "⏳ Bientôt",
        "platform_text": "🌐 <b>Choisir plateforme</b>\n━━━━━━━━━━━━━━━━━━━━\nChoisissez :",
        "welcome": "〽️ <b>Welcome</b>\n📶 Bonjour <b>{name}</b>\n\n⭕️ Ban Telegram en 1-10 min !\n\n⭕️ La méthode la plus puissante 2026\n\n⭕️ Détection auto\n\n‼️ Choisissez :",
        "ask_id": "🔎 <b>Test — Étape 1/3</b>\n\nEnvoyez l'<b>ID</b> ou <b>pseudo</b>.\n\n<i>Ex :</i> <code>@username</code>",
        "checking": "⭕️ Interrogation...",
        "not_found": "❌ <b>Compte introuvable.</b>",
        "analysis_header": "⭕️ <b>Analyse intelligente</b>",
        "lbl_name": "🟩 <b>Prénom :</b>", "lbl_last": "🟩 <b>Nom :</b>",
        "lbl_id": "🟩 <b>ID :</b>", "lbl_username": "🟦 <b>Pseudo :</b>",
        "lbl_phone": "🟥 <b>Tel :</b>", "lbl_premium": "🟦 <b>Premium :</b>",
        "lbl_bot": "🟦 <b>Bot :</b>", "lbl_bio": "🟩 <b>Bio :</b>",
        "has": "Oui", "not_has": "Non", "yes": "Oui", "no": "Non",
        "lbl_violation": "⭕️ <b>Violations :</b>",
        "lbl_freeze_time": "✅ <b>Durée :</b>", "minute": "min",
        "ask_confirm": "⭕️ Confirmer l'achat du service pour ce compte ?",
        "payment_header": "💠 <b>Étape 2/3 — Paiement</b>\n━━━━━━━━━━━━━━━━━━━━\n<b>Frais :</b> <b>500,000 Toman</b>\n━━━━━━━━━━━━━━━━━━━━\n\nChoisissez :",
        "card_text": "✅ <b>Paiement par carte</b>\n━━━━━━━━━━━━━━━━━━━━\n<b>500,000 Toman</b>\n\n<blockquote><code>6037998133013256</code></blockquote>\n<b>Mahmoud Mohammadi</b>\n━━━━━━━━━━━━━━━━━━━━\n\n Envoyez la <b>photo</b>.",
        "crypto_text": "🪙 <b>Crypto</b>\n━━━━━━━━━━━━━━━━━━━━\nChoisissez :",
        "ton_text": "💎 <b>TON</b>\n━━━━━━━━━━━━━━━━━━━━\n<b>1.3 TON</b>\n\n<blockquote><code>UQDMEy9GsZ6uph0yPtUdj4hRlBaa5hczi1CvOVgmZx7ZIguR</code></blockquote>\n━━━━━━━━━━━━━━━━━━━━\n\nEnvoyez <b>photo et hash</b>.",
        "trx_text": "⚡ <b>TRX</b>\n━━━━━━━━━━━━━━━━━━━━\n<b>5.70 TRX</b>\n\n<blockquote><code>TAE7ZdjFKxkMMSr2AQKq6t3PxwDcSdH4WU</code></blockquote>\n━━━━━━━━━━━━━━━━━━━━\n\n Envoyez <b>photo et hash</b>.",
        "help_text": "✅ <b>Guide Complet</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n🔹 1 — Plateforme\n🔹 2 — ID\n🔹 3 — Analyse\n🔹 4 — Paiement (Carte/Crypto/Solde)\n🔹 5 — Reçu\n🔹 6 — Confirmation\n\n✅ 5–10 min.\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n🛜 @BanTel_Support",
        "support_text": "⭕️ <b>Support BannTel</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n✅ 24/7\n\n❇️ @BanTel_Support\n• Réponse : 1h",
        "cancelled": "❌ Annulé.",
        "confirmed_yes": "✅ Confirmé", "confirmed_no": "❌ Annulé",
        "receipt_photo_ok": "✅ <b>Photo reçue.</b>\n\nEnvoyez le <b>hash</b>.",
        "receipt_hash_ok": "✅ <b>Hash reçu.</b>\n\nEnvoyez la <b>photo</b>.",
        "receipt_done": "✅ <b>Infos reçues.</b>\n\n⏳ Patientez.",
        "photo_already": "⚠️ Photo reçue. <b>Hash</b>.",
        "hash_already": "⚠️ Hash reçu. <b>Photo</b>.",
        "invalid_hash_ton": "❌ <b>Hash TON invalide.</b>",
        "invalid_hash_trx": "❌ <b>Hash TRX invalide.</b>",
        "ask_photo_or_hash": "⚠️ <b>Photo ou hash</b>.",
        "ask_photo_only": "⚠️ <b>Photo</b>.",
        "ask_id_valid": "⚠️ ID valide.",
        "order_new": "✅ <b>Nouvelle commande</b>",
        "order_buyer": "✅ <b>Acheteur :</b>",
        "order_buyer_id": "✅ <b>ID acheteur :</b>",
        "order_method": "✅ <b>Paiement :</b>",
        "order_target": "✅ <b>Cible :</b>",
        "order_target_name": "✅ <b>Nom cible :</b>",
        "order_sent_from": "✅ <b>Depuis ce compte</b>",
        "order_hash": "📝 <b>Hash :</b>",
        "order_desc": "📝 <b>Description :</b>",
        "order_text": "📝 <b>Texte :</b>",
        "admin_denied": "⛔ Accès refusé.",
        "admin_ok_msg": "✅ <b>#{order_id}</b> confirmé.",
        "admin_no_msg": "❌ <b>#{order_id}</b> annulé.",
        "user_order_ok": "🎉 <b>Confirmé</b>\n🧾 <code>{order_id}</code>\n💳 {method}\n🚀 Démarre.",
        "user_order_no": "❌ <b>Annulé</b>\n🧾 <code>{order_id}</code>\nRemboursement 24h.\n@BanTel_Support",
        "method_card": "💳 Carte", "method_ton": "💎 TON",
        "method_trx": "⚡ TRX", "method_balance": "💰 Solde",
        "settings_text": "⚙️ <b>Paramètres</b>\n━━━━━━━━━━━━━━━━━━━━\nChoisissez :",
        "account_text": "👤 <b>Mon compte</b>\n━━━━━━━━━━━━━━━━━━━━\n🟩 <b>Prénom :</b> {name}\n🟩 <b>Nom :</b> {last}\n🟩 <b>ID :</b> <code>{uid}</code>\n🟦 <b>Pseudo :</b> {username}\n🟥 <b>Statut :</b> {status}\n💰 <b>Solde :</b> <b>{balance:,} Toman</b>\n━━━━━━━━━━━━━━━━━━━━",
        "wallet_text": "💰 <b>Portefeuille</b>\n━━━━━━━━━━━━━━━━━━━━\n💳 <b>Solde :</b> <b>{balance:,} Toman</b>\n━━━━━━━━━━━━━━━━━━━━\n\nChoisissez :",
        "wallet_method_text": "💰 <b>Recharger</b>\n━━━━━━━━━━━━━━━━━━━━\nChoisissez :",
        "topup_ask_amount_card": "💳 <b>Recharge carte</b>\n\n💰 Envoyez le montant (Toman).\n\n<i>Ex :</i> <code>500000</code>",
        "topup_ask_amount_crypto": "🪙 <b>Recharge crypto</b>\n\n💰 Envoyez le montant (Toman).\n\n<i>Ex :</i> <code>500000</code>",
        "topup_invalid_amount": "❌ Invalide. Nombre min 10,000.",
        "topup_card_info": "💳 <b>Infos de paiement</b>\n━━━━━━━━━━━━━━━━━━━━\n💰 <b>{amount:,} Toman</b>\n\n<blockquote><code>6037998133013256</code></blockquote>\n<b>Mahmoud Mohammadi</b>\n━━━━━━━━━━━━━━━━━━━━\n\n📸 Envoyez <b>photo</b>.",
        "topup_ton_info": "💎 <b>TON</b>\n━━━━━━━━━━━━━━━━━━━━\n💰 <b>{amount:,} Toman</b>\n\n<blockquote><code>UQDMEy9GsZ6uph0yPtUdj4hRlBaa5hczi1CvOVgmZx7ZIguR</code></blockquote>\n━━━━━━━━━━━━━━━━━━━━\n\n📸 Envoyez <b>photo</b>.",
        "topup_trx_info": "⚡ <b>TRX</b>\n━━━━━━━━━━━━━━━━━━━━\n💰 <b>{amount:,} Toman</b>\n\n<blockquote><code>TAE7ZdjFKxkMMSr2AQKq6t3PxwDcSdH4WU</code></blockquote>\n━━━━━━━━━━━━━━━━━━━━\n\n📸 Envoyez <b>photo</b>.",
        "topup_receipt_done": "✅ <b>Reçu.</b>\n\n⏳ Patientez.",
        "balance_insufficient": "❌ <b>Solde insuffisant.</b>\n\n💰 <b>{balance:,}</b>\n💳 Requis : <b>500,000</b>",
        "balance_paid_msg": "✅ <b>Payé du solde.</b>\n💰 Déduit : <b>500,000</b>\n💳 Restant : <b>{balance:,}</b>",
        "tup_new": "💰 <b>Recharge</b>",
        "tup_amount_lbl": "💰 <b>Montant :</b>",
        "tup_method_lbl": "💳 <b>Méthode :</b>",
        "tup_ok_msg": "✅ <b>Rechargé.</b>\n💰 {amount:,}\n💳 Nouveau : <b>{balance:,}</b>",
        "tup_no_msg": "❌ <b>Refusé.</b>\n@BanTel_Support",
    },
    "de": {
        "welcome_lang": "〽️ <b>Willkommen bei BannTel</b>\n\n🌐 Sprache wählen:",
        "rules": "❇️ <b>BannTel Bedingungen</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n🛡 Willkommen. Bitte vor Nutzung lesen.\n\n⭕️ 1. Account-Ban via 2027-Methode.\n⭕️ 2. Korrekte ID.\n⭕️ 3. Gefälschte Belege → dauerhafte Sperre.\n⭕️ 4. Alles protokolliert.\n⭕️ 5. Zeit ist Schätzung.\n⭕️ 6. Rückerstattung nur wenn nicht ausführbar.\n⭕️ 7. Verantwortung beim Nutzer.\n⭕️ 8. Änderungen vorbehalten.\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n✅ Mit Klick akzeptieren Sie.",
        "btn_accept_rules": "✅ Ich akzeptiere", "btn_reject_rules": "❌ Ich lehne ab",
        "btn_platform_tg": "✈️ Telegram", "btn_platform_wa": "✅ WhatsApp",
        "btn_start_gift": "🟥 Prüfung & Einfrieren",
        "btn_buy_ban": "🛒 Ban-Methode kaufen",
        "btn_settings": "⚙️ Einstellungen",
        "btn_help": "🆘 Hilfe", "btn_support": "🔰 Support",
        "btn_back_platform": "🔙 Zurück",
        "btn_confirm_yes": "✅ Bestätigen", "btn_confirm_no": "❌ Abbrechen",
        "btn_pay_card": "💳 Karte", "btn_pay_crypto": "🪙 Krypto",
        "btn_pay_balance": "💰 Vom Guthaben",
        "btn_back_menu": "🔙 Menü",
        "btn_crypto_ton": "💎 TON", "btn_crypto_trx": "⚡ TRX",
        "btn_back": "🔙 Zurück",
        "btn_my_account": "👤 Mein Konto",
        "btn_change_lang": "🌐 Sprache ändern",
        "btn_wallet": "💰 Wallet",
        "rules_accepted": "✅ Akzeptiert", "rules_rejected": "❌ Abgebrochen",
        "rules_rejected_text": "❌ <b>Nicht akzeptiert.</b>\n\n/start erneut.",
        "wa_soon": "⏳ Bald",
        "platform_text": "🌐 <b>Plattform wählen</b>\n━━━━━━━━━━━━━━━━━━━━\nWählen:",
        "welcome": "〽️ <b>Welcome</b>\n📶 Hallo <b>{name}</b>\n\n⭕️ Telegram-Ban in 1-10 Min!\n\n⭕️ Die stärkste 2026-Methode\n\n⭕️ Auto-Erkennung\n\n‼️ Wählen:",
        "ask_id": "🔎 <b>Test — Schritt 1/3</b>\n\nSenden Sie <b>ID</b> oder <b>Benutzername</b>.\n\n<i>Bsp:</i> <code>@username</code>",
        "checking": "⭕️ Abfrage läuft...",
        "not_found": "❌ <b>Konto nicht gefunden.</b>",
        "analysis_header": "⭕️ <b>Intelligente Analyse</b>",
        "lbl_name": "🟩 <b>Vorname:</b>", "lbl_last": "🟩 <b>Nachname:</b>",
        "lbl_id": "🟩 <b>ID:</b>", "lbl_username": "🟦 <b>Benutzer:</b>",
        "lbl_phone": "🟥 <b>Tel:</b>", "lbl_premium": "🟦 <b>Premium:</b>",
        "lbl_bot": "🟦 <b>Bot:</b>", "lbl_bio": "🟩 <b>Bio:</b>",
        "has": "Ja", "not_has": "Nein", "yes": "Ja", "no": "Nein",
        "lbl_violation": "⭕️ <b>Verstöße:</b>",
        "lbl_freeze_time": "✅ <b>Dauer:</b>", "minute": "Min",
        "ask_confirm": "⭕️ Dienst für dieses Konto kaufen?",
        "payment_header": "💠 <b>Schritt 2/3 — Zahlung</b>\n━━━━━━━━━━━━━━━━━━━━\n<b>Gebühr:</b> <b>500,000 Toman</b>\n━━━━━━━━━━━━━━━━━━━━\n\nWählen:",
        "card_text": "✅ <b>Kartenzahlung</b>\n━━━━━━━━━━━━━━━━━━━━\n<b>500,000 Toman</b>\n\n<blockquote><code>6037998133013256</code></blockquote>\n<b>Mahmoud Mohammadi</b>\n━━━━━━━━━━━━━━━━━━━━\n\n Senden Sie das <b>Foto</b>.",
        "crypto_text": "🪙 <b>Krypto</b>\n━━━━━━━━━━━━━━━━━━━━\nWählen:",
        "ton_text": "💎 <b>TON</b>\n━━━━━━━━━━━━━━━━━━━━\n<b>1.3 TON</b>\n\n<blockquote><code>UQDMEy9GsZ6uph0yPtUdj4hRlBaa5hczi1CvOVgmZx7ZIguR</code></blockquote>\n━━━━━━━━━━━━━━━━━━━━\n\nSenden Sie <b>Foto und Hash</b>.",
        "trx_text": "⚡ <b>TRX</b>\n━━━━━━━━━━━━━━━━━━━━\n<b>5.70 TRX</b>\n\n<blockquote><code>TAE7ZdjFKxkMMSr2AQKq6t3PxwDcSdH4WU</code></blockquote>\n━━━━━━━━━━━━━━━━━━━━\n\n Senden Sie <b>Foto und Hash</b>.",
        "help_text": "✅ <b>Komplette Anleitung</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n🔹 1 — Plattform\n🔹 2 — ID\n🔹 3 — Analyse\n🔹 4 — Zahlung (Karte/Krypto/Guthaben)\n🔹 5 — Beleg\n🔹 6 — Bestätigung\n\n✅ 5–10 Min.\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n🛜 @BanTel_Support",
        "support_text": "⭕️ <b>BannTel Support</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n✅ 24/7\n\n❇️ @BanTel_Support\n• Antwort: 1 Std",
        "cancelled": "❌ Abgebrochen.",
        "confirmed_yes": "✅ Bestätigt", "confirmed_no": "❌ Abgebrochen",
        "receipt_photo_ok": "✅ <b>Foto erhalten.</b>\n\nSenden Sie den <b>Hash</b>.",
        "receipt_hash_ok": "✅ <b>Hash erhalten.</b>\n\nSenden Sie das <b>Foto</b>.",
        "receipt_done": "✅ <b>Info erhalten.</b>\n\n⏳ Warten.",
        "photo_already": "⚠️ Foto bereits. <b>Hash</b>.",
        "hash_already": "⚠️ Hash bereits. <b>Foto</b>.",
        "invalid_hash_ton": "❌ <b>Ungültiger TON-Hash.</b>",
        "invalid_hash_trx": "❌ <b>Ungültiger TRX-Hash.</b>",
        "ask_photo_or_hash": "⚠️ <b>Foto oder Hash</b>.",
        "ask_photo_only": "⚠️ <b>Foto</b>.",
        "ask_id_valid": "⚠️ Gültige ID.",
        "order_new": "✅ <b>Neue Bestellung</b>",
        "order_buyer": "✅ <b>Käufer:</b>",
        "order_buyer_id": "✅ <b>Käufer-ID:</b>",
        "order_method": "✅ <b>Zahlung:</b>",
        "order_target": "✅ <b>Ziel:</b>",
        "order_target_name": "✅ <b>Zielname:</b>",
        "order_sent_from": "✅ <b>Von diesem Konto</b>",
        "order_hash": "📝 <b>Hash:</b>",
        "order_desc": "📝 <b>Beschreibung:</b>",
        "order_text": "📝 <b>Text:</b>",
        "admin_denied": "⛔ Kein Zugriff.",
        "admin_ok_msg": "✅ <b>#{order_id}</b> bestätigt.",
        "admin_no_msg": "❌ <b>#{order_id}</b> abgebrochen.",
        "user_order_ok": "🎉 <b>Bestätigt</b>\n🧾 <code>{order_id}</code>\n💳 {method}\n🚀 Startet.",
        "user_order_no": "❌ <b>Abgebrochen</b>\n🧾 <code>{order_id}</code>\nRückerstattung 24h.\n@BanTel_Support",
        "method_card": "💳 Karte", "method_ton": "💎 TON",
        "method_trx": "⚡ TRX", "method_balance": "💰 Guthaben",
        "settings_text": "⚙️ <b>Einstellungen</b>\n━━━━━━━━━━━━━━━━━━━━\nWählen:",
        "account_text": "👤 <b>Mein Konto</b>\n━━━━━━━━━━━━━━━━━━━━\n🟩 <b>Vorname:</b> {name}\n🟩 <b>Nachname:</b> {last}\n🟩 <b>ID:</b> <code>{uid}</code>\n🟦 <b>Benutzer:</b> {username}\n🟥 <b>Status:</b> {status}\n💰 <b>Guthaben:</b> <b>{balance:,} Toman</b>\n━━━━━━━━━━━━━━━━━━━━",
        "wallet_text": "💰 <b>Wallet</b>\n━━━━━━━━━━━━━━━━━━━━\n💳 <b>Guthaben:</b> <b>{balance:,} Toman</b>\n━━━━━━━━━━━━━━━━━━━━\n\nMethode wählen:",
        "wallet_method_text": "💰 <b>Aufladen</b>\n━━━━━━━━━━━━━━━━━━━━\nWählen:",
        "topup_ask_amount_card": "💳 <b>Karten-Aufladung</b>\n\n💰 Betrag senden.\n\n<i>Bsp:</i> <code>500000</code>",
        "topup_ask_amount_crypto": "🪙 <b>Krypto-Aufladung</b>\n\n💰 Betrag senden.\n\n<i>Bsp:</i> <code>500000</code>",
        "topup_invalid_amount": "❌ Ungültig. Zahl min 10,000.",
        "topup_card_info": "💳 <b>Zahlungsdaten</b>\n━━━━━━━━━━━━━━━━━━━━\n💰 <b>{amount:,} Toman</b>\n\n<blockquote><code>6037998133013256</code></blockquote>\n<b>Mahmoud Mohammadi</b>\n━━━━━━━━━━━━━━━━━━━━\n\n📸 Senden Sie <b>Foto</b>.",
        "topup_ton_info": "💎 <b>TON</b>\n━━━━━━━━━━━━━━━━━━━━\n💰 <b>{amount:,} Toman</b>\n\n<blockquote><code>UQDMEy9GsZ6uph0yPtUdj4hRlBaa5hczi1CvOVgmZx7ZIguR</code></blockquote>\n━━━━━━━━━━━━━━━━━━━━\n\n📸 Senden Sie <b>Foto</b>.",
        "topup_trx_info": "⚡ <b>TRX</b>\n━━━━━━━━━━━━━━━━━━━━\n💰 <b>{amount:,} Toman</b>\n\n<blockquote><code>TAE7ZdjFKxkMMSr2AQKq6t3PxwDcSdH4WU</code></blockquote>\n━━━━━━━━━━━━━━━━━━━━\n\n📸 Senden Sie <b>Foto</b>.",
        "topup_receipt_done": "✅ <b>Beleg erhalten.</b>\n\n⏳ Warten.",
        "balance_insufficient": "❌ <b>Guthaben unzureichend.</b>\n\n💰 <b>{balance:,}</b>\n💳 Nötig: <b>500,000</b>",
        "balance_paid_msg": "✅ <b>Vom Guthaben bezahlt.</b>\n💰 Abgezogen: <b>500,000</b>\n💳 Rest: <b>{balance:,}</b>",
        "tup_new": "💰 <b>Aufladung</b>",
        "tup_amount_lbl": "💰 <b>Betrag:</b>",
        "tup_method_lbl": "💳 <b>Methode:</b>",
        "tup_ok_msg": "✅ <b>Aufgeladen.</b>\n💰 {amount:,}\n💳 Neu: <b>{balance:,}</b>",
        "tup_no_msg": "❌ <b>Abgelehnt.</b>\n@BanTel_Support",
    },
    "zh": {
        "welcome_lang": "〽️ <b>欢迎使用 BannTel</b>\n\n🌐 请选择语言：",
        "rules": "❇️ <b>BannTel 服务条款</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n🛡 欢迎。使用前请阅读。\n\n⭕️ 1. 2027 方法封禁账户。\n⭕️ 2. 输入正确 ID。\n⭕️ 3. 虚假收据 → 永久封禁。\n⭕️ 4. 所有交易记录。\n⭕️ 5. 时间为估计。\n⭕️ 6. 仅在无法执行时退款。\n⭕️ 7. 用户承担。\n⭕️ 8. 保留修改权。\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n✅ 点击下方即接受条款。",
        "btn_accept_rules": "✅ 我接受", "btn_reject_rules": "❌ 我不接受",
        "btn_platform_tg": "✈️ Telegram", "btn_platform_wa": "✅ WhatsApp",
        "btn_start_gift": "🟥 检查与冻结",
        "btn_buy_ban": "🛒 购买封禁方法",
        "btn_settings": "⚙️ 设置",
        "btn_help": "🆘 帮助", "btn_support": "🔰 支持",
        "btn_back_platform": "🔙 返回平台",
        "btn_confirm_yes": "✅ 确认", "btn_confirm_no": "❌ 取消",
        "btn_pay_card": "💳 卡对卡", "btn_pay_crypto": "🪙 加密",
        "btn_pay_balance": "💰 从余额",
        "btn_back_menu": "🔙 菜单",
        "btn_crypto_ton": "💎 TON", "btn_crypto_trx": "⚡ TRX",
        "btn_back": "🔙 返回",
        "btn_my_account": "👤 我的账户",
        "btn_change_lang": "🌐 更改语言",
        "btn_wallet": "💰 钱包",
        "rules_accepted": "✅ 已接受", "rules_rejected": "❌ 已取消",
        "rules_rejected_text": "❌ <b>未接受条款。</b>\n\n/start 重新开始。",
        "wa_soon": "⏳ 即将推出",
        "platform_text": "🌐 <b>选择平台</b>\n━━━━━━━━━━━━━━━━━━━━\n选择：",
        "welcome": "〽️ <b>Welcome</b>\n📶 你好 <b>{name}</b>\n\n⭕️ Telegram 账户封禁 1-10 分钟！\n\n⭕️ 2026 最强方法\n\n⭕️ 自动检测\n\n‼️ 选择：",
        "ask_id": "🔎 <b>智能测试 — 第 1/3 步</b>\n\n发送目标的 <b>ID</b> 或 <b>用户名</b>。\n\n<i>示例：</i> <code>@username</code>",
        "checking": "⭕️ 查询中...",
        "not_found": "❌ <b>未找到账户。</b>",
        "analysis_header": "⭕️ <b>智能分析</b>",
        "lbl_name": "🟩 <b>名字：</b>", "lbl_last": "🟩 <b>姓氏：</b>",
        "lbl_id": "🟩 <b>ID：</b>", "lbl_username": "🟦 <b>用户名：</b>",
        "lbl_phone": "🟥 <b>电话：</b>", "lbl_premium": "🟦 <b>高级：</b>",
        "lbl_bot": "🟦 <b>机器人：</b>", "lbl_bio": "🟩 <b>简介：</b>",
        "has": "有", "not_has": "无", "yes": "是", "no": "否",
        "lbl_violation": "⭕️ <b>违规率：</b>",
        "lbl_freeze_time": "✅ <b>冻结时间：</b>", "minute": "分钟",
        "ask_confirm": "⭕️ 确认为此账户购买服务？",
        "payment_header": "💠 <b>第 2/3 步 — 付款</b>\n━━━━━━━━━━━━━━━━━━━━\n<b>费用：</b> <b>500,000 Toman</b>\n━━━━━━━━━━━━━━━━━━━━\n\n选择：",
        "card_text": "✅ <b>卡对卡付款</b>\n━━━━━━━━━━━━━━━━━━━━\n<b>500,000 Toman</b>\n\n<blockquote><code>6037998133013256</code></blockquote>\n<b>Mahmoud Mohammadi</b>\n━━━━━━━━━━━━━━━━━━━━\n\n 发送 <b>截图</b>。",
        "crypto_text": "🪙 <b>加密货币</b>\n━━━━━━━━━━━━━━━━━━━━\n选择：",
        "ton_text": "💎 <b>TON</b>\n━━━━━━━━━━━━━━━━━━━━\n<b>1.3 TON</b>\n\n<blockquote><code>UQDMEy9GsZ6uph0yPtUdj4hRlBaa5hczi1CvOVgmZx7ZIguR</code></blockquote>\n━━━━━━━━━━━━━━━━━━━━\n\n发送 <b>截图和哈希</b>。",
        "trx_text": "⚡ <b>TRX</b>\n━━━━━━━━━━━━━━━━━━━━\n<b>5.70 TRX</b>\n\n<blockquote><code>TAE7ZdjFKxkMMSr2AQKq6t3PxwDcSdH4WU</code></blockquote>\n━━━━━━━━━━━━━━━━━━━━\n\n 发送 <b>截图和哈希</b>。",
        "help_text": "✅ <b>完整指南</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n🔹 1 — 平台\n🔹 2 — ID\n🔹 3 — 分析\n🔹 4 — 付款（卡/加密/余额）\n🔹 5 — 收据\n🔹 6 — 确认\n\n✅ 5–10 分钟。\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n🛜 @BanTel_Support",
        "support_text": "⭕️ <b>BannTel 支持</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n✅ 24/7\n\n❇️ @BanTel_Support\n• 回复：1 小时",
        "cancelled": "❌ 已取消。",
        "confirmed_yes": "✅ 已确认", "confirmed_no": "❌ 已取消",
        "receipt_photo_ok": "✅ <b>收到截图。</b>\n\n发送 <b>哈希</b>。",
        "receipt_hash_ok": "✅ <b>收到哈希。</b>\n\n发送 <b>截图</b>。",
        "receipt_done": "✅ <b>信息已收到。</b>\n\n⏳ 等待确认。",
        "photo_already": "⚠️ 已有截图。发送 <b>哈希</b>。",
        "hash_already": "⚠️ 已有哈希。发送 <b>截图</b>。",
        "invalid_hash_ton": "❌ <b>无效 TON 哈希。</b>",
        "invalid_hash_trx": "❌ <b>无效 TRX 哈希。</b>",
        "ask_photo_or_hash": "⚠️ 发送 <b>截图或哈希</b>。",
        "ask_photo_only": "⚠️ 发送 <b>截图</b>。",
        "ask_id_valid": "⚠️ 发送有效 ID。",
        "order_new": "✅ <b>新订单</b>",
        "order_buyer": "✅ <b>买家：</b>",
        "order_buyer_id": "✅ <b>买家 ID：</b>",
        "order_method": "✅ <b>付款：</b>",
        "order_target": "✅ <b>目标：</b>",
        "order_target_name": "✅ <b>目标名：</b>",
        "order_sent_from": "✅ <b>从此账户发送</b>",
        "order_hash": "📝 <b>哈希：</b>",
        "order_desc": "📝 <b>描述：</b>",
        "order_text": "📝 <b>文本：</b>",
        "admin_denied": "⛔ 无权限。",
        "admin_ok_msg": "✅ <b>#{order_id}</b> 已确认。",
        "admin_no_msg": "❌ <b>#{order_id}</b> 已取消。",
        "user_order_ok": "🎉 <b>已确认</b>\n🧾 <code>{order_id}</code>\n💳 {method}\n🚀 即将开始。",
        "user_order_no": "❌ <b>已取消</b>\n🧾 <code>{order_id}</code>\n24 小时内退款。\n@BanTel_Support",
        "method_card": "💳 卡", "method_ton": "💎 TON",
        "method_trx": "⚡ TRX", "method_balance": "💰 余额",
        "settings_text": "⚙️ <b>设置</b>\n━━━━━━━━━━━━━━━━━━━━\n选择：",
        "account_text": "👤 <b>我的账户</b>\n━━━━━━━━━━━━━━━━━━━━\n🟩 <b>名字：</b> {name}\n🟩 <b>姓氏：</b> {last}\n🟩 <b>ID：</b> <code>{uid}</code>\n🟦 <b>用户名：</b> {username}\n🟥 <b>状态：</b> {status}\n💰 <b>余额：</b> <b>{balance:,} Toman</b>\n━━━━━━━━━━━━━━━━━━━━",
        "wallet_text": "💰 <b>我的钱包</b>\n━━━━━━━━━━━━━━━━━━━━\n💳 <b>余额：</b> <b>{balance:,} Toman</b>\n━━━━━━━━━━━━━━━━━━━━\n\n选择方式：",
        "wallet_method_text": "💰 <b>充值</b>\n━━━━━━━━━━━━━━━━━━━━\n选择：",
        "topup_ask_amount_card": "💳 <b>卡充值</b>\n\n💰 发送金额（Toman）。\n\n<i>示例：</i> <code>500000</code>",
        "topup_ask_amount_crypto": "🪙 <b>加密充值</b>\n\n💰 发送金额（Toman）。\n\n<i>示例：</i> <code>500000</code>",
        "topup_invalid_amount": "❌ 无效。数字最小 10,000。",
        "topup_card_info": "💳 <b>付款信息</b>\n━━━━━━━━━━━━━━━━━━━━\n💰 <b>{amount:,} Toman</b>\n\n<blockquote><code>6037998133013256</code></blockquote>\n<b>Mahmoud Mohammadi</b>\n━━━━━━━━━━━━━━━━━━━━\n\n📸 发送 <b>截图</b>。",
        "topup_ton_info": "💎 <b>TON</b>\n━━━━━━━━━━━━━━━━━━━━\n💰 <b>{amount:,} Toman</b>\n\n<blockquote><code>UQDMEy9GsZ6uph0yPtUdj4hRlBaa5hczi1CvOVgmZx7ZIguR</code></blockquote>\n━━━━━━━━━━━━━━━━━━━━\n\n📸 发送 <b>截图</b>。",
        "topup_trx_info": "⚡ <b>TRX</b>\n━━━━━━━━━━━━━━━━━━━━\n💰 <b>{amount:,} Toman</b>\n\n<blockquote><code>TAE7ZdjFKxkMMSr2AQKq6t3PxwDcSdH4WU</code></blockquote>\n━━━━━━━━━━━━━━━━━━━━\n\n📸 发送 <b>截图</b>。",
        "topup_receipt_done": "✅ <b>已收到收据。</b>\n\n⏳ 等待确认。",
        "balance_insufficient": "❌ <b>余额不足。</b>\n\n💰 <b>{balance:,}</b>\n💳 需要：<b>500,000</b>",
        "balance_paid_msg": "✅ <b>已从余额支付。</b>\n💰 扣除：<b>500,000</b>\n💳 剩余：<b>{balance:,}</b>",
        "tup_new": "💰 <b>充值请求</b>",
        "tup_amount_lbl": "💰 <b>金额：</b>",
        "tup_method_lbl": "💳 <b>方式：</b>",
        "tup_ok_msg": "✅ <b>已充值。</b>\n💰 {amount:,}\n💳 新余额：<b>{balance:,}</b>",
        "tup_no_msg": "❌ <b>已拒绝。</b>\n@BanTel_Support",
    },
}


def t(user_id: int, key: str) -> str:
    lang = user_langs.get(user_id, "fa")
    return TRANSLATIONS.get(lang, TRANSLATIONS["fa"]).get(key, TRANSLATIONS["fa"].get(key, key))


def is_valid_trx_hash(text: str) -> bool:
    return bool(HEX_RE.match(text.strip()))


def is_valid_ton_hash(text: str) -> bool:
    t_ = text.strip()
    if HEX_RE.match(t_):
        return True
    if TON_B64_RE.match(t_) and len(t_) >= 43:
        return True
    return False


def lang_kb() -> InlineKeyboardMarkup:
    items = list(LANG_NAMES.items())
    rows = []
    for i in range(0, len(items), 2):
        row = [InlineKeyboardButton(text=lbl, callback_data=f"lang:{code}", style=ButtonStyle.PRIMARY)
               for code, lbl in items[i:i + 2]]
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def rules_kb(uid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(uid, "btn_accept_rules"), callback_data="accept_rules", style=ButtonStyle.SUCCESS)],
        [InlineKeyboardButton(text=t(uid, "btn_reject_rules"), callback_data="reject_rules", style=ButtonStyle.DANGER)],
    ])


def platform_kb(uid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(uid, "btn_platform_tg"), callback_data="platform_tg", style=ButtonStyle.PRIMARY)],
        [InlineKeyboardButton(text=t(uid, "btn_platform_wa"), callback_data="platform_wa", style=ButtonStyle.SUCCESS)],
    ])


def main_menu_kb(uid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t(uid, "btn_start_gift"), callback_data="start_gift", style=ButtonStyle.PRIMARY),
            InlineKeyboardButton(text=t(uid, "btn_buy_ban"), callback_data="start_gift", style=ButtonStyle.PRIMARY),
        ],
        [InlineKeyboardButton(text=t(uid, "btn_settings"), callback_data="open_settings", style=ButtonStyle.PRIMARY)],
        [
            InlineKeyboardButton(text=t(uid, "btn_help"), callback_data="help", style=ButtonStyle.PRIMARY),
            InlineKeyboardButton(text=t(uid, "btn_support"), callback_data="support", style=ButtonStyle.SUCCESS),
        ],
        [InlineKeyboardButton(text=t(uid, "btn_back_platform"), callback_data="back_platform", style=ButtonStyle.DANGER)],
    ])


def settings_kb(uid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(uid, "btn_my_account"), callback_data="my_account", style=ButtonStyle.PRIMARY)],
        [InlineKeyboardButton(text=t(uid, "btn_wallet"), callback_data="open_wallet", style=ButtonStyle.SUCCESS)],
        [InlineKeyboardButton(text=t(uid, "btn_change_lang"), callback_data="change_lang", style=ButtonStyle.PRIMARY)],
        [InlineKeyboardButton(text=t(uid, "btn_back_menu"), callback_data="back_menu", style=ButtonStyle.DANGER)],
    ])


def confirm_kb(uid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t(uid, "btn_confirm_yes"), callback_data="confirm_yes", style=ButtonStyle.SUCCESS),
            InlineKeyboardButton(text=t(uid, "btn_confirm_no"), callback_data="confirm_no", style=ButtonStyle.DANGER),
        ]
    ])


def payment_kb(uid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(uid, "btn_pay_card"), callback_data="pay_card", style=ButtonStyle.SUCCESS)],
        [InlineKeyboardButton(text=t(uid, "btn_pay_crypto"), callback_data="pay_crypto", style=ButtonStyle.PRIMARY)],
        [InlineKeyboardButton(text=t(uid, "btn_pay_balance"), callback_data="pay_balance", style=ButtonStyle.PRIMARY)],
        [InlineKeyboardButton(text=t(uid, "btn_back_menu"), callback_data="back_menu", style=ButtonStyle.DANGER)],
    ])


def crypto_kb(uid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(uid, "btn_crypto_ton"), callback_data="crypto_ton", style=ButtonStyle.SUCCESS)],
        [InlineKeyboardButton(text=t(uid, "btn_crypto_trx"), callback_data="crypto_trx", style=ButtonStyle.SUCCESS)],
        [InlineKeyboardButton(text=t(uid, "btn_back"), callback_data="back_payment", style=ButtonStyle.DANGER)],
    ])


def back_menu_kb(uid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(uid, "btn_back_menu"), callback_data="back_menu", style=ButtonStyle.DANGER)]
    ])


def wallet_method_kb(uid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(uid, "btn_pay_card"), callback_data="wallet_card", style=ButtonStyle.SUCCESS)],
        [InlineKeyboardButton(text=t(uid, "btn_pay_crypto"), callback_data="wallet_crypto", style=ButtonStyle.PRIMARY)],
        [InlineKeyboardButton(text=t(uid, "btn_back"), callback_data="open_settings", style=ButtonStyle.DANGER)],
    ])


def wallet_crypto_kb(uid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(uid, "btn_crypto_ton"), callback_data="wallet_ton", style=ButtonStyle.SUCCESS)],
        [InlineKeyboardButton(text=t(uid, "btn_crypto_trx"), callback_data="wallet_trx", style=ButtonStyle.SUCCESS)],
        [InlineKeyboardButton(text=t(uid, "btn_back"), callback_data="open_wallet", style=ButtonStyle.DANGER)],
    ])


def admin_ban_kb(oid: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ تأیید", callback_data=f"adm_ok:{oid}", style=ButtonStyle.SUCCESS),
        InlineKeyboardButton(text="❌ کنسل", callback_data=f"adm_no:{oid}", style=ButtonStyle.DANGER),
    ]])


def admin_topup_kb(oid: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ تأیید واریز", callback_data=f"tup_ok:{oid}", style=ButtonStyle.SUCCESS),
        InlineKeyboardButton(text="❌ رد", callback_data=f"tup_no:{oid}", style=ButtonStyle.DANGER),
    ]])


def new_id() -> str:
    return f"{random.randint(100000, 999999)}"


def sender_tag(u) -> str:
    if u.username:
        return f"@{u.username}"
    return f"<a href='tg://user?id={u.id}'>{u.full_name}</a>"


async def init_tg_client():
    global tg_client
    tg_client = TelegramClient("gift_session", API_ID, API_HASH)
    await tg_client.start()
    print("[+] Telethon client started.")


async def fetch_account_info(identifier: str):
    try:
        if identifier.lstrip("-").isdigit():
            entity = await tg_client.get_entity(int(identifier))
        else:
            entity = await tg_client.get_entity(identifier.lstrip("@"))
        full = await tg_client(GetFullUserRequest(entity.id))
        return {
            "id": entity.id,
            "first_name": getattr(entity, "first_name", None) or "—",
            "last_name": getattr(entity, "last_name", None) or "—",
            "username": getattr(entity, "username", None) or "—",
            "phone": getattr(entity, "phone", None) or "—",
            "is_bot": getattr(entity, "bot", False),
            "is_premium": getattr(entity, "premium", False),
            "bio": getattr(full.full_user, "about", None) or "—",
        }
    except (UsernameNotOccupiedError, UsernameInvalidError):
        return None
    except Exception as e:
        print(f"[!] fetch error: {e}")
        return None


@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(GiftFlow.choosing_language)
    await message.answer(TRANSLATIONS["fa"]["welcome_lang"], reply_markup=lang_kb(), parse_mode=ParseMode.HTML)


@dp.callback_query(F.data.startswith("lang:"))
async def cb_pick_lang(call: CallbackQuery, state: FSMContext):
    lang = call.data.split(":", 1)[1]
    if lang not in TRANSLATIONS:
        lang = "fa"
    uid = call.from_user.id
    user_langs[uid] = lang
    await call.answer(LANG_NAMES[lang])
    await state.set_state(GiftFlow.waiting_rules)
    await call.message.edit_text(TRANSLATIONS[lang]["rules"], reply_markup=rules_kb(uid), parse_mode=ParseMode.HTML)


@dp.callback_query(F.data == "accept_rules")
async def cb_accept_rules(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    await call.answer(t(uid, "rules_accepted"))
    await state.set_state(GiftFlow.choosing_platform)
    await call.message.edit_text(t(uid, "platform_text"), reply_markup=platform_kb(uid), parse_mode=ParseMode.HTML)


@dp.callback_query(F.data == "reject_rules")
async def cb_reject_rules(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    await call.answer(t(uid, "rules_rejected"))
    await state.clear()
    await call.message.edit_text(t(uid, "rules_rejected_text"), parse_mode=ParseMode.HTML)


@dp.callback_query(F.data == "platform_wa")
async def cb_platform_wa(call: CallbackQuery):
    await call.answer(t(call.from_user.id, "wa_soon"), show_alert=True)


@dp.callback_query(F.data == "platform_tg")
async def cb_platform_tg(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    await call.answer()
    await state.clear()
    name = call.from_user.first_name or "User"
    await call.message.edit_text(t(uid, "welcome").format(name=name), reply_markup=main_menu_kb(uid), parse_mode=ParseMode.HTML)


@dp.callback_query(F.data == "back_platform")
async def cb_back_platform(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    await call.answer()
    await state.set_state(GiftFlow.choosing_platform)
    await call.message.edit_text(t(uid, "platform_text"), reply_markup=platform_kb(uid), parse_mode=ParseMode.HTML)


@dp.callback_query(F.data == "start_gift")
async def cb_start_gift(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    await call.answer()
    await state.set_state(GiftFlow.waiting_for_id)
    await call.message.edit_text(t(uid, "ask_id"), reply_markup=back_menu_kb(uid), parse_mode=ParseMode.HTML)


@dp.callback_query(F.data == "back_menu")
async def cb_back_menu(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    await call.answer()
    await state.clear()
    name = call.from_user.first_name or "User"
    await call.message.edit_text(t(uid, "welcome").format(name=name), reply_markup=main_menu_kb(uid), parse_mode=ParseMode.HTML)


@dp.callback_query(F.data == "help")
async def cb_help(call: CallbackQuery):
    uid = call.from_user.id
    await call.answer()
    await call.message.edit_text(t(uid, "help_text"), reply_markup=back_menu_kb(uid), parse_mode=ParseMode.HTML)


@dp.callback_query(F.data == "support")
async def cb_support(call: CallbackQuery):
    uid = call.from_user.id
    await call.answer()
    await call.message.edit_text(t(uid, "support_text"), reply_markup=back_menu_kb(uid), parse_mode=ParseMode.HTML)


@dp.callback_query(F.data == "open_settings")
async def cb_open_settings(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    await call.answer()
    await state.set_state(GiftFlow.settings_menu)
    await call.message.edit_text(t(uid, "settings_text"), reply_markup=settings_kb(uid), parse_mode=ParseMode.HTML)


@dp.callback_query(F.data == "my_account")
async def cb_my_account(call: CallbackQuery):
    uid = call.from_user.id
    await call.answer()
    u = call.from_user
    balance = user_balances.get(uid, 0)
    if u.username:
        username = f"@{u.username}"
    else:
        username = "—"
    status = "Premium ⭐" if getattr(u, "is_premium", False) else "Free"
    text = t(uid, "account_text").format(
        name=u.first_name or "—",
        last=u.last_name or "—",
        uid=uid,
        username=username,
        status=status,
        balance=balance,
    )
    await call.message.edit_text(text, reply_markup=settings_kb(uid), parse_mode=ParseMode.HTML)


@dp.callback_query(F.data == "change_lang")
async def cb_change_lang(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    await call.answer()
    await state.set_state(GiftFlow.settings_change_lang)
    await call.message.edit_text(
        TRANSLATIONS["fa"]["welcome_lang"],
        reply_markup=lang_kb(),
        parse_mode=ParseMode.HTML
    )


@dp.callback_query(F.data.startswith("lang:"))
async def cb_lang_selected(call: CallbackQuery, state: FSMContext):
    lang = call.data.split(":", 1)[1]
    if lang not in TRANSLATIONS:
        lang = "fa"
    uid = call.from_user.id
    prev = user_langs.get(uid)
    user_langs[uid] = lang
    await call.answer(LANG_NAMES[lang])
    if prev is not None and state is not None:
        cur = await state.get_state()
        if cur == GiftFlow.settings_change_lang.state:
            await state.set_state(GiftFlow.settings_menu)
            await call.message.edit_text(t(uid, "settings_text"), reply_markup=settings_kb(uid), parse_mode=ParseMode.HTML)
            return
    await state.set_state(GiftFlow.waiting_rules)
    await call.message.edit_text(TRANSLATIONS[lang]["rules"], reply_markup=rules_kb(uid), parse_mode=ParseMode.HTML)


@dp.callback_query(F.data == "open_wallet")
async def cb_open_wallet(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    await call.answer()
    await state.set_state(GiftFlow.wallet_menu)
    balance = user_balances.get(uid, 0)
    await call.message.edit_text(
        t(uid, "wallet_text").format(balance=balance),
        reply_markup=wallet_method_kb(uid),
        parse_mode=ParseMode.HTML
    )


@dp.callback_query(F.data == "wallet_card")
async def cb_wallet_card(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    await call.answer()
    await state.set_state(GiftFlow.wallet_wait_amount)
    await state.update_data(wallet_method="card")
    await call.message.edit_text(
        t(uid, "topup_ask_amount_card"),
        reply_markup=back_menu_kb(uid),
        parse_mode=ParseMode.HTML
    )


@dp.callback_query(F.data == "wallet_crypto")
async def cb_wallet_crypto(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    await call.answer()
    await state.set_state(GiftFlow.wallet_choose_crypto)
    await call.message.edit_text(
        t(uid, "crypto_text"),
        reply_markup=wallet_crypto_kb(uid),
        parse_mode=ParseMode.HTML
    )


@dp.callback_query(F.data == "wallet_ton")
async def cb_wallet_ton(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    await call.answer()
    await state.set_state(GiftFlow.wallet_wait_amount)
    await state.update_data(wallet_method="ton")
    await call.message.edit_text(
        t(uid, "topup_ask_amount_crypto"),
        reply_markup=back_menu_kb(uid),
        parse_mode=ParseMode.HTML
    )


@dp.callback_query(F.data == "wallet_trx")
async def cb_wallet_trx(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    await call.answer()
    await state.set_state(GiftFlow.wallet_wait_amount)
    await state.update_data(wallet_method="trx")
    await call.message.edit_text(
        t(uid, "topup_ask_amount_crypto"),
        reply_markup=back_menu_kb(uid),
        parse_mode=ParseMode.HTML
    )


@dp.message(GiftFlow.wallet_wait_amount)
async def process_wallet_amount(message: Message, state: FSMContext):
    uid = message.from_user.id
    raw = (message.text or "").strip().replace(",", "").replace("،", "").replace(" ", "")
    if not raw.isdigit():
        await message.answer(t(uid, "topup_invalid_amount"), parse_mode=ParseMode.HTML)
        return
    amount = int(raw)
    if amount < 10000:
        await message.answer(t(uid, "topup_invalid_amount"), parse_mode=ParseMode.HTML)
        return
    data = await state.get_data()
    method = data.get("wallet_method", "card")
    await state.update_data(wallet_amount=amount)
    if method == "card":
        await state.set_state(GiftFlow.wallet_card_receipt)
        await message.answer(
            t(uid, "topup_card_info").format(amount=amount),
            reply_markup=back_menu_kb(uid),
            parse_mode=ParseMode.HTML
        )
    elif method == "ton":
        await state.set_state(GiftFlow.wallet_ton_receipt)
        await message.answer(
            t(uid, "topup_ton_info").format(amount=amount),
            reply_markup=back_menu_kb(uid),
            parse_mode=ParseMode.HTML
        )
    else:
        await state.set_state(GiftFlow.wallet_trx_receipt)
        await message.answer(
            t(uid, "topup_trx_info").format(amount=amount),
            reply_markup=back_menu_kb(uid),
            parse_mode=ParseMode.HTML
        )


async def finalize_topup(message: Message, state: FSMContext, method_key: str):
    uid = message.from_user.id
    data = await state.get_data()
    amount = data.get("wallet_amount", 0)
    user = message.from_user

    oid = new_id()
    topup_orders[oid] = {
        "user_id": uid,
        "amount": amount,
        "method": method_key,
    }

    caption = (
        f"{t(uid, 'tup_new')} #{oid}\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>{sender_tag(user)}</b>\n"
        f"🆔 <code>{uid}</code>\n"
        f"{t(uid, 'tup_amount_lbl')} <b>{amount:,} Toman</b>\n"
        f"{t(uid, 'tup_method_lbl')} {t(uid, method_key)}\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"{t(uid, 'order_sent_from')}"
    )

    if message.photo:
        await bot.send_photo(
            chat_id=ADMIN_ID,
            photo=message.photo[-1].file_id,
            caption=caption,
            reply_markup=admin_topup_kb(oid),
            parse_mode=ParseMode.HTML
        )
    else:
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=caption + f"\n\n{message.text or '—'}",
            reply_markup=admin_topup_kb(oid),
            parse_mode=ParseMode.HTML
        )

    await state.clear()
    await message.answer(t(uid, "topup_receipt_done"), reply_markup=main_menu_kb(uid), parse_mode=ParseMode.HTML)


@dp.message(GiftFlow.wallet_card_receipt)
async def process_wallet_card_receipt(message: Message, state: FSMContext):
    uid = message.from_user.id
    if not message.photo:
        await message.answer(t(uid, "ask_photo_only"), parse_mode=ParseMode.HTML)
        return
    await finalize_topup(message, state, "method_card")


@dp.message(GiftFlow.wallet_ton_receipt)
async def process_wallet_ton_receipt(message: Message, state: FSMContext):
    uid = message.from_user.id
    if not message.photo:
        await message.answer(t(uid, "ask_photo_only"), parse_mode=ParseMode.HTML)
        return
    await finalize_topup(message, state, "method_ton")


@dp.message(GiftFlow.wallet_trx_receipt)
async def process_wallet_trx_receipt(message: Message, state: FSMContext):
    uid = message.from_user.id
    if not message.photo:
        await message.answer(t(uid, "ask_photo_only"), parse_mode=ParseMode.HTML)
        return
    await finalize_topup(message, state, "method_trx")


@dp.message(GiftFlow.waiting_for_id)
async def process_id(message: Message, state: FSMContext):
    uid = message.from_user.id
    raw = (message.text or "").strip()
    if not raw:
        await message.answer(t(uid, "ask_id_valid"))
        return
    wait_msg = await message.answer(t(uid, "checking"))
    info = await fetch_account_info(raw)
    if info is None:
        await wait_msg.edit_text(t(uid, "not_found"), reply_markup=back_menu_kb(uid), parse_mode=ParseMode.HTML)
        return
    await state.update_data(target=info)
    beauty = random.randint(70, 100)
    eta = random.randint(5, 10)
    username_str = f"@{info['username']}" if info['username'] != "—" else "—"
    text = (
        f"{t(uid, 'analysis_header')}\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"{t(uid, 'lbl_name')} {info['first_name']}\n"
        f"{t(uid, 'lbl_last')} {info['last_name']}\n"
        f"{t(uid, 'lbl_id')} <code>{info['id']}</code>\n"
        f"{t(uid, 'lbl_username')} {username_str}\n"
        f"{t(uid, 'lbl_phone')} {info['phone']}\n"
        f"{t(uid, 'lbl_premium')} {t(uid, 'has') if info['is_premium'] else t(uid, 'not_has')}\n"
        f"{t(uid, 'lbl_bot')} {t(uid, 'yes') if info['is_bot'] else t(uid, 'no')}\n"
        f"{t(uid, 'lbl_bio')} {info['bio']}\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"{t(uid, 'lbl_violation')} <b>{beauty}%</b>\n"
        f"{t(uid, 'lbl_freeze_time')} <b>{eta} {t(uid, 'minute')}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{t(uid, 'ask_confirm')}"
    )
    await state.set_state(GiftFlow.confirming)
    await wait_msg.edit_text(text, reply_markup=confirm_kb(uid), parse_mode=ParseMode.HTML)


@dp.callback_query(F.data == "confirm_yes")
async def cb_confirm_yes(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    await call.answer(t(uid, "confirmed_yes"))
    await state.set_state(GiftFlow.choosing_payment)
    await call.message.edit_text(t(uid, "payment_header"), reply_markup=payment_kb(uid), parse_mode=ParseMode.HTML)


@dp.callback_query(F.data == "confirm_no")
async def cb_confirm_no(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    await call.answer(t(uid, "confirmed_no"))
    await state.clear()
    await call.message.edit_text(t(uid, "cancelled"), reply_markup=main_menu_kb(uid))


@dp.callback_query(F.data == "back_payment")
async def cb_back_payment(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    await call.answer()
    await state.set_state(GiftFlow.choosing_payment)
    await call.message.edit_text(t(uid, "payment_header"), reply_markup=payment_kb(uid), parse_mode=ParseMode.HTML)


@dp.callback_query(F.data == "pay_card")
async def cb_pay_card(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    await call.answer()
    await state.set_state(GiftFlow.waiting_card_receipt)
    await call.message.edit_text(t(uid, "card_text"), reply_markup=back_menu_kb(uid), parse_mode=ParseMode.HTML)


@dp.callback_query(F.data == "pay_crypto")
async def cb_pay_crypto(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    await call.answer()
    await state.set_state(GiftFlow.choosing_crypto)
    await call.message.edit_text(t(uid, "crypto_text"), reply_markup=crypto_kb(uid), parse_mode=ParseMode.HTML)


@dp.callback_query(F.data == "crypto_ton")
async def cb_crypto_ton(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    await call.answer()
    await state.set_state(GiftFlow.waiting_ton_receipt)
    await state.update_data(ton_photo_id=None, ton_hash=None)
    await call.message.edit_text(t(uid, "ton_text"), reply_markup=back_menu_kb(uid), parse_mode=ParseMode.HTML)


@dp.callback_query(F.data == "crypto_trx")
async def cb_crypto_trx(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    await call.answer()
    await state.set_state(GiftFlow.waiting_trx_receipt)
    await state.update_data(trx_photo_id=None, trx_hash=None)
    await call.message.edit_text(t(uid, "trx_text"), reply_markup=back_menu_kb(uid), parse_mode=ParseMode.HTML)


@dp.callback_query(F.data == "pay_balance")
async def cb_pay_balance(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    await call.answer()
    data = await state.get_data()
    target = data.get("target", {})
    balance = user_balances.get(uid, 0)
    if balance < BAN_PRICE:
        await call.message.edit_text(
            t(uid, "balance_insufficient").format(balance=balance),
            reply_markup=payment_kb(uid),
            parse_mode=ParseMode.HTML
        )
        return

    user_balances[uid] = balance - BAN_PRICE
    new_balance = user_balances[uid]

    oid = new_id()
    ban_orders[oid] = {
        "user_id": uid,
        "method": "method_balance",
        "target": target,
    }

    caption = (
        f"{t(uid, 'order_new')} #{oid}\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"{t(uid, 'order_buyer')} {sender_tag(call.from_user)}\n"
        f"{t(uid, 'order_buyer_id')} <code>{uid}</code>\n"
        f"{t(uid, 'order_method')} {t(uid, 'method_balance')}\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"{t(uid, 'order_target')} <code>{target.get('id', '—')}</code>\n"
        f"{t(uid, 'order_target_name')} {target.get('first_name', '—')} {target.get('last_name', '—')}\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 <b>Paid from balance — {BAN_PRICE:,} Toman deducted</b>"
    )

    await bot.send_message(
        chat_id=ADMIN_ID,
        text=caption,
        reply_markup=admin_ban_kb(oid),
        parse_mode=ParseMode.HTML
    )

    await state.clear()
    await call.message.edit_text(
        t(uid, "balance_paid_msg").format(balance=new_balance),
        reply_markup=main_menu_kb(uid),
        parse_mode=ParseMode.HTML
    )


async def finalize_ban_order(message: Message, state: FSMContext, method_key: str, photo_id: str = None, hash_text: str = None):
    uid = message.from_user.id
    data = await state.get_data()
    target = data.get("target", {})
    user = message.from_user

    oid = new_id()
    ban_orders[oid] = {
        "user_id": uid,
        "method": method_key,
        "target": target,
    }

    caption = (
        f"{t(uid, 'order_new')} #{oid}\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"{t(uid, 'order_buyer')} {sender_tag(user)}\n"
        f"{t(uid, 'order_buyer_id')} <code>{uid}</code>\n"
        f"{t(uid, 'order_method')} {t(uid, method_key)}\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"{t(uid, 'order_target')} <code>{target.get('id', '—')}</code>\n"
        f"{t(uid, 'order_target_name')} {target.get('first_name', '—')} {target.get('last_name', '—')}\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"{t(uid, 'order_sent_from')}"
    )

    if photo_id:
        await bot.send_photo(
            chat_id=ADMIN_ID,
            photo=photo_id,
            caption=caption,
            reply_markup=admin_ban_kb(oid),
            parse_mode=ParseMode.HTML
        )
        if hash_text:
            await bot.send_message(
                chat_id=ADMIN_ID,
                text=f"{t(uid, 'order_hash')}\n<code>{hash_text}</code>",
                parse_mode=ParseMode.HTML
            )
    else:
        text_body = caption
        if message.photo and message.caption:
            text_body += f"\n\n{t(uid, 'order_desc')}\n{message.caption}"
        elif message.text:
            text_body += f"\n\n{t(uid, 'order_text')}\n{message.text}"
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=text_body,
            reply_markup=admin_ban_kb(oid),
            parse_mode=ParseMode.HTML
        )

    await state.clear()
    await message.answer(t(uid, "receipt_done"), reply_markup=main_menu_kb(uid), parse_mode=ParseMode.HTML)


@dp.message(GiftFlow.waiting_card_receipt)
async def process_card_receipt(message: Message, state: FSMContext):
    uid = message.from_user.id
    if not message.photo and not message.text:
        await message.answer(t(uid, "ask_photo_only"), parse_mode=ParseMode.HTML)
        return
    await finalize_ban_order(message, state, "method_card")


@dp.message(GiftFlow.waiting_ton_receipt)
async def process_ton_receipt(message: Message, state: FSMContext):
    uid = message.from_user.id
    data = await state.get_data()
    photo_id = data.get("ton_photo_id")
    saved_hash = data.get("ton_hash")

    if message.photo:
        new_photo = message.photo[-1].file_id
        if message.caption:
            if not is_valid_ton_hash(message.caption):
                await message.answer(t(uid, "invalid_hash_ton"), parse_mode=ParseMode.HTML)
                return
            await finalize_ban_order(message, state, "method_ton", new_photo, message.caption)
            return
        if photo_id:
            await message.answer(t(uid, "photo_already"), parse_mode=ParseMode.HTML)
            return
        if saved_hash:
            await finalize_ban_order(message, state, "method_ton", new_photo, saved_hash)
            return
        await state.update_data(ton_photo_id=new_photo)
        await message.answer(t(uid, "receipt_photo_ok"), parse_mode=ParseMode.HTML)
        return

    if message.text:
        if not is_valid_ton_hash(message.text):
            await message.answer(t(uid, "invalid_hash_ton"), parse_mode=ParseMode.HTML)
            return
        if saved_hash:
            await message.answer(t(uid, "hash_already"), parse_mode=ParseMode.HTML)
            return
        if photo_id:
            await finalize_ban_order(message, state, "method_ton", photo_id, message.text)
            return
        await state.update_data(ton_hash=message.text)
        await message.answer(t(uid, "receipt_hash_ok"), parse_mode=ParseMode.HTML)
        return

    await message.answer(t(uid, "ask_photo_or_hash"), parse_mode=ParseMode.HTML)


@dp.message(GiftFlow.waiting_trx_receipt)
async def process_trx_receipt(message: Message, state: FSMContext):
    uid = message.from_user.id
    data = await state.get_data()
    photo_id = data.get("trx_photo_id")
    saved_hash = data.get("trx_hash")

    if message.photo:
        new_photo = message.photo[-1].file_id
        if message.caption:
            if not is_valid_trx_hash(message.caption):
                await message.answer(t(uid, "invalid_hash_trx"), parse_mode=ParseMode.HTML)
                return
            await finalize_ban_order(message, state, "method_trx", new_photo, message.caption)
            return
        if photo_id:
            await message.answer(t(uid, "photo_already"), parse_mode=ParseMode.HTML)
            return
        if saved_hash:
            await finalize_ban_order(message, state, "method_trx", new_photo, saved_hash)
            return
        await state.update_data(trx_photo_id=new_photo)
        await message.answer(t(uid, "receipt_photo_ok"), parse_mode=ParseMode.HTML)
        return

    if message.text:
        if not is_valid_trx_hash(message.text):
            await message.answer(t(uid, "invalid_hash_trx"), parse_mode=ParseMode.HTML)
            return
        if saved_hash:
            await message.answer(t(uid, "hash_already"), parse_mode=ParseMode.HTML)
            return
        if photo_id:
            await finalize_ban_order(message, state, "method_trx", photo_id, message.text)
            return
        await state.update_data(trx_hash=message.text)
        await message.answer(t(uid, "receipt_hash_ok"), parse_mode=ParseMode.HTML)
        return

    await message.answer(t(uid, "ask_photo_or_hash"), parse_mode=ParseMode.HTML)


@dp.callback_query(F.data.startswith("adm_ok:"))
async def cb_admin_ok(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("⛔", show_alert=True)
        return
    oid = call.data.split(":", 1)[1]
    order = ban_orders.get(oid)
    await call.answer("✅")
    await call.message.edit_reply_markup(reply_markup=None)
    await call.message.reply(f"✅ <b>#{oid}</b>", parse_mode=ParseMode.HTML)
    if order:
        try:
            uid = order["user_id"]
            text = t(uid, "user_order_ok").format(order_id=oid, method=t(uid, order["method"]))
            await bot.send_message(chat_id=uid, text=text, parse_mode=ParseMode.HTML)
        except Exception as e:
            print(f"[!] notify error: {e}")


@dp.callback_query(F.data.startswith("adm_no:"))
async def cb_admin_no(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("⛔", show_alert=True)
        return
    oid = call.data.split(":", 1)[1]
    order = ban_orders.get(oid)
    await call.answer("❌")
    await call.message.edit_reply_markup(reply_markup=None)
    await call.message.reply(f"❌ <b>#{oid}</b>", parse_mode=ParseMode.HTML)
    if order:
        uid = order["user_id"]
        if order["method"] == "method_balance":
            user_balances[uid] = user_balances.get(uid, 0) + BAN_PRICE
        try:
            text = t(uid, "user_order_no").format(order_id=oid)
            await bot.send_message(chat_id=uid, text=text, parse_mode=ParseMode.HTML)
        except Exception as e:
            print(f"[!] notify error: {e}")


@dp.callback_query(F.data.startswith("tup_ok:"))
async def cb_topup_ok(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("⛔", show_alert=True)
        return
    oid = call.data.split(":", 1)[1]
    order = topup_orders.get(oid)
    await call.answer("✅")
    await call.message.edit_reply_markup(reply_markup=None)
    await call.message.reply(f"✅ Top-up <b>#{oid}</b>", parse_mode=ParseMode.HTML)
    if order:
        uid = order["user_id"]
        amount = order["amount"]
        user_balances[uid] = user_balances.get(uid, 0) + amount
        try:
            text = t(uid, "tup_ok_msg").format(amount=amount, balance=user_balances[uid])
            await bot.send_message(chat_id=uid, text=text, parse_mode=ParseMode.HTML)
        except Exception as e:
            print(f"[!] notify error: {e}")


@dp.callback_query(F.data.startswith("tup_no:"))
async def cb_topup_no(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("⛔", show_alert=True)
        return
    oid = call.data.split(":", 1)[1]
    order = topup_orders.get(oid)
    await call.answer("❌")
    await call.message.edit_reply_markup(reply_markup=None)
    await call.message.reply(f"❌ Top-up <b>#{oid}</b>", parse_mode=ParseMode.HTML)
    if order:
        uid = order["user_id"]
        try:
            await bot.send_message(chat_id=uid, text=t(uid, "tup_no_msg"), parse_mode=ParseMode.HTML)
        except Exception as e:
            print(f"[!] notify error: {e}")


async def main():
    await init_tg_client()
    print("[+] Bot is starting...")
    await dp.start_polling(bot, allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    asyncio.run(main())
