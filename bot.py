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
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"SELL STARS RT is running")

    def log_message(self, format, *args):
        pass


def run_server():
    port = int(os.environ.get("PORT", "10000"))

    server = HTTPServer(
        ("0.0.0.0", port),
        Handler
    )

    server.serve_forever()


threading.Thread(
    target=run_server,
    daemon=True
).start()


# =========================================================
# НАСТРОЙКИ
# =========================================================

BOT_TOKEN = os.environ.get("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN не найден в Render Environment"
    )


ADMIN_ID = 6189064599

SBER_DETAILS = "2202208584208103 Эрик Ваанович Т."
SBP_DETAILS = "2202208584208103 Эрик Ваанович Т."

SUPPORT_USERNAME = "Ireqhat4"


bot = telebot.TeleBot(
    BOT_TOKEN,
    parse_mode=None
)


# =========================================================
# ФАЙЛ ЦЕН
# =========================================================

PRICES_FILE = "prices.json"

DEFAULT_PRICES = {
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


def save_prices(data):
    try:
        with open(
            PRICES_FILE,
            "w",
            encoding="utf-8"
        ) as file:
            json.dump(
                data,
                file,
                ensure_ascii=False,
                indent=4
            )

    except Exception as error:
        print(
            "Ошибка сохранения prices.json:",
            error
        )


def load_prices():

    try:
        with open(
            PRICES_FILE,
            "r",
            encoding="utf-8"
        ) as file:
            data = json.load(file)

        if "stars" not in data:
            data["stars"] = DEFAULT_PRICES["stars"]

        if "premium" not in data:
            data["premium"] = DEFAULT_PRICES["premium"]

        return data

    except Exception:
        data = {
            "stars": DEFAULT_PRICES["stars"].copy(),
            "premium": DEFAULT_PRICES["premium"].copy()
        }

        save_prices(data)

        return data


prices = load_prices()

STARS_PRICES = prices["stars"]
PREMIUM_PRICES = prices["premium"]


# =========================================================
# ПОЛЬЗОВАТЕЛИ
# =========================================================

USERS_FILE = "users.json"

users = set()


def load_users():

    global users

    try:
        with open(
            USERS_FILE,
            "r",
            encoding="utf-8"
        ) as file:
            users = set(json.load(file))

    except Exception:
        users = set()


def save_users():

    try:
        with open(
            USERS_FILE,
            "w",
            encoding="utf-8"
        ) as file:
            json.dump(
                list(users),
                file,
                ensure_ascii=False
            )

    except Exception as error:
        print(
            "Ошибка сохранения users.json:",
            error
        )


def add_user(user_id):

    if user_id not in users:
        users.add(user_id)
        save_users()


load_users()


# =========================================================
# ЗАКАЗЫ
# =========================================================

orders = {}


# =========================================================
# СОСТОЯНИЯ
# =========================================================

review_waiting = set()

admin_price_waiting = {}


# =========================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =========================================================

def get_username(user):

    if user.username:
        return "@" + user.username

    return "ID " + str(user.id)


def order_text(order):

    if order["product"] == "Stars":

        product = (
            "⭐ Stars: "
            + str(order["amount"])
        )

    else:

        product = (
            "💎 Premium: "
            + str(order["months"])
            + " месяцев"
        )

    recipient = order.get(
        "recipient",
        "не указан"
    )

    price = order.get(
        "price",
        0
    )

    return (
        product
        + "\n🎁 Получатель: "
        + recipient
        + "\n💰 Сумма: "
        + str(price)
        + " ₽"
    )


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
            "💬 Поддержка",
            url="https://t.me/" + SUPPORT_USERNAME
        )
    )

    if user_id == ADMIN_ID:

        markup.add(
            types.InlineKeyboardButton(
                "⚙️ Админ-панель",
                callback_data="admin_panel"
            )
        )

    return markup


def edit_message(
    call,
    text,
    markup=None
):

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
# ПРОВЕРКА СРОКА ЗАКАЗОВ
# =========================================================

