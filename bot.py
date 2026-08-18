import os
import json
import time
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import telebot
from telebot import types


# =========================================================
# RENDER
# =========================================================

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"SELL STARS RT is running")

    def log_message(self, format, *args):
        pass


def run_server():
    port = int(os.environ.get("PORT", "10000"))
    server = HTTPServer(("0.0.0.0", port), Handler)
    print("Web server started on port", port)
    server.serve_forever()


threading.Thread(target=run_server, daemon=True).start()


# =========================================================
# SETTINGS
# =========================================================

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не найден в Render Environment")

ADMIN_ID = 6189064599

SUPPORT_USERNAME = "RtSupp_bot"
REVIEWS_URL = "https://t.me/RTstoreREVIEW"

TON_ADDRESS = "UQAm8vafnYdyPH1u-IA8xD3Sqh3rO-K76LhPh8NUu4oY6J7S"

# Ссылка, которую ты прислал.
YOOMONEY_URL = "https://yoomoney.ru/to/4100119601496891"

# Если позже будут другие реквизиты — меняются только эти две строки.
SBER_DETAILS = YOOMONEY_URL
SBP_DETAILS = YOOMONEY_URL

PRICES_FILE = "prices.json"
USERS_FILE = "users.json"
PURCHASES_FILE = "purchases.json"
BLOCKED_FILE = "blocked.json"

DEFAULT_TON_RUB_RATE = 125.0

DEFAULT_PRICES = {
    "star_price": 1.50,
    "stars": {
        "50": 75,
        "100": 150,
        "150": 225,
        "250": 375,
        "500": 750,
        "1000": 1500
    },
    "premium": {
        "3": 1100,
        "6": 1550,
        "12": 2599
    },
    "ton_rub_rate": DEFAULT_TON_RUB_RATE
}


# =========================================================
# BOT
# =========================================================

bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)


# =========================================================
# MEMORY
# =========================================================

orders = {}
users = set()
blocked_users = set()
purchases = []


# =========================================================
# JSON HELPERS
# =========================================================

def load_json(filename, default):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(filename, data):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"Ошибка {filename}: {e}")
        return False


# =========================================================
# USERS
# =========================================================

loaded_users = load_json(USERS_FILE, [])
try:
    users = {int(x) for x in loaded_users}
except Exception:
    users = set()


def save_users():
    save_json(USERS_FILE, list(users))


def add_user(user_id):
    if user_id not in users:
        users.add(user_id)
        save_users()


# =========================================================
# BLOCKED
# =========================================================

loaded_blocked = load_json(BLOCKED_FILE, [])
try:
    blocked_users = {int(x) for x in loaded_blocked}
except Exception:
    blocked_users = set()


def save_blocked():
    save_json(BLOCKED_FILE, list(blocked_users))


# =========================================================
# PURCHASES
# =========================================================

loaded_purchases = load_json(PURCHASES_FILE, [])
purchases = loaded_purchases if isinstance(loaded_purchases, list) else []


def save_purchases():
    save_json(PURCHASES_FILE, purchases)


# =========================================================
# PRICES
# =========================================================

def load_prices():
    data = load_json(PRICES_FILE, {})

    result = {
        "star_price": float(
            data.get("star_price", DEFAULT_PRICES["star_price"])
        ),
        "stars": {},
        "premium": {},
        "ton_rub_rate": float(
            data.get("ton_rub_rate", DEFAULT_TON_RUB_RATE)
        )
    }

    saved_stars = data.get("stars", {})
    saved_premium = data.get("premium", {})

    for amount, default in DEFAULT_PRICES["stars"].items():
        try:
            result["stars"][amount] = float(
                saved_stars.get(amount, default)
            )
        except Exception:
            result["stars"][amount] = float(default)

    for months, default in DEFAULT_PRICES["premium"].items():
        try:
            result["premium"][months] = float(
                saved_premium.get(months, default)
            )
        except Exception:
            result["premium"][months] = float(default)

    save_prices_data = dict(result)
    save_json(PRICES_FILE, save_prices_data)

    return result


