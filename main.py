import asyncio
import hashlib
import hmac
import json
import os
import random
import re
import time
from typing import Optional

import aiohttp
from aiohttp import web

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.enums import ButtonStyle, ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from translations import LANG_NAMES, TRANSLATIONS, t, set_lang_resolver


BOT_TOKEN = "8648481533:AAFARlXqffNG4TsEGWOE0F5fpk_SMFXp79U"
ADMIN_ID = 7316971152
BAN_PRICE = 500000

RUBIKA_BAN_PRICE = 200000
RUBIKA_LOOKUP_PRICE = 100000
SOROUSH_BAN_PRICE = 200000
SOROUSH_LOOKUP_PRICE = 100000

PHONE_API_BASE = "http://api.subhxcosmo.in/api"
PHONE_API_KEY = "WALTER"
PHONE_API_TIMEOUT = 20

TG_USER_BASE = os.getenv("TG_USER_BASE", "https://tg-user.id")
TG_USER_TIMEOUT = int(os.getenv("TG_USER_TIMEOUT", "20"))
TG_USER_CACHE_TTL = int(os.getenv("TG_USER_CACHE_TTL", "1800"))
TG_USER_MIN_INTERVAL = float(os.getenv("TG_USER_MIN_INTERVAL", "1.2"))
TG_USER_MAX_RETRIES = int(os.getenv("TG_USER_MAX_RETRIES", "3"))

HOOSHPAY_BASE = os.getenv("HOOSHPAY_BASE", "https://hooshpay.xyz")
HOOSHPAY_API_KEY = os.getenv(
    "HOOSHPAY_API_KEY", "hp_live_7cc4d2e5896c7e0ee614a515647b66e2c4e18a21"
)
HOOSHPAY_SECRET = os.getenv(
    "HOOSHPAY_SECRET", "963c59be4d4c945cc36ad2ba540a803702c2034cf9f5841c"
)
HOOSHPAY_FEE_MODE = os.getenv("HOOSHPAY_FEE_MODE", "buyer")
HOOSHPAY_CALLBACK_URL = os.getenv("HOOSHPAY_CALLBACK_URL", "")
HOOSHPAY_RETURN_URL = os.getenv("HOOSHPAY_RETURN_URL", "")
HOOSHPAY_WEBHOOK_HOST = os.getenv("HOOSHPAY_WEBHOOK_HOST", "0.0.0.0")
HOOSHPAY_WEBHOOK_PORT = int(os.getenv("HOOSHPAY_WEBHOOK_PORT", "0") or "0")
HOOSHPAY_POLL_INTERVAL = int(os.getenv("HOOSHPAY_POLL_INTERVAL", "8"))
HOOSHPAY_TIMEOUT = int(os.getenv("HOOSHPAY_TIMEOUT", "20"))

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:132.0) Gecko/20100101 Firefox/132.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
]

ACCEPT_HEADERS = [
    "application/json, text/plain, */*",
    "application/json, text/javascript, */*; q=0.01",
    "application/json",
]

ACCEPT_LANGS = [
    "en-US,en;q=0.9",
    "en-GB,en;q=0.9",
    "en-US,en;q=0.9,fa;q=0.8",
    "en-US,en;q=0.9,ru;q=0.7",
]

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


class GiftFlow(StatesGroup):
    choosing_language = State()
    waiting_rules = State()
    choosing_platform = State()
    waiting_for_id = State()
    confirming = State()
    choosing_payment = State()
    choosing_crypto = State()
    waiting_card_receipt = State()
    waiting_ton_receipt = State()
    waiting_trx_receipt = State()
    settings_menu = State()
    settings_change_lang = State()
    wallet_menu = State()
    wallet_choose_method = State()
    wallet_choose_crypto = State()
    wallet_wait_amount = State()
    wallet_card_receipt = State()
    wallet_ton_receipt = State()
    wallet_trx_receipt = State()
    phone_lookup_waiting = State()


user_langs: dict = {}
user_balances: dict = {}
ban_orders: dict = {}
topup_orders: dict = {}
pending_invoices: dict = {}

set_lang_resolver(lambda uid: user_langs.get(uid, "fa"))

HEX_RE = re.compile(r"^[0-9a-fA-F]{64}$")
TON_B64_RE = re.compile(r"^[A-Za-z0-9+/=_-]{40,90}$")
USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{4,32}$")


def is_valid_trx_hash(text: str) -> bool:
    return bool(HEX_RE.match(text.strip()))


def is_valid_ton_hash(text: str) -> bool:
    t_ = text.strip()
    if HEX_RE.match(t_):
        return True
    if TON_B64_RE.match(t_) and len(t_) >= 43:
        return True
    return False


def is_persian_lang(uid: int) -> bool:
    return user_langs.get(uid, "fa") == "fa"


def lang_kb() -> InlineKeyboardMarkup:
    items = list(LANG_NAMES.items())
    rows = []
    for i in range(0, len(items), 2):
        row = [
            InlineKeyboardButton(
                text=lbl, callback_data=f"lang:{code}", style=ButtonStyle.PRIMARY
            )
            for code, lbl in items[i : i + 2]
        ]
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def rules_kb(uid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(uid, "btn_accept_rules"),
                    callback_data="accept_rules",
                    style=ButtonStyle.SUCCESS,
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(uid, "btn_reject_rules"),
                    callback_data="reject_rules",
                    style=ButtonStyle.DANGER,
                )
            ],
        ]
    )


def platform_kb(uid: int) -> InlineKeyboardMarkup:
    if is_persian_lang(uid):
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=t(uid, "btn_platform_tg"),
                        callback_data="platform_tg",
                        style=ButtonStyle.PRIMARY,
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=t(uid, "btn_platform_wa"),
                        callback_data="platform_wa",
                        style=ButtonStyle.SUCCESS,
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=t(uid, "btn_platform_rubika"),
                        callback_data="platform_rubika",
                        style=ButtonStyle.PRIMARY,
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=t(uid, "btn_platform_soroush"),
                        callback_data="platform_soroush",
                        style=ButtonStyle.PRIMARY,
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=t(uid, "btn_platform_prices"),
                        callback_data="show_prices",
                        style=ButtonStyle.SUCCESS,
                    )
                ],
            ]
        )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(uid, "btn_platform_tg"),
                    callback_data="platform_tg",
                    style=ButtonStyle.PRIMARY,
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(uid, "btn_platform_wa"),
                    callback_data="platform_wa",
                    style=ButtonStyle.SUCCESS,
                )
            ],
        ]
    )


def main_menu_kb(uid: int, platform: str = "tg") -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=t(uid, "btn_start_gift"),
                callback_data="start_gift",
                style=ButtonStyle.PRIMARY,
            ),
            InlineKeyboardButton(
                text=t(uid, "btn_buy_ban"),
                callback_data="start_gift",
                style=ButtonStyle.PRIMARY,
            ),
        ],
    ]
    if platform == "tg":
        rows.append(
            [
                InlineKeyboardButton(
                    text=t(uid, "btn_phone_lookup"),
                    callback_data="phone_lookup",
                    style=ButtonStyle.SUCCESS,
                )
            ]
        )
    if platform == "rubika":
        rows.append(
            [
                InlineKeyboardButton(
                    text=t(uid, "btn_phone_lookup"),
                    callback_data="phone_lookup_rubika",
                    style=ButtonStyle.SUCCESS,
                )
            ]
        )
    if platform == "soroush":
        rows.append(
            [
                InlineKeyboardButton(
                    text=t(uid, "btn_phone_lookup"),
                    callback_data="phone_lookup_soroush",
                    style=ButtonStyle.SUCCESS,
                )
            ]
        )
    rows.extend(
        [
            [
                InlineKeyboardButton(
                    text=t(uid, "btn_my_account"),
                    callback_data="my_account",
                    style=ButtonStyle.PRIMARY,
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(uid, "btn_wallet"),
                    callback_data="open_wallet",
                    style=ButtonStyle.SUCCESS,
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(uid, "btn_settings"),
                    callback_data="open_settings",
                    style=ButtonStyle.PRIMARY,
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(uid, "btn_help"),
                    callback_data="help",
                    style=ButtonStyle.PRIMARY,
                ),
                InlineKeyboardButton(
                    text=t(uid, "btn_support"),
                    callback_data="support",
                    style=ButtonStyle.SUCCESS,
                ),
            ],
            [
                InlineKeyboardButton(
                    text=t(uid, "btn_back_platform"),
                    callback_data="back_platform",
                    style=ButtonStyle.DANGER,
                )
            ],
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def settings_kb(uid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(uid, "btn_change_lang"),
                    callback_data="change_lang",
                    style=ButtonStyle.PRIMARY,
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(uid, "btn_back_menu"),
                    callback_data="back_menu",
                    style=ButtonStyle.DANGER,
                )
            ],
        ]
    )