def expire_old_orders():

    while True:

        try:

            current_time = time.time()

            expired_users = []

            for user_id, order in list(
                orders.items()
            ):

                created_at = order.get(
                    "created_at",
                    current_time
                )

                if order.get("confirmed"):
                    continue

                if order.get("expired"):
                    continue

                if order.get("waiting_receipt"):
                    continue

                if current_time - created_at >= 1800:

                    order["expired"] = True

                    expired_users.append(
                        user_id
                    )

                    try:

                        bot.send_message(
                            user_id,
                            "❌ Заказ отменён.\n\n"
                            "⏱ Прошло 30 минут "
                            "с момента создания заказа.\n\n"
                            "Если хотите купить снова, "
                            "создайте новый заказ через /start.",
                            reply_markup=main_menu(user_id)
                        )

                    except Exception as error:

                        print(
                            "Ошибка отправки отмены:",
                            error
                        )

            for user_id in expired_users:

                orders.pop(
                    user_id,
                    None
                )

        except Exception as error:

            print(
                "Ошибка проверки заказов:",
                error
            )

        time.sleep(30)


threading.Thread(
    target=expire_old_orders,
    daemon=True
).start()


# =========================================================
# СОЗДАНИЕ ЗАКАЗА
# =========================================================

def create_order(
    user_id,
    order
):

    order["created_at"] = time.time()
    order["expired"] = False
    order["confirmed"] = False
    order["waiting_receipt"] = False

    orders[user_id] = order


# =========================================================
# START
# =========================================================

@bot.message_handler(
    commands=["start"]
)
def start(message):

    add_user(
        message.from_user.id
    )

    text = (
        "👋 Привет, "
        + get_username(message.from_user)
        + "!\n\n"
        "✨ Добро пожаловать в SELL STARS RT!\n\n"
        "⭐ Telegram Stars\n"
        "💎 Telegram Premium\n\n"
        "Выберите нужное действие:"
    )

    bot.send_message(
        message.chat.id,
        text,
        reply_markup=main_menu(
            message.from_user.id
        )
    )


# =========================================================
# HOME
# =========================================================

@bot.callback_query_handler(
    func=lambda call: call.data == "home"
)
def home(call):

    bot.answer_callback_query(
        call.id
    )

    edit_message(
        call,
        "🏠 Главное меню\n\n"
        "Выберите нужное действие:",
        main_menu(
            call.from_user.id
        )
    )


# =========================================================
# STARS
# =========================================================