def save_prices():
    save_json(PRICES_FILE, prices)


prices = load_prices()
TON_RUB_RATE = float(
    prices.get("ton_rub_rate", DEFAULT_TON_RUB_RATE)
)


# =========================================================
# HELPERS
# =========================================================

def is_admin(user_id):
    return user_id == ADMIN_ID


def is_blocked(user_id):
    return user_id in blocked_users and user_id != ADMIN_ID


def username(user):
    if user.username:
        return "@" + user.username
    return (user.first_name or "Пользователь") + f" (ID {user.id})"


def money(value):
    value = float(value)
    if value.is_integer():
        return str(int(value))
    return str(round(value, 2)).replace(".", ",")


def ton(value):
    return f"{float(value):.4f}".rstrip("0").rstrip(".")


def ton_payment_price(rub_price):
    # Скидка 1% действует только при выборе способа оплаты TON.
    discounted_rub = float(rub_price) * 0.99
    return round(discounted_rub / TON_RUB_RATE, 4)


def current_ton_price_without_discount(rub_price):
    return round(float(rub_price) / TON_RUB_RATE, 4)


def order_text(order):
    product = order.get("product")

    if product == "Stars":
        product_text = f"⭐ Stars: {order.get('stars', 0)}"
    else:
        product_text = f"💎 Premium: {order.get('months', 0)} мес."

    price_rub = float(order.get("price_rub", 0))

    text = (
        product_text
        + "\n"
        + "💰 Цена: "
        + money(price_rub)
        + " ₽"
    )

    if order.get("recipient"):
        text += "\n🎁 Получатель: " + str(order["recipient"])

    return text


def create_order(user_id, data):
    order = dict(data)
    order["user_id"] = user_id
    order["created_at"] = int(time.time())
    order["status"] = "created"
    orders[user_id] = order
    return order


def finish_purchase(user_id):
    order = orders.get(user_id)
    if not order:
        return False

    record = dict(order)
    record["completed_at"] = int(time.time())
    purchases.append(record)
    save_purchases()
    orders.pop(user_id, None)
    return True


# =========================================================
# MAIN MENU
# =========================================================

def main_menu(user_id):
    markup = types.InlineKeyboardMarkup(row_width=1)

    markup.add(
        types.InlineKeyboardButton("⭐ Купить Stars", callback_data="stars")
    )
    markup.add(
        types.InlineKeyboardButton(
            "💎 Купить Telegram Premium",
            callback_data="premium"
        )
    )
    markup.add(
        types.InlineKeyboardButton("👤 Профиль", callback_data="profile")
    )
    markup.add(
        types.InlineKeyboardButton("⭐ Отзывы", url=REVIEWS_URL)
    )
    markup.add(
        types.InlineKeyboardButton(
            "💬 Поддержка",
            url="https://t.me/" + SUPPORT_USERNAME
        )
    )

    if is_admin(user_id):
        markup.add(
            types.InlineKeyboardButton(
                "📊 История покупок",
                callback_data="purchase_history"
            )
        )
        markup.add(
            types.InlineKeyboardButton(
                "🚫 Блокировка",
                callback_data="block_menu"
            )
        )
        markup.add(
            types.InlineKeyboardButton(
                "💰 Изменить цены",
                callback_data="prices"
            )
        )
        markup.add(
            types.InlineKeyboardButton(
                "📢 Рассылка",
                callback_data="broadcast"
            )
        )

    return markup


# =========================================================
# START
# =========================================================

@bot.message_handler(commands=["start"])
def start(message):
    user_id = message.from_user.id
    add_user(user_id)

    if is_blocked(user_id):
        bot.send_message(message.chat.id, "🚫 Вы заблокированы.")
        return

    bot.send_message(
        message.chat.id,
        "👋 Привет, " + username(message.from_user) + "!\n\n"
        "✨ Добро пожаловать в SELL STARS RT!\n\n"
        "⭐ Telegram Stars\n"
        "💎 Telegram Premium\n\n"
        "Выберите нужное действие:",
        reply_markup=main_menu(user_id)
    )


# =========================================================
# HOME
# =========================================================

