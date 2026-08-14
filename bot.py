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
    server = HTTPServer(("0.0.0.0", port), Handler)
    server.serve_forever()


threading.Thread(target=run_server, daemon=True).start()


# =========================================================
# SETTINGS
# =========================================================

BOT_TOKEN = os.environ.get("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не найден в Render Environment")

ADMIN_ID = 6189064599

SBER_DETAILS = "2202208584208103 Эрик Ваанович Т."
SBP_DETAILS = "2202208584208103 Эрик Ваанович Т."

SUPPORT_USERNAME = "Ireqhat4"

USERS_FILE = "users.json"
PRICES_FILE = "prices.json"


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

bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)


# =========================================================
# DATA
# =========================================================

orders = {}
users = set()

waiting_receipt = set()
waiting_review = set()
broadcast_waiting = set()
price_waiting = {}


# =========================================================
# PRICES
# =========================================================

def save_prices():
    try:
        with open(PRICES_FILE, "w", encoding="utf-8") as f:
            json.dump(
                prices,
                f,
                ensure_ascii=False,
                indent=4
            )
    except Exception as e:
        print("Ошибка сохранения цен:", e)


def load_prices():
    try:
        with open(PRICES_FILE, "r", encoding="utf-8") as f:
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
                data.get("stars", {}).get(
                    amount,
                    default
                )
            )

        for months, default in DEFAULT_PRICES["premium"].items():
            result["premium"][months] = float(
                data.get("premium", {}).get(
                    months,
                    default
                )
            )

        return result

    except Exception:
        data = {
            "star_price": DEFAULT_PRICES["star_price"],
            "stars": DEFAULT_PRICES["stars"].copy(),
            "premium": DEFAULT_PRICES["premium"].copy()
        }

        try:
            with open(PRICES_FILE, "w", encoding="utf-8") as f:
                json.dump(
                    data,
                    f,
                    ensure_ascii=False,
                    indent=4
                )
        except Exception as e:
            print("Ошибка создания prices.json:", e)

        return data


prices = load_prices()


def money(value):
    value = float(value)

    if value.is_integer():
        return str(int(value))

    return str(round(value, 2)).replace(".", ",")


def refresh_star_prices():
    for amount in prices["stars"]:
        try:
            prices["stars"][amount] = round(
                int(amount) * float(prices["star_price"]),
                2
            )
        except Exception:
            pass

    save_prices()


# =========================================================
# USERS
# =========================================================

def load_users():
    global users

    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        users = set(int(x) for x in data)

    except Exception:
        users = set()


def save_users():
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(
                list(users),
                f,
                ensure_ascii=False
            )
    except Exception as e:
        print("Ошибка users.json:", e)


def add_user(user_id):
    if user_id not in users:
        users.add(user_id)
        save_users()


load_users()


# =========================================================
# HELPERS
# =========================================================

def get_username(user):
    if user.username:
        return "@" + user.username

    return "ID " + str(user.id)


def is_admin(user_id):
    return user_id == ADMIN_ID


def order_text(order):
    if order["product"] == "Stars":
        product = "⭐ Stars: " + str(order["amount"])
    else:
        product = (
            "💎 Premium: "
            + str(order["months"])
            + " месяцев"
        )

    return (
        product
        + "\n🎁 Получатель: "
        + order.get("recipient", "не указан")
        + "\n💰 Сумма: "
        + money(order.get("price", 0))
        + " ₽"
    )


# =========================================================
# MAIN MENU
# =========================================================

def main_menu(user_id):
    markup = types.InlineKeyboardMarkup(row_width=1)

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
            "⭐ Оставить отзыв",
            callback_data="review"
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
                "📢 Рассылка",
                callback_data="admin_broadcast"
            )
        )

        markup.add(
            types.InlineKeyboardButton(
                "💰 Изменить цены",
                callback_data="admin_prices"
            )
        )

    return markup


def send_main_menu(chat_id, user_id):
    bot.send_message(
        chat_id,
        "🏠 Главное меню\n\nВыберите нужное действие:",
        reply_markup=main_menu(user_id)
    )


# =========================================================
# ORDERS
# =========================================================

def create_order(user_id, data):
    data["created_at"] = time.time()
    data["expired"] = False
    data["confirmed"] = False
    data["waiting_receipt"] = False
    data["receipt_received"] = False

    orders[user_id] = data


def expire_orders_loop():
    while True:
        try:
            now = time.time()

            for user_id, order in list(orders.items()):
                if order.get("confirmed"):
                    continue

                if order.get("expired"):
                    continue

                created_at = order.get("created_at", now)

                if now - created_at < 1800:
                    continue

                order["expired"] = True

                orders.pop(user_id, None)
                waiting_receipt.discard(user_id)

                try:
                    bot.send_message(
                        user_id,
                        "❌ Заказ отменён.\n\n"
                        "⏱ Прошло 30 минут с момента создания заказа.\n\n"
                        "Если хотите купить снова — нажмите /start.",
                        reply_markup=main_menu(user_id)
                    )
                except Exception as e:
                    print("Ошибка уведомления:", e)

        except Exception as e:
            print("Ошибка expire_orders_loop:", e)

        time.sleep(30)


threading.Thread(
    target=expire_orders_loop,
    daemon=True
).start()


# =========================================================
# START
# =========================================================

