import os
import json
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
        self.end_headers()
        self.wfile.write(b"SELL STARS RT is running")

    def log_message(self, format, *args):
        pass


def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), Handler)
    server.serve_forever()


threading.Thread(
    target=run_server,
    daemon=True
).start()


# =========================================================
# НАСТРОЙКИ
# =========================================================

BOT_TOKEN = os.environ["BOT_TOKEN"]

ADMIN_ID = 6189064599

SBER_DETAILS = "2202208584208103 Эрик Ваанович Т."
SBP_DETAILS = "2202208584208103 Эрик Ваанович Т."

bot = telebot.TeleBot(BOT_TOKEN)


# =========================================================
# ЦЕНЫ STARS
# =========================================================

PRICES = {
    50: 68,
    100: 136,
    150: 204,
    250: 340,
    500: 680,
    1000: 1360
}


# =========================================================
# ЦЕНЫ PREMIUM
# =========================================================

PREMIUM_PRICES = {
    3: 1150,
    6: 1550,
    12: 2499
}


# =========================================================
# ЗАКАЗЫ
# =========================================================

orders = {}


# =========================================================
# ПОЛЬЗОВАТЕЛИ
# =========================================================

USERS_FILE = "users.json"


def load_users():
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as file:
            return set(json.load(file))
    except Exception:
        return set()


users = load_users()


def save_users():
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as file:
            json.dump(list(users), file)
    except Exception as error:
        print("Ошибка users.json:", error)


# =========================================================
# USERNAME
# =========================================================

def get_username(user):
    if user.username:
        return "@" + user.username

    return "ID " + str(user.id)


# =========================================================
# ГЛАВНОЕ МЕНЮ
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


# =========================================================
# ОПИСАНИЕ ЗАКАЗА
# =========================================================

def order_description(order):

    if order["product"] == "Stars":

        return (
            f"⭐ Stars: {order['amount']}\n"
            f"🎁 Получатель: {order.get('recipient', 'не указан')}\n"
        )

    return (
        f"💎 Premium: {order['months']} мес.\n"
        f"🎁 Получатель: {order.get('recipient', 'не указан')}\n"
    )


# =========================================================
# START
# =========================================================

@bot.message_handler(commands=["start"])
def start(message):

    user_id = message.from_user.id

    users.add(user_id)
    save_users()

    username = get_username(message.from_user)

    text = (
        f"👋 Приветствую, {username}!\n\n"
        "✨ Добро пожаловать в бота SELL STARS RT!\n\n"
        "⭐ Здесь вы можете купить звёзды "
        "по курсу 1,40 ₽ за 1 шт.\n\n"
        "📦 Минимальный заказ — от 50 Stars.\n\n"
        "💎 Так же продаются Telegram Premium.\n\n"
        "Выберите нужное действие:"
    )

    bot.send_message(
        message.chat.id,
        text,
        reply_markup=main_menu(user_id)
    )


# =========================================================
# STARS
# =========================================================