@bot.callback_query_handler(func=lambda c: c.data == "home")
def home(call):
    if is_blocked(call.from_user.id):
        bot.answer_callback_query(
            call.id, "🚫 Вы заблокированы", show_alert=True
        )
        return

    bot.answer_callback_query(call.id)

    try:
        bot.edit_message_text(
            "🏠 Главное меню\n\nВыберите нужное действие:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=main_menu(call.from_user.id)
        )
    except Exception:
        bot.send_message(
            call.message.chat.id,
            "🏠 Главное меню",
            reply_markup=main_menu(call.from_user.id)
        )


# =========================================================
# PROFILE
# =========================================================

@bot.callback_query_handler(func=lambda c: c.data == "profile")
def profile(call):
    user_id = call.from_user.id

    if is_blocked(user_id):
        bot.answer_callback_query(
            call.id, "🚫 Вы заблокированы", show_alert=True
        )
        return

    bot.answer_callback_query(call.id)

    user_purchases = [
        x for x in purchases if x.get("user_id") == user_id
    ]

    total_rub = sum(
        float(x.get("price_rub", 0)) for x in user_purchases
    )

    total_stars = sum(
        int(x.get("stars", 0))
        for x in user_purchases
        if x.get("product") == "Stars"
    )

    total_premium = sum(
        int(x.get("months", 0))
        for x in user_purchases
        if x.get("product") == "Premium"
    )

    text = (
        "👤 ПРОФИЛЬ\n\n"
        f"🆔 ID: {user_id}\n"
        "👤 Username: "
        + (
            "@" + call.from_user.username
            if call.from_user.username
            else "не указан"
        )
        + "\n\n"
        f"⭐ Всего Stars: {total_stars}\n"
        f"💎 Premium куплено: {total_premium} мес.\n"
        f"💰 Потрачено: {money(total_rub)} ₽\n"
        f"📦 Покупок: {len(user_purchases)}"
    )

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("⬅️ Назад", callback_data="home")
    )

    try:
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
    except Exception:
        bot.send_message(
            call.message.chat.id,
            text,
            reply_markup=markup
        )


# =========================================================
# STARS
# =========================================================

@bot.callback_query_handler(func=lambda c: c.data == "stars")
def stars(call):
    user_id = call.from_user.id

    if is_blocked(user_id):
        bot.answer_callback_query(
            call.id, "🚫 Вы заблокированы", show_alert=True
        )
        return

    bot.answer_callback_query(call.id)

    markup = types.InlineKeyboardMarkup(row_width=1)

    for amount, price_rub in prices["stars"].items():
        markup.add(
            types.InlineKeyboardButton(
                f"⭐ {amount} — {money(price_rub)} ₽",
                callback_data="star_" + amount
            )
        )

    markup.add(
        types.InlineKeyboardButton(
            "✏️ Своё количество",
            callback_data="custom_stars"
        )
    )
    markup.add(
        types.InlineKeyboardButton("⬅️ Назад", callback_data="home")
    )

    text = (
        "⭐ ВЫБЕРИТЕ STARS\n\n"
        "💎 На данный момент доступны способы оплаты: TON и рубли\n"
        "🇺🇦 В скором времени будет доступна оплата в гривнах\n\n"
        "💱 Курс: 1 TON = "
        + money(TON_RUB_RATE)
        + " ₽"
    )

    try:
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
    except Exception:
        bot.send_message(
            call.message.chat.id,
            text,
            reply_markup=markup
        )


# =========================================================
# CHOOSE STARS
# =========================================================

@bot.callback_query_handler(
    func=lambda c: c.data.startswith("star_")
)
def choose_stars(call):
    user_id = call.from_user.id

    if is_blocked(user_id):
        bot.answer_callback_query(
            call.id, "🚫 Вы заблокированы", show_alert=True
        )
        return

    amount = call.data.split("_", 1)[1]

    if amount not in prices["stars"]:
        bot.answer_callback_query(
            call.id, "❌ Такой пакет не найден", show_alert=True
        )
        return

    amount_int = int(amount)
    price_rub = float(prices["stars"][amount])

    create_order(
        user_id,
        {
            "product": "Stars",
            "stars": amount_int,
            "amount": amount_int,
            "price_rub": price_rub
        }
    )

    bot.answer_callback_query(call.id)

    show_recipient(
        call.message.chat.id,
        call.message.message_id,
        user_id
    )