def confirm_kb(uid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(uid, "btn_confirm_yes"),
                    callback_data="confirm_yes",
                    style=ButtonStyle.SUCCESS,
                ),
                InlineKeyboardButton(
                    text=t(uid, "btn_confirm_no"),
                    callback_data="confirm_no",
                    style=ButtonStyle.DANGER,
                ),
            ]
        ]
    )


def payment_kb(uid: int) -> InlineKeyboardMarkup:
    lang = user_langs.get(uid, "fa")
    rows = []
    if lang == "fa":
        rows.append(
            [
                InlineKeyboardButton(
                    text=t(uid, "btn_pay_card"),
                    callback_data="pay_card",
                    style=ButtonStyle.SUCCESS,
                )
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(
                text=t(uid, "btn_pay_crypto"),
                callback_data="pay_crypto",
                style=ButtonStyle.PRIMARY,
            )
        ]
    )
    rows.append(
        [
            InlineKeyboardButton(
                text=t(uid, "btn_pay_balance"),
                callback_data="pay_balance",
                style=ButtonStyle.PRIMARY,
            )
        ]
    )
    rows.append(
        [
            InlineKeyboardButton(
                text=t(uid, "btn_back_menu"),
                callback_data="back_menu",
                style=ButtonStyle.DANGER,
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def crypto_kb(uid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(uid, "btn_crypto_ton"),
                    callback_data="crypto_ton",
                    style=ButtonStyle.SUCCESS,
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(uid, "btn_crypto_trx"),
                    callback_data="crypto_trx",
                    style=ButtonStyle.SUCCESS,
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(uid, "btn_back"),
                    callback_data="back_payment",
                    style=ButtonStyle.DANGER,
                )
            ],
        ]
    )


def back_menu_kb(uid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(uid, "btn_back_menu"),
                    callback_data="back_menu",
                    style=ButtonStyle.DANGER,
                )
            ]
        ]
    )


def wallet_method_kb(uid: int) -> InlineKeyboardMarkup:
    lang = user_langs.get(uid, "fa")
    rows = []
    if lang == "fa":
        rows.append(
            [
                InlineKeyboardButton(
                    text=t(uid, "btn_pay_card"),
                    callback_data="wallet_card",
                    style=ButtonStyle.SUCCESS,
                )
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(
                text=t(uid, "btn_pay_crypto"),
                callback_data="wallet_crypto",
                style=ButtonStyle.PRIMARY,
            )
        ]
    )
    rows.append(
        [
            InlineKeyboardButton(
                text=t(uid, "btn_back"),
                callback_data="open_settings",
                style=ButtonStyle.DANGER,
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def wallet_crypto_kb(uid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(uid, "btn_crypto_ton"),
                    callback_data="wallet_ton",
                    style=ButtonStyle.SUCCESS,
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(uid, "btn_crypto_trx"),
                    callback_data="wallet_trx",
                    style=ButtonStyle.SUCCESS,
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(uid, "btn_back"),
                    callback_data="open_wallet",
                    style=ButtonStyle.DANGER,
                )
            ],
        ]
    )


def lookup_pay_kb(uid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(uid, "btn_pay_card"),
                    callback_data="lookup_pay_card",
                    style=ButtonStyle.SUCCESS,
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(uid, "btn_pay_crypto"),
                    callback_data="lookup_pay_crypto",
                    style=ButtonStyle.PRIMARY,
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(uid, "btn_pay_balance"),
                    callback_data="lookup_pay_balance",
                    style=ButtonStyle.PRIMARY,
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(uid, "btn_back_menu"),
                    callback_data="back_menu",
                    style=ButtonStyle.DANGER,
                )
            ],
        ]
    )


def admin_ban_kb(oid: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ تأیید",
                    callback_data=f"adm_ok:{oid}",
                    style=ButtonStyle.SUCCESS,
                ),
                InlineKeyboardButton(
                    text="❌ کنسل",
                    callback_data=f"adm_no:{oid}",
                    style=ButtonStyle.DANGER,
                ),
            ]
        ]
    )


def admin_topup_kb(oid: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ تأیید واریز",
                    callback_data=f"tup_ok:{oid}",
                    style=ButtonStyle.SUCCESS,
                ),
                InlineKeyboardButton(
                    text="❌ رد",
                    callback_data=f"tup_no:{oid}",
                    style=ButtonStyle.DANGER,
                ),
            ]
        ]
    )


def new_id() -> str:
    return f"{random.randint(100000, 999999)}"


def sender_tag(u) -> str:
    if u.username:
        return f"@{u.username}"
    return f"<a href='tg://user?id={u.id}'>{u.full_name}</a>"


def _current_ban_price(platform: str) -> int:
    if platform == "rubika":
        return RUBIKA_BAN_PRICE
    if platform == "soroush":
        return SOROUSH_BAN_PRICE
    return BAN_PRICE


def _platform_welcome_key(platform: str) -> str:
    if platform == "wa":
        return "welcome_wa"
    if platform == "rubika":
        return "welcome_rubika"
    if platform == "soroush":
        return "welcome_soroush"
    return "welcome"


def _random_headers(referer_path: str = "/") -> dict:
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": random.choice(ACCEPT_HEADERS),
        "Accept-Language": random.choice(ACCEPT_LANGS),
        "Accept-Encoding": "gzip, deflate, br",
        "Cache-Control": random.choice(["no-cache", "no-store", "max-age=0"]),
        "Pragma": "no-cache",
        "DNT": "1",
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": random.choice(["empty", "cors"]),
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Ch-Ua": '"Chromium";v="131", "Not_A Brand";v="24"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": random.choice(['"Windows"', '"macOS"', '"Linux"']),
        "Origin": TG_USER_BASE,
        "Referer": f"{TG_USER_BASE}{referer_path}",
    }


_hp_session: Optional[aiohttp.ClientSession] = None
_api_session: Optional[aiohttp.ClientSession] = None
_tguser_session: Optional[aiohttp.ClientSession] = None
_tguser_csrf: Optional[str] = None
_tguser_csrf_time: float = 0.0
_tguser_cache: dict = {}
_tguser_lock: asyncio.Lock = None
_tguser_last_request: float = 0.0


async def hp_http() -> aiohttp.ClientSession:
    global _hp_session
    if _hp_session is None or _hp_session.closed:
        _hp_session = aiohttp.ClientSession()
    return _hp_session


async def api_http() -> aiohttp.ClientSession:
    global _api_session
    if _api_session is None or _api_session.closed:
        _api_session = aiohttp.ClientSession()
    return _api_session


async def tguser_http() -> aiohttp.ClientSession:
    global _tguser_session
    if _tguser_session is None or _tguser_session.closed:
        connector = aiohttp.TCPConnector(
            limit=20,
            limit_per_host=10,
            ttl_dns_cache=300,
            enable_cleanup_closed=True,
        )
        _tguser_session = aiohttp.ClientSession(
            connector=connector,
            cookie_jar=aiohttp.CookieJar(unsafe=True),
        )
    return _tguser_session


async def _tguser_throttle():
    global _tguser_last_request
    if _tguser_lock is None:
        return
    async with _tguser_lock:
        now = time.time()
        delta = now - _tguser_last_request
        if delta < TG_USER_MIN_INTERVAL:
            await asyncio.sleep(TG_USER_MIN_INTERVAL - delta)
        _tguser_last_request = time.time()


def _tguser_cache_get(username: str) -> Optional[dict]:
    entry = _tguser_cache.get(username.lower())
    if not entry:
        return None
    if time.time() - entry["ts"] > TG_USER_CACHE_TTL:
        _tguser_cache.pop(username.lower(), None)
        return None
    return entry["data"]


