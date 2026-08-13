import os
import json
import threading
import traceback
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


def start_web_server():
    port = int(os.environ.get("PORT", "10000"))

    server = HTTPServer(
        ("0.0.0.0", port),
        Handler
    )

    print("WEB SERVER STARTED ON PORT", port)

    server.serve_forever()


threading.Thread(
    target=start_web_server,
    daemon=True
).start()


# =========================================================
# НАСТРОЙКИ
# =========================================================

BOT_TOKEN = os.environ.get("BOT_TOKEN")

if not BOT_TOKEN:
    print("ERROR: BOT_TOKEN НЕ НАЙДЕН В RENDER")
    raise RuntimeError("BOT_TOKEN is not set")


ADMIN_ID = 6189064599

SBER_DETAILS = "2202208584208103 Эрик Ваанович Т."
SBP_DETAILS = "2202208584208103 Эрик Ваанович Т."


bot = telebot.TeleBot(BOT_TOKEN)


# =========================================================
# ЦЕНЫ
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
# ДАННЫЕ
# =========================================================

orders = {}
users = set()

USERS_FILE = "users.json"


def load_users():
    global users

    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            users = set(json.load(f))
    except Exception:
        users = set()


def save_users():
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(list(users), f)
    except Exception as e:
        print("users.json error:", e)


load_users()


def add_user(user_id):
    if user_id not in users:
        users.add(user_id)
        save_users()


# =========================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =========================================================

def username(user):
    if user.username:
        return "@" + user.username

    return "ID " + str(user.id)


def order_text(order):
    if order["product"] == "Stars":
        product = f"⭐ Stars: {order['amount']}"
    else:
        product = f"💎 Premium: {order['months']} мес."

    recipient = order.get("recipient", "не указан")

    return (
        f"{product}\n"
        f"🎁 Получатель: {recipient}\n"
        f"💰 Сумма: {order['price']} ₽"
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
            "💎 Купить Premium",
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


def edit_or_send(call, text, markup=None):

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
        f"👋 Привет, {username(message.from_user)}!\n\n"
        "✨ Добро пожаловать в SELL STARS RT!\n\n"
        "⭐ Telegram Stars\n"
        "💎 Telegram Premium\n\n"
        "Выберите нужный раздел:"
    )

    bot.send_message(
        message.chat.id,
        text,
        reply_markup=main_menu(message.from_user.id)
    )


# =========================================================
# STARS
# =========================================================