# =========================================================
# CUSTOM STARS
# =========================================================

@bot.callback_query_handler(func=lambda c: c.data == "custom_stars")
def custom_stars(call):
    if is_blocked(call.from_user.id):
        bot.answer_callback_query(
            call.id, "🚫 Вы заблокированы", show_alert=True
        )
        return

    bot.answer_callback_query(call.id)

    msg = bot.send_message(
        call.message.chat.id,
        "✏️ Напишите количество Stars.\n\n"
        "Минимум — 50 Stars.\n"
        "Цена рассчитывается автоматически."
    )

    bot.register_next_step_handler(msg, custom_stars_amount)


def custom_stars_amount(message):
    user_id = message.from_user.id

    if is_blocked(user_id):
        return

    if not message.text:
        bot.send_message(
            message.chat.id,
            "❌ Введите количество числом."
        )
        return

    try:
        amount = int(message.text.strip())
    except ValueError:
        bot.send_message(
            message.chat.id,
            "❌ Введите количество числом."
        )
        return

    if amount < 50:
        bot.send_message(
            message.chat.id,
            "❌ Минимум — 50 Stars."
        )
        return

    price_rub = round(
        amount * float(prices["star_price"]),
        2
    )

    create_order(
        user_id,
        {
            "product": "Stars",
            "stars": amount,
            "amount": amount,
            "price_rub": price_rub
        }
    )

    show_recipient(
        message.chat.id,
        None,
        user_id
    )


# =========================================================
# PREMIUM
# =========================================================

@bot.callback_query_handler(func=lambda c: c.data == "premium")
def premium(call):
    user_id = call.from_user.id

    if is_blocked(user_id):
        bot.answer_callback_query(
            call.id, "🚫 Вы заблокированы", show_alert=True
        )
        return

    bot.answer_callback_query(call.id)

    markup = types.InlineKeyboardMarkup(row_width=1)

    for months, price_rub in prices["premium"].items():
        markup.add(
            types.InlineKeyboardButton(
                f"💎 {months} мес. — {money(price_rub)} ₽",
                callback_data="premium_" + months
            )
        )

    markup.add(
        types.InlineKeyboardButton("⬅️ Назад", callback_data="home")
    )

    text = (
        "💎 TELEGRAM PREMIUM\n\n"
        "💎 На данный момент доступны способы оплаты: TON и рубли\n"
        "🇺🇦 В скором времени будет доступна оплата в гривнах\n\n"
        "💱 Курс: 1 TON = "
        + money(TON_RUB_RATE)
        + " ₽"
    )

    try:
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
    except Exception:
        bot.send_message(
            call.message.chat.id,
            text,
            reply_markup=markup
        )


# =========================================================
# CHOOSE PREMIUM
# =========================================================

@bot.callback_query_handler(
    func=lambda c: c.data.startswith("premium_")
)
def choose_premium(call):
    user_id = call.from_user.id

    if is_blocked(user_id):
        bot.answer_callback_query(
            call.id, "🚫 Вы заблокированы", show_alert=True
        )
        return

    months = call.data.split("_", 1)[1]

    if months not in prices["premium"]:
        bot.answer_callback_query(
            call.id,
            "❌ Такой вариант отсутствует",
            show_alert=True
        )
        return

    create_order(
        user_id,
        {
            "product": "Premium",
            "months": int(months),
            "price_rub": float(prices["premium"][months])
        }
    )

    bot.answer_callback_query(call.id)

    show_recipient(
        call.message.chat.id,
        call.message.message_id,
        user_id
    )


# =========================================================
# RECIPIENT
# =========================================================

