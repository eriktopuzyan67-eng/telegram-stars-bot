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
    port = int(os.environ.get("PORT", "10000"))

    server = HTTPServer(
        ("0.0.0.0", port),
        Handler
    )

    print("Web server started on port", port)
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

TON_ADDRESS = (
    "UQAm8vafnYdyPH1u-IA8xD3Sqh3rO-K76LhPh8NUu4oY6J7S"
)

# Курс для расчёта цен TON
TON_RUB_RATE = 125.0

PRICES_FILE = "prices.json"
USERS_FILE = "users.json"
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

waiting_review = set()

price_waiting = {}

review_ratings = {}


# =========================================================
# PURCHASES
# =========================================================

purchases = []


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
                ensure_ascii=False
            )

    except Exception as e:

        print(
            "Ошибка users.json:",
            e
        )


load_users()


# =========================================================
# BLOCKED USERS
# =========================================================

def load_blocked():

    global blocked_users

    try:

        with open(
            "blocked.json",
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
            "blocked.json",
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
# HELPERS
# =========================================================

def is_admin(user_id):

    return user_id == ADMIN_ID


def is_blocked(user_id):

    return (
        user_id in blocked_users
        and user_id != ADMIN_ID
    )


def add_user(user_id):

    if user_id not in users:

        users.add(user_id)
        save_users()


def username(user):

    if user.username:
        return "@" + user.username

    name = user.first_name or "Пользователь"

    return name + " (ID " + str(user.id) + ")"


def money(value):

    value = float(value)

    if value.is_integer():
        return str(int(value))

    return str(
        round(value, 2)
    ).replace(".", ",")


def ton(value):

    value = float(value)

    return f"{value:.2f}"


def ton_price_from_rub(
    rub_price,
    stars_amount=None
):

    # 50 Stars специально фиксированы
    if stars_amount == 50:
        return 0.60

    price = (
        float(rub_price)
        / TON_RUB_RATE
    )

    # скидка 1%
    price *= 0.99

    return round(
        price,
        2
    )


def premium_ton_price(
    rub_price
):

    price = (
        float(rub_price)
        / TON_RUB_RATE
    )

    # скидка 1%
    price *= 0.99

    return round(
        price,
        2
    )


# =========================================================
# PRICES
# =========================================================

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
            "Ошибка сохранения цен:",
            e
        )