@bot.callback_query_handler(
    func=lambda c: c.data == "stars"
)
def stars_menu(call):

    bot.answer_callback_query(call.id)

    markup = types.InlineKeyboardMarkup(row_width=2)

    for amount, price in STARS_PRICES.items():
        markup.add(
            types.InlineKeyboardButton(
                f"⭐ {amount} — {price} ₽",
                callback_data=f"stars_{amount}"
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

    edit_or_send(
        call,
        "⭐ Выберите количество Stars:",
        markup
    )


@bot.callback_query_handler(
    func=lambda c: c.data.startswith("stars_")
)
def select_stars(call):

    try:
        amount = int(call.data.split("_")[1])
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
# СВОИ STARS
# =========================================================

@bot.callback_query_handler(
    func=lambda c: c.data == "custom_stars"
)
def custom_stars(call):

    bot.answer_callback_query(call.id)

    msg = bot.send_message(
        call.message.chat.id,
        "✏️ Введите количество Stars.\n\n"
        "Минимум: 50\n"
        "Цена: 1.40 ₽ за Star."
    )

    bot.register_next_step_handler(
        msg,
        custom_stars_input
    )


def custom_stars_input(message):

    try:
        amount = int(message.text.strip())
    except Exception:
        bot.send_message(
            message.chat.id,
            "❌ Введите число."
        )
        return

    if amount < 50:
        bot.send_message(
            message.chat.id,
            "❌ Минимум — 50 Stars."
        )
        return

    price = round(amount * 1.40)

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
    func=lambda c: c.data == "premium"
)
def premium_menu(call):

    bot.answer_callback_query(call.id)

    markup = types.InlineKeyboardMarkup(row_width=1)

    markup.add(
        types.InlineKeyboardButton(
            "💎 3 месяца — 1150 ₽",
            callback_data="prem_3"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "💎 6 месяцев — 1550 ₽",
            callback_data="prem_6"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "💎 12 месяцев — 2499 ₽",
            callback_data="prem_12"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "⬅️ Назад",
            callback_data="home"
        )
    )

    edit_or_send(
        call,
        "💎 Выберите Telegram Premium:",
        markup
    )


@bot.callback_query_handler(
    func=lambda c: c.data in (
        "prem_3",
        "prem_6",
        "prem_12"
    )
)
def select_premium(call):

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
# ПОЛУЧАТЕЛЬ
# =========================================================

def recipient_menu(chat_id, message_id, user_id):

    order = orders.get(user_id)

    if not order:
        return

    markup = types.InlineKeyboardMarkup(row_width=1)

    markup.add(
        types.InlineKeyboardButton(
            "👤 Себе",
            callback_data="self"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "🎁 Другому",
            callback_data="other"
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
        + "Кому оформить заказ?"
    )

    if message_id:
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
    func=lambda c: c.data == "self"
)
def recipient_self(call):

    user_id = call.from_user.id

    if user_id not in orders:
        bot.answer_callback_query(
            call.id,
            "Заказ не найден"
        )
        return

    orders[user_id]["recipient"] = username(
        call.from_user
    )

    bot.answer_callback_query(call.id)

    payment_menu(
        call.message.chat.id,
        call.message.message_id,
        user_id
    )


# =========================================================
# ДРУГОМУ
# =========================================================

@bot.callback_query_handler(
    func=lambda c: c.data == "other"
)
def recipient_other(call):

    bot.answer_callback_query(call.id)

    msg = bot.send_message(
        call.message.chat.id,
        "👤 Введите @username получателя:"
    )

    bot.register_next_step_handler(
        msg,
        save_recipient
    )


def save_recipient(message):

    if not message.text:
        bot.send_message(
            message.chat.id,
            "❌ Введите username."
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
# ОПЛАТА
# =========================================================

def payment_menu(chat_id, message_id, user_id):

    order = orders.get(user_id)

    if not order:
        return

    markup = types.InlineKeyboardMarkup(row_width=1)

    markup.add(
        types.InlineKeyboardButton(
            "🏦 Сбербанк",
            callback_data="sber"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "📱 СБП",
            callback_data="sbp"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "⬅️ Назад",
            callback_data="recipient"
        )
    )

    text = (
        order_text(order)
        + "\n\n"
        + "💳 Выберите способ оплаты:"
    )

    if message_id:
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
# СБЕР
# =========================================================

@bot.callback_query_handler(
    func=lambda c: c.data == "sber"
)
def sber(call):

    user_id = call.from_user.id

    if user_id not in orders:
        bot.answer_callback_query(
            call.id,
            "Заказ не найден"
        )
        return

    orders[user_id]["payment"] = "Сбербанк"

    bot.answer_callback_query(call.id)

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
            callback_data="payment"
        )
    )

    text = (
        "🏦 СБЕРБАНК\n\n"
        + order_text(orders[user_id])
        + "\n\n"
        + "💳 Реквизиты:\n"
        + SBER_DETAILS
        + "\n\n"
        + "После оплаты нажмите «Я оплатил»."
    )

    edit_or_send(
        call,
        text,
        markup
    )


# =========================================================
# СБП
# =========================================================

@bot.callback_query_handler(
    func=lambda c: c.data == "sbp"
)
def sbp(call):

    user_id = call.from_user.id

    if user_id not in orders:
        bot.answer_callback_query(
            call.id,
            "Заказ не найден"
        )
        return

    orders[user_id]["payment"] = "СБП"

    bot.answer_callback_query(call.id)

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
            callback_data="payment"
        )
    )

    text = (
        "📱 СБП\n\n"
        + order_text(orders[user_id])
        + "\n\n"
        + "💳 Реквизиты:\n"
        + SBP_DETAILS
        + "\n\n"
        + "После оплаты нажмите «Я оплатил»."
    )

    edit_or_send(
        call,
        text,
        markup
    )