def show_recipient(chat_id, message_id, user_id):
    order = orders.get(user_id)

    if not order:
        return

    markup = types.InlineKeyboardMarkup(row_width=1)

    markup.add(
        types.InlineKeyboardButton(
            "👤 Себе",
            callback_data="recipient_self"
        )
    )
    markup.add(
        types.InlineKeyboardButton(
            "🎁 Другому",
            callback_data="recipient_other"
        )
    )

    back = "stars" if order["product"] == "Stars" else "premium"

    markup.add(
        types.InlineKeyboardButton(
            "⬅️ Назад",
            callback_data=back
        )
    )

    text = order_text(order) + "\n\nКому оформить заказ?"

    if message_id is not None:
        try:
            bot.edit_message_text(
                text,
                chat_id,
                message_id,
                reply_markup=markup
            )
            return
        except Exception:
            pass

    bot.send_message(
        chat_id,
        text,
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda c: c.data == "recipient_self")
def recipient_self(call):
    user_id = call.from_user.id

    if is_blocked(user_id):
        bot.answer_callback_query(
            call.id, "🚫 Вы заблокированы", show_alert=True
        )
        return

    order = orders.get(user_id)

    if not order:
        bot.answer_callback_query(
            call.id, "❌ Заказ не найден", show_alert=True
        )
        return

    order["recipient"] = username(call.from_user)

    bot.answer_callback_query(call.id)

    show_payment(
        call.message.chat.id,
        call.message.message_id,
        user_id
    )


@bot.callback_query_handler(func=lambda c: c.data == "recipient_other")
def recipient_other(call):
    if is_blocked(call.from_user.id):
        bot.answer_callback_query(
            call.id, "🚫 Вы заблокированы", show_alert=True
        )
        return

    bot.answer_callback_query(call.id)

    msg = bot.send_message(
        call.message.chat.id,
        "🎁 Напишите @username получателя.\n\n"
        "Например:\n"
        "@username"
    )

    bot.register_next_step_handler(msg, recipient_other_text)


def recipient_other_text(message):
    user_id = message.from_user.id

    if is_blocked(user_id):
        return

    if not message.text:
        bot.send_message(
            message.chat.id,
            "❌ Укажите username."
        )
        return

    recipient = message.text.strip()

    if not recipient.startswith("@"):
        recipient = "@" + recipient

    order = orders.get(user_id)

    if not order:
        bot.send_message(
            message.chat.id,
            "❌ Заказ не найден."
        )
        return

    order["recipient"] = recipient

    show_payment(
        message.chat.id,
        None,
        user_id
    )


@bot.callback_query_handler(func=lambda c: c.data == "back_recipient")
def back_recipient(call):
    bot.answer_callback_query(call.id)
    show_recipient(
        call.message.chat.id,
        call.message.message_id,
        call.from_user.id
    )


# =========================================================
# PAYMENT MENU
# =========================================================

def payment_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)

    markup.add(
        types.InlineKeyboardButton(
            "💎 TON",
            callback_data="pay_ton"
        )
    )
    markup.add(
        types.InlineKeyboardButton(
            "🏦 Сбербанк",
            callback_data="pay_sber"
        )
    )
    markup.add(
        types.InlineKeyboardButton(
            "💳 СБП",
            callback_data="pay_sbp"
        )
    )
    markup.add(
        types.InlineKeyboardButton(
            "💰 ЮMoney",
            callback_data="pay_yoomoney"
        )
    )
    markup.add(
        types.InlineKeyboardButton(
            "⬅️ Назад",
            callback_data="back_recipient"
        )
    )

    return markup


def show_payment(chat_id, message_id, user_id):
    order = orders.get(user_id)

    if not order:
        return

    text = (
        "💳 ОПЛАТА ЗАКАЗА\n\n"
        + order_text(order)
        + "\n\n"
        "Выберите способ оплаты:"
    )

    markup = payment_menu()

    if message_id is not None:
        try:
            bot.edit_message_text(
                text,
                chat_id,
                message_id,
                reply_markup=markup
            )
            return
        except Exception:
            pass

    bot.send_message(
        chat_id,
        text,
        reply_markup=markup
    )


# =========================================================
# TON PAYMENT
# =========================================================

