import os
import json
import threading
import traceback
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
    print("Starting web server on port:", port)

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
# CONFIG
# =========================================================

BOT_TOKEN = os.environ.get("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN не найден. Добавь BOT_TOKEN в Render Environment."
    )

ADMIN_ID = 6189064599

SBER_DETAILS = "2202208584208103 Эрик Ваанович Т."
SBP_DETAILS = "2202208584208103 Эрик Ваанович Т."


# =========================================================
# BOT
# =========================================================

bot = telebot.TeleBot(BOT_TOKEN)


# =========================================================
# PRICES
# =========================================================

STARS_PRICES = {
    50: 68,
    100: 136,
    150: 204,
    250: 340,
    500: 680,
    1000: 1360
}

PREMIUM_PRICES = {
    3: 1150,
    6: 1550,
    12: 2499
}


# =========================================================
# DATA
# =========================================================

orders = {}
users = set()

USERS_FILE = "users.json"


def load_users():
    global users

    try:
        with open(USERS_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        users = set(data)

    except Exception:
        users = set()


def save_users():
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as file:
            json.dump(list(users), file)

    except Exception as error:
        print("users.json error:", error)


load_users()


def add_user(user_id):
    if user_id not in users:
        users.add(user_id)
        save_users()


# =========================================================
# HELPERS
# =========================================================

def get_username(user):
    if user.username:
        return "@" + user.username

    return "ID " + str(user.id)


def get_order_text(order):
    if order["product"] == "Stars":
        product = "⭐ Stars: " + str(order["amount"])
    else:
        product = "💎 Premium: " + str(order["months"]) + " мес."

    recipient = order.get(
        "recipient",
        "не указан"
    )

    return (
        product
        + "\n"
        + "🎁 Получатель: "
        + recipient
        + "\n"
        + "💰 Сумма: "
        + str(order["price"])
        + " ₽"
    )


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
            "💬 Поддержка",
            callback_data="support"
        )
    )

    if user_id == ADMIN_ID:
        markup.add(
            types.InlineKeyboardButton(
                "📢 Рассылка",
                callback_data="broadcast"
            )
        )

    return markup


def edit_message(call, text, markup):
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
# START
# =========================================================

@bot.message_handler(commands=["start"])
def start(message):
    add_user(message.from_user.id)

    text = (
        "👋 Привет, "
        + get_username(message.from_user)
        + "!\n\n"
        "✨ Добро пожаловать в SELL STARS RT!\n\n"
        "⭐ Telegram Stars\n"
        "💎 Telegram Premium\n\n"
        "Выберите нужный раздел:"
    )

    bot.send_message(
        message.chat.id,
        text,
        reply_markup=main_menu(
            message.from_user.id
        )
    )


# =========================================================
# STARS MENU
# =========================================================

