import os
import json
import time
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import telebot
from telebot import types


# =========================================================
# RENDER WEB SERVER
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
        os.environ.get(
            "PORT",
            "10000"
        )
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

REVIEWS_URL = "https://t.me/RTstoreREVIEW"

# TON
TON_ADDRESS = (
    "UQAm8vafnYdyPH1u-IA8xD3Sqh3rO-K76LhPh8NUu4oY6J7S"
)

# Курс TON
TON_RUB_RATE = 125.0

# ЮMoney
YOOMONEY_URL = (
    "https://yoomoney.ru/to/4100119601496891"
)

# По твоей просьбе кнопки СБП и Сбер
# также открывают эту ссылку.
SBER_PAYMENT = YOOMONEY_URL
SBP_PAYMENT = YOOMONEY_URL

PRICES_FILE = "prices.json"
USERS_FILE = "users.json"
BLOCKED_FILE = "blocked.json"
PURCHASES_FILE = "purchases.json"


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

price_waiting = {}

broadcast_waiting = set()

block_waiting = set()

unblock_waiting = set()


# =========================================================
# FILE HELPERS
# =========================================================

def load_json(
    filename,
    default
):

    try:

        with open(
            filename,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except Exception:

        return default


def save_json(
    filename,
    data
):

    try:

        with open(
            filename,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                data,
                file,
                ensure_ascii=False,
                indent=4
            )

        return True

    except Exception as error:

        print(
            "Ошибка сохранения",
            filename,
            error
        )

        return False


# =========================================================
# USERS
# =========================================================

def load_users():

    global users

    data = load_json(
        USERS_FILE,
        []
    )

    try:

        users = set(
            int(x)
            for x in data
        )

    except Exception:

        users = set()


def save_users():

    save_json(
        USERS_FILE,
        list(users)
    )


def add_user(user_id):

    if user_id not in users:

        users.add(user_id)

        save_users()


load_users()


# =========================================================
# BLOCKED USERS
# =========================================================

def load_blocked():

    global blocked_users

    data = load_json(
        BLOCKED_FILE,
        []
    )

    try:

        blocked_users = set(
            int(x)
            for x in data
        )

    except Exception:

        blocked_users = set()


def save_blocked():

    save_json(
        BLOCKED_FILE,
        list(blocked_users)
    )


load_blocked()


# =========================================================
# PURCHASES
# =========================================================

def load_purchases():

    global purchases

    data = load_json(
        PURCHASES_FILE,
        []
    )

    if isinstance(data, list):

        purchases = data

    else:

        purchases = []


def save_purchases():

    save_json(
        PURCHASES_FILE,
        purchases
    )


load_purchases()


# =========================================================
# PRICES
# =========================================================

def load_prices():

    data = load_json(
        PRICES_FILE,
        DEFAULT_PRICES
    )

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

    for amount, default in DEFAULT_PRICES["stars"].items():

        result["stars"][amount] = float(
            data.get(
                "stars",
                {}
            ).get(
                amount,
                default
            )
        )

    for months, default in DEFAULT_PRICES["premium"].items():

        result["premium"][months] = float(
            data.get(
                "premium",
                {}
            ).get(
                months,
                default
            )
        )

    save_json(
        PRICES_FILE,
        result
    )

    return result


def save_prices():

    save_json(
        PRICES_FILE,
        prices
    )


prices = load_prices()


# =========================================================
# BASIC HELPERS
# =========================================================

def is_admin(user_id):

    return user_id == ADMIN_ID


def is_blocked(user_id):

    if user_id == ADMIN_ID:
        return False

    return user_id in blocked_users


def user_name(user):

    if user.username:

        return "@" + user.username

    if user.first_name:

        return user.first_name

    return "ID " + str(user.id)


def money(value):

    value = float(value)

    if value.is_integer():

        return str(
            int(value)
        )

    return str(
        round(value, 2)
    ).replace(
        ".",
        ","
    )


def ton(value):

    return f"{float(value):.4f}".rstrip("0").rstrip(".")


def stars_ton_price(
    rub_price,
    amount
):

    rub_price = float(rub_price)

    if int(amount) != 50:

        rub_price *= 0.99

    return round(
        rub_price / TON_RUB_RATE,
        4
    )


def premium_ton_price(
    rub_price
):

    rub_price = float(rub_price)

    rub_price *= 0.99

    return round(
        rub_price / TON_RUB_RATE,
        4
    )


# =========================================================
# ORDER HELPERS
# =========================================================

def create_order(
    user_id,
    data
):

    order = dict(data)

    order["user_id"] = user_id

    order["created_at"] = int(
        time.time()
    )

    order["payment_method"] = None

    order["payment_status"] = (
        "waiting_method"
    )

    order["status"] = "new"

    orders[user_id] = order

    return order


def order_text(order):

    if order.get("product") == "Stars":

        amount = int(
            order.get(
                "stars",
                order.get(
                    "amount",
                    0
                )
            )
        )

        rub = float(
            order.get(
                "price_rub",
                0
            )
        )

        return (
            "⭐ Stars: "
            + str(amount)
            + "\n"
            "💰 Цена: "
            + money(rub)
            + " ₽"
        )

    if order.get("product") == "Premium":

        months = int(
            order.get(
                "months",
                0
            )
        )

        rub = float(
            order.get(
                "price_rub",
                order.get(
                    "price",
                    0
                )
            )
        )

        return (
            "💎 Premium: "
            + str(months)
            + " мес.\n"
            "💰 Цена: "
            + money(rub)
            + " ₽"
        )

    return "❌ Неизвестный товар"


def save_purchase(
    order
):

    purchase = dict(order)

    purchase["completed_at"] = int(
        time.time()
    )

    purchases.append(
        purchase
    )

    save_purchases()


# =========================================================
# BLOCK CHECK
# =========================================================

def check_blocked(
    user_id,
    call_id=None
):

    if not is_blocked(user_id):
        return False

    if call_id:

        try:

            bot.answer_callback_query(
                call_id,
                "🚫 Вы заблокированы",
                show_alert=True
            )

        except Exception:
            pass

    return True
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
            url="https://t.me/"
            + SUPPORT_USERNAME
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

@bot.message_handler(
    commands=["start"]
)
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
        + user_name(message.from_user)
        + "!\n\n"
        "✨ Добро пожаловать в SELL STARS RT!\n\n"
        "⭐ Telegram Stars\n"
        "💎 Telegram Premium\n\n"
        "Выберите нужное действие:",

        reply_markup=main_menu(
            user_id
        )
    )