# =========================================================
# КНОПКИ НАЗАД
# =========================================================

@bot.callback_query_handler(
    func=lambda c: c.data == "recipient"
)
def back_recipient(call):

    bot.answer_callback_query(call.id)

    recipient_menu(
        call.message.chat.id,
        call.message.message_id,
        call.from_user.id
    )


@bot.callback_query_handler(
    func=lambda c: c.data == "payment"
)
def back_payment(call):

    bot.answer_callback_query(call.id)

    payment_menu(
        call.message.chat.id,
        call.message.message_id,
        call.from_user.id
    )


@bot.callback_query_handler(
    func=lambda c: c.data == "home"
)
def home(call):

    bot.answer_callback_query(call.id)

    edit_or_send(
        call,
        "🏠 Главное меню:",
        main_menu(call.from_user.id)
    )


# =========================================================
# Я ОПЛАТИЛ
# =========================================================

@bot.callback_query_handler(
    func=lambda c: c.data == "paid"
)
def paid(call):

    user_id = call.from_user.id

    if user_id not in orders:
        bot.answer_callback_query(
            call.id,
            "Заказ не найден"
        )
        return

    order = orders[user_id]

    if "payment" not in order:
        bot.answer_callback_query(
            call.id,
            "Выберите оплату"
        )
        return

    order["waiting_receipt"] = True

    bot.answer_callback_query(call.id)

    bot.send_message(
        call.message.chat.id,
        "📸 Отправьте сюда чек или скриншот оплаты."
    )


# =========================================================
# ПОЛУЧЕНИЕ ЧЕКА
# =========================================================

@bot.message_handler(
    content_types=["photo"]
)
def receive_receipt(message):

    user_id = message.from_user.id

    if user_id not in orders:
        bot.reply_to(
            message,
            "❌ Сначала создайте заказ."
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
        f"👤 {username(message.from_user)}\n"
        f"🆔 {user_id}\n\n"
        + order_text(order)
        + "\n"
        + f"💳 Оплата: {order.get('payment', '-')}"
    )

    markup = types.InlineKeyboardMarkup(row_width=2)

    markup.add(
        types.InlineKeyboardButton(
            "✅ Подтвердить",
            callback_data=f"approve_{user_id}"
        ),
        types.InlineKeyboardButton(
            "❌ Отклонить",
            callback_data=f"reject_{user_id}"
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
            "✅ Чек отправлен администратору.\n"
            "Ожидайте проверки."
        )

    except Exception as e:

        print("SEND RECEIPT ERROR:", e)

        bot.reply_to(
            message,
            "❌ Ошибка отправки чека."
        )


# =========================================================
# АДМИН — ПОДТВЕРДИТЬ
# =========================================================

@bot.callback_query_handler(
    func=lambda c: c.data.startswith("approve_")
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
            call.data.split("_")[1]
        )
    except Exception:
        bot.answer_callback_query(
            call.id,
            "Ошибка"
        )
        return

    if user_id not in orders:
        bot.answer_callback_query(
            call.id,
            "Заказ не найден"
        )
        return

    order = orders[user_id]

    order["confirmed"] = True

    bot.answer_callback_query(
        call.id,
        "Оплата подтверждена"
    )

    markup = types.InlineKeyboardMarkup()

    markup.add(
        types.InlineKeyboardButton(
            "📦 Заказ выполнен",
            callback_data=f"done_{user_id}"
        )
    )

    try:
        bot.edit_message_reply_markup(
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
    except Exception:
        pass

    bot.send_message(
        user_id,
        "✅ ОПЛАТА ПОДТВЕРЖДЕНА!\n\n"
        + order_text(order)
        + "\n\n"
        "📦 Заказ передан в обработку."
    )


# =========================================================
# АДМИН — ОТКЛОНИТЬ
# =========================================================

@bo