def _tguser_cache_set(username: str, data: dict):
    _tguser_cache[username.lower()] = {"ts": time.time(), "data": data}
    if len(_tguser_cache) > 5000:
        cutoff = time.time() - TG_USER_CACHE_TTL
        for k in list(_tguser_cache.keys()):
            if _tguser_cache[k]["ts"] < cutoff:
                _tguser_cache.pop(k, None)


async def fetch_tguser_csrf(force: bool = False) -> Optional[str]:
    global _tguser_csrf, _tguser_csrf_time
    if _tguser_csrf and not force and (time.time() - _tguser_csrf_time) < 600:
        return _tguser_csrf
    try:
        await _tguser_throttle()
        session = await tguser_http()
        headers = _random_headers("/")
        headers.pop("Origin", None)
        headers.pop("Referer", None)
        async with session.get(
            f"{TG_USER_BASE}/",
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=TG_USER_TIMEOUT),
        ) as resp:
            html = await resp.text()
        m = re.search(r'name="csrf-token"\s+content="([^"]+)"', html)
        if not m:
            m = re.search(r'"csrf[_-]?token"\s*:\s*"([^"]+)"', html)
        if m:
            _tguser_csrf = m.group(1)
            _tguser_csrf_time = time.time()
            return _tguser_csrf
        return None
    except Exception as e:
        print(f"[!] tg-user.id csrf error: {e}")
        return None


async def _tguser_post(username: str, csrf: str) -> Optional[dict]:
    headers = _random_headers("/")
    headers["Content-Type"] = random.choice(
        ["application/json;charset=UTF-8", "application/json"]
    )
    headers["X-CSRF-Token"] = csrf
    headers["X-Requested-With"] = "XMLHttpRequest"
    payload = {"username": username}
    try:
        session = await tguser_http()
        async with session.post(
            f"{TG_USER_BASE}/api/get-userid",
            json=payload,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=TG_USER_TIMEOUT),
        ) as resp:
            if resp.status == 429:
                await asyncio.sleep(3 + random.random() * 3)
                return None
            if resp.status in (401, 403):
                return {"__csrf_invalid__": True}
            data = await resp.json(content_type=None)
            if isinstance(data, dict):
                return data
            return None
    except Exception as e:
        print(f"[!] tg-user.id post error: {e}")
        return None


async def resolve_username_via_api(username: str) -> Optional[dict]:
    username = username.lstrip("@").strip()
    if not username or not USERNAME_RE.match(username):
        return None

    cached = _tguser_cache_get(username)
    if cached is not None:
        return cached

    for attempt in range(TG_USER_MAX_RETRIES):
        csrf = await fetch_tguser_csrf(force=(attempt > 0))
        if not csrf:
            await asyncio.sleep(1 + random.random())
            continue

        await _tguser_throttle()
        data = await _tguser_post(username, csrf)

        if data is None:
            await asyncio.sleep(1.5 + random.random() * 1.5)
            continue

        if data.get("__csrf_invalid__"):
            await fetch_tguser_csrf(force=True)
            await asyncio.sleep(0.8 + random.random())
            continue

        if not data.get("id"):
            return None

        _tguser_cache_set(username, data)
        return data

    return None


async def safe_edit(
    message: Message, text: str, markup: Optional[InlineKeyboardMarkup] = None
) -> None:
    try:
        if markup is not None:
            await message.edit_text(text, reply_markup=markup, parse_mode=ParseMode.HTML)
        else:
            await message.edit_text(text, parse_mode=ParseMode.HTML)
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise


async def hooshpay_request(
    method: str, path: str, json_body: Optional[dict] = None
) -> Optional[dict]:
    url = f"{HOOSHPAY_BASE}{path}"
    headers = {
        "X-API-KEY": HOOSHPAY_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    try:
        session = await hp_http()
        async with session.request(
            method,
            url,
            headers=headers,
            json=json_body,
            timeout=aiohttp.ClientTimeout(total=HOOSHPAY_TIMEOUT),
        ) as resp:
            return await resp.json(content_type=None)
    except Exception as e:
        print(f"[!] hooshpay {method} {path} error: {e}")
        return None


async def hooshpay_create_invoice(
    amount: int, order_id: str, description: str = ""
) -> Optional[dict]:
    payload = {
        "amount": int(amount),
        "fee_mode": HOOSHPAY_FEE_MODE,
        "order_id": str(order_id),
    }
    if description:
        payload["description"] = description
    if HOOSHPAY_CALLBACK_URL:
        payload["callback_url"] = HOOSHPAY_CALLBACK_URL
    if HOOSHPAY_RETURN_URL:
        payload["return_url"] = HOOSHPAY_RETURN_URL
    res = await hooshpay_request("POST", "/api/v1/invoices", payload)
    if not isinstance(res, dict) or not res.get("success"):
        print(f"[!] hooshpay create invoice failed: {res}")
        return None
    return res.get("data") or None


async def hooshpay_verify_invoice(inv_uid: str) -> Optional[dict]:
    res = await hooshpay_request("POST", f"/api/v1/invoices/{inv_uid}/verify")
    if isinstance(res, dict) and (res.get("paid") or res.get("status") == "paid"):
        return res
    return None


def hooshpay_valid_signature(payload: dict, signature: str) -> bool:
    if not HOOSHPAY_SECRET or not signature:
        return False
    body = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    expected = hmac.new(
        HOOSHPAY_SECRET.encode("utf-8"), body.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature.strip())


def gateway_text(uid: int, inv: dict) -> str:
    card = inv.get("card") or {}
    amount = int(inv.get("amount") or 0)
    payable = int(inv.get("payable_amount") or amount)
    expires = str(inv.get("expires_at") or "—").replace("T", " ")
    return t(uid, "hp_text").format(
        amount=amount,
        payable=payable,
        card=card.get("card_number") or "—",
        holder=card.get("holder_name") or "—",
        oid=inv.get("uid") or "—",
        expires=expires,
    )


def gateway_kb(uid: int, inv_uid: str, pay_url: Optional[str]) -> InlineKeyboardMarkup:
    rows = []
    if pay_url:
        rows.append(
            [
                InlineKeyboardButton(
                    text=t(uid, "hp_btn_pay"),
                    url=pay_url,
                    style=ButtonStyle.SUCCESS,
                )
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(
                text=t(uid, "hp_btn_check"),
                callback_data=f"hpcheck:{inv_uid}",
                style=ButtonStyle.PRIMARY,
            )
        ]
    )
    rows.append(
        [
            InlineKeyboardButton(
                text=t(uid, "btn_back_menu"),
                callback_data="back_menu",
                style=ButtonStyle.DANGER,
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def open_card_gateway(
    uid: int,
    kind: str,
    amount: int,
    oid: str,
    buyer_tag: str,
    target: Optional[dict] = None,
    edit_target: Optional[Message] = None,
    chat_id: Optional[int] = None,
    description: str = "",
) -> bool:
    inv = await hooshpay_create_invoice(amount, oid, description)
    if not inv or not inv.get("uid"):
        return False
    inv_uid = str(inv["uid"])
    payable = int(inv.get("payable_amount") or amount)
    pending_invoices[inv_uid] = {
        "user_id": uid,
        "kind": kind,
        "oid": oid,
        "amount": int(amount),
        "payable": payable,
        "buyer_tag": buyer_tag,
        "target": target or {},
        "created": time.time(),
    }
    text = gateway_text(uid, inv)
    markup = gateway_kb(uid, inv_uid, inv.get("payment_url"))
    if edit_target is not None:
        await safe_edit(edit_target, text, markup)
    else:
        await bot.send_message(
            chat_id or uid, text, reply_markup=markup, parse_mode=ParseMode.HTML
        )
    return True


async def complete_pending_invoice(inv_uid: str, tracking: str = "") -> bool:
    rec = pending_invoices.pop(inv_uid, None)
    if rec is None:
        return False
    uid = rec["user_id"]
    oid = rec["oid"]
    amount = rec["amount"]
    payable = rec.get("payable") or amount
    method_label = t(uid, "hp_method")

    if rec["kind"] in ("ban", "ban_rubika", "ban_soroush"):
        target = rec.get("target") or {}
        platform = "tg"
        if rec["kind"] == "ban_rubika":
            platform = "rubika"
        elif rec["kind"] == "ban_soroush":
            platform = "soroush"
        ban_orders[oid] = {"user_id": uid, "method": "hp_method", "target": target}
        platform_label = ""
        if platform != "tg":
            platform_label = f" ({platform.title()})"
        caption = (
            f"{t(uid, 'order_new')} #{oid}{platform_label}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"{t(uid, 'order_buyer')} {rec.get('buyer_tag', '—')}\n"
            f"{t(uid, 'order_buyer_id')} <code>{uid}</code>\n"
            f"{t(uid, 'order_method')} {method_label}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"{t(uid, 'order_target')} <code>{target.get('id', '—')}</code>\n"
            f"{t(uid, 'order_target_name')} {target.get('first_name', '—')} {target.get('last_name', '—')}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "✅ <b>Gateway verified</b>\n"
            f"🧾 <code>{inv_uid}</code>\n"
            f"🔖 <code>{tracking or '—'}</code>\n"
            f"💰 <b>{payable:,} Toman</b>"
        )
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=caption,
            reply_markup=admin_ban_kb(oid),
            parse_mode=ParseMode.HTML,
        )
        await bot.send_message(
            chat_id=uid,
            text=t(uid, "hp_paid").format(
                oid=inv_uid, amount=payable, tracking=tracking or "—"
            ),
            reply_markup=main_menu_kb(uid, platform),
            parse_mode=ParseMode.HTML,
        )
    elif rec["kind"] in ("lookup_rubika", "lookup_soroush"):
        target = rec.get("target") or {}
        platform = "rubika" if rec["kind"] == "lookup_rubika" else "soroush"
        caption = (
            f"📱 <b>User To Number Lookup Order</b> #{oid}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 {rec.get('buyer_tag', '—')}\n"
            f"🆔 <code>{uid}</code>\n"
            f"💳 {method_label}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"🎯 Target: <code>{target.get('id', '—')}</code>\n"
            f"🏷 Platform: <b>{platform.title()}</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "✅ <b>Gateway verified</b>\n"
            f"🧾 <code>{inv_uid}</code>\n"
            f"🔖 <code>{tracking or '—'}</code>\n"
            f"💰 <b>{payable:,} Toman</b>"
        )
        await bot.send_message(chat_id=ADMIN_ID, text=caption, parse_mode=ParseMode.HTML)
        await bot.send_message(
            chat_id=uid,
            text=t(uid, "hp_paid").format(
                oid=inv_uid, amount=payable, tracking=tracking or "—"
            ),
            reply_markup=main_menu_kb(uid, platform),
            parse_mode=ParseMode.HTML,
        )
    else:
        user_balances[uid] = user_balances.get(uid, 0) + amount
        topup_orders[oid] = {"user_id": uid, "amount": amount, "method": "hp_method"}
        admin_text = (
            f"{t(uid, 'tup_new')} #{oid}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 {rec.get('buyer_tag', '—')}\n"
            f"🆔 <code>{uid}</code>\n"
            f"{t(uid, 'tup_amount_lbl')} <b>{amount:,} Toman</b>\n"
            f"{t(uid, 'tup_method_lbl')} {method_label}\n"
            f"✅ <b>Gateway verified</b> — <code>{tracking or '—'}</code>"
        )
        await bot.send_message(
            chat_id=ADMIN_ID, text=admin_text, parse_mode=ParseMode.HTML
        )
        await bot.send_message(
            chat_id=uid,
            text=t(uid, "tup_ok_msg").format(
                amount=amount, balance=user_balances[uid]
            ),
            reply_markup=main_menu_kb(uid),
            parse_mode=ParseMode.HTML,
        )
    print(f"[+] hooshpay invoice {inv_uid} completed ({rec['kind']})")
    return True


async def invoice_poller():
    while True:
        try:
            for inv_uid in list(pending_invoices.keys()):
                data = await hooshpay_verify_invoice(inv_uid)
                if data:
                    tracking = str((data.get("data") or {}).get("tracking_code") or "")
                    await complete_pending_invoice(inv_uid, tracking=tracking)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            print(f"[!] invoice poller error: {e}")
        await asyncio.sleep(HOOSHPAY_POLL_INTERVAL)


async def _hooshpay_webhook(request: web.Request) -> web.Response:
    raw = await request.read()
    signature = request.headers.get("X-HooshPay-Signature", "")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except Exception:
        return web.Response(status=400, text="invalid json")
    if not isinstance(payload, dict):
        return web.Response(status=400, text="invalid payload")
    if HOOSHPAY_SECRET and not hooshpay_valid_signature(payload, signature):
        return web.Response(status=403, text="invalid signature")
    inv_uid = str(payload.get("invoice") or "")
    if payload.get("event") == "payment.success" and inv_uid:
        await complete_pending_invoice(
            inv_uid, tracking=str(payload.get("tracking_code") or "")
        )
    return web.Response(status=200, text="OK")


async def run_webhook_server():
    app = web.Application()
    app.router.add_post("/hooshpay/callback", _hooshpay_webhook)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, HOOSHPAY_WEBHOOK_HOST, HOOSHPAY_WEBHOOK_PORT)
    await site.start()
    print(
        f"[+] HooshPay webhook listening on {HOOSHPAY_WEBHOOK_HOST}:{HOOSHPAY_WEBHOOK_PORT}"
    )


async def fetch_account_info(identifier: str):
    raw = identifier.strip()
    if raw.lstrip("-").isdigit():
        return None

    cleaned = raw.lstrip("@").strip()
    if raw.startswith("https://t.me/") or raw.startswith("t.me/"):
        cleaned = raw.rstrip("/").split("/")[-1].lstrip("@")
    if not USERNAME_RE.match(cleaned):
        return None

    data = await resolve_username_via_api(cleaned)
    if not data or not data.get("id"):
        return None

    try:
        numeric_id = int(data["id"])
    except (TypeError, ValueError):
        return None

    return {
        "id": numeric_id,
        "first_name": data.get("firstName") or "—",
        "last_name": data.get("lastName") or "—",
        "username": data.get("username") or cleaned,
        "is_bot": bool(data.get("isBot", False)),
    }


async def fetch_wa_account_info(phone: str):
    cleaned = re.sub(r"[^\d+]", "", phone)
    if not cleaned.startswith("+"):
        if cleaned.startswith("00"):
            cleaned = "+" + cleaned[2:]
        else:
            cleaned = "+" + cleaned.lstrip("+")
    digits_only = cleaned.lstrip("+")
    if not digits_only.isdigit() or len(digits_only) < 6 or len(digits_only) > 15:
        return None
    fake_id = int(hashlib.sha256(cleaned.encode()).hexdigest(), 16) % (10**12)
    return {
        "id": fake_id,
        "first_name": "WhatsApp",
        "last_name": "User",
        "username": "—",
        "phone": cleaned,
        "is_bot": False,
    }


async def fetch_rubika_account_info(identifier: str):
    raw = identifier.lstrip("@").strip()
    if not raw:
        return None
    if raw.lstrip("-").isdigit():
        numeric_id = int(raw)
        username = "—"
    elif re.match(r"^[A-Za-z0-9_\.]{3,32}$", raw):
        numeric_id = (
            int(hashlib.sha256(raw.lower().encode()).hexdigest(), 16) % (10**10)
        )
        username = raw
    else:
        return None
    return {
        "id": numeric_id,
        "first_name": "Rubika",
        "last_name": "User",
        "username": username,
        "phone": "—",
        "is_bot": False,
    }


async def fetch_soroush_account_info(identifier: str):
    raw = identifier.lstrip("@").strip()
    if not raw:
        return None
    if raw.lstrip("-").isdigit():
        numeric_id = int(raw)
        username = "—"
    elif re.match(r"^[A-Za-z0-9_\.]{3,32}$", raw):
        numeric_id = (
            int(hashlib.sha256(raw.lower().encode()).hexdigest(), 16) % (10**10)
        )
        username = raw
    else:
        return None
    return {
        "id": numeric_id,
        "first_name": "Soroush",
        "last_name": "Plus User",
        "username": username,
        "phone": "—",
        "is_bot": False,
    }


async def phone_lookup_query(tg_id: int) -> Optional[dict]:
    url = f"{PHONE_API_BASE}?key={PHONE_API_KEY}&type=tg&term={tg_id}"
    try:
        session = await api_http()
        async with session.get(
            url, timeout=aiohttp.ClientTimeout(total=PHONE_API_TIMEOUT)
        ) as resp:
            data = await resp.json(content_type=None)
            if not isinstance(data, dict):
                return None
            return data
    except Exception as e:
        print(f"[!] phone lookup error: {e}")
        return None


def parse_phone_api_response(data: dict) -> Optional[dict]:
    if not isinstance(data, dict):
        return None
    result = data.get("result")
    if not isinstance(result, dict):
        return None
    if not result.get("status"):
        return {"status": "not_found"}
    phones = result.get("phone") or []
    if not isinstance(phones, list) or not phones:
        return {"status": "no_phone"}
    first = phones[0] or {}
    return {
        "status": "found",
        "number": str(first.get("number") or ""),
        "country_code": str(first.get("country_code") or ""),
        "country": str(first.get("country") or ""),
        "flag": str(first.get("country_flag") or "🌐"),
    }


@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(GiftFlow.choosing_language)
    await message.answer(
        TRANSLATIONS["fa"]["welcome_lang"],
        reply_markup=lang_kb(),
        parse_mode=ParseMode.HTML,
    )


@dp.callback_query(F.data.startswith("lang:"))
async def cb_lang_select(call: CallbackQuery, state: FSMContext):
    lang = call.data.split(":", 1)[1]
    if lang not in TRANSLATIONS:
        lang = "fa"
    uid = call.from_user.id
    user_langs[uid] = lang
    await call.answer(LANG_NAMES[lang])
    current = await state.get_state()
    if current == GiftFlow.settings_change_lang.state:
        await state.set_state(GiftFlow.settings_menu)
        await safe_edit(call.message, t(uid, "settings_text"), settings_kb(uid))
    else:
        await state.set_state(GiftFlow.waiting_rules)
        await safe_edit(call.message, TRANSLATIONS[lang]["rules"], rules_kb(uid))


@dp.callback_query(F.data == "accept_rules")
async def cb_accept_rules(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    await call.answer(t(uid, "rules_accepted"))
    await state.set_state(GiftFlow.choosing_platform)
    await safe_edit(call.message, t(uid, "platform_text"), platform_kb(uid))


@dp.callback_query(F.data == "reject_rules")
async def cb_reject_rules(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    await call.answer(t(uid, "rules_rejected"))
    await state.clear()
    await safe_edit(call.message, t(uid, "rules_rejected_text"))


@dp.callback_query(F.data == "show_prices")
async def cb_show_prices(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    await call.answer()
    await safe_edit(call.message, t(uid, "prices_text"), platform_kb(uid))


@dp.callback_query(F.data == "platform_tg")
async def cb_platform_tg(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    await call.answer()
    await state.clear()
    await state.update_data(platform="tg")
    name = call.from_user.first_name or "User"
    await safe_edit(
        call.message, t(uid, "welcome").format(name=name), main_menu_kb(uid, "tg")
    )


@dp.callback_query(F.data == "platform_wa")
async def cb_platform_wa(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    await call.answer()
    await state.clear()
    await state.update_data(platform="wa")
    name = call.from_user.first_name or "User"
    await safe_edit(
        call.message, t(uid, "welcome_wa").format(name=name), main_menu_kb(uid, "wa")
    )


@dp.callback_query(F.data == "platform_rubika")
async def cb_platform_rubika(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    await call.answer()
    await state.clear()
    await state.update_data(platform="rubika")
    name = call.from_user.first_name or "User"
    await safe_edit(
        call.message,
        t(uid, "welcome_rubika").format(name=name),
        main_menu_kb(uid, "rubika"),
    )


@dp.callback_query(F.data == "platform_soroush")
async def cb_platform_soroush(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    await call.answer()
    await state.clear()
    await state.update_data(platform="soroush")
    name = call.from_user.first_name or "User"
    await safe_edit(
        call.message,
        t(uid, "welcome_soroush").format(name=name),
        main_menu_kb(uid, "soroush"),
    )


@dp.callback_query(F.data == "back_platform")
async def cb_back_platform(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    await call.answer()
    await state.clear()
    await state.set_state(GiftFlow.choosing_platform)
    await safe_edit(call.message, t(uid, "platform_text"), platform_kb(uid))


@dp.callback_query(F.data == "start_gift")
async def cb_start_gift(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    await call.answer()
    data = await state.get_data()
    platform = data.get("platform") or "tg"
    await state.set_state(GiftFlow.waiting_for_id)
    await state.update_data(platform=platform)
    if platform == "wa":
        await safe_edit(call.message, t(uid, "ask_id_wa"), back_menu_kb(uid))
    elif platform == "rubika":
        await safe_edit(call.message, t(uid, "ask_id_rubika"), back_menu_kb(uid))
    elif platform == "soroush":
        await safe_edit(call.message, t(uid, "ask_id_soroush"), back_menu_kb(uid))
    else:
        await safe_edit(call.message, t(uid, "ask_id"), back_menu_kb(uid))


@dp.callback_query(F.data == "phone_lookup")
async def cb_phone_lookup(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    await call.answer()
    await state.set_state(GiftFlow.phone_lookup_waiting)
    await state.update_data(lookup_platform="tg")
    await safe_edit(call.message, t(uid, "pl_ask"), back_menu_kb(uid))


@dp.callback_query(F.data == "phone_lookup_rubika")
async def cb_phone_lookup_rubika(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    await call.answer()
    await state.set_state(GiftFlow.phone_lookup_waiting)
    await state.update_data(lookup_platform="rubika")
    await safe_edit(call.message, t(uid, "pl_ask_rubika"), back_menu_kb(uid))


@dp.callback_query(F.data == "phone_lookup_soroush")
async def cb_phone_lookup_soroush(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    await call.answer()
    await state.set_state(GiftFlow.phone_lookup_waiting)
    await state.update_data(lookup_platform="soroush")
    await safe_edit(call.message, t(uid, "pl_ask_soroush"), back_menu_kb(uid))


@dp.message(GiftFlow.phone_lookup_waiting)
async def process_phone_lookup(message: Message, state: FSMContext):
    uid = message.from_user.id
    raw = (message.text or "").strip()
    data_state = await state.get_data()
    lookup_platform = data_state.get("lookup_platform", "tg")

    if not raw:
        if lookup_platform == "rubika":
            await message.answer(
                t(uid, "pl_invalid_rubika"), parse_mode=ParseMode.HTML
            )
        elif lookup_platform == "soroush":
            await message.answer(
                t(uid, "pl_invalid_soroush"), parse_mode=ParseMode.HTML
            )
        else:
            await message.answer(t(uid, "pl_invalid"), parse_mode=ParseMode.HTML)
        return

    if lookup_platform in ("rubika", "soroush"):
        await process_paid_lookup(message, state, lookup_platform, raw)
        return

    numeric_id: Optional[int] = None
    username: Optional[str] = None

    cleaned = raw.lstrip("@").strip()
    if cleaned.lstrip("-").isdigit():
        numeric_id = int(cleaned)
    elif raw.startswith("https://t.me/") or raw.startswith("t.me/"):
        username = raw.rstrip("/").split("/")[-1].lstrip("@")
        if not USERNAME_RE.match(username):
            username = None
    elif USERNAME_RE.match(cleaned):
        username = cleaned
    else:
        await message.answer(t(uid, "pl_invalid"), parse_mode=ParseMode.HTML)
        return

    wait_msg = await message.answer(t(uid, "pl_checking"), parse_mode=ParseMode.HTML)

    resolved_first_name = ""
    resolved_last_name = ""
    resolved_username = ""

    if username:
        data = await resolve_username_via_api(username)
        if not data or not data.get("id"):
            await safe_edit(wait_msg, t(uid, "pl_no_user"), back_menu_kb(uid))
            return
        try:
            numeric_id = int(data["id"])
        except (TypeError, ValueError):
            await safe_edit(wait_msg, t(uid, "pl_no_user"), back_menu_kb(uid))
            return
        resolved_first_name = data.get("firstName") or ""
        resolved_last_name = data.get("lastName") or ""
        resolved_username = data.get("username") or username
    elif numeric_id is None:
        await safe_edit(wait_msg, t(uid, "pl_invalid"), back_menu_kb(uid))
        return

    data = await phone_lookup_query(numeric_id)
    parsed = parse_phone_api_response(data) if data else None

    target_lines = []
    target_lines.append(f"{t(uid, 'pl_target_id')} <code>{numeric_id}</code>")
    if resolved_username:
        target_lines.append(f"{t(uid, 'pl_target_user')} @{resolved_username}")
    name_combined = f"{resolved_first_name} {resolved_last_name}".strip()
    if name_combined:
        target_lines.append(f"{t(uid, 'pl_target_name')} {name_combined}")
    target_block = "\n".join(target_lines)

    if parsed is None:
        text = (
            f"{t(uid, 'pl_result_header')}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"{target_block}\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{t(uid, 'pl_api_error')}"
        )
        await safe_edit(wait_msg, text, back_menu_kb(uid))
        return

    if parsed["status"] == "not_found":
        text = (
            f"{t(uid, 'pl_result_header')}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"{target_block}\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{t(uid, 'pl_not_found')}"
        )
        await safe_edit(wait_msg, text, back_menu_kb(uid))
        return

    if parsed["status"] == "no_phone":
        text = (
            f"{t(uid, 'pl_result_header')}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"{target_block}\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{t(uid, 'pl_no_phone_in_api')}"
        )
        await safe_edit(wait_msg, text, back_menu_kb(uid))
        return

    full_number = f"{parsed['country_code']} {parsed['number']}".strip()
    text = (
        f"{t(uid, 'pl_result_header')}\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"{target_block}\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"{t(uid, 'pl_phone')} <code>{full_number}</code>\n"
        f"{t(uid, 'pl_country')} {parsed['flag']} {parsed['country']}\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{t(uid, 'pl_btn_copy')}: {full_number}",
                    callback_data="pl_noop",
                    style=ButtonStyle.SUCCESS,
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(uid, "pl_back"),
                    callback_data="back_menu",
                    style=ButtonStyle.DANGER,
                )
            ],
        ]
    )
    await safe_edit(wait_msg, text, kb)


async def process_paid_lookup(
    message: Message, state: FSMContext, platform: str, raw: str
):
    uid = message.from_user.id
    if platform == "rubika":
        info = await fetch_rubika_account_info(raw)
        price = RUBIKA_LOOKUP_PRICE
    else:
        info = await fetch_soroush_account_info(raw)
        price = SOROUSH_LOOKUP_PRICE

    if info is None:
        invalid_key = (
            "pl_invalid_rubika" if platform == "rubika" else "pl_invalid_soroush"
        )
        await message.answer(t(uid, invalid_key), parse_mode=ParseMode.HTML)
        return

    await state.update_data(
        lookup_target=info, lookup_platform=platform, lookup_price=price
    )

    target_display = (
        f"@{info['username']}" if info["username"] != "—" else str(info["id"])
    )

    await state.set_state(GiftFlow.choosing_payment)
    text = t(uid, "pl_pay_header").format(
        price=price, target=f"<code>{target_display}</code>"
    )
    await message.answer(
        text, reply_markup=lookup_pay_kb(uid), parse_mode=ParseMode.HTML
    )


@dp.callback_query(F.data == "pl_noop")
async def cb_pl_noop(call: CallbackQuery):
    await call.answer("📋", show_alert=False)


@dp.callback_query(F.data == "back_menu")
async def cb_back_menu(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    await call.answer()
    data = await state.get_data()
    platform = data.get("platform") or "tg"
    await state.clear()
    await state.update_data(platform=platform)
    name = call.from_user.first_name or "User"
    welcome_key = _platform_welcome_key(platform)
    await safe_edit(
        call.message,
        t(uid, welcome_key).format(name=name),
        main_menu_kb(uid, platform),
    )


@dp.callback_query(F.data == "help")
async def cb_help(call: CallbackQuery):
    uid = call.from_user.id
    await call.answer()
    await safe_edit(call.message, t(uid, "help_text"), back_menu_kb(uid))


@dp.callback_query(F.data == "support")
async def cb_support(call: CallbackQuery):
    uid = call.from_user.id
    await call.answer()
    await safe_edit(call.message, t(uid, "support_text"), back_menu_kb(uid))


@dp.callback_query(F.data == "open_settings")
async def cb_open_settings(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    await call.answer()
    data = await state.get_data()
    platform = data.get("platform") or "tg"
    await state.set_state(GiftFlow.settings_menu)
    await state.update_data(platform=platform)
    await safe_edit(call.message, t(uid, "settings_text"), settings_kb(uid))


@dp.callback_query(F.data == "my_account")
async def cb_my_account(call: CallbackQuery):
    uid = call.from_user.id
    await call.answer()
    u = call.from_user
    balance = user_balances.get(uid, 0)
    username = f"@{u.username}" if u.username else "—"
    status = "Premium ⭐" if getattr(u, "is_premium", False) else "Free"
    text = t(uid, "account_text").format(
        name=u.first_name or "—",
        last=u.last_name or "—",
        uid=uid,
        username=username,
        status=status,
        balance=balance,
    )
    await safe_edit(call.message, text, settings_kb(uid))


@dp.callback_query(F.data == "change_lang")
async def cb_change_lang(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    await call.answer()
    await state.set_state(GiftFlow.settings_change_lang)
    await safe_edit(call.message, TRANSLATIONS["fa"]["welcome_lang"], lang_kb())


@dp.callback_query(F.data == "open_wallet")
async def cb_open_wallet(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    await call.answer()
    await state.set_state(GiftFlow.wallet_menu)
    balance = user_balances.get(uid, 0)
    await safe_edit(
        call.message,
        t(uid, "wallet_text").format(balance=balance),
        wallet_method_kb(uid),
    )


@dp.callback_query(F.data == "wallet_card")
async def cb_wallet_card(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    await call.answer()
    await state.set_state(GiftFlow.wallet_wait_amount)
    await state.update_data(wallet_method="card")
    await safe_edit(call.message, t(uid, "topup_ask_amount_card"), back_menu_kb(uid))


@dp.callback_query(F.data == "wallet_crypto")
async def cb_wallet_crypto(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    await call.answer()
    await state.set_state(GiftFlow.wallet_choose_crypto)
    await safe_edit(call.message, t(uid, "crypto_text"), wallet_crypto_kb(uid))


@dp.callback_query(F.data == "wallet_ton")
async def cb_wallet_ton(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    await call.answer()
    await state.set_state(GiftFlow.wallet_wait_amount)
    await state.update_data(wallet_method="ton")
    await safe_edit(call.message, t(uid, "topup_ask_amount_crypto"), back_menu_kb(uid))


@dp.callback_query(F.data == "wallet_trx")
async def cb_wallet_trx(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    await call.answer()
    await state.set_state(GiftFlow.wallet_wait_amount)
    await state.update_data(wallet_method="trx")
    await safe_edit(call.message, t(uid, "topup_ask_amount_crypto"), back_menu_kb(uid))


@dp.message(GiftFlow.wallet_wait_amount)
async def process_wallet_amount(message: Message, state: FSMContext):
    uid = message.from_user.id
    raw = (
        (message.text or "")
        .strip()
        .replace(",", "")
        .replace("،", "")
        .replace(" ", "")
    )
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
        if HOOSHPAY_API_KEY:
            oid = new_id()
            await message.answer(t(uid, "hp_creating"), parse_mode=ParseMode.HTML)
            ok = await open_card_gateway(
                uid=uid,
                kind="topup",
                amount=amount,
                oid=oid,
                buyer_tag=sender_tag(message.from_user),
                chat_id=message.chat.id,
                description=f"TOPUP-{oid}",
            )
            if not ok:
                await message.answer(
                    t(uid, "hp_error"),
                    reply_markup=main_menu_kb(uid),
                    parse_mode=ParseMode.HTML,
                )
            await state.clear()
            return
        await state.set_state(GiftFlow.wallet_card_receipt)
        await message.answer(
            t(uid, "topup_card_info").format(amount=amount),
            reply_markup=back_menu_kb(uid),
            parse_mode=ParseMode.HTML,
        )
    elif method == "ton":
        await state.set_state(GiftFlow.wallet_ton_receipt)
        await message.answer(
            t(uid, "topup_ton_info").format(amount=amount),
            reply_markup=back_menu_kb(uid),
            parse_mode=ParseMode.HTML,
        )
    else:
        await state.set_state(GiftFlow.wallet_trx_receipt)
        await message.answer(
            t(uid, "topup_trx_info").format(amount=amount),
            reply_markup=back_menu_kb(uid),
            parse_mode=ParseMode.HTML,
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
            parse_mode=ParseMode.HTML,
        )
    else:
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=caption + f"\n\n{message.text or '—'}",
            reply_markup=admin_topup_kb(oid),
            parse_mode=ParseMode.HTML,
        )

    await state.clear()
    await message.answer(
        t(uid, "topup_receipt_done"),
        reply_markup=main_menu_kb(uid),
        parse_mode=ParseMode.HTML,
    )


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
    data = await state.get_data()
    platform = data.get("platform") or "tg"
    raw = (message.text or "").strip()

    if platform == "tg":
        if not raw:
            await message.answer(t(uid, "ask_id_valid"))
            return
        await message.answer(t(uid, "checking"))
        wait_msg = await message.answer("⏳", parse_mode=ParseMode.HTML)
        info = await fetch_account_info(raw)
        if info is None:
            await safe_edit(wait_msg, t(uid, "not_found"), back_menu_kb(uid))
            return
        await state.update_data(target=info, platform="tg")
        beauty = random.randint(70, 100)
        eta = random.randint(5, 10)
        username_str = f"@{info['username']}" if info["username"] != "—" else "—"
        text = (
            f"{t(uid, 'analysis_header')}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"{t(uid, 'lbl_name')} {info['first_name']}\n"
            f"{t(uid, 'lbl_last')} {info['last_name']}\n"
            f"{t(uid, 'lbl_id')} <code>{info['id']}</code>\n"
            f"{t(uid, 'lbl_username')} {username_str}\n"
            f"{t(uid, 'lbl_bot')} {t(uid, 'yes') if info['is_bot'] else t(uid, 'no')}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"{t(uid, 'lbl_violation')} <b>{beauty}%</b>\n"
            f"{t(uid, 'lbl_freeze_time')} <b>{eta} {t(uid, 'minute')}</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{t(uid, 'ask_confirm')}"
        )
        await state.set_state(GiftFlow.confirming)
        await safe_edit(wait_msg, text, confirm_kb(uid))
        return

    if platform == "wa":
        if not raw:
            await message.answer(t(uid, "ask_id_valid_wa"))
            return
        info = await fetch_wa_account_info(raw)
        if info is None:
            await message.answer(t(uid, "not_found_wa"), parse_mode=ParseMode.HTML)
            return
        await state.update_data(target=info, platform="wa")
        target_display = info["phone"]
        text = t(uid, "wa_confirm_simple").format(target=target_display)
        await state.set_state(GiftFlow.confirming)
        await message.answer(
            text, reply_markup=confirm_kb(uid), parse_mode=ParseMode.HTML
        )
        return

    if platform == "rubika":
        if not raw:
            await message.answer(t(uid, "ask_id_valid_rubika"))
            return
        info = await fetch_rubika_account_info(raw)
        if info is None:
            await message.answer(t(uid, "not_found_rubika"), parse_mode=ParseMode.HTML)
            return
        await state.update_data(target=info, platform="rubika")
        target_display = (
            f"@{info['username']}" if info["username"] != "—" else str(info["id"])
        )
        text = t(uid, "rubika_confirm_simple").format(target=target_display)
        await state.set_state(GiftFlow.confirming)
        await message.answer(
            text, reply_markup=confirm_kb(uid), parse_mode=ParseMode.HTML
        )
        return

    if platform == "soroush":
        if not raw:
            await message.answer(t(uid, "ask_id_valid_soroush"))
            return
        info = await fetch_soroush_account_info(raw)
        if info is None:
            await message.answer(t(uid, "not_found_soroush"), parse_mode=ParseMode.HTML)
            return
        await state.update_data(target=info, platform="soroush")
        target_display = (
            f"@{info['username']}" if info["username"] != "—" else str(info["id"])
        )
        text = t(uid, "soroush_confirm_simple").format(target=target_display)
        await state.set_state(GiftFlow.confirming)
        await message.answer(
            text, reply_markup=confirm_kb(uid), parse_mode=ParseMode.HTML
        )
        return


@dp.callback_query(F.data == "confirm_yes")
async def cb_confirm_yes(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    await call.answer(t(uid, "confirmed_yes"))
    await state.set_state(GiftFlow.choosing_payment)
    data = await state.get_data()
    platform = data.get("platform") or "tg"
    if platform == "rubika":
        await safe_edit(call.message, t(uid, "payment_header_rubika"), payment_kb(uid))
    elif platform == "soroush":
        await safe_edit(call.message, t(uid, "payment_header_soroush"), payment_kb(uid))
    else:
        await safe_edit(call.message, t(uid, "payment_header"), payment_kb(uid))


@dp.callback_query(F.data == "confirm_no")
async def cb_confirm_no(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    await call.answer(t(uid, "confirmed_no"))
    data = await state.get_data()
    platform = data.get("platform") or "tg"
    await state.clear()
    await state.update_data(platform=platform)
    name = call.from_user.first_name or "User"
    welcome_key = _platform_welcome_key(platform)
    await safe_edit(
        call.message,
        t(uid, "cancelled") + "\n\n" + t(uid, welcome_key).format(name=name),
        main_menu_kb(uid, platform),
    )


@dp.callback_query(F.data == "back_payment")
async def cb_back_payment(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    await call.answer()
    await state.set_state(GiftFlow.choosing_payment)
    data = await state.get_data()
    platform = data.get("platform") or "tg"
    if platform == "rubika":
        await safe_edit(call.message, t(uid, "payment_header_rubika"), payment_kb(uid))
    elif platform == "soroush":
        await safe_edit(call.message, t(uid, "payment_header_soroush"), payment_kb(uid))
    else:
        await safe_edit(call.message, t(uid, "payment_header"), payment_kb(uid))


@dp.callback_query(F.data == "pay_card")
async def cb_pay_card(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    await call.answer()
    data = await state.get_data()
    platform = data.get("platform") or "tg"
    price = _current_ban_price(platform)
    if not HOOSHPAY_API_KEY:
        await state.set_state(GiftFlow.waiting_card_receipt)
        await safe_edit(call.message, t(uid, "card_text"), back_menu_kb(uid))
        return
    target = data.get("target", {})
    oid = new_id()
    await safe_edit(call.message, t(uid, "hp_creating"))
    kind = "ban"
    if platform == "rubika":
        kind = "ban_rubika"
    elif platform == "soroush":
        kind = "ban_soroush"
    ok = await open_card_gateway(
        uid=uid,
        kind=kind,
        amount=price,
        oid=oid,
        buyer_tag=sender_tag(call.from_user),
        target=target,
        edit_target=call.message,
        description=f"BAN-{oid}",
    )
    if not ok:
        await safe_edit(call.message, t(uid, "hp_error"), payment_kb(uid))
        return


@dp.callback_query(F.data.startswith("hpcheck:"))
async def cb_hp_check(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    inv_uid = call.data.split(":", 1)[1]
    if inv_uid not in pending_invoices:
        await call.answer("✅")
        return
    data = await hooshpay_verify_invoice(inv_uid)
    if data:
        tracking = str((data.get("data") or {}).get("tracking_code") or "")
        await call.answer("✅")
        await complete_pending_invoice(inv_uid, tracking=tracking)
    else:
        await call.answer(t(uid, "hp_not_paid"), show_alert=True)


@dp.callback_query(F.data == "pay_crypto")
async def cb_pay_crypto(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    await call.answer()
    await state.set_state(GiftFlow.choosing_crypto)
    await safe_edit(call.message, t(uid, "crypto_text"), crypto_kb(uid))


@dp.callback_query(F.data == "crypto_ton")
async def cb_crypto_ton(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    await call.answer()
    await state.set_state(GiftFlow.waiting_ton_receipt)
    await state.update_data(ton_photo_id=None, ton_hash=None)
    await safe_edit(call.message, t(uid, "ton_text"), back_menu_kb(uid))


@dp.callback_query(F.data == "crypto_trx")
async def cb_crypto_trx(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    await call.answer()
    await state.set_state(GiftFlow.waiting_trx_receipt)
    await state.update_data(trx_photo_id=None, trx_hash=None)
    await safe_edit(call.message, t(uid, "trx_text"), back_menu_kb(uid))


@dp.callback_query(F.data == "pay_balance")
async def cb_pay_balance(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    await call.answer()
    data = await state.get_data()
    target = data.get("target", {})
    platform = data.get("platform") or "tg"
    price = _current_ban_price(platform)
    balance = user_balances.get(uid, 0)
    if balance < price:
        await safe_edit(
            call.message,
            t(uid, "balance_insufficient").format(balance=balance, price=price),
            payment_kb(uid),
        )
        return

    user_balances[uid] = balance - price
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
        f"💰 <b>Paid from balance — {price:,} Toman deducted</b>"
    )

    await bot.send_message(
        chat_id=ADMIN_ID,
        text=caption,
        reply_markup=admin_ban_kb(oid),
        parse_mode=ParseMode.HTML,
    )

    await state.clear()
    await state.update_data(platform=platform)
    await safe_edit(
        call.message,
        t(uid, "balance_paid_msg").format(balance=new_balance, price=price),
        main_menu_kb(uid, platform),
    )


@dp.callback_query(F.data.in_({"lookup_pay_card", "lookup_pay_crypto"}))
async def cb_lookup_pay_gateway(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    await call.answer()
    data = await state.get_data()
    platform = data.get("lookup_platform") or "rubika"
    price = data.get("lookup_price") or RUBIKA_LOOKUP_PRICE
    target = data.get("lookup_target") or {}
    oid = new_id()
    await safe_edit(call.message, t(uid, "hp_creating"))
    kind = "lookup_rubika" if platform == "rubika" else "lookup_soroush"
    ok = await open_card_gateway(
        uid=uid,
        kind=kind,
        amount=price,
        oid=oid,
        buyer_tag=sender_tag(call.from_user),
        target=target,
        edit_target=call.message,
        description=f"LOOKUP-{platform.upper()}-{oid}",
    )
    if not ok:
        await safe_edit(call.message, t(uid, "hp_error"), back_menu_kb(uid))
        return


@dp.callback_query(F.data == "lookup_pay_balance")
async def cb_lookup_pay_balance(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    await call.answer()
    data = await state.get_data()
    platform = data.get("lookup_platform") or "rubika"
    price = data.get("lookup_price") or RUBIKA_LOOKUP_PRICE
    target = data.get("lookup_target") or {}
    balance = user_balances.get(uid, 0)
    if balance < price:
        await safe_edit(
            call.message,
            t(uid, "balance_insufficient").format(balance=balance, price=price),
            back_menu_kb(uid),
        )
        return
    user_balances[uid] = balance - price
    new_balance = user_balances[uid]
    oid = new_id()
    target_display = (
        f"@{target.get('username')}"
        if target.get("username") and target.get("username") != "—"
        else str(target.get("id", "—"))
    )
    caption = (
        f"📱 <b>User To Number Lookup — Paid from balance</b> #{oid}\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 {sender_tag(call.from_user)}\n"
        f"🆔 <code>{uid}</code>\n"
        f"💳 {t(uid, 'method_balance')}\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"🎯 Target: <code>{target_display}</code>\n"
        f"🏷 Platform: <b>{platform.title()}</b>\n"
        f"💰 Paid: <b>{price:,} Toman</b>"
    )
    await bot.send_message(chat_id=ADMIN_ID, text=caption, parse_mode=ParseMode.HTML)
    await state.clear()
    await state.update_data(platform=platform)
    await safe_edit(
        call.message,
        t(uid, "pl_paid_success").format(
            target=f"<code>{target_display}</code>", price=price
        ),
        main_menu_kb(uid, platform),
    )


async def finalize_ban_order(
    message: Message,
    state: FSMContext,
    method_key: str,
    photo_id: str = None,
    hash_text: str = None,
):
    uid = message.from_user.id
    data = await state.get_data()
    target = data.get("target", {})
    platform = data.get("platform") or "tg"
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
            parse_mode=ParseMode.HTML,
        )
        if hash_text:
            await bot.send_message(
                chat_id=ADMIN_ID,
                text=f"{t(uid, 'order_hash')}\n<code>{hash_text}</code>",
                parse_mode=ParseMode.HTML,
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
            parse_mode=ParseMode.HTML,
        )

    await state.clear()
    await state.update_data(platform=platform)
    await message.answer(
        t(uid, "receipt_done"),
        reply_markup=main_menu_kb(uid, platform),
        parse_mode=ParseMode.HTML,
    )


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
                await message.answer(
                    t(uid, "invalid_hash_ton"), parse_mode=ParseMode.HTML
                )
                return
            await finalize_ban_order(
                message, state, "method_ton", new_photo, message.caption
            )
            return
        if photo_id:
            await message.answer(t(uid, "photo_already"), parse_mode=ParseMode.HTML)
            return
        if saved_hash:
            await finalize_ban_order(
                message, state, "method_ton", new_photo, saved_hash
            )
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
            await finalize_ban_order(
                message, state, "method_ton", photo_id, message.text
            )
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
                await message.answer(
                    t(uid, "invalid_hash_trx"), parse_mode=ParseMode.HTML
                )
                return
            await finalize_ban_order(
                message, state, "method_trx", new_photo, message.caption
            )
            return
        if photo_id:
            await message.answer(t(uid, "photo_already"), parse_mode=ParseMode.HTML)
            return
        if saved_hash:
            await finalize_ban_order(
                message, state, "method_trx", new_photo, saved_hash
            )
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
            await finalize_ban_order(
                message, state, "method_trx", photo_id, message.text
            )
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
    try:
        await call.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest:
        pass
    await call.message.reply(f"✅ <b>#{oid}</b>", parse_mode=ParseMode.HTML)
    if order:
        try:
            uid = order["user_id"]
            text = t(uid, "user_order_ok").format(
                order_id=oid, method=t(uid, order["method"])
            )
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
    try:
        await call.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest:
        pass
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
    try:
        await call.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest:
        pass
    await call.message.reply(f"✅ Top-up <b>#{oid}</b>", parse_mode=ParseMode.HTML)
    if order:
        uid = order["user_id"]
        amount = order["amount"]
        user_balances[uid] = user_balances.get(uid, 0) + amount
        try:
            text = t(uid, "tup_ok_msg").format(
                amount=amount, balance=user_balances[uid]
            )
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
    try:
        await call.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest:
        pass
    await call.message.reply(f"❌ Top-up <b>#{oid}</b>", parse_mode=ParseMode.HTML)
    if order:
        uid = order["user_id"]
        try:
            await bot.send_message(
                chat_id=uid, text=t(uid, "tup_no_msg"), parse_mode=ParseMode.HTML
            )
        except Exception as e:
            print(f"[!] notify error: {e}")


async def main():
    global _tguser_lock
    _tguser_lock = asyncio.Lock()

    background = [asyncio.create_task(invoice_poller())]
    if HOOSHPAY_WEBHOOK_PORT:
        background.append(asyncio.create_task(run_webhook_server()))

    if HOOSHPAY_API_KEY:
        print(
            f"[+] Card gateway enabled (fee_mode={HOOSHPAY_FEE_MODE}, base={HOOSHPAY_BASE})"
        )
    else:
        print(
            "[i] HOOSHPAY_API_KEY not set: card payments fall back to the manual flow."
        )

    print(
        f"[+] Telegram resolver: {TG_USER_BASE} (cache={TG_USER_CACHE_TTL}s, rate={TG_USER_MIN_INTERVAL}s)"
    )
    print("[+] Bot is starting...")
    try:
        await dp.start_polling(bot, allowed_updates=["message", "callback_query"])
    finally:
        for task in background:
            task.cancel()
        await asyncio.gather(*background, return_exceptions=True)
        if _hp_session is not None and not _hp_session.closed:
            await _hp_session.close()
        if _api_session is not None and not _api_session.closed:
            await _api_session.close()
        if _tguser_session is not None and not _tguser_session.closed:
            await _tguser_session.close()


if __name__ == "__main__":
    asyncio.run(main())