@bot.callback_query_handler(func=lambda c: c.data == "pay_ton")
def pay_ton(call):
    user_id = call.from_user.id
    order = orders.get(user_id)

    if not order:
        bot.answer_callback_query(
            call.id, "❌ Заказ не найден", show_alert=True
        )
        return

    ton_amount = ton_payment_price(
        float(order["price_rub"])
    )

    order["payment_method"] = "TON"
    order["payment_status"] = "waiting_payment"
    order["ton_amount"] = ton_amount

    text = (
        "💎 ОПЛАТА TON\n\n"
        + order_text(order)
        + "\n\n"
        "🔥 Скидка 1% при оплате TON\n"
        "💎 К оплате: "
        + ton(ton_amount)
        + " TON\n\n"
        "📋 Адрес TON:\n"
        + TON_ADDRESS
        + "\n\n"
        "⚠️ После перевода сообщите админу об оплате.\n"
        "⏱ Заказ действует 30 минут."
    )

    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, text)


# =========================================================
# BANK / YOOMONEY PAYMENT
# =========================================================

def send_payment_details(call, details, method):
    user_id = call.from_user.id
    order = orders.get(user_id)

    if not order:
        bot.answer_callback_query(
            call.id, "❌ Заказ не найден", show_alert=True
        )
        return

    order["payment_method"] = method
    order["payment_status"] = "waiting_payment"

    bot.answer_callback_query(call.id)

    bot.send_message(
        call.message.chat.id,
        "💳 ОПЛАТА\n\n"
        + order_text(order)
        + "\n\n"
        "🏦 Способ: "
        + method
        + "\n\n"
        "📋 Реквизиты / ссылка:\n"
        + details
        + "\n\n"
        "После оплаты сообщите админу."
    )


@bot.callback_query_handler(func=lambda c: c.data == "pay_sber")
def pay_sber(call):
    send_payment_details(
        call,
        SBER_DETAILS,
        "Сбербанк"
    )


@bot.callback_query_handler(func=lambda c: c.data == "pay_sbp")
def pay_sbp(call):
    send_payment_details(
        call,
        SBP_DETAILS,
        "СБП"
    )


@bot.callback_query_handler(func=lambda c: c.data == "pay_yoomoney")
def pay_yoomoney(call):
    send_payment_details(
        call,
        YOOMONEY_URL,
        "ЮMoney"
    )


# =========================================================
# ADMIN: SET TON RATE
# =========================================================

@bot.message_handler(commands=["setton"])
def setton_command(message):
    global TON_RUB_RATE

    if not is_admin(message.from_user.id):
        return

    parts = message.text.split()

    if len(parts) != 2:
        bot.reply_to(
            message,
            "❌ Использование:\n/setton 125"
        )
        return

    try:
        new_rate = float(
            parts[1].replace(",", ".")
        )
    except ValueError:
        bot.reply_to(
            message,
            "❌ Введите число.\nНапример: /setton 130"
        )
        return

    if new_rate <= 0:
        bot.reply_to(
            message,
            "❌ Курс должен быть больше 0."
        )
        return

    TON_RUB_RATE = new_rate
    prices["ton_rub_rate"] = new_rate
    save_prices()

    bot.reply_to(
        message,
        "✅ Курс TON изменён\n\n"
        "💎 1 TON = "
        + money(new_rate)
        + " ₽"
    )


@bot.message_handler(commands=["tonrate"])
def tonrate_command(message):
    if not is_admin(message.from_user.id):
        return

    bot.reply_to(
        message,
        "💱 Текущий курс:\n"
        "1 TON = "
        + money(TON_RUB_RATE)
        + " ₽\n\n"
        "Изменить:\n"
        "/setton 130"
    )


# =========================================================
# ADMIN: BLOCK / UNBLOCK
# =========================================================