# =========================================================
# HOME
# =========================================================

@bot.callback_query_handler(
    func=lambda call:
        call.data == "home"
)
def home(call):

    if check_blocked(
        call.from_user.id,
        call.id
    ):

        return

    bot.answer_callback_query(
        call.id
    )

    text = (
        "🏠 ГЛАВНОЕ МЕНЮ\n\n"
        "Выберите нужное действие:"
    )

    try:

        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=main_menu(
                call.from_user.id
            )
        )

    except Exception:

        bot.send_message(
            call.message.chat.id,
            text,
            reply_markup=main_menu(
                call.from_user.id
            )
        )


# =========================================================
# PROFILE
# =========================================================

@bot.callback_query_handler(
    func=lambda call:
        call.data == "profile"
)
def profile(call):

    if check_blocked(
        call.from_user.id,
        call.id
    ):

        return

    bot.answer_callback_query(
        call.id
    )

    user_id = call.from_user.id

    user_purchases = [
        item
        for item in purchases
        if int(
            item.get(
                "user_id",
                0
            )
        ) == user_id
    ]

    total_rub = 0

    total_stars = 0

    total_premium = 0

    for item in user_purchases:

        total_rub += float(
            item.get(
                "price_rub",
                item.get(
                    "price",
                    0
                )
            )
        )

        if item.get(
            "product"
        ) == "Stars":

            total_stars += int(
                item.get(
                    "stars",
                    0
                )
            )

        elif item.get(
            "product"
        ) == "Premium":

            total_premium += int(
                item.get(
                    "months",
                    0
                )
            )

    username = (
        "@"
        + call.from_user.username
        if call.from_user.username
        else "не указан"
    )

    text = (
        "👤 ПРОФИЛЬ\n\n"

        "🆔 ID: "
        + str(user_id)
        + "\n"

        "👤 Username: "
        + username
        + "\n\n"

        "⭐ Куплено Stars: "
        + str(total_stars)
        + "\n"

        "💎 Куплено Premium: "
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
# STARS MENU
# =========================================================

@bot.callback_query_handler(
    func=lambda call:
        call.data == "stars"
)
def stars(call):

    if check_blocked(
        call.from_user.id,
        call.id
    ):

        return

    bot.answer_callback_query(
        call.id
    )

    markup = types.InlineKeyboardMarkup(
        row_width=2
    )

    for amount, price_rub in prices[
        "stars"
    ].items():

        amount_int = int(
            amount
        )

        ton_amount = stars_ton_price(
            price_rub,
            amount_int
        )

        markup.add(
            types.InlineKeyboardButton(
                "⭐ "
                + amount
                + " — "
                + ton(ton_amount)
                + " TON",
                callback_data=(
                    "star_"
                    + amount
                )
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
        "⭐ ВЫБЕРИТЕ STARS\n\n"
        "💎 Оплата в TON\n"
        "💱 Курс: 1 TON = "
        + money(TON_RUB_RATE)
        + " ₽\n\n"
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
    func=lambda call:
        call.data.startswith("star_")
)
def choose_stars(call):

    if check_blocked(
        call.from_user.id,
        call.id
    ):

        return

    amount = call.data.split(
        "_",
        1
    )[1]

    if amount not in prices["stars"]:

        bot.answer_callback_query(
            call.id,
            "❌ Пакет не найден",
            show_alert=True
        )

        return

    amount_int = int(
        amount
    )

    price_rub = float(
        prices["stars"][amount]
    )

    create_order(
        call.from_user.id,
        {
            "product": "Stars",
            "stars": amount_int,
            "amount": amount_int,
            "price_rub": price_rub
        }
    )

    bot.answer_callback_query(
        call.id
    )

    show_recipient(
        call.message.chat.id,
        call.message.message_id,
        call.from_user.id
    )


# =========================================================
# CUSTOM STARS
# =========================================================

@bot.callback_query_handler(
    func=lambda call:
        call.data == "custom_stars"
)
def custom_stars(call):

    if check_blocked(
        call.from_user.id,
        call.id
    ):

        return

    bot.answer_callback_query(
        call.id
    )

    msg = bot.send_message(
        call.message.chat.id,

        "✏️ Введите количество Stars.\n\n"
        "Минимум: 50 Stars."
    )

    bot.register_next_step_handler(
        msg,
        custom_stars_amount
    )


def custom_stars_amount(message):

    user_id = message.from_user.id

    if is_blocked(user_id):

        return

    if not message.text:

        bot.send_message(
            message.chat.id,
            "❌ Введите число."
        )

        return

    try:

        amount = int(
            message.text.strip()
        )

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
        amount
        * float(
            prices["star_price"]
        ),
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

@bot.callback_query_handler(
    func=lambda call:
        call.data == "premium"
)
def premium(call):

    if check_blocked(
        call.from_user.id,
        call.id
    ):

        return

    bot.answer_callback_query(
        call.id
    )

    markup = types.InlineKeyboardMarkup(
        row_width=1
    )

    for months, price_rub in prices[
        "premium"
    ].items():

        ton_amount = premium_ton_price(
            price_rub
        )

        markup.add(
            types.InlineKeyboardButton(
                "💎 "
                + months
                + " мес. — "
                + ton(ton_amount)
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
    func=lambda call:
        call.data.startswith("premium_")
)
def choose_premium(call):

    if check_blocked(
        call.from_user.id,
        call.id
    ):

        return

    months = call.data.split(
        "_",
        1
    )[1]

    if months not in prices["premium"]:

        bot.answer_callback_query(
            call.id,
            "❌ Вариант не найден",
            show_alert=True
        )

        return

    price_rub = float(
        prices["premium"][months]
    )

    create_order(
        call.from_user.id,
        {
            "product": "Premium",
            "months": int(months),
            "price_rub": price_rub
        }
    )

    bot.answer_callback_query(
        call.id
    )

    show_recipient(
        call.message.chat.id,
        call.message.message_id,
        call.from_user.id
        
    )
    # =========================================================
# RECIPIENT
# =========================================================

def show_recipient(
    chat_id,
    message_id,
    user_id
):

    order = orders.get(
        user_id
    )

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

    if order.get(
        "product"
    ) == "Stars":

        back = "stars"

    else:

        back = "premium"

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
    func=lambda call:
        call.data == "recipient_self"
)
def recipient_self(call):

    if check_blocked(
        call.from_user.id,
        call.id
    ):

        return

    order = orders.get(
        call.from_user.id
    )

    if not order:

        bot.answer_callback_query(
            call.id,
            "❌ Заказ не найден",
            show_alert=True
        )

        return

    order["recipient"] = user_name(
        call.from_user
    )

    bot.answer_callback_query(
        call.id
    )

    show_payment(
        call.message.chat.id,
        call.message.message_id,
        call.from_user.id
    )


# =========================================================
# RECIPIENT OTHER
# =========================================================

@bot.callback_query_handler(
    func=lambda call:
        call.data == "recipient_other"
)
def recipient_other(call):

    if check_blocked(
        call.from_user.id,
        call.id
    ):

        return

    bot.answer_callback_query(
        call.id
    )

    msg = bot.send_message(
        call.message.chat.id,

        "🎁 Введите @username получателя.\n\n"
        "Например:\n"
        "@username"
    )

    bot.register_next_step_handler(
        msg,
        recipient_other_text
    )


def recipient_other_text(message):

    user_id = message.from_user.id

    if is_blocked(user_id):

        return

    if not message.text:

        bot.send_message(
            message.chat.id,
            "❌ Введите username."
        )

        return

    recipient = message.text.strip()

    if not recipient.startswith("@"):

        recipient = "@" + recipient

    order = orders.get(
        user_id
    )

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
    func=lambda call:
        call.data == "back_recipient"
)
def back_recipient(call):

    if check_blocked(
        call.from_user.id,
        call.id
    ):

        return

    bot.answer_callback_query(
        call.id
    )

    show_recipient(
        call.message.chat.id,
        call.message.message_id,
        call.from_user.id
    )


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

    order = orders.get(
        user_id
    )

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

@bot.callback_query_handler(
    func=lambda call:
        call.data == "pay_ton"
)
def pay_ton(call):

    if check_blocked(
        call.from_user.id,
        call.id
    ):

        return

    user_id = call.from_user.id

    order = orders.get(
        user_id
    )

    if not order:

        bot.answer_callback_query(
            call.id,
            "❌ Заказ не найден",
            show_alert=True
        )

        return

    if order.get(
        "product"
    ) == "Stars":

        amount = int(
            order.get(
                "stars",
                0
            )
        )

        ton_amount = stars_ton_price(
            order["price_rub"],
            amount
        )

    else:

        ton_amount = premium_ton_price(
            order["price_rub"]
        )

    order["payment_method"] = "TON"

    order["payment_status"] = (
        "waiting_payment"
    )

    order["ton_amount"] = ton_amount

    text = (
        "💎 ОПЛАТА TON\n\n"
        + order_text(order)
        + "\n\n"
        "💎 К оплате: "
        + ton(ton_amount)
        + " TON\n\n"
        "📋 TON-адрес:\n"
        + TON_ADDRESS
        + "\n\n"
        "⚠️ После перевода отправьте админу "
        "подтверждение оплаты.\n\n"
        "⏱ Заказ действует 30 минут."
    )

    markup = types.InlineKeyboardMarkup()

    markup.add(
        types.InlineKeyboardButton(
            "⬅️ Назад",
            callback_data="back_recipient"
        )
    )

    bot.answer_callback_query(
        call.id
    )

    bot.send_message(
        call.message.chat.id,
        text,
        reply_markup=markup
    )


# =========================================================
# BANK / YOOMONEY PAYMENT
# =========================================================

def send_payment_link(
    call,
    title,
    payment_url
):

    if check_blocked(
        call.from_user.id,
        call.id
    ):

        return

    order = orders.get(
        call.from_user.id
    )

    if not order:

        bot.answer_callback_query(
            call.id,
            "❌ Заказ не найден",
            show_alert=True
        )

        return

    order["payment_method"] = title

    order["payment_status"] = (
        "waiting_payment"
    )

    markup = types.InlineKeyboardMarkup()

    markup.add(
        types.InlineKeyboardButton(
            "💳 ОПЛАТИТЬ",
            url=payment_url
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "⬅️ Назад",
            callback_data="back_recipient"
        )
    )

    text = (
        "💳 ОПЛАТА\n\n"
        + order_text(order)
        + "\n\n"
        "🏦 Способ: "
        + title
        + "\n\n"
        "Нажмите кнопку ниже для оплаты.\n\n"
        "После оплаты отправьте подтверждение "
        "администратору."
    )

    bot.answer_callback_query(
        call.id
    )

    bot.send_message(
        call.message.chat.id,
        text,
        reply_markup=markup
    )


# =========================================================
# SBERBANK
# =========================================================

@bot.callback_query_handler(
    func=lambda call:
        call.data == "pay_sber"
)
def pay_sber(call):

    send_payment_link(
        call,
        "Сбербанк",
        SBER_PAYMENT
    )


# =========================================================
# SBP
# =========================================================

@bot.callback_query_handler(
    func=lambda call:
        call.data == "pay_sbp"
)
def pay_sbp(call):

    send_payment_link(
        call,
        "СБП",
        SBP_PAYMENT
    )


# =========================================================
# YOOMONEY
# =========================================================

@bot.callback_query_handler(
    func=lambda call:
        call.data == "pay_yoomoney"
)
def pay_yoomoney(call):

    send_payment_link(
        call,
        "ЮMoney",
        YOOMONEY_URL
    )


# =========================================================
# ADMIN PURCHASE HISTORY
# =========================================================

@bot.callback_query_handler(
    func=lambda call:
        call.data == "purchase_history"
)
def purchase_history(call):

    if not is_admin(
        call.from_user.id
    ):

        bot.answer_callback_query(
            call.id,
            "❌ Нет доступа",
            show_alert=True
        )

        return

    bot.answer_callback_query(
        call.id
    )

    if not purchases:

        text = (
            "📊 ИСТОРИЯ ПОКУПОК\n\n"
            "Покупок пока нет."
        )

    else:

        recent = purchases[-20:]

        lines = [
            "📊 ИСТОРИЯ ПОКУПОК",
            ""
        ]

        for item in reversed(
            recent
        ):

            product = item.get(
                "product",
                "?"
            )

            user_id = item.get(
                "user_id",
                "?"
            )

            price = item.get(
                "price_rub",
                item.get(
                    "price",
                    0
                )
            )

            lines.append(
                "• "
                + str(product)
                + " | ID "
                + str(user_id)
                + " | "
                + money(price)
                + " ₽"
            )

        text = "\n".join(
            lines
        )

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
# ADMIN BLOCK MENU
# =========================================================

@bot.callback_query_handler(
    func=lambda call:
        call.data == "block_menu"
)
def block_menu(call):

    if not is_admin(
        call.from_user.id
    ):

        bot.answer_callback_query(
            call.id,
            "❌ Нет доступа",
            show_alert=True
        )

        return

    bot.answer_callback_query(
        call.id
    )

    markup = types.InlineKeyboardMarkup(
        row_width=1
    )

    markup.add(
        types.InlineKeyboardButton(
            "🚫 Заблокировать",
            callback_data="block_user"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "✅ Разблокировать",
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

    bot.send_message(
        call.message.chat.id,

        "🚫 УПРАВЛЕНИЕ БЛОКИРОВКАМИ\n\n"
        "Выберите действие:",

        reply_markup=markup
    )


# =========================================================
# BLOCK USER
# =========================================================

@bot.callback_query_handler(
    func=lambda call:
        call.data == "block_user"
)
def block_user(call):

    if not is_admin(
        call.from_user.id
    ):

        return

    bot.answer_callback_query(
        call.id
    )

    block_waiting.add(
        call.from_user.id
    )

    msg = bot.send_message(
        call.message.chat.id,

        "🚫 Введите Telegram ID пользователя,\n"
        "которого нужно заблокировать."
    )

    bot.register_next_step_handler(
        msg,
        block_user_id
    )


def block_user_id(message):

    admin_id = message.from_user.id

    if not is_admin(admin_id):

        return

    block_waiting.discard(
        admin_id
    )

    try:

        user_id = int(
            message.text.strip()
        )

    except Exception:

        bot.send_message(
            message.chat.id,
            "❌ ID должен состоять из цифр."
        )

        return

    if user_id == ADMIN_ID:

        bot.send_message(
            message.chat.id,
            "❌ Нельзя заблокировать администратора."
        )

        return

    blocked_users.add(
        user_id
    )

    save_blocked()

    bot.send_message(
        message.chat.id,

        "🚫 Пользователь "
        + str(user_id)
        + " заблокирован."
    )


# =========================================================
# UNBLOCK USER
# =========================================================

@bot.callback_query_handler(
    func=lambda call:
        call.data == "unblock_user"
)
def unblock_user(call):

    if not is_admin(
        call.from_user.id
    ):

        return

    bot.answer_callback_query(
        call.id
    )

    msg = bot.send_message(
        call.message.chat.id,

        "✅ Введите Telegram ID пользователя,\n"
        "которого нужно разблокировать."
    )

    bot.register_next_step_handler(
        msg,
        unblock_user_id
    )


def unblock_user_id(message):

    if not is_admin(
        message.from_user.id
    ):

        return

    try:

        user_id = int(
            message.text.strip()
        )

    except Exception:

        bot.send_message(
            message.chat.id,
            "❌ ID должен состоять из цифр."
        )

        return

    if user_id in blocked_users:

        blocked_users.remove(
            user_id
        )

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
            "ℹ️ Этот пользователь не заблокирован."
        )


# =========================================================
# BLOCKED LIST
# =========================================================

@bot.callback_query_handler(
    func=lambda call:
        call.data == "blocked_list"
)
def blocked_list(call):

    if not is_admin(
        call.from_user.id
    ):

        return

    bot.answer_callback_query(
        call.id
    )

    if not blocked_users:

        text = (
            "📋 Заблокированных пользователей нет."
        )

    else:

        text = (
            "📋 ЗАБЛОКИРОВАННЫЕ:\n\n"
            + "\n".join(
                "🚫 " + str(user_id)
                for user_id in sorted(
                    blocked_users
                )
            )
        )

    bot.send_message(
        call.message.chat.id,
        text
    )


# =========================================================
# ADMIN PRICES
# =========================================================

@bot.callback_query_handler(
    func=lambda call:
        call.data == "prices"
)
def prices_menu(call):

    if not is_admin(
        call.from_user.id
    ):

        return

    bot.answer_callback_query(
        call.id
    )

    text = (
        "💰 ИЗМЕНЕНИЕ ЦЕН\n\n"

        "⭐ Текущая цена Stars: "
        + money(
            prices["star_price"]
        )
        + " ₽/шт\n\n"

        "⭐ 50: "
        + money(prices["stars"]["50"])
        + " ₽\n"

        "⭐ 100: "
        + money(prices["stars"]["100"])
        + " ₽\n"

        "⭐ 150: "
        + money(prices["stars"]["150"])
        + " ₽\n"

        "⭐ 250: "
        + money(prices["stars"]["250"])
        + " ₽\n"

        "⭐ 500: "
        + money(prices["stars"]["500"])
        + " ₽\n"

        "⭐ 1000: "
        + money(prices["stars"]["1000"])
        + " ₽\n\n"

        "💎 Premium 3: "
        + money(prices["premium"]["3"])
        + " ₽\n"

        "💎 Premium 6: "
        + money(prices["premium"]["6"])
        + " ₽\n"

        "💎 Premium 12: "
        + money(prices["premium"]["12"])
        + " ₽"
    )

    markup = types.InlineKeyboardMarkup(
        row_width=1
    )

    markup.add(
        types.InlineKeyboardButton(
            "⭐ Цена Stars за 1 шт.",
            callback_data="price_star"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "⭐ Пакеты Stars",
            callback_data="price_stars"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "💎 Premium",
            callback_data="price_premium"
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
        text,
        reply_markup=markup
    )


# =========================================================
# CHANGE STAR PRICE
# =========================================================

@bot.callback_query_handler(
    func=lambda call:
        call.data == "price_star"
)
def price_star(call):

    if not is_admin(
        call.from_user.id
    ):

        return

    bot.answer_callback_query(
        call.id
    )

    msg = bot.send_message(
        call.message.chat.id,
        "⭐ Введите новую цену Stars за 1 шт. в ₽:"
    )

    bot.register_next_step_handler(
        msg,
        save_star_price
    )


def save_star_price(message):

    if not is_admin(
        message.from_user.id
    ):

        return

    try:

        value = float(
            message.text.replace(
                ",",
                "."
            ).strip()
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

        "✅ Цена Stars изменена на "
        + money(value)
        + " ₽."
    )


# =========================================================
# CHANGE STAR PACK
# =========================================================

@bot.callback_query_handler(
    func=lambda call:
        call.data == "price_stars"
)
def price_stars(call):

    if not is_admin(
        call.from_user.id
    ):

        return

    bot.answer_callback_query(
        call.id
    )

    msg = bot.send_message(
        call.message.chat.id,

        "⭐ Введите пакет и цену через пробел.\n\n"
        "Например:\n"
        "100 150"
    )

    bot.register_next_step_handler(
        msg,
        save_star_pack
    )


def save_star_pack(message):

    if not is_admin(
        message.from_user.id
    ):

        return

    parts = message.text.split()

    if len(parts) != 2:

        bot.send_message(
            message.chat.id,
            "❌ Формат: 100 150"
        )

        return

    amount = parts[0]

    try:

        price = float(
            parts[1].replace(
                ",",
                "."
            )
        )

        if (
            int(amount) <= 0
            or price <= 0
        ):

            raise ValueError

    except Exception:

        bot.send_message(
            message.chat.id,
            "❌ Неверные данные."
        )

        return

    if amount not in prices["stars"]:

        bot.send_message(
            message.chat.id,
            "❌ Такого пакета нет."
        )

        return

    prices["stars"][amount] = price

    save_prices()

    bot.send_message(
        message.chat.id,

        "✅ Цена "
        + amount
        + " Stars изменена на "
        + money(price)
        + " ₽."
    )


# =========================================================
# CHANGE PREMIUM
# =========================================================

@bot.callback_query_handler(
    func=lambda call:
        call.data == "price_premium"
)
def price_premium(call):

    if not is_admin(
        call.from_user.id
    ):

        return

    bot.answer_callback_query(
        call.id
    )

    msg = bot.send_message(
        call.message.chat.id,

        "💎 Введите срок и цену через пробел.\n\n"
        "Например:\n"
        "3 1100"
    )

    bot.register_next_step_handler(
        msg,
        save_premium_price
    )


def save_premium_price(message):

    if not is_admin(
        message.from_user.id
    ):

        return

    parts = message.text.split()

    if len(parts) != 2:

        bot.send_message(
            message.chat.id,
            "❌ Формат: 3 1100"
        )

        return

    months = parts[0]

    try:

        price = float(
            parts[1].replace(
                ",",
                "."
            )
        )

        if (
            int(months) <= 0
            or price <= 0
        ):

            raise ValueError

    except Exception:

        bot.send_message(
            message.chat.id,
            "❌ Неверные данные."
        )

        return

    if months not in prices["premium"]:

        bot.send_message(
            message.chat.id,
            "❌ Такого срока нет."
        )

        return

    prices["premium"][months] = price

    save_prices()

    bot.send_message(
        message.chat.id,

        "✅ Premium "
        + months
        + " мес. теперь стоит "
        + money(price)
        + " ₽."
    )


# =========================================================
# BROADCAST
# =========================================================

@bot.callback_query_handler(
    func=lambda call:
        call.data == "broadcast"
)
def broadcast(call):

    if not is_admin(
        call.from_user.id
    ):

        return

    bot.answer_callback_query(
        call.id
    )

    msg = bot.send_message(
        call.message.chat.id,

        "📢 Отправьте сообщение для рассылки.\n\n"
        "Текст, фото или другое сообщение."
    )

    bot.register_next_step_handler(
        msg,
        broadcast_message
    )


def broadcast_message(message):

    if not is_admin(
        message.from_user.id
    ):

        return

    success = 0

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

            success += 1

            time.sleep(0.05)

        except Exception:

            failed += 1

    bot.send_message(
        message.chat.id,

        "📢 Рассылка завершена.\n\n"
        "✅ Отправлено: "
        + str(success)
        + "\n"
        "❌ Ошибок: "
        + str(failed)
    )


# =========================================================
# ADMIN COMMANDS
# =========================================================

@bot.message_handler(
    commands=["admin"]
)
def admin_command(message):

    if not is_admin(
        message.from_user.id
    ):

        return

    bot.send_message(
        message.chat.id,

        "🔧 АДМИН-ПАНЕЛЬ",

        reply_markup=main_menu(
            message.from_user.id
        )
    )


@bot.message_handler(
    commands=["block"]
)
def block_command(message):

    if not is_admin(
        message.from_user.id
    ):

        return

    parts = message.text.split()

    if len(parts) != 2:

        bot.send_message(
            message.chat.id,
            "Использование: /block ID"
        )

        return

    try:

        user_id = int(
            parts[1]
        )

    except Exception:

        bot.send_message(
            message.chat.id,
            "❌ Неверный ID."
        )

        return

    if user_id == ADMIN_ID:

        bot.send_message(
            message.chat.id,
            "❌ Нельзя заблокировать администратора."
        )

        return

    blocked_users.add(
        user_id
    )

    save_blocked()

    bot.send_message(
        message.chat.id,

        "🚫 Пользователь "
        + str(user_id)
        + " заблокирован."
    )


@bot.message_handler(
    commands=["unblock"]
)
def unblock_command(message):

    if not is_admin(
        message.from_user.id
    ):

        return

    parts = message.text.split()

    if len(parts) != 2:

        bot.send_message(
            message.chat.id,
            "Использование: /unblock ID"
        )

        return

    try:

        user_id = int(
            parts[1]
        )

    except Exception:

        bot.send_message(
            message.chat.id,
            "❌ Неверный ID."
        )

        return

    blocked_users.discard(
        user_id
    )

    save_blocked()

    bot.send_message(
        message.chat.id,

        "✅ Пользователь "
        + str(user_id)
        + " разблокирован."
    )


# =========================================================
# FALLBACK
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
def other_messages(message):

    if is_blocked(
        message.from_user.id
    ):

        return

    if message.text and message.text.startswith("/"):
        return

    bot.send_message(
        message.chat.id,

        "🏠 Используйте меню ниже:",

        reply_markup=main_menu(
            message.from_user.id
        )
    )


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

    except Exception as error:

        print(
            "Ошибка бота:",
            error
        )

        time.sleep(5)
