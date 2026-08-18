import os
import json
import time
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import telebot
from telebot import types


# =========================================================
# RENDER SERVER
# =========================================================

class Handler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header(
            "Content-Type",
            "text/plain; charset=utf-8"
        )
        self.end_headers()

        self.wfile.write(
            b"SELL STARS RT is running"
        )

    def log_message(self, format, *args):
        pass


def run_server():
    port = int(
        os.environ.get("PORT", "10000")
    )

    server = HTTPServer(
        ("0.0.0.0", port),
        Handler
    )

    print(
        "Web server started on port",
        port
    )

    server.serve_forever()


threading.Thread(
    target=run_server,
    daemon=True
).start()


# =========================================================
# SETTINGS
# =========================================================

BOT_TOKEN = os.environ.get("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN не найден в Render Environment"
    )


ADMIN_ID = 6189064599

SUPPORT_USERNAME = "RtSupp_bot"

REVIEWS_URL = (
    "https://t.me/RTstoreREVIEW"
)

# TON-адрес
TON_ADDRESS = (
    "UQAm8vafnYdyPH1u-IA8xD3Sqh3rO-K76LhPh8NUu4oY6J7S"
)

# Твоя ссылка ЮMoney
YOOMONEY_URL = (
    "https://yoomoney.ru/to/4100119601496891"
)

# Для Сбера и СБП сейчас также используется
# эта ссылка, как ты попросил
SBER_DETAILS = YOOMONEY_URL
SBP_DETAILS = YOOMONEY_URL

# Курс TON к рублю
TON_RUB_RATE = 125.0

# Файлы
PRICES_FILE = "prices.json"
USERS_FILE = "users.json"
PURCHASES_FILE = "purchases.json"
BLOCKED_FILE = "blocked.json"


# =========================================================
# DEFAULT PRICES
# =========================================================

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
    }
}


# =========================================================
# BOT
# =========================================================

bot = telebot.TeleBot(
    BOT_TOKEN,
    parse_mode=None
)


# =========================================================
# MEMORY
# =========================================================

orders = {}

users = set()

blocked_users = set()

purchases = []

admin_waiting = {}


# =========================================================
# GENERAL HELPERS
# =========================================================

def is_admin(user_id):
    return user_id == ADMIN_ID


def is_blocked(user_id):
    return (
        user_id in blocked_users
        and user_id != ADMIN_ID
    )


def username(user):
    if user.username:
        return "@" + user.username

    name = user.first_name or "Пользователь"

    return (
        name
        + " (ID "
        + str(user.id)
        + ")"
    )


def money(value):
    value = float(value)

    if value.is_integer():
        return str(int(value))

    return str(
        round(value, 2)
    ).replace(".", ",")


def ton(value):
    return f"{float(value):.4f}"


# =========================================================
# USERS
# =========================================================

def load_users():
    global users

    try:
        with open(
            USERS_FILE,
            "r",
            encoding="utf-8"
        ) as f:
            data = json.load(f)

        users = set(
            int(x)
            for x in data
        )

    except Exception:
        users = set()


def save_users():
    try:
        with open(
            USERS_FILE,
            "w",
            encoding="utf-8"
        ) as f:
            json.dump(
                list(users),
                f,
                ensure_ascii=False,
                indent=4
            )

    except Exception as e:
        print(
            "Ошибка users.json:",
            e
        )


def add_user(user_id):
    if user_id not in users:
        users.add(user_id)
        save_users()


load_users()


# =========================================================
# BLOCKED
# =========================================================

def load_blocked():
    global blocked_users

    try:
        with open(
            BLOCKED_FILE,
            "r",
            encoding="utf-8"
        ) as f:
            data = json.load(f)

        blocked_users = set(
            int(x)
            for x in data
        )

    except Exception:
        blocked_users = set()


def save_blocked():
    try:
        with open(
            BLOCKED_FILE,
            "w",
            encoding="utf-8"
        ) as f:
            json.dump(
                list(blocked_users),
                f,
                ensure_ascii=False,
                indent=4
            )

    except Exception as e:
        print(
            "Ошибка blocked.json:",
            e
        )


load_blocked()


# =========================================================
# PURCHASES
# =========================================================

def load_purchases():
    global purchases

    try:
        with open(
            PURCHASES_FILE,
            "r",
            encoding="utf-8"
        ) as f:
            data = json.load(f)

        if isinstance(data, list):
            purchases = data
        else:
            purchases = []

    except Exception:
        purchases = []


def save_purchases():
    try:
        with open(
            PURCHASES_FILE,
            "w",
            encoding="utf-8"
        ) as f:
            json.dump(
                purchases,
                f,
                ensure_ascii=False,
                indent=4
            )

    except Exception as e:
        print(
            "Ошибка purchases.json:",
            e
        )


