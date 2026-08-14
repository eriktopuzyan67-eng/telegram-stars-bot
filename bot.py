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

    print("Web server started on port", port)

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

SBER_DETAILS = os.environ.get(
    "SBER_DETAILS",
    "Укажите реквизиты Сбербанка"
)

SBP_DETAILS = os.environ.get(
    "SBP_DETAILS",
    "Укажите реквизиты СБП"
)


bot = telebot.TeleBot(
    BOT_TOKEN,
    parse_mode=None
)


# =========================================================
# ФАЙЛЫ
# =========================================================

PRICES_FILE = "prices.json"
USERS_FILE = "users.json"
ORDERS_FILE = "orders.json"


# =========================================================
# ЦЕНЫ ПО УМОЛЧАНИЮ
# =========================================================

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


# =========================================================
# ЗАГРУЗКА ЦЕН
# =========================================================

def save_prices():
    try:
        with open(
            PRICES_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                {
                    "stars": STARS_PRICES,
                    "premium": PREMIUM_PRICES
                },
                file,
                ensure_ascii=False,
                indent=4
            )

    except Exception as error:
        print(
            "Ошибка сохранения цен:",
            error
        )


def load_prices():

    global STARS_PRICES
    global PREMIUM_PRICES

    try:

        with open(
            PRICES_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        STARS_PRICES = data.get(
            "stars",
            DEFAULT_PRICES["stars"].copy()
        )

        PREMIUM_PRICES = data.get(
            "premium",
            DEFAULT_PRICES["premium"].copy()
        )

    except Exception:

        STARS_PRICES = DEFAULT_PRICES["stars"].copy()

        PREMIUM_PRICES = DEFAULT_PRICES["premium"].copy()

        save_prices()


STARS_PRICES = {}
PREMIUM_PRICES = {}

load_prices()


# =========================================================
# ПОЛЬЗОВАТЕЛИ
# =========================================================

users = set()


def load_users():

    global users

    try:

        with open(
            USERS_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            users = set(
                json.load(file)
            )

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
                file
            )

    except Exception as error:

        print(
            "Ошибка сохранения пользователей:",
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
# ОТЗЫВЫ
# =========================================================

review_waiting = set()


# =========================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =========================================================

def get_username(user):

    if user.username:
        return "@" + user.username

    return "ID " + str(user.id)


def order_text(order):

    if order.get("product") == "Stars":

        product = (
            "⭐ Stars: "
            + str(order.get("amount"))
        )

    else:

        product = (
            "💎 Premium: "
            + str(order.get("months"))
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


# =========================================================
# ГЛАВНОЕ МЕНЮ
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
            "💬 Поддержка",
            url="https://t.me/Ireqhat4"
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
    markup
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
# СОХРАНЕНИЕ ЗАКАЗОВ
# =========================================================

def save_orders():

    data = {}

    for user_id, order in orders.items():

        clean_order = {}

        for key, value in order.items():

            if key == "timer":
                continue

            clean_order[key] = value

        data[str(user_id)] = clean_order

    try:

        with open(
            ORDERS_FILE,
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
            "Ошибка сохранения заказов:",
            error
        )


def load_orders():

    global orders

    try:

        with open(
            ORDERS_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        orders = {}

        for user_id, order in data.items():

            orders[int(user_id)] = order

    except Exception:

        orders = {}


load_orders()


# =========================================================
# ТАЙМЕР ЗАКАЗА
# =========================================================

ORDER_TIMEOUT = 30 * 60


def schedule_order_timer(user_id):

    order = orders.get(user_id)

    if not order:
        return

    created_at = order.get(
        "created_at",
        time.time()
    )

    elapsed = time.time() - created_at

    remaining = ORDER_TIMEOUT - elapsed

    if remaining <= 0:

        expire_order(
            user_id,
            order.get("order_id")
        )

        return

    timer = threading.Timer(
        remaining,
        expire_order,
        args=(
            user_id,
            order.get("order_id")
        )
    )

    timer.daemon = True

    timer.start()

    order["timer"] = timer


def expire_order(
    user_id,
    order_id
):

    order = orders.get(user_id)

    if not order:
        return

    # Проверяем, что это всё ещё тот же заказ
    if order.get("order_id") != order_id:
        return

    if order.get("confirmed"):
        return

    # Если чек уже отправлен админу,
    # заказ не удаляем
    if order.get("receipt_sent"):
        return

    order["expired"] = True

    save_orders()

    try:

        bot.send_message(
            user_id,

            "❌ ЗАКАЗ ОТМЕНЁН\n\n"
            "⏱ Время ожидания оплаты "
            "30 минут истекло.\n\n"
            "Если хотите купить снова, "
            "создайте новый заказ через /start.",

            reply_markup=main_menu(
                user_id
            )
        )

    except Exception as error:

        print(
            "Ошибка отправки отмены:",
            error
        )

    orders.pop(
        user_id,
        None
    )

    save_orders()


def create_order(
    user_id,
    order
):

    # Отменяем старый таймер,
    # если у пользователя уже был заказ
    old_order = orders.get(user_id)

    if old_order:

        old_timer = old_order.get(
            "timer"
        )

        if old_timer:

            try:
                old_timer.cancel()
            except Exception:
                pass

    order["order_id"] = (
        str(user_id)
        + "_"
        + str(int(time.time() * 1000))
    )

    order["created_at"] = time.time()

    order["expired"] = False

    order["confirmed"] = False

    order["receipt_sent"] = False

    orders[user_id] = order

    save_orders()

    schedule_order_timer(
        user_id
    )


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

    bot.send_message(
        message.chat.id,

        "👋 Привет, "
        + get_username(
            message.from_user
        )
        + "!\n\n"

        "✨ Добро пожаловать "
        "в SELL STARS RT!\n\n"

        "⭐ Telegram Stars\n"
        "💎 Telegram Premium\n\n"

        "Выберите нужное действие:",

        reply_markup=main_menu(
            message.from_user.id
        )
    )


# =========================================================
# STARS
# =========================================================

@bot.callback_query_handler(
    func=lambda call:
    call.data == "stars"
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

                callback_data=(
                    "star_"
                    + str(amount)
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

    edit_message(
        call,
        "⭐ Выберите количество Stars:",
        markup
    )


# =========================================================
# ГОТОВЫЕ STARS
# =========================================================

@bot.callback_query_handler(
    func=lambda call:
    call.data.startswith("star_")
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

    amount_key = str(amount)

    if amount_key not in STARS_PRICES:

        bot.answer_callback_query(
            call.id,
            "❌ Такой пакет не найден"
        )

        return

    create_order(
        call.from_user.id,

        {
            "product": "Stars",
            "amount": amount,
            "price": STARS_PRICES[
                amount_key
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
# СВОЁ КОЛИЧЕСТВО STARS
# =========================================================

@bot.callback_query_handler(
    func=lambda call:
    call.data == "custom_stars"
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
    func=lambda call:
    call.data == "premium"
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

                callback_data=(
                    "premium_"
                    + str(months)
                )
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
    func=lambda call:
    call.data in (
        "premium_3",
        "premium_6",
        "premium_12"
    )
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

    months_key = str(months)

    if months_key not in PREMIUM_PRICES:

        bot.answer_callback_query(
            call.id,
            "❌ Цена не найдена"
        )

        return

    create_order(
        call.from_user.id,

        {
            "product": "Premium",
            "months": months,
            "price": PREMIUM_PRICES[
                months_key
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
    func=lambda call:
    call.data == "recipient_self"
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

    save_orders()

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
    func=lambda call:
    call.data == "recipient_other"
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

    if orders[user_id].get("expired"):

        bot.send_message(
            message.chat.id,
            "❌ Заказ уже отменён."
        )

        return

    orders[user_id]["recipient"] = recipient

    save_orders()

    show_payment(
        message.chat.id,
        None,
        user_id
    )


# =========================================================
# ОПЛАТА
# =========================================================

def show_payment(
    ch