@bot.callback_query_handler(func=lambda c: c.data == "block_menu")
def block_menu(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
        return

    bot.answer_callback_query(call.id)

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton(
            "🚫 Заблокировать пользователя",
            callback_data="block_user"
        )
    )
    markup.add(
        types.InlineKeyboardButton(
            "✅ Разблокировать пользователя",
            callback_data="unblock_user"
        )
    )
    markup.add(
        types.InlineKeyboardButton(
            "📋 Список заблокированных",
            callback_data="blocked_list"
        )
    )
    markup.add(
        types.InlineKeyboardButton(
            "⬅️ Назад",
            callback_data="home"
        )
    )

    try:
        bot.edit_message_text(
            "🚫 УПРАВЛЕНИЕ БЛОКИРОВКОЙ",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
    except Exception:
        bot.send_message(
            call.message.chat.id,
            "🚫 УПРАВЛЕНИЕ БЛОКИРОВКОЙ",
            reply_markup=markup
        )


@bot.callback_query_handler(func=lambda c: c.data == "block_user")
def block_user(call):
    if not is_admin(call.from_user.id):
        return

    bot.answer_callback_query(call.id)

    msg = bot.send_message(
        call.message.chat.id,
        "Введите ID пользователя для блокировки:"
    )
    bot.register_next_step_handler(msg, block_user_id)


def block_user_id(message):
    if not is_admin(message.from_user.id):
        return

    try:
        user_id = int(message.text.strip())
    except Exception:
        bot.send_message(message.chat.id, "❌ ID должен быть числом.")
        return

    if user_id == ADMIN_ID:
        bot.send_message(message.chat.id, "❌ Нельзя заблокировать админа.")
        return

    blocked_users.add(user_id)
    save_blocked()

    bot.send_message(
        message.chat.id,
        f"✅ Пользователь {user_id} заблокирован."
    )


@bot.callback_query_handler(func=lambda c: c.data == "unblock_user")
def unblock_user(call):
    if not is_admin(call.from_user.id):
        return

    bot.answer_callback_query(call.id)

    msg = bot.send_message(
        call.message.chat.id,
        "Введите ID пользователя для разблокировки:"
    )
    bot.register_next_step_handler(msg, unblock_user_id)


def unblock_user_id(message):
    if not is_admin(message.from_user.id):
        return

    try:
        user_id = int(message.text.strip())
    except Exception:
        bot.send_message(message.chat.id, "❌ ID должен быть числом.")
        return

    if user_id in blocked_users:
        blocked_users.remove(user_id)
        save_blocked()
        bot.send_message(
            message.chat.id,
            f"✅ Пользователь {user_id} разблокирован."
        )
    else:
        bot.send_message(
            message.chat.id,
            "ℹ️ Этот пользователь не заблокирован."
        )


@bot.callback_query_handler(func=lambda c: c.data == "blocked_list")
def blocked_list(call):
    if not is_admin(call.from_user.id):
        return

    bot.answer_callback_query(call.id)

    if not blocked_users:
        text = "📋 Заблокированных пользователей нет."
    else:
        text = "📋 ЗАБЛОКИРОВАННЫЕ:\n\n"
        text += "\n".join(str(x) for x in sorted(blocked_users))

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(
            "⬅️ Назад",
            callback_data="block_menu"
        )
    )

    bot.send_message(
        call.message.chat.id,
        text,
        reply_markup=markup
    )


# =========================================================
# ADMIN: PRICE MENU
# =========================================================

@bot.callback_query_handler(func=lambda c: c.data == "prices")
def prices_menu(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
        return

    bot.answer_callback_query(call.id)

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton(
            "⭐ Изменить цену 1 Star",
            callback_data="price_star"
        )
    )

    for amount in prices["stars"]:
        markup.add(
            types.InlineKeyboardButton(
                f"⭐ Пакет {amount}",
                callback_data="price_stars_" + amount
            )
        )

    for months in prices["premium"]:
        markup.add(
            types.InlineKeyboardButton(
                f"💎 Premium {months} мес.",
                callback_data="price_premium_" + months
            )
        )

    markup.add(
        types.InlineKeyboardButton(
            "⬅️ Назад",
            callback_data="home"
        )
    )

    bot.send_message(
        call.message.chat.id,
        "💰 ИЗМЕНЕНИЕ ЦЕН",
        reply_markup=markup
    )


