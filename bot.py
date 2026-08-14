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
        "BOT_TOKEN не найден. Добавь BOT_TOKEN в Render Environment."
    )

ADMIN_ID = 6189064599

SUPPORT_USERNAME = "Ireqhat4"

# РЕКВИЗИТЫ
SBER_DETAILS = "2202208584208103 Эрик Ваанович Т."
SBP_DETAILS = "2202208584208103 Эрик Ваанович Т."

PRICES_FILE = "prices.json"
USERS_FILE = "users.json"


# =========================================================
# ЦЕНЫ
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
# DATA
# =========================================================

orders = {}
users = set()

waiting_receipt = set()
waiting_review = set()
broadcast_waiting = set()
price_waiting = {}


# =========================================================
# ЦЕНЫ
# =========================================================

def money(value):
    value = float(value)

    if value.is_integer():
        return str(int(value))

    return str(round(value, 2)).replace(".", ",")


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
        print("Ошибка сохранения цен:", e)


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
            print("Ошибка создания prices.json:", e)

        return data


prices = load_prices()


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

        users = set(int(x) for x in data)

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
        print("Ошибка users.json:", e)


def add_user(user_id):

    if user_id not in users:
        users.add(user_id)
        save_users()


load_users()


# =========================================================
# HELPERS
# =========================================================

def is_admin(user_id):
    return user_id == ADMIN_ID


def username(user):

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

    return (
        product
        + "\n🎁 Получатель: "
        + order.get("recipient", "не указан")
        + "\n💰 Сумма: "
        + money(order["price"])
        + " ₽"
    )


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
                callback_data="broadcast"
            )
        )

        markup.add(
            types.InlineKeyboardButton(
                "💰 Изменить цены",
                callback_data="prices"
            )
        )

    return markup


def send_home(chat_id, user_id):

    bot.send_message(
        chat_id,
        "🏠 Главное меню\n\nВыберите нужное действие:",
        reply_markup=main_menu(user_id)
    )


# =========================================================
# ORDER
# =========================================================

def create_order(user_id, data):

    data["created_at"] = time.time()
    data["expired"] = False
    data["confirmed"] = False

    orders[user_id] = data


# =========================================================
# PAYMENT
# =========================================================

def payment_menu():

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

    if message_id is not None:

        try:
            bot.edit_message_text(
                text,
                chat_id,
                message_id,
                reply_markup=payment_menu()
            )
            return
        except Exception:
            pass

    bot.send_message(
        chat_id,
        text,
        reply_markup=payment_menu()
    )


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

    bot.answer_callback_query(call.id)

    send_home(
        call.message.chat.id,
        call.from_user.id
    )


# =========================================================
# STARS
# =========================================================

@bot.callback_query_handler(
    func=lambda c: c.data == "stars"
)
def stars(call):

    bot.answer_callback_query(call.id)

    markup = types.InlineKeyboardMarkup(
        row_width=2
    )

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


@bot.callback_query_handler(
    func=lambda c: c.data.startswith("star_")
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
    func=lambda c: c.data == "custom_stars"
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
    func=lambda c: c.data == "premium"
)
def premium(call):

    bot.answer_callback_query(call.id)

    markup = types.InlineKeyboardMarkup(
        row_width=1
    )

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