@bot.callback_query_handler(
    func=lambda call: call.data == "stars"
)
def stars_menu(call):
    bot.answer_callback_query(call.id)

    markup = types.InlineKeyboardMarkup(row_width=2)

    for amount, price in STARS_PRICES.items():
        markup.add(
            types.InlineKeyboardButton(
                "⭐ "
                + str(amount)
                + " — "
                + str(price)
                + " ₽",
                callback_data="stars_" + str(amount)
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
# STARS PACKAGE
# =========================================================

@bot.callback_query_handler(
    func=lambda call: call.data.startswith("stars_")
)
def choose_stars(call):
    try:
        amount = int(
            call.data.split("_")[1]
        )

    except Exception:
        bot.answer_callback_query(
            call.id,
            "Ошибка"
        )
        return

    if amount not in STARS_PRICES:
        bot.answer_callback_query(
            call.id,
            "Пакет не найден"
        )
        return

    orders[call.from_user.id] = {
        "product": "Stars",
        "amount": amount,
        "price": STARS_PRICES[amount]
    }

    bot.answer_callback_query(call.id)

    recipient_menu(
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
        "Цена — 1,40 ₽ за 1 Star."
    )

    bot.register_next_step_handler(
        msg,
        custom_stars_input
    )


def custom_stars_input(message):
    if not message.text:
        bot.send_message(
            message.chat.id,
            "❌ Введите количество числом."
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
            "❌ Минимальный заказ — 50 Stars."
        )
        return

    price = round(
        amount * 1.40
    )

    orders[message.from_user.id] = {
        "product": "Stars",
        "amount": amount,
        "price": price
    }

    recipient_menu(
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
def premium_menu(call):
    bot.answer_callback_query(call.id)

    markup = types.InlineKeyboardMarkup(row_width=1)

    markup.add(
        types.InlineKeyboardButton(
            "💎 3 месяца — 1150 ₽",
            callback_data="premium_3"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "💎 6 месяцев — 1550 ₽",
            callback_data="premium_6"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "💎 12 месяцев — 2499 ₽",
            callback_data="premium_12"
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
        "💎 Выберите срок Telegram Premium:",
        markup
    )


# =========================================================
# PREMIUM PACKAGE
# =========================================================

@bot.callback_query_handler(
    func=lambda call: call.data in (
        "premium_3",
        "premium_6",
        "premium_12"
    )
)
def choose_premium(call):
    months = int(
        call.data.split("_")[1]
    )

    orders[call.from_user.id] = {
        "product": "Premium",
        "months": months,
        "price": PREMIUM_PRICES[months]
    }

    bot.answer_callback_query(call.id)

    recipient_menu(
        call.message.chat.id,
        call.message.message_id,
        call.from_user.id
    )


# =========================================================
# RECIPIENT
# =========================================================

def recipient_menu(
    chat_id,
    message_id,
    user_id
):
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
        get_order_text(order)
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
# RECIPIENT SELF
# =========================================================

@bot.callback_query_handler(
    func=lambda call: call.data == "recipient_self"
)
def recipient_self(call):
    user_id = call.from_user.id

    if user_id not in orders:
        bot.answer_callback_query(
            call.id,
            "Заказ не найден"
        )
        return

    orders[user_id]["recipient"] = get_username(
        call.from_user
    )

    bot.answer_callback_query(call.id)

    payment_menu(
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
        "👤 Напишите @username получателя:"
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

    payment_menu(
        message.chat.id,
        None,
        user_id
    )


# =========================================================
# PAYMENT MENU
# =========================================================

def payment_menu(
    chat_id,
    message_id,
    user_id
):
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
            callback_data="back_recipient"
        )
    )

    text = (
        get_order_text(order)
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
# SBERBANK
# =========================================================

@bot.callback_query_handler(
    func=lambda call: call.data == "pay_sber"
)
def pay_sber(call):
    user_id = call.from_user.id

    if user_id not in orders:
        bot.answer_callback_query(
            call.id,
            "Заказ не найден"
        )
        return

    order = orders[user_id]
    order["payment"] = "Сбербанк"

    bot.answer_callback_query(call.id)

    markup = types.InlineKeyboardMarkup(row_width=1)

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
        "🏦 ОПЛАТА СБЕРБАНК\n\n"
        + get_order_text(order)
        + "\n\n"
        "💳 Реквизиты:\n"
        + SBER_DETAILS
        + "\n\n"
        "После оплаты нажмите «Я оплатил» "
        "и отправьте чек."
    )

    edit_message(
        call,
        text,
        markup
    )


# =========================================================
# SBP
# =========================================================

@bot.callback_query_handler(
    func=lambda call: call.data == "pay_sbp"
)
def pay_sbp(call):
    user_id = call.from_user.id

    if user_id not in orders:
        bot.answer_callback_query(
            call.id,
            "Заказ не найден"
        )
        return

    order = orders[user_id]
    order["payment"] = "СБП"

    bot.answer_callback_query(call.id)

    markup = types.InlineKeyboardMarkup(row_width=1)

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
        "📱 ОПЛАТА СБП\n\n"
        + get_order_text(order)
        + "\n\n"
        "💳 Реквизиты:\n"
        + SBP_DETAILS
        + "\n\n"
        "После оплаты нажмите «Я оплатил» "
        "и отправьте чек."
    )

    edit_message(
        call,
        text,
        markup
    )


# =========================================================
# BACK RECIPIENT
# =========================================================

@bot.callback_query_handler(
    func=lambda call: call.data == "back_recipient"
)
def back_recipient(call):
    bot.answer_callback_query(call.id)

    recipient_menu(
        call.message.chat.id,
        call.message.message_id,
        call.from_user.id
    )


# =========================================================
# BACK PAYMENT
# =========================================================

@bot.callback_query_handler(
    func=lambda call: call.data == "back_payment"
)
def back_payment(call):
    bot.answer_callback_query(call.id)

    payment_menu(
        call.message.chat.id,
        call.message.message_id,
        call.from_user.id
    )


# =========================================================
# PAID
# =========================================================

@bot.callback_query_handler(
    func=lambda call: call.data == "paid"
)
def paid(call):
    user_id = call.from_user.id

    if user_id not in orders:
        bot.answer_callback_query(
            call.id,
            "Заказ не найден"
        )
        return

    orders[user_id]["waiting_receipt"] = True

    bot.answer_callback_query(call.id)

    bot.send_message(
        call.message.chat.id,
        "📸 Теперь отправьте сюда чек "
        "или скриншот оплаты."
    )


# =========================================================
# RECEIPT
# =========================================================

@bot.message_handler(
    content_types=["photo"]
)
def receipt_photo(message):
    user_id = message.from_user.id

    if user_id not in orders:
        bot.reply_to(
            message,
            "❌ Сначала создайте заказ через /start."
        )
        return

    order = orders[user_id]

    if not order.get("waiting_receipt"):
        bot.reply_to(
            message,
            "❌ Сначала нажмите «Я оплатил»."
        )
        return

    file_id = message.photo[-1].file_id

    order["receipt"] = file_id
    order["waiting_receipt"] = False

    admin_text = (
        "🧾 НОВЫЙ ЧЕК\n\n"
        "👤 Покупатель: "
        + get_username(message.from_user)
        + "\n"
        "🆔 ID: "
        + str(user_id)
        + "\n\n"
        + get_order_text(order)
        + "\n"
        "💳 Оплата: "
        + order.get("payment", "не указано")
    )

    markup = types.InlineKeyboardMarkup(row_width=2)

    markup.add(
        types.InlineKeyboardButton(
            "✅ Подтвердить",
            callback_data="approve_" + str(user_id)
        ),
        types.InlineKeyboardButton(
            "❌ Отклонить",
            callback_data="reject_" + str(user_id)
        )
    )

    try:
        bot.send_photo(
            ADMIN_ID,
            file_id,
            caption=admin_text,
            reply_markup=markup
        )

        bot.reply_to(
            message,
            "✅ Чек отправлен администратору!\n\n"
            "⏳ Ожидайте проверки."
        )

    except Exception as error:
        print("Receipt error:", error)

        bot.reply_to(
            message,
            "❌ Не удалось отправить чек."
        )


# =========================================================
# ADMIN APPROVE
# =========================================================

@bot.callback_query_handler(
    func=lambda call: call.data.startswith("approve_")
)
def approve(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(
            call.id,
            "⛔ Нет доступа"
        )
        return

    try:
        user_id = int(
    