def load_prices():

    try:

        with open(
            PRICES_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

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

        return result

    except Exception:

        data = {

            "star_price":
                DEFAULT_PRICES["star_price"],

            "stars":
                DEFAULT_PRICES["stars"].copy(),

            "premium":
                DEFAULT_PRICES["premium"].copy()
        }

        try:

            with open(
                PRICES_FILE,
                "w",
                encoding="utf-8"
            ) as f:

                json.dump(
                    data,
                    f,
                    ensure_ascii=False,
                    indent=4
                )

        except Exception as e:

            print(
                "Ошибка создания prices.json:",
                e
            )

        return data


prices = load_prices()


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
        float(x.get("price_rub", 0))
        for x in user_purchases
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

        "🆔 ID: "
        + str(user_id)
        + "\n"

        "👤 Username: "
        + (
            "@" + call.from_user.username
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

    for amount, price_rub in prices["stars"].items():

        amount_int = int(amount)

        crypto_price = ton_price_from_rub(
            price_rub,
            amount_int
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

    amount = call.data.split("_", 1)[1]

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

    price_ton = ton_price_from_rub(
        price_rub,
        amount_int
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
        "Минимум — 50 Stars.\n"
        "Цена рассчитывается автоматически."
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
        amount * float(
            prices["star_price"]
        ),
        2
    )

    price_ton = ton_price_from_rub(
        price_rub,
        amount if amount == 50 else None
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

    for months, price_rub in prices["premium"].items():

        price_ton = premium_ton_price(
            price_rub
        )

        markup.add(
            types.InlineKeyboardButton(
                "💎 "
                + months
                + " мес. — "
                + ton(price_ton)
                + " TON",

                callback_data=
                "premium_"
                + months
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
# ВЫБОР PREMIUM
# =========================================================

@bot.callback_query_handler(
    func=lambda c: c.data.startswith("premium_")
)
def choose_premium(call):

    months = call.data.split("_", 1)[1]

    if months not in prices["premium"]:
        bot.answer_callback_query(
            call.id,
            "❌ Такой вариант отсутствует",
            show_alert=True
        )
        return

    create_order(
        call.from_user.id,
        {
            "product": "Premium",
            "months": int(months),
            "price": prices["premium"][months]
        }
    )

    bot.answer_callback_query(call.id)

    show_recipient(
        call.message.chat.id,
        call.message.message_id,
        call.from_user.id
    )


# =========================================================
# ПОЛУЧАТЕЛЬ
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

    if order["product"] == "Stars":
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
# СЕБЕ
# =========================================================

@bot.callback_query_handler(
    func=lambda c: c.data == "recipient_self"
)
def recipient_self(call):

    order = orders.get(call.from_user.id)

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
        call.from_user.id
    )


# =========================================================
# ДРУГОМУ
# =========================================================

@bot.callback_query_handler(
    func=lambda c: c.data == "recipient_other"
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

    order = orders.get(
        message.from_user.id
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
        message.from_user.id
    )


# =========================================================
# НАЗАД
# =========================================================

@bot.callback_query_handler(
    func=lambda c: c.data == "back_recipient"
)
def back_recipient(call):

    bot.answer_callback_query(call.id)

    show_recipient(
        call.message.chat.id,
        call.message.message_id,
        call.from_user.id
    )


# =========================================================
# ОПЛАТА
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
        "💳 Оплата заказа\n\n"
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
# TON ОПЛАТА
# =========================================================

TON_ADDRESS = (
    "UQAm8vafnYdyPH1u-IA8xD3Sqh3rO-K76LhPh8NUu4oY6J7S"
)

# ВАЖНО:
# Здесь укажи актуальный курс TON к рублю.
TON_RUB_RATE = 125.0


def ton_price(rub_price, is_50_stars=False):

    # 50 Stars — без скидки
    if is_50_stars:
        final_rub = rub_price
    else:
        # Остальные товары — скидка 1%
        final_rub = rub_price * 0.99

    return round(
        final_rub / TON_RUB_RATE,
        4
    )


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

    if (
        order.get("product") == "Stars"
        and int(order.get("amount", 0)) == 50
    ):
        is_50 = True
    else:
        is_50 = False

    ton_amount = ton_price(
        float(order["price"]),
        is_50_stars=is_50
    )

    order["payment_method"] = "TON"
    order["payment_status"] = "waiting_payment"
    order["ton_amount"] = ton_amount

    text = (
        "💎 ОПЛАТА TON\n\n"
        + order_text(order)
        + "\n\n"
        "💎 К оплате: "
        + str(ton_amount)
        + " TON\n\n"
        "📋 Адрес TON:\n"
        + TON_ADDRESS
        + "\n\n"
        "⚠️ После перевода сообщите админу "
        "об оплате.\n\n"
        "⏱ Заказ действует 30 минут."
    )

    bot.answer_callback_query(call.id)

    bot.send_message(
        call.message.chat.id,
        text
    )


# =========================================================
# СБЕРБАНК / СБП
# =========================================================

def send_bank_payment(
    call,
    details,
    method
):

    user_id = call.from_user.id

    order = orders.get(user_id)

    if not order:
        bot.answer_callback_query(
            call.id,
            "❌ Заказ не найден",
            show_alert=True
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
        "📋 Реквизиты:\n"
        + details
        + "\n\n"
        "После оплаты напишите админу."
    )


@bot.callback_query_handler(
    func=lambda c: c.data == "pay_sber"
)
def pay_sber(call):

    send_bank_payment(
        call,
        SBER_DETAILS,
        "Сбербанк"
    )


@bot.callback_query_handler(
    func=lambda c: c.data == "pay_sbp"
)
def pay_sbp(call):

    send_bank_payment(
        call,
        SBP_DETAILS,
        "СБП"
    )


# =========================================================
# ЗАПУСК
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

        print(
            "Ошибка бота:",
            e
        )

        time.sleep(5)
    )

    