@bot.callback_query_handler(
    func=lambda call: call.data == "stars"
)
def stars(call):

    markup = types.InlineKeyboardMarkup(row_width=2)

    for amount, price in PRICES.items():

        markup.add(
            types.InlineKeyboardButton(
                f"⭐ {amount} — {price} ₽",
                callback_data=f"amount_{amount}"
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
            callback_data="back"
        )
    )

    bot.answer_callback_query(call.id)

    bot.edit_message_text(
        "⭐ Выберите количество Stars:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )


# =========================================================
# ГОТОВОЕ КОЛИЧЕСТВО
# =========================================================

@bot.callback_query_handler(
    func=lambda call: call.data.startswith("amount_")
)
def choose_amount(call):

    amount = int(
        call.data.split("_", 1)[1]
    )

    orders[call.from_user.id] = {
        "product": "Stars",
        "amount": amount,
        "price": PRICES[amount]
    }

    bot.answer_callback_query(call.id)

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

    bot.answer_callback_query(call.id)

    markup = types.InlineKeyboardMarkup()

    markup.add(
        types.InlineKeyboardButton(
            "⬅️ Назад",
            callback_data="stars"
        )
    )

    msg = bot.send_message(
        call.message.chat.id,
        "✏️ Напишите количество Stars.\n\n"
        "Минимум — 50 Stars.\n"
        "Цена — 1,40 ₽ за 1 Star.",
        reply_markup=markup
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
            callback_data="back"
        )
    )

    bot.answer_callback_query(call.id)

    bot.edit_message_text(
        "💎 Выберите срок Telegram Premium:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )


# =========================================================
# ВАЖНО: ТОЛЬКО ЧИСЛОВЫЕ PREMIUM CALLBACK
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
        call.data.split("_", 1)[1]
    )

    orders[call.from_user.id] = {
        "product": "Premium",
        "months": months,
        "price": PREMIUM_PRICES[months]
    }

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

        back_callback = "stars"

    else:

        back_callback = "premium"

    markup.add(
        types.InlineKeyboardButton(
            "⬅️ Назад",
            callback_data=back_callback
        )
    )

    text = (
        order_description(order)
        + f"💰 Сумма: {order['price']} ₽\n\n"
        "Кому отправить/оформить?"
    )

    if message_id is not None:

        bot.edit_message_text(
            text,
            chat_id,
            message_id,
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
            "Заказ не найден"
        )

        return

    orders[user_id]["recipient"] = get_username(
        call.from_user
    )

    bot.answer_callback_query(call.id)

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

    bot.answer_callback_query(call.id)

    markup = types.InlineKeyboardMarkup()

    markup.add(
        types.InlineKeyboardButton(
            "⬅️ Назад",
            callback_data="recipient_back"
        )
    )

    msg = bot.send_message(
        call.message.chat.id,
        "👤 Напишите @username пользователя,\n"
        "которому отправить Stars или оформить Premium.",
        reply_markup=markup
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
# НАЗАД К ПОЛУЧАТЕЛЮ
# =========================================================

@bot.callback_query_handler(
    func=lambda call: call.data == "recipient_back"
)
def recipient_back(call):

    bot.answer_callback_query(call.id)

    show_recipient(
        call.message.chat.id,
        call.message.message_id,
        call.from_user.id
    )


# =========================================================
# ОПЛАТА
# =========================================================

def show_payment(
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
            callback_data="payment_back"
        )
    )

    text = (
        order_description(order)
        + f"💰 Сумма: {order['price']} ₽\n\n"
        "Выберите способ оплаты:"
    )

    if message_id is not None:

        bot.edit_message_text(
            text,
            chat_id,
            message_id,
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

    order = orders.get(user_id)

    if not order:

        bot.answer_callback_query(
            call.id,
            "Заказ не найден"
        )

        return

    order["payment"] = "Сбербанк"

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
            callback_data="payment_back"
        )
    )

    bot.answer_callback_query(call.id)

    bot.edit_message_text(
        "🏦 ОПЛАТА СБЕРБАНК\n\n"
        + order_description(order)
        + f"💰 Сумма: {order['price']} ₽\n\n"
        + f"Реквизиты:\n{SBER_DETAILS}\n\n"
        "После оплаты нажмите «Я оплатил» "
        "и отправьте чек.",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )


# =========================================================
# СБП
# =========================================================

@bot.callback_query_handler(
    func=lambda call: call.data == "pay_sbp"
)
def pay_sbp(call):

    user_id = call.from_user.id

    order = orders.get(user_id)

    if not order:

        bot.answer_callback_query(
            call.id,
            "Заказ не найден"
        )

        return

    order["payment"] = "СБП"

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
            callback_data="payment_back"
        )
    )

    bot.answer_callback_query(call.id)

    bot.edit_message_text(
        "📱 ОПЛАТА СБП\n\n"
        + order_description(order)
        + f"💰 Сумма: {order['price']} ₽\n\n"
        + f"Реквизиты:\n{SBP_DETAILS}\n\n"
        "После оплаты нажмите «Я оплатил» "
        "и отправьте чек.",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )


# =========================================================
# НАЗАД ОТ ОПЛАТЫ
# =========================================================

@bot.callback_query_handler(
    func=lambda call: call.data == "payment_back"
)
def payment_back(call):

    bot.answer_callback_query(call.id)

    show_recipient(
        call.message.chat.id,
        call.message.message_id,
        call.from_user.id
    )


# =========================================================
# Я ОПЛАТИЛ
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
        "или скриншот оплаты.\n\n"
        "⏳ Ожидайте проверки платежа.\n"
        "Это займет не больше 15 минут."
    )


# =========================================================
# ПОЛУЧЕНИЕ ЧЕКА
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

    admin_text = (
        "🧾 НОВЫЙ ЧЕК\n\n"
        f"👤 Покупатель: {get_username(message.from_user)}\n"
        f"🆔 ID: {user_id}\n\n"
        + order_description(order)
        + f"💰 Сумма: {order['price']} ₽\n"
        + f"💳 Оплата: {order.get('payment', 'не указано')}"
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

    bot.send_photo(
        ADMIN_ID,
        message.photo[-1].file_id,
        caption=admin_text,
        reply_markup=markup
    )

    bot.reply_to(
        message,
        "✅ Чек отправлен администратору!\n\n"
        "⏳ Ожидайте проверки платежа.\n"
        "Это займет не больше 15 минут."
    )


# =========================================================
# АДМИН: ПОДТВЕРДИТЬ
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

    user_id = int(
        call.data.split("_", 1)[1]
    )

    order = orders.get(user_id)

    if not order:

        bot.answer_callback_query(
            call.id,
            "Заказ уже обработан"
        )

        return

    order["payment_confirmed"] = True

    markup = types.InlineKeyboardMarkup()

    markup.add(
        types.InlineKeyboardButton(
            "📦 Заказ выполнен",
            callback_data=f"done_{user_id}"
        )
    )

    bot.send_message(
     