@bot.message_handler(commands=["start"])
def start(message):
    user_id = message.from_user.id

    add_user(user_id)

    waiting_receipt.discard(user_id)
    waiting_review.discard(user_id)
    broadcast_waiting.discard(user_id)
    price_waiting.pop(user_id, None)

    bot.send_message(
        message.chat.id,
        "👋 Привет, "
        + get_username(message.from_user)
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
    func=lambda call: call.data == "home"
)
def home(call):
    bot.answer_callback_query(call.id)

    try:
        bot.edit_message_text(
            "🏠 Главное меню\n\nВыберите нужное действие:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=main_menu(call.from_user.id)
        )
    except Exception:
        send_main_menu(
            call.message.chat.id,
            call.from_user.id
        )


# =========================================================
# STARS
# =========================================================

@bot.callback_query_handler(
    func=lambda call: call.data == "stars"
)
def stars(call):
    bot.answer_callback_query(call.id)

    markup = types.InlineKeyboardMarkup(row_width=2)

    for amount, price in prices["stars"].items():
        markup.add(
            types.InlineKeyboardButton(
                "⭐ "
                + amount
                + " — "
                + money(price)
                + " ₽",
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

    try:
        bot.edit_message_text(
            "⭐ Выберите количество Stars:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
    except Exception:
        bot.send_message(
            call.message.chat.id,
            "⭐ Выберите количество Stars:",
            reply_markup=markup
        )


# =========================================================
# READY STARS
# =========================================================

@bot.callback_query_handler(
    func=lambda call: call.data.startswith("star_")
)
def choose_stars(call):
    amount = call.data.split("_", 1)[1]

    if amount not in prices["stars"]:
        bot.answer_callback_query(
            call.id,
            "❌ Такой пакет отсутствует"
        )
        return

    create_order(
        call.from_user.id,
        {
            "product": "Stars",
            "amount": int(amount),
            "price": prices["stars"][amount]
        }
    )

    bot.answer_callback_query(call.id)

    show_recipient(
        call.message.chat.id,
        call.message.message_id,
        call.from_user.id
    )


# =========================================================
# CUSTOM STARS
# =========================================================

@bot.callback_query_handler(
    func=lambda call: call.data == "custom_stars"
)
def custom_stars(call):
    bot.answer_callback_query(call.id)

    msg = bot.send_message(
        call.message.chat.id,
        "✏️ Напишите количество Stars.\n\n"
        "Минимум — 50 Stars.\n"
        "Цена — "
        + money(prices["star_price"])
        + " ₽ за 1 Star."
    )

    bot.register_next_step_handler(
        msg,
        custom_stars_amount
    )


def custom_stars_amount(message):
    if not message.text:
        bot.send_message(
            message.chat.id,
            "❌ Введите количество числом."
        )
        return

    try:
        amount = int(message.text.strip())
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
        amount * float(prices["star_price"]),
        2
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
    bot.answer_callback_query(call.id)

    markup = types.InlineKeyboardMarkup(row_width=1)

    for months, price in prices["premium"].items():
        markup.add(
            types.InlineKeyboardButton(
                "💎 "
                + months
                + " месяцев — "
                + money(price)
                + " ₽",
                callback_data="premium_" + months
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
            "💎 Выберите Telegram Premium:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
    except Exception:
        bot.send_message(
            call.message.chat.id,
            "💎 Выберите Telegram Premium:",
            reply_markup=markup
        )


# =========================================================
# CHOOSE PREMIUM
# =========================================================

@bot.callback_query_handler(
    func=lambda call: call.data.startswith("premium_")
)
def choose_premium(call):
    months = call.data.split("_", 1)[1]

    if months not in prices["premium"]:
        bot.answer_callback_query(
            call.id,
            "❌ Такой вариант отсутствует"
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
# RECIPIENT
# =========================================================

def show_recipient(chat_id, message_id, user_id):
    order = orders.get(user_id)

    if not order or order.get("expired"):
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
        + "\n\nКому оформить заказ?"
    )

    if message_id is None:
        bot.send_message(
            chat_id,
            text,
            reply_markup=markup
        )
    else:
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


# =========================================================
# RECIPIENT SELF
# =========================================================

@bot.callback_query_handler(
    func=lambda call: call.data == "recipient_self"
)
def recipient_self(call):
    user_id = call.from_user.id

    order = orders.get(user_id)

    if not order:
        bot.answer_callback_query(
            call.id,
            "❌ Заказ не найден"
        )
        return

    order["recipient"] = get_username(
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
    func=lambda call: call.data == "recipient_other"
)
def recipient_other(call):
    bot.answer_callback_query(call.id)

    msg = bot.send_message(
        call.message.chat.id,
        "👤 Напишите @username получателя.\n\n"
        "Например: @username"
    )

    bot.register_next_step_handler(
        msg,
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

    orders[user_id]["recipient"] = recipient

    show_payment(
        message.chat.id,
        None,
        user_id
    )


# =========================================================
# PAYMENT
# =========================================================

def show_payment(chat_id, message_id, user_id):
    order = orders.get(user_id)

    if not order:
        return

    markup = types.InlineKeyboardMarkup(row_width=1)

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
        + "\n\n💳 Выберите способ оплаты:"
    )

    if message_id is None:
        bot.send_message(
            chat_id,
            text,
            reply_markup=markup
        )
    else:
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


# ==========================