@bot.callback_query_handler(
    func=lambda call: call.data == "stars"
)
def stars(call):

    bot.answer_callback_query(
        call.id
    )

    markup = types.InlineKeyboardMarkup(
        row_width=2
    )

    for amount, price in STARS_PRICES.items():

        markup.add(
            types.InlineKeyboardButton(
                "⭐ "
                + str(amount)
                + " — "
                + str(price)
                + " ₽",
                callback_data="star_"
                + str(amount)
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

    edit_message(
        call,
        "⭐ Выберите количество Stars:",
        markup
    )


# =========================================================
# ГОТОВЫЕ STARS
# =========================================================

@bot.callback_query_handler(
    func=lambda call: call.data.startswith("star_")
)
def choose_stars(call):

    try:

        amount = int(
            call.data.split(
                "_",
                1
            )[1]
        )

    except Exception:

        bot.answer_callback_query(
            call.id,
            "❌ Ошибка"
        )

        return

    if str(amount) not in STARS_PRICES:

        bot.answer_callback_query(
            call.id,
            "❌ Такой пакет отсутствует"
        )

        return

    create_order(
        call.from_user.id,
        {
            "product": "Stars",
            "amount": amount,
            "price": STARS_PRICES[
                str(amount)
            ]
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
# СВОЁ КОЛИЧЕСТВО
# =========================================================

@bot.callback_query_handler(
    func=lambda call: call.data == "custom_stars"
)
def custom_stars(call):

    bot.answer_callback_query(
        call.id
    )

    message = bot.send_message(
        call.message.chat.id,
        "✏️ Напишите количество Stars.\n\n"
        "Минимум — 50 Stars.\n"
        "Цена — 1,50 ₽ за 1 Star."
    )

    bot.register_next_step_handler(
        message,
        custom_stars_amount
    )


def custom_stars_amount(message):

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

    price = round(
        amount * 1.50
    )

    create_order(
        message.from_user.id,
        {
            "product": "Stars",
            "amount": amount,
            "price": price
        }
    )

    show_recipient(
        message.chat.id,
        None,
        message.from_user.id
    )


# =========================================================
# PREMIUM
# =========================================================

@bot.callback_query_handler(
    func=lambda call: call.data == "premium"
)
def premium(call):

    bot.answer_callback_query(
        call.id
    )

    markup = types.InlineKeyboardMarkup(
        row_width=1
    )

    for months, price in PREMIUM_PRICES.items():

        markup.add(
            types.InlineKeyboardButton(
                "💎 "
                + str(months)
                + " месяцев — "
                + str(price)
                + " ₽",
                callback_data="premium_"
                + str(months)
            )
        )

    markup.add(
        types.InlineKeyboardButton(
            "⬅️ Назад",
            callback_data="home"
        )
    )

    edit_message(
        call,
        "💎 Выберите Telegram Premium:",
        markup
    )


@bot.callback_query_handler(
    func=lambda call: call.data.startswith("premium_")
)
def choose_premium(call):

    try:

        months = int(
            call.data.split(
                "_",
                1
            )[1]
        )

    except Exception:

        bot.answer_callback_query(
            call.id,
            "❌ Ошибка"
        )

        return

    if str(months) not in PREMIUM_PRICES:

        bot.answer_callback_query(
            call.id,
            "❌ Такой вариант отсутствует"
        )

        return

    create_order(
        call.from_user.id,
        {
            "product": "Premium",
            "months": months,
            "price": PREMIUM_PRICES[
                str(months)
            ]
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
# ПОЛУЧАТЕЛЬ
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

    if order.get("expired"):
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

        except Exception:

            bot.send_message(
                chat_id,
                text,
                reply_markup=markup
            )

    else:

        bot.send_message(
            chat_id,
            text,
            reply_markup=markup
        )


# =========================================================
# СЕБЕ
# =========================================================

@bot.callback_query_handler(
    func=lambda call: call.data == "recipient_self"
)
def recipient_self(call):

    user_id = call.from_user.id

    if user_id not in orders:

        bot.answer_callback_query(
            call.id,
            "❌ Заказ не найден"
        )

        return

    order = orders[user_id]

    if order.get("expired"):

        bot.answer_callback_query(
            call.id,
            "❌ Заказ отменён"
        )

        return

    order["recipient"] = (
        get_username(
            call.from_user
        )
    )

    bot.answer_callback_query(
        call.id
    )

    show_payment(
        call.message.chat.id,
        call.message.message_id,
        user_id
    )


# =========================================================
# ДРУГОМУ
# =========================================================

@bot.callback_query_handler(
    func=lambda call: call.data == "recipient_other"
)
def recipient_other(call):

    bot.answer_callback_query(
        call.id
    )

    message = bot.send_message(
        call.message.chat.id,
        "👤 Напишите @username пользователя."
    )

    bot.register_next_step_handler(
        message,
        save_recipient
    )


def save_recipient(message):

    if not message.text:

        bot.send_message(
            message.chat.id,
            "❌ Введите @username."
        )

        return

    recipient = message.text.strip()

    if not recipient.startswith("@"):
        recipient = "@" + recipient

    user_id = message.from_user.id

    if user_id not in orders:

        bot.send_message(
            message.chat.id,
            "❌ Заказ не найден."
        )

        return

    order = orders[user_id]

    if order.get("expired"):

        bot.send_message(
            message.chat.id,
            "❌ Заказ уже отменён."
        )

        return

    order["recipient"] = recipient

    show_payment(
        message.chat.id,
        None,
        user_id
    )


# =========================================================
# ОПЛАТА
# =========================================================

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

    if order.get("expired"):
        return

    markup = types.InlineKeyboardMarkup(
        row_width=1
    )

    markup.add(
        types.InlineKeyboardButton(
            "🏦 Сбербанк",
            callback_data="pay_sber"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "📱 СБП",
            callback_data="pay_sbp"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "⬅️ Назад",
            callback_data="payment_back"
        )
    )

    text = (
        order_text(order)
        + "\n\n"
        "💳 Выберите способ оплаты:"
    )

    if message_id is not None:

        try:

            bot.edit_message_text(
                text,
                chat_id,
                message_id,
                reply_markup=markup
            )

        except Exception:

            bot.send_message(
                chat_id,
                text,
                reply_markup=markup
            )

    else:

        bot.send_message(
            chat_id,
            text,
            reply_markup=markup
        )


# =========================================================
# СБЕРБАНК
# =========================================================

@bot.callback_query_handler(
    func=lambda call: call.data == "pay_sber"
)
def pay_sber(call):

    user_id = call.from_user.id

    if user_id not in orders:

        bot.answer_callback_query(
            call.id,
            "❌ Заказ не найден"
        )

        return

    order = orders[user_id]

    if order.get("expired"):

        bot.answer_callback_qu