load_purchases()


# =========================================================
# PRICES
# =========================================================

def load_prices():

    try:
        with open(
            PRICES_FILE,
            "r",
            encoding="utf-8"
        ) as f:
            data = json.load(f)

    except Exception:
        data = {}

    result = {
        "star_price": float(
            data.get(
                "star_price",
                DEFAULT_PRICES["star_price"]
            )
        ),
        "stars": {},
        "premium": {}
    }

    for amount, default in (
        DEFAULT_PRICES["stars"].items()
    ):
        result["stars"][amount] = float(
            data.get(
                "stars",
                {}
            ).get(
                amount,
                default
            )
        )

    for months, default in (
        DEFAULT_PRICES["premium"].items()
    ):
        result["premium"][months] = float(
            data.get(
                "premium",
                {}
            ).get(
                months,
                default
            )
        )

    return result


prices = load_prices()


def save_prices():
    try:
        with open(
            PRICES_FILE,
            "w",
            encoding="utf-8"
        ) as f:
            json.dump(
                prices,
                f,
                ensure_ascii=False,
                indent=4
            )

    except Exception as e:
        print(
            "Ошибка prices.json:",
            e
        )


# =========================================================
# TON PRICE
# =========================================================

def calculate_ton(
    rub_price,
    discount=True
):
    value = float(rub_price)

    if discount:
        value *= 0.99

    return round(
        value / TON_RUB_RATE,
        4
    )


# =========================================================
# ORDER
# =========================================================

def create_order(user_id, data):

    order = dict(data)

    order["user_id"] = user_id
    order["created_at"] = time.time()
    order["payment_status"] = "created"

    orders[user_id] = order

    return order


def order_text(order):

    product = order.get(
        "product",
        "Товар"
    )

    if product == "Stars":

        amount = order.get(
            "stars",
            order.get("amount", 0)
        )

        text = (
            "⭐ Stars: "
            + str(amount)
        )

    elif product == "Premium":

        months = order.get(
            "months",
            0
        )

        text = (
            "💎 Premium: "
            + str(months)
            + " мес."
        )

    else:
        text = "📦 " + str(product)

    recipient = order.get(
        "recipient"
    )

    if recipient:
        text += (
            "\n👤 Получатель: "
            + str(recipient)
        )

    price_rub = order.get(
        "price_rub",
        order.get("price", 0)
    )

    text += (
        "\n💰 Цена: "
        + money(price_rub)
        + " ₽"
    )

    return text


# =========================================================
# MAIN MENU
# =========================================================