@bot.callback_query_handler(
    func=lambda c: c.data.startswith("premium_")
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
        + "\n\nКому оформить заказ?"
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


@bot.callback_query_handler(
    func=lambda c: c.data == "recipient_self"
)
def recipient_self(call):

    order = orders.get(call.from_user.id)

    if not order:
        bot.answer_callback_query(
            call.id,
            "❌ Заказ не найден"
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

    order = orders.get(message.from_user.id)

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
# PAYMENT METHODS
# =========================================================

def send_payment_details(call, details, method):

    user_id = call.from_user.id
    order = orders.get(user_id)

    if not order:
        bot.answer_callback_query(
            call.id,
            "❌ Заказ не найден"
        )
        return

    order["payment_method"] = method
    waiting_receipt.add(user_id)

    text = (
        "💳 ОПЛАТА\n\n"
        + order_text(order)
        + "\n\n"
        "🏦 Способ: "
        + method
        + "\n\n"
        "📋 Реквизиты:\n"
        + details
        + "\n\n"
        "⚠️ После оплаты отправьте сюда "
        "чек или скриншот оплаты.\n\n"
        "⏱ Заказ действует 30 минут."
    )

    bot.answer_callback_query(call.id)

    bot.send_message(
        call.message.chat.id,
        text
    )


@bot.callback_query_handler(
    func=lambda c: c.data == "pay_sber"
)
def pay_sber(call):

    send_payment_details(
        call,
        SBER_DETAILS,
        "Сбербанк"
    )


@bot.callback_query_handler(
    func=lambda c: c.data == "pay_sbp"
)
def pay_sbp(call):

    send_payment_details(
        call,
        SBP_DETAILS,
        "СБП"
    )
# =========================================================
# RECEIPTS
# =========================================================

@bot.message_handler(
    content_types=["photo", "document"]
)
def receipt(message):

    user_id = message.from_user.id

    if user_id not in waiting_receipt:
        return

    order = orders.get(user_id)

    if not order:
        waiting_receipt.discard(user_id)

        bot.send_message(
            message.chat.id,
            "❌ Заказ не найден."
        )
        return

    order["receipt_received"] = True
    order["payment_status"] = "waiting"

    waiting_receipt.discard(user_id)

    # Сообщение покупателю
    bot.send_message(
        message.chat.id,
        "✅ Чек получен!\n\n"
        "⏳ Ожидайте проверки оплаты администратором."
    )

    # Кнопки админа
    markup = types.InlineKeyboardMarkup(row_width=2)

    markup.add(
        types.InlineKeyboardButton(
            "✅ Одобрить оплату",
            callback_data="approve_" + str(user_id)
        ),
        types.InlineKeyboardButton(
            "❌ Отказать",
            callback_data="reject_" + str(user_id)
        )
    )

    admin_text = (
        "💳 НОВЫЙ ЧЕК\n\n"
        + order_text(order)
        + "\n\n"
        + "👤 Покупатель: "
        + username(message.from_user)
        + "\n"
        + "🆔 ID: "
        + str(user_id)
        + "\n"
        + "💳 Способ: "
        + order.get("payment_method", "не указан")
        + "\n"
        + "📌 Статус: Ожидает проверки"
    )

    try:

        bot.send_message(
            ADMIN_ID,
            admin_text,
            reply_markup=markup
        )

        # Пересылаем сам чек админу
        bot.forward_message(
            ADMIN_ID,
            message.chat.id,
            message.message_id
        )

    except Exception as e:

        print(
            "Ошибка отправки чека админу:",
            e
        )


# =========================================================
# ОДОБРЕНИЕ ОПЛАТЫ
# =========================================================

@bot.callback_query_handler(
    func=lambda c: c.data.startswith("approve_")
)
def approve_payment(call):

    if not is_admin(call.from_user.id):
        bot.answer_callback_query(
            call.id,
            "❌ Нет доступа",
            show_alert=True
        )
        return

    try:
        user_id = int(
            call.data.split("_", 1)[1]
        )
    except Exception:
        bot.answer_callback_query(
            call.id,
            "❌ Ошибка заказа",
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

    order["payment_status"] = "approved"
    order["confirmed"] = True
    order["completed"] = False

    bot.answer_callback_query(
        call.id,
        "✅ Оплата одобрена"
    )

    # Кнопка "Заказ выполнен"
    markup = types.InlineKeyboardMarkup()

    markup.add(
        types.InlineKeyboardButton(
            "✅ Заказ выполнен",
            callback_data="complete_" + str(user_id)
        )
    )

    admin_text = (
        "✅ ОПЛАТА ОДОБРЕНА\n\n"
        + order_text(order)
        + "\n\n"
        + "👤 Покупатель: ID "
        + str(user_id)
        + "\n\n"
        + "📦 Теперь выполните заказ."
    )

    try:

        bot.edit_message_text(
            admin_text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )

    except Exception:
        bot.send_message(
            ADMIN_ID,
            admin_text,
            reply_markup=markup
        )

    # Сообщение покупателю
    try:

        bot.send_message(
            user_id,
            "✅ Оплата подтверждена!\n\n"
            "📦 Ваш заказ принят в работу.\n"
            "⏳ Ожидайте выполнения заказа."
        )

    except Exception as e:

        print(
            "Ошибка сообщения покупателю:",
            e
        )


# =========================================================
# ОТКАЗ ОПЛАТЫ
# =========================================================

@bot.callback_query_handler(
    func=lambda c: c.data.startswith("reject_")
)
def reject_payment(call):

    if not is_admin(call.from_user.id):
        bot.answer_callback_query(
            call.id,
            "❌ Нет доступа",
            show_alert=True
        )
        return

    try:
        user_id = int(
            call.data.split("_", 1)[1]
        )
    except Exception:
        bot.answer_callback_query(
            call.id,
            "❌ Ошибка заказа",
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

    order["payment_status"] = "rejected"
    order["confirmed"] = False

    bot.answer_callback_query(
        call.id,
        "❌ Оплата отклонена"
    )

    try:

        bot.edit_message_text(
            "❌ ОПЛАТА ОТКЛОНЕНА\n\n"
            + order_text(order)
            + "\n\n"
            + "👤 Покупатель: ID "
            + str(user_id),
            call.message.chat.id,
            call.message.message_id
        )

    except Exception:
        pass

    try:

        bot.send_message(
            user_id,
            "❌ Оплата не подтверждена.\n\n"
            "Пожалуйста, свяжитесь с поддержкой:\n"
            "@"
            + SUPPORT_USERNAME
        )

    except Exception as e:

        print(
            "Ошибка сообщения покупателю:",
            e
        )


# =========================================================
# ЗАКАЗ ВЫПОЛНЕН
# =========================================================

@bot.callback_query_handler(
    func=lambda c: c.data.startswith("complete_")
)
def complete_order(call):

    if not is_admin(call.from_user.id):
        bot.answer_callback_query(
            call.id,
            "❌ Нет доступа",
            show_alert=True
        )
        return

    try:
        user_id = int(
            call.data.split("_", 1)[1]
        )
    except Exception:
        bot.answer_callback_query(
            call.id,
            "❌ Ошибка заказа",
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

    if order.get("payment_status") != "approved":
        bot.answer_callback_query(
            call.id,
            "❌ Сначала одобрите оплату",
            show_alert=True
        )
        return

    order["completed"] = True
    order["payment_status"] = "completed"

    # Разрешаем покупателю оставить отзыв
    order["can_review"] = True

    bot.answer_callback_query(
        call.id,
        "✅ Заказ отмечен выполненным"
    )

    try:

        bot.edit_message_text(
            "✅ ЗАКАЗ ВЫПОЛНЕН\n\n"
            + order_text(order)
            + "\n\n"
            + "👤 Покупатель: ID "
            + str(user_id),
            call.message.chat.id,
            call.message.message_id
        )

    except Exception:
        pass

    try:

        markup = types.InlineKeyboardMarkup()

        markup.add(
            types.InlineKeyboardButton(
                "⭐ Оставить отзыв",
                callback_data="review"
            )
        )

        bot.send_message(
            user_id,
            "🎉 Ваш заказ выполнен!\n\n"
            "Спасибо за покупку ❤️\n\n"
            "Теперь вы можете оставить отзыв.",
            reply_markup=markup
        )

    except Exception as e:

        print(
            "Ошибка сообщения о выполнении:",
            e
        )


# =========================================================
# ОТЗЫВ
# Только покупатели с выполненным заказом
# =========================================================

@bot.callback_query_handler(
    func=lambda c: c.data == "review"
)
def review(call):

    user_id = call.from_user.id

    # Проверяем, есть ли выполненный заказ
    completed_order = None

    for order in orders.values():

        if (
            order.get("completed") is True
            and order.get("can_review") is True
        ):
            # orders хранится по user_id
            if orders.get(user_id) is order:
                completed_order = order
                break

    if completed_order is None:

        bot.answer_callback_query(
            call.id,
            "❌ Отзыв доступен только после выполненного заказа.",
            show_alert=True
        )
        return

    bot.answer_callback_query(call.id)

    waiting_review.add(user_id)

    bot.send_message(
        call.message.chat.id,
        "⭐ Напишите ваш отзыв одним сообщением."
    )


# =========================================================
# ПОЛУЧЕНИЕ ОТЗЫВА
# =========================================================

@bot.message_handler(
    func=lambda m: (
        m.from_user.id in waiting_review
        and bool(m.text)
    )
)
def receive_review(message):

    user_id = message.from_user.id

    if user_id not in waiting_review:
        return

    order = orders.get(user_id)

    if not order or not order.get("completed"):
        waiting_review.discard(user_id)

        bot.send_message(
            message.chat.id,
            "❌ Отзыв можно оставить только после выполнения заказа."
        )
        return

    waiting_review.discard(user_id)

    review_text = message.text.strip()

    if not review_text:
        bot.send_message(
            message.chat.id,
            "❌ Отзыв не может быть пустым."
        )
        return

    admin_review = (
        "⭐ НОВЫЙ ОТЗЫВ\n\n"
        + "👤 Покупатель: "
        + username(message.from_user)
        + "\n"
        + "🆔 ID: "
        + str(user_id)
        + "\n\n"
        + review_text
    )

    try:

        bot.send_message(
            ADMIN_ID,
            admin_review
        )

        bot.send_message(
            message.chat.id,
            "✅ Спасибо за ваш отзыв! ❤️"
        )

        # Чтобы один заказ нельзя было использовать
        # для бесконечного количества отзывов
        order["can_review"] = False

    except Exception as e:

        print(
            "Ошибка отправки отзыва:",
            e
        )


# =========================================================
# РАССЫЛКА — АДМИН
# =========================================================

@bot.callback_query_handler(
    func=lambda c: c.data == "broadcast"
)
def broadcast_start(call):

    if not is_admin(call.from_user.id):
        bot.answer_callback_query(
            call.id,
            "❌ Нет доступа",
            show_alert=True
        )
        return

    bot.answer_callback_query(call.id)

    broadcast_waiting.add(call.from_user.id)

    bot.send_message(
        call.message.chat.id,
        "📢 РАССЫЛКА\n\n"
        "Отправьте сообщение, которое нужно разослать всем пользователям.\n\n"
        "Можно отправить текст, фото или документ.\n\n"
        "Для отмены отправьте /cancel."
    )


# =========================================================
# ПОЛУЧЕНИЕ РАССЫЛКИ
# =========================================================

@bot.message_handler(
    func=lambda m: (
        m.from_user.id in broadcast_waiting
        and m.from_user.id == ADMIN_ID
    ),
    content_types=[
        "text",
        "photo",
        "document",
        "video"
    ]
)
def broadcast_send(message):

    user_id = message.from_user.id

    if user_id not in broadcast_waiting:
        return

    if message.text == "/cancel":
        broadcast_waiting.discard(user_id)

        bot.send_message(
            message.chat.id,
            "❌ Рассылка отменена."
        )
        return

    broadcast_waiting.discard(user_id)

    sent = 0
    failed = 0

    bot.send_message(
        ADMIN_ID,
        "📢 Начинаю рассылку...\n"
        "👥 Пользователей: "
        + str(len(users))
    )

    for target_id in list(users):

        try:

            bot.copy_message(
                target_id,
                message.chat.id,
                message.message_id
            )

            sent += 1

            time.sleep(0.05)

        except Exception as e:

            failed += 1

            print(
                "Ошибка рассылки пользователю",
                target_id,
                e
            )

    bot.send_message(
        ADMIN_ID,
        "✅ РАССЫЛКА ЗАВЕРШЕНА\n\n"
        "📨 Отправлено: "
        + str(sent)
        + "\n"
        "❌ Ошибок: "
        + str(failed)
    )


# =========================================================
# ИЗМЕНЕНИЕ ЦЕН
# =========================================================

@bot.callback_query_handler(
    func=lambda c: c.data == "prices"
)
def prices_menu(call):

    if not is_admin(call.from_user.id):
        bot.answer_callback_query(
            call.id,
            "❌ Нет доступа",
            show_alert=True
        )
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
                "⭐ "
                + amount
                + " Stars",
                callback_data="price_stars_" + amount
            )
        )

    for months in prices["premium"]:

        markup.add(
            types.InlineKeyboardButton(
                "💎 Premium "
                + months
                + " мес.",
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
        "💰 ИЗМЕНЕНИЕ ЦЕН\n\n"
        "Выберите цену:",
        reply_markup=markup
    )


# =========================================================
# ВЫБОР ЦЕНЫ
# =========================================================

@bot.callback_query_handler(
    func=lambda c: (
        c.data == "price_star"
        or c.data.startswith("price_stars_")
        or c.data.startswith("price_premium_")
    )
)
def choose_price(call):

    if not is_admin(call.from_user.id):
        bot.answer_callback_query(
            call.id,
            "❌ Нет доступа",
            show_alert=True
        )
        return

    bot.answer_callback_query(call.id)

    data = call.data

    if data == "price_star":

        price_waiting[
            call.from_user.id
        ] = (
            "star_price",
            None
        )

        text = (
            "⭐ Текущая цена 1 Star: "
            + money(prices["star_price"])
            + " ₽\n\n"
            "Введите новую цену:"
        )

    elif data.startswith("price_stars_"):

        amount = data.split(
            "_",
            2
        )[2]

        price_waiting[
            call.from_user.id
        ] = (
            "stars",
            amount
        )

        text = (
            "⭐ "
            + amount
            + " Stars\n"
            "Текущая цена: "
            + money(prices["stars"][amount])
            + " ₽\n\n"
            "Введите новую цену:"
        )

    else:

        months = data.split(
            "_",
            2
        )[2]

        price_waiting[
            call.from_user.id
        ] = (
            "premium",
            months
        )

        text = (
            "💎 Premium "
            + months
            + " месяцев\n"
            "Текущая цена: "
            + money(prices["premium"][months])
            + " ₽\n\n"
            "Введите новую цену:"
        )

    bot.send_message(
        call.message.chat.id,
        text
    )


# =========================================================
# ПОЛУЧЕНИЕ НОВОЙ ЦЕНЫ
# =========================================================

@bot.message_handler(
    func=lambda m: (
        m.from_user.id in price_waiting
        and m.from_user.id == ADMIN_ID
        and bool(m.text)
    )
)
def set_new_price(message):

    user_id = message.from_user.id

    if message.text == "/cancel":

        price_waiting.pop(
            user_id,
            None
        )

        bot.send_message(
            message.chat.id,
            "❌ Изменение цены отменено."
        )
        return

    try:

        new_price = float(
            message.text.replace(",", ".").strip()
        )

        if new_price <= 0:
            raise ValueError

    except Exception:

        bot.send_message(
            message.chat.id,
            "❌ Введите корректную цену.\n"
            "Например: 150 или 149.50"
        )
        return

    target = price_waiting.pop(
        user_id
    )

    category, key = target

    if category == "star_price":

        prices["star_price"] = new_price

        changed = (
            "Цена 1 Star изменена на "
            + money(new_price)
            + " ₽"
        )

    elif category == "stars":

        prices["stars"][key] = new_price

        changed = (
            "Цена "
            + key
            + " Stars изменена на "
            + money(new_price)
            + " ₽"
        )

    else:

        prices["premium"][key] = new_price

        changed = (
            "Цена Premium "
            + key
            + " мес. изменена на "
            + money(new_price)
            + " ₽"
        )

    save_prices()

    bot.send_message(
        message.chat.id,
        "✅ Цена успешно изменена!\n\n"
        + changed
    )


# =========================================================
# ОТМЕНА
# =========================================================

@bot.message_handler(
    commands=["cancel"]
)
def cancel(message):

    user_id = message.from_user.id

    broadcast_waiting.discard(user_id)
    waiting_review.discard(user_id)
    waiting_receipt.discard(user_id)
    price_waiting.pop(user_id, None)

    bot.send_message(
        message.chat.id,
        "❌ Действие отменено."
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