def ask_new_price(call, kind, key):
    if not is_admin(call.from_user.id):
        return

    bot.answer_callback_query(call.id)

    msg = bot.send_message(
        call.message.chat.id,
        "Введите новую цену в рублях:"
    )
    bot.register_next_step_handler(
        msg,
        set_price_value,
        kind,
        key
    )


@bot.callback_query_handler(func=lambda c: c.data == "price_star")
def price_star(call):
    ask_new_price(call, "star_price", None)


@bot.callback_query_handler(
    func=lambda c: c.data.startswith("price_stars_")
)
def price_stars(call):
    key = call.data.split("_", 2)[2]
    if key not in prices["stars"]:
        return
    ask_new_price(call, "stars", key)


@bot.callback_query_handler(
    func=lambda c: c.data.startswith("price_premium_")
)
def price_premium(call):
    key = call.data.split("_", 2)[2]
    if key not in prices["premium"]:
        return
    ask_new_price(call, "premium", key)


def set_price_value(message, kind, key):
    if not is_admin(message.from_user.id):
        return

    try:
        value = float(
            message.text.strip().replace(",", ".")
        )
    except Exception:
        bot.send_message(message.chat.id, "❌ Цена должна быть числом.")
        return

    if value <= 0:
        bot.send_message(
            message.chat.id,
            "❌ Цена должна быть больше 0."
        )
        return

    if kind == "star_price":
        prices["star_price"] = value
        label = "1 Star"
    elif kind == "stars":
        prices["stars"][key] = value
        label = f"{key} Stars"
    else:
        prices["premium"][key] = value
        label = f"Premium {key} мес."

    save_prices()

    bot.send_message(
        message.chat.id,
        "✅ Цена изменена\n\n"
        + label
        + ": "
        + money(value)
        + " ₽"
    )


# =========================================================
# ADMIN: PURCHASE HISTORY
# =========================================================

@bot.callback_query_handler(
    func=lambda c: c.data == "purchase_history"
)
def purchase_history(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
        return

    bot.answer_callback_query(call.id)

    if not purchases:
        text = "📊 История покупок пока пустая."
    else:
        recent = purchases[-20:]
        lines = ["📊 ПОСЛЕДНИЕ ПОКУПКИ\n"]

        for item in reversed(recent):
            product = item.get("product", "—")
            user_id = item.get("user_id", "—")
            price = money(item.get("price_rub", 0))
            method = item.get("payment_method", "—")

            if product == "Stars":
                product_name = f"⭐ {item.get('stars', 0)} Stars"
            else:
                product_name = f"💎 Premium {item.get('months', 0)} мес."

            lines.append(
                f"{product_name} | {price} ₽ | {method} | ID {user_id}"
            )

        text = "\n".join(lines)

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(
            "⬅️ Назад",
            callback_data="home"
        )
    )

    bot.send_message(
        call.message.chat.id,
        text,
        reply_markup=markup
    )


# =========================================================
# ADMIN: BROADCAST
# =========================================================

@bot.callback_query_handler(func=lambda c: c.data == "broadcast")
def broadcast(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
        return

    bot.answer_callback_query(call.id)

    msg = bot.send_message(
        call.message.chat.id,
        "📢 Отправьте сообщение для рассылки."
    )
    bot.register_next_step_handler(msg, do_broadcast)


def do_broadcast(message):
    if not is_admin(message.from_user.id):
        return

    sent = 0
    failed = 0

    for user_id in list(users):
        try:
            bot.copy_message(
                user_id,
                message.chat.id,
                message.message_id
            )
            sent += 1
        except Exception:
            failed += 1

    bot.send_message(
        message.chat.id,
        f"📢 Рассылка завершена.\n\n"
        f"✅ Отправлено: {sent}\n"
        f"❌ Ошибок: {failed}"
    )


# =========================================================
# RUN
# =========================================================

print("SELL STARS RT запущен")

while True:
    try:
        bot.infinity_polling(
            skip_pending=True,
            timeout=30,
            long_polling_timeout=30
        )
    except Exception as e:
        print("Ошибка бота:", e)
        time.sleep(5)