def main_menu(user_id):

    markup = types.InlineKeyboardMarkup(
        row_width=1
    )

    markup.add(
        types.InlineKeyboardButton(
            "⭐ Купить Stars",
            callback_data="stars"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "💎 Купить Telegram Premium",
            callback_data="premium"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "👤 Профиль",
            callback_data="profile"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "⭐ Отзывы",
            url=REVIEWS_URL
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "💬 Поддержка",
            url=(
                "https://t.me/"
                + SUPPORT_USERNAME
            )
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

        bot.send_message(
            message.chat.id,
            "🚫 Вы заблокированы."
        )
        return

    bot.send_message(
        message.chat.id,

        "👋 Привет, "
        + username(message.from_user)
        + "!\n\n"
        "✨ Добро пожаловать в SELL STARS RT!\n\n"
        "⭐ Telegram Stars\n"
        "💎 Telegram Premium\n\n"
        "Выберите нужное действие:",

        reply_markup=main_menu(user_id)
    )


# =========================================================
# HOME
# =========================================================

@bot.callback_query_handler(
    func=lambda c: c.data == "home"
)
def home(call):

    if is_blocked(call.from_user.id):

        bot.answer_callback_query(
            call.id,
            "🚫 Вы заблокированы",
            show_alert=True
        )
        return

    bot.answer_callback_query(call.id)

    try:
        bot.edit_message_text(
            "🏠 Главное меню\n\n"
            "Выберите нужное действие:",

            call.message.chat.id,
            call.message.message_id,

            reply_markup=main_menu(
                call.from_user.id
            )
        )

    except Exception:
        bot.send_message(
            call.message.chat.id,
            "🏠 Главное меню",
            reply_markup=main_menu(
                call.from_user.id
            )
        )


# =========================================================
# PROFILE
# =========================================================

@bot.callback_query_handler(
    func=lambda c: c.data == "profile"
)
def profile(call):

    user_id = call.from_user.id

    if is_blocked(user_id):

        bot.answer_callback_query(
            call.id,
            "🚫 Вы заблокированы",
            show_alert=True
        )
        return

    bot.answer_callback_query(call.id)

    user_purchases = [
        x for x in purchases
        if x.get("user_id") == user_id
    ]

    total_rub = sum(
        float(
            x.get("price_rub", 0)
        )
        for x in user_purchases
    )

    total_stars = sum(
        int(
            x.get("stars", 0)
        )
        for x in user_purchases
        if x.get("product") == "Stars"
    )

    total_premium = sum(
        int(
            x.get("months", 0)
        )
        for x in user_purchases
        if x.get("product") == "Premium"
    )

    text = (
        "👤 ПРОФИЛЬ\n\n"
        "🆔 ID: "
        + str(user_id)
        + "\n"
        "👤 Username: "
        + (
            "@"
            + call.from_user.username
            if call.from_user.username
            else "не указан"
        )
        + "\n\n"
        "⭐ Всего Stars: "
        + str(total_stars)
        + "\n"
        "💎 Premium куплено: "
        + str(total_premium)
        + " мес.\n"
        "💰 Потрачено: "
        + money(total_rub)
        + " ₽\n"
        "📦 Покупок: "
        + str(len(user_purchases))
    )

    markup = types.InlineKeyboardMarkup()

    markup.add(
        types.InlineKeyboardButton(
            "⬅️ Назад",
            callback_data="home"
        )
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

@bot.callback_query_handler(
    func=lambda c: c.data == "stars"
)
def stars(call):

    if is_blocked(call.from_user.id):

        bot.answer_callback_query(
            call.id,
            "🚫 Вы заблокированы",
            show_alert=True
        )
        return

    bot.answer_callback_query(call.id)

    markup = types.InlineKeyboardMarkup(
        row_width=2
    )

    for amount, price_rub in (
        prices["stars"].items()
    ):

        amount_int = int(amount)

        # 50 Stars без скидки
        discount = amount_int != 50

        crypto_price = calculate_ton(
            price_rub,
            discount
        )

        markup.add(
            types.InlineKeyboardButton(
                "⭐ "
                + amount
                + " — 💎 "
                + ton(crypto_price)
                + " TON",
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
        types.InlineKeyboardButton(
            "⬅️ Назад",
            callback_data="home"
        )
    )

    text = (
        "⭐ ВЫБЕРИТЕ КОЛИЧЕСТВО STARS\n\n"
        "💎 Оплата производится в TON\n"
        "💱 Курс: 1 TON = "
        + money(TON_RUB_RATE)
        + " ₽\n"
        "🔥 На все пакеты, кроме 50 Stars, "
        "скидка 1%"
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
    func=lambda c: (
        c.data.startswith("star_")
        and c.data != "stars"
    )
)
def choose_stars(call):

    user_id = call.from_user.id

    if is_blocked(user_id):

        bot.answer_callback_query(
            call.id,
            "🚫 Вы заблокированы",
            show_alert=True
        )
        return

    amount = call.data.split(
        "_",
        1
    )[1]

    if amount not in prices["stars"]:

        bot.answer_callback_query(
            call.id,
            "❌ Такой пакет не найден",
            show_alert=True
        )
        return

    amount_int = int(amount)

    price_rub = float(
        prices["stars"][amount]
    )

    price_ton = calculate_ton(
        price_rub,
        amount_int != 50
    )

    create_order(
        user_id,
        {
            "product": "Stars",
            "stars": amount_int,
            "amount": amount_int,
            "price_rub": price_rub,
            "price_ton": price_ton
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

@bot.callback_query_handler(
    func=lambda c: c.data == "custom_stars"
)
def custom_stars(call):

    if is_blocked(call.from_user.id):

        bot.answer_callback_query(
            call.id,
            "🚫 Вы заблокированы",
            show_alert=True
        )
        return

    bot.answer_callback_query(call.id)

    msg = bot.send_message(
        call.message.chat.id,
        "✏️ Напишите количество Stars.\n\n"
        "Минимум — 50 Stars."
    )

    bot.register_next_step_handler(
        msg,
        custom_stars_amount
    )


def custom_stars_amount(message):

    user_id = message.from_user.id

    if is_blocked(user_id):
        return

    try:
        amount = int(
            message.text.strip()
        )

    except Exception:
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
        amount
        * float(
            prices["star_price"]
        ),
        2
    )

    price_ton = calculate_ton(
        price_rub,
        amount != 50
    )

    create_order(
        user_id,
        {
            "product": "Stars",
            "stars": amount,
            "amount": amount,
            "price_rub": price_rub,
            "price_ton": price_ton
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

@bot.callback_query_handler(
    func=lambda c: c.data == "premium"
)
def premium(call):

    if is_blocked(call.from_user.id):

        bot.answer_callback_query(
            call.id,
            "🚫 Вы заблокированы",
            show_alert=True
        )
        return

    bot.answer_callback_query(call.id)

    markup = types.InlineKeyboardMarkup(
        row_width=1
    )

    for months, price_rub in (
        prices["premium"].items()
    ):

        price_ton = calculate_ton(
            price_rub,
            True
        )

        markup.add(
            types.InlineKeyboardButton(
                "💎 "
                + months
                + " мес. — "
                + ton(price_ton)
                + " TON",
                callback_data=(
                    "premium_"
                    + months
                )
            )
        )

    markup.add(
        types.InlineKeyboardButton(
            "⬅️ Назад",
            callback_data="home"
        )
    )

    text = (
        "💎 TELEGRAM PREMIUM\n\n"
        "💎 Оплата в TON\n"
        "🔥 Скидка 1% на Premium"
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
    func=lambda c: (
        c.data.startswith("premium_")
    )
)
def choose_premium(call):

    user_id = call.from_user.id

    if is_blocked(user_id):

        bot.answer_callback_query(
            call.id,
            "🚫 Вы заблокированы",
            show_alert=True
        )
        return

    months = call.data.split(
        "_",
        1
    )[1]

    if months not in prices["premium"]:

        bot.answer_callback_query(
            call.id,
            "❌ Такой вариант отсутствует",
            show_alert=True
        )
        return

    price_rub = float(
        prices["premium"][months]
    )

    price_ton = calculate_ton(
        price_rub,
        True
    )

    create_order(
        user_id,
        {
            "product": "Premium",
            "months": int(months),
            "price_rub": price_rub,
            "price_ton": price_ton
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

def show_recipient(
    chat_id,
    message_id,
    user_id
):

    order = orders.get(user_id)

    if not order:
        return

    markup = types.InlineKeyboardMarkup(
        row_width=1
    )

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

    back = (
        "stars"
        if order["product"] == "Stars"
        else "premium"
    )

    markup.add(
        types.InlineKeyboardButton(
            "⬅️ Назад",
            callback_data=back
        )
    )

    text = (
        order_text(order)
        + "\n\n"
        "Кому оформить заказ?"
    )

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
# RECIPIENT SELF
# =========================================================

@bot.callback_query_handler(
    func=lambda c: (
        c.data == "recipient_self"
    )
)
def recipient_self(call):

    user_id = call.from_user.id

    order = orders.get(user_id)

    if not order:

        bot.answer_callback_query(
            call.id,
            "❌ Заказ не найден",
            show_alert=True
        )
        return

    order["recipient"] = username(
        call.from_user
    )

    bot.answer_callback_query(call.id)

    show_payment(
        call.message.chat.id,
        call.message.message_id,
        user_id
    )


# =========================================================
# RECIPIENT OTHER
# =========================================================

@bot.callback_query_handler(
    func=lambda c: (
        c.data == "recipient_other"
    )
)
def recipient_other(call):

    bot.answer_callback_query(call.id)

    msg = bot.send_message(
        call.message.chat.id,
        "🎁 Напишите @username получателя.\n\n"
        "Например:\n"
        "@username"
    )

    bot.register_next_step_handler(
        msg,
        recipient_other_text
    )


def recipient_other_text(message):

    if not message.text:

        bot.send_message(
            message.chat.id,
            "❌ Укажите username."
        )
        return

    recipient = message.text.strip()

    if not recipient.startswith("@"):
        recipient = "@" + recipient

    user_id = message.from_user.id

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


# =========================================================
# BACK RECIPIENT
# =========================================================

@bot.callback_query_handler(
    func=lambda c: (
        c.data == "back_recipient"
    )
)
def back_recipient(call):

    bot.answer_callback_query(call.id)

    show_recipient(
        call.message.chat.id,
        call.message.message_id,
        call.from_user.id
        # =========================================================
# PAYMENT MENU
# =========================================================

def payment_menu():

    markup = types.InlineKeyboardMarkup(
        row_width=1
    )

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


def show_payment(
    chat_id,
    message_id,
    user_id
):

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
# PAYMENT DETAILS
# =========================================================

def send_payment_details(
    call,
    method,
    details
):

    user_id = call.from_user.id

    if is_blocked(user_id):

        bot.answer_callback_query(
            call.id,
            "🚫 Вы заблокированы",
            show_alert=True
        )
        return

    order = orders.get(user_id)

    if not order:

        bot.answer_callback_query(
            call.id,
            "❌ Заказ не найден",
            show_alert=True
        )
        return

    order["payment_method"] = method
    order["payment_status"] = (
        "waiting_payment"
    )

    markup = types.InlineKeyboardMarkup()

    markup.add(
        types.InlineKeyboardButton(
            "✅ Я оплатил",
            callback_data="paid"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "⬅️ Назад",
            callback_data="back_payment"
        )
    )

    text = (
        "💳 ОПЛАТА\n\n"
        + order_text(order)
        + "\n\n"
        "🏦 Способ: "
        + method
        + "\n\n"
        "📋 РЕКВИЗИТЫ:\n"
        + details
        + "\n\n"
        "После оплаты нажмите "
        "«✅ Я оплатил».\n\n"
        "⏱ Заказ действует 30 минут."
    )

    bot.answer_callback_query(call.id)

    bot.send_message(
        call.message.chat.id,
        text,
        reply_markup=markup
    )


# =========================================================
# TON
# =========================================================

@bot.callback_query_handler(
    func=lambda c: c.data == "pay_ton"
)
def pay_ton(call):

    user_id = call.from_user.id

    order = orders.get(user_id)

    if not order:

        bot.answer_callback_query(
            call.id,
            "❌ Заказ не найден",
            show_alert=True
        )
        return

    discount = True

    if (
        order.get("product") == "Stars"
        and int(
            order.get("amount", 0)
        ) == 50
    ):
        discount = False

    ton_amount = calculate_ton(
        order.get(
            "price_rub",
            order.get("price", 0)
        ),
        discount
    )

    order["payment_method"] = "TON"
    order["payment_status"] = (
        "waiting_payment"
    )
    order["ton_amount"] = ton_amount

    markup = types.InlineKeyboardMarkup()

    markup.add(
        types.InlineKeyboardButton(
            "✅ Я оплатил",
            callback_data="paid"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "⬅️ Назад",
            callback_data="back_payment"
        )
    )

    text = (
        "💎 ОПЛАТА TON\n\n"
        + order_text(order)
        + "\n\n"
        "💎 К оплате: "
        + ton(ton_amount)
        + " TON\n\n"
        "📋 TON-АДРЕС:\n"
        + TON_ADDRESS
        + "\n\n"
        "⚠️ Отправьте точную сумму.\n"
        "После перевода нажмите "
        "«✅ Я оплатил».\n\n"
        "⏱ Заказ действует 30 минут."
    )

    bot.answer_callback_query(call.id)

    bot.send_message(
        call.message.chat.id,
        text,
        reply_markup=markup
    )


# =========================================================
# SBERBANK
# =========================================================

@bot.callback_query_handler(
    func=lambda c: c.data == "pay_sber"
)
def pay_sber(call):

    send_payment_details(
        call,
        "Сбербанк",
        SBER_DETAILS
    )


# =========================================================
# SBP
# =========================================================

@bot.callback_query_handler(
    func=lambda c: c.data == "pay_sbp"
)
def pay_sbp(call):

    send_payment_details(
        call,
        "СБП",
        SBP_DETAILS
    )


# =========================================================
# YOOMONEY
# =========================================================

@bot.callback_query_handler(
    func=lambda c: c.data == "pay_yoomoney"
)
def pay_yoomoney(call):

    markup = types.InlineKeyboardMarkup()

    markup.add(
        types.InlineKeyboardButton(
            "💰 Открыть ЮMoney",
            url=YOOMONEY_URL
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "✅ Я оплатил",
            callback_data="paid"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "⬅️ Назад",
            callback_data="back_payment"
        )
    )

    user_id = call.from_user.id

    order = orders.get(user_id)

    if not order:

        bot.answer_callback_query(
            call.id,
            "❌ Заказ не найден",
            show_alert=True
        )
        return

    order["payment_method"] = "ЮMoney"
    order["payment_status"] = (
        "waiting_payment"
    )

    text = (
        "💰 ОПЛАТА ЮMONEY\n\n"
        + order_text(order)
        + "\n\n"
        "📋 Ссылка на оплату:\n"
        + YOOMONEY_URL
        + "\n\n"
        "После оплаты нажмите "
        "«✅ Я оплатил».\n\n"
        "⏱ Заказ действует 30 минут."
    )

    bot.answer_callback_query(call.id)

    bot.send_message(
        call.message.chat.id,
        text,
        reply_markup=markup
    )


# =========================================================
# BACK PAYMENT
# =========================================================

@bot.callback_query_handler(
    func=lambda c: c.data == "back_payment"
)
def back_payment(call):

    bot.answer_callback_query(call.id)

    show_payment(
        call.message.chat.id,
        call.message.message_id,
        call.from_user.id
    )


# =========================================================
# USER SAYS PAID
# =========================================================

@bot.callback_query_handler(
    func=lambda c: c.data == "paid"
)
def paid(call):

    user_id = call.from_user.id

    order = orders.get(user_id)

    if not order:

        bot.answer_callback_query(
            call.id,
            "❌ Заказ не найден",
            show_alert=True
        )
        return

    order["payment_status"] = (
        "waiting_admin"
    )

    bot.answer_callback_query(
        call.id,
        "Заявка отправлена админу"
    )

    bot.send_message(
        call.message.chat.id,
        "⏳ Заявка на проверку оплаты "
        "отправлена администратору.\n\n"
        "Ожидайте подтверждения."
    )

    markup = types.InlineKeyboardMarkup(
        row_width=2
    )

    markup.add(
        types.InlineKeyboardButton(
            "✅ Подтвердить",
            callback_data=(
                "approve_"
                + str(user_id)
            )
        ),
        types.InlineKeyboardButton(
            "❌ Отклонить",
            callback_data=(
                "reject_"
                + str(user_id)
            )
        )
    )

    bot.send_message(
        ADMIN_ID,
        "🔔 НОВАЯ ОПЛАТА\n\n"
        "👤 Пользователь: "
        + username(call.from_user)
        + "\n"
        "🆔 ID: "
        + str(user_id)
        + "\n\n"
        + order_text(order)
        + "\n\n"
        "💳 Способ: "
        + str(
            order.get(
                "payment_method",
                "не указан"
            )
        ),
        reply_markup=markup
    )


# =========================================================
# APPROVE PAYMENT
# =========================================================

@bot.callback_query_handler(
    func=lambda c: (
        c.data.startswith("approve_")
    )
)
def approve_payment(call):

    if not is_admin(call.from_user.id):
        return

    user_id = int(
        call.data.split(
            "_",
            1
        )[1]
    )

    order = orders.get(user_id)

    if not order:

        bot.answer_callback_query(
            call.id,
            "Заказ уже отсутствует",
            show_alert=True
        )
        return

    order["payment_status"] = (
        "approved"
    )

    purchase = dict(order)

    purchase["approved_at"] = time.time()

    purchases.append(purchase)

    save_purchases()

    try:
        bot.send_message(
            user_id,
            "✅ ОПЛАТА ПОДТВЕРЖДЕНА!\n\n"
            + order_text(order)
            + "\n\n"
            "📦 Заказ принят в обработку."
        )

    except Exception as e:
        print(
            "Не удалось уведомить пользователя:",
            e
        )

    bot.answer_callback_query(
        call.id,
        "✅ Оплата подтверждена"
    )

    try:
        bot.edit_message_reply_markup(
            call.message.chat.id,
            call.message.message_id,
            reply_markup=None
        )
    except Exception:
        pass

    orders.pop(user_id, None)


# =========================================================
# REJECT PAYMENT
# =========================================================

@bot.callback_query_handler(
    func=lambda c: (
        c.data.startswith("reject_")
    )
)
def reject_payment(call):

    if not is_admin(call.from_user.id):
        return

    user_id = int(
        call.data.split(
            "_",
            1
        )[1]
    )

    order = orders.get(user_id)

    if not order:

        bot.answer_callback_query(
            call.id,
            "Заказ уже отсутствует",
            show_alert=True
        )
        return

    order["payment_status"] = (
        "rejected"
    )

    try:
        bot.send_message(
            user_id,
            "❌ Оплата не подтверждена.\n\n"
            "Обратитесь в поддержку, "
            "если произошла ошибка."
        )

    except Exception:
        pass

    bot.answer_callback_query(
        call.id,
        "❌ Оплата отклонена"
    )

    try:
        bot.edit_message_reply_markup(
            call.message.chat.id,
            call.message.message_id,
            reply_markup=None
        )
    except Exception:
        pass

    orders.pop(user_id, None)


# =========================================================
# PURCHASE HISTORY
# =========================================================

@bot.callback_query_handler(
    func=lambda c: (
        c.data == "purchase_history"
    )
)
def purchase_history(call):

    if not is_admin(call.from_user.id):
        return

    bot.answer_callback_query(call.id)

    if not purchases:

        text = (
            "📊 ИСТОРИЯ ПОКУПОК\n\n"
            "Покупок пока нет."
        )

    else:

        last = purchases[-20:]

        lines = [
            "📊 ИСТОРИЯ ПОКУПОК",
            ""
        ]

        for item in reversed(last):

            lines.append(
                "👤 ID: "
                + str(
                    item.get(
                        "user_id",
                        "?"
                    )
                )
                + " | "
                + str(
                    item.get(
                        "product",
                        "?"
                    )
                )
                + " | "
                + money(
                    item.get(
                        "price_rub",
                        0
                    )
                )
                + " ₽"
            )

        text = "\n".join(lines)

    markup = types.InlineKeyboardMarkup()

    markup.add(
        types.InlineKeyboardButton(
            "⬅️ Назад",
            callback_data="home"
        )
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
            # =========================================================
# BLOCK MENU
# =========================================================

@bot.callback_query_handler(
    func=lambda c: c.data == "block_menu"
)
def block_menu(call):

    if not is_admin(call.from_user.id):
        return

    bot.answer_callback_query(call.id)

    markup = types.InlineKeyboardMarkup(
        row_width=1
    )

    markup.add(
        types.InlineKeyboardButton(
            "🚫 Заблокировать",
            callback_data="block_add"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "✅ Разблокировать",
            callback_data="block_remove"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "📋 Список заблокированных",
            callback_data="block_list"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "⬅️ Назад",
            callback_data="home"
        )
    )

    text = (
        "🚫 УПРАВЛЕНИЕ БЛОКИРОВКАМИ\n\n"
        "Выберите действие:"
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
# BLOCK ADD
# =========================================================

@bot.callback_query_handler(
    func=lambda c: c.data == "block_add"
)
def block_add(call):

    if not is_admin(call.from_user.id):
        return

    bot.answer_callback_query(call.id)

    msg = bot.send_message(
        call.message.chat.id,
        "🚫 Введите Telegram ID пользователя:"
    )

    bot.register_next_step_handler(
        msg,
        block_add_id
    )


def block_add_id(message):

    if not is_admin(message.from_user.id):
        return

    try:
        user_id = int(
            message.text.strip()
        )
    except Exception:
        bot.send_message(
            message.chat.id,
            "❌ ID должен быть числом."
        )
        return

    if user_id == ADMIN_ID:

        bot.send_message(
            message.chat.id,
            "❌ Нельзя заблокировать администратора."
        )
        return

    blocked_users.add(user_id)

    save_blocked()

    bot.send_message(
        message.chat.id,
        "🚫 Пользователь "
        + str(user_id)
        + " заблокирован."
    )


# =========================================================
# BLOCK REMOVE
# =========================================================

@bot.callback_query_handler(
    func=lambda c: c.data == "block_remove"
)
def block_remove(call):

    if not is_admin(call.from_user.id):
        return

    bot.answer_callback_query(call.id)

    msg = bot.send_message(
        call.message.chat.id,
        "✅ Введите Telegram ID пользователя:"
    )

    bot.register_next_step_handler(
        msg,
        block_remove_id
    )


def block_remove_id(message):

    if not is_admin(message.from_user.id):
        return

    try:
        user_id = int(
            message.text.strip()
        )
    except Exception:
        bot.send_message(
            message.chat.id,
            "❌ ID должен быть числом."
        )
        return

    if user_id in blocked_users:

        blocked_users.remove(user_id)

        save_blocked()

        bot.send_message(
            message.chat.id,
            "✅ Пользователь "
            + str(user_id)
            + " разблокирован."
        )

    else:

        bot.send_message(
            message.chat.id,
            "ℹ️ Этот пользователь "
            "не заблокирован."
        )


# =========================================================
# BLOCK LIST
# =========================================================

@bot.callback_query_handler(
    func=lambda c: c.data == "block_list"
)
def block_list(call):

    if not is_admin(call.from_user.id):
        return

    bot.answer_callback_query(call.id)

    if not blocked_users:

        text = (
            "📋 Заблокированных пользователей нет."
        )

    else:

        text = (
            "📋 ЗАБЛОКИРОВАННЫЕ:\n\n"
            + "\n".join(
                str(x)
                for x in sorted(blocked_users)
            )
        )

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
# PRICES MENU
# =========================================================

@bot.callback_query_handler(
    func=lambda c: c.data == "prices"
)
def prices_menu(call):

    if not is_admin(call.from_user.id):
        return

    bot.answer_callback_query(call.id)

    markup = types.InlineKeyboardMarkup(
        row_width=1
    )

    markup.add(
        types.InlineKeyboardButton(
            "⭐ Цена 1 Star",
            callback_data="price_star"
        )
    )

    for amount in prices["stars"]:

        markup.add(
            types.InlineKeyboardButton(
                "⭐ Stars "
                + amount,
                callback_data=(
                    "price_stars_"
                    + amount
                )
            )
        )

    for months in prices["premium"]:

        markup.add(
            types.InlineKeyboardButton(
                "💎 Premium "
                + months
                + " мес.",
                callback_data=(
                    "price_premium_"
                    + months
                )
            )
        )

    markup.add(
        types.InlineKeyboardButton(
            "⬅️ Назад",
            callback_data="home"
        )
    )

    bot.edit_message_text(
        "💰 ИЗМЕНЕНИЕ ЦЕН\n\n"
        "Выберите цену:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )


# =========================================================
# PRICE STAR
# =========================================================

@bot.callback_query_handler(
    func=lambda c: c.data == "price_star"
)
def price_star(call):

    if not is_admin(call.from_user.id):
        return

    bot.answer_callback_query(call.id)

    msg = bot.send_message(
        call.message.chat.id,
        "⭐ Введите новую цену 1 Star в ₽:"
    )

    bot.register_next_step_handler(
        msg,
        set_star_price
    )


def set_star_price(message):

    if not is_admin(message.from_user.id):
        return

    try:
        value = float(
            message.text.replace(",", ".")
        )

        if value <= 0:
            raise ValueError

    except Exception:
        bot.send_message(
            message.chat.id,
            "❌ Неверная цена."
        )
        return

    prices["star_price"] = value

    save_prices()

    bot.send_message(
        message.chat.id,
        "✅ Цена 1 Star изменена на "
        + money(value)
        + " ₽."
    )


# =========================================================
# PRICE STARS PACKAGE
# =========================================================

@bot.callback_query_handler(
    func=lambda c: (
        c.data.startswith("price_stars_")
    )
)
def price_stars_package(call):

    if not is_admin(call.from_user.id):
        return

    amount = call.data.split(
        "_",
        2
    )[2]

    if amount not in prices["stars"]:
        return

    bot.answer_callback_query(call.id)

    msg = bot.send_message(
        call.message.chat.id,
        "⭐ Новая цена для "
        + amount
        + " Stars в ₽:"
    )

    bot.register_next_step_handler(
        msg,
        lambda m: set_package_price(
            m,
            "stars",
            amount
        )
    )


def set_package_price(
    message,
    category,
    key
):

    if not is_admin(message.from_user.id):
        return

    try:
        value = float(
            message.text.replace(",", ".")
        )

        if value <= 0:
            raise ValueError

    except Exception:
        bot.send_message(
            message.chat.id,
            "❌ Неверная цена."
        )
        return

    prices[category][key] = value

    save_prices()

    bot.send_message(
        message.chat.id,
        "✅ Цена изменена."
    )


# =========================================================
# PRICE PREMIUM
# =========================================================

@bot.callback_query_handler(
    func=lambda c: (
        c.data.startswith("price_premium_")
    )
)
def price_premium(call):

    if not is_admin(call.from_user.id):
        return

    months = call.data.split(
        "_",
        2
    )[2]

    if months not in prices["premium"]:
        return

    bot.answer_callback_query(call.id)

    msg = bot.send_message(
        call.message.chat.id,
        "💎 Новая цена Premium "
        + months
        + " мес. в ₽:"
    )

    bot.register_next_step_handler(
        msg,
        lambda m: set_package_price(
            m,
            "premium",
            months
        )
    )


# =========================================================
# BROADCAST
# =========================================================

@bot.callback_query_handler(
    func=lambda c: c.data == "broadcast"
)
def broadcast(call):

    if not is_admin(call.from_user.id):
        return

    bot.answer_callback_query(call.id)

    msg = bot.send_message(
        call.message.chat.id,
        "📢 Отправьте сообщение для рассылки:"
    )

    bot.register_next_step_handler(
        msg,
        do_broadcast
    )


def do_broadcast(message):

    if not is_admin(message.from_user.id):
        return

    sent = 0
    failed = 0

    for user_id in list(users):

        if is_blocked(user_id):
            continue

        try:

            bot.copy_message(
                user_id,
                message.chat.id,
                message.message_id
            )

            sent += 1

            time.sleep(0.05)

        except Exception:

            failed += 1

    bot.send_message(
        message.chat.id,
        "📢 Рассылка завершена.\n\n"
        "✅ Отправлено: "
        + str(sent)
        + "\n"
        "❌ Ошибок: "
        + str(failed)
    )


# =========================================================
# BLOCK CHECK FOR NORMAL MESSAGES
# =========================================================

@bot.message_handler(
    content_types=[
        "text",
        "photo",
        "document",
        "video",
        "audio",
        "voice"
    ]
)
def all_messages(message):

    user_id = message.from_user.id

    add_user(user_id)

    if is_blocked(user_id):

        bot.send_message(
            message.chat.id,
            "🚫 Вы заблокированы."
        )
        return


# =========================================================
# START BOT
# =========================================================

print(
    "SELL STARS RT запущен"
)

while True:

    try:

        bot.infinity_polling(
            skip_pending=True,
            timeout=30,
            long_polling_timeout=30
        )

    except Exception as e:

        print(
            "Ошибка бота:",
            e
        )

        time.sleep(5)
    )
    )
